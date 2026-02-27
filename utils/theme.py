"""
========================================
THÈMES UI - SpiritStitch (MVC: couche présentation)
========================================

Données de thème uniquement : pas de logique métier.
Utilisé par : views/auth_view.py (page connexion), app.py (sidebar).

Thèmes : premium_glass | ultra_minimal
"""

import os

# Choix du thème : variable d'environnement THEME ou défaut premium_glass
THEME_ACTIVE = os.getenv("THEME", "premium_glass").strip().lower()
if THEME_ACTIVE not in ("premium_glass", "ultra_minimal"):
    THEME_ACTIVE = "premium_glass"

# Libellés affichés sur la page de connexion (identiques au modèle SpiritStitch)
LOGIN_DISPLAY_TITLE = "SpiritStitch"
LOGIN_DISPLAY_SUBTITLE = "Gestion intelligente de couture"


def get_login_css() -> str:
    """
    Retourne le bloc CSS pour la page de connexion selon le thème actif.
    Vue (auth_view) l'injecte tel quel ; pas de logique métier ici.
    """
    if THEME_ACTIVE == "ultra_minimal":
        return _login_css_ultra_minimal()
    return _login_css_premium_glass()


def _login_css_premium_glass() -> str:
    """Version Premium (effet glass). Fond #E9E4F0 → #E3F4F4, carte glassmorphism."""
    return """
    <style>
    /* Fond diagonal doux */
    .stApp { background: linear-gradient(135deg, #E9E4F0 0%, #E3F4F4 100%) !important; min-height: 100vh; }
    .main .block-container { background: transparent !important; padding-top: 2rem; max-width: 1200px; }
    /* Carte login : glassmorphism */
    .login-theme-card {
        background: rgba(255, 255, 255, 0.72) !important;
        backdrop-filter: blur(12px); -webkit-backdrop-filter: blur(12px);
        border: 1px solid rgba(255, 255, 255, 0.9);
        border-radius: 18px;
        box-shadow: 0 8px 32px rgba(0, 0, 0, 0.08);
        padding: 2rem;
        margin: 0 auto;
        max-width: 420px;
    }
    /* Titre SpiritStitch dégradé */
    .login-theme-title {
        font-weight: 700; font-size: 2rem; letter-spacing: 0.02em;
        background: linear-gradient(90deg, #B19CD9 0%, #40E0D0 100%);
        -webkit-background-clip: text; -webkit-text-fill-color: transparent;
        background-clip: text; text-align: center; margin-bottom: 0.25rem;
    }
    .login-theme-subtitle { color: #6B7280; font-size: 0.95rem; text-align: center; margin-bottom: 1.5rem; }
    /* Bouton Se connecter */
    .login-theme-card .stButton > button, .login-theme-card button[kind="primary"] {
        background: linear-gradient(90deg, #B19CD9 0%, #40E0D0 100%) !important;
        color: #FFFFFF !important; border: none !important;
        border-radius: 12px !important; box-shadow: 0 2px 8px rgba(177, 156, 217, 0.3);
        font-weight: 600 !important; width: 100%;
    }
    .login-theme-card .stButton > button:hover { opacity: 0.95; box-shadow: 0 4px 12px rgba(177, 156, 217, 0.4); }
    .login-theme-forgot { text-align: center; margin-top: 0.75rem; }
    .login-theme-forgot a { color: #9CA3AF; font-size: 0.875rem; text-decoration: none; }
    .login-theme-forgot a:hover { color: #6B7280; }
    #MainMenu { visibility: hidden; } footer { visibility: hidden; } header { visibility: hidden; }
    </style>
    """


def _login_css_ultra_minimal() -> str:
    """Version Ultra Minimal (fintech). Fond #F8F9FA, carte blanche, bouton sobre."""
    return """
    <style>
    .stApp { background: #F8F9FA !important; min-height: 100vh; }
    .main .block-container { background: transparent !important; padding-top: 2rem; max-width: 1200px; }
    .login-theme-card {
        background: #FFFFFF !important;
        border-radius: 14px;
        box-shadow: 0 1px 3px rgba(0, 0, 0, 0.06);
        padding: 2rem;
        margin: 0 auto;
        max-width: 420px;
    }
    .login-theme-title {
        font-weight: 700; font-size: 1.75rem; letter-spacing: 0.01em;
        background: linear-gradient(90deg, #8E7AB5 0%, #36CFC9 100%);
        -webkit-background-clip: text; -webkit-text-fill-color: transparent;
        background-clip: text; text-align: center; margin-bottom: 0.25rem;
    }
    .login-theme-subtitle { color: #6B7280; font-size: 0.9rem; text-align: center; margin-bottom: 1.5rem; }
    .login-theme-card .stButton > button, .login-theme-card button[kind="primary"] {
        background: linear-gradient(90deg, #8E7AB5 0%, #36CFC9 100%) !important;
        color: #FFFFFF !important; border: none !important;
        border-radius: 10px !important; box-shadow: 0 1px 4px rgba(142, 122, 181, 0.25);
        font-weight: 600 !important; width: 100%;
    }
    .login-theme-card .stButton > button:hover { opacity: 0.92; }
    .login-theme-forgot { text-align: center; margin-top: 0.75rem; }
    .login-theme-forgot a { color: #9CA3AF; font-size: 0.875rem; text-decoration: none; }
    .login-theme-forgot a:hover { color: #6B7280; }
    #MainMenu { visibility: hidden; } footer { visibility: hidden; } header { visibility: hidden; }
    </style>
    """


def get_sidebar_bg_css() -> str:
    """
    Retourne le CSS de fond de la sidebar selon le thème actif.
    Utilisé par app.py pour injecter le style (sans image en prod).
    """
    if THEME_ACTIVE == "ultra_minimal":
        return "background: #FFFFFF !important; border-right: 1px solid #E5E7EB !important;"
    # premium_glass
    return """
    background: linear-gradient(180deg, #ECE6F8 0%, #DFF7F4 100%) !important;
    border-right: 1px solid rgba(0, 0, 0, 0.06) !important;
    """
