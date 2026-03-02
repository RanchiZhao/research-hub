"""Tests for Reading Path feature."""
from unittest.mock import patch

import pytest

from dashboard.app import compute_reading_path

# ---------------------------------------------------------------------------
# Fixtures / shared test data
# ---------------------------------------------------------------------------

PAPER_A = {
    "id": "2020-01-01_0000.00001",
    "title": "Foundation Paper",
    "date": "2020-01-01",
    "arxiv_id": "0000.00001",
    "summary": {
        "one_liner": "The foundational work.",
        "problem": "",
        "method": "",
        "innovation": "",
        "results": "",
    },
    "key_references": [],
}

PAPER_B = {
    "id": "2021-01-01_0000.00002",
    "title": "Derived Paper",
    "date": "2021-01-01",
    "arxiv_id": "0000.00002",
    "summary": {
        "one_liner": "Builds on the foundation.",
        "problem": "",
        "method": "",
        "innovation": "",
        "results": "",
    },
    "key_references": [
        {"title": "Foundation Paper", "arxiv_id": "0000.00001", "relationship": "builds_on"}
    ],
}

PAPER_C = {
    "id": "2022-01-01_0000.00003",
    "title": "Standalone Paper",
    "date": "2022-01-01",
    "arxiv_id": "0000.00003",
    "summary": {
        "one_liner": "Standalone work, no in-library prereqs.",
        "problem": "",
        "method": "",
        "innovation": "",
        "results": "",
    },
    "key_references": [
        {"title": "External Paper", "arxiv_id": "9999.99999", "relationship": "builds_on"}
    ],
}

PAPER_D = {
    "id": "2022-06-01_0000.00004",
    "title": "Compare-only Paper",
    "date": "2022-06-01",
    "arxiv_id": "0000.00004",
    "summary": {"one_liner": "Only compares.", "problem": "", "method": "", "innovation": "", "results": ""},
    "key_references": [
        {"title": "Foundation Paper", "arxiv_id": "0000.00001", "relationship": "compares"}
    ],
}


# ---------------------------------------------------------------------------
# Unit tests for compute_reading_path
# ---------------------------------------------------------------------------


class TestComputeReadingPath:
    def test_topological_sort_prerequisites_first(self) -> None:
        """Prerequisite papers appear before the paper that builds on them."""
        path = compute_reading_path(PAPER_B["id"], [PAPER_A, PAPER_B])
        assert len(path) == 2
        assert path[0]["id"] == PAPER_A["id"]
        assert path[1]["id"] == PAPER_B["id"]

    def test_reading_order_is_sequential(self) -> None:
        path = compute_reading_path(PAPER_B["id"], [PAPER_A, PAPER_B])
        assert path[0]["reading_order"] == 1
        assert path[1]["reading_order"] == 2

    def test_target_paper_is_flagged(self) -> None:
        path = compute_reading_path(PAPER_B["id"], [PAPER_A, PAPER_B])
        assert path[1]["is_target"] is True
        assert path[0]["is_target"] is False

    def test_no_library_refs_returns_only_self(self) -> None:
        """External-only references → path contains just the target itself."""
        path = compute_reading_path(PAPER_C["id"], [PAPER_C])
        assert len(path) == 1
        assert path[0]["id"] == PAPER_C["id"]
        assert path[0]["is_target"] is True

    def test_missing_paper_returns_empty(self) -> None:
        path = compute_reading_path("nonexistent_id", [PAPER_A])
        assert path == []

    def test_includes_one_liner(self) -> None:
        path = compute_reading_path(PAPER_B["id"], [PAPER_A, PAPER_B])
        assert path[0]["one_liner"] == "The foundational work."

    def test_relationship_to_next_populated(self) -> None:
        """relationship_to_next on PAPER_A should reflect how PAPER_B references it."""
        path = compute_reading_path(PAPER_B["id"], [PAPER_A, PAPER_B])
        assert path[0]["relationship_to_next"] == "builds_on"
        assert path[1]["relationship_to_next"] == ""

    def test_ignores_non_builds_on_relationships(self) -> None:
        """'compares' relationships should not pull in the referenced paper."""
        path = compute_reading_path(PAPER_D["id"], [PAPER_A, PAPER_D])
        assert len(path) == 1
        assert path[0]["id"] == PAPER_D["id"]

    def test_extends_relationship_is_followed(self) -> None:
        """'extends' is treated the same as 'builds_on'."""
        paper_extends = {
            "id": "2023-01-01_0000.00005",
            "title": "Extends Foundation",
            "date": "2023-01-01",
            "arxiv_id": "0000.00005",
            "summary": {"one_liner": "Extends it.", "problem": "", "method": "", "innovation": "", "results": ""},
            "key_references": [
                {"title": "Foundation Paper", "arxiv_id": "0000.00001", "relationship": "extends"}
            ],
        }
        path = compute_reading_path(paper_extends["id"], [PAPER_A, paper_extends])
        assert len(path) == 2
        assert path[0]["id"] == PAPER_A["id"]

    def test_result_fields_present(self) -> None:
        """Each item in the path has all required fields."""
        path = compute_reading_path(PAPER_A["id"], [PAPER_A])
        item = path[0]
        for field in ("id", "title", "date", "one_liner", "relationship_to_next", "reading_order", "is_target"):
            assert field in item, f"Missing field: {field}"


# ---------------------------------------------------------------------------
# API endpoint tests
# ---------------------------------------------------------------------------


class TestReadingPathApi:
    @pytest.fixture
    def client(self):
        from fastapi.testclient import TestClient
        from dashboard.app import app

        return TestClient(app)

    def test_reading_path_api_returns_structure(self, client) -> None:
        """API returns correct JSON structure."""
        with patch("dashboard.app.load_papers", return_value=[PAPER_A, PAPER_B]):
            resp = client.get(f"/api/reading-path/{PAPER_B['id']}")
        assert resp.status_code == 200
        data = resp.json()
        assert "path" in data
        assert isinstance(data["path"], list)
        assert len(data["path"]) == 2

    def test_reading_path_api_empty_no_lib_refs(self, client) -> None:
        """Paper with no in-library references returns path of length 1."""
        with patch("dashboard.app.load_papers", return_value=[PAPER_C]):
            resp = client.get(f"/api/reading-path/{PAPER_C['id']}")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["path"]) == 1
        assert data["path"][0]["id"] == PAPER_C["id"]

    def test_reading_path_api_unknown_paper(self, client) -> None:
        """Nonexistent paper_id returns empty path (not 404)."""
        with patch("dashboard.app.load_papers", return_value=[]):
            resp = client.get("/api/reading-path/nonexistent_id")
        assert resp.status_code == 200
        data = resp.json()
        assert data["path"] == []
