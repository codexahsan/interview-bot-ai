# backend/app/main.py
"""
FastAPI application entry point.
"""

import uvicorn
from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from backend.app.features.chat.chat_routes import router as chat_router
from backend.app.features.resume.resume_routes import router as resume_router
from backend.app.features.interview.interview_routes import router as interview_router
from backend.app.shared.utils.response import StandardResponse
from backend.app.core.exceptions import AppException
from backend.app.constants import APP_TITLE, APP_DESCRIPTION, ROOT_MESSAGE
from backend.app.core.logger import get_logger

logger = get_logger(__name__)

app = FastAPI(
    title=APP_TITLE,
    description=APP_DESCRIPTION
)

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Exception handler for our custom AppException
@app.exception_handler(AppException)
async def app_exception_handler(request: Request, exc: AppException) -> JSONResponse:
    """Return all AppException errors in the StandardResponse format."""
    logger.error(f"AppException: {exc.detail} (status={exc.status_code})")
    return JSONResponse(
        status_code=exc.status_code,
        content=StandardResponse.error_response(
            message=exc.detail,
            status_code=exc.status_code
        ).model_dump()
    )


# Optional: Also catch generic HTTPException for consistency
@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
    """Catch any HTTPException not covered by AppException and return standard format."""
    logger.error(f"HTTPException: {exc.detail} (status={exc.status_code})")
    return JSONResponse(
        status_code=exc.status_code,
        content=StandardResponse.error_response(
            message=exc.detail,
            status_code=exc.status_code
        ).model_dump()
    )


# Include feature routers
app.include_router(chat_router)
app.include_router(resume_router)
app.include_router(interview_router)

logger.info("Application routers registered")


@app.get("/")
def read_root() -> dict:
    """Health check endpoint."""
    return {"message": ROOT_MESSAGE}


if __name__ == "__main__":
    uvicorn.run(
        "backend.app.main:app",
        host="127.0.0.1",
        port=8000,
        reload=True
    )