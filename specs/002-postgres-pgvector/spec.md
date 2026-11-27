# 002 — PostgreSQL + pgvector + migrations

- **Status:** Partly implemented (retroactive spec + closing tasks)
- **Phase:** 2
- **Last updated:** 2026-11-19
- **Related:** `specs/constitution.md` (section 1 stack, section 3 testing, section 5 secrets), `specs/001-data-model/spec.md` (gaps G1-G4), `docs/architecture.md`

> Retroactive spec, like 001: it records what Phase 2 already built. Unlike 001, Phase 2 is not closed.
> What is still missing goes to "Known gaps" here and becomes a task in `tasks.md` (written after this spec).

---

## 1. Context

The `/ask` endpoint (Phase 6) has to find the fragments of a user's transcriptions that are closest to a question. SQLite has no vector type and no nearest-neighbour search, so the project moved to PostgreSQL with the pgvector extension, which adds a `vector` column type and distance operators such as cosine distance `<=>` (`docs/architecture.md` section 4). This phase serves the first two goals of `000-vision.md` section 4: transcriptions are stored, and a user can ask questions about them.

The schema is managed with Alembic migrations instead of `Base.metadata.create_all`. `create_all` only creates the tables that are missing; it can't change an existing table, and it keeps no history. Migrations are versioned in git, they can be reviewed by hand (constitution section 3), and they can be reverted.

## 2. Scope

### In scope
- The `db` service in `compose.yaml`: the PostgreSQL + pgvector image, a named volume for its data, and a healthcheck that the API waits for.
- Connection settings read from environment variables (`.env` locally), with a clear error when one is missing.
- The first Alembic migration: it creates the `vector` extension and every table of the models, including the `Vector(384)` column.
- Running the database tests against a real PostgreSQL + pgvector database with testcontainers, and closing gaps G1-G4 of spec 001.

### Out of scope
| Item | Where it goes |
|---|---|
| Schema changes decided in ADR 0002 (`RealTimeTranscription`, session create and close dates) | `005-ingestion` |
| Running the tests on GitHub Actions | `004-ci` |
| A vector index (HNSW or IVFFlat) for faster search | `006-ask`, when there is real data to measure |
| A managed PostgreSQL on Render, and running `alembic upgrade head` automatically before the API starts (Q2) | `010-readme-cd` |
| Code that breaks constitution section 5 (G10) | `003-security-fixes` (see Q4) |

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
- **Current revision(s):** one, `e6edc15da35a` ("initial schema", file `e6edc15da35a_initial_schema.py`; renamed from Spanish in T11, see G11). It is the first migration (`down_revision = None`) and the current head.
- **Who creates the `vector` extension:** the migration itself. The first line of `upgrade()` runs `CREATE EXTENSION IF NOT EXISTS vector`, so an empty database gets the extension from `alembic upgrade head`, not from the app.
- **How the schema is applied:** by hand. The developer runs `alembic upgrade head` inside the API container. Nothing runs it automatically.

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
- **AC-2.2** WHEN `alembic downgrade base` is run, THE SYSTEM SHALL drop every table and index that the migration created, leaving no application tables, and SHALL drop the `vector` extension.
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
| AC-2.1 | Two tests in `tests/test_db.py` on the `pg_engine` container (empty before `upgrade head`): `test_pgEngineSetup` (tables half: exactly the `models.py` tables plus `alembic_version`, shared with AC-5.1) and `test_alembic_upgrade_extensions` (extension half: `vector` is in `pg_extension`) (T13) | Yes (2026-11-27): `python -m pytest -q tests\test_db.py` with Docker on, 16 passed. Mutation check: without `CREATE EXTENSION` the `pg_engine` setup errors with `UndefinedObject` (type `vector` does not exist) |
| AC-2.2 | `test_alembic_downgrade`: after `downgrade base`, only `alembic_version` is left and `vector` is not in `pg_extension` (T14; `upgrade head` again in a `finally`) | No (2026-11-27): the tables half passes, the extension half fails because `downgrade()` doesn't drop `vector` (G12). Marked `xfail(strict=True)` until T12 |
| AC-2.3 | `test_check_alembic` | No test (2026-11-19) |
| AC-3.1 | `test_missing_postgres_var` (one variable missing, parametrized) and `test_missing_postgres_variables` (all three missing) in `tests/test_db.py`, which call `get_engine()`; `lifespan` calls it first, so the same error stops the app (T4, T5) | Yes (2026-11-23): passes with the `POSTGRES_*` variables unset and set in the shell; the mutation check (dropping the `POSTGRES_DB` check) makes two cases fail |
| AC-4.1 | Write a row, `docker compose down`, `up -d`: the row is still there. After `down -v` it is gone (expected). | Not checked (Docker not running, 2026-11-19) |
| AC-5.1 | `pg_engine` and `db_session` fixtures in `conftest.py` (repo root, T6); `test_pgEngineSetup`: after `upgrade head` the container has the `models.py` tables plus `alembic_version` | Yes (2026-11-23): `python -m pytest -rs tests\test_db.py` with Docker on, 5 passed, 6 skipped (the T7 model tests) |
| AC-5.2 | Stop Docker, run `python -m pytest -rs tests\test_db.py`: the database tests error, none is skipped | Yes (2026-11-23): `ERROR ... Docker is needed for the database tests: start Docker Desktop`, no test skipped because of Docker |

> Fill "Passes today?" by running the check, not from memory, and write the date.

## 6. Known gaps

- **G1-G4 from spec 001, section 6**, all come here. G1 checked again on 2026-11-19: `python -m pytest --collect-only tests/test_db.py` stops with `RuntimeError` (missing `POSTGRES_*` variables), and no tests are collected.
- **G5. Nobody knows if the migration is applied.** Not checked yet (Docker not running on 2026-11-19). Checked by AC-2.1.
- **G6. Dead code in `app/main.py:62-66`.** `CREATE EXTENSION` and `Base.metadata.create_all` are commented out. The migration does both now, so R2 says they should be deleted, not kept.
- **G7. `app/database.py` does four jobs at import time:** it reads the settings, builds the URI, creates the engine and defines `Base`. That breaks the Single Responsibility Principle, and it is the root cause of G1: the tests can't import the models (which only need `Base`) without a full Postgres configuration.
- **G8. The host `db` is hard-coded in `pg_uri`, and the `db` service publishes no port.** Alembic and psql can only connect from inside compose, and a testcontainers database (which runs on a random host port) can't be used without changing the code. The URI (or host and port) must come from settings.
- **G9. AC-3.1 has no pytest test.** Constitution section 3 asks for at least one test per criterion. Covered by T5 (2026-11-23).
- **G10. Code that breaks constitution section 5** (out of scope: moved to `003-security-fixes`, see Q4). Kept here so the new spec can copy the list:
  - `"soyadmin"` bypass: `app/main.py:138`.
  - `verify_exp: False`: `app/main.py:143`, and also `:172`, `:281` and `:379` (four places, not one).
  - JWT payload printed: `app/main.py:144`. The token expiry is also printed at `:113`.
  - Admin credentials as query parameters in `/register`: `app/main.py:480`.
- **G11. The existing migration is named in Spanish** (`e6edc15da35a_esquema_inicial.py`, message "esquema inicial"). That breaks constitution section 4 (everything in English, migration names included). Rename the file and change the message to English; the `revision` id `e6edc15da35a` must not change (Q5).
- **G12. `downgrade()` does not drop the `vector` extension**, so AC-2.2 fails today (Q1).

## 7. Open questions

- **Q1.** `upgrade()` creates the `vector` extension, but `downgrade()` doesn't drop it. Should `downgrade()` run `DROP EXTENSION IF EXISTS vector`, or should it stay because other databases or migrations may need it? **Answered 2026-11-19:** `downgrade()` should run `DROP EXTENSION IF EXISTS vector` because there will not be other databases that need it.
- **Q2.** Who runs `alembic upgrade head`, and when? Today it is run by hand. Should it run when the container starts (`start.sh` or the compose `command`)? **Answered 2026-11-19:** Local: by hand to get used to checking migrations. Deploy: running it automatically before the API starts (Render start command or pre-deploy) is decided in `010-readme-cd`.
- **Q3.** Should the test fixture create the schema with `alembic upgrade head` (which also tests the migration) or with `Base.metadata.create_all` (faster, but it doesn't test the migration)? **Answered 2026-11-19:** the test should create the schema with `alembic upgrade head` because it turns AC-2.1, AC-2.2 and AC-2.3 into automatic tests.
- **Q4.** G10 is in scope here, but it isn't about Postgres, and the constitution asks for one spec per feature. Should it stay here or get its own small spec (e.g. `002a-auth-fixes`)? **Answered 2026-11-19:** G10 gets its own spec, `specs/003-security-fixes/`, done after 002 and before `004-ci`. The roadmap in `000-vision.md` section 7 was renumbered (phases 3-9 became 4-10) so that numbers keep the order. Why: "one spec per feature" (CLAUDE.md section 3.2), so the security fixes get their own issue, branch and PR, and the review is not mixed with the database work.
- **Q5.** Should every migration have a name that says what it creates or changes, and what happens to the existing `e6edc15da35a` ("esquema inicial")? **Answered 2026-11-19:** every migration has a message (and filename) that describes what it creates or changes.
  - Where the rule lives: constitution section 4 (v3.1.0, a MINOR amendment because it adds a rule), because it applies to every spec that adds a migration, not only 002.
  - Existing migration: renamed in 002 (G11), because its Spanish name breaks the "everything in English" rule. Only the filename and the message change; the `revision` id stays.
