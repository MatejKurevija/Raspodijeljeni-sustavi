# main.py
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import httpx

app = FastAPI()

# Definiraj dozvoljene domene
origins = [
    "http://localhost:8000",
    "http://localhost:8080",  # Port gdje će tvoj frontend biti dostupan
    "http://127.0.0.1:8000",  # Localhost IP
]

# Dodaj CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],  # Dozvoli sve metode (GET, POST, itd.)
    allow_headers=["*"],  # Dozvoli sva zaglavlja
)

workers = [
    'http://localhost:8081/process',
    'http://localhost:8082/process'
]
health_check_urls = [
    'http://localhost:8081/health',
    'http://localhost:8082/health'
]

class ProcessData(BaseModel):
    text: str
    analysisType: str

async def check_worker_health(worker_url: str) -> bool:
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(worker_url)
            return response.status_code == 200
        except httpx.RequestError:
            return False

@app.post("/process")
async def process(data: ProcessData):
    text = data.text
    analysis_type = data.analysisType
    valid_workers = []
    worker_responses = []

    # Provjeri zdravlje radnika
    for health_url in health_check_urls:
        if await check_worker_health(health_url):
            valid_workers.append(health_url.replace('/health', '/process'))

    if not valid_workers:
        raise HTTPException(status_code=503, detail="No workers available")

    # Raspodijeli zadatak validnim radnicima
    async with httpx.AsyncClient() as client:
        for worker_url in valid_workers:
            try:
                response = await client.post(worker_url, json={'text': text, 'analysisType': analysis_type})
                worker_responses.append(response.json())
            except httpx.RequestError as e:
                print(f'Worker failed: {worker_url} with error {e}')
                worker_responses.append({'result': f'Failed to connect to worker: {worker_url}'})

    return worker_responses

@app.options("/process")
async def options_process():
    return {}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
