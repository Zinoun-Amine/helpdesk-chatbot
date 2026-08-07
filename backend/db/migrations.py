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

        await conn.execute(
            text(
                """
                UPDATE tickets
                SET
                    description = COALESCE(description, content),
                    category = COALESCE(category, c.name),
                    priority_label = COALESCE(priority_label,
                        CASE
                            WHEN priority <= 1 THEN 'Urgent'
                            WHEN priority = 2 THEN 'High'
                            WHEN priority = 3 THEN 'Medium'
                            ELSE 'Low'
                        END
                    ),
                    status_label = COALESCE(status_label,
                        CASE status
                            WHEN 'nouveau' THEN 'Open'
                            WHEN 'en_cours' THEN 'In Progress'
                            WHEN 'resolu' THEN 'Resolved'
                            WHEN 'clos' THEN 'Closed'
                            ELSE 'Open'
                        END
                    ),
                    resolved_at = COALESCE(resolved_at, solved_at)
                FROM categories c
                WHERE tickets.category_id = c.id;
                """
            )
        )
        await conn.execute(
            text(
                """
                UPDATE tickets
                SET description = COALESCE(description, content)
                WHERE description IS NULL;
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
