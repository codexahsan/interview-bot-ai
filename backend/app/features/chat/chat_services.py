# backend/app/features/chat/chat_services.py

"""
Service layer for chat business logic.
Handles message storage, RAG pipeline execution, and PII restoration.
"""

from sqlalchemy.orm import Session

from backend.app.constants import (
    ERR_RESUME_NOT_LINKED,
    ERR_SYSTEM_ERROR,
    RESUME_COLLECTION_PREFIX,
    DEFAULT_RAG_HISTORY_LIMIT,
)
from backend.app.core.logger import get_logger
from backend.app.features.chat.chat_repositories import ChatRepository
from backend.app.features.chat.chat_models import ChatSession
from backend.app.rag.pipeline import RAGPipeline
from backend.app.shared.utils.pii_helper import pii_vault

logger = get_logger(__name__)


class ChatService:
    """Service for handling chat messages and RAG interactions."""

    def __init__(self, repository: ChatRepository):
        self.repository = repository
        self.pipeline = RAGPipeline()

    def process_chat_message(self, session_id: str, user_query: str, db: Session) -> str:
        """
        Process a user message: store it, retrieve context, run RAG,
        restore PII, store assistant response, and return the final answer.

        Args:
            session_id: Chat session UUID.
            user_query: User's raw question.
            db: Database session.

        Returns:
            Final answer string with restored PII.
        """
        # 1. Store user message
        self.repository.add_message(session_id, "user", user_query)
        logger.info(f"Stored user message for session {session_id}")

        # 2. Retrieve recent conversation history
        history = self.repository.get_session_history(
            session_id, limit=DEFAULT_RAG_HISTORY_LIMIT
        )

        # 3. Get session and associated resume data
        session = db.query(ChatSession).filter(ChatSession.id == session_id).first()
        if not session or not session.resume:
            logger.error(f"Session {session_id} has no linked resume")
            return ERR_RESUME_NOT_LINKED

        resume_id = str(session.resume_id)
        collection_name = f"{RESUME_COLLECTION_PREFIX}{resume_id}"
        chunks = session.resume.chunks_json

        # 4. Run RAG pipeline with PII masking
        try:
            logger.info(f"Running RAG pipeline for session {session_id}")
            masked_response = self.pipeline.run(
                user_query,
                history,
                chunks,
                collection_name
            )
        except Exception as e:
            logger.error(f"RAG pipeline failed for session {session_id}: {str(e)}")
            return ERR_SYSTEM_ERROR

        # 5. Restore original PII from vault
        final_answer = pii_vault.restore_pii(resume_id, masked_response)

        # 6. Store assistant response
        self.repository.add_message(session_id, "assistant", final_answer)
        logger.info(f"Stored assistant response for session {session_id}")

        return final_answer