"""
Utilitaires UI centralisés pour les vues Streamlit.
"""

from contextlib import contextmanager
import streamlit as st


def ajouter_espace_vertical(lignes: int = 1) -> None:
    """
    Ajoute un espacement vertical sans HTML inline.
    """
    for _ in range(max(0, lignes)):
        st.write("")


def appliquer_style_pages_critiques() -> None:
    """
    Applique un style visuel minimal et coherent pour les pages critiques.
    """
    st.markdown(
        """
        <style>
        .main .block-container {
            max-width: 1200px;
            padding-top: 1.6rem;
            padding-bottom: 1.6rem;
        }

        h3 {
            margin-top: 0.6rem;
            margin-bottom: 0.65rem;
        }

        .stButton > button, button[kind="primary"] {
            border-radius: 10px !important;
            min-height: 2.45rem;
            font-weight: 600 !important;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def afficher_titre_section(titre: str, niveau: int = 3) -> None:
    """
    Affiche un titre homogene pour les sections.
    """
    niveau = min(6, max(1, int(niveau)))
    st.markdown(f"{'#' * niveau} {titre}")


def afficher_erreur_minimale(message: str) -> None:
    """
    Affiche une erreur concise et coherente.
    """
    st.error(f"❌ {message}")


def afficher_info_minimale(message: str) -> None:
    """
    Affiche une information concise et coherente.
    """
    st.info(f"ℹ️ {message}")


@contextmanager
def etat_chargement(message: str):
    """
    Spinner standardise pour les etats de chargement.
    """
    with st.spinner(f"⏳ {message}"):
        yield

