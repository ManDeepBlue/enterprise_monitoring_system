from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, DeclarativeBase
from ..settings import settings

class Base(DeclarativeBase):
    pass

def make_engine(database_url: str):
    return create_engine(database_url, pool_pre_ping=True, pool_size=10, max_overflow=20)

def make_session(engine):
    return sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False)

# Global instances for the app to use
engine = make_engine(settings.database_url)
SessionLocal = make_session(engine)
