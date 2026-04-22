"""
Modèle de gestion de la base de données (Model dans MVC)
"""
from typing import Optional, Dict, List, Tuple, Any
from datetime import datetime
from utils.security import hash_password

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
        self.last_error: Optional[str] = None
        
    def connect(self) -> bool:
        """
        Établit la connexion à la base de données
        
        Returns:
            True si succès, False sinon
        """
        # Réutiliser une connexion déjà active évite une nouvelle négociation réseau.
        if self.is_connected():
            return True

        self.last_error = None

        try:
            if self.db_type == 'postgresql':
                if psycopg2 is None:
                    self.last_error = "psycopg2 non installé"
                    print(self.last_error)
                    return False
                conn_params = {
                    'host': self.config['host'],
                    'port': int(self.config.get('port', 5432)),
                    'database': self.config['database'],
                    'user': self.config['user'],
                    'password': self.config['password'],
                    'connect_timeout': int(self.config.get('connect_timeout', 6)),
                    'application_name': self.config.get('application_name', 'couturier_app')
                }
                # SSL requis pour Render PostgreSQL
                if self.config.get('sslmode'):
                    conn_params['sslmode'] = self.config['sslmode']
                # Keepalive pour limiter les connexions "zombies" en cloud.
                conn_params['keepalives'] = int(self.config.get('keepalives', 1))
                conn_params['keepalives_idle'] = int(self.config.get('keepalives_idle', 30))
                conn_params['keepalives_interval'] = int(self.config.get('keepalives_interval', 10))
                conn_params['keepalives_count'] = int(self.config.get('keepalives_count', 5))
                self.connection = psycopg2.connect(**conn_params)
                return True
            elif self.db_type == 'mysql':
                if mysql is None:
                    self.last_error = "mysql-connector-python non installé"
                    print(self.last_error)
                    return False
                self.connection = mysql.connector.connect(
                    host=self.config['host'],
                    port=int(self.config['port']),
                    database=self.config['database'],
                    user=self.config['user'],
                    password=self.config['password'],
                    connection_timeout=int(self.config.get('connect_timeout', 6))
                )
                return True
            else:
                self.last_error = f"Type de base de données non supporté: {self.db_type}"
                print(self.last_error)
                return False
        except (MySQLError, PGError, Exception) as e:
            self.last_error = str(e)
            print(f"Erreur de connexion: {self.last_error}")
            self.connection = None
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
        self.last_error: Optional[str] = None
    
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
            # PostgreSQL: nettoyer une transaction potentiellement abandonnée
            # avant d'exécuter de nouvelles requêtes.
            if self.db.db_type != 'mysql':
                try:
                    self.db.get_connection().rollback()
                except Exception:
                    pass

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
            try:
                self.db.get_connection().rollback()
            except Exception:
                pass
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
            if self.db.db_type != 'mysql':
                try:
                    self.db.get_connection().rollback()
                except Exception:
                    pass
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
            try:
                self.db.get_connection().rollback()
            except Exception:
                pass
            return []
    
    def creer_utilisateur(self, code_couturier: str, password: str, nom: str, prenom: str,
                          role: str = 'employe', email: Optional[str] = None,
                          telephone: Optional[str] = None, salon_id: Optional[str] = None) -> Optional[int]:
        """
        Crée un nouvel utilisateur dans la base de données (multi-tenant)
        
        Args:
            code_couturier: Code unique de connexion (ex: COUT001)
            password: Mot de passe en clair (sera hashe en bcrypt)
            nom: Nom de l'utilisateur
            prenom: Prénom de l'utilisateur
            role: Rôle de l'utilisateur ('admin' ou 'employe')
            email: Email (optionnel)
            telephone: Téléphone (optionnel)
            salon_id: ID du salon (si None, sera assigné automatiquement)
            
        Returns:
            ID de l'utilisateur créé ou None si erreur
        """
        cursor = None
        self.last_error = None
        try:
            # PostgreSQL: repartir d'un état transactionnel propre.
            if self.db.db_type != 'mysql':
                try:
                    self.db.get_connection().rollback()
                except Exception:
                    pass

            # Vérifier que le code n'existe pas déjà
            existe, _ = self.verifier_code(code_couturier)
            if existe:
                self.last_error = f"Le code de connexion '{code_couturier}' existe déjà."
                return None  # Code déjà existant
            
            # Vérifier que le rôle est valide
            if role not in ['admin', 'employe']:
                self.last_error = f"Rôle invalide '{role}', basculement automatique vers 'employe'."
                role = 'employe'
            
            cursor = self.db.get_connection().cursor()

            # En multi-tenant, un utilisateur doit toujours être rattaché à un salon existant.
            if not salon_id:
                self.last_error = "Salon non défini pour cet utilisateur. Reconnectez-vous puis réessayez."
                cursor.close()
                return None

            cursor.execute("SELECT 1 FROM salons WHERE salon_id = %s", (salon_id,))
            salon_exists = cursor.fetchone()
            if not salon_exists:
                self.last_error = f"Le salon '{salon_id}' est introuvable."
                cursor.close()
                return None
            
            # Hasher le mot de passe avant stockage
            password_hash = hash_password(password)

            # Insérer l'utilisateur (actif par défaut)
            if self.db.db_type == 'mysql':
                query = """
                    INSERT INTO couturiers (code_couturier, password, nom, prenom, role, email, telephone, salon_id, actif)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, 1)
                """
                cursor.execute(query, (code_couturier, password_hash, nom, prenom, role, email, telephone, salon_id))
                user_id = cursor.lastrowid
            else:
                # Séquence SERIAL potentiellement désynchronisée (import/seed manuel).
                cursor.execute(
                    """
                    SELECT setval(
                        pg_get_serial_sequence('couturiers', 'id'),
                        COALESCE((SELECT MAX(id) FROM couturiers), 0) + 1,
                        false
                    )
                    """
                )
                query = """
                    INSERT INTO couturiers (code_couturier, password, nom, prenom, role, email, telephone, salon_id, actif)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, TRUE) RETURNING id
                """
                cursor.execute(query, (code_couturier, password_hash, nom, prenom, role, email, telephone, salon_id))
                user_id = cursor.fetchone()[0]
            
            self.db.get_connection().commit()
            cursor.close()
            return user_id
        except (MySQLError, PGError, Exception) as e:
            print(f"Erreur création utilisateur: {e}")
            self.last_error = str(e)
            try:
                self.db.get_connection().rollback()
            except Exception:
                pass
            if cursor:
                try:
                    cursor.close()
                except Exception:
                    pass
            return None

    def mettre_a_jour_statut_actif(self, user_id: int, actif: bool) -> bool:
        """
        Active ou désactive un utilisateur.

        Args:
            user_id: ID du couturier
            actif: True pour activer, False pour désactiver
        """
        try:
            if self.db.db_type != 'mysql':
                try:
                    self.db.get_connection().rollback()
                except Exception:
                    pass
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
            try:
                self.db.get_connection().rollback()
            except Exception:
                pass
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
            if self.db.db_type != 'mysql':
                try:
                    self.db.get_connection().rollback()
                except Exception:
                    pass
            cursor = self.db.get_connection().cursor()
            query = "UPDATE couturiers SET password = %s WHERE id = %s"
            cursor.execute(query, (hash_password(nouveau_password), couturier_id))
            self.db.get_connection().commit()
            cursor.close()
            return True
        except (MySQLError, PGError, Exception) as e:
            print(f"Erreur réinitialisation mot de passe: {e}")
            try:
                self.db.get_connection().rollback()
            except Exception:
                pass
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
            if self.db.db_type != 'mysql':
                try:
                    self.db.get_connection().rollback()
                except Exception:
                    pass
            
            cursor = self.db.get_connection().cursor()
            query = "UPDATE couturiers SET role = %s WHERE id = %s"
            cursor.execute(query, (nouveau_role, couturier_id))
            self.db.get_connection().commit()
            cursor.close()
            return True
        except (MySQLError, PGError, Exception) as e:
            print(f"Erreur modification rôle: {e}")
            try:
                self.db.get_connection().rollback()
            except Exception:
                pass
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
            if self.db.db_type != 'mysql':
                try:
                    self.db.get_connection().rollback()
                except Exception:
                    pass
            cursor = self.db.get_connection().cursor()
            query = "DELETE FROM couturiers WHERE id = %s"
            cursor.execute(query, (couturier_id,))
            self.db.get_connection().commit()
            cursor.close()
            return True
        except (MySQLError, PGError, Exception) as e:
            print(f"Erreur suppression utilisateur: {e}")
            try:
                self.db.get_connection().rollback()
            except Exception:
                pass
            return False


class ClientModel:
    """Modèle pour la gestion des clients"""
    
    def __init__(self, db_connection: DatabaseConnection):
        self.db = db_connection
        self.last_error: Optional[str] = None

    def _ensure_clients_salon_id_column(self) -> None:
        """Garantit la présence de la colonne salon_id sur les bases existantes."""
        cursor = self.db.get_connection().cursor()
        try:
            if self.db.db_type == 'mysql':
                cursor.execute(
                    """
                    ALTER TABLE clients
                    ADD COLUMN IF NOT EXISTS salon_id VARCHAR(100)
                    """
                )
            else:
                cursor.execute(
                    """
                    ALTER TABLE clients
                    ADD COLUMN IF NOT EXISTS salon_id VARCHAR(100)
                    """
                )
            self.db.get_connection().commit()
        finally:
            cursor.close()
    
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
                        salon_id VARCHAR(100),
                        nom VARCHAR(100) NOT NULL,
                        prenom VARCHAR(100) NOT NULL,
                        telephone VARCHAR(20) NOT NULL,
                        email VARCHAR(150),
                        date_creation TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY (couturier_id) REFERENCES couturiers(id),
                        FOREIGN KEY (salon_id) REFERENCES salons(id)
                    )
                    """
                )
                cursor.execute(
                    """
                    ALTER TABLE clients
                    ADD COLUMN IF NOT EXISTS salon_id VARCHAR(100)
                    """
                )
                cursor.execute(
                    """
                    CREATE TABLE IF NOT EXISTS commandes (
                        id INT AUTO_INCREMENT PRIMARY KEY,
                        client_id INT,
                        couturier_id INT,
                        salon_id VARCHAR(100),
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
                        FOREIGN KEY (couturier_id) REFERENCES couturiers(id),
                        FOREIGN KEY (salon_id) REFERENCES salons(id)
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
                        salon_id VARCHAR(100) REFERENCES salons(id),
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
                    ALTER TABLE clients
                    ADD COLUMN IF NOT EXISTS salon_id VARCHAR(100)
                    """
                )
                cursor.execute(
                    """
                    CREATE TABLE IF NOT EXISTS commandes (
                        id SERIAL PRIMARY KEY,
                        client_id INTEGER REFERENCES clients(id),
                        couturier_id INTEGER REFERENCES couturiers(id),
                        salon_id VARCHAR(100) REFERENCES salons(id),
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
            self.last_error = None
            self._ensure_clients_salon_id_column()
            cursor = self.db.get_connection().cursor()
            # Multi-tenant: rattacher explicitement le client au salon du couturier
            cursor.execute("SELECT salon_id FROM couturiers WHERE id = %s", (couturier_id,))
            row_salon = cursor.fetchone()
            salon_id = row_salon[0] if row_salon and row_salon[0] is not None else None
            if not salon_id:
                cursor.close()
                self.last_error = f"Impossible de déterminer le salon_id pour le couturier {couturier_id}."
                return None
            if self.db.db_type == 'mysql':
                query = (
                    "INSERT INTO clients (couturier_id, salon_id, nom, prenom, telephone, email) "
                    "VALUES (%s, %s, %s, %s, %s, %s)"
                )
                cursor.execute(query, (couturier_id, salon_id, nom, prenom, telephone, email))
                client_id = cursor.lastrowid
            else:
                query = """
                    INSERT INTO clients (couturier_id, salon_id, nom, prenom, telephone, email)
                    VALUES (%s, %s, %s, %s, %s, %s)
                    RETURNING id
                """
                cursor.execute(query, (couturier_id, salon_id, nom, prenom, telephone, email))
                client_id = cursor.fetchone()[0]
            self.db.get_connection().commit()
            cursor.close()
            return client_id
        except (MySQLError, PGError, Exception) as e:
            self.last_error = str(e)
            print(f"Erreur ajout client: {e}")
            return None
    
    def rechercher_client(self, couturier_id: int, telephone: str) -> Optional[Dict]:
        """Recherche un client par téléphone"""
        try:
            self.last_error = None
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
        except (MySQLError, PGError, Exception) as e:
            self.last_error = str(e)
            print(f"Erreur recherche client: {e}")
            return None

    def compter_clients_distincts_salon(self, salon_id: str) -> int:
        """
        Compte les clients distincts d'un salon (tous couturiers du salon).
        """
        try:
            cursor = self.db.get_connection().cursor()
            query = """
                SELECT COUNT(DISTINCT c.id)
                FROM clients c
                INNER JOIN couturiers ct ON c.couturier_id = ct.id
                WHERE ct.salon_id = %s
            """
            cursor.execute(query, (salon_id,))
            result = cursor.fetchone()
            cursor.close()
            return int(result[0]) if result and result[0] is not None else 0
        except Exception as e:
            print(f"Erreur comptage clients salon: {e}")
            return 0


from models.commande_model import CommandeModel  # backward compat

class ChargesModel:
    """Modèle pour la gestion des charges (dépenses de l'atelier)"""

    def __init__(self, db_connection: DatabaseConnection):
        self.db = db_connection
        self.last_error: Optional[str] = None

    def _ensure_charges_schema(self, cursor) -> None:
        """Ajoute colonnes manquantes (anciennes BDD) pour aligner schéma et requêtes."""
        try:
            if self.db.db_type == "mysql":

                def _mysql_col_exists(table: str, col: str) -> bool:
                    cursor.execute(
                        """
                        SELECT COUNT(*) FROM information_schema.COLUMNS
                        WHERE TABLE_SCHEMA = DATABASE()
                          AND TABLE_NAME = %s
                          AND COLUMN_NAME = %s
                        """,
                        (table, col),
                    )
                    row = cursor.fetchone()
                    return bool(row and row[0] > 0)

                if not _mysql_col_exists("charges", "reference"):
                    cursor.execute(
                        "ALTER TABLE charges ADD COLUMN reference VARCHAR(100) NULL"
                    )

                try:
                    cursor.execute(
                        "ALTER TABLE charge_documents MODIFY COLUMN file_path VARCHAR(500) NULL"
                    )
                except (MySQLError, PGError, Exception):
                    pass

                for col, ddl in (
                    ("file_size", "BIGINT NULL"),
                    ("file_data", "LONGBLOB NULL"),
                    ("description", "VARCHAR(500) NULL"),
                ):
                    if not _mysql_col_exists("charge_documents", col):
                        cursor.execute(
                            f"ALTER TABLE charge_documents ADD COLUMN {col} {ddl}"
                        )
            else:
                cursor.execute(
                    "ALTER TABLE charges ADD COLUMN IF NOT EXISTS reference VARCHAR(100)"
                )
                try:
                    cursor.execute(
                        "ALTER TABLE charge_documents ALTER COLUMN file_path DROP NOT NULL"
                    )
                except (MySQLError, PGError, Exception):
                    pass
                cursor.execute(
                    "ALTER TABLE charge_documents ADD COLUMN IF NOT EXISTS file_size BIGINT"
                )
                cursor.execute(
                    "ALTER TABLE charge_documents ADD COLUMN IF NOT EXISTS file_data BYTEA"
                )
                cursor.execute(
                    "ALTER TABLE charge_documents ADD COLUMN IF NOT EXISTS description TEXT"
                )
        except (MySQLError, PGError, Exception) as e:
            print(f"Erreur migration schéma charges: {e}")

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

            self._ensure_charges_schema(cursor)

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
        self.last_error = None
        if couturier_id is None:
            self.last_error = "Identifiant couturier manquant (impossible d'enregistrer la charge)."
            return None
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
            self.last_error = str(e)
            print(f"Erreur ajout charge: {e}")
            try:
                if getattr(self.db, "db_type", "") == "postgresql":
                    self.db.get_connection().rollback()
            except Exception:
                pass
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
            try:
                self.db.get_connection().rollback()
            except Exception:
                pass
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
            try:
                self.db.get_connection().rollback()
            except Exception:
                pass
            return None
