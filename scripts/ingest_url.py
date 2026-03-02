"""Ingest a web article (Zhihu, blog, etc.) into Research Hub."""
import argparse
import json
import re
from datetime import datetime, timezone
from pathlib import Path

from trafilatura import fetch_url, bare_extraction

DATA_DIR = Path(__file__).resolve().parent.parent / "data" / "papers"


def fetch_article(url: str) -> dict:
    """Fetch and extract article content from URL using trafilatura."""
    downloaded = fetch_url(url)
    if not downloaded:
        raise RuntimeError(f"Failed to fetch {url}")

    result = bare_extraction(downloaded, url=url, with_metadata=True)
    if not result:
        raise RuntimeError(f"Failed to extract content from {url}")

    return result


def detect_source_type(url: str) -> str:
    """Detect source type from URL."""
    if "zhihu.com" in url:
        return "zhihu"
    elif "notion.site" in url or "notion.so" in url:
        return "notion"
    elif "arxiv.org" in url:
        return "arxiv_paper"
    else:
        return "blog"


def generate_id(date_str: str, title: str) -> str:
    """Generate a paper-like ID from date and title slug."""
    slug = re.sub(r"[^a-z0-9]+", "-", title.lower().strip())[:50].strip("-")
    return f"{date_str}_{slug}"


def article_to_paper_json(url: str, extracted: dict) -> dict:
    """Convert extracted article data to paper JSON format."""
    now = datetime.now(timezone.utc).isoformat()
    title = extracted.get("title") or "Untitled"
    author = extracted.get("author") or ""
    date_str = extracted.get("date") or ""

    # Normalize date to YYYY-MM-DD
    if date_str and len(date_str) > 10:
        date_str = date_str[:10]
    if not date_str:
        date_str = datetime.now().strftime("%Y-%m-%d")

    body = extracted.get("text") or ""
    source_type = detect_source_type(url)
    authors = [a.strip() for a in author.split(",")] if author else []
    paper_id = generate_id(date_str, title)

    paragraphs = [p.strip() for p in body.split("\n") if p.strip()]
    one_liner = paragraphs[0][:200] if paragraphs else title

    tags: list[str] = []
    categories = extracted.get("categories") or extracted.get("tags") or ""
    if categories:
        if isinstance(categories, str):
            tags = [t.strip() for t in categories.split(",") if t.strip()]
        elif isinstance(categories, list):
            tags = list(categories)

    return {
        "id": paper_id,
        "ingested_at": now,
        "source_type": source_type,
        "source_url": url,
        "title": title,
        "authors": authors,
        "date": date_str,
        "summary": {
            "one_liner": one_liner,
            "problem": "",
            "method": "",
            "innovation": "",
            "results": "",
        },
        "tags": tags,
        "benchmarks": [],
        "key_references": [],
        "body_text": body,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Ingest a web article into Research Hub")
    parser.add_argument("url", help="URL of the article to ingest")
    parser.add_argument("--dry-run", action="store_true", help="Print JSON without saving")
    args = parser.parse_args()

    print(f"Fetching {args.url}...")
    extracted = fetch_article(args.url)
    paper = article_to_paper_json(args.url, extracted)

    if args.dry_run:
        print(json.dumps(paper, ensure_ascii=False, indent=2))
        return

    DATA_DIR.mkdir(parents=True, exist_ok=True)
    out_path = DATA_DIR / f"{paper['id']}.json"
    out_path.write_text(json.dumps(paper, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Saved to {out_path}")
    print(f"  Title: {paper['title']}")
    print(f"  Type:  {paper['source_type']}")
    print(f"  Date:  {paper['date']}")


if __name__ == "__main__":
    main()
