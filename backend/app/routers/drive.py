from fastapi import APIRouter, HTTPException, Cookie, Response
from fastapi.responses import RedirectResponse
from loguru import logger
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build
from google.oauth2.credentials import Credentials
import os
import secrets
from app.services.supabase_service import get_supabase

router = APIRouter()

SCOPES = ["https://www.googleapis.com/auth/drive.readonly"]

def _is_https() -> bool:
    """
    Cookies must be Secure on HTTPS, but localhost dev is often plain HTTP.
    """
    frontend_url = os.getenv("FRONTEND_URL", "http://localhost:3000")
    redirect_uri = os.getenv("GOOGLE_REDIRECT_URI", "")
    return frontend_url.startswith("https://") and redirect_uri.startswith("https://")

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
        key="google_oauth_state",
        value=state,
        httponly=True,
        secure=_is_https(),
        samesite="lax",
        max_age=10 * 60,  # 10 minutes
    )
    response.set_cookie(
        key="google_oauth_code_verifier",
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
    response: Response,
    state: str | None = None,
    google_oauth_state: str | None = Cookie(None),
    google_oauth_code_verifier: str | None = Cookie(None),
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
        response.delete_cookie(key="google_oauth_state")
        response.delete_cookie(key="google_oauth_code_verifier")
        return response

    except Exception as e:
        logger.error(f"OAuth callback failed | error={e}")
        raise HTTPException(status_code=400, detail="OAuth failed")

@router.get("/files")
async def list_drive_files(session_id: str = Cookie(None)):
    """List user's Drive files using their stored token"""
    if not session_id:
        raise HTTPException(status_code=401, detail="Not authenticated")

    token = _get_token_for_session(session_id)
    credentials = Credentials(token=token["google_access_token"])

    service = build("drive", "v3", credentials=credentials)
    results = service.files().list(
        pageSize=20,
        fields="files(id, name, mimeType)",
        q="mimeType='application/vnd.google-apps.document' or mimeType='text/plain'"
    ).execute()

    files = results.get("files", [])
    logger.info(f"Listed {len(files)} Drive files | session={session_id[:8]}...")
    return {"files": files}

@router.get("/file/{file_id}")
async def read_drive_file(file_id: str, session_id: str = Cookie(None)):
    """Read content of a specific Drive file"""
    if not session_id:
        raise HTTPException(status_code=401, detail="Not authenticated")

    token = _get_token_for_session(session_id)
    credentials = Credentials(token=token["google_access_token"])

    service = build("drive", "v3", credentials=credentials)

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