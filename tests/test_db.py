import pytest
from app.models import User, RealTimeSession, BatchTranscription, TranscriptionEmbeddings
from app.database import Base, engine, SessionLocal
from app.security import hash_password

from sqlalchemy.exc import IntegrityError

@pytest.fixture(scope="module")
def db_session():
        Base.metadata.create_all(engine)
        session = SessionLocal()

        user1 = User(username = "articuno", password = hash_password("12345"))
        session.add(user1)
        session.commit()

        yield session

        session.rollback()
        session.close()

@pytest.fixture(scope="module")
def rt():
    rtses = RealTimeSession(session_id = "articuno#12", username = "articuno")
    return rtses

@pytest.fixture(scope="module")
def btch():
    batch = BatchTranscription(batch_id = "articuno#B1", context = "batch prueba", username = "articuno")
    return batch

        
class TestDatabase:

    def test_realTime_Batch_db(self,db_session,rt,btch):
        db_session.add(rt)
        db_session.commit()
        db_session.add(btch)
        db_session.commit()

        realTime = db_session.query(RealTimeSession).filter_by(session_id = "articuno#12").first()
        assert realTime.session_id == "articuno#12"
        assert realTime.username == "articuno"

        batch = db_session.query(BatchTranscription).filter_by(batch_id = "articuno#B1").first()
        assert batch.batch_id == "articuno#B1"
        assert batch.username == "articuno"

    @pytest.mark.xfail(raises=IntegrityError)
    def test_embedding_two_transcriptions(self,db_session):
        session = db_session.query(RealTimeSession).filter_by(session_id = "articuno#12").first()
        batch = db_session.query(BatchTranscription).filter_by(batch_id = "articuno#B1").first()

        emb = TranscriptionEmbeddings(
            session_id = session.session_id, 
            batch_id = batch.batch_id, 
            embedding = "asdfg", 
            start_time = 12, 
            end_time = 13, 
            text = "ayer fui a por manzanas")
        db_session.add(emb)
        try:
            db_session.commit()
        except IntegrityError:
            db_session.rollback()

