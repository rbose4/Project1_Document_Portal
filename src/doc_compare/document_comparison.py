import sys
from dotenv import load_dotenv
import pandas as pd
from model.models import *
from prompt.prompt_library import PROMPT_LIBRARY as prompt
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
        pass
    
    def compare_documents(self):
        """
        Compare two documents and return a structured comparison.  
        """
        pass
    
    def _format_response(self):
        """
        Format the response from the language model into a structured format.
        """
        pass