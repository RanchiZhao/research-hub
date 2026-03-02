"""Tests for models/paper.py."""
import json
import tempfile
from pathlib import Path

import pytest

from models.paper import Benchmark, Paper, Reference, Summary, list_papers

VESPO_PATH = Path(__file__).resolve().parent.parent / "data" / "papers" / "2026-02-11_2602.10693.json"


@pytest.fixture
def vespo_dict() -> dict:
    return json.loads(VESPO_PATH.read_text())


@pytest.fixture
def vespo_paper(vespo_dict: dict) -> Paper:
    return Paper.from_dict(vespo_dict)


def test_from_json_loads_vespo():
    paper = Paper.from_json(VESPO_PATH)
    assert paper.id == "2026-02-11_2602.10693"
    assert paper.title.startswith("VESPO")
    assert paper.source_url == "https://arxiv.org/abs/2602.10693"
    assert isinstance(paper.summary, Summary)
    assert paper.summary.one_liner


def test_roundtrip_dict(vespo_dict: dict, vespo_paper: Paper):
    """from_dict -> to_dict should preserve data."""
    exported = vespo_paper.to_dict()
    assert exported["id"] == vespo_dict["id"]
    assert exported["title"] == vespo_dict["title"]
    assert exported["summary"]["problem"] == vespo_dict["summary"]["problem"]
    assert len(exported["benchmarks"]) == len(vespo_dict["benchmarks"])
    assert len(exported["key_references"]) == len(vespo_dict["key_references"])


def test_roundtrip_json(vespo_paper: Paper):
    """to_json -> from_json should produce equivalent paper."""
    with tempfile.TemporaryDirectory() as tmpdir:
        path = Path(tmpdir) / "test.json"
        vespo_paper.to_json(path)
        loaded = Paper.from_json(path)
        assert loaded.id == vespo_paper.id
        assert loaded.title == vespo_paper.title
        assert loaded.summary.one_liner == vespo_paper.summary.one_liner
        assert len(loaded.benchmarks) == len(vespo_paper.benchmarks)


def test_validate_missing_id():
    paper = Paper(id="", title="T", source_url="http://x", summary=Summary("p", "m", "i", "r", "o"))
    with pytest.raises(ValueError, match="id"):
        paper.validate()


def test_validate_missing_title():
    paper = Paper(id="1", title="", source_url="http://x", summary=Summary("p", "m", "i", "r", "o"))
    with pytest.raises(ValueError, match="title"):
        paper.validate()


def test_validate_ok(vespo_paper: Paper):
    vespo_paper.validate()  # should not raise


def test_list_papers():
    data_dir = VESPO_PATH.parent
    papers = list_papers(data_dir)
    assert len(papers) >= 1
    assert any(p.id == "2026-02-11_2602.10693" for p in papers)


def test_list_papers_empty_dir():
    with tempfile.TemporaryDirectory() as tmpdir:
        assert list_papers(tmpdir) == []


def test_list_papers_nonexistent_dir():
    assert list_papers("/tmp/nonexistent_dir_12345") == []


def test_benchmarks_parsed(vespo_paper: Paper):
    assert len(vespo_paper.benchmarks) == 4
    assert isinstance(vespo_paper.benchmarks[0], Benchmark)
    assert vespo_paper.benchmarks[0].dataset == "AIME 2024/2025"


def test_references_parsed(vespo_paper: Paper):
    assert len(vespo_paper.key_references) == 4
    assert isinstance(vespo_paper.key_references[0], Reference)
    assert vespo_paper.key_references[0].relationship == "compares"
