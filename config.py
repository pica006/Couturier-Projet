"""
========================================
FICHIER DE CONFIGURATION (config.py)
========================================

POURQUOI CE FICHIER ?
---------------------
Ce fichier contient TOUTES les configurations de l'application.
Au lieu de mettre les paramètres partout dans le code, on les centralise ici.
Avantage : Si on veut changer quelque chose (ex: ajouter un modèle), 
on modifie uniquement ce fichier, pas tout le code !

COMMENT IL EST UTILISÉ ?
------------------------
Les autres fichiers importent ce fichier avec : from config import MODELES, MESURES, etc.
Exemple : Dans views/commande_view.py, on fait "from config import MODELES"
          pour afficher la liste des modèles disponibles.

OÙ IL EST UTILISÉ ?
-------------------
- app.py : Utilise DATABASE_CONFIG pour se connecter à la base
- views/commande_view.py : Utilise MODELES et MESURES pour les formulaires
- controllers/pdf_controller.py : Utilise PDF_STORAGE_PATH pour sauvegarder les PDF
"""

# ============================================================================
# IMPORT DES MODULES NÉCESSAIRES
# ============================================================================

# os : Module Python pour interagir avec le système d'exploitation
# Utilisé ici pour créer des chemins de fichiers et des dossiers
import os

# Charger .env dès l'import de config (pour DB_PASSWORD, etc.)
try:
    from dotenv import load_dotenv
    load_dotenv()
except Exception:
    pass

# ============================================================================
# CONFIGURATION DE L'APPLICATION
# ============================================================================

# POURQUOI ? Pour personnaliser le nom et l'apparence de l'application
# COMMENT ? Modifiez ces valeurs pour changer le nom et le sous-titre
# UTILISÉ OÙ ? Dans app.py pour afficher le header avec logo et nom

APP_CONFIG = {
    'name': 'An\'s Learning',           # Nom principal de l'application
    'subtitle': 'Système de gestion d\'atelier',  # Sous-titre/description
    'logo_path': 'assets/logo',             # Chemin du logo (sans extension)
    # Formats de logo supportés : .png, .jpg, .jpeg
    # Le système cherchera automatiquement logo.png, puis logo.jpg, puis logo.jpeg
    'wallpaper_url': 'assets/background_dark.png',  # Image de fond (fichier local)
    # Si None, aucune image de fond ne sera affichée
}

# ============================================================================
# IMAGES DE FOND PAR PAGE (zone principale, après connexion)
# ============================================================================
# Fichiers dans assets/ : chaque page affiche son image en arrière-plan.
# Clé = identifiant de la page (st.session_state.page), valeur = nom du fichier.
PAGE_BACKGROUND_IMAGES = {
    'administration': 'Admnistrateur.png',       # Page Administration
    'super_admin_dashboard': 'Admnistrateur.png',  # Dashboard Super Admin
    'nouvelle_commande': 'commandes.png',        # Nouvelle commande
    'liste_commandes': 'commandes.png',         # Mes commandes
    'dashboard': 'TableauDeBord.png',            # Tableau de bord
    'comptabilite': 'Comptabilite.png',         # Comptabilité
    'charges': 'Charges.png',                    # Mes charges
    'fermer_commandes': 'commandes.png',        # Fermer mes commandes
    'calendrier': 'commandes.png',              # Mon calendrier
}

# ============================================================================
# BRANDING (COULEURS & STYLE)
# ============================================================================
#
# Modifiez ces couleurs pour coller au branding exact de vos clients.
# Ces valeurs sont utilisées sur la page de connexion (style luxe).
BRANDING = {
    'primary': '#C9A227',   # Or principal
    'secondary': '#0E0B08', # Noir profond
    'accent': '#F5EFE6',    # Ivoire
    'text_dark': '#1A140F', # Texte sombre
    'text_light': '#F2ECE3' # Texte clair
}

# ============================================================================
# INFORMATIONS DE L'ENTREPRISE
# ============================================================================
#
# Ces informations sont affichées sur la page de connexion.
COMPANY_INFO = {
    'name': "An's Learning",
    'address': 'Douala - Kotto',
    'manager': 'Sango Justin',
    'phone': '698192507',
    'email': 'andresgroup63@gmail.com'
}

# ============================================================================
# CONFIGURATION DE LA BASE DE DONNÉES
# ============================================================================

# POURQUOI ? Pour stocker les informations de connexion à la base de données
# COMMENT ? Détection automatique : Render (variables d'environnement) ou Local (PostgreSQL)
# UTILISÉ OÙ ? Dans app.py et views/auth_view.py lors de la connexion

# Détecter si on est sur Render (production)
IS_RENDER = os.getenv('RENDER') is not None or os.getenv('DATABASE_HOST') is not None

if IS_RENDER:
    # ========== CONFIGURATION RENDER (PRODUCTION) ==========
    # Les variables d'environnement sont automatiquement configurées par Render
    # sslmode=require : requis pour PostgreSQL sur Render
    DATABASE_CONFIG = {
        'render_production': {
            'host': os.getenv('DATABASE_HOST', ''),
            'port': os.getenv('DATABASE_PORT', '5432'),
            'database': os.getenv('DATABASE_NAME', ''),
            'user': os.getenv('DATABASE_USER', ''),
            'password': os.getenv('DATABASE_PASSWORD', ''),
            'sslmode': os.getenv('DATABASE_SSLMODE', 'require')
        }
    }
else:
    # ========== CONFIGURATION LOCAL (POSTGRESQL) ==========
    # Configuration pour PostgreSQL installé localement sur votre PC
    # Dans .env utilisez : DB_HOST, DB_PORT=5432, DB_NAME=db_couturier, DB_USER=postgres, DB_PASSWORD=...
    # Attention : le port 3306 est pour MySQL ; PostgreSQL utilise le port 5432 !
    _port = os.getenv('DB_PORT', '5432')
    try:
        _port = int(_port)
    except ValueError:
        _port = 5432
    DATABASE_CONFIG = {
        'postgresql_local': {
            'host': os.getenv('DB_HOST', 'localhost'),
            'port': _port,
            'database': os.getenv('DB_NAME', 'db_couturier'),
            'user': os.getenv('DB_USER', 'postgres'),
            'password': os.getenv('DB_PASSWORD', '')  # À mettre dans .env uniquement
        }
    }

# ============================================================================
# MODÈLES DE VÊTEMENTS DISPONIBLES
# ============================================================================

# POURQUOI ? Pour définir tous les types de vêtements que le couturier peut faire
# COMMENT ? Dictionnaire à 3 niveaux : catégorie → sexe → liste de modèles
# UTILISÉ OÙ ? Dans views/commande_view.py pour afficher les options dans le formulaire
#
# STRUCTURE :
# MODELES['adulte']['homme'] → retourne la liste des modèles pour homme adulte
# MODELES['enfant']['fille'] → retourne la liste des modèles pour fille
#
# COMMENT AJOUTER UN MODÈLE ?
# Ajoutez simplement le nom dans la liste appropriée, exemple :
# 'homme': ['Costume 3 pièces', 'Costume 2 pièces', 'VOTRE NOUVEAU MODÈLE']

MODELES = {
    # ========== CATÉGORIE : ADULTE ==========
    'adulte': {
        # --- Modèles pour HOMME ---
        'homme': [
            'Costume 3 pièces',      # Veste + pantalon + gilet
            'Costume 2 pièces',      # Veste + pantalon
            'Pantalon classique',    # Pantalon seul
            'Chemise sur mesure',    # Chemise personnalisée
            'Veste',                 # Veste seule
            'Boubou',                # Vêtement traditionnel africain
            'Caftan',                # Vêtement traditionnel
            'Gandoura'               # Vêtement traditionnel
        ],
        
        # --- Modèles pour FEMME ---
        'femme': [
            'Robe de soirée',        # Pour événements formels
            'Robe cocktail',         # Pour soirées
            'Tailleur jupe',         # Ensemble professionnel avec jupe
            'Tailleur pantalon',     # Ensemble professionnel avec pantalon
            'Robe traditionnelle',   # Vêtement culturel
            'Caftan',                # Vêtement traditionnel
            'Boubou',                # Vêtement traditionnel africain
            'Ensemble pagne'         # Ensemble en tissu pagne
        ]
    },
    
    # ========== CATÉGORIE : ENFANT ==========
    'enfant': {
        # --- Modèles pour GARÇON ---
        'garcon': [
            'Costume enfant',        # Costume adapté aux enfants
            'Pantalon',              # Pantalon simple
            'Chemise',               # Chemise enfant
            'Ensemble traditionnel', # Tenue traditionnelle
            'Boubou enfant'          # Boubou taille enfant
        ],
        
        # --- Modèles pour FILLE ---
        'fille': [
            'Robe de cérémonie',     # Pour événements spéciaux
            'Robe casual',           # Robe de tous les jours
            'Ensemble jupe',         # Ensemble avec jupe
            'Robe traditionnelle',   # Tenue culturelle
            'Boubou enfant'          # Boubou taille enfant
        ]
    }
}

# ============================================================================
# MESURES REQUISES PAR MODÈLE
# ============================================================================

# POURQUOI ? Chaque modèle de vêtement a ses propres mesures spécifiques
# COMMENT ? Dictionnaire avec le nom du modèle comme clé → liste de mesures
# UTILISÉ OÙ ? Dans views/commande_view.py pour générer les champs de saisie selon le modèle choisi
#
# EXEMPLE D'UTILISATION :
# mesures_boubou = MESURES['Boubou']
# → Retourne ['Tour de cou', 'Largeur épaules', ...]
# Ensuite, on crée un champ de saisie pour chaque mesure
#
# IMPORTANT : Le nom du modèle doit correspondre EXACTEMENT à celui dans MODELES
# COMMENT AJOUTER UNE MESURE ?
# Ajoutez-la dans la liste du modèle approprié, elle apparaîtra automatiquement dans le formulaire

MESURES = {
    # ========== MODÈLES HOMME ADULTE ==========
    'Costume 3 pièces': [
        'Tour de cou',
        'Largeur épaules',
        'Tour de poitrine',
        'Tour de taille',
        'Tour de hanches',
        'Longueur dos',
        'Longueur manche',
        'Tour de bras',
        'Longueur pantalon',
        'Entrejambe',
        'Largeur pantalon (cuisse)'
    ],
    
    'Costume 2 pièces': [
        'Tour de cou',
        'Largeur épaules',
        'Tour de poitrine',
        'Tour de taille',
        'Tour de hanches',
        'Longueur dos',
        'Longueur manche',
        'Tour de bras',
        'Longueur pantalon',
        'Entrejambe',
        'Largeur pantalon (cuisse)'
    ],
    
    'Pantalon classique': [
        'Tour de taille',
        'Tour de hanches',
        'Longueur pantalon',
        'Entrejambe',
        'Largeur pantalon (cuisse)',
        'Largeur pantalon (bas)'
    ],
    
    'Chemise sur mesure': [
        'Tour de cou',
        'Largeur épaules',
        'Tour de poitrine',
        'Tour de taille',
        'Longueur dos',
        'Longueur manche',
        'Tour de bras',
        'Longueur chemise'
    ],
    
    'Veste': [
        'Tour de cou',
        'Largeur épaules',
        'Tour de poitrine',
        'Tour de taille',
        'Longueur dos',
        'Longueur manche',
        'Tour de bras',
        'Longueur veste'
    ],
    
    'Boubou': [
        'Tour de cou',
        'Largeur épaules',
        'Tour de poitrine',
        'Tour de taille',
        'Longueur dos',
        'Longueur manche',
        'Longueur boubou',
        'Largeur bas'
    ],
    
    'Caftan': [
        'Tour de cou',
        'Largeur épaules',
        'Tour de poitrine',
        'Tour de taille',
        'Tour de hanches',
        'Longueur dos',
        'Longueur manche',
        'Longueur caftan',
        'Largeur bas'
    ],
    
    'Gandoura': [
        'Tour de cou',
        'Largeur épaules',
        'Tour de poitrine',
        'Tour de taille',
        'Longueur dos',
        'Longueur manche',
        'Longueur gandoura',
        'Largeur bas'
    ],
    
    # ========== MODÈLES FEMME ADULTE ==========
    'Robe de soirée': [
        'Tour de cou',
        'Largeur épaules',
        'Tour de poitrine',
        'Tour de taille',
        'Tour de hanches',
        'Longueur dos',
        'Longueur manche',
        'Tour de bras',
        'Longueur robe',
        'Hauteur poitrine'
    ],
    
    'Robe cocktail': [
        'Tour de cou',
        'Largeur épaules',
        'Tour de poitrine',
        'Tour de taille',
        'Tour de hanches',
        'Longueur dos',
        'Longueur manche',
        'Tour de bras',
        'Longueur robe',
        'Hauteur poitrine'
    ],
    
    'Tailleur jupe': [
        'Tour de cou',
        'Largeur épaules',
        'Tour de poitrine',
        'Tour de taille',
        'Tour de hanches',
        'Longueur dos',
        'Longueur manche',
        'Tour de bras',
        'Longueur jupe',
        'Hauteur poitrine'
    ],
    
    'Tailleur pantalon': [
        'Tour de cou',
        'Largeur épaules',
        'Tour de poitrine',
        'Tour de taille',
        'Tour de hanches',
        'Longueur dos',
        'Longueur manche',
        'Tour de bras',
        'Longueur pantalon',
        'Entrejambe',
        'Hauteur poitrine'
    ],
    
    'Robe traditionnelle': [
        'Tour de cou',
        'Largeur épaules',
        'Tour de poitrine',
        'Tour de taille',
        'Tour de hanches',
        'Longueur dos',
        'Longueur manche',
        'Longueur robe',
        'Largeur bas'
    ],
    
    'Ensemble pagne': [
        'Tour de cou',
        'Largeur épaules',
        'Tour de poitrine',
        'Tour de taille',
        'Tour de hanches',
        'Longueur dos',
        'Longueur manche',
        'Longueur pagne',
        'Largeur bas'
    ],
    
    # Note: 'Caftan' et 'Boubou' pour femme utilisent les mêmes mesures que pour homme
    # (déjà définis plus haut dans la section homme)
    
    # ========== MODÈLES ENFANT FILLE (suite) ==========
    'Robe traditionnelle': [
        'Tour de cou',
        'Tour de poitrine',
        'Tour de taille',
        'Tour de hanches',
        'Longueur dos',
        'Longueur manche',
        'Longueur robe',
        'Largeur bas'
    ],
    
    # ========== MODÈLES ENFANT GARÇON ==========
    'Costume enfant': [
        'Tour de cou',
        'Tour de poitrine',
        'Tour de taille',
        'Longueur dos',
        'Longueur manche',
        'Longueur pantalon',
        'Entrejambe'
    ],
    
    'Pantalon': [
        'Tour de taille',
        'Tour de hanches',
        'Longueur pantalon',
        'Entrejambe',
        'Largeur pantalon (cuisse)'
    ],
    
    'Chemise': [
        'Tour de cou',
        'Tour de poitrine',
        'Tour de taille',
        'Longueur dos',
        'Longueur manche',
        'Longueur chemise'
    ],
    
    'Ensemble traditionnel': [
        'Tour de cou',
        'Tour de poitrine',
        'Tour de taille',
        'Longueur dos',
        'Longueur manche',
        'Longueur ensemble',
        'Largeur bas'
    ],
    
    'Boubou enfant': [
        'Tour de cou',
        'Tour de poitrine',
        'Tour de taille',
        'Longueur dos',
        'Longueur manche',
        'Longueur boubou',
        'Largeur bas'
    ],
    
    # ========== MODÈLES ENFANT FILLE ==========
    'Robe de cérémonie': [
        'Tour de cou',
        'Tour de poitrine',
        'Tour de taille',
        'Tour de hanches',
        'Longueur dos',
        'Longueur manche',
        'Longueur robe'
    ],
    
    'Robe casual': [
        'Tour de cou',
        'Tour de poitrine',
        'Tour de taille',
        'Tour de hanches',
        'Longueur dos',
        'Longueur manche',
        'Longueur robe'
    ],
    
    'Ensemble jupe': [
        'Tour de cou',
        'Tour de poitrine',
        'Tour de taille',
        'Tour de hanches',
        'Longueur dos',
        'Longueur manche',
        'Longueur jupe'
    ]
}

# ============================================================================
# CONFIGURATION EMAIL (SMTP)
# ============================================================================
#
# Variables d'environnement recommandées :
# - EMAIL_HOST, EMAIL_PORT, EMAIL_USER, EMAIL_PASSWORD
# - EMAIL_FROM (optionnel)
#
# En production (Render), définissez EMAIL_HOST, EMAIL_PORT, EMAIL_USER, EMAIL_PASSWORD dans les variables d'environnement.
# En local, mettez-les dans .env (ne jamais commiter de vrais mots de passe dans le code).
EMAIL_CONFIG = {
    'enabled': True,
    'host': os.getenv('EMAIL_HOST', 'smtp.gmail.com'),
    'port': int(os.getenv('EMAIL_PORT', '587')),
    'user': os.getenv('EMAIL_USER', ''),
    'password': os.getenv('EMAIL_PASSWORD', ''),
    'from_email': os.getenv('EMAIL_FROM', os.getenv('EMAIL_USER', '')),
    'use_tls': True,
    'use_ssl': False
}

# ============================================================================
# RÉPERTOIRE DE STOCKAGE DES PDF
# ============================================================================

# POURQUOI ? Pour définir où sauvegarder les PDF générés
# COMMENT ? On crée un chemin vers le dossier 'pdfs' à côté de ce fichier
# UTILISÉ OÙ ? Dans controllers/pdf_controller.py lors de la génération de PDF
#
# EXPLICATION LIGNE PAR LIGNE :
# 1. os.path.dirname(__file__) → Obtient le dossier où se trouve config.py
#    Exemple : Si config.py est dans x:/CouturierProjet/, ça retourne x:/CouturierProjet/
#
# 2. os.path.join(..., 'pdfs') → Ajoute 'pdfs' au chemin
#    Résultat : x:/CouturierProjet/pdfs/
#
# 3. if not os.path.exists(...) → Vérifie si le dossier existe
#    Si le dossier n'existe pas, on le crée avec os.makedirs()
 
PDF_STORAGE_PATH = os.path.join(os.path.dirname(__file__), 'pdfs')

# Créer le dossier 'pdfs' s'il n'existe pas encore
if not os.path.exists(PDF_STORAGE_PATH):
    os.makedirs(PDF_STORAGE_PATH)  # Crée le dossier et tous les dossiers parents si nécessaire

# ============================================================================
# RÉPERTOIRE DE STOCKAGE DES DOCUMENTS DE CHARGES
# ============================================================================

# POURQUOI ? Pour stocker les factures et justificatifs des charges
# COMMENT ? On crée un chemin vers le dossier 'charges_docs' à côté de ce fichier
# UTILISÉ OÙ ? Dans views/comptabilite_view.py lors de l'upload de documents

CHARGES_STORAGE_PATH = os.path.join(os.path.dirname(__file__), 'charges_docs')

# Créer le dossier 'charges_docs' s'il n'existe pas encore
if not os.path.exists(CHARGES_STORAGE_PATH):
    os.makedirs(CHARGES_STORAGE_PATH)
