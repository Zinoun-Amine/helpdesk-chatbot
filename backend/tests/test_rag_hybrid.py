"""
Smoke tests for the RAG hybrid retrieval upgrade (Phase 2).

Run from the backend/ folder:
    pytest -q tests/test_rag_hybrid.py

These tests intentionally do NOT require a running Chroma server — they
exercise the in-memory paths (BM25 + lexical fallback + hybrid merge).
"""
import asyncio
import os
import sys

# Make `backend/` importable when running pytest from repo root.
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from rag.vector_store import VectorStore, _split_into_chunks  # noqa: E402


SAMPLE_KB = [
    {
        "id": "kb-001",
        "title": "Impossible de se connecter au VPN",
        "category": "Ligne VPN",
        "problem_description": "L'utilisateur n'arrive pas à établir la connexion VPN depuis l'extérieur.",
        "solution_steps": [
            "Vérifiez l'accès Internet.",
            "Vérifiez le mot de passe Windows.",
            "Redémarrez le client VPN.",
        ],
        "keywords": ["vpn", "connexion", "distant", "erreur", "authentication", "bloqué"],
    },
    {
        "id": "kb-002",
        "title": "Lenteurs d'accès à l'ERP Sage",
        "category": "Sage",
        "problem_description": "Sage est très lent ou se fige pendant la saisie.",
        "solution_steps": ["Privilégiez le câble réseau.", "Vérifiez la latence Citrix."],
        "keywords": ["sage", "lent", "fige", "erp", "comptabilité"],
    },
    {
        "id": "kb-003",
        "title": "Mot de passe de messagerie expiré",
        "category": "Messagerie",
        "problem_description": "Outlook demande le mot de passe en boucle.",
        "solution_steps": ["Supprimez les credentials.", "Relancez Outlook."],
        "keywords": ["outlook", "messagerie", "mot de passe", "boucle"],
    },
]


def test_split_into_chunks_short_text_returns_single_chunk():
    chunks = _split_into_chunks("Bonjour le monde", size=10, overlap=2)
    assert chunks == ["Bonjour le monde"]


def test_split_into_chunks_long_text_slices_with_overlap():
    text = " ".join(f"w{i}" for i in range(50))  # 50 words
    chunks = _split_into_chunks(text, size=20, overlap=5)
    assert len(chunks) >= 2
    # First chunk should start with w0
    assert chunks[0].startswith("w0 w1")
    # Consecutive chunks should overlap
    assert "w15" in chunks[0] and "w15" in chunks[1]


def _new_store() -> VectorStore:
    """Build a VectorStore that bypasses Chroma (simulate OLLAMA_ONLY mode)."""
    store = VectorStore.__new__(VectorStore)
    store.local_documents = []
    store.bm25_chunks = []
    store.bm25 = None
    store.reranker = None
    store.client = None
    store.collection = None
    return store


def test_indexing_builds_bm25():
    store = _new_store()
    asyncio.run(store.add_documents(SAMPLE_KB))
    assert store.bm25 is not None, "BM25 index should be built when rank_bm25 is installed"
    assert len(store.bm25_chunks) >= len(SAMPLE_KB), "Each KB card should yield at least one chunk"


def test_lexical_fallback_returns_relevant_card():
    store = _new_store()
    asyncio.run(store.add_documents(SAMPLE_KB))
    results = asyncio.run(store.search("VPN ne marche pas", top_k=2))
    assert results, "Lexical fallback should find at least one match for 'VPN ne marche pas'"
    assert any("VPN" in r.title for r in results)


def test_category_filter_is_respected_by_lexical_fallback():
    store = _new_store()
    asyncio.run(store.add_documents(SAMPLE_KB))
    results = asyncio.run(
        store.search("Outlook mot de passe", top_k=2, category_filter="Messagerie")
    )
    assert results
    for r in results:
        assert r.category == "Messagerie"


def test_solution_steps_is_a_list():
    store = _new_store()
    asyncio.run(store.add_documents(SAMPLE_KB))
    results = asyncio.run(store.search("VPN", top_k=1))
    assert results
    assert isinstance(results[0].solution_steps, list)
    assert all(isinstance(step, str) for step in results[0].solution_steps)


# ---------------------------------------------------------------------------
# Phase 3 — cross-encoder reranker (plumbing test, no real model download)
# ---------------------------------------------------------------------------

class _StubReranker:
    """Predicts higher scores for results whose category token matches the query."""
    def predict(self, pairs):
        out = []
        for q, doc_text in pairs:
            base = 0.0
            q_lower = q.lower()
            if "vpn" in q_lower and "vpn" in doc_text.lower():
                base = 0.95
            elif "outlook" in q_lower and "messagerie" in doc_text.lower():
                base = 0.9
            elif "sage" in q_lower and "sage" in doc_text.lower():
                base = 0.85
            else:
                base = 0.1
            out.append(base)
        return out


def test_rerank_reorders_by_cross_encoder_score():
    store = _new_store()
    asyncio.run(store.add_documents(SAMPLE_KB))

    # Inject a stub reranker (no model download).
    store.reranker = _StubReranker()

    results = asyncio.run(store.search("vpn ne marche pas", top_k=3))
    assert len(results) >= 1
    # The VPN card should now be at the top (it has score 0.95 from the stub).
    assert "VPN" in results[0].title, f"Expected VPN card on top, got: {results[0].title}"
    # Score should be the cross-encoder score, not the hybrid score.
    assert 0.0 <= results[0].score <= 1.0


def test_rerank_failure_keeps_input_order():
    """If the cross-encoder raises, the original order must be preserved."""
    store = _new_store()
    asyncio.run(store.add_documents(SAMPLE_KB))

    class _BoomReranker:
        def predict(self, pairs):
            raise RuntimeError("simulated model failure")

    store.reranker = _BoomReranker()
    results = asyncio.run(store.search("vpn", top_k=3))
    assert results, "Lexical fallback should still return at least one result"
    # Order should match the lexical fallback (VPN-related card first).
    assert any("VPN" in r.title for r in results)


def test_rerank_disabled_by_default():
    """When no reranker is set, results should still come back (lexical fallback)."""
    store = _new_store()
    asyncio.run(store.add_documents(SAMPLE_KB))
    assert store.reranker is None
    results = asyncio.run(store.search("VPN", top_k=2))
    assert results
