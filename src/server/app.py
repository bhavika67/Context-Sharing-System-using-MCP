"""
app.py — FastAPI application entry point
─────────────────────────────────────────
Architecture:
    Next.js UI → FastAPI (port 8000) → MCP Server → SQLite

Module layout:
    config.py            — env vars & settings
    models.py            — Pydantic request models
    mcp_client.py        — MCP session lifecycle + mcp_call()
    memory_routes.py     — /memory/* endpoints
    domain_routes.py     — /domains/* endpoints
    chat_routes.py       — /chat endpoints + conversation history
    stats_routes.py      — /stats endpoint

Run:
    python src/server/app.py

Docs:
    http://localhost:8000/docs
"""

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from server_config import settings
from mcp_client import lifespan
import memory_routes
import domain_routes
import chat_routes
import stats_routes

# Wire up the histories provider so /stats can report memory turns
stats_routes.set_histories_provider(chat_routes.get_histories)

app = FastAPI(
    title=settings.APP_TITLE,
    description=settings.APP_DESCRIPTION,
    version=settings.APP_VERSION,
    lifespan=lifespan,
)

# Hardened CORS: Restrict origins to the trusted frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",  # Next.js dev server
        "http://127.0.0.1:3000",
    ],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(memory_routes.router)
app.include_router(domain_routes.router)
app.include_router(chat_routes.router)
app.include_router(stats_routes.router)


if __name__ == "__main__":
    uvicorn.run("app:app", host="0.0.0.0", port=8000, reload=False, app_dir="src")
