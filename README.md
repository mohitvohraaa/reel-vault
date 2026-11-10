# ReelVault — Instagram Reel Knowledge Vault (Phase 1)

Turn the Instagram Reels you share into a **private Instagram DM** into a searchable,
structured personal knowledge base. ReelVault parses your Instagram **data export**, lets you
pick the conversation to import, retrieves public reel audio, transcribes it, uses an LLM to
summarize + categorize each reel into validated structured data, and serves a clean dashboard
with **full‑text + semantic search**, **scoped RAG chat**, and **templated PDF export**.

> Phase 1 scope: historical ingestion from a **data export** only. No live Instagram
> integration, webhooks, or browser automation (the interfaces are left modular for Phase 2).

---

## Features

- **DM‑export ingestion** — upload a `.zip`/`.json` export, auto‑detect conversations, **choose
  which conversation to import**, and get a detailed **ingestion report** (messages scanned,
  reel URLs found, unique reels, duplicates skipped, unsupported, parse errors).
- **Robust parser** — tolerant of export schema variants, multi‑part conversations, missing
  fields and malformed JSON; repairs Instagram's mojibake; normalizes + de‑duplicates reel URLs;
  does **not** treat every Instagram link as a reel.
- **Processing pipeline** (async, per‑stage, idempotent, retryable):
  `discovered → metadata_extracted → downloading → transcribing → summarizing → embedding → completed`
  with failure states `media_unavailable`, `transcription_failed`, `summarization_failed`,
  `embedding_failed`, `insufficient_content`. One failed reel never stops the batch.
- **Media retrieval** — yt‑dlp **audio‑only** for public reels (timeouts, size caps, cleanup);
  optional **cookies.txt** to fetch login‑walled reels your own account can see. Private/deleted/
  sound‑withheld reels are **retained** and marked, never lost. No auth bypass.
- **Transcription** — faster‑whisper, multilingual, segment timestamps; music‑only reels fall
  back to caption and are flagged rather than hallucinated.
- **LLM understanding** — Pydantic‑validated JSON (title, one‑liner, summary, category,
  subcategories, key takeaways, entities, actionable insights, content type, importance,
  language). Versioned, isolated prompts; retries with backoff; configurable provider.
- **Search** — PostgreSQL full‑text (keyword), **pgvector semantic**, and **hybrid**.
- **RAG chat** over **selectable, named knowledge bases** — scope a KB to a conversation, a
  collection, a category filter, or hand‑picked reels; answers cite the reels they came from.
- **Deeper categorization** — collections, hierarchical category taxonomy, and **manual
  re‑categorization** (protected from being overwritten by re‑processing).
- **Templated PDF export** — per‑reel, per‑collection/KB/filter, with custom templates.
- **Dashboard** — stats, category distribution, recent reels, library with filters + pagination,
  reel detail with transcript + retry, dark mode, responsive.

**Runs fully offline**: with `LLM_PROVIDER=stub` and `EMBEDDING_PROVIDER=stub` (the defaults),
summaries, embeddings/semantic search and chat work with **no API keys** (deterministic
placeholders). Set a real provider for production‑quality output.

---

## Quick start (Docker)

```bash
cp .env.example .env            # defaults work out of the box (offline stub providers)
docker compose up --build
```

Then open:

- **Frontend**: http://localhost:8080
- **API docs (OpenAPI)**: http://localhost:8000/docs
- **Health**: http://localhost:8000/health

Generate a synthetic export to try the full flow (no real data needed):

```bash
python scripts/make_sample_export.py
# → sample_data/instagram_export.zip  (upload it on the Import page)
```

In the UI: **Import** → upload the ZIP → select the conversation with the most reels → **Import**
→ watch per‑reel statuses → browse **Library**, **Search**, create a **Knowledge Base** and chat,
export a **PDF**.

> The services: `db` (Postgres + pgvector), `redis`, `api` (FastAPI), `worker` (Celery),
> `frontend` (nginx). The `api` container runs Alembic migrations on startup.

---

## How to get your Instagram data export

1. Instagram app/website → **Settings → Accounts Centre → Your information and permissions →
   Download your information**.
2. Request a download of **Messages** (DMs). Choose **JSON** format (not HTML).
3. When the export is ready, download the ZIP. It contains
   `your_instagram_activity/messages/inbox/<conversation>/message_1.json`.
4. Upload that ZIP directly on the ReelVault **Import** page and pick your alt‑account
   conversation. ReelVault only reads the conversation you select.

---

## Getting the actual reel content (yt-dlp cookies)

The DM export contains only reel **URLs** (plus sender/timestamp/creator) — not the video, caption,
or transcript. ReelVault fetches the real content with **yt-dlp** in the media stage, then
transcribes it with Whisper. Fully-public reels download anonymously, but Instagram **login-walls
most reels**, which show up as `media_unavailable`.

To fetch the reels *your own account can see*, give yt-dlp your **browser cookies** (this is your own
session — **not** an API key, and no auth is bypassed):

1. In a browser where you're **logged into Instagram**, export cookies in **Netscape `cookies.txt`
   format** using a reputable extension (e.g. "Get cookies.txt LOCALLY"). Export for `instagram.com`.
2. Save the file as **`secrets/cookies.txt`** in the project root. It's mounted read-only into the
   `api` and `worker` containers at `/secrets/cookies.txt` (the default `YTDLP_COOKIES_FILE`), and
   git-ignored.
3. Recreate the workers so they pick it up:
   ```bash
   docker compose up -d --force-recreate api worker
   ```
4. Re-process affected reels with **Retry** (per reel) — `media_unavailable` reels will now download,
   transcribe, and summarize.

Notes: cookies expire (re-export when downloads start failing again); keep requests modest to avoid
rate-limiting; ReelVault never bypasses access controls — cookies only let it see what you already can.
Leave `secrets/cookies.txt` absent to fetch public reels only.

---

## Configuring AI providers

All providers are environment‑driven (`.env`). Never hardcode keys.

| Variable | Purpose | Values |
|---|---|---|
| `LLM_PROVIDER` | summarization + chat | `stub` (offline), `openai`, `gemini` |
| `LLM_MODEL` / `LLM_API_KEY` | model + key | e.g. `gpt-4o-mini` |
| `EMBEDDING_PROVIDER` | semantic search + RAG | `stub` (offline), `openai`, `gemini` |
| `EMBEDDING_MODEL` / `EMBEDDING_API_KEY` | embedding model + key | e.g. `text-embedding-3-small` |
| `EMBEDDING_DIM` | vector size | must match the model (OpenAI small = `1536`) |
| `WHISPER_MODEL` | transcription size | `tiny`…`large-v3` (`base` default) |

**Changing `EMBEDDING_DIM`** after the DB exists requires re‑creating the `reel_chunks` table
(the vector column is fixed‑width). Drop the volume or re‑run migrations on a fresh DB.

---

## Local development (without Docker)

**Backend** (Python 3.12 recommended; 3.10+ works via a `StrEnum` shim):

```bash
cd backend
python -m venv .venv && source .venv/Scripts/activate   # Windows Git Bash
pip install -r requirements.txt
# point DATABASE_URL at a local Postgres+pgvector, then:
alembic upgrade head
uvicorn app.main:app --reload
celery -A app.core.celery_app.celery_app worker -Q reelvault   # in another shell
```

**Frontend**:

```bash
cd frontend
npm install
npm run dev        # http://localhost:5173, proxies /api to http://localhost:8000
```

---

## Tests

```bash
cd backend
pip install fastapi pydantic pydantic-settings SQLAlchemy python-multipart jinja2 httpx pytest "qrcode[pil]"
pytest
```

The suite runs **fully offline** on SQLite with stub providers (no Celery, no network, no
yt‑dlp/whisper). It covers export parsing, conversation identification, URL extraction,
dedup, timestamp parsing, malformed‑export tolerance, LLM‑response validation, pipeline
failure isolation + retry, PDF templating, and API pagination/filters/search/chat.

---

## Architecture

```
reel_vault/
  backend/            FastAPI + SQLAlchemy 2.0 + Celery
    app/
      api/routes/     ingestion, reels, collections, categories,
                      knowledge_bases, chat, search, pdf
      services/
        instagram/    deterministic export parser + URL classifier
        ingestion/    upload → parse → import orchestration + report
        media/        yt-dlp audio-only retrieval
        transcription/faster-whisper
        summarization/LLM providers + versioned prompts + Pydantic schema
        embeddings/   provider abstraction + chunk/embed
        search/       keyword + semantic (pgvector) + hybrid
        chat/         retrieval-augmented generation with citations
        pdf/          WeasyPrint templated export
        pipeline.py   per-stage orchestration (idempotent, retryable)
      workers/        Celery tasks + inline dispatch
      models/ schemas/ core/
    alembic/          migrations (pgvector extension, FTS + ivfflat indexes)
    tests/            synthetic fixtures + suite
  frontend/           React + Vite + TS + Tailwind + shadcn-style UI
  scripts/            make_sample_export.py
  sample_data/        generated synthetic export (gitignored)
  docker-compose.yml  .env.example
```

---

## Known limitations

- **Export‑only ingestion** in Phase 1 — no live Instagram integration (Phase 2). Interfaces are
  modular so live ingestion can be added without reworking the pipeline.
- **Public‑only media retrieval** via yt‑dlp. Private, deleted, or **sound‑withheld** (music‑rights)
  reels can't be downloaded; they're retained and marked `media_unavailable`. ReelVault never
  bypasses Instagram authentication or access controls (this also avoids the account‑ban risk of
  private‑API scraping tools).
- Reels with **no speech and no caption** → `insufficient_content`. OCR of on‑screen/burned‑in
  text is a planned enhancement (the pipeline is modular for it).
- With **stub providers** (no keys), summaries/embeddings/chat are deterministic placeholders
  grounded in the available text — good for demos and tests, not a substitute for a real model.
- The DM export generally does **not** include the reel's original caption, so captions are often
  empty; ReelVault relies on the transcript and never fabricates metadata.

---

## Phase 2+ roadmap

Live DM ingestion (Meta webhooks), OCR of on‑screen text, an MCP server to query the vault from
any AI assistant, transcript translation, saved/dynamic knowledge bases, and shareable read‑only
KB pages.
