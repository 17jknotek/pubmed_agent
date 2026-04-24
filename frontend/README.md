# PubMed Research Agent

An AI-powered biomedical literature search tool with agent evaluation infrastructure and Google Drive integration. Built as a portfolio project demonstrating full-stack AI application development, agentic system design, and production deployment.

**Live demo:** [pubmed-agent-nine.vercel.app](https://pubmed-agent-nine.vercel.app)

---

## What it does

**PubMed Search** — Enter a natural language research query and get back the top 5 relevant PubMed articles, ranked and summarized by Claude. Each result includes an AI-generated relevance score (1–5) with a one-sentence explanation of why it matches your query.

**Agent Evaluation Dashboard** — Every search is automatically evaluated using two complementary methods: an LLM-as-judge that scores each article independently, and user feedback ratings collected directly in the UI. Aggregate metrics are surfaced in a live eval dashboard.

**Google Drive Agent** — Connect your Google Drive via OAuth and ask natural language questions about your files. The agent reads relevant documents and uses them as context for Claude responses.

---

## Why I built it this way

### The agent evaluation problem

A common interview question for AI roles is: *how do you measure the accuracy of an agent?* Unlike classification tasks, there is no single correct answer for open-ended research queries — a search for "CRISPR off-target effects" might have dozens of genuinely relevant articles. Binary accuracy metrics don't apply.

This project implements three complementary evaluation strategies:

**1. LLM-as-Judge (automated, scalable)**
After every search, Claude Haiku independently scores each returned article 1–5 against the original query using a biomedical relevance rubric. This provides automated eval signal without requiring labeled ground truth data. Haiku is used instead of Sonnet for cost and latency reasons — for a simple scoring task, the cheaper model is sufficient.

**2. User Feedback (real-world signal)**
Users can rate each article 1–5 directly in the search results. This captures whether the agent is actually useful in practice — the ground truth that automated judges can miss. Feedback is persisted to Supabase and factored into the eval dashboard.

**3. Golden Dataset (reference-based, offline)**
For rigorous offline evaluation, a small curated set of query/article pairs from domain experts can be used to compute Recall@5 — measuring how many of the "correct" articles appear in the top 5 results. This is the closest analog to labeled accuracy for retrieval tasks.

### Architecture decisions

**Separate Python backend for AI logic.** The frontend is Next.js (TypeScript) deployed on Vercel. The AI service is FastAPI (Python) deployed on Railway. This mirrors real production architecture at AI startups — a Node/Next frontend, a Python AI service behind it. It also means the backend can eventually call model inference directly without fighting JavaScript.

**Claude Sonnet for ranking, Claude Haiku for evaluation.** Using the right model for the right job is a real cost-optimization pattern. Ranking and summarization require nuanced reasoning — Sonnet. Scoring a single article on a simple rubric — Haiku. At scale this matters significantly.

**Structured logging over console logs.** Every request is logged with consistent fields (timestamp, level, query ID, latency). This means you can filter by level, search by field, and trace the full lifecycle of a request across the pipeline — something ad-hoc console logs can't provide.

**Server-side token storage for OAuth.** Google Drive tokens are stored in Supabase keyed to a server-generated session ID. The browser only ever sees the session ID via an httpOnly cookie — never the token itself. This means a compromised frontend cannot exfiltrate Drive access.

---

## System architecture

```
┌─────────────────────────────────────────────────────────┐
│                    User's Browser                        │
│                                                          │
│   Next.js Frontend (Vercel)                             │
│   ├── / (PubMed search + feedback)                      │
│   ├── /eval (evaluation dashboard)                      │
│   └── /drive (Google Drive agent)                       │
└──────────────────┬──────────────────────────────────────┘
                   │ HTTP + credentials: include
                   ▼
┌─────────────────────────────────────────────────────────┐
│              FastAPI Backend (Railway)                   │
│                                                          │
│   /api/pubmed/search                                    │
│   ├── NCBI E-utilities API (PubMed fetch)               │
│   ├── Claude Sonnet (ranking + summary)                 │
│   ├── Claude Haiku (LLM judge scoring)                  │
│   └── Supabase (persist query + scores)                 │
│                                                          │
│   /api/evaluate/feedback                                │
│   └── Supabase (persist user ratings)                   │
│                                                          │
│   /api/evaluate/stats                                   │
│   └── Supabase (aggregate metrics)                      │
│                                                          │
│   /api/drive/*                                          │
│   ├── Google OAuth 2.0 (token exchange)                 │
│   ├── Google Drive API v3 (file access)                 │
│   ├── Claude Sonnet (Drive chat)                        │
│   └── Supabase (session + token storage)                │
└──────────────────┬──────────────────────────────────────┘
                   │
                   ▼
┌─────────────────────────────────────────────────────────┐
│                   Supabase (Postgres)                    │
│   ├── queries (search history + AI summaries)           │
│   ├── eval_scores (LLM judge scores per article)        │
│   ├── feedback (user ratings per article)               │
│   └── user_sessions (OAuth tokens, server-side only)    │
└─────────────────────────────────────────────────────────┘
```

---

## PubMed search pipeline

Each search executes a three-step pipeline against NCBI's E-utilities API:

1. **esearch** — Takes the natural language query, returns a ranked list of PMIDs
2. **esummary** — Fetches metadata (title, authors, journal, date) for those PMIDs
3. **efetch** — Fetches full abstracts for context

Claude then receives all five abstracts and returns a structured JSON response with a summary and per-article relevance scores. The response is parsed and stored in Supabase before being returned to the frontend.

---

## Security considerations

**Google Drive OAuth**
- Scope is `drive.readonly` — the minimum necessary. Write access is never requested.
- Access tokens are stored server-side in Supabase, encrypted at rest. The browser receives only a session ID via an httpOnly cookie, which JavaScript cannot read.
- Tokens are never logged.

**API security**
- CORS is locked to specific Vercel domains — not open to all origins
- Only GET and POST methods are allowed
- All secrets are environment variables, never committed to version control
- The Supabase service role key (which bypasses RLS) is backend-only — the frontend uses the anon key

**File upload / content handling**
- Drive file content is capped at 5,000 characters per file before being passed to Claude, preventing prompt injection via oversized documents
- File exports are text-only — no binary execution

---

## Tech stack

| Layer | Technology |
|-------|-----------|
| Frontend | Next.js 15, TypeScript, Tailwind CSS |
| Backend | FastAPI, Python 3.13, Pydantic |
| AI | Anthropic Claude (Sonnet + Haiku) |
| Database | Supabase (Postgres) |
| Auth | Google OAuth 2.0 |
| Logging | Loguru (structured), Sentry (error tracking) |
| Deployment | Vercel (frontend), Railway (backend) |
| Package management | uv (Python), npm (Node) |

---

## Local development

### Prerequisites
- Python 3.11+
- Node.js 18+
- uv (`curl -LsSf https://astral.sh/uv/install.sh | sh`)

### Backend

```bash
cd backend
uv run uvicorn app.main:app --reload --port 8000
```

Create `backend/.env`:
```
ANTHROPIC_API_KEY=
SUPABASE_URL=
SUPABASE_SERVICE_KEY=
SENTRY_DSN=
GOOGLE_CLIENT_ID=
GOOGLE_CLIENT_SECRET=
GOOGLE_REDIRECT_URI=http://localhost:8000/api/drive/callback
FRONTEND_URL=http://localhost:3000
```

### Frontend

```bash
cd frontend
npm install
npm run dev
```

Create `frontend/.env.local`:
```
NEXT_PUBLIC_API_URL=http://localhost:8000
```

API docs available at `http://localhost:8000/docs` when backend is running.

---

## Project structure

```
pubmed_agent/
├── backend/
│   ├── app/
│   │   ├── main.py              # FastAPI app, middleware, router registration
│   │   ├── routers/
│   │   │   ├── pubmed.py        # Search endpoint
│   │   │   ├── evaluate.py      # Feedback + stats endpoints
│   │   │   └── drive.py         # OAuth + Drive endpoints
│   │   ├── services/
│   │   │   ├── pubmed_service.py   # NCBI API integration
│   │   │   ├── claude_service.py   # Ranking + summarization
│   │   │   ├── eval_service.py     # LLM judge scoring
│   │   │   └── supabase_service.py # Database persistence
│   │   └── models/
│   │       └── schemas.py       # Pydantic request/response models
│   └── railway.toml             # Railway deployment config
└── frontend/
    └── src/
        └── app/
            ├── page.tsx         # PubMed search UI
            ├── eval/page.tsx    # Eval dashboard
            ├── drive/page.tsx   # Drive agent UI
            └── lib/
                └── api.ts       # Typed API client
```

---

## What I'd add with more time

- **Streaming responses** — Claude's API supports streaming; sending tokens to the frontend as they arrive would eliminate the ~9 second wait for ranking results
- **Recall@5 with golden dataset** — curate 20–30 expert-labeled query/article pairs for reference-based offline eval
- **Token refresh** — Google access tokens expire after 1 hour; implementing refresh token rotation would make Drive sessions persistent
- **Rate limiting** — per-IP rate limiting on the search endpoint to prevent abuse
- **Pagination** — the Drive file list is capped at 50; implementing cursor-based pagination would expose the full Drive
- **Async eval scoring** — the LLM judge currently runs synchronously after the search; moving it to a background task queue (Celery, Railway cron) would reduce response latency