# utils.py

# Interval (u sekundama) za slanje heartbeat-a (i od strane lidera i od strane radnika)
HEARTBEAT_INTERVAL = 2

# Ako radnik ne ažurira last_seen unutar ovih sekundi, smatramo da je pao
WORKER_TIMEOUT = 5

# Ako lider ne ažurira last_seen unutar ovih sekundi, radnici pokreću election
LEADER_TIMEOUT = 5

# Radnici će svakih 5 sekundi ispisati svoj status (“Alive/Idle”)
STATUS_PRINT_INTERVAL = 5
