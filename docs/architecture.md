# Architecture — whisper_rag_llm

This document describes the system's components and pipelines. It explains **how the pieces connect**.
- *Why* the project exists and what is out of scope: `specs/000-vision.md`.
- Binding rules (stack, security, quality gates): `specs/constitution.md`.
- Concrete numbers (limits, chunk sizes, top-k…): the feature specs in `specs/NNN-name/`.

Each part is labelled **[current]** (already in the code), **[decided]** (agreed, not implemented yet) or **[planned]** (phase not started).

---

## 1. Components

| Component | Role | Status |
|---|---|---|
| API (FastAPI + Uvicorn) | Auth, upload/real-time endpoints, `/ask` | [current] / `/ask` [planned, Phase 6] |
| Whisper `tiny` (in-process, CPU) | Audio → text with timestamps | [current] |
| MiniLM `all-MiniLM-L6-v2` (in-process) | Text → 384-dim vector | [planned, Phase 5] |
| PostgreSQL + pgvector | Users, transcriptions, chunks and their vectors | [current] schema · data writes [decided] |
| External LLM (API) | Writes the answer from the retrieved text | [planned, Phase 6] |
| LangGraph agent | Picks between vector search and metadata (SQL) queries | [planned, Phase 7] |
| Worker | Moves transcription/ingestion off the request path | [planned, Phase 9] |

---

## 2. Transcription pipeline

**Batch** — `PUT /upload`
```
.wav upload → validate format/size → convert to PCM → temp file → Whisper → result
                                                         └─ temp file deleted
```
- [current] Result returned to the caller; nothing is stored in the database.
- [decided] Store the result in `batch_transcription` with the owner's `username`, a `context` label (see `notas.txt`) and the **date and time the request was received**.

**Real-time** — `/crearRTsession` → `/broadcast` (chunks) → `/cerrarRTsession`
- [current] Partial transcriptions are kept in an in-memory dict (`sesiones`) and are lost on restart.
- [decided] `rt_session` stores the owner's `username` and the session's **create and close date and time**. Each `/broadcast` request is stored **as soon as it is transcribed** as a row of a new table `RealTimeTranscription` (N:1 to `rt_session`): the **date and time it was received** and Whisper's full output, segments included. See ADR `docs/decisions/0002-store-each-realtime-request.md`. [planned, Phase 5]
- Real time of a segment ≈ the request's received time + the segment's `start` offset (Whisper's offsets count from the start of that chunk).

---

## 3. Ingestion pipeline (Phase 5) [planned]
Runs once per stored transcription.
```
transcription (JSON with segments + timestamps)
  → chunks by time window
  → MiniLM → vector(384) per chunk
  → trcpt_embedding: embedding + text + start_time + end_time
                     + session_id XOR batch_id   (constraint check_one_source)
```
- The `text` column is stored next to the vector because **we search with the vector but send the text** (section 4).
- Ownership is not stored on the chunk: it is reached through `session_id → rt_session.username` or `batch_id → batch_transcription.username`.

---

## 4. Question pipeline — `/ask` (Phase 6) [planned]
Runs on every question. This is RAG: a retriever selects relevant passages and only those go to the generator ([Lewis et al., 2020](https://arxiv.org/abs/2005.11401)).
```
question
  → MiniLM (same model as ingestion) → vector(384)
  → pgvector nearest-neighbour search (e.g. cosine distance `<=>`),
    restricted to chunks the user owns
  → top-k chunks (text + timestamps)
  → prompt = question + chunk texts → external LLM
  → answer + citations (chunk text, start_time/end_time)
```
- Vector search: [pgvector README](https://github.com/pgvector/pgvector). Embedding model and semantic search: [sentence-transformers](https://www.sbert.net/).
- Why retrieve instead of sending the whole transcript: lower cost and latency, timestamped citations, and it scales to questions over several transcripts.

---

## 5. Agent (Phase 7) [planned]
A LangGraph agent wraps the question pipeline as tools:
- `search_transcript`: the vector search from section 4.
- `query_metadata`: SQL over transcription metadata (dates, context labels…).

---

## 6. What leaves the server

| Data | Leaves the server? | Where to |
|---|---|---|
| Audio | No | — |
| Embeddings (vectors) | No | — (MiniLM runs locally) |
| Transcript text: retrieved chunks + the question | **Yes** | External LLM provider |
| Credentials and secrets | No | — |

This must be stated in the README and in the `/ask` endpoint description (constitution section 5).

---

## 7. Database access layer (`app/models.py`, `app/database.py`)

SQLAlchemy separates **what the tables look like** from **how to talk to the database**. These are the objects involved:

| Object | What it is | How many | Lives for | Needs the database? |
|---|---|---|---|---|
| `Base` | The catalogue of tables (`Base.metadata`). Every model (`class User(Base)`) registers itself in it. | One | The whole program | No |
| Engine | Knows the URL and the dialect, and keeps a **pool** of open connections that it lends out and takes back. | One per database, per process | The whole process | Only when a connection is first used |
| `SessionLocal` | A `sessionmaker`: a **factory** set up with the engine. Calling `SessionLocal()` gives you a new Session. | One | The whole process | No |
| Session | A **unit of work**: it tracks the objects you load or add, holds a transaction, and `commit()`s or `rollback()`s it. Not safe to share between threads or requests. | One per request or task | Short: open, work, close | Yes, it borrows a connection from the engine |
| `get_db()` | A FastAPI dependency with `yield`: opens a Session for each request and **always closes it** after the response, even if the endpoint raised an error. | One function | — | Yes, through the Session |

Analogy: `Base` is the house's **blueprint**. The engine is the **switchboard** with a few phone lines. `SessionLocal` is the "new call" button. A Session is **one phone call**: you make it, say what you need, and hang up. `get_db` makes sure every endpoint hangs up.

Sources:
- Declarative models and `Base`: [SQLAlchemy, Declarative Mapping Styles](https://docs.sqlalchemy.org/en/20/orm/declarative_styles.html). The 2.0 style is `class Base(DeclarativeBase)`; `declarative_base()` is the older one: [API](https://docs.sqlalchemy.org/en/20/orm/mapping_api.html#sqlalchemy.orm.DeclarativeBase).
- Engine: "intended to normally be a permanent fixture established up-front and maintained throughout the lifespan of an application", [SQLAlchemy, Working with Engines and Connections](https://docs.sqlalchemy.org/en/20/core/connections.html#basic-usage). `create_engine()` does not connect; the first connection is opened on first use: [Engine Configuration](https://docs.sqlalchemy.org/en/20/core/engines.html).
- Session per request, closed at the end: [SQLAlchemy, Session Basics, "When do I construct a Session…"](https://docs.sqlalchemy.org/en/20/orm/session_basics.html#when-do-i-construct-a-session-when-do-i-commit-it-and-when-do-i-close-it).
- `get_db` with `yield`: [FastAPI, Dependencies with yield](https://fastapi.tiangolo.com/tutorial/dependencies/dependencies-with-yield/).

### One engine: the singleton
- **[current]** `main.py` does **not** create a second engine. Python runs a module only the first time it is imported and caches it in `sys.modules`. Every later `import` gets that same module object, so every file that imports `engine` from `app.database` shares **the same** engine ([Python FAQ, "How do I share global variables across modules?"](https://docs.python.org/3/faq/programming.html#how-do-i-share-global-variables-across-modules)). A module-level object is already a singleton in Python.
- **The problem was *when*, not *how many*.** Until spec 002 T4, `app/database.py` read and checked the settings at **import time**, so importing anything from it (even `Base`) failed without a full `.env` (spec 002 G7, and the import part of G1). It also fixed the URL before a test or Alembic could choose a different one (testcontainers, spec 002 T6).
- **[current, since spec 002 T4] Lazy singleton.** `Base` lives in `app/models.py` and needs no settings. `get_engine()` in `app/database.py` builds the engine **the first time it is called**, keeps it in the private `_engine`, and returns the same engine on every later call. `SessionLocal` is created unbound and is bound inside `get_engine()`. `lifespan` in `app/main.py` calls `get_engine()` first, so missing settings still stop the app at startup. Nothing touches the settings on import.
  - Why a plain function and not a `Singleton` class: in Python a module or a cached function already guarantees a single instance, and a class would add code without adding behaviour ([Refactoring Guru, Singleton](https://refactoring.guru/design-patterns/singleton) describes the pattern; the "no class" choice is Claude's judgment, agreed with Marco).
  - Who reaches for it: `app/main.py` (in `lifespan` at startup and in each request through `get_db`) and `alembic/env.py` (only when Alembic runs). `tests/test_db.py` only needs `Base`.
