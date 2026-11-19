"""
Standalone CLI script to build and persist vector embeddings from ./articles into ./storage.
Run via: python index_data.py
"""

import sys
from pathlib import Path


BACKEND_DIR = Path(__file__).resolve().parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.core.logger import logger  # noqa: E402
from app.services.article_service import article_service  # noqa: E402


def main():
    try:
        chunks, files = article_service.build_and_persist_index()
        logger.info(
            f"Successfully indexed {chunks} chunk(s) across {len(files)} files."
        )
    except Exception as e:
        logger.error(f"Failed to index financial documents: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
