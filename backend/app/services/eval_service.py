from loguru import logger
from app.models.schemas import Article

async def score_with_llm_judge(query_id: str, query: str, articles: list[Article]) -> None:
    # Stub — no-op for now
    logger.info(f"score_with_llm_judge called | query_id={query_id}")