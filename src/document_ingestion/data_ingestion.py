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
from langchain.schema import Document

import fitz
from langchain.schema import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.document_loaders import PyPDFLoader, Docx2txtLoader, TextLoader
from langchain_community.vectorstores import FAISS

from utils.model_loader import ModelLoader
from logger import GLOBAL_LOGGER as log
from exception.custom_exception import DocumentPortalException
from utils.file_io import generate_session_id, save_uploaded_files
from utils.document_ops import load_documents


class FaissManager:
    """Manage a FAISS vector index directory and ingestion metadata.

    Responsibilities:
    - Create or load a FAISS index stored under `index_dir`.
    - Track simple ingestion metadata to avoid duplicate document
      insertions (via a fingerprinting strategy).
    - Add new Document chunks to the index and persist both the
      FAISS index files and a JSON metadata file (`ingested_meta.json`).

    The class exposes internal helper methods used by higher-level
    ingestion workflows: `_load_or_create`, `_add_document`, `_exists`,
    and `_fingerprint`.
    """

    def __init__(self, index_dir:Path, model_loader:Optional[ModelLoader]=None) -> None:
        """Initialize the FaissManager.

        Args:
            index_dir (Path): Directory where FAISS index files and
                metadata JSON will be stored.
            model_loader (Optional[ModelLoader]): Optional `ModelLoader`
                instance providing embedding functions. If not provided,
                a new `ModelLoader` will be constructed.

        Behavior:
            - Ensures `index_dir` exists.
            - Loads existing ingestion metadata from `ingested_meta.json`
              if present.
            - Loads embeddings via `model_loader` and prepares an empty
              FAISS reference (`self.vs`) to be populated later.
        """
        self.index_dir = Path(index_dir)
        self.index_dir.mkdir(parents=True, exist_ok=True)

        self.meta_path = self.index_dir / "ingested_meta.json"
        self._meta:Dict[str,Any] = {"rows":{}} # dictionary of rows

        if self.meta_path.exists():
            try:
                self._meta = json.loads(self.meta_path.read_text(encoding="utf-8")) or {"rows":{}}
            except Exception:
                self._meta = {"rows":{}}
        self.model_loader = model_loader or ModelLoader()
        self.embedding = self.model_loader.load_embeddings()
        self.vs:Optional[FAISS] = None

    def _exists(self):
        """Return True if the FAISS index files exist in `index_dir`.

        Checks for the presence of both `index.faiss` and `index.pkl`.
        """
        return (self.index_dir/"index.faiss").exists() and (self.index_dir/"index.pkl").exists()
    
    @staticmethod
    def _fingerprint(text:str, md:Dict[str, Any]) ->str:
        """Create a stable fingerprint for a document chunk.

        If metadata contains a `source` or `file_path`, the fingerprint is
        derived from that (optionally combined with `row_id`) so that the
        same source/row maps to the same key. Otherwise the SHA-256 of
        the text content is returned.

        Args:
            text (str): The chunk text to fingerprint.
            md (Dict[str, Any]): Metadata dict that may contain
                `source`, `file_path`, or `row_id` keys.

        Returns:
            str: A fingerprint string used to detect duplicates.
        """
        src = md.get("source") or md.get("file_path")
        rid = md.get("row_id")

        if src is not None:
            return f"{src}::{'' if rid is None else rid}"
        return hashlib.sha256(text.encode("utf-8")).hexdigest()
    
    def _save_meta(self):
        """Persist the in-memory ingestion metadata to disk.

        Writes `self._meta` to `ingested_meta.json` in the index directory
        using UTF-8 encoding.
        """
        self.meta_path.write_text(json.dumps(self._meta,ensure_ascii=False,indent=2),encoding="utf-8")
    
    def _add_document(self,docs:list[Document]):
        """Add a list of `Document` objects to the FAISS index.

        Args:
            docs (list[Document]): Documents/chunks to add to the index.

        Returns:
            int: Number of documents actually added (duplicates skipped).

        Raises:
            RuntimeError: If the FAISS vectorstore (`self.vs`) is not
                initialized. Call `_load_or_create()` before adding.
        """
        if self.vs is None:
            raise RuntimeError("Call load_or_create() before add_documents")

        new_docs:list[Document] = []

        for d in docs:
            key = self._fingerprint(d.page_content,d.metadata or {})
            if key in self._meta["rows"]:
                continue
            self._meta["rows"][key] = True
            new_docs.append(d)

        if new_docs:
            self.vs.add_documents(new_docs)
            self.vs.save_local(str(self.index_dir))
            self._save_meta()
        return len(new_docs)
    
    def _load_or_create(self,texts:Optional[list[str]]=None, metadatas:Optional[list[dict]]=None):
        """Load an existing FAISS index or create a new one from texts.

        If the index files exist on disk, they are loaded and returned.
        Otherwise, `texts` (and optional `metadatas`) must be provided to
        create a new index which will then be persisted to `index_dir`.

        Args:
            texts (Optional[list[str]]): List of text passages to index.
            metadatas (Optional[list[dict]]): Corresponding metadata for
                each text.

        Returns:
            FAISS: The loaded or newly-created FAISS vectorstore instance.

        Raises:
            DocumentPortalException: If there is no existing index and no
                `texts` provided to create one.
        """
        if self._exists():
            self.vs = FAISS.load_local(str(self.index_dir), 
                                       embeddings=self.embedding,
                                       allow_dangerous_deserialization=True)
            return self.vs

        if not texts:
            raise DocumentPortalException("No existing FAISS index and no data to create one")

        self.vs = FAISS.from_texts(texts=texts, embedding=self.embedding, metadatas=metadatas or [])
        self.vs.save_local(str(self.index_dir))
        return self.vs


class DocHandler:
    """Utility for saving and reading PDF documents within a session.

    `DocHandler` manages a session-specific directory where uploaded
    files are persisted and provides helpers to read PDF content.
    The session directory is created under `data_dir` and identified by
    `session_id` (generated if not provided).
    """

    def __init__(self, data_dir:Optional[str]=None, session_id:Optional[str]=None) -> None:
        """Initialize a `DocHandler`.

        Args:
            data_dir (Optional[str]): Base directory to store session data.
                If omitted the `DATA_STORAGE_PATH` env var is used or a
                default `data/document_analysis` folder under the cwd.
            session_id (Optional[str]): Optional session identifier. A new
                id is generated when not provided.
        """

        self.data_dir = Path( data_dir or os.getenv("DATA_STORAGE_PATH",Path.cwd() / "data"/"document_analysis"))
        self.session_id = session_id or generate_session_id()
        self.session_path = Path(self.data_dir) / self.session_id  #type:ignore

        self.session_path.mkdir(parents=True, exist_ok=True)
        log.info("DocHandler initialized", session_id = self.session_id, session_path = self.session_path)
        
    def save_pdf(self, uploaded_file) -> str:
        """Save an uploaded PDF to the session directory.

        Args:
            uploaded_file: A file-like object (e.g. FastAPI `UploadFile` or
                any object exposing `read()` or `getbuffer()` and a `name`).

        Returns:
            str: Path to the saved PDF file on disk.

        Raises:
            DocumentPortalException: If saving fails or the uploaded file
                is not a PDF.
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
            log.info("PDF saved successfully.", filename=filename, save_path=save_path, session_id=self.session_id)
            return save_path
        except Exception as e:
            log.error("Failed to save PDF", error=str(e), session_id=self.session_id)
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
            log.info("PDF read successfully.", pdf_path=pdf_path, session_id=self.session_id, pages=len(text_chunks))
            return text

        except Exception as e:
            log.error("Failed to read PDF", error=str(e), pdf_path=pdf_path, session_id=self.session_id)
            raise DocumentPortalException(f"Couldn't read PDF file from path: {pdf_path}", e) from e


class DocumentComparator:
    """Compare two PDF documents within a session-scoped workspace.

    `DocumentComparator` provides helpers to save a pair of PDFs
    (reference and actual), read each PDF's text content, combine them
    for downstream comparison, and clean up older sessions.
    """
    
    def __init__(self, base_dir="data/document_compare", session_id = None):
        self.base_dir = Path(base_dir)
        self.session_id = session_id or generate_session_id()
        self.session_path = self.base_dir/ self.session_id
        self.session_path.mkdir(parents=True, exist_ok=True)
        
        log.info("DocumentComparator initialized", session_path=str(self.session_path))
    
    def save_uploaded_files(self, reference_file, actual_file):
        """Persist a reference and an actual PDF to the session folder.

        Both files are validated as PDFs and written to the session
        directory. The method first removes old sessions (keeping the
        configured recent count) and then writes the two files.

        Args:
            reference_file: File-like object for the reference PDF.
            actual_file: File-like object for the actual PDF.

        Returns:
            Tuple[Path, Path]: Paths to the saved reference and actual PDFs.

        Raises:
            DocumentPortalException: When saving fails.
        """
        try:
            self.clean_old_sessions()
            log.info("Existing files deleted successfully.")
            
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
            
            log.info("Files saved successfully.", reference_path=str(ref_path), actual_path=str(act_path))
            return ref_path, act_path
        except Exception as e:
            log.error(f"Error saving uploaded files", error=str(e), session_id=self.session_id)
            raise DocumentPortalException("An error occurred while saving the uploaded files",e) from e
    
    def read__pdf(self,pdf_path:Path) -> str:
        """Extract and return textual content from a PDF file.

        Args:
            pdf_path (Path): Path to the PDF file to read.

        Returns:
            str: Concatenated per-page text extracted from the PDF.

        Raises:
            DocumentPortalException: If the PDF cannot be read or is
                encrypted.
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
            log.info("PDF read successfully", file=str(pdf_path), pages=len(all_text))
            return "\n".join(all_text)
        except Exception as e:
            log.error(f"Error reading PDF",error=str(e), file_path=str(pdf_path))
            raise DocumentPortalException("An error occured while reading the PDF", e) from e
    
    def combine_documents(self) -> str:
        """Aggregate all PDF files in the session directory into one string.

        Iterates over stored PDFs in the session folder, reads each one
        and concatenates them with simple headers identifying filename
        and page numbers. Useful to create a single text body for a
        comparison or analysis chain.

        Returns:
            str: The combined document text.

        Raises:
            DocumentPortalException: If combining fails.
        """
        try:
            doc_parts = []
            for file in sorted(self.session_path.iterdir()):
                if file.is_file() and file.suffix.lower()==".pdf":
                    content = self.read__pdf(file)
                    doc_parts.append(f"Document:{file}\n {content}")
            
            combined_text = "\n\n".join(doc_parts)
            log.info("Documents combined successfully", count=len(doc_parts), session=self.session_id)
            return combined_text
        except Exception as e:
            log.error(f"Error combining documents", error=str(e), session = self.session_id)
            raise DocumentPortalException("An error occurred while combining the documents", e) from e
    
    def clean_old_sessions(self, keep_latest:int=3):
        """Remove older session directories, retaining only the newest N.

        Args:
            keep_latest (int): Number of most recent sessions to keep.
        """
        try:
            if self.base_dir.exists() and self.base_dir.is_dir():
                session_folders = sorted([f for f in self.base_dir.iterdir() if f.is_dir()],reverse=True)
                for folder in session_folders[keep_latest:]:
                    shutil.rmtree(folder,ignore_errors=True)
                    log.info("Old sessions deleted", path=str(folder))
                    
        except Exception as e:
            log.error(f"Error deleting old sessions", error=str(e))
            raise DocumentPortalException("An error occurred while cleaning old sessions", e) from e

class ChatIngestor:
    """High-level helper to ingest documents for conversational retrieval.

    Responsibilities:
    - Accept uploaded files, save them to a temporary session directory.
    - Load and split documents into chunks suitable for vector indexing.
    - Create or update a FAISS vectorstore (via `FaissManager`) and avoid
      duplicate inserts.

    The class supports optional per-session directories so multiple
    ingestions can be isolated.
    """

    def __init__(self,
                 temp_base:str="data",
                 faiss_base:str="faiss_index",
                 use_session_dirs:bool=True,
                 session_id:Optional[str]=None) -> None:
        """Initialize ingestion paths and model loader.

        Args:
            temp_base (str): Base directory for temporary uploaded files.
            faiss_base (str): Base directory for FAISS indices.
            use_session_dirs (bool): When True, create subdirectories named
                after `session_id` under `temp_base` and `faiss_base`.
            session_id (Optional[str]): Optional session identifier. When
                omitted a new session id is generated.
        """
        try:
            self.model_loader = ModelLoader()
            
            self.use_session = use_session_dirs
            self.session_id = session_id or generate_session_id()
            
            self.temp_base = Path(temp_base)
            self.temp_base.mkdir(parents=True, exist_ok=True)
            
            self.faiss_base = Path(faiss_base)
            self.faiss_base.mkdir(parents=True, exist_ok=True)
            
            self.temp_dir = self._resolve_dir(self.temp_base)
            self.faiss_dir = self._resolve_dir(self.faiss_base)
                        
            log.info("ChatIngestor intialized",
                          session_id=self.session_id,
                          temp_dir=str(self.temp_dir),
                          faiss_dir=str(self.faiss_dir),
                          sessionized=self.use_session)
        except Exception as e:
            log.error("Failed to initialize ChatIngestor", error=str(e))
            raise DocumentPortalException("Error while initializing ChatIngestor", e) from e
    
    def _resolve_dir(self, base:Path):
        """Resolve and (optionally) create a session-scoped directory.

        Args:
            base (Path): Base directory to resolve against.

        Returns:
            Path: If `use_session` is True, returns `base / session_id`
            (created if necessary); otherwise returns `base`.
        """
        if self.use_session:
            d = base / self.session_id  # e.g. "faiss_index/abc123"
            d.mkdir(parents=True, exist_ok=True)
            return d
        return base # fallback: "faiss_index/"
    
    def _split(self,docs:List[Document], chunk_size=1000, chunk_overlap=200)->list[Document]:
        """Split loaded `Document` objects into smaller text chunks.

        Uses `RecursiveCharacterTextSplitter` to produce chunks of roughly
        `chunk_size` characters with the specified overlap.

        Args:
            docs (List[Document]): Documents to split.
            chunk_size (int): Target characters per chunk.
            chunk_overlap (int): Character overlap between adjacent chunks.

        Returns:
            list[Document]: A list of chunk `Document` objects.

        Raises:
            DocumentPortalException: If the splitter fails.
        """
        try:
            splitter = RecursiveCharacterTextSplitter(chunk_size=chunk_size, chunk_overlap=chunk_overlap)
            chunks = splitter.split_documents(documents=docs)
            log.info("Documents splitted to chunks", chunks=len(chunks), chunk_size=chunk_size,chunk_overlap=chunk_overlap)
            return chunks
        except Exception as e:
            log.error("Failed to split documents into chunks", error=str(e))
            raise DocumentPortalException("Failed to split documents into chunks", e) from e
    
    def build_retriever(self, 
                        uploaded_files:Iterable, 
                        *, 
                        chunk_size:int=1000,
                        chunk_overlap:int=200,
                        k:int=5,):
        """Process uploaded files and ensure a FAISS retriever is available.

        Workflow:
        1. Save uploaded files to the temporary session directory.
        2. Load documents from disk and split into chunks.
        3. Create or load a FAISS index via `FaissManager` and add new
           chunks while avoiding duplicates.

        Args:
            uploaded_files (Iterable): Iterable of uploaded file-like objects.
            chunk_size (int): Chunk size for splitting documents.
            chunk_overlap (int): Overlap between chunks.
            k (int): Number of nearest neighbors for retrieval (currently
                reserved; not used directly in this method).

        Raises:
            DocumentPortalException: If any step of the ingestion fails.
        """
        try:
            paths = save_uploaded_files(uploaded_files, self.temp_dir)
            docs = load_documents(paths=paths)
            if not docs:
                raise ValueError("No valid documents loaded")

            chunks = self._split(docs, chunk_size=chunk_size,chunk_overlap=chunk_overlap)

            # FaissManager class deals with loading and creating vector store and also with duplicate entries
            fm = FaissManager(self.faiss_dir, self.model_loader)

            texts = [chunk.page_content for chunk in chunks]
            metas = [chunk.metadata for chunk in chunks]

            try:
                vs = fm._load_or_create(texts=texts, metadatas=metas)
            except:
                if fm._exists():
                    self._delete_fiass_index()
                vs = fm._load_or_create(texts=texts, metadatas=metas)

            added = fm._add_document(chunks)
        except Exception as e:
            log.error("Failed to build retriever", error=str(e))
            raise DocumentPortalException("Failed to build retriever", e) from e
    
    def _delete_fiass_index(self):
        """Delete local FAISS index files (used when an index is corrupt).

        Removes `index.faiss` and `index.pkl` from the faiss directory if
        present. Any failure to remove files will raise
        `DocumentPortalException`.
        """
        files_to_delete = ["index.faiss","index.pkl"]

        for filename in files_to_delete:
            file_path = self.faiss_dir/filename

            try:
                file_path.unlink(missing_ok=True)
                log.info(f"File deleted",file_path=file_path)
            except Exception as e:
                log.error(f"Failed to delete file", filename=filename, file_path=file_path)
                raise DocumentPortalException("Failed to delete file", e) from e