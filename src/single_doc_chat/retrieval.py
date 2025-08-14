import sys
import os
from dotenv import load_dotenv
from langchain_core.chat_history import BaseChatMessageHistory
from langchain_community.chat_message_histories import ChatMessageHistory
from langchain.vectorstores import FAISS
from langchain_core.runnables.history import RunnableWithMessageHistory
from langchain.chains import create_retrieval_chain, create_history_aware_retriever
from langchain.chains.combine_documents import create_stuff_documents_chain
from utils.model_loader import ModelLoader
from exception.custom_exception import DocumentPortalException
from logger.custom_logger import CustomLogger
from prompt.prompt_library import PROMPT_REGISTRY
from model.models import PromptType

class ConversationalRAG:
    def __init__(self, session_id:str, retriever) -> None:
        try:
            self.log = CustomLogger().get_logger(__name__)
            self.session_id = session_id
            self.retriever = retriever
            self.llm = self._load_llm()
            self.contextualize_prompt = PROMPT_REGISTRY[PromptType.CONTEXTUALIZE_QUESTION.value]
            self.qa_prompt = PROMPT_REGISTRY[PromptType.CONTEXT_QA.value]
            
            self.history_aware_retriever = create_history_aware_retriever(
                self.llm,
                self.retriever,
                self.contextualize_prompt
            )
            self.log.info("Created history-aware retriever", session_id=session_id)
            
            self.qa_chain = create_stuff_documents_chain(
                llm=self.llm,
                prompt=self.qa_prompt
            )
            
            self.rag_chain = create_retrieval_chain(retriever=self.history_aware_retriever,
                                                    combine_docs_chain = self.qa_chain)
                
            self.log.info("Created a RAG chain", session_id=session_id)
            self.chain = RunnableWithMessageHistory(self.rag_chain,
                                                    self._get_session_history,
                                                    input_messages_key="input",
                                                    history_messages_key="chat_history",
                                                    output_messages_key="answer"
            )
            self.log.info("Created a RunnableWithMessageHistory", session_id=session_id)
                    
        except Exception as e:
            self.log.error("Error initializing ConversationalRAG", error=str(e), session_id=session_id)
            raise DocumentPortalException("Failed to initialize ConversationalRAG", sys)
    
    def _load_llm(self):
        try:
            llm = ModelLoader().load_llm()
            self.log.info("LLM loaded successfully", class_name=llm.__class__.__name__)
            return llm
        except Exception as e:
            self.log.error("Error loading LLM via ModelLoader", error=str(e), session_id=self.session_id)
            raise DocumentPortalException("Failed to load LLM", sys)
    
    def _get_session_history(self):
        try:
            return ChatMessageHistory()
        except Exception as e:
            self.log.error("Failed to access session history", error=str(e), session_id=self.session_id)
            raise DocumentPortalException("Failed to retrieve session history", sys)
    
    def load_retriever_from_faiss(self, index_path:str):
        try:
            embedding = ModelLoader().load_embeddings()
            if not os.path.isdir(index_path):
                raise FileNotFoundError(f"FAISS index directory not found at {index_path}")
            vector_store = FAISS.load_local(index_path, embedding)
            self.log.info("Loaded retriever from FAISS index", index_path=index_path)
            return vector_store.as_retriever(search_type='similarity', search_kwargs={"k":5})
        except Exception as e:
            self.log.error("Error loading retriever from FAISS", error=str(e), session_id=self.session_id)
            raise DocumentPortalException("Failed to load retriever from FAISS", sys)
    
    def invoke(self, user_input:str):
        try:
            self.log.info(f"Type of user_input: {type(user_input)}")
            response = self.chain.invoke(
                {"input":user_input},
                config={"configurable":{"session_id":self.session_id}}
            )
            answer = response.get("answer", "No answer")
            if not answer:
                self.log.warning("Empty answer recieved", sessions_id=self.session_id)
            self.log.info("RAG chain invoked successfully", user_input=user_input, answer=answer[:150], session_id=self.session_id)
            return answer
        except Exception as e:
            self.log.error("Error invoking ConversationalRAG", error=str(e), session_id=self.session_id)
            raise DocumentPortalException("Failed to invoke RAG chain", sys)
        