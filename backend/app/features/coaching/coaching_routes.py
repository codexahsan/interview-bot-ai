# backend/app/features/coaching/coaching_routes.py

from fastapi import APIRouter, Depends, Body
from sqlalchemy.orm import Session
from backend.app.core.database import get_db
from backend.app.features.coaching.coaching_service import CoachingService
from backend.app.shared.utils.response import StandardResponse
from backend.app.constants import STATUS_OK, STATUS_BAD_REQUEST

router = APIRouter(prefix="/coach", tags=["Coaching"])


@router.post("/start/{interview_session_id}", response_model=StandardResponse)
async def start_coach(interview_session_id: str, db: Session = Depends(get_db)):
    service = CoachingService(db)
    result = service.start_coaching_session(interview_session_id)

    if "error" in result:
        return StandardResponse.error_response(
            message=result["error"],
            status_code=STATUS_BAD_REQUEST
        )

    return StandardResponse.success_response(
        data=result,
        message="Coaching session started",
        status_code=STATUS_OK
    )


@router.post("/chat", response_model=StandardResponse)
async def coach_chat(
    session_id: str = Body(...),
    message: str = Body(...),
    db: Session = Depends(get_db)
):
    service = CoachingService(db)
    answer = service.get_coaching_answer(session_id, message)

    return StandardResponse.success_response(
        data={"answer": answer},
        message="Coaching response generated",
        status_code=STATUS_OK
    )