"""
migrate_to_memory.py — Migration script to convert Context Store to Project Memory
"""
import sqlite3
import json
import logging
from mcp_config import DB_PATH

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("Migration")

def migrate():
    logger.info(f"Starting migration of {DB_PATH}...")

    try:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        # 1. Create the new project_memory table
        logger.info("Creating 'project_memory' table...")
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS project_memory (
                domain      TEXT NOT NULL,
                concept     TEXT NOT NULL,
                value       TEXT NOT NULL,
                tags        TEXT NOT NULL DEFAULT '[]',
                created_at  TEXT NOT NULL,
                updated_at  TEXT NOT NULL,
                expires_at  TEXT,
                shared_from  TEXT,
                links       TEXT NOT NULL DEFAULT '[]',
                metadata    TEXT NOT NULL DEFAULT '{}',
                PRIMARY KEY (domain, concept)
            )
        """)

        # 2. Migrate data from 'context' to 'project_memory'
        logger.info("Migrating data from 'context' table...")

        # Check if 'context' table exists
        table_exists = cursor.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='context'"
        ).fetchone()

        if not table_exists:
            logger.warning("Table 'context' not found. Nothing to migrate.")
        else:
            # Perform migration
            # namespace -> domain
            # key -> concept
            # value, tags, timestamps are preserved
            # links and metadata are initialized as empty
            cursor.execute("""
                INSERT OR REPLACE INTO project_memory (
                    domain, concept, value, tags, created_at, updated_at, expires_at, shared_from, links, metadata
                )
                SELECT
                    namespace, key, value, tags, created_at, updated_at, expires_at, shared_from, '[]', '{}'
                FROM context
            """)
            migrated_count = cursor.rowcount
            logger.info(f"Successfully migrated {migrated_count} entries.")

        # 3. Verify migration
        total_memories = cursor.execute("SELECT COUNT(*) as n FROM project_memory").fetchone()["n"]
        logger.info(f"Total memories in 'project_memory' table: {total_memories}")

        # 4. Drop the old 'context' table (since this is a conversion)
        if table_exists:
            logger.info("Dropping old 'context' table...")
            cursor.execute("DROP TABLE context")

        conn.commit()
        conn.close()
        logger.info("Migration completed successfully.")

    except Exception as e:
        logger.error(f"Migration failed: {e}")
        raise

if __name__ == "__main__":
    migrate()
