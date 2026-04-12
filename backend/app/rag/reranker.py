# backend/app/rag/reranker.py 

"""
Document reranking using FlashRank.
"""

from flashrank import Ranker, RerankRequest

from backend.app.core.logger import get_logger

logger = get_logger(__name__)

# Singleton ranker instance
_ranker = None


def get_ranker() -> Ranker:
    """Return a singleton FlashRank Ranker instance."""
    global _ranker
    if _ranker is None:
        _ranker = Ranker()
        logger.debug("FlashRank ranker initialized")
    return _ranker


def rerank(query: str, docs: list) -> list:
    """
    Rerank a list of documents based on relevance to the query.

    Args:
        query: Search query string.
        docs: List of LangChain Document objects.

    Returns:
        List of top 5 documents sorted by relevance score.
    """
    if not docs:
        return []

    ranker = get_ranker()

    passages = [
        {"id": i, "text": doc.page_content}
        for i, doc in enumerate(docs)
    ]

    request = RerankRequest(query=query, passages=passages)
    results = ranker.rerank(request)

    # Sort by score descending
    ranked = sorted(results, key=lambda x: x["score"], reverse=True)

    # Map back to original documents
    top_docs = [docs[r["id"]] for r in ranked[:5]]
    logger.debug(f"Reranked {len(docs)} docs, returning top {len(top_docs)}")
    return top_docs