# backend/app/rag/hybrid_retriever.py

"""
Hybrid retriever combining BM25 (sparse) and Dense (semantic) retrieval.
"""

from langchain_community.retrievers import BM25Retriever
from langchain_classic.retrievers import EnsembleRetriever

from backend.app.db.qdrant import get_vector_store
from backend.app.constants import (
    BM25_K,
    DENSE_K,
    ENSEMBLE_WEIGHTS,
)
from backend.app.core.logger import get_logger

logger = get_logger(__name__)


def get_hybrid_retriever(text_chunks: list, collection_name: str) -> EnsembleRetriever:
    """
    Build an ensemble retriever combining BM25 (on the fly from provided chunks)
    and dense vector search from an existing Qdrant collection.

    Args:
        text_chunks: List of text chunks from the resume (used for BM25).
        collection_name: Name of the Qdrant collection.

    Returns:
        Configured EnsembleRetriever instance.
    """
    # Ensure chunks are strings
    safe_chunks = [str(chunk) for chunk in text_chunks if chunk]

    # BM25 (Keyword matching) built per request
    bm25 = BM25Retriever.from_texts(safe_chunks)
    bm25.k = BM25_K

    # Dense (Semantic search) from existing Qdrant collection
    vector_store = get_vector_store(collection_name)
    dense = vector_store.as_retriever(search_kwargs={"k": DENSE_K})

    # Ensemble with weights
    retriever = EnsembleRetriever(
        retrievers=[bm25, dense],
        weights=ENSEMBLE_WEIGHTS  # 0.4 BM25, 0.6 Dense
    )

    logger.debug(f"Created hybrid retriever for collection '{collection_name}'")
    return retriever