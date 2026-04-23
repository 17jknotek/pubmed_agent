from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from loguru import logger
import sentry_sdk
from dotenv import load_dotenv
import os

from app.routers import pubmed, evaluate

load_dotenv()

sentry_dsn = os.getenv("SENTRY_DSN")
if sentry_dsn:
    sentry_sdk.init(
        dsn=sentry_dsn,
        traces_sample_rate=1.0,
    )
else:
    logger.warning("SENTRY_DSN not set — Sentry disabled")

app = FastAPI(title="PubMed Search API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        os.getenv("FRONTEND_URL", "http://localhost:3000"),
        "https://pubmed-agent-nine.vercel.app",
    ],
    allow_origin_regex=r"https://pubmed-agent-.*\.vercel\.app",
    allow_credentials=True,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)

app.include_router(pubmed.router, prefix="/api/pubmed", tags=["pubmed"])
app.include_router(evaluate.router, prefix="/api/evaluate", tags=["evaluate"])

@app.get("/health")
async def health():
    logger.info("Health check hit")
    return {"status": "ok"}