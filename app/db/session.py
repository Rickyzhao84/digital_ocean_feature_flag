from sqlmodel import SQLModel, create_engine, Session
from app.core.config import get_settings

engine = None


def _get_engine():
    global engine
    if engine is None:
        settings = get_settings()
        engine = create_engine(settings.DATABASE_URL, echo=False)
    return engine


def init_db():
    e = _get_engine()
    SQLModel.metadata.create_all(e)


def get_session() -> Session:
    e = _get_engine()
    return Session(e)
