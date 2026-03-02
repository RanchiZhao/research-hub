"""Tests for /timeline page and build_timeline_data."""
from __future__ import annotations

from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from dashboard.app import app, build_timeline_data


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


FAKE_PAPERS = [
    {
        "id": "2025-03-01_1111.00001",
        "title": "Paper B",
        "date": "2025-03-01",
        "arxiv_id": "1111.00001",
        "summary": {"one_liner": "Second paper."},
        "key_references": [
            {"title": "Paper A", "arxiv_id": "1111.00000", "relationship": "extends"}
        ],
    },
    {
        "id": "2024-01-01_1111.00000",
        "title": "Paper A",
        "date": "2024-01-01",
        "arxiv_id": "1111.00000",
        "summary": {"one_liner": "First paper."},
        "key_references": [],
    },
]


class TestTimelinePage:
    def test_timeline_page_returns_200(self, client: TestClient) -> None:
        resp = client.get("/timeline")
        assert resp.status_code == 200

    def test_timeline_page_contains_heading(self, client: TestClient) -> None:
        resp = client.get("/timeline")
        assert "Timeline" in resp.text

    def test_timeline_page_navbar_has_timeline_link(self, client: TestClient) -> None:
        resp = client.get("/timeline")
        assert "/timeline" in resp.text

    def test_timeline_page_shows_papers(self, client: TestClient) -> None:
        with patch("dashboard.app.load_papers", return_value=FAKE_PAPERS):
            resp = client.get("/timeline")
        assert resp.status_code == 200
        assert "Paper A" in resp.text
        assert "Paper B" in resp.text

    def test_timeline_page_empty(self, client: TestClient) -> None:
        with patch("dashboard.app.load_papers", return_value=[]):
            resp = client.get("/timeline")
        assert resp.status_code == 200
        assert "No papers" in resp.text


class TestBuildTimelineData:
    def test_sorted_oldest_first(self) -> None:
        result = build_timeline_data(FAKE_PAPERS)
        assert result[0]["id"] == "2024-01-01_1111.00000"
        assert result[1]["id"] == "2025-03-01_1111.00001"

    def test_connection_resolved_for_in_library_ref(self) -> None:
        result = build_timeline_data(FAKE_PAPERS)
        paper_b = next(r for r in result if r["id"] == "2025-03-01_1111.00001")
        assert len(paper_b["connections"]) == 1
        conn = paper_b["connections"][0]
        assert conn["arxiv_id"] == "1111.00000"
        assert conn["relationship"] == "extends"
        assert conn["id"] == "2024-01-01_1111.00000"

    def test_no_connections_for_unknown_ref(self) -> None:
        papers = [
            {
                "id": "2025-01-01_9999.00001",
                "title": "Lonely Paper",
                "date": "2025-01-01",
                "arxiv_id": "9999.00001",
                "summary": {},
                "key_references": [
                    {"title": "Outside", "arxiv_id": "0000.00000", "relationship": "extends"}
                ],
            }
        ]
        result = build_timeline_data(papers)
        assert result[0]["connections"] == []

    def test_one_liner_extracted(self) -> None:
        result = build_timeline_data(FAKE_PAPERS)
        paper_a = next(r for r in result if r["id"] == "2024-01-01_1111.00000")
        assert paper_a["one_liner"] == "First paper."

    def test_required_fields_present(self) -> None:
        result = build_timeline_data(FAKE_PAPERS)
        for item in result:
            assert "id" in item
            assert "title" in item
            assert "date" in item
            assert "one_liner" in item
            assert "connections" in item
