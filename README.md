# Distributed Task System

> Jednostavan distribuirani sustav u Pythonu s automatskim election-om među worker-threadovima, failover-om i web UI.

---

##  Sadržaj

1. [Opis projekta](#opis-projekta)  
2. [Struktura repozitorija](#struktura-repozitorija)  
3. [Preduvjeti](#preduvjeti)  
4. [Pokretanje s Docker Compose](#pokretanje-s-docker-compose)  
5. [Konfiguracija broja radnika](#konfiguracija-broja-radnika)  
6. [Horizontalno skaliranje](#horizontalno-skaliranje)  
7. [Dashboard & API](#dashboard--api)  
8. [Failover testiranje](#failover-testiranje)  
9. [Čišćenje baze](#čišćenje-baze)  
10. [Upravljanje logovima](#upravljanje-logovima)  
11. [Daljnji koraci](#daljnji-koraci)  

---

##  Opis projekta

Ovaj projekt implementira jednostavan distribuirani sustav:

- **Worker-threadovi** obrađuju zadatke iz PostgreSQL queuea.  
- **Election** thread među njima bira jednog za **lidera**, bez posebnog procesa.  
- Kada lider “padne”, drugi worker automatski preuzima ulogu.  
- **Monitor** thread automatski restart-a neočekivano umrle radnike.  
- **Flask UI** služi za dodavanje zadataka i praćenje statusa radnika i lidera.

---

##  Struktura repozitorija

.
├── Dockerfile
├── docker-compose.yml
├── main.py # Jedini app: election, monitor, workers & Flask
├── tasks.py # Definicija execute_task(...)
├── db.py # init_db() & get_conn() za PostgreSQL
├── utils.py # HEARTBEAT_INTERVAL, time-outi itd.
├── sites_config.py # Konfiguracija za web-scraping
├── requirements.txt
└── templates/
└── index.html # Frontend dashboard

---

##  Preduvjeti

- **Docker & Docker Compose**  
  _ili_  
- Python 3.12 + virtualenv + PostgreSQL instanca

---

##  Pokretanje s Docker Compose

1. **Ugasit i obrisat stare kontejnere/volume**  
   ```bash
   docker-compose down -v
2.	Buildaj image
3.	docker-compose build
4.	Podigni servise
5.	docker-compose up -d
6.	Provjeri stanje
7.	docker-compose ps
8.	Prati logove
9.	docker-compose logs -f app
10.	Otvori dashboard
http://localhost:5000
________________________________________
 Konfiguracija broja radnika
U main.py promijena:
NUM_WORKERS = 3
na željeni broj (npr. 5), pa ponovo:
docker-compose build
docker-compose up -d
________________________________________
 Horizontalno skaliranje
Povećaj broj instanci aplikacije:
docker-compose up -d --scale app=3
________________________________________
 Dashboard & API
•	Web UI: dodaj zadatke i prat i status
•	/api/status: vraća JSON sa zadacima i radnicima
•	/api/add_task: POST { type, parameters }
•	/api/kill/<worker_id>: POST za test
________________________________________
 Failover testiranje
1.	Ubij lidera:
2.	curl -X POST http://localhost:5000/api/kill/w1
3.	U logu:
4.	[Worker w1] stopping
5.	[Monitor] Worker w1 died → restarting
6.	[Worker w1] started
7.	[Election] Leader w1 dead → new leader: w2
8.	U UI-ju — Trenutni lider: postalo w2.
________________________________________
 Čišćenje baze
docker-compose down -v
docker volume prune
________________________________________
 Upravljanje logovima
Logovi su vremenski obilježeni i koriste Python logging:
2025-06-26 12:00:01 INFO: [Worker w1] started
2025-06-26 12:05:10 INFO: [Monitor] Worker w1 died → restarting
________________________________________


