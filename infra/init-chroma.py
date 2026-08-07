#!/usr/bin/env python3
# ============================================================
# Script d'initialisation ChromaDB — Chatbot AUTOHALL Helpdesk
# Charge les fiches de résolution dans la base vectorielle
# ============================================================

"""
Ce script est exécuté automatiquement au démarrage du backend.
Il peut aussi être lancé manuellement :
    python infra/init-chroma.py

Il charge les fiches de résolution depuis backend/rag/knowledge_data.json
et les indexe dans ChromaDB pour la recherche RAG.
"""

import json
import sys
import os
import time

# Ajouter le répertoire parent au path pour les imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend'))


def wait_for_chroma(host: str, port: int, max_retries: int = 30) -> bool:
    """Attend que ChromaDB soit disponible."""
    import httpx

    url = f"http://{host}:{port}/api/v1/heartbeat"
    for i in range(max_retries):
        try:
            response = httpx.get(url, timeout=5.0)
            if response.status_code == 200:
                print(f"✅ ChromaDB est disponible sur {host}:{port}")
                return True
        except Exception:
            pass
        print(f"⏳ Attente de ChromaDB... ({i + 1}/{max_retries})")
        time.sleep(2)

    print("❌ ChromaDB n'est pas disponible après les tentatives maximales")
    return False


def load_knowledge_base():
    """Charge les fiches de résolution dans ChromaDB."""
    # Configuration
    chroma_host = os.getenv("CHROMA_HOST", "localhost")
    chroma_port = int(os.getenv("CHROMA_PORT", "8001"))

    # Attendre que ChromaDB soit prêt
    if not wait_for_chroma(chroma_host, chroma_port):
        sys.exit(1)

    # Import ChromaDB
    import chromadb
    from chromadb.utils import embedding_functions

    # Connexion au serveur ChromaDB
    client = chromadb.HttpClient(host=chroma_host, port=chroma_port)

    # Fonction d'embedding (modèle multilingue pour le français)
    embedding_fn = embedding_functions.SentenceTransformerEmbeddingFunction(
        model_name="all-MiniLM-L6-v2"
    )

    # Créer ou récupérer la collection
    collection = client.get_or_create_collection(
        name="helpdesk_kb",
        embedding_function=embedding_fn,
        metadata={"hnsw:space": "cosine"}
    )

    # Vérifier si les documents sont déjà chargés
    existing = collection.count()
    if existing > 0:
        print(f"ℹ️  La collection contient déjà {existing} documents. Aucun rechargement nécessaire.")
        return

    # Charger les fiches depuis le fichier JSON
    kb_path = os.path.join(
        os.path.dirname(__file__), '..', 'backend', 'rag', 'knowledge_data.json'
    )

    with open(kb_path, 'r', encoding='utf-8') as f:
        fiches = json.load(f)

    # Préparer les documents pour ChromaDB
    ids = []
    documents = []
    metadatas = []

    for fiche in fiches:
        doc_id = f"kb_{fiche['id']}"
        # Combiner titre + description + solution pour un embedding riche
        doc_text = (
            f"{fiche['title']}\n\n"
            f"Problème : {fiche['problem_description']}\n\n"
            f"Solution : {' '.join(fiche['solution_steps'])}\n\n"
            f"Mots-clés : {', '.join(fiche['keywords'])}"
        )
        metadata = {
            "category": fiche["category"],
            "title": fiche["title"],
            "fiche_id": fiche["id"]
        }

        ids.append(doc_id)
        documents.append(doc_text)
        metadatas.append(metadata)

    # Indexer dans ChromaDB
    collection.add(
        ids=ids,
        documents=documents,
        metadatas=metadatas
    )

    print(f"✅ {len(fiches)} fiches de résolution chargées dans ChromaDB")
    for fiche in fiches:
        print(f"   📄 [{fiche['category']}] {fiche['title']}")


if __name__ == "__main__":
    load_knowledge_base()
