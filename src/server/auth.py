"""
auth.py — API authentication for the REST layer
"""
import os
from fastapi import HTTPException, Security, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from server_config import settings

# Security scheme for Bearer tokens
security = HTTPBearer()

def validate_api_key(credentials: HTTPAuthorizationCredentials = Security(security)):
    """
    Dependency to validate the API key provided in the Authorization header.
    """
    token = credentials.credentials
    # We use the same API_KEY from .env as the Bearer token for simplicity
    # In a production system, this would be a JWT or a hashed token from a DB.
    expected_key = os.getenv("MCP_API_KEY")

    if not expected_key:
        # If no API key is configured, we allow access but log a warning
        return True

    if token != expected_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing API Key.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return True
