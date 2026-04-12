# backend/app/features/chat/chat_models.py

from sqlalchemy import Column, String, Integer, ForeignKey, Text, DateTime, Boolean
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid
from backend.app.core.database import Base

class ChatSession(Base):
    __tablename__ = "chat_sessions"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    resume_id = Column(Integer, ForeignKey("resumes.id", ondelete="CASCADE"), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Interview fields
    current_question = Column(Text, nullable=True)
    question_count = Column(Integer, default=0)
    total_score = Column(Integer, default=0)

    # --- NEW COLUMNS ---
    is_active = Column(Boolean, default=True)      # Interview active status
    final_verdict = Column(Text, nullable=True)    # Final summary report
    title = Column(Text, nullable=True)            # Auto-generated or manual title
    is_deleted = Column(Boolean, default=False)    # Soft delete flag

    # Relationships
    messages = relationship("ChatMessage", back_populates="session", cascade="all, delete-orphan")
    # Resume link
    resume = relationship("Resume")

class ChatMessage(Base):
    __tablename__ = "chat_messages"

    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(String, ForeignKey("chat_sessions.id", ondelete="CASCADE"), nullable=False)
    role = Column(String)  # 'user' or 'assistant'
    content = Column(Text, nullable=False)

    # --- NEW COLUMN ---
    ans_tip = Column(Text, nullable=True)  # Specific tip for user's answer

    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationship back to session
    session = relationship("ChatSession", back_populates="messages")