"""
domain_routes.py — /domains/* endpoints
"""

import json
from fastapi import APIRouter, Depends

from mcp_client import mcp_call
from responses import wrap_response
from auth import validate_api_key

router = APIRouter(
    prefix="/domains",
    tags=["domains"],
    dependencies=[Depends(validate_api_key)]
)


@router.get("", summary="List all domains")
async def list_domains():
    result = await mcp_call("list_domains")
    try:
        return wrap_response(data={"domains": json.loads(result)})
    except Exception:
        return wrap_response(data={"domains": {}, "message": result})


@router.delete("/{domain}", status_code=204, summary="Clear all entries in a domain")
async def clear_domain(domain: str):
    result = await mcp_call("clear_domain", domain=domain)
    return wrap_response(data=result)
