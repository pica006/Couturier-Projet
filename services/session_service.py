"""
Service centralise de gestion du session_state Streamlit.
"""

import os
import streamlit as st


SESSION_DEFAULTS = {
    "db_connection": None,
    "authentifie": False,
    "couturier_data": None,
    "page": "connexion",
    "db_type": None,
}

TRANSIENT_KEYS = {
    "pdf_path_upload",
    "pdf_filename",
    "show_download_section",
    "show_upload_section",
    # Clés ad hoc de la vue commande (évite stale state entre sessions)
    "prix_total_form",
    "avance_form",
    "reste_form",
    "modele_selectionne",
    "categorie_precedente",
    "sexe_precedent",
}


def initialize_session_state() -> None:
    for key, default_value in SESSION_DEFAULTS.items():
        if key not in st.session_state:
            st.session_state[key] = default_value


def sanitize_session_state() -> None:
    """
    Applique des garde-fous sur l'etat Streamlit pour eviter stale state.
    """
    initialize_session_state()

    if not isinstance(st.session_state.get("authentifie"), bool):
        st.session_state["authentifie"] = False
    if st.session_state.get("page") is None:
        st.session_state["page"] = "connexion"
    # Une connexion stale peut subsister après un rerun/logout.
    db_connection = st.session_state.get("db_connection")
    if db_connection is not None:
        try:
            is_connected = db_connection.is_connected() if hasattr(db_connection, "is_connected") else bool(db_connection.get_connection())
            if not is_connected:
                st.session_state["db_connection"] = None
                st.session_state["db_type"] = None
        except Exception:
            st.session_state["db_connection"] = None
            st.session_state["db_type"] = None

    pdf_path = st.session_state.get("pdf_path_upload")
    if pdf_path and (not isinstance(pdf_path, str) or not os.path.exists(pdf_path)):
        st.session_state["pdf_path_upload"] = None
        st.session_state["pdf_filename"] = None
        st.session_state["show_download_section"] = False
        st.session_state["show_upload_section"] = False

    if not st.session_state.get("authentifie", False):
        st.session_state["page"] = "connexion"
        for key in TRANSIENT_KEYS:
            if key in st.session_state:
                try:
                    del st.session_state[key]
                except Exception:
                    pass


def logout_user() -> None:
    db_connection = st.session_state.get("db_connection")
    if db_connection:
        try:
            db_connection.disconnect()
        except Exception:
            pass

    for key in list(st.session_state.keys()):
        if key not in ("db_connection", "db_type"):
            try:
                del st.session_state[key]
            except Exception:
                pass

    st.session_state["db_connection"] = None
    st.session_state["db_type"] = None
    st.session_state["authentifie"] = False
    st.session_state["couturier_data"] = None
    st.session_state["page"] = "connexion"
