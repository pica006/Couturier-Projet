"""
========================================
VUE TABLEAU DE BORD (dashboard_view.py)
========================================

POURQUOI CE FICHIER ?
---------------------
Page d'accueil et tableau de bord pour le couturier
Affiche les statistiques principales, graphiques rapides et indicateurs clés

FONCTIONNALITÉS :
-----------------
- Statistiques du mois en cours, totales
- En mode ADMIN : + filtre par couturier, répartition par modèle, graphiques
- Actions rapides, dernières activités
"""

import streamlit as st
from datetime import datetime
import pandas as pd
import plotly.express as px
from models.database import ChargesModel, CommandeModel, CouturierModel
from utils.role_utils import est_admin, obtenir_salon_id
from utils.ui import (
    ajouter_espace_vertical,
    appliquer_style_pages_critiques,
    afficher_erreur_minimale,
    afficher_info_minimale,
    afficher_titre_section,
)


def afficher_page_dashboard():
    """
    Page Tableau de bord : Vue d'ensemble de l'activité
    Contenu complet + en mode ADMIN : filtre par couturier, répartition par modèle, figures
    """
    
    appliquer_style_pages_critiques()

    # En-tête encadré standardisé
    from utils.page_header import afficher_header_page
    afficher_header_page("📊 Tableau de bord", "Vue d'ensemble de votre activité")
    
    # Vérifier la connexion
    if not st.session_state.db_connection or not st.session_state.authentifie:
        afficher_erreur_minimale("Vous devez être connecté pour accéder à cette page")
        return
    
    couturier_data = st.session_state.couturier_data
    couturier_id = couturier_data['id']
    salon_id = obtenir_salon_id(couturier_data)
    
    try:
        from controllers.comptabilite_controller import ComptabiliteController
        
        compta_controller = ComptabiliteController(st.session_state.db_connection)
        charges_model = ChargesModel(st.session_state.db_connection)
        
        # ========================================================================
        # SÉLECTION DE LA PÉRIODE
        # ========================================================================
        
        afficher_titre_section("📅 Sélection de la période d'analyse")
        
        aujourdhui = datetime.now()
        debut_mois = datetime(aujourdhui.year, aujourdhui.month, 1).date()
        
        # Gérer la réinitialisation : supprimer les clés des widgets si nécessaire
        if 'reset_dashboard_dates' in st.session_state and st.session_state.reset_dashboard_dates:
            # Supprimer les clés des widgets pour permettre la réinitialisation
            if 'dashboard_date_debut_input' in st.session_state:
                del st.session_state.dashboard_date_debut_input
            if 'dashboard_date_fin_input' in st.session_state:
                del st.session_state.dashboard_date_fin_input
            st.session_state.reset_dashboard_dates = False
        
        col_date1, col_date2, col_date3 = st.columns([2, 2, 1])
        
        with col_date1:
            # Déterminer la valeur par défaut
            if 'dashboard_date_debut_input' in st.session_state:
                # Le widget existe déjà, utiliser sa valeur
                default_debut = st.session_state.dashboard_date_debut_input
            else:
                # Première fois ou après réinitialisation, utiliser le début du mois
                default_debut = debut_mois
            
            date_debut = st.date_input(
                "Date de début",
                value=default_debut,
                key="dashboard_date_debut_input",
                help="Sélectionnez la date de début de la période à analyser"
            )
        
        with col_date2:
            # Déterminer la valeur par défaut
            if 'dashboard_date_fin_input' in st.session_state:
                # Le widget existe déjà, utiliser sa valeur
                default_fin = st.session_state.dashboard_date_fin_input
            else:
                # Première fois ou après réinitialisation, utiliser aujourd'hui
                default_fin = aujourdhui.date()
            
            date_fin = st.date_input(
                "Date de fin",
                value=default_fin,
                key="dashboard_date_fin_input",
                help="Sélectionnez la date de fin de la période à analyser"
            )
        
        with col_date3:
            ajouter_espace_vertical()
            if st.button("🔄 Mois en cours", use_container_width=True, key="btn_reset_dashboard_dates"):
                # Marquer pour supprimer les clés des widgets au prochain rerun
                st.session_state.reset_dashboard_dates = True
                st.rerun()
        
        # Filtrer par couturier (admin uniquement)
        couturier_id_filtre_modeles = couturier_id
        if est_admin(couturier_data) and salon_id:
            couturier_model = CouturierModel(st.session_state.db_connection)
            tous_couturiers = couturier_model.lister_tous_couturiers(salon_id=salon_id)
            options = ["👥 Tous les couturiers"] + [
                f"{c['code_couturier']} - {c['prenom']} {c['nom']}" for c in (tous_couturiers or [])
            ]
            couturier_selectionne = st.selectbox(
                "Filtrer par couturier",
                options=options,
                key="dashboard_filtre_couturier",
                help="Pour la section Modèles réalisés ci-dessous"
            )
            if couturier_selectionne and couturier_selectionne != "👥 Tous les couturiers":
                code = couturier_selectionne.split(" - ")[0]
                obj = next((c for c in (tous_couturiers or []) if c['code_couturier'] == code), None)
                couturier_id_filtre_modeles = obj['id'] if obj else couturier_id
            else:
                couturier_id_filtre_modeles = None
        
        # Validation des dates
        if date_debut > date_fin:
            afficher_erreur_minimale("La date de début doit être antérieure à la date de fin")
            return
        
        # Convertir les dates en datetime pour les requêtes
        date_debut_dt = datetime.combine(date_debut, datetime.min.time())
        date_fin_dt = datetime.combine(date_fin, datetime.max.time())
        
        # Calculer le nombre de jours
        nb_jours = (date_fin - date_debut).days + 1
        
        afficher_info_minimale(
            f"Analyse de la période du **{date_debut.strftime('%d/%m/%Y')}** au **{date_fin.strftime('%d/%m/%Y')}** "
            f"({nb_jours} jour{'s' if nb_jours > 1 else ''})"
        )
        st.markdown("---")
        
        # ========================================================================
        # STATISTIQUES DE LA PÉRIODE SÉLECTIONNÉE
        # ========================================================================
        
        afficher_titre_section("📈 Statistiques de la période")
        
        # Stats de la période sélectionnée
        stats_periode = compta_controller.obtenir_statistiques(couturier_id, date_debut_dt, date_fin_dt)
        charges_periode = charges_model.total_charges(couturier_id, date_debut_dt, date_fin_dt)
        resultat_periode = stats_periode['ca_total'] - charges_periode
        
        # Cartes principales
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric(
                label="💰 Chiffre d'affaires",
                value=f"{stats_periode['ca_total']:,.0f} FCFA",
                help=f"CA total sur la période ({nb_jours} jours)"
            )
        
        with col2:
            st.metric(
                label="📦 Commandes",
                value=stats_periode['nb_commandes'],
                help="Nombre de commandes sur la période"
            )
        
        with col3:
            st.metric(
                label="📄 Charges",
                value=f"{charges_periode:,.0f} FCFA",
                help="Total des dépenses sur la période"
            )
        
        with col4:
            st.metric(
                label="📈 Résultat net",
                value=f"{resultat_periode:,.0f} FCFA",
                delta_color="normal" if resultat_periode >= 0 else "inverse",
                help="Bénéfice sur la période (CA - Charges)"
            )
        
        # Métriques supplémentaires
        st.markdown("---")
        col5, col6, col7, col8 = st.columns(4)
        
        with col5:
            st.metric(
                label="💳 Avances reçues",
                value=f"{stats_periode['avances_total']:,.0f} FCFA",
                delta=f"{stats_periode['taux_avance']:.1f}%",
                help="Montant des avances perçues"
            )
        
        with col6:
            st.metric(
                label="⏳ Reste à percevoir",
                value=f"{stats_periode['reste_total']:,.0f} FCFA",
                delta=f"-{100-stats_periode['taux_avance']:.1f}%",
                delta_color="inverse",
                help="Montant restant à encaisser"
            )
        
        with col7:
            ca_moyen_jour = stats_periode['ca_total'] / nb_jours if nb_jours > 0 else 0
            st.metric(
                label="📊 CA moyen/jour",
                value=f"{ca_moyen_jour:,.0f} FCFA",
                help="Chiffre d'affaires moyen par jour"
            )
        
        with col8:
            charges_moyen_jour = charges_periode / nb_jours if nb_jours > 0 else 0
            st.metric(
                label="💸 Charges moyennes/jour",
                value=f"{charges_moyen_jour:,.0f} FCFA",
                help="Charges moyennes par jour"
            )
        
        st.markdown("---")
        
        # ========================================================================
        # STATISTIQUES TOTALES (TOUTES PÉRIODES)
        # ========================================================================
        
        afficher_titre_section("🎯 Statistiques totales (toutes périodes)")
        
        # Stats globales (sans filtre de date)
        stats_total = compta_controller.obtenir_statistiques(couturier_id)
        charges_total = charges_model.total_charges(couturier_id)
        
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric(
                label="💵 CA total",
                value=f"{stats_total['ca_total']:,.0f} FCFA",
                help="Chiffre d'affaires depuis le début"
            )
        
        with col2:
            st.metric(
                label="✅ Total commandes",
                value=stats_total['nb_commandes'],
                help="Nombre total de commandes"
            )
        
        with col3:
            st.metric(
                label="💳 Total encaissé",
                value=f"{stats_total['avances_total']:,.0f} FCFA",
                delta=f"{stats_total['taux_avance']:.1f}%",
                help="Montant déjà encaissé"
            )
        
        with col4:
            st.metric(
                label="⏳ Total à encaisser",
                value=f"{stats_total['reste_total']:,.0f} FCFA",
                delta=f"-{100-stats_total['taux_avance']:.1f}%",
                delta_color="inverse",
                help="Montant restant à percevoir"
            )
        
        st.markdown("---")
        
        # ========================================================================
        # ACTIONS RAPIDES
        # ========================================================================
        
        afficher_titre_section("⚡ Actions rapides")
        
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            if st.button("➕ Nouvelle commande", use_container_width=True):
                st.session_state.page = 'nouvelle_commande'
                st.rerun()
        
        with col2:
            if st.button("📜 Mes commandes", use_container_width=True):
                st.session_state.page = 'liste_commandes'
                st.rerun()
        
        with col3:
            if st.button("💰 Comptabilité", use_container_width=True):
                st.session_state.page = 'comptabilite'
                st.rerun()
        
        with col4:
            if st.button("📄 Mes charges", use_container_width=True):
                st.session_state.page = 'charges'
                st.rerun()
        
        st.markdown("---")
        
        # ========================================================================
        # DERNIÈRES ACTIVITÉS
        # ========================================================================
        
        afficher_titre_section("🕐 Dernières activités")
        
        # Commandes à relancer
        commandes_relance = compta_controller.obtenir_commandes_a_relancer(couturier_id)
        if commandes_relance:
            st.warning(f"🔔 {len(commandes_relance)} commande(s) à relancer pour paiement")
        else:
            st.success("✅ Tous les paiements sont à jour !")
        
        # Performance du jour
        debut_jour = datetime.combine(aujourdhui.date(), datetime.min.time())
        fin_jour = datetime.combine(aujourdhui.date(), datetime.max.time())
        stats_jour = compta_controller.obtenir_statistiques(couturier_id, debut_jour, fin_jour)
        
        if stats_jour['nb_commandes'] > 0:
            st.success(f"🎉 Aujourd'hui : {stats_jour['nb_commandes']} commande(s) pour {stats_jour['ca_total']:,.0f} FCFA")
        else:
            afficher_info_minimale("Aujourd'hui : pas encore de commande, continuez vos efforts !")
        
        # ========================================================================
        # SECTION MODÈLES RÉALISÉS (admin uniquement) - comme page Modèles réalisés
        # ========================================================================
        if est_admin(couturier_data) and salon_id:
            st.markdown("---")
            afficher_titre_section("👗 Modèles réalisés par le salon")
            
            date_debut_dt = datetime.combine(date_debut, datetime.min.time())
            date_fin_dt = datetime.combine(date_fin, datetime.max.time())
            
            commande_model = CommandeModel(st.session_state.db_connection)
            modeles = commande_model.lister_modeles_realises(
                couturier_id=couturier_id_filtre_modeles,
                tous_les_couturiers=(couturier_id_filtre_modeles is None),
                salon_id=salon_id,
                date_debut=date_debut_dt,
                date_fin=date_fin_dt,
            )
            
            if modeles:
                df_modeles = pd.DataFrame(modeles)
                df_modeles['CA (FCFA)'] = df_modeles['ca_total'].apply(lambda x: f"{x:,.0f}")
                total_ca_modeles = df_modeles['ca_total'].sum()
                total_ordres_modeles = df_modeles['nb_commandes'].sum()
                
                col_m1, col_m2 = st.columns(2)
                with col_m1:
                    st.metric("📦 Total commandes", total_ordres_modeles)
                with col_m2:
                    st.metric("💰 Chiffre d'affaires", f"{total_ca_modeles:,.0f} FCFA")
                
                st.markdown("#### Répartition par modèle")
                df_display = df_modeles[['modele', 'categorie', 'sexe', 'nb_commandes', 'CA (FCFA)']].copy()
                df_display.columns = ['Modèle', 'Catégorie', 'Sexe', 'Nombre', 'CA (FCFA)']
                st.dataframe(df_display, hide_index=True, use_container_width=True)
                
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
            else:
                afficher_info_minimale("Aucun modèle réalisé pour cette période.")
    
    except Exception as e:
        afficher_erreur_minimale(f"Erreur lors du chargement du tableau de bord : {e}")
        import traceback
        st.code(traceback.format_exc())

