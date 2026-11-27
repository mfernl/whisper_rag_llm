import pytest
from app.models import Base
import sqlalchemy
from app.database import get_engine
import re
from app.models import RealTimeSession, BatchTranscription, TranscriptionEmbeddings, User
from sqlalchemy.exc import IntegrityError



        
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
        Spec 002 AC-5.1: after alembic upgrade head, the container has exactly the models.py tables
        plus alembic_version (Alembic's own table with the current revision).
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

    @pytest.mark.skip(reason="T10: use real vectors")
    def test_embedding_two_transcriptions(self,db_session,user,rt,btch):
        ses = db_session.query(RealTimeSession).filter_by(session_id = "articuno#12").first()
        batch = db_session.query(BatchTranscription).filter_by(batch_id = "articuno#B1").first()

        emb = TranscriptionEmbeddings(
            session_id = ses.session_id, 
            batch_id = batch.batch_id, 
            embedding = "asdfg", 
            start_time = 12, 
            end_time = 13, 
            text = "ayer fui a por manzanas")
        
        db_session.add(emb)
        with pytest.raises(IntegrityError):
            db_session.commit()
        db_session.rollback()

    @pytest.mark.skip(reason="T10: use real vectors")
    def test_embedding_no_transcriptions(self,db_session):
        emb = TranscriptionEmbeddings(
            embedding = "asdfg", 
            start_time = 12, 
            end_time = 13, 
            text = "hoy a por melocotones")
        
        db_session.add(emb)
        with pytest.raises(IntegrityError):
            db_session.commit()
        db_session.rollback()

    @pytest.mark.skip(reason="T10: use real vectors")
    def test_only_batch_accepted(self, db_session, user, btch):
        emb = TranscriptionEmbeddings(
            batch_id = btch.batch_id,  
            embedding = "asdfg", 
            start_time = 12, 
            end_time = 13, 
            text = "maniana a por platanos")
        
        db_session.add(emb)
        db_session.commit()                 # si falla, el test falla
        assert db_session.query(TranscriptionEmbeddings).count() == 1

    @pytest.mark.skip(reason="T10: use real vectors")
    def test_only_session_accepted(self, db_session, user, rt):
        emb = TranscriptionEmbeddings(
            session_id = rt.session_id,  
            embedding = "asdfg", 
            start_time = 12, 
            end_time = 13, 
            text = "y pasado a por peras")
        
        db_session.add(emb)
        db_session.commit()                 # si falla, el test falla
        assert db_session.query(TranscriptionEmbeddings).count() == 1


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
        db_session.rollback()  # after a failed commit() the session can't be used until rollback()

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
        db_session.rollback()
        assert db_session.query(User).count() == 1

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
        db_session.rollback()

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
        db_session.rollback()


