import os
import sys
from utils.model_loader import ModelLoader
from logger.custom_logger import CustomLogger
from exception.custom_exception import DocumentPortalException  
from model.models import *
from langchain_core.output_parsers import JsonOutputParser
from langchain.output_parsers import OutputFixingParser
from prompt.prompt_library import *

class DocumentAnalyzer:
    def __init__(self):
        self.log = CustomLogger().get_logger(__name__)
        try:
            self.model_loader = ModelLoader()
            self.llm = self.model_loader.load_llm()
            
            # prepare parsers
            self.parser = JsonOutputParser(pydantic_object=MetaData)
            self.fixing_parser = OutputFixingParser.from_llm(
                llm=self.llm,
                parser=self.parser
            )
            self.prompt = prompt
            self.log.info("DocumentAnalyzer initialized successfully.")
            
        except Exception as e:
            app_exc = DocumentPortalException(e, sys)
            self.log.error(app_exc)
            raise app_exc
    def analyze_document(self, document_text: str) -> dict:
        """
        Analyze the text in the document using the LLM and extract strcutured metadata and summary.
        Args:
            document_text (str): The text content of the document to be analyzed.
        Returns:
            dict: A dictionary containing the structured metadata and summary of the document.
        """
        try:
            chain = self.prompt|self.llm|self.fixing_parser
            
            self.log.info("Metdata analysis started")
            response = chain.invoke({
                "document_text": document_text,
                "format_instructions": self.parser.get_format_instructions()
            })
            self.log.info("Metadata extraction completed", keys=list(response.keys()))
        except Exception as e:
            app_exc = DocumentPortalException(e, sys)
            self.log.error(app_exc)
            raise app_exc