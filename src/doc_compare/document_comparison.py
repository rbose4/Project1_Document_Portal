import sys
from dotenv import load_dotenv
import pandas as pd
from model.models import *
from prompt.prompt_library import PROMPT_REGISTRY as prompt
from utils.model_loader import ModelLoader
from logger.custom_logger import CustomLogger
from exception.custom_exception import DocumentPortalException
from langchain_core.output_parsers import JsonOutputParser
from langchain.output_parsers import OutputFixingParser

class DocumentComparatorLLM:
    """
    Handles the comparison of two documents using a language model.
    It compares the contents of the documents and identifies differences page-wise.
    """
    def __init__(self):
        self.log = CustomLogger().get_logger(__name__)
        try:
            self.loader = ModelLoader()
            self.llm = self.loader.load_llm()
            self.parser = JsonOutputParser(pydantic_object=SummaryResponse)
            self.fixing_parser = OutputFixingParser.from_llm(
                llm=self.llm,
                parser=self.parser
            )
            self.prompt = prompt["document_comparison"]
            self.chain = self.prompt | self.llm | self.parser
            self.log.info("DocumentComparatorLLM initialized successfully with model and parser.")
        except Exception as e:
            self.log.error(f"Error initializing DocumentComparatorLLM: {str(e)}")
            raise DocumentPortalException("Error initializing DocumentComparatorLLM",sys)
    
    def compare_documents(self, combined_docs:str) -> pd.DataFrame:
        """
        Compare two documents and return a structured comparison.  
        """
        try:
            inputs = {
                "combined_documents": combined_docs,
                "format_instructions":self.parser.get_format_instructions()
            }
            self.log.info("Invoking document comparison LLM chain")
            response = self.chain.invoke(inputs)
            return self._format_response(response_parsed=response)
        except Exception as e:
            self.log.error(f"Error comparing documents: {str(e)}")
            raise DocumentPortalException("Error comparing documents",sys)
    
    def _format_response(self, response_parsed:list[dict]) ->pd.DataFrame:
        """
        Format the response from the language model into a structured format.
        """
        try:
            df = pd.DataFrame(response_parsed)
            return df
        except Exception as e:
            self.log.error(f"Error formatting response: {str(e)}")
            raise DocumentPortalException("Error formatting response",sys)