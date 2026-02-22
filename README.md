# Connective

Discover work overlap across your tools. Connective connects to Slack, GitHub, and Google Drive, indexes team activity, and surfaces relevant prior work through a chat interface with cited answers.

Ask "Has someone worked on X?" and get sourced responses. Run "Scan my current work" to find overlaps and draft a check-in message. Get notified when new work overlaps with yours.

## Architecture

```
┌─────────────┐     ┌──────────────┐     ┌──────────────────────┐
│   Next.js   │────▶│   FastAPI    │────▶│  PostgreSQL 17       │
│   Frontend  │ JWT │   Backend    │     │  + pgvector (HNSW)   │
│   (React)   │◀────│   (Python)   │◀────│  + tsvector (GIN)    │
└─────────────┘ SSE └──────┬───────┘     └──────────────────────┘
                           │
                    ┌──────┴───────┐
                    │   OpenAI     │
                    │  Embeddings  │
                    │  + GPT-4o    │
                    └──────────────┘
```

- **Frontend**: Next.js 15, React 19, TypeScript, Tailwind CSS, NextAuth (Google OAuth)
- **Backend**: Python 3.13+, FastAPI, SQLModel, asyncpg, Alembic
- **Database**: PostgreSQL 17 with pgvector for vector search
- **LLM**: OpenAI `text-embedding-3-small` (1536d) + `gpt-4o` for RAG
- **Infra**: Docker Compose (Postgres), mkcert for local HTTPS

## Features

- **Connectors** — OAuth integration with Slack, GitHub, and Google Drive. Selective sync (pick repos/folders). Auto-sync every minute.
- **Hybrid search** — Vector similarity (pgvector HNSW with halfvec cosine ops) + full-text search (tsvector/GIN) merged via Reciprocal Rank Fusion, then LLM-reranked.
- **RAG chat** — SSE-streamed answers with inline citations, confidence indicators, and persistent chat history.
- **Overlap detection** — Cross-user similarity search on new documents. Alerts when someone else is working on similar things.
- **Deduplication** — Documents are globally unique by `(provider, external_id)`. Multiple users share embeddings via `document_access` table.
- **Scan** — Paste text or a URL, get overlapping work, relevant people, and a draft check-in message.

## Getting started

### Prerequisites

- Python 3.13+
- Node.js 18+ (22 recommended)
- Docker & Docker Compose
- An OpenAI API key
- OAuth credentials for the connectors you want (Google required for sign-in)

### 1. Clone and configure

```bash
git clone <repo-url> && cd connective
cp .env.example .env
```

Edit `.env` and fill in your keys:

| Variable | Required | Notes |
|----------|----------|-------|
| `CONNECTIVE_OPENAI_API_KEY` | Yes | OpenAI API key |
| `CONNECTIVE_JWT_SECRET` | Yes | Random string, pin it so restarts don't invalidate sessions |
| `CONNECTIVE_FERNET_KEY` | Yes | Generate with `python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"` |
| `CONNECTIVE_GOOGLE_CLIENT_ID` | Yes | Google OAuth (used for sign-in + Drive connector) |
| `CONNECTIVE_GOOGLE_CLIENT_SECRET` | Yes | |
| `GOOGLE_CLIENT_ID` | Yes | Same value, used by NextAuth |
| `GOOGLE_CLIENT_SECRET` | Yes | Same value, used by NextAuth |
| `NEXTAUTH_SECRET` | Yes | Random string for session encryption |
| `CONNECTIVE_SLACK_CLIENT_ID` | Optional | Slack OAuth app |
| `CONNECTIVE_SLACK_CLIENT_SECRET` | Optional | |
| `CONNECTIVE_GITHUB_CLIENT_ID` | Optional | GitHub OAuth app |
| `CONNECTIVE_GITHUB_CLIENT_SECRET` | Optional | |

### 2. Start the database

```bash
docker compose up -d
```

### 3. Set up the backend

```bash
cd backend
uv venv --python 3.13
source .venv/bin/activate
uv pip install -e .
alembic upgrade head
```

#### HTTPS (required for Slack OAuth)

Slack requires HTTPS redirect URLs. Generate self-signed certs with [mkcert](https://github.com/FiloSottile/mkcert):

```bash
mkcert localhost 127.0.0.1
# produces localhost.pem and localhost-key.pem in the current directory
```

#### Run the backend

```bash
# With HTTPS (needed for Slack):
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload \
  --ssl-keyfile localhost-key.pem --ssl-certfile localhost.pem

# Without HTTPS (GitHub/Google Drive only):
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

If using HTTPS, update `.env`:
```
CONNECTIVE_BACKEND_URL=https://localhost:8000
NEXT_PUBLIC_API_URL=https://localhost:8000
```

### 4. Set up the frontend

```bash
cd frontend
npm install
```

Create `frontend/.env.local`:
```
NEXTAUTH_SECRET=<same as .env>
NEXTAUTH_URL=http://localhost:3000
GOOGLE_CLIENT_ID=<your google client id>
GOOGLE_CLIENT_SECRET=<your google client secret>
NEXT_PUBLIC_API_URL=https://localhost:8000
NODE_TLS_REJECT_UNAUTHORIZED=0
```

```bash
npm run dev
```

Open [http://localhost:3000](http://localhost:3000).

## OAuth setup

### Google (required)

1. Go to [Google Cloud Console](https://console.cloud.google.com/apis/credentials)
2. Create an OAuth 2.0 Client ID (Web application)
3. Add authorized redirect URIs:
   - `http://localhost:3000/api/auth/callback/google` (NextAuth)
   - `https://localhost:8000/api/connectors/google_drive/callback` (Drive connector)
4. Copy Client ID and Secret to `.env`

### GitHub

1. Go to [GitHub Developer Settings](https://github.com/settings/developers)
2. Create a new OAuth App
3. Set callback URL to `https://localhost:8000/api/connectors/github/callback`
4. Copy Client ID and Secret to `.env`

After connecting, you'll be prompted to select which repos to sync.

### Slack

1. Go to [Slack API Apps](https://api.slack.com/apps)
2. Create a new app, add OAuth redirect URL: `https://localhost:8000/api/connectors/slack/callback`
3. Add **User Token Scopes**: `channels:history`, `channels:read`, `groups:history`, `groups:read`, `users:read`
4. Copy Client ID and Secret to `.env`

Note: Slack requires HTTPS redirect URLs — see the HTTPS setup above.

## Project structure

```
connective/
├── docker-compose.yml
├── .env.example
│
├── backend/
│   ├── pyproject.toml
│   ├── alembic.ini
│   ├── alembic/versions/          # 3 migrations
│   └── app/
│       ├── main.py                # FastAPI app, CORS, auto-sync loop
│       ├── config.py              # Pydantic Settings (CONNECTIVE_ prefix)
│       ├── database.py            # Async engine + session factory
│       ├── models/                # SQLModel tables (8 models)
│       ├── api/                   # Route handlers
│       │   ├── auth.py            # Login, JWT exchange
│       │   ├── connectors.py      # OAuth flows, repo/folder listing
│       │   ├── chat.py            # RAG chat with SSE streaming
│       │   ├── scan.py            # Overlap scanning
│       │   ├── ingest.py          # Background ingestion
│       │   └── notifications.py   # Overlap alert notifications
│       ├── connectors/            # Slack, GitHub, Google Drive
│       ├── pipeline/
│       │   ├── chunker.py         # Recursive text splitting (512 tokens)
│       │   ├── embedder.py        # OpenAI embeddings with backoff
│       │   ├── indexer.py         # Dedup + chunk + embed + store
│       │   ├── retriever.py       # Hybrid search + RRF + LLM rerank
│       │   └── overlap_detector.py
│       ├── prompts/               # RAG + scan prompt templates
│       └── services/              # Encryption, OpenAI client
│
└── frontend/
    ├── package.json
    ├── app/
    │   ├── page.tsx               # Landing page (3D hero)
    │   ├── dashboard/page.tsx     # Connector management
    │   └── chat/page.tsx          # Chat interface
    ├── components/
    │   ├── ui/                    # Radix UI primitives
    │   ├── chat/                  # Message list, input, citations
    │   ├── connectors/            # Cards, repo/folder selectors
    │   ├── evidence/              # Evidence panel, timeline
    │   ├── landing/               # 3D animations (Three.js)
    │   └── notifications/         # Alert bell + dropdown
    ├── lib/
    │   ├── api-client.ts          # Backend API wrapper
    │   ├── types.ts               # TypeScript interfaces
    │   └── hooks/                 # useChat, useConnectors, etc.
    └── providers/                 # Auth + session context
```

## Retrieval pipeline

1. **Embed query** — `text-embedding-3-small`
2. **Vector search** — cosine similarity via halfvec cast (`<=>` operator), top 40
3. **Full-text search** — `plainto_tsquery` + `ts_rank`, top 40
4. **Reciprocal Rank Fusion** — merge results with k=60
5. **LLM rerank** — GPT-4o scores top 10 candidates, returns top 6
6. **Generate** — GPT-4o with RAG prompt, mandatory inline citations
7. **Stream** — SSE token-by-token, final event with citations + confidence
