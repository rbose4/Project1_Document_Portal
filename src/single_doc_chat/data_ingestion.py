import uuid
import sys
from pathlib import Path
from datetime import datetime, timezone
from langchain_community.document_loaders import PyPDFLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.vectorstores import FAISS
from logger.custom_logger import CustomLogger
from exception.custom_exception import DocumentPortalException
from utils.model_loader import ModelLoader
import io
from typing import List

class SingleDocIngestor:
    def __init__(self,data_dir:str="data/single_doc_chat", faiss_dir:str="faiss_index"):
        """
        Args:
            data_dir (str, optional): _description_. Defaults to "data/single_doc_chat".
            faiss_dir (str, optional): _description_. Defaults to "faiss_index".
        Summary:
        This class is used to ingest a single document into the document portal for chat bot use.

        """
        try:
            self.log = CustomLogger().get_logger(__name__)
            
            self.data_dir = Path(data_dir)
            self.data_dir.mkdir(parents=True, exist_ok=True)
            
            self.faiss_dir = Path(faiss_dir)
            self.faiss_dir.mkdir(parents=True, exist_ok=True)
            
            self.model_loader = ModelLoader()
            self.log.info("SingleDocIngestor initialized", temp_path=str(self.data_dir), faiss_path=str(self.faiss_dir))
        except Exception as e:
            self.log.error("Failed to initialize SingleDOcIngestor", error=str(e))
            raise DocumentPortalException("Failed to initialize SingleDocIngestor", sys)
    
    def ingest_file(self, uploaded_files:List[io.BufferedReader]):
        """
        Save the uploaded file to the data directory, load the documents and return the retriever 
        created from the documents. 
        """
        try:
            documents = []
            for uploaded_file in uploaded_files:
                unique_filename = f"session_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:8]}.pdf"
                temp_path = self.data_dir/unique_filename
                
                with open(temp_path, "wb") as f_out:
                    f_out.write(uploaded_file.read())
                self.log.info("PDF saved for ingestion", file_name=uploaded_file)
                
                loader = PyPDFLoader(temp_path)
                docs = loader.load()
                documents.extend(docs)
            self.log.info("PDF files loaded", count=len(documents))
            return self._create_retriever(documents)
                
        except Exception as e:
            self.log.error("Document ingestion failed", error=str(e))
            raise DocumentPortalException("Error during file ingestion", sys)
    
    def _create_retriever(self, documents):
        try:
            
            # Split the documents into chunks
            text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=300)
            chunks = text_splitter.split_documents(documents)
            self.log.info("Text split into chunks", count=len(chunks))
            
            # load embeddings and create the vectore store
            embeddings = self.model_loader.load_embeddings()
            vector_store = FAISS.from_documents(documents=chunks, 
                                                embedding=embeddings)
            # Save Faiss index
            vector_store.save_local(str(self.faiss_dir))
            self.log.info("Faiss index created and saved.", faiss_path=self.faiss_dir)
            
            retriever = vector_store.as_retriever(
                search_type="similarity",
                search_kwargs={"k":5}
            )
            self.log.info("Retriever created successfully", retriever_type=type(retriever))
            return retriever
            
        except Exception as e:
            self.log.error("Error occurred while creating the retriever", error=str(e))
            raise DocumentPortalException("Failed to create retriever", sys)