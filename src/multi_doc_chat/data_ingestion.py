import uuid
import sys
from pathlib import Path
from datetime import datetime, timezone
from langchain_community.document_loaders import PyPDFLoader, TextLoader, Docx2txtLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.vectorstores import FAISS
from logger.custom_logger import CustomLogger
from exception.custom_exception import DocumentPortalException
from utils.model_loader import ModelLoader

SUPPORTED_EXTENSIONS = {".pdf", ".docx", ".txt"}

class DocumentIngestor:
    def __init__(self, temp_dir:str="data/multi_doc_chat", faiss_dir:str="faiss_index", session_id:str=None):
        try:
            self.log = CustomLogger().get_logger(__name__)
            
            # create base directory for temporary files
            self.temp_dir = Path(temp_dir)
            self.faiss_dir = Path(faiss_dir)
            
            self.temp_dir.mkdir(parents=True, exist_ok=True)
            self.faiss_dir.mkdir(parents=True, exist_ok=True)
            
            # Create session paths
            self.session_id = session_id or f"session_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:8]}"
            self.session_temp_dir = self.temp_dir / self.session_id
            self.session_faiss_dir = self.faiss_dir / self.session_id
            self.session_temp_dir.mkdir(parents=True, exist_ok=True)
            self.session_faiss_dir.mkdir(parents=True, exist_ok=True)
            
            self.model_loader = ModelLoader()
            
            self.log.info("Document Ingestor initialized", 
                          temp_base = str(self.temp_dir),
                          faiss_base = str(self.faiss_dir),
                          session_id = self.session_id,
                          temp_path = str(self.session_temp_dir),
                          faiss_path = str(self.session_faiss_dir))
            
        except Exception as e:
            self.log.error("Failed to initialize DocumentIngestor", error=str(e))
            raise DocumentPortalException("Error while initializing DocumentIngestor", sys)
    
    def ingest_files(self, uploaded_files):
        try:
            documents = []
            for upload_file in uploaded_files:
                extn = Path(upload_file).name.suffix.lower()
                if extn not in SUPPORTED_EXTENSIONS:
                    self.log.warning("Unsupported file extension", file_name=upload_file.name, extn=extn)
                    continue
                
                unique_filename = f"{uuid.uuid4().hex[:8]}{extn}"
                temp_path = self.session_temp_dir / unique_filename
                
                with open(temp_path, "wb") as f:
                    f.write(upload_file.read())
                
                self.log.info("File saved in session folder for ingestion", 
                              filename = upload_file.name,
                              saved_path=str(temp_path),
                              session_id = self.session_id)
                
                if extn == ".pdf":
                    loader = PyPDFLoader(temp_path)
                elif extn == ".docx":
                    loader = Docx2txtLoader(temp_path)
                elif extn == ".txt":
                    loader = TextLoader(temp_path)
                else:
                    self.log.warning("Unsupported file type encountered", filename=upload_file.name)
                
                docs = loader.load()
                documents.extend(docs)
            
            if not documents:
                raise DocumentPortalException("No valid documents found in uploaded files", sys)
            
            self.log.info("All documents loaded", total_docs = len(documents), session_id = self.session_id)
            return self._create_retriever(documents)
                
        except Exception as e:
            self.log.error("Failed to ingest files", error=str(e))
            raise DocumentPortalException("Error while ingesting files", sys)
    
    def _create_retriever(self, documents):
        try:
            splitter = RecursiveCharacterTextSplitter(chunk_size = 1000, chunk_overlap=300)
            chunks = splitter.split_documents(documents=documents)
            self.log.info("Documents split into chunks", total_chunks=len(chunks), session_id = self.session_id)
            
            embedding = self.model_loader.load_embeddings()
            vector_store = FAISS.from_documents(documents=chunks, embedding=embedding)
            
            # save FAISS index under sesssion folder
            vector_store.save_local(folder_path=str(self.session_faiss_dir))
            self.log.info("FAISS index saved to disk", path=str(self.session_faiss_dir), session_id=self.session_id)
            
            # create retriever
            retriever = vector_store.as_retriever(search_type="similarity", search_kwargs={"k":5})
            self.log.info("FAISS retriever created and ready to use", session_id = self.session_id)
            return retriever 
        except Exception as e:
            self.log.error("Failed to create retriever", error=str(e))
            raise DocumentPortalException("Error while creating retriever", sys)