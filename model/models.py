from pydantic import BaseModel, Field, RootModel
from typing import Optional, List, Dict, Any, Union
from enum import Enum

class MetaData(BaseModel):
    """
    Metadata for the document.
    """
    Summary:List[str] = Field(default_factory=list, description="Summary of the document")
    Title:str = Field(description="Title of the document")
    Author:str = Field(description="Author of the document")
    DateCreated:str = Field(description="The date at which the document was created.")
    LastModifiedDate:str = Field(description="The date at which the document was last modified.")
    Publisher:str = Field(description="The publisher of the document")
    Language:str = Field(description="The language in which the document is written")
    PageCount:Union[int,str] = Field(description="Total number of pages in the document. It can be an integer or string value Not available") # Can be "Not Available" or an integer
    SentimentTone:str = Field(description="Sentiment of the document. It can be positive, negative or neutral")

class ChangeFormat(BaseModel):
    """
    Change format for the document.
    """
    Page: str
    Changes:str

class SummaryResponse(RootModel[list[ChangeFormat]]):
    pass

class PromptType(str, Enum):
    DOCUMENT_ANALYSIS = "document_analysis"
    DOCUMENT_COMPARISON = "document_comparison"
    CONTEXTUALIZE_QUESTION = "contextualize_question"
    CONTEXT_QA = "context_qa"