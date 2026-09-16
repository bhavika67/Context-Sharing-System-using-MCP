"""
responses.py — Standardized API response envelope
"""
from typing import Any, Optional, Generic, TypeVar
from pydantic import BaseModel
from fastapi.responses import JSONResponse

T = TypeVar("T")

class ApiResponse(BaseModel, Generic[T]):
    success: bool
    data: Optional[T] = None
    error: Optional[dict] = None

def wrap_response(data: Any = None, error: Optional[dict] = None, status_code: int = 200) -> JSONResponse:
    """
    Wraps data or error into a standardized ApiResponse envelope.
    """
    success = error is None
    response_body = ApiResponse(
        success=success,
        data=data,
        error=error
    )
    return JSONResponse(
        status_code=status_code,
        content=response_body.model_dump()
    )
