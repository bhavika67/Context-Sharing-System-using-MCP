"""
models.py — Pydantic request models shared across route files
"""

from typing import Optional
from pydantic import BaseModel


class SaveMemoryRequest(BaseModel):
    domain:      str = "default"
    concept:     str
    value:       str
    tags:        str = ""
    ttl_seconds: int = 0
    metadata:    Optional[str] = "{}"


class ShareMemoryRequest(BaseModel):
    concept:          str
    source_domain:    str
    target_domain:    str
    new_concept:      Optional[str] = None


class LinkMemoryRequest(BaseModel):
    source_domain:    str
    source_concept:   str
    target_domain:    str
    target_concept:   str


class ChatRequest(BaseModel):
    message:   str
    domain:    str = "default"
