"""
database.py — Project Memory persistence layer
All raw DB operations live here. No MCP or business logic.
"""
import json
import sqlite3
import time
from datetime import datetime, timezone
from typing import Optional

from mcp_config import DB_PATH


# ── Connection ────────────────────────────────────────────────────────────────
def get_db() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("""
        CREATE TABLE IF NOT EXISTS project_memory (
            domain      TEXT NOT NULL,
            concept     TEXT NOT NULL,
            value       TEXT NOT NULL,
            tags        TEXT NOT NULL DEFAULT '[]',
            created_at  TEXT NOT NULL,
            updated_at  TEXT NOT NULL,
            expires_at  TEXT,
            shared_from TEXT,
            links       TEXT NOT NULL DEFAULT '[]',
            metadata    TEXT NOT NULL DEFAULT '{}',
            PRIMARY KEY (domain, concept)
        )
    """)
    conn.commit()
    return conn


# ── Time helpers ──────────────────────────────────────────────────────────────
def now() -> str:
    return datetime.now(timezone.utc).isoformat()


def expires_at(ttl: int) -> Optional[str]:
    if ttl <= 0:
        return None
    return datetime.fromtimestamp(time.time() + ttl, tz=timezone.utc).isoformat()


def is_expired(exp: Optional[str]) -> bool:
    if not exp:
        return False
    return datetime.fromisoformat(exp) < datetime.now(timezone.utc)


# ── CRUD operations ───────────────────────────────────────────────────────────
def upsert_memory(domain: str, concept: str, value: str,
                  tag_list: list, exp: Optional[str],
                  metadata: dict = None) -> str:
    """Insert or update a memory entry. Returns 'created' or 'updated'."""
    ts = now()
    meta_json = json.dumps(metadata or {})
    with get_db() as db:
        if existing := db.execute(
            "SELECT concept FROM project_memory WHERE domain=? AND concept=?",
            (domain, concept),
        ).fetchone():
            db.execute(
                "UPDATE project_memory SET value=?, tags=?, updated_at=?, expires_at=?, metadata=? "
                "WHERE domain=? AND concept=?",
                (value, json.dumps(tag_list), ts, exp, meta_json, domain, concept)
            )
            return "updated"
        db.execute(
            "INSERT INTO project_memory (domain, concept, value, tags, created_at, updated_at, expires_at, shared_from, links, metadata) "
            "VALUES (?,?,?,?,?,?,?,?,?,?)",
            (domain, concept, value, json.dumps(tag_list), ts, ts, exp, None, '[]', meta_json)
        )
        return "created"


def fetch_memory(domain: str, concept: str) -> Optional[sqlite3.Row]:
    with get_db() as db:
        return db.execute(
            "SELECT value, expires_at, links, metadata FROM project_memory WHERE domain=? AND concept=?",
            (domain, concept)
        ).fetchone()


def remove_memory(domain: str, concept: str) -> int:
    with get_db() as db:
        cursor = db.execute(
            "DELETE FROM project_memory WHERE domain=? AND concept=?", (domain, concept)
        )
    return cursor.rowcount


def fetch_domain(domain: str) -> list:
    with get_db() as db:
        return db.execute(
            "SELECT concept, value, tags, updated_at, expires_at FROM project_memory WHERE domain=?",
            (domain,)
        ).fetchall()


def remove_expired_memories(domain: str, concepts: list):
    with get_db() as db:
        db.executemany(
            "DELETE FROM project_memory WHERE domain=? AND concept=?",
            [(domain, c) for c in concepts]
        )


def search_memories(domain: str, query: str) -> list:
    with get_db() as db:
        return db.execute(
            "SELECT concept, value, tags, expires_at FROM project_memory "
            "WHERE domain=? AND (value LIKE ? OR concept LIKE ?)",
            (domain, f"%{query}%", f"%{query}%")
        ).fetchall()


def copy_memory(source_domain: str, concept: str, target_domain: str, dest_concept: str):
    with get_db() as db:
        row = db.execute(
            "SELECT * FROM project_memory WHERE domain=? AND concept=?", (source_domain, concept)
        ).fetchone()
        if not row:
            return None
        db.execute(
            "INSERT OR REPLACE INTO project_memory (domain, concept, value, tags, created_at, updated_at, expires_at, shared_from, links, metadata) "
            "VALUES (?,?,?,?,?,?,?,?,?,?)",
            (target_domain, dest_concept, row["value"], row["tags"],
             row["created_at"], now(), row["expires_at"], f"{source_domain}/{concept}",
             row["links"], row["metadata"])
        )
        return row


def fetch_all_domains() -> list:
    with get_db() as db:
        return db.execute(
            "SELECT domain, COUNT(*) as count FROM project_memory GROUP BY domain"
        ).fetchall()


def remove_domain(domain: str) -> int:
    with get_db() as db:
        cursor = db.execute("DELETE FROM project_memory WHERE domain=?", (domain,))
    return cursor.rowcount


def fetch_memory_stats() -> dict:
    with get_db() as db:
        total   = db.execute("SELECT COUNT(*) as n FROM project_memory").fetchone()["n"]
        dom_cnt = db.execute("SELECT COUNT(DISTINCT domain) as n FROM project_memory").fetchone()["n"]
        expired = db.execute(
            "SELECT COUNT(*) as n FROM project_memory WHERE expires_at IS NOT NULL AND expires_at < ?",
            (now(),)
        ).fetchone()["n"]
    return {"total": total, "domains": dom_cnt, "expired": expired}


# ── Linking Logic ───────────────────────────────────────────────────────────────

def add_memory_link(source_domain: str, source_concept: str, target_domain: str, target_concept: str):
    """Creates a link from one memory entry to another."""
    with get_db() as db:
        # 1. Verify target exists
        target = db.execute(
            "SELECT concept FROM project_memory WHERE domain=? AND concept=?",
            (target_domain, target_concept)
        ).fetchone()
        if not target:
            raise ValueError(f"Target memory {target_domain}/{target_concept} not found.")

        # 2. Fetch existing links
        row = db.execute(
            "SELECT links FROM project_memory WHERE domain=? AND concept=?",
            (source_domain, source_concept)
        ).fetchone()
        if not row:
            raise ValueError(f"Source memory {source_domain}/{source_concept} not found.")

        links = json.loads(row["links"])
        # Avoid duplicates
        if any(l["domain"] == target_domain and l["concept"] == target_concept for l in links):
            return False

        # 3. Update links
        links.append({"domain": target_domain, "concept": target_concept})
        db.execute(
            "UPDATE project_memory SET links=? WHERE domain=? AND concept=?",
            (json.dumps(links), source_domain, source_concept)
        )
        return True


def fetch_memory_links(domain: str, concept: str) -> list:
    """Retrieves all linked memories for a given entry."""
    with get_db() as db:
        row = db.execute(
            "SELECT links FROM project_memory WHERE domain=? AND concept=?",
            (domain, concept)
        ).fetchone()
        if not row:
            return []
        return json.loads(row["links"])
