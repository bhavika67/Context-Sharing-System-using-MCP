"""
memory_routes.py — /memory/* endpoints
"""

import json
from fastapi import APIRouter, HTTPException, Query, Depends

from mcp_client import mcp_call
from models import SaveMemoryRequest, ShareMemoryRequest, LinkMemoryRequest
from responses import wrap_response
from auth import validate_api_key

router = APIRouter(
    prefix="/memory",
    tags=["memory"],
    dependencies=[Depends(validate_api_key)]
)


@router.post("/save", status_code=201, summary="Store a memory entry")
async def save_memory(req: SaveMemoryRequest):
    result = await mcp_call(
        "save_memory",
        concept=req.concept, value=req.value,
        domain=req.domain, tags=req.tags,
        ttl_seconds=req.ttl_seconds,
        metadata_json=req.metadata,
    )
    return wrap_response(data=result)


@router.get("/get/{domain}/{concept}", summary="Retrieve a memory entry")
async def get_memory(domain: str, concept: str):
    result = await mcp_call("get_memory", concept=concept, domain=domain)
    if "not found" in result:
        return wrap_response(error={"code": "NOT_FOUND", "message": result}, status_code=404)

    # Result from tool is JSON
    try:
        data = json.loads(result)
        return wrap_response(data={"concept": concept, "domain": domain, **data})
    except Exception:
        return wrap_response(data={"concept": concept, "domain": domain, "value": result})


@router.get("/list/{domain}", summary="List all memories in a domain")
async def list_memories(domain: str, tag_filter: str = Query(default="")):
    result = await mcp_call("list_memories", domain=domain, tag_filter=tag_filter)
    try:
        return wrap_response(data={"domain": domain, "entries": json.loads(result)})
    except Exception:
        return wrap_response(data={"domain": domain, "entries": [], "message": result})


@router.delete("/delete/{domain}/{concept}", status_code=204, summary="Delete a memory entry")
async def delete_memory(domain: str, concept: str):
    result = await mcp_call("delete_memory", concept=concept, domain=domain)
    if "not found" in result:
        return wrap_response(error={"code": "NOT_FOUND", "message": result}, status_code=404)
    return wrap_response(data=result)


@router.get("/search/{domain}", summary="Search memories in a domain")
async def search_memories(domain: str, query: str = Query(...)):
    result = await mcp_call("search_memories", query=query, domain=domain)
    try:
        return wrap_response(data={"domain": domain, "matches": json.loads(result)})
    except Exception:
        return wrap_response(data={"domain": domain, "matches": [], "message": result})


@router.post("/share", summary="Share a memory entry between domains")
async def share_memory(req: ShareMemoryRequest):
    result = await mcp_call(
        "share_memory",
        concept=req.concept,
        source_domain=req.source_domain,
        target_domain=req.target_domain,
        new_concept=req.new_concept,
    )
    return wrap_response(data=result)


@router.post("/link", summary="Link two memories together")
async def link_memories(req: LinkMemoryRequest):
    result = await mcp_call(
        "link_memories",
        source_domain=req.source_domain,
        source_concept=req.source_concept,
        target_domain=req.target_domain,
        target_concept=req.target_concept,
    )
    return wrap_response(data=result)
