import sys
import os
from operator import itemgetter
from typing import List, Optional

from langchain_core.messages import BaseMessage
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import RunnablePassthrough
from langchain.vectorstores import FAISS


from utils.model_loader import ModelLoader
from exception.custom_exception import DocumentPortalException
from logger.custom_logger import CustomLogger
from prompt.prompt_library import PROMPT_REGISTRY
from model.models import PromptType

class ConversationalRAG:
    def __init__(self, session_id:str, retriever=None):
        try:
            self.log = CustomLogger().get_logger(__name__)
            
            self.session_id = session_id
            self.llm = self._load_llm()
            self.contextualize_prompt = PROMPT_REGISTRY[PromptType.CONTEXTUALIZE_QUESTION.value]
            self.qa_prompt = PROMPT_REGISTRY[PromptType.CONTEXT_QA.value]
            
            if retriever is None:
                raise ValueError("Retriever cannot be None")
            self._build_lcel_chain()
        except Exception as e:
            self.log.error("Failed to initialize ConversationalRAG", error = str(e))
            raise DocumentPortalException("Failed to initialize ConversationalRAG", sys)
            
    
    def load_retriever_from_faiss(self, index_path:str):
        """
        Load the FAISS vector store from disk and create a retriever.
        """
        try:
            embedding = ModelLoader().load_embeddings()
            
            if not os.path.exists(index_path):
                raise FileNotFoundError(f"FAISS index directory not found {index_path}")
            vector_store = FAISS.load_local(folder_path=index_path,
                                            embedding=embedding,
                                            allow_dangerous_deserialization=True) # only if you trust the index
            self.retriever = vector_store.as_retriever(search_type="similarity", search_kwargs = {"k": 5})
            self.log.info("FAISS retriever loaded sucessfully from the disk", 
                          index_path = index_path, 
                          session_id = self.session_id)
            self._build_lcel_chain()
            return self.retriever
        except Exception as e:
            self.log.error("Failed to load retriever from FAISS", error = str(e))
            raise DocumentPortalException("Loading error while loading FAISS vector DB in ConversationalRAG", sys)
    
    def invoke(self,user_input:str, chat_history: Optional[List[BaseMessage]]=None)->str:
        try:
            chat_history = chat_history or []
            payload = {"input":user_input,
                       "chat_history": chat_history}
            answer = self.chain.invoke(payload)
            if not answer:
                self.log.warning("No answer generated", suer_input=user_input, session_id = self.session_id)
                return "no answer generated"
            self.log.info("Chain invoked successfully", 
                          user_input=user_input, 
                          session_id = self.session_id,
                          answer_preview = answer[:150]
                          )
            
            return answer
        except Exception as e:
            self.log.error("Failed to invoke ConversationalRAG", error = str(e))
            raise DocumentPortalException("Failed to invoke ConversationalRAG", sys)
    
    def _load_llm(self):
        try:
            llm = ModelLoader().load_llm()
            if llm is None:
                raise ValueError("LLM not found")
            self.log.info("LLM loaded successfully", session_id = self.session_id)
            return llm
        except Exception as e:
            self.log.error("Failed to load LLM", error = str(e))
            raise DocumentPortalException("Error while loading LLM in ConversationalRAG", sys)
    
    @staticmethod
    def _format_docs(docs):
        return "\n\n".join([d.page_content for d in docs])
    
    def _build_lcel_chain(self):
        try:
            if self.retriever is None:
                raise DocumentPortalException("Retrieved not loaded to build the LCEL chain", sys)
            
            question_rewritter = (
                {
                    "input":itemgetter("input"),
                    "chat_history":itemgetter("chat_history")
                }
            | self.contextualize_prompt
            | self.llm 
            | StrOutputParser()
            )
            
            retrieve_docs = question_rewritter| self.retriever| self._format_docs
            
            self.chain = ({
                "context":retrieve_docs,
                "input":itemgetter("input"),
                "chat_history":itemgetter("chat_history"),
            }
            | self.qa_prompt
            | self.llm
            | StrOutputParser()
            )
            
        except Exception as e:
            self.log.error("Failed to build LCEL chain", error = str(e))
            raise DocumentPortalException("Error while building LCEL chain in ConversationalRAG", sys)