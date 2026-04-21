"""
========================================
THEMES UI - SpiritStitch / An's Learning (couche presentation MVC)
========================================

Donnees de theme uniquement : pas de logique metier.
Utilise par : views/auth_view.py (page connexion), app.py (sidebar + global).

Themes : premium_glass (par defaut) | ultra_minimal

API publique (ne pas casser) :
    - get_login_css()           -> str : CSS de la page de connexion
    - get_sidebar_bg_css()      -> str : fond de la sidebar
    - get_app_premium_css()     -> str : CSS global apres connexion (optionnel)
    - get_brand_gradient()      -> str : dégradé primaire réutilisable
    - LOGIN_DISPLAY_TITLE_1 / _2 / LOGIN_DISPLAY_SUBTITLE
"""

import os

# Choix du theme : variable d'environnement THEME ou defaut premium_glass
THEME_ACTIVE = os.getenv("THEME", "premium_glass").strip().lower()
if THEME_ACTIVE not in ("premium_glass", "ultra_minimal"):
    THEME_ACTIVE = "premium_glass"

# Libelles affiches sur la page de connexion
LOGIN_DISPLAY_TITLE_1 = "Spirit"
LOGIN_DISPLAY_TITLE_2 = "Stitch"
LOGIN_DISPLAY_SUBTITLE = ""

# Palette premium (utilisable depuis d'autres modules)
BRAND_PRIMARY = "#6C63FF"       # violet profond
BRAND_ACCENT = "#00C9A7"        # turquoise
BRAND_PRIMARY_SOFT = "#8B7FFF"  # violet clair
BRAND_BG_FROM = "#E0C3FC"       # lavande
BRAND_BG_TO = "#8EC5FC"         # cyan clair
BRAND_TEXT = "#111827"
BRAND_TEXT_SOFT = "#6B7280"
BRAND_SURFACE = "#FFFFFF"
BRAND_SURFACE_SOFT = "#F8F9FC"
BRAND_BORDER = "#E5E7EB"


def get_brand_gradient(direction: str = "135deg") -> str:
    """Retourne le degrade principal de la marque."""
    return f"linear-gradient({direction}, {BRAND_PRIMARY} 0%, {BRAND_ACCENT} 100%)"


def get_login_css() -> str:
    """
    Retourne le bloc CSS pour la page de connexion selon le theme actif.
    """
    if THEME_ACTIVE == "ultra_minimal":
        return _login_css_ultra_minimal()
    return _login_css_premium_glass()


def _login_css_premium_glass() -> str:
    """
    Theme login type SpiritStitch - version premium amelioree :
    - Fond degrade anime doux lavande -> cyan
    - Glows decoratifs radiaux
    - Carte glass centree avec liseret brillant
    - Bouton principal degrade violet -> turquoise avec shimmer hover
    """
    return """
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&family=Poppins:wght@500;600;700;800&display=swap');

    /* Cacher la sidebar pour un login plein ecran */
    [data-testid="stSidebar"] { display: none \!important; }

    .main .block-container {
        max-width: 520px \!important;
        min-height: 100vh \!important;
        padding: 0 1.5rem \!important;
        margin: 0 auto \!important;
        display: flex \!important;
        align-items: center \!important;
        justify-content: center \!important;
        background: transparent \!important;
    }

    /* FOND : degrade anime lavande -> cyan */
    .stApp {
        background: linear-gradient(135deg, #E0C3FC 0%, #8EC5FC 50%, #A6E1FA 100%) \!important;
        background-size: 200% 200% \!important;
        animation: gradientShift 18s ease infinite \!important;
        min-height: 100vh;
        position: relative;
        font-family: 'Inter', 'Segoe UI', sans-serif;
    }
    @keyframes gradientShift {
        0% { background-position: 0% 50%; }
        50% { background-position: 100% 50%; }
        100% { background-position: 0% 50%; }
    }

    /* Glows decoratifs */
    .stApp::before {
        content: '';
        position: fixed;
        inset: 0;
        background:
            radial-gradient(circle at 18% 12%, rgba(255, 255, 255, 0.55) 0%, transparent 55%),
            radial-gradient(circle at 82% 88%, rgba(108, 99, 255, 0.28) 0%, transparent 55%),
            radial-gradient(circle at 50% 50%, rgba(0, 201, 167, 0.12) 0%, transparent 60%);
        pointer-events: none;
        z-index: 0;
    }
    .stApp::after {
        content: '';
        position: fixed;
        inset: 0;
        background: rgba(255, 255, 255, 0.04);
        pointer-events: none;
        z-index: 0;
    }

    .login-page-wrapper {
        position: relative;
        z-index: 1;
        width: 100%;
    }

    /* CARTE LOGIN GLASS */
    .login-theme-card {
        background: rgba(255, 255, 255, 0.92) \!important;
        backdrop-filter: blur(28px) saturate(180%);
        -webkit-backdrop-filter: blur(28px) saturate(180%);
        border-radius: 28px \!important;
        box-shadow:
            0 24px 60px rgba(15, 23, 42, 0.22),
            0 0 0 1px rgba(255, 255, 255, 0.6),
            inset 0 1px 0 rgba(255, 255, 255, 0.9) \!important;
        padding: 2.75rem 2.5rem \!important;
        margin: 0 auto;
        max-width: 460px;
        width: 100%;
        animation: cardFadeIn 0.6s cubic-bezier(0.22, 1, 0.36, 1);
    }
    @keyframes cardFadeIn {
        from { opacity: 0; transform: translateY(16px) scale(0.98); }
        to   { opacity: 1; transform: translateY(0) scale(1); }
    }

    /* TITRE */
    .login-theme-title {
        font-family: 'Poppins', 'Inter', sans-serif \!important;
        font-size: 42px \!important;
        font-weight: 800 \!important;
        letter-spacing: -0.02em \!important;
        text-align: center;
        margin-bottom: 0.35rem;
        background: linear-gradient(135deg, #6C63FF 0%, #00C9A7 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        background-clip: text;
    }
    .login-theme-title-tone1, .login-theme-title-tone2 { display: none; }
    .login-theme-subtitle {
        color: #6B7280 \!important;
        font-size: 0.95rem;
        text-align: center;
        margin-bottom: 1.5rem;
    }
    .login-theme-card .login-theme-label {
        text-align: center;
        margin-bottom: 1.1rem;
        color: #374151 \!important;
        font-size: 1rem \!important;
        font-weight: 600 \!important;
        letter-spacing: 0.01em;
    }
    .login-theme-card h3 { display: none; }

    /* INPUTS */
    .login-theme-card [data-testid="stForm"] { margin-top: 0.75rem; }
    .login-theme-card [data-testid="stTextInput"] > div,
    .login-theme-card [data-testid="stPasswordInput"] > div { background: transparent \!important; }

    .login-theme-card .stTextInput > div > div,
    .login-theme-card .stPasswordInput > div > div {
        background: #ffffff \!important;
        border: 1.5px solid #E5E7EB \!important;
        border-radius: 14px \!important;
        padding: 14px \!important;
        min-height: 50px \!important;
        transition: border-color 0.2s ease, box-shadow 0.2s ease, background 0.2s ease;
        box-shadow: 0 1px 2px rgba(0, 0, 0, 0.02);
    }
    .login-theme-card .stTextInput > div > div:hover,
    .login-theme-card .stPasswordInput > div > div:hover {
        border-color: #C7C2FF \!important;
    }
    .login-theme-card .stTextInput > div > div:focus-within,
    .login-theme-card .stPasswordInput > div > div:focus-within {
        border-color: #6C63FF \!important;
        box-shadow: 0 0 0 4px rgba(108, 99, 255, 0.18) \!important;
        background: #FEFEFF \!important;
    }
    .login-theme-card .stTextInput input,
    .login-theme-card .stPasswordInput input {
        background: #ffffff \!important;
        border: none \!important;
        padding: 14px \!important;
        font-size: 1rem \!important;
        color: #111 \!important;
    }
    .login-theme-card .stTextInput input::placeholder,
    .login-theme-card .stPasswordInput input::placeholder { color: #9CA3AF \!important; }
    .login-theme-card [data-testid="stForm"] label,
    .login-theme-card [data-testid="stForm"] label p {
        font-weight: 500 \!important;
        color: #374151 \!important;
        font-size: 0.9375rem \!important;
    }
    .login-theme-card [data-testid="stTextInput"],
    .login-theme-card [data-testid="stPasswordInput"] { margin-bottom: 1rem \!important; }

    /* BOUTON PRINCIPAL */
    .login-theme-card .stButton > button,
    .login-theme-card button[kind="primary"] {
        width: 100% \!important;
        padding: 16px 1.5rem \!important;
        min-height: 54px \!important;
        border-radius: 14px \!important;
        background: linear-gradient(135deg, #6C63FF 0%, #00C9A7 100%) \!important;
        background-size: 180% 180% \!important;
        color: #fff \!important;
        border: none \!important;
        font-weight: 700 \!important;
        font-size: 1.0625rem \!important;
        letter-spacing: 0.01em;
        box-shadow: 0 10px 24px rgba(108, 99, 255, 0.28) \!important;
        transition: transform 0.18s ease, box-shadow 0.25s ease, background-position 0.4s ease;
        position: relative;
        overflow: hidden;
    }
    .login-theme-card .stButton > button:hover,
    .login-theme-card button[kind="primary"]:hover {
        transform: translateY(-2px) scale(1.01);
        background-position: 100% 0;
        box-shadow: 0 18px 36px rgba(108, 99, 255, 0.42) \!important;
    }
    .login-theme-card .stButton > button:active,
    .login-theme-card button[kind="primary"]:active {
        transform: translateY(0) scale(0.99);
        box-shadow: 0 8px 18px rgba(108, 99, 255, 0.25) \!important;
    }

    /* Liens & aide */
    .login-theme-forgot { text-align: center; margin-top: 1rem; }
    .login-theme-forgot a {
        color: #6C63FF;
        font-size: 0.875rem;
        text-decoration: none;
        font-weight: 500;
        transition: color 0.2s ease;
    }
    .login-theme-forgot a:hover { color: #00C9A7; }
    .login-theme-support {
        color: #6B7280;
        font-size: 0.8rem;
        text-align: center;
        margin-top: 1.25rem;
        padding-top: 1rem;
        border-top: 1px solid #E5E7EB;
    }

    /* Alertes dans le formulaire */
    [data-testid="stForm"] .stAlert {
        margin-top: 0.5rem;
        border-radius: 12px \!important;
        border-left: 4px solid #6C63FF \!important;
    }

    /* Responsive mobile */
    @media (max-width: 768px) {
        .login-page-wrapper [data-testid="column"]:first-child,
        .login-page-wrapper [data-testid="column"]:last-child {
            min-height: auto;
            padding: 1.5rem 1rem \!important;
        }
        .login-theme-card { max-width: 100%; padding: 2rem \!important; }
        .login-theme-title { font-size: 34px \!important; }
    }

    #MainMenu { visibility: hidden; }
    header { visibility: hidden; }
    footer:not(.app-footer) { visibility: hidden; }
    .app-footer { visibility: visible \!important; }
    </style>
    """


def _login_css_ultra_minimal() -> str:
    """Version Ultra Minimal (fintech)."""
    return """
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');
    .stApp {
        background: #F8F9FA \!important;
        min-height: 100vh;
        font-family: 'Inter', 'Segoe UI', sans-serif;
    }
    .main .block-container {
        background: transparent \!important;
        padding-top: 1.5rem;
        padding-bottom: 2rem;
        max-width: 680px;
    }
    .login-theme-card {
        background: #FFFFFF \!important;
        border-radius: 20px;
        box-shadow: 0 8px 32px rgba(0, 0, 0, 0.08), 0 1px 3px rgba(0,0,0,0.04);
        padding: 2.75rem 2.5rem;
        margin: 0 auto;
        max-width: 560px;
        min-width: 420px;
        border: 1px solid rgba(229, 231, 235, 0.6);
    }
    .login-theme-title {
        font-weight: 800; font-size: 2.1rem; letter-spacing: -0.01em;
        text-align: center; margin-bottom: 0.35rem;
        background: linear-gradient(90deg, #8E7AB5 0%, #36CFC9 100%);
        -webkit-background-clip: text; -webkit-text-fill-color: transparent;
        background-clip: text;
    }
    .login-theme-subtitle { color: #6B7280; font-size: 0.9rem; text-align: center; margin-bottom: 1.5rem; }
    .login-theme-card [data-testid="stForm"] { margin-top: 0.75rem; }
    .login-theme-card .stTextInput > div > div,
    .login-theme-card .stPasswordInput > div > div {
        background: #fff \!important;
        border: 1px solid #E5E7EB \!important;
        border-radius: 12px \!important;
        box-shadow: 0 1px 2px rgba(0,0,0,0.04) \!important;
        transition: border-color 0.2s ease, box-shadow 0.2s ease;
        min-height: 52px \!important;
    }
    .login-theme-card .stTextInput > div > div:focus-within,
    .login-theme-card .stPasswordInput > div > div:focus-within {
        border-color: #8E7AB5 \!important;
        box-shadow: 0 0 0 3px rgba(142, 122, 181, 0.2) \!important;
    }
    .login-theme-card .stTextInput input,
    .login-theme-card .stPasswordInput input {
        background: transparent \!important; border: none \!important;
        padding: 1rem 1.2rem \!important; font-size: 1.0625rem \!important;
        min-height: 52px \!important; line-height: 1.4 \!important; color: #1f2937 \!important;
    }
    .login-theme-card .stButton > button, .login-theme-card button[kind="primary"] {
        background: linear-gradient(90deg, #8E7AB5 0%, #36CFC9 100%) \!important;
        color: #FFFFFF \!important; border: none \!important;
        border-radius: 12px \!important;
        box-shadow: 0 6px 18px rgba(142, 122, 181, 0.3);
        font-weight: 600 \!important; font-size: 1rem \!important;
        width: 100%; padding: 0.9rem 1.25rem;
        transition: transform 0.15s ease, box-shadow 0.2s ease;
    }
    .login-theme-card .stButton > button:hover {
        transform: translateY(-1px);
        box-shadow: 0 10px 24px rgba(142, 122, 181, 0.42);
    }
    .login-theme-forgot { text-align: center; margin-top: 0.75rem; }
    .login-theme-forgot a { color: #36CFC9; font-size: 0.875rem; text-decoration: none; }
    .login-theme-support { color: #6B7280; font-size: 0.8rem; text-align: center; margin-top: 1.25rem; line-height: 1.4; padding-top: 1rem; border-top: 1px solid #EEE; }
    #MainMenu { visibility: hidden; } footer { visibility: hidden; } header { visibility: hidden; }
    </style>
    """


def get_sidebar_bg_css() -> str:
    """Retourne le CSS de fond de la sidebar selon le theme actif."""
    if THEME_ACTIVE == "ultra_minimal":
        return "background: #FFFFFF \!important; border-right: 1px solid #E5E7EB \!important;"
    return """
    background: linear-gradient(180deg, #ECE6F8 0%, #DFF7F4 100%) \!important;
    border-right: 1px solid rgba(0, 0, 0, 0.06) \!important;
    """


def get_app_premium_css() -> str:
    """CSS global premium optionnel pour la zone principale apres connexion.

    A injecter via st.markdown(get_app_premium_css(), unsafe_allow_html=True).
    Non utilise par defaut : l'app.py existant a son propre CSS.
    """
    return f"""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&family=Poppins:wght@500;600;700;800&display=swap');

    :root {{
        --brand-primary: {BRAND_PRIMARY};
        --brand-accent: {BRAND_ACCENT};
        --brand-bg: #F7F8FC;
        --brand-surface: {BRAND_SURFACE};
        --brand-surface-soft: {BRAND_SURFACE_SOFT};
        --brand-text: {BRAND_TEXT};
        --brand-text-soft: {BRAND_TEXT_SOFT};
        --brand-border: {BRAND_BORDER};
        --brand-gradient: {get_brand_gradient()};
        --shadow-xs: 0 1px 2px rgba(15, 23, 42, 0.04);
        --shadow-sm: 0 4px 10px rgba(15, 23, 42, 0.06);
        --shadow-md: 0 12px 24px rgba(15, 23, 42, 0.08);
        --shadow-lg: 0 24px 48px rgba(15, 23, 42, 0.12);
        --radius-sm: 10px;
        --radius-md: 14px;
        --radius-lg: 20px;
    }}

    html, body, .stApp, [data-testid="stAppViewContainer"] {{
        font-family: 'Inter', 'Segoe UI', sans-serif \!important;
        color: var(--brand-text) \!important;
    }}

    h1, h2, h3, h4, h5, h6 {{
        font-family: 'Poppins', 'Inter', sans-serif \!important;
        color: var(--brand-text) \!important;
        letter-spacing: -0.01em;
    }}

    /* Titres de sections : petite barre gauche couleur marque */
    .main h2, .main h3 {{
        position: relative;
        padding-left: 0.9rem;
    }}
    .main h2::before, .main h3::before {{
        content: '';
        position: absolute;
        left: 0; top: 12%;
        height: 76%;
        width: 4px;
        border-radius: 4px;
        background: var(--brand-gradient);
    }}

    /* Boutons premium */
    .stButton > button, div[data-testid="stButton"] > button {{
        background: var(--brand-gradient) \!important;
        color: #fff \!important;
        border: none \!important;
        border-radius: var(--radius-md) \!important;
        padding: 0.7rem 1.4rem \!important;
        font-weight: 600 \!important;
        letter-spacing: 0.01em;
        box-shadow: var(--shadow-sm) \!important;
        transition: transform 0.15s ease, box-shadow 0.25s ease \!important;
    }}
    .stButton > button:hover, div[data-testid="stButton"] > button:hover {{
        transform: translateY(-2px);
        box-shadow: var(--shadow-md) \!important;
    }}
    .stButton > button:active {{
        transform: translateY(0);
    }}

    /* Metriques : carte elegante */
    [data-testid="stMetric"] {{
        background: var(--brand-surface);
        border: 1px solid var(--brand-border);
        border-radius: var(--radius-md);
        padding: 1.1rem 1.2rem;
        box-shadow: var(--shadow-xs);
        transition: box-shadow 0.25s ease, transform 0.15s ease;
    }}
    [data-testid="stMetric"]:hover {{
        box-shadow: var(--shadow-md);
        transform: translateY(-2px);
    }}
    [data-testid="stMetricValue"] {{
        font-family: 'Poppins', sans-serif \!important;
        font-size: 2rem \!important;
        font-weight: 700 \!important;
        color: var(--brand-primary) \!important;
    }}
    [data-testid="stMetricLabel"] {{
        font-size: 0.85rem \!important;
        color: var(--brand-text-soft) \!important;
        font-weight: 500 \!important;
        text-transform: uppercase;
        letter-spacing: 0.06em;
    }}

    /* Tableaux */
    .stDataFrame, [data-testid="stTable"] {{
        border-radius: var(--radius-md);
        overflow: hidden;
        box-shadow: var(--shadow-sm);
        background: var(--brand-surface);
    }}
    .stDataFrame thead, [data-testid="stTable"] thead {{
        background: var(--brand-surface-soft) \!important;
    }}
    .stDataFrame th, [data-testid="stTable"] th {{
        color: var(--brand-text) \!important;
        font-weight: 600 \!important;
        font-size: 0.85rem \!important;
        letter-spacing: 0.03em;
    }}

    /* Inputs */
    .stTextInput > div > div,
    .stNumberInput > div > div,
    .stDateInput > div > div,
    .stTextArea > div > div {{
        border-radius: var(--radius-sm) \!important;
        border: 1.5px solid var(--brand-border) \!important;
        transition: border-color 0.2s ease, box-shadow 0.2s ease \!important;
    }}
    .stTextInput > div > div:focus-within,
    .stNumberInput > div > div:focus-within,
    .stDateInput > div > div:focus-within,
    .stTextArea > div > div:focus-within {{
        border-color: var(--brand-primary) \!important;
        box-shadow: 0 0 0 3px rgba(108, 99, 255, 0.15) \!important;
    }}

    /* Tabs */
    .stTabs [data-baseweb="tab-list"] {{
        gap: 0.4rem;
        background: var(--brand-surface-soft);
        padding: 0.35rem;
        border-radius: var(--radius-md);
    }}
    .stTabs [data-baseweb="tab"] {{
        background: transparent \!important;
        border-radius: var(--radius-sm) \!important;
        padding: 0.6rem 1.2rem \!important;
        color: var(--brand-text) \!important;
        font-weight: 500 \!important;
        transition: all 0.2s ease;
    }}
    .stTabs [data-baseweb="tab"]:hover {{
        background: rgba(108, 99, 255, 0.08) \!important;
    }}
    .stTabs [aria-selected="true"] {{
        background: var(--brand-gradient) \!important;
        color: #fff \!important;
        box-shadow: var(--shadow-sm) \!important;
    }}

    /* Alertes */
    .stAlert {{
        border-radius: var(--radius-md) \!important;
        border-left-width: 4px \!important;
        box-shadow: var(--shadow-xs) \!important;
    }}

    /* Expander */
    [data-testid="stExpander"] {{
        border-radius: var(--radius-md) \!important;
        border: 1px solid var(--brand-border) \!important;
        box-shadow: var(--shadow-xs) \!important;
    }}
    [data-testid="stExpander"] summary {{
        font-weight: 600 \!important;
        color: var(--brand-text) \!important;
    }}

    /* Liens */
    a, a:visited {{ color: var(--brand-primary); }}
    a:hover {{ color: var(--brand-accent); }}

    /* Separators */
    hr {{
        border: none;
        border-top: 1px solid var(--brand-border);
        margin: 1.5rem 0;
    }}

    /* Scrollbar moderne */
    ::-webkit-scrollbar {{ width: 10px; height: 10px; }}
    ::-webkit-scrollbar-track {{ background: transparent; }}
    ::-webkit-scrollbar-thumb {{
        background: rgba(108, 99, 255, 0.25);
        border-radius: 6px;
    }}
    ::-webkit-scrollbar-thumb:hover {{
        background: rgba(108, 99, 255, 0.45);
    }}
    </style>
    """
