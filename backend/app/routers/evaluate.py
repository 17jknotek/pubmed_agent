from fastapi import APIRouter
from loguru import logger
from app.models.schemas import FeedbackRequest

router = APIRouter()

@router.post("/feedback")
async def submit_feedback(request: FeedbackRequest):
    logger.info(f"Feedback received | query_id={request.query_id} | pmid={request.pmid} | rating={request.rating}")
    return {"status": "received"}