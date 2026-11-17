# Vision — whisper_rag_llm
Date: 2026-11-16

This file answers **why** the project exists and **what** it covers.
How the pieces connect → `docs/architecture.md`. Rules → `specs/constitution.md`. Numbers and acceptance criteria → `specs/NNN-name/spec.md`.

## 1. Problem
- Transcript_whisper uses FastAPI combined with OpenAI's Whisper model to transcribe `.wav` audio into text. It includes user and admin authentication, batch and real-time transcription, important-word detection, and host/app status monitoring.
- Transcript_whisper only returns a transcription; it doesn't store it anywhere, so the user cannot come back to it later.
- To find out what was said in a recording, the user has to read the whole transcription, and finding a specific detail in a long recording is slow.

## 2. Solution
- Transcriptions are stored and linked to the user who created them.
- A new `/ask` endpoint lets users ask questions about their transcriptions. It uses embeddings, vector search over PostgreSQL and an LLM, and answers with the fragments it is based on and their timestamps. This removes the need to read the whole transcription to understand what was said, and makes it easier to find specific things said during the recording.
- The project also aims to follow good SDD and CI/CD practices, with tests and GitHub issues.

## 3. Users
- **User:** logs in to the app, transcribes audio, checks uptime and host status, creates and closes real-time sessions, and asks questions about their own transcriptions.
- **Admin:** has all the features without restrictions and can ask questions about every transcription stored in the database. Admins also register new users and manage the important-words list.

## 4. Goals
- A user's transcriptions (batch and real-time) are stored, so they can be used after the request that created them.
- A user can ask a question about their transcriptions and get an answer that cites the fragment and its timestamp.
- A user can ask questions that combine content and metadata, e.g. "What did they say about X in last Tuesday's meeting?"
- Answer quality is measured, not assumed.
- The whole system starts locally with a single `docker compose up`, and it is deployed on Render.

## 5. Non-goals (out of scope)
- Fine-tuning.
- Speaker diarization.
- User data deletion (constitution §5).
- Audio formats other than `.wav`.
- A graphical frontend: the API, with its Swagger UI, is the interface.
- Asking questions about a real-time session before it is closed. Each request is stored as it arrives (constitution §5), but embeddings are not created yet; `004-ingestion` decides whether this stays a non-goal (ADR 0002).

## 6. Success criteria
- Answer quality is evaluated with RAGAS on a fixed set of questions about real transcriptions, and the results are published in the README. Target values are defined in the Phase 7 spec.
- The system is deployed on Render's free tier (constitution §2), and a registered user can transcribe audio and ask questions about it there.
- Someone who has never seen the project can run it locally by following the README.

## 7. Roadmap
Each phase has one spec folder, one GitHub issue, one branch and one pull request (constitution §4). Phases 1-2 were built before the SDD workflow; their specs are retroactive.

| Phase | Outcome | Spec |
|---|---|---|
| 1 | Data model for transcriptions and embeddings *(retroactive)* | `specs/001-data-model/` |
| 2 | PostgreSQL + pgvector + migrations *(retroactive)* | `specs/002-postgres-pgvector/` |
| 3 | CI: the test suite runs on GitHub Actions on every push and pull request | `specs/003-ci/` |
| 4 | Storage and ingestion: transcriptions are stored per user, then chunked and embedded | `specs/004-ingestion/` |
| 5 | `/ask`: answers with cited fragments and timestamps | `specs/005-ask/` |
| 6 | Agent combining transcript search and metadata queries | `specs/006-agent/` |
| 7 | Answer quality evaluated with RAGAS | `specs/007-evaluation/` |
| 8 | Worker + multi-service Docker Compose | `specs/008-worker/` |
| 9 | README + continuous deployment to Render | `specs/009-readme-cd/` |
