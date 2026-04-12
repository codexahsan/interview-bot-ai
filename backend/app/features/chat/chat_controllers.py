# backend/app/features/chat/chat_controllers.py 

"""
Controller layer for chat operations.
Handles HTTP requests, coordinates services, and returns standard responses.
"""

import json
from sqlalchemy.orm import Session

from backend.app.constants import (
    DEFAULT_CHAT_HISTORY_LIMIT,
)
from backend.app.core.logger import get_logger
from backend.app.core.exceptions import ChatProcessingError, SessionNotFoundError
from backend.app.features.chat.chat_services import ChatService
from backend.app.features.chat.chat_repositories import ChatRepository
from backend.app.core.redis_client import get_redis

logger = get_logger(__name__)

redis_client = get_redis()

class ChatController:
    """Controller for chat session and message handling."""

    def __init__(self, db: Session):
        self.repository = ChatRepository(db)
        self.service = ChatService(self.repository)

    def create_new_chat(self, resume_id: int) -> dict:
        """
        Create a new chat session linked to a specific resume.
        Also caches initial session state in Redis.

        Args:
            resume_id: ID of the uploaded resume.

        Returns:
            The newly created ChatSession object (as dict or ORM model).
        """
        logger.info(f"Creating new chat session for resume_id={resume_id}")
        session = self.service.repository.create_session(resume_id)

        # Cache initial session state in Redis
        redis_client.set(
            f"session:{session.id}",
            json.dumps({
                "resume_id": resume_id,
                "question_count": 0,
                "total_score": 0,
                "is_active": True,
                "current_question": None
            }),
            ex=7200  # 2 hours TTL
        )

        return session

    def send_message(self, session_id: str, content: str, db: Session) -> dict:
        """
        Process a user message within a chat session.

        Args:
            session_id: UUID of the chat session.
            content: The user's message text.
            db: Database session.

        Returns:
            Dict with assistant role and response content.

        Raises:
            ChatProcessingError: If processing fails.
        """
        try:
            logger.info(f"Processing message for session {session_id}")
            response_content = self.service.process_chat_message(session_id, content, db)
        
            # Cache Invalidate: Sirf delete nahi, aglay request par automatic update hoga
            redis_client.delete(f"chat_history:{session_id}") 
            
            return {"role": "assistant", "content": response_content}
        except Exception as e:
            logger.error(f"Error in send_message for session {session_id}: {str(e)}")
            raise ChatProcessingError(detail=str(e))

    def get_history(self, session_id: str) -> list:
        """
        Retrieve the last N messages of a chat session.
        Uses Redis cache if available.

        Args:
            session_id: UUID of the chat session.

        Returns:
            List of ChatMessage objects (max 20 messages).

        Raises:
            SessionNotFoundError: If session not found or no messages exist.
        """
        logger.info(f"Fetching history for session {session_id}")

        cache_key = f"chat:{session_id}"
        cached = redis_client.get(cache_key)
        if cached:
            logger.debug(f"Returning cached history for session {session_id}")
            return json.loads(cached)

        history = self.service.repository.get_session_history(
            session_id, limit=DEFAULT_CHAT_HISTORY_LIMIT
        )
        if not history:
            logger.warning(f"No history found for session {session_id}")
            raise SessionNotFoundError()

        # Cache for 5 minutes (300 seconds)
        redis_client.set(cache_key, json.dumps(history), ex=300)

        return history