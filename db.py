# db.py

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from models import Base

DB_FILENAME = "distributed_system.db"
engine = create_engine(f'sqlite:///{DB_FILENAME}', connect_args={'check_same_thread': False})
SessionLocal = sessionmaker(bind=engine)

def init_db():
    # Kreira sve tablice iz modela ako ne postoje
    Base.metadata.create_all(bind=engine)
