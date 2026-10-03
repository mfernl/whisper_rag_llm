from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Boolean
from datetime import datetime
from app.database import Base,relationship
from sqlalchemy_json import mutable_json_type
from sqlalchemy import CheckConstraint
from sqlalchemy import JSON

class Admin(Base):
    __tablename__ = 'admins'
    id = Column(Integer,primary_key=True,index=True)
    username = Column(String,unique=True,nullable=False)
    password = Column(String,nullable=False)

class User(Base):
    __tablename__ = 'users'
    id = Column(Integer,primary_key=True,index=True)
    username = Column(String,unique=True,nullable=False)
    password = Column(String,nullable=False)

class IWord(Base):
    __tablename__ = 'iwords'
    id = Column(Integer,primary_key=True,index=True)
    word = Column(String,unique=True,nullable=False)
    count = Column(Integer, default=0)
    lastDetectedAt = Column(DateTime,default=datetime.now)
    lastDetectedBy = Column(Integer,ForeignKey("users.username"),default=0)
    transcriptionType = Column(String,default="upload")

    user = relationship("User", backref="last_detection")

class WordDetectionLog(Base):
    __tablename__ = "word_detection_log"

    id = Column(Integer, primary_key=True, index=True)
    word = Column(String,ForeignKey("iwords.word"))
    detectedAt = Column(DateTime, default=datetime.now)
    detectedBy = Column(String,ForeignKey("users.username"))
    transcriptionType = Column(String,default="upload")

    wordD = relationship("IWord", backref="word_detections")
    user = relationship("User", backref="user_detections")

class RealTimeSession(Base):
    __tablename__ = "rt_session"

    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(String, unique=True, nullable=False)
    username = Column(String,ForeignKey("users.username"))
    exp_date = Column(DateTime, default=datetime.now)
    transcription = Column(mutable_json_type(dbtype=JSON, nested=True))

    user = relationship("User", backref="user_session")

class BatchTranscription(Base):
    __tablename__ = "batch_transcription"

    id = Column(Integer, primary_key = True, index=True)
    batch_id = Column(String, unique=True, nullable=False)
    context = Column(String, nullable=False)
    username = Column(String,ForeignKey("users.username"))
    transcription = Column(mutable_json_type(dbtype=JSON, nested=True))

    user = relationship("User", backref="user_batch")

class TranscriptionEmbeddings(Base):
    __tablename__ = "trcpt_embedding"
    
    id = Column(Integer, primary_key = True, index=True)
    session_id = Column(String, ForeignKey("rt_session.session_id"), nullable=True)
    batch_id = Column(String, ForeignKey("batch_transcription.batch_id"), nullable=True)
    embedding = Column(String,nullable=False)
    start_time = Column(Integer,nullable=False)
    end_time = Column(Integer, nullable=False)
    text = Column(String, nullable=False)

    __table_args__ = (
            CheckConstraint('(session_id IS NULL != batch_id IS NULL)', name="check_one_source"),
        ) # check if it works, create pytest

    session = relationship("RealTimeSession", backref="emb_rt")
    batch = relationship("BatchTranscription", backref="emb_batch")