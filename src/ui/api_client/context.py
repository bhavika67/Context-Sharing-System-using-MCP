"""
api_client/context.py — Memory and domain API calls
"""

from .http import api_get, api_post, api_delete


# ── Memory CRUD ──────────────────────────────────────────────────────────────

def save_memory(domain: str, concept: str, value: str, tags: str, ttl: int) -> str:
    if not concept or not value:
        return "Concept and Value are required."
    res = api_post("/memory/save", {
        "domain": domain, "concept": concept, "value": value,
        "tags": tags, "ttl_seconds": int(ttl),
    })
    return res.get("result", res.get("error", "Unknown error"))


def list_memories(domain: str, tag_filter: str = "") -> list[list]:
    res = api_get(f"/memory/list/{domain}", {"tag_filter": tag_filter} if tag_filter else None)
    if "error" in res:
        return [[res["error"], "", "", "", ""]]
    entries = res.get("entries", [])
    rows = []
    for e in entries:
        tags = e.get("tags", [])
        tags_str = ", ".join(tags) if isinstance(tags, list) else str(tags)
        rows.append([
            e.get("concept", ""),
            tags_str or "—",
            e.get("updated_at", "")[:19],
            e.get("expires_at", "never")[:19] if e.get("expires_at") else "never",
            e.get("preview", e.get("value", ""))[:80],
        ])
    return rows


def search_memories(domain: str, query: str) -> list[list]:
    if not query:
        return []
    res = api_get(f"/memory/search/{domain}", {"query": query})
    if "error" in res:
        return [[res["error"], "", "", "", ""]]
    rows = []
    for m in res.get("matches", []):
        tags = m.get("tags", [])
        tags_str = ", ".join(tags) if isinstance(tags, list) else str(tags)
        rows.append([m.get("concept", ""), tags_str or "—", "", "", m.get("preview", "")])
    return rows


def get_memory(domain: str, concept: str) -> str:
    if not concept:
        return "Concept is required."
    res = api_get(f"/memory/get/{domain}/{concept}")
    if "error" in res:
        return res["error"]

    # The API now returns a JSON object with value, links, metadata
    if isinstance(res, dict) and "value" in res:
        val = res["value"]
        links = res.get("links", [])
        meta = res.get("metadata", {})

        link_str = "\nLinks: " + ", ".join([f"{l['domain']}/{l['concept']}" for l in links]) if links else ""
        meta_str = f"\nMeta: {json.dumps(meta)}" if meta else ""
        return f"{val}\n{link_str}{meta_str}"

    return str(res)


def delete_memory(domain: str, concept: str) -> str:
    if not concept:
        return "Concept is required."
    res = api_delete(f"/memory/delete/{domain}/{concept}")
    return res.get("result", res.get("error", "Unknown error"))


# ── Domain operations ──────────────────────────────────────────────────────

def list_domains() -> list[list]:
    res = api_get("/domains")
    if "error" in res:
        return [[res["error"], ""]]
    doms = res.get("domains", {})
    return [[k, v] for k, v in doms.items()] if doms else []


def share_memory(concept: str, src: str, dst: str, new_concept: str) -> str:
    if not concept or not src or not dst:
        return "Concept, source and target domain are required."
    res = api_post("/memory/share", {
        "concept": concept, "source_domain": src,
        "target_domain": dst, "new_concept": new_concept or None,
    })
    return res.get("result", res.get("error", "Unknown error"))


def clear_domain(domain: str) -> str:
    if not domain:
        return "Domain is required."
    res = api_delete(f"/domains/{domain}")
    return res.get("result", res.get("error", "Unknown error"))
