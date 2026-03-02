"""Ingest papers into LightRAG for semantic search."""
from __future__ import annotations

import json
from pathlib import Path

from .engine import PAPERS_DIR, create_rag


def format_paper_text(paper: dict) -> str:
    """Format paper JSON into natural language text for LightRAG."""
    parts: list[str] = []
    parts.append(f"Title: {paper.get('title', '')}")
    if paper.get("authors"):
        parts.append(f"Authors: {', '.join(paper['authors'])}")
    if paper.get("date"):
        parts.append(f"Date: {paper['date']}")
    s = paper.get("summary", {})
    if s.get("one_liner"):
        parts.append(f"Summary: {s['one_liner']}")
    if s.get("problem"):
        parts.append(f"Problem: {s['problem']}")
    if s.get("method"):
        parts.append(f"Method: {s['method']}")
    if s.get("innovation"):
        parts.append(f"Innovation: {s['innovation']}")
    if s.get("results"):
        parts.append(f"Results: {s['results']}")
    if paper.get("tags"):
        parts.append(f"Tags: {', '.join(paper['tags'])}")
    for ref in paper.get("key_references", []):
        parts.append(f"Reference: {ref.get('title', '')} ({ref.get('relationship', '')})")
    for bm in paper.get("benchmarks", []):
        parts.append(f"Benchmark: {bm.get('dataset', '')} {bm.get('metric', '')}: {bm.get('score', '')}")
    return "\n".join(parts)


async def ingest_paper(paper_path: Path) -> None:
    """Insert a single paper's text into LightRAG."""
    paper = json.loads(paper_path.read_text(encoding="utf-8"))
    text = format_paper_text(paper)
    rag = create_rag()
    await rag.initialize_storages()
    try:
        await rag.ainsert(text)
    finally:
        await rag.finalize_storages()


async def ingest_all_papers() -> int:
    """Insert all papers into LightRAG. Returns count."""
    rag = create_rag()
    await rag.initialize_storages()
    count = 0
    try:
        for path in sorted(PAPERS_DIR.glob("*.json")):
            paper = json.loads(path.read_text(encoding="utf-8"))
            text = format_paper_text(paper)
            await rag.ainsert(text)
            count += 1
    finally:
        await rag.finalize_storages()
    return count
