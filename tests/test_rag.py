"""Tests for rag/ module."""
import json
import tempfile
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest

from rag.ingest import format_paper_text

VESPO_PATH = Path(__file__).resolve().parent.parent / "data" / "papers" / "2026-02-11_2602.10693.json"


@pytest.fixture
def vespo_dict() -> dict:
    return json.loads(VESPO_PATH.read_text())


class TestFormatPaperText:
    def test_includes_title(self, vespo_dict: dict) -> None:
        text = format_paper_text(vespo_dict)
        assert "Title: VESPO" in text

    def test_includes_authors(self, vespo_dict: dict) -> None:
        text = format_paper_text(vespo_dict)
        assert "Authors:" in text

    def test_includes_date(self, vespo_dict: dict) -> None:
        text = format_paper_text(vespo_dict)
        assert "Date: 2026-02-11" in text

    def test_includes_summary(self, vespo_dict: dict) -> None:
        text = format_paper_text(vespo_dict)
        assert "Summary:" in text
        assert "Problem:" in text
        assert "Method:" in text

    def test_includes_tags(self, vespo_dict: dict) -> None:
        text = format_paper_text(vespo_dict)
        assert "Tags:" in text

    def test_includes_references(self, vespo_dict: dict) -> None:
        text = format_paper_text(vespo_dict)
        assert "Reference:" in text

    def test_includes_benchmarks(self, vespo_dict: dict) -> None:
        text = format_paper_text(vespo_dict)
        assert "Benchmark:" in text

    def test_minimal_paper(self) -> None:
        paper = {"title": "Test Paper"}
        text = format_paper_text(paper)
        assert text == "Title: Test Paper"

    def test_empty_paper(self) -> None:
        text = format_paper_text({})
        assert text == "Title: "


class TestSearchKGRoute:
    """Test the /api/search-kg endpoint (mocking LightRAG)."""

    @pytest.fixture
    def client(self):
        from fastapi.testclient import TestClient
        from dashboard.app import app
        return TestClient(app)

    def test_search_kg_page(self, client) -> None:
        resp = client.get("/search-kg")
        assert resp.status_code == 200
        assert "Knowledge Search" in resp.text

    def test_search_kg_empty_question(self, client) -> None:
        resp = client.post("/api/search-kg", json={"question": ""})
        assert resp.status_code == 200
        assert resp.json() == {"results": []}

    def test_search_kg_whitespace_question(self, client) -> None:
        resp = client.post("/api/search-kg", json={"question": "   "})
        assert resp.status_code == 200
        assert resp.json() == {"results": []}

    @patch("rag.engine.create_rag")
    def test_search_kg_with_question(self, mock_create_rag, client) -> None:
        mock_rag = AsyncMock()
        mock_rag.aquery.return_value = "VESPO uses variational framework"
        mock_create_rag.return_value = mock_rag

        resp = client.post("/api/search-kg", json={"question": "What is VESPO?"})
        assert resp.status_code == 200
        assert resp.json() == {"results": "VESPO uses variational framework"}
