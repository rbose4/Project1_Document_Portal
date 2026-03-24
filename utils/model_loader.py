from dotenv import load_dotenv
import os
import sys
from langchain_google_genai import GoogleGenerativeAIEmbeddings, ChatGoogleGenerativeAI
from langchain_groq import ChatGroq
from exception.custom_exception import DocumentPortalException
from logger import GLOBAL_LOGGER as log
from utils.config_loader import load_config
import asyncio


class ModelLoader:
    """
    A utility class to load embedding mdoels and language models.
    """
    def __init__(self):
        load_dotenv()
        self._validate_env()
        self.config = load_config()
        log.info("Configuration loaded successfully", config=self.config)
        
    def _validate_env(self):
        """
        Validate neccesarry environment variables.
        """
        required_env_vars = ["GOOGLE_API_KEY", "GROQ_API_KEY"]
        self.api_keys = {key:os.getenv(key) for key in required_env_vars}
        missing_keys = [k for k,v in self.api_keys.items() if not v]
        if missing_keys:
            log.error("Missing required environment variables", missing_keys=missing_keys)
            raise DocumentPortalException(f"Missing required environment variables:" + "".join(missing_keys)) # type: ignore
        log.info("Environment variables validated", available_keys=[k for k in self.api_keys.keys() if self.api_keys[k]])
        
    def load_embeddings(self):
        """
        Load and return the embedding model based on the configuration.
        """
        try:
            log.info("Loading embedding model ... ")
            model_name = self.config["embedding_model"]["model_name"]
            try:
                asyncio.get_running_loop()
            except RuntimeError:
                asyncio.set_event_loop(asyncio.new_event_loop())
            embedding_model = GoogleGenerativeAIEmbeddings(model=model_name)
            log.info("Embedding model loaded successfully", model_name=model_name)
            return embedding_model
        except Exception as e:
            log.error("Error while loading embedding model", error=str(e))
            raise DocumentPortalException("Failed to load embedding model", e) from e
        
    def load_llm(self):
        """
        Load and return the language model based on the configuration.
        """
        llm_block = self.config["llm"]
        # Set default provider to "groq" if not specified
        provider_key = os.getenv("LLM_PROVIDER", "groq")
        if provider_key not in llm_block:
            log.error(f"LLM provider not found in configuration.", provider_key = provider_key)
            raise DocumentPortalException(f"LLM provider {provider_key} not found in configuration")
        
        llm_config = llm_block[provider_key]
        provider = llm_config.get("provider")
        model_name = llm_config.get("model_name")
        temperature = llm_config.get("temperature", 0.2)
        max_tokens = llm_config.get("max_tokens", 2048)
        
        log.info("Loading language model ... ", provider=provider, model_name=model_name, temperature=temperature, max_tokens=max_tokens)
        
        if provider == "google":
            llm = ChatGoogleGenerativeAI(
                model=model_name,
                temperature=temperature,
                max_output_tokens=max_tokens,
                api_key= self.api_keys["GOOGLE_API_KEY"]
            )
            return llm
        elif provider == "groq":
            llm = ChatGroq(
                model=model_name,
                temperature=temperature,
                api_key=self.api_keys["GROQ_API_KEY"] # type: ignore
            )
            return llm
        else:
            log.error(f"Unsupported LLM provider", provider=provider)
            raise DocumentPortalException(f"Unsupported LLM provider: {provider}") # type: ignore
        
##------------ Standalone test ----------------------------
# if __name__ == "__main__":
#     loader = ModelLoader()
    
#     # Test embedding model
#     embedding_model = loader.load_embeddings()
#     print(f"Embedding model loaded: {embedding_model}")
#     embed_vector = embedding_model.embed_query("Test query for embedding model")
#     print(f"Embedding vector: {len(embed_vector)}")
    
#     # Test LLM model
#     llm_model = loader.load_llm()
#     print(f"LLM model loaded: {llm_model}")
#     response = llm_model.invoke("What is the capital of France?")
#     print(f"LLM response: {response.content}")