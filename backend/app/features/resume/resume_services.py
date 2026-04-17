# backend/app/features/resume/resume_services.py

"""
Service layer for resume ingestion: PDF parsing, PII masking, chunking, and storage.
"""

from sqlalchemy.orm import Session
from langchain_text_splitters import RecursiveCharacterTextSplitter

from backend.app.shared.utils.pdf_parser import extract_text_from_pdf
from backend.app.shared.utils.pii_helper import mask_pii_data, pii_vault
from backend.app.db.qdrant import get_vector_store
from backend.app.features.resume.resume_models import Resume
from backend.app.constants import (
    CHUNK_SIZE,
    CHUNK_OVERLAP,
    DEFAULT_COLLECTION_PREFIX,
)
from backend.app.core.logger import get_logger

logger = get_logger(__name__)


class ResumeService:
    """Handles resume processing and storage."""

    def __init__(self, db: Session):
        self.db = db

    def ingest_resume(self, pdf_path: str) -> dict:
        """
        Process a PDF resume:
        1. Extract raw text.
        2. Mask PII and store mapping.
        3. Chunk the masked text.
        4. Save Resume record in DB.
        5. Store chunks in Qdrant vector store.

        Args:
            pdf_path: Local path to the uploaded PDF file.

        Returns:
            Dict containing resume_id, chunk count, and status.
        """
        # 1. Extract raw text
        raw_text = extract_text_from_pdf(pdf_path)
        logger.info(f"Extracted raw text from {pdf_path}")

        # 2. Mask PII & get mapping
        masked_text, mapping = mask_pii_data(raw_text)
        logger.debug("PII masking completed")

        # 3. Split into chunks
        splitter = RecursiveCharacterTextSplitter(
            chunk_size=CHUNK_SIZE,
            chunk_overlap=CHUNK_OVERLAP
        )
        chunks = splitter.split_text(masked_text)
        logger.info(f"Split into {len(chunks)} chunks")

        # 3.5 Classify Domain
        from backend.app.shared.utils.domain_classifier import classify_domain
        domain_type = classify_domain(raw_text)
        logger.info(f"Domain Classified as: {domain_type}")

        # 4. Create Resume record
        new_resume = Resume(masked_text=masked_text, chunks_json=chunks, domain_type=domain_type)
        self.db.add(new_resume)
        self.db.commit()
        self.db.refresh(new_resume)
        logger.info(f"Resume saved with ID {new_resume.id}")

        # 5. Store PII mapping in vault keyed by resume_id
        pii_vault.store_new_mapping(str(new_resume.id), mapping)

        # 6. Store chunks in Qdrant
        collection_name = f"{DEFAULT_COLLECTION_PREFIX}{new_resume.id}"
        vector_store = get_vector_store(collection_name)
        vector_store.add_texts(chunks)
        logger.info(f"Chunks stored in Qdrant collection '{collection_name}'")

        return {
            "resume_id": new_resume.id,
            "chunks": len(chunks),
            "status": "success"
        }