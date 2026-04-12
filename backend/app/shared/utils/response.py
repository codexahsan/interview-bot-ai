# backend/app/shared/utils/response.py
"""
Standardised API response wrapper.
All endpoints will return this structure: { success, data, message, statusCode }
"""

from typing import Any, Optional
from pydantic import BaseModel
from backend.app.constants import STATUS_OK, STATUS_INTERNAL_SERVER_ERROR


class StandardResponse(BaseModel):
    success: bool
    data: Optional[Any] = None
    message: str
    statusCode: int

    @classmethod
    def success_response(
        cls,
        data: Any = None,
        message: str = "Success",
        status_code: int = STATUS_OK
    ) -> "StandardResponse":
        """Helper to create a success response."""
        return cls(success=True, data=data, message=message, statusCode=status_code)

    @classmethod
    def error_response(
        cls,
        message: str,
        status_code: int = STATUS_INTERNAL_SERVER_ERROR,
        data: Any = None
    ) -> "StandardResponse":
        """Helper to create an error response."""
        return cls(success=False, data=data, message=message, statusCode=status_code)