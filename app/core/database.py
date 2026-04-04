# app/core/database.py
import os
from typing import Generator

from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import Session, sessionmaker

# Use SQLite for development, can change to PostgreSQL later
SQLALCHEMY_DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./agentic_analyst.db")

# Configure connection pooling for PostgreSQL/MySQL
if "postgresql" in SQLALCHEMY_DATABASE_URL or "mysql" in SQLALCHEMY_DATABASE_URL:
    engine = create_engine(
        SQLALCHEMY_DATABASE_URL,
        pool_size=int(os.getenv("DB_POOL_SIZE", 20)),
        max_overflow=int(os.getenv("DB_MAX_OVERFLOW", 10)),
        pool_timeout=int(os.getenv("DB_POOL_TIMEOUT", 30)),
        pool_recycle=int(os.getenv("DB_POOL_RECYCLE", 3600)),
        pool_pre_ping=True,  # Verify connections before using
    )
else:
    # SQLite doesn't need pooling
    engine = create_engine(
        SQLALCHEMY_DATABASE_URL,
        connect_args={"check_same_thread": False} if "sqlite" in SQLALCHEMY_DATABASE_URL else {}
    )

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


def get_db() -> Generator[Session, None, None]:
    """
    Dependency for getting database session.
    Usage: db: Session = Depends(get_db)
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


__all__ = ['engine', 'SessionLocal', 'Base', 'get_db']