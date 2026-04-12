# backend/app/core/database.py

"""
Database connection and session management for SQLAlchemy.
"""

from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

from backend.app.core.config import settings

# 1. Create Engine
SQLALCHEMY_DATABASE_URL = settings.POSTGRES_URL

engine = create_engine(SQLALCHEMY_DATABASE_URL)

# 2. Session Factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# 3. Base Class for Models
Base = declarative_base()

# 4. Dependency for FastAPI routes
def get_db():
    """Yield a database session and ensure closure after request."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()