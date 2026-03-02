"""Initialize LightRAG with all existing papers."""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from rag.ingest import ingest_all_papers


async def main() -> None:
    count = await ingest_all_papers()
    print(f"Ingested {count} papers into LightRAG")


if __name__ == "__main__":
    asyncio.run(main())
