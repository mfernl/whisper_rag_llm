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
  - Create the venv `py -3.11 -m venv .venv`.
  - Activate the environment: `.venv\Scripts\activate`.
  - Install requirements from requirements.txt `py -m pip install -r requirements.txt`.
- **Done when:** 
  - python --version prints Python 3.11.9.
  - python -m pip install -r requirements.txt --dry-run shows no "Would install" line, which means every pin is already satisfied.
  - python -m pip check prints "No broken requirements found.".
- **Commit:** none (the `.venv` is not in git). Why is this still a task? T1 closes part of G1: the tests can't even be collected without psycopg.

### T2. Add the test-only dependencies
- **Closes:** prepares AC-5.1.
- **Depends on:** T1.
- **Steps:** 
  - Create `requirements-dev.txt` (the name planned in ADR 0001) with `-r requirements.txt` as its first line, so one install sets up the whole `.venv`.
  - Add what the tests import that `requirements.txt` doesn't have: `testcontainers[postgres]`, `pytest`, `pytest-asyncio`, `httpx`.
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
- **Steps:**
  - In `app/database.py`, read `POSTGRES_HOST` (default `db`) and `POSTGRES_PORT` (default `5432`).
  - Build the URL with `sqlalchemy.URL.create`, which escapes special characters in the password.
  - In `compose.yaml`, publish the `db` port on `127.0.0.1:5432:5432` only.
- **Done when:**
  - `docker compose up` with the current `.env` unchanged: the API starts and `/docs` loads.
  - In cmd, with the `.venv` active and the `POSTGRES_*` variables set plus `set POSTGRES_HOST=127.0.0.1`: `alembic current` prints the revision instead of a "could not translate host name" error.
- **Commit:** `feat(db): read database host and port from settings`

### T4. Split `app/database.py` so the models import without a database
- **Closes:** G7, and the import part of G1.
- **Depends on:** T3.
- **Background:** what `Base`, the engine, `SessionLocal` and `get_db` are, and why a lazy singleton: `docs/architecture.md` section 7.
- **Steps:**
  - Move `Base` to `app/models.py`, because defining it is the only one of the four jobs that needs no settings. Import it from there in `alembic/env.py`, `tests/test_db.py` and `tests/test_fastapi.py`.
  - In `app/database.py`, move "read settings → check them → build the URL → create the engine" into `get_engine()`. It is a lazy singleton: the first call builds the engine and keeps it in the private module variable `_engine`, and later calls return the same engine. A plain function is enough; a `Singleton` class would add code without adding behaviour.
  - Create `SessionLocal = sessionmaker()` with no bind at import time, and bind it inside `get_engine()` with `SessionLocal.configure(bind=_engine)`.
  - Call `get_engine()` first thing in `lifespan` (`app/main.py`), so the engine exists before the first `SessionLocal()` and a missing variable still stops the app at startup (AC-3.1). `alembic/env.py` takes the URL from `get_engine().url`.
  - SOLID: this fixes the Single Responsibility Principle. `models.py` changes when a table changes, and `database.py` changes when the way we connect changes.
- **Done when:**
  - `python -m pytest --collect-only tests/test_db.py` collects the 6 tests with no `POSTGRES_*` variables set.
  - `docker compose up`: the API logs `Application startup complete` and `/docs` loads.
  - In cmd, with the `POSTGRES_*` variables set plus `set POSTGRES_HOST=127.0.0.1`: `alembic current` prints `e6edc15da35a (head)`.
- **Commit:** `refactor(db): create the engine lazily and move Base to models`

### T5. Test AC-3.1 (missing settings)
- **Closes:** G9, AC-3.1.
- **Depends on:** T4.
- **Steps:**
  - In `tests/test_db.py`, create the fixture `envCred` (pytest `monkeypatch`). It resets the cached `database._engine` to `None` and sets the three `POSTGRES_*` variables to dummy values, so each test controls its own environment and doesn't depend on the shell or on an earlier test.
  - Create `test_missing_postgres_var`, parametrized over the three variables: it deletes one and checks that the `RuntimeError` from `get_engine()` names it.
  - Create `test_missing_postgres_variables`: with all three deleted, it checks that the error lists the three messages.
  - Point the skip reason of the six model tests to T7 (they need the Postgres fixture, spec 001 G1).
- **Done when:**
  - `python -m pytest -v tests\test_db.py` shows the four T5 cases as passed, both with the `POSTGRES_*` variables unset and with them set in cmd (`set POSTGRES_DB=x`, and so on).
  - Mutation check: commenting out one of the `if not ...` checks in `get_engine()` makes at least one T5 case fail.
- **Commit:** `test(db): check that missing database settings stop the engine`

## Block C: test database (R5)

### T6. Write the testcontainers fixture in `conftest.py`
- **Closes:** AC-5.1, AC-5.2, the rest of G1.
- **Depends on:** T2, T4.
- **Background:** the diagram at the top of `conftest.py`.
- **Steps:**
  - Create `conftest.py` in the **repo root** (not `tests/`), so `Path(__file__).parent` is the folder with `alembic.ini`. Run the tests from the repo root (`python -m pytest tests\...`): with no pytest config file, a root `conftest.py` is not loaded when pytest runs from `tests/`.
  - Session-scoped fixture `pg_engine`:
    1. Start `PostgresContainer("pgvector/pgvector:0.8.7-pg18-bookworm", username=..., password=..., dbname=...)`. Pass the credentials explicitly; otherwise testcontainers reads `POSTGRES_PASSWORD` and `POSTGRES_DB` from the shell.
    2. With `pytest.MonkeyPatch.context()` (the `monkeypatch` fixture is function-scoped and can't be used in a session fixture), set the five `POSTGRES_*` settings: the same credentials, `POSTGRES_HOST` from `get_container_host_ip()`, `POSTGRES_PORT` from `get_exposed_port(5432)` (the random host port mapped to the container's 5432).
    3. Reset `database._engine` to `None` and call `get_engine()`: it builds a new engine from the container settings.
    4. Run `command.upgrade(Config(<repo root>/alembic.ini), "head")`. No `set_main_option`: `alembic/env.py` takes the URL from `get_engine()`, so the app, Alembic and the tests share the container URL and nothing touches the dev database.
    5. `yield` the engine inside `MonkeyPatch.context()`. In a `finally`: `engine.dispose()` and `pg.stop()`; a teardown error becomes a `warnings.warn`, not a failure.
  - Function-scoped fixture `db_session(pg_engine)`: connection → `begin()` → `Session` bound to that connection → `yield` → close the session, roll back the transaction, close the connection.
  - No `autouse` fixture: tests that need the database ask for `db_session` (or `pg_engine`), so the T5 tests don't need Docker.
  - Delete the old SQLite `db_session` fixture from `tests/test_db.py`; the one in `conftest.py` replaces it.
  - AC-5.2: only `PostgresContainer(...)` is in a `try` (its constructor is what fails with Docker off); `except DockerException` calls `pytest.fail("Docker is needed ...", pytrace=False)`. Never `pytest.skip`.
- **Done when:**
  - With Docker on, `test_pgEngineSetup` (`pg_engine`) passes: the container has exactly the `models.py` tables plus `alembic_version`. Kept as a start for AC-2.1 (block D).
  - With Docker on, `python -m pytest -v tests\test_db.py` still shows the four T5 cases passed.
  - With Docker off, `python -m pytest -rs tests\test_db.py` shows `ERROR` with a message saying Docker is needed, and no `SKIPPED`.
  - The dev database is untouched: `alembic current` from cmd still prints `e6edc15da35a (head)`.
- **Commit:** `test(db): add a testcontainers fixture for a throwaway Postgres`

### T7. Move the existing model tests to the new fixture
- **Closes:** spec 001 G1 (the tests run).
- **Depends on:** T6.
- **Steps:**
  - Old SQLite `db_session` fixture in `tests/test_db.py` deleted in T6. Because `conftest.py` replaces the old fixture with a new one connecting to a test database.
  - Delete old `test_fastapi.py` database setup and replace it with the new fixture.
  - Organize tests from `test_fastapi.py` so they are fixed in different specs (003, 004 and 005).
  - Modify `conftest.py` in order to yield a session to the tests that creates savepoints each time the tests COMMIT/BEGIN/ROLLBACK (using `join_transaction_mode`).
  - Create test to prove `join_transaction` saves the session as it was before the tests COMMITS/ROLLBACKS.
- **Done when:** 
  - With docker on, `python -m pytest -v tests\test_fastapi.py` is collected, every test skipped with its spec.
  - With Docker on, `python -m pytest -v tests\test_db.py` passes all the tests.
- **Commit:** `test(db): organize tests and modify fixture to allow commits during tests`

### T8. Restore the foreign key check
- **Closes:** spec 001 G2.
- **Depends on:** T7.
- **Steps:**
  - Rename `test_rt_session_usuario_inexistente` to `test_rt_session_nonexistentUser`: constitution section 4 says everything is in English.
  - Keep `pytest.raises(IntegrityError)` and assert that the driver error is the foreign key one: `excinfo.value.orig.sqlstate == "23503"` (`foreign_key_violation`, `psycopg.errors.ForeignKeyViolation`). `IntegrityError` alone also covers `NOT NULL`, `UNIQUE` and `CHECK` violations.
  - Keep `db_session.rollback()` after the `with`: after a failed `commit()` the session can't be used until it is rolled back.
  - Update spec 001: the AC-3.1 row in section 5 (new test name) and gap G2 (resolved).
- **Done when:**
  - With Docker on, `python -m pytest -v tests\test_db.py` passes all the tests.
  - Mutation check: with an existing user (`user` fixture) and `session_id=None`, the commit raises a `NOT NULL` error (`23502`). The old test (only `pytest.raises(IntegrityError)`) passes, and the new one fails with `assert '23502' == '23503'`. Checked 2026-11-26.
- **Commit:** `test(db): restore foreign key check`

### T9. Test duplicate ids
- **Closes:** spec 001 G3 (spec 001 AC-1.3).
- **Depends on:** T7.
- **Steps:**
  - Create `test_duplicated_session_id`: save a real-time session with the `session_id` of the `rt` fixture and assert that the commit raises `IntegrityError` with SQLSTATE `23505` (`unique_violation`, `psycopg.errors.UniqueViolation`).
  - Create `test_duplicated_batch_id`: the same with the `batch_id` of the `btch` fixture. Give it a `context`, so the only possible error is the duplicate (without it, a `NOT NULL` error `23502` would fire instead).
  - Update spec 001: the AC-1.3 row in section 5 (new tests) and gap G3 (resolved). Also mark G1 resolved and update the AC-1.1 and AC-1.2 rows (left over from T7).
  - Give every test from T5-T9 a docstring that names the spec and criterion it checks, with a short explanation. From now on, every new test gets one.
- **Done when:**
  - With Docker on, `python -m pytest -v tests\test_db.py` passes all the tests (10 passed, 4 skipped for T10).
  - Mutation check: with a new id (`"other#1"`, `"other#B1"`) instead of the fixture's, both tests fail with `DID NOT RAISE`. The schema comes from the migration (`alembic upgrade head` in `pg_engine`), not from `models.py`, so removing `unique=True` from the model would not change the test database. Checked 2026-11-27.
- **Commit:** `test(db): reject duplicate session and batch ids`

### T10. Use real 384-dimension vectors in the embedding tests
- **Closes:** spec 001 G4.
- **Depends on:** T7.
- **Steps:**
  - Add a module-level constant `VECTOR_384 = [0.1] * 384` in `tests/test_db.py`: a plain Python list is a valid value for `Vector(384)` ([pgvector-python, SQLAlchemy](https://github.com/pgvector/pgvector-python#sqlalchemy)). The column is already declared in `app/models.py`; the tests only pass a value.
  - Use it in the four embedding tests (spec 001 AC-2.1 to AC-2.4) and remove their `skip` markers. Use the `rt` and `btch` fixtures directly instead of querying them again.
  - In the two "rejected" tests, assert SQLSTATE `23514` (`check_violation`) and `diag.constraint_name == "check_one_source"`. With `"asdfg"`, pgvector-python raised `StatementError` before the query reached Postgres, so the old tests never tested the CHECK constraint.
  - Add spec 001 AC-2.5 (wrong length rejected) and `test_embedding_wrongDimension`: pgvector raises `DataError`, SQLSTATE `22000` (`data_exception`), message `expected 384 dimensions, not 3`. It is a `DataError`, not an `IntegrityError`.
  - Remove `db_session.rollback()` from tests that don't use the session after the failed commit: the `db_session` fixture closes the session and rolls back the outer transaction. Keep it in `test_session_joinTransaction`, which queries afterwards. (This changes the T8 step "keep `db_session.rollback()`".)
  - Translate the test texts and the comment `# si falla, el test falla` to English (constitution section 4).
  - Docstrings with spec and criterion (constitution section 3, v3.4.0). Update spec 001: AC-2.5, the AC-2.x rows in section 5, and G4 (resolved).
- **Done when:**
  - With Docker on, `python -m pytest -v -rs tests	est_db.py`: 15 passed, 0 skipped.
  - Mutation checks (checked 2026-11-27), each one goes red:
    - AC-2.1 with `text=None`: `assert '23502' == '23514'` (another integrity error doesn't make it pass).
    - AC-2.2 with a `batch_id`: `DID NOT RAISE IntegrityError`.
    - AC-2.3 with a vector of length 3: `DataError` on commit.
    - AC-2.4 with the `session_id` of a session that doesn't exist: `IntegrityError` (foreign key) on commit.
    - AC-2.5 with `VECTOR_384`: `DID NOT RAISE DataError`.
- **Commit:** `test(db): use real 384-dimension vectors in the embedding tests`

## Block D: the migration (R2)

> Order (decided 2026-11-27): T11 → T13 → T14 → T12 → T15. T11 changes no behaviour, so it needs no test first. T12 does change behaviour, so by test first (constitution section 3) T14 is written first and fails, and T12 makes it pass.

### T11. Rename the first migration to English
- **Closes:** G11.
- **Depends on:** nothing.
- **Steps:**
  - `git mv` the file from `e6edc15da35a_esquema_inicial.py` to `e6edc15da35a_initial_schema.py` (lowercase, like the slug Alembic generates from the message).
  - Change the first line of its docstring (the message) from `esquema inicial` to `initial schema`.
  - Leave `revision = 'e6edc15da35a'` alone: `alembic_version` stores only that id, and Alembic finds the script by the `revision` variable, not by the filename.
  - Delete `alembic/versions/__pycache__` so no stale `.pyc` of the old name is left.
  - Update the references that describe the current state (spec 002 section 3.3, CLAUDE.md section 2). The gap G11 and Q5 text stays as history.
- **Done when:**
  - `alembic history` shows `<base> -> e6edc15da35a (head), initial schema`.
  - `alembic current` on the existing local database still shows `e6edc15da35a (head)`.
  - `python -m pytest -v tests\test_db.py` still gives 15 passed (the fixture runs `upgrade head` with the renamed file).
- **Commit:** `refactor(alembic): rename the first migration to English`

### T12. Drop the `vector` extension in `downgrade()`
- **Closes:** G12.
- **Depends on:** T14.
- **Steps:** 
  - Add to `downgrade()` in `alembic/versions/e6edc15da35a_initial_schema.py`: `op.execute("DROP EXTENSION IF EXISTS vector")` (add to the bottom of the method).
- **Done when:** T14 passes.
- **Commit:** `alembic(): drop vector extension when downgrade()`

### T13. `test_alembic_upgrade_extensions`
- **Closes:** AC-2.1.
- **Depends on:** T6.
- **Steps:**
  - Split AC-2.1 in two, so nothing is checked twice. The tables half is already `test_pgEngineSetup` (T6, `inspect().get_table_names()`), and its docstring now names AC-2.1 as well as AC-5.1. The extension half is a new test, `test_alembic_upgrade_extensions(pg_engine)`, which queries `pg_extension` for `extname = 'vector'`.
  - `pg_engine` and not `db_session`: the test only reads the catalog, so it needs no session or rollback.
  - "Empty database" comes from the fixture: the container is new for every run and has no volume (conftest step 1).
  - Update spec 002 section 5, the AC-2.1 row (both test names).
- **Done when:**
  - `python -m pytest -v tests\test_db.py` with Docker on: 16 passed (checked 2026-11-27).
  - Mutation check (2026-11-27): commenting out `CREATE EXTENSION` in `upgrade()` goes red, but as an ERROR in `pg_engine` setup, not a FAIL in this test: `upgrade head` stops at the `trcpt_embedding` table with `UndefinedObject` (type `vector` does not exist), so every test that uses the container errors. The extension is required by the schema itself.
- **Commit:** `test(db): check that upgrade head creates the vector extension`

### T14. `test_alembic_downgrade`
- **Closes:** AC-2.2.
- **Depends on:** T6, T13.
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
