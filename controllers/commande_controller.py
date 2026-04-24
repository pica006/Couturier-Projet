"""
Contrôleur de gestion des commandes (Controller dans MVC)
"""
from typing import Optional, Dict, List, Tuple
from models.database import DatabaseConnection, ClientModel
from models.commande_model import CommandeModel
from datetime import datetime
import json
import os
from config import PDF_STORAGE_PATH, IS_RENDER


class CommandeController:
    """Gère la logique métier des commandes"""
    
    def __init__(self, db_connection: DatabaseConnection):
        self.db_connection = db_connection
        self.client_model = ClientModel(db_connection)
        self.commande_model = CommandeModel(db_connection)
    
    def initialiser_tables(self) -> bool:
        """Initialise les tables clients et commandes"""
        return self.client_model.creer_tables()
    
    def creer_ou_recuperer_client(self, couturier_id: int, nom: str, 
                                   prenom: str, telephone: str, 
                                   email: Optional[str] = None) -> Optional[int]:
        """
        Crée un nouveau client ou récupère un existant
        
        Returns:
            ID du client ou None
        """
        # Vérifier si le client existe déjà
        client_existant = self.client_model.rechercher_client(couturier_id, telephone)
        
        if client_existant:
            return client_existant['id']
        
        # Créer un nouveau client
        return self.client_model.ajouter_client(
            couturier_id, nom, prenom, telephone, email
        )
    
    def sauvegarder_image(self, uploaded_file, commande_id: int, image_type: str) -> Optional[str]:
        """
        Sauvegarde une image uploadée
        
        Args:
            uploaded_file: Fichier uploadé par Streamlit
            commande_id: ID de la commande
            image_type: Type d'image ('fabric' ou 'model')
            
        Returns:
            Chemin relatif du fichier sauvegardé ou None
        """
        try:
            # En production Render, on force un dossier temporaire dédié.
            # En local, on garde le comportement historique à côté du stockage PDF.
            if IS_RENDER:
                images_path = os.path.join(PDF_STORAGE_PATH, "images")
            else:
                images_path = os.path.join(os.path.dirname(PDF_STORAGE_PATH), "images")
            os.makedirs(images_path, exist_ok=True)
            
            # Générer un nom de fichier unique
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            extension = uploaded_file.name.split('.')[-1]
            filename = f"commande_{commande_id}_{image_type}_{timestamp}.{extension}"
            filepath = os.path.join(images_path, filename)
            
            # Sauvegarder le fichier
            with open(filepath, "wb") as f:
                f.write(uploaded_file.getbuffer())
            
            return filepath
        except Exception as e:
            print(f"Erreur sauvegarde image: {e}")
            return None
    
    def creer_commande(self, couturier_id: int, client_info: Dict,
                       commande_info: Dict) -> Tuple[bool, Optional[int], str]:
        """
        Crée une nouvelle commande complète
        
        Args:
            couturier_id: ID du couturier
            client_info: Informations du client (nom, prenom, telephone, email)
            commande_info: Informations de la commande (categorie, sexe, modele, mesures, prix, avance, date_livraison, fabric_image_path, model_type, model_image_path)
            
        Returns:
            Tuple (succès, commande_id, message)
        """
        try:
            # Créer ou récupérer le client
            client_id = self.creer_ou_recuperer_client(
                couturier_id,
                client_info['nom'],
                client_info['prenom'],
                client_info['telephone'],
                client_info.get('email')
            )
            
            if not client_id:
                details = getattr(self.client_model, "last_error", None)
                if details:
                    return False, None, f"Erreur lors de la création du client : {details}"
                return False, None, "Erreur lors de la création du client"
            
            # Vérifier que l'image du tissu est présente (OBLIGATOIRE)
            if not commande_info.get('fabric_image_path'):
                return False, None, "L'image du tissu est obligatoire"
            
            # Créer la commande avec les TROIS valeurs financières
            commande_id = self.commande_model.ajouter_commande(
                client_id,
                couturier_id,
                commande_info['categorie'],
                commande_info['sexe'],
                commande_info['modele'],
                commande_info['mesures'],
                commande_info['prix_total'],
                commande_info['avance'],
                commande_info.get('date_livraison'),
                commande_info.get('fabric_image_path'),  # Chemin (optionnel)
                commande_info.get('model_type', 'image'),
                commande_info.get('model_image_path'),  # Chemin (optionnel)
                commande_info.get('fabric_image'),  # Image en binaire
                commande_info.get('fabric_image_name'),  # Nom du fichier
                commande_info.get('model_image'),  # Image en binaire
                commande_info.get('model_image_name'),  # Nom du fichier
                commande_info.get('reste')  # Reste calculé (valeur 2)
            )
            
            if commande_id:
                return True, commande_id, "Commande créée avec succès"
            else:
                details = getattr(self.commande_model, "last_error", None)
                if details:
                    return False, None, f"Erreur lors de la création de la commande : {details}"
                return False, None, "Erreur lors de la création de la commande"
                
        except Exception as e:
            return False, None, f"Erreur: {str(e)}"
    
    def obtenir_details_commande(self, commande_id: int, couturier_id: Optional[int] = None) -> Optional[Dict]:
        """Récupère les détails complets d'une commande (avec fallback robuste)."""
        try:
            commande_id = int(commande_id)
        except Exception:
            return None

        # 1) Chemin standard via le modèle
        details = self.commande_model.obtenir_commande(commande_id)
        if details:
            if couturier_id is not None and str(details.get("couturier_id")) != str(couturier_id):
                return None
            return details

        # 2) Fallback controller: utile quand le schéma réel diffère et bloque
        # certaines requêtes dynamiques du modèle.
        try:
            conn = self.db_connection.get_connection()
            try:
                conn.rollback()
            except Exception:
                pass

            cursor = conn.cursor()
            query = """
                SELECT
                    c.id, c.client_id, c.couturier_id,
                    c.categorie, c.sexe, c.modele, c.mesures,
                    c.prix_total, c.avance, c.reste,
                    c.date_livraison, c.statut, c.date_creation,
                    cl.nom, cl.prenom, cl.telephone, cl.email,
                    co.nom, co.prenom, co.code_couturier
                FROM commandes c
                LEFT JOIN clients cl ON c.client_id = cl.id
                LEFT JOIN couturiers co ON c.couturier_id = co.id
                WHERE c.id = %s
                  AND COALESCE(c.est_supprime, FALSE) = FALSE
            """
            params: List = [commande_id]
            if couturier_id is not None:
                query += " AND c.couturier_id = %s"
                params.append(couturier_id)

            cursor.execute(query, tuple(params))
            row = cursor.fetchone()
            cursor.close()

            if not row:
                return None

            mesures_data = row[6]
            if isinstance(mesures_data, str):
                try:
                    mesures_data = json.loads(mesures_data)
                except Exception:
                    mesures_data = {}
            elif mesures_data is None:
                mesures_data = {}

            return {
                "id": row[0],
                "client_id": row[1],
                "couturier_id": row[2],
                "categorie": row[3],
                "sexe": row[4],
                "modele": row[5],
                "mesures": mesures_data,
                "prix_total": float(row[7] or 0),
                "avance": float(row[8] or 0),
                "reste": float(row[9] or 0),
                "date_livraison": row[10],
                "statut": row[11],
                "date_creation": row[12],
                "client_nom": row[13],
                "client_prenom": row[14],
                "client_telephone": row[15],
                "client_email": row[16],
                "couturier_nom": row[17],
                "couturier_prenom": row[18],
                "couturier_code": row[19],
                "fabric_image_path": None,
                "fabric_image": None,
                "fabric_image_name": None,
                "model_type": None,
                "model_image_path": None,
                "model_image": None,
                "model_image_name": None,
                "salon_id": None,
                "pdf_data": None,
                "pdf_name": None,
                "pdf_path": None,
            }
        except Exception:
            return None
    
    def lister_commandes_couturier(self, couturier_id: int) -> List[Dict]:
        """Liste toutes les commandes d'un couturier"""
        return self.commande_model.lister_commandes(couturier_id)

    def supprimer_commande_employe(
        self,
        commande_id: int,
        employe_id: int,
        salon_id_employe: Optional[str] = None,
        motif: Optional[str] = None,
    ) -> bool:
        """Suppression logique d'une commande par un employé (règles strictes)."""
        return self.commande_model.supprimer_commande_employe(
            commande_id=commande_id,
            employe_id=employe_id,
            salon_id_employe=salon_id_employe,
            motif=motif,
        )
    
    def calculer_reste(self, prix_total: float, avance: float) -> float:
        """Calcule le reste à payer"""
        return max(0, prix_total - avance)
    
    def valider_mesures(self, mesures: Dict) -> Tuple[bool, str]:
        """
        Valide que toutes les mesures sont présentes et valides
        
        Returns:
            Tuple (valide, message)
        """
        for nom, valeur in mesures.items():
            if valeur is None or valeur == "" or valeur <= 0:
                return False, f"La mesure '{nom}' est invalide"
        
        return True, "Mesures valides"
    
    def valider_prix(self, prix_total: float, avance: float) -> Tuple[bool, str]:
        """
        Valide les prix
        
        Returns:
            Tuple (valide, message)
        """
        if prix_total <= 0:
            return False, "Le prix total doit être supérieur à 0"
        
        if avance < 0:
            return False, "L'avance ne peut pas être négative"
        
        if avance > prix_total:
            return False, "L'avance ne peut pas être supérieure au prix total"
        
        return True, "Prix valides"
    
    def calculer_somme_terminees(self, salon_id: Optional[str] = None, 
                                 code_couturier: Optional[str] = None) -> Tuple[float, int]:
        """
        Calcule la somme et le nombre des commandes totalement payées (reste <= 0)
        Filtrées par salon_id et code_couturier (code employé)
        
        Args:
            salon_id: ID du salon (optionnel)
            code_couturier: Code de l'employé (optionnel)
            
        Returns:
            Tuple (somme des prix_totaux, nombre de commandes)
        """
        try:
            cursor = self.db_connection.get_connection().cursor()
            
            # Construire la requête avec les filtres
            query = """
                SELECT COALESCE(SUM(c.prix_total), 0) as somme,
                       COUNT(c.id) as nombre
                FROM commandes c
                JOIN couturiers co ON c.couturier_id = co.id
                WHERE c.reste <= 0
                  AND COALESCE(c.est_supprime, FALSE) = FALSE
            """
            params = []
            
            # Ajouter les filtres
            conditions = []
            if salon_id:
                conditions.append("co.salon_id = %s")
                params.append(salon_id)
            
            if code_couturier:
                conditions.append("co.code_couturier = %s")
                params.append(code_couturier)
            
            if conditions:
                query += " AND " + " AND ".join(conditions)
            
            cursor.execute(query, tuple(params) if params else None)
            result = cursor.fetchone()
            cursor.close()
            
            somme = float(result[0]) if result and result[0] else 0.0
            nombre = int(result[1]) if result and result[1] else 0
            
            return (somme, nombre)
            
        except Exception as e:
            print(f"Erreur calcul somme terminées: {e}")
            return (0.0, 0)
    
    def calculer_somme_livrees(self, salon_id: Optional[str] = None,
                              code_couturier: Optional[str] = None) -> Tuple[float, int]:
        """
        Calcule la somme et le nombre des commandes validées par l'administrateur
        (dans historique_commandes avec statut_validation = 'validee')
        Filtrées par salon_id et code_couturier (code employé)
        
        Args:
            salon_id: ID du salon (optionnel)
            code_couturier: Code de l'employé (optionnel)
            
        Returns:
            Tuple (somme des prix_totaux, nombre de commandes)
        """
        try:
            cursor = self.db_connection.get_connection().cursor()
            
            # Construire la requête avec les filtres
            query = """
                SELECT COALESCE(SUM(c.prix_total), 0) as somme,
                       COUNT(DISTINCT c.id) as nombre
                FROM commandes c
                JOIN historique_commandes hc ON c.id = hc.commande_id
                JOIN couturiers co ON c.couturier_id = co.id
                WHERE hc.statut_validation = 'validee'
                AND hc.type_action = 'fermeture_demande'
                AND COALESCE(c.est_supprime, FALSE) = FALSE
            """
            params = []
            
            # Ajouter les filtres
            conditions = []
            if salon_id:
                conditions.append("co.salon_id = %s")
                params.append(salon_id)
            
            if code_couturier:
                conditions.append("co.code_couturier = %s")
                params.append(code_couturier)
            
            if conditions:
                query += " AND " + " AND ".join(conditions)
            
            cursor.execute(query, tuple(params) if params else None)
            result = cursor.fetchone()
            cursor.close()
            
            somme = float(result[0]) if result and result[0] else 0.0
            nombre = int(result[1]) if result and result[1] else 0
            
            return (somme, nombre)
            
        except Exception as e:
            print(f"Erreur calcul somme livrées: {e}")
            return (0.0, 0)

    def lister_commandes_paiements_a_completer(
        self, couturier_id: int, salon_id: str, date_debut=None, date_fin=None
    ) -> List[Dict]:
        return self.commande_model.lister_commandes_paiements_a_completer(
            couturier_id=couturier_id,
            salon_id=salon_id,
            date_debut=date_debut,
            date_fin=date_fin,
        )

    def mettre_a_jour_statut_si_soldee(self, commande_id: int, nouveau_reste: float) -> bool:
        return self.commande_model.mettre_a_jour_statut_si_soldee(commande_id, nouveau_reste)

    def lister_commandes_terminees_pour_livraison(
        self,
        salon_id: str,
        date_debut=None,
        date_fin=None,
        couturier_id: Optional[int] = None,
        couturier_id_filter: Optional[int] = None,
        vue_admin: bool = False,
    ) -> List[Dict]:
        return self.commande_model.lister_commandes_terminees_pour_livraison(
            salon_id=salon_id,
            date_debut=date_debut,
            date_fin=date_fin,
            couturier_id=couturier_id,
            couturier_id_filter=couturier_id_filter,
            vue_admin=vue_admin,
        )

    def get_historique_demandes_par_commandes(
        self, couturier_id: int, commande_ids: List[int]
    ) -> Dict[int, Dict[str, int]]:
        return self.commande_model.get_historique_demandes_par_commandes(couturier_id, commande_ids)

    def get_resume_demande_fermeture_commande(self, commande_id: int, couturier_id: int) -> Dict:
        return self.commande_model.get_resume_demande_fermeture_commande(commande_id, couturier_id)

    def valider_commande_livree_payee(self, commande_id: int) -> bool:
        return self.commande_model.valider_commande_livree_payee(commande_id)

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
        return self.commande_model.lister_commandes_livrees_pour_pdf(
            salon_id=salon_id,
            couturier_id=couturier_id,
            vue_admin=vue_admin,
            date_debut=date_debut,
            date_fin=date_fin,
            nom_client_filter=nom_client_filter,
            couturier_id_filter=couturier_id_filter,
        )