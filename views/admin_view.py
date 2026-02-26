"""
================================================================================
PAGE D'ADMINISTRATION - VUE 360° DE L'ENTREPRISE
================================================================================
Page réservée aux administrateurs pour voir toutes les activités de l'entreprise
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
from typing import Optional, Dict
import os
import io
import tempfile
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.units import cm
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image
from reportlab.lib.utils import ImageReader
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle

from models.database import ChargesModel, CommandeModel, CouturierModel, ClientModel, AppLogoModel
from views.mes_charges_view import _generer_pdf_impots
from models.salon_model import SalonModel
from utils.role_utils import est_admin, obtenir_salon_id

# Barème d'impôts (identique à celui de mes_charges_view.py)
TRANCHES_IMPOTS = [
    {'min': 0, 'max': 500000, 'impot': 5000},
    {'min': 500000, 'max': 1000000, 'impot': 75000},
    {'min': 1000000, 'max': 1500000, 'impot': 100000},
    {'min': 1500000, 'max': 2000000, 'impot': 125000},
    {'min': 2000000, 'max': 2500000, 'impot': 150000},
    {'min': 2500000, 'max': 5000000, 'impot': 375000},
    {'min': 5000000, 'max': 10000000, 'impot': 750000},
    {'min': 10000000, 'max': 20000000, 'impot': 1250000},
    {'min': 20000000, 'max': 30000000, 'impot': 2500000},
    {'min': 30000000, 'max': 50000000, 'impot': 5000000},
]


def afficher_page_administration():
    """
    Page d'administration - Vue 360° de l'entreprise
    Accessible uniquement aux administrateurs
    """
    
    # En-tête encadré standardisé
    #afficher_header_page("🔧 Administration", "Vue 360° de votre entreprise")
    
    # Vérification de l'authentification
    if not st.session_state.get('authentifie', False):
        st.error("❌ Vous devez être connecté pour accéder à cette page")
        return
    
    if not st.session_state.get('db_connection'):
        st.error("❌ Connexion à la base de données requise")
        return
    
    # Vérification du rôle admin
    couturier_data = st.session_state.get('couturier_data')
    if not est_admin(couturier_data):
        st.error("❌ Accès refusé. Cette page est réservée aux administrateurs.")
        st.info("💡 Contactez un administrateur pour obtenir les droits d'accès.")
        return
    
    # Initialisation des modèles
    charges_model = ChargesModel(st.session_state.db_connection)
    commande_model = CommandeModel(st.session_state.db_connection)
    couturier_model = CouturierModel(st.session_state.db_connection)
    client_model = ClientModel(st.session_state.db_connection)
    salon_model = SalonModel(st.session_state.db_connection)
    salon_id_admin = obtenir_salon_id(couturier_data)
    
    # Récupérer les informations du salon
    salon_info = None
    if salon_id_admin:
        salon_info = salon_model.obtenir_salon_by_id(salon_id_admin)
    
    # ========================================================================
    # HEADER DE LA PAGE
    # ========================================================================
    
    st.markdown("""
        <div style='background: linear-gradient(135deg, #B19CD9 0%, #40E0D0 100%); 
                    padding: 2rem; border-radius: 16px; margin-bottom: 2rem; 
                    box-shadow: 0 4px 8px rgba(0,0,0,0.1); text-align: center;'>
            <h1 style='color: white; margin: 0; font-size: 2.5rem; font-weight: 700; 
                       font-family: Poppins, sans-serif; text-shadow: 0 2px 4px rgba(0,0,0,0.2);'>👑 Administration</h1>
            <p style='color: rgba(255,255,255,0.95); margin: 0.5rem 0 0 0; font-size: 1.1rem;'>Vue 360° de l'entreprise - Toutes les activités</p>
        </div>
    """, unsafe_allow_html=True)
    
    # Afficher les informations du salon actuel
    if salon_info:
        col_salon1, col_salon2, col_salon3 = st.columns(3)
        with col_salon1:
            st.info(f"🏢 **Salon :** {salon_info.get('nom_salon', salon_id_admin)}")
        with col_salon2:
            st.info(f"📍 **Quartier :** {salon_info.get('quartier', 'N/A')}")
        with col_salon3:
            st.info(f"🆔 **ID Salon :** {salon_id_admin}")
        st.markdown("---")
    elif salon_id_admin:
        st.info(f"🏢 **Salon ID :** {salon_id_admin}")
        st.markdown("---")
    
    # ========================================================================
    # TABS PRINCIPAUX
    # ========================================================================
    
    tab1, tab2, tab3, tab4, tab5, tab6, tab7 = st.tabs([
        "📊 Tableau de bord",
        "🌐 Vue 360°",
        "💰 Toutes les charges",
        "📦 Gestion des commandes",
        "📋 Modèles & Calendrier",
        "🧮 Calcul d'impôts",
        "👥 Gestion des utilisateurs",
    ])
    
    # ========================================================================
    # TAB 1 : TABLEAU DE BORD (figures + tableau)
    # ========================================================================
    
    with tab1:
        afficher_tableau_de_bord_admin(commande_model, couturier_model, salon_id_admin)
    
    # ========================================================================
    # TAB 2 : VUE 360° DE L'ATELIER
    # ========================================================================
    
    with tab2:
        afficher_vue_360(couturier_model, charges_model, commande_model, client_model, salon_id_admin)
    
    # ========================================================================
    # TAB 3 : TOUTES LES CHARGES
    # ========================================================================
    
    with tab3:
        afficher_toutes_charges(charges_model, salon_id_admin)
    
    # ========================================================================
    # TAB 4 : GESTION DES COMMANDES
    # ========================================================================
    
    with tab4:
        afficher_gestion_commandes_admin(commande_model, couturier_data)
    
    # ========================================================================
    # TAB 5 : CALENDRIER DES LIVRAISONS
    # ========================================================================
    
    with tab5:
        from views.calendrier_view import afficher_page_calendrier
        afficher_page_calendrier(onglet_admin=True)
    
    # ========================================================================
    # TAB 6 : CALCUL D'IMPÔTS
    # ========================================================================
    
    with tab6:
        afficher_calcul_impots_admin(charges_model, commande_model)
    
    # ========================================================================
    # TAB 7 : GESTION DES UTILISATEURS
    # ========================================================================
    
    with tab7:
        afficher_gestion_utilisateurs(couturier_model, couturier_data)
    
    # (Plus d'onglet spécifique de réinitialisation : tout est géré dans "Gestion des utilisateurs")


def afficher_tableau_de_bord_admin(
    commande_model: CommandeModel,
    couturier_model: CouturierModel,
    salon_id_admin: str,
):
    """Affiche le tableau de bord admin : exactement le même contenu que l'onglet Modèles réalisés."""
    if not salon_id_admin:
        st.warning("⚠️ Aucun salon associé à votre compte administrateur")
        return

    st.markdown("### 📊 Tableau de bord administrateur")
    st.markdown("— Même contenu que l'onglet **Modèles réalisés** : filtre par couturier, répartition par modèle, graphiques, galerie photos.")
    st.markdown("---")

    couturier_id_admin = st.session_state.get("couturier_data", {}).get("id")
    from views.calendrier_view import _afficher_modeles_realises
    _afficher_modeles_realises(
        commande_model,
        couturier_model,
        couturier_id=couturier_id_admin,
        salon_id=salon_id_admin,
        est_admin_user=True,
        key_prefix="admin_tdb",
    )


def afficher_vue_360(couturier_model: CouturierModel, charges_model: ChargesModel, 
                     commande_model: CommandeModel, client_model: ClientModel,
                     salon_id_admin: str):
    """Affiche une vue 360° complète de l'atelier"""
    
    st.markdown("### 🌐 Vue 360° de l'atelier")
    
    # Afficher le salon actuel
    if salon_id_admin:
        st.info(f"📊 **Statistiques du salon :** {salon_id_admin}")
    else:
        st.warning("⚠️ Aucun salon associé à votre compte administrateur")
        return
    
    st.markdown("Vue d'ensemble complète de toutes les activités de votre salon")
    st.markdown("---")
    
    # Récupérer tous les couturiers du salon
    tous_couturiers = couturier_model.lister_tous_couturiers(salon_id=salon_id_admin)
    
    # Sélection de période et de couturier
    col1, col2, col3 = st.columns(3)
    
    with col1:
        date_debut = st.date_input(
            "Date de début",
            value=datetime.now().date().replace(day=1, month=1),
            key="admin_vue360_debut"
        )
    
    with col2:
        date_fin = st.date_input(
            "Date de fin",
            value=datetime.now().date(),
            key="admin_vue360_fin"
        )
    
    with col3:
        # Sélecteur de couturier (option "Tous" pour voir le total)
        options_couturiers = ["👥 Tous les couturiers"] + [
            f"{c['code_couturier']} - {c['prenom']} {c['nom']} ({'👑 Admin' if c.get('role') == 'admin' else '👤 Employé'})"
            for c in tous_couturiers
        ]
        couturier_selectionne = st.selectbox(
            "Filtrer par couturier",
            options=options_couturiers,
            key="admin_vue360_couturier"
        )
    
    st.markdown("---")
    
    # Déterminer le couturier_id sélectionné
    couturier_id_filtre = None
    if couturier_selectionne and couturier_selectionne != "👥 Tous les couturiers":
        # Extraire l'ID du couturier sélectionné
        code_selectionne = couturier_selectionne.split(" - ")[0]
        couturier_selectionne_obj = next(
            (c for c in tous_couturiers if c['code_couturier'] == code_selectionne),
            None
        )
        if couturier_selectionne_obj:
            couturier_id_filtre = couturier_selectionne_obj['id']
    
    # Calculs globaux
    date_debut_dt = datetime.combine(date_debut, datetime.min.time())
    date_fin_dt = datetime.combine(date_fin, datetime.max.time())
    
    # ========================================================================
    # STATISTIQUES GLOBALES OU PAR COUTURIER
    # ========================================================================
    
    if couturier_id_filtre:
        st.markdown(f"#### 📊 Statistiques détaillées - {couturier_selectionne}")
        couturier_obj = couturier_selectionne_obj
    else:
        st.markdown("#### 📊 Statistiques globales du salon")
        couturier_obj = None
    
    # Total des charges (filtré par couturier si sélectionné)
    total_charges = charges_model.total_charges(
        couturier_id=couturier_id_filtre,
        date_debut=date_debut_dt,
        date_fin=date_fin_dt,
        tous_les_couturiers=False,
        salon_id=salon_id_admin
    )
    
    # Total du CA (filtré par couturier si sélectionné)
    commandes = commande_model.lister_commandes(
        couturier_id_filtre, 
        tous_les_couturiers=False, 
        salon_id=salon_id_admin
    )
    ca_total = 0
    nb_commandes = 0
    commandes_en_cours = 0
    commandes_terminees = 0
    
    if commandes:
        df_cmd = pd.DataFrame(commandes)
        if 'date_creation' in df_cmd.columns:
            df_cmd['date_creation'] = pd.to_datetime(df_cmd['date_creation'])
            mask = (
                (df_cmd['date_creation'].dt.date >= date_debut) &
                (df_cmd['date_creation'].dt.date <= date_fin)
            )
            df_cmd = df_cmd[mask]
            ca_total = df_cmd['prix_total'].sum() if 'prix_total' in df_cmd.columns else 0
            nb_commandes = len(df_cmd)
            if 'statut' in df_cmd.columns:
                commandes_en_cours = len(df_cmd[df_cmd['statut'].str.contains('En cours|en cours', case=False, na=False)])
                commandes_terminees = len(df_cmd[df_cmd['statut'].str.contains('Terminé|terminé|Livré|livré', case=False, na=False)])
    
    # Nombre total de clients (tous les couturiers du salon)
    try:
        cursor = client_model.db.get_connection().cursor()
        # Requête compatible MySQL et PostgreSQL
        query = """
            SELECT COUNT(DISTINCT c.id)
            FROM clients c
            INNER JOIN couturiers ct ON c.couturier_id = ct.id
            WHERE ct.salon_id = %s
        """
        cursor.execute(query, (salon_id_admin,))
        result = cursor.fetchone()
        nb_clients_total = result[0] if result and result[0] is not None else 0
        cursor.close()
    except Exception as e:
        print(f"Erreur récupération nombre de clients: {e}")
        nb_clients_total = 0
    
    # Nombre d'employés (uniquement si vue globale)
    if not couturier_id_filtre:
        nb_employes = len([c for c in tous_couturiers if c.get('role') == 'employe'])
        nb_admins = len([c for c in tous_couturiers if c.get('role') == 'admin'])
    else:
        nb_employes = 0
        nb_admins = 0
    
    # Bénéfice net
    benefice_net = ca_total - total_charges
    
    # Nombre de charges (filtrées par couturier si sélectionné)
    charges = charges_model.lister_charges(
        couturier_id=couturier_id_filtre, 
        limit=10000, 
        tous_les_couturiers=(couturier_id_filtre is None),
        salon_id=salon_id_admin
    )
    nb_charges = len(charges)
    
    # Résumé financier
    if couturier_id_filtre:
        st.markdown(f"#### 📊 Résumé financier - {couturier_obj['prenom']} {couturier_obj['nom']}")
    else:
        st.markdown("#### 📊 Résumé financier du salon")
    
    # KPIs Principaux
    col_k1, col_k2, col_k3, col_k4 = st.columns(4)
    
    with col_k1:
        st.metric(
            label="💰 Chiffre d'affaires",
            value=f"{ca_total:,.0f} FCFA",
            help=f"Total des commandes pour la période sélectionnée (Salon: {salon_id_admin})"
        )
    
    with col_k2:
        st.metric(
            label="💸 Total des charges",
            value=f"{total_charges:,.0f} FCFA",
            help=f"Total des charges enregistrées pour la période (Salon: {salon_id_admin})"
        )
    
    with col_k3:
        st.metric(
            label="💚 Bénéfice net",
            value=f"{benefice_net:,.0f} FCFA",
            delta=f"{(benefice_net/ca_total*100):.1f}%" if ca_total > 0 else None,
            delta_color="normal" if benefice_net >= 0 else "inverse",
            help=f"CA - Charges (Salon: {salon_id_admin})"
        )
    
    with col_k4:
        taux_marge = (benefice_net/ca_total*100) if ca_total > 0 else 0
        st.metric(
            label="📈 Taux de marge",
            value=f"{taux_marge:.1f}%",
            help=f"Pourcentage de marge bénéficiaire (Salon: {salon_id_admin})"
        )
    
    st.markdown("---")
    
    # KPIs Secondaires - Activité du salon
    st.markdown("#### 📈 Activité du salon")
    col_k5, col_k6, col_k7, col_k8, col_k9 = st.columns(5)
    
    with col_k5:
        st.metric(
            label="📝 Nombre de charges",
            value=f"{nb_charges}",
            help=f"Total des charges enregistrées (Salon: {salon_id_admin})"
        )
    
    with col_k6:
        st.metric(
            label="🛍️ Commandes",
            value=f"{nb_commandes}",
            help=f"Nombre total de commandes pour la période (Salon: {salon_id_admin})"
        )
    
    with col_k7:
        st.metric(
            label="👥 Clients",
            value=f"{nb_clients_total}",
            help=f"Nombre total de clients du salon (Salon: {salon_id_admin})"
        )
    
    with col_k8:
        if couturier_id_filtre:
            # Afficher le code couturier à la place du nombre d'employés
            st.metric(
                label="🆔 Code",
                value=f"{couturier_obj['code_couturier']}",
                help="Code du couturier"
            )
        else:
            st.metric(
                label="👔 Employés",
                value=f"{nb_employes}",
                help=f"Nombre d'employés du salon (Salon: {salon_id_admin})"
            )
    
    with col_k9:
        st.metric(
            label="✅ Commandes terminées",
            value=f"{commandes_terminees}",
            help="Commandes terminées pour la période"
        )
    
    st.markdown("---")
    
    # ========================================================================
    # VUE DÉTAILLÉE PAR COUTURIER (si un couturier est sélectionné)
    # ========================================================================
    
    if couturier_id_filtre:
        st.markdown(f"#### 👤 Détails - {couturier_obj['prenom']} {couturier_obj['nom']} ({couturier_obj['code_couturier']})")
        
        # Informations du couturier
        col_info1, col_info2, col_info3 = st.columns(3)
        with col_info1:
            st.info(f"📧 **Email :** {couturier_obj.get('email', 'N/A')}")
        with col_info2:
            st.info(f"📱 **Téléphone :** {couturier_obj.get('telephone', 'N/A')}")
        with col_info3:
            st.info(f"👤 **Rôle :** {'👑 Administrateur' if couturier_obj.get('role') == 'admin' else '👤 Employé'}")
        
        st.markdown("---")
        
        # Liste des charges du couturier
        st.markdown("##### 💰 Charges du couturier")
        if charges:
            df_charges_cout = pd.DataFrame(charges)
            if 'date_charge' in df_charges_cout.columns:
                df_charges_cout['date_charge'] = pd.to_datetime(df_charges_cout['date_charge'])
                mask_charges = (
                    (df_charges_cout['date_charge'].dt.date >= date_debut) &
                    (df_charges_cout['date_charge'].dt.date <= date_fin)
                )
                df_charges_cout = df_charges_cout[mask_charges]
            
            if not df_charges_cout.empty:
                st.dataframe(
                    df_charges_cout[['date_charge', 'type', 'categorie', 'description', 'montant']],
                    width='stretch',
                    hide_index=True
                )
            else:
                st.info("Aucune charge pour cette période")
        else:
            st.info("Aucune charge enregistrée")
        
        st.markdown("---")

        # Liste des commandes du couturier
        st.markdown("##### 📦 Commandes du couturier")
        if commandes:
            df_cmd_cout = pd.DataFrame(commandes)
            if 'date_creation' in df_cmd_cout.columns:
                df_cmd_cout['date_creation'] = pd.to_datetime(df_cmd_cout['date_creation'])
                mask_cmd = (
                    (df_cmd_cout['date_creation'].dt.date >= date_debut) &
                    (df_cmd_cout['date_creation'].dt.date <= date_fin)
                )
                df_cmd_cout = df_cmd_cout[mask_cmd]
            
            if not df_cmd_cout.empty:
                colonnes_afficher = ['id', 'modele', 'client_prenom', 'client_nom', 'prix_total', 'avance', 'reste', 'statut', 'date_creation']
                colonnes_existantes = [col for col in colonnes_afficher if col in df_cmd_cout.columns]
                st.dataframe(
                    df_cmd_cout[colonnes_existantes],
                    width='stretch',
                    hide_index=True
                )
            else:
                st.info("Aucune commande pour cette période")
        else:
            st.info("Aucune commande enregistrée")

        # --------------------------------------------------------------------
        # MODÈLES RÉALISÉS PAR LE COUTURIER (tableaux et figures)
        # --------------------------------------------------------------------
        st.markdown("---")
        st.markdown("##### 👗 Modèles réalisés sur la période")

        modeles_cout = commande_model.lister_modeles_realises(
            couturier_id=couturier_id_filtre,
            tous_les_couturiers=False,
            salon_id=salon_id_admin,
            date_debut=date_debut_dt,
            date_fin=date_fin_dt,
        )

        if modeles_cout:
            df_modeles = pd.DataFrame(modeles_cout)
            df_modeles['CA (FCFA)'] = df_modeles['ca_total'].apply(lambda x: f"{x:,.0f}")
            total_ca_modeles = df_modeles['ca_total'].sum()
            total_ordres_modeles = df_modeles['nb_commandes'].sum()

            col_m1, col_m2 = st.columns(2)
            with col_m1:
                st.metric("📦 Total commandes", total_ordres_modeles)
            with col_m2:
                st.metric("💰 Chiffre d'affaires", f"{total_ca_modeles:,.0f} FCFA")

            st.markdown("**Répartition par modèle**")
            df_display_modeles = df_modeles[['modele', 'categorie', 'sexe', 'nb_commandes', 'CA (FCFA)']].copy()
            df_display_modeles.columns = ['Modèle', 'Catégorie', 'Sexe', 'Nombre', 'CA (FCFA)']
            st.dataframe(df_display_modeles, hide_index=True, width='stretch')

            col_g1, col_g2 = st.columns(2)
            with col_g1:
                fig_bar = px.bar(
                    df_modeles.head(15),
                    x='modele',
                    y='nb_commandes',
                    title="Modèles les plus vendus",
                    labels={'modele': 'Modèle', 'nb_commandes': 'Nombre'}
                )
                fig_bar.update_layout(xaxis_tickangle=-45, height=400)
                st.plotly_chart(fig_bar, use_container_width=True)
            with col_g2:
                fig_pie = px.pie(
                    df_modeles,
                    values='ca_total',
                    names='modele',
                    title="Répartition du CA par modèle",
                    hole=0.4
                )
                st.plotly_chart(fig_pie, use_container_width=True)

            # Galerie photos
            from views.calendrier_view import _afficher_galerie_photos
            st.markdown("---")
            st.markdown("##### 📷 Galerie photos")
            _afficher_galerie_photos(
                commande_model,
                couturier_id_filtre,
                salon_id_admin,
                date_debut_dt,
                date_fin_dt,
                key_prefix="admin_vue360",
            )
        else:
            st.info("Aucun modèle réalisé pour cette période.")

        st.markdown("---")
    
    # ========================================================================
    # VUE D'ENSEMBLE DE TOUS LES COUTURIERS (si "Tous" est sélectionné)
    # ========================================================================
    
    if not couturier_id_filtre:
        st.markdown("#### 👥 Vue d'ensemble de tous les couturiers du salon")
        
        # Créer un tableau récapitulatif de tous les couturiers
        stats_couturiers = []
        for couturier in tous_couturiers:
            cout_id = couturier['id']
            
            # Charges du couturier (avec salon_id pour sécurité multi-tenant)
            charges_cout = charges_model.total_charges(
                couturier_id=cout_id,
                date_debut=date_debut_dt,
                date_fin=date_fin_dt,
                tous_les_couturiers=False,
                salon_id=salon_id_admin
            )
            
            # CA du couturier
            cmd_cout = commande_model.lister_commandes(cout_id, tous_les_couturiers=False, salon_id=salon_id_admin)
            ca_cout = 0
            nb_cmd_cout = 0
            total_avance_cout = 0
            total_encaisse_cout = 0
            nb_clients_cout = 0
            if cmd_cout:
                df_cmd_cout = pd.DataFrame(cmd_cout)
                if 'date_creation' in df_cmd_cout.columns:
                    df_cmd_cout['date_creation'] = pd.to_datetime(df_cmd_cout['date_creation'])
                    mask_cout = (
                        (df_cmd_cout['date_creation'].dt.date >= date_debut) &
                        (df_cmd_cout['date_creation'].dt.date <= date_fin)
                    )
                    df_cmd_cout = df_cmd_cout[mask_cout]
                    if not df_cmd_cout.empty:
                        if 'prix_total' in df_cmd_cout.columns:
                            ca_cout = df_cmd_cout['prix_total'].sum()
                        nb_cmd_cout = len(df_cmd_cout)
                        if 'avance' in df_cmd_cout.columns:
                            total_avance_cout = df_cmd_cout['avance'].sum()
                        if 'prix_total' in df_cmd_cout.columns and 'reste' in df_cmd_cout.columns:
                            total_encaisse_cout = df_cmd_cout['prix_total'].sum() - df_cmd_cout['reste'].sum()
                        # Estimation du nombre de clients distincts à partir du nom/prénom client
                        if 'client_prenom' in df_cmd_cout.columns and 'client_nom' in df_cmd_cout.columns:
                            df_cmd_cout['client_full'] = df_cmd_cout['client_prenom'].fillna('') + " " + df_cmd_cout['client_nom'].fillna('')
                            nb_clients_cout = df_cmd_cout['client_full'].nunique()
            
            benefice_cout = ca_cout - charges_cout
            
            stats_couturiers.append({
                'Code': couturier['code_couturier'],
                'Nom': f"{couturier['prenom']} {couturier['nom']}",
                'Rôle': '👑 Admin' if couturier.get('role') == 'admin' else '👤 Employé',
                'CA (FCFA)': ca_cout,
                'Charges (FCFA)': charges_cout,
                'Bénéfice (FCFA)': benefice_cout,
                'Commandes': nb_cmd_cout,
                'Avances (FCFA)': total_avance_cout,
                'Encaissé (FCFA)': total_encaisse_cout,
                'Clients distincts': nb_clients_cout
            })
        
        if stats_couturiers:
            df_couturiers = pd.DataFrame(stats_couturiers)
            df_couturiers = df_couturiers.sort_values('Bénéfice (FCFA)', ascending=False)
            
            # Tableau récapitulatif global
            st.markdown("##### 📋 Tableau récapitulatif des couturiers")
            st.dataframe(
                df_couturiers,
                width='stretch',
                hide_index=True
            )
            
            st.markdown("---")

            # ====================================================================
            # NOUVELLE SECTION : COMPARATIF DÉTAILLÉ PAR COUTURIER
            # ====================================================================
            st.markdown("#### 📊 Comparatif des couturiers (charges, commandes, avances, encaissé, clients)")

            # 1. Comparatif des charges par couturier
            st.markdown("##### 💸 Charges par couturier")
            col_ch_fig, col_ch_tab = st.columns([2, 1])
            with col_ch_fig:
                fig_charges = px.bar(
                    df_couturiers,
                    x='Nom',
                    y='Charges (FCFA)',
                    color='Charges (FCFA)',
                    color_continuous_scale='Oranges',
                    title="Charges totales par couturier",
                    labels={'Nom': 'Couturier', 'Charges (FCFA)': 'Charges (FCFA)'}
                )
                fig_charges.update_layout(xaxis_tickangle=-45, height=400, showlegend=False)
                st.plotly_chart(fig_charges, use_container_width=True)
            with col_ch_tab:
                st.dataframe(
                    df_couturiers[['Code', 'Nom', 'Charges (FCFA)']],
                    width='stretch',
                    hide_index=True
                )

            st.markdown("---")

            # 2. Comparatif du chiffre d'affaires / commandes
            st.markdown("##### 💰 Chiffre d'affaires et nombre de commandes")
            col_ca_fig, col_ca_tab = st.columns([2, 1])
            with col_ca_fig:
                fig_ca = go.Figure()
                fig_ca.add_trace(go.Bar(
                    name="CA (FCFA)",
                    x=df_couturiers['Nom'],
                    y=df_couturiers['CA (FCFA)'],
                    marker_color='#2ECC71'
                ))
                fig_ca.add_trace(go.Bar(
                    name="Commandes",
                    x=df_couturiers['Nom'],
                    y=df_couturiers['Commandes'],
                    marker_color='#3498DB',
                    yaxis='y2'
                ))
                fig_ca.update_layout(
                    title="CA et nombre de commandes par couturier",
                    xaxis_title="Couturier",
                    yaxis_title="CA (FCFA)",
                    yaxis2=dict(
                        title="Commandes",
                        overlaying='y',
                        side='right'
                    ),
                    barmode='group',
                    xaxis_tickangle=-45,
                    height=450
                )
                st.plotly_chart(fig_ca, use_container_width=True)
            with col_ca_tab:
                st.dataframe(
                    df_couturiers[['Code', 'Nom', 'CA (FCFA)', 'Commandes']],
                    width='stretch',
                    hide_index=True
                )

            st.markdown("---")

            # 3. Comparatif avances / encaissé
            st.markdown("##### 💵 Avances et montants encaissés")
            col_av_fig, col_av_tab = st.columns([2, 1])
            with col_av_fig:
                fig_av = go.Figure()
                fig_av.add_trace(go.Bar(
                    name="Avances",
                    x=df_couturiers['Nom'],
                    y=df_couturiers['Avances (FCFA)'],
                    marker_color='#9B59B6'
                ))
                fig_av.add_trace(go.Bar(
                    name="Encaissé",
                    x=df_couturiers['Nom'],
                    y=df_couturiers['Encaissé (FCFA)'],
                    marker_color='#1ABC9C'
                ))
                fig_av.update_layout(
                    title="Comparaison des avances et des montants encaissés par couturier",
                    xaxis_title="Couturier",
                    yaxis_title="Montants (FCFA)",
                    barmode='group',
                    xaxis_tickangle=-45,
                    height=450
                )
                st.plotly_chart(fig_av, use_container_width=True)
            with col_av_tab:
                st.dataframe(
                    df_couturiers[['Code', 'Nom', 'Avances (FCFA)', 'Encaissé (FCFA)']],
                    width='stretch',
                    hide_index=True
                )

            st.markdown("---")

            # 4. Comparatif des clients
            st.markdown("##### 👥 Nombre de clients par couturier")
            col_cl_fig, col_cl_tab = st.columns([2, 1])
            with col_cl_fig:
                fig_clients = px.bar(
                    df_couturiers,
                    x='Nom',
                    y='Clients distincts',
                    color='Clients distincts',
                    color_continuous_scale='Blues',
                    title="Nombre de clients distincts par couturier (sur la période)",
                    labels={'Nom': 'Couturier', 'Clients distincts': 'Clients distincts'}
                )
                fig_clients.update_layout(xaxis_tickangle=-45, height=400, showlegend=False)
                st.plotly_chart(fig_clients, use_container_width=True)
            with col_cl_tab:
                st.dataframe(
                    df_couturiers[['Code', 'Nom', 'Clients distincts']],
                    width='stretch',
                    hide_index=True
                )

            st.markdown("---")


def afficher_toutes_charges(charges_model: ChargesModel, salon_id_admin: str):
    """Affiche toutes les charges du salon de l'admin avec analyses complètes"""
    
    st.markdown("### 💰 Toutes les charges de l'entreprise")
    st.markdown("---")
    
    # Récupérer tous les couturiers du salon pour le filtre
    from models.database import CouturierModel
    couturier_model = CouturierModel(charges_model.db)
    tous_couturiers = couturier_model.lister_tous_couturiers(salon_id=salon_id_admin)
    
    # Filtres
    col_f1, col_f2, col_f3, col_f4 = st.columns(4)
    
    with col_f1:
        date_debut_filter = st.date_input(
            "Date de début",
            value=datetime.now().date() - timedelta(days=30),
            key="admin_charges_debut"
        )
    
    with col_f2:
        date_fin_filter = st.date_input(
            "Date de fin",
            value=datetime.now().date(),
            key="admin_charges_fin"
        )
    
    with col_f3:
        type_filter = st.multiselect(
            "Filtrer par type",
            options=["Fixe", "Ponctuelle", "Commande", "Salaire"],
            default=["Fixe", "Ponctuelle", "Commande", "Salaire"],
            key="admin_charges_type"
        )
    
    with col_f4:
        # Sélecteur de couturier
        options_couturiers = ["👥 Tous les couturiers"] + [
            f"{c['code_couturier']} - {c['prenom']} {c['nom']}"
            for c in tous_couturiers
        ]
        couturier_selectionne = st.selectbox(
            "Filtrer par couturier",
            options=options_couturiers,
            key="admin_charges_couturier"
        )
    
    st.markdown("---")
    
    # Déterminer le couturier_id sélectionné
    couturier_id_filtre = None
    if couturier_selectionne and couturier_selectionne != "👥 Tous les couturiers":
        code_selectionne = couturier_selectionne.split(" - ")[0]
        couturier_selectionne_obj = next(
            (c for c in tous_couturiers if c['code_couturier'] == code_selectionne),
            None
        )
        if couturier_selectionne_obj:
            couturier_id_filtre = couturier_selectionne_obj['id']
    
    # Récupérer les charges (filtrées par couturier si sélectionné)
    charges = charges_model.lister_charges(
        couturier_id=couturier_id_filtre,
        limit=10000,
        tous_les_couturiers=(couturier_id_filtre is None),
        salon_id=salon_id_admin
    )
    
    if not charges:
        st.info("💭 Aucune charge enregistrée dans l'entreprise")
        return
    
    # Convertir en DataFrame
    df = pd.DataFrame(charges)
    df['date_charge'] = pd.to_datetime(df['date_charge'])
    
    # Filtrer
    mask = (
        (df['date_charge'].dt.date >= date_debut_filter) &
        (df['date_charge'].dt.date <= date_fin_filter) &
        (df['type'].isin(type_filter))
    )
    
    df_filtered = df[mask].copy()
    
    if df_filtered.empty:
        st.warning("⚠️ Aucune charge ne correspond aux filtres sélectionnés")
        return

    # Préparer le nom de l'employé (utilisé pour les tableaux + exports + PDF)
    if 'couturier_nom' in df_filtered.columns and 'couturier_prenom' in df_filtered.columns:
        df_filtered['employe_nom'] = df_filtered.apply(
            lambda row: f"{row.get('couturier_prenom', '')} {row.get('couturier_nom', '')}".strip() or f"ID: {row.get('couturier_id', 'N/A')}",
            axis=1
        )
    else:
        if 'couturier_id' in df_filtered.columns:
            df_filtered['employe_nom'] = df_filtered['couturier_id'].astype(str)
        else:
            df_filtered['employe_nom'] = 'N/A'
    
    # Statistiques
    st.markdown("#### 📊 Statistiques globales")
    
    col_s1, col_s2, col_s3, col_s4 = st.columns(4)
    
    with col_s1:
        total = df_filtered['montant'].sum()
        st.metric("💰 Total", f"{total:,.0f} FCFA")
    
    with col_s2:
        nb = len(df_filtered)
        st.metric("📝 Nombre", f"{nb}")
    
    with col_s3:
        moy = df_filtered['montant'].mean()
        st.metric("📈 Moyenne", f"{moy:,.0f} FCFA")
    
    with col_s4:
        nb_jours = (date_fin_filter - date_debut_filter).days + 1
        moy_j = total / nb_jours if nb_jours > 0 else 0
        st.metric("📅 Moy/jour", f"{moy_j:,.0f} FCFA")
    
    st.markdown("---")
    
    # ========================================================================
    # GRAPHIQUE 3 : RÉPARTITION GLOBALE DE TOUTES LES CHARGES
    # ========================================================================
    
    st.markdown("#### 📈 Répartition globale de toutes les charges")
    
    # Par type
    df_type_global = df_filtered.groupby('type')['montant'].sum().reset_index()
    
    col_g1, col_g2 = st.columns(2)
    
    with col_g1:
        # Graphique en camembert par type
        fig_pie_type = px.pie(
            df_type_global,
            values='montant',
            names='type',
            title='Répartition par type (montant)',
            hole=0.4
        )
        st.plotly_chart(fig_pie_type, use_container_width=True)
    
    with col_g2:
        # Graphique en barres par type
        fig_bar_type = px.bar(
            df_type_global,
            x='type',
            y='montant',
            title='Montant total par type',
            labels={'type': 'Type', 'montant': 'Montant (FCFA)'},
            color='montant',
            color_continuous_scale='Oranges',
            text='montant'
        )
        fig_bar_type.update_traces(texttemplate='%{text:,.0f}', textposition='outside')
        st.plotly_chart(fig_bar_type, use_container_width=True)
    
    st.markdown("---")
    
    # ========================================================================
    # DÉTAIL DES CHARGES PAR EMPLOYÉ
    # ========================================================================
    
    st.markdown("#### 📄 Détails des charges par employé")
    
    # Grouper par employé
    employes_uniques = df_filtered['employe_nom'].unique()
    
    for employe in sorted(employes_uniques):
        df_emp = df_filtered[df_filtered['employe_nom'] == employe].copy()
        total_emp = df_emp['montant'].sum()
        nb_emp = len(df_emp)
        
        with st.expander(f"👤 {employe} - {nb_emp} charge(s) - Total: {total_emp:,.0f} FCFA", expanded=False):
            df_emp_display = df_emp.copy()
            df_emp_display['date_charge'] = df_emp_display['date_charge'].dt.strftime('%d/%m/%Y')
            df_emp_display['montant'] = df_emp_display['montant'].apply(lambda x: f"{x:,.0f} FCFA")
            
            colonnes_afficher = ['date_charge', 'type', 'categorie', 'description', 'montant', 'reference']
            colonnes_existantes = [col for col in colonnes_afficher if col in df_emp_display.columns]
            
            df_emp_display = df_emp_display[colonnes_existantes]
            df_emp_display.columns = ['Date', 'Type', 'Catégorie', 'Description', 'Montant', 'Référence']

            st.dataframe(
                df_emp_display,
                width='stretch',
                hide_index=True
            )

            # Bouton de téléchargement PDF pour ce tableau employé
            pdf_emp = _generer_pdf_table_charges(
                titre=f"Charges de {employe}",
                sous_titre=f"Période du {date_debut_filter.strftime('%d/%m/%Y')} au {date_fin_filter.strftime('%d/%m/%Y')}",
                df_table=df_emp[['date_charge', 'type', 'categorie', 'description', 'montant']]
            )
            if pdf_emp:
                st.download_button(
                    label="📄 Télécharger ce tableau en PDF",
                    data=pdf_emp["content"],
                    file_name=pdf_emp["filename"],
                    mime="application/pdf",
                    width='stretch',
                )
    
    st.markdown("---")
    
    # Export
    st.markdown("#### 📥 Exporter les données")
    
    df_display = df_filtered.copy()
    df_display['date_charge'] = df_display['date_charge'].dt.strftime('%d/%m/%Y')
    df_display['montant'] = df_display['montant'].apply(lambda x: f"{x:,.0f} FCFA")
    
    colonnes_afficher = ['date_charge', 'employe_nom', 'type', 'categorie', 'description', 'montant', 'reference']
    colonnes_existantes = [col for col in colonnes_afficher if col in df_display.columns]
    
    df_display = df_display[colonnes_existantes]
    df_display.columns = ['Date', 'Employé', 'Type', 'Catégorie', 'Description', 'Montant', 'Référence']

    # Tableau global (affiché) + export CSV + PDF
    st.dataframe(
        df_display,
        width='stretch',
        hide_index=True
    )

    csv = df_display.to_csv(index=False, encoding='utf-8-sig')
    col_exp1, col_exp2 = st.columns(2)

    with col_exp1:
        st.download_button(
            label="📄 Télécharger CSV",
            data=csv,
            file_name=f"toutes_charges_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
            mime="text/csv",
            width='stretch'
        )

    with col_exp2:
        pdf_global = _generer_pdf_table_charges(
            titre="Toutes les charges de l'entreprise",
            sous_titre=f"Période du {date_debut_filter.strftime('%d/%m/%Y')} au {date_fin_filter.strftime('%d/%m/%Y')}",
            df_table=df_filtered[['date_charge', 'employe_nom', 'type', 'categorie', 'description', 'montant']]
        )
        if pdf_global:
            st.download_button(
                label="📄 Télécharger le tableau global en PDF",
                data=pdf_global["content"],
                file_name=pdf_global["filename"],
                mime="application/pdf",
                width='stretch'
            )


def _generer_pdf_table_charges(titre: str, sous_titre: str, df_table: pd.DataFrame) -> Optional[Dict[str, bytes]]:
    """
    Génère un PDF simple contenant un tableau de charges (global ou par employé).
    Retourne un dict {filename, content} ou None en cas d'erreur.
    """
    try:
        if df_table is None or df_table.empty:
            return None

        # Normaliser les données
        df_pdf = df_table.copy()
        df_pdf['date_charge'] = pd.to_datetime(df_pdf['date_charge']).dt.strftime('%d/%m/%Y')
        df_pdf['montant'] = df_pdf['montant'].astype(float)

        # Préparer les données du tableau
        colonnes = list(df_pdf.columns)
        headers = [col.replace('_', ' ').title() for col in colonnes]
        data = [headers]
        total_montant = 0.0
        for _, row in df_pdf.iterrows():
            ligne = []
            for col in colonnes:
                val = row[col]
                if col == 'montant':
                    montant_val = float(val)
                    total_montant += montant_val
                    ligne.append(f"{montant_val:,.0f} FCFA")
                else:
                    ligne.append(str(val))
            data.append(ligne)

        # Ajouter une ligne de total à la fin
        if 'montant' in colonnes:
            idx_montant = colonnes.index('montant')
            total_row = [""] * len(colonnes)
            total_row[idx_montant] = f"{total_montant:,.0f} FCFA"
            if len(colonnes) > 1:
                total_row[0] = "TOTAL"
            data.append(total_row)

        # Fichier temporaire
        filename = f"Charges_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
        temp_dir = tempfile.gettempdir()
        filepath = os.path.join(temp_dir, filename)

        doc = SimpleDocTemplate(
            filepath,
            pagesize=A4,
            rightMargin=1.5 * cm,
            leftMargin=1.5 * cm,
            topMargin=1.5 * cm,
            bottomMargin=1.5 * cm,
        )

        elements = []
        styles = getSampleStyleSheet()

        title_style = ParagraphStyle(
            'TitreCharges',
            parent=styles['Heading1'],
            fontSize=18,
            textColor=colors.HexColor('#2C3E50'),
            alignment=1,
            spaceAfter=12
        )

        subtitle_style = ParagraphStyle(
            'SousTitreCharges',
            parent=styles['Heading2'],
            fontSize=11,
            textColor=colors.HexColor('#7F8C8D'),
            alignment=1,
            spaceAfter=18
        )

        # Récupérer le logo du salon (depuis la BDD) pour l'en-tête du PDF
        salon_id = None
        try:
            if st.session_state.get('couturier_data'):
                from utils.role_utils import obtenir_salon_id
                salon_id = obtenir_salon_id(st.session_state.couturier_data)
        except Exception:
            pass

        logo_img = None
        if salon_id and st.session_state.get('db_connection'):
            try:
                logo_model = AppLogoModel(st.session_state.db_connection)
                logo_data = logo_model.recuperer_logo(salon_id)
                if logo_data and logo_data.get('logo_data'):
                    logo_bytes = logo_data['logo_data']
                    logo_reader = ImageReader(io.BytesIO(logo_bytes))
                    logo_img = Image(logo_reader, width=3.0 * cm, height=3.0 * cm)
            except Exception as e:
                print(f"Erreur récupération logo pour PDF charges: {e}")

        # Préparer les lignes de pied de page (informations du salon)
        footer_lines = None
        try:
            if salon_id and st.session_state.get('db_connection'):
                salon_model = SalonModel(st.session_state.db_connection)
                salon = salon_model.obtenir_salon_by_id(salon_id)
                if salon:
                    nom = salon.get('nom_salon') or salon_id
                    quartier = salon.get('quartier') or ''
                    responsable = salon.get('responsable') or ''
                    telephone = salon.get('telephone') or ''
                    email = salon.get('email') or ''

                    line1 = f"{nom} ({salon_id})"
                    parts = []
                    if quartier:
                        parts.append(quartier)
                    if responsable:
                        parts.append(f"Resp.: {responsable}")
                    if telephone:
                        parts.append(f"Tél: {telephone}")
                    if email:
                        parts.append(f"Email: {email}")
                    line2 = " | ".join(parts) if parts else ""

                    footer_lines = [line1]
                    if line2:
                        footer_lines.append(line2)
        except Exception as e:
            print(f"Erreur construction pied de page PDF charges: {e}")

        if logo_img:
            try:
                logo_table = Table([[logo_img]], colWidths=[15 * cm])
                logo_table.setStyle(TableStyle([
                    ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                    ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                ]))
                elements.append(logo_table)
                elements.append(Spacer(1, 0.4 * cm))
            except Exception as e:
                print(f"Erreur ajout logo dans PDF charges: {e}")

        elements.append(Paragraph(titre, title_style))
        elements.append(Paragraph(sous_titre, subtitle_style))

        table = Table(data, repeatRows=1)
        table.setStyle(TableStyle([
            ('GRID', (0, 0), (-1, -1), 0.4, colors.grey),
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#3498DB')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 9),
            ('FONTSIZE', (0, 1), (-1, -2), 8),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ]))
        # Mettre en évidence la dernière ligne (total)
        if len(data) > 1:
            table.setStyle(TableStyle([
                ('BACKGROUND', (0, len(data) - 1), (-1, len(data) - 1), colors.HexColor('#ECF0F1')),
                ('FONTNAME', (0, len(data) - 1), (-1, len(data) - 1), 'Helvetica-Bold'),
            ]))

        elements.append(table)

        def dessiner_footer(canvas_obj, doc_obj):
            if not footer_lines:
                return
            try:
                canvas_obj.saveState()
                page_width, _ = doc_obj.pagesize
                footer_height = 2 * cm
                # Bande de fond sur toute la largeur en bas de page
                canvas_obj.setFillColor(colors.HexColor('#857CF6'))
                canvas_obj.rect(0, 0, page_width, footer_height, fill=1, stroke=0)

                # Texte du salon par-dessus la bande
                font_name = "Helvetica"
                font_size = 8
                canvas_obj.setFont(font_name, font_size)
                canvas_obj.setFillColor(colors.white)
                base_y = 0.6 * cm
                for idx, line in enumerate(footer_lines):
                    text = str(line)
                    text_width = canvas_obj.stringWidth(text, font_name, font_size)
                    x = (page_width - text_width) / 2
                    y = base_y + idx * 0.35 * cm
                    if y < footer_height - 0.2 * cm:
                        canvas_obj.drawString(x, y, text)
                canvas_obj.restoreState()
            except Exception as e:
                print(f"Erreur dessin pied de page PDF charges: {e}")

        doc.build(
            elements,
            onFirstPage=dessiner_footer,
            onLaterPages=dessiner_footer
        )

        with open(filepath, "rb") as f:
            content = f.read()

        try:
            os.remove(filepath)
        except Exception:
            pass

        return {"filename": filename, "content": content}
    except Exception as e:
        print(f"Erreur génération PDF tableau charges: {e}")
        return None


def afficher_calcul_impots_admin(charges_model: ChargesModel, commande_model: CommandeModel):
    """Affiche le calcul d'impôts pour toutes les charges de l'entreprise"""
    
    st.markdown("### 🧮 Calcul d'impôts - Vue globale")
    st.info("👑 **Vue administrateur** : Calcul des impôts sur toutes les activités de l'entreprise")
    st.markdown("---")
    
    # Sélection de période
    col1, col2 = st.columns(2)
    
    with col1:
        date_debut = st.date_input(
            "Date de début",
            value=datetime.now().replace(day=1).date(),
            key="admin_impots_debut"
        )
    
    with col2:
        date_fin = st.date_input(
            "Date de fin",
            value=datetime.now().date(),
            key="admin_impots_fin"
        )
    
    st.markdown("---")
    
    # Récupérer le salon_id de l'admin pour le filtrage multi-tenant
    salon_id_admin = None
    try:
        if st.session_state.get('couturier_data'):
            salon_id_admin = obtenir_salon_id(st.session_state.couturier_data)
    except:
        pass
    
    if not salon_id_admin:
        st.error("❌ Impossible de déterminer votre salon. Veuillez vous reconnecter.")
        return
    
    # Calcul du CA sur la période (toutes les commandes du salon)
    commandes = commande_model.lister_commandes(None, tous_les_couturiers=True, salon_id=salon_id_admin)
    ca_total = 0
    
    if commandes:
        df_cmd = pd.DataFrame(commandes)
        if 'date_creation' in df_cmd.columns:
            df_cmd['date_creation'] = pd.to_datetime(df_cmd['date_creation'])
            mask_cmd = (
                (df_cmd['date_creation'].dt.date >= date_debut) &
                (df_cmd['date_creation'].dt.date <= date_fin)
            )
            df_cmd = df_cmd[mask_cmd]
            ca_total = df_cmd['prix_total'].sum() if 'prix_total' in df_cmd.columns else 0
    
    # Permettre la modification manuelle du CA
    ca_manuel = st.number_input(
        "Chiffre d'affaires (FCFA)",
        min_value=0.0,
        value=float(ca_total),
        step=100000.0,
        key="admin_ca_manuel"
    )
    
    # Calcul du total des charges (toutes les charges de tous les employés du salon)
    date_debut_dt = datetime.combine(date_debut, datetime.min.time())
    date_fin_dt = datetime.combine(date_fin, datetime.max.time())
    
    total_charges = charges_model.total_charges(
        couturier_id=None,
        date_debut=date_debut_dt,
        date_fin=date_fin_dt,
        tous_les_couturiers=True,
        salon_id=salon_id_admin
    )
    
    # Affichage des métriques principales
    col_m1, col_m2 = st.columns(2)
    
    with col_m1:
        st.metric("💵 Chiffre d'affaires", f"{ca_manuel:,.0f} FCFA")
    
    with col_m2:
        st.metric("💸 Total des charges", f"{total_charges:,.0f} FCFA")
    
    st.markdown("---")
    
    # Calcul de l'impôt selon les tranches
    impot = 0
    for tranche in TRANCHES_IMPOTS:
        if tranche['min'] <= ca_manuel <= tranche['max']:
            impot = tranche['impot']
            break
    
    # Si le CA dépasse la dernière tranche, utiliser la dernière tranche
    if ca_manuel > TRANCHES_IMPOTS[-1]['max']:
        impot = TRANCHES_IMPOTS[-1]['impot']
    
    # Affichage du barème
    st.markdown("#### 📋 Barème d'impôts")
    st.info(
        "**Barème:** 0-500.000 → 5.000 FCFA | "
        "500.000-1M → 75.000 FCFA | "
        "1M-1.5M → 100.000 FCFA | "
        "1.5M-2M → 125.000 FCFA | "
        "2M-2.5M → 150.000 FCFA | "
        "2.5M-5M → 375.000 FCFA | "
        "5M-10M → 750.000 FCFA | "
        "10M-20M → 1.250.000 FCFA | "
        "20M-30M → 2.500.000 FCFA | "
        "30M-50M → 5.000.000 FCFA"
    )
    
    st.markdown("---")
    
    # Résultats finaux
    col_r1, col_r2 = st.columns(2)
    
    with col_r1:
        st.metric("🏦 Impôt à payer", f"{impot:,.0f} FCFA")
    
    benefice_net = ca_manuel - total_charges - impot
    
    with col_r2:
        st.metric(
            "💚 Bénéfice net",
            f"{benefice_net:,.0f} FCFA",
            delta=f"{(benefice_net/ca_manuel*100):.1f}%" if ca_manuel > 0 else None
        )
    
    st.markdown("---")
    
    # Graphique de synthèse
    st.markdown("#### 📊 Synthèse financière")
    
    fig_synthese = go.Figure()
    
    fig_synthese.add_trace(go.Bar(
        name='Chiffre d\'affaires',
        x=['Synthèse'],
        y=[ca_manuel],
        marker_color='#2ECC71'
    ))
    
    fig_synthese.add_trace(go.Bar(
        name='Charges',
        x=['Synthèse'],
        y=[total_charges],
        marker_color='#F39C12'
    ))
    
    fig_synthese.add_trace(go.Bar(
        name='Impôt',
        x=['Synthèse'],
        y=[impot],
        marker_color='#F39C12'
    ))
    
    fig_synthese.add_trace(go.Bar(
        name='Bénéfice net',
        x=['Synthèse'],
        y=[benefice_net],
        marker_color='#3498DB'
    ))
    
    fig_synthese.update_layout(
        title='Répartition financière (CA, Charges, Impôt, Bénéfice)',
        barmode='group',
        height=400
    )
    
    st.plotly_chart(fig_synthese, use_container_width=True)
    
    st.markdown("---")
    
    # Détail des charges pour la période (filtrées par salon_id)
    st.markdown("#### 📝 Détail des charges de la période")
    
    charges_list = charges_model.lister_charges(
        couturier_id=None,
        limit=10000,
        tous_les_couturiers=True,
        salon_id=salon_id_admin
    )
    
    df_charges = pd.DataFrame(charges_list) if charges_list else pd.DataFrame()

    if not df_charges.empty and 'date_charge' in df_charges.columns:
        df_charges['date_charge'] = pd.to_datetime(df_charges['date_charge'])
        mask = (
            (df_charges['date_charge'].dt.date >= date_debut) &
            (df_charges['date_charge'].dt.date <= date_fin)
        )
        df_charges = df_charges[mask]

    if not df_charges.empty:
        # Préparer l'affichage
        df_display = df_charges[['date_charge', 'type', 'categorie', 'description', 'montant', 'reference']].copy()
        df_display['date_charge'] = df_display['date_charge'].dt.strftime('%d/%m/%Y')
        df_display['montant'] = df_display['montant'].apply(lambda x: f"{x:,.0f} FCFA")
        df_display.columns = ['Date', 'Type', 'Catégorie', 'Description', 'Montant', 'Référence']
        
        st.dataframe(
            df_display,
            width='stretch',
            hide_index=True,
            height=300
        )

        # Bouton de téléchargement PDF du relevé d'impôts avec tableau des charges
        pdf_data = _generer_pdf_impots(
            date_debut,
            date_fin,
            ca_manuel,
            total_charges,
            impot,
            benefice_net,
            df_charges
        )

        st.markdown("#### 📥 Export PDF du relevé d'impôts")
        if pdf_data:
            st.download_button(
                label="📄 Télécharger le relevé d'impôts (PDF)",
                data=pdf_data["content"],
                file_name=pdf_data["filename"],
                mime="application/pdf",
                width='stretch'
            )
    else:
        st.info("Aucune charge enregistrée pour cette période.")


def afficher_gestion_utilisateurs(couturier_model: CouturierModel, admin_data: Dict):
    """Affiche la gestion complète des utilisateurs (création, modification, suppression)"""
    
    st.markdown("### 👥 Gestion des utilisateurs")
    st.markdown("---")
    
    # Sous-onglets pour création, liste, gestion des mots de passe et gestion du logo
    sub_tab1, sub_tab2, sub_tab3, sub_tab4 = st.tabs([
        "➕ Créer un utilisateur", 
        "📋 Liste des utilisateurs",
        "🔐 Gestion des mots de passe",
        "🖼️ Gestion du logo"
    ])
    
    with sub_tab1:
        afficher_formulaire_creation_utilisateur(couturier_model, admin_data)
    
    with sub_tab2:
        afficher_liste_utilisateurs(couturier_model, admin_data)
    
    with sub_tab3:
        afficher_gestion_mots_de_passe(couturier_model, admin_data)
    
    with sub_tab4:
        afficher_gestion_logo(admin_data)


def afficher_formulaire_creation_utilisateur(couturier_model: CouturierModel, admin_data: Dict):
    """Formulaire de création d'un nouvel utilisateur (multi-tenant)"""
    
    st.markdown("#### ➕ Créer un nouvel utilisateur")
    st.info("Créez un nouveau compte utilisateur avec attribution de rôle. L'utilisateur sera automatiquement assigné à votre salon.")
    st.markdown("---")
    
    with st.form("form_creer_utilisateur", clear_on_submit=True):
        col1, col2 = st.columns(2)
        
        with col1:
            code_couturier = st.text_input(
                "Code de connexion *",
                placeholder="Ex: COUT002, EMP001",
                help="Code unique pour se connecter (ne peut pas être modifié après création)"
            )
            
            nom = st.text_input(
                "Nom *",
                placeholder="Ex: DUPONT",
                help="Nom de famille"
            )
            
            prenom = st.text_input(
                "Prénom *",
                placeholder="Ex: Jean",
                help="Prénom"
            )
            
            role = st.selectbox(
                "Rôle *",
                options=["employe", "admin"],
                format_func=lambda x: "👤 Employé" if x == "employe" else "👑 Administrateur",
                help="Rôle de l'utilisateur dans le système"
            )
        
        with col2:
            password = st.text_input(
                "Mot de passe *",
                type="password",
                help="Mot de passe de connexion (minimum 4 caractères)"
            )
            
            password_confirm = st.text_input(
                "Confirmer le mot de passe *",
                type="password",
                help="Répétez le mot de passe"
            )
            
            email = st.text_input(
                "Email (optionnel)",
                placeholder="exemple@email.com",
                help="Adresse email de l'utilisateur"
            )
            
            telephone = st.text_input(
                "Téléphone (optionnel)",
                placeholder="+237 6XX XXX XXX",
                help="Numéro de téléphone"
            )
        
        st.markdown("---")
        
        submit = st.form_submit_button(
            "💾 Créer l'utilisateur",
            type="primary",
            width='stretch'
        )
        
        if submit:
            # Validations
            erreurs = []
            
            if not code_couturier or len(code_couturier.strip()) < 3:
                erreurs.append("Le code de connexion doit contenir au moins 3 caractères")
            
            if not nom or len(nom.strip()) < 2:
                erreurs.append("Le nom doit contenir au moins 2 caractères")
            
            if not prenom or len(prenom.strip()) < 2:
                erreurs.append("Le prénom doit contenir au moins 2 caractères")
            
            if not password or len(password) < 4:
                erreurs.append("Le mot de passe doit contenir au moins 4 caractères")
            
            if password != password_confirm:
                erreurs.append("Les mots de passe ne correspondent pas")
            
            if erreurs:
                for err in erreurs:
                    st.error(f"❌ {err}")
            else:
                # Vérifier si le code existe déjà
                existe, _ = couturier_model.verifier_code(code_couturier.strip().upper())
                if existe:
                    st.error(f"❌ Le code '{code_couturier}' existe déjà. Veuillez en choisir un autre.")
                else:
                    # Récupérer le salon_id de l'admin (multi-tenant)
                    from utils.role_utils import obtenir_salon_id
                    salon_id = obtenir_salon_id(admin_data)
                    
                    # Tous les nouveaux utilisateurs héritent du salon de l'admin créateur
                    user_salon_id = salon_id
                    
                    # Créer l'utilisateur avec salon_id
                    user_id = couturier_model.creer_utilisateur(
                        code_couturier=code_couturier.strip().upper(),
                        password=password,
                        nom=nom.strip(),
                        prenom=prenom.strip(),
                        role=role,
                        email=email.strip() if email else None,
                        telephone=telephone.strip() if telephone else None,
                        salon_id=user_salon_id  # None pour admin (créera son salon), salon_id pour employé
                    )
                    
                    # Si c'est un admin créé, on garde le salon hérité (pas de nouveau salon auto)
                    
                    if user_id:
                        st.success(f"✅ Utilisateur '{code_couturier}' créé avec succès !")
                        st.balloons()
                        st.rerun()
                    else:
                        st.error("❌ Erreur lors de la création de l'utilisateur")


def afficher_liste_utilisateurs(couturier_model: CouturierModel, admin_data: Dict):
    """Affiche la liste de tous les utilisateurs avec possibilité de modifier le rôle"""
    
    st.markdown("#### 📋 Liste de tous les utilisateurs")
    st.markdown("---")
    
    # Récupérer tous les utilisateurs du salon de l'admin
    salon_id = admin_data.get('salon_id')
    utilisateurs = couturier_model.lister_tous_couturiers(salon_id=salon_id)
    
    if not utilisateurs:
        st.info("💭 Aucun utilisateur enregistré")
        return
    
    # Afficher dans un DataFrame
    df = pd.DataFrame(utilisateurs)
    
    # Formater les colonnes pour l'affichage
    df_display = df.copy()
    df_display['role'] = df_display['role'].apply(
        lambda x: "👑 Admin" if x == 'admin' else "👤 Employé"
    )
    
    if 'date_creation' in df_display.columns:
        df_display['date_creation'] = pd.to_datetime(df_display['date_creation']).dt.strftime('%d/%m/%Y')
    
    # Sélectionner les colonnes à afficher
    colonnes = ['code_couturier', 'nom', 'prenom', 'role', 'email', 'telephone', 'date_creation']
    colonnes_existantes = [col for col in colonnes if col in df_display.columns]
    
    df_display = df_display[colonnes_existantes]
    df_display.columns = ['Code', 'Nom', 'Prénom', 'Rôle', 'Email', 'Téléphone', 'Date création']
    
    st.dataframe(
        df_display,
        width='stretch',
        hide_index=True,
        height=400
    )
    
    st.markdown("---")
    st.markdown("#### 🔄 Modifier le rôle d'un utilisateur")
    
    # Sélection de l'utilisateur
    options_utilisateurs = {
        f"{u['code_couturier']} - {u['prenom']} {u['nom']} ({'👑 Admin' if u.get('role') == 'admin' else '👤 Employé'})": u['id']
        for u in utilisateurs
    }
    
    if options_utilisateurs:
        utilisateur_selectionne = st.selectbox(
            "Sélectionner l'utilisateur",
            options=list(options_utilisateurs.keys()),
            key="select_user_role"
        )
        
        user_id = options_utilisateurs[utilisateur_selectionne]
        
        # Récupérer le rôle actuel
        user_data = next((u for u in utilisateurs if u['id'] == user_id), None)
        role_actuel = user_data.get('role', 'employe') if user_data else 'employe'
        
        col_r1, col_r2 = st.columns(2)
        
        with col_r1:
            nouveau_role = st.selectbox(
                "Nouveau rôle",
                options=["employe", "admin"],
                index=0 if role_actuel == "employe" else 1,
                format_func=lambda x: "👤 Employé" if x == "employe" else "👑 Administrateur",
                key="new_role_select"
            )
        
        with col_r2:
            st.markdown("<br>", unsafe_allow_html=True)  # Espacement
            if st.button("💾 Modifier le rôle", type="primary", width='stretch', key="btn_modif_role"):
                if nouveau_role != role_actuel:
                    if couturier_model.modifier_role(user_id, nouveau_role):
                        st.success("✅ Rôle modifié avec succès !")
                        st.rerun()
                    else:
                        st.error("❌ Erreur lors de la modification du rôle")
                else:
                    st.info("ℹ️ Le rôle est déjà défini à cette valeur")


def afficher_gestion_mots_de_passe(couturier_model: CouturierModel, admin_data: Dict):
    """Affiche la gestion des mots de passe dans l'onglet Gestion des utilisateurs"""
    
    st.markdown("#### 🔐 Gestion des mots de passe")
    st.info("Réinitialisez le mot de passe d'un utilisateur")
    st.markdown("---")
    
    # Récupérer tous les utilisateurs
    utilisateurs = couturier_model.lister_tous_couturiers(salon_id=admin_data.get('salon_id'))
    
    if not utilisateurs:
        st.info("💭 Aucun utilisateur enregistré")
        return
    
    # Sélection de l'utilisateur
    options_utilisateurs = {
        f"{u['code_couturier']} - {u['prenom']} {u['nom']} ({'👑 Admin' if u.get('role') == 'admin' else '👤 Employé'})": u['id']
        for u in utilisateurs
    }
    
    utilisateur_selectionne = st.selectbox(
        "Sélectionner l'utilisateur",
        options=list(options_utilisateurs.keys()),
        key="select_user_gestion_mdp"
    )
    
    user_id = options_utilisateurs[utilisateur_selectionne]
    user_data = next((u for u in utilisateurs if u['id'] == user_id), None)
    
    if not user_data:
        st.error("❌ Utilisateur non trouvé")
        return
    
    st.markdown("---")
    
    # Formulaire de réinitialisation
    with st.form("form_gestion_mdp", clear_on_submit=True):
        st.markdown(f"#### 🔐 Réinitialisation pour : **{user_data.get('prenom')} {user_data.get('nom')}** ({user_data.get('code_couturier')})")
        
        nouveau_password = st.text_input(
            "Nouveau mot de passe *",
            type="password",
            help="Le nouveau mot de passe (minimum 4 caractères)",
            key="new_pwd_gestion"
        )
        
        password_confirm = st.text_input(
            "Confirmer le nouveau mot de passe *",
            type="password",
            help="Répétez le nouveau mot de passe",
            key="confirm_pwd_gestion"
        )
        
        st.markdown("---")
        
        submit = st.form_submit_button(
            "🔐 Réinitialiser le mot de passe",
            type="primary",
            width='stretch'
        )
        
        if submit:
            # Validations
            erreurs = []
            
            if not nouveau_password or len(nouveau_password) < 4:
                erreurs.append("Le mot de passe doit contenir au moins 4 caractères")
            
            if nouveau_password != password_confirm:
                erreurs.append("Les mots de passe ne correspondent pas")
            
            if erreurs:
                for err in erreurs:
                    st.error(f"❌ {err}")
            else:
                # Réinitialiser le mot de passe
                if couturier_model.reinitialiser_mot_de_passe(user_id, nouveau_password):
                    st.success("✅ Mot de passe réinitialisé avec succès !")
                    st.info("💡 L'utilisateur devra utiliser ce nouveau mot de passe pour se connecter.")
                    st.balloons()
                    st.rerun()
                else:
                    st.error("❌ Erreur lors de la réinitialisation du mot de passe")


def afficher_reinitialisation_mot_de_passe(couturier_model: CouturierModel, admin_data: Dict):
    """Affiche le formulaire de réinitialisation de mot de passe avec sous-onglets"""
    
    st.markdown("### 🔐 Réinitialiser un mot de passe")
    st.info("Réinitialisez le mot de passe d'un utilisateur ou le vôtre")
    st.markdown("---")
    
    # Récupérer tous les utilisateurs
    utilisateurs = couturier_model.lister_tous_couturiers(salon_id=admin_data.get('salon_id'))
    
    if not utilisateurs:
        st.info("💭 Aucun utilisateur enregistré")
        return
    
    # Sous-onglets
    sub_tab1, sub_tab2 = st.tabs(["👤 Autre utilisateur", "👑 Moi-même (admin)"])
    
    # ========================================================================
    # SOUS-ONGLET 1 : AUTRE UTILISATEUR
    # ========================================================================
    with sub_tab1:
        st.markdown("#### 👤 Réinitialiser le mot de passe d'un autre utilisateur")
        
        # Sélection de l'utilisateur
        options_utilisateurs = {
            f"{u['code_couturier']} - {u['prenom']} {u['nom']}": u['id']
            for u in utilisateurs
        }
        
        utilisateur_selectionne = st.selectbox(
            "Sélectionner l'utilisateur",
            options=list(options_utilisateurs.keys()),
            key="select_user_reset"
        )
        
        user_id = options_utilisateurs[utilisateur_selectionne]
        user_data = next((u for u in utilisateurs if u['id'] == user_id), None)
        
        if not user_data:
            st.error("❌ Utilisateur non trouvé")
        else:
            st.markdown("---")
            
            # Formulaire de réinitialisation
            with st.form("form_reset_password_autre", clear_on_submit=True):
                st.markdown(f"#### 🔐 Réinitialisation pour : **{user_data.get('prenom')} {user_data.get('nom')}** ({user_data.get('code_couturier')})")
                
                nouveau_password = st.text_input(
                    "Nouveau mot de passe *",
                    type="password",
                    help="Le nouveau mot de passe (minimum 4 caractères)",
                    key="new_pwd_autre"
                )
                
                password_confirm = st.text_input(
                    "Confirmer le nouveau mot de passe *",
                    type="password",
                    help="Répétez le nouveau mot de passe",
                    key="confirm_pwd_autre"
                )
                
                st.markdown("---")
                
                submit = st.form_submit_button(
                    "🔐 Réinitialiser le mot de passe",
                    type="primary",
                    width='stretch'
                )
                
                if submit:
                    # Validations
                    erreurs = []
                    
                    if not nouveau_password or len(nouveau_password) < 4:
                        erreurs.append("Le mot de passe doit contenir au moins 4 caractères")
                    
                    if nouveau_password != password_confirm:
                        erreurs.append("Les mots de passe ne correspondent pas")
                    
                    if erreurs:
                        for err in erreurs:
                            st.error(f"❌ {err}")
                    else:
                        # Réinitialiser le mot de passe
                        if couturier_model.reinitialiser_mot_de_passe(user_id, nouveau_password):
                            st.success("✅ Mot de passe réinitialisé avec succès !")
                            st.info("💡 L'utilisateur devra utiliser ce nouveau mot de passe pour se connecter.")
                            st.balloons()
                            st.rerun()
                        else:
                            st.error("❌ Erreur lors de la réinitialisation du mot de passe")
    
    # ========================================================================
    # SOUS-ONGLET 2 : MOI-MÊME (ADMIN)
    # ========================================================================
    with sub_tab2:
        st.markdown("#### 👑 Réinitialiser votre propre mot de passe")
        st.info(f"Vous allez réinitialiser votre propre mot de passe ({admin_data.get('code_couturier')})")
        st.markdown("---")
        
        user_id = admin_data.get('id')
        user_data = admin_data
        
        # Formulaire de réinitialisation
        with st.form("form_reset_password_moi", clear_on_submit=True):
            st.markdown(f"#### 🔐 Réinitialisation pour : **{user_data.get('prenom')} {user_data.get('nom')}** ({user_data.get('code_couturier')})")
            
            nouveau_password = st.text_input(
                "Nouveau mot de passe *",
                type="password",
                help="Le nouveau mot de passe (minimum 4 caractères)",
                key="new_pwd_moi"
            )
            
            password_confirm = st.text_input(
                "Confirmer le nouveau mot de passe *",
                type="password",
                help="Répétez le nouveau mot de passe",
                key="confirm_pwd_moi"
            )
            
            st.markdown("---")
            
            submit = st.form_submit_button(
                "🔐 Réinitialiser mon mot de passe",
                type="primary",
                width='stretch'
            )
            
            if submit:
                # Validations
                erreurs = []
                
                if not nouveau_password or len(nouveau_password) < 4:
                    erreurs.append("Le mot de passe doit contenir au moins 4 caractères")
                
                if nouveau_password != password_confirm:
                    erreurs.append("Les mots de passe ne correspondent pas")
                
                if erreurs:
                    for err in erreurs:
                        st.error(f"❌ {err}")
                else:
                    # Réinitialiser le mot de passe
                    if couturier_model.reinitialiser_mot_de_passe(user_id, nouveau_password):
                        st.success("✅ Mot de passe réinitialisé avec succès !")
                        st.info("💡 Vous devrez utiliser ce nouveau mot de passe pour vous connecter.")
                        st.balloons()
                        st.rerun()
                    else:
                        st.error("❌ Erreur lors de la réinitialisation du mot de passe")


def afficher_gestion_logo(admin_data: Dict):
    """Affiche la gestion du logo du salon (multi-tenant)"""
    
    import base64
    from utils.role_utils import obtenir_salon_id
    
    # Initialiser le modèle
    logo_model = AppLogoModel(st.session_state.db_connection)
    
    # Créer la table si elle n'existe pas
    logo_model.creer_tables()
    
    # Récupérer le salon_id de l'admin
    salon_id = obtenir_salon_id(admin_data)
    
    if not salon_id:
        st.error("❌ Impossible de déterminer votre salon. Veuillez vous reconnecter.")
        return
    
    st.markdown("#### 🖼️ Gestion du logo de votre salon")
    st.info(f"Téléchargez le logo de votre salon (Salon ID: {salon_id}). Ce logo sera utilisé dans l'application et tous les PDFs générés pour votre salon.")
    st.markdown("---")
    
    # Afficher le logo actuel s'il existe
    st.markdown("##### 📷 Logo actuel de votre salon")
    
    logo_data = logo_model.recuperer_logo(salon_id)
    
    if logo_data and logo_data.get('logo_data'):
        # Afficher le logo depuis la BDD
        logo_bytes = logo_data['logo_data']
        logo_mime = logo_data.get('mime_type', 'image/png')
        
        # Convertir en base64 pour l'affichage
        logo_base64 = base64.b64encode(logo_bytes).decode()
        logo_data_uri = f"data:{logo_mime};base64,{logo_base64}"
        
        st.image(logo_data_uri, caption=f"Logo actuel - {logo_data.get('logo_name', 'logo')}", width=200)
        st.success(f"✅ Logo actuel trouvé : {logo_data.get('logo_name', 'logo')} ({logo_data.get('file_size', 0)} octets)")
        
        if logo_data.get('uploaded_at'):
            st.info(f"📅 Uploadé le : {logo_data['uploaded_at']}")
    else:
        st.warning("⚠️ Aucun logo actuel trouvé pour votre salon. Téléchargez-en un ci-dessous.")
    
    st.markdown("---")
    
    # Formulaire d'upload
    st.markdown("##### 📤 Télécharger un nouveau logo")
    
    uploaded_file = st.file_uploader(
        "Choisir un fichier image",
        type=['png', 'jpg', 'jpeg'],
        help="Formats acceptés : PNG, JPG, JPEG. Le logo sera stocké dans la base de données.",
        key="upload_logo_salon"
    )
    
    if uploaded_file is not None:
        # Afficher un aperçu
        st.image(uploaded_file, caption="Aperçu du nouveau logo", width=200)
        
        # Détecter l'extension et le MIME type
        file_ext = uploaded_file.name.split('.')[-1].lower()
        mime_types = {
            'png': 'image/png',
            'jpg': 'image/jpeg',
            'jpeg': 'image/jpeg'
        }
        
        if file_ext not in mime_types:
            st.error("❌ Format de fichier non supporté. Veuillez utiliser PNG, JPG ou JPEG.")
        else:
            mime_type = mime_types[file_ext]
            st.markdown("---")
            
            # Bouton de confirmation
            if st.button("💾 Enregistrer le nouveau logo", type="primary", width='stretch', key="btn_save_logo"):
                try:
                    # Lire le contenu du fichier
                    file_bytes = uploaded_file.read()
                    
                    # Récupérer l'ID de l'admin connecté
                    admin_id = admin_data.get('id')
                    
                    # Sauvegarder dans la base de données avec salon_id
                    if logo_model.sauvegarder_logo(
                        salon_id=salon_id,
                        logo_data=file_bytes,
                        logo_name=uploaded_file.name,
                        mime_type=mime_type,
                        uploaded_by=admin_id,
                        description=f"Logo du salon {salon_id} uploadé via l'interface admin"
                    ):
                        st.success("✅ Logo enregistré avec succès dans la base de données !")
                        st.info("💡 Le nouveau logo sera utilisé dans l'application et tous les PDFs générés pour votre salon.")
                        st.balloons()
                        st.rerun()
                    else:
                        st.error("❌ Erreur lors de l'enregistrement du logo dans la base de données")
                    
                except Exception as e:
                    st.error(f"❌ Erreur lors de l'enregistrement du logo : {str(e)}")
    
    st.markdown("---")
    
    # Informations supplémentaires
    with st.expander("ℹ️ Informations sur le logo"):
        st.markdown(f"""
        **Stockage :**
        - Le logo est stocké dans la base de données (table `app_logo`) pour votre salon (Salon ID: {salon_id})
        - Un seul logo actif par salon
        - Le logo est automatiquement utilisé dans l'application et les PDFs de votre salon uniquement
        
        **Recommandations :**
        - Format : PNG (transparence) ou JPG (petite taille)
        - Taille recommandée : 200x200 pixels minimum
        - Ratio : Carré (1:1) pour un meilleur rendu
        - Taille maximale : 4 Mo (limite LONGBLOB)
        
        **Note :** Le logo sera automatiquement redimensionné dans l'application et les PDFs.
        Chaque salon a son propre logo indépendant des autres salons.
        """)


def afficher_gestion_commandes_admin(commande_model: CommandeModel, admin_data: Dict):
    """Affiche la gestion des commandes pour l'administrateur"""
    
    st.markdown("### 📦 Gestion des commandes")
    st.markdown("Vue d'ensemble et validation des commandes ouvertes/fermées")
    st.markdown("---")
    
    admin_id = admin_data.get('id')
    salon_id_admin = obtenir_salon_id(admin_data)
    
    # Récupérer tous les couturiers du salon pour le filtre
    from models.database import CouturierModel
    couturier_model = CouturierModel(commande_model.db)
    tous_couturiers = couturier_model.lister_tous_couturiers(salon_id=salon_id_admin)
    
    # Filtre par couturier (affiché en haut de tous les onglets)
    col_filtre1, col_filtre2 = st.columns([1, 3])
    with col_filtre1:
        options_couturiers = ["👥 Tous les couturiers"] + [
            f"{c['code_couturier']} - {c['prenom']} {c['nom']}"
            for c in tous_couturiers
        ]
        couturier_selectionne = st.selectbox(
            "Filtrer par couturier",
            options=options_couturiers,
            key="admin_commandes_couturier"
        )
    
    # Déterminer le couturier_id sélectionné
    couturier_id_filtre = None
    if couturier_selectionne and couturier_selectionne != "👥 Tous les couturiers":
        code_selectionne = couturier_selectionne.split(" - ")[0]
        couturier_selectionne_obj = next(
            (c for c in tous_couturiers if c['code_couturier'] == code_selectionne),
            None
        )
        if couturier_selectionne_obj:
            couturier_id_filtre = couturier_selectionne_obj['id']
    
    st.markdown("---")
    
    # Sous-onglets
    sub_tab1, sub_tab2, sub_tab3 = st.tabs([
        "🔔 Demandes en attente",
        "📂 Commandes ouvertes",
        "✅ Commandes fermées"
    ])
    
    # ========================================================================
    # ONGLET 1 : DEMANDES EN ATTENTE
    # ========================================================================
    with sub_tab1:
        st.markdown("#### 🔔 Demandes en attente de validation")
        st.info("💡 Validez ou rejetez les paiements et fermetures de commandes demandés par les employés.")
        
        # Bouton de rafraîchissement
        col_refresh, _ = st.columns([1, 5])
        with col_refresh:
            if st.button("🔄 Actualiser", width='stretch', key="refresh_demandes"):
                st.rerun()
        
        st.markdown("---")
        
        demandes_all = commande_model.lister_demandes_validation()
        if salon_id_admin:
            demandes = [
                d for d in demandes_all
                if str(d.get('salon_id')) == str(salon_id_admin)
            ]
        else:
            demandes = demandes_all
        
        if not demandes:
            st.success("✅ Aucune demande en attente. Tout est à jour !")
            if salon_id_admin and demandes_all:
                st.info(
                    f"ℹ️ Des demandes existent mais ne correspondent pas à votre salon_id={salon_id_admin}."
                )
        else:
            # Compteur de notifications
            nb_paiements = len([d for d in demandes if d['type_action'] == 'paiement'])
            nb_fermetures = len([d for d in demandes if d['type_action'] == 'fermeture_demande'])
            
            col_notif1, col_notif2 = st.columns(2)
            with col_notif1:
                st.metric("💰 Paiements en attente", nb_paiements)
            with col_notif2:
                st.metric("🔒 Fermetures en attente", nb_fermetures)
            
            st.markdown("---")
            
            # Afficher chaque demande
            for idx, demande in enumerate(demandes):
                with st.expander(
                    f"🔔 {demande['type_action'].upper()} - Commande #{demande['commande_id']} - "
                    f"{demande['client_prenom']} {demande['client_nom']} - "
                    f"{demande['modele']}",
                    expanded=False
                ):
                    col_d1, col_d2 = st.columns(2)
                    
                    with col_d1:
                        st.markdown("**📋 Informations de la demande**")
                        st.write(f"**Type :** {demande['type_action']}")
                        st.write(f"**Date :** {demande['date_creation']}")
                        st.write(f"**Employé :** {demande['couturier_prenom']} {demande['couturier_nom']}")
                        
                        if demande['type_action'] == 'paiement':
                            st.write(f"**Montant payé :** {demande['montant_paye']:,.0f} FCFA")
                            st.write(f"**Reste après paiement :** {demande['reste_apres_paiement']:,.0f} FCFA")
                        
                        if demande['commentaire']:
                            st.write(f"**Commentaire :** {demande['commentaire']}")
                    
                    with col_d2:
                        st.markdown("**📦 Informations de la commande**")
                        st.write(f"**Modèle :** {demande['modele']}")
                        st.write(f"**Client :** {demande['client_prenom']} {demande['client_nom']}")
                        st.write(f"**Prix total :** {demande['prix_total']:,.0f} FCFA")
                        st.write(f"**Avance actuelle :** {demande['avance']:,.0f} FCFA")
                        st.write(f"**Reste actuel :** {demande['reste']:,.0f} FCFA")
                        st.write(f"**Statut avant :** {demande['statut_avant']}")
                        st.write(f"**Statut après :** {demande['statut_apres']}")
                    
                    st.markdown("---")
                    
                    # Actions de validation - Approche simplifiée sans rerun dans les formulaires
                    col_act1, col_act2 = st.columns(2)
                    
                    with col_act1:
                        with st.form(f"form_valider_{demande['id']}", clear_on_submit=True):
                            commentaire_admin = st.text_area(
                                "Commentaire de validation (optionnel)",
                                key=f"comment_val_{demande['id']}",
                                height=100
                            )
                            
                            if st.form_submit_button("✅ Valider", type="primary", width='stretch'):
                                try:
                                    if commande_model.valider_fermeture(
                                        demande['id'], admin_id, True, commentaire_admin
                                    ):
                                        st.success("✅ Demande validée avec succès !")
                                        st.balloons()
                                        st.rerun()
                                    else:
                                        st.error("❌ Erreur lors de la validation")
                                except Exception as e:
                                    st.error(f"❌ Erreur : {str(e)}")
                    
                    with col_act2:
                        with st.form(f"form_rejeter_{demande['id']}", clear_on_submit=True):
                            commentaire_rejet = st.text_area(
                                "Raison du rejet (optionnel)",
                                key=f"comment_rej_{demande['id']}",
                                height=100
                            )
                            
                            if st.form_submit_button("❌ Rejeter", width='stretch'):
                                try:
                                    if commande_model.valider_fermeture(
                                        demande['id'], admin_id, False, commentaire_rejet
                                    ):
                                        st.warning("⚠️ Demande rejetée")
                                        st.rerun()
                                    else:
                                        st.error("❌ Erreur lors du rejet")
                                except Exception as e:
                                    st.error(f"❌ Erreur : {str(e)}")
                    
                    st.markdown("---")
    
    # ========================================================================
    # ONGLET 2 : COMMANDES OUVERTES
    # ========================================================================
    with sub_tab2:
        st.markdown("#### 📂 Commandes ouvertes")
        st.markdown("Liste de toutes les commandes en cours (non fermées)")
        st.markdown("---")
        
        commandes_ouvertes = commande_model.lister_commandes_ouvertes(
            couturier_id_filtre,
            tous_les_couturiers=(couturier_id_filtre is None),
            salon_id=salon_id_admin,
        )
        
        if not commandes_ouvertes:
            st.info("📭 Aucune commande ouverte pour le moment.")
        else:
            # Statistiques
            total_ca_ouvert = sum(c['prix_total'] for c in commandes_ouvertes)
            total_avance_ouvert = sum(c['avance'] for c in commandes_ouvertes)
            total_reste_ouvert = sum(c['reste'] for c in commandes_ouvertes)
            
            col_stat1, col_stat2, col_stat3, col_stat4 = st.columns(4)
            with col_stat1:
                st.metric("📦 Nombre", len(commandes_ouvertes))
            with col_stat2:
                st.metric("💰 CA Total", f"{total_ca_ouvert:,.0f} FCFA")
            with col_stat3:
                st.metric("💵 Avances", f"{total_avance_ouvert:,.0f} FCFA")
            with col_stat4:
                st.metric("💸 Reste", f"{total_reste_ouvert:,.0f} FCFA")
            
            st.markdown("---")
            
            # Tableau des commandes
            df = pd.DataFrame(commandes_ouvertes)
            required_cols = [
                'id', 'modele', 'client_prenom', 'client_nom',
                'couturier_prenom', 'couturier_nom', 'prix_total',
                'avance', 'reste', 'statut', 'date_creation'
            ]
            for col in required_cols:
                if col not in df.columns:
                    df[col] = None
            df_display = df[required_cols].copy()
            df_display.columns = ['ID', 'Modèle', 'Prénom Client', 'Nom Client',
                                  'Prénom Employé', 'Nom Employé', 'Prix Total',
                                  'Avance', 'Reste', 'Statut', 'Date Création']
            df_display['Prix Total'] = df_display['Prix Total'].apply(lambda x: f"{x:,.0f} FCFA")
            df_display['Avance'] = df_display['Avance'].apply(lambda x: f"{x:,.0f} FCFA")
            df_display['Reste'] = df_display['Reste'].apply(lambda x: f"{x:,.0f} FCFA")
            
            st.dataframe(df_display, width='stretch', hide_index=True, height=400)
    
    # ========================================================================
    # ONGLET 3 : COMMANDES FERMÉES
    # ========================================================================
    with sub_tab3:
        st.markdown("#### ✅ Commandes fermées")
        st.markdown("Historique de toutes les commandes fermées et validées")
        st.markdown("---")
        
        # Filtres de période (date de fermeture)
        col_date1, col_date2 = st.columns(2)
        with col_date1:
            date_debut_fermees = st.date_input(
                "📅 Date de début (fermeture)",
                value=None,
                key="admin_fermees_date_debut"
            )
        with col_date2:
            date_fin_fermees = st.date_input(
                "📅 Date de fin (fermeture)",
                value=None,
                key="admin_fermees_date_fin"
            )
        
        st.markdown("---")
        
        commandes_fermees = commande_model.lister_commandes_fermees(
            couturier_id_filtre,
            tous_les_couturiers=(couturier_id_filtre is None),
            salon_id=salon_id_admin,
        )
        
        # Filtrer par salon_id si nécessaire
        if commandes_fermees and salon_id_admin:
            # Filtrer les commandes par salon_id via le couturier
            commandes_fermees = [
                cmd for cmd in commandes_fermees
                if cmd.get('couturier_salon_id') == salon_id_admin or 
                   (couturier_id_filtre and cmd.get('couturier_id') == couturier_id_filtre)
            ]
        
        # Filtrer par période si nécessaire
        if commandes_fermees and (date_debut_fermees or date_fin_fermees):
            def _date_ok(value, date_debut, date_fin):
                if not value:
                    return False
                try:
                    date_val = pd.to_datetime(value).date()
                except Exception:
                    return False
                if date_debut and date_val < date_debut:
                    return False
                if date_fin and date_val > date_fin:
                    return False
                return True
            
            commandes_fermees = [
                cmd for cmd in commandes_fermees
                if _date_ok(cmd.get('date_fermeture'), date_debut_fermees, date_fin_fermees)
            ]
        
        if not commandes_fermees:
            st.info("📭 Aucune commande fermée pour le moment.")
        else:
            # Statistiques
            total_ca_ferme = sum(c['prix_total'] for c in commandes_fermees)
            nb_fermees = len(commandes_fermees)
            
            col_stat1, col_stat2 = st.columns(2)
            with col_stat1:
                st.metric("📦 Nombre", nb_fermees)
            with col_stat2:
                st.metric("💰 CA Total", f"{total_ca_ferme:,.0f} FCFA")
            
            st.markdown("---")
            
            # Tableau des commandes fermées
            df = pd.DataFrame(commandes_fermees)
            required_cols = [
                'id', 'modele', 'client_prenom', 'client_nom',
                'couturier_prenom', 'couturier_nom', 'prix_total',
                'avance', 'date_creation', 'date_fermeture'
            ]
            for col in required_cols:
                if col not in df.columns:
                    df[col] = None
            df_display = df[required_cols].copy()
            df_display.columns = ['ID', 'Modèle', 'Prénom Client', 'Nom Client',
                                  'Prénom Employé', 'Nom Employé', 'Prix Total',
                                  'Avance', 'Date Création', 'Date Fermeture']
            df_display['Prix Total'] = df_display['Prix Total'].apply(lambda x: f"{x:,.0f} FCFA")
            df_display['Avance'] = df_display['Avance'].apply(lambda x: f"{x:,.0f} FCFA")
            
            if 'date_fermeture' in df_display.columns:
                df_display['Date Fermeture'] = pd.to_datetime(df_display['Date Fermeture']).dt.strftime('%d/%m/%Y %H:%M')
            
            st.dataframe(df_display, width='stretch', hide_index=True, height=400)

