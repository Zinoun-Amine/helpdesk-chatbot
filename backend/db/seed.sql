
-- ── 1) Catégories
INSERT INTO categories (name, description) VALUES
    ('Wincar', 'Logiciel de gestion automobile Wincar — facturation, stock, commandes'),
    ('Messagerie', 'Messagerie électronique — Outlook, Exchange, configuration email'),
    ('Citrix', 'Environnement Citrix — sessions distantes, connexions, performances'),
    ('Matériel', 'Matériel informatique — postes, écrans, périphériques, imprimantes'),
    ('Internet', 'Connexion Internet — accès web, navigation, proxy, pare-feu'),
    ('Logiciel Système', 'Logiciels système — installations, mises à jour, licences'),
    ('Sage', 'Suite Sage — comptabilité, paie, gestion commerciale'),
    ('Windows', 'Système Windows — authentification, profils, mises à jour OS'),
    ('APPCC', 'Application APPCC — contrôle qualité, conformité alimentaire'),
    ('Réseau', 'Infrastructure réseau — switches, câblage, Wi-Fi, DHCP, DNS'),
    ('Outillages SAV', 'Outils de diagnostic SAV — logiciels techniques, licences'),
    ('GestorNet', 'Application GestorNet — gestion des flux documentaires'),
    ('CRM', 'CRM — gestion relation client, synchronisation données'),
    ('Auto Naps', 'Application Auto Naps — planification atelier automobile'),
    ('Poste IP Phone', 'Téléphonie IP — postes, configuration SIP, problèmes audio'),
    ('Reporting', 'Outils de reporting — tableaux de bord, rapports, BI'),
    ('Ligne VPN', 'VPN — connexions site-à-site, accès distant sécurisé'),
    ('Consommable', 'Consommables IT — toners, câbles, accessoires'),
    ('Ligne Téléphonique', 'Lignes téléphoniques fixes — abonnements, pannes opérateur'),
    ('GSM', 'Téléphonie mobile — smartphones, forfaits, MDM'),
    ('Moovapps', 'Plateforme Moovapps — workflows, formulaires, GED'),
    ('PayRoll', 'Logiciel de paie PayRoll — bulletins, déclarations sociales'),
    ('SRM', 'SRM — gestion des relations fournisseurs, achats'),
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

-- ── 2) Techniciens (4 responsables avec catégories équilibrées) ──
INSERT INTO technicians (full_name, email, role, team, category_id, active) VALUES
    ('Amine Zinoun', 'amine.spk.zinoun@gmail.com', 'Support IT', 'AUTOHALL IT', NULL, TRUE),
    ('Sofia El Idrissi', 'sofia.elidrissi@autohall.ma', 'Support IT', 'AUTOHALL IT', NULL, TRUE),
    ('Youssef Bensaid', 'youssef.bensaid@autohall.ma', 'Support IT', 'AUTOHALL IT', NULL, TRUE),
    ('Nabil Cherkaoui', 'nabil.cherkaoui@autohall.ma', 'Support IT', 'AUTOHALL IT', NULL, TRUE)
ON CONFLICT (email) DO NOTHING;

-- ── 3) Conversations fictives ────────────────────────────────
INSERT INTO conversations (id, user_name, user_email, current_state, status) VALUES
    (1, 'Amine Rachidi',      'amine.rachidi@exemple.com',      'closed', 'closed'),
    (2, 'Fatima Benali',      'fatima.benali@exemple.com',      'closed', 'closed'),
    (3, 'Youssef El Amrani',  'youssef.elamrani@exemple.com',   'closed', 'closed')
ON CONFLICT (id) DO NOTHING;

-- Mettre à jour la séquence
SELECT setval('conversations_id_seq', 3, true);

-- ── 4) Tickets fictifs (avec auto-assignation par catégorie) ─
INSERT INTO tickets (
    id, title, content, description, type, priority, priority_label,
    criticality, status, status_label, category_id, category,
    user_name, user_email, conversation_id,
    assigned_to_id, assigned_to_name, assigned_to_email, assigned_at,
    created_at
) VALUES
    (1, 'Impossible de lancer Wincar après mise à jour',
        'Depuis la mise à jour de ce matin, Wincar affiche une erreur "Module facturation introuvable" au démarrage. Impossible de créer des factures.',
        'Depuis la mise à jour de ce matin, Wincar affiche une erreur "Module facturation introuvable" au démarrage. Impossible de créer des factures.',
        1, 3, 'Medium', 'haute', 'resolu', 'Resolved',
        (SELECT id FROM categories WHERE name = 'Wincar'), 'Wincar',
        'Amine Rachidi', 'amine.rachidi@exemple.com', 1,
        (SELECT id FROM technicians WHERE email = 'amine.zinoun@autohall.ma'),
        'Amine Zinoun', 'amine.zinoun@autohall.ma', '2026-07-15 09:31:00+01',
        '2026-07-15 09:30:00+01'),

    (2, 'Demande de création de boîte mail pour nouveau collaborateur',
        'Bonjour, merci de créer une boîte mail pour Karim Idrissi, nouveau responsable atelier. Email souhaité : k.idrissi@autohall.ma',
        'Bonjour, merci de créer une boîte mail pour Karim Idrissi, nouveau responsable atelier. Email souhaité : k.idrissi@autohall.ma',
        2, 3, 'Medium', 'moyenne', 'resolu', 'Resolved',
        (SELECT id FROM categories WHERE name = 'Messagerie'), 'Messagerie',
        'Fatima Benali', 'fatima.benali@exemple.com', 2,
        (SELECT id FROM technicians WHERE email = 'sofia.elidrissi@autohall.ma'),
        'Sofia El Idrissi', 'sofia.elidrissi@autohall.ma', '2026-07-16 14:01:00+01',
        '2026-07-16 14:00:00+01'),

    (3, 'Session Citrix se déconnecte toutes les 10 minutes',
        'Ma session Citrix se ferme automatiquement toutes les 10 minutes environ. Je perds mon travail en cours à chaque fois.',
        'Ma session Citrix se ferme automatiquement toutes les 10 minutes environ. Je perds mon travail en cours à chaque fois.',
        1, 2, 'High', 'haute', 'en_cours', 'In Progress',
        (SELECT id FROM categories WHERE name = 'Citrix'), 'Citrix',
        'Youssef El Amrani', 'youssef.elamrani@exemple.com', 3,
        (SELECT id FROM technicians WHERE email = 'youssef.bensaid@autohall.ma'),
        'Youssef Bensaid', 'youssef.bensaid@autohall.ma', '2026-07-20 11:16:00+01',
        '2026-07-20 11:15:00+01'),

    (4, 'Écran externe ne s''affiche plus',
        'Mon deuxième écran n''est plus détecté depuis ce matin. J''ai essayé de changer le câble HDMI sans succès.',
        'Mon deuxième écran n''est plus détecté depuis ce matin. J''ai essayé de changer le câble HDMI sans succès.',
        1, 3, 'Medium', 'moyenne', 'nouveau', 'Open',
        (SELECT id FROM categories WHERE name = 'Matériel'), 'Matériel',
        'Nadia Tazi', 'nadia.tazi@exemple.com', NULL,
        (SELECT id FROM technicians WHERE email = 'nabil.cherkaoui@autohall.ma'),
        'Nabil Cherkaoui', 'nabil.cherkaoui@autohall.ma', '2026-07-22 08:46:00+01',
        '2026-07-22 08:45:00+01'),

    (5, 'Accès Internet bloqué sur certains sites',
        'Je n''arrive pas à accéder aux sites de pièces détachées automobiles. Le proxy affiche "Accès refusé". J''en ai besoin pour mon travail.',
        'Je n''arrive pas à accéder aux sites de pièces détachées automobiles. Le proxy affiche "Accès refusé". J''en ai besoin pour mon travail.',
        1, 3, 'Medium', 'moyenne', 'nouveau', 'Open',
        (SELECT id FROM categories WHERE name = 'Internet'), 'Internet',
        'Hassan Moukrim', 'hassan.moukrim@exemple.com', NULL,
        (SELECT id FROM technicians WHERE email = 'hassan.rami@autohall.ma'),
        'Hassan Rami', 'hassan.rami@autohall.ma', '2026-07-23 10:01:00+01',
        '2026-07-23 10:00:00+01'),

    (6, 'Installation Adobe Acrobat Pro demandée',
        'Bonjour, j''aurais besoin d''Adobe Acrobat Pro pour éditer des PDF techniques. Merci de procéder à l''installation.',
        'Bonjour, j''aurais besoin d''Adobe Acrobat Pro pour éditer des PDF techniques. Merci de procéder à l''installation.',
        2, 4, 'Low', 'basse', 'nouveau', 'Open',
        (SELECT id FROM categories WHERE name = 'Logiciel Système'), 'Logiciel Système',
        'Sara Lahlou', 'sara.lahlou@exemple.com', NULL,
        (SELECT id FROM technicians WHERE email = 'karim.tazi@autohall.ma'),
        'Karim Tazi', 'karim.tazi@autohall.ma', '2026-07-24 16:31:00+01',
        '2026-07-24 16:30:00+01'),

    (7, 'Erreur de connexion Sage Comptabilité',
        'Sage Comptabilité affiche "Impossible de se connecter au serveur de données" depuis 14h. Toute l''équipe comptable est bloquée.',
        'Sage Comptabilité affiche "Impossible de se connecter au serveur de données" depuis 14h. Toute l''équipe comptable est bloquée.',
        1, 1, 'Urgent', 'très haute', 'en_cours', 'In Progress',
        (SELECT id FROM categories WHERE name = 'Sage'), 'Sage',
        'Rachid Kabbaj', 'rachid.kabbaj@exemple.com', NULL,
        (SELECT id FROM technicians WHERE email = 'leila.mounir@autohall.ma'),
        'Leila Mounir', 'leila.mounir@autohall.ma', '2026-07-25 14:11:00+01',
        '2026-07-25 14:10:00+01'),

    (8, 'Mot de passe Windows expiré',
        'Mon mot de passe Windows a expiré et je n''arrive pas à le changer. Le message dit "Contactez votre administrateur".',
        'Mon mot de passe Windows a expiré et je n''arrive pas à le changer. Le message dit "Contactez votre administrateur".',
        1, 3, 'Medium', 'moyenne', 'resolu', 'Resolved',
        (SELECT id FROM categories WHERE name = 'Windows'), 'Windows',
        'Imane Fassi', 'imane.fassi@exemple.com', NULL,
        (SELECT id FROM technicians WHERE email = 'omar.fassi@autohall.ma'),
        'Omar Fassi', 'omar.fassi@autohall.ma', '2026-07-26 07:56:00+01',
        '2026-07-26 07:55:00+01'),

    (9, 'VPN ne se connecte pas depuis le site de Kénitra',
        'Depuis le site de Kénitra, impossible d''établir la connexion VPN vers le siège. Erreur "Timeout de connexion".',
        'Depuis le site de Kénitra, impossible d''établir la connexion VPN vers le siège. Erreur "Timeout de connexion".',
        1, 2, 'High', 'haute', 'nouveau', 'Open',
        (SELECT id FROM categories WHERE name = 'Ligne VPN'), 'Ligne VPN',
        'Omar Bennani', 'omar.bennani@exemple.com', NULL,
        (SELECT id FROM technicians WHERE email = 'samir.lahmadi@autohall.ma'),
        'Samir Lahmadi', 'samir.lahmadi@autohall.ma', '2026-07-28 09:21:00+01',
        '2026-07-28 09:20:00+01'),

    (10, 'Demande de toner pour imprimante HP LaserJet',
         'Bonjour, l''imprimante du 2ème étage (HP LaserJet Pro M404) est à court de toner noir. Merci de commander un remplacement.',
         'Bonjour, l''imprimante du 2ème étage (HP LaserJet Pro M404) est à court de toner noir. Merci de commander un remplacement.',
         2, 4, 'Low', 'basse', 'nouveau', 'Open',
         (SELECT id FROM categories WHERE name = 'Consommable'), 'Consommable',
         'Leila Chraibi', 'leila.chraibi@exemple.com', NULL,
         (SELECT id FROM technicians WHERE email = 'fouad.lahlou@autohall.ma'),
         'Fouad Lahlou', 'fouad.lahlou@autohall.ma', '2026-07-29 11:41:00+01',
         '2026-07-29 11:40:00+01')
ON CONFLICT (id) DO NOTHING;

-- Mettre à jour la séquence
SELECT setval('tickets_id_seq', 10, true);

-- ── 5) Audit d'assignation (historique) ──────────────────────
INSERT INTO ticket_assignments (ticket_id, technician_id, assigned_by, reason)
SELECT t.id, t.assigned_to_id, 'system', 'Auto-assignation par catégorie: ' || t.category
FROM tickets t
WHERE t.assigned_to_id IS NOT NULL
ON CONFLICT DO NOTHING;

-- ── 6) Messages fictifs ──────────────────────────────────────
-- Conversation 1 : Problème Wincar
INSERT INTO messages (conversation_id, role, content, metadata) VALUES
    (1, 'assistant', 'Bonjour ! Je suis l''assistant AUTOHALL Helpdesk. Comment puis-je vous aider aujourd''hui ?', '{}'),
    (1, 'user',      'Bonjour, Wincar ne marche plus depuis la mise à jour de ce matin', '{}'),
    (1, 'assistant', 'Je comprends que vous rencontrez un problème avec Wincar après une mise à jour. Pouvez-vous me préciser le message d''erreur exact qui s''affiche ?', '{}'),
    (1, 'user',      'Oui, ça dit "Module facturation introuvable" quand j''essaie d''ouvrir le module de facturation', '{}'),
    (1, 'assistant', 'Merci pour cette précision. J''ai identifié votre problème. Il s''agit d''un incident lié à Wincar, catégorie facturation. Laissez-moi vérifier dans notre base de connaissances...', '{"state": "recherche_kb"}'),
    (1, 'assistant', 'J''ai trouvé une solution ! Voici les étapes :\n1. Fermez complètement Wincar\n2. Allez dans C:\\Wincar\\Modules\\\n3. Renommez le fichier facturation.dll.bak en facturation.dll\n4. Relancez Wincar\n\nEst-ce que cela résout votre problème ?', '{"state": "solution_proposee", "kb_match": true}');

-- Conversation 2 : Demande messagerie
INSERT INTO messages (conversation_id, role, content, metadata) VALUES
    (2, 'assistant', 'Bonjour ! Je suis l''assistant AUTOHALL Helpdesk. Comment puis-je vous aider aujourd''hui ?', '{}'),
    (2, 'user',      'Je voudrais créer une adresse email pour un nouveau collaborateur', '{}'),
    (2, 'assistant', 'Bien sûr ! Pour créer une nouvelle boîte mail, j''ai besoin de quelques informations :\n1. Nom complet du collaborateur\n2. Service / département\n3. Format d''email souhaité (ex: prenom.nom@autohall.ma)', '{}'),
    (2, 'user',      'Karim Idrissi, responsable atelier, k.idrissi@autohall.ma', '{}'),
    (2, 'assistant', 'Parfait ! Je vais créer un ticket de type "Demande" pour la création de la boîte mail.\n\n📋 **Récapitulatif :**\n- **Type** : Demande\n- **Catégorie** : Messagerie\n- **Priorité** : Moyenne\n- **Collaborateur** : Karim Idrissi\n- **Email** : k.idrissi@autohall.ma\n\nLe ticket a été créé avec le numéro #2 et assigné à Sofia El Idrissi (support Messagerie).', '{"state": "ticket_cree", "ticket_id": 2}');

-- Conversation 3 : Incident Citrix
INSERT INTO messages (conversation_id, role, content, metadata) VALUES
    (3, 'assistant', 'Bonjour ! Je suis l''assistant AUTOHALL Helpdesk. Comment puis-je vous aider aujourd''hui ?', '{}'),
    (3, 'user',      'Ma session Citrix se déconnecte sans arrêt', '{}'),
    (3, 'assistant', 'Je suis désolé pour ce désagrément. Pour mieux comprendre votre problème Citrix, pouvez-vous me préciser :\n1. À quelle fréquence la déconnexion se produit-elle ?\n2. Depuis combien de temps avez-vous ce problème ?\n3. Travaillez-vous depuis le bureau ou à distance ?', '{}'),
    (3, 'user',      'Toutes les 10 minutes environ, depuis ce matin, je suis au bureau', '{}'),
    (3, 'assistant', 'Merci. Je qualifie cela comme un **Incident Citrix** de priorité **Haute** car il impacte votre productivité.\n\nUn ticket #3 a été créé et assigné à Youssef Bensaid (support Citrix). Il va intervenir rapidement.', '{"state": "ticket_cree", "ticket_id": 3}');

-- ── 7) Brouillon d'e-mail fictif ─────────────────────────────
INSERT INTO email_drafts (ticket_id, conversation_id, recipient_email, subject, body, status) VALUES
    (2, 2, 'fatima.benali@exemple.com',
     'Confirmation de votre demande #2 — Création boîte mail',
     'Bonjour Fatima,\n\nVotre demande de création de boîte mail pour Karim Idrissi (k.idrissi@autohall.ma) a bien été enregistrée sous le numéro de ticket #2.\n\nCe ticket a été assigné à Sofia El Idrissi (support Messagerie). Vous serez recontactée dans un délai de 24 à 48 heures.\n\nCordialement,\nL''équipe Helpdesk AUTOHALL',
     'draft');

-- ── 8) Consolidation des techniciens ───────────────────────
UPDATE technicians
SET role = 'Support IT', team = 'AUTOHALL IT', category_id = NULL
WHERE email IN (
    'amine.spk.zinoun@gmail.com', 'sofia.elidrissi@autohall.ma',
    'youssef.bensaid@autohall.ma', 'nabil.cherkaoui@autohall.ma'
);

UPDATE tickets
SET assigned_to_id = (
        SELECT id FROM technicians
        WHERE email = CASE
            WHEN category IN ('Wincar', 'Windows', 'GestorNet', 'Consommable', 'Moovapps', 'Contrat de Vente', 'GENERAFI', 'Fidélisation', 'SMS', 'VOXCO', 'TPE') THEN 'amine.spk.zinoun@gmail.com'
            WHEN category IN ('Citrix', 'Logiciel Système', 'Réseau', 'CRM', 'Ligne VPN', 'RIAPP', 'Qalitel Doc', 'Microsoft Teams', 'VPN_FortiClient', 'Antivirus', 'Intranet', 'eSeller') THEN 'sofia.elidrissi@autohall.ma'
            WHEN category IN ('Matériel', 'Internet', 'APPCC', 'Poste IP Phone', 'Reporting', 'PayRoll', 'GDoc', 'Site Web', 'Optimmo', 'Qalitel Compar', 'SLV', 'C.Conformité') THEN 'youssef.bensaid@autohall.ma'
            WHEN category IN ('Messagerie', 'Sage', 'Outillages SAV', 'Auto Naps', 'Ligne Téléphonique', 'GSM', 'Sage Paie & RH', 'WebEX', 'AppGCMA', 'SRM', 'Devopps', 'OPEL') THEN 'nabil.cherkaoui@autohall.ma'
            ELSE NULL
        END
    );

UPDATE tickets
SET assigned_to_name = technicians.full_name,
    assigned_to_email = technicians.email
FROM technicians
WHERE tickets.assigned_to_id = technicians.id;

UPDATE ticket_assignments assignments
SET technician_id = tickets.assigned_to_id
FROM tickets
WHERE assignments.ticket_id = tickets.id
  AND tickets.assigned_to_id IS NOT NULL;

DELETE FROM technicians
WHERE email NOT IN (
    'amine.spk.zinoun@gmail.com', 'sofia.elidrissi@autohall.ma',
    'youssef.bensaid@autohall.ma', 'nabil.cherkaoui@autohall.ma'
);