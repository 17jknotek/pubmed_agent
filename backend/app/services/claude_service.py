import anthropic
import os
import json
from loguru import logger
from app.models.schemas import Article

def get_client():
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        raise ValueError("ANTHROPIC_API_KEY is not set in environment")
    return anthropic.Anthropic(api_key=api_key)

RANKING_PROMPT = """You are a biomedical research assistant helping evaluate PubMed search results.

Given a user's research query and a list of articles, you will:
1. Write a 2-3 sentence summary of what the search found overall
2. Score each article 1-5 for relevance to the query (5 = highly relevant)
3. Write one sentence explaining each score

Return ONLY valid JSON in this exact format:
{{
  "summary": "Overall summary here",
  "scores": [
    {{"pmid": "12345678", "score": 5, "reason": "Directly addresses the query by..."}}
  ]
}}"""

async def summarize_and_rank(query: str, articles: list[Article]) -> tuple[str, list[dict]]:
    if not articles:
        return "No articles found for this query.", []

    articles_text = "\n\n".join([
        f"PMID: {a.pmid}\nTitle: {a.title}\nJournal: {a.journal} ({a.pub_date})\nAbstract: {a.abstract[:500]}..."
        for a in articles
    ])

    user_message = f"Research query: {query}\n\nArticles:\n{articles_text}"

    logger.info(f"Calling Claude for ranking | query={query} | articles={len(articles)}")

    response = get_client().messages.create(
        model="claude-sonnet-4-5",
        max_tokens=1000,
        system=RANKING_PROMPT,
        messages=[{"role": "user", "content": user_message}],
    )

    raw = response.content[0].text
    logger.info(f"Claude raw response | preview={raw[:300]}")

    # Strip markdown code fences if Claude wrapped the JSON in them
    cleaned = raw.strip()
    if cleaned.startswith("```"):
        cleaned = cleaned.split("```")[1]
        if cleaned.startswith("json"):
            cleaned = cleaned[4:]
        cleaned = cleaned.strip()

    try:
        parsed = json.loads(cleaned)
        summary = parsed.get("summary", "")
        scores = parsed.get("scores", [])
        logger.info(f"Parsed successfully | summary_len={len(summary)} | scores={len(scores)}")
        return summary, scores
    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse Claude JSON | error={e} | raw={raw[:300]}")
        return "Summary unavailable.", []