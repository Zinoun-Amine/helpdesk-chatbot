import json
import os
import logging
from rag.vector_store import VectorStore

logger = logging.getLogger(__name__)

async def load_knowledge_base(vector_store: VectorStore):
    """
    Charge les données depuis le fichier JSON et les indexe dans ChromaDB.
    A exécuter au démarrage de l'application (lifespan).
    """
    file_path = os.path.join(os.path.dirname(__file__), "knowledge_base.json")
    
    try:
        if not os.path.exists(file_path):
            logger.error(f"Fichier de base de connaissances non trouvé: {file_path}")
            return
            
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)
            
        if not data:
            logger.warning("Fichier de connaissances vide.")
            return
            
        await vector_store.add_documents(data)
        logger.info(f"Base de connaissances chargée avec succès. ({len(data)} fiches)")
        
    except json.JSONDecodeError:
        logger.error("Erreur de format dans le fichier knowledge_base.json")
    except Exception as e:
        logger.error(f"Erreur inattendue lors du chargement de la base de connaissances: {e}")
