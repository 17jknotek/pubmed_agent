from __future__ import annotations

import os
import secrets
from typing import Any

from fastapi import APIRouter, Cookie, HTTPException
from fastapi.responses import RedirectResponse
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build
from google.oauth2.credentials import Credentials
from loguru import logger
from pydantic import BaseModel

from app.services.supabase_service import get_supabase

router = APIRouter()

SCOPES: list[str] = ["https://www.googleapis.com/auth/drive.readonly"]
DRIVE_LIST_PAGE_SIZE = 50
OAUTH_STATE_COOKIE = "google_oauth_state"
OAUTH_CODE_VERIFIER_COOKIE = "google_oauth_code_verifier"

def _is_https() -> bool:
    """
    Cookies must be Secure on HTTPS, but localhost dev is often plain HTTP.
    """
    frontend_url = os.getenv("FRONTEND_URL", "http://localhost:3000")
    redirect_uri = os.getenv("GOOGLE_REDIRECT_URI", "")
    return frontend_url.startswith("https://") and redirect_uri.startswith("https://")


def _drive_service_for_session(session_id: str):
    token = _get_token_for_session(session_id)
    credentials = Credentials(token=token["google_access_token"])
    return build("drive", "v3", credentials=credentials)


def _list_drive_files(service) -> list[dict[str, Any]]:
    results = (
        service.files()
        .list(
            pageSize=DRIVE_LIST_PAGE_SIZE,
            fields="files(id, name, mimeType)",
            q="'me' in owners",
            orderBy="modifiedTime desc",
        )
        .execute()
    )
    return results.get("files", [])

def get_flow():
    return Flow.from_client_config(
        {
            "web": {
                "client_id": os.getenv("GOOGLE_CLIENT_ID"),
                "client_secret": os.getenv("GOOGLE_CLIENT_SECRET"),
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token",
                "redirect_uris": [os.getenv("GOOGLE_REDIRECT_URI")],
            }
        },
        scopes=SCOPES,
        redirect_uri=os.getenv("GOOGLE_REDIRECT_URI"),
    )

@router.get("/auth")
async def drive_auth():
    flow = get_flow()
    auth_url, state = flow.authorization_url(
        access_type="offline",
        include_granted_scopes="true",
        prompt="consent",
        code_challenge_method="S256",
    )
    logger.info("Redirecting user to Google OAuth consent screen")
    response = RedirectResponse(auth_url)
    # google-auth-oauthlib stores verifier on the Flow instance; persist it across redirect.
    response.set_cookie(
        key=OAUTH_STATE_COOKIE,
        value=state,
        httponly=True,
        secure=_is_https(),
        samesite="lax",
        max_age=10 * 60,  # 10 minutes
    )
    response.set_cookie(
        key=OAUTH_CODE_VERIFIER_COOKIE,
        value=getattr(flow, "code_verifier", ""),
        httponly=True,
        secure=_is_https(),
        samesite="lax",
        max_age=10 * 60,  # 10 minutes
    )
    return response

@router.get("/callback")
async def drive_callback(
    code: str,
    state: str | None = None,
    google_oauth_state: str | None = Cookie(None, alias=OAUTH_STATE_COOKIE),
    google_oauth_code_verifier: str | None = Cookie(
        None, alias=OAUTH_CODE_VERIFIER_COOKIE
    ),
):
    """Handle OAuth callback — exchange code for token, store in DB, set session cookie"""
    try:
        if not state or not google_oauth_state or state != google_oauth_state:
            raise HTTPException(status_code=400, detail="OAuth state mismatch")

        flow = get_flow()
        flow.fetch_token(
            code=code,
            code_verifier=google_oauth_code_verifier,
        )
        credentials = flow.credentials

        # Generate a session ID — this is all the browser will ever see
        session_id = secrets.token_urlsafe(32)

        # Store token in Supabase keyed to session ID
        db = get_supabase()
        db.table("user_sessions").insert({
            "session_id": session_id,
            "google_access_token": credentials.token,
            "google_refresh_token": credentials.refresh_token,
            "token_expiry": credentials.expiry.isoformat() if credentials.expiry else None,
        }).execute()

        logger.info(f"OAuth complete — session created | session_id={session_id[:8]}...")

        # Set httpOnly cookie — browser can't read this with JavaScript
        frontend_url = os.getenv("FRONTEND_URL", "http://localhost:3000")
        response = RedirectResponse(url=f"{frontend_url}?drive_connected=true")
        response.set_cookie(
            key="session_id",
            value=session_id,
            httponly=True,   # JS cannot read this
            secure=_is_https(),     # HTTPS only in prod
            samesite="lax",
            max_age=3600 * 24,  # 24 hours
        )
        # Clear one-time OAuth cookies
        response.delete_cookie(key=OAUTH_STATE_COOKIE)
        response.delete_cookie(key=OAUTH_CODE_VERIFIER_COOKIE)
        return response

    except Exception as e:
        logger.error(f"OAuth callback failed | error={e}")
        raise HTTPException(status_code=400, detail="OAuth failed")

@router.get("/files")
async def list_drive_files(session_id: str = Cookie(None)):
    if not session_id:
        raise HTTPException(status_code=401, detail="Not authenticated")

    service = _drive_service_for_session(session_id)
    files = _list_drive_files(service)
    logger.info(f"Listed {len(files)} Drive files | session={session_id[:8]}...")
    return {"files": files}

@router.get("/file/{file_id}")
async def read_drive_file(file_id: str, session_id: str = Cookie(None)):
    """Read content of a specific Drive file"""
    if not session_id:
        raise HTTPException(status_code=401, detail="Not authenticated")

    service = _drive_service_for_session(session_id)

    # Export Google Docs as plain text
    try:
        content = service.files().export(
            fileId=file_id,
            mimeType="text/plain"
        ).execute()
        text = content.decode("utf-8") if isinstance(content, bytes) else content
        logger.info(f"Read Drive file | file_id={file_id} | chars={len(text)}")
        return {"file_id": file_id, "content": text[:5000]}  # cap at 5000 chars
    except Exception as e:
        logger.error(f"Failed to read Drive file | file_id={file_id} | error={e}")
        raise HTTPException(status_code=400, detail="Could not read file")

@router.get("/status")
async def drive_status(session_id: str = Cookie(None)):
    """Check if user has a valid Drive session"""
    if not session_id:
        return {"connected": False}
    try:
        _get_token_for_session(session_id)
        return {"connected": True}
    except:
        return {"connected": False}

def _get_token_for_session(session_id: str) -> dict:
    db = get_supabase()
    result = db.table("user_sessions").select("*").eq("session_id", session_id).execute()
    if not result.data:
        raise HTTPException(status_code=401, detail="Session not found")
    return result.data[0]


class ChatRequest(BaseModel):
    message: str

@router.post("/chat")
async def drive_chat(request: ChatRequest, session_id: str = Cookie(None)):
    if not session_id:
        raise HTTPException(status_code=401, detail="Not authenticated")

    service = _drive_service_for_session(session_id)
    files = _list_drive_files(service)

    # Build file context
    file_context = f"The user has {len(files)} files in Google Drive:\n"
    file_context += "\n".join([f"- {f['name']} (id: {f['id']})" for f in files])

    # Find relevant files based on message keywords
    message_lower = request.message.lower()
    content_context = ""

    keywords = message_lower.split()
    relevant_files = [
        f for f in files
        if any(kw in f["name"].lower() for kw in keywords if len(kw) > 3)
    ][:3]  # cap at 3 files to avoid token limits

    # Fall back to most recent files if no keyword match but content is requested
    if not relevant_files and any(word in message_lower for word in [
        "summarize", "content", "read", "what does", "format", "wording", "style"
    ]):
        relevant_files = files[:2]

    for f in relevant_files:
        try:
            content = service.files().export(
                fileId=f["id"],
                mimeType="text/plain"
            ).execute()
            text = content.decode("utf-8") if isinstance(content, bytes) else content
            content_context += f"\n\nContent of '{f['name']}':\n{text[:2000]}"
            logger.info(f"Loaded file content | file={f['name']} | chars={len(text)}")
        except Exception as e:
            logger.warning(f"Could not read file | file={f['name']} | error={e}")

    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        raise HTTPException(status_code=500, detail="ANTHROPIC_API_KEY not configured")
    try:
        import anthropic  # type: ignore
    except ModuleNotFoundError:
        raise HTTPException(
            status_code=500,
            detail="anthropic package not installed on backend",
        )
    client = anthropic.Anthropic(api_key=api_key)

    response = client.messages.create(
        model="claude-sonnet-4-5",
        max_tokens=1500,
        system=(
            "You are a helpful assistant that answers questions about a user's Google Drive files.\n\n"
            f"{file_context}{content_context}\n\n"
            "Answer the user's question based on this context. Be concise and helpful. "
            "If you have file content available, use it directly in your response."
        ),
        messages=[{"role": "user", "content": request.message}],
    )

    answer = response.content[0].text
    logger.info(f"Drive chat response | session={session_id[:8]}... | chars={len(answer)}")
    return {"response": answer}