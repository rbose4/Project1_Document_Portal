from __future__ import annotations
from pathlib import Path
from fastapi import UploadFile, HTTPException
from typing import Iterable
from pathlib import Path
from langchain.schema import Document
from langchain_community.document_loaders import PyPDFLoader, Docx2txtLoader, TextLoader
from exception.custom_exception import DocumentPortalException
from logger import GLOBAL_LOGGER as log

SUPPORTED_EXTENSIONS = {".pdf",".docx",".txt"}

class FastAPIFileAdapter:
    """Adapter for FastAPI `UploadFile` to a simple file-like object.

    Use this adapter when an API endpoint receives a `FastAPI` `UploadFile`
    and downstream code expects a simpler file-like object with a
    `name` attribute, context-manager support, and a `getbuffer()`
    convenience method.

    Example:
        with FastAPIFileAdapter(upload_file) as f:
            data = f.getbuffer()
    """
    def __init__(self, uf:UploadFile) -> None:
        self._uf = uf
        self.name = uf.filename
        
    def __enter__(self):
        """Enter context and return this adapter.

        Returns:
            FastAPIFileAdapter: the adapter instance providing a file-like
            interface to the underlying `UploadFile`.
        """
        return self
    
    def __exit__(self, exc_type, exc, tb):
        """Ensure the underlying file is closed when exiting the context."""
        self._uf.file.close()
    
    def getbuffer(self) -> bytes:
        """Read and return the full contents of the uploaded file.

        Seeks to the beginning of the underlying file and returns its
        bytes content. This mirrors the behaviour of `UploadFile` buffer
        access in a synchronous context.

        Returns:
            bytes: The raw bytes of the uploaded file.
        """
        self._uf.file.seek(0)
        return self._uf.file.read()

def read_pdf_via_handler(handler, path:str)->str:
    """Dispatch PDF reading to a handler supporting either `read_pdf` or `read_`.

    Some PDF handler implementations expose different method names for
    reading content. This helper prefers `read_pdf` but will fall back to
    `read_` if available.

    Args:
        handler: An object implementing either `read_pdf(path)` or
            `read_(path)`.
        path (str): Path to the PDF file to read.

    Returns:
        str: The extracted text/content from the handler.

    Raises:
        RuntimeError: If the handler implements neither expected method.
    """
    if hasattr(handler,"read_pdf"):
        return handler.read_pdf(path)
    if hasattr(handler,"read_"):
        return handler.read_(path)
    raise RuntimeError("DocHandler has niether read_pdf nor read_ method.")

def load_documents(paths:Iterable[Path]) -> list[Document]:
    """Load files from `paths` into LangChain `Document` objects.

    Selects an appropriate loader based on file extension and aggregates
    the results into a single list of `Document` instances.

    Supported extensions are defined in `SUPPORTED_EXTENSIONS`.

    Args:
        paths (Iterable[Path]): Sequence of filesystem paths to load.

    Returns:
        list[Document]: Loaded and parsed documents.

    Raises:
        DocumentPortalException: If any loader fails during processing.
    """
    docs:list[Document] = []
    try:
        for p in paths:
            ext = p.suffix.lower()
            if ext ==".pdf":
                loader = PyPDFLoader(str(p))
            elif ext ==".docx":
                loader = Docx2txtLoader(str(p))
            elif ext==".txt":
                loader = TextLoader(str(p))
            else:
                log.warning("Unsupported file extension skipped", paht=str(p))
                continue
            docs.extend(loader.load())
        
        log.info("Documents loaded",count=len(docs))
        return docs
            
    except Exception as e:
        log.error("Failed loading documents", error=str(e))
        raise DocumentPortalException("Error loading documents", e) from e
    