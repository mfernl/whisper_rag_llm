import pytest
from app.models import Base
import sqlalchemy
from app.database import get_engine
import re
from sqlalchemy import text
from app.models import RealTimeSession, BatchTranscription, TranscriptionEmbeddings, User
from sqlalchemy.exc import IntegrityError, DataError
from alembic import command
from alembic.config import Config
from pathlib import Path

# A valid value for the Vector(384) column (app/models.py): a plain list of 384 floats.
# All the values are the same because the tests only check where the embedding comes from.
VECTOR_384 = [0.1] * 384


class TestDatabase:

    @pytest.mark.parametrize("missing_var", ["POSTGRES_USERNAME", "POSTGRES_PASSWORD", "POSTGRES_DB"])
    def test_missing_postgres_var(self, missing_var, monkeypatch, envCred):
        """
        Spec 002 AC-3.1: get_engine() with any one variable missing raises RuntimeError,
        and the message names that variable.
        """
        monkeypatch.delenv(name = missing_var, raising = False)
        with pytest.raises(RuntimeError) as rerr:
            get_engine()
        assert missing_var in str(rerr.value)
    
    def test_missing_postgres_variables(self,monkeypatch, envCred):
        """
        Spec 002 AC-3.1: get_engine() with all three variables missing raises RuntimeError,
        and the message names every missing variable (not only the first one).
        """
        for var in ["POSTGRES_USERNAME", "POSTGRES_PASSWORD", "POSTGRES_DB"]:
            monkeypatch.delenv(name = var, raising = False)
        
        with pytest.raises(RuntimeError, match = re.escape('[ERR]: database username (POSTGRES_USERNAME) not found in .env file\n[ERR]: database user' \
        ' password (POSTGRES_PASSWORD) not found in .env file\n[ERR]: database name (POSTGRES_DB) not found in .env file')):
            get_engine()   

    def test_pgEngineSetup(self,pg_engine):
        """
        Spec 002 AC-5.1 and AC-2.1 (tables half): after alembic upgrade head, the container has
        exactly the models.py tables plus alembic_version (Alembic's own table with the current
        revision). The extension half of AC-2.1 is checked by test_alembic_upgrade_extensions.
        """
        db_tables = set(sqlalchemy.inspect(pg_engine).get_table_names())
        model_tables = set(Base.metadata.tables)       # the keys are the table names
        # Sets, not lengths: a missing table plus an unexpected one would still give the
        # same length. If it fails, pytest shows which names are missing or extra.
        assert db_tables == model_tables | {"alembic_version"}


    def test_realTime_Batch_db(self,db_session,user,rt,btch):
        """
        Spec 001 AC-1.1 and AC-1.2: a real-time session and a batch transcription saved
        for an existing user (the rt and btch fixtures) are returned when queried by their id.
        """

        realTime = db_session.query(RealTimeSession).filter_by(session_id = "articuno#12").first()
        assert realTime.session_id == "articuno#12"
        assert realTime.username == "articuno"

        batch = db_session.query(BatchTranscription).filter_by(batch_id = "articuno#B1").first()
        assert batch.batch_id == "articuno#B1"
        assert batch.username == "articuno"

    def test_embedding_two_transcriptions(self, db_session, rt, btch):
        """
        Spec 001 AC-2.1: an embedding with both a session_id and a batch_id is rejected
        by the check_one_source CHECK constraint (SQLSTATE 23514), not by another error.
        """
        emb = TranscriptionEmbeddings(
            session_id = rt.session_id,
            batch_id = btch.batch_id,
            embedding = VECTOR_384,
            start_time = 12,
            end_time = 13,
            text = "yesterday I went to buy apples")
        db_session.add(emb)
        with pytest.raises(IntegrityError) as excinfo:
            db_session.commit()
        assert excinfo.value.orig.sqlstate == "23514"  # check_violation
        assert excinfo.value.orig.diag.constraint_name == "check_one_source"

    def test_embedding_no_transcriptions(self, db_session):
        """
        Spec 001 AC-2.2: an embedding with neither a session_id nor a batch_id is rejected
        by the check_one_source CHECK constraint (SQLSTATE 23514).
        """
        emb = TranscriptionEmbeddings(
            embedding = VECTOR_384,
            start_time = 12,
            end_time = 13,
            text = "today I am going to buy peaches")
        db_session.add(emb)
        with pytest.raises(IntegrityError) as excinfo:
            db_session.commit()
        assert excinfo.value.orig.sqlstate == "23514"  # check_violation
        assert excinfo.value.orig.diag.constraint_name == "check_one_source"

    def test_only_batch_accepted(self, db_session, btch):
        """
        Spec 001 AC-2.3: an embedding with only a batch_id is stored.
        """
        emb = TranscriptionEmbeddings(
            batch_id = btch.batch_id,
            embedding = VECTOR_384,
            start_time = 12,
            end_time = 13,
            text = "tomorrow I am going to buy bananas")
        db_session.add(emb)
        db_session.commit()                 # if the insert is rejected, this raises and the test fails
        assert db_session.query(TranscriptionEmbeddings).count() == 1

    def test_only_session_accepted(self, db_session, rt):
        """
        Spec 001 AC-2.4: an embedding with only a session_id is stored.
        """
        emb = TranscriptionEmbeddings(
            session_id = rt.session_id,
            embedding = VECTOR_384,
            start_time = 12,
            end_time = 13,
            text = "and the day after I am going to buy pears")
        db_session.add(emb)
        db_session.commit()                 # if the insert is rejected, this raises and the test fails
        assert db_session.query(TranscriptionEmbeddings).count() == 1

    def test_embedding_wrongDimension(self, db_session, btch):
        """
        Spec 001 AC-2.5: an embedding whose length is not 384 is rejected by pgvector
        (DataError, SQLSTATE 22000), even when its source is valid.
        """
        emb = TranscriptionEmbeddings(
            batch_id = btch.batch_id,
            embedding = [0.1] * 3,
            start_time = 12,
            end_time = 13,
            text = "a vector that is too short")
        db_session.add(emb)
        with pytest.raises(DataError) as excinfo:
            db_session.commit()
        assert excinfo.value.orig.sqlstate == "22000"  # data_exception
        assert "expected 384 dimensions" in str(excinfo.value.orig)

    def test_rt_session_nonexistentUser(self, db_session):
        """
        Spec 001 AC-3.1: a real-time session for a username that doesn't exist is rejected
        by the foreign key (SQLSTATE 23503), not by another integrity error.
        """
        rtses = RealTimeSession(                                                                                 
            session_id = "rt.session_id",                                                                                              
            username = "manolo"                                                                              
        )                                                                                                                                        
        db_session.add(rtses)                                                                                                                        
        with pytest.raises(IntegrityError) as excinfo:                                                    
            db_session.commit()
        assert excinfo.value.orig.sqlstate == "23503"  # foreign_key_violation

    def test_session_joinTransaction(self,db_session, user):
        """
        Spec 002 AC-5.1 (test isolation, T7): a failed commit inside a test only rolls back
        to the savepoint, so the user committed by the fixture is still there afterwards.
        """
        rtses = RealTimeSession(                                                                                 
            session_id = "rt.session_id",                                                                                              
            username = "manolo"                                                                              
        )                                                                                                                                        
        db_session.add(rtses)                                                                                                                        
        with pytest.raises(IntegrityError) as excinfo:                                                    
            db_session.commit()                                                                                                                 
        # After a failed commit() the session can't run queries until rollback(). Here it is
        # needed because the test uses the session again; the other tests leave it to the fixture.
        db_session.rollback()
        assert db_session.query(User).count() == 1

    # Red on purpose until T12 (G12: downgrade() does not drop the vector extension yet).
    # strict=True: when T12 makes it pass, XPASS(strict) turns into a FAIL, which forces
    # removing this marker in the T12 commit.
    @pytest.mark.xfail(strict=True, reason="T12: downgrade() does not drop the vector extension yet (G12)")
    def test_alembic_downgrade(self, pg_engine):
        """
        Spec 002 AC-2.2: after alembic downgrade base, only alembic_version is left (no application
        tables) and the vector extension is gone. The finally runs upgrade head again, so the tests
        after this one still get the full schema on the shared pg_engine container.
        """
        config = Config(Path(__file__).parent.parent / "alembic.ini")
        try:
            command.downgrade(config, "base")
            # A new Inspector after the downgrade: an Inspector caches what it has read.
            db_tables = set(sqlalchemy.inspect(pg_engine).get_table_names())

            with pg_engine.connect() as conn:
                result = conn.execute(text("SELECT extname FROM pg_extension WHERE extname = 'vector'")).scalar()

            assert db_tables == {'alembic_version'}
            assert result is None
        finally:
            command.upgrade(config, "head") # Restore the migration to keep running the tests


    def test_duplicated_session_id(self, db_session, rt, user):
        """
        Spec 001 AC-1.3: a second real-time session with an existing session_id is rejected.
        """
        rtses = RealTimeSession(
            session_id = rt.session_id,
            username = user.username
        )
        db_session.add(rtses)
        with pytest.raises(IntegrityError) as excinfo:
            db_session.commit()
        assert excinfo.value.orig.sqlstate == "23505"  # unique_violation

    def test_duplicated_batch_id(self, db_session, btch, user):
        """
        Spec 001 AC-1.3: a second batch transcription with an existing batch_id is rejected.
        """
        bt = BatchTranscription(
            batch_id = btch.batch_id,
            username = user.username,
            context = "test duplicate batch_id"
        )
        db_session.add(bt)
        with pytest.raises(IntegrityError) as excinfo:
            db_session.commit()
        assert excinfo.value.orig.sqlstate == "23505"  # unique_violation

    def test_alembic_upgrade_extensions(self, pg_engine):
        """
        Spec 002 AC-2.1 (extension half): after alembic upgrade head on the empty test container,
        the vector extension is installed. The tables half is checked by test_pgEngineSetup.
        """
        with pg_engine.connect() as conn:
            result = conn.execute(text("SELECT extname FROM pg_extension WHERE extname = 'vector'")).scalar()
        assert result is not None

    