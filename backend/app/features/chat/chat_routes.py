# backend/app/features/chat/chat_routes.py

"""
FastAPI route definitions for chat endpoints.
All responses are wrapped in the StandardResponse model.
"""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from backend.app.core.database import get_db
from backend.app.features.chat.chat_controllers import ChatController
from backend.app.features.chat.chat_schemas import (
    MessageCreate,
    MessageResponse,
    SessionResponse,
)
from backend.app.features.chat.chat_models import ChatSession
from backend.app.shared.utils.response import StandardResponse
from backend.app.constants import (
    STATUS_CREATED,
    STATUS_OK,
    MSG_CHAT_CREATED,
    MSG_MESSAGE_SENT,
    MSG_HISTORY_RETRIEVED,
    MSG_SESSION_STARTED,
)
from backend.app.core.logger import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/chat", tags=["Chat"])


@router.post("/new/{resume_id}", response_model=StandardResponse)
def start_new_chat(resume_id: int, db: Session = Depends(get_db)) -> StandardResponse:
    """
    Start a new chat session for a given resume.
    """
    controller = ChatController(db)
    session = controller.create_new_chat(resume_id)
    logger.info(f"New chat session started for resume {resume_id}: {session.id}")

    # Convert ORM object to Pydantic schema for JSON serialization
    session_data = SessionResponse.model_validate(session).model_dump()

    return StandardResponse.success_response(
        data=session_data,
        message=MSG_CHAT_CREATED,
        status_code=STATUS_CREATED
    )


@router.post("/{session_id}/message", response_model=StandardResponse)
def chat_with_resume(
    session_id: str, message: MessageCreate, db: Session = Depends(get_db)
) -> StandardResponse:
    """
    Send a message to an existing chat session.
    """
    controller = ChatController(db)
    assistant_reply = controller.send_message(session_id, message.content, db)
    logger.info(f"Message processed for session {session_id}")
    return StandardResponse.success_response(
        data=assistant_reply,
        message=MSG_MESSAGE_SENT,
        status_code=STATUS_OK
    )


@router.get("/{session_id}/history", response_model=StandardResponse)
def get_chat_history(session_id: str, db: Session = Depends(get_db)) -> StandardResponse:
    """
    Retrieve the conversation history of a chat session.
    """
    controller = ChatController(db)
    history = controller.get_history(session_id)

    # Convert list of ORM objects to list of Pydantic schemas
    history_data = [MessageResponse.model_validate(msg).model_dump() for msg in history]

    return StandardResponse.success_response(
        data=history_data,
        message=MSG_HISTORY_RETRIEVED,
        status_code=STATUS_OK
    )


@router.post("/start", response_model=StandardResponse)
def start_chat(db: Session = Depends(get_db)) -> StandardResponse:
    """
    Create a blank chat session (legacy endpoint – may be unused).
    """
    logger.info("Legacy /start endpoint called")
    session = ChatSession()
    db.add(session)
    db.commit()
    db.refresh(session)
    return StandardResponse.success_response(
        data={"session_id": str(session.id)},
        message=MSG_SESSION_STARTED,
        status_code=STATUS_CREATED
    )