from fastapi import APIRouter, HTTPException
from loguru import logger
from app.models.schemas import PubMedQueryRequest, PubMedQueryResponse
from app.services.pubmed_service import fetch_pubmed_articles
from app.services.claude_service import summarize_and_rank
from app.services.eval_service import score_with_llm_judge
from app.services.supabase_service import log_query
import uuid

router = APIRouter()

@router.post("/search", response_model=PubMedQueryResponse)
async def search_pubmed(request: PubMedQueryRequest):
    query_id = str(uuid.uuid4())
    logger.info(f"PubMed search | query_id={query_id} | query={request.query}")

    try:
        articles = await fetch_pubmed_articles(request.query, request.max_results)
        logger.info(f"Fetched {len(articles)} articles | query_id={query_id}")
    except Exception as e:
        logger.error(f"PubMed fetch failed | query_id={query_id} | error={e}")
        raise HTTPException(status_code=502, detail="PubMed fetch failed")

    try:
        summary, scores = await summarize_and_rank(request.query, articles)
        logger.info(f"Claude ranking complete | query_id={query_id}")
    except Exception as e:
        logger.error(f"Claude call failed | query_id={query_id} | error={e}")
        raise HTTPException(status_code=502, detail="AI ranking failed")

    # Persist query to Supabase — don't block response if it fails
    try:
        await log_query(
            query_id=query_id,
            query=request.query,
            ai_summary=summary,
            pmids=[a.pmid for a in articles],
        )
    except Exception as e:
        logger.warning(f"Supabase logging failed silently | query_id={query_id} | error={e}")

    # Background eval scoring
    try:
        await score_with_llm_judge(query_id, request.query, articles)
    except Exception as e:
        logger.warning(f"LLM judge scoring failed silently | query_id={query_id} | error={e}")

    return PubMedQueryResponse(
        query=request.query,
        articles=articles,
        ai_summary=summary,
        relevance_scores=scores,
    )