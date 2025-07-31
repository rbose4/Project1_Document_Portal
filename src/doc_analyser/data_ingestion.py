import os
import sys
import fitz
import uuid
from datetime import datetime
from logger.custom_logger import CustomLogger
from exception.custom_exception import DocumentPortalException

class DocumentHandler:
    """
    Handled PDF saving and reading operations.
    Automatically logs all actions and supports session-based oraginzation.
    """
    
    def __init__(self, data_dir=None, session_id=None):
        try:
            self.log = CustomLogger().get_logger(__name__)
            self.data_dir = data_dir or os.getenv("DATA_STORAGE_PATH",
                                                  os.path.join(os.getcwd(), "data","document_analysis")
                                                  )
            self.session_id = session_id or f"session_{datetime.utcnow().strftime('%Y-%m-%d-H%M%S')}_{uuid.uuid4().hex[:8]}"
            
            # Create a session directory 
            self.session_path = os.path.join(self.data_dir, self.session_id)
            os.makedirs(self.session_path, exist_ok=True)
            self.log.info("PDFHandler initialized.", session_id=self.session_id, session_path=self.session_path)
            
        except Exception as e:
            app_exc = DocumentPortalException(e, sys)
            self.log.error(app_exc)
            raise app_exc
    
    def save_pdf(self):
        pass
    def read_pdf(self):
        pass
    
if __name__ == "__main__":
    handler = DocumentHandler()
  