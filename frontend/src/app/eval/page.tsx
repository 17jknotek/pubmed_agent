"use client";

import { useEffect, useState } from "react";
import { getEvalStats, EvalStats } from "@/lib/api";
import Link from "next/link";

export default function EvalDashboard() {
  const [stats, setStats] = useState<EvalStats | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    getEvalStats()
      .then(setStats)
      .catch(() => setError("Failed to load stats"))
      .finally(() => setLoading(false));
  }, []);

  function ScoreBar({ value, max = 5 }: { value: number; max?: number }) {
    const pct = (value / max) * 100;
    const color = value >= 4 ? "bg-green-500" : value >= 3 ? "bg-yellow-500" : "bg-red-500";
    return (
      <div className="w-full bg-gray-800 rounded-full h-2 mt-2">
        <div className={`${color} h-2 rounded-full transition-all`} style={{ width: `${pct}%` }} />
      </div>
    );
  }

  return (
    <main className="min-h-screen bg-gray-950 text-gray-100">
      <div className="max-w-4xl mx-auto px-4 py-16">

        <div className="flex items-center justify-between mb-12">
          <div>
            <h1 className="text-4xl font-bold text-white mb-2">Eval Dashboard</h1>
            <p className="text-gray-400">Agent quality metrics over time</p>
          </div>
          <Link
            href="/"
            className="text-blue-400 hover:text-blue-300 text-sm transition"
          >
            ← Back to search
          </Link>
        </div>

        {loading && (
          <div className="text-gray-400 text-center py-20">Loading stats...</div>
        )}

        {error && (
          <div className="bg-red-900/50 border border-red-700 text-red-300 px-4 py-3 rounded-lg">
            {error}
          </div>
        )}

        {stats && (
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-12">

            {/* Total queries */}
            <div className="bg-gray-900 border border-gray-800 rounded-lg p-6">
              <p className="text-gray-400 text-sm uppercase tracking-wider mb-1">Total Queries</p>
              <p className="text-5xl font-bold text-white">{stats.total_queries ?? 0}</p>
            </div>

            {/* LLM judge score */}
            <div className="bg-gray-900 border border-gray-800 rounded-lg p-6">
              <p className="text-gray-400 text-sm uppercase tracking-wider mb-1">Avg LLM Judge Score</p>
              {stats.avg_llm_judge_score !== null ? (
                <>
                  <p className="text-5xl font-bold text-white">
                    {stats.avg_llm_judge_score.toFixed(1)}
                    <span className="text-2xl text-gray-500">/5</span>
                  </p>
                  <ScoreBar value={stats.avg_llm_judge_score} />
                </>
              ) : (
                <p className="text-gray-500 mt-2">No data yet</p>
              )}
            </div>

            {/* User rating */}
            <div className="bg-gray-900 border border-gray-800 rounded-lg p-6">
              <p className="text-gray-400 text-sm uppercase tracking-wider mb-1">Avg User Rating</p>
              {stats.avg_user_rating !== null ? (
                <>
                  <p className="text-5xl font-bold text-white">
                    {stats.avg_user_rating.toFixed(1)}
                    <span className="text-2xl text-gray-500">/5</span>
                  </p>
                  <ScoreBar value={stats.avg_user_rating} />
                </>
              ) : (
                <p className="text-gray-500 mt-2">No ratings yet</p>
              )}
            </div>

          </div>
        )}

        {/* Eval methodology explanation */}
        {stats && (
          <div className="bg-gray-900 border border-gray-800 rounded-lg p-6">
            <h2 className="text-lg font-semibold text-white mb-4">How Agent Quality is Measured</h2>
            <div className="space-y-4 text-sm text-gray-400 leading-relaxed">
              <div>
                <p className="text-gray-200 font-medium mb-1">LLM-as-Judge</p>
                <p>Each returned article is independently scored 1–5 by Claude Haiku against the original query using a biomedical relevance rubric. This provides automated, scalable eval without requiring labeled ground truth data.</p>
              </div>
              <div>
                <p className="text-gray-200 font-medium mb-1">User Feedback</p>
                <p>Users can rate each article 1–5 directly in the search results. This captures implicit signal about whether the agent is actually useful in practice — the ground truth that LLM judges can miss.</p>
              </div>
              <div>
                <p className="text-gray-200 font-medium mb-1">Why Not Just Accuracy %?</p>
                <p>Unlike classification tasks, there is no single correct answer for open-ended research queries. A query for &quot;CRISPR off-target effects&quot; might have dozens of genuinely relevant articles. Eval here measures relevance quality and usefulness, not binary correctness.</p>
              </div>
            </div>
          </div>
        )}

      </div>
    </main>
  );
}