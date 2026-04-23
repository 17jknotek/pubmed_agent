const API_URL = process.env.NEXT_PUBLIC_API_URL;

export interface Article {
  pmid: string;
  title: string;
  abstract: string;
  authors: string[];
  journal: string;
  pub_date: string;
  url: string;
}

export interface RelevanceScore {
  pmid: string;
  score: number;
  reason: string;
}

export interface SearchResponse {
    query_id: string;
    query: string;
    articles: Article[];
    ai_summary: string;
    relevance_scores: RelevanceScore[];
  }

export interface EvalStats {
  total_queries: number;
  avg_user_rating: number | null;
  avg_llm_judge_score: number | null;
}

export async function searchPubMed(query: string, maxResults = 5): Promise<SearchResponse> {
  const res = await fetch(`${API_URL}/api/pubmed/search`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ query, max_results: maxResults }),
  });
  if (!res.ok) throw new Error("Search failed");
  return res.json();
}

export async function submitFeedback(
  queryId: string,
  pmid: string,
  rating: number
): Promise<void> {
  await fetch(`${API_URL}/api/evaluate/feedback`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ query_id: queryId, pmid, rating }),
  });
}

export async function getEvalStats(): Promise<EvalStats> {
  const res = await fetch(`${API_URL}/api/evaluate/stats`);
  if (!res.ok) throw new Error("Failed to fetch stats");
  return res.json();
}