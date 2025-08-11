import uuid
import sys
from pathlib import Path
from langchain_community.document_loaders import PyPDFLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.vectorstores import FAISS
from logger.custom_logger import CustomLogger
from exception.custom_exception import DocumentPortalException
from utils.model_loader import ModelLoader

class SingleDocIngestor:
    def __init__(self):
        try:
            self.log = CustomLogger().get_logger(__name__)
        except Exception as e:
            self.log.error("Failed to initialize SingleDOcIngestor", error=str(e))
            raise DocumentPortalException("Failed to initialize SingleDocIngestor", sys)
    
    def ingest_file(self):
        try:
            pass
        except Exception as e:
            self.log.error("Document ingestion failed", error=str(e))
            raise DocumentPortalException("Error during file ingestion", sys)
    
    def _create_retriever(self):
        try:
            pass
        except Exception as e:
            self.log.error("Error occurred while creating the retriever", error=str(e))
            raise DocumentPortalException("Failed to create retriever", sys)