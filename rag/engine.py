"""LightRAG knowledge graph engine for Research Hub."""
from __future__ import annotations

from pathlib import Path

import numpy as np
from lightrag import LightRAG, QueryParam
from lightrag.base import EmbeddingFunc
from sentence_transformers import SentenceTransformer

# Paths
RAG_DIR = Path(__file__).resolve().parent.parent / "data" / "rag_storage"
PAPERS_DIR = Path(__file__).resolve().parent.parent / "data" / "papers"

# Embedding model — loaded lazily
_embed_model: SentenceTransformer | None = None


def _get_embed_model() -> SentenceTransformer:
    global _embed_model
    if _embed_model is None:
        _embed_model = SentenceTransformer("all-MiniLM-L6-v2", device="cuda")
    return _embed_model


async def local_embed(texts: list[str]) -> np.ndarray:
    """Embed texts using local sentence-transformers model on GPU."""
    model = _get_embed_model()
    return model.encode(texts, convert_to_numpy=True)


async def dummy_llm(prompt: str, **kwargs: object) -> str:
    """Return retrieved context directly — no real LLM synthesis.

    LightRAG passes retrieved chunks via ``system_prompt``.  We surface
    the context portion so naive-mode queries return meaningful results
    without requiring an external LLM.
    """
    system_prompt = kwargs.get("system_prompt", "")
    if system_prompt:
        # LightRAG uses "---Context---" (3 dashes, singular) as marker
        marker = "---Context---"
        if marker in system_prompt:
            return system_prompt.split(marker, 1)[1].strip()
        return system_prompt
    return prompt


def create_rag() -> LightRAG:
    """Create and return a LightRAG instance with local file storage."""
    RAG_DIR.mkdir(parents=True, exist_ok=True)
    return LightRAG(
        working_dir=str(RAG_DIR),
        embedding_func=EmbeddingFunc(
            embedding_dim=384,
            func=local_embed,
            max_token_size=512,
        ),
        llm_model_func=dummy_llm,
    )


async def query_papers(question: str) -> str:
    """Query the knowledge base with natural language."""
    rag = create_rag()
    await rag.initialize_storages()
    try:
        result = await rag.aquery(
            question,
            param=QueryParam(mode="naive"),
        )
        return result
    finally:
        await rag.finalize_storages()
