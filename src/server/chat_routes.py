"""
chat_routes.py — /chat endpoints + OpenAI integration

Maintains per-domain conversation history in memory.
"""

import json
from fastapi import APIRouter, Depends
from openai import AsyncOpenAI

from server_config import settings
from mcp_client import mcp_call
from models import ChatRequest
from responses import wrap_response
from auth import validate_api_key

router = APIRouter(tags=["chat"], dependencies=[Depends(validate_api_key)])

openai = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)

_histories: dict[str, list[dict]] = {}
MAX_TURNS = 20  # user+assistant pairs kept per domain

def get_histories() -> dict[str, list[dict]]:
    """Return the live histories dict (consumed by stats_routes)."""
    return _histories


@router.post("/chat", summary="Chat with OpenAI using MCP context")
async def chat(req: ChatRequest):
    # 1. Pull stored context for the domain
    raw = await mcp_call("list_memories", domain=req.domain)
    try:
        entries = json.loads(raw)
    except Exception:
        entries = []

    # 2. Build system prompt
    if entries:
        lines = [f"You are a helpful assistant. Shared context from domain '{req.domain}':\n"]
        for e in entries:
            val = await mcp_call("get_memory", concept=e["concept"], domain=req.domain)
            # get_memory returns JSON now, extract 'value'
            try:
                val_data = json.loads(val)
                val_text = val_data.get("value", val)
            except Exception:
                val_text = val
            lines.append(f"[{e['concept']}]: {val_text}")
        system_prompt = "\n".join(lines)
    else:
        system_prompt = "You are a helpful assistant. No context stored yet."

    # 3. Append user message and build full message list
    history = _histories.setdefault(req.domain, [])
    history.append({"role": "user", "content": req.message})
    messages = [{"role": "system", "content": system_prompt}] + history

    # 4. Call OpenAI
    try:
        response = await openai.chat.completions.create(
            model=settings.OPENAI_MODEL,
            messages=messages,
        )
        reply = response.choices[0].message.content
        history.append({"role": "assistant", "content": reply})

        # Trim old turns
        if len(history) > MAX_TURNS * 2:
            _histories[req.domain] = history[-(MAX_TURNS * 2):]

        return wrap_response(data={
            "reply": reply,
            "domain": req.domain,
            "context_keys": [e["concept"] for e in entries],
            "memory_turns": len(history) // 2,
        })
    except Exception as e:
        return wrap_response(error={"code": "OPENAI_ERROR", "message": str(e)}, status_code=500)


@router.post("/chat/reset", summary="Reset conversation history for a domain")
async def reset_chat(domain: str = "default"):
    _histories.pop(domain, None)
    return wrap_response(data=f"History cleared for domain '{domain}'.")
