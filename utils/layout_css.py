"""
Largeur responsive de la zone de contenu Streamlit (.main .block-container).

Ne pas utiliser sur la page de connexion : utils/theme.py impose une carte étroite
avec max-width: 520px !important (prioritaire).
"""

# Fragment à insérer dans un bloc <style> existant (hors login).
MAIN_BLOCK_CONTAINER_CSS = """
    .main .block-container {
        width: 100% !important;
        max-width: min(100%, 1680px) !important;
        margin-left: auto !important;
        margin-right: auto !important;
        padding-left: clamp(0.65rem, 2.2vw, 1.75rem) !important;
        padding-right: clamp(0.65rem, 2.2vw, 1.75rem) !important;
        box-sizing: border-box !important;
    }
    @media (max-width: 768px) {
        .main .block-container {
            max-width: 100% !important;
            padding-left: 0.5rem !important;
            padding-right: 0.5rem !important;
        }
    }
    @media (max-width: 480px) {
        .main .block-container {
            padding-left: 0.4rem !important;
            padding-right: 0.4rem !important;
        }
    }
"""

# Alignement footer / bottom-nav sur la même largeur que le contenu
CONTENT_INNER_WIDTH_CSS = """
    .app-footer-inner,
    .bottom-nav-inner {
        width: 100% !important;
        max-width: min(100%, 1680px) !important;
        margin-left: auto !important;
        margin-right: auto !important;
        padding-left: clamp(0.65rem, 2.2vw, 1.75rem) !important;
        padding-right: clamp(0.65rem, 2.2vw, 1.75rem) !important;
        box-sizing: border-box !important;
    }
    @media (max-width: 768px) {
        .app-footer-inner,
        .bottom-nav-inner {
            max-width: 100% !important;
            padding-left: 0.5rem !important;
            padding-right: 0.5rem !important;
        }
    }
"""
