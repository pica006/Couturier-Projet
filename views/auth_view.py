"""
========================================
VUE D'AUTHENTIFICATION (auth_view.py)
========================================

POURQUOI CE FICHIER ?
---------------------
C'est la page de connexion de l'application. Elle gère :
1. La connexion automatique à la base de données (détection automatique Render/Local)
2. L'authentification du couturier avec son code et mot de passe

COMMENT IL EST UTILISÉ ?
------------------------
Appelé par app.py quand l'utilisateur n'est pas encore connecté.
Fonction principale : afficher_page_connexion()

OÙ IL EST UTILISÉ ?
-------------------
Dans app.py, ligne : afficher_page_connexion()
"""

import base64
import mimetypes
import os
import logging
import streamlit as st
from controllers.auth_controller import AuthController
from config import DATABASE_CONFIG, APP_CONFIG, BRANDING, VISUAL_SAFE_MODE, IS_RENDER
from utils.bottom_nav import load_site_content
from utils.theme import get_login_css, LOGIN_DISPLAY_TITLE_1, LOGIN_DISPLAY_TITLE_2, LOGIN_DISPLAY_SUBTITLE
from services.db_bootstrap_service import connect_and_initialize, validate_required_config
from utils.ui import (
    appliquer_style_pages_critiques,
    afficher_erreur_minimale,
    afficher_info_minimale,
    afficher_titre_section,
    etat_chargement,
)

logger = logging.getLogger(__name__)

def _resolve_logo_path():
    logo_base = APP_CONFIG.get('logo_path')
    if not logo_base:
        return None

    if os.path.isabs(logo_base) and os.path.exists(logo_base):
        return logo_base

    project_root = os.path.dirname(os.path.dirname(__file__))
    candidate = os.path.join(project_root, logo_base)

    if os.path.splitext(candidate)[1]:
        return candidate if os.path.exists(candidate) else None

    for ext in ('.png', '.jpg', '.jpeg'):
        possible = f"{candidate}{ext}"
        if os.path.exists(possible):
            return possible

    return None


def _get_logo_data_uri():
    logo_path = _resolve_logo_path()
    if not logo_path:
        return None

    mime_type, _ = mimetypes.guess_type(logo_path)
    if not mime_type:
        mime_type = 'image/png'

    try:
        with open(logo_path, 'rb') as file:
            encoded = base64.b64encode(file.read()).decode('utf-8')
        return f"data:{mime_type};base64,{encoded}"
    except Exception:
        return None


@st.cache_data(show_spinner=False)
def _load_wallpaper_data_uri(wallpaper_path: str):
    """Charge et encode l'image de fond en base64 (cache pour éviter 10s de chargement)."""
    if not wallpaper_path:
        return None
    project_root = os.path.dirname(os.path.dirname(__file__))
    image_path = os.path.join(project_root, wallpaper_path)
    if not os.path.exists(image_path):
        return None
    try:
        with open(image_path, 'rb') as f:
            img_b64 = base64.b64encode(f.read()).decode('utf-8')
        mime = mimetypes.guess_type(image_path)[0] or 'image/png'
        return f"data:{mime};base64,{img_b64}"
    except Exception:
        return None


def _get_lux_vars_style():
    return f"""
    <style>
    :root {{
        --lux-primary: {BRANDING.get('primary', '#C9A227')};
        --lux-secondary: {BRANDING.get('secondary', '#0E0B08')};
        --lux-accent: {BRANDING.get('accent', '#F5EFE6')};
        --lux-text-dark: {BRANDING.get('text_dark', '#1A140F')};
        --lux-text-light: {BRANDING.get('text_light', '#F2ECE3')};
    }}
    </style>
"""

# Styles CSS pour la page de connexion (appliqués dans afficher_page_connexion)
hide_st_style = """
    <style>
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    
    /* Boutons avec dégradé violet-bleu (pas de rouge !) */
    .login-scope .stButton > button {
        background: linear-gradient(135deg, #B19CD9 0%, #40E0D0 100%) !important;
        color: #FFFFFF !important;
        border: none !important;
        border-radius: 12px !important;
        padding: 0.75rem 1.5rem !important;
        font-weight: 500 !important;
        transition: all 0.3s ease !important;
        box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1) !important;
    }

    .login-scope .stButton > button:hover {
        background: linear-gradient(135deg, #B19CD9 0%, #40E0D0 100%) !important;
        color: #FFFFFF !important;
        transform: translateY(-2px);
        box-shadow: 0 4px 8px rgba(0, 0, 0, 0.1) !important;
        opacity: 0.9;
    }
    
    /* Boutons primaires - dégradé inversé */
    .login-scope button[kind="primary"],
    .login-scope button[data-baseweb="button"][kind="primary"] {
        background: linear-gradient(135deg, #40E0D0 0%, #B19CD9 100%) !important;
        color: #FFFFFF !important;
        border: none !important;
    }
    
    .login-scope button[kind="primary"]:hover,
    .login-scope button[kind="primary"]:active,
    .login-scope button[kind="primary"]:focus {
        background: linear-gradient(135deg, #40E0D0 0%, #B19CD9 100%) !important;
        color: #FFFFFF !important;
    }
    
    /* Empêcher Streamlit de mettre du rouge par défaut */
    .login-scope button[data-baseweb="button"] {
        background: linear-gradient(135deg, #B19CD9 0%, #40E0D0 100%) !important;
        color: #FFFFFF !important;
    }
    
    .login-scope button[data-baseweb="button"]:hover,
    .login-scope button[data-baseweb="button"]:active,
    .login-scope button[data-baseweb="button"]:focus {
        background: linear-gradient(135deg, #B19CD9 0%, #40E0D0 100%) !important;
        color: #FFFFFF !important;
    }

    /* =====================================================================
       PAGE DE CONNEXION - DESIGN PREMIUM
       ===================================================================== */
    .login-header {
        background: linear-gradient(135deg, #B19CD9 0%, #40E0D0 100%);
        padding: 2rem;
        border-radius: 16px;
        margin-bottom: 2rem;
        box-shadow: 0 4px 8px rgba(0,0,0,0.1);
        text-align: center;
    }

    .login-header-logo {
        max-width: min(240px, 85%);
        max-height: 240px;
        width: auto;
        height: auto;
        border-radius: 12px;
        margin: 0 auto 0.9rem auto;
        display: block;
        object-fit: contain;
        box-shadow: 0 3px 12px rgba(0,0,0,0.15);
    }

    .login-header-title {
        color: #FFFFFF;
        font-size: 2.1rem;
        font-weight: 700;
        margin-top: 0.6rem;
        font-family: Poppins, sans-serif;
        text-shadow: 0 2px 4px rgba(0,0,0,0.2);
    }

    .login-header-subtitle {
        color: rgba(255,255,255,0.95);
        margin-top: 0.4rem;
        font-size: 1.05rem;
    }

    .login-scope .login-hero {
        --hero-logo: none;
        background-image: linear-gradient(135deg, #0E0B08 0%, #251A12 100%), var(--hero-logo);
        background-repeat: no-repeat;
        background-position: right 24px bottom 18px;
        background-size: 240px;
        border: 1px solid rgba(201, 162, 39, 0.35);
        border-radius: 22px;
        padding: 2.7rem;
        box-shadow: 0 14px 30px rgba(0, 0, 0, 0.25);
    }

    .login-scope .login-badge {
        display: inline-block;
        padding: 0.35rem 0.9rem;
        border-radius: 999px;
        background: linear-gradient(135deg, var(--lux-primary) 0%, #E3C873 100%);
        color: #1A140F;
        font-size: 0.85rem;
        font-weight: 700;
        letter-spacing: 0.4px;
        margin-bottom: 1.1rem;
    }

    .login-scope .login-hero h1 {
        color: var(--lux-text-light);
        font-size: 2.35rem;
        margin: 0 0 0.8rem 0;
        line-height: 1.15;
        font-weight: 700;
    }

    .login-scope .login-hero p {
        color: rgba(242, 236, 227, 0.85);
        font-size: 1.02rem;
        margin: 0 0 1.3rem 0;
    }

    .login-scope .login-list {
        margin: 0;
        padding-left: 1.2rem;
        color: rgba(242, 236, 227, 0.88);
    }

    .login-scope .login-list li {
        margin-bottom: 0.6rem;
    }


    .login-scope [data-testid="column"]:nth-child(2) > div {
        display: flex !important;
        flex-direction: column !important;
        align-items: center !important;
        width: 100% !important;
    }

    .login-scope .login-card {
        background: var(--lux-accent);
        border-radius: 22px;
        border: 1px solid rgba(201, 162, 39, 0.3);
        padding: 2.8rem;
        box-shadow: 0 16px 32px rgba(0, 0, 0, 0.18);
        text-align: center;
        max-width: 560px;
        min-width: 380px;
        margin: 0 auto;
        width: 100%;
    }

    .login-scope .login-card h3 {
        font-size: 2.1rem !important;
        font-weight: 700 !important;
        margin-bottom: 0.5rem !important;
    }

    .login-scope .login-card h4 {
        font-size: 1.35rem !important;
        font-weight: 600 !important;
        margin-top: 1rem !important;
        margin-bottom: 1rem !important;
    }

    .login-scope .login-card [data-testid="stForm"] label,
    .login-scope .login-card [data-testid="stForm"] p {
        font-size: 1.15rem !important;
    }

    .login-scope .login-muted {
        color: rgba(26, 20, 15, 0.7);
        font-size: 1.2rem;
        margin-top: -0.6rem;
        margin-bottom: 1.2rem;
        line-height: 1.45;
    }

    .login-scope .login-support {
        margin-top: 1.2rem;
        padding-top: 1rem;
        border-top: 1px solid rgba(201, 162, 39, 0.2);
        color: rgba(26, 20, 15, 0.75);
        font-size: 1.12rem;
        text-align: center;
        line-height: 1.5;
    }

    .login-scope .login-company {
        margin-top: 1.6rem;
        background: rgba(20, 16, 12, 0.7);
        border: 1px solid rgba(201, 162, 39, 0.3);
        border-radius: 18px;
        padding: 1.5rem;
        box-shadow: 0 10px 20px rgba(0, 0, 0, 0.2);
    }

    .login-scope .login-company h3 {
        margin: 0 0 0.8rem 0;
        font-size: 1.1rem;
        color: var(--lux-text-light);
    }

    .login-scope .login-company p {
        margin: 0.35rem 0;
        color: rgba(242, 236, 227, 0.82);
    }

    .login-scope .stTextInput > div > div input,
    .login-scope .stPasswordInput > div > div input {
        border-radius: 12px !important;
        border: 1px solid rgba(201, 162, 39, 0.35) !important;
        padding: 0.75rem 1rem !important;
        background: #FFFFFF !important;
        font-size: 1.1rem !important;
    }

    .login-scope .stTextInput > div > div input:focus,
    .login-scope .stPasswordInput > div > div input:focus {
        border-color: var(--lux-primary) !important;
        box-shadow: 0 0 0 0.15rem rgba(201, 162, 39, 0.25) !important;
    }

    .login-scope .stButton > button,
    .login-scope button[kind="primary"],
    .login-scope button[data-baseweb="button"][kind="primary"] {
        background: linear-gradient(135deg, var(--lux-primary) 0%, #E3C873 100%) !important;
        color: #1A140F !important;
        border: none !important;
        font-weight: 700 !important;
        letter-spacing: 0.2px;
        font-size: 1.08rem !important;
        padding: 0.65rem 1.25rem !important;
    }

    .login-scope .stButton > button:hover,
    .login-scope button[kind="primary"]:hover,
    .login-scope button[data-baseweb="button"][kind="primary"]:hover {
        background: linear-gradient(135deg, #E3C873 0%, var(--lux-primary) 100%) !important;
        color: #1A140F !important;
        opacity: 0.95;
    }

    </style>
"""


def _ensure_db_connection() -> tuple[bool, str]:
    """
    Etablit la connexion DB uniquement quand c'est necessaire (au submit).
    """
    existing = st.session_state.get("db_connection")
    if existing is not None:
        try:
            if existing.is_connected() if hasattr(existing, "is_connected") else bool(existing.get_connection()):
                return True, ""
            st.session_state.db_connection = None
            st.session_state.db_type = None
        except Exception:
            st.session_state.db_connection = None
            st.session_state.db_type = None

    from config import IS_RENDER
    config_key = "render_production" if IS_RENDER else "postgresql_local"
    config = DATABASE_CONFIG.get(config_key, {})
    required = ("host", "database", "user", "password") if IS_RENDER else ("host", "database", "user")
    missing = validate_required_config(config, required)

    if missing:
        if IS_RENDER:
            return False, (
                "Configuration Render incomplète. Vérifiez les variables "
                "DATABASE_HOST, DATABASE_NAME, DATABASE_USER, DATABASE_PASSWORD."
            )
        return False, "Configuration PostgreSQL locale incomplète. Vérifiez config.py / .env."

    ok, db_connection, error_msg = connect_and_initialize(config)
    if not ok or not db_connection:
        base_label = "Render" if IS_RENDER else "PostgreSQL local"
        return False, f"Échec connexion {base_label}: {error_msg or 'Erreur inconnue'}"

    st.session_state.db_connection = db_connection
    st.session_state.db_type = config_key
    return True, ""


def afficher_page_connexion():
    """
    FONCTION PRINCIPALE DE LA PAGE DE CONNEXION
    
    POURQUOI ? Pour permettre à l'utilisateur de se connecter
    COMMENT ? Détection automatique de l'environnement :
        1. Sur Render : Connexion automatique via variables d'environnement
        2. En local : Connexion automatique via config.py (PostgreSQL local)
        3. Authentification : L'utilisateur entre son code couturier et mot de passe
    
    UTILISÉ OÙ ? Appelé dans app.py quand l'user n'est pas authentifié
    """
    appliquer_style_pages_critiques()

    # Appliquer le thème SpiritStitch (Premium Glass / Ultra Minimal) — couche présentation uniquement
    try:
        st.markdown(get_login_css(), unsafe_allow_html=True)
        if not VISUAL_SAFE_MODE:
            st.markdown(_get_lux_vars_style(), unsafe_allow_html=True)
    except Exception as e:
        logger.exception("Erreur affichage initial page connexion: %s", e)
        # En cas d'erreur UI, on réaffiche les éléments Streamlit natifs.
        st.markdown(
            "<style>header{visibility:visible!important;} footer{visibility:visible!important;}</style>",
            unsafe_allow_html=True,
        )
        afficher_erreur_minimale("Erreur d'initialisation de l'interface de connexion.")

    content = load_site_content()

    # ========================================================================
    # AUTHENTIFICATION DU COUTURIER
    # ========================================================================
    
    # Si on arrive ici, c'est qu'on est déjà connecté à la base de données
    # Maintenant, le couturier doit entrer son code pour s'authentifier
    
    # ====================================================================
    # FORMULAIRE D'AUTHENTIFICATION AVEC CODE COUTURIER
    # ====================================================================
    
    # POURQUOI ? Pour vérifier l'identité du couturier
    # COMMENT ? L'user entre son code + password, on vérifie dans la base de données
    st.markdown('<div class="login-scope">', unsafe_allow_html=True)
    
    _, form_col, _ = st.columns([1, 1.3, 1], gap="large")

    with form_col:
        # Carte d'authentification style SpiritStitch (thème depuis utils.theme)
        st.markdown(
            f'<div class="login-theme-card">'
            f'<div class="login-theme-title">{LOGIN_DISPLAY_TITLE_1}{LOGIN_DISPLAY_TITLE_2}</div>'
            f'<div class="login-theme-subtitle">{LOGIN_DISPLAY_SUBTITLE}</div>'
            f'<h3>Authentification</h3>',
            unsafe_allow_html=True
        )
        
        with st.form("auth_form", clear_on_submit=False):
            # Champ de saisie du code couturier
            code_couturier = st.text_input(
                "Code Couturier *",
                placeholder="Ex: COUT001",
                help="Votre code d'identification unique",
                key="code_input"
            )
            
            # Champ de saisie du mot de passe
            password_input = st.text_input(
                "Mot de passe *",
                type="password",
                placeholder="Entrez votre mot de passe",
                help="Votre mot de passe sécurisé",
                key="password_input"
            )
            
            # Bouton de soumission
            submit_auth = st.form_submit_button(
                "Se connecter",
                type="primary"
            )
            
            # Lien "Mot de passe oublié ?" (présentation modèle SpiritStitch)
            st.markdown(
                '<div class="login-theme-forgot"><a href="#">Mot de passe oublié ?</a></div>',
                unsafe_allow_html=True
            )
            
            # ================================================================
            # TRAITEMENT DE L'AUTHENTIFICATION
            # ================================================================
            
            if submit_auth:
                # Lire les valeurs aussi depuis session_state (plus robuste)
                code_value = st.session_state.get("code_input", code_couturier)
                password_value = st.session_state.get("password_input", password_input)

                # Nettoyer les espaces (évite échec si l'utilisateur tape des espaces)
                code_clean = (code_value or "").strip()
                password_clean = (password_value or "").strip()

                # On NE bloque plus ici sur les champs vides : on laisse le contrôleur
                # d'authentification renvoyer un message explicite (code vide, mot de passe vide, etc.)

                # Afficher un spinner pendant la vérification
                try:
                    with etat_chargement("Connexion à la base et vérification des identifiants..."):
                        ok_conn, msg_conn = _ensure_db_connection()
                        if not ok_conn:
                            afficher_erreur_minimale(msg_conn)
                        else:
                            # Créer un contrôleur d'authentification
                            # POURQUOI ? Pour gérer la logique d'authentification
                            auth_controller = AuthController(st.session_state.db_connection)

                            # Appeler la méthode authentifier() avec CODE + MOT DE PASSE (nettoyés)
                            # RETOURNE : (succès, données, message)
                            succes, donnees, message = auth_controller.authentifier(code_clean, password_clean)

                            # Si l'authentification a réussi
                            if succes:
                                # Sauvegarder l'état d'authentification dans la session
                                st.session_state.authentifie = True

                                # Sauvegarder les données du couturier
                                st.session_state.couturier_data = donnees

                                # Rediriger selon le rôle de l'utilisateur
                                # Si c'est un super administrateur, rediriger vers le dashboard super admin
                                role_utilisateur = donnees.get('role', '')
                                # Normaliser le rôle (gérer les variations : SUPER_ADMIN, super_admin, etc.)
                                role_normalise = str(role_utilisateur).upper().strip()

                                # Debug : afficher le rôle détecté (temporaire)
                                if role_normalise == 'SUPER_ADMIN':
                                    afficher_info_minimale(
                                        f"Rôle détecté : {role_utilisateur} → Redirection vers Dashboard Super Admin"
                                    )
                                    st.session_state.page = 'super_admin_dashboard'
                                else:
                                    # Pour les autres rôles, rediriger vers la page de nouvelle commande
                                    st.session_state.page = 'nouvelle_commande'

                                # Afficher un message de succès
                                st.success(f"✅ {message}")

                                # Afficher des ballons pour célébrer !
                                st.balloons()

                                # Recharger la page pour afficher l'interface principale
                                st.rerun()
                            else:
                                # Si l'authentification a échoué, afficher l'erreur
                                afficher_erreur_minimale(message)
                except Exception as e:
                    logger.exception("Erreur non capturee pendant la connexion: %s", e)
                    afficher_erreur_minimale(
                        "Une erreur inattendue est survenue pendant la connexion. Veuillez reessayer."
                    )
        
        support_text = content.get("support_text", "")
        if support_text:
            st.markdown(
                f'<div class="login-theme-support">{support_text}</div>',
                unsafe_allow_html=True,
            )
        st.markdown("</div><!-- login-theme-card -->", unsafe_allow_html=True)
    
    st.markdown("</div>", unsafe_allow_html=True)

    # Fond d'écran après le formulaire (réduit risque de réponse tronquée en prod)
    # En production (Render) : pas de data URI pour éviter payload lourd / timeout
    if not IS_RENDER:
        wallpaper_path = APP_CONFIG.get('wallpaper_url')
        data_uri = _load_wallpaper_data_uri(wallpaper_path) if wallpaper_path else None
        if data_uri:
            st.markdown(f"""
                <style>
                .stApp {{
                    background-image: url("{data_uri}") !important;
                    background-size: cover !important;
                    background-position: center !important;
                    background-attachment: fixed !important;
                    background-repeat: no-repeat !important;
                    background-color: transparent !important;
                    min-height: 100vh;
                }}
                .main .block-container {{
                    background: transparent !important;
                    padding-top: 2rem;
                    max-width: 1200px;
                }}
                </style>
            """, unsafe_allow_html=True)

