"""Tests for the /compare page and /api/compare-data endpoint."""
from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from dashboard.app import app

VESPO_PATH = Path(__file__).resolve().parent.parent / "data" / "papers" / "2026-02-11_2602.10693.json"


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


@pytest.fixture
def vespo_id() -> str:
    data = json.loads(VESPO_PATH.read_text())
    return data["id"]


# ---------------------------------------------------------------------------
# /compare page
# ---------------------------------------------------------------------------


class TestComparePage:
    def test_compare_page_no_ids(self, client: TestClient) -> None:
        resp = client.get("/compare")
        assert resp.status_code == 200
        assert "Compare" in resp.text

    def test_compare_page_with_id(self, client: TestClient, vespo_id: str) -> None:
        resp = client.get(f"/compare?ids={vespo_id}")
        assert resp.status_code == 200
        assert "Compare" in resp.text

    def test_compare_page_contains_all_papers(self, client: TestClient) -> None:
        resp = client.get("/compare")
        assert resp.status_code == 200
        # Paper selector should contain checkboxes
        assert "paper-check" in resp.text

    def test_compare_page_navbar_has_compare_link(self, client: TestClient) -> None:
        resp = client.get("/compare")
        assert "/compare" in resp.text


# ---------------------------------------------------------------------------
# /api/compare-data
# ---------------------------------------------------------------------------


class TestCompareData:
    def test_compare_data_empty(self, client: TestClient) -> None:
        resp = client.get("/api/compare-data")
        assert resp.status_code == 200
        data = resp.json()
        assert data["papers"] == []
        assert data["benchmarks"] == []

    def test_compare_data_empty_ids_param(self, client: TestClient) -> None:
        resp = client.get("/api/compare-data?ids=")
        assert resp.status_code == 200
        data = resp.json()
        assert data["papers"] == []
        assert data["benchmarks"] == []

    def test_compare_data_single_paper(self, client: TestClient, vespo_id: str) -> None:
        resp = client.get(f"/api/compare-data?ids={vespo_id}")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["papers"]) == 1
        assert data["papers"][0]["id"] == vespo_id
        assert "title" in data["papers"][0]
        assert "date" in data["papers"][0]

    def test_compare_data_structure(self, client: TestClient, vespo_id: str) -> None:
        resp = client.get(f"/api/compare-data?ids={vespo_id}")
        assert resp.status_code == 200
        data = resp.json()
        # Each benchmark row must have dataset, metric, scores
        for row in data["benchmarks"]:
            assert "dataset" in row
            assert "metric" in row
            assert "scores" in row

    def test_compare_data_unknown_id(self, client: TestClient) -> None:
        resp = client.get("/api/compare-data?ids=nonexistent-paper-id")
        assert resp.status_code == 200
        data = resp.json()
        assert data["papers"] == []
        assert data["benchmarks"] == []

    def test_compare_data_highlights_best(self, client: TestClient) -> None:
        """Verify comparison matrix is correctly built with multiple papers."""
        fake_papers = [
            {
                "id": "paper-A",
                "title": "Paper A",
                "date": "2025-01-01",
                "benchmarks": [
                    {"dataset": "MATH", "metric": "accuracy", "score": "80%", "notes": ""},
                    {"dataset": "GSM8K", "metric": "accuracy", "score": "90%", "notes": ""},
                ],
                "summary": {},
                "tags": ["RL"],
            },
            {
                "id": "paper-B",
                "title": "Paper B",
                "date": "2025-06-01",
                "benchmarks": [
                    {"dataset": "MATH", "metric": "accuracy", "score": "75%", "notes": ""},
                    {"dataset": "GSM8K", "metric": "accuracy", "score": "95%", "notes": "CoT"},
                ],
                "summary": {},
                "tags": ["LLM", "RL"],
            },
        ]

        with patch("dashboard.app.load_papers", return_value=fake_papers):
            resp = client.get("/api/compare-data?ids=paper-A,paper-B")

        assert resp.status_code == 200
        data = resp.json()
        assert len(data["papers"]) == 2

        # Build lookup by (dataset, metric)
        row_map = {(r["dataset"], r["metric"]): r for r in data["benchmarks"]}

        math_row = row_map[("MATH", "accuracy")]
        assert math_row["scores"]["paper-A"]["score"] == "80%"
        assert math_row["scores"]["paper-B"]["score"] == "75%"

        gsm_row = row_map[("GSM8K", "accuracy")]
        assert gsm_row["scores"]["paper-A"]["score"] == "90%"
        assert gsm_row["scores"]["paper-B"]["score"] == "95%"
        assert gsm_row["scores"]["paper-B"]["notes"] == "CoT"

    def test_compare_data_union_of_benchmarks(self, client: TestClient) -> None:
        """Papers with different benchmark sets are unified in the matrix."""
        fake_papers = [
            {
                "id": "paper-X",
                "title": "X",
                "date": "2025-01-01",
                "benchmarks": [{"dataset": "A", "metric": "acc", "score": "50%", "notes": ""}],
                "summary": {},
                "tags": [],
            },
            {
                "id": "paper-Y",
                "title": "Y",
                "date": "2025-01-01",
                "benchmarks": [{"dataset": "B", "metric": "acc", "score": "60%", "notes": ""}],
                "summary": {},
                "tags": [],
            },
        ]

        with patch("dashboard.app.load_papers", return_value=fake_papers):
            resp = client.get("/api/compare-data?ids=paper-X,paper-Y")

        data = resp.json()
        datasets = {r["dataset"] for r in data["benchmarks"]}
        assert "A" in datasets
        assert "B" in datasets
        # paper-X has no score for B, paper-Y has no score for A
        row_map = {r["dataset"]: r for r in data["benchmarks"]}
        assert "paper-X" not in row_map["B"]["scores"]
        assert "paper-Y" not in row_map["A"]["scores"]


# ---------------------------------------------------------------------------
# /api/paper-summary
# ---------------------------------------------------------------------------


class TestPaperSummary:
    def test_paper_summary_found(self, client: TestClient, vespo_id: str) -> None:
        resp = client.get(f"/api/paper-summary?id={vespo_id}")
        assert resp.status_code == 200
        data = resp.json()
        assert "method" in data
        assert "innovation" in data
        assert "tags" in data
        assert isinstance(data["tags"], list)

    def test_paper_summary_not_found(self, client: TestClient) -> None:
        resp = client.get("/api/paper-summary?id=does-not-exist")
        assert resp.status_code == 404
