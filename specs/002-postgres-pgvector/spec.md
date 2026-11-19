# 002 — PostgreSQL + pgvector + migrations

- **Status:** TODO (e.g. "Partly implemented (retroactive spec + closing tasks)")
- **Phase:** 2
- **Last updated:** TODO (YYYY-MM-DD)
- **Related:** `specs/constitution.md` (section 1 stack, section 3 testing, section 5 secrets), `specs/001-data-model/spec.md` (gaps G1-G4), `docs/architecture.md`

> Retroactive spec, like 001: it records what Phase 2 already built. Unlike 001, Phase 2 is not closed.
> What is still missing goes to "Known gaps" here and becomes a task in `tasks.md` (written after this spec).

---

## 1. Context

<!-- TODO: 2-4 sentences. Why did the project move from SQLite to PostgreSQL + pgvector?
     Hints:
     - What can't SQLite do that /ask (Phase 5) needs? Look at architecture.md section 4 ("pgvector nearest-neighbour search").
     - Why migrations (Alembic) instead of Base.metadata.create_all? Look at app/main.py:66 (commented out).
     - Link the goal of 000-vision.md that this phase serves. -->
In order to implement an /ask endpoint where users can ask about transcriptions theyve made, it was necessary to change the database to a Postgres one. Also, with pgvector we can implement vector nearest-neighbour search. With alembic we ensure that the production database is version-controlled and reversible, whereas SQLite Base.create_all() only creates missing tables and cant modify existing ones.
## 2. Scope

### In scope
<!-- TODO: list what this phase covers.
     Hints: look at compose.yaml (the `db` service), app/database.py, alembic/ and alembic/versions/.
     Does running the tests against Postgres (constitution section 3, testcontainers) belong here? CLAUDE.md says gaps G1-G4 of 001 come here. -->
- TODO

### Out of scope
<!-- TODO: what is NOT covered here, and which spec covers it.
     Hints:
     - The schema changes decided for Phase 4 (RealTimeTranscription, ADR 0002) → which spec?
     - Running the tests on GitHub Actions → which spec?
     - The code that violates constitution section 5 ("soyadmin" bypass, verify_exp: False, printed JWT, credentials in query params,
       listed in CLAUDE.md section 3.4 step 1): it was planned as "Phase 2 tasks", but is it about Postgres?
       Decide: does it go here, in its own small spec, or somewhere else? Write down why. -->
- TODO

## 3. Components

<!-- Describe WHAT each piece is and does, not its config line by line. One short block per component. -->

### 3.1 Database service
- **What it is:** TODO  <!-- Hint: which image? Is it the one pinned in constitution section 1? -->
- **Where its data lives:** TODO  <!-- Hint: the `db-data` volume. What happens to it on `docker compose down`? And on `down -v`? -->
- **How the API knows it is ready:** TODO  <!-- Hint: healthcheck + depends_on condition -->

### 3.2 Connection configuration
- **Where the settings come from:** TODO  <!-- Hint: app/database.py + .env + constitution section 5 Secrets -->
- **What happens if a setting is missing:** TODO
- **Host:** TODO  <!-- Hint: look at pg_uri in app/database.py. Can Alembic or psql connect from your Windows host with that URI, or only from inside compose? -->

### 3.3 Schema migrations
- **Tool:** TODO
- **Current revision(s):** TODO  <!-- Hint: alembic/versions/. How many are there? -->
- **Who creates the `vector` extension:** TODO  <!-- Hint: read the first line of upgrade() in the migration. This answers pending question 2 in CLAUDE.md section 2. -->
- **How the schema is applied:** TODO  <!-- Hint: who runs `alembic upgrade head`, and when? By hand, at container start, never? -->

### 3.4 Test database
- **Today:** TODO  <!-- Hint: tests/test_db.py fixture + gap G1 in spec 001 -->
- **Target:** TODO  <!-- Hint: constitution section 3 names the tool and the image -->

## 4. Requirements and acceptance criteria

<!-- Same format as 001: user story + EARS criteria with IDs.
     EARS patterns:
       - Ubiquitous:   THE SYSTEM SHALL <response>.
       - Event:        WHEN <trigger>, THE SYSTEM SHALL <response>.
       - Unwanted:     IF <unwanted condition>, THEN THE SYSTEM SHALL <response>.
     Constitution section 3: every criterion needs at least one test. Some of these can't be pytest tests
     (e.g. "compose starts"): write how they are checked instead (a command and its expected output). -->

### R1. TODO (the database starts with the system and the API waits for it)
**As** TODO, **I want** TODO, **so that** TODO.

- **AC-1.1** WHEN `docker compose up` is run, THE SYSTEM SHALL TODO.
- **AC-1.2** IF the database is not healthy yet, THEN THE SYSTEM SHALL TODO.

### R2. TODO (the schema is created only by migrations)
**As** TODO, **I want** TODO, **so that** TODO.

- **AC-2.1** WHEN `alembic upgrade head` is run on an empty database, THE SYSTEM SHALL create the `vector` extension and every table of the models.
- **AC-2.2** WHEN TODO (downgrade?), THE SYSTEM SHALL TODO.
- **AC-2.3** TODO  <!-- Hint: should the models and the latest migration always match? How would you check that? (Search: "alembic check") -->

### R3. TODO (connection settings come from the environment)
**As** TODO, **I want** TODO, **so that** TODO.

- **AC-3.1** IF TODO, THEN THE SYSTEM SHALL TODO.  <!-- Hint: app/database.py already does this. What exactly does it do? -->

### R4. TODO (data survives restarts)
**As** TODO, **I want** TODO, **so that** TODO.

- **AC-4.1** WHEN TODO, THE SYSTEM SHALL TODO.

### R5. TODO (tests run against the real database engine)
**As** TODO, **I want** TODO, **so that** TODO.

- **AC-5.1** WHEN the test suite runs, THE SYSTEM SHALL TODO.
- **AC-5.2** IF Docker is not available, THEN THE TEST SUITE SHALL TODO.  <!-- Hint: CLAUDE.md section 3.4 step 1 already decided: fail or skip? -->

## 5. Traceability

| Criterion | How it is checked (test or command) | Passes today? |
|---|---|---|
| AC-1.1 | TODO | TODO |
| AC-1.2 | TODO | TODO |
| AC-2.1 | TODO  <!-- e.g. `alembic current` + `\dt` and `\dx` in psql --> | TODO |
| AC-2.2 | TODO | TODO |
| AC-2.3 | TODO | TODO |
| AC-3.1 | TODO | TODO |
| AC-4.1 | TODO | TODO |
| AC-5.1 | TODO | TODO |
| AC-5.2 | TODO | TODO |

<!-- Fill "Passes today?" by RUNNING the check, not from memory. Write the date you checked it. -->

## 6. Known gaps

<!-- TODO: what is missing or wrong today. Each gap → one task in tasks.md.
     Hints:
     - Bring G1-G4 from spec 001 section 6 here (or reference them by ID).
     - Pending items in CLAUDE.md section 2: is the migration applied? Do the tests pass with the Vector column?
     - app/main.py:63-66: commented-out create_all and CREATE EXTENSION. Delete or keep?
     - SOLID (your rule): app/database.py reads the settings, builds the URI, creates the engine AND defines Base,
       all at import time. Which principle does that break, and is that the root cause of G1? -->
- TODO

## 7. Open questions

<!-- TODO: anything you are not sure about. Claude does the "clarify" pass on this. -->
- TODO
