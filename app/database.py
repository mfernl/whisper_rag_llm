from sqlalchemy import URL, create_engine
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

# Host and port are not secrets: they default to the compose service, so an existing .env keeps working.
# Outside compose (alembic from cmd, testcontainers) override them, e.g. POSTGRES_HOST=127.0.0.1.
host = os.getenv("POSTGRES_HOST", "db")
port = int(os.getenv("POSTGRES_PORT", "5432"))

# URL.create escapes special characters (@ / :) in the password for us.
pg_uri = URL.create(
    drivername="postgresql+psycopg",
    username=uname,
    password=pssw,
    host=host,
    port=port,
    database=dbn,
)

engine = create_engine(pg_uri)

SessionLocal = sessionmaker(bind=engine)

Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()