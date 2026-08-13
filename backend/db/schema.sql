-- ============================================================
-- Schéma PostgreSQL — Chatbot AUTOHALL Helpdesk
-- Tables : categories, technicians, conversations, tickets,
--          messages, ticket_messages, ticket_history,
--          ticket_assignments, email_drafts
-- ============================================================

CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- ── Catégories ITIL ─────────────────────────────────────────
CREATE TABLE IF NOT EXISTS categories (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL UNIQUE,
    description TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- ── Techniciens ──────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS technicians (
    id SERIAL PRIMARY KEY,
    full_name VARCHAR(200) NOT NULL,
    email VARCHAR(200) NOT NULL UNIQUE,
    role VARCHAR(200),
    team VARCHAR(100),
    category_id INTEGER REFERENCES categories(id) ON DELETE SET NULL,
    active BOOLEAN DEFAULT TRUE,
    max_concurrent_tickets INTEGER DEFAULT 20,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_technicians_category ON technicians(category_id);
CREATE INDEX IF NOT EXISTS idx_technicians_email    ON technicians(LOWER(email));

-- ── Conversations ────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS conversations (
    id SERIAL PRIMARY KEY,
    user_name VARCHAR(200),
    user_email VARCHAR(200),
    current_state VARCHAR(50) DEFAULT 'accueil',
    qualification_data JSONB DEFAULT '{}',
    status VARCHAR(20) DEFAULT 'active'
        CHECK (status IN ('active', 'closed')),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- ── Tickets (schéma étendu) ──────────────────────────────────
CREATE TABLE IF NOT EXISTS tickets (
    id SERIAL PRIMARY KEY,
    title VARCHAR(500) NOT NULL,
    content TEXT NOT NULL,
    description TEXT,               -- alias for content used by API
    summary TEXT,                   -- résumé court (LLM)
    -- 1 = Incident, 2 = Demande
    type INTEGER NOT NULL DEFAULT 1 CHECK (type IN (1, 2)),
    -- GLPI numeric (1..6)
    priority INTEGER NOT NULL DEFAULT 3 CHECK (priority BETWEEN 1 AND 6),
    priority_label VARCHAR(20) DEFAULT 'Medium',
    criticality VARCHAR(20) DEFAULT 'moyenne'
        CHECK (criticality IN ('très basse', 'basse', 'moyenne', 'haute', 'très haute')),
    -- Legacy status (fr)
    status VARCHAR(20) DEFAULT 'nouveau'
        CHECK (status IN ('nouveau', 'en_cours', 'resolu', 'clos')),
    status_label VARCHAR(30) DEFAULT 'Open',
    category_id INTEGER REFERENCES categories(id),
    category VARCHAR(100),          -- redundant text label for fast reads
    user_name VARCHAR(200),
    user_email VARCHAR(200),
    conversation_id INTEGER REFERENCES conversations(id),
    -- Assignment (denormalized for quick reads)
    assigned_to_id INTEGER REFERENCES technicians(id) ON DELETE SET NULL,
    assigned_to_name VARCHAR(200),
    assigned_to_email VARCHAR(200),
    assigned_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    solved_at TIMESTAMP WITH TIME ZONE,
    resolved_at TIMESTAMP WITH TIME ZONE,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- ── Messages de conversation ─────────────────────────────────
CREATE TABLE IF NOT EXISTS messages (
    id SERIAL PRIMARY KEY,
    conversation_id INTEGER NOT NULL REFERENCES conversations(id) ON DELETE CASCADE,
    role VARCHAR(20) NOT NULL CHECK (role IN ('user', 'assistant', 'system')),
    content TEXT NOT NULL,
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- ── Messages échangés SUR un ticket (comments) ───────────────
CREATE TABLE IF NOT EXISTS ticket_messages (
    id SERIAL PRIMARY KEY,
    ticket_id INTEGER NOT NULL REFERENCES tickets(id) ON DELETE CASCADE,
    sender_role VARCHAR(30) NOT NULL,    -- 'user', 'technician', 'system'
    sender_name VARCHAR(200),
    content TEXT NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- ── Historique des modifications d'un ticket ─────────────────
CREATE TABLE IF NOT EXISTS ticket_history (
    id SERIAL PRIMARY KEY,
    ticket_id INTEGER NOT NULL REFERENCES tickets(id) ON DELETE CASCADE,
    field_name VARCHAR(100) NOT NULL,
    old_value TEXT,
    new_value TEXT,
    changed_by VARCHAR(200),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- ── Audit trail des assignations ─────────────────────────────
CREATE TABLE IF NOT EXISTS ticket_assignments (
    id SERIAL PRIMARY KEY,
    ticket_id INTEGER NOT NULL REFERENCES tickets(id) ON DELETE CASCADE,
    technician_id INTEGER REFERENCES technicians(id) ON DELETE SET NULL,
    assigned_by VARCHAR(200),
    reason TEXT,
    assigned_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- ── Brouillons d'e-mail ──────────────────────────────────────
CREATE TABLE IF NOT EXISTS email_drafts (
    id SERIAL PRIMARY KEY,
    ticket_id INTEGER REFERENCES tickets(id),
    conversation_id INTEGER REFERENCES conversations(id),
    recipient_email VARCHAR(200) NOT NULL,
    subject VARCHAR(500) NOT NULL,
    body TEXT NOT NULL,
    status VARCHAR(20) DEFAULT 'draft' CHECK (status IN ('draft', 'sent')),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    sent_at TIMESTAMP WITH TIME ZONE
);

-- ── Index ────────────────────────────────────────────────────
CREATE INDEX IF NOT EXISTS idx_tickets_status         ON tickets(status);
CREATE INDEX IF NOT EXISTS idx_tickets_user_email     ON tickets(user_email);
CREATE INDEX IF NOT EXISTS idx_tickets_category       ON tickets(category_id);
CREATE INDEX IF NOT EXISTS idx_tickets_assigned       ON tickets(assigned_to_id, status);
CREATE INDEX IF NOT EXISTS idx_messages_conversation  ON messages(conversation_id);
CREATE INDEX IF NOT EXISTS idx_conversations_status   ON conversations(status);
CREATE INDEX IF NOT EXISTS idx_email_drafts_ticket    ON email_drafts(ticket_id);
CREATE INDEX IF NOT EXISTS idx_email_drafts_status    ON email_drafts(status);
CREATE INDEX IF NOT EXISTS idx_ticket_messages_ticket ON ticket_messages(ticket_id);
CREATE INDEX IF NOT EXISTS idx_ticket_history_ticket  ON ticket_history(ticket_id);
CREATE INDEX IF NOT EXISTS idx_ticket_assign_ticket   ON ticket_assignments(ticket_id);