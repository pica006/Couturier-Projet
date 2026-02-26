"""
Modèle de gestion de la base de données (Model dans MVC)
"""
from typing import Optional, Dict, List, Tuple
from datetime import datetime

# Support multi-SGBD: PostgreSQL (legacy) et MySQL (XAMPP)
try:
    import mysql.connector  # type: ignore
    from mysql.connector import Error as MySQLError  # type: ignore
except Exception:
    mysql = None  # type: ignore
    MySQLError = Exception  # type: ignore

try:
    import psycopg2  # type: ignore
    from psycopg2 import Error as PGError  # type: ignore
except Exception:
    psycopg2 = None  # type: ignore
    PGError = Exception  # type: ignore

"""#-----------------------------------------
-- Ajouter TOUTES les colonnes nécessaires en une fois
ALTER TABLE commandes
ADD COLUMN IF NOT EXISTS fabric_image_path VARCHAR(500) AFTER statut,
ADD COLUMN IF NOT EXISTS fabric_image LONGBLOB AFTER fabric_image_path,
ADD COLUMN IF NOT EXISTS fabric_image_name VARCHAR(255) AFTER fabric_image,
ADD COLUMN IF NOT EXISTS model_type VARCHAR(20) DEFAULT 'simple' AFTER fabric_image_name,
ADD COLUMN IF NOT EXISTS model_image_path VARCHAR(500) AFTER model_type,
ADD COLUMN IF NOT EXISTS model_image LONGBLOB AFTER model_image_path,
ADD COLUMN IF NOT EXISTS model_image_name VARCHAR(255) AFTER model_image;
#--------------------------------------------
"""

class DatabaseConnection:
    """Classe pour gérer la connexion à la base de données"""
    
    def __init__(self, db_type: str, config: Dict):
        """
        Initialise la connexion
        
        Args:
            db_type: Type de base de données ('postgresql')
            config: Configuration de connexion
        """
        self.db_type = db_type
        self.config = config
        self.connection = None
        
    def connect(self) -> bool:
        """
        Établit la connexion à la base de données
        
        Returns:
            True si succès, False sinon
        """
        try:
            if self.db_type == 'postgresql':
                if psycopg2 is None:
                    print("psycopg2 non installé")
                    return False
                conn_params = {
                    'host': self.config['host'],
                    'port': int(self.config.get('port', 5432)),
                    'database': self.config['database'],
                    'user': self.config['user'],
                    'password': self.config['password']
                }
                # SSL requis pour Render PostgreSQL
                if self.config.get('sslmode'):
                    conn_params['sslmode'] = self.config['sslmode']
                self.connection = psycopg2.connect(**conn_params)
                return True
            elif self.db_type == 'mysql':
                if mysql is None:
                    print("mysql-connector-python non installé")
                    return False
                self.connection = mysql.connector.connect(
                    host=self.config['host'],
                    port=int(self.config['port']),
                    database=self.config['database'],
                    user=self.config['user'],
                    password=self.config['password']
                )
                return True
            else:
                print(f"Type de base de données non supporté: {self.db_type}")
                return False
        except (MySQLError, PGError, Exception) as e:
            print(f"Erreur de connexion: {e}")
            return False
    
    def disconnect(self):
        """Ferme la connexion"""
        if self.connection:
            self.connection.close()
            self.connection = None
    
    def get_connection(self):
        """Retourne l'objet de connexion"""
        return self.connection
    
    def is_connected(self) -> bool:
        """Vérifie si la connexion est active"""
        if self.connection is None:
            return False
        # mysql-connector n'a pas l'attribut 'closed' comme psycopg2
        try:
            if hasattr(self.connection, 'is_connected'):
                return bool(self.connection.is_connected())
            return not getattr(self.connection, 'closed', True)
        except Exception:
            return False


class CouturierModel:
    """Modèle pour la gestion des couturiers"""
    
    def __init__(self, db_connection: DatabaseConnection):
        self.db = db_connection
    
    def verifier_code(self, code_couturier: str) -> Tuple[bool, Optional[Dict]]:
        """
        Vérifie si un code couturier existe et récupère ses données
        
        POURQUOI ? Pour chercher un couturier dans la base par son code
        COMMENT ? Requête SQL SELECT avec WHERE code_couturier = ...
        
        Args:
            code_couturier: Code à vérifier (ex: COUT001)
            
        Returns:
            Tuple (existe, données)
            - existe : True si le code existe, False sinon
            - données : Dictionnaire avec toutes les infos du couturier (incluant le password hashé)
        
        IMPORTANT : On récupère aussi le PASSWORD pour le vérifier après !
        """
        try:
            # Créer un curseur pour exécuter la requête SQL
            cursor = self.db.get_connection().cursor()
            
            # Requête SQL pour chercher le couturier
            # IMPORTANT : On récupère aussi le password, le role, le salon_id et le statut actif
            query = """
                SELECT id, code_couturier, password, nom, prenom, email, telephone, role, salon_id, actif
                FROM couturiers 
                WHERE code_couturier = %s
            """
            
            # Exécuter la requête avec le code fourni
            # %s est remplacé par code_couturier (protection contre SQL injection)
            cursor.execute(query, (code_couturier,))
            
            # Récupérer le résultat (une seule ligne)
            result = cursor.fetchone()
            
            # Fermer le curseur
            cursor.close()
            
            # Si un résultat a été trouvé
            if result:
                # Créer un dictionnaire avec toutes les données
                salon_id = result[8] if len(result) > 8 else None
                role = result[7] if len(result) > 7 else 'employe'
                actif = bool(result[9]) if len(result) > 9 else True
                user_id = result[0]
                
                return True, {
                    'id': user_id,                  # ID du couturier
                    'code_couturier': result[1],    # Code (ex: COUT001)
                    'password': result[2],          # Hash du mot de passe
                    'nom': result[3],               # Nom
                    'prenom': result[4],            # Prénom
                    'email': result[5],             # Email
                    'telephone': result[6],         # Téléphone
                    'role': role,                   # Role (admin ou employe)
                    'salon_id': salon_id,           # ID du salon
                    'actif': actif                  # Statut actif / désactivé
                }
            
            # Si aucun résultat trouvé
            return False, None
            
        except (MySQLError, PGError, Exception) as e:
            # En cas d'erreur SQL
            print(f"Erreur vérification: {e}")
            return False, None
    
    def creer_tables(self) -> bool:
        """
        Crée la table couturiers si elle n'existe pas
        
        POURQUOI ? Pour initialiser la base de données
        QUAND ? Appelé automatiquement lors de la première connexion
        
        IMPORTANT : La table inclut maintenant la colonne PASSWORD !
        """
        try:
            cursor = self.db.get_connection().cursor()
            
            if self.db.db_type == 'mysql':
                cursor.execute(
                    """
                    CREATE TABLE IF NOT EXISTS couturiers (
                        id INT AUTO_INCREMENT PRIMARY KEY,
                        code_couturier VARCHAR(50) UNIQUE NOT NULL,
                        password VARCHAR(255) NOT NULL,
                        nom VARCHAR(100) NOT NULL,
                        prenom VARCHAR(100) NOT NULL,
                        email VARCHAR(150),
                        telephone VARCHAR(20),
                        role ENUM('admin', 'employe') NOT NULL DEFAULT 'employe',
                        salon_id VARCHAR(50) NULL COMMENT 'ID du salon auquel appartient cet utilisateur',
                        actif TINYINT(1) NOT NULL DEFAULT 1 COMMENT '1 = actif, 0 = désactivé',
                        date_creation TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        INDEX idx_salon (salon_id)
                    )
                    """
                )
                # S'assurer que la colonne actif existe aussi sur une base déjà créée
                # MySQL ne supporte pas IF NOT EXISTS dans ALTER TABLE, on gère l'erreur
                try:
                    cursor.execute(
                        """
                        ALTER TABLE couturiers
                        ADD COLUMN actif TINYINT(1) NOT NULL DEFAULT 1 COMMENT '1 = actif, 0 = désactivé'
                        """
                    )
                except (MySQLError, PGError, Exception):
                    # La colonne existe déjà, on ignore l'erreur
                    pass
            else:
                # PostgreSQL
                cursor.execute(
                    """
                    CREATE TABLE IF NOT EXISTS couturiers (
                        id SERIAL PRIMARY KEY,
                        code_couturier VARCHAR(50) UNIQUE NOT NULL,
                        password VARCHAR(255) NOT NULL,
                        nom VARCHAR(100) NOT NULL,
                        prenom VARCHAR(100) NOT NULL,
                        email VARCHAR(150),
                        telephone VARCHAR(20),
                        role VARCHAR(20) NOT NULL DEFAULT 'employe' CHECK (role IN ('admin', 'employe')),
                        salon_id VARCHAR(50) NULL,
                        actif BOOLEAN NOT NULL DEFAULT TRUE,
                        date_creation TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                    """
                )
                # Index pour PostgreSQL
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_couturiers_salon ON couturiers(salon_id)")
                # S'assurer que la colonne actif existe aussi sur une base déjà créée
                cursor.execute(
                    """
                    ALTER TABLE couturiers
                    ADD COLUMN IF NOT EXISTS actif BOOLEAN NOT NULL DEFAULT TRUE
                    """
                )
            
            self.db.get_connection().commit()
            cursor.close()
            return True
        except (MySQLError, PGError, Exception) as e:
            print(f"Erreur création tables: {e}")
            return False
    
    def lister_tous_couturiers(self, salon_id: Optional[str] = None) -> List[Dict]:
        """Liste tous les couturiers (optionnellement filtrés par salon)"""
        try:
            cursor = self.db.get_connection().cursor()
            if salon_id:
                query = """
                    SELECT id, code_couturier, nom, prenom, email, telephone, role, salon_id, actif, date_creation
                    FROM couturiers 
                    WHERE salon_id = %s
                    ORDER BY nom, prenom
                """
                cursor.execute(query, (salon_id,))
            else:
                query = """
                    SELECT id, code_couturier, nom, prenom, email, telephone, role, salon_id, actif, date_creation
                    FROM couturiers 
                    ORDER BY nom, prenom
                """
                cursor.execute(query)
            results = cursor.fetchall()
            cursor.close()
            
            couturiers = []
            for row in results:
                couturiers.append({
                    'id': row[0],
                    'code_couturier': row[1],
                    'nom': row[2],
                    'prenom': row[3],
                    'email': row[4],
                    'telephone': row[5],
                    'role': row[6] if len(row) > 6 else 'employe',
                    'salon_id': row[7] if len(row) > 7 else None,
                    'actif': bool(row[8]) if len(row) > 8 else True,
                    'date_creation': row[9] if len(row) > 9 else None
                })
            return couturiers
        except (MySQLError, PGError, Exception) as e:
            print(f"Erreur liste couturiers: {e}")
            return []
    
    def creer_utilisateur(self, code_couturier: str, password: str, nom: str, prenom: str,
                          role: str = 'employe', email: Optional[str] = None,
                          telephone: Optional[str] = None, salon_id: Optional[str] = None) -> Optional[int]:
        """
        Crée un nouvel utilisateur dans la base de données (multi-tenant)
        
        Args:
            code_couturier: Code unique de connexion (ex: COUT001)
            password: Mot de passe en clair (sera stocké tel quel)
            nom: Nom de l'utilisateur
            prenom: Prénom de l'utilisateur
            role: Rôle de l'utilisateur ('admin' ou 'employe')
            email: Email (optionnel)
            telephone: Téléphone (optionnel)
            salon_id: ID du salon (si None, sera assigné automatiquement)
            
        Returns:
            ID de l'utilisateur créé ou None si erreur
        """
        try:
            # Vérifier que le code n'existe pas déjà
            existe, _ = self.verifier_code(code_couturier)
            if existe:
                return None  # Code déjà existant
            
            # Vérifier que le rôle est valide
            if role not in ['admin', 'employe']:
                role = 'employe'
            
            cursor = self.db.get_connection().cursor()
            
            # Insérer l'utilisateur (actif par défaut)
            if self.db.db_type == 'mysql':
                query = """
                    INSERT INTO couturiers (code_couturier, password, nom, prenom, role, email, telephone, salon_id, actif)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, 1)
                """
                cursor.execute(query, (code_couturier, password, nom, prenom, role, email, telephone, salon_id))
                user_id = cursor.lastrowid
            else:
                query = """
                    INSERT INTO couturiers (code_couturier, password, nom, prenom, role, email, telephone, salon_id, actif)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, TRUE) RETURNING id
                """
                cursor.execute(query, (code_couturier, password, nom, prenom, role, email, telephone, salon_id))
                user_id = cursor.fetchone()[0]
            
            # Si c'est un admin et qu'il n'a pas de salon_id, lui assigner son propre id
            if role == 'admin' and not salon_id:
                cursor.execute("UPDATE couturiers SET salon_id = %s WHERE id = %s", (user_id, user_id))
            
            self.db.get_connection().commit()
            cursor.close()
            return user_id
        except (MySQLError, PGError, Exception) as e:
            print(f"Erreur création utilisateur: {e}")
            return None

    def mettre_a_jour_statut_actif(self, user_id: int, actif: bool) -> bool:
        """
        Active ou désactive un utilisateur.

        Args:
            user_id: ID du couturier
            actif: True pour activer, False pour désactiver
        """
        try:
            cursor = self.db.get_connection().cursor()
            if self.db.db_type == 'mysql':
                query = "UPDATE couturiers SET actif = %s WHERE id = %s"
                cursor.execute(query, (1 if actif else 0, user_id))
            else:
                query = "UPDATE couturiers SET actif = %s WHERE id = %s"
                cursor.execute(query, (actif, user_id))

            self.db.get_connection().commit()
            cursor.close()
            return True
        except (MySQLError, PGError, Exception) as e:
            print(f"Erreur mise à jour statut actif utilisateur {user_id}: {e}")
            return False
    
    def reinitialiser_mot_de_passe(self, couturier_id: int, nouveau_password: str) -> bool:
        """
        Réinitialise le mot de passe d'un utilisateur
        
        Args:
            couturier_id: ID de l'utilisateur
            nouveau_password: Nouveau mot de passe en clair
            
        Returns:
            True si succès, False sinon
        """
        try:
            cursor = self.db.get_connection().cursor()
            query = "UPDATE couturiers SET password = %s WHERE id = %s"
            cursor.execute(query, (nouveau_password, couturier_id))
            self.db.get_connection().commit()
            cursor.close()
            return True
        except (MySQLError, PGError, Exception) as e:
            print(f"Erreur réinitialisation mot de passe: {e}")
            return False
    
    def modifier_role(self, couturier_id: int, nouveau_role: str) -> bool:
        """
        Modifie le rôle d'un utilisateur
        
        Args:
            couturier_id: ID de l'utilisateur
            nouveau_role: Nouveau rôle ('admin' ou 'employe')
            
        Returns:
            True si succès, False sinon
        """
        try:
            # Vérifier que le rôle est valide
            if nouveau_role not in ['admin', 'employe']:
                return False
            
            cursor = self.db.get_connection().cursor()
            query = "UPDATE couturiers SET role = %s WHERE id = %s"
            cursor.execute(query, (nouveau_role, couturier_id))
            self.db.get_connection().commit()
            cursor.close()
            return True
        except (MySQLError, PGError, Exception) as e:
            print(f"Erreur modification rôle: {e}")
            return False
    
    def supprimer_utilisateur(self, couturier_id: int) -> bool:
        """
        Supprime un utilisateur (avec vérification de sécurité)
        
        Args:
            couturier_id: ID de l'utilisateur à supprimer
            
        Returns:
            True si succès, False sinon
        """
        try:
            cursor = self.db.get_connection().cursor()
            query = "DELETE FROM couturiers WHERE id = %s"
            cursor.execute(query, (couturier_id,))
            self.db.get_connection().commit()
            cursor.close()
            return True
        except (MySQLError, PGError, Exception) as e:
            print(f"Erreur suppression utilisateur: {e}")
            return False


class ClientModel:
    """Modèle pour la gestion des clients"""
    
    def __init__(self, db_connection: DatabaseConnection):
        self.db = db_connection
    
    def creer_tables(self) -> bool:
        """Crée les tables clients et commandes"""
        try:
            cursor = self.db.get_connection().cursor()
            
            if self.db.db_type == 'mysql':
                cursor.execute(
                    """
                    CREATE TABLE IF NOT EXISTS clients (
                        id INT AUTO_INCREMENT PRIMARY KEY,
                        couturier_id INT,
                        nom VARCHAR(100) NOT NULL,
                        prenom VARCHAR(100) NOT NULL,
                        telephone VARCHAR(20) NOT NULL,
                        email VARCHAR(150),
                        date_creation TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY (couturier_id) REFERENCES couturiers(id)
                    )
                    """
                )
                cursor.execute(
                    """
                    CREATE TABLE IF NOT EXISTS commandes (
                        id INT AUTO_INCREMENT PRIMARY KEY,
                        client_id INT,
                        couturier_id INT,
                        categorie VARCHAR(20) NOT NULL,
                        sexe VARCHAR(20) NOT NULL,
                        modele VARCHAR(100) NOT NULL,
                        mesures JSON NOT NULL,
                        prix_total DECIMAL(10, 2) NOT NULL,
                        avance DECIMAL(10, 2) NOT NULL,
                        reste DECIMAL(10, 2) NOT NULL,
                        date_livraison DATE,
                        statut VARCHAR(50) DEFAULT 'En cours',
                        fabric_image_path VARCHAR(500),
                        fabric_image LONGBLOB,
                        fabric_image_name VARCHAR(255),
                        model_type VARCHAR(20) DEFAULT 'simple',
                        model_image_path VARCHAR(500),
                        model_image LONGBLOB,
                        model_image_name VARCHAR(255),
                        date_creation TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY (client_id) REFERENCES clients(id),
                        FOREIGN KEY (couturier_id) REFERENCES couturiers(id)
                    )
                    """
                )
            else:
                # PostgreSQL
                cursor.execute(
                    """
                    CREATE TABLE IF NOT EXISTS clients (
                        id SERIAL PRIMARY KEY,
                        couturier_id INTEGER REFERENCES couturiers(id),
                        nom VARCHAR(100) NOT NULL,
                        prenom VARCHAR(100) NOT NULL,
                        telephone VARCHAR(20) NOT NULL,
                        email VARCHAR(150),
                        date_creation TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                    """
                )
                cursor.execute(
                    """
                    CREATE TABLE IF NOT EXISTS commandes (
                        id SERIAL PRIMARY KEY,
                        client_id INTEGER REFERENCES clients(id),
                        couturier_id INTEGER REFERENCES couturiers(id),
                        categorie VARCHAR(20) NOT NULL,
                        sexe VARCHAR(20) NOT NULL,
                        modele VARCHAR(100) NOT NULL,
                        mesures JSONB NOT NULL,
                        prix_total DECIMAL(10, 2) NOT NULL,
                        avance DECIMAL(10, 2) NOT NULL,
                        reste DECIMAL(10, 2) NOT NULL,
                        date_livraison DATE,
                        statut VARCHAR(50) DEFAULT 'En cours',
                        fabric_image_path VARCHAR(500),
                        fabric_image BYTEA,
                        fabric_image_name VARCHAR(255),
                        model_type VARCHAR(20) DEFAULT 'simple',
                        model_image_path VARCHAR(500),
                        model_image BYTEA,
                        model_image_name VARCHAR(255),
                        date_creation TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                    """
                )
            
            self.db.get_connection().commit()
            cursor.close()
            return True
        except (MySQLError, PGError, Exception) as e:
            print(f"Erreur création tables: {e}")
            return False
    
    def ajouter_client(self, couturier_id: int, nom: str, prenom: str, 
                       telephone: str, email: Optional[str] = None) -> Optional[int]:
        """
        Ajoute un nouveau client
        
        Returns:
            ID du client créé ou None
        """
        try:
            cursor = self.db.get_connection().cursor()
            if self.db.db_type == 'mysql':
                query = (
                    "INSERT INTO clients (couturier_id, nom, prenom, telephone, email) "
                    "VALUES (%s, %s, %s, %s, %s)"
                )
                cursor.execute(query, (couturier_id, nom, prenom, telephone, email))
                client_id = cursor.lastrowid
            else:
                query = """
                    INSERT INTO clients (couturier_id, nom, prenom, telephone, email)
                    VALUES (%s, %s, %s, %s, %s)
                    RETURNING id
                """
                cursor.execute(query, (couturier_id, nom, prenom, telephone, email))
                client_id = cursor.fetchone()[0]
            self.db.get_connection().commit()
            cursor.close()
            return client_id
        except Error as e:
            print(f"Erreur ajout client: {e}")
            return None
    
    def rechercher_client(self, couturier_id: int, telephone: str) -> Optional[Dict]:
        """Recherche un client par téléphone"""
        try:
            cursor = self.db.get_connection().cursor()
            query = """
                SELECT id, nom, prenom, telephone, email
                FROM clients
                WHERE couturier_id = %s AND telephone = %s
            """
            cursor.execute(query, (couturier_id, telephone))
            result = cursor.fetchone()
            cursor.close()
            
            if result:
                return {
                    'id': result[0],
                    'nom': result[1],
                    'prenom': result[2],
                    'telephone': result[3],
                    'email': result[4]
                }
            return None
        except Error as e:
            print(f"Erreur recherche client: {e}")
            return None


class CommandeModel:
    """Modèle pour la gestion des commandes"""
    
    def __init__(self, db_connection: DatabaseConnection):
        self.db = db_connection



    def ajouter_commande(self, client_id: int, couturier_id: int, 
                         categorie: str, sexe: str, modele: str,
                         mesures: Dict, prix_total: float, avance: float,
                         date_livraison: Optional[str] = None,
                         fabric_image_path: Optional[str] = None,
                         model_type: Optional[str] = None,
                         model_image_path: Optional[str] = None,
                         fabric_image: Optional[bytes] = None,
                         fabric_image_name: Optional[str] = None,
                         model_image: Optional[bytes] = None,
                         model_image_name: Optional[str] = None,
                         reste: Optional[float] = None) -> Optional[int]:
        """
        Ajoute une nouvelle commande dans la base de données.

        Args:
            client_id (int): ID du client
            couturier_id (int): ID du couturier
            categorie (str): Catégorie (ex: costume, robe)
            sexe (str): Sexe concerné
            modele (str): Nom ou référence du modèle
            mesures (Dict): Dictionnaire des mesures (sera stocké en JSON)
            prix_total (float): Prix total du modèle
            avance (float): Montant versé
            date_livraison (str, optional): Date prévue de livraison
            fabric_image_path (str, optional): Chemin de l'image du tissu
            model_type (str, optional): Type ou chemin du modèle
            model_image_path (str, optional): Chemin de l'image du modèle de vêtement
            fabric_image (bytes, optional): Image du tissu en binaire
            fabric_image_name (str, optional): Nom du fichier de l'image du tissu
            model_image (bytes, optional): Image du modèle en binaire
            model_image_name (str, optional): Nom du fichier de l'image du modèle

        Returns:
            int | None: ID de la commande créée ou None si erreur
        """
        try:
            import json
            connection = self.db.get_connection()
            cursor = connection.cursor()

            # Utiliser le reste passé en paramètre, sinon le calculer
            if reste is None:
                reste = prix_total - avance
            else:
                # S'assurer que le reste est cohérent
                reste = max(0.0, float(reste))
            
            statut = "En cours"

            # Requête SQL adaptée à ta table actuelle
            if self.db.db_type == 'mysql':
                query = (
                    "INSERT INTO commandes "
                    "(client_id, couturier_id, categorie, sexe, modele, mesures, "
                    " prix_total, avance, reste, date_livraison, fabric_image_path, fabric_image, fabric_image_name, "
                    " model_type, model_image_path, model_image, model_image_name, statut) "
                    "VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)"
                )

                cursor.execute(query, (
                    client_id, couturier_id, categorie, sexe, modele,
                    json.dumps(mesures), prix_total, avance, reste, 
                    date_livraison, fabric_image_path, fabric_image, fabric_image_name,
                    model_type, model_image_path, model_image, model_image_name, statut
                ))

                commande_id = cursor.lastrowid

            else:
                # Version PostgreSQL (si jamais tu l'utilises aussi)
                query = """
                    INSERT INTO commandes 
                    (client_id, couturier_id, categorie, sexe, modele, mesures,
                     prix_total, avance, reste, date_livraison, fabric_image_path, fabric_image, fabric_image_name,
                     model_type, model_image_path, model_image, model_image_name, statut)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    RETURNING id
                """

                cursor.execute(query, (
                    client_id, couturier_id, categorie, sexe, modele,
                    json.dumps(mesures), prix_total, avance, reste,
                    date_livraison, fabric_image_path, fabric_image, fabric_image_name,
                    model_type, model_image_path, model_image, model_image_name, statut
                ))

                commande_id = cursor.fetchone()[0]

            connection.commit()
            cursor.close()
            return commande_id

        except (MySQLError, PGError, Exception) as e:
            print(f"❌ Erreur ajout commande: {e}")
            return None






        


    def obtenir_commande(self, commande_id: int) -> Optional[Dict]:
        """Récupère les détails d'une commande"""
        try:
            cursor = self.db.get_connection().cursor()
            # Utiliser des colonnes explicites au lieu de c.* pour éviter les problèmes d'ordre
            query = """
                SELECT 
                    c.id, c.client_id, c.couturier_id,
                    c.categorie, c.sexe, c.modele, c.mesures,
                    c.prix_total, c.avance, c.reste,
                    c.date_livraison, c.statut,
                    c.fabric_image_path, c.fabric_image, c.fabric_image_name,
                    c.model_type, c.model_image_path, c.model_image, c.model_image_name,
                    c.date_creation,
                    c.pdf_data, c.pdf_name, c.pdf_path,
                    cl.nom as client_nom, cl.prenom as client_prenom, 
                    cl.telephone as client_telephone, cl.email as client_email,
                    co.nom as couturier_nom, co.prenom as couturier_prenom, 
                    co.code_couturier as couturier_code
                FROM commandes c
                JOIN clients cl ON c.client_id = cl.id
                JOIN couturiers co ON c.couturier_id = co.id
                WHERE c.id = %s
            """
            cursor.execute(query, (commande_id,))
            result = cursor.fetchone()
            cursor.close()
            
            if result:
                # Compter le nombre de colonnes pour gérer la compatibilité
                num_cols = len(result)
                data = {
                    'id': result[0],
                    'client_id': result[1],
                    'couturier_id': result[2],
                    'categorie': result[3],
                    'sexe': result[4],
                    'modele': result[5],
                    'mesures': result[6],
                    'prix_total': float(result[7]),
                    'avance': float(result[8]),
                    'reste': float(result[9]),
                    'date_livraison': result[10],
                    'statut': result[11],
                    'fabric_image_path': result[12],
                    'fabric_image': result[13],
                    'fabric_image_name': result[14],
                    'model_type': result[15],
                    'model_image_path': result[16],
                    'model_image': result[17],
                    'model_image_name': result[18],
                    'date_creation': result[19],
                }
                
                # Ajouter les données PDF si disponibles (colonnes 20-22)
                if num_cols > 22:
                    data['pdf_data'] = result[20]
                    data['pdf_name'] = result[21]
                    data['pdf_path'] = result[22]
                    # Données client et couturier (colonnes 23-29)
                    data['client_nom'] = result[23]
                    data['client_prenom'] = result[24]
                    data['client_telephone'] = result[25]
                    data['client_email'] = result[26]
                    data['couturier_nom'] = result[27]
                    data['couturier_prenom'] = result[28]
                    data['couturier_code'] = result[29]
                else:
                    # Ancien format sans PDF (colonnes 20-26)
                    data['pdf_data'] = None
                    data['pdf_name'] = None
                    data['pdf_path'] = None
                    data['client_nom'] = result[20] if num_cols > 20 else None
                    data['client_prenom'] = result[21] if num_cols > 21 else None
                    data['client_telephone'] = result[22] if num_cols > 22 else None
                    data['client_email'] = result[23] if num_cols > 23 else None
                    data['couturier_nom'] = result[24] if num_cols > 24 else None
                    data['couturier_prenom'] = result[25] if num_cols > 25 else None
                    data['couturier_code'] = result[26] if num_cols > 26 else None
                # Normaliser le champ mesures: parser JSON si MySQL retourne une string
                try:
                    import json as _json
                    if isinstance(data['mesures'], str):
                        data['mesures'] = _json.loads(data['mesures'])
                except Exception:
                    pass
                return data
            return None
        except (MySQLError, PGError, Exception) as e:
            print(f"Erreur récupération commande: {e}")
            return None
    
    def lister_commandes(self, couturier_id: Optional[int] = None, 
                         tous_les_couturiers: bool = False,
                         salon_id: Optional[str] = None) -> List[Dict]:
        """
        Liste les commandes d'un couturier ou de tous les couturiers (pour admin)
        
        Args:
            couturier_id: ID du couturier (None si admin veut voir tout)
            tous_les_couturiers: Si True, retourne toutes les commandes de tous les couturiers
            
        Returns:
            Liste des commandes
        """
        try:
            cursor = self.db.get_connection().cursor()
            
            if tous_les_couturiers and not salon_id:
                # SUPER_ADMIN : voir toutes les commandes de tous les salons
                query = """
                    SELECT c.id, c.modele, c.prix_total, c.statut, c.date_creation,
                           cl.nom, cl.prenom, c.couturier_id,
                           co.nom as couturier_nom, co.prenom as couturier_prenom, co.salon_id
                    FROM commandes c
                    JOIN clients cl ON c.client_id = cl.id
                    LEFT JOIN couturiers co ON c.couturier_id = co.id
                    ORDER BY c.date_creation DESC
                """
                cursor.execute(query)
            elif tous_les_couturiers and salon_id:
                # SUPER_ADMIN positionné sur un salon précis
                query = """
                    SELECT c.id, c.modele, c.prix_total, c.statut, c.date_creation,
                           cl.nom, cl.prenom, c.couturier_id,
                           co.nom as couturier_nom, co.prenom as couturier_prenom, co.salon_id
                    FROM commandes c
                    JOIN clients cl ON c.client_id = cl.id
                    LEFT JOIN couturiers co ON c.couturier_id = co.id
                    WHERE co.salon_id = %s
                    ORDER BY c.date_creation DESC
                """
                cursor.execute(query, (salon_id,))
            else:
                # Admin/Employé : voir uniquement les commandes de leur salon (ou du couturier)
                if salon_id and couturier_id:
                    # Filtrer par salon_id ET couturier_id
                    query = """
                        SELECT c.id, c.modele, c.prix_total, c.statut, c.date_creation,
                               cl.nom, cl.prenom, c.couturier_id,
                               co.nom as couturier_nom, co.prenom as couturier_prenom, co.salon_id
                        FROM commandes c
                        JOIN clients cl ON c.client_id = cl.id
                        LEFT JOIN couturiers co ON c.couturier_id = co.id
                        WHERE co.salon_id = %s AND c.couturier_id = %s
                        ORDER BY c.date_creation DESC
                    """
                    cursor.execute(query, (salon_id, couturier_id))
                elif salon_id:
                    # Filtrer uniquement par salon_id
                    query = """
                        SELECT c.id, c.modele, c.prix_total, c.statut, c.date_creation,
                               cl.nom, cl.prenom, c.couturier_id,
                               co.nom as couturier_nom, co.prenom as couturier_prenom, co.salon_id
                        FROM commandes c
                        JOIN clients cl ON c.client_id = cl.id
                        LEFT JOIN couturiers co ON c.couturier_id = co.id
                        WHERE co.salon_id = %s
                        ORDER BY c.date_creation DESC
                    """
                    cursor.execute(query, (salon_id,))
                elif couturier_id:
                    # Filtrer uniquement par couturier_id
                    query = """
                        SELECT c.id, c.modele, c.prix_total, c.statut, c.date_creation,
                               cl.nom, cl.prenom
                        FROM commandes c
                        JOIN clients cl ON c.client_id = cl.id
                        WHERE c.couturier_id = %s
                        ORDER BY c.date_creation DESC
                    """
                    cursor.execute(query, (couturier_id,))
                else:
                    # Aucun filtre : retourner liste vide
                    query = """
                        SELECT c.id, c.modele, c.prix_total, c.statut, c.date_creation,
                               cl.nom, cl.prenom
                        FROM commandes c
                        JOIN clients cl ON c.client_id = cl.id
                        WHERE 1=0
                        ORDER BY c.date_creation DESC
                    """
                    cursor.execute(query)
            
            results = cursor.fetchall()
            cursor.close()
            
            commandes = []
            for row in results:
                if tous_les_couturiers:
                    commandes.append({
                        'id': row[0],
                        'modele': row[1],
                        'prix_total': float(row[2]),
                        'statut': row[3],
                        'date_creation': row[4],
                        'client_nom': row[5],
                        'client_prenom': row[6],
                        'couturier_id': row[7],
                        'couturier_nom': row[8],
                        'couturier_prenom': row[9],
                        'salon_id': row[10] if len(row) > 10 else None
                    })
                else:
                    commandes.append({
                        'id': row[0],
                        'modele': row[1],
                        'prix_total': float(row[2]),
                        'statut': row[3],
                        'date_creation': row[4],
                        'client_nom': row[5],
                        'client_prenom': row[6]
                    })
            return commandes
        except (MySQLError, PGError, Exception) as e:
            print(f"Erreur liste commandes: {e}")
            return []
    
    def enregistrer_paiement(self, commande_id: int, couturier_id: int, 
                            montant_paye: float, commentaire: Optional[str] = None) -> Optional[int]:
        """
        Enregistre un paiement pour une commande et crée une entrée dans l'historique
        
        Args:
            commande_id: ID de la commande
            couturier_id: ID du couturier qui enregistre le paiement
            montant_paye: Montant payé
            commentaire: Commentaire optionnel
            
        Returns:
            ID de l'entrée d'historique créée ou None si erreur
        """
        try:
            connection = self.db.get_connection()
            cursor = connection.cursor()
            
            # Récupérer les infos de la commande
            commande = self.obtenir_commande(commande_id)
            if not commande:
                return None
            
            statut_avant = commande.get('statut', 'En cours')
            reste_avant = float(commande.get('reste', 0))
            reste_apres = max(0.0, reste_avant - montant_paye)
            
            # Mettre à jour la commande
            nouvelle_avance = float(commande.get('avance', 0)) + montant_paye
            statut_apres = 'Terminé' if reste_apres <= 0 else statut_avant
            
            update_query = """
                UPDATE commandes 
                SET avance = %s, reste = %s, statut = %s, date_dernier_paiement = NOW()
                WHERE id = %s
            """
            cursor.execute(update_query, (nouvelle_avance, reste_apres, statut_apres, commande_id))
            
            # Créer l'entrée dans l'historique
            hist_query = """
                INSERT INTO historique_commandes 
                (commande_id, couturier_id, type_action, montant_paye, reste_apres_paiement,
                 statut_avant, statut_apres, commentaire, statut_validation)
                VALUES (%s, %s, 'paiement', %s, %s, %s, %s, %s, 'en_attente')
            """
            params = (
                commande_id, couturier_id, montant_paye, reste_apres,
                statut_avant, statut_apres, commentaire
            )
            if self.db.db_type == 'mysql':
                cursor.execute(hist_query, params)
                hist_id = cursor.lastrowid
            else:
                cursor.execute(hist_query + " RETURNING id", params)
                hist_id = cursor.fetchone()[0]
            
            connection.commit()
            cursor.close()
            return hist_id
            
        except (MySQLError, PGError, Exception) as e:
            print(f"Erreur enregistrement paiement: {e}")
            return None
    
    def sauvegarder_pdf_upload(self, commande_id: int, pdf_bytes: bytes, 
                              pdf_filename: str, pdf_path: str) -> bool:
        """
        Sauvegarde un PDF uploadé pour une commande
        
        Args:
            commande_id: ID de la commande
            pdf_bytes: Contenu du PDF en bytes
            pdf_filename: Nom du fichier PDF
            pdf_path: Chemin du fichier PDF
            
        Returns:
            True si succès, False sinon
        """
        try:
            connection = self.db.get_connection()
            cursor = connection.cursor()
            
            query = """
                UPDATE commandes 
                SET pdf_data = %s, pdf_name = %s, pdf_path = %s
                WHERE id = %s
            """
            cursor.execute(query, (pdf_bytes, pdf_filename, pdf_path, commande_id))
            connection.commit()
            cursor.close()
            return True
        except (MySQLError, PGError, Exception) as e:
            print(f"Erreur sauvegarde PDF upload: {e}")
            return False

    def modifier_prix_commande(self, commande_id: int, prix_total: float, 
                               avance: float, reste: Optional[float] = None) -> bool:
        """
        Modifie directement les prix d'une commande (prix_total, avance, reste)
        
        Args:
            commande_id: ID de la commande
            prix_total: Nouveau prix total
            avance: Nouvelle avance
            reste: Nouveau reste (si None, calculé automatiquement)
            
        Returns:
            True si succès, False sinon
        """
        try:
            connection = self.db.get_connection()
            cursor = connection.cursor()
            
            # Calculer le reste si non fourni
            if reste is None:
                reste = max(0.0, prix_total - avance)
            else:
                # S'assurer que le reste est cohérent
                reste = max(0.0, float(reste))
            
            # Mettre à jour la commande
            update_query = """
                UPDATE commandes 
                SET prix_total = %s, avance = %s, reste = %s
                WHERE id = %s
            """
            cursor.execute(update_query, (prix_total, avance, reste, commande_id))
            
            connection.commit()
            cursor.close()
            return True
            
        except (MySQLError, PGError, Exception) as e:
            print(f"Erreur modification prix commande: {e}")
            return False
    
    def demander_fermeture(self, commande_id: int, couturier_id: int, 
                          commentaire: Optional[str] = None) -> Optional[int]:
        """
        Demande la fermeture d'une commande (création d'une entrée en attente de validation)
        
        Args:
            commande_id: ID de la commande
            couturier_id: ID du couturier qui demande la fermeture
            commentaire: Commentaire optionnel
            
        Returns:
            ID de l'entrée d'historique créée ou None si erreur
        """
        try:
            connection = self.db.get_connection()
            cursor = connection.cursor()
            
            # Récupérer les infos de la commande directement depuis la base
            cursor.execute("""
                SELECT prix_total, avance, reste, statut 
                FROM commandes 
                WHERE id = %s
            """, (commande_id,))
            result = cursor.fetchone()
            
            if not result:
                print(f"❌ Commande {commande_id} introuvable")
                cursor.close()
                return None
            
            prix_total = float(result[0]) if result[0] else 0.0
            avance = float(result[1]) if result[1] else 0.0
            reste = float(result[2]) if result[2] else 0.0
            statut_avant = result[3] if result[3] else 'En cours'
            
            # Vérifier que le reste est bien à 0 (avec une petite tolérance pour les erreurs d'arrondi)
            if reste > 0.01:  # Tolérance de 0.01 FCFA pour les erreurs d'arrondi
                print(f"❌ Impossible de fermer la commande {commande_id}: reste = {reste} FCFA (doit être <= 0)")
                cursor.close()
                return None
            
            # Vérifier si une demande existe déjà pour cette commande
            cursor.execute("""
                SELECT id FROM historique_commandes 
                WHERE commande_id = %s 
                  AND type_action = 'fermeture_demande' 
                  AND statut_validation = 'en_attente'
            """, (commande_id,))
            demande_existante = cursor.fetchone()
            
            if demande_existante:
                print(f"⚠️ Une demande de fermeture existe déjà pour la commande {commande_id} (ID demande: {demande_existante[0]})")
                cursor.close()
                # Retourner l'ID de la demande existante avec un indicateur (pas de nouvel envoi)
                return {"id": demande_existante[0], "created": False}
            
            # Créer l'entrée dans l'historique en attente de validation
            hist_query = """
                INSERT INTO historique_commandes 
                (commande_id, couturier_id, type_action, montant_paye, reste_apres_paiement,
                 statut_avant, statut_apres, commentaire, statut_validation)
                VALUES (%s, %s, 'fermeture_demande', 0, %s, %s, 'Livré et payé', %s, 'en_attente')
            """
            params = (commande_id, couturier_id, reste, statut_avant, commentaire)
            if self.db.db_type == 'mysql':
                cursor.execute(hist_query, params)
                hist_id = cursor.lastrowid
            else:
                cursor.execute(hist_query + " RETURNING id", params)
                hist_id = cursor.fetchone()[0]

            connection.commit()
            cursor.close()
            print(f"✅ Demande de fermeture créée avec succès (ID: {hist_id}) pour la commande {commande_id}")
            return {"id": hist_id, "created": True}
            
        except (MySQLError, PGError, Exception) as e:
            import traceback
            error_details = traceback.format_exc()
            print(f"❌ Erreur demande fermeture: {e}")
            print(f"Détails: {error_details}")
            try:
                cursor.close()
            except:
                pass
            return None
    
    def valider_fermeture(self, historique_id: int, admin_id: int, 
                         valide: bool, commentaire_admin: Optional[str] = None) -> bool:
        """
        Valide ou rejette une demande (paiement ou fermeture de commande)
        
        Args:
            historique_id: ID de l'entrée d'historique à valider
            admin_id: ID de l'administrateur qui valide
            valide: True pour valider, False pour rejeter
            commentaire_admin: Commentaire de l'admin
            
        Returns:
            True si succès, False sinon
        """
        try:
            connection = self.db.get_connection()
            cursor = connection.cursor()
            
            # Récupérer l'entrée d'historique avec le type d'action
            cursor.execute("""
                SELECT commande_id, type_action, statut_avant, statut_apres, 
                       montant_paye, reste_apres_paiement
                FROM historique_commandes 
                WHERE id = %s AND statut_validation = 'en_attente'
            """, (historique_id,))
            result = cursor.fetchone()
            
            if not result:
                return False
            
            commande_id = result[0]
            type_action = result[1]
            statut_avant = result[2]
            statut_apres = result[3]
            montant_paye = float(result[4]) if result[4] else 0.0
            reste_apres = float(result[5]) if result[5] else 0.0
            
            statut_validation = 'validee' if valide else 'rejetee'
            
            # Mettre à jour l'historique
            update_hist_query = """
                UPDATE historique_commandes 
                SET statut_validation = %s, admin_validation_id = %s, 
                    date_validation = NOW(), commentaire_admin = %s
                WHERE id = %s
            """
            cursor.execute(update_hist_query, (
                statut_validation, admin_id, commentaire_admin, historique_id
            ))
            
            # Si validé, mettre à jour la commande selon le type d'action
            if valide:
                if type_action == 'paiement':
                    # Mettre à jour les montants de la commande
                    cursor.execute("""
                        SELECT avance, reste FROM commandes WHERE id = %s
                    """, (commande_id,))
                    cmd_result = cursor.fetchone()
                    if cmd_result:
                        nouvelle_avance = float(cmd_result[0]) + montant_paye
                        nouveau_reste = reste_apres
                        nouveau_statut = 'Terminé' if nouveau_reste <= 0 else statut_avant
                        
                        update_cmd_query = """
                            UPDATE commandes 
                            SET avance = %s, reste = %s, statut = %s, 
                                date_dernier_paiement = NOW()
                            WHERE id = %s
                        """
                        cursor.execute(update_cmd_query, (
                            nouvelle_avance, nouveau_reste, nouveau_statut, commande_id
                        ))
                
                elif type_action == 'fermeture_demande':
                    # Fermer la commande - utiliser uniquement le statut (pas est_ouverte)
                    update_cmd_query = """
                        UPDATE commandes 
                        SET statut = 'Livré et payé'
                        WHERE id = %s
                    """
                    cursor.execute(update_cmd_query, (commande_id,))
            else:
                # Si rejeté, on peut éventuellement restaurer l'état précédent
                # Pour l'instant, on laisse la commande dans son état actuel
                pass
            
            connection.commit()
            cursor.close()
            return True
            
        except (MySQLError, PGError, Exception) as e:
            print(f"Erreur validation: {e}")
            return False
    
    def lister_commandes_ouvertes(
        self,
        couturier_id: Optional[int] = None,
        tous_les_couturiers: bool = False,
        salon_id: Optional[str] = None,
    ) -> List[Dict]:
        """Liste les commandes ouvertes (est_ouverte = TRUE), optionnellement filtrées par salon."""
        try:
            cursor = self.db.get_connection().cursor()
            
            if tous_les_couturiers:
                # Vue globale pour un salon (via le couturier)
                base_query = """
                    SELECT c.id, c.modele, c.prix_total, c.avance, c.reste, c.statut, 
                           c.date_creation, c.date_livraison,
                           cl.nom, cl.prenom, c.couturier_id,
                           co.nom as couturier_nom, co.prenom as couturier_prenom,
                           co.salon_id
                    FROM commandes c
                    JOIN clients cl ON c.client_id = cl.id
                    LEFT JOIN couturiers co ON c.couturier_id = co.id
                    WHERE c.est_ouverte = TRUE
                """
                params: list = []
                if salon_id:
                    base_query += " AND co.salon_id = %s"
                    params.append(salon_id)
                base_query += " ORDER BY c.date_creation DESC"
                cursor.execute(base_query, tuple(params))
            else:
                query = """
                    SELECT c.id, c.modele, c.prix_total, c.avance, c.reste, c.statut, 
                           c.date_creation, c.date_livraison,
                           cl.nom, cl.prenom
                    FROM commandes c
                    JOIN clients cl ON c.client_id = cl.id
                    WHERE c.couturier_id = %s AND c.est_ouverte = TRUE
                    ORDER BY c.date_creation DESC
                """
                cursor.execute(query, (couturier_id,))
            
            results = cursor.fetchall()
            cursor.close()
            
            commandes = []
            for row in results:
                if tous_les_couturiers:
                    commandes.append({
                        'id': row[0],
                        'modele': row[1],
                        'prix_total': float(row[2]),
                        'avance': float(row[3]),
                        'reste': float(row[4]),
                        'statut': row[5],
                        'date_creation': row[6],
                        'date_livraison': row[7],
                        'client_nom': row[8],
                        'client_prenom': row[9],
                        'couturier_id': row[10],
                        'couturier_nom': row[11],
                        'couturier_prenom': row[12],
                        'couturier_salon_id': row[13],
                    })
                else:
                    commandes.append({
                        'id': row[0],
                        'modele': row[1],
                        'prix_total': float(row[2]),
                        'avance': float(row[3]),
                        'reste': float(row[4]),
                        'statut': row[5],
                        'date_creation': row[6],
                        'date_livraison': row[7],
                        'client_nom': row[8],
                        'client_prenom': row[9],
                    })
            return commandes
        except (MySQLError, PGError, Exception) as e:
            print(f"Erreur liste commandes ouvertes: {e}")
            return []
    
    def lister_commandes_fermees(
        self,
        couturier_id: Optional[int] = None,
        tous_les_couturiers: bool = False,
        salon_id: Optional[str] = None,
    ) -> List[Dict]:
        """Liste les commandes fermées (est_ouverte = FALSE), filtrables par salon."""
        try:
            cursor = self.db.get_connection().cursor()

            if tous_les_couturiers:
                query = """
                    SELECT c.id, c.modele, c.prix_total, c.avance, c.reste, c.statut, 
                           c.date_creation, c.date_fermeture,
                           cl.nom, cl.prenom, c.couturier_id,
                           co.nom as couturier_nom, co.prenom as couturier_prenom,
                           co.salon_id
                    FROM commandes c
                    JOIN clients cl ON c.client_id = cl.id
                    LEFT JOIN couturiers co ON c.couturier_id = co.id
                    WHERE c.est_ouverte = FALSE
                """
                params: list = []
                if salon_id:
                    query += " AND co.salon_id = %s"
                    params.append(salon_id)
                query += " ORDER BY c.date_fermeture DESC"
                cursor.execute(query, tuple(params))
            else:
                query = """
                    SELECT c.id, c.modele, c.prix_total, c.avance, c.reste, c.statut, 
                           c.date_creation, c.date_fermeture,
                           cl.nom, cl.prenom, co.salon_id
                    FROM commandes c
                    JOIN clients cl ON c.client_id = cl.id
                    LEFT JOIN couturiers co ON c.couturier_id = co.id
                    WHERE c.couturier_id = %s AND c.est_ouverte = FALSE
                """
                params = [couturier_id]
                if salon_id:
                    query += " AND co.salon_id = %s"
                    params.append(salon_id)
                query += " ORDER BY c.date_fermeture DESC"
                cursor.execute(query, tuple(params))

            results = cursor.fetchall()
            cursor.close()

            commandes = []
            for row in results:
                if tous_les_couturiers:
                    commandes.append({
                        'id': row[0],
                        'modele': row[1],
                        'prix_total': float(row[2]),
                        'avance': float(row[3]),
                        'reste': float(row[4]),
                        'statut': row[5],
                        'date_creation': row[6],
                        'date_fermeture': row[7],
                        'client_nom': row[8],
                        'client_prenom': row[9],
                        'couturier_id': row[10],
                        'couturier_nom': row[11],
                        'couturier_prenom': row[12],
                        'couturier_salon_id': row[13],
                    })
                else:
                    commandes.append({
                        'id': row[0],
                        'modele': row[1],
                        'prix_total': float(row[2]),
                        'avance': float(row[3]),
                        'reste': float(row[4]),
                        'statut': row[5],
                        'date_creation': row[6],
                        'date_fermeture': row[7],
                        'client_nom': row[8],
                        'client_prenom': row[9],
                        'couturier_salon_id': row[10],
                    })
            return commandes
        except (MySQLError, PGError, Exception) as e:
            print(f"Erreur liste commandes fermées: {e}")
            return []
    
    def lister_commandes_calendrier(
        self,
        date_debut,
        date_fin,
        couturier_id: Optional[int] = None,
        tous_les_couturiers: bool = False,
        salon_id: Optional[str] = None,
    ) -> List[Dict]:
        """
        Liste les commandes ouvertes avec date_livraison dans la plage donnée (pour le calendrier).
        Retourne les infos nécessaires : id, modele, client, couturier, date_livraison, prix.
        """
        try:
            cursor = self.db.get_connection().cursor()
            if tous_les_couturiers:
                query = """
                    SELECT c.id, c.modele, c.prix_total, c.avance, c.reste, c.statut,
                           c.date_creation, c.date_livraison,
                           cl.nom, cl.prenom, cl.telephone,
                           c.couturier_id, co.nom as couturier_nom, co.prenom as couturier_prenom,
                           co.email as couturier_email, co.telephone as couturier_telephone,
                           co.salon_id as couturier_salon_id
                    FROM commandes c
                    JOIN clients cl ON c.client_id = cl.id
                    LEFT JOIN couturiers co ON c.couturier_id = co.id
                    WHERE c.est_ouverte = TRUE
                      AND c.date_livraison IS NOT NULL
                      AND c.date_livraison >= %s
                      AND c.date_livraison <= %s
                """
                params = [date_debut, date_fin]
                if salon_id:
                    query += " AND co.salon_id = %s"
                    params.append(salon_id)
                query += " ORDER BY c.date_livraison ASC, co.nom, co.prenom"
                cursor.execute(query, tuple(params))
            else:
                query = """
                    SELECT c.id, c.modele, c.prix_total, c.avance, c.reste, c.statut,
                           c.date_creation, c.date_livraison,
                           cl.nom, cl.prenom, cl.telephone,
                           c.couturier_id, co.nom as couturier_nom, co.prenom as couturier_prenom,
                           co.email as couturier_email, co.telephone as couturier_telephone,
                           co.salon_id as couturier_salon_id
                    FROM commandes c
                    JOIN clients cl ON c.client_id = cl.id
                    LEFT JOIN couturiers co ON c.couturier_id = co.id
                    WHERE c.couturier_id = %s
                      AND c.est_ouverte = TRUE
                      AND c.date_livraison IS NOT NULL
                      AND c.date_livraison >= %s
                      AND c.date_livraison <= %s
                """
                params = [couturier_id, date_debut, date_fin]
                if salon_id:
                    query = query.replace(
                        "WHERE c.couturier_id = %s",
                        "WHERE c.couturier_id = %s AND co.salon_id = %s"
                    )
                    params.insert(1, salon_id)
                query += " ORDER BY c.date_livraison ASC"
                cursor.execute(query, tuple(params))
            results = cursor.fetchall()
            cursor.close()
            commandes = []
            for row in results:
                commandes.append({
                    'id': row[0],
                    'modele': row[1],
                    'prix_total': float(row[2]),
                    'avance': float(row[3]),
                    'reste': float(row[4]),
                    'statut': row[5],
                    'date_creation': row[6],
                    'date_livraison': row[7],
                    'client_nom': row[8],
                    'client_prenom': row[9],
                    'client_telephone': row[10],
                    'couturier_id': row[11],
                    'couturier_nom': row[12],
                    'couturier_prenom': row[13],
                    'couturier_email': row[14],
                    'couturier_telephone': row[15] if len(row) > 15 else None,
                    'couturier_salon_id': row[16] if len(row) > 16 else None,
                })
            return commandes
        except (MySQLError, PGError, Exception) as e:
            print(f"Erreur liste commandes calendrier: {e}")
            return []

    def lister_modeles_realises(
        self,
        couturier_id: Optional[int] = None,
        tous_les_couturiers: bool = False,
        salon_id: Optional[str] = None,
        date_debut=None,
        date_fin=None,
    ) -> List[Dict]:
        """
        Liste les modèles réalisés par le salon (agrégés par type de modèle).
        Retourne: modele, categorie, sexe, nb_commandes, ca_total.
        """
        try:
            cursor = self.db.get_connection().cursor()
            where_clauses = ["1=1"]
            params = []
            if salon_id:
                where_clauses.append("co.salon_id = %s")
                params.append(salon_id)
            if couturier_id and not tous_les_couturiers:
                where_clauses.append("c.couturier_id = %s")
                params.append(couturier_id)
            if date_debut:
                where_clauses.append("c.date_creation >= %s")
                params.append(date_debut)
            if date_fin:
                where_clauses.append("c.date_creation <= %s")
                params.append(date_fin)
            where_sql = " AND ".join(where_clauses)
            query = f"""
                SELECT c.modele, c.categorie, c.sexe,
                       COUNT(*) as nb_commandes, COALESCE(SUM(c.prix_total), 0) as ca_total
                FROM commandes c
                LEFT JOIN couturiers co ON c.couturier_id = co.id
                WHERE {where_sql}
                GROUP BY c.modele, c.categorie, c.sexe
                ORDER BY nb_commandes DESC, ca_total DESC
            """
            cursor.execute(query, tuple(params))
            results = cursor.fetchall()
            cursor.close()
            return [
                {
                    "modele": row[0],
                    "categorie": row[1],
                    "sexe": row[2],
                    "nb_commandes": int(row[3]),
                    "ca_total": float(row[4]),
                }
                for row in results
            ]
        except (MySQLError, PGError, Exception) as e:
            print(f"Erreur liste modèles réalisés: {e}")
            return []

    def lister_commandes_avec_images(
        self,
        couturier_id: Optional[int] = None,
        tous_les_couturiers: bool = False,
        salon_id: Optional[str] = None,
        date_debut=None,
        date_fin=None,
    ) -> List[Dict]:
        """
        Liste les commandes ayant au moins une image (fabric ou model).
        Retourne id, modele, client_nom, client_prenom, fabric_image, model_image, etc.
        """
        try:
            cursor = self.db.get_connection().cursor()
            where_clauses = ["(c.fabric_image IS NOT NULL OR c.model_image IS NOT NULL)"]
            params = []
            if salon_id:
                where_clauses.append("co.salon_id = %s")
                params.append(salon_id)
            if couturier_id and not tous_les_couturiers:
                where_clauses.append("c.couturier_id = %s")
                params.append(couturier_id)
            if date_debut:
                where_clauses.append("c.date_creation >= %s")
                params.append(date_debut)
            if date_fin:
                where_clauses.append("c.date_creation <= %s")
                params.append(date_fin)
            where_sql = " AND ".join(where_clauses)
            query = f"""
                SELECT c.id, c.modele, c.categorie, c.sexe, c.prix_total, c.date_creation,
                       cl.nom, cl.prenom,
                       c.fabric_image, c.fabric_image_name,
                       c.model_image, c.model_image_name,
                       co.nom as couturier_nom, co.prenom as couturier_prenom
                FROM commandes c
                JOIN clients cl ON c.client_id = cl.id
                LEFT JOIN couturiers co ON c.couturier_id = co.id
                WHERE {where_sql}
                ORDER BY c.date_creation DESC
            """
            cursor.execute(query, tuple(params))
            results = cursor.fetchall()
            cursor.close()
            return [
                {
                    "id": row[0],
                    "modele": row[1],
                    "categorie": row[2],
                    "sexe": row[3],
                    "prix_total": float(row[4]),
                    "date_creation": row[5],
                    "client_nom": row[6],
                    "client_prenom": row[7],
                    "fabric_image": row[8],
                    "fabric_image_name": row[9],
                    "model_image": row[10],
                    "model_image_name": row[11],
                    "couturier_nom": row[12],
                    "couturier_prenom": row[13],
                }
                for row in results
            ]
        except (MySQLError, PGError, Exception) as e:
            print(f"Erreur liste commandes avec images: {e}")
            return []

    def creer_table_rappels_livraison(self) -> bool:
        """Crée la table rappels_livraison si elle n'existe pas."""
        try:
            cursor = self.db.get_connection().cursor()
            if self.db.db_type == 'mysql':
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS rappels_livraison (
                        id INT AUTO_INCREMENT PRIMARY KEY,
                        commande_id INT NOT NULL,
                        couturier_id INT NOT NULL,
                        date_livraison DATE NOT NULL,
                        date_envoi TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY (commande_id) REFERENCES commandes(id) ON DELETE CASCADE,
                        FOREIGN KEY (couturier_id) REFERENCES couturiers(id) ON DELETE CASCADE,
                        UNIQUE KEY uk_rappel_commande_date (commande_id, date_livraison)
                    )
                """)
            else:
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS rappels_livraison (
                        id SERIAL PRIMARY KEY,
                        commande_id INTEGER NOT NULL REFERENCES commandes(id) ON DELETE CASCADE,
                        couturier_id INTEGER NOT NULL REFERENCES couturiers(id) ON DELETE CASCADE,
                        date_livraison DATE NOT NULL,
                        date_envoi TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        UNIQUE (commande_id, date_livraison)
                    )
                """)
            self.db.get_connection().commit()
            cursor.close()
            return True
        except (MySQLError, PGError, Exception) as e:
            print(f"Erreur création table rappels_livraison: {e}")
            return False

    def rappel_deja_envoye(self, commande_id: int, date_livraison) -> bool:
        """Vérifie si un rappel a déjà été envoyé pour cette commande à cette date de livraison."""
        try:
            cursor = self.db.get_connection().cursor()
            cursor.execute(
                "SELECT 1 FROM rappels_livraison WHERE commande_id = %s AND date_livraison = %s LIMIT 1",
                (commande_id, date_livraison)
            )
            ok = cursor.fetchone() is not None
            cursor.close()
            return ok
        except Exception:
            return False

    def enregistrer_rappel_envoye(self, commande_id: int, couturier_id: int, date_livraison) -> bool:
        """Enregistre qu'un rappel a été envoyé au couturier pour cette commande."""
        try:
            cursor = self.db.get_connection().cursor()
            cursor.execute(
                """
                INSERT INTO rappels_livraison (commande_id, couturier_id, date_livraison)
                VALUES (%s, %s, %s)
                """,
                (commande_id, couturier_id, date_livraison)
            )
            self.db.get_connection().commit()
            cursor.close()
            return True
        except Exception as e:
            print(f"Erreur enregistrement rappel: {e}")
            return False

    def lister_demandes_validation(
        self,
        salon_id: Optional[str] = None,
        date_debut: Optional[datetime] = None,
        date_fin: Optional[datetime] = None,
    ) -> List[Dict]:
        """
        Liste toutes les demandes en attente de validation (paiements et fermetures).
        Optionnellement filtrées par salon (via le couturier) et par période.
        """
        try:
            cursor = self.db.get_connection().cursor()

            where_clauses = ["h.statut_validation = 'en_attente'"]
            params: list = []

            if salon_id:
                where_clauses.append("co.salon_id = %s")
                params.append(salon_id)

            if date_debut:
                where_clauses.append("h.date_creation >= %s")
                params.append(date_debut)

            if date_fin:
                where_clauses.append("h.date_creation <= %s")
                params.append(date_fin)

            where_sql = " AND ".join(where_clauses)

            query = f"""
                SELECT h.id, h.commande_id, h.couturier_id, h.type_action, 
                       h.montant_paye, h.reste_apres_paiement, h.commentaire,
                       h.date_creation, h.statut_avant, h.statut_apres,
                       c.modele, c.prix_total, c.avance, c.reste,
                       cl.nom as client_nom, cl.prenom as client_prenom,
                       co.nom as couturier_nom, co.prenom as couturier_prenom,
                       co.salon_id, s.nom as salon_nom
                FROM historique_commandes h
                JOIN commandes c ON h.commande_id = c.id
                JOIN clients cl ON c.client_id = cl.id
                JOIN couturiers co ON h.couturier_id = co.id
                LEFT JOIN salons s ON co.salon_id = s.salon_id
                WHERE {where_sql}
                ORDER BY h.date_creation DESC
            """
            cursor.execute(query, tuple(params))
            results = cursor.fetchall()
            cursor.close()
            
            demandes = []
            for row in results:
                demandes.append({
                    'id': row[0],
                    'commande_id': row[1],
                    'couturier_id': row[2],
                    'type_action': row[3],
                    'montant_paye': float(row[4]) if row[4] else 0.0,
                    'reste_apres_paiement': float(row[5]) if row[5] else 0.0,
                    'commentaire': row[6],
                    'date_creation': row[7],
                    'statut_avant': row[8],
                    'statut_apres': row[9],
                    'modele': row[10],
                    'prix_total': float(row[11]),
                    'avance': float(row[12]),
                    'reste': float(row[13]),
                    'client_nom': row[14],
                    'client_prenom': row[15],
                    'couturier_nom': row[16],
                    'couturier_prenom': row[17],
                    'salon_id': row[18],
                    'salon_nom': row[19],
                })
            return demandes
        except (MySQLError, PGError, Exception) as e:
            print(f"Erreur liste demandes validation: {e}")
            return []


class ChargesModel:
    """Modèle pour la gestion des charges (dépenses de l'atelier)"""

    def __init__(self, db_connection: DatabaseConnection):
        self.db = db_connection

    def creer_tables(self) -> bool:
        """Crée les tables des charges et des documents liés"""
        try:
            cursor = self.db.get_connection().cursor()
            
            if self.db.db_type == 'mysql':
                # Table des charges
                cursor.execute(
                    """
                    CREATE TABLE IF NOT EXISTS charges (
                        id INT AUTO_INCREMENT PRIMARY KEY,
                        couturier_id INT NOT NULL,
                        type VARCHAR(20) NOT NULL,
                        categorie VARCHAR(50) NOT NULL,
                        description VARCHAR(255),
                        montant DECIMAL(12,2) NOT NULL,
                        date_charge DATE NOT NULL,
                        commande_id INT NULL,
                        employe_id INT NULL,
                        fichier_justificatif VARCHAR(500),
                        date_creation TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY (couturier_id) REFERENCES couturiers(id)
                    )
                    """
                )
                # Table des documents liés aux charges
                cursor.execute(
                    """
                    CREATE TABLE IF NOT EXISTS charge_documents (
                        id INT AUTO_INCREMENT PRIMARY KEY,
                        charge_id INT NOT NULL,
                        file_path VARCHAR(500) NOT NULL,
                        file_name VARCHAR(255) NOT NULL,
                        mime_type VARCHAR(100),
                        uploaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY (charge_id) REFERENCES charges(id) ON DELETE CASCADE
                    )
                    """
                )
            else:
                # PostgreSQL
                cursor.execute(
                    """
                    CREATE TABLE IF NOT EXISTS charges (
                        id SERIAL PRIMARY KEY,
                        couturier_id INTEGER NOT NULL REFERENCES couturiers(id),
                        type VARCHAR(20) NOT NULL,
                        categorie VARCHAR(50) NOT NULL,
                        description VARCHAR(255),
                        montant DECIMAL(12,2) NOT NULL,
                        date_charge DATE NOT NULL,
                        commande_id INTEGER NULL,
                        employe_id INTEGER NULL,
                        fichier_justificatif VARCHAR(500),
                        date_creation TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                    """
                )
                cursor.execute(
                    """
                    CREATE TABLE IF NOT EXISTS charge_documents (
                        id SERIAL PRIMARY KEY,
                        charge_id INTEGER NOT NULL REFERENCES charges(id) ON DELETE CASCADE,
                        file_path VARCHAR(500) NOT NULL,
                        file_name VARCHAR(255) NOT NULL,
                        mime_type VARCHAR(100),
                        uploaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                    """
                )
            
            self.db.get_connection().commit()
            cursor.close()
            return True
        except (MySQLError, PGError, Exception) as e:
            print(f"Erreur création tables charges: {e}")
            return False

    def ajouter_charge(self, couturier_id: int, type_charge: str, categorie: str,
                       montant: float, date_charge: str, description: Optional[str] = None,
                       commande_id: Optional[int] = None, employe_id: Optional[int] = None,
                       fichier_justificatif: Optional[str] = None,
                       reference: Optional[str] = None) -> Optional[int]:
        """
        Ajoute une nouvelle charge dans la base de données
        
        Args:
            couturier_id: ID du couturier
            type_charge: Type de charge (Fixe, Ponctuelle, Commande, Salaire)
            categorie: Catégorie ou ID de l'employé/commande
            montant: Montant de la charge en FCFA
            date_charge: Date de la charge (format YYYY-MM-DD)
            description: Description optionnelle
            commande_id: ID de la commande liée (si applicable)
            employe_id: ID de l'employé (si type_charge = Salaire)
            fichier_justificatif: Chemin du fichier justificatif
            reference: Référence unique de la charge (optionnel)
            
        Returns:
            ID de la charge créée ou None si erreur
        """
        try:
            cursor = self.db.get_connection().cursor()
            
            if self.db.db_type == 'mysql':
                query = (
                    "INSERT INTO charges (couturier_id, type, categorie, description, montant, date_charge, "
                    "commande_id, employe_id, fichier_justificatif, reference) "
                    "VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)"
                )
                cursor.execute(query, (couturier_id, type_charge, categorie, description, montant, 
                                       date_charge, commande_id, employe_id, fichier_justificatif, reference))
                charge_id = cursor.lastrowid
            else:
                query = (
                    "INSERT INTO charges (couturier_id, type, categorie, description, montant, date_charge, "
                    "commande_id, employe_id, fichier_justificatif, reference) "
                    "VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s) RETURNING id"
                )
                cursor.execute(query, (couturier_id, type_charge, categorie, description, montant, 
                                       date_charge, commande_id, employe_id, fichier_justificatif, reference))
                charge_id = cursor.fetchone()[0]
            
            self.db.get_connection().commit()
            cursor.close()
            return charge_id
        except (MySQLError, PGError, Exception) as e:
            print(f"Erreur ajout charge: {e}")
            return None

    def ajouter_document(self, charge_id: int, file_name: str, 
                         file_data: bytes,
                         mime_type: Optional[str] = None,
                         file_size: Optional[int] = None,
                         description: Optional[str] = None) -> bool:
        """
        Ajoute un document (facture/justificatif) lié à une charge.
        Le fichier est stocké UNIQUEMENT en base de données (LONGBLOB).
        
        Args:
            charge_id: ID de la charge
            file_name: Nom original du fichier
            file_data: Contenu binaire du fichier (OBLIGATOIRE)
            mime_type: Type MIME du fichier (ex: application/pdf, image/jpeg)
            file_size: Taille du fichier en octets (calculé automatiquement si non fourni)
            description: Description optionnelle du document
            
        Returns:
            True si succès, False sinon
        """
        try:
            # Validation : file_data est obligatoire
            if not file_data:
                print("Erreur: file_data est obligatoire (stockage uniquement en BDD)")
                return False
            
            cursor = self.db.get_connection().cursor()
            
            # Calculer la taille si non fournie
            if file_size is None:
                file_size = len(file_data)
            
            query = (
                "INSERT INTO charge_documents "
                "(charge_id, file_name, mime_type, file_size, file_data, description) "
                "VALUES (%s, %s, %s, %s, %s, %s)"
            )
            cursor.execute(query, (
                charge_id, 
                file_name, 
                mime_type,
                file_size,
                file_data,
                description
            ))
            self.db.get_connection().commit()
            cursor.close()
            return True
        except (MySQLError, PGError, Exception) as e:
            print(f"Erreur ajout document charge: {e}")
            return False
    
    def recuperer_document(self, document_id: int) -> Optional[Dict]:
        """
        Récupère un document par son ID
        
        Args:
            document_id: ID du document
            
        Returns:
            Dictionnaire avec les informations du document ou None
        """
        try:
            cursor = self.db.get_connection().cursor()
            query = (
                "SELECT id, charge_id, file_name, mime_type, file_size, "
                "file_data, uploaded_at, description "
                "FROM charge_documents WHERE id = %s"
            )
            cursor.execute(query, (document_id,))
            row = cursor.fetchone()
            cursor.close()
            
            if row:
                return {
                    'id': row[0],
                    'charge_id': row[1],
                    'file_name': row[2],
                    'mime_type': row[3],
                    'file_size': row[4],
                    'file_data': row[5],
                    'uploaded_at': row[6],
                    'description': row[7]
                }
            return None
        except (MySQLError, PGError, Exception) as e:
            print(f"Erreur récupération document: {e}")
            return None
    
    def lister_documents_charge(self, charge_id: int) -> List[Dict]:
        """
        Liste tous les documents associés à une charge
        
        Args:
            charge_id: ID de la charge
            
        Returns:
            Liste des documents
        """
        try:
            cursor = self.db.get_connection().cursor()
            query = (
                "SELECT id, file_name, mime_type, file_size, "
                "uploaded_at, description "
                "FROM charge_documents WHERE charge_id = %s ORDER BY uploaded_at DESC"
            )
            cursor.execute(query, (charge_id,))
            rows = cursor.fetchall()
            cursor.close()
            
            return [
                {
                    'id': r[0],
                    'file_name': r[1],
                    'mime_type': r[2],
                    'file_size': r[3],
                    'uploaded_at': r[4],
                    'description': r[5]
                }
                for r in rows
            ]
        except (MySQLError, PGError, Exception) as e:
            print(f"Erreur liste documents charge: {e}")
            return []

    def total_charges(self, couturier_id: Optional[int] = None, 
                      date_debut: Optional[datetime] = None, 
                      date_fin: Optional[datetime] = None,
                      tous_les_couturiers: bool = False,
                      salon_id: Optional[str] = None) -> float:
        """
        Calcule le total des charges pour un couturier ou tous les couturiers (pour admin)
        
        Args:
            couturier_id: ID du couturier (None si admin veut voir tout)
            date_debut: Date de début (optionnel)
            date_fin: Date de fin (optionnel)
            tous_les_couturiers: Si True, calcule le total de tous les couturiers
            
        Returns:
            Total des charges en FCFA
        """
        try:
            cursor = self.db.get_connection().cursor()
            where = []
            params: List = []
            
            if tous_les_couturiers and not salon_id:
                # Tout voir
                pass
            elif salon_id and couturier_id:
                # Filtrer par couturier_id ET salon_id (sécurité multi-tenant)
                where.append("couturier_id = %s AND couturier_id IN (SELECT id FROM couturiers WHERE salon_id = %s)")
                params.append(couturier_id)
                params.append(salon_id)
            elif salon_id:
                where.append("couturier_id IN (SELECT id FROM couturiers WHERE salon_id = %s)")
                params.append(salon_id)
            elif couturier_id:
                where.append("couturier_id = %s")
                params.append(couturier_id)
            else:
                return 0.0
            
            if date_debut:
                where.append("date_charge >= %s")
                params.append(date_debut)
            if date_fin:
                where.append("date_charge <= %s")
                params.append(date_fin)
            
            where_clause = " WHERE " + " AND ".join(where) if where else ""
            query = f"SELECT COALESCE(SUM(montant), 0) FROM charges{where_clause}"
            cursor.execute(query, tuple(params))
            total = cursor.fetchone()[0] or 0
            cursor.close()
            return float(total)
        except (MySQLError, PGError, Exception) as e:
            print(f"Erreur total charges: {e}")
            return 0.0

    def lister_charges(self, couturier_id: Optional[int] = None, limit: int = 50, 
                       tous_les_couturiers: bool = False,
                       salon_id: Optional[str] = None) -> List[Dict]:
        """
        Liste les charges d'un couturier ou de tous les couturiers (pour admin)
        
        Args:
            couturier_id: ID du couturier (None si admin veut voir tout)
            limit: Nombre maximum de charges à retourner
            tous_les_couturiers: Si True, retourne toutes les charges de tous les couturiers
            
        Returns:
            Liste des charges
        """
        try:
            cursor = self.db.get_connection().cursor()
            
            if tous_les_couturiers and not salon_id:
                # SUPER_ADMIN : toutes les charges
                query = (
                    "SELECT c.id, c.type, c.categorie, c.description, c.montant, c.date_charge, "
                    "c.date_creation, c.reference, c.commande_id, c.employe_id, c.couturier_id, "
                    "cout.nom, cout.prenom "
                    "FROM charges c "
                    "LEFT JOIN couturiers cout ON c.couturier_id = cout.id "
                    "ORDER BY c.date_charge DESC, c.id DESC LIMIT %s"
                )
                cursor.execute(query, (limit,))
            elif salon_id and couturier_id:
                # Employé : filtrer par couturier_id ET salon_id (sécurité multi-tenant)
                query = (
                    "SELECT c.id, c.type, c.categorie, c.description, c.montant, c.date_charge, "
                    "c.date_creation, c.reference, c.commande_id, c.employe_id, c.couturier_id, "
                    "cout.nom, cout.prenom "
                    "FROM charges c "
                    "LEFT JOIN couturiers cout ON c.couturier_id = cout.id "
                    "WHERE c.couturier_id = %s AND cout.salon_id = %s "
                    "ORDER BY c.date_charge DESC, c.id DESC LIMIT %s"
                )
                cursor.execute(query, (couturier_id, salon_id, limit))
            elif salon_id:
                # Admin : filtre par salon via couturiers
                query = (
                    "SELECT c.id, c.type, c.categorie, c.description, c.montant, c.date_charge, "
                    "c.date_creation, c.reference, c.commande_id, c.employe_id, c.couturier_id, "
                    "cout.nom, cout.prenom "
                    "FROM charges c "
                    "LEFT JOIN couturiers cout ON c.couturier_id = cout.id "
                    "WHERE cout.salon_id = %s "
                    "ORDER BY c.date_charge DESC, c.id DESC LIMIT %s"
                )
                cursor.execute(query, (salon_id, limit))
            else:
                # Employé : voir uniquement ses propres charges (sans filtre salon_id)
                query = (
                    "SELECT id, type, categorie, description, montant, date_charge, date_creation, "
                    "reference, commande_id, employe_id "
                    "FROM charges WHERE couturier_id = %s ORDER BY date_charge DESC, id DESC LIMIT %s"
                )
                cursor.execute(query, (couturier_id, limit))
            
            rows = cursor.fetchall()
            cursor.close()
            
            # Détecter le format selon le nombre de colonnes retournées
            # Si on a fait un JOIN avec couturiers, on a 13 colonnes
            # Sinon, on a 10 colonnes
            if rows and len(rows[0]) > 10:
                # Format avec informations du couturier (JOIN avec couturiers)
                return [
                    {
                        'id': r[0],
                        'type': r[1],
                        'categorie': r[2],
                        'description': r[3],
                        'montant': float(r[4]),
                        'date_charge': r[5],
                        'date_creation': r[6],
                        'reference': r[7] if len(r) > 7 else None,
                        'commande_id': r[8] if len(r) > 8 else None,
                        'employe_id': r[9] if len(r) > 9 else None,
                        'couturier_id': r[10] if len(r) > 10 else None,
                        'couturier_nom': r[11] if len(r) > 11 else None,
                        'couturier_prenom': r[12] if len(r) > 12 else None
                    }
                    for r in rows
                ]
            else:
                # Format standard (sans JOIN)
                return [
                    {
                        'id': r[0],
                        'type': r[1],
                        'categorie': r[2],
                        'description': r[3],
                        'montant': float(r[4]),
                        'date_charge': r[5],
                        'date_creation': r[6],
                        'reference': r[7] if len(r) > 7 else None,
                        'commande_id': r[8] if len(r) > 8 else None,
                        'employe_id': r[9] if len(r) > 9 else None
                    }
                    for r in rows
                ]
        except (MySQLError, PGError, Exception) as e:
            print(f"Erreur liste charges: {e}")
            return []


class AppLogoModel:
    """Modèle pour la gestion du logo de l'application (multi-tenant)"""
    
    def __init__(self, db_connection: DatabaseConnection):
        """
        Initialise le modèle
        
        Args:
            db_connection: Connexion à la base de données
        """
        self.db = db_connection
    
    def creer_tables(self) -> bool:
        """
        Crée la table app_logo si elle n'existe pas (multi-tenant)
        
        Returns:
            True si succès, False sinon
        """
        try:
            cursor = self.db.get_connection().cursor()
            
            # Créer la table app_logo avec salon_id
            if self.db.db_type == 'mysql':
                query = """
                CREATE TABLE IF NOT EXISTS app_logo (
                    salon_id VARCHAR(50) PRIMARY KEY COMMENT 'ID du salon propriétaire du logo',
                    logo_data LONGBLOB NOT NULL COMMENT 'Contenu binaire du logo',
                    logo_name VARCHAR(255) NOT NULL COMMENT 'Nom original du fichier',
                    mime_type VARCHAR(100) NOT NULL COMMENT 'Type MIME (ex: image/png, image/jpeg)',
                    file_size BIGINT NOT NULL COMMENT 'Taille du logo en octets',
                    uploaded_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT 'Date d\\'upload',
                    uploaded_by INT NULL COMMENT 'ID de l\\'administrateur qui a uploadé',
                    description VARCHAR(255) NULL COMMENT 'Description optionnelle',
                    FOREIGN KEY (uploaded_by) REFERENCES couturiers(id) 
                        ON DELETE SET NULL 
                        ON UPDATE CASCADE
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
                COMMENT='Table stockant les logos des salons (un logo par salon)'
                """
            else:  # PostgreSQL
                query = """
                CREATE TABLE IF NOT EXISTS app_logo (
                    salon_id VARCHAR(50) PRIMARY KEY,
                    logo_data BYTEA NOT NULL,
                    logo_name VARCHAR(255) NOT NULL,
                    mime_type VARCHAR(100) NOT NULL,
                    file_size BIGINT NOT NULL,
                    uploaded_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    uploaded_by INT NULL,
                    description VARCHAR(255) NULL,
                    FOREIGN KEY (uploaded_by) REFERENCES couturiers(id) 
                        ON DELETE SET NULL 
                        ON UPDATE CASCADE
                )
                """
            
            cursor.execute(query)
            self.db.get_connection().commit()
            cursor.close()
            return True
        except (MySQLError, PGError, Exception) as e:
            print(f"Erreur création table app_logo: {e}")
            return False
    
    def sauvegarder_logo(self, salon_id: str, logo_data: bytes, logo_name: str, 
                        mime_type: str, uploaded_by: Optional[int] = None,
                        description: Optional[str] = None) -> bool:
        """
        Sauvegarde ou met à jour le logo d'un salon
        
        Args:
            salon_id: ID du salon propriétaire du logo
            logo_data: Contenu binaire du logo (OBLIGATOIRE)
            logo_name: Nom original du fichier
            mime_type: Type MIME (ex: image/png, image/jpeg)
            uploaded_by: ID de l'administrateur qui upload (optionnel)
            description: Description optionnelle
            
        Returns:
            True si succès, False sinon
        """
        try:
            if not logo_data:
                print("Erreur: logo_data est obligatoire")
                return False
            
            cursor = self.db.get_connection().cursor()
            file_size = len(logo_data)
            
            # Vérifier si un logo existe déjà pour ce salon
            cursor.execute("SELECT COUNT(*) FROM app_logo WHERE salon_id = %s", (salon_id,))
            exists = cursor.fetchone()[0] > 0
            
            if exists:
                # Mettre à jour le logo existant
                query = """
                UPDATE app_logo 
                SET logo_data = %s, logo_name = %s, mime_type = %s, 
                    file_size = %s, uploaded_at = CURRENT_TIMESTAMP,
                    uploaded_by = %s, description = %s
                WHERE salon_id = %s
                """
                cursor.execute(query, (
                    logo_data, logo_name, mime_type, file_size,
                    uploaded_by, description, salon_id
                ))
            else:
                # Insérer un nouveau logo
                query = """
                INSERT INTO app_logo (salon_id, logo_data, logo_name, mime_type, file_size, uploaded_by, description)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                """
                cursor.execute(query, (
                    salon_id, logo_data, logo_name, mime_type, file_size,
                    uploaded_by, description
                ))
            
            self.db.get_connection().commit()
            cursor.close()
            return True
        except (MySQLError, PGError, Exception) as e:
            print(f"Erreur sauvegarde logo: {e}")
            return False
    
    def recuperer_logo(self, salon_id: str) -> Optional[Dict]:
        """
        Récupère le logo d'un salon
        
        Args:
            salon_id: ID du salon
            
        Returns:
            Dictionnaire avec les données du logo ou None si non trouvé
        """
        try:
            cursor = self.db.get_connection().cursor()
            cursor.execute("""
                SELECT logo_data, logo_name, mime_type, file_size, 
                       uploaded_at, uploaded_by, description
                FROM app_logo 
                WHERE salon_id = %s
            """, (salon_id,))
            row = cursor.fetchone()
            cursor.close()
            
            if row and row[0]:  # Vérifier que logo_data n'est pas vide
                return {
                    'logo_data': row[0],
                    'logo_name': row[1],
                    'mime_type': row[2],
                    'file_size': row[3],
                    'uploaded_at': row[4],
                    'uploaded_by': row[5],
                    'description': row[6]
                }
            return None
        except (MySQLError, PGError, Exception) as e:
            print(f"Erreur récupération logo: {e}")
            return None
