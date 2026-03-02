"""Paper storage utilities with atomic writes."""
from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path

from models.paper import Paper


def _atomic_write(path: Path, content: str) -> None:
    """Write content to path atomically using temp file + os.rename."""
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=path.parent, suffix=".tmp")
    try:
        with os.fdopen(fd, "w") as f:
            f.write(content)
        os.rename(tmp, path)
    except BaseException:
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise


def save_paper(paper_dict: dict, data_dir: str | Path) -> Paper:
    """Validate, save paper JSON + mindmap atomically. Returns Paper."""
    paper = Paper.from_dict(paper_dict)
    paper.validate()
    data_dir = Path(data_dir)

    json_path = data_dir / f"{paper.id}.json"
    _atomic_write(json_path, json.dumps(paper.to_dict(), ensure_ascii=False, indent=2) + "\n")

    mindmap = _generate_mindmap(paper)
    mindmap_path = data_dir / f"{paper.id}.mindmap.md"
    _atomic_write(mindmap_path, mindmap)

    return paper


def _generate_mindmap(paper: Paper) -> str:
    """Generate a markmap-compatible mindmap markdown."""
    lines = [f"# {paper.title}", ""]
    s = paper.summary
    lines.append("## Problem")
    lines.append(f"- {s.problem}")
    lines.append("")
    lines.append("## Method")
    lines.append(f"- {s.method}")
    lines.append("")
    lines.append("## Innovation")
    lines.append(f"- {s.innovation}")
    lines.append("")
    lines.append("## Results")
    lines.append(f"- {s.results}")
    lines.append("")
    if paper.tags:
        lines.append("## Tags")
        for tag in paper.tags:
            lines.append(f"- {tag}")
        lines.append("")
    return "\n".join(lines) + "\n"


def load_paper(paper_id: str, data_dir: str | Path) -> Paper:
    """Load a single paper by id. Raises FileNotFoundError if missing."""
    path = Path(data_dir) / f"{paper_id}.json"
    return Paper.from_json(path)


def list_all_papers(data_dir: str | Path) -> list[Paper]:
    """List all papers sorted by date descending."""
    data_dir = Path(data_dir)
    if not data_dir.is_dir():
        return []
    papers = []
    for p in data_dir.glob("*.json"):
        if p.name.endswith(".mindmap.json"):
            continue
        papers.append(Paper.from_json(p))
    papers.sort(key=lambda p: p.date, reverse=True)
    return papers


def search_papers(query: str, data_dir: str | Path) -> list[Paper]:
    """Simple text search over title, tags, and one_liner."""
    query_lower = query.lower()
    results = []
    for paper in list_all_papers(data_dir):
        searchable = " ".join([
            paper.title,
            " ".join(paper.tags),
            paper.summary.one_liner,
        ]).lower()
        if query_lower in searchable:
            results.append(paper)
    return results
