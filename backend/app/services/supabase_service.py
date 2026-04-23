import os
from supabase import create_client, Client
from loguru import logger

def get_supabase() -> Client:
    url = os.getenv("SUPABASE_URL")
    key = os.getenv("SUPABASE_SERVICE_KEY")  # service role for backend
    if not url or not key:
        raise ValueError("SUPABASE_URL and SUPABASE_SERVICE_KEY must be set")
    return create_client(url, key)

async def log_query(query_id: str, query: str, ai_summary: str, pmids: list[str]) -> None:
    try:
        db = get_supabase()
        db.table("queries").insert({
            "id": query_id,
            "query": query,
            "ai_summary": ai_summary,
            "result_pmids": pmids,
        }).execute()
        logger.info(f"Query logged to Supabase | query_id={query_id}")
    except Exception as e:
        logger.error(f"Failed to log query | query_id={query_id} | error={e}")

async def log_feedback(query_id: str, pmid: str, rating: int, comment: str | None) -> None:
    try:
        db = get_supabase()
        db.table("feedback").insert({
            "query_id": query_id,
            "pmid": pmid,
            "rating": rating,
            "comment": comment,
        }).execute()
        logger.info(f"Feedback logged | query_id={query_id} | pmid={pmid} | rating={rating}")
    except Exception as e:
        logger.error(f"Failed to log feedback | query_id={query_id} | error={e}")

async def log_eval_score(query_id: str, pmid: str, score: int, reason: str) -> None:
    try:
        db = get_supabase()
        db.table("eval_scores").insert({
            "query_id": query_id,
            "pmid": pmid,
            "llm_score": score,
            "llm_reason": reason,
        }).execute()
        logger.info(f"Eval score logged | query_id={query_id} | pmid={pmid} | score={score}")
    except Exception as e:
        logger.error(f"Failed to log eval score | query_id={query_id} | error={e}")