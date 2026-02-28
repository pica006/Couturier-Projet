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
    """Prompt strict: SaaS haut de gamme, glass réel, dégradé #7B61FF → #00D4C7."""
    return """
    <style>
    /* FOND: grand dégradé + overlay blanc 60% pour adoucir, profondeur */
    .stApp {
        background: linear-gradient(180deg, rgba(255,255,255,0.6) 0%, rgba(255,255,255,0.5) 100%),
                    linear-gradient(135deg, #B19CD9 0%, #40E0D0 100%) !important;
        min-height: 100vh;
    }
    .main .block-container {
        background: transparent !important;
        padding-top: 1.5rem; padding-bottom: 2rem;
        max-width: 520px;
        margin-left: auto; margin-right: auto;
    }
    /* CARTE: glass réel, flottante */
    .login-theme-card {
        background: rgba(255, 255, 255, 0.75) !important;
        backdrop-filter: blur(25px); -webkit-backdrop-filter: blur(25px);
        border: 1px solid rgba(255, 255, 255, 0.4) !important;
        box-shadow: 0 30px 60px rgba(0, 0, 0, 0.15) !important;
        border-radius: 20px !important;
        padding: 2.5rem !important;
        margin: 0 auto;
        max-width: 480px;
    }
    /* TITRE: 42px, 800, letter-spacing 1px, dégradé #7B61FF → #00D4C7 */
    .login-theme-title {
        font-size: 42px !important;
        font-weight: 800 !important;
        letter-spacing: 1px !important;
        text-align: center;
        margin-bottom: 0.25rem;
        background: linear-gradient(90deg, #7B61FF 0%, #00D4C7 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        background-clip: text;
    }
    .login-theme-title-tone1, .login-theme-title-tone2 { display: none; }
    .login-theme-subtitle {
        color: #555 !important;
        font-size: 0.95rem;
        text-align: center;
        margin-bottom: 1.5rem;
    }
    .login-theme-card h3 {
        text-align: center;
        margin-bottom: 1rem;
        color: #333 !important;
        font-weight: 700;
    }
    /* INPUTS: zones de saisie premium, bien visibles et interactives */
    .login-theme-card [data-testid="stForm"] { margin-top: 0.75rem; }
    .login-theme-card [data-testid="stTextInput"] > div,
    .login-theme-card [data-testid="stPasswordInput"] > div {
        background: transparent !important;
    }
    .login-theme-card .stTextInput > div > div,
    .login-theme-card .stPasswordInput > div > div {
        background: rgba(255,255,255,0.95) !important;
        border: 1px solid rgba(0,0,0,0.1) !important;
        border-radius: 12px !important;
        box-shadow: 0 1px 3px rgba(0,0,0,0.04) !important;
        transition: border-color 0.2s ease, box-shadow 0.2s ease, background 0.2s ease;
    }
    .login-theme-card .stTextInput > div > div:focus-within,
    .login-theme-card .stPasswordInput > div > div:focus-within {
        border-color: #7B61FF !important;
        box-shadow: 0 0 0 3px rgba(123, 97, 255, 0.2) !important;
        background: #fff !important;
    }
    .login-theme-card .stTextInput input,
    .login-theme-card .stPasswordInput input {
        background: transparent !important;
        border: none !important;
        border-radius: 12px !important;
        padding: 0.85rem 1rem !important;
        font-size: 1rem !important;
        min-height: 48px !important;
        color: #1f2937 !important;
    }
    .login-theme-card .stTextInput input::placeholder,
    .login-theme-card .stPasswordInput input::placeholder {
        color: #9CA3AF !important;
    }
    .login-theme-card .stTextInput input:focus,
    .login-theme-card .stPasswordInput input:focus {
        outline: none !important;
        box-shadow: none !important;
    }
    .login-theme-card [data-testid="stForm"] label,
    .login-theme-card [data-testid="stForm"] label p {
        font-weight: 500 !important;
        color: #374151 !important;
        font-size: 0.9375rem !important;
    }
    /* BOUTON: 100%, padding 14px, radius 14px, dégradé intense, hover scale + ombre */
    .login-theme-card .stButton > button,
    .login-theme-card button[kind="primary"] {
        width: 100% !important;
        padding: 14px 1.25rem !important;
        border-radius: 14px !important;
        background: linear-gradient(90deg, #7B61FF 0%, #00D4C7 100%) !important;
        color: #FFFFFF !important;
        border: none !important;
        font-weight: 700 !important;
        font-size: 1rem !important;
        box-shadow: 0 8px 24px rgba(123, 97, 255, 0.35);
        transition: transform 0.2s ease, box-shadow 0.2s ease;
    }
    .login-theme-card .stButton > button:hover,
    .login-theme-card button[kind="primary"]:hover {
        transform: scale(1.03);
        box-shadow: 0 12px 32px rgba(123, 97, 255, 0.45);
    }
    .login-theme-forgot { text-align: center; margin-top: 0.75rem; }
    .login-theme-forgot a { color: #00D4C7; font-size: 0.875rem; text-decoration: none; }
    .login-theme-forgot a:hover { color: #00b8ad; }
    .login-theme-support {
        color: #555;
        font-size: 0.8rem;
        text-align: center;
        margin-top: 1.25rem;
        line-height: 1.4;
        padding-top: 1rem;
        border-top: 1px solid rgba(0,0,0,0.08);
    }
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
        font-weight: 800; font-size: 2rem; letter-spacing: 0.02em;
        text-align: center; margin-bottom: 0.35rem;
        background: linear-gradient(90deg, #8E7AB5 0%, #36CFC9 100%);
        -webkit-background-clip: text; -webkit-text-fill-color: transparent;
        background-clip: text;
    }
    .login-theme-subtitle { color: #6B7280; font-size: 0.9rem; text-align: center; margin-bottom: 1.5rem; }
    .login-theme-card [data-testid="stForm"] { margin-top: 0.75rem; }
    .login-theme-card [data-testid="stTextInput"] > div,
    .login-theme-card [data-testid="stPasswordInput"] > div { background: transparent !important; }
    .login-theme-card .stTextInput > div > div,
    .login-theme-card .stPasswordInput > div > div {
        background: #fff !important;
        border: 1px solid #E5E7EB !important;
        border-radius: 12px !important;
        box-shadow: 0 1px 2px rgba(0,0,0,0.04) !important;
        transition: border-color 0.2s ease, box-shadow 0.2s ease;
    }
    .login-theme-card .stTextInput > div > div:focus-within,
    .login-theme-card .stPasswordInput > div > div:focus-within {
        border-color: #8E7AB5 !important;
        box-shadow: 0 0 0 3px rgba(142, 122, 181, 0.18) !important;
    }
    .login-theme-card .stTextInput input,
    .login-theme-card .stPasswordInput input {
        background: transparent !important;
        border: none !important;
        padding: 0.85rem 1rem !important;
        font-size: 1rem !important;
        min-height: 48px !important;
        color: #1f2937 !important;
    }
    .login-theme-card .stTextInput input::placeholder,
    .login-theme-card .stPasswordInput input::placeholder { color: #9CA3AF !important; }
    .login-theme-card .stTextInput input:focus,
    .login-theme-card .stPasswordInput input:focus { outline: none !important; box-shadow: none !important; }
    .login-theme-card [data-testid="stForm"] label,
    .login-theme-card [data-testid="stForm"] label p { font-weight: 500 !important; color: #374151 !important; font-size: 0.9375rem !important; }
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
