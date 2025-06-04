# leader.py

import threading
import time
import uuid
from datetime import datetime

from flask import Flask, render_template, request, redirect, url_for, jsonify

from db import SessionLocal, init_db
from models import Task, WorkerStatus, LeaderStatus
from utils import HEARTBEAT_INTERVAL, WORKER_TIMEOUT

import json  # Za parsiranje JSON‐a iz tasks.result

app = Flask(__name__)


def initialize_leader():
    """
    Inicijalna inicijalizacija: pobriši stare LeaderStatus zapise
    i zapiši novi red za ovog lidera.
    """
    init_db()
    session = SessionLocal()
    try:
        # Generiraj jedinstveni ID za lidera
        my_id = f"leader-{uuid.uuid4()}"
        # Obriši stare redove u tablici LeaderStatus
        session.query(LeaderStatus).delete()
        session.commit()
        # Stvori novi red za ovog lidera
        leader_row = LeaderStatus(leader_id=my_id, last_seen=datetime.utcnow())
        session.add(leader_row)
        session.commit()
        print(f"[Leader] Pokrećem se s ID‐jem: {my_id}")
        return my_id
    finally:
        session.close()


@app.route("/", methods=["GET", "POST"])
def index():
    """
    GET /:
      - Dohvati tasks i workere iz baze i renderaj frontend (index.html).
    POST /:
      - Dodaj novi Task (preuzet iz HTML forme), zatim redirect na GET /.
    """
    if request.method == "POST":
        task_type = request.form.get("task_type")
        params = request.form.get("parameters")

        if task_type and params:
            session = SessionLocal()
            try:
                new_task = Task(
                    type=task_type,
                    parameters=params,
                    status="pending",
                    worker_id=None,
                    result=None,
                    created_at=datetime.utcnow(),
                    updated_at=datetime.utcnow()
                )
                session.add(new_task)
                session.commit()
            except Exception as e:
                session.rollback()
                print(f"[Leader][ERROR] Nemoguće spremiti novi task: {e}")
            finally:
                session.close()

        return redirect(url_for("index"))

    # ====== GET ======
    session = SessionLocal()
    try:
        # Dohvati sve zadatke (sort po created_at desc)
        tasks = session.query(Task).order_by(Task.created_at.desc()).all()
        # Dohvati sve radnike
        workers = session.query(WorkerStatus).all()
        # Dohvati trenutni lider status (trebao bi biti samo jedan red)
        leader_info = session.query(LeaderStatus).first()

        # Parsiraj JSON rezultat samo za compare_offers i compare_skin_offers
        for t in tasks:
            if t.result and t.type in ("compare_offers", "compare_skin_offers"):
                try:
                    t.parsed_result = json.loads(t.result)
                except Exception:
                    t.parsed_result = None
            else:
                t.parsed_result = None

        return render_template(
            "index.html",
            tasks=tasks,
            workers=workers,
            leader=leader_info,
            now=datetime.utcnow()
        )
    finally:
        session.close()


@app.route("/api/add_task", methods=["POST"])
def api_add_task():
    """
    POST /api/add_task
    Prima JSON:
      { "type": "<task_type>", "parameters": "<parametri>" }
    Kreira novi Task sa status="pending" i vraća:
      { "success": True, "task_id": <id> }
    ili:
      { "success": False, "error": "<poruka>" }
    """
    data = request.get_json()
    if not data:
        return jsonify({ "success": False, "error": "Prazan JSON payload." }), 400

    task_type = data.get("type")
    params = data.get("parameters")
    if not task_type or not params:
        return jsonify({ "success": False, "error": "Nedostaju type ili parameters." }), 400

    session = SessionLocal()
    try:
        new_task = Task(
            type=task_type,
            parameters=params,
            status="pending",
            worker_id=None,
            result=None,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        session.add(new_task)
        session.commit()
        return jsonify({ "success": True, "task_id": new_task.id })
    except Exception as e:
        session.rollback()
        return jsonify({ "success": False, "error": str(e) }), 500
    finally:
        session.close()


@app.route("/api/status", methods=["GET"])
def api_status():
    """
    GET /api/status
    Vraća JSON s trenutačnim stanjem svih Tasks i WorkerStatus redova:
    {
      "tasks": [
        { "id": 1, "type": "...", "parameters": "...", "status": "...",
          "worker_id": 2, "result": "..." }, ...
      ],
      "workers": [
        { "worker_id": 1, "status": "Alive", "last_seen": "2025-06-05T15:00:00" },
        ...
      ]
    }
    """
    session = SessionLocal()
    try:
        # Dohvati sve zadatke
        tasks = session.query(Task).order_by(Task.id).all()
        tasks_list = []
        for t in tasks:
            tasks_list.append({
                "id": t.id,
                "type": t.type,
                "parameters": t.parameters,
                "status": t.status,
                "worker_id": t.worker_id,
                "result": t.result or ""
            })

        # Dohvati sve radnike
        workers = session.query(WorkerStatus).all()
        workers_list = []
        now_check = datetime.utcnow()
        for w in workers:
            iso_time = w.last_seen.isoformat() if w.last_seen else ""
            # Računamo status na temelju last_seen i WORKER_TIMEOUT
            delta = (now_check - w.last_seen).total_seconds() if w.last_seen else float('inf')
            status_str = "Alive" if delta <= WORKER_TIMEOUT else "Offline"
            workers_list.append({
                "worker_id": w.id,
                "status": status_str,
                "last_seen": iso_time
            })

        return jsonify({ "tasks": tasks_list, "workers": workers_list })
    finally:
        session.close()


def send_heartbeat(my_id: str):
    """
    Pozadinski thread: svaki put kad prođe HEARTBEAT_INTERVAL, ažurira
    LeaderStatus.last_seen za ovog lidera. Ako izgubi polje, prekida se.
    """
    while True:
        time.sleep(HEARTBEAT_INTERVAL)
        session = SessionLocal()
        try:
            row = session.query(LeaderStatus).first()
            if row and row.leader_id == my_id:
                row.last_seen = datetime.utcnow()
                session.commit()
            else:
                print("[Leader] Izgubio sam liderstvo, prekidam heartbeat.")
                break
        finally:
            session.close()


def monitor_workers():
    """
    Pozadinski thread: svaki put kad prođe HEARTBEAT_INTERVAL, provjerava
    je li neki worker „umro”. Ako jest, vraća njegove zadatke na pending
    i briše WorkerStatus red.
    """
    while True:
        time.sleep(HEARTBEAT_INTERVAL)
        now_check = datetime.utcnow()
        session = SessionLocal()
        try:
            workers_list = session.query(WorkerStatus).all()
            for w in workers_list:
                delta = (now_check - w.last_seen).total_seconds()
                if delta > WORKER_TIMEOUT:
                    print(f"[Leader] Worker {w.id} je prekinuo rad (delta={delta:.1f}s). Requeue zadataka.")
                    # Prebaci sve in_progress zadatke tog workera na pending
                    tasks_to_requeue = session.query(Task).filter(
                        Task.worker_id == w.id,
                        Task.status == 'in_progress'
                    ).all()
                    for t in tasks_to_requeue:
                        t.status = 'pending'
                        t.worker_id = None
                    session.commit()

                    # Izbriši tog workera iz baze
                    session.delete(w)
                    session.commit()
        finally:
            session.close()


def leader_process(flask_port=5000):
    """
    Glavna funkcija za lidera:
      1. initialize_leader() – postavi LeaderStatus
      2. pokreni threadove send_heartbeat() i monitor_workers()
      3. pokreni Flask server na portu flask_port
    """
    my_id = initialize_leader()

    heartbeat_thread = threading.Thread(target=send_heartbeat, args=(my_id,), daemon=True)
    heartbeat_thread.start()

    monitor_thread = threading.Thread(target=monitor_workers, daemon=True)
    monitor_thread.start()

    app.run(host="0.0.0.0", port=flask_port, debug=True)
