-- ============================================================
-- Seed PostgreSQL — Données 100% FICTIVES
-- Ordre : categories → technicians → conversations → tickets
--          → messages → email_drafts
-- ============================================================

-- ── 1) Catégories métier AUTOHALL ────────────────────────────
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

-- ── 2) Techniciens (1 tech par catégorie) ────────────────────
INSERT INTO technicians (full_name, email, role, team, category_id, active) VALUES
    ('Amine Zinoun',       'amine.spk.zinoun@gmail.com',       'Support Wincar',                'Wincar',             (SELECT id FROM categories WHERE name = 'Wincar'),             TRUE),
    ('Sofia El Idrissi',   'sofia.elidrissi@autohall.ma',    'Support messagerie / Outlook',              'Messagerie',         (SELECT id FROM categories WHERE name = 'Messagerie'),         TRUE),
    ('Youssef Bensaid',    'youssef.bensaid@autohall.ma',    'Support Citrix / virtualisation',           'Citrix',             (SELECT id FROM categories WHERE name = 'Citrix'),             TRUE),
    ('Nabil Cherkaoui',    'nabil.cherkaoui@autohall.ma',    'Support matériel et périphériques',         'Matériel',           (SELECT id FROM categories WHERE name = 'Matériel'),           TRUE),
    ('Hassan Rami',        'hassan.rami@autohall.ma',        'Support accès internet / réseau',           'Internet',           (SELECT id FROM categories WHERE name = 'Internet'),           TRUE),
    ('Karim Tazi',         'karim.tazi@autohall.ma',         'Support logiciels système',                 'Logiciel Système',   (SELECT id FROM categories WHERE name = 'Logiciel Système'),   TRUE),
    ('Leila Mounir',       'leila.mounir@autohall.ma',       'Support Sage / comptabilité',               'Sage',               (SELECT id FROM categories WHERE name = 'Sage'),               TRUE),
    ('Omar Fassi',         'omar.fassi@autohall.ma',         'Support Windows / postes',                  'Windows',            (SELECT id FROM categories WHERE name = 'Windows'),            TRUE),
    ('Reda Najmi',         'reda.najmi@autohall.ma',         'Support APPCC / conformité',                'APPCC',              (SELECT id FROM categories WHERE name = 'APPCC'),              TRUE),
    ('Zakaria Benali',     'zakaria.benali@autohall.ma',     'Support réseau / Wi-Fi / switches',         'Réseau',             (SELECT id FROM categories WHERE name = 'Réseau'),             TRUE),
    ('Mehdi Essalhi',      'mehdi.essalhi@autohall.ma',      'Support outillages SAV / diagnostics',      'Outillages SAV',     (SELECT id FROM categories WHERE name = 'Outillages SAV'),     TRUE),
    ('Salma Karim',        'salma.karim@autohall.ma',        'Support GestorNet / workflow',              'GestorNet',          (SELECT id FROM categories WHERE name = 'GestorNet'),          TRUE),
    ('Mohamed Aouad',      'mohamed.aouad@autohall.ma',      'Support CRM / données clients',             'CRM',                (SELECT id FROM categories WHERE name = 'CRM'),                TRUE),
    ('Ilyas Oulhaj',       'ilyas.oulhaj@autohall.ma',       'Support Auto Naps / planification atelier', 'Auto Naps',          (SELECT id FROM categories WHERE name = 'Auto Naps'),          TRUE),
    ('Anas Choukri',       'anas.choukri@autohall.ma',       'Support téléphonie IP / postes',            'Poste IP Phone',     (SELECT id FROM categories WHERE name = 'Poste IP Phone'),     TRUE),
    ('Sara Bourou',        'sara.bourou@autohall.ma',        'Support reporting / BI',                    'Reporting',          (SELECT id FROM categories WHERE name = 'Reporting'),          TRUE),
    ('Samir Lahmadi',      'samir.lahmadi@autohall.ma',      'Support VPN / accès distant',               'Ligne VPN',          (SELECT id FROM categories WHERE name = 'Ligne VPN'),          TRUE),
    ('Fouad Lahlou',       'fouad.lahlou@autohall.ma',       'Support consommables / matériel de bureau', 'Consommable',        (SELECT id FROM categories WHERE name = 'Consommable'),        TRUE),
    ('Mounir Sefrioui',    'mounir.sefrioui@autohall.ma',    'Support lignes téléphoniques',              'Ligne Téléphonique', (SELECT id FROM categories WHERE name = 'Ligne Téléphonique'), TRUE),
    ('Yacine Debbagh',     'yacine.debbagh@autohall.ma',     'Support GSM / smartphones',                 'GSM',                (SELECT id FROM categories WHERE name = 'GSM'),                TRUE),
    ('Hicham Regragui',    'hicham.regragui@autohall.ma',    'Support Moovapps / GED',                    'Moovapps',           (SELECT id FROM categories WHERE name = 'Moovapps'),           TRUE),
    ('Nadia El Yacoubi',   'nadia.elyacoubi@autohall.ma',    'Support PayRoll / paie',                    'PayRoll',            (SELECT id FROM categories WHERE name = 'PayRoll'),            TRUE),
    ('Imane Zaki',        'imane.zaki@autohall.ma',        'Support SRM / achats fournisseurs',         'SRM',                 (SELECT id FROM categories WHERE name = 'SRM'),                 TRUE),
    ('Hamza El Mansouri', 'hamza.elmansouri@autohall.ma', 'Support RIAPP', 'RIAPP', (SELECT id FROM categories WHERE name = 'RIAPP'), TRUE),
    ('Imane Berrada', 'imane.berrada@autohall.ma', 'Support Qalitel Doc', 'Qalitel Doc', (SELECT id FROM categories WHERE name = 'Qalitel Doc'), TRUE),
    ('Rachid Alaoui', 'rachid.alaoui@autohall.ma', 'Support GDoc', 'GDoc', (SELECT id FROM categories WHERE name = 'GDoc'), TRUE),
    ('Salma Bennani', 'salma.bennani@autohall.ma', 'Support contrats de vente', 'Contrat de Vente', (SELECT id FROM categories WHERE name = 'Contrat de Vente'), TRUE),
    ('Adil Chafik', 'adil.chafik@autohall.ma', 'Support Sage Paie et RH', 'Sage Paie & RH', (SELECT id FROM categories WHERE name = 'Sage Paie & RH'), TRUE),
    ('Oumaima El Fassi', 'oumaima.elfassi@autohall.ma', 'Support Microsoft Teams', 'Microsoft Teams', (SELECT id FROM categories WHERE name = 'Microsoft Teams'), TRUE),
    ('Bilal Amrani', 'bilal.amrani@autohall.ma', 'Support WebEX', 'WebEX', (SELECT id FROM categories WHERE name = 'WebEX'), TRUE),
    ('Hajar Naciri', 'hajar.naciri@autohall.ma', 'Support GENERAFI', 'GENERAFI', (SELECT id FROM categories WHERE name = 'GENERAFI'), TRUE),
    ('Ayoub Tazi', 'ayoub.tazi@autohall.ma', 'Support site web', 'Site Web', (SELECT id FROM categories WHERE name = 'Site Web'), TRUE),
    ('Wiam El Khatib', 'wiam.elkhatib@autohall.ma', 'Support AppGCMA', 'AppGCMA', (SELECT id FROM categories WHERE name = 'AppGCMA'), TRUE),
    ('Ismail Rahmani', 'ismail.rahmani@autohall.ma', 'Support VPN FortiClient', 'VPN_FortiClient', (SELECT id FROM categories WHERE name = 'VPN_FortiClient'), TRUE),
    ('Mariam Zahir', 'mariam.zahir@autohall.ma', 'Support fidélisation', 'Fidélisation', (SELECT id FROM categories WHERE name = 'Fidélisation'), TRUE),
    ('Soufiane Idrissi', 'soufiane.idrissi@autohall.ma', 'Support Optimmo', 'Optimmo', (SELECT id FROM categories WHERE name = 'Optimmo'), TRUE),
    ('Chaimae Ait Lahcen', 'chaimae.aitlahcen@autohall.ma', 'Support SMS', 'SMS', (SELECT id FROM categories WHERE name = 'SMS'), TRUE),
    ('Yassine El Ouardi', 'yassine.elouardi@autohall.ma', 'Support Qalitel Compar', 'Qalitel Compar', (SELECT id FROM categories WHERE name = 'Qalitel Compar'), TRUE),
    ('Hind Bennis', 'hind.bennis@autohall.ma', 'Support antivirus', 'Antivirus', (SELECT id FROM categories WHERE name = 'Antivirus'), TRUE),
    ('Noura El Kadi', 'noura.elkadi@autohall.ma', 'Support SLV', 'SLV', (SELECT id FROM categories WHERE name = 'SLV'), TRUE),
    ('Mehdi Rahal', 'mehdi.rahal@autohall.ma', 'Support VOXCO', 'VOXCO', (SELECT id FROM categories WHERE name = 'VOXCO'), TRUE),
    ('Kawtar Benjelloun', 'kawtar.benjelloun@autohall.ma', 'Support intranet', 'Intranet', (SELECT id FROM categories WHERE name = 'Intranet'), TRUE),
    ('Anass El Ghazali', 'anass.elghazali@autohall.ma', 'Support Devopps', 'Devopps', (SELECT id FROM categories WHERE name = 'Devopps'), TRUE),
    ('Siham Lahlou', 'siham.lahlou@autohall.ma', 'Support conformité', 'C.Conformité', (SELECT id FROM categories WHERE name = 'C.Conformité'), TRUE),
    ('Zakaria El Haddad', 'zakaria.elhaddad@autohall.ma', 'Support eSeller', 'eSeller', (SELECT id FROM categories WHERE name = 'eSeller'), TRUE),
    ('Amina Bouazza', 'amina.bouazza@autohall.ma', 'Support terminaux de paiement', 'TPE', (SELECT id FROM categories WHERE name = 'TPE'), TRUE),
    ('Tarik Azzouzi', 'tarik.azzouzi@autohall.ma', 'Support OPEL', 'OPEL', (SELECT id FROM categories WHERE name = 'OPEL'), TRUE)
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