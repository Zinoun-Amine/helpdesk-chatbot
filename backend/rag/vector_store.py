import logging
import re
import time
import unicodedata
from typing import List, Optional
from models.schemas import KBSearchResult
from config import settings as app_settings

try:
    import chromadb
    from chromadb.config import Settings
except Exception as exc:  # pragma: no cover - runtime fallback for local env mismatches
    chromadb = None
    Settings = None
    _chromadb_import_error = exc

logger = logging.getLogger(__name__)

class VectorStore:
    """
    Gestionnaire de la base de données vectorielle ChromaDB.
    Permet l'indexation et la recherche des fiches de connaissances.
    """

    def __init__(self):
        self.local_documents: List[dict] = []
        if app_settings.OLLAMA_ONLY:
            logger.info("Mode Ollama seul activé : ChromaDB désactivé, usage du KB local uniquement.")
            self.client = None
            self.collection = None
            return

        if chromadb is None:
            logger.warning(f"ChromaDB indisponible, base KB désactivée: {_chromadb_import_error}")
            self.client = None
            self.collection = None
            return

        for attempt in range(1, 4):
            try:
                self.client = chromadb.HttpClient(
                    host=app_settings.CHROMA_HOST, 
                    port=app_settings.CHROMA_PORT,
                    settings=Settings(allow_reset=True)
                )
                # Utilise un modèle d'embedding par défaut (all-MiniLM-L6-v2 par exemple)
                self.collection = self.client.get_or_create_collection(
                    name="helpdesk_kb",
                    metadata={"hnsw:space": "cosine"}
                )
                logger.info("ChromaDB initialisé avec succès.")
                break
            except Exception as e:
                if attempt >= 3:
                    logger.error(f"Erreur lors de l'initialisation de ChromaDB après plusieurs tentatives: {e}")
                    self.collection = None
                else:
                    logger.warning(f"Tentative {attempt} de connexion à ChromaDB échouée, nouvelle tentative dans 1s: {e}")
                    time.sleep(1)

    async def add_documents(self, documents: List[dict]):
        """
        Ajoute une liste de documents (fiches KB) à la collection ChromaDB.
        """
        self.local_documents = list(documents)
        if not self.collection:
            if not app_settings.OLLAMA_ONLY:
                logger.warning("ChromaDB non initialisé, impossible d'ajouter des documents.")
            return

        ids = [doc["id"] for doc in documents]
        
        # Vérifier quels documents existent déjà
        try:
            existing = self.collection.get(ids=ids)
            existing_ids = existing.get("ids", [])
        except Exception:
            existing_ids = []

        new_docs = [doc for doc in documents if doc["id"] not in existing_ids]
        
        if not new_docs:
            logger.info("Tous les documents sont déjà indexés.")
            return

        texts = [
            f"{doc['title']}. {doc['problem_description']}. Mots clés: {', '.join(doc['keywords'])}"
            for doc in new_docs
        ]
        metadatas = [
            {
                "title": doc["title"],
                "category": doc["category"],
                "problem_description": doc["problem_description"],
                # ChromaDB metadata ne prend que des strings, int, float, on sérialise les listes si besoin, 
                # mais ici on stocke les solutions en string séparées par |
                "solution_steps": "|".join(doc["solution_steps"])
            }
            for doc in new_docs
        ]
        new_ids = [doc["id"] for doc in new_docs]

        try:
            self.collection.add(
                documents=texts,
                metadatas=metadatas,
                ids=new_ids
            )
            logger.info(f"Ajout de {len(new_ids)} documents à ChromaDB.")
        except Exception as e:
            logger.error(f"Erreur lors de l'ajout des documents à ChromaDB: {e}")

    @staticmethod
    def _tokens(value: str) -> set[str]:
        normalized = unicodedata.normalize("NFKD", value or "")
        normalized = "".join(char for char in normalized if not unicodedata.combining(char))
        return {token for token in re.findall(r"[a-z0-9]+", normalized.lower()) if len(token) > 2}

    async def _search_local(self, query: str, top_k: int, category_filter: Optional[str]) -> List[KBSearchResult]:
        query_tokens = self._tokens(query)
        category_tokens = self._tokens(category_filter or "")
        ranked = []
        for doc in self.local_documents:
            if category_filter and category_filter != "Inconnue" and not category_tokens.intersection(self._tokens(doc.get("category", ""))):
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
                title=doc["title"],
                category=doc["category"],
                problem_description=doc["problem_description"],
                solution_steps=doc["solution_steps"],
                score=score,
            )
            for score, doc in ranked[:top_k]
            if score >= 0.15
        ]

    async def search(self, query: str, top_k: int = 3, category_filter: Optional[str] = None) -> List[KBSearchResult]:
        """
        Recherche sémantique dans la base de connaissances.
        """
        if not self.collection:
            return await self._search_local(query, top_k, category_filter)

        where_clause = None
        if category_filter and category_filter != "Inconnue":
            where_clause = {"category": category_filter}

        try:
            results = self.collection.query(
                query_texts=[query],
                n_results=top_k,
                where=where_clause
            )
            
            kb_results = []
            if results and results.get("ids") and len(results["ids"]) > 0:
                for i in range(len(results["ids"][0])):
                    doc_id = results["ids"][0][i]
                    metadata = results["metadatas"][0][i]
                    # La distance de cosine (plus bas est meilleur, souvent converti en score)
                    distance = results["distances"][0][i] if results.get("distances") else 0.0
                    
                    # Convertir en score de similarité basique si on utilise la distance
                    score = 1.0 / (1.0 + distance)
                    
                    # Si le score est trop bas, on ignore (seuil arbitraire)
                    if score < 0.5:
                        continue

                    kb_results.append(KBSearchResult(
                        id=doc_id,
                        title=metadata.get("title", ""),
                        category=metadata.get("category", ""),
                        problem_description=metadata.get("problem_description", ""),
                        solution_steps=metadata.get("solution_steps", "").split("|"),
                        score=score
                    ))
            
            if kb_results:
                return kb_results
            return await self._search_local(query, top_k, category_filter)
        except Exception as e:
            logger.error(f"Erreur lors de la recherche RAG: {e}")
            return await self._search_local(query, top_k, category_filter)
