"""
Modèle pour la gestion des salons (système multi-tenant)
"""
from typing import Optional, Dict, List

try:
    from mysql.connector import Error as MySQLError  # type: ignore
except Exception:
    MySQLError = Exception  # type: ignore

try:
    from psycopg2 import Error as PGError  # type: ignore
except Exception:
    PGError = Exception  # type: ignore


class SalonModel:
    """Modèle pour la gestion des salons de couture"""
    
    def __init__(self, db_connection):
        """
        Initialise le modèle avec une connexion à la base
        
        Args:
            db_connection: Instance de DatabaseConnection
        """
        self.db = db_connection
    
    def creer_salon_avec_admin(
        self,
        nom_salon: str,
        quartier: str,
        responsable: str,
        telephone: str,
        email: str,
        code_admin: str,
        password_admin: str,
        nom_admin: str,
        prenom_admin: str,
        # Configuration SMTP spécifique au salon (multi-tenant)
        smtp_host: Optional[str] = None,
        smtp_port: Optional[int] = None,
        smtp_user: Optional[str] = None,
        smtp_password: Optional[str] = None,
        smtp_from: Optional[str] = None,
        smtp_use_tls: Optional[bool] = None,
        smtp_use_ssl: Optional[bool] = None,
        salon_id_force: Optional[str] = None,
    ) -> Optional[Dict]:
        """
        Crée un nouveau salon avec son administrateur
        Utilise la procédure stockée creer_nouveau_salon
        
        Args:
            nom_salon: Nom commercial du salon
            quartier: Quartier/Adresse du salon
            responsable: Nom du responsable
            telephone: Téléphone du salon
            email: Email du salon
            code_admin: Code de connexion de l'admin
            password_admin: Mot de passe de l'admin (en clair)
            nom_admin: Nom de l'admin
            prenom_admin: Prénom de l'admin
            smtp_host: Hôte SMTP (ex: smtp.gmail.com)
            smtp_port: Port SMTP (ex: 587)
            smtp_user: Adresse email utilisée pour l'envoi
            smtp_password: Mot de passe d'application (ou SMTP)
            smtp_from: Adresse "From" (souvent = smtp_user)
            smtp_use_tls: Utiliser TLS (True par défaut)
            smtp_use_ssl: Utiliser SSL (False par défaut)
            
        Returns:
            Dict avec salon_id, admin_id, message ou None si erreur
        """
        # Si on force un salon_id (prévisualisé), on passe directement en manuel
        if salon_id_force:
            return self.creer_salon_manuel(
                nom_salon,
                quartier,
                responsable,
                telephone,
                email,
                code_admin,
                password_admin,
                nom_admin,
                prenom_admin,
                smtp_host=smtp_host,
                smtp_port=smtp_port,
                smtp_user=smtp_user,
                smtp_password=smtp_password,
                smtp_from=smtp_from,
                smtp_use_tls=smtp_use_tls,
                smtp_use_ssl=smtp_use_ssl,
                salon_id_force=salon_id_force,
            )
        
        try:
            cursor = self.db.get_connection().cursor()
            
            # Appeler la procédure stockée (MySQL uniquement)
            # PostgreSQL utilise une syntaxe différente, donc on passe directement au fallback
            if self.db.db_type == 'mysql':
                cursor.callproc('creer_nouveau_salon', [
                    nom_salon, quartier, responsable, telephone, email,
                    code_admin, password_admin, nom_admin, prenom_admin
                ])
                
                # Récupérer le résultat
                has_result = False
                for result in cursor.stored_results():
                    row = result.fetchone()
                    if row:
                        has_result = True
                        self.db.get_connection().commit()
                        cursor.close()
                        return {
                            'salon_id': row[0],
                            'nom_salon': row[2],
                            'code_admin': row[3],
                            'message': row[4]
                        }
                
                cursor.close()
                
                # Si la procédure n'a rien renvoyé, on bascule sur la méthode manuelle
                if not has_result:
                    print("⚠️ Procédure creer_nouveau_salon n'a retourné aucun résultat, fallback manuel.")
                    return self.creer_salon_manuel(
                        nom_salon,
                        quartier,
                        responsable,
                        telephone,
                        email,
                        code_admin,
                        password_admin,
                        nom_admin,
                        prenom_admin,
                        smtp_host=smtp_host,
                        smtp_port=smtp_port,
                        smtp_user=smtp_user,
                        smtp_password=smtp_password,
                        smtp_from=smtp_from,
                        smtp_use_tls=smtp_use_tls,
                        smtp_use_ssl=smtp_use_ssl,
                    )
            else:
                # PostgreSQL : passer directement à la méthode manuelle
                cursor.close()
                print("ℹ️ PostgreSQL détecté, utilisation de la méthode manuelle (pas de procédure stockée)")
                return self.creer_salon_manuel(
                    nom_salon,
                    quartier,
                    responsable,
                    telephone,
                    email,
                    code_admin,
                    password_admin,
                    nom_admin,
                    prenom_admin,
                    smtp_host=smtp_host,
                    smtp_port=smtp_port,
                    smtp_user=smtp_user,
                    smtp_password=smtp_password,
                    smtp_from=smtp_from,
                    smtp_use_tls=smtp_use_tls,
                    smtp_use_ssl=smtp_use_ssl,
                )
            
            return None
            
        except Exception as e:
            print(f"Erreur création salon (procédure) : {e}")
            # Fallback : méthode manuelle si la procédure n'existe pas
            return self.creer_salon_manuel(
                nom_salon,
                quartier,
                responsable,
                telephone,
                email,
                code_admin,
                password_admin,
                nom_admin,
                prenom_admin,
                smtp_host=smtp_host,
                smtp_port=smtp_port,
                smtp_user=smtp_user,
                smtp_password=smtp_password,
                smtp_from=smtp_from,
                smtp_use_tls=smtp_use_tls,
                smtp_use_ssl=smtp_use_ssl,
            )
    
    def creer_salon_manuel(
        self,
        nom_salon: str,
        quartier: str,
        responsable: str,
        telephone: str,
        email: str,
        code_admin: str,
        password_admin: str,
        nom_admin: str,
        prenom_admin: str,
        smtp_host: Optional[str] = None,
        smtp_port: Optional[int] = None,
        smtp_user: Optional[str] = None,
        smtp_password: Optional[str] = None,
        smtp_from: Optional[str] = None,
        smtp_use_tls: Optional[bool] = None,
        smtp_use_ssl: Optional[bool] = None,
        salon_id_force: Optional[str] = None,
    ) -> Optional[Dict]:
        """
        Crée un salon manuellement (sans procédure stockée)
        Méthode de fallback si la procédure stockée ne fonctionne pas
        """
        try:
            conn = self.db.get_connection()
            cursor = conn.cursor()
            
            # ÉTAPE 0 : Générer le prochain salon_id (format Jaind_000, Jaind_001, ...)
            salon_id = salon_id_force
            if not salon_id:
                query_gen_id = "SELECT generer_prochain_salon_id() AS nouveau_id"
                cursor.execute(query_gen_id)
                result = cursor.fetchone()
                salon_id = result[0] if result and result[0] else "Jaind_000"
            
            # Préparer la configuration SMTP (avec valeurs par défaut si non fournies)
            smtp_host_final = smtp_host or "smtp.gmail.com"
            smtp_port_final = int(smtp_port) if smtp_port is not None else 587
            smtp_user_final = smtp_user or None
            smtp_password_final = smtp_password or None
            smtp_from_final = smtp_from or smtp_user_final
            smtp_use_tls_final = smtp_use_tls if smtp_use_tls is not None else True
            smtp_use_ssl_final = smtp_use_ssl if smtp_use_ssl is not None else False

            # ÉTAPE 1 : Créer le salon avec l'ID personnalisé
            query_salon = """
                INSERT INTO salons (
                    salon_id, nom, quartier, responsable, telephone, email,
                    code_admin, smtp_host, smtp_port, smtp_user, smtp_password,
                    smtp_from, smtp_use_tls, smtp_use_ssl
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """
            cursor.execute(
                query_salon,
                (
                    salon_id,
                    nom_salon,
                    quartier,
                    responsable,
                    telephone,
                    email,
                    code_admin,
                    smtp_host_final,
                    smtp_port_final,
                    smtp_user_final,
                    smtp_password_final,
                    smtp_from_final,
                    smtp_use_tls_final,
                    smtp_use_ssl_final,
                ),
            )
            
            # ÉTAPE 2 : Créer l'admin (salon_id est VARCHAR)
            query_admin = """
                INSERT INTO couturiers (code_couturier, password, nom, prenom, role, salon_id, email, telephone)
                VALUES (%s, %s, %s, %s, 'admin', %s, %s, %s)
            """
            if self.db.db_type == 'mysql':
                cursor.execute(query_admin, (code_admin, password_admin, nom_admin, prenom_admin, salon_id, email, telephone))
                admin_id = cursor.lastrowid
            else:  # PostgreSQL
                query_admin += " RETURNING id"
                cursor.execute(query_admin, (code_admin, password_admin, nom_admin, prenom_admin, salon_id, email, telephone))
                admin_id = cursor.fetchone()[0]
            
            conn.commit()
            cursor.close()
            
            return {
                'success': True,
                'salon_id': salon_id,
                'nom_salon': nom_salon,
                'code_admin': code_admin,
                'message': 'Salon créé avec succès !'
            }
            
        except (MySQLError, PGError, Exception) as e:
            print(f"Erreur création salon manuelle : {e}")
            try:
                conn.rollback()
            except:
                pass
            return {
                'success': False,
                'message': f"Erreur création salon : {e}"
            }
    
    def obtenir_prochain_salon_id(self, code_admin: str = "") -> Optional[str]:
        """
        Prévisualise le prochain salon_id.
        Utilise la fonction SQL generer_prochain_salon_id (sans dépendance au code_admin).
        Retourne None en cas d'erreur.
        """
        try:
            cursor = self.db.get_connection().cursor()
            cursor.execute("SELECT generer_prochain_salon_id() AS id")
            res = cursor.fetchone()
            cursor.close()
            return res[0] if res and res[0] else "Jaind_000"
        except Exception as e:
            print(f"Erreur prévisualisation salon_id : {e}")
            return None
    
    def lister_tous_salons(self) -> List[Dict]:
        """
        Liste tous les salons avec leurs statistiques
        Pour SUPER_ADMIN uniquement
        
        Returns:
            Liste des salons avec statistiques
        """
        try:
            cursor = self.db.get_connection().cursor()
            
            # D'abord, vérifier si la table salons existe et sa structure
            # Essayer une requête simple d'abord
            try:
                simple_query = """
                    SELECT salon_id,
                           nom,
                           quartier,
                           responsable,
                           telephone,
                           email,
                           code_admin,
                           actif,
                           date_creation,
                           smtp_host,
                           smtp_port,
                           smtp_user,
                           smtp_from,
                           smtp_use_tls,
                           smtp_use_ssl
                    FROM salons
                    ORDER BY salon_id
                """
                cursor.execute(simple_query)
                results = cursor.fetchall()
                
                if not results:
                    print("⚠️ Table 'salons' existe mais est vide")
                    cursor.close()
                    return []
                
                # Si on a des résultats, construire la liste avec les données de base
                salons = []
                for row in results:
                    salon_id = row[0]
                    
                    # Récupérer les statistiques pour chaque salon
                    try:
                        # Nombre d'employés
                        cursor.execute(
                            "SELECT COUNT(*) FROM couturiers WHERE salon_id = %s AND role = 'employe'",
                            (salon_id,)
                        )
                        nb_employes = cursor.fetchone()[0] or 0
                    except:
                        nb_employes = 0
                    
                    try:
                        # Nombre de clients
                        cursor.execute(
                            "SELECT COUNT(*) FROM clients WHERE salon_id = %s",
                            (salon_id,)
                        )
                        nb_clients = cursor.fetchone()[0] or 0
                    except:
                        nb_clients = 0
                    
                    try:
                        # Nombre de commandes
                        cursor.execute(
                            "SELECT COUNT(*) FROM commandes WHERE salon_id = %s",
                            (salon_id,)
                        )
                        nb_commandes = cursor.fetchone()[0] or 0
                    except:
                        nb_commandes = 0
                    
                    # Calculer le CA total
                    try:
                        cursor.execute(
                            "SELECT COALESCE(SUM(prix_total), 0) FROM commandes WHERE salon_id = %s",
                            (salon_id,)
                        )
                        ca_total = float(cursor.fetchone()[0] or 0)
                    except:
                        ca_total = 0.0
                    
                    # Récupérer l'admin du salon
                    try:
                        cursor.execute(
                            "SELECT nom, prenom FROM couturiers WHERE salon_id = %s AND role = 'admin' LIMIT 1",
                            (salon_id,)
                        )
                        admin_row = cursor.fetchone()
                        admin_nom = admin_row[0] if admin_row else None
                        admin_prenom = admin_row[1] if admin_row and len(admin_row) > 1 else None
                    except:
                        admin_nom = None
                        admin_prenom = None
                    
                    salons.append({
                        'salon_id': salon_id,
                        'nom_salon': row[1] if len(row) > 1 and row[1] else f"Salon {salon_id}",
                        'quartier': row[2] if len(row) > 2 and row[2] else '',
                        'responsable': row[3] if len(row) > 3 and row[3] else '',
                        'telephone': row[4] if len(row) > 4 and row[4] else '',
                        'email': row[5] if len(row) > 5 and row[5] else '',
                        'code_admin': row[6] if len(row) > 6 and row[6] else '',
                        'actif': row[7] if len(row) > 7 else True,
                        'date_creation': row[8] if len(row) > 8 else None,
                        'admin_nom': admin_nom,
                        'admin_prenom': admin_prenom,
                        'nb_employes': int(nb_employes),
                        'nb_clients': int(nb_clients),
                        'nb_commandes': int(nb_commandes),
                        'ca_total': ca_total,
                        # Infos SMTP (pour debug / future UI)
                        'smtp_host': row[9] if len(row) > 9 else None,
                        'smtp_port': row[10] if len(row) > 10 else None,
                        'smtp_user': row[11] if len(row) > 11 else None,
                        'smtp_from': row[12] if len(row) > 12 else None,
                        'smtp_use_tls': row[13] if len(row) > 13 else None,
                        'smtp_use_ssl': row[14] if len(row) > 14 else None,
                    })
                
                cursor.close()
                return salons
                
            except Exception as e_simple:
                print(f"Erreur requête simple salons: {e_simple}")
                # Essayer de vérifier si la table existe
                try:
                    if self.db.db_type == 'mysql':
                        cursor.execute("SHOW TABLES LIKE 'salons'")
                    else:  # PostgreSQL
                        cursor.execute("""
                            SELECT table_name 
                            FROM information_schema.tables 
                            WHERE table_schema = 'public' AND table_name = 'salons'
                        """)
                    table_exists = cursor.fetchone()
                    cursor.close()
                    
                    if not table_exists:
                        print("❌ La table 'salons' n'existe pas dans la base de données")
                        return []
                    else:
                        print("⚠️ La table 'salons' existe mais la requête a échoué")
                        return []
                except Exception as e_check:
                    print(f"Erreur vérification table: {e_check}")
                    cursor.close()
                    return []
            
        except (MySQLError, PGError, Exception) as e:
            print(f"Erreur liste salons : {e}")
            import traceback
            traceback.print_exc()
            try:
                cursor.close()
            except:
                pass
            return []
    
    def obtenir_salon_by_code_admin(self, code_admin: str) -> Optional[Dict]:
        """
        Récupère un salon par le code de son admin
        Utilisé par SUPER_ADMIN pour "se placer" sur un salon
        
        Args:
            code_admin: Code du couturier admin (ex: Jaind_001)
            
        Returns:
            Dict avec les infos du salon ou None
        """
        try:
            cursor = self.db.get_connection().cursor()
            query = """
                SELECT 
                    s.salon_id AS salon_id,
                    s.nom AS nom_salon,
                    s.quartier,
                    s.responsable,
                    s.telephone,
                    s.code_admin,
                    c.id AS admin_id,
                    c.nom AS admin_nom,
                    c.prenom AS admin_prenom
                FROM salons s
                LEFT JOIN couturiers c 
                    ON c.salon_id = s.salon_id AND c.role = 'admin'
                WHERE s.code_admin = %s
            """
            cursor.execute(query, (code_admin,))
            row = cursor.fetchone()
            cursor.close()
            
            if row:
                return {
                    'salon_id': row[0],
                    'nom_salon': row[1],
                    'quartier': row[2],
                    'responsable': row[3],
                    'telephone': row[4],
                    'code_admin': row[5],
                    'admin_id': row[6],
                    'admin_nom': row[7],
                    'admin_prenom': row[8]
                }
            return None
            
        except (MySQLError, PGError, Exception) as e:
            print(f"Erreur recherche salon : {e}")
            return None
    
    def obtenir_salon_by_id(self, salon_id: str) -> Optional[Dict]:
        """
        Récupère un salon par son ID
        
        Args:
            salon_id: ID du salon
            
        Returns:
            Dict avec les infos du salon ou None
        """
        try:
            cursor = self.db.get_connection().cursor()
            query = """
                SELECT 
                    s.salon_id,
                    s.nom,
                    s.quartier,
                    s.responsable,
                    s.telephone,
                    s.email,
                    s.code_admin,
                    s.actif,
                    s.date_creation,
                    c.nom AS admin_nom,
                    c.prenom AS admin_prenom,
                    s.smtp_host,
                    s.smtp_port,
                    s.smtp_user,
                    s.smtp_password,
                    s.smtp_from,
                    s.smtp_use_tls,
                    s.smtp_use_ssl
                FROM salons s
                LEFT JOIN (
                    SELECT salon_id, nom, prenom
                    FROM couturiers
                    WHERE role = 'admin'
                ) c ON c.salon_id = s.salon_id
                WHERE s.salon_id = %s
            """
            cursor.execute(query, (salon_id,))
            row = cursor.fetchone()
            cursor.close()
            
            if row:
                return {
                    'salon_id': row[0],
                    'nom_salon': row[1],
                    'quartier': row[2],
                    'responsable': row[3],
                    'telephone': row[4],
                    'email': row[5],
                    'code_admin': row[6],
                    'actif': row[7],
                    'date_creation': row[8],
                    'admin_nom': row[9],
                    'admin_prenom': row[10],
                    'smtp_host': row[11],
                    'smtp_port': row[12],
                    'smtp_user': row[13],
                    'smtp_password': row[14],
                    'smtp_from': row[15],
                    'smtp_use_tls': row[16],
                    'smtp_use_ssl': row[17],
                }
            return None
            
        except (MySQLError, PGError, Exception) as e:
            print(f"Erreur récupération salon : {e}")
            return None

    def obtenir_config_email_salon(self, salon_id: str) -> Optional[Dict]:
        """
        Récupère la configuration SMTP d'un salon pour l'envoi d'e-mails.
        Retourne un dict compatible avec EmailController ou None si non configuré.
        """
        try:
            salon = self.obtenir_salon_by_id(salon_id)
            if not salon:
                return None

            smtp_user = salon.get("smtp_user")
            smtp_password = salon.get("smtp_password")

            # Si pas d'utilisateur ou mot de passe SMTP, on considère que la config n'est pas prête
            if not smtp_user or not smtp_password:
                return None

            return {
                "enabled": True,
                "host": salon.get("smtp_host") or "smtp.gmail.com",
                "port": int(salon.get("smtp_port") or 587),
                "user": smtp_user,
                "password": smtp_password,
                "from_email": salon.get("smtp_from") or smtp_user,
                "use_tls": salon.get("smtp_use_tls") if salon.get("smtp_use_tls") is not None else True,
                "use_ssl": salon.get("smtp_use_ssl") if salon.get("smtp_use_ssl") is not None else False,
            }
        except Exception as e:
            print(f"Erreur récupération config email salon: {e}")
            return None
    
    def modifier_salon(self, salon_id: str, nom: str = None, quartier: str = None,
                       responsable: str = None, telephone: str = None,
                       email: str = None, actif: bool = None,
                       smtp_host: Optional[str] = None,
                       smtp_port: Optional[int] = None,
                       smtp_user: Optional[str] = None,
                       smtp_password: Optional[str] = None,
                       smtp_from: Optional[str] = None,
                       smtp_use_tls: Optional[bool] = None,
                       smtp_use_ssl: Optional[bool] = None) -> bool:
        """
        Modifie les informations d'un salon
        
        Args:
            salon_id: ID du salon à modifier
            nom: Nouveau nom (optionnel)
            quartier: Nouveau quartier (optionnel)
            responsable: Nouveau responsable (optionnel)
            telephone: Nouveau téléphone (optionnel)
            email: Nouvel email (optionnel)
            actif: Nouveau statut actif/inactif (optionnel)
            
        Returns:
            True si succès, False sinon
        """
        try:
            conn = self.db.get_connection()
            cursor = conn.cursor()
            
            # Construire la requête UPDATE dynamiquement
            updates = []
            params = []
            
            if nom is not None:
                updates.append("nom = %s")
                params.append(nom)
            if quartier is not None:
                updates.append("quartier = %s")
                params.append(quartier)
            if responsable is not None:
                updates.append("responsable = %s")
                params.append(responsable)
            if telephone is not None:
                updates.append("telephone = %s")
                params.append(telephone)
            if email is not None:
                updates.append("email = %s")
                params.append(email)
            if actif is not None:
                updates.append("actif = %s")
                params.append(actif)
            if smtp_host is not None:
                updates.append("smtp_host = %s")
                params.append(smtp_host)
            if smtp_port is not None:
                updates.append("smtp_port = %s")
                params.append(smtp_port)
            if smtp_user is not None:
                updates.append("smtp_user = %s")
                params.append(smtp_user)
            if smtp_password is not None:
                updates.append("smtp_password = %s")
                params.append(smtp_password)
            if smtp_from is not None:
                updates.append("smtp_from = %s")
                params.append(smtp_from)
            if smtp_use_tls is not None:
                updates.append("smtp_use_tls = %s")
                params.append(smtp_use_tls)
            if smtp_use_ssl is not None:
                updates.append("smtp_use_ssl = %s")
                params.append(smtp_use_ssl)
            
            if not updates:
                cursor.close()
                return False  # Aucune modification demandée
            
            # Ajouter salon_id aux paramètres
            params.append(salon_id)
            
            query = f"""
                UPDATE salons
                SET {', '.join(updates)}
                WHERE salon_id = %s
            """
            
            cursor.execute(query, tuple(params))
            conn.commit()
            cursor.close()
            
            return True
            
        except (MySQLError, PGError, Exception) as e:
            print(f"Erreur modification salon : {e}")
            try:
                conn.rollback()
            except:
                pass
            return False

