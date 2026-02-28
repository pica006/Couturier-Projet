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
    """SpiritStitch refonte: layout 40/60, fond premium #6C63FF→#00C9A7, glass, CTA dominant (Stripe/Linear)."""
    return """
    <style>
    /* ========== CACHER SIDEBAR STREAMLIT POUR PLEINE LARGEUR LOGIN ========== */
    [data-testid="stSidebar"] { display: none !important; }
    .main .block-container {
        max-width: 100% !important;
        padding: 0 !important;
        margin: 0 !important;
    }
    /* ========== FOND GLOBAL : premium, profondeur (pas pastel) ========== */
    .stApp {
        background: linear-gradient(135deg, #6C63FF 0%, #00C9A7 100%) !important;
        min-height: 100vh;
        position: relative;
    }
    .stApp::before {
        content: '';
        position: fixed;
        inset: 0;
        background: radial-gradient(ellipse 70% 60% at 70% 50%, rgba(108, 99, 255, 0.35) 0%, transparent 55%),
                    radial-gradient(ellipse 50% 50% at 30% 80%, rgba(0, 201, 167, 0.2) 0%, transparent 50%);
        pointer-events: none;
        z-index: 0;
    }
    .stApp::after {
        content: '';
        position: fixed;
        inset: 0;
        background: rgba(255, 255, 255, 0.05);
        pointer-events: none;
        z-index: 0;
    }
    .login-page-wrapper { position: relative; z-index: 1; min-height: 100vh; width: 100%; }
    /* ========== LAYOUT 40% / 60% ========== */
    .login-page-wrapper [data-testid="column"]:first-child {
        background: rgba(255, 255, 255, 0.15) !important;
        backdrop-filter: blur(30px); -webkit-backdrop-filter: blur(30px);
        border-right: 1px solid rgba(255, 255, 255, 0.12);
        min-height: 100vh;
        display: flex !important;
        flex-direction: column !important;
        justify-content: center !important;
        padding: 2.5rem 2rem !important;
    }
    .login-page-wrapper [data-testid="column"]:last-child {
        display: flex !important;
        align-items: center !important;
        justify-content: center !important;
        min-height: 100vh;
        padding: 2rem !important;
    }
    /* ========== SIDEBAR BRANDING (gauche) ========== */
    .login-branding-logo {
        font-size: 40px !important;
        font-weight: 800 !important;
        background: linear-gradient(180deg, #FFFFFF 0%, #E0E0FF 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        background-clip: text;
        margin-bottom: 0.5rem;
        letter-spacing: -0.02em;
    }
    .login-branding-subtitle {
        color: rgba(255, 255, 255, 0.8) !important;
        font-size: 1rem;
        margin-bottom: 1.25rem;
        font-weight: 500;
    }
    .login-branding-desc {
        color: rgba(255, 255, 255, 0.7) !important;
        font-size: 0.9375rem;
        line-height: 1.5;
        max-width: 280px;
    }
    .login-branding-icon {
        margin-top: 2.5rem;
        opacity: 0.9;
    }
    /* ========== CARTE LOGIN (droite) : flottante, glass ========== */
    .login-theme-card {
        background: rgba(255, 255, 255, 0.85) !important;
        backdrop-filter: blur(25px); -webkit-backdrop-filter: blur(25px);
        border-radius: 22px !important;
        box-shadow: 0 40px 80px rgba(0, 0, 0, 0.25) !important;
        padding: 3rem !important;
        margin: 0 auto;
        max-width: 420px;
        width: 100%;
        border: 1px solid rgba(255, 255, 255, 0.5);
    }
    /* ========== TITRE CARTE : SpiritStitch 38px gradient, Authentification #333 ========== */
    .login-theme-title {
        font-size: 38px !important;
        font-weight: 800 !important;
        letter-spacing: -0.02em !important;
        text-align: center;
        margin-bottom: 0.35rem;
        background: linear-gradient(135deg, #6C63FF 0%, #00C9A7 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        background-clip: text;
    }
    .login-theme-title-tone1, .login-theme-title-tone2 { display: none; }
    .login-theme-subtitle { display: none; }
    .login-theme-card .login-theme-label {
        text-align: center;
        margin-bottom: 1.5rem;
        color: #333 !important;
        font-size: 1rem !important;
        font-weight: 600 !important;
    }
    .login-theme-card h3 { display: none; }
    /* ========== INPUTS : fond blanc, border #E5E7EB, focus #6C63FF glow ========== */
    .login-theme-card [data-testid="stForm"] { margin-top: 0.5rem; }
    .login-theme-card [data-testid="stTextInput"] > div,
    .login-theme-card [data-testid="stPasswordInput"] > div { background: transparent !important; }
    .login-theme-card .stTextInput > div > div,
    .login-theme-card .stPasswordInput > div > div {
        background: #ffffff !important;
        border: 1px solid #E5E7EB !important;
        border-radius: 12px !important;
        padding: 14px !important;
        min-height: 48px !important;
        transition: border-color 0.2s ease, box-shadow 0.2s ease;
    }
    .login-theme-card .stTextInput > div > div:focus-within,
    .login-theme-card .stPasswordInput > div > div:focus-within {
        border-color: #6C63FF !important;
        box-shadow: 0 0 0 3px rgba(108, 99, 255, 0.2) !important;
    }
    .login-theme-card .stTextInput input,
    .login-theme-card .stPasswordInput input {
        background: #ffffff !important;
        border: none !important;
        padding: 14px !important;
        font-size: 1rem !important;
        color: #111 !important;
    }
    .login-theme-card .stTextInput input::placeholder,
    .login-theme-card .stPasswordInput input::placeholder { color: #9CA3AF !important; }
    .login-theme-card [data-testid="stForm"] label,
    .login-theme-card [data-testid="stForm"] label p {
        font-weight: 500 !important;
        color: #374151 !important;
        font-size: 0.9375rem !important;
    }
    .login-theme-card [data-testid="stTextInput"],
    .login-theme-card [data-testid="stPasswordInput"] { margin-bottom: 1rem !important; }
    /* ========== BOUTON PRINCIPAL : dominant, gradient, hover scale + shadow ========== */
    .login-theme-card .stButton > button,
    .login-theme-card button[kind="primary"] {
        width: 100% !important;
        padding: 16px 1.5rem !important;
        min-height: 52px !important;
        border-radius: 14px !important;
        background: linear-gradient(135deg, #6C63FF 0%, #00C9A7 100%) !important;
        color: #fff !important;
        border: none !important;
        font-weight: 700 !important;
        font-size: 1.0625rem !important;
        transition: transform 0.2s ease, box-shadow 0.2s ease;
    }
    .login-theme-card .stButton > button:hover,
    .login-theme-card button[kind="primary"]:hover {
        transform: scale(1.03);
        box-shadow: 0 15px 30px rgba(108, 99, 255, 0.4) !important;
    }
    .login-theme-forgot { text-align: center; margin-top: 1rem; }
    .login-theme-forgot a { color: #6C63FF; font-size: 0.875rem; text-decoration: none; font-weight: 500; }
    .login-theme-forgot a:hover { color: #00C9A7; }
    .login-theme-support {
        color: #6B7280;
        font-size: 0.8rem;
        text-align: center;
        margin-top: 1.25rem;
        padding-top: 1rem;
        border-top: 1px solid #E5E7EB;
    }
    /* ========== RESPONSIVE MOBILE : empiler colonnes ========== */
    @media (max-width: 768px) {
        .login-page-wrapper [data-testid="column"]:first-child {
            min-height: auto;
            padding: 2rem 1.5rem !important;
        }
        .login-page-wrapper [data-testid="column"]:last-child {
            min-height: auto;
            padding: 1.5rem 1rem !important;
        }
        .login-theme-card { max-width: 100%; padding: 2rem !important; }
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
        max-width: 560px;
        min-width: 420px;
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
        min-height: 52px !important;
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
        padding: 1rem 1.2rem !important;
        font-size: 1.0625rem !important;
        min-height: 52px !important;
        line-height: 1.4 !important;
        color: #1f2937 !important;
    }
    .login-theme-card .stTextInput input::placeholder,
    .login-theme-card .stPasswordInput input::placeholder { color: #9CA3AF !important; }
    .login-theme-card .stTextInput input:focus,
    .login-theme-card .stPasswordInput input:focus { outline: none !important; box-shadow: none !important; }
    .login-theme-card [data-testid="stForm"] label,
    .login-theme-card [data-testid="stForm"] label p { font-weight: 500 !important; color: #374151 !important; font-size: 1rem !important; }
    .login-theme-card [data-testid="stTextInput"],
    .login-theme-card [data-testid="stPasswordInput"] { margin-bottom: 1rem !important; }
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
