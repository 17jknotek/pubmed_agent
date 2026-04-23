import json
import os
import anthropic
from loguru import logger
from app.models.schemas import Article
from app.services.supabase_service import log_eval_score

def get_client():
    return anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

JUDGE_PROMPT = """You are an expert biomedical research librarian evaluating search results.

Given a research query and an article, score the article's relevance 1-5:
5 = Directly addresses the query, highly relevant
4 = Mostly relevant, addresses main topic
3 = Somewhat relevant, tangentially related
2 = Weakly relevant, shares some keywords but misses the point
1 = Not relevant

Return ONLY valid JSON:
{{"score": <1-5>, "reason": "<one sentence explanation>"}}"""

async def score_with_llm_judge(query_id: str, query: str, articles: list[Article]) -> None:
    client = get_client()

    for article in articles:
        try:
            response = client.messages.create(
                model="claude-haiku-4-5-20251001",  # haiku is faster and cheaper for eval
                max_tokens=200,
                system=JUDGE_PROMPT,
                messages=[{
                    "role": "user",
                    "content": f"Query: {query}\n\nArticle title: {article.title}\n\nAbstract: {article.abstract[:400]}"
                }],
            )

            raw = response.content[0].text.strip()
            if raw.startswith("```"):
                raw = raw.split("```")[1]
                if raw.startswith("json"):
                    raw = raw[4:]
                raw = raw.strip()

            parsed = json.loads(raw)
            score = parsed.get("score", 3)
            reason = parsed.get("reason", "")

            await log_eval_score(
                query_id=query_id,
                pmid=article.pmid,
                score=score,
                reason=reason,
            )

        except Exception as e:
            logger.error(f"LLM judge failed for pmid={article.pmid} | error={e}")