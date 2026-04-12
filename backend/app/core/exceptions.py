# backend/app/core/exceptions.py
"""
Custom exception classes for the application.
All exceptions inherit from AppException, which extends FastAPI's HTTPException.
This allows automatic handling by our global exception handler.
"""

from fastapi import HTTPException
from http import HTTPStatus

from backend.app.constants import (
    ERR_SESSION_NOT_FOUND,
    ERR_NO_RESUME_FOR_SESSION,
    ERR_INVALID_SESSION,
    ERR_RESUME_NOT_LINKED,
    ERR_SYSTEM_ERROR,
    STATUS_BAD_REQUEST,
    STATUS_UNAUTHORIZED,
    STATUS_FORBIDDEN,
    STATUS_NOT_FOUND,
    STATUS_INTERNAL_SERVER_ERROR,
)


class AppException(HTTPException):
    """Base exception for all application-specific errors."""
    def __init__(self, detail: str, status_code: int = STATUS_BAD_REQUEST):
        super().__init__(status_code=status_code, detail=detail)


# ---------------------
# Resume-related Errors
# ---------------------
class ResumeNotFoundError(AppException):
    """Raised when a requested resume does not exist."""
    def __init__(self, detail: str = "Resume not found"):
        super().__init__(detail=detail, status_code=STATUS_NOT_FOUND)


class ResumeProcessingError(AppException):
    """Raised when resume ingestion or parsing fails."""
    def __init__(self, detail: str = "Failed to process resume"):
        super().__init__(detail=detail, status_code=STATUS_INTERNAL_SERVER_ERROR)


class ResumeNotLinkedError(AppException):
    """Raised when a chat session has no associated resume."""
    def __init__(self, detail: str = ERR_RESUME_NOT_LINKED):
        super().__init__(detail=detail, status_code=STATUS_BAD_REQUEST)


# ---------------------
# Session/History Errors
# ---------------------
class SessionNotFoundError(AppException):
    """Raised when a chat session does not exist."""
    def __init__(self, detail: str = ERR_SESSION_NOT_FOUND):
        super().__init__(detail=detail, status_code=STATUS_NOT_FOUND)


class InvalidSessionError(AppException):
    """Raised when a session is invalid for an operation."""
    def __init__(self, detail: str = ERR_INVALID_SESSION):
        super().__init__(detail=detail, status_code=STATUS_BAD_REQUEST)


class NoResumeForSessionError(AppException):
    """Raised when an interview session lacks a resume."""
    def __init__(self, detail: str = ERR_NO_RESUME_FOR_SESSION):
        super().__init__(detail=detail, status_code=STATUS_BAD_REQUEST)


# ---------------------
# Interview Errors
# ---------------------
class InterviewAlreadyCompletedError(AppException):
    """Raised when attempting to submit an answer after interview is done."""
    def __init__(self, detail: str = "Interview has already been completed"):
        super().__init__(detail=detail, status_code=STATUS_BAD_REQUEST)


class InterviewNotStartedError(AppException):
    """Raised when submitting an answer before starting the interview."""
    def __init__(self, detail: str = "Interview has not been started yet"):
        super().__init__(detail=detail, status_code=STATUS_BAD_REQUEST)


# ---------------------
# Chat/Message Errors
# ---------------------
class ChatProcessingError(AppException):
    """Raised when the RAG pipeline or LLM fails during chat."""
    def __init__(self, detail: str = ERR_SYSTEM_ERROR):
        super().__init__(detail=detail, status_code=STATUS_INTERNAL_SERVER_ERROR)


# ---------------------
# Authentication/Authorization (if needed later)
# ---------------------
class AuthenticationError(AppException):
    def __init__(self, detail: str = "Authentication required"):
        super().__init__(detail=detail, status_code=STATUS_UNAUTHORIZED)


class PermissionDeniedError(AppException):
    def __init__(self, detail: str = "Permission denied"):
        super().__init__(detail=detail, status_code=STATUS_FORBIDDEN)


# ---------------------
# Generic Bad Request
# ---------------------
class BadRequestError(AppException):
    """Generic client error."""
    def __init__(self, detail: str = "Invalid request"):
        super().__init__(detail=detail, status_code=STATUS_BAD_REQUEST)


class NotFoundError(AppException):
    """Generic resource not found."""
    def __init__(self, detail: str = "Resource not found"):
        super().__init__(detail=detail, status_code=STATUS_NOT_FOUND)

# ---------------------
# Interview Errors (additional)
# ---------------------
class InterviewProcessingError(AppException):
    """Raised when interview start or answer processing fails."""
    def __init__(self, detail: str = "Failed to process interview request"):
        super().__init__(detail=detail, status_code=STATUS_INTERNAL_SERVER_ERROR)