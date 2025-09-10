"""Run local .eml ingestion from a directory (default: sample/).

Usage:
  python scripts/local_ingest.py [directory] [pattern]

Examples:
  python scripts/local_ingest.py
  python scripts/local_ingest.py sample "*.eml"
"""

from __future__ import annotations

import sys
from typing import Optional

from app.db.session import SessionLocal
from app.local.ingest import ingest_eml_files


def main(argv: Optional[list[str]] = None) -> None:
    argv = list(sys.argv[1:] if argv is None else argv)
    directory = argv[0] if len(argv) >= 1 else "sample"
    pattern = argv[1] if len(argv) >= 2 else "*.eml"

    db = SessionLocal()
    try:
        result = ingest_eml_files(db, directory=directory, pattern=pattern, enqueue=True)
        print({"directory": directory, "pattern": pattern, **result})
    finally:
        db.close()


if __name__ == "__main__":
    main()

