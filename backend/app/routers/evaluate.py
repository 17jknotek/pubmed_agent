from fastapi import APIRouter
from loguru import logger
from app.models.schemas import FeedbackRequest
from app.services.supabase_service import log_feedback

router = APIRouter()

@router.post("/feedback")
async def submit_feedback(request: FeedbackRequest):
    logger.info(f"Feedback received | query_id={request.query_id} | pmid={request.pmid} | rating={request.rating}")
    await log_feedback(
        query_id=request.query_id,
        pmid=request.pmid,
        rating=request.rating,
        comment=request.comment,
    )
    return {"status": "received"}

@router.get("/stats")
async def get_stats():
    from app.services.supabase_service import get_supabase
    db = get_supabase()

    queries = db.table("queries").select("id", count="exact").execute()
    feedback = db.table("feedback").select("rating").execute()
    eval_scores = db.table("eval_scores").select("llm_score").execute()

    avg_feedback = None
    if feedback.data:
        avg_feedback = round(sum(r["rating"] for r in feedback.data) / len(feedback.data), 2)

    avg_eval = None
    if eval_scores.data:
        avg_eval = round(sum(r["llm_score"] for r in eval_scores.data) / len(eval_scores.data), 2)

    return {
        "total_queries": queries.count,
        "avg_user_rating": avg_feedback,
        "avg_llm_judge_score": avg_eval,
    }