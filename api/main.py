from fastapi import FastAPI, UploadFile, File, Form, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
import os
from typing import List, Optional, Any, Dict
from pathlib import Path
from contextlib import ExitStack
from src.document_ingestion.data_ingestion import (
    FaissManager, 
    DocHandler, 
    DocumentComparator, 
    ChatIngestor
    )
from src.document_analyzer.data_analysis import DocumentAnalyzer
from src.document_compare.document_comparator import DocumentComparatorLLM
from utils.document_ops import FastAPIFileAdapter, read_pdf_via_handler
from logger import GLOBAL_LOGGER as log

FAISS_BASE = os.getenv("FAISS_BASE","faiss_index")
UPLOAD_BASE = os.getenv("UPLOAD_BASE","data")
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

# ---------------- Document Analyze --------------------
@app.post("/analyze")
async def analyze_documents(file:UploadFile=File(...))->Any:
    try:
        dh = DocHandler()
        # saved_path = dh.save_pdf(FastAPIFileAdapter(file))
        with FastAPIFileAdapter(file) as adapter:
            saved_path = dh.save_pdf(adapter)
        text = read_pdf_via_handler(dh, saved_path)
        analyzer = DocumentAnalyzer()
        result = analyzer.analyze_document(document_text=text)
        return JSONResponse(content=result)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Analysis failed: {e}")

# ---------------- Document Compare --------------------
@app.post("/compare")
async def compare_documents(reference:UploadFile=File(...),actual:UploadFile=File(...)) -> Any:
    try:
        dc = DocumentComparator()
        with FastAPIFileAdapter(reference) as ref_adapter,\
            FastAPIFileAdapter(actual) as act_adapter:
                _ = dc.save_uploaded_files(ref_adapter, act_adapter)
        
        combined_text = dc.combine_documents()
        compLLM = DocumentComparatorLLM()
        df = compLLM.compare_documents(combined_docs=combined_text)
        return {"rows":df.to_dict(orient="records"),"session_id":dc.session_id}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Comparison failed: {e}")
    
    
@app.post("/chat/index")
async def chat_build_index(files:list[UploadFile]=File(...),
                           session_id:Optional[str]=Form(None),
                           use_session_dirs:bool=Form(True),
                           chunk_size:int=Form(1000),
                           chunk_overlap:int=Form(200),
                           k:int=Form(5),
                           )->Any:
    try:
        log.info(f"Indexing chat session, Session ID:{session_id}, Files:{[f.filename for f in files]}")
        with ExitStack() as stack:
            wrapped = [stack.enter_context(FastAPIFileAdapter(f)) for f in files]
            # ChatIngestor class is responsible for storing data into VectorDB
            ci = ChatIngestor(temp_base=UPLOAD_BASE,
                              faiss_base=FAISS_BASE,
                              use_session_dirs=use_session_dirs,
                              session_id=session_id or None)
            ci.build_retriever(wrapped, chunk_size=chunk_size, chunk_overlap=chunk_overlap,k=k)
            
        log.info(f"Index created successfullt for session:{ci.session_id}")
        return{"session_id":ci.session_id,"k":k,"use_session_dirs":use_session_dirs}
    except HTTPException:
        raise
    except Exception as e:
        log.exception("Building chat index failed")
        raise HTTPException(status_code=500, detail=f"Indexingfailed: {e}")    
    
    

@app.post("/chat/query")
async def chat_query():
    try:
        pass
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Query failed: {e}")