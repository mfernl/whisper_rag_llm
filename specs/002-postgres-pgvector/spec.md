# 002 — PostgreSQL + pgvector + migrations

- **Status:** Partly implemented (retroactive spec + closing tasks)
- **Phase:** 2
- **Last updated:** 2026-11-19
- **Related:** `specs/constitution.md` (section 1 stack, section 3 testing, section 5 secrets), `specs/001-data-model/spec.md` (gaps G1-G4), `docs/architecture.md`

> Retroactive spec, like 001: it records what Phase 2 already built. Unlike 001, Phase 2 is not closed.
> What is still missing goes to "Known gaps" here and becomes a task in `tasks.md` (written after this spec).

---

## 1. Context

The `/ask` endpoint (Phase 5) has to find the fragments of a user's transcriptions that are closest to a question. SQLite has no vector type and no nearest-neighbour search, so the project moved to PostgreSQL with the pgvector extension, which adds a `vector` column type and distance operators such as cosine distance `<=>` (`docs/architecture.md` section 4). This phase serves the first two goals of `000-vision.md` section 4: transcriptions are stored, and a user can ask questions about them.

The schema is managed with Alembic migrations instead of `Base.metadata.create_all`. `create_all` only creates the tables that are missing; it can't change an existing table, and it keeps no history. Migrations are versioned in git, they can be reviewed by hand (constitution section 3), and they can be reverted.

## 2. Scope

### In scope
- The `db` service in `compose.yaml`: the PostgreSQL + pgvector image, a named volume for its data, and a healthcheck that the API waits for.
- Connection settings read from environment variables (`.env` locally), with a clear error when one is missing.
- The first Alembic migration: it creates the `vector` extension and every table of the models, including the `Vector(384)` column.
- Running the database tests against a real PostgreSQL + pgvector database with testcontainers, and closing gaps G1-G4 of spec 001.
- The code that breaks constitution section 5 (G10). Whether it stays in this spec is open (Q4).

### Out of scope
| Item | Where it goes |
|---|---|
| Schema changes decided in ADR 0002 (`RealTimeTranscription`, session create and close dates) | `004-ingestion` |
| Running the tests on GitHub Actions | `003-ci` |
| A vector index (HNSW or IVFFlat) for faster search | `005-ask`, when there is real data to measure |
| A managed PostgreSQL on Render | `009-readme-cd` |

## 3. Components

### 3.1 Database service
- **What it is:** PostgreSQL 18 with pgvector 0.8.7, from the image `pgvector/pgvector:0.8.7-pg18-bookworm`, the one pinned in constitution section 1.
- **Where its data lives:** in the named volume `db-data`, mounted at `/var/lib/postgresql`. The volume survives `docker compose down` and image rebuilds. `docker compose down -v` deletes it, and all the data with it.
- **How the API knows it is ready:** the `db` service has a healthcheck (`pg_isready` every 10 s, up to 5 retries). The API service uses `depends_on` with `condition: service_healthy`, so Compose starts the API only after the database is healthy.

### 3.2 Connection configuration
- **Where the settings come from:** the environment variables `POSTGRES_USERNAME`, `POSTGRES_PASSWORD` and `POSTGRES_DB`. Compose loads them from `.env` (`env_file`), and `app/database.py` reads them. The `.env` file is ignored by git (constitution section 5, Secrets).
- **What happens if a setting is missing:** `app/database.py` raises a `RuntimeError` when it is imported, listing every missing variable. The API, Alembic and the tests all import it, so none of them starts.
- **Host:** the host `db` is hard-coded in `pg_uri`. It is the name of the Compose service, so it only resolves inside the Compose network, and the `db` service publishes no port. Alembic and psql can only connect from inside Compose (G8).

### 3.3 Schema migrations
- **Tool:** Alembic. `alembic/env.py` takes the URL from `pg_uri` and the target schema from `Base.metadata`.
- **Current revision(s):** one, `e6edc15da35a` ("esquema inicial"). It is the first migration (`down_revision = None`) and the current head.
- **Who creates the `vector` extension:** the migration itself. The first line of `upgrade()` runs `CREATE EXTENSION IF NOT EXISTS vector`, so an empty database gets the extension from `alembic upgrade head`, not from the app.
- **How the schema is applied:** by hand. The developer runs `alembic upgrade head` inside the API container. Nothing runs it automatically yet (Q2).

### 3.4 Test database
- **Today:** the `db_session` fixture in `tests/test_db.py` creates an in-memory SQLite database with `create_all`. The suite doesn't even collect, because importing the models needs the Postgres settings (G1). SQLite also doesn't check foreign keys (G2) or vectors (G4).
- **Target:** pytest + testcontainers-python start a throwaway container from the same image as `db`, with Python 3.11, both locally and in CI (constitution section 3).

## 4. Requirements and acceptance criteria

### R1. The database starts with the system and the API waits for it
**As** the developer, **I want** the database to start together with the API, **so that** the API never tries to connect to a database that isn't ready.

- **AC-1.1** WHEN `docker compose up` is run, THE SYSTEM SHALL start the database and report it as healthy.
- **AC-1.2** IF the database is not healthy yet, THEN THE SYSTEM SHALL wait to start the API until it is.

### R2. The schema is created only by migrations
**As** the developer, **I want** to change the database schema only with Alembic migrations, **so that** every version of the schema is recorded in git and a change can be reverted if something goes wrong.

- **AC-2.1** WHEN `alembic upgrade head` is run on an empty database, THE SYSTEM SHALL create the `vector` extension and every table of the models.
- **AC-2.2** WHEN `alembic downgrade base` is run, THE SYSTEM SHALL drop every table and index that the migration created, leaving no application tables (see Q1 for the `vector` extension).
- **AC-2.3** WHEN `alembic check` is run, THE SYSTEM SHALL report that the models and the migrations match (no new upgrade operations).

### R3. Connection settings come from the environment
**As** the developer, **I want** the database settings to come from environment variables, **so that** secrets are kept out of git and out of the code.

- **AC-3.1** IF any of `POSTGRES_USERNAME`, `POSTGRES_PASSWORD` or `POSTGRES_DB` is missing, THEN THE SYSTEM SHALL refuse to start and raise an error that names every missing variable.

### R4. Data survives restarts
**As** a user, **I want** my data to survive restarts and rebuilds, **so that** I don't lose my transcriptions during maintenance.

- **AC-4.1** WHEN the containers are stopped and started again (`docker compose down`, then `up`) or the API image is rebuilt, THE SYSTEM SHALL keep all the data stored before. (`docker compose down -v` deletes the data on purpose and is not covered.)

### R5. Tests run against the real database engine
**As** the developer, **I want** the tests to run against the same database engine as production, in a throwaway database, **so that** they check what PostgreSQL really enforces (foreign keys, vectors) without touching the real data.

- **AC-5.1** WHEN the test suite runs, THE SYSTEM SHALL start a throwaway PostgreSQL + pgvector container (image `pgvector/pgvector:0.8.7-pg18-bookworm`) with testcontainers, create the schema in it, and run the database tests against it.
- **AC-5.2** IF Docker is not available, THEN THE TEST SUITE SHALL fail with an error saying that Docker is needed, and SHALL NOT skip the database tests (constitution section 3).

## 5. Traceability

| Criterion | How it is checked (test or command) | Passes today? |
|---|---|---|
| AC-1.1 | `docker compose up -d`, then `docker compose ps`: `whisper_rag_db` shows `(healthy)` | Not checked (Docker not running, 2026-11-19) |
| AC-1.2 | `docker compose up`: `whisper_rag_service` starts only after `whisper_rag_db` is `(healthy)` (`depends_on` + `condition: service_healthy`) | Not checked (Docker not running, 2026-11-19) |
| AC-2.1 | Empty DB (`docker compose down -v`, then `up -d`), then `docker compose exec server_fastAPI alembic upgrade head`. `alembic current` shows `e6edc15da35a (head)`, `\dx` lists `vector`, `\dt` lists the model tables. Later also an integration test (R5). | Not checked (Docker not running, 2026-11-19) |
| AC-2.2 | `alembic downgrade base`, then `\dt` shows only `alembic_version` | Not checked (Docker not running, 2026-11-19) |
| AC-2.3 | `alembic check` prints "No new upgrade operations detected." | Not checked (Docker not running, 2026-11-19) |
| AC-3.1 | Today: `python -c "import app.database"` with the three `POSTGRES_*` variables unset raises `RuntimeError` naming each one. Needs a pytest test (G9). | Yes, by command (2026-11-19) |
| AC-4.1 | Write a row, `docker compose down`, `up -d`: the row is still there. After `down -v` it is gone (expected). | Not checked (Docker not running, 2026-11-19) |
| AC-5.1 | Testcontainers fixture in `tests/conftest.py` (not written yet) | No (G1, checked 2026-11-19) |
| AC-5.2 | Stop Docker, run `python -m pytest -rs`: the database tests error, none is skipped | No: there is no fixture yet |

> Fill "Passes today?" by running the check, not from memory, and write the date.

## 6. Known gaps

- **G1-G4 from spec 001, section 6**, all come here. G1 checked again on 2026-11-19: `python -m pytest --collect-only tests/test_db.py` stops with `RuntimeError` (missing `POSTGRES_*` variables), and no tests are collected.
- **G5. Nobody knows if the migration is applied.** Not checked yet (Docker not running on 2026-11-19). Checked by AC-2.1.
- **G6. Dead code in `app/main.py:62-66`.** `CREATE EXTENSION` and `Base.metadata.create_all` are commented out. The migration does both now, so R2 says they should be deleted, not kept.
- **G7. `app/database.py` does four jobs at import time:** it reads the settings, builds the URI, creates the engine and defines `Base`. That breaks the Single Responsibility Principle, and it is the root cause of G1: the tests can't import the models (which only need `Base`) without a full Postgres configuration.
- **G8. The host `db` is hard-coded in `pg_uri`, and the `db` service publishes no port.** Alembic and psql can only connect from inside compose, and a testcontainers database (which runs on a random host port) can't be used without changing the code. The URI (or host and port) must come from settings.
- **G9. AC-3.1 has no pytest test.** Constitution section 3 asks for at least one test per criterion.
- **G10. Code that breaks constitution section 5** (in scope, see section 2):
  - `"soyadmin"` bypass: `app/main.py:138`.
  - `verify_exp: False`: `app/main.py:143`, and also `:172`, `:281` and `:379` (four places, not one).
  - JWT payload printed: `app/main.py:144`. The token expiry is also printed at `:113`.
  - Admin credentials as query parameters in `/register`: `app/main.py:480`.

## 7. Open questions

- **Q1.** `upgrade()` creates the `vector` extension, but `downgrade()` doesn't drop it. Should `downgrade()` run `DROP EXTENSION IF EXISTS vector`, or should it stay because other databases or migrations may need it?
- **Q2.** Who runs `alembic upgrade head`, and when? Today it is run by hand. Should it run when the container starts (`start.sh` or the compose `command`)? This affects Render in Phase 9.
- **Q3.** Should the test fixture create the schema with `alembic upgrade head` (which also tests the migration) or with `Base.metadata.create_all` (faster, but it doesn't test the migration)?
- **Q4.** G10 is in scope here, but it isn't about Postgres, and the constitution asks for one spec per feature. Should it stay here or get its own small spec (e.g. `002a-auth-fixes`)? Write down why.
