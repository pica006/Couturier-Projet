"""
Module unique "airan2" pour centraliser le SUPER_ADMIN en production.

Ce fichier sert de point d'entree unique et reutilise le dashboard super admin
deja present dans le projet (avec tous ses onglets).
"""

import streamlit as st

from utils.permissions import est_super_admin
from views.super_admin_dashboard import afficher_dashboard_super_admin


def afficher_page_superadmin_airan2():
    """
    Point d'entree unique SUPER_ADMIN (prod Render).

    Inclut tous les onglets via `afficher_dashboard_super_admin()` :
    - Vue d'ensemble
    - Gerer les salons
    - Gerer les utilisateurs
    - Toutes les commandes
    - Statistiques avancees
    - Demandes globales
    - Rapports
    """
    st.title("Super Admin - Airan2")

    if not st.session_state.get("authentifie"):
        st.error("Vous devez etre connecte pour acceder a cette page.")
        return

    if not st.session_state.get("db_connection"):
        st.error("Connexion base de donnees absente.")
        return

    if not est_super_admin():
        st.error("Acces refuse: cette page est reservee au Super Admin.")
        return

    afficher_dashboard_super_admin()


if __name__ == "__main__":
    afficher_page_superadmin_airan2()

