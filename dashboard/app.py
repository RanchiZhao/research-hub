"""Research Hub Dashboard — FastAPI + htmx + DaisyUI."""

from __future__ import annotations

import json
import re
from collections import Counter
from pathlib import Path
from typing import Any

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from lightrag import QueryParam

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


def build_graph_data(papers: list[dict[str, Any]]) -> dict[str, Any]:
    """Build nodes and links for D3.js force-directed graph."""
    arxiv_map: dict[str, dict[str, Any]] = {}
    for p in papers:
        aid = p.get("arxiv_id")
        if aid:
            arxiv_map[aid] = p

    nodes = [
        {
            "id": p["id"],
            "name": p.get("title", "")[:30],
            "arxiv_id": p.get("arxiv_id"),
        }
        for p in papers
    ]

    links: list[dict[str, str]] = []
    for p in papers:
        for ref in p.get("key_references", []):
            target_arxiv = ref.get("arxiv_id")
            if not target_arxiv:
                continue
            target_paper = arxiv_map.get(target_arxiv)
            if target_paper:
                links.append(
                    {
                        "source": p["id"],
                        "target": target_paper["id"],
                        "relationship": ref.get("relationship", "extends"),
                    }
                )

    return {"nodes": nodes, "links": links}


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
    arxiv_map = {p["arxiv_id"]: p for p in papers if p.get("arxiv_id")}

    # Compute prev/next papers (papers are sorted newest-first)
    idx = next(i for i, p in enumerate(papers) if p.get("id") == paper_id)
    prev_paper = papers[idx - 1] if idx > 0 else None
    next_paper = papers[idx + 1] if idx < len(papers) - 1 else None

    return templates.TemplateResponse(
        "paper.html",
        {
            "request": request,
            "paper": paper,
            "mindmap": mindmap,
            "arxiv_map": arxiv_map,
            "prev_paper": prev_paper,
            "next_paper": next_paper,
        },
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


@app.get("/graph", response_class=HTMLResponse)
async def graph(request: Request) -> HTMLResponse:
    return templates.TemplateResponse("graph.html", {"request": request})


@app.get("/api/graph-data")
async def graph_data() -> JSONResponse:
    papers = load_papers()
    data = build_graph_data(papers)
    return JSONResponse(data)


@app.get("/search-kg", response_class=HTMLResponse)
async def search_kg_page(request: Request) -> HTMLResponse:
    return templates.TemplateResponse("search_kg.html", {"request": request})


def parse_content_string(content: str) -> dict | None:
    """Parse a 'Title: X\nAuthors: Y\n...' content string into a dict."""
    if not content:
        return None
    result: dict[str, Any] = {}
    for line in content.split("\n"):
        line = line.strip()
        if not line:
            continue
        if line.startswith("Title: "):
            result["title"] = line[7:]
        elif line.startswith("Authors: "):
            result["authors"] = line[9:]
        elif line.startswith("Date: "):
            result["date"] = line[6:]
        elif line.startswith("Summary: "):
            result["summary"] = line[9:]
        elif line.startswith("Problem: "):
            result["problem"] = line[9:]
        elif line.startswith("Method: "):
            result["method"] = line[8:]
        elif line.startswith("Innovation: "):
            result["innovation"] = line[12:]
        elif line.startswith("Results: "):
            result["results"] = line[9:]
        elif line.startswith("Tags: "):
            result["tags"] = [t.strip() for t in line[6:].split(",")]
        elif line.startswith("Benchmark: "):
            result.setdefault("benchmarks", []).append(line[11:])
    return result if result.get("title") else None


def parse_search_results(raw: str) -> list[dict]:
    """Parse LightRAG raw output into structured paper chunks."""
    if not raw or not raw.strip():
        return []

    json_match = re.search(r"```json\s*(.*?)```", raw, re.DOTALL)
    if json_match:
        json_text = json_match.group(1).strip()
        chunks = []
        for match in re.finditer(r'\{[^{}]*"content"[^{}]*\}', json_text, re.DOTALL):
            try:
                obj = json.loads(match.group())
                chunk = parse_content_string(obj.get("content", ""))
                if chunk:
                    chunks.append(chunk)
            except json.JSONDecodeError:
                continue
        if chunks:
            return chunks

    return [{"title": "Search Results", "summary": raw[:500]}]


@app.post("/api/search-kg")
async def api_search_kg(request: Request) -> JSONResponse:
    body = await request.json()
    question = body.get("question", "")
    if not question.strip():
        return JSONResponse({"results": []})
    from rag.engine import create_rag

    rag = create_rag()
    await rag.initialize_storages()
    try:
        result = await rag.aquery(question, param=QueryParam(mode="naive"))
        papers = parse_search_results(result)
        return JSONResponse({"results": papers})
    finally:
        await rag.finalize_storages()
