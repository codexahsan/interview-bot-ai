# backend/app/shared/llm/client.py

"""
LLM and embedding model factory functions.
"""

from langchain_google_genai import ChatGoogleGenerativeAI, GoogleGenerativeAIEmbeddings

from backend.app.core.config import settings
from backend.app.constants import DEFAULT_TEMPERATURE, DEFAULT_EMBEDDING_MODEL
from backend.app.core.logger import get_logger

logger = get_logger(__name__)


def get_llm():
    """Return a configured Gemini chat model instance."""
    logger.debug(f"Initializing LLM with model {settings.MODEL_NAME}")
    return ChatGoogleGenerativeAI(
        model=settings.MODEL_NAME,
        api_key=settings.GOOGLE_API_KEY,
        temperature=DEFAULT_TEMPERATURE,
    )


def get_embeddings():
    """Return a configured Gemini embeddings model instance."""
    logger.debug(f"Initializing embeddings with model {DEFAULT_EMBEDDING_MODEL}")
    return GoogleGenerativeAIEmbeddings(
        model=DEFAULT_EMBEDDING_MODEL,
        api_key=settings.GOOGLE_API_KEY
    )