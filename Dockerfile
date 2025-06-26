FROM python:3.12-slim

WORKDIR /app
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt \
    && apt-get update && apt-get install -y docker.io \
    && rm -rf /var/lib/apt/lists/*

COPY . .

CMD ["python", "main.py", "--leader"]
