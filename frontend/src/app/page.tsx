"use client";

import { useState } from "react";
import { searchPubMed, submitFeedback, SearchResponse, Article, RelevanceScore } from "@/lib/api";
import Link from "next/link";

export default function Home() {
  const [query, setQuery] = useState("");
  const [loading, setLoading] = useState(false);
  const [results, setResults] = useState<SearchResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [feedback, setFeedback] = useState<Record<string, number>>({});
  const [queryId, setQueryId] = useState<string | null>(null);

  async function handleSearch() {
    if (!query.trim()) return;
    setLoading(true);
    setError(null);
    setResults(null);
    setFeedback({});

    try {
      const data = await searchPubMed(query);
      setResults(data);
      setQueryId(crypto.randomUUID());
    } catch (e) {
      setError("Search failed. Please try again.");
    } finally {
      setLoading(false);
    }
  }

  async function handleFeedback(pmid: string, rating: number) {
    if (!queryId) return;
    setFeedback(prev => ({ ...prev, [pmid]: rating }));
    await submitFeedback(queryId, pmid, rating);
  }

  function getScoreForArticle(pmid: string): RelevanceScore | undefined {
    return results?.relevance_scores.find(s => s.pmid === pmid);
  }

  function getScoreBadgeClass(score: number): string {
    if (score >= 4) return "bg-green-900 text-green-300";
    if (score === 3) return "bg-yellow-900 text-yellow-300";
    return "bg-red-900 text-red-300";
  }

  return (
    <main className="min-h-screen bg-gray-950 text-gray-100">
      <div className="max-w-4xl mx-auto px-4 py-16">

        {/* Header */}
        <div className="mb-12 text-center">
          <h1 className="text-4xl font-bold text-white mb-3">PubMed Research Agent</h1>
          <p className="text-gray-400 text-lg">
            Search biomedical literature with AI-powered relevance ranking
          </p>
        </div>
        
        {/* Eval dashboard link */}
        <div className="text-center mb-8">
          <Link href="/eval" className="text-gray-500 hover:text-gray-300 text-sm transition">
            View eval dashboard →
          </Link>
        </div>

        {/* Search bar */}
        <div className="flex gap-3 mb-8">
          <input
            type="text"
            value={query}
            onChange={e => setQuery(e.target.value)}
            onKeyDown={e => e.key === "Enter" && handleSearch()}
            placeholder="e.g. CRISPR off-target effects in cancer therapy"
            className="flex-1 bg-gray-800 border border-gray-700 rounded-lg px-4 py-3 text-white placeholder-gray-500 focus:outline-none focus:border-blue-500 transition"
          />
          <button
            onClick={handleSearch}
            disabled={loading}
            className="bg-blue-600 hover:bg-blue-500 disabled:bg-blue-900 text-white px-6 py-3 rounded-lg font-medium transition"
          >
            {loading ? "Searching..." : "Search"}
          </button>
        </div>

        {/* Error */}
        {error && (
          <div className="bg-red-900/50 border border-red-700 text-red-300 px-4 py-3 rounded-lg mb-6">
            {error}
          </div>
        )}

        {/* AI Summary */}
        {results && (
          <div className="bg-blue-950/50 border border-blue-800 rounded-lg px-5 py-4 mb-8">
            <p className="text-xs font-semibold text-blue-400 uppercase tracking-wider mb-2">AI Summary</p>
            <p className="text-gray-200 leading-relaxed">{results.ai_summary}</p>
          </div>
        )}

        {/* Results */}
        {results?.articles.map((article: Article) => {
          const score = getScoreForArticle(article.pmid);
          const userRating = feedback[article.pmid];

          return (
            <div key={article.pmid} className="bg-gray-900 border border-gray-800 rounded-lg p-5 mb-4">

              {/* Title + score badge */}
              <div className="flex items-start justify-between gap-4 mb-2">
                <a
                  href={article.url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="text-blue-400 hover:text-blue-300 font-medium leading-snug transition"
                >
                  {article.title}
                </a>
                {score && (
                  <span className={`shrink-0 text-sm font-bold px-2 py-1 rounded ${getScoreBadgeClass(score.score)}`}>
                    {score.score}/5
                  </span>
                )}
              </div>

              {/* Meta */}
              <p className="text-gray-500 text-sm mb-3">
                {article.journal} · {article.pub_date} · {article.authors.slice(0, 3).join(", ")}
                {article.authors.length > 3 && " et al."}
              </p>

              {/* AI relevance reason */}
              {score && (
                <p className="text-gray-400 text-sm italic mb-3">&quot;{score.reason}&quot;</p>
              )}

              {/* Abstract */}
              <p className="text-gray-300 text-sm leading-relaxed line-clamp-3 mb-4">
                {article.abstract}
              </p>

              {/* Feedback */}
              <div className="flex items-center gap-2">
                <span className="text-gray-500 text-xs">Helpful?</span>
                {[1, 2, 3, 4, 5].map(rating => (
                  <button
                    key={rating}
                    onClick={() => handleFeedback(article.pmid, rating)}
                    className={`w-7 h-7 rounded text-xs font-bold transition ${
                      userRating === rating
                        ? "bg-blue-600 text-white"
                        : "bg-gray-800 text-gray-400 hover:bg-gray-700"
                    }`}
                  >
                    {rating}
                  </button>
                ))}
                {userRating && <span className="text-green-400 text-xs ml-1">Thanks!</span>}
              </div>

            </div>
          );
        })}

      </div>
    </main>
  );
}