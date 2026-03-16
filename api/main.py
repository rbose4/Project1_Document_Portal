from fastapi import FastAPI, UploadFile, File, Form, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
import os
from typing import List, Optional, Any, Dict
from pathlib import Path
from src.document_ingestion.data_ingestion import (
    FaissManager, 
    DocHandler, 
    DocumentComparator, 
    ChatIngestor
    )

BASE_DIR = Path(__file__).resolve().parent.parent

app = FastAPI(title="Document Portal API", version="0.1")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"]
)

# serve static templates
app.mount("/static", StaticFiles(directory=BASE_DIR / "static"), name="static")
templates = Jinja2Templates(directory=BASE_DIR / "templates")

@app.get("/", response_class=HTMLResponse)
async def serve_ui(request: Request):
    return templates.TemplateResponse("index.html",{"request":request})

@app.get("/health")
def health() -> Dict[str, str]:
    return {"status":"ok", "service":"document-portal"}

@app.post("/analyze")
async def analyze_documents(file:UploadFile=File(...))->Any:
    try:
        pass
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Analysis failed: {e}")

@app.post("/compare")
async def compare_documents(referece:UploadFile=File(...),actual:UploadFile=File(...)) -> Any:
    try:
        pass
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Comparison failed: {e}")
    
    
@app.post("/chat/index")
async def chat_build_index()->Any:
    try:
        pass
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Indexingfailed: {e}")    
    
    

@app.post("/chat/query")
async def chat_query():
    try:
        pass
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Query failed: {e}")