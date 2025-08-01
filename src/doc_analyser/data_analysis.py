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
    def analyze_document(self):
        pass