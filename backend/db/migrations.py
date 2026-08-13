import logging

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine

logger = logging.getLogger(__name__)


async def apply_migrations(engine: AsyncEngine) -> None:
    """Applique des migrations légères au démarrage sans dépendre d'un framework dédié."""
    statements = [
        """
        ALTER TABLE tickets ADD COLUMN IF NOT EXISTS description TEXT;
        """,
        """
        ALTER TABLE tickets ADD COLUMN IF NOT EXISTS category VARCHAR(100);
        """,
        """
        ALTER TABLE tickets ADD COLUMN IF NOT EXISTS priority_label VARCHAR(20) DEFAULT 'Medium';
        """,
        """
        ALTER TABLE tickets ADD COLUMN IF NOT EXISTS status_label VARCHAR(30) DEFAULT 'Open';
        """,
        """
        ALTER TABLE tickets ADD COLUMN IF NOT EXISTS summary TEXT;
        """,
        """
        ALTER TABLE tickets ADD COLUMN IF NOT EXISTS resolved_at TIMESTAMP WITH TIME ZONE;
        """,
        """
        ALTER TABLE tickets ADD COLUMN IF NOT EXISTS assigned_to_id INTEGER;
        """,
        """
        ALTER TABLE tickets ADD COLUMN IF NOT EXISTS assigned_to_name VARCHAR(200);
        """,
        """
        ALTER TABLE tickets ADD COLUMN IF NOT EXISTS assigned_to_email VARCHAR(200);
        """,
        """
        ALTER TABLE tickets ADD COLUMN IF NOT EXISTS assigned_at TIMESTAMP WITH TIME ZONE;
        """,
        """
        CREATE TABLE IF NOT EXISTS technicians (
            id SERIAL PRIMARY KEY,
            full_name VARCHAR(200) NOT NULL,
            email VARCHAR(200) NOT NULL UNIQUE,
            role VARCHAR(200),
            team VARCHAR(100),
            category_id INTEGER REFERENCES categories(id),
            active BOOLEAN DEFAULT true,
            created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
        );
        """,
        """
        CREATE TABLE IF NOT EXISTS ticket_assignments (
            id SERIAL PRIMARY KEY,
            ticket_id INTEGER NOT NULL REFERENCES tickets(id) ON DELETE CASCADE,
            technician_id INTEGER NOT NULL REFERENCES technicians(id),
            assigned_by VARCHAR(200),
            reason TEXT,
            assigned_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
        );
        """,
        """
        CREATE TABLE IF NOT EXISTS ticket_messages (
            id SERIAL PRIMARY KEY,
            ticket_id INTEGER NOT NULL REFERENCES tickets(id) ON DELETE CASCADE,
            sender_role VARCHAR(20) NOT NULL,
            sender_name VARCHAR(200),
            content TEXT NOT NULL,
            created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
        );
        """,
        """
        CREATE TABLE IF NOT EXISTS ticket_history (
            id SERIAL PRIMARY KEY,
            ticket_id INTEGER NOT NULL REFERENCES tickets(id) ON DELETE CASCADE,
            field_name VARCHAR(100) NOT NULL,
            old_value TEXT,
            new_value TEXT,
            changed_by VARCHAR(200),
            created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
        );
        """,
        """
        CREATE TABLE IF NOT EXISTS app_settings (
            id INTEGER PRIMARY KEY DEFAULT 1,
            data JSONB NOT NULL DEFAULT '{}'::jsonb,
            updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
        );
        """,
        """
        INSERT INTO app_settings (id, data)
        VALUES (1, '{
            "general": {"chatbot_name": "AUTOHALL Helpdesk", "language": "fr"},
            "appearance": {"theme": "system"},
            "chat": {"temperature": 0.3, "max_tokens": 2048, "streaming": true, "memory": true, "history": true, "sources": true},
            "llm": {"primary_provider": "ollama", "fallback_1": "groq", "fallback_2": "gemini", "enable_fallback": true},
            "notifications": {"tickets": true, "status_changes": true, "errors": true, "system_events": true}
        }'::jsonb)
        ON CONFLICT (id) DO NOTHING;
        """,
        """
        CREATE TABLE IF NOT EXISTS chat_feedback (
            id SERIAL PRIMARY KEY,
            conversation_id INTEGER REFERENCES conversations(id) ON DELETE SET NULL,
            message_id VARCHAR(100),
            rating SMALLINT NOT NULL CHECK (rating IN (-1, 0, 1)),
            comment TEXT,
            created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
        );
        """,
    ]

    async with engine.begin() as conn:
        for statement in statements:
            await conn.execute(text(statement))

        # ✅ FIX: qualify all column references with `tickets.` to resolve
        # the ambiguity with `categories.description` introduced by the FROM join.
        await conn.execute(
            text(
                """
                UPDATE tickets
                SET
                    description = COALESCE(tickets.description, tickets.content),
                    category = COALESCE(tickets.category, c.name),
                    priority_label = COALESCE(tickets.priority_label,
                        CASE
                            WHEN tickets.priority <= 1 THEN 'Urgent'
                            WHEN tickets.priority = 2 THEN 'High'
                            WHEN tickets.priority = 3 THEN 'Medium'
                            ELSE 'Low'
                        END
                    ),
                    status_label = COALESCE(tickets.status_label,
                        CASE tickets.status
                            WHEN 'nouveau' THEN 'Open'
                            WHEN 'en_cours' THEN 'In Progress'
                            WHEN 'resolu' THEN 'Resolved'
                            WHEN 'clos' THEN 'Closed'
                            ELSE 'Open'
                        END
                    ),
                    resolved_at = COALESCE(tickets.resolved_at, tickets.solved_at)
                FROM categories c
                WHERE tickets.category_id = c.id;
                """
            )
        )
        await conn.execute(
            text(
                """
                UPDATE tickets
                SET description = COALESCE(tickets.description, tickets.content)
                WHERE tickets.description IS NULL;
                """
            )
        )
        await conn.execute(
            text(
                """
                INSERT INTO technicians (full_name, email, role, team, category_id, active)
                VALUES
                    ('Amine Zinoun', 'amine.zinoun@autohall.ma', 'Responsable support Wincar', 'Wincar', (SELECT id FROM categories WHERE name = 'Wincar'), true),
                    ('Sofia El Idrissi', 'sofia.elidrissi@autohall.ma', 'Support messagerie / Outlook', 'Messagerie', (SELECT id FROM categories WHERE name = 'Messagerie'), true),
                    ('Youssef Bensaid', 'youssef.bensaid@autohall.ma', 'Support Citrix / virtualisation', 'Citrix', (SELECT id FROM categories WHERE name = 'Citrix'), true),
                    ('Nabil Cherkaoui', 'nabil.cherkaoui@autohall.ma', 'Support matériel et périphériques', 'Matériel', (SELECT id FROM categories WHERE name = 'Matériel'), true),
                    ('Hassan Rami', 'hassan.rami@autohall.ma', 'Support accès internet / réseau', 'Internet', (SELECT id FROM categories WHERE name = 'Internet'), true),
                    ('Karim Tazi', 'karim.tazi@autohall.ma', 'Support logiciels système', 'Logiciel Système', (SELECT id FROM categories WHERE name = 'Logiciel Système'), true),
                    ('Leila Mounir', 'leila.mounir@autohall.ma', 'Support Sage / comptabilité', 'Sage', (SELECT id FROM categories WHERE name = 'Sage'), true),
                    ('Omar Fassi', 'omar.fassi@autohall.ma', 'Support Windows / postes', 'Windows', (SELECT id FROM categories WHERE name = 'Windows'), true),
                    ('Reda Najmi', 'reda.najmi@autohall.ma', 'Support APPCC / conformité', 'APPCC', (SELECT id FROM categories WHERE name = 'APPCC'), true),
                    ('Zakaria Benali', 'zakaria.benali@autohall.ma', 'Support réseau / Wi-Fi / switches', 'Réseau', (SELECT id FROM categories WHERE name = 'Réseau'), true),
                    ('Mehdi Essalhi', 'mehdi.essalhi@autohall.ma', 'Support outillages SAV / diagnostics', 'Outillages SAV', (SELECT id FROM categories WHERE name = 'Outillages SAV'), true),
                    ('Salma Karim', 'salma.karim@autohall.ma', 'Support GestorNet / workflow', 'GestorNet', (SELECT id FROM categories WHERE name = 'GestorNet'), true),
                    ('Mohamed Aouad', 'mohamed.aouad@autohall.ma', 'Support CRM / données clients', 'CRM', (SELECT id FROM categories WHERE name = 'CRM'), true),
                    ('Ilyas Oulhaj', 'ilyas.oulhaj@autohall.ma', 'Support Auto Naps / planification atelier', 'Auto Naps', (SELECT id FROM categories WHERE name = 'Auto Naps'), true),
                    ('Anas Choukri', 'anas.choukri@autohall.ma', 'Support téléphonie IP / postes', 'Poste IP Phone', (SELECT id FROM categories WHERE name = 'Poste IP Phone'), true),
                    ('Sara Bourou', 'sara.bourou@autohall.ma', 'Support reporting / BI', 'Reporting', (SELECT id FROM categories WHERE name = 'Reporting'), true),
                    ('Samir Lahmadi', 'samir.lahmadi@autohall.ma', 'Support VPN / accès distant', 'Ligne VPN', (SELECT id FROM categories WHERE name = 'Ligne VPN'), true),
                    ('Fouad Lahlou', 'fouad.lahlou@autohall.ma', 'Support consommables / matériel de bureau', 'Consommable', (SELECT id FROM categories WHERE name = 'Consommable'), true),
                    ('Mounir Sefrioui', 'mounir.sefrioui@autohall.ma', 'Support lignes téléphoniques', 'Ligne Téléphonique', (SELECT id FROM categories WHERE name = 'Ligne Téléphonique'), true),
                    ('Yacine Debbagh', 'yacine.debbagh@autohall.ma', 'Support GSM / smartphones', 'GSM', (SELECT id FROM categories WHERE name = 'GSM'), true),
                    ('Hicham Regragui', 'hicham.regragui@autohall.ma', 'Support Moovapps / GED', 'Moovapps', (SELECT id FROM categories WHERE name = 'Moovapps'), true),
                    ('Nadia El Yacoubi', 'nadia.elyacoubi@autohall.ma', 'Support PayRoll / paie', 'PayRoll', (SELECT id FROM categories WHERE name = 'PayRoll'), true),
                    ('Imane Zaki', 'imane.zaki@autohall.ma', 'Support SRM / achats fournisseurs', 'SRM', (SELECT id FROM categories WHERE name = 'SRM'), true)
                ON CONFLICT (email) DO NOTHING;
                """
            )
        )
        await conn.execute(
            text(
                """
                UPDATE app_settings
                SET updated_at = NOW()
                WHERE id = 1;
                """
            )
        )