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
    """
    Handles the ingestion of documents, including saving, reading and combining PDF files 
    for comparison with session-based versioning.
    """
    
    def __init__(self, base_dir="data/document_compare", session_id = None):
        self.log = CustomLogger().get_logger(__name__)
        self.base_dir = Path(base_dir)
        self.session_id = session_id or generate_session_id()
        self.session_path = self.base_dir/ self.session_id
        self.session_path.mkdir(parents=True, exist_ok=True)
        
        self.log.info("DocumentComparator initialized", session_path=str(self.session_path))
    
    def save_uploaded_files(self, reference_file, actual_file):
        """
        Save reference and actual files in the session folders and returns their paths.
        """
        try:
            self.clean_old_sessions()
            self.log.info("Existing files deleted successfully.")
            
            # updated version of the file
            ref_path = self.session_path/reference_file.name
            # original file
            act_path = self.session_path/actual_file.name
            
            for fobj, out in ((reference_file,ref_path),(actual_file, act_path)):
                if not fobj.name.lower().endswith(".pdf"):
                    raise ValueError("Only PDF files are allowed")
                with open(out,'wb') as f:
                    if hasattr(fobj,"read"):
                        f.write(fobj.read())
                    else:
                        f.write(fobj.getbuffer())
            
            self.log.info("Files saved successfully.", reference_path=str(ref_path), actual_path=str(act_path))
            return ref_path, act_path
        except Exception as e:
            self.log.error(f"Error saving uploaded files", error=str(e), session_id=self.session_id)
            raise DocumentPortalException("An error occurred while saving the uploaded files",e) from e
    
    def read__pdf(self,pdf_path:Path) -> str:
        """
        Read the text content of a PDF file page by page and return the content as a string.
        """
        try:
            with fitz.open(pdf_path) as doc:
                if doc.is_encrypted:
                    raise ValueError(f"PDF is encrypted:{pdf_path.name}")
                all_text = []
                for page_num in range(doc.page_count):
                    page = doc.load_page(page_num)
                    text = page.get_text() # type: ignore
                    if text.strip():
                        all_text.append(f"\n --------- Page {page_num+1} ------ \n {text}")
            self.log.info("PDF read successfully", file=str(pdf_path), pages=len(all_text))
            return "\n".join(all_text)
        except Exception as e:
            self.log.error(f"Error reading PDF",error=str(e), file_path=str(pdf_path))
            raise DocumentPortalException("An error occured while reading the PDF", e) from e
    
    def combine_documents(self) -> str:
        """
        Combine contents of reference and actual PDFs into a single string with file name and page numbers.
        """
        try:
            doc_parts = []
            for file in sorted(self.session_path.iterdir()):
                if file.is_file() and file.suffix.lower()==".pdf":
                    content = self.read__pdf(file)
                    doc_parts.append(f"Document:{file}\n {content}")
            
            combined_text = "\n\n".join(doc_parts)
            self.log.info("Documents combined successfully", count=len(doc_parts), session=self.session_id)
            return combined_text
        except Exception as e:
            self.log.error(f"Error combining documents", error=str(e), session = self.session_id)
            raise DocumentPortalException("An error occurred while combining the documents", e) from e
    
    def clean_old_sessions(self, keep_latest:int=3):
        """
        Optional method to clean up old sessions folders, keeping only latest N
        """
        try:
            if self.base_dir.exists() and self.base_dir.is_dir():
                session_folders = sorted([f for f in self.base_dir.iterdir() if f.is_dir()],reverse=True)
                for folder in session_folders[keep_latest:]:
                    shutil.rmtree(folder,ignore_errors=True)
                    self.log.info("Old sessions deleted", path=str(folder))
                    
        except Exception as e:
            self.log.error(f"Error deleting old sessions", error=str(e))
            raise DocumentPortalException("An error occurred while cleaning old sessions", e) from e

class ChatIngestor:
    def __init__(self) -> None:
        pass
    
    def _resolve_dir(self):
        pass
    
    def _split(self):
        pass
    
    def built_retriever(self):
        pass