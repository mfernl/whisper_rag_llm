import pytest
from app.models import User, RealTimeSession, BatchTranscription, TranscriptionEmbeddings
from app.models import Base
from app.security import hash_password
import sqlalchemy
from sqlalchemy.orm import sessionmaker
from app.database import get_engine
from app import database
import re

from sqlalchemy.exc import IntegrityError

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

        
class TestDatabase:

    @pytest.mark.parametrize("missing_var", ["POSTGRES_USERNAME", "POSTGRES_PASSWORD", "POSTGRES_DB"])
    def test_missing_postgres_var(self, missing_var, monkeypatch, envCred):
        """
        Get engine with any variable missing raises RuntimeError.
        """
        monkeypatch.delenv(name = missing_var, raising = False)
        with pytest.raises(RuntimeError) as rerr:
            get_engine()
        assert missing_var in str(rerr.value)
    
    def test_missing_postgres_variables(self,monkeypatch, envCred):
        """
        Get engine without the env variables raises RuntimeError.
        """
        for var in ["POSTGRES_USERNAME", "POSTGRES_PASSWORD", "POSTGRES_DB"]:
            monkeypatch.delenv(name = var, raising = False)
        
        with pytest.raises(RuntimeError, match = re.escape('[ERR]: database username (POSTGRES_USERNAME) not found in .env file\n[ERR]: database user' \
        ' password (POSTGRES_PASSWORD) not found in .env file\n[ERR]: database name (POSTGRES_DB) not found in .env file')):
            get_engine()   

    def test_pgEngineSetup(self,pg_engine):
        """
        After alembic upgrade head, the container has exactly the models.py tables
        plus alembic_version (Alembic's own table with the current revision).
        """
        db_tables = set(sqlalchemy.inspect(pg_engine).get_table_names())
        model_tables = set(Base.metadata.tables)       # the keys are the table names
        # Sets, not lengths: a missing table plus an unexpected one would still give the
        # same length. If it fails, pytest shows which names are missing or extra.
        assert db_tables == model_tables | {"alembic_version"}


    @pytest.mark.skip(reason="T7: needs the Postgres fixture (spec 001 G1)")
    def test_realTime_Batch_db(self,db_session,user,rt,btch):

        realTime = db_session.query(RealTimeSession).filter_by(session_id = "articuno#12").first()
        assert realTime.session_id == "articuno#12"
        assert realTime.username == "articuno"

        batch = db_session.query(BatchTranscription).filter_by(batch_id = "articuno#B1").first()
        assert batch.batch_id == "articuno#B1"
        assert batch.username == "articuno"

    @pytest.mark.skip(reason="T7: needs the Postgres fixture (spec 001 G1)")
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

    @pytest.mark.skip(reason="T7: needs the Postgres fixture (spec 001 G1)")
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

    @pytest.mark.skip(reason="T7: needs the Postgres fixture (spec 001 G1)")
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

    @pytest.mark.skip(reason="T7: needs the Postgres fixture (spec 001 G1)")
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

    @pytest.mark.skip(reason="T7: needs the Postgres fixture (spec 001 G1)")
    def test_rt_session_usuario_inexistente(self, db_session):                                                     
        rtses = RealTimeSession(                                                                                 
            session_id = "rt.session_id",                                                                                              
            username = "manolo"                                                                              
        )                                                                                                                                        
        db_session.add(rtses)                                                                                                                        
        #with pytest.raises(IntegrityError) as excinfo:                                                    
        db_session.commit()                                                                                                                 
        #print(excinfo.value)
        db_session.rollback()

