-- ============================================================================
-- Schéma PostgreSQL pour l'application Streamlit "Gestion Couturier"
-- Multi-tenant (salons), commandes, charges, historique, logos
-- À exécuter après création de la base : \c db_couturier
-- ============================================================================

-- Extension utile pour l'index JSONB (déjà dispo par défaut sur PG >=9.4)
-- CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- --------------------------------------------------------------------------
-- TABLE : salons
-- --------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS salons (
    salon_id       VARCHAR(50) PRIMARY KEY,
    nom            VARCHAR(200) NOT NULL,
    quartier       VARCHAR(200) NOT NULL,
    responsable    VARCHAR(200) NOT NULL,
    telephone      VARCHAR(20)  NOT NULL,
    email          VARCHAR(150),
    code_admin     VARCHAR(50) UNIQUE NOT NULL,
    admin_id       INTEGER NULL,
    actif          BOOLEAN DEFAULT TRUE,
    -- Configuration SMTP spécifique au salon (multi-tenant)
    smtp_host      VARCHAR(200) DEFAULT 'smtp.gmail.com',
    smtp_port      INTEGER      DEFAULT 587,
    smtp_user      VARCHAR(200),
    smtp_password  VARCHAR(200),
    smtp_from      VARCHAR(200),
    smtp_use_tls   BOOLEAN      DEFAULT TRUE,
    smtp_use_ssl   BOOLEAN      DEFAULT FALSE,
    date_creation  TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_salons_code_admin ON salons(code_admin);
CREATE INDEX IF NOT EXISTS idx_salons_actif ON salons(actif);
CREATE INDEX IF NOT EXISTS idx_salons_admin_id ON salons(admin_id);

-- --------------------------------------------------------------------------
-- TABLE : couturiers (utilisateurs)
-- --------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS couturiers (
    id             SERIAL PRIMARY KEY,
    code_couturier VARCHAR(50) UNIQUE NOT NULL,
    password       VARCHAR(255) NOT NULL,
    nom            VARCHAR(100) NOT NULL,
    prenom         VARCHAR(100) NOT NULL,
    email          VARCHAR(150),
    telephone      VARCHAR(20),
    role           VARCHAR(20) NOT NULL DEFAULT 'employe' CHECK (role IN ('admin','employe','super_admin')),
    salon_id       VARCHAR(50) NULL,
    actif          BOOLEAN NOT NULL DEFAULT TRUE,
    date_creation  TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_couturiers_code ON couturiers(code_couturier);
CREATE INDEX IF NOT EXISTS idx_couturiers_email ON couturiers(email);
CREATE INDEX IF NOT EXISTS idx_couturiers_salon ON couturiers(salon_id);
CREATE INDEX IF NOT EXISTS idx_couturiers_role ON couturiers(role);

-- FK vers salons (optionnelle car super_admin peut être NULL)
ALTER TABLE couturiers
    ADD CONSTRAINT IF NOT EXISTS fk_couturiers_salon
    FOREIGN KEY (salon_id) REFERENCES salons(salon_id)
    ON DELETE SET NULL ON UPDATE CASCADE;

-- --------------------------------------------------------------------------
-- TABLE : clients
-- --------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS clients (
    id            SERIAL PRIMARY KEY,
    couturier_id  INTEGER NOT NULL,
    salon_id      VARCHAR(50) NULL,
    nom           VARCHAR(100) NOT NULL,
    prenom        VARCHAR(100) NOT NULL,
    telephone     VARCHAR(20) NOT NULL,
    email         VARCHAR(150),
    date_creation TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (couturier_id) REFERENCES couturiers(id) ON DELETE CASCADE ON UPDATE CASCADE,
    FOREIGN KEY (salon_id) REFERENCES salons(salon_id) ON DELETE SET NULL ON UPDATE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_clients_couturier ON clients(couturier_id);
CREATE INDEX IF NOT EXISTS idx_clients_salon ON clients(salon_id);
CREATE INDEX IF NOT EXISTS idx_clients_telephone ON clients(telephone);
CREATE INDEX IF NOT EXISTS idx_clients_nom_prenom ON clients(nom, prenom);

-- --------------------------------------------------------------------------
-- TABLE : commandes
-- --------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS commandes (
    id                 SERIAL PRIMARY KEY,
    client_id          INTEGER NOT NULL,
    couturier_id       INTEGER NOT NULL,
    salon_id           VARCHAR(50) NULL,

    categorie          VARCHAR(20) NOT NULL,
    sexe               VARCHAR(20) NOT NULL,
    modele             VARCHAR(100) NOT NULL,
    mesures            JSONB NOT NULL,

    prix_total         DECIMAL(10,2) NOT NULL,
    avance             DECIMAL(10,2) NOT NULL DEFAULT 0.00,
    reste              DECIMAL(10,2) NOT NULL,

    date_livraison     DATE,
    date_creation      TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    date_dernier_paiement TIMESTAMP NULL,
    date_fermeture     TIMESTAMP NULL,

    statut             VARCHAR(50) DEFAULT 'En cours',
    est_ouverte        BOOLEAN DEFAULT TRUE,

    fabric_image_path  VARCHAR(500),
    fabric_image       BYTEA,
    fabric_image_name  VARCHAR(255),

    model_type         VARCHAR(20) DEFAULT 'simple',
    model_image_path   VARCHAR(500),
    model_image        BYTEA,
    model_image_name   VARCHAR(255),

    pdf_data           BYTEA,
    pdf_path           VARCHAR(500),
    pdf_name           VARCHAR(255),

    FOREIGN KEY (client_id) REFERENCES clients(id) ON DELETE CASCADE ON UPDATE CASCADE,
    FOREIGN KEY (couturier_id) REFERENCES couturiers(id) ON DELETE CASCADE ON UPDATE CASCADE,
    FOREIGN KEY (salon_id) REFERENCES salons(salon_id) ON DELETE SET NULL ON UPDATE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_commandes_client_id ON commandes(client_id);
CREATE INDEX IF NOT EXISTS idx_commandes_couturier_id ON commandes(couturier_id);
CREATE INDEX IF NOT EXISTS idx_commandes_salon ON commandes(salon_id);
CREATE INDEX IF NOT EXISTS idx_commandes_statut ON commandes(statut);
CREATE INDEX IF NOT EXISTS idx_commandes_date_creation ON commandes(date_creation);
CREATE INDEX IF NOT EXISTS idx_commandes_date_livraison ON commandes(date_livraison);
CREATE INDEX IF NOT EXISTS idx_commandes_couturier_statut ON commandes(couturier_id, statut);
CREATE INDEX IF NOT EXISTS idx_commandes_est_ouverte ON commandes(est_ouverte);
CREATE INDEX IF NOT EXISTS idx_commandes_date_fermeture ON commandes(date_fermeture);
CREATE INDEX IF NOT EXISTS idx_commandes_mesures ON commandes USING GIN (mesures);

-- --------------------------------------------------------------------------
-- TABLE : historique_commandes
-- --------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS historique_commandes (
    id                   SERIAL PRIMARY KEY,
    commande_id          INTEGER NOT NULL,
    couturier_id         INTEGER NOT NULL,
    type_action          VARCHAR(50) NOT NULL,
    montant_paye         DECIMAL(10,2) DEFAULT 0.00,
    reste_apres_paiement DECIMAL(10,2) DEFAULT 0.00,
    statut_avant         VARCHAR(50),
    statut_apres         VARCHAR(50),
    commentaire          TEXT,
    statut_validation    VARCHAR(50) DEFAULT 'en_attente',
    admin_validation_id  INTEGER NULL,
    date_validation      TIMESTAMP NULL,
    commentaire_admin    TEXT,
    date_creation        TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (commande_id) REFERENCES commandes(id) ON DELETE CASCADE ON UPDATE CASCADE,
    FOREIGN KEY (couturier_id) REFERENCES couturiers(id) ON DELETE CASCADE ON UPDATE CASCADE,
    FOREIGN KEY (admin_validation_id) REFERENCES couturiers(id) ON DELETE SET NULL ON UPDATE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_historique_commande_id ON historique_commandes(commande_id);
CREATE INDEX IF NOT EXISTS idx_historique_couturier_id ON historique_commandes(couturier_id);
CREATE INDEX IF NOT EXISTS idx_historique_statut_validation ON historique_commandes(statut_validation);
CREATE INDEX IF NOT EXISTS idx_historique_date_creation ON historique_commandes(date_creation);
CREATE INDEX IF NOT EXISTS idx_historique_type_action ON historique_commandes(type_action);

-- --------------------------------------------------------------------------
-- TABLE : charges
-- --------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS charges (
    id              SERIAL PRIMARY KEY,
    couturier_id    INTEGER NOT NULL,
    salon_id        VARCHAR(50) NULL,
    type            VARCHAR(20) NOT NULL CHECK (type IN ('Salaire','Ponctuelle','Fixe','Commande')),
    categorie       VARCHAR(50) NOT NULL,
    description     TEXT,
    montant         DECIMAL(12,2) NOT NULL CHECK (montant >= 0),
    date_charge     DATE NOT NULL,
    date_creation   TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    reference       VARCHAR(100),
    commande_id     INTEGER NULL,
    employe_id      INTEGER NULL,
    fichier_justificatif VARCHAR(500),
    FOREIGN KEY (couturier_id) REFERENCES couturiers(id) ON DELETE CASCADE ON UPDATE CASCADE,
    FOREIGN KEY (commande_id) REFERENCES commandes(id) ON DELETE SET NULL ON UPDATE CASCADE,
    FOREIGN KEY (employe_id) REFERENCES couturiers(id) ON DELETE SET NULL ON UPDATE CASCADE,
    FOREIGN KEY (salon_id) REFERENCES salons(salon_id) ON DELETE SET NULL ON UPDATE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_charges_couturier ON charges(couturier_id);
CREATE INDEX IF NOT EXISTS idx_charges_salon ON charges(salon_id);
CREATE INDEX IF NOT EXISTS idx_charges_type ON charges(type);
CREATE INDEX IF NOT EXISTS idx_charges_date ON charges(date_charge);
CREATE INDEX IF NOT EXISTS idx_charges_commande ON charges(commande_id);
CREATE INDEX IF NOT EXISTS idx_charges_employe ON charges(employe_id);

-- --------------------------------------------------------------------------
-- TABLE : charge_documents (fichiers liés aux charges)
-- --------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS charge_documents (
    id           SERIAL PRIMARY KEY,
    charge_id    INTEGER NOT NULL,
    salon_id     VARCHAR(50) NULL,
    file_path    VARCHAR(500) NOT NULL,
    file_data    BYTEA,
    file_name    VARCHAR(255) NOT NULL,
    file_size    BIGINT,
    mime_type    VARCHAR(100),
    uploaded_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    uploaded_by  INTEGER NULL,
    description  TEXT,
    FOREIGN KEY (charge_id) REFERENCES charges(id) ON DELETE CASCADE ON UPDATE CASCADE,
    FOREIGN KEY (uploaded_by) REFERENCES couturiers(id) ON DELETE SET NULL ON UPDATE CASCADE,
    FOREIGN KEY (salon_id) REFERENCES salons(salon_id) ON DELETE SET NULL ON UPDATE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_charge_documents_charge ON charge_documents(charge_id);
CREATE INDEX IF NOT EXISTS idx_charge_documents_salon ON charge_documents(salon_id);
CREATE INDEX IF NOT EXISTS idx_charge_documents_uploaded ON charge_documents(uploaded_at);

-- --------------------------------------------------------------------------
-- TABLE : app_logo (un logo par salon)
-- --------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS app_logo (
    salon_id    VARCHAR(50) PRIMARY KEY,
    logo_data   BYTEA NOT NULL,
    logo_name   VARCHAR(255) NOT NULL,
    mime_type   VARCHAR(100) NOT NULL,
    file_size   BIGINT NOT NULL,
    uploaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    uploaded_by INTEGER NULL,
    description VARCHAR(255),
    FOREIGN KEY (salon_id) REFERENCES salons(salon_id) ON DELETE CASCADE ON UPDATE CASCADE,
    FOREIGN KEY (uploaded_by) REFERENCES couturiers(id) ON DELETE SET NULL ON UPDATE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_app_logo_uploaded_by ON app_logo(uploaded_by);
CREATE INDEX IF NOT EXISTS idx_app_logo_uploaded_at ON app_logo(uploaded_at);

-- --------------------------------------------------------------------------
-- TABLE : rappels_livraison (historique des rappels 2 jours avant livraison)
-- --------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS rappels_livraison (
    id              SERIAL PRIMARY KEY,
    commande_id     INTEGER NOT NULL REFERENCES commandes(id) ON DELETE CASCADE,
    couturier_id    INTEGER NOT NULL REFERENCES couturiers(id) ON DELETE CASCADE,
    date_livraison  DATE NOT NULL,
    date_envoi      TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (commande_id, date_livraison)
);

CREATE INDEX IF NOT EXISTS idx_rappels_commande ON rappels_livraison(commande_id);
CREATE INDEX IF NOT EXISTS idx_rappels_date_livraison ON rappels_livraison(date_livraison);

-- --------------------------------------------------------------------------
-- FK retour sur salons.admin_id (créée après couturiers)
-- --------------------------------------------------------------------------
ALTER TABLE salons
    ADD CONSTRAINT IF NOT EXISTS fk_salons_admin_id
    FOREIGN KEY (admin_id) REFERENCES couturiers(id)
    ON DELETE SET NULL ON UPDATE CASCADE;

-- --------------------------------------------------------------------------
-- Fonction utilitaire : générer le prochain salon_id
-- --------------------------------------------------------------------------
CREATE OR REPLACE FUNCTION generer_prochain_salon_id()
RETURNS VARCHAR(50) AS $$
DECLARE
    next_num INTEGER;
    new_id   VARCHAR(50);
BEGIN
    SELECT COALESCE(MAX(CAST(SUBSTRING(salon_id FROM '_(.+)$') AS INTEGER)), -1) + 1
    INTO next_num
    FROM salons
    WHERE salon_id LIKE 'Jaind_%';

    new_id := 'Jaind_' || LPAD(next_num::TEXT, 3, '0');
    RETURN new_id;
END;
$$ LANGUAGE plpgsql;

-- --------------------------------------------------------------------------
-- Vérifications / infos
-- --------------------------------------------------------------------------
SELECT table_name FROM information_schema.tables WHERE table_schema = 'public' AND table_type = 'BASE TABLE' ORDER BY table_name;

DO $$
BEGIN
    RAISE NOTICE '✅ Schéma db_couturier créé. Tables : salons, couturiers, clients, commandes, historique_commandes, charges, charge_documents, app_logo, rappels_livraison';
END $$;

