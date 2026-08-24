import logging
import re
import time
import unicodedata
from collections import defaultdict
from typing import Dict, List, Optional, Tuple
from models.schemas import KBSearchResult
from config import settings as app_settings

try:
    import chromadb
    from chromadb.config import Settings
    from chromadb.utils import embedding_functions
except Exception as exc:  # pragma: no cover - runtime fallback for local env mismatches
    chromadb = None
    Settings = None
    embedding_functions = None
    _chromadb_import_error = exc

try:
    from rank_bm25 import BM25Okapi
except Exception:  # pragma: no cover - optional dep
    BM25Okapi = None

try:
    from sentence_transformers import CrossEncoder
except Exception:  # pragma: no cover - already in requirements via sentence-transformers
    CrossEncoder = None

logger = logging.getLogger(__name__)


def _split_into_chunks(text: str, size: int, overlap: int) -> List[str]:
    """Word-boundary sliding window. Returns a list of chunk strings.

    Short texts are returned as a single chunk. Otherwise the text is split
    on whitespace into a list of words, then sliced with the given overlap.
    """
    text = re.sub(r"\s+", " ", text or "").strip()
    if not text:
        return []
    words = text.split(" ")
    if len(words) <= size:
        return [text]
    chunks: List[str] = []
    step = max(1, size - overlap)
    for i in range(0, len(words), step):
        piece = words[i:i + size]
        if not piece:
            break
        chunks.append(" ".join(piece))
        if i + size >= len(words):
            break
    return chunks


class VectorStore:
    """
    Gestionnaire de la base de connaissances — indexation et recherche hybrides.

    Stocke chaque fiche KB sous forme de *chunks* (morceaux) et combine deux
    signaux au moment de la recherche :
      - **Sémantique** : similarité cosinus sur embeddings (ChromaDB).
      - **Lexical**    : BM25 sur les mêmes chunks (rank_bm25, en mémoire).

    Les deux listes sont fusionnées via une moyenne pondérée
    (KB_SEMANTIC_WEIGHT / KB_BM25_WEIGHT) et filtrées par KB_HYBRID_MIN_SCORE.

    Le fallback `_search_local` (overlap de tokens) reste disponible si Chroma
    est indisponible et que BM25 ne peut pas être construit.
    """

    def __init__(self):
        self.local_documents: List[dict] = []
        self.bm25_chunks: List[dict] = []   # [{parent_id, chunk_index, text, doc}, ...]
        self.bm25 = None                   # BM25Okapi index over bm25_chunks
        self.reranker = None               # CrossEncoder (lazy-loaded, opt-in)

        if app_settings.OLLAMA_ONLY:
            logger.info("Mode Ollama seul activé : ChromaDB désactivé, usage du KB local uniquement.")
            self.client = None
            self.collection = None
        elif chromadb is None:
            logger.warning(f"ChromaDB indisponible, base KB désactivée: {_chromadb_import_error}")
            self.client = None
            self.collection = None
        else:
            self.client = None
            self.collection = None
            for attempt in range(1, 4):
                try:
                    self.client = chromadb.HttpClient(
                        host=app_settings.CHROMA_HOST,
                        port=app_settings.CHROMA_PORT,
                        settings=Settings(allow_reset=True),
                    )
                    # Embedding function:
                    # - default: French-capable multilingual model (recommended)
                    # - opt-out (KB_USE_DEFAULT_EMBEDDING=true): Chroma built-in
                    ef = None
                    if not app_settings.KB_USE_DEFAULT_EMBEDDING and embedding_functions is not None:
                        try:
                            ef = embedding_functions.SentenceTransformerEmbeddingFunction(
                                model_name=app_settings.EMBEDDING_MODEL
                            )
                            logger.info(
                                "Embedding model chargé: %s (multilingue, FR-friendly)",
                                app_settings.EMBEDDING_MODEL,
                            )
                        except Exception as ef_exc:
                            logger.warning(
                                "Impossible de charger %s, fallback embedding par défaut: %s",
                                app_settings.EMBEDDING_MODEL,
                                ef_exc,
                            )
                            ef = None
                    self.collection = self.client.get_or_create_collection(
                        name="helpdesk_kb",
                        embedding_function=ef,
                        metadata={"hnsw:space": "cosine"},
                    )
                    logger.info("ChromaDB initialisé avec succès.")
                    break
                except Exception as e:
                    if attempt >= 3:
                        logger.error(
                            "Erreur lors de l'initialisation de ChromaDB après plusieurs tentatives: %s",
                            e,
                        )
                        self.collection = None
                    else:
                        logger.warning(
                            "Tentative %d de connexion à ChromaDB échouée, nouvelle tentative dans 1s: %s",
                            attempt,
                            e,
                        )
                        time.sleep(1)

        # ----- Optional cross-encoder reranker (opt-in via env) -----
        # Lazy-loaded: only downloaded/built when KB_RERANKER_ENABLED=true.
        # Failure here is non-fatal — we simply fall back to no rerank.
        self.reranker = None
        if app_settings.KB_RERANKER_ENABLED:
            if CrossEncoder is None:
                logger.warning(
                    "KB_RERANKER_ENABLED=true mais sentence_transformers.CrossEncoder "
                    "n'est pas disponible — reranker désactivé."
                )
            else:
                try:
                    logger.info(
                        "Chargement du cross-encoder reranker: %s",
                        app_settings.KB_RERANKER_MODEL,
                    )
                    self.reranker = CrossEncoder(
                        app_settings.KB_RERANKER_MODEL,
                        max_length=512,
                    )
                except Exception as e:
                    logger.warning(
                        "Impossible de charger le reranker %s: %s — rerank désactivé.",
                        app_settings.KB_RERANKER_MODEL,
                        e,
                    )
                    self.reranker = None

    # ------------------------------------------------------------------
    # Indexing
    # ------------------------------------------------------------------

    async def add_documents(self, documents: List[dict]):
        """
        Découpe chaque fiche KB en chunks et les indexe :
          - dans ChromaDB (sémantique), si disponible
          - dans un index BM25 en mémoire (lexical)
        Les chunks déjà présents (même parent_id + chunk_index) sont ignorés.
        """
        self.local_documents = list(documents)

        # 1. Build chunks (toujours, même sans Chroma — sert au BM25 et au fallback)
        self.bm25_chunks = []
        for doc in documents:
            base_text = (
                f"{doc.get('title', '')}. "
                f"{doc.get('problem_description', '')}. "
                f"Mots clés: {', '.join(doc.get('keywords', []))}"
            ).strip()
            chunks = _split_into_chunks(
                base_text,
                size=app_settings.KB_CHUNK_SIZE,
                overlap=app_settings.KB_CHUNK_OVERLAP,
            )
            for idx, chunk in enumerate(chunks):
                self.bm25_chunks.append({
                    "parent_id": doc["id"],
                    "chunk_index": idx,
                    "text": chunk,
                    "doc": doc,
                })

        # 2. Build BM25 index over chunks
        if BM25Okapi is not None and self.bm25_chunks:
            try:
                tokenized = [self._token_list(c["text"]) for c in self.bm25_chunks]
                self.bm25 = BM25Okapi(tokenized)
                logger.info(
                    "Index BM25 construit sur %d chunks (size=%d, overlap=%d).",
                    len(self.bm25_chunks),
                    app_settings.KB_CHUNK_SIZE,
                    app_settings.KB_CHUNK_OVERLAP,
                )
            except Exception as e:
                logger.warning("Échec construction BM25, lexical search désactivé: %s", e)
                self.bm25 = None
        else:
            if BM25Okapi is None:
                logger.warning("rank_bm25 non disponible — recherche lexicale désactivée.")
            self.bm25 = None

        # 3. Push chunks to Chroma (dédup par parent_id + chunk_index)
        if not self.collection:
            if not app_settings.OLLAMA_ONLY:
                logger.warning("ChromaDB non initialisé, chunks non persistés.")
            return

        new_chunks = self._filter_existing_chunks(self.bm25_chunks)
        if not new_chunks:
            logger.info("Tous les chunks sont déjà indexés dans ChromaDB.")
            return

        ids = [self._chunk_id(c["parent_id"], c["chunk_index"]) for c in new_chunks]
        texts = [c["text"] for c in new_chunks]
        metadatas = [
            {
                "title": c["doc"].get("title", ""),
                "category": c["doc"].get("category", ""),
                "problem_description": c["doc"].get("problem_description", ""),
                # Chroma metadata n'accepte que string/int/float → sérialisation
                "solution_steps": "|".join(c["doc"].get("solution_steps", [])),
                "parent_id": c["parent_id"],
                "chunk_index": c["chunk_index"],
            }
            for c in new_chunks
        ]

        try:
            self.collection.add(documents=texts, metadatas=metadatas, ids=ids)
            logger.info("Ajout de %d chunks à ChromaDB.", len(ids))
        except Exception as e:
            logger.error("Erreur lors de l'ajout des chunks à ChromaDB: %s", e)

    def _filter_existing_chunks(self, chunks: List[dict]) -> List[dict]:
        if not self.collection:
            return []
        ids = [self._chunk_id(c["parent_id"], c["chunk_index"]) for c in chunks]
        try:
            existing = self.collection.get(ids=ids)
            existing_ids = set(existing.get("ids", []))
        except Exception:
            existing_ids = set()
        return [
            c for c in chunks
            if self._chunk_id(c["parent_id"], c["chunk_index"]) not in existing_ids
        ]

    @staticmethod
    def _chunk_id(parent_id: str, index: int) -> str:
        return f"{parent_id}__c{index}"

    # ------------------------------------------------------------------
    # Tokenizers
    # ------------------------------------------------------------------

    @staticmethod
    def _tokens(value: str) -> set[str]:
        normalized = unicodedata.normalize("NFKD", value or "")
        normalized = "".join(char for char in normalized if not unicodedata.combining(char))
        return {token for token in re.findall(r"[a-z0-9]+", normalized.lower()) if len(token) > 2}

    @staticmethod
    def _token_list(value: str) -> List[str]:
        normalized = unicodedata.normalize("NFKD", value or "")
        normalized = "".join(char for char in normalized if not unicodedata.combining(char))
        return [t for t in re.findall(r"[a-z0-9]+", normalized.lower()) if len(t) > 2]

    # ------------------------------------------------------------------
    # Search — public entry point
    # ------------------------------------------------------------------

    async def search(
        self,
        query: str,
        top_k: int = 3,
        category_filter: Optional[str] = None,
    ) -> List[KBSearchResult]:
        """
        Recherche hybride : combine similarité sémantique (Chroma) et BM25,
        puis réordonne éventuellement avec un cross-encoder.

        Si ni Chroma ni BM25 ne sont disponibles, bascule sur la recherche
        lexicale simple `_search_local`.
        """
        # On over-fetch pour laisser de la marge au reranker :
        # il trie les N meilleurs puis on garde top_k.
        fetch_n = max(top_k, app_settings.KB_RERANKER_TOP_N if self.reranker else top_k)

        semantic = await self._semantic_search(query, fetch_n, category_filter)
        bm25 = self._bm25_search(query, fetch_n, category_filter)

        if not semantic and not bm25:
            return await self._search_local(query, top_k, category_filter)

        merged = self._hybrid_merge(semantic, bm25, fetch_n)
        if not merged:
            return await self._search_local(query, top_k, category_filter)

        # Phase 3 : reranking cross-encoder (opt-in).
        if self.reranker is not None:
            merged = self._rerank(query, merged)
            return merged[:top_k]
        return merged[:top_k]

    # ------------------------------------------------------------------
    # Cross-encoder reranker (Phase 3)
    # ------------------------------------------------------------------

    def _rerank(self, query: str, candidates: List[KBSearchResult]) -> List[KBSearchResult]:
        """Réordonne `candidates` selon un score cross-encoder (query, doc).

        Le score est réinjecté dans `KBSearchResult.score` (arrondi à 4 décimales).
        En cas d'échec du modèle, l'ordre d'entrée est conservé.
        """
        if not candidates:
            return candidates
        # Tronque les textes pour rester sous la limite max_length du cross-encoder.
        pairs = [
            (
                query,
                f"{(r.title or '')}. {(r.problem_description or '')}"[:1000],
            )
            for r in candidates
        ]
        try:
            scores = self.reranker.predict(pairs)
            # `predict` accepte une liste et renvoie un numpy array → on force list
            scores = [float(s) for s in scores]
            # Tri descendant ; on stabilise par score d'origine pour les égalités
            indexed = list(enumerate(candidates))
            indexed.sort(
                key=lambda ic: (scores[ic[0]], ic[1].score),
                reverse=True,
            )
            reranked = [c for _, c in indexed]
            for i, r in enumerate(reranked):
                r.score = round(scores[i], 4)
            return reranked
        except Exception as e:
            logger.warning("Rerank a échoué, ordre d'entrée conservé: %s", e)
            return candidates

    # ------------------------------------------------------------------
    # Semantic search (Chroma)
    # ------------------------------------------------------------------

    async def _semantic_search(
        self,
        query: str,
        top_k: int,
        category_filter: Optional[str],
    ) -> List[KBSearchResult]:
        if not self.collection:
            return []
        where = (
            {"category": category_filter}
            if category_filter and category_filter != "Inconnue"
            else None
        )
        try:
            res = self.collection.query(
                query_texts=[query],
                n_results=top_k,
                where=where,
            )
            out: List[KBSearchResult] = []
            if res and res.get("ids") and len(res["ids"]) > 0:
                for i, doc_id in enumerate(res["ids"][0]):
                    md = res["metadatas"][0][i]
                    dist = res["distances"][0][i] if res.get("distances") else 0.0
                    score = 1.0 / (1.0 + dist)
                    if score < 0.4:
                        continue
                    out.append(KBSearchResult(
                        id=md.get("parent_id", doc_id),
                        title=md.get("title", ""),
                        category=md.get("category", ""),
                        problem_description=md.get("problem_description", ""),
                        solution_steps=md.get("solution_steps", "").split("|") if md.get("solution_steps") else [],
                        score=score,
                    ))
            return out
        except Exception as e:
            logger.error("Erreur lors de la recherche sémantique: %s", e)
            return []

    # ------------------------------------------------------------------
    # BM25 search
    # ------------------------------------------------------------------

    def _bm25_search(
        self,
        query: str,
        top_k: int,
        category_filter: Optional[str],
    ) -> List[KBSearchResult]:
        if not self.bm25 or not self.bm25_chunks:
            return []
        q_tokens = self._token_list(query)
        if not q_tokens:
            return []
        try:
            scores = self.bm25.get_scores(q_tokens)
        except Exception as e:
            logger.warning("BM25 get_scores a échoué: %s", e)
            return []

        ranked: List[Tuple[int, float]] = sorted(
            enumerate(scores), key=lambda x: x[1], reverse=True
        )
        out: List[KBSearchResult] = []
        seen_parents: set[str] = set()
        for idx, sc in ranked:
            if sc <= 0:
                break
            chunk = self.bm25_chunks[idx]
            parent = chunk["parent_id"]
            if parent in seen_parents:
                continue  # une seule fiche par résultat (évite doublons)
            if (
                category_filter
                and category_filter != "Inconnue"
                and chunk["doc"].get("category") != category_filter
            ):
                continue
            seen_parents.add(parent)
            doc = chunk["doc"]
            # Normalise BM25 (peut être grand) → [0, 1) via / (1 + score)
            norm = float(sc) / (1.0 + float(sc))
            out.append(KBSearchResult(
                id=parent,
                title=doc.get("title", ""),
                category=doc.get("category", ""),
                problem_description=doc.get("problem_description", ""),
                solution_steps=doc.get("solution_steps", []),
                score=norm,
            ))
            if len(out) >= top_k:
                break
        return out

    # ------------------------------------------------------------------
    # Hybrid merge
    # ------------------------------------------------------------------

    def _hybrid_merge(
        self,
        semantic: List[KBSearchResult],
        bm25: List[KBSearchResult],
        top_k: int,
    ) -> List[KBSearchResult]:
        buckets: Dict[str, Dict[str, object]] = defaultdict(lambda: {"sem": 0.0, "bm": 0.0, "obj": None})
        for r in semantic:
            b = buckets[r.id]
            b["sem"] = max(b["sem"], r.score)  # type: ignore[arg-type]
            b["obj"] = r
        for r in bm25:
            b = buckets[r.id]
            b["bm"] = max(b["bm"], r.score)  # type: ignore[arg-type]
            b["obj"] = b["obj"] or r

        w_sem = app_settings.KB_SEMANTIC_WEIGHT
        w_bm = app_settings.KB_BM25_WEIGHT
        merged: List[KBSearchResult] = []
        for _id, b in buckets.items():
            sem = float(b["sem"])  # type: ignore[arg-type]
            bm = float(b["bm"])  # type: ignore[arg-type]
            final = w_sem * sem + w_bm * bm
            if final < app_settings.KB_HYBRID_MIN_SCORE:
                continue
            obj: KBSearchResult = b["obj"]  # type: ignore[assignment]
            obj.score = round(final, 4)
            merged.append(obj)
        merged.sort(key=lambda r: r.score, reverse=True)
        return merged[:top_k]

    # ------------------------------------------------------------------
    # Lexical fallback (kept as a last-resort safety net)
    # ------------------------------------------------------------------

    async def _search_local(
        self,
        query: str,
        top_k: int,
        category_filter: Optional[str],
    ) -> List[KBSearchResult]:
        query_tokens = self._tokens(query)
        category_tokens = self._tokens(category_filter or "")
        ranked: List[Tuple[float, dict]] = []
        for doc in self.local_documents:
            if (
                category_filter
                and category_filter != "Inconnue"
                and not category_tokens.intersection(self._tokens(doc.get("category", "")))
            ):
                continue
            searchable = " ".join([
                doc.get("title", ""),
                doc.get("problem_description", ""),
                doc.get("category", ""),
                " ".join(doc.get("keywords", [])),
            ])
            document_tokens = self._tokens(searchable)
            overlap = query_tokens.intersection(document_tokens)
            if not overlap:
                continue
            score = len(overlap) / max(len(query_tokens), 1)
            ranked.append((score, doc))

        ranked.sort(key=lambda item: item[0], reverse=True)
        return [
            KBSearchResult(
                id=doc["id"],
                title=doc.get("title", ""),
                category=doc.get("category", ""),
                problem_description=doc.get("problem_description", ""),
                solution_steps=doc.get("solution_steps", []),
                score=score,
            )
            for score, doc in ranked[:top_k]
            if score >= 0.15
        ]
