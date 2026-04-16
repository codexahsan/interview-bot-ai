# backend/app/features/interview/interview_routes.py

"""
FastAPI routes for interview flow.
All responses follow the StandardResponse envelope.
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel

from backend.app.core.database import get_db
from backend.app.features.interview.interview_service import InterviewService
from backend.app.features.chat.chat_models import ChatSession, ChatMessage
from backend.app.shared.utils.response import StandardResponse
from backend.app.constants import (
    STATUS_OK,
    STATUS_BAD_REQUEST,
    MSG_INTERVIEW_COMPLETED,
)
from backend.app.core.logger import get_logger
from backend.app.core.exceptions import InterviewProcessingError

logger = get_logger(__name__)

router = APIRouter(prefix="/interview", tags=["Interview"])


# -----------------------------
# 📦 REQUEST MODELS
# -----------------------------
class StartInterviewRequest(BaseModel):
    session_id: str


class AnswerRequest(BaseModel):
    session_id: str
    answer: str


class RenameSessionRequest(BaseModel):
    new_title: str

class EndSessionRequest(BaseModel):
    session_id: str

# -----------------------------
# 🟢 START INTERVIEW
# -----------------------------
@router.post("/start", response_model=StandardResponse)
def start_interview(req: StartInterviewRequest, db: Session = Depends(get_db)):
    """
    Begin the interview for a given chat session.
    Returns the first question.
    """
    logger.info(f"Starting interview for session {req.session_id}")
    try:
        service = InterviewService(db)
        result = service.start_interview(req.session_id)

        if "error" in result:
            return StandardResponse.error_response(
                message=result["error"], status_code=STATUS_BAD_REQUEST
            )

        return StandardResponse.success_response(
            data=result, message="Interview started", status_code=STATUS_OK
        )
    except Exception as e:
        logger.error(f"Error starting interview: {str(e)}")
        raise InterviewProcessingError(detail="Failed to start interview")


# -----------------------------
# 🔵 SUBMIT ANSWER
# -----------------------------
@router.post("/answer", response_model=StandardResponse)
def submit_answer(req: AnswerRequest, db: Session = Depends(get_db)):
    """
    Submit an answer to the current question.
    Returns feedback, next question, or completion summary.
    """
    logger.info(f"Submitting answer for session {req.session_id}")
    try:
        service = InterviewService(db)
        result = service.submit_answer(req.session_id, req.answer)

        if "error" in result:
            return StandardResponse.error_response(
                message=result["error"], status_code=STATUS_BAD_REQUEST
            )

        # Determine success message based on completion
        message = (
            MSG_INTERVIEW_COMPLETED
            if result.get("status") == "completed"
            else "Answer submitted"
        )

        return StandardResponse.success_response(
            data=result, message=message, status_code=STATUS_OK
        )
    except Exception as e:
        logger.error(f"Error submitting answer: {str(e)}")
        raise InterviewProcessingError(detail="Failed to process answer")

# -----------------------------
# 🛑 END INTERVIEW MANUALLY
# -----------------------------
@router.post("/end", response_model=StandardResponse)
def end_interview_manually(req: EndSessionRequest, db: Session = Depends(get_db)):
    """
    Manually lock the chat and generate the final verdict.
    """
    logger.info(f"Manual end requested for session {req.session_id}")
    try:
        service = InterviewService(db)
        result = service.end_interview_manually(req.session_id)

        if "error" in result:
            return StandardResponse.error_response(
                message=result["error"], status_code=STATUS_BAD_REQUEST
            )

        return StandardResponse.success_response(
            data=result, message="Interview manually completed", status_code=STATUS_OK
        )
    except Exception as e:
        logger.error(f"Error ending interview manually: {str(e)}")
        raise InterviewProcessingError(detail="Failed to end interview")


# -----------------------------
# 📜 GET ALL SESSIONS (Sidebar History) - Excludes deleted
# -----------------------------
@router.get("/history", response_model=StandardResponse)
def get_all_sessions(db: Session = Depends(get_db)):
    sessions = (
        db.query(ChatSession)
        .filter(ChatSession.is_deleted == False)
        .order_by(ChatSession.created_at.desc())
        .all()
    )

    data = [
        {
            "id": s.id,
            "title": s.title or "Untitled Session",
            "date": s.created_at.strftime("%Y-%m-%d %H:%M"),
            "status": "Completed" if not s.is_active else f"Q{s.question_count}/5",
            "is_active": s.is_active,
            "session_type": getattr(s, 'session_type', 'interview')  # ✅ ADDED
        }
        for s in sessions
    ]

    return StandardResponse.success_response(
        data=data, message="Session history retrieved", status_code=STATUS_OK
    )

# -----------------------------
# 📄 GET SESSION DETAILS (Load specific chat)
# -----------------------------
@router.get("/session/{session_id}", response_model=StandardResponse)
def get_session_details(session_id: str, db: Session = Depends(get_db)):
    session = (
        db.query(ChatSession)
        .filter(ChatSession.id == session_id, ChatSession.is_deleted == False)
        .first()
    )
    if not session:
        return StandardResponse.error_response(
            message="Session not found", status_code=STATUS_BAD_REQUEST
        )

    messages = (
        db.query(ChatMessage)
        .filter(ChatMessage.session_id == session_id)
        .order_by(ChatMessage.created_at.asc())
        .all()
    )

    message_data = [
        {
            "id": m.id,
            "role": m.role,
            "content": m.content,
            "ans_tip": m.ans_tip,
            "created_at": m.created_at.isoformat(),
        }
        for m in messages
    ]

    return StandardResponse.success_response(
        data={
            "messages": message_data,
            "final_verdict": session.final_verdict,
            "is_active": session.is_active,
            "total_score": session.total_score,
            "question_count": session.question_count,
            "title": session.title,
            "session_type": getattr(session, 'session_type', 'interview')  # ✅ ADDED
        },
        message="Session details retrieved",
        status_code=STATUS_OK,
    )



# -----------------------------
# ✏️ RENAME SESSION
# -----------------------------
@router.patch("/session/{session_id}/rename", response_model=StandardResponse)
def rename_session(
    session_id: str, req: RenameSessionRequest, db: Session = Depends(get_db)
):
    """Rename a session's title."""
    session = (
        db.query(ChatSession)
        .filter(ChatSession.id == session_id, ChatSession.is_deleted == False)
        .first()
    )
    if not session:
        return StandardResponse.error_response(
            message="Session not found", status_code=STATUS_BAD_REQUEST
        )

    new_title = req.new_title.strip()
    if not new_title:
        return StandardResponse.error_response(
            message="Title cannot be empty", status_code=STATUS_BAD_REQUEST
        )

    session.title = new_title
    db.commit()
    return StandardResponse.success_response(
        data={"id": session_id, "title": new_title},
        message="Session renamed successfully",
        status_code=STATUS_OK,
    )


# -----------------------------
# 🗑️ SOFT DELETE SESSION
# -----------------------------
@router.delete("/session/{session_id}", response_model=StandardResponse)
def delete_session(session_id: str, db: Session = Depends(get_db)):
    """Soft delete a session (mark as deleted)."""
    session = (
        db.query(ChatSession)
        .filter(ChatSession.id == session_id, ChatSession.is_deleted == False)
        .first()
    )
    if not session:
        return StandardResponse.error_response(
            message="Session not found", status_code=STATUS_BAD_REQUEST
        )

    session.is_deleted = True
    db.commit()
    return StandardResponse.success_response(
        data={"id": session_id},
        message="Session deleted successfully",
        status_code=STATUS_OK,
    )
