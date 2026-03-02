"""Tests for scripts/ingest_url.py — URL ingestion helpers."""
import sys
from pathlib import Path
from unittest.mock import patch

import pytest

# Allow importing from scripts/ without installing as a package
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

from ingest_url import article_to_paper_json, detect_source_type, fetch_article, generate_id


class TestDetectSourceType:
    def test_zhihu(self):
        assert detect_source_type("https://zhuanlan.zhihu.com/p/123456") == "zhihu"

    def test_zhihu_question(self):
        assert detect_source_type("https://www.zhihu.com/question/12345") == "zhihu"

    def test_notion_site(self):
        assert detect_source_type("https://mysite.notion.site/Some-Page-abc123") == "notion"

    def test_notion_so(self):
        assert detect_source_type("https://www.notion.so/myworkspace/page-id") == "notion"

    def test_arxiv(self):
        assert detect_source_type("https://arxiv.org/abs/2402.03300") == "arxiv_paper"

    def test_medium(self):
        assert detect_source_type("https://medium.com/@user/some-post") == "blog"

    def test_cnblogs(self):
        assert detect_source_type("https://www.cnblogs.com/user/p/123.html") == "blog"

    def test_generic_blog(self):
        assert detect_source_type("https://myblog.example.com/post/hello-world") == "blog"


class TestGenerateId:
    def test_basic(self):
        result = generate_id("2024-01-15", "Hello World")
        assert result == "2024-01-15_hello-world"

    def test_special_chars_stripped(self):
        result = generate_id("2024-03-01", "Some: Special! Chars?")
        assert result.startswith("2024-03-01_")
        assert ":" not in result
        assert "!" not in result

    def test_slug_truncated_at_50(self):
        long_title = "A" * 100
        result = generate_id("2024-01-01", long_title)
        slug = result.split("_", 1)[1]
        assert len(slug) <= 50

    def test_no_leading_trailing_hyphens_in_slug(self):
        result = generate_id("2024-01-01", "---hello---")
        slug = result.split("_", 1)[1]
        assert not slug.startswith("-")
        assert not slug.endswith("-")


class _FakeDocument:
    """Minimal stub for trafilatura 2.0 Document object."""

    def __init__(self, data: dict):
        self._data = data

    def as_dict(self) -> dict:
        return self._data


class TestArticleToPaperJson:
    def _base_extracted(self, **overrides) -> dict:
        base = {
            "title": "My Test Article",
            "author": "Alice, Bob",
            "date": "2024-06-15",
            "text": "First paragraph.\n\nSecond paragraph.",
            "categories": "AI, ML",
        }
        base.update(overrides)
        return base

    def _base_document(self, **overrides) -> _FakeDocument:
        return _FakeDocument(self._base_extracted(**overrides))

    def test_basic_fields(self):
        extracted = self._base_extracted()
        paper = article_to_paper_json("https://zhuanlan.zhihu.com/p/1", extracted)

        assert paper["title"] == "My Test Article"
        assert paper["source_url"] == "https://zhuanlan.zhihu.com/p/1"
        assert paper["source_type"] == "zhihu"
        assert paper["authors"] == ["Alice", "Bob"]
        assert paper["date"] == "2024-06-15"

    def test_id_format(self):
        extracted = self._base_extracted()
        paper = article_to_paper_json("https://example.com/post", extracted)
        assert paper["id"].startswith("2024-06-15_")

    def test_body_text_stored(self):
        extracted = self._base_extracted(text="Full article content here.")
        paper = article_to_paper_json("https://example.com/post", extracted)
        assert paper["body_text"] == "Full article content here."

    def test_one_liner_from_first_paragraph(self):
        extracted = self._base_extracted(text="Lead sentence.\n\nRest of article.")
        paper = article_to_paper_json("https://example.com/post", extracted)
        assert paper["summary"]["one_liner"] == "Lead sentence."

    def test_tags_from_categories_string(self):
        extracted = self._base_extracted(categories="NLP, LLM, RAG")
        paper = article_to_paper_json("https://example.com/post", extracted)
        assert "NLP" in paper["tags"]
        assert "LLM" in paper["tags"]
        assert "RAG" in paper["tags"]

    def test_tags_from_categories_list(self):
        extracted = self._base_extracted(categories=["NLP", "Vision"])
        paper = article_to_paper_json("https://example.com/post", extracted)
        assert paper["tags"] == ["NLP", "Vision"]

    def test_date_normalized_to_10_chars(self):
        extracted = self._base_extracted(date="2024-06-15T12:00:00Z")
        paper = article_to_paper_json("https://example.com/post", extracted)
        assert paper["date"] == "2024-06-15"

    def test_missing_date_defaults_to_today(self):
        extracted = self._base_extracted(date=None)
        paper = article_to_paper_json("https://example.com/post", extracted)
        import re
        assert re.match(r"\d{4}-\d{2}-\d{2}", paper["date"])

    def test_missing_author_gives_empty_list(self):
        extracted = self._base_extracted(author=None)
        paper = article_to_paper_json("https://example.com/post", extracted)
        assert paper["authors"] == []

    def test_schema_keys_present(self):
        extracted = self._base_extracted()
        paper = article_to_paper_json("https://example.com/post", extracted)
        for key in ("id", "ingested_at", "source_type", "source_url", "title",
                    "authors", "date", "summary", "tags", "benchmarks",
                    "key_references", "body_text"):
            assert key in paper, f"Missing key: {key}"

    def test_summary_structure(self):
        extracted = self._base_extracted()
        paper = article_to_paper_json("https://example.com/post", extracted)
        summary = paper["summary"]
        for key in ("one_liner", "problem", "method", "innovation", "results"):
            assert key in summary


class TestFetchArticleDocumentConversion:
    """Verify fetch_article converts trafilatura 2.0 Document objects to dict."""

    def test_returns_dict_when_bare_extraction_returns_document(self):
        doc = _FakeDocument({"title": "Test", "text": "Body", "author": None, "date": None})

        with patch("ingest_url.fetch_url", return_value="<html>fake</html>"), \
             patch("ingest_url.bare_extraction", return_value=doc):
            result = fetch_article("https://example.com/article")

        assert isinstance(result, dict)
        assert result["title"] == "Test"

    def test_returns_dict_when_bare_extraction_already_returns_dict(self):
        data = {"title": "Plain", "text": "Content", "author": None, "date": None}

        with patch("ingest_url.fetch_url", return_value="<html>fake</html>"), \
             patch("ingest_url.bare_extraction", return_value=data):
            result = fetch_article("https://example.com/article")

        assert isinstance(result, dict)
        assert result["title"] == "Plain"

    def test_raises_on_fetch_failure(self):
        with patch("ingest_url.fetch_url", return_value=None):
            with pytest.raises(RuntimeError, match="Failed to fetch"):
                fetch_article("https://example.com/article")

    def test_raises_on_extraction_failure(self):
        with patch("ingest_url.fetch_url", return_value="<html>fake</html>"), \
             patch("ingest_url.bare_extraction", return_value=None):
            with pytest.raises(RuntimeError, match="Failed to extract"):
                fetch_article("https://example.com/article")
