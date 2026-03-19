from __future__ import annotations
from pathlib import Path
from fastapi import UploadFile, HTTPException

class FastAPIFileAdapter:
    """
    Adapt FastAPI UploadFile object to standard python file object 
    """
    def __init__(self, uf:UploadFile) -> None:
        self._uf = uf
        self.name = uf.filename
        
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc, tb):
        self._uf.file.close()
    
    def getbuffer(self) -> bytes:
        self._uf.file.seek(0)
        return self._uf.file.read()

def read_pdf_via_handler(handler, path:str)->str:
    if hasattr(handler,"read_pdf"):
        return handler.read_pdf(path)
    if hasattr(handler,"read_"):
        return handler.read_(path)
    raise RuntimeError("DocHandler has niether read_pdf nor read_ method.")