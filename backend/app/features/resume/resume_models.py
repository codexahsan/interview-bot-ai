# backend/app/features/resume/resume_models.py

from sqlalchemy import Column, Integer, Text
from sqlalchemy.dialects.postgresql import JSON
from backend.app.core.database import Base


class Resume(Base):
    __tablename__ = "resumes"

    id = Column(Integer, primary_key=True, index=True)
    masked_text = Column(Text, nullable=False)
    chunks_json = Column(JSON, nullable=True)
    domain_type = Column(Text, default="General", nullable=True)