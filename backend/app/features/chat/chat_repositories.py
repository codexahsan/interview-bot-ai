# backend/app/features/chat/chat_repositories.py

"""
Repository layer for chat database operations.
"""

from sqlalchemy.orm import Session
from backend.app.features.chat.chat_models import ChatSession, ChatMessage
from backend.app.core.logger import get_logger
from backend.app.core.redis_client import get_redis
from backend.app.constants import DEFAULT_RAG_HISTORY_LIMIT
import json

logger = get_logger(__name__)


class ChatRepository:
    """Database operations for chat sessions and messages."""

    def __init__(self, db: Session):
        self.db = db

    def create_session(self, resume_id: int) -> ChatSession:
        """
        Create a new chat session linked to a resume.

        Args:
            resume_id: ID of the associated resume.

        Returns:
            The newly created ChatSession object.
        """
        session = ChatSession(resume_id=resume_id)
        self.db.add(session)
        self.db.commit()
        self.db.refresh(session)
        logger.debug(f"Created chat session {session.id} for resume {resume_id}")
        return session

    def add_message(self, session_id: str, role: str, content: str) -> ChatMessage:
        """
        Persist a chat message (user or assistant).
        """
        message = ChatMessage(session_id=session_id, role=role, content=content)
        self.db.add(message)
        self.db.commit()
        self.db.refresh(message)
        
        # FIX: Redis se purana cache delete karein
        redis = get_redis()
        cache_key = f"chat_history:{session_id}"
        redis.delete(cache_key)
        
        logger.debug(f"Added {role} message to session {session_id} and cleared cache")
        return message

    def get_session_history(self, session_id: str, limit: int = 20):
        redis = get_redis()
        cache_key = f"chat_history:{session_id}"
        
        # 1. Check Redis
        cached_data = redis.get(cache_key)
        if cached_data:
            logger.debug(f"History fetched from Redis for {session_id}")
            return json.loads(cached_data)

        # 2. Fallback to DB (Existing logic)
        messages = (
            self.db.query(ChatMessage)
            .filter(ChatMessage.session_id == session_id)
            .order_by(ChatMessage.created_at.desc())
            .limit(limit)
            .all()
        )
        
        # 3. Save to Redis for next time
        # Note: Messages list ko serializable banana hoga
        history_list = [{"role": m.role, "content": m.content} for m in messages[::-1]]
        redis.set(cache_key, json.dumps(history_list), ex=600) # 10 mins cache
        
        return messages[::-1]

    def get_all_user_sessions(self) -> list:
        """
        Retrieve all chat sessions, ordered by newest first.

        Returns:
            List of ChatSession objects.
        """
        return self.db.query(ChatSession).order_by(ChatSession.created_at.desc()).all()