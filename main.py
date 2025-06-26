# main.py

import os
import time
import threading
import json
import uuid
import logging
from types import SimpleNamespace
from datetime import datetime
from flask import Flask, render_template, request, redirect, url_for, jsonify
import psycopg2
from psycopg2.extras import RealDictCursor

from db import init_db, get_conn
from tasks import execute_task
from utils import HEARTBEAT_INTERVAL

# ---- Logging setup ----
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# ---- Configuration ----
NUM_WORKERS    = 3
worker_threads = {}    # wid -> Thread
shutdown_flags = {}    # wid -> Event
leader_lock    = threading.Lock()
leader_id      = None  # e.g. "w1"

# ---- Election Functions ----
def elect_initial_leader():
    global leader_id
    with leader_lock:
        for wid, thr in worker_threads.items():
            if thr.is_alive():
                leader_id = wid
                logger.info(f"[Election] Initial leader: {leader_id}")
                return

def election_loop():
    global leader_id
    while True:
        time.sleep(HEARTBEAT_INTERVAL)
        with leader_lock:
            if leader_id is None or not worker_threads.get(leader_id).is_alive():
                prev = leader_id
                for wid, thr in worker_threads.items():
                    if thr.is_alive():
                        leader_id = wid
                        logger.info(f"[Election] Leader {prev} dead → new leader: {leader_id}")
                        break

# ---- Worker Monitor (auto-restart) ----
def monitor_workers():
    while True:
        time.sleep(HEARTBEAT_INTERVAL)
        for wid, thr in list(worker_threads.items()):
            if not thr.is_alive():
                logger.info(f"[Monitor] Worker {wid} died → restarting")
                evt = threading.Event()
                shutdown_flags[wid] = evt
                new_thr = threading.Thread(target=worker_loop, args=(wid, evt), daemon=True)
                worker_threads[wid] = new_thr
                new_thr.start()

# ---- Worker Loop ----
def worker_loop(worker_id: str, stop_evt: threading.Event):
    logger.info(f"[Worker {worker_id}] started")
    init_db()
    while not stop_evt.is_set():
        # heartbeat / registration
        with get_conn() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                  INSERT INTO worker_status(worker_id, status, last_seen, last_active)
                  VALUES (%s,'Alive',now(),now())
                  ON CONFLICT(worker_id) DO UPDATE SET last_seen = now();
                """, (worker_id,))
            conn.commit()

        # fetch one pending task
        task = None
        with get_conn() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                  SELECT * FROM tasks
                   WHERE status = 'pending'
                   ORDER BY created_at
                   FOR UPDATE SKIP LOCKED
                   LIMIT 1;
                """)
                task = cur.fetchone()
                if task:
                    cur.execute("""
                      UPDATE tasks
                         SET status='in_progress',
                             worker_id=%s,
                             updated_at=now()
                       WHERE id=%s;
                    """, (worker_id, task["id"]))
                conn.commit()

        if task:
            task_obj = SimpleNamespace(**task)
            res = execute_task(task_obj)
            out = res if isinstance(res, str) else json.dumps(res)
            with get_conn() as conn:
                with conn.cursor() as cur:
                    cur.execute("""
                      UPDATE tasks
                         SET status='completed',
                             result=%s,
                             updated_at=now()
                       WHERE id=%s;
                    """, (out, task["id"]))
                    cur.execute(
                      "UPDATE worker_status SET last_active = now() WHERE worker_id = %s;",
                      (worker_id,)
                    )
                conn.commit()
        else:
            time.sleep(1)

    # cleanup on intentional shutdown
    logger.info(f"[Worker {worker_id}] stopping")
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM worker_status WHERE worker_id=%s;", (worker_id,))
        conn.commit()

# ---- Flask Routes ----
@app.route("/", methods=["GET", "POST"])
def index():
    if request.method == "POST":
        ttype = request.form.get("task_type")
        params = request.form.get("parameters")
        if ttype and params:
            with get_conn() as conn:
                with conn.cursor() as cur:
                    cur.execute("""
                      INSERT INTO tasks(type, parameters, status, created_at, updated_at)
                      VALUES (%s, %s, 'pending', now(), now());
                    """, (ttype, params))
                conn.commit()
        return redirect(url_for("index"))

    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT * FROM tasks ORDER BY created_at DESC;")
            tasks = cur.fetchall()
            cur.execute("SELECT * FROM worker_status;")
            workers = cur.fetchall()

    # parse JSON results
    for t in tasks:
        if t["result"] and t["type"].startswith("compare"):
            try:
                t["parsed"] = json.loads(t["result"])
            except:
                t["parsed"] = None
        else:
            t["parsed"] = None

    return render_template(
        "index.html",
        tasks=tasks,
        workers=workers,
        leader=leader_id,
        now=datetime.utcnow()
    )

@app.route("/api/add_task", methods=["POST"])
def api_add_task():
    data = request.get_json() or {}
    ttype = data.get("type")
    params = data.get("parameters")
    if not ttype or not params:
        return jsonify(success=False, error="type i parameters required"), 400

    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("""
              INSERT INTO tasks(type, parameters, status, created_at, updated_at)
              VALUES (%s, %s, 'pending', now(), now()) RETURNING id;
            """, (ttype, params))
            tid = cur.fetchone()["id"]
        conn.commit()

    return jsonify(success=True, task_id=tid)

@app.route("/api/status", methods=["GET"])
def api_status():
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT * FROM tasks ORDER BY id;")
            ts = cur.fetchall()
            cur.execute("SELECT * FROM worker_status;")
            ws = cur.fetchall()
    return jsonify(tasks=ts, workers=ws)

# test-kill endpoint
@app.route("/api/kill/<worker_id>", methods=["POST"])
def api_kill(worker_id):
    evt = shutdown_flags.get(worker_id)
    if not evt:
        return jsonify(success=False, error=f"No such worker {worker_id}"), 404
    evt.set()
    return jsonify(success=True, killed=worker_id)

# ---- Startup ----
if __name__ == "__main__":
    init_db()

    # spawn initial workers
    for i in range(1, NUM_WORKERS + 1):
        wid = f"w{i}"
        evt = threading.Event()
        shutdown_flags[wid] = evt
        thr = threading.Thread(target=worker_loop, args=(wid, evt), daemon=True)
        worker_threads[wid] = thr
        thr.start()

    elect_initial_leader()

    # start election and monitor threads
    threading.Thread(target=election_loop, daemon=True).start()
    threading.Thread(target=monitor_workers, daemon=True).start()

    app.run(host="0.0.0.0", port=5000, debug=False, use_reloader=False)
