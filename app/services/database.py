from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from models.object_model import Base
import os

_db_path = os.path.join(os.path.dirname(__file__), '..', 'objects.db')
_engine = create_engine(f'sqlite:///{_db_path}', echo=False)
Base.metadata.create_all(_engine)
SessionLocal = sessionmaker(bind=_engine)

def get_db() -> Session:
    return SessionLocal()