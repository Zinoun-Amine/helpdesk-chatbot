# AUTOHALL Helpdesk Project Report Brief

## Purpose of This File

This file is a prepared context brief for Gemini. Use it to help write a formal academic and technical report about the AUTOHALL Helpdesk chatbot project. The report should be based on the implementation described below, not on assumptions.

## Ready-to-Use Prompt for Gemini

> You are helping me write a professional academic and technical report about the AUTOHALL Helpdesk project. Use the complete project brief below as your source of truth. Produce a well-structured report in clear formal English, with an optional French executive summary if useful.
>
> The report should include:
> 1. Title page content and abstract
> 2. Context and motivation
> 3. Problem statement
> 4. Project objectives and functional requirements
> 5. Requirements analysis and user roles
> 6. System architecture and technology choices
> 7. Backend design and API organization
> 8. Frontend design and user workflows
> 9. Artificial intelligence components: LLM providers, classification, conversation engine, and RAG
> 10. Knowledge-base preparation and the analysis of 47 ITIL categories
> 11. Ticket lifecycle, assignment, status consultation, and email notifications
> 12. Role-based security and ticket/dashboard visibility
> 13. Database model and persistence strategy
> 14. Deployment with Docker Compose
> 15. Testing and validation results
> 16. Limitations, risks, and improvements
> 17. Conclusion and future work
>
> Explain design decisions, data flow, and security implications. Distinguish clearly between implemented features, test/demo data, fictional technician identities, and future improvements. Do not invent metrics that are not present in this brief. Where the project README conflicts with this brief, mention the discrepancy and use the current implementation as the primary reference.

## Project Identity

- Project name: AUTOHALL Helpdesk
- Domain: Internal IT helpdesk for an automotive organization
- Main purpose: Help employees describe IT problems, receive knowledge-base solutions, create and follow tickets, and notify support technicians.
- Language of chatbot responses: French
- Deployment style: Docker Compose for local development and integrated services
- Main user roles: `admin` and `user`

## Main Technologies

### Frontend

- React 19
- Vite
- Tailwind CSS
- Server-Sent Events for streaming chat responses
- Browser `localStorage` for JWT and user session persistence

Important frontend areas:

- `frontend/src/App.jsx`: application shell, authentication gate, navigation, chat, dashboard, and ticket views
- `frontend/src/components/ChatWindow.jsx`: chat interface
- `frontend/src/components/TicketsPage.jsx`: ticket list, filters, details, comments, assignment, and email actions
- `frontend/src/components/DashboardPage.jsx`: dashboard statistics and charts
- `frontend/src/hooks/useChat.js`: SSE chat client and authenticated requests
- `frontend/src/hooks/useAuth.js`: public authentication hook
- `frontend/src/contexts/AuthContext.jsx`: shared authentication state and persistence
- `frontend/src/services/api.js`: authenticated REST client
- `frontend/src/services/authApi.js`: login and registration API calls

### Backend

- Python 3.12
- FastAPI
- Uvicorn
- Pydantic schemas
- SQLAlchemy async engine with asyncpg
- PostgreSQL
- Redis for caching and rate limiting
- ChromaDB for vector search
- Sentence-transformers / embedding-based retrieval
- Ollama as the primary local or host LLM provider
- Groq and Gemini as optional fallback providers
- SMTP for email delivery

Important backend areas:

- `backend/main.py`: FastAPI application and lifespan startup
- `backend/api/chat.py`: authenticated chat endpoint and SSE response
- `backend/api/auth.py`: registration, login, and current-user operations
- `backend/api/tickets.py`: ticket CRUD, assignment, email drafts, and status operations
- `backend/api/dashboard.py`: role-aware dashboard endpoint
- `backend/core/conversation_engine.py`: conversation workflow and ticket-status query handling
- `backend/core/classifier.py`: rule-based and LLM-assisted classification
- `backend/core/security.py`: bcrypt password hashing and JWT verification
- `backend/services/ticket_service.py`: ticket persistence and technician assignment map
- `backend/services/dashboard_service.py`: dashboard aggregation
- `backend/services/conversation_service.py`: conversations and message statistics
- `backend/services/email_service.py`: email draft generation and SMTP sending
- `backend/rag/knowledge_loader.py`: knowledge-base loading
- `backend/rag/vector_store.py`: hybrid semantic/BM25 retrieval
- `backend/db/schema.sql`: database schema
- `backend/db/seed.sql`: initial data
- `backend/db/migrations.py`: startup migrations and technician consolidation

## Architecture and Data Flow

1. A user opens the React frontend.
2. The user authenticates through `/auth/login` or registers through `/auth/register`.
3. The backend returns a JWT and public user profile. The frontend stores both in `localStorage`.
4. REST requests include `Authorization: Bearer <JWT>` through the API client.
5. Chat SSE requests also include the JWT directly in their headers.
6. The backend validates the JWT and derives the authenticated user identity.
7. The conversation engine processes the user message.
8. The classifier uses fast rules for common terms and calls an LLM when rules do not match.
9. The RAG layer searches the knowledge base using vector and BM25 retrieval.
10. If a known solution is found, the assistant proposes it.
11. If a ticket is required, the system creates the ticket, assigns a technician by category, creates email drafts, and can send them through SMTP.
12. PostgreSQL stores tickets, conversations, messages, assignments, users, categories, technicians, and email drafts.
13. Redis supports caching and request rate limiting.
14. ChromaDB stores and queries vector representations of the knowledge base.

## Functional Features Implemented

### Authentication

- User registration
- Login with email and password
- bcrypt password hashing
- JWT-based authentication
- Persistent frontend session using `localStorage`
- Admin and regular-user roles
- Authenticated chat, tickets, and dashboard requests

Current demo administrator:

- Email: `admin@autohall.ma`
- Password: `admin1234`

Do not describe this password as a production credential. It is a local demonstration credential and should be changed in a real deployment.

### Conversational Helpdesk

- French-language conversational interface
- Greeting handling
- Context-aware conversation history
- Streaming assistant responses through SSE
- Classification of incident versus service request
- Priority and criticality determination
- Clarification when a request is ambiguous
- Knowledge-base search before ticket creation
- Ticket creation when no suitable knowledge-base answer is found

### Ticket Status Consultation

The conversation engine detects requests such as:

- `Quel est l'état du ticket #46 ?`
- `Statut du ticket 123`
- `Ou en est le ticket #78 ?`

It extracts the ticket ID, retrieves the ticket, and returns status, category, priority, assigned technician, and creation date. It returns early without running normal classification, RAG, or ticket creation.

### Ticket Management

- List and search tickets
- Filter by status and priority
- Ticket details
- Ticket updates
- Ticket comments/messages
- Ticket history
- Manual technician reassignment
- Automatic assignment by category
- Status query from chat

### Email Workflow

- Email draft generation
- Technician notification
- User confirmation email
- Email draft update and send endpoints
- Reassignment updates the latest pending draft to target the new technician
- Direct ticket creation creates separate technician and user email drafts
- With `SMTP_ENABLED=True` and `SMTP_AUTO_SEND=True`, emails are sent automatically

Email delivery depends on valid SMTP configuration. Logs showing `E-mail SMTP envoyé` indicate that the SMTP client completed a send operation; actual inbox delivery still depends on the mail server and recipient configuration.

### Role-Based Visibility

- Administrators see all tickets and dashboard data.
- Regular users see only tickets whose `user_email` matches their authenticated account.
- The backend enforces the ownership rule from the JWT; the frontend filter is not the only protection.
- Regular-user dashboard statistics are scoped to the user’s tickets, conversations, messages, activity, statuses, and priorities.

## Category Analysis and Technician Balancing

The workbook `ticket.xlsx` was analyzed with `backend/tests/test.py`.

Results:

- Official validated categories: 47
- Overflow/noise rows not matching the official taxonomy: 3,572
- Official category ticket total used for balancing: 46,427
- Ideal average workload across four technicians: 11,606.75 tickets

The balancing script is `backend/tests/balance_categories.py`. It uses a largest-first greedy load-balancing algorithm: categories remain intact and each next category is assigned to the technician with the lowest current workload.

Balanced result:

| Technician | Categories | Tickets |
|---|---:|---:|
| Amine Zinoun | 11 | 11,606 |
| Sofia El Idrissi | 12 | 11,606 |
| Youssef Bensaid | 12 | 11,608 |
| Nabil Cherkaoui | 12 | 11,607 |

Workload range: 2 tickets.

Category groups:

- Amine Zinoun: Wincar, Windows, GestorNet, Consommable, Moovapps, Contrat de Vente, GENERAFI, Fidélisation, SMS, VOXCO, TPE
- Sofia El Idrissi: Citrix, Logiciel Système, Réseau, CRM, Ligne VPN, RIAPP, Qalitel Doc, Microsoft Teams, VPN_FortiClient, Antivirus, Intranet, eSeller
- Youssef Bensaid: Matériel, Internet, APPCC, Poste IP Phone, Reporting, PayRoll, GDoc, Site Web, Optimmo, Qalitel Compar, SLV, C.Conformité
- Nabil Cherkaoui: Messagerie, Sage, Outillages SAV, Auto Naps, Ligne Téléphonique, GSM, Sage Paie & RH, WebEX, AppGCMA, SRM, Devopps, OPEL

The current runtime assignment map is generated in `backend/services/ticket_service.py` through `TECHNICIAN_GROUPS` and `TECHNICIAN_BY_CATEGORY`.

The PostgreSQL migration consolidates existing technicians and reassigns existing tickets to these four technicians. The current database was verified with exactly four technician records and no tickets pointing to removed technician emails.

The generated technician identities are fictional demo data and must be replaced with real employees and verified email addresses before production use.

## Database Model

Main tables:

- `users`: authenticated accounts, roles, password hashes, activation state
- `categories`: ITIL categories
- `technicians`: four active support technicians after consolidation
- `tickets`: title, description, type, priority, status, category, owner, assignment, timestamps
- `ticket_assignments`: assignment history
- `conversations`: chat sessions and owner identity
- `messages`: chat message history
- `ticket_messages`: ticket comments
- `ticket_history`: changes to ticket fields
- `email_drafts`: generated email content and send status
- `app_settings`: persistent application configuration
- `chat_feedback`: assistant response ratings

## Security Design

- Passwords are hashed with direct bcrypt usage.
- JWT tokens identify the user and expire according to configuration.
- Password hashes are never returned in public user responses.
- Ticket list visibility is enforced server-side.
- Chat ticket ownership is derived server-side from the authenticated user, preventing fallback ownership errors.
- Attachments have size and MIME-type restrictions.
- Redis rate limiting protects the chat endpoint.
- SMTP credentials are configuration secrets and should remain in `.env`, never in source control.

## Deployment

Start the application from the repository root:

```powershell
docker-compose up -d
```

Services:

- Frontend: `http://localhost:3000`
- Backend API: `http://localhost:8000`
- FastAPI documentation: `http://localhost:8000/docs`
- PostgreSQL host port: `5433`
- ChromaDB host port: `8001`
- Redis host port: `6379`

Check container status:

```powershell
docker-compose ps
```

Check backend health:

```powershell
Invoke-WebRequest -UseBasicParsing http://localhost:8000/health
```

Expected backend health response:

```json
{"status":"ok","app":"AUTOHALL Helpdesk API"}
```

## Testing and Verified Results

### Category validation

```powershell
Push-Location backend\tests
python test.py
Pop-Location
```

Expected: 47 validated categories and 3,572 overflow/noise rows.

### Workload balancing

```powershell
python backend\tests\balance_categories.py
```

Expected: 47 categories, 46,427 official-category tickets, and a workload range of 2 tickets.

### Python validation

```powershell
python -m py_compile backend\core\conversation_engine.py backend\services\ticket_service.py
python -m py_compile backend\api\chat.py backend\api\tickets.py backend\api\dashboard.py
```

### Frontend validation

```powershell
Push-Location frontend
npm run build
npm run lint
Pop-Location
```

The production build passed. Lint has warnings in some existing files, but no blocking lint errors.

### Authentication and visibility validation

Verified behavior:

- Admin account returns `role=admin` and can see all tickets.
- Regular account returns `role=user` and receives only its own tickets.
- Backend ignores a regular user’s attempt to request another user’s email through the query string.
- Dashboard totals differ between admin and regular-user accounts according to ownership.

### Ticket-status validation

An authenticated live SSE request for ticket `#46` returned a response containing its status, category, priority, assigned technician, and creation date. No ticket was created by that query.

### Email validation

SMTP was configured in the running environment with automatic sending enabled. Recent logs confirmed SMTP sends to assigned technicians. The implementation now creates separate drafts for technicians and ticket owners on direct ticket creation.

## Known Limitations and Report Caveats

1. The 3,572 overflow rows contain raw, inconsistent, or free-text category values. They are excluded from official category balancing and should be cleaned or mapped in a future data-preparation phase.
2. The four generated technician identities are fictional. Their addresses must not be treated as real organizational contacts.
3. SMTP log success confirms the application handed the message to the SMTP server; it does not guarantee final inbox delivery.
4. Ollama, Groq, and Gemini behavior depends on external configuration, API availability, model availability, and network access.
5. RAG quality depends on the quality and coverage of the knowledge base.
6. The backend development container uses Uvicorn reload mode, so an immediate health probe during reload can be temporarily reset.
7. Some repository documentation is outdated: the README still mentions 23 categories and says emails are not automatically sent, while the current implementation uses 47 categories and supports automatic sending when enabled.
8. A non-fatal ChromaDB telemetry compatibility warning may appear during startup.
9. Development/demo credentials are present in the local environment and should be rotated before deployment.
10. The dashboard and ticket visibility controls are scoped by the authenticated user in the current PostgreSQL path; alternative GLPI/Ollama-only modes should receive the same ownership enforcement before being used in production.

## Suggested Report Tables and Figures

- System architecture diagram: React frontend, FastAPI backend, PostgreSQL, Redis, ChromaDB, Ollama, SMTP
- Functional requirements table
- User-role permissions matrix
- Database entity relationship diagram
- Ticket lifecycle flowchart
- Chat decision flow: greeting, classification, RAG, ticket creation, status query
- 47-category volume table
- Four-technician workload distribution table
- API endpoint table
- Test and validation table

## Important Accuracy Instructions

- Use the current implementation described here as the main source of truth.
- Do not claim that all 47 categories have real assigned employees; the generated technician names are fictional demo identities.
- Do not claim that 3,572 overflow rows were successfully classified.
- Do not expose SMTP passwords, API keys, JWT secrets, or database credentials in the report.
- Explain that the system supports automatic emails only when SMTP configuration and auto-send settings are enabled.
- Explain that regular-user access restrictions are enforced by the backend, not only by the frontend.
