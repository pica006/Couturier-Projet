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
    - LOGIN_SUPPORT_LINE1 / LOGIN_SUPPORT_CONTACT_HTML
"""

import os

# Choix du theme : variable d'environnement THEME ou defaut premium_glass
THEME_ACTIVE = os.getenv("THEME", "premium_glass").strip().lower()
if THEME_ACTIVE not in ("premium_glass", "ultra_minimal"):
    THEME_ACTIVE = "premium_glass"

# Libelles affiches sur la page de connexion (maquette SpiritStitch)
LOGIN_DISPLAY_TITLE_1 = "Spirit"
LOGIN_DISPLAY_TITLE_2 = "Stitch"
LOGIN_DISPLAY_SUBTITLE = "— Votre espace couture —"
LOGIN_SUPPORT_LINE1 = "Besoin d'aide ? Contactez l'administrateur de votre atelier."
LOGIN_SUPPORT_CONTACT_HTML = (
    "<strong>An's Learning</strong> — Douala, Kotto | +237 698 19 25 07"
)

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
    Page de connexion alignee sur la maquette SpiritStitch :
    fond tres doux (lavande en bordure, halo clair au centre), carte blanche nette,
    titre en degrade horizontal violet -> turquoise, formulaire epure.
    """
    return """
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&family=Poppins:wght@500;600;700;800&display=swap');

    [data-testid="stSidebar"] { display: none \!important; }

    .main .block-container {
        max-width: 480px \!important;
        min-height: 100vh \!important;
        padding: 1.5rem 1.25rem 2rem \!important;
        margin: 0 auto \!important;
        display: flex \!important;
        align-items: center \!important;
        justify-content: center \!important;
        background: transparent \!important;
    }

    /* Fond : lavande discret sur les bords, centre quasi blanc bleute (maquette) */
    .stApp {
        background:
            radial-gradient(ellipse 85% 70% at 50% 42%, #f8fffe 0%, #eef9ff 42%, #ebe8ff 100%) \!important;
        min-height: 100vh;
        position: relative;
        font-family: 'Inter', 'Segoe UI', sans-serif;
    }

    .stApp::before {
        content: '';
        position: fixed;
        inset: 0;
        background:
            radial-gradient(circle at 0% 0%, rgba(224, 219, 255, 0.55) 0%, transparent 45%),
            radial-gradient(circle at 100% 100%, rgba(212, 250, 243, 0.5) 0%, transparent 48%);
        pointer-events: none;
        z-index: 0;
    }

    .login-page-wrapper {
        position: relative;
        z-index: 1;
        width: 100%;
    }

    /* Carte blanche centrale */
    .login-theme-card {
        background: #FFFFFF \!important;
        border-radius: 26px \!important;
        box-shadow:
            0 20px 50px rgba(108, 99, 255, 0.12),
            0 8px 24px rgba(15, 23, 42, 0.06) \!important;
        border: 1px solid rgba(229, 231, 235, 0.85) \!important;
        padding: 2.5rem 2.25rem 2.35rem \!important;
        margin: 0 auto;
        max-width: 420px;
        width: 100%;
    }

    .login-theme-title {
        font-family: 'Poppins', 'Inter', sans-serif \!important;
        font-size: 2rem \!important;
        font-weight: 800 \!important;
        letter-spacing: -0.02em \!important;
        line-height: 1.15 \!important;
        text-align: center;
        margin: 0 0 0.5rem 0;
        background: linear-gradient(90deg, #6C63FF 0%, #00C9A7 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        background-clip: text;
    }
    .login-theme-title-tone1, .login-theme-title-tone2 { display: none; }

    .login-theme-subtitle {
        color: #9CA3AF \!important;
        font-size: 0.875rem \!important;
        font-weight: 500 \!important;
        text-align: center;
        margin: 0 0 1.75rem 0;
        letter-spacing: 0.02em;
    }

    .login-theme-card h3 { display: none; }

    .login-theme-card [data-testid="stForm"] { margin-top: 0; }
    .login-theme-card [data-testid="stTextInput"] > div,
    .login-theme-card [data-testid="stPasswordInput"] > div { background: transparent \!important; }

    .login-theme-card .stTextInput > div > div,
    .login-theme-card .stPasswordInput > div > div {
        background: #ffffff \!important;
        border: 1px solid #E5E7EB \!important;
        border-radius: 10px \!important;
        padding: 2px 4px \!important;
        min-height: 48px \!important;
        transition: border-color 0.2s ease, box-shadow 0.2s ease;
    }
    .login-theme-card .stTextInput > div > div:focus-within,
    .login-theme-card .stPasswordInput > div > div:focus-within {
        border-color: #6C63FF \!important;
        box-shadow: 0 0 0 3px rgba(108, 99, 255, 0.13) \!important;
    }
    .login-theme-card .stTextInput input,
    .login-theme-card .stPasswordInput input {
        background: transparent \!important;
        border: none \!important;
        padding: 0.65rem 0.85rem \!important;
        font-size: 0.9375rem \!important;
        color: #111827 \!important;
    }
    .login-theme-card .stTextInput input::placeholder,
    .login-theme-card .stPasswordInput input::placeholder { color: #9CA3AF \!important; }

    .login-theme-card [data-testid="stForm"] label,
    .login-theme-card [data-testid="stForm"] label p {
        font-weight: 700 \!important;
        color: #374151 \!important;
        font-size: 0.8125rem \!important;
    }
    .login-theme-card [data-testid="stTextInput"],
    .login-theme-card [data-testid="stPasswordInput"] { margin-bottom: 1.1rem \!important; }

    .login-theme-card .stButton,
    .login-theme-card div[data-testid="stButton"] { width: 100% \!important; }
    .login-theme-card .stButton > button,
    .login-theme-card button[kind="primary"],
    .login-theme-card div[data-testid="stButton"] > button {
        width: 100% \!important;
        padding: 0.85rem 1.25rem \!important;
        min-height: 48px \!important;
        border-radius: 10px \!important;
        background: linear-gradient(90deg, #6C63FF 0%, #00C9A7 100%) \!important;
        color: #fff \!important;
        border: none \!important;
        font-weight: 700 \!important;
        font-size: 1rem \!important;
        font-family: 'Inter', 'Segoe UI', sans-serif \!important;
        box-shadow: 0 8px 20px rgba(108, 99, 255, 0.22) \!important;
        transition: transform 0.15s ease, box-shadow 0.2s ease;
    }
    .login-theme-card .stButton > button:hover,
    .login-theme-card button[kind="primary"]:hover,
    .login-theme-card div[data-testid="stButton"] > button:hover {
        transform: translateY(-1px);
        box-shadow: 0 12px 28px rgba(108, 99, 255, 0.28) \!important;
    }

    .login-theme-forgot {
        text-align: center;
        margin-top: 1.1rem;
    }
    .login-theme-forgot a {
        color: #6366F1;
        font-size: 0.875rem;
        text-decoration: none;
        font-weight: 500;
    }
    .login-theme-forgot a:hover { color: #6C63FF; text-decoration: underline; }

    .login-theme-support {
        margin-top: 1.5rem;
        padding-top: 1.25rem;
        border-top: 1px solid #E5E7EB;
        text-align: center;
    }
    .login-theme-support-line1 {
        color: #6B7280 \!important;
        font-size: 0.8rem \!important;
        line-height: 1.45 \!important;
        margin: 0 0 0.5rem 0;
    }
    .login-theme-support-contact {
        color: #4B5563 \!important;
        font-size: 0.78rem \!important;
        line-height: 1.45 \!important;
        margin: 0;
    }
    .login-theme-support-contact strong {
        color: #111827 \!important;
        font-weight: 700 \!important;
    }

    [data-testid="stForm"] .stAlert {
        margin-top: 0.5rem;
        border-radius: 10px \!important;
        border-left: 4px solid #6C63FF \!important;
    }

    @media (max-width: 768px) {
        .login-theme-card { padding: 2rem 1.5rem \!important; max-width: 100%; }
        .login-theme-title { font-size: 1.75rem \!important; }
    }

    #MainMenu { visibility: hidden; }
    header { visibility: hidden; }
    footer:not(.app-footer) { visibility: hidden; }
    .app-footer { visibility: visible \!important; }
    </style>
    """


def _login_css_ultra_minimal() -> str:
    """Meme structure visuelle que la maquette (palette #6C63FF / #00C9A7), variante epuree."""
    return """
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&family=Poppins:wght@600;700;800&display=swap');
    [data-testid="stSidebar"] { display: none \!important; }
    .stApp {
        background: radial-gradient(ellipse 85% 70% at 50% 42%, #f8fffe 0%, #eef9ff 42%, #ebe8ff 100%) \!important;
        min-height: 100vh;
        font-family: 'Inter', 'Segoe UI', sans-serif;
    }
    .main .block-container {
        background: transparent \!important;
        max-width: 480px \!important;
        min-height: 100vh \!important;
        padding: 1.5rem 1.25rem \!important;
        margin: 0 auto \!important;
        display: flex \!important;
        align-items: center \!important;
        justify-content: center \!important;
    }
    .login-theme-card {
        background: #FFFFFF \!important;
        border-radius: 26px \!important;
        box-shadow: 0 20px 50px rgba(108, 99, 255, 0.1), 0 4px 16px rgba(0,0,0,0.05);
        padding: 2.5rem 2.25rem \!important;
        margin: 0 auto;
        max-width: 420px;
        width: 100%;
        border: 1px solid #E5E7EB;
    }
    .login-theme-title {
        font-family: 'Poppins', 'Inter', sans-serif \!important;
        font-weight: 800; font-size: 2rem; letter-spacing: -0.02em;
        text-align: center; margin: 0 0 0.5rem 0;
        background: linear-gradient(90deg, #6C63FF 0%, #00C9A7 100%);
        -webkit-background-clip: text; -webkit-text-fill-color: transparent;
        background-clip: text;
    }
    .login-theme-subtitle { color: #9CA3AF; font-size: 0.875rem; text-align: center; margin: 0 0 1.75rem 0; }
    .login-theme-card .stTextInput > div > div,
    .login-theme-card .stPasswordInput > div > div {
        background: #fff \!important;
        border: 1px solid #E5E7EB \!important;
        border-radius: 10px \!important;
        min-height: 48px \!important;
    }
    .login-theme-card .stTextInput > div > div:focus-within,
    .login-theme-card .stPasswordInput > div > div:focus-within {
        border-color: #6C63FF \!important;
        box-shadow: 0 0 0 3px rgba(108, 99, 255, 0.13) \!important;
    }
    .login-theme-card [data-testid="stForm"] label p { font-weight: 700 \!important; font-size: 0.8125rem \!important; color: #374151 \!important; }
    .login-theme-card .stButton > button, .login-theme-card button[kind="primary"],
    .login-theme-card div[data-testid="stButton"] > button {
        background: linear-gradient(90deg, #6C63FF 0%, #00C9A7 100%) \!important;
        color: #FFFFFF \!important; border: none \!important;
        border-radius: 10px \!important;
        font-weight: 700 \!important; width: 100% \!important;
        box-shadow: 0 8px 20px rgba(108, 99, 255, 0.2);
    }
    .login-theme-forgot { text-align: center; margin-top: 1rem; }
    .login-theme-forgot a { color: #6366F1; font-size: 0.875rem; text-decoration: none; }
    .login-theme-support { margin-top: 1.5rem; padding-top: 1.25rem; border-top: 1px solid #E5E7EB; text-align: center; }
    .login-theme-support-line1 { color: #6B7280; font-size: 0.8rem; margin: 0 0 0.5rem 0; }
    .login-theme-support-contact { color: #4B5563; font-size: 0.78rem; margin: 0; }
    #MainMenu { visibility: hidden; } footer:not(.app-footer) { visibility: hidden; } header { visibility: hidden; }
    .app-footer { visibility: visible \!important; }
    </style>
    """


def get_sidebar_bg_css() -> str:
    """Retourne le CSS de fond de la sidebar selon le theme actif."""
    if THEME_ACTIVE == "ultra_minimal":
        return "background: #FFFFFF \!important; border-right: 1px solid #E5E7EB \!important;"
    return """
    background: linear-gradient(180deg, #ede9fe 0%, #d1faf3 100%) \!important;
    border-right: 1px solid rgba(108, 99, 255, 0.10) \!important;
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
