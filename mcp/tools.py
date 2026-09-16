"""
tools.py — All MCP tools (save, get, list, delete, search, share, domains, stats)
Registered on the FastMCP instance passed in from server.py
"""
import json
from typing import Optional

from mcp_config import API_KEY, DEFAULT_TTL, RATE_LIMIT, DB_PATH, TRANSPORT
from auth import check_auth, check_rate
from database import (
    upsert_memory, fetch_memory, remove_memory, fetch_domain,
    remove_expired_memories, search_memories, copy_memory,
    fetch_all_domains, remove_domain, fetch_memory_stats,
    expires_at, is_expired,
    add_memory_link, fetch_memory_links,
)
from logger import logger
from .jira_tools import register_jira_tools


def register_tools(mcp):
    """Register all tools onto the FastMCP instance."""

    # Register Jira-specific tools
    register_jira_tools(mcp)

    @mcp.tool()
    def save_memory(
        concept: str,
        value: str,
        domain: str = "default",
        tags: str = "",
        ttl_seconds: int = 0,
        api_key: str = "",
        metadata_json: str = "{}",
    ) -> str:
        """Store a memory. Optionally set TTL (seconds until expiry, 0=forever)."""
        # Strip domain and concept to prevent leading/trailing space bugs
        domain = domain.strip()
        concept = concept.strip()

        if not check_auth(api_key):
            logger.warning({"action": "save_memory", "result": "auth_failed", "domain": domain, "concept": concept})
            return "Error: Invalid API key."
        if not check_rate():
            return "Error: Rate limit exceeded. Try again in a minute."

        tag_list = [t.strip() for t in tags.split(",") if t.strip()]
        # ttl_seconds=0 means "no expiry"
        effective_ttl = ttl_seconds if ttl_seconds > 0 else 0
        exp = expires_at(effective_ttl)

        try:
            meta = json.loads(metadata_json) if metadata_json else {}
        except json.JSONDecodeError:
            meta = {"error": "Invalid metadata JSON"}

        action = upsert_memory(domain, concept, value, tag_list, exp, metadata=meta)

        logger.info({"action": "save_memory", "domain": domain, "concept": concept, "result": action})
        ttl_note = f" (expires in {effective_ttl}s)" if exp else ""
        return f"{action.capitalize()} '{concept}' in '{domain}'{ttl_note}."


    @mcp.tool()
    def get_memory(concept: str, domain: str = "default", api_key: str = "") -> str:
        """Retrieve a memory by concept."""
        domain = domain.strip()
        concept = concept.strip()

        if not check_auth(api_key):
            return "Error: Invalid API key."
        if not check_rate():
            return "Error: Rate limit exceeded."

        row = fetch_memory(domain, concept)
        if not row:
            return f"Concept '{concept}' not found in '{domain}'."
        if is_expired(row["expires_at"]):
            remove_memory(domain, concept)
            return f"Concept '{concept}' has expired and was removed."

        logger.info({"action": "get_memory", "domain": domain, "concept": concept})

        # Return value along with links and metadata
        return json.dumps({
            "value": row["value"],
            "links": json.loads(row["links"]),
            "metadata": json.loads(row["metadata"])
        }, indent=2)


    @mcp.tool()
    def list_memories(domain: str = "default", tag_filter: str = "", api_key: str = "") -> str:
        """List all concepts in a domain. Expired entries are auto-removed."""
        domain = domain.strip()

        if not check_auth(api_key):
            return "Error: Invalid API key."
        if not check_rate():
            return "Error: Rate limit exceeded."

        rows = fetch_domain(domain)
        results = []
        expired_concepts = []

        for row in rows:
            if is_expired(row["expires_at"]):
                expired_concepts.append(row["concept"])
                continue
            tag_list = json.loads(row["tags"])
            if tag_filter and tag_filter not in tag_list:
                continue
            results.append({
                "concept": row["concept"],
                "tags": tag_list,
                "updated_at": row["updated_at"],
                "expires_at": row["expires_at"],
                "preview": row["value"][:100] + ("…" if len(row["value"]) > 100 else ""),
            })

        if expired_concepts:
            remove_expired_memories(domain, expired_concepts)

        if not results:
            return f"No memories in domain '{domain}'" + (f" with tag '{tag_filter}'" if tag_filter else "") + "."
        return json.dumps(results, indent=2)


    @mcp.tool()
    def delete_memory(concept: str, domain: str = "default", api_key: str = "") -> str:
        """Delete a memory entry."""
        domain = domain.strip()
        concept = concept.strip()

        if not check_auth(api_key):
            return "Error: Invalid API key."

        count = remove_memory(domain, concept)
        if count == 0:
            return f"Concept '{concept}' not found in '{domain}'."
        logger.info({"action": "delete_memory", "domain": domain, "concept": concept})
        return f"Deleted '{concept}' from '{domain}'."


    @mcp.tool()
    def search_memories(query: str, domain: str = "default", api_key: str = "") -> str:
        """Full-text search across all values in a domain."""
        domain = domain.strip()

        if not check_auth(api_key):
            return "Error: Invalid API key."
        if not check_rate():
            return "Error: Rate limit exceeded."

        rows = search_memories(domain, query)
        matches = [
            {"concept": r["concept"], "tags": json.loads(r["tags"]), "preview": r["value"][:100]}
            for r in rows if not is_expired(r["expires_at"])
        ]
        if not matches:
            return f"No matches for '{query}' in '{domain}'."
        return json.dumps(matches, indent=2)


    @mcp.tool()
    def share_memory(
        concept: str,
        source_domain: str,
        target_domain: str,
        new_concept: Optional[str] = None,
        api_key: str = "",
    ) -> str:
        """Copy a memory entry from one domain to another."""
        source_domain = source_domain.strip()
        target_domain = target_domain.strip()
        concept = concept.strip()

        if not check_auth(api_key):
            return "Error: Invalid API key."

        dest_concept = (new_concept.strip() if new_concept else None) or concept
        row = copy_memory(source_domain, concept, target_domain, dest_concept)
        if row is None:
            return f"Concept '{concept}' not found in '{source_domain}'."
        if is_expired(row["expires_at"]):
            return f"Concept '{concept}' has expired."

        logger.info({"action": "share_memory", "from": f"{source_domain}/{concept}", "to": f"{target_domain}/{dest_concept}"})
        return f"Shared '{concept}' from '{source_domain}' → '{dest_concept}' in '{target_domain}'."


    @mcp.tool()
    def list_domains(api_key: str = "") -> str:
        """List all domains and their memory counts."""
        if not check_auth(api_key):
            return "Error: Invalid API key."

        rows = fetch_all_domains()
        if not rows:
            return "No domains yet."
        return json.dumps({r["domain"]: r["count"] for r in rows}, indent=2)


    @mcp.tool()
    def clear_domain(domain: str, api_key: str = "") -> str:
        """Delete all memories in a domain."""
        domain = domain.strip()

        if not check_auth(api_key):
            return "Error: Invalid API key."

        count = remove_domain(domain)
        logger.info({"action": "clear_domain", "domain": domain, "deleted": count})
        return f"Cleared '{domain}' ({count} entries removed)."


    @mcp.tool()
    def server_stats(api_key: str = "") -> str:
        """Return server stats: total memories, domains, expired count."""
        if not check_auth(api_key):
            return "Error: Invalid API key."

        stats = fetch_memory_stats()
        return json.dumps({
            "total_memories": stats["total"],
            "domains": stats["domains"],
            "expired_pending_cleanup": stats["expired"],
            "rate_limit_per_min": RATE_LIMIT,
            "auth_enabled": bool(API_KEY),
            "db_path": DB_PATH,
            "transport": TRANSPORT,
        }, indent=2)

    @mcp.tool()
    def link_memories(
        source_domain: str,
        source_concept: str,
        target_domain: str,
        target_concept: str,
        api_key: str = "",
    ) -> str:
        """Create a relational link between two memories."""
        if not check_auth(api_key):
            return "Error: Invalid API key."

        try:
            success = add_memory_link(
                source_domain.strip(), source_concept.strip(),
                target_domain.strip(), target_concept.strip()
            )
            if success:
                logger.info({"action": "link_memories", "source": f"{source_domain}/{source_concept}", "target": f"{target_domain}/{target_concept}"})
                return f"Successfully linked '{source_concept}' → '{target_concept}'."
            else:
                return f"Link already exists between '{source_concept}' and '{target_concept}'."
        except ValueError as e:
            return f"Error: {str(e)}"
