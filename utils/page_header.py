"""
Fonction utilitaire pour generer l'en-tete banniere des pages.
Style : Degrade violet #6C63FF -> turquoise #00C9A7 (Premium Glass).
"""

import streamlit as st


def afficher_header_page(titre: str, sous_titre: str = ""):
    """
    Affiche un en-tete banner avec degrade violet->turquoise.

    Args:
        titre    : Titre principal (avec emoji si souhaite)
        sous_titre: Sous-titre optionnel
    """
    sous_html = (
        f"<p style='color:rgba(255,255,255,0.88);margin:0.4rem 0 0 0;"
        f"font-size:0.95rem;font-family:Inter,sans-serif;'>{sous_titre}</p>"
        if sous_titre else ""
    )
    st.markdown(
        f"""
        <div style='
            background: linear-gradient(135deg, #6C63FF 0%, #00C9A7 100%);
            padding: 1.75rem 2rem;
            border-radius: 20px;
            margin-bottom: 2rem;
            box-shadow: 0 10px 32px rgba(108,99,255,0.22);
            position: relative;
            overflow: hidden;
        '>
            <div style='position:absolute;top:-50%;right:-5%;width:200px;height:200px;
                border-radius:50%;background:rgba(255,255,255,0.08);'></div>
            <div style='position:absolute;bottom:-40%;right:12%;width:110px;height:110px;
                border-radius:50%;background:rgba(255,255,255,0.05);'></div>
            <div style='position:relative;z-index:1;'>
                <h1 style='color:white;margin:0;font-size:1.7rem;font-weight:700;
                    font-family:Poppins,Inter,sans-serif;letter-spacing:-0.01em;
                    text-shadow:0 2px 8px rgba(0,0,0,0.10);'>{titre}</h1>
                {sous_html}
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
