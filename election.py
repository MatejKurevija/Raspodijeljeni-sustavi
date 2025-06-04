# election.py

from datetime import datetime
from models import WorkerStatus, LeaderStatus

def election(session, my_id):

    from utils import WORKER_TIMEOUT

    now = datetime.utcnow()
    active_workers = session.query(WorkerStatus).all()
    candidates = [w.id for w in active_workers if (now - w.last_seen).total_seconds() <= WORKER_TIMEOUT]

    # Ako nema aktivnih, ne radimo ništa
    if not candidates:
        print(f"[Election {my_id}] Nema aktivnih radnika, ne mogu preuzeti liderstvo.")
        return

    # Ubaci i sebe (u slučaju da nisam bio na popisu)
    if my_id not in candidates:
        candidates.append(my_id)

    # Leksički najveći ID postaje novi lider
    new_leader = sorted(candidates)[-1]
    if new_leader == my_id:
        ls = session.query(LeaderStatus).first()
        if ls:
            ls.leader_id = my_id
            ls.last_seen = datetime.utcnow()
        else:
            ls = LeaderStatus(leader_id=my_id, last_seen=datetime.utcnow())
            session.add(ls)
        session.commit()
        print(f"[Election {my_id}] Postao novi lider.")
    else:
        print(f"[Election {my_id}] Lider je {new_leader}, ja ({my_id}) nisam lider.")
