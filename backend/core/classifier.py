import logging
import re
import unicodedata
from typing import List, Dict, Any
from core.llm_provider import LLMProvider

logger = logging.getLogger(__name__)

# Les 47 catégories métier IT validées depuis ticket.xlsx
CATEGORIES = [
    "Wincar", "Messagerie", "Citrix", "Matériel", "Internet",
    "Logiciel Système", "Sage", "Windows", "APPCC", "Réseau",
    "Outillages SAV", "GestorNet", "CRM", "Auto Naps", "Poste IP Phone",
    "Reporting", "Ligne VPN", "Consommable", "Ligne Téléphonique", "GSM",
    "Moovapps", "PayRoll", "RIAPP", "Qalitel Doc", "GDoc",
    "Contrat de Vente", "Sage Paie & RH", "Microsoft Teams", "WebEX",
    "GENERAFI", "Site Web", "AppGCMA", "VPN_FortiClient", "Fidélisation",
    "Optimmo", "SMS", "SRM", "Qalitel Compar", "Antivirus", "SLV",
    "VOXCO", "Intranet", "Devopps", "C.Conformité", "eSeller", "TPE",
    "OPEL"
]

class Classifier:
    """
    Service responsable de la classification des demandes utilisateurs.
    Utilise le LLMProvider pour analyser les textes.
    """
    
    def __init__(self, llm_provider: LLMProvider):
        self.llm_provider = llm_provider

    async def analyze_issue(self, text: str) -> Dict[str, Any]:
        """
        Analyse une description de problème et retourne les méta-données.
        Si la confiance est basse, 'needs_clarification' est mis à True.
        """
        logger.info(f"Classification du texte: {text[:50]}...")

        # Fast rule-based classification first to avoid calling the LLM on every message.
        rule_result = self._classify_with_rules(text)
        if rule_result is not None:
            return self.normalize_result(rule_result)

        # Fallback to LLM provider when rules don't match
        try:
            result = await self.llm_provider.classify(text, CATEGORIES)
            return self.normalize_result(result)
        except Exception as exc:
            logger.warning("Classification LLM failed, returning conservative fallback: %s", exc)
            return self.normalize_result({
                "type": 1,
                "category": "Inconnue",
                "priority": 3,
                "criticality": "moyenne",
                "confidence": 0.2,
                "needs_clarification": True,
            })

    def _classify_with_rules(self, text: str) -> Dict[str, Any] | None:
        """Simple heuristic-based classifier to short-circuit common categories."""
        normalized = self._plain(text)
        if not normalized:
            return None

        # Category patterns
        patterns = [
            (r"\b(wincar)\b", "Wincar"),
            (r"\b(outlook|mail|messagerie|email|boite mail|boîte mail)\b", "Messagerie"),
            (r"\b(citrix|workspace)\b", "Citrix"),
            (r"\b(vpn)\b", "Ligne VPN"),
            (r"\b(wifi|wireless|réseau|internet|connexion)\b", "Réseau"),
            (r"\b(imprimante|printer)\b", "Imprimante"),
            (r"\b(serveur|server)\b", "Serveur"),
            (r"\b(sage|erp)\b", "Sage"),
        ]

        category = None
        for pat, cat in patterns:
            if re.search(pat, normalized, flags=re.IGNORECASE):
                category = cat
                break

        if category is None:
            return None

        # Priority heuristics
        priority = 3
        if re.search(r"\b(urgent|bloqué|impossible|inaccessible|hors service|ne marche plus|ne fonctionne plus)\b", normalized, flags=re.IGNORECASE):
            priority = 1
        elif re.search(r"\b(important|crash|erreur|bloque|plantage)\b", normalized, flags=re.IGNORECASE):
            priority = 2

        ticket_type = 1
        if re.search(r"\b(créer|creation|demande|installer|mettre à jour|ajouter)\b", normalized, flags=re.IGNORECASE):
            ticket_type = 2

        return {
            "type": ticket_type,
            "category": category,
            "priority": priority,
            "criticality": "très haute" if priority == 1 else "haute" if priority == 2 else "moyenne",
            "confidence": 0.9,
            "needs_clarification": False,
        }

    @staticmethod
    def _plain(value: Any) -> str:
        value = unicodedata.normalize("NFKD", str(value or ""))
        return "".join(char for char in value if not unicodedata.combining(char)).lower().strip()

    @classmethod
    def normalize_result(cls, result: Dict[str, Any]) -> Dict[str, Any]:
        """Valide le contrat de classification avant de l'envoyer au workflow."""
        raw_type = result.get("type", 1)
        if isinstance(raw_type, str):
            raw_type = 2 if cls._plain(raw_type) in {"demande", "request", "service"} else 1
        try:
            ticket_type = 2 if int(raw_type) == 2 else 1
        except (TypeError, ValueError):
            ticket_type = 1

        raw_category = str(result.get("category", "Inconnue")).strip()
        category_lookup = {cls._plain(category): category for category in CATEGORIES}
        aliases = {"vpn": "Ligne VPN", "reseau": "Réseau", "mail": "Messagerie", "email": "Messagerie"}
        category = category_lookup.get(cls._plain(raw_category), aliases.get(cls._plain(raw_category), "Inconnue"))

        try:
            priority = max(1, min(6, int(result.get("priority", 3))))
        except (TypeError, ValueError):
            priority = {"urgent": 1, "high": 2, "haute": 2, "medium": 3, "moyenne": 3, "low": 5, "basse": 5}.get(cls._plain(result.get("priority")), 3)

        if priority <= 1:
            criticality = "très haute"
        elif priority <= 2:
            criticality = "haute"
        elif priority <= 4:
            criticality = "moyenne"
        else:
            criticality = "basse"

        try:
            confidence = max(0.0, min(1.0, float(result.get("confidence", 0.0))))
        except (TypeError, ValueError):
            confidence = 0.0

        return {
            "type": ticket_type,
            "category": category,
            "priority": priority,
            "criticality": criticality,
            "confidence": confidence,
            "needs_clarification": bool(result.get("needs_clarification", False)) or confidence < 0.6 or category == "Inconnue",
        }
