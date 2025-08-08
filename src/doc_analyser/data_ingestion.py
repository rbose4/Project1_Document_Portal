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
    Automatically logs all actions and supports session-based organization.
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
    
    def save_pdf(self, uploaded_file):
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
                raise DocumentPortalException("Uploaded file is not a PDF. Only PDFs are allowed", sys)
            save_path = os.path.join(self.session_path, filename)
            
            with open(save_path, 'wb') as f:
                f.write(uploaded_file.getbuffer())
            self.log.info("PDF saved successfully.", filename=filename, save_path=save_path, session_id=self.session_id)
            return save_path
        except Exception as e:
            app_exc = DocumentPortalException(e, sys)
            self.log.error(app_exc)
            raise app_exc
        
    def read_pdf(self,pdf_path:str):
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
                for page_num,page in enumerate(doc,start=1):
                    text_chunks.append(f"\n-- Page {page_num} --\n{page.get_text()}")
            text = ''.join(text_chunks)
            self.log.info("PDF read successfully.", pdf_path=pdf_path, session_id=self.session_id, pages=len(text_chunks))
            return text

        except Exception as e:
            app_exc = DocumentPortalException(e, sys)
            self.log.error(app_exc)
            raise app_exc
    
if __name__ == "__main__":
    from pathlib import Path
    from io import BytesIO
    # Example usage
    # Replace with the actual path to your PDF file
    pdf_path = r"/Users/ROOPS/Documents/VS-Workspace/LLMOPS/Project1_Document_Portal/data/document_analysis/sample.pdf"
    # pdf_path = r"/Users/ROOPS/Documents/VS-Workspace/LLMOPS/Project1_Document_Portal/data/document_analysis/NIPS-2017-attention-is-all-you-need-Paper.pdf"
    class MockFile:
        def __init__(self, file_path):
            self.name = Path(file_path).name
            self._file_path = file_path      
        def getbuffer(self):
            with open(self._file_path, 'rb') as f:
                return f.read()
    
    mock_file = MockFile(pdf_path)
    handler = DocumentHandler()
    
    try:
        saved_path = handler.save_pdf(mock_file)
        print(f"PDF saved at: {saved_path}")
        content = handler.read_pdf(saved_path)
        print(f"PDF content read successfully: {content[:500]}...")  # Print first 500 characters
    except DocumentPortalException as e:
        print(f"Error: {e}")