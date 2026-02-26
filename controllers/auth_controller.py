"""
========================================
CONTRÔLEUR D'AUTHENTIFICATION (auth_controller.py)
========================================

POURQUOI CE FICHIER ?
---------------------
Ce fichier gère la LOGIQUE D'AUTHENTIFICATION (vérification des identifiants)
C'est le "cerveau" qui décide si un couturier peut se connecter ou non

COMMENT IL FONCTIONNE ?
------------------------
1. L'utilisateur entre son code et mot de passe
2. Ce contrôleur cherche dans la base de données
3. Il vérifie le mot de passe (avec bcrypt pour la sécurité)
4. Il retourne : succès ou échec

OÙ IL EST UTILISÉ ?
-------------------
Dans views/auth_view.py, ligne : auth_controller.authentifier(code, password)
"""

from typing import Optional, Dict, Tuple
from models.database import DatabaseConnection, CouturierModel
from models.salon_model import SalonModel


class AuthController:
    """
    CLASSE : Contrôleur d'authentification
    
    RÔLE : Gérer la connexion des couturiers
    MÉTHODES :
    - authentifier() : Vérifie code + mot de passe
    - initialiser_tables() : Crée les tables si elles n'existent pas
    """
    
    def __init__(self, db_connection: DatabaseConnection):
        """
        INITIALISATION du contrôleur
        
        POURQUOI ? Pour avoir accès à la base de données
        COMMENT ? On stocke la connexion et on crée un CouturierModel
        
        PARAMÈTRES :
        - db_connection : Connexion active à la base de données
        """
        self.db_connection = db_connection
        self.couturier_model = CouturierModel(db_connection)
    
    def authentifier(self, code_couturier: str, password: str) -> Tuple[bool, Optional[Dict], str]:
        """
        ========================================================================
        FONCTION PRINCIPALE : AUTHENTIFIER UN COUTURIER
        ========================================================================
        
        POURQUOI ? Pour vérifier si le code ET le mot de passe sont corrects
        
        COMMENT ÇA MARCHE ?
        -------------------
        1. Vérifier que le code n'est pas vide
        2. Vérifier que la connexion DB est active
        3. Chercher le couturier dans la base de données par son code
        4. Si trouvé : vérifier le mot de passe (comparaison avec hash bcrypt)
        5. Si tout est OK : retourner les données du couturier
        6. Sinon : retourner une erreur
        
        PARAMÈTRES :
        - code_couturier : Code de connexion (ex: COUT001)
        - password : Mot de passe en clair (ex: password123)
        
        RETOURNE :
        Tuple de 3 éléments :
        - bool : True si authentification réussie, False sinon
        - Dict : Données du couturier (nom, prénom, etc.) ou None
        - str : Message à afficher à l'utilisateur
        
        EXEMPLE D'UTILISATION :
        succes, donnees, message = auth_controller.authentifier('COUT001', 'password123')
        if succes:
            print(f"Bienvenue {donnees['prenom']} !")
        else:
            print(f"Erreur : {message}")
        """
        
        # ====================================================================
        # ÉTAPE 1 : VALIDATION DES ENTRÉES
        # ====================================================================
        
        # Vérifier que le code couturier n'est pas vide
        if not code_couturier or code_couturier.strip() == "":
            return False, None, "Le code couturier ne peut pas être vide"
        
        # Vérifier que le mot de passe n'est pas vide
        if not password or password.strip() == "":
            return False, None, "Le mot de passe ne peut pas être vide"
        
        # Vérifier que la connexion à la base de données est active
        if not self.db_connection.is_connected():
            return False, None, "Pas de connexion à la base de données"
        
        # ====================================================================
        # ÉTAPE 2 : RECHERCHE DU COUTURIER DANS LA BASE DE DONNÉES
        # ====================================================================
        
        # Appeler le modèle pour chercher le couturier par son code
        # RETOURNE : (existe: bool, donnees: dict ou None)
        existe, donnees = self.couturier_model.verifier_code(code_couturier)
        
        # Si le code n'existe pas dans la base
        if not existe:
            return False, None, "Code couturier invalide"
        
        # ====================================================================
        # ÉTAPE 3 : VÉRIFICATION DU MOT DE PASSE
        # ====================================================================
        
        # Récupérer le mot de passe depuis la base de données
        password_db = donnees.get('password')
        
        # Si pas de mot de passe dans la base
        if not password_db:
            return False, None, "Mot de passe non configuré pour cet utilisateur"
        
        # ====================================================================
        # VÉRIFICATION SIMPLE : COMPARAISON DIRECTE DES MOTS DE PASSE
        # ====================================================================
        
        # Comparer directement le mot de passe saisi avec celui de la base
        if password == password_db:
            # ✅ MOT DE PASSE CORRECT !

            # 1) Vérifier d'abord si l'utilisateur lui-même est actif
            user_actif = donnees.get('actif', True)
            if user_actif is False:
                return False, None, "Ton compte utilisateur a été désactivé par ton salon."

            # 2) Vérifier maintenant l'état du salon (sauf pour SUPER_ADMIN qui n'a pas de salon)
            role_utilisateur = str(donnees.get('role', '')).upper().strip()
            salon_id = donnees.get('salon_id')

            if role_utilisateur != 'SUPER_ADMIN' and salon_id:
                try:
                    salon_model = SalonModel(self.db_connection)
                    salon_info = salon_model.obtenir_salon_by_id(salon_id)
                    # Si le salon existe et est inactif (False)
                    if salon_info and salon_info.get('actif') is False:
                        return False, None, "Ton salon a été désactivé. Contacte An's Learning  698192507."
                except Exception as e:
                    # En cas d'erreur de récupération du salon, on log mais on ne bloque pas la connexion
                    print(f"Erreur contrôle salon actif lors de l'authentification: {e}")

            return True, donnees, f"Bienvenue {donnees['prenom']} {donnees['nom']}"
        else:
            # ❌ MOT DE PASSE INCORRECT
            return False, None, "Mot de passe incorrect"
    
    def initialiser_tables(self) -> bool:
        """
        INITIALISER LES TABLES DE LA BASE DE DONNÉES
        
        POURQUOI ? Pour créer les tables si elles n'existent pas encore
        QUAND ? Appelé automatiquement lors de la première connexion
        
        RETOURNE : True si succès, False sinon
        """
        return self.couturier_model.creer_tables()
