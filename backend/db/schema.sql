-- ============================================================
-- Schéma PostgreSQL — Chatbot AUTOHALL Helpdesk
-- Tables : categories, tickets, conversations, messages, email_drafts
-- ============================================================

-- Extension pour UUID si nécessaire
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- ── Table des catégories ITIL ────────────────────────────────
CREATE TABLE categories (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL UNIQUE,
    description TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- ── Table des conversations ──────────────────────────────────
CREATE TABLE conversations (
    id SERIAL PRIMARY KEY,
    user_name VARCHAR(200),
    user_email VARCHAR(200),
    -- État de la conversation dans le flux guidé
    current_state VARCHAR(50) DEFAULT 'accueil',
    -- Données de qualification accumulées (JSON)
    qualification_data JSONB DEFAULT '{}',
    status VARCHAR(20) DEFAULT 'active'
        CHECK (status IN ('active', 'closed')),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- ── Table des tickets (simulateur GLPI) ──────────────────────
CREATE TABLE tickets (
    id SERIAL PRIMARY KEY,
    title VARCHAR(500) NOT NULL,
    content TEXT NOT NULL,
    -- 1 = Incident, 2 = Demande
    type INTEGER NOT NULL CHECK (type IN (1, 2)),
    -- Échelle GLPI de 1 à 6
    priority INTEGER NOT NULL DEFAULT 3
        CHECK (priority BETWEEN 1 AND 6),
    -- Criticité textuelle
    criticality VARCHAR(20) DEFAULT 'moyenne'
        CHECK (criticality IN ('très basse', 'basse', 'moyenne', 'haute', 'très haute')),
    -- Statut du ticket
    status VARCHAR(20) DEFAULT 'nouveau'
        CHECK (status IN ('nouveau', 'en_cours', 'resolu', 'clos')),
    category_id INTEGER REFERENCES categories(id),
    -- Informations utilisateur
    user_name VARCHAR(200),
    user_email VARCHAR(200),
    -- Lien avec la conversation
    conversation_id INTEGER REFERENCES conversations(id),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    solved_at TIMESTAMP WITH TIME ZONE,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- ── Table des messages (historique de chat) ───────────────────
CREATE TABLE messages (
    id SERIAL PRIMARY KEY,
    conversation_id INTEGER NOT NULL REFERENCES conversations(id)
        ON DELETE CASCADE,
    role VARCHAR(20) NOT NULL
        CHECK (role IN ('user', 'assistant', 'system')),
    content TEXT NOT NULL,
    -- Métadonnées : classification, actions déclenchées, etc.
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- ── Table des brouillons d'e-mail ─────────────────────────────
CREATE TABLE email_drafts (
    id SERIAL PRIMARY KEY,
    ticket_id INTEGER REFERENCES tickets(id),
    conversation_id INTEGER REFERENCES conversations(id),
    recipient_email VARCHAR(200) NOT NULL,
    subject VARCHAR(500) NOT NULL,
    body TEXT NOT NULL,
    -- Jamais envoyé automatiquement : toujours 'draft' d'abord
    status VARCHAR(20) DEFAULT 'draft'
        CHECK (status IN ('draft', 'sent')),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    sent_at TIMESTAMP WITH TIME ZONE
);

-- ── Index pour les requêtes fréquentes ───────────────────────
CREATE INDEX idx_tickets_status ON tickets(status);
CREATE INDEX idx_tickets_user_email ON tickets(user_email);
CREATE INDEX idx_tickets_category ON tickets(category_id);
CREATE INDEX idx_messages_conversation ON messages(conversation_id);
CREATE INDEX idx_conversations_status ON conversations(status);
CREATE INDEX idx_email_drafts_ticket ON email_drafts(ticket_id);
CREATE INDEX idx_email_drafts_status ON email_drafts(status);
