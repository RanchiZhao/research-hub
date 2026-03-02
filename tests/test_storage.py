"""Tests for utils/storage.py."""
import json
import tempfile
from pathlib import Path

import pytest

from models.paper import Paper, Summary
from utils.storage import list_all_papers, load_paper, save_paper, search_papers

VESPO_PATH = Path(__file__).resolve().parent.parent / "data" / "papers" / "2026-02-11_2602.10693.json"


@pytest.fixture
def vespo_dict() -> dict:
    return json.loads(VESPO_PATH.read_text())


@pytest.fixture
def tmp_data_dir():
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


def test_save_and_load(vespo_dict: dict, tmp_data_dir: Path):
    paper = save_paper(vespo_dict, tmp_data_dir)
    loaded = load_paper(paper.id, tmp_data_dir)
    assert loaded.id == paper.id
    assert loaded.title == paper.title


def test_save_creates_mindmap(vespo_dict: dict, tmp_data_dir: Path):
    paper = save_paper(vespo_dict, tmp_data_dir)
    mindmap_path = tmp_data_dir / f"{paper.id}.mindmap.md"
    assert mindmap_path.exists()
    content = mindmap_path.read_text()
    assert paper.title in content
    assert "## Problem" in content


def test_save_atomic_write(vespo_dict: dict, tmp_data_dir: Path):
    """Verify no .tmp files are left after save."""
    save_paper(vespo_dict, tmp_data_dir)
    tmp_files = list(tmp_data_dir.glob("*.tmp"))
    assert tmp_files == []


def test_load_nonexistent(tmp_data_dir: Path):
    with pytest.raises(FileNotFoundError):
        load_paper("nonexistent", tmp_data_dir)


def test_list_all_papers_sorted(vespo_dict: dict, tmp_data_dir: Path):
    # Save two papers with different dates
    dict1 = {**vespo_dict, "id": "2026-01-01_paper1", "date": "2026-01-01"}
    dict2 = {**vespo_dict, "id": "2026-03-01_paper2", "date": "2026-03-01"}
    save_paper(dict1, tmp_data_dir)
    save_paper(dict2, tmp_data_dir)
    papers = list_all_papers(tmp_data_dir)
    assert len(papers) == 2
    assert papers[0].date >= papers[1].date  # descending


def test_search_by_title(vespo_dict: dict, tmp_data_dir: Path):
    save_paper(vespo_dict, tmp_data_dir)
    results = search_papers("VESPO", tmp_data_dir)
    assert len(results) == 1
    assert results[0].id == vespo_dict["id"]


def test_search_by_tag(vespo_dict: dict, tmp_data_dir: Path):
    save_paper(vespo_dict, tmp_data_dir)
    results = search_papers("reinforcement learning", tmp_data_dir)
    assert len(results) == 1


def test_search_case_insensitive(vespo_dict: dict, tmp_data_dir: Path):
    save_paper(vespo_dict, tmp_data_dir)
    results = search_papers("vespo", tmp_data_dir)
    assert len(results) == 1


def test_search_no_results(vespo_dict: dict, tmp_data_dir: Path):
    save_paper(vespo_dict, tmp_data_dir)
    results = search_papers("quantum computing xyz", tmp_data_dir)
    assert len(results) == 0


def test_save_validates(tmp_data_dir: Path):
    bad_dict = {"id": "", "title": "T", "source_url": "http://x",
                "summary": {"problem": "p", "method": "m", "innovation": "i", "results": "r", "one_liner": "o"}}
    with pytest.raises(ValueError, match="id"):
        save_paper(bad_dict, tmp_data_dir)
