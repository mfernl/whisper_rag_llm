# conftest.py (repo root)
# pytest loads this file before any test, so every fixture defined here can be used
# by any test file without importing it (spec 002 T6, AC-5.1 and AC-5.2).
# It lives in the repo root so Path(__file__).parent is the folder with alembic.ini.
#
# How it works:
#
#   pg_engine (scope="session", runs ONCE per pytest run)
#     1. start a throwaway pgvector container  ~ the "db" service of compose.yaml,
#        but with no volume, and a random host port:
#             127.0.0.1:<random>  ->  container:5432
#     2. point the app's settings (POSTGRES_*) at it with MonkeyPatch.context()
#     3. reset database._engine, so get_engine() builds a NEW engine from those settings
#     4. alembic upgrade head: alembic/env.py also calls get_engine(),
#        so the app, Alembic and the tests all use the SAME container URL
#     5. yield the engine -> the tests run
#     6. teardown: put the settings back, dispose the engine, stop and delete the container
#        (errors here -> warning, not a failure)
#   Docker off -> ERROR "Docker is needed..." (pytest.fail), never SKIPPED (AC-5.2).
#
#   db_session (function scope, runs once PER TEST)
#     connection -> BEGIN -> Session bound to that connection -> test -> ROLLBACK
#     so every test starts with empty tables.
#
#   Why get_engine() and not a URL of my own: get_engine() has no database written in it,
#   it builds whatever URL the POSTGRES_* settings describe (dev .env or this container).

import pytest
from testcontainers.community.postgres import PostgresContainer
from alembic import command
from alembic.config import Config
from app import database
from sqlalchemy.orm import sessionmaker
from pathlib import Path
from docker.errors import DockerException
import warnings
from app.models import User, RealTimeSession, BatchTranscription
from app.security import hash_password



# Starts the test database, migrates it and gives the tests an engine pointing at it.
@pytest.fixture(scope="session")
def pg_engine():
    # The same values go to BOTH sides: the container CREATES this account and database
    # on its first start, and get_engine() LOGS IN with them. Passing them explicitly
    # stops PostgresContainer from reading my shell's POSTGRES_PASSWORD / POSTGRES_DB.
    puser = 'Ivern'
    ppwsd = 'mawOfMalmortius'
    pdb = 'rift'

    # 1) Docker check (AC-5.2). Creating PostgresContainer already connects to the Docker
    #    daemon (DockerClient() in testcontainers' __init__), so THIS is the line that fails
    #    when Docker is off. Only this line is in the try: any other DockerException
    #    (e.g. the image can't be pulled) must keep its own message.
    try:
        pg = PostgresContainer('pgvector/pgvector:0.8.7-pg18-bookworm',
                               username=puser,
                               password=ppwsd,
                               dbname=pdb)
    except DockerException as e:
        # pytest.fail -> ERROR with my message, never SKIPPED. pytrace=False hides the traceback.
        pytest.fail(f"Docker is needed for the database tests: start Docker Desktop. ({e})",
                    pytrace=False)

    # 2) Setup + tests + teardown. Setup errors (migration, login, image...) are NOT caught:
    #    pytest shows them as they are. The finally always cleans up, even if setup failed.
    engine = None
    try:
        pg.start()
        # MonkeyPatch.context() and not the monkeypatch fixture: that one is function-scoped,
        # and a session fixture can't use it (ScopeMismatch). Everything set here is undone
        # when the "with" ends, so the yield must stay inside it.
        with pytest.MonkeyPatch.context() as mp:

            mp.setenv('POSTGRES_USERNAME', puser)
            mp.setenv('POSTGRES_PASSWORD', ppwsd)
            mp.setenv('POSTGRES_DB', pdb)
            mp.setenv('POSTGRES_HOST', pg.get_container_host_ip())

            # I give the port INSIDE the container (Postgres always listens on 5432)
            # and get back the random HOST port Docker mapped it to. setenv needs a str.
            port = str(pg.get_exposed_port(5432))
            mp.setenv('POSTGRES_PORT', port)

            mp.setattr(database, "_engine", None) # Reset engine to create a new one using the test credentials

            engine = database.get_engine()

            # Same as "alembic upgrade head" in cmd. No set_main_option here: env.py takes the
            # URL from get_engine(), which already points at the container.
            config = Config(Path(__file__).parent / "alembic.ini")
            command.upgrade(config, "head")

            yield engine                      # the tests run here

    finally:
        # 3) Teardown. A failure here can't change any test result (they already ran),
        #    so it's reported as a warning in pytest's "warnings summary" (visible without -s)
        #    instead of hiding a setup error or turning a green run red.
        try:
            if engine is not None:
                engine.dispose()              # close the pool before the container stops
            pg.stop()                         # remove the container (what the "with" did before)
        except Exception as exc:
            warnings.warn(f"Teardown of the test database failed: {exc!r}")

# Gives each test its own session inside a transaction that is always rolled back,
# so no test sees the data of another test (function scope = once per test).
@pytest.fixture
def db_session(pg_engine):
    connection = pg_engine.connect()
    transaction = connection.begin()          # outer transaction, owned by the fixture
    Session = sessionmaker()                  # create session class
    session = Session(bind=connection, join_transaction_mode="create_savepoint") 
    # "create_savepoint"  indicates that new SAVEPOINTs should 
    # be created in order to implement BEGIN/COMMIT/ROLLBACK for the Session
    try:
        yield session
    finally:
        session.close()
        transaction.rollback()                # throw away everything the test wrote
        connection.close()

@pytest.fixture(scope="function")
def user(db_session):
     user1 = User(username="articuno", password=hash_password("12345"))
     db_session.add(user1)
     db_session.commit()
     return user1

@pytest.fixture(scope="function")
def rt(db_session, user):
    rtses = RealTimeSession(session_id = "articuno#12", username = user.username)
    db_session.add(rtses)
    db_session.commit()
    return rtses

@pytest.fixture(scope="function")
def btch(db_session, user):
    batch = BatchTranscription(batch_id = "articuno#B1", context = "batch prueba", username = user.username)
    db_session.add(batch)
    db_session.commit()
    return batch

@pytest.fixture(scope="function")
def envCred(monkeypatch):
    monkeypatch.setattr(database, "_engine", None)

    monkeypatch.setenv('POSTGRES_USERNAME', 'test')
    monkeypatch.setenv('POSTGRES_PASSWORD', 'test')
    monkeypatch.setenv('POSTGRES_DB', 'test')