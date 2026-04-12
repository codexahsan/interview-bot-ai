# backend/app/features/resume/resume_routes.py

"""
FastAPI routes for resume upload and ingestion.
"""

import os
import shutil
from fastapi import APIRouter, UploadFile, File, Depends
from sqlalchemy.orm import Session

from backend.app.core.database import get_db
from backend.app.features.resume.resume_services import ResumeService
from backend.app.shared.utils.response import StandardResponse
from backend.app.constants import (
    TEMP_UPLOAD_DIR,
    STATUS_OK,
)
from backend.app.core.logger import get_logger
from backend.app.core.exceptions import ResumeProcessingError

logger = get_logger(__name__)

router = APIRouter(prefix="/resume", tags=["Resume"])


@router.post("/upload", response_model=StandardResponse)
async def upload_resume(file: UploadFile = File(...), db: Session = Depends(get_db)):
    """
    Upload a PDF resume, extract text, mask PII, chunk, and store in database and vector store.
    """
    # Ensure temp directory exists
    os.makedirs(TEMP_UPLOAD_DIR, exist_ok=True)
    file_path = os.path.join(TEMP_UPLOAD_DIR, file.filename)

    try:
        # Save uploaded file temporarily
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        logger.info(f"Resume uploaded: {file.filename}")

        # Process the resume
        service = ResumeService(db)
        result = service.ingest_resume(file_path)

        # Clean up temp file
        os.remove(file_path)
        logger.info(f"Temporary file removed: {file_path}")

        return StandardResponse.success_response(
            data=result, message="Resume ingested successfully", status_code=STATUS_OK
        )

    except Exception as e:
        logger.error(f"Resume upload failed: {str(e)}")
        # Attempt cleanup if file exists
        if os.path.exists(file_path):
            os.remove(file_path)
        raise ResumeProcessingError(detail="Failed to process resume")