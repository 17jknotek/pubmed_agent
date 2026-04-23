from pydantic import BaseModel
from typing import Optional

class PubMedQueryRequest(BaseModel):
    query: str
    max_results: int = 5

class Article(BaseModel):
    pmid: str
    title: str
    abstract: str
    authors: list[str]
    journal: str
    pub_date: str
    url: str

class PubMedQueryResponse(BaseModel):
    query_id: str
    query: str
    articles: list[Article]
    ai_summary: str
    relevance_scores: list[dict]

class FeedbackRequest(BaseModel):
    query_id: str
    pmid: str
    rating: int  # 1-5
    comment: Optional[str] = None

class EvalResult(BaseModel):
    query_id: str
    llm_judge_score: float
    recall_at_5: Optional[float] = None