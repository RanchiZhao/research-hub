"""Tests for rag/ module."""
import json
import tempfile
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest

from rag.engine import dummy_llm
from rag.ingest import format_paper_text
from dashboard.app import parse_content_string, parse_search_results

VESPO_PATH = Path(__file__).resolve().parent.parent / "data" / "papers" / "2026-02-11_2602.10693.json"


@pytest.fixture
def vespo_dict() -> dict:
    return json.loads(VESPO_PATH.read_text())


class TestDummyLlm:
    @pytest.fixture
    def anyio_backend(self):
        return "asyncio"

    @pytest.mark.anyio
    async def test_extracts_context_after_marker(self):
        system_prompt = "---Role---\nYou are...\n---Context---\nChunk data here"
        result = await dummy_llm("question", system_prompt=system_prompt)
        assert result == "Chunk data here"
        assert "---Role---" not in result

    @pytest.mark.anyio
    async def test_returns_full_system_prompt_without_marker(self):
        system_prompt = "Some context without marker"
        result = await dummy_llm("question", system_prompt=system_prompt)
        assert result == system_prompt

    @pytest.mark.anyio
    async def test_returns_prompt_when_no_system_prompt(self):
        result = await dummy_llm("my question")
        assert result == "my question"

    @pytest.mark.anyio
    async def test_returns_prompt_when_empty_system_prompt(self):
        result = await dummy_llm("my question", system_prompt="")
        assert result == "my question"


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
        raw = (
            "```json\n"
            '{"reference_id": "", "content": "Title: VESPO\\nAuthors: A\\nDate: 2026-01-01\\nSummary: A variational framework"}\n'
            "```"
        )
        mock_rag = AsyncMock()
        mock_rag.aquery.return_value = raw
        mock_create_rag.return_value = mock_rag

        resp = client.post("/api/search-kg", json={"question": "What is VESPO?"})
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data["results"], list)
        assert len(data["results"]) == 1
        assert data["results"][0]["title"] == "VESPO"
        assert data["results"][0]["summary"] == "A variational framework"

    @patch("rag.engine.create_rag")
    def test_search_kg_fallback_for_plain_text(self, mock_create_rag, client) -> None:
        mock_rag = AsyncMock()
        mock_rag.aquery.return_value = "VESPO uses variational framework"
        mock_create_rag.return_value = mock_rag

        resp = client.post("/api/search-kg", json={"question": "What is VESPO?"})
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data["results"], list)
        assert data["results"][0]["title"] == "Search Results"


class TestParseContentString:
    def test_full_entry(self) -> None:
        content = (
            "Title: My Paper\nAuthors: Alice, Bob\nDate: 2025-01-01\n"
            "Summary: A great paper\nProblem: Hard problem\nMethod: Novel method\n"
            "Innovation: Key insight\nResults: SOTA\nTags: NLP, LLM\nBenchmark: MMLU: 90"
        )
        result = parse_content_string(content)
        assert result is not None
        assert result["title"] == "My Paper"
        assert result["authors"] == "Alice, Bob"
        assert result["date"] == "2025-01-01"
        assert result["summary"] == "A great paper"
        assert result["tags"] == ["NLP", "LLM"]
        assert result["benchmarks"] == ["MMLU: 90"]

    def test_returns_none_without_title(self) -> None:
        assert parse_content_string("Summary: No title here") is None

    def test_returns_none_for_empty(self) -> None:
        assert parse_content_string("") is None

    def test_multiple_benchmarks(self) -> None:
        content = "Title: T\nBenchmark: A: 10\nBenchmark: B: 20"
        result = parse_content_string(content)
        assert result is not None
        assert result["benchmarks"] == ["A: 10", "B: 20"]


class TestParseSearchResults:
    def test_parses_json_block(self) -> None:
        raw = (
            "Some prefix\n"
            "```json\n"
            '{"reference_id": "", "content": "Title: DAPO\\nSummary: RL paper"}\n'
            "```\nReference list..."
        )
        results = parse_search_results(raw)
        assert len(results) == 1
        assert results[0]["title"] == "DAPO"
        assert results[0]["summary"] == "RL paper"

    def test_parses_multiple_chunks(self) -> None:
        raw = (
            "```json\n"
            '{"reference_id": "1", "content": "Title: Paper A\\nSummary: First"}\n'
            '{"reference_id": "2", "content": "Title: Paper B\\nSummary: Second"}\n'
            "```"
        )
        results = parse_search_results(raw)
        assert len(results) == 2
        assert results[0]["title"] == "Paper A"
        assert results[1]["title"] == "Paper B"

    def test_fallback_for_plain_text(self) -> None:
        results = parse_search_results("Some plain text result")
        assert len(results) == 1
        assert results[0]["title"] == "Search Results"
        assert "Some plain text" in results[0]["summary"]

    def test_empty_input(self) -> None:
        assert parse_search_results("") == []
        assert parse_search_results("   ") == []

    def test_skips_invalid_json_entries(self) -> None:
        raw = (
            "```json\n"
            '{"reference_id": "1", "content": "Title: Good\\nSummary: OK"}\n'
            "{bad json}\n"
            "```"
        )
        results = parse_search_results(raw)
        assert len(results) == 1
        assert results[0]["title"] == "Good"
