import os
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

DATABASE_URL = os.getenv('DATABASE_URL', 'sqlite:///app.db')
engine = create_engine(DATABASE_URL, pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)
Base = declarative_base()

def init_db():
    """Initialize database tables."""
    try:
        Base.metadata.create_all(bind=engine)
    except Exception as exc:  # pragma: no cover - defensive
        raise RuntimeError(f"Error initializing database: {exc}") from exc
