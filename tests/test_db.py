import pytest
from app.models import User, RealTimeSession, BatchTranscription, TranscriptionEmbeddings
from app.database import Base
from app.security import hash_password
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from sqlalchemy.exc import IntegrityError

@pytest.fixture(scope="function")
def db_session():
        engine = create_engine('sqlite:///:memory:')   
        Base.metadata.create_all(engine)
        Session = sessionmaker(bind=engine)
        session = Session()
        
        yield session

        session.rollback()
        session.close()

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

        
class TestDatabase:

    def test_realTime_Batch_db(self,db_session,user,rt,btch):

        realTime = db_session.query(RealTimeSession).filter_by(session_id = "articuno#12").first()
        assert realTime.session_id == "articuno#12"
        assert realTime.username == "articuno"

        batch = db_session.query(BatchTranscription).filter_by(batch_id = "articuno#B1").first()
        assert batch.batch_id == "articuno#B1"
        assert batch.username == "articuno"

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

