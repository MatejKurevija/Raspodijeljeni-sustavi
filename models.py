# models.py

from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, Text
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()

class Task(Base):
    __tablename__ = 'tasks'
    id = Column(Integer, primary_key=True, autoincrement=True)
    type = Column(String(50), nullable=False)         # npr. count_primes, scrape, scrape_url, reverse, uppercase
    parameters = Column(Text, nullable=True)           # za count_primes → "200000", za scrape → URL, itd.
    status = Column(String(20), default='pending')     # pending / in_progress / completed / failed
    worker_id = Column(String(50), nullable=True)      # ID radnika koji radi na zadatku
    result = Column(Text, nullable=True)               # rezultat (npr. broj prostih, HTML title, itd.)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class WorkerStatus(Base):
    __tablename__ = 'worker_status'
    id = Column(String(50), primary_key=True)          # npr. w1, w2, w3
    last_seen = Column(DateTime, default=datetime.utcnow)  # timestamp zadnjeg heartbeat-a

class LeaderStatus(Base):
    __tablename__ = 'leader_status'
    # U ovoj tablici uvijek postoji (naj) jedan red
    id = Column(Integer, primary_key=True)
    leader_id = Column(String(50), unique=True)        # ID trenutnog lidera (npr. "leader-<UUID>")
    last_seen = Column(DateTime, default=datetime.utcnow)   # timestamp zadnjeg heartbeat-a
