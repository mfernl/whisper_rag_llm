# CLAUDE.md — whisper_rag_llm

> Claude Code loads this file at the start of every session. It explains **how we work** and **where to pick up**.
> Last updated: 2026-11-27.

---

## 1. How Claude has to work in this project

### Mentoring (rules inherited from `instrucciones.txt`)
- **Everything in English (decided 2026-11-16)**: conversations, code, commits, specs and docs. Answer step by step.
- **No `§` sign (decided 2026-11-19)**: write "section N" (e.g. "constitution section 5"), because Marco can't type `§` on his keyboard.
- **English practice**: point out Marco's *big* grammar or spelling mistakes (briefly, at the start of the reply, with the corrected phrase). Ignore small slips.
- **Don't give the full solution.** Give hints, guiding questions, skeletons with gaps (`TODO`) and criteria to check the result. If Marco asks "do X for me", give him a skeleton with hints.
- Diagnose from the code and the output Marco pastes, and point him to where he has to look.
- **Design patterns + SOLID (requested 2026-11-17)**: when a new feature starts (at the `plan.md` step, from Phase 5 on), suggest one or more architecture or design patterns that fit (e.g. factory, singleton, strategy, repository, dependency injection), explaining *why* each one fits and linking a source. Say so when no pattern is needed, and don't force one in. Also remind Marco to check his plan against the SOLID principles, and point out the principles that matter for that feature.
- The LangChain, LangGraph and RAGAS APIs change fast: **check the current documentation** before guiding him through those phases.
- Environment: Windows, **cmd.exe**, venv in `.venv`, **Python 3.11.9** (recreated 2026-11-20, spec 002 T1; packages match the pins in `requirements.txt`, torch is the CPU build). The Dockerfile uses `python:3.11-slim-bookworm` (3.11.18): 3.11.9 is the last 3.11 release with a Windows installer, so the patch version differs on purpose.

### Always cite sources (Marco's explicit request)
- Every claim about **how SDD works** (or any technique or tool) must come with its **source and link**.
- Every proposal about **how Marco should work** must explain **why** and where it comes from.
- When a recommendation is **Claude's own judgment** and doesn't come from a source, say so, with the reasoning.
- The base references are in section 5.

---

## 2. Current state (2026-11-19)

**Development is PAUSED.** Before continuing, Marco wants to move the project to an **SDD (Spec-Driven Development)** workflow. The plan is in section 3.

- Detailed context from earlier sessions is in `instrucciones.txt` (ignored by git and **out of date**: it says Phase 2 hasn't started). `razonamiento.md` explains why SQLAlchemy is kept, and `chuleta_comandos_rag_llm.md` is the command cheat sheet (both ignored by git, in Spanish).
- **Phase 1 (data model and tests): closed.** Models `RealTimeSession`, `BatchTranscription` and `TranscriptionEmbeddings`, with the `check_one_source` `CheckConstraint`. There are 6 tests in `tests/test_db.py` against in-memory SQLite (they can't run today: see gap G1 in `specs/001-data-model/spec.md`). Spec: `specs/001-data-model/spec.md`.
- **Phase 2 (Postgres + pgvector + Alembic): almost closed.** Last Phase 2 code commit: `75c39fe`. The `db` service is in compose with a volume and healthcheck, `pg_uri` reads the `.env`, the column is `Vector(384)` and the migration `alembic/versions/e6edc15da35a_initial_schema.py` exists (renamed from `esquema_inicial` in spec 002 T11). `create_all` and `CREATE EXTENSION` are commented out in `main.py`.
  Pending (with guiding questions, without giving the solution):
  1. Is the migration applied? Check with `alembic current`, and with `\dt` and `\dx` in psql.
  2. With an empty DB (after `down -v`), who creates the `vector` extension? Does the migration create it?
  3. Do the tests still pass on SQLite now that there is a `Vector` column? Should they run against Postgres? (See gaps G1-G4 in spec 001.)
- **Remaining phases** (reordered 2026-11-16, renumbered 2026-11-19 to insert the security fixes; see `specs/000-vision.md` section 7): 3 security fixes (`003-security-fixes`, gap G10 of spec 002), 4 CI (GitHub Actions + `requirements-dev.txt` + exclude GPU tests), 5 storage and ingestion (time-window chunking + sentence-transformers), 6 `/ask` endpoint with citations, 7 LangGraph agent (tools `search_transcript` and `query_metadata`), 8 RAGAS evaluation, 9 worker + multi-service compose, 10 README + CD to Render.

---

## 3. Plan: move to SDD, then resume

### 3.1 What SDD is (summary with sources)
- The **spec is the source of truth**. Code, tests and docs come from it, and every change starts by changing the spec. [Allstacks], [Allegro]
- There are three levels: *spec-first* (the spec is written before coding), *spec-anchored* (the spec is kept alive afterwards) and *spec-as-source* (only the spec is edited; not practical yet). [Böckeler], [InfoWorld]
- The reference workflow is similar in the two main tools. **GitHub Spec Kit**: constitution → specify → clarify → plan → tasks → analyze → implement [Augment], [CodeMySpec-SK], [Bitovi]. **Kiro**: `requirements.md` (criteria in EARS notation) → `design.md` → `tasks.md` [Kiro], [CodeMySpec-Kiro].

### 3.2 Good practices we adopt and why

| Practice | Why | Source |
|---|---|---|
| Separate the **what** (spec) from the **how** (plan and tasks) | The spec is stable and the plan can be thrown away. Mixing them causes confusion and makes incremental work harder | [Allegro] |
| Have a **constitution** with the shared principles | Standards aren't repeated in every spec and stay consistent | [Allegro], [Augment], [Bitovi] |
| One **spec per feature or phase**, not one monolithic document | It fits better in the agent's context and is easier to maintain | [Allegro], [Osmani] |
| **Verifiable acceptance criteria** in EARS notation (WHEN/IF … THE SYSTEM SHALL …) | They remove ambiguity and can be turned directly into tests | [Kiro], [CodeMySpec-Kiro] |
| **Small tasks**, linked to a criterion and small enough for one session | Big, vague tasks don't go well with a limited context | [Allegro], [Kilo], [CodeMySpec-Kiro] |
| **Tests as the feedback loop** (test first) | They give the agent, and Marco, a concrete target to check | [Allegro] |
| **Iterate** on the spec, without too little or too much detail | A vague spec leaves too much to interpretation, and an over-detailed one ends up as code in prose | [Allegro], [Osmani], [Intent] |
| **Keep the spec up to date** (spec-anchored) | A spec that drifts from the code stops being useful | [Intent], [Allegro] |
| **Match rigour to risk**: no spec for trivial changes | For trivial tasks SDD costs more work than it saves | [Allegro] |
| **Human review**, ideally in a new session with no previous context | A clean session catches what the original one missed. The final responsibility is the person's | [Allegro] |

### 3.3 Adaptation decisions (Claude's own judgment, with reasoning)
- **SDD by hand, without installing Spec Kit or Kiro.** In Spec Kit the agent generates the specs [Augment], [Bitovi], which clashes with the mentoring rule of not giving solutions. Writing them by hand makes Marco think through the requirements, which is exactly what he wants to learn. *Can be revisited if he wants to try the tool.*
- **Spec-anchored level.** Spec-as-source isn't practical yet [Böckeler], [InfoWorld], and plain spec-first lets the spec go stale [Intent].
- **Split of roles.** Marco writes the spec, the plan and the tasks. Claude does *clarify* and *analyze* (questions about ambiguities and checking consistency between spec and plan), which are Spec Kit steps [Augment], and gives hints during implementation.
- **The Phase 1 and 2 specs are retroactive and short.** That work is already done; documenting it gives traceability (criterion → test), not a redesign.

### 3.4 Migration steps (in order)
- [x] 0. Create this `CLAUDE.md`.
- [x] 1. Create `specs/constitution.md` (written by Marco with guiding questions from Claude). **Done 2026-11-16.** v1.0.0 adopted; v1.1.0 adds pinned stack versions (from the image; also pinned in `requirements.txt`, and torch in the `Dockerfile`); v2.0.0 switches to one issue/branch/PR per spec + CI gate (ADR `docs/decisions/0001-branch-per-spec-and-ci.md`); v3.0.0 (2026-11-17) redefines section 5 Persistence (ADR 0002, see step 9); v3.1.0 (2026-11-19) adds the migration naming rule to section 4 and updates the phase numbers; v3.2.0 (2026-11-20, Marco's decision) applies issue/branch/PR per spec from spec 002 on instead of waiting for CI (note added to ADR 0001); v3.3.0 (2026-11-20, Marco's decision) adds the pinned test-only dependencies to section 1 (`requirements-dev.txt`). v3.4.0 (2026-11-27, Marco's decision) adds to section 3 that every test has a docstring naming the spec and criterion it checks.
  - Still TODO in section 1: sentence-transformers version (Phase 5) and LLM provider and model (after Marco's research).
  - Note: the local `.venv` (3.10.11) had different versions (e.g. FastAPI 0.142.2, SQLAlchemy 2.0.54). **Done 2026-11-20:** recreated with 3.11.9 from the pinned `requirements.txt` (spec 002 T1).
  - Code that violates section 5, moved on 2026-11-19 from Phase 2 to its own spec `003-security-fixes` (spec 002 gap G10): `"soyadmin"` bypass (`app/main.py:138`), `verify_exp: False` (`:143`), JWT payload printed (`:144`), admin credentials as query params in `/register` (`:480`).
  - Open risk: measure whether torch + Whisper tiny + MiniLM fit in 512 MB (propose it as one of the first Phase 4 (CI) tasks).
  - For the Phase 2 `tasks.md`: the testcontainers fixture must fail, not skip, when Docker isn't available.
- [x] 2. Create `specs/000-vision.md`: goal, scope, non-goals. **Done 2026-11-16.** Problem/Solution split, goals, non-goals, success criteria, 9-phase roadmap, 10 phases since 2026-11-19 (storage of transcriptions goes at the start of Phase 5). Risks to check in the Phase 9-10 specs: Render's free tier may not offer background workers, free Postgres has a limited lifetime, and Render doesn't run Docker Compose (Blueprint `render.yaml`).
- [x] 3. Create `specs/001-data-model/spec.md`, retroactive. **Done 2026-11-17** (commit `6acad57`; Marco's draft, corrected and completed by Claude). Q2 and Q4 in section 7 are left for `005-ingestion`. Gaps G1-G4 become tasks of `002`.
- [x] 4. Create `specs/002-postgres-pgvector/spec.md` and `tasks.md`, with the pending items from section 2 and gaps G1-G4 of spec 001 as tasks. **In progress (2026-11-19):** `spec.md` filled in by Marco, Q1-Q5 answered (gaps G11 rename the migration, G12 `downgrade()` drops `vector`). Spec committed (`afc129f`, constitution v3.1.0 in `0feadc0`). `tasks.md` skeleton (T1-T18, blocks A-E, with `TODO`s and hints) created by Claude on 2026-11-19, **not committed yet**. Decided 2026-11-20: issue #1, branch `002-postgres-pgvector` (pushed); commit the skeleton on that branch after Claude's analyze pass on `Closes`/`Depends on` (every gap and AC has a task, the order works); then fill in each task's TODOs just before doing it, and commit the `tasks.md` update together with that task. No `plan.md` for this retroactive spec.
- [ ] 5. Turn `razonamiento.md` into an ADR in `docs/decisions/` (next number: 0003) and decide what to do with `instrucciones.txt` (move what is still valid into `specs/`).
- [ ] 6. Close Phase 2 following its `tasks.md`. **In progress:** skeleton committed 2026-11-20 (`d473c13`) on branch `002-postgres-pgvector`, issue #1. Done: T1 (`.venv` with Python 3.11.9, `0f60e28`), T2 (`requirements-dev.txt`, `b38c315`; constitution v3.3.0 in `7787cde`), T3 (`POSTGRES_HOST`/`POSTGRES_PORT` with defaults `db:5432`, `URL.create`, db port published on `127.0.0.1:5432`, `ebff75e`; written by Claude at Marco's request, overriding the mentoring rule for this task only). Outside compose use `POSTGRES_HOST=127.0.0.1`, not `localhost` (`::1` is tried first and hangs). `alembic current` from outside showed `e6edc15da35a (head)`, so pending item 1 in section 2 is answered: the migration is applied. Marco decided not to have a `.env.example`. T4 (`Base` moved to `app/models.py`, lazy `get_engine()` in `app/database.py`, `SessionLocal` bound inside it, `lifespan` calls `get_engine()` first; explained in `docs/architecture.md` section 7). Marco wrote the T4 code with hints; Claude wrote the T4 entry in `tasks.md` and the commit at his request. If uvicorn's reloader gets stuck after a failed startup, run `docker compose restart server_fastAPI`. T5 (`37a9158`, 2026-11-23): tests for AC-3.1 in `tests/test_db.py`. The `envCred` fixture (monkeypatch) resets `database._engine` to `None` and sets dummy `POSTGRES_*` values; `test_missing_postgres_var` (parametrized) and `test_missing_postgres_variables` call `get_engine()`. They pass with the shell variables set or unset, and the mutation check goes red. Marco dropped `python-dotenv` (no `.env` loading in tests). The six model tests are skipped with reason "T7: needs the Postgres fixture" (on SQLite, `embedding="asdfg"` fails in the `Vector` column). T6 (`87c0310`, 2026-11-23): `conftest.py` in the **repo root** (run tests from the root; from `tests\` pytest doesn't load it, no pytest config file). `pg_engine` (session) starts `pgvector/pgvector:0.8.7-pg18-bookworm`, sets the five `POSTGRES_*` with `MonkeyPatch.context()`, resets `_engine`, runs `alembic upgrade head` through `get_engine()` (no `set_main_option`); `db_session` (function) rolls back per test. Docker off → `pytest.fail("Docker is needed ...")`. Marco wrote the fixture with hints; Claude wrote the `try/except/finally` structure and the set-based `test_pgEngineSetup` at his request. T6 "Done when" 4 (`alembic current` on the dev DB still `e6edc15da35a (head)`) checked 2026-11-27. **T7 done** (`48dfd39`, 2026-11-25): `db_session` uses `join_transaction_mode="create_savepoint"` (the new `test_session_joinTransaction` goes red without it); `test_db.py` 8 passed, 4 skipped (T10). `test_fastapi.py` is collected and all 32 tests are skipped with the spec that fixes them. `test_rt_session_usuario_inexistente` was turned on in T7; **T8 done** (`169b14f`, 2026-11-26): renamed to `test_rt_session_nonexistentUser`, keeps `pytest.raises(IntegrityError)` and asserts `excinfo.value.orig.sqlstate == "23503"`; mutation check (`session_id=None` → `23502`) goes red; spec 001 AC-3.1 row and G2 updated. Leftovers in `test_fastapi.py` from Claude's review (not blocking): put `@pytest.mark.asyncio` back next to the skips; say *why* in the skip reasons; re-check the spec of the `soyadmin` tests (`test_appstatus`, `test_appstatistics`, `test_upload_notWavFile` → 003?) and of `test_word_error_rate` (GPU → 004?). Remember `-r` needs letters (`-rs`), otherwise it eats the path and pytest collects everything. **T9 done** (`336beca`, 2026-11-27): `test_duplicated_session_id` and `test_duplicated_batch_id` assert SQLSTATE `23505`; mutation check (new id → `DID NOT RAISE`) goes red. The unique constraints come from the migration, not `models.py`, so mutating the model proves nothing. Every T5-T9 test now has a docstring "Spec NNN AC-x.y: ..." (Marco's rule from now on). Spec 001 G1 and G3 marked resolved. `test_db.py`: 10 passed, 4 skipped (T10). **T10 done** (`6e1ac0a`, 2026-11-27): `VECTOR_384 = [0.1] * 384` (plain list), skips removed, rejection tests assert `23514` + `check_one_source`; new spec 001 AC-2.5 + `test_embedding_wrongDimension` (`DataError`, `22000`). `rollback()` after a failed commit is left to the fixture unless the test reuses the session. `test_db.py`: 15 passed, 0 skipped. **T11 done** (`20d5f8c`, 2026-11-27): migration renamed to `e6edc15da35a_initial_schema.py`, message `initial schema` (lowercase like Alembic's own slug), revision id unchanged; `alembic history`, `alembic current` (dev DB, `e6edc15da35a (head)`, which also closes T6 "Done when" 4) and the 15-passed run all checked by Marco. Order decided for block D: T13 → T14 (red) → T12 (green) → T15 (written in `tasks.md`). The T12 commit message (`alembic():`) still needs a Conventional Commits type. **Next: T13** (`test_alembic_upgrade`, AC-2.1; already started).
- [ ] 7. Phase 3 — security fixes: `specs/003-security-fixes/` (spec 002 gap G10). Issue + branch `003-security-fixes` + PR (constitution v3.2.0 section 4; no CI gate yet).
  - Also for 003 (added 2026-11-25, from the T7 split): the auth and session tests in `tests/test_fastapi.py` (skipped "spec 003"). Open points: the API tests can't see the `user` fixture's data (pick `dependency_overrides[get_db]` once `main.py` uses `Depends(get_db)`, or a committing fixture with cleanup); tests without a DB fixture depend on test order (`SessionLocal` unbound); no fixtures for `gyarados` and admin `Marco`. Also `SECRET_KEY` comes from `subprocess.run(["openssl", ...])` at **import time** (`app/main.py:30`): it breaks collection where `openssl` isn't on PATH (check `where openssl` in cmd); consider reading it from the environment (constitution section 5). Decide `collect_ignore` vs `importorskip` for `test_fastapi.py` until then.
  - Also for 003 (added 2026-11-22, Marco's decision; not a section 5 violation, so the spec's title or scope may need to say "and session handling"): **make session handling consistent in `app/main.py`.** Today there are three patterns: `Depends(get_db)` in the endpoints (`:480`, `:502`, `:622`, `:654`); `next(get_db())` by hand in the token check (`:149`) and `comprueboadmin` (`:600`), where the generator's `finally` never runs; and `SessionLocal()` directly in `lifespan` (`:69`) and in the word-detection loops of `/broadcast` and `/upload` (`:272`, `:370`), which open one session per segment with no `try/finally`. Rule to apply: `Depends(get_db)` in endpoints, `with SessionLocal() as db:` outside a request. Related bug: in `lifespan`, `db.close()` (`:77`) is inside the `if` and `db` is used again afterwards. Background: `docs/architecture.md` section 7. (Line numbers as of `ebff75e`.)
- [ ] 8. Phase 4 — CI: `specs/004-ci/`. GitHub Actions running the suite on push/PR (testcontainers works on GitHub's Ubuntu runners), install `requirements-dev.txt` (created and pinned in spec 002 T2; constitution v3.3.0), exclude/rewrite GPU tests in `tests/test_fastapi.py`. From here on, PRs also need green CI to merge (constitution section 3).
- [ ] 9. **Resume development**: Phase 5 (storage and ingestion) with the full flow: issue + branch `005-ingestion` → `spec.md` → clarify → `plan.md` → analyze → `tasks.md` → implement (test first, one commit per task) → update the spec → PR with green CI → merge.
  Decisions already made for the `005-ingestion` spec (NOT implemented yet):
  - 2026-11-16: `batch_transcription` gets the date+time the request was received.
  - 2026-11-17 (ADR `docs/decisions/0002-store-each-realtime-request.md`, commit `f57f946`): new table `RealTimeTranscription`, N:1 to `RealTimeSession`, with `id` (PK), `session_id` (FK), received date-time and Whisper's full output (segments included). `RealTimeSession` keeps only `session_id`, `username`, create and close dates (its JSON `transcription` and `exp_date` go away). **Each `/broadcast` writes its row immediately.**
  - Still open: inactivity expiry after a restart (derive it from the last received time?), replacing the in-memory token check with `username`, when ingestion runs (at close or per request), JSONB vs JSON, timestamptz in UTC, how embedding `start_time`/`end_time` relate to request times, bug `timedelta(RTSESSION_EXP)` = days in `/broadcast` (`app/main.py:234`).
  - When 005 is done, update `001` and `docs/architecture.md` section 2 (constitution section 3).

  Decisions already made for the `010-readme-cd` spec (NOT implemented yet):
  - 2026-11-19: **`alembic upgrade head` runs automatically before the API starts, and IF it fails THEN the API SHALL NOT start.** Marco's decision. The idea is to chain the two commands with `&&`, so uvicorn starts only when Alembic exits with 0.
    - Locally: in the compose `command` of `server_fastAPI` (today `uvicorn ...` only). **Decided 2026-11-19: the compose change waits for 010.** Spec 002 keeps "by hand" (its Q2), so 002 has no task for it.
    - On Render: Render doesn't run Docker Compose, so the same chain goes in the service's Docker Command (start command). The pre-deploy command is the cleaner option but it's paid only ([Render changelog](https://render-www.onrender.com/changelog/predeploy-command)). Don't migrate inside `docker build`: the database password would have to be a build arg and could stay in the image layers, which breaks constitution section 5 ([Render community](https://community.render.com/t/release-command-for-db-migrations/247)).
    - Why it's safe: there's only one instance on the free tier, so there's no migration race. `upgrade head` on an up-to-date database is a no-op (it runs on every wake-up after spin-down). On PostgreSQL, a failed migration is rolled back by the transaction in `alembic/env.py` (`context.begin_transaction()`).
    - How to check success (candidates for 010 criteria): Alembic's exit code in the logs; `alembic current` == `alembic heads`; a Render health check path (if it fails, the previous deploy keeps running, see https://render.com/docs/deploys#zero-downtime-deploys, check that this also applies to the free tier). Idea: `/health` also compares the database revision with the code's head.
    - If a migration fails: fail fast (no API start), keep the old version serving, and fix forward with a new migration. Never edit an applied one. Write migrations with expand/contract so old and new code both work ([Fowler, ParallelChange](https://martinfowler.com/bliki/ParallelChange.html)).

Target structure:
```
CLAUDE.md
specs/constitution.md
specs/000-vision.md
specs/NNN-name/{spec.md, plan.md, tasks.md}
docs/architecture.md
docs/decisions/NNNN-title.md
.github/workflows/
```

**At the start of the next session:** remind Marco which step of section 3.4 he is on and propose continuing with the first unchecked step. When each step is finished, tick its box and update the date at the top of this file.

---

## 4. Useful commands
See `chuleta_comandos_rag_llm.md`. Tests: `python -m pytest -v tests\test_db.py` (in cmd, with the `.venv` activated).

---

## 5. References
- [Böckeler] B. Böckeler, *Understanding Spec-Driven-Development: Kiro, spec-kit, and Tessl*, martinfowler.com (Oct 2025): https://www.martinfowler.com/articles/exploring-gen-ai/sdd-3-tools.html
- [Allegro] K. Piechna, *Spec-driven development best practices*, Allegro Tech Blog (Jun 2026): https://blog.allegro.tech/2026/06/spec-driven-development-best-practices.html
- [Osmani] A. Osmani, *How to write a good spec for AI agents*: https://addyosmani.com/blog/good-spec/
- [Intent] *Best Practices for Spec-Driven Development*, intent-driven.dev: https://intent-driven.dev/knowledge/best-practices/
- [Allstacks] *Spec-driven development*, Allstacks: https://www.allstacks.com/blog/spec-driven-development
- [Kilo] *Spec-Driven Development pattern*, Kilo: https://path.kilo.ai/introduction/patterns/spec-driven-development/
- [Kiro] *Specs — concepts*, official Kiro documentation: https://kiro.dev/docs/specs/concepts
- [CodeMySpec-Kiro] *Kiro Specs Explained: EARS, Spec Mode, and the Trade-offs*: https://codemyspec.com/blog/kiro-specs-explained
- [CodeMySpec-SK] *GitHub Spec Kit: How It Works and When to Use It (2026)*: https://codemyspec.com/blog/github-spec-kit-guide
- [Augment] *GitHub Spec Kit practical guide (SDD workflow)*: https://www.augmentcode.com/guides/github-spec-kit-practical-guide-sdd-workflow
- [Bitovi] *Spec Kit — Analysis*, Bitovi wiki: https://wiki.at.bitovi.com/wiki/spaces/AIEnabledDevelopment/pages/1799847940/Spec+Kit+-+Analysis
- [InfoWorld] M. Heller, *Four cutting-edge tools for spec-driven development*: https://infoworld.com/article/4171332/four-cutting-edge-tools-for-spec-driven-development.html
- Official Spec Kit repository (check the current command names before citing them): https://github.com/github/spec-kit
