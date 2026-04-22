"""
Modèle Commande (extrait de database.py pour modularité).
"""
from typing import Optional, Dict, List, Tuple, Any
from datetime import datetime

from models.database import DatabaseConnection, MySQLError, PGError


class CommandeModel:
    """Modèle pour la gestion des commandes"""
    
    def __init__(self, db_connection: DatabaseConnection):
        self.db = db_connection
        self.last_error: Optional[str] = None

    def _ensure_soft_delete_columns(self) -> None:
        """Ajoute les colonnes de suppression logique si elles n'existent pas."""
        cursor = self.db.get_connection().cursor()
        try:
            if self.db.db_type == 'mysql':
                cursor.execute("ALTER TABLE commandes ADD COLUMN IF NOT EXISTS est_supprime BOOLEAN NOT NULL DEFAULT FALSE")
                cursor.execute("ALTER TABLE commandes ADD COLUMN IF NOT EXISTS supprime_par INT NULL")
                cursor.execute("ALTER TABLE commandes ADD COLUMN IF NOT EXISTS date_suppression TIMESTAMP NULL")
                cursor.execute("ALTER TABLE commandes ADD COLUMN IF NOT EXISTS motif_suppression TEXT NULL")
            else:
                cursor.execute("ALTER TABLE commandes ADD COLUMN IF NOT EXISTS est_supprime BOOLEAN NOT NULL DEFAULT FALSE")
                cursor.execute("ALTER TABLE commandes ADD COLUMN IF NOT EXISTS supprime_par INTEGER NULL")
                cursor.execute("ALTER TABLE commandes ADD COLUMN IF NOT EXISTS date_suppression TIMESTAMP NULL")
                cursor.execute("ALTER TABLE commandes ADD COLUMN IF NOT EXISTS motif_suppression TEXT NULL")
            self.db.get_connection().commit()
        except Exception:
            try:
                self.db.get_connection().rollback()
            except Exception:
                pass
        finally:
            try:
                cursor.close()
            except Exception:
                pass

    def _ensure_historique_demandes_schema(self) -> None:
        """Garantit la présence de la table/colonnes utilisées pour les demandes de fermeture."""
        connection = self.db.get_connection()
        cursor = connection.cursor()
        try:
            if self.db.db_type == 'mysql':
                cursor.execute(
                    """
                    CREATE TABLE IF NOT EXISTS historique_commandes (
                        id INT AUTO_INCREMENT PRIMARY KEY,
                        commande_id INT NOT NULL,
                        couturier_id INT NOT NULL,
                        type_action VARCHAR(50) NOT NULL,
                        montant_paye DECIMAL(10,2) DEFAULT 0.00,
                        reste_apres_paiement DECIMAL(10,2) DEFAULT 0.00,
                        statut_avant VARCHAR(50),
                        statut_apres VARCHAR(50),
                        commentaire TEXT,
                        statut_validation VARCHAR(50) DEFAULT 'en_attente',
                        admin_validation_id INT NULL,
                        date_validation TIMESTAMP NULL,
                        commentaire_admin TEXT,
                        date_creation TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        INDEX idx_historique_commande_id (commande_id),
                        INDEX idx_historique_couturier_id (couturier_id),
                        INDEX idx_historique_statut_validation (statut_validation),
                        INDEX idx_historique_type_action (type_action),
                        CONSTRAINT fk_hist_commande FOREIGN KEY (commande_id) REFERENCES commandes(id) ON DELETE CASCADE ON UPDATE CASCADE,
                        CONSTRAINT fk_hist_couturier FOREIGN KEY (couturier_id) REFERENCES couturiers(id) ON DELETE CASCADE ON UPDATE CASCADE,
                        CONSTRAINT fk_hist_admin FOREIGN KEY (admin_validation_id) REFERENCES couturiers(id) ON DELETE SET NULL ON UPDATE CASCADE
                    )
                    """
                )
            else:
                cursor.execute(
                    """
                    CREATE TABLE IF NOT EXISTS historique_commandes (
                        id SERIAL PRIMARY KEY,
                        commande_id INTEGER NOT NULL,
                        couturier_id INTEGER NOT NULL,
                        type_action VARCHAR(50) NOT NULL,
                        montant_paye DECIMAL(10,2) DEFAULT 0.00,
                        reste_apres_paiement DECIMAL(10,2) DEFAULT 0.00,
                        statut_avant VARCHAR(50),
                        statut_apres VARCHAR(50),
                        commentaire TEXT,
                        statut_validation VARCHAR(50) DEFAULT 'en_attente',
                        admin_validation_id INTEGER NULL,
                        date_validation TIMESTAMP NULL,
                        commentaire_admin TEXT,
                        date_creation TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY (commande_id) REFERENCES commandes(id) ON DELETE CASCADE ON UPDATE CASCADE,
                        FOREIGN KEY (couturier_id) REFERENCES couturiers(id) ON DELETE CASCADE ON UPDATE CASCADE,
                        FOREIGN KEY (admin_validation_id) REFERENCES couturiers(id) ON DELETE SET NULL ON UPDATE CASCADE
                    )
                    """
                )
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_historique_commande_id ON historique_commandes(commande_id)")
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_historique_couturier_id ON historique_commandes(couturier_id)")
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_historique_statut_validation ON historique_commandes(statut_validation)")
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_historique_type_action ON historique_commandes(type_action)")

            cursor.execute("ALTER TABLE historique_commandes ADD COLUMN IF NOT EXISTS statut_validation VARCHAR(50) DEFAULT 'en_attente'")
            cursor.execute("ALTER TABLE historique_commandes ADD COLUMN IF NOT EXISTS admin_validation_id INTEGER NULL")
            cursor.execute("ALTER TABLE historique_commandes ADD COLUMN IF NOT EXISTS date_validation TIMESTAMP NULL")
            cursor.execute("ALTER TABLE historique_commandes ADD COLUMN IF NOT EXISTS commentaire_admin TEXT")
            connection.commit()
        except Exception as e:
            try:
                connection.rollback()
            except Exception:
                pass
            print(f"Erreur migration historique_commandes: {e}")
        finally:
            try:
                cursor.close()
            except Exception:
                pass

    def _ensure_commandes_salon_id_column(self) -> None:
        """Garantit la présence de la colonne salon_id dans commandes."""
        cursor = self.db.get_connection().cursor()
        try:
            cursor.execute(
                """
                ALTER TABLE commandes
                ADD COLUMN IF NOT EXISTS salon_id VARCHAR(100)
                """
            )
            self.db.get_connection().commit()
        except Exception:
            try:
                self.db.get_connection().rollback()
            except Exception:
                pass
        finally:
            try:
                cursor.close()
            except Exception:
                pass

    def obtenir_email_client_par_commande(
        self, commande_id: int, salon_id: str
    ) -> Optional[Dict[str, Any]]:
        """
        Récupère la configuration SMTP du salon associée à la commande (multi-tenant).
        Le nom historique de la méthode est conservé pour compatibilité ; les données
        servent à l'envoi d'email au client (hébergement SMTP du salon).
        """
        try:
            cursor = self.db.get_connection().cursor()
            try:
                cursor.execute(
                    """
                    SELECT
                        s.smtp_host,
                        s.smtp_port,
                        s.smtp_user,
                        s.smtp_password,
                        s.smtp_from,
                        s.smtp_use_tls,
                        s.smtp_use_ssl,
                        s.email
                    FROM commandes c
                    JOIN salons s ON s.salon_id = c.salon_id
                    WHERE c.id = %s AND c.salon_id = %s
                    """,
                    (commande_id, salon_id),
                )
                row = cursor.fetchone()
                if not row:
                    return None
                return {
                    "enabled": True,
                    "host": row[0],
                    "port": row[1],
                    "user": row[2] or row[7],
                    "password": row[3],
                    "from_email": row[4] or row[2] or row[7],
                    "use_tls": row[5],
                    "use_ssl": row[6],
                }
            finally:
                cursor.close()
        except Exception as e:
            try:
                print(f"Erreur obtenir_email_client_par_commande: {e}")
            except Exception:
                pass
            return None

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
            self.last_error = None
            self._ensure_commandes_salon_id_column()
            connection = self.db.get_connection()
            cursor = connection.cursor()

            # Multi-tenant: rattacher explicitement la commande au salon du couturier
            cursor.execute("SELECT salon_id FROM couturiers WHERE id = %s", (couturier_id,))
            row_salon = cursor.fetchone()
            salon_id = row_salon[0] if row_salon and row_salon[0] is not None else None
            if not salon_id:
                cursor.close()
                return None

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
                    "(client_id, couturier_id, salon_id, categorie, sexe, modele, mesures, "
                    " prix_total, avance, reste, date_livraison, fabric_image_path, fabric_image, fabric_image_name, "
                    " model_type, model_image_path, model_image, model_image_name, statut) "
                    "VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)"
                )

                cursor.execute(query, (
                    client_id, couturier_id, salon_id, categorie, sexe, modele,
                    json.dumps(mesures), prix_total, avance, reste, 
                    date_livraison, fabric_image_path, fabric_image, fabric_image_name,
                    model_type, model_image_path, model_image, model_image_name, statut
                ))

                commande_id = cursor.lastrowid

            else:
                # Version PostgreSQL (si jamais tu l'utilises aussi)
                query = """
                    INSERT INTO commandes 
                    (client_id, couturier_id, salon_id, categorie, sexe, modele, mesures,
                     prix_total, avance, reste, date_livraison, fabric_image_path, fabric_image, fabric_image_name,
                     model_type, model_image_path, model_image, model_image_name, statut)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    RETURNING id
                """

                cursor.execute(query, (
                    client_id, couturier_id, salon_id, categorie, sexe, modele,
                    json.dumps(mesures), prix_total, avance, reste,
                    date_livraison, fabric_image_path, fabric_image, fabric_image_name,
                    model_type, model_image_path, model_image, model_image_name, statut
                ))

                commande_id = cursor.fetchone()[0]

            connection.commit()
            cursor.close()
            return commande_id

        except (MySQLError, PGError, Exception) as e:
            self.last_error = str(e)
            print(f"❌ Erreur ajout commande: {e}")
            return None






        


    def obtenir_commande(self, commande_id: int) -> Optional[Dict]:
        """Récupère les détails d'une commande"""
        try:
            if self.db.db_type != 'mysql':
                try:
                    self.db.get_connection().rollback()
                except Exception:
                    pass
            cursor = self.db.get_connection().cursor()
            query_mode = None
            queries = [
                (
                    "full",
                    """
                    SELECT 
                        c.id, c.client_id, c.couturier_id,
                        c.categorie, c.sexe, c.modele, c.mesures,
                        c.prix_total, c.avance, c.reste,
                        c.date_livraison, c.statut,
                        c.fabric_image_path, c.fabric_image, c.fabric_image_name,
                        c.model_type, c.model_image_path, c.model_image, c.model_image_name,
                        c.date_creation, c.salon_id,
                        c.pdf_data, c.pdf_name, c.pdf_path,
                        cl.nom as client_nom, cl.prenom as client_prenom, 
                        cl.telephone as client_telephone, cl.email as client_email,
                        co.nom as couturier_nom, co.prenom as couturier_prenom, 
                        co.code_couturier as couturier_code
                    FROM commandes c
                    LEFT JOIN clients cl ON c.client_id = cl.id
                    LEFT JOIN couturiers co ON c.couturier_id = co.id
                    WHERE c.id = %s
                    """,
                ),
                (
                    "no_pdf",
                    """
                    SELECT 
                        c.id, c.client_id, c.couturier_id,
                        c.categorie, c.sexe, c.modele, c.mesures,
                        c.prix_total, c.avance, c.reste,
                        c.date_livraison, c.statut,
                        c.fabric_image_path, c.fabric_image, c.fabric_image_name,
                        c.model_type, c.model_image_path, c.model_image, c.model_image_name,
                        c.date_creation, c.salon_id,
                        cl.nom as client_nom, cl.prenom as client_prenom, 
                        cl.telephone as client_telephone, cl.email as client_email,
                        co.nom as couturier_nom, co.prenom as couturier_prenom, 
                        co.code_couturier as couturier_code
                    FROM commandes c
                    LEFT JOIN clients cl ON c.client_id = cl.id
                    LEFT JOIN couturiers co ON c.couturier_id = co.id
                    WHERE c.id = %s
                    """,
                ),
                (
                    "legacy",
                    """
                    SELECT 
                        c.id, c.client_id, c.couturier_id,
                        c.categorie, c.sexe, c.modele, c.mesures,
                        c.prix_total, c.avance, c.reste,
                        c.date_livraison, c.statut,
                        c.fabric_image_path, c.fabric_image, c.fabric_image_name,
                        c.model_type, c.model_image_path, c.model_image, c.model_image_name,
                        c.date_creation,
                        cl.nom as client_nom, cl.prenom as client_prenom, 
                        cl.telephone as client_telephone, cl.email as client_email,
                        co.nom as couturier_nom, co.prenom as couturier_prenom, 
                        co.code_couturier as couturier_code
                    FROM commandes c
                    LEFT JOIN clients cl ON c.client_id = cl.id
                    LEFT JOIN couturiers co ON c.couturier_id = co.id
                    WHERE c.id = %s
                    """,
                ),
            ]

            result = None
            last_query_error = None
            for mode, query in queries:
                try:
                    cursor.execute(query, (commande_id,))
                    result = cursor.fetchone()
                    query_mode = mode
                    break
                except Exception as e:
                    last_query_error = e
                    continue

            if result is None and last_query_error is not None:
                raise last_query_error
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
                    'salon_id': result[20] if query_mode in ("full", "no_pdf") and num_cols > 20 else None,
                }
                
                # Ajouter les données selon le mode de requête réellement exécuté
                if query_mode == "full" and num_cols > 30:
                    data['pdf_data'] = result[21]
                    data['pdf_name'] = result[22]
                    data['pdf_path'] = result[23]
                    # Données client et couturier
                    data['client_nom'] = result[24]
                    data['client_prenom'] = result[25]
                    data['client_telephone'] = result[26]
                    data['client_email'] = result[27]
                    data['couturier_nom'] = result[28]
                    data['couturier_prenom'] = result[29]
                    data['couturier_code'] = result[30]
                elif query_mode == "no_pdf":
                    data['pdf_data'] = None
                    data['pdf_name'] = None
                    data['pdf_path'] = None
                    data['client_nom'] = result[21] if num_cols > 21 else None
                    data['client_prenom'] = result[22] if num_cols > 22 else None
                    data['client_telephone'] = result[23] if num_cols > 23 else None
                    data['client_email'] = result[24] if num_cols > 24 else None
                    data['couturier_nom'] = result[25] if num_cols > 25 else None
                    data['couturier_prenom'] = result[26] if num_cols > 26 else None
                    data['couturier_code'] = result[27] if num_cols > 27 else None
                else:
                    # legacy: sans salon_id ni PDF
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
            try:
                self.db.get_connection().rollback()
            except Exception:
                pass
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
            self._ensure_soft_delete_columns()
            cursor = self.db.get_connection().cursor()
            
            if tous_les_couturiers and not salon_id:
                # SUPER_ADMIN : voir toutes les commandes de tous les salons
                query = """
                    SELECT c.id, c.modele, c.prix_total, c.statut, c.date_creation,
                           cl.nom, cl.prenom, c.couturier_id,
                           co.nom as couturier_nom, co.prenom as couturier_prenom, co.salon_id
                    FROM commandes c
                    LEFT JOIN clients cl ON c.client_id = cl.id
                    LEFT JOIN couturiers co ON c.couturier_id = co.id
                    WHERE COALESCE(c.est_supprime, FALSE) = FALSE
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
                    LEFT JOIN clients cl ON c.client_id = cl.id
                    LEFT JOIN couturiers co ON c.couturier_id = co.id
                    WHERE co.salon_id = %s
                      AND COALESCE(c.est_supprime, FALSE) = FALSE
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
                        LEFT JOIN clients cl ON c.client_id = cl.id
                        LEFT JOIN couturiers co ON c.couturier_id = co.id
                        WHERE co.salon_id = %s AND c.couturier_id = %s
                          AND COALESCE(c.est_supprime, FALSE) = FALSE
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
                        LEFT JOIN clients cl ON c.client_id = cl.id
                        LEFT JOIN couturiers co ON c.couturier_id = co.id
                        WHERE co.salon_id = %s
                          AND COALESCE(c.est_supprime, FALSE) = FALSE
                        ORDER BY c.date_creation DESC
                    """
                    cursor.execute(query, (salon_id,))
                elif couturier_id:
                    # Filtrer uniquement par couturier_id
                    query = """
                        SELECT c.id, c.modele, c.prix_total, c.statut, c.date_creation,
                               cl.nom, cl.prenom
                        FROM commandes c
                        LEFT JOIN clients cl ON c.client_id = cl.id
                        WHERE c.couturier_id = %s
                          AND COALESCE(c.est_supprime, FALSE) = FALSE
                        ORDER BY c.date_creation DESC
                    """
                    cursor.execute(query, (couturier_id,))
                else:
                    # Aucun filtre : retourner liste vide
                    query = """
                        SELECT c.id, c.modele, c.prix_total, c.statut, c.date_creation,
                               cl.nom, cl.prenom
                        FROM commandes c
                        LEFT JOIN clients cl ON c.client_id = cl.id
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
                         commentaire: Optional[str] = None) -> Optional[dict]:
        """
        Demande la fermeture d'une commande (création d'une entrée en attente de validation)
        
        Args:
            commande_id: ID de la commande
            couturier_id: ID du couturier qui demande la fermeture
            commentaire: Commentaire optionnel
            
        Returns:
            dict: {"id": <id>, "created": <bool>} ou None si erreur
        """
        try:
            self._ensure_historique_demandes_schema()
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
                if getattr(self.db, "db_type", "") == "postgresql":
                    self.db.get_connection().rollback()
            except Exception:
                pass
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
            self._ensure_historique_demandes_schema()
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
            self._ensure_soft_delete_columns()
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
                      AND COALESCE(c.est_supprime, FALSE) = FALSE
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
                      AND COALESCE(c.est_supprime, FALSE) = FALSE
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
            self._ensure_soft_delete_columns()
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
                      AND COALESCE(c.est_supprime, FALSE) = FALSE
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
                      AND COALESCE(c.est_supprime, FALSE) = FALSE
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
            self._ensure_soft_delete_columns()
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
                      AND COALESCE(c.est_supprime, FALSE) = FALSE
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
                      AND COALESCE(c.est_supprime, FALSE) = FALSE
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

    def supprimer_commande(
        self,
        commande_id: int,
        admin_id: int,
        salon_id_admin: Optional[str] = None,
        motif: Optional[str] = None,
    ) -> bool:
        """
        Suppression logique d'une commande par un administrateur.
        """
        try:
            self._ensure_soft_delete_columns()
            conn = self.db.get_connection()
            cursor = conn.cursor()
            cursor.execute(
                "SELECT id, statut, salon_id, COALESCE(est_supprime, FALSE) FROM commandes WHERE id = %s",
                (commande_id,),
            )
            row = cursor.fetchone()
            if not row:
                cursor.close()
                return False
            _, statut_avant, salon_id_cmd, est_supprime = row
            if est_supprime or (salon_id_admin and str(salon_id_cmd) != str(salon_id_admin)):
                cursor.close()
                return False
            cursor.execute(
                """
                UPDATE commandes
                SET est_supprime = %s, supprime_par = %s, date_suppression = NOW(),
                    motif_suppression = %s, statut = %s
                WHERE id = %s
                """,
                (True, admin_id, motif, "Supprimée", commande_id),
            )
            cursor.execute(
                """
                INSERT INTO historique_commandes (
                    commande_id, couturier_id, type_action, statut_avant, statut_apres, commentaire, date_creation
                ) VALUES (%s, %s, %s, %s, %s, %s, NOW())
                """,
                (commande_id, admin_id, "suppression", statut_avant, "Supprimée", motif or "Suppression par administrateur"),
            )
            conn.commit()
            cursor.close()
            return True
        except Exception as e:
            print(f"Erreur suppression commande: {e}")
            try:
                self.db.get_connection().rollback()
            except Exception:
                pass
            return False

    def supprimer_commande_employe(
        self,
        commande_id: int,
        employe_id: int,
        salon_id_employe: Optional[str] = None,
        motif: Optional[str] = None,
    ) -> bool:
        """
        Suppression logique stricte par employé:
        - uniquement ses propres commandes,
        - uniquement dans son salon,
        - exclut les commandes déjà supprimées.
        """
        try:
            self._ensure_soft_delete_columns()
            conn = self.db.get_connection()
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT id, statut, salon_id, couturier_id, COALESCE(est_supprime, FALSE)
                FROM commandes
                WHERE id = %s
                """,
                (commande_id,),
            )
            row = cursor.fetchone()
            if not row:
                cursor.close()
                return False
            _, statut_avant, salon_id_cmd, couturier_id_cmd, est_supprime = row
            is_owner = str(couturier_id_cmd) == str(employe_id)
            same_salon = (not salon_id_employe) or (str(salon_id_cmd) == str(salon_id_employe))
            if est_supprime or not is_owner or not same_salon:
                cursor.close()
                return False
            cursor.execute(
                """
                UPDATE commandes
                SET est_supprime = %s, supprime_par = %s, date_suppression = NOW(),
                    motif_suppression = %s, statut = %s
                WHERE id = %s
                """,
                (True, employe_id, motif, "Supprimée", commande_id),
            )
            cursor.execute(
                """
                INSERT INTO historique_commandes (
                    commande_id, couturier_id, type_action, statut_avant, statut_apres, commentaire, date_creation
                ) VALUES (%s, %s, %s, %s, %s, %s, NOW())
                """,
                (commande_id, employe_id, "suppression_employe", statut_avant, "Supprimée", motif or "Suppression par employé"),
            )
            conn.commit()
            cursor.close()
            return True
        except Exception as e:
            print(f"Erreur suppression commande employé: {e}")
            try:
                self.db.get_connection().rollback()
            except Exception:
                pass
            return False

    def lister_commandes_supprimees(self, salon_id: Optional[str] = None) -> List[Dict]:
        """Liste les commandes supprimées logiquement pour suivi admin/superadmin."""
        try:
            self._ensure_soft_delete_columns()
            cursor = self.db.get_connection().cursor()
            query = """
                SELECT c.id, c.modele, c.prix_total, c.statut, c.salon_id,
                       c.date_creation, c.date_suppression, c.motif_suppression,
                       cl.nom, cl.prenom, co.code_couturier, co.nom, co.prenom
                FROM commandes c
                JOIN clients cl ON c.client_id = cl.id
                LEFT JOIN couturiers co ON c.couturier_id = co.id
                WHERE COALESCE(c.est_supprime, FALSE) = TRUE
            """
            params: List = []
            if salon_id:
                query += " AND c.salon_id = %s"
                params.append(salon_id)
            query += " ORDER BY c.date_suppression DESC NULLS LAST, c.date_creation DESC"
            cursor.execute(query, tuple(params))
            rows = cursor.fetchall()
            cursor.close()
            return [
                {
                    "id": row[0],
                    "modele": row[1],
                    "prix_total": float(row[2] or 0),
                    "statut": row[3],
                    "salon_id": row[4],
                    "date_creation": row[5],
                    "date_suppression": row[6],
                    "motif_suppression": row[7],
                    "client_nom": row[8],
                    "client_prenom": row[9],
                    "couturier_code": row[10],
                    "couturier_nom": row[11],
                    "couturier_prenom": row[12],
                }
                for row in rows
            ]
        except Exception as e:
            print(f"Erreur liste commandes supprimées: {e}")
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
            self._ensure_soft_delete_columns()
            where_clauses = ["1=1", "COALESCE(c.est_supprime, FALSE) = FALSE"]
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
            self._ensure_soft_delete_columns()
            where_clauses = ["(c.fabric_image IS NOT NULL OR c.model_image IS NOT NULL)", "COALESCE(c.est_supprime, FALSE) = FALSE"]
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
            self._ensure_historique_demandes_schema()
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
                       COALESCE(co.salon_id, c.salon_id) as salon_id, s.nom as salon_nom
                FROM historique_commandes h
                JOIN commandes c ON h.commande_id = c.id
                JOIN clients cl ON c.client_id = cl.id
                JOIN couturiers co ON h.couturier_id = co.id
                LEFT JOIN salons s ON COALESCE(co.salon_id, c.salon_id) = s.salon_id
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

    def lister_commandes_paiements_a_completer(
        self,
        couturier_id: int,
        salon_id: str,
        date_debut=None,
        date_fin=None,
    ) -> List[Dict]:
        """
        Liste les commandes avec avance > 0 et reste > 0 pour un couturier/salon.
        """
        try:
            if self.db.db_type != 'mysql':
                try:
                    self.db.get_connection().rollback()
                except Exception:
                    pass
            cursor = self.db.get_connection().cursor()
            query = """
                SELECT c.id, c.modele, c.prix_total, c.avance, c.reste, c.statut,
                       c.date_creation, c.date_livraison,
                       cl.nom, cl.prenom
                FROM commandes c
                JOIN clients cl ON c.client_id = cl.id
                JOIN couturiers co ON c.couturier_id = co.id
                WHERE c.couturier_id = %s
                  AND co.salon_id = %s
                  AND COALESCE(c.est_supprime, FALSE) = FALSE
                  AND c.statut != 'Fermé'
                  AND c.avance > 0
                  AND c.reste > 0
            """
            params = [couturier_id, salon_id]
            if date_debut:
                query += " AND c.date_creation::date >= %s"
                params.append(date_debut)
            if date_fin:
                query += " AND c.date_creation::date <= %s"
                params.append(date_fin)
            query += " ORDER BY c.date_creation DESC"
            cursor.execute(query, tuple(params))
            rows = cursor.fetchall()
            cursor.close()
            return [
                {
                    "id": row[0],
                    "modele": row[1],
                    "prix_total": float(row[2]),
                    "avance": float(row[3]),
                    "reste": float(row[4]),
                    "statut": row[5],
                    "date_creation": row[6],
                    "date_livraison": row[7],
                    "client_nom": row[8],
                    "client_prenom": row[9],
                }
                for row in rows
            ]
        except Exception as e:
            print(f"Erreur liste paiements à compléter: {e}")
            return []

    def mettre_a_jour_statut_si_soldee(self, commande_id: int, nouveau_reste: float) -> bool:
        """
        Passe la commande en 'Terminé' si le reste est soldé.
        """
        try:
            if float(nouveau_reste) > 0:
                return True
            connection = self.db.get_connection()
            cursor = connection.cursor()
            cursor.execute(
                "UPDATE commandes SET statut = 'Terminé' WHERE id = %s",
                (commande_id,),
            )
            connection.commit()
            cursor.close()
            return True
        except Exception as e:
            print(f"Erreur mise à jour statut soldé: {e}")
            return False

    def lister_commandes_terminees_pour_livraison(
        self,
        salon_id: str,
        date_debut=None,
        date_fin=None,
        couturier_id: Optional[int] = None,
        couturier_id_filter: Optional[int] = None,
        vue_admin: bool = False,
    ) -> List[Dict]:
        """
        Liste les commandes terminées (reste <= 0, statut Terminé) prêtes pour demande/validation livraison.
        """
        try:
            if self.db.db_type != 'mysql':
                try:
                    self.db.get_connection().rollback()
                except Exception:
                    pass
            cursor = self.db.get_connection().cursor()
            if vue_admin:
                query = """
                    SELECT c.id, c.modele, c.prix_total, c.avance, c.reste, c.statut,
                           c.date_creation, c.date_livraison,
                           cl.nom, cl.prenom, cl.email, c.couturier_id,
                           co.nom as couturier_nom, co.prenom as couturier_prenom
                    FROM commandes c
                    JOIN clients cl ON c.client_id = cl.id
                    LEFT JOIN couturiers co ON c.couturier_id = co.id
                    WHERE co.salon_id = %s
                      AND COALESCE(c.est_supprime, FALSE) = FALSE
                      AND c.reste <= 0
                      AND c.statut = 'Terminé'
                """
                params = [salon_id]
                if couturier_id_filter:
                    query += " AND c.couturier_id = %s"
                    params.append(couturier_id_filter)
            else:
                query = """
                    SELECT c.id, c.modele, c.prix_total, c.avance, c.reste, c.statut,
                           c.date_creation, c.date_livraison,
                           cl.nom, cl.prenom
                    FROM commandes c
                    JOIN clients cl ON c.client_id = cl.id
                    JOIN couturiers co ON c.couturier_id = co.id
                    WHERE c.couturier_id = %s
                      AND co.salon_id = %s
                      AND COALESCE(c.est_supprime, FALSE) = FALSE
                      AND c.reste <= 0
                      AND c.statut = 'Terminé'
                """
                params = [couturier_id, salon_id]
                if couturier_id_filter:
                    query += " AND c.couturier_id = %s"
                    params.append(couturier_id_filter)
            if date_debut:
                query += " AND c.date_creation::date >= %s"
                params.append(date_debut)
            if date_fin:
                query += " AND c.date_creation::date <= %s"
                params.append(date_fin)
            query += " ORDER BY c.date_creation DESC"
            cursor.execute(query, tuple(params))
            rows = cursor.fetchall()
            cursor.close()
            commandes: List[Dict] = []
            for row in rows:
                data = {
                    "id": row[0],
                    "modele": row[1],
                    "prix_total": float(row[2]),
                    "avance": float(row[3]),
                    "reste": float(row[4]),
                    "statut": row[5],
                    "date_creation": row[6],
                    "date_livraison": row[7],
                    "client_nom": row[8],
                    "client_prenom": row[9],
                }
                if vue_admin:
                    data.update(
                        {
                            "client_email": row[10],
                            "couturier_id": row[11],
                            "couturier_nom": row[12],
                            "couturier_prenom": row[13],
                        }
                    )
                commandes.append(data)
            return commandes
        except Exception as e:
            print(f"Erreur liste commandes terminées livraison: {e}")
            return []

    def get_historique_demandes_par_commandes(
        self, couturier_id: int, commande_ids: List[int]
    ) -> Dict[int, Dict[str, int]]:
        """
        Retourne des stats agrégées des demandes de fermeture par commande.
        """
        if not commande_ids:
            return {}
        try:
            self._ensure_historique_demandes_schema()
            cursor = self.db.get_connection().cursor()
            placeholders = ", ".join(["%s"] * len(commande_ids))
            query = f"""
                SELECT commande_id,
                       COUNT(*) as total,
                       SUM(CASE WHEN statut_validation = 'en_attente' THEN 1 ELSE 0 END) as en_attente,
                       SUM(CASE WHEN statut_validation = 'validee' THEN 1 ELSE 0 END) as validee,
                       SUM(CASE WHEN statut_validation = 'rejetee' THEN 1 ELSE 0 END) as rejetee
                FROM historique_commandes
                WHERE couturier_id = %s
                  AND type_action = 'fermeture_demande'
                  AND commande_id IN ({placeholders})
                GROUP BY commande_id
            """
            cursor.execute(query, tuple([couturier_id] + commande_ids))
            rows = cursor.fetchall()
            cursor.close()
            return {
                row[0]: {
                    "total": int(row[1] or 0),
                    "en_attente": int(row[2] or 0),
                    "validee": int(row[3] or 0),
                    "rejetee": int(row[4] or 0),
                }
                for row in rows
            }
        except Exception as e:
            print(f"Erreur historique demandes par commandes: {e}")
            return {}

    def get_resume_demande_fermeture_commande(self, commande_id: int, couturier_id: int) -> Dict:
        """
        Retourne le total des demandes et le dernier statut pour une commande.
        """
        try:
            self._ensure_historique_demandes_schema()
            cursor = self.db.get_connection().cursor()
            cursor.execute(
                """
                SELECT COUNT(*), MAX(statut_validation)
                FROM historique_commandes
                WHERE commande_id = %s
                  AND couturier_id = %s
                  AND type_action = 'fermeture_demande'
                """,
                (commande_id, couturier_id),
            )
            row = cursor.fetchone()
            cursor.close()
            return {
                "total": int(row[0] or 0) if row else 0,
                "dernier_statut": row[1] if row else None,
            }
        except Exception as e:
            print(f"Erreur résumé demande fermeture: {e}")
            return {"total": 0, "dernier_statut": None}

    def valider_commande_livree_payee(self, commande_id: int) -> bool:
        """
        Valide directement une commande en 'Livré et payé'.
        """
        try:
            connection = self.db.get_connection()
            if self.db.db_type != 'mysql':
                try:
                    connection.rollback()
                except Exception:
                    pass
            cursor = connection.cursor()
            cursor.execute(
                "UPDATE commandes SET statut = 'Livré et payé', date_fermeture = NOW() WHERE id = %s",
                (commande_id,),
            )
            # Mettre à jour le statut de la demande dans historique (si en attente)
            try:
                cursor.execute(
                    """UPDATE historique_commandes
                         SET statut_validation = 'validee', date_validation = NOW()
                         WHERE commande_id = %s
                           AND type_action = 'fermeture_demande'
                           AND statut_validation = 'en_attente'""",
                    (commande_id,),
                )
            except Exception as _e_hist:
                print(f"Avertissement historique valider_livree_payee: {_e_hist}")
            connection.commit()
            cursor.close()
            return True
        except Exception as e:
            print(f"Erreur validation commande livrée/payée: {e}")
            return False

    def lister_commandes_livrees_pour_pdf(
        self,
        salon_id: str,
        couturier_id: Optional[int] = None,
        vue_admin: bool = False,
        date_debut=None,
        date_fin=None,
        nom_client_filter: Optional[str] = None,
        couturier_id_filter: Optional[int] = None,
    ) -> List[Dict]:
        """
        Liste les commandes validées (Livré et payé) pour téléchargement PDF.
        """
        try:
            if self.db.db_type != 'mysql':
                try:
                    self.db.get_connection().rollback()
                except Exception:
                    pass
            cursor = self.db.get_connection().cursor()
            if vue_admin:
                query = """
                    SELECT c.id, c.modele, c.prix_total, c.avance, c.reste, c.statut,
                           c.date_creation, c.date_livraison,
                           cl.nom, cl.prenom, cl.telephone, cl.email,
                           c.couturier_id, co.nom as couturier_nom, co.prenom as couturier_prenom,
                           c.pdf_name, c.pdf_path
                    FROM commandes c
                    JOIN clients cl ON c.client_id = cl.id
                    LEFT JOIN couturiers co ON c.couturier_id = co.id
                    WHERE co.salon_id = %s
                      AND COALESCE(c.est_supprime, FALSE) = FALSE
                      AND c.statut = 'Livré et payé'
                """
                params = [salon_id]
                if couturier_id_filter:
                    query += " AND c.couturier_id = %s"
                    params.append(couturier_id_filter)
            else:
                query = """
                    SELECT c.id, c.modele, c.prix_total, c.avance, c.reste, c.statut,
                           c.date_creation, c.date_livraison,
                           cl.nom, cl.prenom, cl.telephone, cl.email,
                           c.pdf_name, c.pdf_path
                    FROM commandes c
                    JOIN clients cl ON c.client_id = cl.id
                    JOIN couturiers co ON c.couturier_id = co.id
                    WHERE c.couturier_id = %s
                      AND co.salon_id = %s
                      AND COALESCE(c.est_supprime, FALSE) = FALSE
                      AND c.statut = 'Livré et payé'
                """
                params = [couturier_id, salon_id]
            if date_debut:
                query += " AND c.date_creation::date >= %s"
                params.append(date_debut)
            if date_fin:
                query += " AND c.date_creation::date <= %s"
                params.append(date_fin)
            if nom_client_filter:
                query += " AND (cl.nom LIKE %s OR cl.prenom LIKE %s)"
                params.append(f"%{nom_client_filter}%")
                params.append(f"%{nom_client_filter}%")
            query += " ORDER BY c.date_creation DESC"
            cursor.execute(query, tuple(params))
            rows = cursor.fetchall()
            cursor.close()
            commandes: List[Dict] = []
            for row in rows:
                data = {
                    "id": row[0],
                    "modele": row[1],
                    "prix_total": float(row[2]),
                    "avance": float(row[3]),
                    "reste": float(row[4]),
                    "statut": row[5],
                    "date_creation": row[6],
                    "date_livraison": row[7],
                    "client_nom": row[8],
                    "client_prenom": row[9],
                    "client_telephone": row[10],
                    "client_email": row[11],
                }
                if vue_admin:
                    data.update(
                        {
                            "couturier_id": row[12],
                            "couturier_nom": row[13],
                            "couturier_prenom": row[14],
                            "pdf_name": row[15] if len(row) > 15 else None,
                            "pdf_path": row[16] if len(row) > 16 else None,
                        }
                    )
                else:
                    data.update(
                        {
                            "pdf_name": row[12] if len(row) > 12 else None,
                            "pdf_path": row[13] if len(row) > 13 else None,
                        }
                    )
                commandes.append(data)
            return commandes
        except Exception as e:
            print(f"Erreur liste commandes livrées pour PDF: {e}")
            return []


{e}")
            return []
