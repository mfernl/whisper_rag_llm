from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
import os

uname = os.getenv("POSTGRES_USERNAME")
pssw = os.getenv("POSTGRES_PASSWORD")
dbn = os.getenv("POSTGRES_DB")

errores = []
if not uname:
    errores.append("[ERR]: database username (POSTGRES_USERNAME) not found in .env file")
if not pssw:
    errores.append("[ERR]: database user password (POSTGRES_PASSWORD) not found in .env file")
if not dbn:
    errores.append("[ERR]: database name (POSTGRES_DB) not found in .env file")

if errores:
    raise RuntimeError("\n".join(errores)) # la app no arranca sin la configuración de la BD

pg_uri = f"postgresql+psycopg://{uname}:{pssw}@db/{dbn}"

# 'sqlite:///./transcription.db'

engine = create_engine(pg_uri) # postgres database on another container

SessionLocal = sessionmaker(bind=engine)

Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()