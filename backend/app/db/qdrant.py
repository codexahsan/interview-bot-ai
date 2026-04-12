# backend/app/db/qdrant.py

"""
Qdrant vector store client and collection management.
"""

from qdrant_client import QdrantClient
from langchain_qdrant import QdrantVectorStore
from qdrant_client.http.models import Distance, VectorParams

from backend.app.shared.llm.client import get_embeddings
from backend.app.constants import QDRANT_LOCAL_PATH, QDRANT_EMBEDDING_TEST_TEXT
from backend.app.core.logger import get_logger

logger = get_logger(__name__)

_qdrant_client = None


def get_qdrant_client() -> QdrantClient:
    """
    Return a singleton Qdrant client instance using local persistent storage.
    """
    global _qdrant_client
    if _qdrant_client is None:
        _qdrant_client = QdrantClient(path=QDRANT_LOCAL_PATH)
        logger.info(f"Initialized Qdrant client at {QDRANT_LOCAL_PATH}")
    return _qdrant_client


def get_vector_store(collection_name: str) -> QdrantVectorStore:
    """
    Retrieve or create a Qdrant vector store for a given collection name.

    Args:
        collection_name: Unique name for the vector collection (e.g., per resume).

    Returns:
        Configured QdrantVectorStore instance.
    """
    client = get_qdrant_client()
    embeddings = get_embeddings()

    vector_dim = len(embeddings.embed_query(QDRANT_EMBEDDING_TEST_TEXT))

    try:
        client.get_collection(collection_name=collection_name)
        logger.debug(f"Collection '{collection_name}' already exists")
    except Exception:
        client.create_collection(
            collection_name=collection_name,
            vectors_config=VectorParams(
                size=vector_dim,
                distance=Distance.COSINE
            ),
        )
        logger.info(f"Created new collection '{collection_name}' with dim={vector_dim}")

    vector_store = QdrantVectorStore(
        client=client,
        collection_name=collection_name,
        embedding=embeddings
    )
    return vector_store