import logging
from typing import List, Optional
from fastapi import APIRouter, Query
from models.schemas import KBSearchResult
from api.chat import vector_store

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/kb", tags=["Knowledge Base"])

@router.get("/search", response_model=List[KBSearchResult])
async def search_kb(
    q: str = Query(..., description="Requête de recherche"),
    top_k: int = Query(3, description="Nombre de résultats"),
    category: Optional[str] = Query(None, description="Filtre par catégorie")
):
    """
    Recherche directement dans la base de connaissances (ChromaDB).
    Utilisé pour la recherche manuelle.
    """
    results = await vector_store.search(query=q, top_k=top_k, category_filter=category)
    return results
