from __future__ import annotations
import os
import sys
import json
import uuid
import hashlib
import shutil
from pathlib import Path
from datetime import datetime, timezone
from typing import Iterable, List, Optional, Dict, Any

import fitz
from langchain.schema import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.document_loaders import PyPDFLoader, Docx2txtLoader, TextLoader
from langchain_community.vectorstores import FAISS

from utils.model_loader import ModelLoader
from logger.custom_logger import CustomLogger
from exception.custom_exception import DocumentPortalException
from utils.file_io import generate_session_id


class FaissManager:
    def __init__(self) -> None:
        pass
    
    def _exists(self):
        pass
    
    @staticmethod
    def _fingerprint():
        pass
    
    def _save_meta(self):
        pass
    
    def _add_document(self):
        pass
    
    def _load_or_create(self):
        pass


class DocHandler:
    def __init__(self, data_dir:Optional[str]=None, session_id:Optional[str]=None) -> None:
        self.log = CustomLogger().get_logger(__name__)
        
        self.data_dir = Path( data_dir or os.getenv("DATA_STORAGE_PATH",Path.cwd() / "data"/"document_analysis"))
        self.session_id = session_id or generate_session_id()
        self.session_path = Path(self.data_dir) / self.session_id  #type:ignore
        
        self.session_path.mkdir(parents=True, exist_ok=True)
        self.log.info("DocHandler initialized", session_id = self.session_id, session_path = self.session_path)
        
    def save_pdf(self, uploaded_file) -> str:
        """ 
        Saves the uploaded PDF file to the session directory.
        Args:
            uploaded_file: File-like object containing the PDF data.
        Returns:
            str: Path to the saved PDF file.
        """
        try:
            filename = os.path.basename(uploaded_file.name)
            if not filename.lower().endswith('.pdf'):
                raise DocumentPortalException("Uploaded file is not a PDF. Only PDFs are allowed")
            
            save_path = Path(self.session_path) / filename
            with open(save_path, 'wb') as f:
                if hasattr(uploaded_file,"read"):
                    f.write(uploaded_file.read())
                else:
                    f.write(uploaded_file.getbuffer())
            self.log.info("PDF saved successfully.", filename=filename, save_path=save_path, session_id=self.session_id)
            return save_path
        except Exception as e:
            self.log.error("Failed to save PDF", error=str(e), session_id=self.session_id)
            raise DocumentPortalException(f"Failed to save PDF: {str(e)}", e) from e    
    
    def read_pdf(self, pdf_path:str) -> str:
        """
        Reads the content of a PDF file from a given path and returns the content as a string.

        Args:
            pdf_path (str): file path to the PDF document.

        Returns:
            str: content of the PDF document
        """
        try:
            text_chunks = []
            with fitz.open(pdf_path) as doc:
                for page_num,page in enumerate(doc,start=1): # type: ignore
                    text_chunks.append(f"\n-- Page {page_num} --\n{page.get_text()}")
            text = ''.join(text_chunks)
            self.log.info("PDF read successfully.", pdf_path=pdf_path, session_id=self.session_id, pages=len(text_chunks))
            return text

        except Exception as e:
            self.log.error("Failed to read PDF", error=str(e), pdf_path=pdf_path, session_id=self.session_id)
            raise DocumentPortalException(f"Couldn't read PDF file from path: {pdf_path}", e) from e


class DocumentComparator:
    def __init__(self) -> None:
        pass
    
    def save_uploaded_file(self):
        pass
    
    def read_pdf(self):
        pass
    
    def combine_documents(self):
        pass
    
    def clean_old_sessions(self):
        pass

class ChatIngestor:
    def __init__(self) -> None:
        pass
    
    def _resolve_dir(self):
        pass
    
    def _split(self):
        pass
    
    def built_retriever(self):
        pass