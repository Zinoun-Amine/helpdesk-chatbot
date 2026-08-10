import unittest
from unittest.mock import AsyncMock, patch

import httpx

from core.classifier import Classifier
from core.conversation_engine import ConversationEngine
from integrations.glpi_client import GLPIClient
from rag.knowledge_loader import load_knowledge_base
from rag.vector_store import VectorStore
from services.email_service import EmailService
from services.ollama_ticket_service import OllamaTicketService


class QualificationTests(unittest.IsolatedAsyncioTestCase):
    async def test_incident_wincar_urgent(self):
        class Provider:
            async def classify(self, text, categories):
                return {
                    "type": 1,
                    "category": "Wincar",
                    "priority": 1,
                    "criticality": "Haute",
                    "confidence": 0.96,
                    "needs_clarification": False,
                }

        result = await Classifier(Provider()).analyze_issue("Wincar affiche une erreur au démarrage")
        self.assertEqual(result["type"], 1)
        self.assertEqual(result["category"], "Wincar")
        self.assertEqual(result["priority"], 1)
        self.assertEqual(result["criticality"], "très haute")
        self.assertFalse(result["needs_clarification"])

    async def test_demande_messagerie_medium(self):
        class Provider:
            async def classify(self, text, categories):
                return {
                    "type": "Demande",
                    "category": "email",
                    "priority": "Medium",
                    "confidence": 0.91,
                }

        result = await Classifier(Provider()).analyze_issue("Créer une boîte mail")
        self.assertEqual(result["type"], 2)
        self.assertEqual(result["category"], "Messagerie")
        self.assertEqual(result["priority"], 3)
        self.assertEqual(result["criticality"], "moyenne")

    async def test_low_confidence_requires_clarification(self):
        class Provider:
            async def classify(self, text, categories):
                return {"type": 1, "category": "Inconnue", "priority": 8, "confidence": 0.2}

        result = await Classifier(Provider()).analyze_issue("Ça ne marche pas")
        self.assertEqual(result["priority"], 6)
        self.assertTrue(result["needs_clarification"])

    async def test_short_greeting_does_not_trigger_ticket_flow(self):
        class Provider:
            async def classify(self, text, categories):
                return {"type": 1, "category": "Inconnue", "priority": 3, "confidence": 0.5, "needs_clarification": False}

            async def chat_stream(self, messages, temperature=0.3):
                yield "Bonjour"

        store = VectorStore()
        store.collection = None
        store.local_documents = []
        engine = ConversationEngine(
            llm_provider=Provider(),
            classifier=Classifier(Provider()),
            vector_store=store,
            ticket_service=OllamaTicketService(),
            email_service=EmailService(None, Provider()),
        )

        events = [event async for event in engine.process_message_stream([{"role": "user", "content": "bonjour"}], conversation_id=7)]
        self.assertTrue(any(event.get("type") == "token" and "Bonjour" in event.get("content", "") for event in events))
        self.assertFalse(any(event.get("action") == "ticket_created" for event in events))

    async def test_create_ticket_request_is_classified_as_ticket(self):
        rule = Classifier._classify_with_rules(Classifier(object()), "créer un ticket")
        self.assertEqual(rule["type"], 2)
        self.assertTrue(rule["needs_clarification"] is False)

    async def test_ticket_service_maps_category_to_technician(self):
        from services.ticket_service import TicketService

        technician = TicketService.get_default_technician_for_category("Wincar")
        self.assertIsNotNone(technician)
        self.assertEqual(technician["name"], "Amine Zinoun")
        self.assertEqual(technician["email"], "amine.zinoun@autohall.ma")
        self.assertIn("Wincar", technician["role"])

    async def test_local_knowledge_base_is_available_without_chroma(self):
        store = VectorStore()
        await load_knowledge_base(store)
        results = await store.search("Outlook demande sans cesse le mot de passe", category_filter="Messagerie")
        self.assertTrue(results)
        self.assertEqual(results[0].category, "Messagerie")
        self.assertTrue(results[0].solution_steps)

    async def test_glpi_rest_ticket_creation_contract(self):
        calls = []

        def handler(request):
            calls.append((request.method, request.url.path, request.headers.get("App-Token")))
            if request.url.path.endswith("/initSession/"):
                return httpx.Response(200, json={"session_token": "session-test"})
            return httpx.Response(201, json={"id": 42})

        client = GLPIClient()
        client.base_url = "https://glpi.test/apirest.php"
        client.app_token = "app-test"
        client.user_token = "user-test"
        client.client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
        result = await client.create_ticket({
            "title": "Wincar indisponible",
            "description": "Erreur au démarrage",
            "priority": "High",
            "ticket_type": 1,
        })
        await client.close()
        self.assertEqual(result["id"], 42)
        self.assertEqual(calls[0][1], "/apirest.php/initSession/")
        self.assertEqual(calls[1][1], "/apirest.php/Ticket/")

    async def test_smtp_send_is_not_simulated(self):
        email = EmailService(None)
        draft = await email.create_draft(99, "user@example.com", "Ticket", "Contenu")
        with patch.object(email.smtp, "send", new_callable=AsyncMock) as send:
            sent = await email.send_draft(draft.id)
        send.assert_awaited_once_with("user@example.com", "Ticket", "Contenu")
        self.assertEqual(sent.status, "sent")

    async def test_ollama_only_engine_qualifies_and_creates_ticket(self):
        class Provider:
            async def classify(self, text, categories):
                return {"type": 1, "category": "Wincar", "priority": 2, "confidence": 0.95}

            async def chat(self, messages, temperature=0.3):
                return '{"title":"Wincar indisponible","description":"Erreur Wincar","category":"Wincar","priority":"High","summary":"Erreur"}'

            async def chat_stream(self, messages, temperature=0.3):
                yield "Ticket créé"

        store = VectorStore()
        store.collection = None
        store.local_documents = []
        engine = ConversationEngine(
            llm_provider=Provider(),
            classifier=Classifier(Provider()),
            vector_store=store,
            ticket_service=OllamaTicketService(),
            email_service=EmailService(None, Provider()),
        )
        events = [event async for event in engine.process_message_stream(
            [{"role": "user", "content": "Wincar ne démarre plus"}],
            user_email="test@example.com",
            conversation_id=7,
        )]
        ticket_events = [event for event in events if event.get("action") == "ticket_created"]
        self.assertEqual(len(ticket_events), 1)
        self.assertEqual(ticket_events[0]["ticket"]["ticket_type"], 1)
        self.assertEqual(ticket_events[0]["ticket"]["category"], "Wincar")
        self.assertEqual(ticket_events[0]["ticket"]["priority"], "High")
        self.assertTrue(any(event.get("action") == "email_draft" for event in events))


if __name__ == "__main__":
    unittest.main()
