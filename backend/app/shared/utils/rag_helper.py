# backend/app/shared/utils/rag_helper.py

"""
Manual RAG testing utility (non-production).
Allows testing the pipeline with a local PDF file.
"""

import uuid
from langchain_text_splitters import RecursiveCharacterTextSplitter

from backend.app.shared.llm.client import get_llm
from backend.app.shared.utils.compliance_agent import ComplianceAgent
from backend.app.rag.hybrid_retriever import get_hybrid_retriever
from backend.app.shared.utils.pdf_parser import extract_text_from_pdf
from backend.app.shared.utils.section_parser import get_structured_sections
from backend.app.rag.reranker import rerank
from backend.app.db.qdrant import get_vector_store
from backend.app.constants import (
    RAG_MANUAL_CHUNK_SIZE,
    RAG_MANUAL_CHUNK_OVERLAP,
    RAG_MANUAL_SEPARATORS,
    RAG_MANUAL_MAX_DOCS_BEFORE_RERANK,
    RAG_MANUAL_QUERY_GENERATION_COUNT,
    RAG_MANUAL_PROMPT_TEMPLATE,
)
from backend.app.core.logger import get_logger

logger = get_logger(__name__)

# Hardcoded path for testing – can be overridden via env if desired.
PDF_PATH = r"C:\Users\AHSAN\Desktop\ChatBot\interview_bot_project\Muzaffar_Latest_CV.pdf"


def rag_manual(query: str) -> str:
    """
    End-to-end manual RAG test against a static PDF.

    Args:
        query: User question.

    Returns:
        LLM answer based on retrieved context.
    """
    logger.info(f"Starting manual RAG with query: {query}")

    # Initialize Agent
    compliance_agent = ComplianceAgent()
    
    # Mask query
    safe_query_result = compliance_agent.process(query)
    safe_query = safe_query_result[0] if isinstance(safe_query_result, tuple) else safe_query_result

    # Extract text from PDF
    raw_text = extract_text_from_pdf(PDF_PATH)

    # Chunk text
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=RAG_MANUAL_CHUNK_SIZE,
        chunk_overlap=RAG_MANUAL_CHUNK_OVERLAP,
        separators=RAG_MANUAL_SEPARATORS
    )
    sections = get_structured_sections(raw_text)
    
    logger.debug(f"Detected {len(sections)} sections")
    chunks = []
    for sec in sections:
        split = splitter.split_text(sec)
        chunks.extend(split)

    logger.info(f"Created {len(chunks)} chunks")

    # Create a temporary collection and populate Qdrant
    collection_name = f"resume_{uuid.uuid4().hex[:8]}"
    logger.info(f"Using collection: {collection_name}")

    vector_store = get_vector_store(collection_name)
    vector_store.add_texts(chunks)

    # Hybrid retrieval
    retriever = get_hybrid_retriever(chunks, collection_name)

    # Generate multiple query variants
    queries = [safe_query] + generate_queries(safe_query)

    all_docs = []
    for q in queries:
        if isinstance(q, tuple):
            q = q[0]
        docs = retriever.invoke(q)
        all_docs.extend(docs)

    # Deduplicate and limit before reranking
    unique_docs = list({doc.page_content: doc for doc in all_docs}.values())
    unique_docs = unique_docs[:RAG_MANUAL_MAX_DOCS_BEFORE_RERANK]
    logger.debug(f"Docs before reranking: {len(unique_docs)}")

    # Rerank
    unique_docs = rerank(safe_query, unique_docs)

    if not unique_docs:
        logger.warning("No relevant documents found")
        return "No relevant info found."

    # Build context
    context = "\n".join([doc.page_content for doc in unique_docs])
    logger.debug(f"Retrieved context length: {len(context)} characters")

    # Generate final answer
    llm = get_llm()
    prompt = RAG_MANUAL_PROMPT_TEMPLATE.format(
        context=context,
        query=safe_query
    )
    response = llm.invoke(prompt)
    logger.info("RAG manual response generated")
    return response.content


def generate_queries(query: str) -> list:
    """
    Use LLM to generate variant search queries for better recall.

    Args:
        query: Original user query.

    Returns:
        List of 3 variant query strings.
    """
    llm = get_llm()

    prompt = f"""
Generate 3 short, distinct search queries to find the answer in a resume.

Rules:
- Only return the queries.
- No explanation, no bullet points, no hyphens, no quotes.
- Each query on a new line.

Question:
{query}
"""
    response = llm.invoke(prompt)
    raw_queries = response.content.strip().split("\n")
    cleaned_queries = [
        str(q).strip("- *\"' ") for q in raw_queries
        if len(str(q).strip()) > 2
    ]
    logger.debug(f"Generated {len(cleaned_queries)} variant queries")
    return cleaned_queries