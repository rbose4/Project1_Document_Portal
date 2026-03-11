import uuid
import sys
from pathlib import Path
from datetime import datetime, timezone
from langchain_community.document_loaders import (PyPDFLoader, 
                                                  Docx2txtLoader,
                                                  TextLoader)
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import FAISS
from logger.custom_logger import CustomLogger
from exception.custom_exception import DocumentPortalException
from utils.model_loader import ModelLoader

class DocumentIngestor:
    SUPPORTED_FILE_TYPES =  {'.pdf','.docx','.txt'}
    def __init__(self, temp_dir:str = "data/multi_doc_chat",faiss_dir:str="faiss_index", session_id:str|None = None) -> None:
        try:
            self.log = CustomLogger().get_logger(__name__)
            
            # create base directories
            self.temp_dir = Path(temp_dir)
            self.faiss_dir = Path(faiss_dir)
            self.temp_dir.mkdir(parents= True, exist_ok=True)
            self.faiss_dir.mkdir(parents=True, exist_ok=True)
            
            # sessionized directory paths
            self.session_id = session_id or f"session_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:8]}"
            self.session_temp_dir = self.temp_dir / self.session_id            
            self.session_faiss_dir = self.faiss_dir / self.session_id
            self.session_temp_dir.mkdir(parents=True, exist_ok=True)
            self.session_faiss_dir.mkdir(parents=True, exist_ok=True)
            
            self.model_loader = ModelLoader()
            
            self.log.info("DocumentIngestor initialized",
                          temp_base = str(self.temp_dir),
                          faiss_base = str(self.faiss_dir),
                          session_id = self.session_id,
                          temp_path=str(self.session_temp_dir),
                          faiss_path=str(self.session_faiss_dir))
            
            
        except Exception as e:
            self.log.error("Failed to initialize DocumentIngester", error=str(e))
            raise DocumentPortalException("Intialization error in DocumentIngestor", sys)
    
    def ingest_file(self, upload_files):
        try:
            documents = []
            for uploaded_file in upload_files:
                ext = Path(uploaded_file.name).suffix.lower()
                if ext not in self.SUPPORTED_FILE_TYPES:
                    self.log.warning("Unsupported file skipped", filename=uploaded_file.name)
                    continue
                unique_filename = f"{uuid.uuid4().hex[:8]}{ext}"
                temp_path = self.session_temp_dir / unique_filename
                
                with open(temp_path,'wb') as f:
                    f.write(uploaded_file.read())
                self.log.info("File saved for ingestion",
                              filename=uploaded_file.name,
                              saved_as=temp_path,
                              session_id=self.session_id)
                if ext==".pdf":
                    loader = PyPDFLoader(str(temp_path))
                elif ext==".txt":
                    loader = TextLoader(str(temp_path))
                elif ext == ".docx":
                    loader = Docx2txtLoader(str(temp_path))
                else:
                    self.log.warning("Unsupported file type encountered",file_name=uploaded_file.name)
                    continue
                
                docs = loader.load()
                documents.extend(docs)
                
            if not documents:
                raise DocumentPortalException("No valid documents loaded", sys)
                
            self.log.info("All documents loaded", total_docs = len(documents), session_id=self.session_id)
                
            return self._create_retriever(documents)
                
                
        except Exception as e:
            self.log.error("Failed to ingest files", error=str(e))
            raise DocumentPortalException("Ingestion error in DocumentIngestor", sys)
    
    def _create_retriever(self, documents):
        try:
            # create chunks from document objects
            splitter = RecursiveCharacterTextSplitter(chunk_size = 1000, chunk_overlap = 300)
            chunks = splitter.split_documents(documents=documents)
            self.log.info("Documents split into chunks", total_chunks=len(chunks), session_id=self.session_id)
            
            # Create Faiss vector store
            embedding = self.model_loader.load_embeddings()
            vector_store = FAISS.from_documents(documents=chunks, embedding=embedding)
            
            # Save Faiss index under session folder
            vector_store.save_local(folder_path=str(self.session_faiss_dir))
            self.log.info("FAISS index saved to disk", path=str(self.session_faiss_dir), session_id = self.session_id)
            
            # Create retriever from vector store
            retriever = vector_store.as_retriever(search_type="similarity",search_kwargs={"k":5})
            return retriever
        except Exception as e:
            self.log.error("Failed to create retriever", error=str(e))
            raise DocumentPortalException("Retrieval error in DocumentIngestor", sys)
