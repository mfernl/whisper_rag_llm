# 0002 — Store each real-time request when it arrives

- Status: Accepted
- Date: 2026-11-17
- Constitution: v2.0.0 → v3.0.0 (MAJOR: section 5 Persistence redefined)

## Context
- Constitution v2.0.0 section 5 said: "When a real-time session is closed, its full transcription is stored in the database."
- Until the close, `/broadcast` appends every Whisper output to an in-memory dict (`sesiones` in `app/main.py`). That list keeps growing for as long as the session is open.
- Anything kept in memory is lost when the server restarts. Render's free tier stops idle services after 15 minutes (https://render.com/docs/free#spinning-down-on-idle), and the deploy target is that tier (constitution section 2).
- A dict in memory is not shared between processes, so it would break once the API runs in more than one process (Phase 8, worker).
- On 2026-11-16 we decided that a session keeps each transcription request separately, with the date and time it was received. Whether to store them as a JSON list in `rt_session` or as rows of a new table was left open (`docs/architecture.md` section 2).

## Decision
1. **A new table, `RealTimeTranscription`, N:1 to `RealTimeSession`.** One row per `/broadcast` request: `id` (PK), `session_id` (FK to `rt_session.session_id`), the date and time the request was received, and Whisper's full output (segments with their timestamps included).
   A table instead of a JSON list, because the requests will be queried by time (Phase 6, metadata queries), and the PostgreSQL docs advise that each JSON value should be an atomic datum that is not modified or queried piece by piece (https://www.postgresql.org/docs/current/datatype-json.html#JSON-DOC-DESIGN).
2. **`RealTimeSession` keeps only `session_id`, `username`, and its create and close dates and times.** The JSON `transcription` and `exp_date` columns are removed.
3. **Each `/broadcast` request writes its row as soon as it is transcribed**, instead of everything being written at close.

## Consequences
- Constitution section 5 Persistence is rewritten (v3.0.0).
- `specs/000-vision.md` section 5: the non-goal "asking about a session before it is closed" can no longer be justified by the data not existing yet. It stays a non-goal for now, and `004-ingestion` decides it, together with when embeddings are created.
- `docs/architecture.md` section 2: the open question (JSON list vs table) is closed.
- `specs/001-data-model` describes the current model and stays as is. `004-ingestion` must update it when the change is implemented (constitution section 3).
- To be decided in `004-ingestion`:
  - how an open session expires after a restart (for example, from the last request's received time plus `RTSESSION_EXP`, without the in-memory deadline);
  - whether `/broadcast` checks ownership with the token's `username` against `rt_session.username`, instead of comparing tokens kept in memory;
  - whether embeddings are created at close or per request;
  - `JSONB` vs `JSON` for the Whisper output;
  - `timestamptz` in UTC for every date and time.
- Nothing changes in the code until Phase 4. Phases 2 (Postgres tests) and 3 (CI) come first, so that the new foreign key can be tested against Postgres.
