"""Tests for the /diff page."""
from __future__ import annotations

import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from dashboard.app import app

PAPERS_DIR = Path(__file__).resolve().parent.parent / "data" / "papers"
PAPER_A_PATH = PAPERS_DIR / "2026-02-11_2602.10693.json"
PAPER_B_PATH = PAPERS_DIR / "2024-02-05_2402.03300.json"


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


@pytest.fixture
def paper_a_id() -> str:
    return json.loads(PAPER_A_PATH.read_text())["id"]


@pytest.fixture
def paper_b_id() -> str:
    return json.loads(PAPER_B_PATH.read_text())["id"]


class TestDiffPage:
    def test_diff_page_loads(self, client: TestClient) -> None:
        resp = client.get("/diff")
        assert resp.status_code == 200

    def test_diff_with_both_papers(
        self, client: TestClient, paper_a_id: str, paper_b_id: str
    ) -> None:
        resp = client.get(f"/diff?a={paper_a_id}&b={paper_b_id}")
        assert resp.status_code == 200
        paper_a = json.loads(PAPER_A_PATH.read_text())
        paper_b = json.loads(PAPER_B_PATH.read_text())
        assert paper_a["title"][:20] in resp.text
        assert paper_b["title"][:20] in resp.text

    def test_diff_with_one_paper(self, client: TestClient, paper_a_id: str) -> None:
        resp = client.get(f"/diff?a={paper_a_id}")
        assert resp.status_code == 200

    def test_diff_page_has_selects(self, client: TestClient) -> None:
        resp = client.get("/diff")
        assert "select-a" in resp.text
        assert "select-b" in resp.text

    def test_diff_page_navbar(self, client: TestClient) -> None:
        resp = client.get("/diff")
        assert "Research Hub" in resp.text
        assert "/compare" in resp.text
