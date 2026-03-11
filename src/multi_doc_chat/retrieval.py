import sys
import os
from operator import itemgetter
from typing import List, Optional
from langchain_core.messages import BaseMessage
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import RunnablePassthrough
from langchain_core.prompts import ChatPromptTemplate
from langchain_community.vectorstores import FAISS
from utils.model_loader import ModelLoader
from exception.custom_exception import DocumentPortalException
from logger.custom_logger import CustomLogger
from prompt.prompt_library import PROMPT_REGISTRY
from model.models import PromptType

class ConversationalRAG:
    
    def __init__(self, session_id:str, retriever=None) -> None:
        """
        Initializes the ConversationalRAG class with the session id and retriever.
        """
        try:
            self.log = CustomLogger().get_logger(__name__)
            
            self.session_id = session_id
            self.llm = self._load_llm()
            
            self.contextualized_prompt:ChatPromptTemplate = PROMPT_REGISTRY[PromptType.CONTEXTUALIZE_QUESTION.value]
            self.qa_prompt:ChatPromptTemplate = PROMPT_REGISTRY[PromptType.CONTEXT_QA.value]
            
            if retriever is None:
                raise ValueError("Retriever cannot be None")
            self.retriever = retriever
            self._build_lcel_chain()
            
            self.log.info("Conversational RAG initialized", session_id=self.session_id)
            
        except Exception as e:
            self.log.error("Failed to initialize Conversational RAG", error=str(e))
            raise DocumentPortalException("Initialization error in Conversational RAG", sys)
            
    
    def load_retriever_from_faiss(self, index_path:str):
        """
        Load FAISS vector store from disk and convert to retriever    
        Args:
            index_path (str): path to faiss.pkl file
        """
        try:
            embeddings = ModelLoader().load_embeddings()
            
            vector_store = FAISS.load_local(folder_path=index_path, 
                                            embeddings=embeddings, 
                                            allow_dangerous_deserialization=True) # only if you trust the index
            self.retriever = vector_store.as_retriever(search_type="similarity", search_kwargs={"k":5})
            self.log.info("FAISS retriever loaded successfully", index_path=index_path, session_id=self.session_id)
            return self.retriever
        except Exception as e:
            self.log.error("Failed to load retriever from FAISS", error=str(e))
            raise DocumentPortalException("Loading error in Converdational RAG", sys)
    def invoke(self,user_input:str, chat_history:Optional[List[BaseMessage]]=None)->str:
        """
        Invoke the ConversationalRAG chain to generate a response.
        """
        try:
            chat_history = chat_history or []
            payload = {"input":user_input,"chat_history":chat_history}
            answer = self.chain.invoke(payload)
            if not answer:
                self.log.warning("No answer generated from ConversationalRAG",
                                 user_input = user_input, 
                                 session_id=self.session_id)
                return "No answer generated"
            self.log.info("Chain invoked successfully", 
                          session_id= self.session_id,
                          user_input=user_input,
                          answer_preview = answer[:150])
            return answer
        except Exception as e:
            self.log.error("Failed to invoke ConversationalRAG", error=str(e))
            raise DocumentPortalException("Invocation error in ConversationalRAG", sys)
    
    def _load_llm(self):
        """
        Loads the LLM by calling the load_llm() in utils
        """
        try:
            llm = ModelLoader().load_llm()
            if not llm:
                raise ValueError("LLM couldnot be loaded")
            self.log.info("Successfully loaded LLM", session_id=self.session_id)
            return llm
        except Exception as e:
            self.log.error("Failed to load LLM",error=str(e))
            raise DocumentPortalException("Error while loading LLM in ConversationalRAG", sys)
    
    @staticmethod
    def _format_docs(docs):
        return "\n\n".join(doc.page_content for doc in docs)
    
    def _build_lcel_chain(self):
        """
        Creates and return the RAG chain (using LCEL)that will be used to generate answers.
        """
        try:
            if self.retriever is None:
                raise DocumentPortalException("Retrieved not loaded to build the LCEL chain", sys)
            # Rewrite the question using chat history and input query
            question_rewriter = (
                {"input":itemgetter("input"),"chat_history":itemgetter("chat_history")}
                |self.contextualized_prompt
                |self.llm
                |StrOutputParser()
                )
            
            # Retrieve the documents based on the rewritten query
            retrieved_docs = question_rewriter| self.retriever | self._format_docs
            
            # Build the final chain context, original input and chat history
            self.chain = ({
                "context":retrieved_docs,
                "input":itemgetter("input"),
                "chat_history":itemgetter("chat_history")
            }
            | self.qa_prompt
            | self.llm 
            | StrOutputParser())
            
            self.log.info("LCEL graph built successfully", session_id = self.session_id)
            
        except Exception as e:
            self.log.error("Failed to build the chain in ConversationalRAG", error=str(e))
            raise DocumentPortalException("Error while building the chain in ConversationalRAG", sys)
    
    