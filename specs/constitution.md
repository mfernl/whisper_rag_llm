# Constitution — whisper_rag_llm
Version: 2.0.0 · Date: 2026-11-16

## 1. Fixed stack
Changing any of these elements requires opening a decision record (ADR) in `docs/decisions/`.

| Layer | Technology | Version |
|---|---|---|
| Language | Python | 3.11 (`python:3.11-slim-bookworm`; image currently 3.11.18) |
| API | FastAPI + Uvicorn | FastAPI 0.162.0 · Uvicorn 0.54.0 |
| Persistence | PostgreSQL + pgvector (image `pgvector/pgvector:0.8.7-pg18-bookworm`) | pgvector 0.8.7 · PostgreSQL 18 |
| ORM and migrations | SQLAlchemy + Alembic + psycopg + pgvector (Python package) | SQLAlchemy 2.1.6 · Alembic 1.20.1 · psycopg 3.3.6 · pgvector 0.5.1 |
| Transcription | openai-whisper (`tiny` model) + torch (CPU) | openai-whisper 20250625 · torch 2.15.0 (CPU build) |
| Embeddings | sentence-transformers with `all-MiniLM-L6-v2` (dimension 384 → `Vector(384)` column) | TODO: pin when added in Phase 4 (ingestion) |
| Authentication | python-jose + bcrypt | python-jose 3.5.0 · bcrypt 5.0.0 |
| Packaging | Docker + Docker Compose | — |

Exact versions are pinned in `requirements.txt` (and torch also in the `Dockerfile`). This table and those files must always match.

**LLM (Phases 5 and 6):** called through an external API. Provider and model version: TODO — to be decided after research, and recorded in this table once chosen.

## 2. Constraints
- Deployment on Render, free tier: 512 MB of RAM. Internet access is available.
- Embeddings are generated with the model loaded in the memory of the Render service.
- Known risk: it has not been measured whether torch + Whisper tiny + MiniLM fit in 512 MB. What to do if they don't is left open; it will be decided once measured.

## 3. Quality gates (Definition of Done)
- A task is done when its tests and the whole suite are green.
  - A skipped test counts as green only if it carries a reason (reviewed with `pytest -rs`).
  - If the integration tests do not run because Docker is unavailable, the suite does NOT count as green.
- Every acceptance criterion (EARS) has at least one test that checks it.
- Work follows TDD cycles (red → green → refactor), starting with the tests for each EARS criterion. Beyond those tests, the developer decides when to stop iterating.
- Integration tests run with pytest + testcontainers-python, locally and in CI, with Python 3.11 and the image `pgvector/pgvector:0.8.7-pg18-bookworm`.
- Once CI exists (Phase 3), a pull request can be merged into `main` only when the CI run on it is green.
- Every Alembic migration is reviewed by hand before it is committed.
- A task that changes the behaviour described in another spec is done only when that other spec has been updated to match.

## 4. Working conventions
- One commit per task.
- Commit messages follow [Conventional Commits](https://www.conventionalcommits.org/en/v1.0.0/) (`feat:`, `fix:`, `test:`, `docs:`…).
- Language: everything in English (code, commits, specs and documentation) from 2026-11-16 on.
- Issues, branches and pull requests: one GitHub issue, one branch and one pull request **per spec**, with one commit per task inside that branch. The branch is named like the spec folder (`NNN-name`), and the pull request closes the issue (`Closes #N`). See `docs/decisions/0001-branch-per-spec-and-ci.md`.
  - This applies from the CI phase (Phase 3) on. Until then, direct commits to `main`.
  - Trivial changes that belong to no spec (typos, docs wording) may be committed directly to `main`; CI still runs on the push.
- Specs structure: `specs/constitution.md`, `specs/000-vision.md` and one folder per feature or phase: `specs/NNN-name/{spec.md, plan.md, tasks.md}`. Decision records go in `docs/decisions/`.

## 5. Security and data principles
- **Ownership.** Each user can only access the data they created: real-time sessions, batch transcriptions and the embeddings derived from them. Ownership is determined by the `username` of the session or batch the data belongs to. Admins can access everything.
- **Retrieval isolation.** Vector search is restricted to the requesting user's data *before* ranking, so other users' chunks can never reach the top-k results or the LLM prompt.
- **Secrets.** Passwords, keys and other secrets are read from environment variables (a `.env` file locally). They must never appear in git or in logs.
- **Credentials.** User and admin passwords are stored only as bcrypt hashes. Credentials and tokens never travel in URLs or query strings.
- **Tokens.** Every access token has an expiry date and it is always verified. There are no hard-coded tokens or authentication bypasses.
- **Third parties.** Only text (retrieved transcript chunks and the user's question) is sent to the external LLM provider. Audio and embeddings never leave the server. This is stated in the README and in the description of every endpoint that calls the LLM.
- **Persistence.** When a real-time session is closed, its full transcription is stored in the database.
- **Retention.** Transcriptions and their embeddings are kept in the database. Users cannot delete them; deletion is not a feature.
- **Upload limits.** Every audio upload is restricted by format (only `.wav`), maximum size per request and maximum amount of audio per user. The limits are stated in the endpoint description; their values are defined in the feature specs, not here.
- **Limit errors.** Exceeding a limit returns a clear error: 413 for size, 429 or 403 for quota (exact code chosen in the feature spec), and nothing is stored.
- See `docs/architecture.md` §6 for what data leaves the server.

## 6. Governance
- **Precedence.** This constitution overrides every spec, plan and task. If a spec contradicts it, the spec is wrong: either the spec is fixed, or the constitution is amended first through this section. There are no silent exceptions.
- **Versioning.** The version follows semantic versioning:
  - MAJOR: a rule is removed or redefined in a way that can make existing specs non-compliant.
  - MINOR: a rule or section is added, or an existing one is materially expanded (e.g. filling a TODO in §1).
  - PATCH: wording, typos or clarifications that do not change meaning.
- **Process.** Every amendment goes in its own `docs:` commit that updates the version and date at the top of this file. A MAJOR amendment also needs a decision record in `docs/decisions/` explaining why.
- **Ripple effect.** An amendment is done only when every affected spec has been updated to comply, in the same change.
