from llm.prompt_templates import memory_prompt_template, pdf_chat_prompt

# Fixed imports for LangChain 2026
from langchain_classic.chains import LLMChain # pyrefly: ignore [missing-import]
from langchain_classic.chains.retrieval_qa.base import RetrievalQA # pyrefly: ignore [missing-import]

from langchain_core.prompts import PromptTemplate # pyrefly: ignore [missing-import]
from langchain_core.messages import HumanMessage, AIMessage # pyrefly: ignore [missing-import]
from langchain_core.documents import Document # pyrefly: ignore [missing-import]
from langchain_core.language_models.llms import LLM # pyrefly: ignore [missing-import]
from typing import Any, List, Optional

from langchain_community.embeddings import HuggingFaceInstructEmbeddings # pyrefly: ignore [missing-import]
from langchain_community.llms import CTransformers # pyrefly: ignore [missing-import]
from langchain_community.vectorstores import Chroma # pyrefly: ignore [missing-import]
from langchain_community.llms import Ollama # pyrefly: ignore [missing-import]

from langchain_text_splitters import RecursiveCharacterTextSplitter # pyrefly: ignore [missing-import]

from operator import itemgetter
from core.utils import load_config
from core.model_loader import (
    ModelLoadError, ModelNotFoundError, ConfigurationError,
    safe_model_create, with_model_error_handling
)
import logging
import os
import chromadb # pyrefly: ignore [missing-import]

logger = logging.getLogger(__name__)

config = load_config()


def load_ollama_model():
    llm = Ollama(model=config["ollama_model"])
    return llm


class MockLLM(LLM):
    def _call(self, prompt: str, stop: Optional[List[str]] = None, **kwargs: Any) -> str:
        return " [MOCK MODE] I am running in mock mode because the local GGUF models were not found. I can still help you test the UI and logic!"

    @property
    def _llm_type(self) -> str:
        return "mock"

    def invoke(self, input: Any, **kwargs: Any) -> Any:
        # Compatibility with Runnable interface
        if isinstance(input, dict) and "human_input" in input:
            return {"text": self._call(input["human_input"])}
        return self._call(str(input))


def create_llm(model_size="large", model_type=None, model_config=None):
    """
    Create language model with comprehensive error handling and recovery.

    Falls back to MockLLM if model loading fails, with detailed logging
    for debugging purposes.

    Args:
        model_size: Size of model (small, medium, large)
        model_type: Type of model (mistral, neural-chat, etc)
        model_config: Model configuration dictionary

    Returns:
        CTransformers model or MockLLM as fallback
    """
    try:
        current_config = load_config()

        if model_type is None:
            model_type = current_config["ctransformers"].get("model_type", "mistral")

        if model_config is None:
            model_config = current_config["ctransformers"].get("model_config", {})

        model_path = current_config["ctransformers"]["model_path"].get(model_size)
        if not model_path:
            logger.warning(f"Model path not found for size '{model_size}', using 'large' as fallback")
            model_path = current_config["ctransformers"]["model_path"].get("large")

        if not model_path:
            logger.error("No model paths configured")
            raise ConfigurationError("No model paths found in configuration")

        if not os.path.exists(model_path):
            logger.error(f"Model file not found at: {model_path}")
            raise ModelNotFoundError(f"Model path does not exist: {model_path}")

        logger.info(f"Loading CTransformers model: {model_path} (type: {model_type})")

        llm = CTransformers(model=model_path, model_type=model_type, config=model_config)
        logger.info("CTransformers model loaded successfully")
        return llm

    except ModelNotFoundError as e:
        logger.warning(f"Model loading failed: {str(e)}. Switching to Mock Mode.")
        return MockLLM()
    except ConfigurationError as e:
        logger.error(f"Configuration error: {str(e)}. Switching to Mock Mode.")
        return MockLLM()
    except Exception as e:
        logger.error(f"Unexpected error loading model: {str(e)}. Switching to Mock Mode.")
        logger.debug(f"Exception type: {type(e).__name__}")
        return MockLLM()


def create_embeddings(embeddings_path=config["embeddings_path"]):
    return HuggingFaceInstructEmbeddings(model_name=embeddings_path)


def create_prompt_from_template(template):
    return PromptTemplate.from_template(template)


def create_llm_chain(llm, chat_prompt):
    return LLMChain(llm=llm, prompt=chat_prompt)


def load_normal_chain():
    return chatChain()


def load_vectordb(embeddings):
    persistent_client = chromadb.PersistentClient(config["chromadb"]["chromadb_path"])

    langchain_chroma = Chroma(
        client=persistent_client,
        collection_name=config["chromadb"]["collection_name"],
        embedding_function=embeddings,
    )

    return langchain_chroma


def load_pdf_chat_chain():
    return pdfChatChain()


def load_retrieval_chain(llm, vector_db):
    return RetrievalQA.from_llm(llm=llm, retriever=vector_db.as_retriever(
        search_kwargs={"k": config["chat_config"]["number_of_retrieved_documents"]}), verbose=True)


def create_pdf_chat_runnable(llm, vector_db, prompt):
    runnable = (
            {
                "context": itemgetter("human_input") | vector_db.as_retriever(
                    search_kwargs={"k": config["chat_config"]["number_of_retrieved_documents"]}),
                "human_input": itemgetter("human_input"),
                "history": itemgetter("history"),
            }
            | prompt | llm.bind(stop=["Human:"])
    )
    return runnable


class pdfChatChain:
    """PDF chat chain with error handling and recovery."""

    def __init__(self):
        """
        Initialize PDF chat chain with comprehensive error handling.

        Logs all loading steps and provides graceful fallbacks if components fail.
        """
        self.llm_chain = None
        self.error = None

        try:
            logger.info("Initializing PDF chat chain...")

            logger.debug("Loading vector database...")
            try:
                embeddings = create_embeddings()
                logger.info("Embeddings created successfully")
            except Exception as e:
                logger.error(f"Failed to create embeddings: {str(e)}")
                raise

            try:
                vector_db = load_vectordb(embeddings)
                logger.info("Vector database loaded successfully")
            except Exception as e:
                logger.error(f"Failed to load vector database: {str(e)}")
                raise

            logger.debug("Creating language model...")
            llm = create_llm()
            logger.info("Language model created successfully")

            logger.debug("Creating prompt template...")
            prompt = create_prompt_from_template(pdf_chat_prompt)
            logger.info("Prompt template created successfully")

            logger.debug("Creating PDF chat runnable...")
            self.llm_chain = create_pdf_chat_runnable(llm, vector_db, prompt)
            logger.info("PDF chat chain initialized successfully")

        except Exception as e:
            logger.error(f"Failed to initialize PDF chat chain: {str(e)}")
            logger.debug(f"Exception type: {type(e).__name__}")
            self.error = str(e)
            self.llm_chain = None

    def run(self, user_input, chat_history):
        """
        Run PDF chat chain with error handling.

        Args:
            user_input: User query
            chat_history: Previous chat messages

        Returns:
            Model response or error message

        Raises:
            RuntimeError: If chain is not initialized
        """
        if self.llm_chain is None:
            error_msg = self.error or "PDF chat chain initialization failed"
            logger.error(f"Cannot run chat: {error_msg}")
            raise RuntimeError(f"PDF chat chain not available: {error_msg}")

        try:
            logger.info("Running PDF chat chain...")
            result = self.llm_chain.invoke(input={"human_input": user_input, "history": chat_history})
            logger.info("PDF chat chain executed successfully")
            return result
        except Exception as e:
            logger.error(f"Error during PDF chat execution: {str(e)}")
            raise


class chatChain:
    """Standard chat chain with error handling and recovery."""

    def __init__(self):
        """
        Initialize chat chain with comprehensive error handling.

        Logs all loading steps and provides graceful fallbacks if components fail.
        """
        self.llm_chain = None
        self.error = None

        try:
            logger.info("Initializing chat chain...")

            logger.debug("Creating language model...")
            llm = create_llm()
            logger.info("Language model created successfully")

            logger.debug("Creating prompt template...")
            chat_prompt = create_prompt_from_template(memory_prompt_template)
            logger.info("Prompt template created successfully")

            logger.debug("Creating LLM chain...")
            self.llm_chain = create_llm_chain(llm, chat_prompt)
            logger.info("Chat chain initialized successfully")

        except Exception as e:
            logger.error(f"Failed to initialize chat chain: {str(e)}")
            logger.debug(f"Exception type: {type(e).__name__}")
            self.error = str(e)
            self.llm_chain = None

    def run(self, user_input, chat_history):
        """
        Run chat chain with error handling.

        Args:
            user_input: User query
            chat_history: Previous chat messages

        Returns:
            Model response or error message

        Raises:
            RuntimeError: If chain is not initialized
        """
        if self.llm_chain is None:
            error_msg = self.error or "Chat chain initialization failed"
            logger.error(f"Cannot run chat: {error_msg}")
            raise RuntimeError(f"Chat chain not available: {error_msg}")

        try:
            logger.info("Running chat chain...")
            result = self.llm_chain.invoke(
                input={"human_input": user_input, "history": chat_history},
                stop=["Human:"]
            )
            logger.info("Chat chain executed successfully")
            return result["text"]
        except Exception as e:
            logger.error(f"Error during chat execution: {str(e)}")
            raise

