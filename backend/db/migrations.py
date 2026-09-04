import logging

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine
from core.security import hash_password
from config import settings

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
        INSERT INTO categories (name, description) VALUES
            ('RIAPP', 'Application RIAPP'),
            ('Qalitel Doc', 'Plateforme Qalitel Doc'),
            ('GDoc', 'Application GDoc'),
            ('Contrat de Vente', 'Gestion des contrats de vente'),
            ('Sage Paie & RH', 'Sage paie et ressources humaines'),
            ('Microsoft Teams', 'Collaboration et visioconférence Microsoft Teams'),
            ('WebEX', 'Visioconférence WebEX'),
            ('GENERAFI', 'Application GENERAFI'),
            ('Site Web', 'Site web AUTOHALL'),
            ('AppGCMA', 'Application AppGCMA'),
            ('VPN_FortiClient', 'Client VPN FortiClient'),
            ('Fidélisation', 'Application de fidélisation'),
            ('Optimmo', 'Application Optimmo'),
            ('SMS', 'Services SMS'),
            ('Qalitel Compar', 'Application Qalitel Compar'),
            ('Antivirus', 'Protection antivirus'),
            ('SLV', 'Application SLV'),
            ('VOXCO', 'Application VOXCO'),
            ('Intranet', 'Intranet AUTOHALL'),
            ('Devopps', 'Outils Devopps'),
            ('C.Conformité', 'Application C.Conformité'),
            ('eSeller', 'Application eSeller'),
            ('TPE', 'Terminaux de paiement électronique'),
            ('OPEL', 'Applications et outils OPEL')
        ON CONFLICT (name) DO NOTHING;
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
        """
        CREATE TABLE IF NOT EXISTS users (
            id SERIAL PRIMARY KEY,
            email VARCHAR(255) UNIQUE NOT NULL,
            full_name VARCHAR(255) NOT NULL,
            hashed_password TEXT NOT NULL,
            role VARCHAR(32) NOT NULL DEFAULT 'user',
            is_active BOOLEAN NOT NULL DEFAULT TRUE,
            created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
            updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
        );
        """,
        """
        CREATE INDEX IF NOT EXISTS idx_users_email ON users (email);
        """,
    ]

    async with engine.begin() as conn:
        for statement in statements:
            await conn.execute(text(statement))

        technician_password_hash = hash_password(settings.TECHNICIAN_DEFAULT_PASSWORD)
        await conn.execute(
            text(
                """
                INSERT INTO users (email, full_name, hashed_password, role, is_active)
                SELECT email, full_name, :password_hash, 'technician', active
                FROM technicians
                WHERE email IN (
                    'amine.spk.zinoun@gmail.com',
                    'sofia.elidrissi@autohall.ma',
                    'youssef.bensaid@autohall.ma',
                    'nabil.cherkaoui@autohall.ma'
                )
                ON CONFLICT (email) DO UPDATE
                SET full_name = EXCLUDED.full_name,
                    role = 'technician',
                    is_active = EXCLUDED.is_active;
                """
            ),
            {"password_hash": technician_password_hash},
        )

        technician_password_hash = hash_password(settings.TECHNICIAN_DEFAULT_PASSWORD)
        await conn.execute(
            text(
                """
                INSERT INTO users (email, full_name, hashed_password, role, is_active)
                SELECT email, full_name, :password_hash, 'technician', active
                FROM technicians
                WHERE email IN (
                    'amine.spk.zinoun@gmail.com',
                    'sofia.elidrissi@autohall.ma',
                    'youssef.bensaid@autohall.ma',
                    'nabil.cherkaoui@autohall.ma'
                )
                ON CONFLICT (email) DO UPDATE
                SET full_name = EXCLUDED.full_name,
                    role = 'technician',
                    is_active = EXCLUDED.is_active;
                """
            ),
            {"password_hash": technician_password_hash},
        )

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

        # ⚠️ DELETE and INSERT are now separate calls – this prevents asyncpg error
        await conn.execute(
            text(
                """
                DELETE FROM technicians
                WHERE email IN (
                    'support.riapp@autohall.ma', 'support.qalitel-doc@autohall.ma',
                    'support.gdoc@autohall.ma', 'support.contrat-vente@autohall.ma',
                    'support.sage-paie-rh@autohall.ma', 'support.microsoft-teams@autohall.ma',
                    'support.webex@autohall.ma', 'support.generafi@autohall.ma',
                    'support.site-web@autohall.ma', 'support.appgcma@autohall.ma',
                    'support.vpn-forticlient@autohall.ma', 'support.fidelisation@autohall.ma',
                    'support.optimmo@autohall.ma', 'support.sms@autohall.ma',
                    'support.qalitel-compar@autohall.ma', 'support.antivirus@autohall.ma',
                    'support.slv@autohall.ma', 'support.voxco@autohall.ma',
                    'support.intranet@autohall.ma', 'support.devopps@autohall.ma',
                    'support.conformite@autohall.ma', 'support.eseller@autohall.ma',
                    'support.tpe@autohall.ma', 'support.opel@autohall.ma'
                );
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
                    ('Imane Zaki', 'imane.zaki@autohall.ma', 'Support SRM / achats fournisseurs', 'SRM', (SELECT id FROM categories WHERE name = 'SRM'), true),
                    ('Hamza El Mansouri', 'hamza.elmansouri@autohall.ma', 'Support RIAPP', 'RIAPP', (SELECT id FROM categories WHERE name = 'RIAPP'), true),
                    ('Imane Berrada', 'imane.berrada@autohall.ma', 'Support Qalitel Doc', 'Qalitel Doc', (SELECT id FROM categories WHERE name = 'Qalitel Doc'), true),
                    ('Rachid Alaoui', 'rachid.alaoui@autohall.ma', 'Support GDoc', 'GDoc', (SELECT id FROM categories WHERE name = 'GDoc'), true),
                    ('Salma Bennani', 'salma.bennani@autohall.ma', 'Support contrats de vente', 'Contrat de Vente', (SELECT id FROM categories WHERE name = 'Contrat de Vente'), true),
                    ('Adil Chafik', 'adil.chafik@autohall.ma', 'Support Sage Paie et RH', 'Sage Paie & RH', (SELECT id FROM categories WHERE name = 'Sage Paie & RH'), true),
                    ('Oumaima El Fassi', 'oumaima.elfassi@autohall.ma', 'Support Microsoft Teams', 'Microsoft Teams', (SELECT id FROM categories WHERE name = 'Microsoft Teams'), true),
                    ('Bilal Amrani', 'bilal.amrani@autohall.ma', 'Support WebEX', 'WebEX', (SELECT id FROM categories WHERE name = 'WebEX'), true),
                    ('Hajar Naciri', 'hajar.naciri@autohall.ma', 'Support GENERAFI', 'GENERAFI', (SELECT id FROM categories WHERE name = 'GENERAFI'), true),
                    ('Ayoub Tazi', 'ayoub.tazi@autohall.ma', 'Support site web', 'Site Web', (SELECT id FROM categories WHERE name = 'Site Web'), true),
                    ('Wiam El Khatib', 'wiam.elkhatib@autohall.ma', 'Support AppGCMA', 'AppGCMA', (SELECT id FROM categories WHERE name = 'AppGCMA'), true),
                    ('Ismail Rahmani', 'ismail.rahmani@autohall.ma', 'Support VPN FortiClient', 'VPN_FortiClient', (SELECT id FROM categories WHERE name = 'VPN_FortiClient'), true),
                    ('Mariam Zahir', 'mariam.zahir@autohall.ma', 'Support fidélisation', 'Fidélisation', (SELECT id FROM categories WHERE name = 'Fidélisation'), true),
                    ('Soufiane Idrissi', 'soufiane.idrissi@autohall.ma', 'Support Optimmo', 'Optimmo', (SELECT id FROM categories WHERE name = 'Optimmo'), true),
                    ('Chaimae Ait Lahcen', 'chaimae.aitlahcen@autohall.ma', 'Support SMS', 'SMS', (SELECT id FROM categories WHERE name = 'SMS'), true),
                    ('Yassine El Ouardi', 'yassine.elouardi@autohall.ma', 'Support Qalitel Compar', 'Qalitel Compar', (SELECT id FROM categories WHERE name = 'Qalitel Compar'), true),
                    ('Hind Bennis', 'hind.bennis@autohall.ma', 'Support antivirus', 'Antivirus', (SELECT id FROM categories WHERE name = 'Antivirus'), true),
                    ('Noura El Kadi', 'noura.elkadi@autohall.ma', 'Support SLV', 'SLV', (SELECT id FROM categories WHERE name = 'SLV'), true),
                    ('Mehdi Rahal', 'mehdi.rahal@autohall.ma', 'Support VOXCO', 'VOXCO', (SELECT id FROM categories WHERE name = 'VOXCO'), true),
                    ('Kawtar Benjelloun', 'kawtar.benjelloun@autohall.ma', 'Support intranet', 'Intranet', (SELECT id FROM categories WHERE name = 'Intranet'), true),
                    ('Anass El Ghazali', 'anass.elghazali@autohall.ma', 'Support Devopps', 'Devopps', (SELECT id FROM categories WHERE name = 'Devopps'), true),
                    ('Siham Lahlou', 'siham.lahlou@autohall.ma', 'Support conformité', 'C.Conformité', (SELECT id FROM categories WHERE name = 'C.Conformité'), true),
                    ('Zakaria El Haddad', 'zakaria.elhaddad@autohall.ma', 'Support eSeller', 'eSeller', (SELECT id FROM categories WHERE name = 'eSeller'), true),
                    ('Amina Bouazza', 'amina.bouazza@autohall.ma', 'Support terminaux de paiement', 'TPE', (SELECT id FROM categories WHERE name = 'TPE'), true),
                    ('Tarik Azzouzi', 'tarik.azzouzi@autohall.ma', 'Support OPEL', 'OPEL', (SELECT id FROM categories WHERE name = 'OPEL'), true)
                ON CONFLICT (email) DO NOTHING;
                """
            )
        )

        await conn.execute(
            text(
                """
                INSERT INTO technicians (full_name, email, role, team, category_id, active)
                VALUES
                    ('Amine Zinoun', 'amine.spk.zinoun@gmail.com', 'Support IT', 'AUTOHALL IT', NULL, true),
                    ('Sofia El Idrissi', 'sofia.elidrissi@autohall.ma', 'Support IT', 'AUTOHALL IT', NULL, true),
                    ('Youssef Bensaid', 'youssef.bensaid@autohall.ma', 'Support IT', 'AUTOHALL IT', NULL, true),
                    ('Nabil Cherkaoui', 'nabil.cherkaoui@autohall.ma', 'Support IT', 'AUTOHALL IT', NULL, true)
                ON CONFLICT (email) DO UPDATE
                SET full_name = EXCLUDED.full_name,
                    role = EXCLUDED.role,
                    team = EXCLUDED.team,
                    active = TRUE;
                """
            )
        )
        await conn.execute(
            text(
                """
                UPDATE tickets
                SET assigned_to_id = CASE
                        WHEN category IN ('Wincar', 'Windows', 'GestorNet', 'Consommable', 'Moovapps', 'Contrat de Vente', 'GENERAFI', 'Fidélisation', 'SMS', 'VOXCO', 'TPE')
                            THEN (SELECT id FROM technicians WHERE email = 'amine.spk.zinoun@gmail.com')
                        WHEN category IN ('Citrix', 'Logiciel Système', 'Réseau', 'CRM', 'Ligne VPN', 'RIAPP', 'Qalitel Doc', 'Microsoft Teams', 'VPN_FortiClient', 'Antivirus', 'Intranet', 'eSeller')
                            THEN (SELECT id FROM technicians WHERE email = 'sofia.elidrissi@autohall.ma')
                        WHEN category IN ('Matériel', 'Internet', 'APPCC', 'Poste IP Phone', 'Reporting', 'PayRoll', 'GDoc', 'Site Web', 'Optimmo', 'Qalitel Compar', 'SLV', 'C.Conformité')
                            THEN (SELECT id FROM technicians WHERE email = 'youssef.bensaid@autohall.ma')
                        WHEN category IN ('Messagerie', 'Sage', 'Outillages SAV', 'Auto Naps', 'Ligne Téléphonique', 'GSM', 'Sage Paie & RH', 'WebEX', 'AppGCMA', 'SRM', 'Devopps', 'OPEL')
                            THEN (SELECT id FROM technicians WHERE email = 'nabil.cherkaoui@autohall.ma')
                        ELSE assigned_to_id
                    END,
                    assigned_to_name = CASE
                        WHEN category IN ('Wincar', 'Windows', 'GestorNet', 'Consommable', 'Moovapps', 'Contrat de Vente', 'GENERAFI', 'Fidélisation', 'SMS', 'VOXCO', 'TPE') THEN 'Amine Zinoun'
                        WHEN category IN ('Citrix', 'Logiciel Système', 'Réseau', 'CRM', 'Ligne VPN', 'RIAPP', 'Qalitel Doc', 'Microsoft Teams', 'VPN_FortiClient', 'Antivirus', 'Intranet', 'eSeller') THEN 'Sofia El Idrissi'
                        WHEN category IN ('Matériel', 'Internet', 'APPCC', 'Poste IP Phone', 'Reporting', 'PayRoll', 'GDoc', 'Site Web', 'Optimmo', 'Qalitel Compar', 'SLV', 'C.Conformité') THEN 'Youssef Bensaid'
                        WHEN category IN ('Messagerie', 'Sage', 'Outillages SAV', 'Auto Naps', 'Ligne Téléphonique', 'GSM', 'Sage Paie & RH', 'WebEX', 'AppGCMA', 'SRM', 'Devopps', 'OPEL') THEN 'Nabil Cherkaoui'
                        ELSE assigned_to_name
                    END,
                    assigned_to_email = CASE
                        WHEN category IN ('Wincar', 'Windows', 'GestorNet', 'Consommable', 'Moovapps', 'Contrat de Vente', 'GENERAFI', 'Fidélisation', 'SMS', 'VOXCO', 'TPE') THEN 'amine.spk.zinoun@gmail.com'
                        WHEN category IN ('Citrix', 'Logiciel Système', 'Réseau', 'CRM', 'Ligne VPN', 'RIAPP', 'Qalitel Doc', 'Microsoft Teams', 'VPN_FortiClient', 'Antivirus', 'Intranet', 'eSeller') THEN 'sofia.elidrissi@autohall.ma'
                        WHEN category IN ('Matériel', 'Internet', 'APPCC', 'Poste IP Phone', 'Reporting', 'PayRoll', 'GDoc', 'Site Web', 'Optimmo', 'Qalitel Compar', 'SLV', 'C.Conformité') THEN 'youssef.bensaid@autohall.ma'
                        WHEN category IN ('Messagerie', 'Sage', 'Outillages SAV', 'Auto Naps', 'Ligne Téléphonique', 'GSM', 'Sage Paie & RH', 'WebEX', 'AppGCMA', 'SRM', 'Devopps', 'OPEL') THEN 'nabil.cherkaoui@autohall.ma'
                        ELSE assigned_to_email
                    END;
                """
            )
        )
        await conn.execute(
            text(
                """
                UPDATE ticket_assignments assignments
                SET technician_id = tickets.assigned_to_id
                FROM tickets
                WHERE assignments.ticket_id = tickets.id
                  AND tickets.assigned_to_id IS NOT NULL;
                """
            )
        )
        await conn.execute(
            text(
                """
                DELETE FROM technicians
                WHERE email NOT IN (
                    'amine.spk.zinoun@gmail.com',
                    'sofia.elidrissi@autohall.ma',
                    'youssef.bensaid@autohall.ma',
                    'nabil.cherkaoui@autohall.ma'
                );
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