# Chatbot AUTOHALL Helpdesk

> Assistant intelligent pour le Helpdesk IT AUTOHALL 

##  Description

Ce chatbot IA aide les utilisateurs AUTOHALL à :
- **Décrire leur problème** via un dialogue guidé en langage naturel
- **Qualifier automatiquement** la demande (Incident vs Demande)
- **Classifier** par catégorie, priorité et criticité
- **Trouver des solutions rapides** via une base de connaissances (RAG)
- **Créer automatiquement un ticket** quand aucune solution n'est trouvée
- **Générer un brouillon d'e-mail** de confirmation 
- **Consulter l'état** d'un ticket existant

##  Architecture

```
┌─────────────┐     SSE      ┌──────────────┐     HTTP      ┌────────────┐
│   Frontend  │◄────────────►│   Backend    │◄─────────────►│   Ollama   │
│  React+Vite │              │   FastAPI    │               │     +      │
│  Tailwind   │              │  (async)     │               │ qwen2.5:3b │
└─────────────┘              └──────┬───────┘               └────────────┘
                                    │
                        ┌───────────┼───────────┐
                        │           │           │
                  ┌─────▼─────┐ ┌───▼───┐ ┌────▼─────┐
                  │ PostgreSQL│ │ Redis │ │ ChromaDB │
                  │  Tickets  │ │ Cache │ │   RAG    │
                  │  Messages │ │       │ │   KB     │
                  └───────────┘ └───────┘ └──────────┘
```

##  Lancement rapide

### Prérequis

- [Docker](https://www.docker.com/get-started) (version 20+)
- [Docker Compose](https://docs.docker.com/compose/) (version 2+)
- 8 Go de RAM minimum (pour Ollama)

### Étapes

1. **Cloner le projet et configurer l'environnement**
```bash
cd "helpdesk-chatbot"
cp .env.example .env
```

2. **Lancer tous les services**
```bash
docker-compose up --build
```

### Mode Ollama Cloud uniquement

Le fichier `.env` est configuré pour utiliser directement l'API Ollama Cloud. PostgreSQL reste facultatif ; le backend utilise un index local de la base de connaissances si ChromaDB n'est pas disponible.

### Using a local Ollama (host) or Dockerized Ollama

If you already have Ollama and a model installed on your host machine (e.g. `mistral-7b`), you can point the backend to it without installing the model again inside the container. In `.env` use:

```env
OLLAMA_BASE_URL=http://host.docker.internal:11434
OLLAMA_MODEL=mistral-7b
```

This keeps model files on your host and is the simplest setup for local development. Note: the backend depends on a host process running at `host.docker.internal:11434`.

Alternatively, if you prefer the `ollama` service to run entirely in Docker, set `OLLAMA_BASE_URL=http://ollama:11434` and either pull/install the model inside the `autohall_ollama` container or mount your host `.ollama` directory into the container's `/root/.ollama` volume.

### Connexion GLPI et SMTP

Le workflow complet est actif en mode Ollama seul. Pour créer les tickets dans une instance GLPI réelle, renseignez dans `.env` :

```env
GLPI_ENABLED=true
GLPI_BASE_URL=https://glpi.example.com
GLPI_APP_TOKEN=...
GLPI_USER_TOKEN=...
```

L'API utilisée est l'API REST GLPI v1 (`initSession`, puis `Ticket/`). Le compte GLPI doit avoir les droits de création et de modification des tickets.

Pour l'envoi réel des e-mails :

```env
SMTP_ENABLED=true
SMTP_HOST=smtp.example.com
SMTP_PORT=587
SMTP_USERNAME=...
SMTP_PASSWORD=...
SMTP_FROM=helpdesk@example.com
SMTP_USE_STARTTLS=true
SMTP_AUTO_SEND=true
```

Sans ces paramètres, les tickets restent en mémoire en mode local et l'envoi SMTP est refusé explicitement ; aucun faux e-mail n'est marqué comme envoyé.

3. **Télécharger le modèle LLM** (première fois uniquement — only needed if using the Dockerized `ollama` service)
```bash
# If you use the Dockerized Ollama service (OLLAMA_BASE_URL=http://ollama:11434):
docker exec -it autohall_ollama ollama pull gpt-oss:20b

# If you point the backend to the host Ollama (OLLAMA_BASE_URL=http://host.docker.internal:11434),
# you can skip the container pull step because the host-installed model will be used.
```

4. **Accéder à l'application**
-  Frontend : [http://localhost:3000](http://localhost:3000)
-  API Backend : [http://localhost:8000](http://localhost:8000)
-  Documentation API : [http://localhost:8000/docs](http://localhost:8000/docs)

##  API Endpoints

| Méthode | Endpoint | Description |
|---------|----------|-------------|
| `POST` | `/chat` | Chat streaming (SSE) — point d'entrée principal |
| `GET` | `/tickets` | Liste des tickets (filtres optionnels) |
| `POST` | `/tickets` | Création manuelle d'un ticket |
| `GET` | `/tickets/{id}/status` | État d'un ticket |
| `PUT` | `/tickets/{id}` | Mise à jour d'un ticket |
| `GET` | `/kb/search` | Recherche dans la base de connaissances |
| `PUT` | `/email-drafts/{id}` | Modifier un brouillon d'e-mail |
| `POST` | `/email-drafts/{id}/send` | Marquer un brouillon comme envoyé |

### Exemple — Chat streaming

```bash
curl -N -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{"messages": [{"role": "user", "content": "Bonjour, Wincar ne fonctionne plus"}]}'
```

Réponse SSE :
```
event: token
data: {"content": "Bonjour"}

event: token
data: {"content": " ! Je comprends"}

event: action
data: {"type": "kb_result", "results": [...]}

event: done
data: [DONE]
```

##  Structure du projet

```
ChatBot Auto Hall/
├── docker-compose.yml          # Orchestration des 6 services
├── .env.example                # Variables d'environnement
├── README.md                   # Ce fichier
│
├── backend/                    # API FastAPI (Python)
│   ├── main.py                 # Point d'entrée
│   ├── config.py               # Configuration
│   ├── api/                    # Endpoints REST & SSE
│   ├── core/                   # LLM, classification, moteur conversationnel
│   ├── rag/                    # Base de connaissances vectorielle
│   ├── services/               # Logique métier (tickets, emails, cache)
│   ├── models/                 # Schémas Pydantic
│   └── db/                     # Schéma SQL & seeds
│
├── frontend/                   # Interface React + Tailwind
│   └── src/
│       ├── components/         # Composants UI
│       ├── hooks/              # Hooks React (chat SSE, thème)
│       └── services/           # Client API
│
└── infra/                      # Scripts d'infrastructure
```

##  Base de données

### Tables principales

| Table | Description |
|-------|-------------|
| `categories` | 23 catégories ITIL métier (Wincar, Messagerie, Citrix...) |
| `tickets` | Tickets helpdesk (type, priorité, catégorie, statut) |
| `conversations` | Sessions de chat avec état du flux |
| `messages` | Historique des messages (user/assistant) |
| `email_drafts` | Brouillons d'e-mail (jamais envoyés sans validation) |

### Interfaces et rôles

| Rôle | Interface | Accès |
|------|-----------|-------|
| `user` | Chat | Chatbot uniquement |
| `technician` | Tickets | Tickets assignés à son adresse e-mail |
| `admin` | Administration | Chat, tous les tickets, dashboard et paramètres |

Les quatre comptes techniciens sont créés automatiquement depuis la table `technicians` pendant la migration PostgreSQL. Leur mot de passe initial local est défini par `TECHNICIAN_DEFAULT_PASSWORD` (valeur par défaut : `technician1234`) et doit être changé avant toute utilisation réelle.

### Catégories métier

Wincar • Messagerie • Citrix • Matériel • Internet • Logiciel Système • Sage • Windows • APPCC • Réseau • Outillages SAV • GestorNet • CRM • Auto Naps • Poste IP Phone • Reporting • Ligne VPN • Consommable • Ligne Téléphonique • GSM • Moovapps • PayRoll • SRM

## ⚙️ Configuration

Les variables d'environnement sont définies dans `.env` :

| Variable | Description | Défaut |
|----------|-------------|--------|
| `OLLAMA_BASE_URL` | URL du serveur Ollama | `http://ollama:11434` |
| `OLLAMA_MODEL` | Modèle LLM à utiliser | `gpt-oss:20b` |
| `OLLAMA_API_KEY` | Clé API Ollama si un proxy/authentification est utilisé | vide |
| `DATABASE_URL` | Connexion PostgreSQL | voir `.env.example` |
| `REDIS_URL` | Connexion Redis | `redis://redis:6379/0` |
| `EMBEDDING_MODEL` | Modèle Sentence-Transformers pour la KB (RAG) | `sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2` |
| `KB_USE_DEFAULT_EMBEDDING` | `true` pour utiliser l'embedding par défaut de Chroma | `false` |
| `RATE_LIMIT_REQUESTS` | Requêtes max / fenêtre | `30` |
| `CACHE_TTL_SECONDS` | Durée du cache | `300` |

##  Sécurité & Contraintes

-  **Aucun e-mail envoyé automatiquement** — toujours un brouillon éditable
-  **Aucune donnée personnelle réelle** dans le code ou les seeds
-  **Pas de classification prématurée** — questions de clarification si ambigu
-  **LLMProvider abstrait** — changement de provider sans modifier le code métier
-  **Rate limiting** — protection contre les abus via Redis
-  **Cache Redis** — réponses rapides pour les questions fréquentes

##  Développement

### Lancer uniquement le backend (hors Docker)

```bash
cd backend
pip install -r requirements.txt
uvicorn main:app --reload --port 8000
```

### Lancer uniquement le frontend (hors Docker)

```bash
cd frontend
npm install
npm run dev
```

##  Licence

Projet interne AUTOHALL — Digital Factory Analytic Apps — 2026
