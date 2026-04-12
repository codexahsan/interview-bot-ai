# backend/app/rag/pipeline.py

"""
RAG Pipeline: query rewriting, retrieval, reranking, and final answer generation.
"""

from typing import List
from langchain_community.retrievers import BM25Retriever

from backend.app.shared.llm.client import get_llm
from backend.app.rag.reranker import rerank
from backend.app.shared.prompts.rephrasing_prompt import REPHRASING_PROMPT_TEMPLATE
from backend.app.db.qdrant import get_vector_store
from backend.app.core.redis_client import get_redis
from backend.app.constants import (
    BM25_K,
    SIMILARITY_SEARCH_K,
    MAX_COMBINED_DOCS,
    TOP_K_AFTER_RERANK,
    FALLBACK_RESPONSE,
    RERANK_FALLBACK_RESPONSE,
    MISSING_INFO_RESPONSE,
    FINAL_RAG_PROMPT_TEMPLATE,
)
from backend.app.core.logger import get_logger
import hashlib
import json

logger = get_logger(__name__)


class RAGPipeline:
    """Orchestrates the end-to-end RAG process."""

    def __init__(self):
        self.llm = get_llm()

    def rewrite_query(self, query: str, history: list) -> str:
        """
        Rewrite the user query into a standalone search query using conversation history.

        Args:
            query: Raw user question.
            history: List of previous ChatMessage objects.

        Returns:
            Rewritten standalone query.
        """
        if not history:
            return query

        formatted_history = "\n".join([f"{m.role}: {m.content}" for m in history])
        prompt = REPHRASING_PROMPT_TEMPLATE.format(
            history=formatted_history,
            query=query
        )
        response = self.llm.invoke(prompt)
        rewritten = response.content.strip()
        logger.debug(f"Query rewritten: '{query}' -> '{rewritten}'")
        return rewritten

    def run(self, query: str, history: list, chunks: List[str], collection_name: str) -> str:
        """
        Execute the full RAG pipeline.

        Args:
            query: User's current question.
            history: Conversation history.
            chunks: List of resume text chunks (for BM25).
            collection_name: Qdrant collection name.

        Returns:
            Final answer string.
        """

        redis = get_redis()

        
        standalone_query = self.rewrite_query(query, history)

        # Dense retrieval
        vector_store = get_vector_store(collection_name)
        dense_docs = vector_store.similarity_search(standalone_query, k=SIMILARITY_SEARCH_K)

        # Sparse retrieval (BM25) if chunks available
        if not chunks:
            combined_docs = dense_docs
        else:
            cache_key = f"chunks:{collection_name}:{len(chunks)}"
            cached_chunks = redis.get(cache_key)

            if cached_chunks:
                chunks = json.loads(cached_chunks)
                logger.debug("Chunks loaded from Redis")
            else:
                redis.set(cache_key, json.dumps(chunks), ex=3600)

            bm25_retriever = BM25Retriever.from_texts(chunks)
            bm25_retriever.k = BM25_K
            bm25_docs = bm25_retriever.invoke(standalone_query)

            # Combine and deduplicate by page_content
            all_docs = dense_docs + bm25_docs
            combined_docs = list({doc.page_content: doc for doc in all_docs}.values())

        # Limit to top N before reranking
        combined_docs = combined_docs[:MAX_COMBINED_DOCS]

        if not combined_docs:
            logger.warning(f"No documents retrieved for query: {standalone_query}")
            return FALLBACK_RESPONSE

        # Rerank
        top_docs = rerank(standalone_query, combined_docs)

        if not top_docs:
            return RERANK_FALLBACK_RESPONSE

        # Build context from top reranked chunks
        context = "\n".join([doc.page_content for doc in top_docs[:TOP_K_AFTER_RERANK]])

        final_prompt = FINAL_RAG_PROMPT_TEMPLATE.format(
            missing_info_msg=MISSING_INFO_RESPONSE,
            context=context,
            query=standalone_query
        )

        cache_key = f"llm:{collection_name}:{hashlib.md5(final_prompt.encode()).hexdigest()}"
        cached_answer = redis.get(cache_key)

        if cached_answer:
            logger.debug("LLM response from cache")
            return cached_answer

        answer = self.llm.invoke(final_prompt).content.strip()

        redis.set(cache_key, answer, ex=3600)
        logger.info("RAG pipeline completed successfully")
        return answer