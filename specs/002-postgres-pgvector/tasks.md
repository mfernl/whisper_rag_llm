# 002 — Tasks

- **Spec:** `specs/002-postgres-pgvector/spec.md`
- **Issue:** #1 · **Branch:** `002-postgres-pgvector` (the pull request says `Closes #1`)
- **Last updated:** 2026-11-20

> Rules (constitution sections 3 and 4): one commit per task, test first where there is a test, and each task names the gap (G) and criterion (AC) it closes.
> A task is small enough for one session. If one grows, split it.
> Fill every `TODO`. Delete the hints (`>` lines) when the task is clear.

**Format of each task**
- **Closes:** gaps and criteria.
- **Depends on:** tasks that must be done first.
- **Steps:** what to do, in order.
- **Done when:** a check that anyone can run (a test or a command) and its expected result.
- **Commit:** the Conventional Commits message.

---

## Block A: environment

### T1. Recreate the `.venv` with Python 3.11
- **Closes:** part of G1 (spec 001: the local `.venv` is 3.10 and has no `psycopg`).
- **Depends on:** nothing.
- **Steps:** 
  - Install python3.11.9 (the last version with windows installer 64x)
  - Create the venv (py -3.11 -m venv .venv)
  - .venv\Scripts\activate
  - Install requirements from requirements.txt (py -m pip install -r requirements.txt)
- **Done when:** 
  - python --version prints Python 3.11.9.
  - python -m pip install -r requirements.txt --dry-run shows no "Would install" line, which means every pin is already satisfied.
  - python -m pip check prints "No broken requirements found.".
- **Commit:** none (the `.venv` is not in git). Why is this still a task? T1 closes part of G1: the tests can't even be collected without psycopg.

### T2. Add the test-only dependencies
- **Closes:** prepares AC-5.1.
- **Depends on:** T1.
- **Steps:** 
  - Create `requirements-dev.txt` (the name planned in ADR 0001) with `-r requirements.txt` as its first line, so one install sets up the whole `.venv`. Test-only packages stay out of `requirements.txt` because the Dockerfile installs that file into the production image.
  - Add what the tests import that `requirements.txt` doesn't have: `testcontainers[postgres]`, `pytest`, `pytest-asyncio`, `httpx` (`jiwer` already comes through `-r`).
  - Pin each one with `==` (latest from `python -m pip index versions <package>`): testcontainers 4.15.0, pytest 9.2.0, pytest-asyncio 1.5.0, httpx 0.28.1.
  - Amend the constitution: the test pins go in the section 1 table, like the runtime ones (v3.3.0, its own `docs:` commit, section 6).
  - Reinstall: `py -m pip install -r requirements-dev.txt`
  - Note for T6: in testcontainers 4.15.0, `testcontainers.postgres` is deprecated; import from `testcontainers.community.postgres`.
- **Done when:**
  - `python -m pip install -r requirements-dev.txt --dry-run` shows no "Would install" line, which means every pin is already satisfied.
  - `python -m pip check` prints "No broken requirements found.".
  - `python -W error -c "from testcontainers.community.postgres import PostgresContainer"` runs with no error and no warning.
  - `python -m pytest --version` prints `pytest 9.2.0`.
- **Commit:**
  - `docs: amend constitution to v3.3.0 (pin test-only dependencies)`
  - `build: add pinned test-only dependencies in requirements-dev.txt`

## Block B: make the database settings testable (G7, G8)

> Why first: the fixture (block C) has to point the app and Alembic at a container on a random port. Today the host `db` is hard-coded and everything runs at import time.

### T3. Read the connection URL (or host and port) from settings
- **Closes:** G8.
- **Depends on:** T1.
- **Steps:** TODO
  > Guiding questions: one variable with the whole URL, or separate host and port? What default keeps `docker compose up` working without editing `.env`? Is `.env` the only file to change? (Remember `.env` is not in git: who else needs to know the new variable?)
- **Done when:** TODO (e.g. the API still connects inside compose, and `alembic current` works from outside compose with TODO).
- **Commit:** TODO

### T4. Split `app/database.py` so the models import without a database
- **Closes:** G7, and the import part of G1.
- **Depends on:** T3.
- **Steps:** TODO
  > Guiding question: which of its four jobs (read settings, build the URI, create the engine, define `Base`) must happen at import time, and which can wait until something asks for an engine? Which SOLID principle does this fix? See the design pattern rule in CLAUDE.md section 1: is there a pattern that fits here, or is a plain function enough?
- **Done when:** `python -m pytest --collect-only tests/test_db.py` collects the tests with no `POSTGRES_*` variables set.
- **Commit:** TODO

### T5. Test AC-3.1 (missing settings)
- **Closes:** G9, AC-3.1.
- **Depends on:** T4.
- **Steps:** TODO
  > Hint: after T4, *when* is the `RuntimeError` raised: at import time or when the engine is created? AC-3.1 says "refuse to start". Does the test still match the criterion? Look up pytest's `monkeypatch.delenv`.
- **Done when:** TODO
- **Commit:** TODO

## Block C: test database (R5)

### T6. Write the testcontainers fixture in `tests/conftest.py`
- **Closes:** AC-5.1, AC-5.2, the rest of G1.
- **Depends on:** T2, T4.
- **Steps:** TODO
  > Use the two layers from our earlier talk: a session-scoped fixture (container + `alembic upgrade head`, Q3) and a function-scoped `db_session` that rolls back after each test.
  > How does Alembic get the container's URL? (`config.set_main_option`, Alembic API docs.)
  > AC-5.2: what does testcontainers do when Docker is off, and how do you make sure it errors instead of skipping?
- **Done when:** with Docker on, TODO. With Docker off, `python -m pytest -rs` shows TODO and no `SKIPPED`.
- **Commit:** TODO

### T7. Move the existing model tests to the new fixture
- **Closes:** spec 001 G1 (the tests run).
- **Depends on:** T6.
- **Steps:** TODO
  > Hint: delete the old SQLite `db_session` fixture in `tests/test_db.py`. Which tests fail now, and why? Write the reasons down, because T8-T10 fix them.
- **Done when:** TODO
- **Commit:** TODO

### T8. Restore the foreign key check
- **Closes:** spec 001 G2.
- **Depends on:** T7.
- **Steps:** TODO
- **Done when:** `test_rt_session_usuario_inexistente` TODO.
- **Commit:** TODO

### T9. Test duplicate ids
- **Closes:** spec 001 G3 (spec 001 AC-1.3).
- **Depends on:** T7.
- **Steps:** TODO
- **Done when:** TODO
- **Commit:** TODO

### T10. Use real 384-dimension vectors in the embedding tests
- **Closes:** spec 001 G4.
- **Depends on:** T7.
- **Steps:** TODO
  > Guiding question: should there also be a test that a vector of the wrong length is rejected? Which criterion would it check?
- **Done when:** TODO
- **Commit:** TODO

## Block D: the migration (R2)

> Order question: do T11-T12 before or after the tests in T13-T15? Test first (constitution section 3) says TODO.

### T11. Rename the first migration to English
- **Closes:** G11.
- **Depends on:** TODO
- **Steps:** TODO
  > Only the filename and the message change. The `revision` id `e6edc15da35a` must not change. Why? (What does the `alembic_version` table store?)
- **Done when:** `alembic history` shows TODO, and `alembic current` on the existing local database still shows `e6edc15da35a`.
- **Commit:** TODO

### T12. Drop the `vector` extension in `downgrade()`
- **Closes:** G12.
- **Depends on:** TODO
- **Steps:** TODO
  > Guiding question: in which position inside `downgrade()`? Can you drop the extension while a `Vector` column still exists?
- **Done when:** T14 passes.
- **Commit:** TODO

### T13. `test_alembic_upgrade`
- **Closes:** AC-2.1.
- **Depends on:** T6.
- **Steps:** TODO
  > Hint: how do you list tables and extensions from SQL instead of `\dt` and `\dx`? Look at SQLAlchemy's `inspect()` and the `pg_extension` catalog.
- **Done when:** TODO
- **Commit:** TODO

### T14. `test_alembic_downgrade`
- **Closes:** AC-2.2.
- **Depends on:** T6, TODO
- **Steps:** TODO
  > Careful: the session fixture already ran `upgrade head`. If this test downgrades, what happens to the tests that run after it? Options: its own container, or upgrade again at the end. Which one, and why?
- **Done when:** TODO
- **Commit:** TODO

### T15. `test_check_alembic`
- **Closes:** AC-2.3.
- **Depends on:** T6.
- **Steps:** TODO
  > Hint: `alembic check` is also available from Python (`alembic.command.check`). What does it raise when the models and migrations don't match?
- **Done when:** TODO
- **Commit:** TODO

## Block E: clean-up and manual checks

### T16. Delete the dead code in `app/main.py`
- **Closes:** G6.
- **Depends on:** TODO
- **Steps:** TODO
- **Done when:** TODO
- **Commit:** TODO

### T17. Run the manual checks with Docker
- **Closes:** G5, AC-1.1, AC-1.2, AC-4.1.
- **Depends on:** T11, T12 (so you check the final migration).
- **Steps:** the commands in spec section 5 for AC-1.1, AC-1.2 and AC-4.1, plus `alembic current` and `\dt`/`\dx` in psql for G5.
- **Done when:** every row of spec section 5 has a real result and a date.
- **Commit:** none (or part of T18). TODO: decide.

### T18. Close the spec
- **Closes:** spec-anchored rule (CLAUDE.md section 3.2: "keep the spec up to date").
- **Depends on:** all.
- **Steps:**
  - Spec 002: status, section 3 (now describes the new settings and the fixture), section 5 ("Passes today?"), section 6 (mark each gap closed with its commit).
  - Spec 001: G1-G4 closed.
  - CLAUDE.md: tick steps 4 and 6 in section 3.4.
  - TODO: anything else? (`docs/architecture.md`? `chuleta_comandos_rag_llm.md`?)
- **Done when:** TODO
- **Commit:** TODO
