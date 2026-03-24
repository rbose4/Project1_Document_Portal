import sys
import os
from operator import itemgetter
from typing import Optional, Dict, Any
from pathlib import Path

from langchain.schema import Document
from langchain_core.messages import BaseMessage
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_community.vectorstores import FAISS

from utils.model_loader import ModelLoader
from exception.custom_exception import DocumentPortalException
from logger import GLOBAL_LOGGER as log
from prompt.prompt_library import PROMPT_REGISTRY
from model.models import PromptType

class ConversationalRAG:
    def __init__(self, session_id:Optional[str],retriever = None) -> None:
        try:
            self.session_id = session_id
            self.llm = self._load_llm()
            
            # Load LLM and prompt templates
            self.contextualize_prompt:ChatPromptTemplate = PROMPT_REGISTRY[PromptType.CONTEXTUALIZE_QUESTION]
            self.qa_prompt:ChatPromptTemplate = PROMPT_REGISTRY[PromptType.CONTEXT_QA]
            
            self.retriever = retriever
            self.chain = None
            
            if self.retriever is not None:
                self._build_lcel_chain()
            
            log.info("ConversationalRAG initialized", session_id=self.session_id)
        except Exception as e:
            log.error("Failed to initialize", session_id = self.session_id)
            raise DocumentPortalException("Failed to initialize ConversationalRAG", e) from e
    
    # -------------- Methods for API --------------------------
    
    def load_retriever_from_faiss(self, 
                                  index_path:str, 
                                  k:int=5,
                                  index_name:str="index",
                                  search_type:str="similarity",
                                  search_kwargs:Optional[Dict[str,Any]]=None):
        try:
            if not Path(index_path).exists():
                raise FileNotFoundError(f"Path doesnot exists: {index_path}")
            if not Path(index_path).is_dir():
                raise NotADirectoryError(f"Path exists but is not a directory: {index_path}")
            
            embeddings = ModelLoader().load_embeddings()
            vectorstore = FAISS.load_local(
                folder_path=index_path, 
                embeddings=embeddings,
                index_name=index_name,
                allow_dangerous_deserialization=True
            )
            
            if search_kwargs is None:
                search_kwargs = {"k":k}
            
            self.retriever = vectorstore.as_retriever(
                search_type=search_type, search_kwargs=search_kwargs
            )
            
            self._build_lcel_chain()
            
            log.info(
                "FAISS retriever loaded successfully",
                index_path=index_path,
                index_name=index_name,
                k=k,
                session_id=self.session_id
            )
            return self.retriever
        except Exception as e:
            log.error("Failed to load retriever from FAISS", error=str(e))
            raise DocumentPortalException("Loading error in ConversationalRAG", e) from e
    
    
    def invoke(self, user_input:str, chat_history:Optional[list[BaseMessage]]=None) -> str:
        try:
            if self.chain is None:
                raise DocumentPortalException(
                    "RAG chain not initialized. Call load_retriever_from_faiss() before invoke()"
                    )
            
            chat_history = chat_history or []
            payload = {"input":user_input, "chat_history":chat_history}
            answer = self.chain.invoke(payload)
            if not answer:
                log.warning("No answer generated", user_input=user_input, session_id=self.session_id)
                return "No answer generated"
            log.info(
                "Chain invoked successfully", 
                    session_id=self.session_id,
                    user_input=user_input,
                    answer_preview=str(answer)[:150]
                )
            return answer
        except Exception as e:
            log.error("Failed to invoke ConversationalRAG", error=str(e))
            raise DocumentPortalException("Error while invoking ConverationalRAG", e) from e
            
    #--------------- Internal Methods -----------------
    def _load_llm(self):
        try:
            llm = ModelLoader().load_llm()
            if not llm:
                raise ValueError("LLM could not be loaded")
            log.info("LLM loaded successfully", session_id=self.session_id)
            return llm
        except Exception as e:
            log.error("Failed to load the LLM", error=str(e))
            raise DocumentPortalException("Error while loading LLM in ConversationalRAG", e) from e
    
    def _build_lcel_chain(self):
        try:
            if self.retriever is None:
                raise DocumentPortalException("Retriever is not set to build the chain")
            
            # 1. Rewrite user question with chat history context
            question_rewriter = ({"input":itemgetter("input"),"chat_history":itemgetter("chat_history")}
                                 | self.contextualize_prompt
                                 | self.llm
                                 |StrOutputParser())
            
            # 2. Retrieve docs for rewritten question
            retrieved_docs = question_rewriter | self.retriever | self._format_docs
            
            # Answer using retrieved context, original user query and chat history
            self.chain = (
                {
                "context":retrieved_docs,
                "input":itemgetter("input"),
                "chat_history":itemgetter("chat_history")
                }
                | self.qa_prompt
                |self.llm
                | StrOutputParser()
            )
            log.info("LCEL graph built successfully", session_id = self.session_id)
        except Exception as e:
            log.error("Failed to build LCEL chain", error=str(e), session_id=self.session_id)
            raise DocumentPortalException("Failed to build LCEL chain", e) from e
    
    @staticmethod
    def _format_docs(docs:list[Document]):
        return "/n/n".join(doc.page_content for doc in docs)