from pydantic import BaseModel, Field, RootModel
from typing import Optional, List, Dict, Any, Union

class MetaData(BaseModel):
    """
    Metadata for the document.
    """
    Summary:List[str] = Field(default_factory=list, description="Summary of the document")
    Title:str
    Author:str
    DateCreated:str
    LastModifiedDate:str
    Publisher:str
    Language:str
    PageCount:Union[int,str] # Can be "Not Available" or an integer
    SentimentTone:str

class ChangeFormat(BaseModel):
    """
    Change format for the document.
    """
    Page: str
    Changes:str

class SummaryResponse(RootModel[list[ChangeFormat]]):
    pass