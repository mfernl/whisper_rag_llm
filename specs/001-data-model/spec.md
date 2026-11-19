# 001 — Data model

- **Status:** Implemented (retroactive spec)
- **Phase:** 1
- **Last updated:** 2026-11-17
- **Related:** `specs/constitution.md`, `specs/000-vision.md`, `docs/architecture.md`

> Retroactive spec: it records what Phase 1 already built and links each criterion to its test.
> It does not redesign anything. Behaviour that is missing or wrong goes to "Known gaps".

---

## 1. Context

Phase 1 added the `RealTimeSession`, `BatchTranscription` and `TranscriptionEmbeddings` models (`app/models.py`). They give the system a place to keep transcriptions from both endpoints (real-time and batch), linked to the user who created them, and to keep the embeddings of transcription fragments, so that vector search can later give the LLM the parts of a transcription the user is asking about. This serves the first goal of `000-vision.md` section 4 ("A user's transcriptions are stored") and prepares the `/ask` goal.

This phase only defines the tables and their rules. Writing to them from the endpoints happens in Phase 5 (see section 2).

## 2. Scope

### In scope
- `RealTimeSession` (table `rt_session`)
- `BatchTranscription` (table `batch_transcription`)
- `TranscriptionEmbeddings` (table `trcpt_embedding`) and its `check_one_source` constraint

### Out of scope
| Item | Where it goes |
|---|---|
| `Admin`, `User` | Not specified yet: they come from Transcript_whisper. `User` is only referenced here, as the owner of sessions and batches. |
| `IWord`, `WordDetectionLog` | Not specified yet (important-word detection, inherited feature). |
| PostgreSQL, pgvector, Alembic | `002-postgres-pgvector` |
| Start and close date+time of a real-time session | `005-ingestion` (decision of 2026-11-16) |
| A new `RealTimeTranscription` model, one row per request with its received date+time and text | `005-ingestion`. Whether it is a table or a JSON list is still open. |
| Received date+time of a batch request | `005-ingestion` |
| Endpoints (`upload_archivo`, `cerrar_RTsession`) storing transcriptions and embeddings | `005-ingestion` (vision section 7: "Storage and ingestion") |

## 3. Entities

### 3.1 Real-time session
- **Represents:** a real-time transcription session opened by a user, together with its transcription.
- **Identified by:** `session_id` (unique, required).
- **Belongs to:** the user given by `username`.
- **Rules:**
  - `session_id` is unique.
  - `username` refers to an existing user (see AC-3.1 and gap G2).
  - The transcription is stored as JSON.

### 3.2 Batch transcription
- **Represents:** the transcription of one uploaded `.wav` file.
- **Identified by:** `batch_id` (unique, required).
- **Belongs to:** the user given by `username`.
- **Rules:**
  - `batch_id` is unique.
  - `context` is required.
  - `username` refers to an existing user.
  - The transcription is stored as JSON.

### 3.3 Transcription embedding
- **Represents:** the embedding of one fragment of a transcription, with the fragment's text and its `start_time`/`end_time`.
- **Identified by:** `id`.
- **Belongs to:** exactly one source, either a real-time session (`session_id`) or a batch transcription (`batch_id`). Through that source, it belongs to a user (constitution section 5, Ownership).
- **Rules:**
  - It has exactly one of `session_id` or `batch_id`: never both, never neither (`check_one_source`).
  - The embedding, `start_time`, `end_time` and `text` are required.
  - The embedding has 384 dimensions.

## 4. Requirements and acceptance criteria

### R1. Sessions and batches are stored per user
**As** a user, **I want** my real-time sessions and batch transcriptions to be saved with my username, **so that** they can be found and used after the request that created them.

- **AC-1.1** WHEN a real-time session is saved with a `session_id` and the `username` of an existing user, THE SYSTEM SHALL store it and return it when queried by `session_id`.
- **AC-1.2** WHEN a batch transcription is saved with a `batch_id`, a `context` and the `username` of an existing user, THE SYSTEM SHALL store it and return it when queried by `batch_id`.
- **AC-1.3** IF a session or batch is saved with a `session_id` or `batch_id` that already exists, THEN THE SYSTEM SHALL reject it.

### R2. An embedding comes from exactly one transcription
**As** a user, **I want** every embedding to point to exactly one transcription, **so that** an answer from `/ask` can cite which recording a fragment comes from and who owns it.

- **AC-2.1** IF an embedding is saved with both `session_id` and `batch_id`, THEN THE SYSTEM SHALL reject it.
- **AC-2.2** IF an embedding is saved with neither `session_id` nor `batch_id`, THEN THE SYSTEM SHALL reject it.
- **AC-2.3** WHEN an embedding is saved with only a `batch_id`, THE SYSTEM SHALL store it.
- **AC-2.4** WHEN an embedding is saved with only a `session_id`, THE SYSTEM SHALL store it.

### R3. Every session and batch belongs to an existing user
**As** an admin, **I want** every session and batch to belong to a registered user, **so that** ownership (constitution section 5) can always be checked and there is no data without an owner.

- **AC-3.1** IF a real-time session or batch transcription is saved with a `username` that does not exist, THEN THE SYSTEM SHALL reject it.

## 5. Traceability

| Criterion | Test (`tests/test_db.py`) | Passes today? |
|---|---|---|
| AC-1.1 | `test_realTime_Batch_db` | Not runnable (G1) |
| AC-1.2 | `test_realTime_Batch_db` | Not runnable (G1) |
| AC-1.3 | — | No test (G3) |
| AC-2.1 | `test_embedding_two_transcriptions` | Not runnable (G1) |
| AC-2.2 | `test_embedding_no_transcriptions` | Not runnable (G1) |
| AC-2.3 | `test_only_batch_accepted` | Not runnable (G1) |
| AC-2.4 | `test_only_session_accepted` | Not runnable (G1) |
| AC-3.1 | `test_rt_session_usuario_inexistente` | Not checked: no `assert` (G2) |

## 6. Known gaps

- **G1. The suite does not collect (checked 2026-11-17).** `tests/test_db.py` imports `app.models`, which imports `app.database`. At import time, that module raises an error if `POSTGRES_USERNAME`, `POSTGRES_PASSWORD` or `POSTGRES_DB` are missing, and it creates a Postgres engine, which needs `psycopg`. The local `.venv` (Python 3.10) doesn't have `psycopg`. So the tests can't use their own SQLite engine, even though they create one. → `002-postgres-pgvector` (testcontainers fixture) + recreate the `.venv` with 3.11.
- **G2. Foreign keys are not enforced in the tests.** By default, SQLite doesn't check foreign keys ([SQLite docs, section 2](https://www.sqlite.org/foreignkeys.html#fk_enable)), so `test_rt_session_usuario_inexistente` saves a session for a user who doesn't exist. Its `pytest.raises` is commented out, so it checks nothing. → `002-postgres-pgvector`: run it against Postgres and restore the `pytest.raises(IntegrityError)`.
- **G3. AC-1.3 (duplicate ids) has no test.** → `002-postgres-pgvector`.
- **G4. The embedding tests use `"asdfg"` as the embedding.** That isn't a 384-dimension vector, and pgvector will reject it. → `002-postgres-pgvector`: use a valid vector of length 384.

## 7. Open questions

- **Q1.** `rt_session.exp_date` defaults to the creation time. Is it an expiry date or a start date? → **Answered 2026-11-17:** it is removed and replaced by create and close dates in `005-ingestion` (ADR 0002).
- **Q2.** What unit do the embedding's `start_time`/`end_time` use (seconds? milliseconds?), and how do they relate to the request times decided on 2026-11-16? → `005-ingestion`.
- **Q3.** If `005-ingestion` adds a `RealTimeTranscription` table, does the JSON `transcription` column on `rt_session` stay? → **Answered 2026-11-17:** no, it is removed (ADR 0002).
- **Q4.** The dimension 384 comes from the planned embedding model (MiniLM). Should the constitution record it, together with the sentence-transformers version (section 1 TODO), so that this spec and `005-ingestion` follow it? **Answered 2026-11-19:** Yes, the constitution should record the transformer version and the vector dimension. Future changes will need to create a ADR.
