"""
Database session management.
Sets up the SQLAlchemy engine, session factory, and declarative base.
"""

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, DeclarativeBase
from ..settings import settings

class Base(DeclarativeBase):
    """
    Base class for all database models.
    Inherits from DeclarativeBase for SQLAlchemy 2.0 style.
    """
    pass

def make_engine(database_url: str):
    """
    Create a SQLAlchemy engine with optimized pooling.
    
    Args:
        database_url: Connection string for the database.
    """
    return create_engine(
        database_url, 
        pool_pre_ping=True, # Validate connections before use
        pool_size=10,       # Persistent connections
        max_overflow=20     # Temporary extra connections
    )

def make_session(engine):
    """
    Create a session factory bound to the provided engine.
    """
    return sessionmaker(
        bind=engine, 
        autoflush=False, 
        autocommit=False, 
        expire_on_commit=False
    )

# Global engine and session factory used by the FastAPI application
engine = make_engine(settings.database_url)
SessionLocal = make_session(engine)
