# worker.py
from fastapi import FastAPI
from pydantic import BaseModel
from typing import Dict
import re

app = FastAPI()

class ProcessData(BaseModel):
    text: str
    analysisType: str

@app.post("/process")
def process(data: ProcessData) -> Dict[str, str]:
    text = data.text
    analysis_type = data.analysisType

    # Različite analize temeljem analize tipa
    if analysis_type == 'pattern1':
        result = find_pattern1(text)
    elif analysis_type == 'pattern2':
        result = find_pattern2(text)
    elif analysis_type == 'pattern3':
        result = find_pattern3(text)
    elif analysis_type == 'pattern4':
        result = find_pattern4(text)
    elif analysis_type == 'pattern5':
        result = find_pattern5(text)
    elif analysis_type == 'pattern6':
        result = find_pattern6(text)
    elif analysis_type == 'pattern7':
        result = find_pattern7(text)
    elif analysis_type == 'pattern8':
        result = find_pattern8(text)
    elif analysis_type == 'pattern9':
        result = find_pattern9(text)
    elif analysis_type == 'pattern10':
        result = find_pattern10(text)
    else:
        result = 'Unknown analysis type'

    return {"result": result}

def find_pattern1(text: str) -> str:
    pattern = r'\b\w{5}\b'  # Riječi dužine 5 znakova
    matches = re.findall(pattern, text)
    return f'Pattern 1 matches: {matches}'

def find_pattern2(text: str) -> str:
    pattern = r'\d{3}-\d{2}-\d{4}'  # Obrasci slični SSN (npr. 123-45-6789)
    matches = re.findall(pattern, text)
    return f'Pattern 2 matches: {matches}'

def find_pattern3(text: str) -> str:
    pattern = r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}'  # Email adrese
    matches = re.findall(pattern, text)
    return f'Pattern 3 matches: {matches}'

def find_pattern4(text: str) -> str:
    pattern = r'https?://[^\s/$.?#].[^\s]*'  # URL-ovi
    matches = re.findall(pattern, text)
    return f'Pattern 4 matches: {matches}'

def find_pattern5(text: str) -> str:
    pattern = r'\b\d{4}-\d{2}-\d{2}\b'  # Datumi u formatu YYYY-MM-DD
    matches = re.findall(pattern, text)
    return f'Pattern 5 matches: {matches}'

def find_pattern6(text: str) -> str:
    pattern = r'\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}'  # Telefonski brojevi u formatu (123) 456-7890
    matches = re.findall(pattern, text)
    return f'Pattern 6 matches: {matches}'

def find_pattern7(text: str) -> str:
    pattern = r'#[0-9A-Fa-f]{6}'  # Heksadecimalne boje u formatu #RRGGBB
    matches = re.findall(pattern, text)
    return f'Pattern 7 matches: {matches}'

def find_pattern8(text: str) -> str:
    pattern = r'\b\d{1,3}(?:,\d{3})*(?:\.\d{2})?\b'  # Brojevi u formatu 1,000.00
    matches = re.findall(pattern, text)
    return f'Pattern 8 matches: {matches}'

def find_pattern9(text: str) -> str:
    pattern = r'\b\d{2}/\d{2}/\d{4}\b'  # Datumi u formatu DD/MM/YYYY
    matches = re.findall(pattern, text)
    return f'Pattern 9 matches: {matches}'

def find_pattern10(text: str) -> str:
    pattern = r'\b[A-Z][a-z]*\b'  # Riječi s početnim velikim slovom
    matches = re.findall(pattern, text)
    return f'Pattern 10 matches: {matches}'

@app.get("/health")
def health_check():
    return {"status": "ok"}

if __name__ == "__main__":
    import sys
    import uvicorn
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8081
    uvicorn.run(app, host="0.0.0.0", port=port)
