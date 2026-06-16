from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, DeclarativeBase

from ..core.config import settings

engine = create_engine(settings.DATABASE_URL, pool_pre_ping=True, echo=settings.DEBUG)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    pass


# Import all models so Base.metadata.create_all picks them up
from .user import User  # noqa: F401
from .club import Club, JoinRequest  # noqa: F401
from .activity import Activity, ActivityRegistration, Checkin  # noqa: F401
from .notification import Notification  # noqa: F401
from .chat import Conversation, Message  # noqa: F401


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
