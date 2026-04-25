"""
Application Streamlit principale - Gestion Couturier
Architecture MVC
"""
import os
import base64
import logging
import streamlit as st
try:
    from dotenv import load_dotenv
except Exception:
    load_dotenv = None

# Charger .env AVANT tout import de config (sinon DB_PASSWORD etc. restent vides).
# Ne jamais faire echouer le demarrage si python-dotenv est absent.
if load_dotenv is not None:
    try:
        load_dotenv()
    except Exception:
        pass

from utils.role_utils import est_admin
from utils.bottom_nav import render_app_footer
from utils.permissions import est_super_admin
from config import APP_CONFIG, PAGE_BACKGROUND_IMAGES, VISUAL_SAFE_MODE
from services.session_service import initialize_session_state, sanitize_session_state, logout_user
from utils.theme import get_sidebar_bg_css as theme_sidebar_bg_css
from utils.layout_css import MAIN_BLOCK_CONTAINER_CSS

logger = logging.getLogger(__name__)


# Configuration de la page
# Note: APP_CONFIG sera importé après, donc on utilise une valeur par défaut ici
st.set_page_config(
    page_title="Gestion Couturier",
    page_icon="👔",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Première initialisation de la session juste après set_page_config, avant tout autre st.* lourd
# (CSS, etc.). Sinon Streamlit peut lever « Tried to use SessionInfo before it was initialized »
# (en français : erreur sur SessionInfo / format de message selon le client).
initialize_session_state()
sanitize_session_state()

# CSS personnalisé - Palette: Violet clair | Bleu turquoise | Beige (60% dominante)
# NOTE: L'erreur 'removeChild' est un bug connu de Streamlit
# Elle est bénigne et n'affecte pas le fonctionnement de l'application
# Aucun JavaScript personnalisé n'est utilisé pour éviter d'aggraver le problème

SIDEBAR_BG_PLAIN = "background: #FAFAFA !important;"
# Sidebar après connexion : dark navy premium (Linear / Stripe)
SIDEBAR_BG_DARK = "background: #0F172A !important;"


@st.cache_data(show_spinner=False)
def _get_sidebar_bg_css_with_image() -> str:
    """Charge l'image sidebar a la demande (pas au boot)."""
    try:
        project_root = os.path.dirname(__file__)
        nav_path = os.path.join(project_root, "assets", "nav.png")
        if not os.path.exists(nav_path):
            return SIDEBAR_BG_PLAIN
        with open(nav_path, "rb") as f:
            nav_b64 = base64.b64encode(f.read()).decode("utf-8")
        data_uri = f"data:image/png;base64,{nav_b64}"
        return f"""
        background-image: url('{data_uri}') !important;
        background-size: cover !important;
        background-position: center !important;
        background-repeat: no-repeat !important;
        """
    except Exception:
        return SIDEBAR_BG_PLAIN

def _safe_visual_css() -> str:
    """
    Mode visuel safe: style minimal, stable et non intrusif.
    """
    return f"""
    <style>
    .stApp, .main .block-container {{
        background: #FEFEFE !important;
        color: #2C2C2C !important;
        font-family: 'Inter', 'Segoe UI', sans-serif;
    }}

    .main .block-container {{
        padding-top: 1.5rem;
        padding-bottom: 1.5rem;
    }}
    {MAIN_BLOCK_CONTAINER_CSS}

    [data-testid="stSidebar"] {{
        background: #FAFAFA !important;
        border-right: 1px solid #EAEAEA;
    }}

    .stButton > button, button[kind="primary"] {{
        background: #B19CD9 !important;
        color: #FFFFFF !important;
        border: 1px solid #B19CD9 !important;
        border-radius: 10px !important;
        box-shadow: none !important;
        transition: none !important;
        transform: none !important;
    }}

    .stButton > button:hover, button[kind="primary"]:hover {{
        background: #9F87D3 !important;
        color: #FFFFFF !important;
        opacity: 1 !important;
    }}

    a, a:visited, a:hover {{
        color: #40E0D0 !important;
    }}
    </style>
    """


# IMPORTANT: ne pas lire/écrire st.session_state au chargement du module en dehors du bootstrap
# juste au-dessus (initialize + sanitize). Le thème riche est désactivé ici.
_apply_rich_theme = False

if VISUAL_SAFE_MODE:
    st.markdown(_safe_visual_css(), unsafe_allow_html=True)
elif _apply_rich_theme:
    st.markdown(
        """
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&family=Poppins:wght@400;500;600;700&display=swap');
    
    /* ========================================================================
       PALETTE DE COULEURS - DESIGN PROFESSIONNEL 2025
       ======================================================================== */
    :root {
        /* Couleurs principales */
        --violet-clair: #B19CD9;
        --bleu-turquoise: #40E0D0;
        --beige: #FEFEFE;
        --beige-fonce: #FAFAFA;
        --beige-tres-fonce: #F5F5F5;
        
        /* Couleurs complémentaires */
        --blanc: #FFFFFF;
        --noir: #2C2C2C;
        --gris-clair: #F8F8F8;
        --gris-moyen: #E0E0E0;
        --gris-fonce: #6C6C6C;
        
        /* Dégradés */
        --gradient-primary: linear-gradient(135deg, #B19CD9 0%, #40E0D0 100%);
        --gradient-soft: linear-gradient(135deg, #F5F5DC 0%, #E8E8D3 100%);
        --gradient-accent: linear-gradient(135deg, #40E0D0 0%, #B19CD9 100%);
        
        /* Ombres */
        --shadow-sm: 0 2px 4px rgba(0, 0, 0, 0.05);
        --shadow-md: 0 4px 8px rgba(0, 0, 0, 0.1);
        --shadow-lg: 0 8px 16px rgba(0, 0, 0, 0.15);
        
        /* Espacements */
        --radius-sm: 8px;
        --radius-md: 12px;
        --radius-lg: 16px;
    }
    
    /* ========================================================================
       FOND GLOBAL - BEIGE DOMINANT (60%)
       ======================================================================== */
    .stApp {
        background: #FEFEFE !important;
        font-family: 'Inter', 'Segoe UI', sans-serif;
    }
    
    .main .block-container {
        background: #FEFEFE !important;
        padding-top: 2rem;
        padding-bottom: 2rem;
    }
"""
        + MAIN_BLOCK_CONTAINER_CSS
        + """
    /* ========================================================================
       HEADERS DE PAGE - GRADIENT VIOLET-BLEU
       (Styles appliqués en inline pour éviter les conflits DOM)
       ======================================================================== */
    
    /* ========================================================================
       SIDEBAR - BEIGE FONCÉ (valeur par défaut, surchargée ensuite)
       ======================================================================== */
    [data-testid="stSidebar"] {
        border-right: 2px solid #F5F5F5;
    }
    
    /* Styles pour le header de la sidebar - Supprimés car utilisés en inline uniquement */
    
    /* ========================================================================
       BOUTONS - GRADIENT VIOLET-BLEU (PAS DE NOIR !)
       ======================================================================== */
    .stButton > button {
        background: linear-gradient(135deg, #B19CD9 0%, #40E0D0 100%) !important;
        color: #FFFFFF !important;
        border: none !important;
        border-radius: var(--radius-md) !important;
        padding: 0.75rem 1.5rem !important;
        font-weight: 500 !important;
        transition: all 0.3s ease !important;
        box-shadow: var(--shadow-sm) !important;
    }
    
    .stButton > button:hover {
        background: linear-gradient(135deg, #B19CD9 0%, #40E0D0 100%) !important;
        color: #FFFFFF !important;
        transform: translateY(-2px);
        box-shadow: var(--shadow-md) !important;
        opacity: 0.9;
    }
    
    .stButton > button:active,
    .stButton > button:focus {
        background: linear-gradient(135deg, #B19CD9 0%, #40E0D0 100%) !important;
        color: #FFFFFF !important;
        border: none !important;
        outline: none !important;
    }
    
    /* Boutons primaires - toujours violet-bleu (FORCER pour éviter le rouge) */
    button[kind="primary"],
    button[data-baseweb="button"][kind="primary"],
    button[data-baseweb="button"][data-testid="baseButton-primary"],
    .stButton > button[kind="primary"],
    div[data-testid="stButton"] > button[kind="primary"],
    button.st-emotion-cache-1[data-baseweb="button"][kind="primary"] {
        background: linear-gradient(135deg, #40E0D0 0%, #B19CD9 100%) !important;
        background-color: transparent !important;
        color: #FFFFFF !important;
        border: none !important;
    }
    
    button[kind="primary"]:hover,
    button[kind="primary"]:active,
    button[kind="primary"]:focus,
    button[data-baseweb="button"][kind="primary"]:hover,
    button[data-baseweb="button"][kind="primary"]:active,
    button[data-baseweb="button"][kind="primary"]:focus {
        background: linear-gradient(135deg, #40E0D0 0%, #B19CD9 100%) !important;
        background-color: transparent !important;
        color: #FFFFFF !important;
    }
    
    /* Empêcher Streamlit de mettre du rouge ou du noir - TOUS les boutons */
    button[data-baseweb="button"],
    button[data-testid="baseButton"],
    .stButton > button,
    div[data-testid="stButton"] > button {
        background: linear-gradient(135deg, #B19CD9 0%, #40E0D0 100%) !important;
        background-color: transparent !important;
        color: #FFFFFF !important;
    }
    
    button[data-baseweb="button"]:hover,
    button[data-baseweb="button"]:active,
    button[data-baseweb="button"]:focus,
    button[data-testid="baseButton"]:hover,
    button[data-testid="baseButton"]:active,
    button[data-testid="baseButton"]:focus {
        background: linear-gradient(135deg, #B19CD9 0%, #40E0D0 100%) !important;
        background-color: transparent !important;
        color: #FFFFFF !important;
    }
    
    /* Forcer le style sur les boutons de formulaire aussi */
    form button[data-baseweb="button"],
    form button[kind="primary"],
    form .stButton > button {
        background: linear-gradient(135deg, #40E0D0 0%, #B19CD9 100%) !important;
        background-color: transparent !important;
        color: #FFFFFF !important;
        border: none !important;
    }
    
    form button[data-baseweb="button"]:hover,
    form button[kind="primary"]:hover {
        background: linear-gradient(135deg, #40E0D0 0%, #B19CD9 100%) !important;
        background-color: transparent !important;
        color: #FFFFFF !important;
    }
    
    /* ========================================================================
       FORCER LE DÉGRADÉ SUR TOUS LES BOUTONS (même les rouges de Streamlit)
       ======================================================================== */
    /* Cibler spécifiquement les boutons qui pourraient être rouges */
    button[data-baseweb="button"][style*="background"],
    button[data-baseweb="button"][style*="rgb"],
    button[data-baseweb="button"][style*="red"],
    button[data-baseweb="button"][style*="#ff"],
    button[data-baseweb="button"][style*="#FF"] {
        background: linear-gradient(135deg, #B19CD9 0%, #40E0D0 100%) !important;
        background-color: transparent !important;
        background-image: linear-gradient(135deg, #B19CD9 0%, #40E0D0 100%) !important;
    }
    
    /* Forcer sur les boutons primaires même avec styles inline */
    button[kind="primary"][style],
    button[data-baseweb="button"][kind="primary"][style] {
        background: linear-gradient(135deg, #40E0D0 0%, #B19CD9 100%) !important;
        background-color: transparent !important;
        background-image: linear-gradient(135deg, #40E0D0 0%, #B19CD9 100%) !important;
    }
    
    /* ========================================================================
       ONGLETS (TABS)
       ======================================================================== */
    .stTabs [data-baseweb="tab-list"] {
        gap: 0.5rem;
        background: #FAFAFA;
        padding: 0.5rem;
        border-radius: var(--radius-md);
        margin-bottom: 1.5rem;
    }
    
    .stTabs [data-baseweb="tab"] {
        background: transparent !important;
        border-radius: var(--radius-sm) !important;
        padding: 0.75rem 1.5rem !important;
        color: var(--noir) !important;
        font-weight: 500 !important;
        transition: all 0.3s ease !important;
    }
    
    .stTabs [data-baseweb="tab"]:hover {
        background: #FEFEFE !important;
    }
    
    .stTabs [aria-selected="true"] {
        background: linear-gradient(135deg, #B19CD9 0%, #40E0D0 100%) !important;
        color: #FFFFFF !important;
        box-shadow: var(--shadow-sm) !important;
    }
    
    .stTabs [aria-selected="true"]:hover,
    .stTabs [aria-selected="true"]:active,
    .stTabs [aria-selected="true"]:focus {
        background: linear-gradient(135deg, #B19CD9 0%, #40E0D0 100%) !important;
        color: #FFFFFF !important;
    }
    
    /* ========================================================================
       MÉTRIQUES
       ======================================================================== */
    [data-testid="stMetricValue"] {
        font-size: 2.5rem;
        font-weight: 700;
        color: var(--noir);
        font-family: 'Poppins', sans-serif;
    }
    
    [data-testid="stMetricLabel"] {
        font-size: 1rem;
        color: var(--gris-fonce);
        font-weight: 500;
    }
    
    /* ========================================================================
       FORMULAIRES
       ======================================================================== */
    .stTextInput > div > div > input,
    .stNumberInput > div > div > input,
    .stSelectbox > div > div > select,
    .stTextArea > div > div > textarea {
        background: var(--blanc) !important;
        border: 2px solid #F5F5F5 !important;
        border-radius: var(--radius-sm) !important;
        transition: all 0.3s ease !important;
    }
    
    .stTextInput > div > div > input:focus,
    .stNumberInput > div > div > input:focus {
        border-color: #B19CD9 !important;
        box-shadow: 0 0 0 3px rgba(177, 156, 217, 0.1) !important;
        outline: none !important;
    }
    
    /* ========================================================================
       TABLEAUX
       ======================================================================== */
    .stDataFrame {
        border-radius: var(--radius-md);
        overflow: hidden;
        box-shadow: var(--shadow-sm);
        background: var(--blanc);
    }
    
    .stDataFrame thead {
        background: var(--gradient-soft);
    }
    
    .stDataFrame th {
        background: var(--beige-fonce) !important;
        color: var(--noir) !important;
        font-weight: 600 !important;
    }
    
    /* ========================================================================
       TYPOGRAPHIE
       ======================================================================== */
    h1, h2, h3, h4, h5, h6 {
        font-family: 'Poppins', sans-serif;
        color: var(--noir);
        font-weight: 600;
    }
    
    p, span, div {
        color: var(--noir);
    }
    
    /* ========================================================================
       ÉLÉMENTS CLIQUABLES - TOUJOURS VIOLET, JAMAIS NOIR
       ======================================================================== */
    a, a:visited, a:hover, a:active, a:focus {
        color: #B19CD9 !important;
    }
    
    /* Empêcher les styles noirs par défaut de Streamlit sur les boutons */
    [data-baseweb="button"] {
        background: linear-gradient(135deg, #B19CD9 0%, #40E0D0 100%) !important;
        color: #FFFFFF !important;
    }
    
    [data-baseweb="button"]:hover,
    [data-baseweb="button"]:active,
    [data-baseweb="button"]:focus {
        background: linear-gradient(135deg, #B19CD9 0%, #40E0D0 100%) !important;
        color: #FFFFFF !important;
    }
    
    /* Liens et éléments interactifs */
    [role="button"],
    [role="link"],
    [role="tab"] {
        color: #B19CD9 !important;
    }
    
    [role="button"]:hover,
    [role="link"]:hover,
    [role="tab"]:hover {
        color: #40E0D0 !important;
    }
    
    /* ========================================================================
       ALERTES
       ======================================================================== */
    .stAlert {
        border-radius: var(--radius-md);
        border-left: 4px solid;
    }
    
    /* ========================================================================
       SÉPARATEURS
       ======================================================================== */
    hr {
        border: none;
        border-top: 2px solid var(--beige-tres-fonce);
        margin: 2rem 0;
    }
    </style>
""", unsafe_allow_html=True)

if (not VISUAL_SAFE_MODE) and (not _apply_rich_theme):
    # Ecran de connexion: style leger pour accelerer le premier rendu.
    # Largeur finale login: theme.py (520px !important) prime sur cette base responsive.
    st.markdown(
        """
        <style>
        .stApp, .main .block-container {
            background: #FEFEFE !important;
            color: #2C2C2C !important;
            font-family: 'Inter', 'Segoe UI', sans-serif;
        }
        .main .block-container {
            padding-top: 1.2rem;
            padding-bottom: 1.2rem;
        }
        """
        + MAIN_BLOCK_CONTAINER_CSS
        + """
        </style>
        """,
        unsafe_allow_html=True,
    )

# Surcharge du fond de la sidebar + harmonisation des boutons
# Après connexion : dark navy premium (Linear / Stripe). Avant : plain ou image.
def _sidebar_styles_css(sidebar_bg_css, is_authenticated=False):
    if VISUAL_SAFE_MODE:
        return f"""
        <style>
        [data-testid="stSidebar"] {{
            {sidebar_bg_css}
        }}
        [data-testid="stSidebar"] [data-testid="stSidebarContent"] {{
            background: transparent !important;
        }}
        [data-testid="stSidebar"] .stButton > button {{
            background: #F3EEF9 !important;
            color: #2C2C2C !important;
            border: 1px solid #D8CCE9 !important;
            border-radius: 10px !important;
        }}
        [data-testid="stSidebar"] .stButton > button:hover {{
            background: #ECE4F8 !important;
        }}
        </style>
        """

    if is_authenticated:
        return f"""
        <style>
        /* Fond sidebar après connexion : même univers pastel que l'écran de login */
        [data-testid="stSidebar"] {{
            {sidebar_bg_css}
            padding: 1.5rem 1rem !important;
        }}
        [data-testid="stSidebar"] [data-testid="stSidebarContent"] {{
            background: transparent !important;
            display: flex;
            flex-direction: column;
            justify-content: center;
        }}

        /* Carte verre (glass) centrée dans la sidebar - modèle SpiritStitch */
        .sidebar-glass-card {{
            background: rgba(255, 255, 255, 0.88) !important;
            backdrop-filter: blur(24px);
            -webkit-backdrop-filter: blur(24px);
            border-radius: 24px;
            box-shadow:
                0 18px 45px rgba(15, 23, 42, 0.25),
                0 0 0 1px rgba(255, 255, 255, 0.55);
            padding: 1.75rem 1.5rem;
            width: 100%;
            box-sizing: border-box;
            display: flex;
            flex-direction: column;
            gap: 1.5rem;
        }}

        .sidebar-brand-title {{
            font-size: 1.25rem;
            font-weight: 800;
            letter-spacing: -0.02em;
            background: linear-gradient(135deg, #6C63FF 0%, #00C9A7 100%);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            background-clip: text;
            margin-bottom: 0.1rem;
        }}

        .sidebar-brand-subtitle {{
            font-size: 0.8rem;
            color: #6B7280;
        }}

        .sidebar-user {{
            margin-top: 0.9rem;
            font-size: 0.8rem;
            color: #6B7280;
        }}

        .sidebar-user-name {{
            font-weight: 600;
            color: #374151;
        }}

        .sidebar-user-role {{
            display: block;
            color: #9CA3AF;
            margin-top: 0.15rem;
        }}

        /* Navigation verticale : items comme sur la maquette */
        .sidebar-nav {{
            display: flex;
            flex-direction: column;
            gap: 0.4rem;
        }}

        .sidebar-nav button {{
            background: transparent !important;
            border-radius: 999px !important;
            border: none !important;
            padding: 0.55rem 0.9rem !important;
            width: 100% !important;
            display: flex !important;
            align-items: center;
            justify-content: flex-start;
            gap: 0.6rem;
            color: #374151 !important;
            font-size: 0.9rem !important;
            font-weight: 500 !important;
            box-shadow: none !important;
        }}

        .sidebar-nav button:hover {{
            background: rgba(148, 163, 184, 0.13) !important;
            color: #111827 !important;
        }}

        .sidebar-nav button::before {{
            content: '';
            flex-shrink: 0;
            width: 26px;
            height: 26px;
            border-radius: 999px;
            background: linear-gradient(135deg, #E0C3FC 0%, #8EC5FC 100%);
            opacity: 0.95;
        }}

        .sidebar-nav button:nth-of-type(1)::before {{
            background: linear-gradient(135deg, #818CF8 0%, #C4B5FD 100%);
        }}
        .sidebar-nav button:nth-of-type(2)::before {{
            background: linear-gradient(135deg, #34D399 0%, #6EE7B7 100%);
        }}
        .sidebar-nav button:nth-of-type(3)::before {{
            background: linear-gradient(135deg, #F97316 0%, #FDBA74 100%);
        }}
        .sidebar-nav button:nth-of-type(4)::before {{
            background: linear-gradient(135deg, #EC4899 0%, #F9A8D4 100%);
        }}
        .sidebar-nav button:nth-of-type(5)::before {{
            background: linear-gradient(135deg, #0EA5E9 0%, #7DD3FC 100%);
        }}
        .sidebar-nav button:nth-of-type(6)::before {{
            background: linear-gradient(135deg, #6B7280 0%, #9CA3AF 100%);
        }}

        .sidebar-logout button {{
            margin-top: 0.75rem;
            width: 100% !important;
            border-radius: 999px !important;
            background: #FFFFFF !important;
            color: #EF4444 !important;
            border: 1px solid rgba(239, 68, 68, 0.2) !important;
            font-weight: 600 !important;
            box-shadow: none !important;
        }}

        .sidebar-logout button:hover {{
            background: #FEF2F2 !important;
        }}
        </style>
        """

    return f"""
    <style>
    [data-testid="stSidebar"] {{
        {sidebar_bg_css}
    }}
    [data-testid="stSidebar"] [data-testid="stSidebarContent"] {{
        background: transparent !important;
    }}
    [data-testid="stSidebar"] .stButton > button {{
        background: linear-gradient(135deg, rgba(246, 239, 232, 0.9) 0%, rgba(143, 186, 217, 0.88) 50%, rgba(154, 143, 216, 0.87) 100%) !important;
        color: #3B2F4A !important;
        border: 1px solid rgba(59, 47, 74, 0.12) !important;
        border-radius: 12px !important;
        padding: 0.7rem 1rem !important;
        font-weight: 500 !important;
    }}
    [data-testid="stSidebar"] .stButton > button:hover {{
        background: linear-gradient(175deg, rgba(246, 239, 232, 0.95) 0%, rgba(143, 186, 217, 0.9) 45%, rgba(154, 143, 216, 0.9) 100%) !important;
    }}
    [data-testid="stSidebar"] .stButton > button.sidebar-btn-active {{
        background: linear-gradient(175deg, rgba(246, 239, 232, 0.98) 0%, rgba(143, 186, 217, 0.92) 40%, rgba(154, 143, 216, 0.92) 100%) !important;
    }}
    [data-testid="stSidebar"] .stMarkdown h3 { color: #3B2F4A !important; }
    [data-testid="stSidebar"] .stSuccess, [data-testid="stSidebar"] .stInfo {{
        background: rgba(246, 239, 232, 0.85) !important;
        color: #3B2F4A !important;
    }}
    </style>
    """


def get_page_background_html(page_id):
    """
    Retourne le HTML pour l'image de fond de la zone principale selon la page.
    Chaque page a sa propre image (config PAGE_BACKGROUND_IMAGES).
    Logo logoBon.png affiché au coin gauche de la zone principale.
    CSS direct + JS de secours pour appliquer sur .main.
    """
    if VISUAL_SAFE_MODE:
        return ""

    image_name = PAGE_BACKGROUND_IMAGES.get(page_id)
    if not image_name:
        return ""
    project_root = os.path.dirname(__file__)
    img_path = os.path.join(project_root, "assets", image_name)
    if not os.path.exists(img_path):
        return ""
    try:
        with open(img_path, "rb") as f:
            b64 = base64.b64encode(f.read()).decode("utf-8")
        ext = os.path.splitext(image_name)[1].lower()
        mime = "image/jpeg" if ext in (".jpg", ".jpeg") else "image/png"
        data_uri = f"data:{mime};base64,{b64}"
        # Échapper pour CSS url() : les apostrophes dans la data URI
        data_uri_css = data_uri.replace("'", "\\'")

        # Logo logoBon intégré en HTML (base64) - coin gauche zone principale
        logo_html = ""
        logo_path = os.path.join(project_root, "assets", "logoBon.png")
        if os.path.exists(logo_path):
            with open(logo_path, "rb") as f_logo:
                logo_b64 = base64.b64encode(f_logo.read()).decode("utf-8")
            logo_html = f'<div style="position:fixed;top:1rem;left:1rem;z-index:99999;width:110px;height:auto;background:rgba(255,255,255,0.95);padding:6px;border-radius:8px;box-shadow:0 4px 12px rgba(0,0,0,0.15);"><img src="data:image/png;base64,{logo_b64}" alt="Logo" style="width:100%;height:auto;display:block;"></div>'

        return (
            f"""
    {logo_html}
    <style id="page-bg-style">
    /* Zone principale : image en arrière-plan (floue) + voile blanc fort pour lisibilité */
    body .main, section.main, [data-testid="stAppViewContainer"] > div > section, section:has(div.block-container) {{
        position: relative !important;
        min-height: 100vh !important;
        background: #FAFAFA !important;
    }}
    /* Calque image : flou pour rester en fond discret */
    body .main::before, section.main::before, [data-testid="stAppViewContainer"] > div > section::before, section:has(div.block-container)::before {{
        content: '' !important;
        position: absolute !important;
        inset: 0 !important;
        z-index: -2 !important;
        background-image: url('{data_uri_css}') !important;
        background-size: cover !important;
        background-position: center !important;
        background-repeat: no-repeat !important;
        filter: blur(14px) !important;
        opacity: 0.75 !important;
    }}
    /* Voile blanc fort : rend le fond très clair, écrits bien visibles */
    body .main::after, section.main::after, [data-testid="stAppViewContainer"] > div > section::after, section:has(div.block-container)::after {{
        content: '' !important;
        position: absolute !important;
        inset: 0 !important;
        z-index: -1 !important;
        background: rgba(255, 255, 255, 0.72) !important;
    }}
    /* Bloc contenu : fond quasi blanc pour excellente lisibilité */
    body .main .block-container, .main .block-container {{
        background: rgba(255, 255, 255, 0.98) !important;
        border-radius: 12px !important;
        padding-top: 2rem !important;
        padding-bottom: 2rem !important;
        box-shadow: 0 2px 14px rgba(0, 0, 0, 0.05) !important;
    }}
    """
            + MAIN_BLOCK_CONTAINER_CSS
            + """
    </style>
    """
        )
    except Exception:
        return ""


def initialiser_session_state():
    """
    POURQUOI ? Pour initialiser toutes les variables de session Streamlit
    COMMENT ? On vérifie si chaque variable existe, sinon on la crée
    UTILISÉ OÙ ? Appelé une première fois juste après st.set_page_config, puis idempotent
    si rappelé (ex. tests). Le démarrage effectif de l'app ne doit pas dépendre uniquement de main().
    
    EXPLICATION DES VARIABLES :
    - db_connection : Stocke la connexion active à la base de données
    - authentifie : True si le couturier est connecté, False sinon
    - couturier_data : Informations du couturier connecté (nom, prénom, etc.)
    - page : Page actuelle ('connexion', 'nouvelle_commande', 'liste_commandes')
    - db_type : Type de connexion choisi ('postgresql_local' ou 'render_production')
    """
    initialize_session_state()
    sanitize_session_state()


def _render_authenticated_page(page_id: str):
    """Charge les vues à la demande pour réduire le cold start."""
    if page_id == 'super_admin_dashboard':
        from views.super_admin_dashboard import afficher_dashboard_super_admin
        afficher_dashboard_super_admin()
    elif page_id == 'nouvelle_commande':
        from views.commande_view import afficher_page_commande
        afficher_page_commande()
    elif page_id == 'liste_commandes':
        from views.liste_view import afficher_page_liste_commandes
        afficher_page_liste_commandes()
    elif page_id == 'comptabilite':
        from views.comptabilite_view import afficher_page_comptabilite
        afficher_page_comptabilite()
    elif page_id == 'charges':
        from views.mes_charges_view import afficher_page_mes_charges
        afficher_page_mes_charges()
    elif page_id == 'fermer_commandes':
        from views.fermer_commandes_view import afficher_page_fermer_commandes
        afficher_page_fermer_commandes()
    elif page_id == 'calendrier':
        from views.calendrier_view import afficher_page_calendrier
        afficher_page_calendrier(onglet_admin=False)
    elif page_id == 'dashboard':
        from views.dashboard_view import afficher_page_dashboard
        afficher_page_dashboard()
    elif page_id == 'administration':
        from views.admin_view import afficher_page_administration
        afficher_page_administration()


def deconnecter_utilisateur():
    """
    Déconnecte proprement l'utilisateur.
    NOTE: Cette fonction n'est plus utilisée directement.
    La déconnexion se fait maintenant via JavaScript pour éviter les erreurs DOM.
    """
    # Cette fonction est conservée pour compatibilité mais n'est plus appelée
    # La déconnexion se fait maintenant directement dans le bouton
    pass


def connecter_postgresql_local(config: dict) -> bool:
    """
    ============================================================================
    FONCTION 1 : CONNEXION À POSTGRESQL LOCAL
    ============================================================================
    
    POURQUOI ? Pour se connecter à PostgreSQL installé localement sur votre PC
    QUAND ? Utilisé pendant le développement et les tests sur votre PC
    
    COMMENT ÇA MARCHE ?
    1. Crée un objet DatabaseConnection avec le type 'postgresql'
    2. Tente de se connecter avec les paramètres fournis (host, port, etc.)
    3. Si succès : initialise les tables et retourne True
    4. Si échec : affiche l'erreur et retourne False
    
    PARAMÈTRES :
    - config : Dictionnaire avec host, port, database, user, password
    
    RETOURNE :
    - True si la connexion a réussi
    - False si la connexion a échoué
    
    UTILISÉ OÙ ? Dans views/auth_view.py quand l'user choisit PostgreSQL local
    """
    try:
        from models.database import DatabaseConnection, ChargesModel
        from controllers.auth_controller import AuthController
        from controllers.commande_controller import CommandeController

        # Créer l'objet de connexion avec le type 'postgresql'
        db_connection = DatabaseConnection('postgresql', config)
        
        # Tenter de se connecter
        if db_connection.connect():
            # Sauvegarder la connexion dans la session Streamlit
            st.session_state.db_connection = db_connection
            st.session_state.db_type = 'postgresql_local'
            
            # Initialiser les tables de la base de données
            # (créer les tables si elles n'existent pas)
            auth_controller = AuthController(db_connection)
            auth_controller.initialiser_tables()
            
            commande_controller = CommandeController(db_connection)
            commande_controller.initialiser_tables()
            
            # Initialiser les tables des charges
            charges_model = ChargesModel(db_connection)
            charges_model.creer_tables()
            
            return True  # Connexion réussie !
        
        return False  # La connexion a échoué
        
    except Exception as e:
        # Si une erreur se produit, l'afficher à l'utilisateur
        st.error(f"❌ Erreur de connexion PostgreSQL local : {e}")
        return False


def connecter_render_production(config: dict) -> bool:
    """
    ============================================================================
    FONCTION 2 : CONNEXION À RENDER PRODUCTION
    ============================================================================
    
    POURQUOI ? Pour se connecter à PostgreSQL hébergé sur Render (cloud)
    QUAND ? Utilisé en production quand l'app est déployée en ligne
    
    COMMENT ÇA MARCHE ?
    Exactement comme connecter_postgresql_local(), mais :
    - Se connecte à un serveur distant (Render) au lieu de localhost
    - Utilise les identifiants fournis par Render
    - Peut nécessiter SSL pour la sécurité
    
    DIFFÉRENCE AVEC POSTGRESQL LOCAL ?
    - PostgreSQL Local : Base de données sur VOTRE ordinateur (localhost)
    - Render : Base de données sur un serveur en ligne (accessible partout)
    
    PARAMÈTRES :
    - config : Dictionnaire avec host, port, database, user, password de Render
    
    RETOURNE :
    - True si la connexion a réussi
    - False si la connexion a échoué
    
    UTILISÉ OÙ ? Dans views/auth_view.py quand l'user choisit Render
    """
    try:
        from models.database import DatabaseConnection, ChargesModel
        from controllers.auth_controller import AuthController
        from controllers.commande_controller import CommandeController

        # Créer l'objet de connexion avec le type 'postgresql'
        # (Render utilise aussi PostgreSQL, mais hébergé en ligne)
        db_connection = DatabaseConnection('postgresql', config)
        
        # Tenter de se connecter au serveur Render
        if db_connection.connect():
            # Sauvegarder la connexion dans la session
            st.session_state.db_connection = db_connection
            st.session_state.db_type = 'render_production'
            
            # Initialiser les tables
            auth_controller = AuthController(db_connection)
            auth_controller.initialiser_tables()
            
            commande_controller = CommandeController(db_connection)
            commande_controller.initialiser_tables()
            
            # Initialiser les tables des charges
            charges_model = ChargesModel(db_connection)
            charges_model.creer_tables()
            
            return True  # Connexion réussie !
        
        return False  # La connexion a échoué
        
    except Exception as e:
        # Afficher l'erreur spécifique à Render
        st.error(f"❌ Erreur de connexion Render : {e}")
        return False


def afficher_header_app():
    """
    Affiche le header de l'application avec logo et nom (multi-tenant)
    Le logo est récupéré depuis la base de données selon le salon de l'utilisateur
    Retourne le HTML formaté pour être utilisé dans la sidebar
    """
    import base64
    import os
    
    # Nom de l'application (depuis la configuration)
    app_name = APP_CONFIG.get('name', 'JAIND')
    
    # Récupérer le logo depuis la base de données (multi-tenant)
    logo_base64 = None
    logo_mime = None
    
    try:
        # Vérifier si on a une connexion à la base de données et un utilisateur connecté
        if st.session_state.get('db_connection') and st.session_state.get('couturier_data'):
            from models.database import AppLogoModel
            from utils.role_utils import obtenir_salon_id
            
            couturier_data = st.session_state.get('couturier_data')
            salon_id = obtenir_salon_id(couturier_data)
            
            if salon_id:
                logo_model = AppLogoModel(st.session_state.db_connection)
                logo_data = logo_model.recuperer_logo(salon_id)
                
                if logo_data and logo_data.get('logo_data'):
                    logo_bytes = logo_data['logo_data']
                    logo_mime = logo_data.get('mime_type', 'image/png')
                    logo_base64 = base64.b64encode(logo_bytes).decode()
    except Exception as e:
        # En cas d'erreur, on continue sans logo
        logger.warning("Erreur recuperation logo depuis BDD: %s", e)
        logo_base64 = None
    
    # Fallback : chercher le logo dans le système de fichiers si pas en BDD
    if not logo_base64:
        logo_base_path = APP_CONFIG.get('logo_path', 'assets/logo')
        logo_path = None
        logo_ext = None
        
        for ext in ['png', 'jpg', 'jpeg']:
            test_path = f"{logo_base_path}.{ext}"
            if os.path.exists(test_path):
                logo_path = test_path
                logo_ext = ext
                break
        
        if logo_path:
            try:
                with open(logo_path, "rb") as img_file:
                    logo_base64 = base64.b64encode(img_file.read()).decode()
                    logo_mime = f"image/{logo_ext}"
            except Exception:
                logo_base64 = None
    
    # Construire le HTML - CENTRÉ avec styles inline uniquement (pas de classes CSS)
    html = '<div style="text-align: center; width: 100%; display: flex; flex-direction: column; align-items: center; justify-content: center; padding: 1.5rem 1rem; margin-bottom: 1rem; border-bottom: 2px solid #F5F5F5;">'
    
    if logo_base64:
        mime_type = logo_mime or 'image/png'
        html += f'<img src="data:{mime_type};base64,{logo_base64}" alt="Logo" style="max-width: min(340px, 95%); max-height: 340px; width: auto; height: auto; margin: 0 auto; display: block; border-radius: 12px; box-shadow: 0 3px 12px rgba(0,0,0,0.15); object-fit: contain;">'
    
    html += '</div>'
    
    return html


def afficher_sidebar():
    """Affiche la barre latérale avec navigation (branding + menu premium après connexion)."""
    with st.sidebar:
        if st.session_state.authentifie:
            # Logo SpiritStitch en haut (premium dark sidebar)
            from utils.theme import LOGIN_DISPLAY_TITLE_1, LOGIN_DISPLAY_TITLE_2
            st.markdown(
                f'<div style="margin-bottom: 1.5rem;">'
                f'<span style="font-size: 1.35rem; font-weight: 800; letter-spacing: -0.02em; '
                f'background: linear-gradient(135deg, #E0E0FF 0%, #00C9A7 100%); '
                f'-webkit-background-clip: text; -webkit-text-fill-color: transparent; '
                f'background-clip: text;">{LOGIN_DISPLAY_TITLE_1}{LOGIN_DISPLAY_TITLE_2}</span></div>',
                unsafe_allow_html=True,
            )
            # Informations du couturier connecté
            st.success(f"**Connecté:** {st.session_state.couturier_data['prenom']} {st.session_state.couturier_data['nom']}")
            role_display = st.session_state.couturier_data.get('role', 'employe')
            db_type = st.session_state.get('db_type', 'inconnue')
            db_label = (
                "Render (production)"
                if db_type == 'render_production'
                else "PostgreSQL local"
                if db_type == 'postgresql_local'
                else str(db_type)
            )
            st.info(
                f"**Code:** {st.session_state.couturier_data['code_couturier']} | "
                f"**Rôle:** {role_display} | **Base:** {db_label}"
            )
            st.markdown("---")
            
            # Menu SUPER ADMINISTRATION (uniquement pour SUPER_ADMIN) - EN PREMIER
            if est_super_admin():
                st.markdown("### 🔧 SUPER ADMINISTRATION")
                
                if st.button("📊 Dashboard Super Admin", use_container_width=True):
                    st.session_state.page = 'super_admin_dashboard'
                    st.rerun()
                
                st.markdown("---")
                st.markdown("### 📋 Navigation")
            else:
                # Navigation standard pour les autres utilisateurs
                st.markdown("### 📋 Navigation")
            
            # Boutons de navigation standard (pour tous)
            if st.button("📊 Tableau de bord", use_container_width=True):
                st.session_state.page = 'dashboard'
                st.rerun()
            
            if st.button("➕ Nouvelle commande", use_container_width=True):
                st.session_state.page = 'nouvelle_commande'
                st.rerun()
            
            if st.button("📜 Mes commandes", use_container_width=True):
                st.session_state.page = 'liste_commandes'
                st.rerun()
            
            if st.button("💰 Comptabilité", use_container_width=True):
                st.session_state.page = 'comptabilite'
                st.rerun()
            
            if st.button("📄 Mes charges", use_container_width=True):
                st.session_state.page = 'charges'
                st.rerun()
            
            if st.button("🔒 Fermer mes commandes", use_container_width=True):
                st.session_state.page = 'fermer_commandes'
                st.rerun()
            
            if st.button("📋 Modèles & Calendrier", use_container_width=True):
                st.session_state.page = 'calendrier'
                st.rerun()
            
            # Menu Administration (uniquement pour les admins normaux, pas SUPER_ADMIN)
            if est_admin(st.session_state.couturier_data) and not est_super_admin():
                st.markdown("---")
                st.markdown("### 👑 Administration")
                if st.button("👑 Administration", use_container_width=True):
                    st.session_state.page = 'administration'
                    st.rerun()
            
            st.markdown("---")
            
            # Bouton de déconnexion avec approche simplifiée
            if st.button("🚪 Déconnexion", use_container_width=True, key="btn_deconnexion"):
                logout_user()
                # Rediriger vers la page de connexion
                st.rerun()
        else:
            # Sidebar page de connexion : branding SpiritStitch (deux tons, plus vide)
            from utils.theme import LOGIN_DISPLAY_TITLE_1, LOGIN_DISPLAY_TITLE_2, LOGIN_DISPLAY_SUBTITLE
            st.markdown(
                "<div style='padding: 2rem 1rem; text-align: center;'>"
                f"<p style='font-size: 1.5rem; font-weight: 700; margin-bottom: 0.2rem;'>"
                f"<span style='color: #B19CD9;'>{LOGIN_DISPLAY_TITLE_1}</span>"
                f"<span style='color: #40E0D0;'>{LOGIN_DISPLAY_TITLE_2}</span>"
                "</p>"
                f"<p style='color: #6B7280; font-size: 0.9rem; margin-bottom: 1.5rem; line-height: 1.4;'>{LOGIN_DISPLAY_SUBTITLE}</p>"
                "<p style='color: #9CA3AF; font-size: 0.85rem; line-height: 1.5;'>"
                "Connectez-vous pour accéder à votre atelier et gérer vos commandes."
                "</p>"
                "<p style='color: #B19CD9; font-size: 0.8rem; margin-top: 1.5rem;'>"
                "— Votre espace couture —"
                "</p>"
                "</div>",
                unsafe_allow_html=True,
            )


def afficher_header_principal():
    """
    Header minimaliste et élégant - Design épuré
    """
    # Header discret avec juste un séparateur élégant
    st.markdown("""
        <div style='border-bottom: 2px solid #e0e0e0; margin-bottom: 1.5rem; padding-bottom: 0.5rem;'>
        </div>
    """, unsafe_allow_html=True)


def main():
    """Fonction principale de l'application (session déjà initialisée après set_page_config)."""
    # Sidebar : thème SpiritStitch (Premium / Ultra Minimal) en mode safe, sinon image nav ou plain
    sidebar_bg_css = (
        theme_sidebar_bg_css()
        if VISUAL_SAFE_MODE
        else (SIDEBAR_BG_DARK if st.session_state.authentifie else _get_sidebar_bg_css_with_image())
    )
    st.markdown(_sidebar_styles_css(sidebar_bg_css, is_authenticated=st.session_state.authentifie), unsafe_allow_html=True)
    
    # Afficher la sidebar
    afficher_sidebar()
    
    # Header minimaliste (optionnel, peut être commenté)
    # afficher_header_principal()
    
    # Router selon la page
    if not st.session_state.authentifie:
        # Page de connexion
        from views.auth_view import afficher_page_connexion
        afficher_page_connexion()
    else:
        # Pages authentifiées : image de fond selon la page (calque fixe + style)
        page_bg_html = get_page_background_html(st.session_state.page)
        if page_bg_html:
            st.markdown(page_bg_html, unsafe_allow_html=True)

        # Logo logoBon au coin gauche de l'image principale
        logo_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets", "logoBon.png")
        if os.path.exists(logo_path):
            try:
                from PIL import Image
                logo_img = Image.open(logo_path)
                c1, c2 = st.columns([0.2, 0.8])
                with c1:
                    st.image(logo_img, width=100)
            except Exception:
                c1, c2 = st.columns([0.2, 0.8])
                with c1:
                    st.image(logo_path, width=100)

        # Dashboard SUPER_ADMIN (priorité absolue)
        if st.session_state.page == 'super_admin_dashboard':
            if est_super_admin():
                _render_authenticated_page('super_admin_dashboard')
            else:
                st.error("❌ Accès refusé. Cette page est réservée au Super Administrateur.")
                st.session_state.page = 'dashboard'
                st.rerun()
        elif st.session_state.page in {
            'nouvelle_commande', 'liste_commandes', 'comptabilite',
            'charges', 'fermer_commandes', 'calendrier', 'dashboard'
        }:
            _render_authenticated_page(st.session_state.page)
        elif st.session_state.page == 'administration':
            # Vérifier que l'utilisateur est admin ou super-admin
            if est_admin(st.session_state.couturier_data) or est_super_admin():
                _render_authenticated_page('administration')
            else:
                st.error("❌ Accès refusé. Cette page est réservée aux administrateurs.")
                st.session_state.page = 'dashboard'
                st.rerun()
        else:
            # Page par défaut après connexion
            if est_super_admin():
                st.session_state.page = 'super_admin_dashboard'
            else:
                st.session_state.page = 'dashboard'
            st.rerun()

    if VISUAL_SAFE_MODE:
        st.markdown("---")
        st.caption(
            f"{APP_CONFIG.get('name', 'Gestion Couturier')} - "
            f"{APP_CONFIG.get('subtitle', 'Systeme de gestion d atelier')}"
        )

    # Footer global uniquement sur pages authentifiées.
    # La page de connexion gère déjà son propre footer.
    if st.session_state.authentifie:
        render_app_footer()


if __name__ == "__main__":
    main()
