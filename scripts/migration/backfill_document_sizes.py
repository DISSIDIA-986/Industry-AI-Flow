#!/usr/bin/env python3
"""One-time migration: backfill size_bytes for seed documents in the documents table.

Seed documents loaded via the vectorization pipeline often have size_bytes=0
because the size was never persisted. This script reads the real file size
from disk and updates the database.

Usage:
    python -m scripts.migration.backfill_document_sizes
    # or from project root:
    python scripts/migration/backfill_document_sizes.py
"""

import os
import sys
from pathlib import Path

# Allow running from project root
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from backend.config import Settings
from backend.services.database.driver_compat import connect as connect_db


def main() -> None:
    settings = Settings()
    conn = connect_db(settings.database_url)
    cur = conn.cursor()

    try:
        cur.execute(
            "SELECT id, filename, filepath FROM documents "
            "WHERE COALESCE(size_bytes, 0) = 0"
        )
        rows = cur.fetchall()
        print(f"Found {len(rows)} documents with size_bytes=0")

        updated = 0
        missing = 0
        for doc_id, filename, filepath in rows:
            if not filepath:
                print(f"  SKIP {filename}: no filepath")
                missing += 1
                continue

            p = Path(filepath)
            if not p.is_absolute():
                # Try resolving relative to project root
                p = Path(__file__).resolve().parents[2] / filepath

            if p.exists():
                size = p.stat().st_size
                if size > 0:
                    cur.execute(
                        "UPDATE documents SET size_bytes = %s WHERE id = %s",
                        (size, doc_id),
                    )
                    updated += 1
                    print(f"  OK   {filename}: {size:,} bytes")
                else:
                    print(f"  SKIP {filename}: file exists but 0 bytes")
                    missing += 1
            else:
                print(f"  MISS {filename}: {filepath} not found on disk")
                missing += 1

        conn.commit()
        print(f"\nDone: {updated} updated, {missing} skipped/missing")

    except Exception as e:
        conn.rollback()
        print(f"ERROR: {e}")
        sys.exit(1)
    finally:
        cur.close()
        conn.close()


if __name__ == "__main__":
    main()
