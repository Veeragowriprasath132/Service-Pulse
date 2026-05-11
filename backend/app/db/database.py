"""
app/db/database.py — SQLAlchemy engine, session factory, Base
"""
from sqlalchemy import create_engine, event
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from app.config import get_settings

settings = get_settings()

# ── Engine ────────────────────────────────────────────────
connect_args = {}
if "sqlite" in settings.database_url:
    connect_args = {"check_same_thread": False}

engine = create_engine(
    settings.database_url,
    connect_args=connect_args,
    pool_pre_ping=True,        # verify connections before use
    pool_recycle=3600,         # recycle connections every hour
    echo=settings.debug,       # log SQL in debug mode
)

# Enable WAL mode for SQLite (better concurrent reads)
if "sqlite" in settings.database_url:
    @event.listens_for(engine, "connect")
    def set_sqlite_pragma(dbapi_conn, connection_record):
        cursor = dbapi_conn.cursor()
        cursor.execute("PRAGMA journal_mode=WAL")
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

# ── Session factory ───────────────────────────────────────
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# ── Base class for ORM models ─────────────────────────────
Base = declarative_base()


# ── Dependency — yields a DB session per request ──────────
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
