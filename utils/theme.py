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
# Deux tons : partie 1 = violet, partie 2 = turquoise
LOGIN_DISPLAY_TITLE_1 = "Spirit"
LOGIN_DISPLAY_TITLE_2 = "Stitch"
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
    """Version Premium (effet glass). Fond #E9E4F0 → #E3F4F4, carte glassmorphism plus grande et soignée."""
    return """
    <style>
    /* Fond diagonal doux */
    .stApp { background: linear-gradient(135deg, #E9E4F0 0%, #E3F4F4 100%) !important; min-height: 100vh; }
    .main .block-container { background: transparent !important; padding-top: 1.5rem; padding-bottom: 2rem; max-width: 680px; }
    /* Carte login : plus grande, glassmorphism soigné */
    .login-theme-card {
        background: rgba(255, 255, 255, 0.82) !important;
        backdrop-filter: blur(16px); -webkit-backdrop-filter: blur(16px);
        border: 1px solid rgba(255, 255, 255, 0.98);
        border-radius: 24px;
        box-shadow: 0 20px 60px rgba(0, 0, 0, 0.08), 0 0 0 1px rgba(255,255,255,0.5) inset;
        padding: 2.75rem 2.5rem;
        margin: 0 auto;
        max-width: 520px;
        min-width: 380px;
    }
    /* Titre SpiritStitch : deux tons, plus lisible */
    .login-theme-title {
        font-weight: 700; font-size: 2.1rem; letter-spacing: 0.03em;
        text-align: center; margin-bottom: 0.35rem;
    }
    .login-theme-title-tone1 { color: #B19CD9 !important; }
    .login-theme-title-tone2 { color: #40E0D0 !important; }
    .login-theme-subtitle { color: #6B7280; font-size: 0.95rem; text-align: center; margin-bottom: 1.5rem; letter-spacing: 0.01em; }
    .login-theme-card [data-testid="stForm"] { margin-top: 0.75rem; }
    .login-theme-card .stTextInput > div > div input { border-radius: 12px; border: 1px solid #E5E7EB; padding: 0.7rem 0.9rem; font-size: 1rem; }
    .login-theme-card .stButton > button, .login-theme-card button[kind="primary"] {
        background: linear-gradient(90deg, #B19CD9 0%, #40E0D0 100%) !important;
        color: #FFFFFF !important; border: none !important;
        border-radius: 14px !important; box-shadow: 0 4px 14px rgba(177, 156, 217, 0.3);
        font-weight: 600 !important; font-size: 1rem !important; width: 100%; padding: 0.75rem 1.25rem;
    }
    .login-theme-card .stButton > button:hover { opacity: 0.96; box-shadow: 0 6px 20px rgba(177, 156, 217, 0.4); }
    .login-theme-forgot { text-align: center; margin-top: 0.75rem; }
    .login-theme-forgot a { color: #40E0D0; font-size: 0.875rem; text-decoration: none; }
    .login-theme-forgot a:hover { color: #2db8aa; }
    .login-theme-support { color: #6B7280; font-size: 0.8rem; text-align: center; margin-top: 1.25rem; line-height: 1.4; padding-top: 1rem; border-top: 1px solid rgba(0,0,0,0.06); }
    #MainMenu { visibility: hidden; } footer { visibility: hidden; } header { visibility: hidden; }
    [data-testid="stForm"] .stAlert { margin-top: 0.5rem; }
    </style>
    """


def _login_css_ultra_minimal() -> str:
    """Version Ultra Minimal (fintech). Carte plus grande, épurée."""
    return """
    <style>
    .stApp { background: #F8F9FA !important; min-height: 100vh; }
    .main .block-container { background: transparent !important; padding-top: 1.5rem; padding-bottom: 2rem; max-width: 680px; }
    .login-theme-card {
        background: #FFFFFF !important;
        border-radius: 20px;
        box-shadow: 0 4px 24px rgba(0, 0, 0, 0.06);
        padding: 2.75rem 2.5rem;
        margin: 0 auto;
        max-width: 520px;
        min-width: 380px;
    }
    .login-theme-title {
        font-weight: 700; font-size: 2rem; letter-spacing: 0.02em;
        text-align: center; margin-bottom: 0.35rem;
    }
    .login-theme-title-tone1 { color: #8E7AB5 !important; }
    .login-theme-title-tone2 { color: #36CFC9 !important; }
    .login-theme-subtitle { color: #6B7280; font-size: 0.9rem; text-align: center; margin-bottom: 1.5rem; }
    .login-theme-card [data-testid="stForm"] { margin-top: 0.75rem; }
    .login-theme-card .stTextInput > div > div input { border-radius: 12px; border: 1px solid #E5E7EB; padding: 0.7rem 0.9rem; font-size: 1rem; }
    .login-theme-card .stButton > button, .login-theme-card button[kind="primary"] {
        background: linear-gradient(90deg, #8E7AB5 0%, #36CFC9 100%) !important;
        color: #FFFFFF !important; border: none !important;
        border-radius: 12px !important; box-shadow: 0 3px 12px rgba(142, 122, 181, 0.25);
        font-weight: 600 !important; font-size: 1rem !important; width: 100%; padding: 0.75rem 1.25rem;
    }
    .login-theme-card .stButton > button:hover { opacity: 0.92; }
    .login-theme-forgot { text-align: center; margin-top: 0.75rem; }
    .login-theme-forgot a { color: #36CFC9; font-size: 0.875rem; text-decoration: none; }
    .login-theme-forgot a:hover { color: #2ab5a9; }
    .login-theme-support { color: #6B7280; font-size: 0.8rem; text-align: center; margin-top: 1.25rem; line-height: 1.4; padding-top: 1rem; border-top: 1px solid #EEE; }
    #MainMenu { visibility: hidden; } footer { visibility: hidden; } header { visibility: hidden; }
    [data-testid="stForm"] .stAlert { margin-top: 0.5rem; }
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
