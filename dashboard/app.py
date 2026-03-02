"""Research Hub Dashboard — FastAPI + htmx + DaisyUI."""

from __future__ import annotations

import json
from collections import Counter
from pathlib import Path
from typing import Any

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

DATA_DIR = Path(__file__).resolve().parent.parent / "data" / "papers"
TEMPLATES_DIR = Path(__file__).resolve().parent / "templates"

app = FastAPI(title="Research Hub Dashboard")
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))


def load_papers() -> list[dict[str, Any]]:
    """Scan data/papers/*.json and return papers sorted by date descending."""
    papers: list[dict[str, Any]] = []
    if not DATA_DIR.exists():
        return papers
    for path in DATA_DIR.glob("*.json"):
        try:
            paper = json.loads(path.read_text(encoding="utf-8"))
            papers.append(paper)
        except (json.JSONDecodeError, KeyError):
            continue
    papers.sort(key=lambda p: p.get("date", ""), reverse=True)
    return papers


def load_mindmap(paper_id: str) -> str | None:
    """Load the .mindmap.md content for a given paper id."""
    md_path = DATA_DIR / f"{paper_id}.mindmap.md"
    if md_path.exists():
        return md_path.read_text(encoding="utf-8")
    return None


def compute_stats(papers: list[dict[str, Any]]) -> dict[str, Any]:
    """Compute aggregate statistics from papers."""
    tag_counter: Counter[str] = Counter()
    for p in papers:
        for tag in p.get("tags", []):
            tag_counter[tag] += 1
    return {
        "total": len(papers),
        "tags": tag_counter.most_common(),
    }


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------


@app.get("/", response_class=HTMLResponse)
async def index(request: Request) -> HTMLResponse:
    papers = load_papers()
    stats = compute_stats(papers)
    return templates.TemplateResponse(
        "index.html", {"request": request, "papers": papers, "stats": stats}
    )


@app.get("/paper/{paper_id}", response_class=HTMLResponse)
async def paper_detail(request: Request, paper_id: str) -> HTMLResponse:
    papers = load_papers()
    paper = next((p for p in papers if p.get("id") == paper_id), None)
    if paper is None:
        return HTMLResponse("<h1>Paper not found</h1>", status_code=404)
    mindmap = load_mindmap(paper_id)
    return templates.TemplateResponse(
        "paper.html", {"request": request, "paper": paper, "mindmap": mindmap}
    )


@app.get("/frag/papers", response_class=HTMLResponse)
async def frag_papers(request: Request) -> HTMLResponse:
    papers = load_papers()
    return templates.TemplateResponse(
        "_paper_list.html", {"request": request, "papers": papers}
    )


@app.get("/frag/stats", response_class=HTMLResponse)
async def frag_stats(request: Request) -> HTMLResponse:
    papers = load_papers()
    stats = compute_stats(papers)
    return templates.TemplateResponse(
        "_stats.html", {"request": request, "stats": stats}
    )
