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
| API (FastAPI + Uvicorn) | Auth, upload/real-time endpoints, `/ask` | [current] / `/ask` [planned, Phase 5] |
| Whisper `tiny` (in-process, CPU) | Audio → text with timestamps | [current] |
| MiniLM `all-MiniLM-L6-v2` (in-process) | Text → 384-dim vector | [planned, Phase 4] |
| PostgreSQL + pgvector | Users, transcriptions, chunks and their vectors | [current] schema · data writes [decided] |
| External LLM (API) | Writes the answer from the retrieved text | [planned, Phase 5] |
| LangGraph agent | Picks between vector search and metadata (SQL) queries | [planned, Phase 6] |
| Worker | Moves transcription/ingestion off the request path | [planned, Phase 8] |

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
- [decided] On close, the full transcription is persisted in `rt_session` with the owner's `username` and the **date and time the session started**. The session keeps **each transcription request separately**, with the date and time it was received and its own text.
- Open design question for the Phase 4 spec: store the requests as a JSON list inside `rt_session.transcription`, or as rows of a new table linked to the session.

---

## 3. Ingestion pipeline (Phase 4) [planned]
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

## 4. Question pipeline — `/ask` (Phase 5) [planned]
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

## 5. Agent (Phase 6) [planned]
A LangGraph agent wraps the question pipeline as tools:
- `buscar_en_transcripcion`: the vector search from section 4.
- `consultar_metadatos`: SQL over transcription metadata (dates, context labels…).

---

## 6. What leaves the server

| Data | Leaves the server? | Where to |
|---|---|---|
| Audio | No | — |
| Embeddings (vectors) | No | — (MiniLM runs locally) |
| Transcript text: retrieved chunks + the question | **Yes** | External LLM provider |
| Credentials and secrets | No | — |

This must be stated in the README and in the `/ask` endpoint description (constitution §5).
