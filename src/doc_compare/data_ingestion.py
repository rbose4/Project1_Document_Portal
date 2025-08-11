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
    
    def __init__(self, base_dir="data/document_compare"):
        self.log = CustomLogger().get_logger(__name__)
        self.base_dir = Path(base_dir)
        self.base_dir.mkdir(parents=True, exist_ok=True)
    
    def save_uploaded_files(self, reference_file, actual_file):
        try:
            # self.clean_old_sessions()
            # self.log.info("Existing files deleted successfully.")
            
            # updated version of the file
            ref_path = self.base_dir/reference_file.name
            # original file
            act_path = self.base_dir/actual_file.name
            
            if not reference_file.name.endswith('.pdf') or not actual_file.name.endswith('.pdf'):
                raise ValueError("Only PDF files are supported.")
            
            with open(ref_path,"wb") as f:
                f.write(reference_file.getbuffer())
            
            with open(act_path,"wb") as f:
                f.write(actual_file.getbuffer())
            
            self.log.info("Files saved successfully.", reference=str(ref_path), actual=str(act_path))
            return ref_path, act_path
        except Exception as e:
            self.log.error(f"Error saving uploaded files: {e}")
            raise DocumentPortalException("An error occurred while saving the uploaded files", sys)
    
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
                    text = page.get_text()
                    if text.strip():
                        all_text.append(f"\n --------- Page {page_num+1} ------ \n {text}")
            self.log.info("PDF read successfully", file=str(pdf_path), pages=len(all_text))
            return "\n".join(all_text)
        except Exception as e:
            self.log.error(f"Error reading PDF: {e}")
            raise DocumentPortalException("An error occured while reading the PDF", sys)
    
    def combine_pdfs(self) -> str:
        """
        Combine contents of reference and actual PDFs into a single string with file name and page numbers.
        """
        try:
            content_dict = {}
            doc_parts = []
            for file_name in sorted(self.base_dir.iterdir()):
                if file_name.is_file() and file_name.suffix==".pdf":
                    content_dict[file_name.name] = self.read__pdf(file_name)
            
            for file_name, content in content_dict.items():
                doc_parts.append(f"Document:{file_name}\n {content}")
            
            combined_text = "\n\n".join(doc_parts)
            self.log.info("Documents combined successfully", count=len(doc_parts))
            return combined_text
        except Exception as e:
            self.log.error(f"Error combining PDFs: {e}")
            raise DocumentPortalException("An error occurred while combining the PDFs", sys)
                
    def clean_old_sessions(self):
        """
        Deletes exisiting files at the specified paths
        """
        try:
            if self.base_dir.exists() and self.base_dir.is_dir():
                for file in self.base_dir.iterdir():
                    if file.is_file():
                        file.unlink()
                        self.log.info("File deleted", path=str(file))
                    
        except Exception as e:
            self.log.error(f"Error deleting existing files: {e}")
            raise DocumentPortalException("An error occurred while cleaning old sessions", sys)