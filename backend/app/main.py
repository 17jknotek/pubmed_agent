from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from loguru import logger
import sentry_sdk
from dotenv import load_dotenv
import os

from app.routers import pubmed, evaluate

load_dotenv()

sentry_sdk.init(
    dsn=os.getenv("SENTRY_DSN"),
    traces_sample_rate=1.0,
)

app = FastAPI(title="Beakr Portfolio API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[os.getenv("FRONTEND_URL", "http://localhost:3000")],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(pubmed.router, prefix="/api/pubmed", tags=["pubmed"])
app.include_router(evaluate.router, prefix="/api/evaluate", tags=["evaluate"])

@app.get("/health")
async def health():
    logger.info("Health check hit")
    return {"status": "ok"}