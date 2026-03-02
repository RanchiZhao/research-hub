"""Paper data model for research-hub."""
from __future__ import annotations

import json
from dataclasses import dataclass, field, asdict
from pathlib import Path


@dataclass
class Summary:
    problem: str
    method: str
    innovation: str
    results: str
    one_liner: str


@dataclass
class Benchmark:
    dataset: str
    metric: str
    score: str
    notes: str = ""


@dataclass
class Reference:
    title: str
    relationship: str
    arxiv_id: str | None = None


@dataclass
class Paper:
    id: str
    title: str
    source_url: str
    summary: Summary
    source_type: str = "arxiv_paper"
    ingested_at: str = ""
    arxiv_id: str = ""
    authors: list[str] = field(default_factory=list)
    affiliations: list[str] = field(default_factory=list)
    date: str = ""
    categories: list[str] = field(default_factory=list)
    tags: list[str] = field(default_factory=list)
    benchmarks: list[Benchmark] = field(default_factory=list)
    key_references: list[Reference] = field(default_factory=list)
    code_url: str = ""

    def validate(self) -> None:
        """Raise ValueError if required fields are missing."""
        missing = []
        for fld in ("id", "title", "source_url"):
            if not getattr(self, fld):
                missing.append(fld)
        if self.summary is None:
            missing.append("summary")
        if missing:
            raise ValueError(f"Missing required fields: {', '.join(missing)}")

    def to_dict(self) -> dict:
        return asdict(self)

    def to_json(self, path: str | Path) -> None:
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(self.to_dict(), ensure_ascii=False, indent=2) + "\n")

    @classmethod
    def from_dict(cls, data: dict) -> Paper:
        summary = Summary(**data["summary"])
        benchmarks = [Benchmark(**b) for b in data.get("benchmarks", [])]
        refs = [Reference(**r) for r in data.get("key_references", [])]
        return cls(
            id=data["id"],
            title=data["title"],
            source_url=data["source_url"],
            summary=summary,
            source_type=data.get("source_type", "arxiv_paper"),
            ingested_at=data.get("ingested_at", ""),
            arxiv_id=data.get("arxiv_id", ""),
            authors=data.get("authors", []),
            affiliations=data.get("affiliations", []),
            date=data.get("date", ""),
            categories=data.get("categories", []),
            tags=data.get("tags", []),
            benchmarks=benchmarks,
            key_references=refs,
            code_url=data.get("code_url", ""),
        )

    @classmethod
    def from_json(cls, path: str | Path) -> Paper:
        data = json.loads(Path(path).read_text())
        return cls.from_dict(data)


def list_papers(data_dir: str | Path) -> list[Paper]:
    """Scan directory for paper JSON files, return list of Paper objects."""
    data_dir = Path(data_dir)
    if not data_dir.is_dir():
        return []
    papers = []
    for p in sorted(data_dir.glob("*.json")):
        if p.name.endswith(".mindmap.json"):
            continue
        papers.append(Paper.from_json(p))
    return papers
