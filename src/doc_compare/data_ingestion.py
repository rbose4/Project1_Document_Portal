import sys
import fitz
import uuid
from pathlib import Path
from datetime import datetime, timezone
from logger.custom_logger import CustomLogger
from exception.custom_exception import DocumentPortalException

class DocumentIngestion:
    """
    Handles the ingestion of documents, including saving, reading and combining PDF files 
    for comparison with session-based versioning.
    """
    
    def __init__(self):
        pass
    
    def save_uploaded_files(self):
        pass
    
    def read__pdf(self):
        pass
    
    def combine_pdfs(self):
        pass
    
    def clean_old_sessions(self):
       pass