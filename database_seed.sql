-- ============================================================================
-- Données de démo pour db_couturier
-- À exécuter APRÈS database_schema.sql : \c db_couturier
-- ============================================================================

-- Nettoyage optionnel
-- TRUNCATE TABLE app_logo CASCADE;
-- TRUNCATE TABLE charge_documents CASCADE;
-- TRUNCATE TABLE charges CASCADE;
-- TRUNCATE TABLE historique_commandes CASCADE;
-- TRUNCATE TABLE commandes CASCADE;
-- TRUNCATE TABLE clients CASCADE;
-- TRUNCATE TABLE couturiers CASCADE;
-- TRUNCATE TABLE salons CASCADE;

-- --------------------------------------------------------------------------
-- Salons
-- --------------------------------------------------------------------------
INSERT INTO salons (salon_id, nom, quartier, responsable, telephone, email, code_admin, actif)
VALUES
('Jaind_000', 'Salon Principal', 'Plateau', 'Amadou Diop', '771234567', 'salon.principal@email.com', 'ADMIN001', TRUE),
('Jaind_001', 'Salon Almadies', 'Almadies', 'Fatou Ndiaye', '771234568', 'salon.almadies@email.com', 'ADMIN002', TRUE),
('Jaind_002', 'Salon Ouakam', 'Ouakam', 'Moussa Sow', '771234569', 'salon.ouakam@email.com', 'ADMIN003', TRUE),
('Jaind_003', 'Salon Mermoz', 'Mermoz', 'Aissatou Ba', '771234570', 'salon.mermoz@email.com', 'ADMIN004', TRUE),
('Jaind_004', 'Salon Yoff', 'Yoff', 'Ibrahima Diallo', '771234571', 'salon.yoff@email.com', 'ADMIN005', TRUE)
ON CONFLICT (salon_id) DO NOTHING;

-- --------------------------------------------------------------------------
-- Couturiers (mots de passe en clair pour la démo)
-- --------------------------------------------------------------------------
INSERT INTO couturiers (code_couturier, password, nom, prenom, email, telephone, role, salon_id, actif)
VALUES
('COUT001', 'admin123', 'Diop', 'Amadou', 'amadou.diop@email.com', '771234567', 'admin', 'Jaind_000', TRUE),
('COUT002', 'emp123', 'Ndiaye', 'Fatou', 'fatou.ndiaye@email.com', '771234568', 'employe', 'Jaind_000', TRUE),
('COUT003', 'admin456', 'Sow', 'Moussa', 'moussa.sow@email.com', '771234569', 'admin', 'Jaind_001', TRUE),
('COUT004', 'emp456', 'Ba', 'Aissatou', 'aissatou.ba@email.com', '771234570', 'employe', 'Jaind_001', TRUE),
('SUPERADMIN', 'super123', 'Admin', 'Super', 'super.admin@email.com', '771234571', 'super_admin', NULL, TRUE)
ON CONFLICT (code_couturier) DO NOTHING;

-- Lier admin_id des salons principaux
UPDATE salons SET admin_id = (SELECT id FROM couturiers WHERE code_couturier = 'COUT001') WHERE salon_id = 'Jaind_000';
UPDATE salons SET admin_id = (SELECT id FROM couturiers WHERE code_couturier = 'COUT003') WHERE salon_id = 'Jaind_001';

-- --------------------------------------------------------------------------
-- Clients
-- --------------------------------------------------------------------------
INSERT INTO clients (couturier_id, salon_id, nom, prenom, telephone, email)
VALUES
((SELECT id FROM couturiers WHERE code_couturier = 'COUT001'), 'Jaind_000', 'Fall', 'Mamadou', '771111111', 'mamadou.fall@email.com'),
((SELECT id FROM couturiers WHERE code_couturier = 'COUT002'), 'Jaind_000', 'Sy', 'Aminata', '771111112', 'aminata.sy@email.com'),
((SELECT id FROM couturiers WHERE code_couturier = 'COUT001'), 'Jaind_000', 'Kane', 'Ousmane', '771111113', 'ousmane.kane@email.com'),
((SELECT id FROM couturiers WHERE code_couturier = 'COUT003'), 'Jaind_001', 'Diallo', 'Mariama', '771111114', 'mariama.diallo@email.com'),
((SELECT id FROM couturiers WHERE code_couturier = 'COUT004'), 'Jaind_001', 'Thiam', 'Ibrahima', '771111115', 'ibrahima.thiam@email.com')
ON CONFLICT DO NOTHING;

-- --------------------------------------------------------------------------
-- Commandes
-- --------------------------------------------------------------------------
INSERT INTO commandes (
    client_id, couturier_id, salon_id,
    categorie, sexe, modele, mesures,
    prix_total, avance, reste, date_livraison,
    statut, est_ouverte,
    fabric_image_path, model_type, model_image_path
) VALUES
(
    (SELECT id FROM clients WHERE telephone = '771111111'),
    (SELECT id FROM couturiers WHERE code_couturier = 'COUT001'),
    'Jaind_000',
    'adulte','homme','Costume 3 pièces',
    '{"Tour de cou": 40, "Largeur épaules": 45, "Tour de poitrine": 100, "Tour de taille": 85, "Tour de hanches": 95, "Longueur dos": 45, "Longueur manche": 60, "Tour de bras": 35, "Longueur pantalon": 105, "Entrejambe": 80}'::jsonb,
    50000.00, 20000.00, 30000.00, '2025-02-15',
    'En cours', TRUE,
    '/images/fabric_001.jpg', 'simple', '/images/model_001.jpg'
),
(
    (SELECT id FROM clients WHERE telephone = '771111112'),
    (SELECT id FROM couturiers WHERE code_couturier = 'COUT002'),
    'Jaind_000',
    'adulte','femme','Robe de soirée',
    '{"Tour de cou": 36, "Largeur épaules": 38, "Tour de poitrine": 90, "Tour de taille": 70, "Tour de hanches": 95, "Longueur dos": 42, "Longueur manche": 55, "Tour de bras": 28, "Longueur robe/jupe": 120, "Hauteur poitrine": 25}'::jsonb,
    45000.00, 25000.00, 20000.00, '2025-02-20',
    'En cours', TRUE,
    '/images/fabric_002.jpg', 'simple', '/images/model_002.jpg'
),
(
    (SELECT id FROM clients WHERE telephone = '771111113'),
    (SELECT id FROM couturiers WHERE code_couturier = 'COUT001'),
    'Jaind_000',
    'adulte','homme','Boubou',
    '{"Tour de cou": 42, "Largeur épaules": 48, "Tour de poitrine": 110, "Tour de taille": 90, "Tour de hanches": 100, "Longueur dos": 50, "Longueur manche": 65, "Tour de bras": 38, "Longueur pantalon": 110, "Entrejambe": 85}'::jsonb,
    35000.00, 35000.00, 0.00, '2025-01-30',
    'Terminé', TRUE,
    '/images/fabric_003.jpg', 'simple', '/images/model_003.jpg'
),
(
    (SELECT id FROM clients WHERE telephone = '771111114'),
    (SELECT id FROM couturiers WHERE code_couturier = 'COUT003'),
    'Jaind_001',
    'enfant','fille','Robe de cérémonie',
    '{"Tour de cou": 28, "Tour de poitrine": 65, "Tour de taille": 55, "Longueur dos": 30, "Longueur manche": 40, "Longueur robe": 80}'::jsonb,
    25000.00, 10000.00, 15000.00, '2025-03-01',
    'En cours', TRUE,
    '/images/fabric_004.jpg', 'simple', '/images/model_004.jpg'
),
(
    (SELECT id FROM clients WHERE telephone = '771111115'),
    (SELECT id FROM couturiers WHERE code_couturier = 'COUT004'),
    'Jaind_001',
    'adulte','femme','Caftan',
    '{"Tour de cou": 35, "Largeur épaules": 36, "Tour de poitrine": 88, "Tour de taille": 68, "Tour de hanches": 92, "Longueur dos": 40, "Longueur manche": 52, "Tour de bras": 26, "Longueur robe/jupe": 130, "Hauteur poitrine": 24}'::jsonb,
    40000.00, 40000.00, 0.00, '2025-01-25',
    'Livré et payé', FALSE,
    '/images/fabric_005.jpg', 'simple', '/images/model_005.jpg'
)
ON CONFLICT DO NOTHING;

-- --------------------------------------------------------------------------
-- Historique des commandes
-- --------------------------------------------------------------------------
INSERT INTO historique_commandes (
    commande_id, couturier_id, type_action, montant_paye, reste_apres_paiement,
    statut_avant, statut_apres, commentaire, statut_validation, admin_validation_id, date_validation
) VALUES
(
    (SELECT id FROM commandes WHERE client_id = (SELECT id FROM clients WHERE telephone = '771111111')),
    (SELECT id FROM couturiers WHERE code_couturier = 'COUT001'),
    'paiement', 20000.00, 30000.00,
    'En cours','En cours','Premier paiement - 40%','validee',
    (SELECT id FROM couturiers WHERE code_couturier = 'COUT001'), CURRENT_TIMESTAMP
),
(
    (SELECT id FROM commandes WHERE client_id = (SELECT id FROM clients WHERE telephone = '771111112')),
    (SELECT id FROM couturiers WHERE code_couturier = 'COUT002'),
    'paiement', 25000.00, 20000.00,
    'En cours','En cours','Paiement initial - 55%','validee',
    (SELECT id FROM couturiers WHERE code_couturier = 'COUT001'), CURRENT_TIMESTAMP
),
(
    (SELECT id FROM commandes WHERE client_id = (SELECT id FROM clients WHERE telephone = '771111113')),
    (SELECT id FROM couturiers WHERE code_couturier = 'COUT001'),
    'paiement', 35000.00, 0.00,
    'En cours','Terminé','Paiement complet','validee',
    (SELECT id FROM couturiers WHERE code_couturier = 'COUT001'), CURRENT_TIMESTAMP
),
(
    (SELECT id FROM commandes WHERE client_id = (SELECT id FROM clients WHERE telephone = '771111114')),
    (SELECT id FROM couturiers WHERE code_couturier = 'COUT003'),
    'paiement', 10000.00, 15000.00,
    'En cours','En cours','Acompte initial','en_attente',
    NULL, NULL
),
(
    (SELECT id FROM commandes WHERE client_id = (SELECT id FROM clients WHERE telephone = '771111115')),
    (SELECT id FROM couturiers WHERE code_couturier = 'COUT004'),
    'fermeture_demande', 0.00, 0.00,
    'Terminé','Livré et payé','Commande livrée et payée en totalité','validee',
    (SELECT id FROM couturiers WHERE code_couturier = 'COUT003'), CURRENT_TIMESTAMP
)
ON CONFLICT DO NOTHING;

-- --------------------------------------------------------------------------
-- Charges
-- --------------------------------------------------------------------------
INSERT INTO charges (
    couturier_id, salon_id, type, categorie, montant, date_charge, description, commande_id, employe_id, reference
) VALUES
(
    (SELECT id FROM couturiers WHERE code_couturier = 'COUT001'),
    'Jaind_000','Fixe','loyer',150000.00,'2025-01-01',
    'Loyer mensuel du salon principal',NULL,NULL,'CHG-2025-001'
),
(
    (SELECT id FROM couturiers WHERE code_couturier = 'COUT001'),
    'Jaind_000','Salaire','salaire',200000.00,'2025-01-05',
    'Salaire mensuel de Fatou Ndiaye',NULL,(SELECT id FROM couturiers WHERE code_couturier = 'COUT002'),'CHG-2025-002'
),
(
    (SELECT id FROM couturiers WHERE code_couturier = 'COUT001'),
    'Jaind_000','Ponctuelle','materiel',50000.00,'2025-01-10',
    'Achat de matériel de couture (ciseaux, fils, aiguilles)',NULL,NULL,'CHG-2025-003'
),
(
    (SELECT id FROM couturiers WHERE code_couturier = 'COUT001'),
    'Jaind_000','Commande','tissu',30000.00,'2025-01-15',
    'Achat de tissu pour commande #1',
    (SELECT id FROM commandes WHERE client_id = (SELECT id FROM clients WHERE telephone = '771111111')),
    NULL,'CHG-2025-004'
),
(
    (SELECT id FROM couturiers WHERE code_couturier = 'COUT003'),
    'Jaind_001','Fixe','electricite',25000.00,'2025-01-01',
    'Facture d''électricité mensuelle',NULL,NULL,'CHG-2025-005'
)
ON CONFLICT DO NOTHING;

-- --------------------------------------------------------------------------
-- Charge documents (fichiers fictifs)
-- --------------------------------------------------------------------------
INSERT INTO charge_documents (
    charge_id, salon_id, file_path, file_name, file_size, mime_type, uploaded_by, description
) VALUES
(
    (SELECT id FROM charges WHERE reference = 'CHG-2025-001'),
    'Jaind_000','/documents/charge_001_facture.pdf','facture_loyer_janvier.pdf',245760,'application/pdf',
    (SELECT id FROM couturiers WHERE code_couturier = 'COUT001'),
    'Facture de loyer janvier 2025'
),
(
    (SELECT id FROM charges WHERE reference = 'CHG-2025-002'),
    'Jaind_000','/documents/charge_002_bulletin.pdf','bulletin_salaire_fatou.pdf',189440,'application/pdf',
    (SELECT id FROM couturiers WHERE code_couturier = 'COUT001'),
    'Bulletin de salaire de Fatou Ndiaye'
),
(
    (SELECT id FROM charges WHERE reference = 'CHG-2025-003'),
    'Jaind_000','/documents/charge_003_facture.jpg','facture_materiel.jpg',524288,'image/jpeg',
    (SELECT id FROM couturiers WHERE code_couturier = 'COUT001'),
    'Photo de la facture d''achat de matériel'
),
(
    (SELECT id FROM charges WHERE reference = 'CHG-2025-004'),
    'Jaind_000','/documents/charge_004_facture.pdf','facture_tissu.pdf',156672,'application/pdf',
    (SELECT id FROM couturiers WHERE code_couturier = 'COUT001'),
    'Facture d''achat de tissu'
),
(
    (SELECT id FROM charges WHERE reference = 'CHG-2025-005'),
    'Jaind_001','/documents/charge_005_facture.pdf','facture_electricite.pdf',198656,'application/pdf',
    (SELECT id FROM couturiers WHERE code_couturier = 'COUT003'),
    'Facture d''électricité janvier 2025'
)
ON CONFLICT DO NOTHING;

-- --------------------------------------------------------------------------
-- Logos (bytea vide pour la démo)
-- --------------------------------------------------------------------------
INSERT INTO app_logo (salon_id, logo_data, logo_name, mime_type, file_size, uploaded_by, description)
VALUES
('Jaind_000', E'\\x'::bytea, 'logo_salon_principal.png', 'image/png', 45678, (SELECT id FROM couturiers WHERE code_couturier = 'COUT001'), 'Logo du salon principal'),
('Jaind_001', E'\\x'::bytea, 'logo_salon_almadies.png', 'image/png', 45678, (SELECT id FROM couturiers WHERE code_couturier = 'COUT003'), 'Logo du salon Almadies'),
('Jaind_002', E'\\x'::bytea, 'logo_salon_ouakam.png', 'image/png', 45678, NULL, 'Logo du salon Ouakam'),
('Jaind_003', E'\\x'::bytea, 'logo_salon_mermoz.png', 'image/png', 45678, NULL, 'Logo du salon Mermoz'),
('Jaind_004', E'\\x'::bytea, 'logo_salon_yoff.png', 'image/png', 45678, NULL, 'Logo du salon Yoff')
ON CONFLICT (salon_id) DO NOTHING;

-- --------------------------------------------------------------------------
-- Récapitulatif
-- --------------------------------------------------------------------------
SELECT '✔ Salons' AS section, COUNT(*) AS total FROM salons
UNION ALL
SELECT '✔ Couturiers', COUNT(*) FROM couturiers
UNION ALL
SELECT '✔ Clients', COUNT(*) FROM clients
UNION ALL
SELECT '✔ Commandes', COUNT(*) FROM commandes
UNION ALL
SELECT '✔ Historique commandes', COUNT(*) FROM historique_commandes
UNION ALL
SELECT '✔ Charges', COUNT(*) FROM charges
UNION ALL
SELECT '✔ Docs charges', COUNT(*) FROM charge_documents
UNION ALL
SELECT '✔ Logos', COUNT(*) FROM app_logo;

