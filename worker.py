# worker.py

import time
import requests
from bs4 import BeautifulSoup
from datetime import datetime

from db import SessionLocal, init_db
from models import Task, WorkerStatus, LeaderStatus
from utils import HEARTBEAT_INTERVAL, WORKER_TIMEOUT, LEADER_TIMEOUT, STATUS_PRINT_INTERVAL
from election import election
from tasks import execute_task

def worker_process(worker_id):
    """
    Worker:
    1) Registrira se u WorkerStatus s vlastitim ID-jem
    2) Svakih HEARTBEAT_INTERVAL sekundi ažurira last_seen
    3) Svakih STATUS_PRINT_INTERVAL sekundi ispiše "Alive/Idle" ili "Processing"
    4) Provjerava je li lider živ; ako nije, pokreće election()
    5) Preuzima pending zadatke, izvršava ih (execute_task) i ažurira status/result
    6) U slučaju da 'scrape' zadatak podijeli posao na pod‐zadatke 'scrape_url'
    7) Ako padne (ne šalje heartbeat), lider ga izbriše, a ostali radnici sami nastavljaju
    """
    init_db()
    session = SessionLocal()
    print(f"[Worker {worker_id}] Pokrećem se...")

    # 1) Registracija ili ažuriranje postojećeg redka
    ws = session.query(WorkerStatus).filter_by(id=worker_id).first()
    if not ws:
        ws = WorkerStatus(id=worker_id, last_seen=datetime.utcnow())
        session.add(ws)
    else:
        ws.last_seen = datetime.utcnow()
    session.commit()

    last_status_print = datetime.utcnow()

    while True:
        now = datetime.utcnow()

        # 2) Heartbeat
        ws.last_seen = now
        session.commit()

        # 3) Svakih STATUS_PRINT_INTERVAL sekundi ispiši status
        if (now - last_status_print).total_seconds() >= STATUS_PRINT_INTERVAL:
            print(f"[Worker {worker_id}] Status: Alive/Idle")
            last_status_print = now

        # 4) Provjera statusa lidera
        ls = session.query(LeaderStatus).first()
        if not ls or (datetime.utcnow() - ls.last_seen).total_seconds() > LEADER_TIMEOUT:
            print(f"[Worker {worker_id}] Lider se ne javlja. Pokrećem election.")
            election(session, worker_id)
            ls = session.query(LeaderStatus).first()
            print(f"[Worker {worker_id}] Novi lider je {ls.leader_id}")

        # Ako smo postali novi lider, izađi iz worker petlje
        ls = session.query(LeaderStatus).first()
        if ls and ls.leader_id == worker_id:
            print(f"[Worker {worker_id}] Preuzimam ulogu lidera, izlazak iz worker petlje.")
            break

        # 5) Pokušaj atomarno preuzeti jedan pending zadatak
        task = None
        try:
            task = (session.query(Task)
                        .filter_by(status='pending')
                        .with_for_update()
                        .first())
            if task:
                task.status = 'in_progress'
                task.worker_id = worker_id
                session.commit()
        except Exception:
            session.rollback()
            task = None

        if not task:
            time.sleep(1)
            continue

        # U ovom trenutku task.status == 'in_progress'
        print(f"[Worker {worker_id}] Preuzeo zadatak {task.id} (type={task.type})")

        # 6) Izvrši zadatak
        result = execute_task(task)

        # 7) Ažuriraj rezultat
        task.status = 'completed' if result is not None else 'failed'
        task.result = str(result)
        session.commit()
        print(f"[Worker {worker_id}] Zadatak {task.id} dovršen, result={result}")

        time.sleep(0.1)
