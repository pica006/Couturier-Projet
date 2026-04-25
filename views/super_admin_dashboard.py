"""
🔧 DASHBOARD SUPER ADMINISTRATEUR - VUE 360° COMPLÈTE
- Gestion des salons
- Gestion des admins
- Gestion des employés
- Statistiques globales
- Rapports
"""
import streamlit as st
from models.salon_model import SalonModel
from models.database import CouturierModel, AppLogoModel
from models.commande_model import CommandeModel
from controllers.super_admin_controller import SuperAdminController
from utils.permissions import est_super_admin
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
import json


def afficher_dashboard_super_admin():
    """
    Dashboard complet du SUPER_ADMIN avec vue 360°
    """
    # Vérifier les permissions
    if not est_super_admin():
        st.error("❌ Accès refusé : Cette page est réservée au Super Administrateur")
        return
    
    # En-tête encadré standardisé
    from utils.page_header import afficher_header_page
    afficher_header_page("🔧 SUPER ADMINISTRATION", "Vue 360° sur tous les salons de couture")
    
    # Vérifier la connexion
    if 'db_connection' not in st.session_state:
        st.error("❌ Erreur : Connexion à la base de données non établie")
        return
    
    # Initialiser le contrôleur (expose les modèles via super_admin_ctrl.XXX_model)
    super_admin_ctrl = SuperAdminController(st.session_state.db_connection)
    salon_model = super_admin_ctrl.salon_model
    couturier_model = super_admin_ctrl.couturier_model
    commande_model = super_admin_ctrl.commande_model
    
    # ========================================================================
    # ONGLETS PRINCIPAUX
    # ========================================================================
    
    tabs = st.tabs([
        "📊 Vue d'ensemble",
        "🏢 Gérer les salons",
        "👥 Gérer les utilisateurs",
        "📦 Toutes les commandes",
        "📈 Statistiques avancées",
        "🔔 Demandes (global)",
        "📄 Rapports"
    ])
    
    # ========================================================================
    # ONGLET 1 : VUE D'ENSEMBLE
    # ========================================================================
    with tabs[0]:
        afficher_vue_ensemble(super_admin_ctrl, salon_model)
    
    # ========================================================================
    # ONGLET 2 : GÉRER LES SALONS
    # ========================================================================
    with tabs[1]:
        afficher_gestion_salons(salon_model)
    
    # ========================================================================
    # ONGLET 3 : GÉRER LES UTILISATEURS (ADMINS + EMPLOYÉS)
    # ========================================================================
    with tabs[2]:
        afficher_gestion_utilisateurs(super_admin_ctrl, salon_model, couturier_model)
    
    # ========================================================================
    # ONGLET 4 : TOUTES LES COMMANDES
    # ========================================================================
    with tabs[3]:
        afficher_toutes_commandes(super_admin_ctrl, salon_model)
    
    # ========================================================================
    # ONGLET 5 : STATISTIQUES AVANCÉES
    # ========================================================================
    with tabs[4]:
        afficher_statistiques_avancees(super_admin_ctrl, salon_model)
    
    # ========================================================================
    # ONGLET 6 : RAPPORTS
    # ========================================================================
    with tabs[5]:
        afficher_demandes_globales_super_admin(commande_model, salon_model)
    
    with tabs[6]:
        afficher_rapports(super_admin_ctrl, salon_model)


# ============================================================================
# FONCTIONS POUR CHAQUE ONGLET
# ============================================================================

def afficher_vue_ensemble(super_admin_ctrl, salon_model):
    """Onglet 1 : Vue d'ensemble globale ou par salon"""
    
    st.subheader("📊 Vue d'ensemble")

    # ------------------------------------------------------------------
    # Filtres de période + sélection de salon
    # ------------------------------------------------------------------
    col_date1, col_date2 = st.columns(2)
    with col_date1:
        date_debut = st.date_input(
            "Date de début",
            value=datetime.now().date() - timedelta(days=90),
            key="superadmin_vue_ensemble_debut",
            help="Début de la période d'analyse pour les statistiques"
        )
    with col_date2:
        date_fin = st.date_input(
            "Date de fin",
            value=datetime.now().date(),
            key="superadmin_vue_ensemble_fin",
            help="Fin de la période d'analyse pour les statistiques"
        )

    date_debut_dt = datetime.combine(date_debut, datetime.min.time())
    date_fin_dt = datetime.combine(date_fin, datetime.max.time())

    # Sélecteur de salon
    salons = salon_model.lister_tous_salons()
    
    # Debug : afficher le nombre de salons trouvés
    if not salons:
        st.warning("⚠️ Aucun salon trouvé dans la base de données")
        st.info("💡 Vérifiez que la table 'salons' contient des données avec des salon_id")
        
        with st.expander("🔍 Debug - Diagnostic complet"):
            st.markdown("### Vérifications à effectuer :")

            diagnostic = super_admin_ctrl.diagnostiquer_salons()
            if diagnostic.get("error"):
                st.error(f"❌ Erreur lors du diagnostic : {diagnostic['error']}")
            elif diagnostic.get("table_exists"):
                st.success("✅ La table 'salons' existe")
                st.info(f"📊 Nombre de salons dans la table : {diagnostic.get('count', 0)}")

                samples = diagnostic.get("samples", [])
                if samples:
                    st.markdown("**Premiers salons trouvés :**")
                    for row in samples:
                        st.write(f"- {row['salon_id']} : {row['nom']} ({row['quartier']})")
                else:
                    st.warning("⚠️ La table est vide. Créez un salon d'abord.")
            else:
                st.error("❌ La table 'salons' n'existe pas")
                st.info("💡 Vous devez créer la table 'salons' d'abord")
            
            st.markdown("---")
            st.code("""
            Pour vérifier manuellement dans votre base de données :
            
            -- MySQL
            SELECT salon_id, nom, quartier FROM salons;
            
            -- PostgreSQL
            SELECT salon_id, nom, quartier FROM salons;
            
            Si cette requête retourne des résultats mais que rien ne s'affiche,
            il y a peut-être un problème avec la structure de la table.
            """)
        return
    
    salon_filter_options = ["[Tous les salons]"] + [
        f"{s['salon_id']} - {s['nom_salon']}" for s in salons
    ]
    
    selected_salon = st.selectbox(
        "🏢 Sélectionner un salon",
        options=salon_filter_options,
        key="vue_ensemble_salon_filter",
        help="Choisissez un salon pour voir ses statistiques détaillées, ou '[Tous les salons]' pour une vue globale"
    )
    
    # Extraire le salon_id
    salon_id_selected = None
    if selected_salon != "[Tous les salons]":
        salon_id_selected = selected_salon.split(" - ")[0]

    def _norm_salon_id(value):
        return str(value or "").strip().lower()
    
    st.markdown("---")
    
    # Si un salon est sélectionné, afficher les stats de ce salon
    if salon_id_selected:
        # KPI ciblés du salon sélectionné (logique métier dans le contrôleur MVC)
        salon_stats = super_admin_ctrl.obtenir_kpis_salon(
            salon_id=salon_id_selected,
            date_debut=date_debut_dt,
            date_fin=date_fin_dt,
        )

        # Fallback: afficher un tableau KPI à 0 plutôt qu'un vide total
        if not salon_stats:
            salon_base = next(
                (
                    s for s in salons
                    if _norm_salon_id(s.get('salon_id')) == _norm_salon_id(salon_id_selected)
                ),
                None
            )
            if salon_base:
                salon_stats = {
                    'salon_id': salon_base.get('salon_id'),
                    'nom_salon': salon_base.get('nom_salon', f"Salon {salon_id_selected}"),
                    'quartier': salon_base.get('quartier', 'N/A'),
                    'responsable': salon_base.get('responsable', 'N/A'),
                    'telephone': salon_base.get('telephone', 'N/A'),
                    'code_admin': salon_base.get('code_admin', 'N/A'),
                    'date_creation': salon_base.get('date_creation'),
                    'nb_employes': int(salon_base.get('nb_employes', 0) or 0),
                    'nb_clients': int(salon_base.get('nb_clients', 0) or 0),
                    'nb_commandes': 0,
                    'ca_total': 0.0,
                    'avances': 0.0,
                    'reste': 0.0,
                    'charges': 0.0,
                    'benefice': 0.0,
                    'taux_encaissement': 0.0,
                }
        
        if not salon_stats:
            st.warning(f"⚠️ Aucune donnée disponible pour le salon {salon_id_selected}")
        else:
            # Si la période sélectionnée est vide, tenter un fallback toutes périodes
            # pour éviter d'afficher un faux "tout à 0" alors que le salon a de l'historique.
            has_financial_activity = any([
                float(salon_stats.get('ca_total', 0) or 0) > 0,
                float(salon_stats.get('avances', 0) or 0) > 0,
                float(salon_stats.get('charges', 0) or 0) > 0,
                int(salon_stats.get('nb_commandes', 0) or 0) > 0,
            ])
            if not has_financial_activity:
                salon_stats_all_time = super_admin_ctrl.obtenir_kpis_salon(
                    salon_id=salon_id_selected
                )
                if salon_stats_all_time and any([
                    float(salon_stats_all_time.get('ca_total', 0) or 0) > 0,
                    float(salon_stats_all_time.get('avances', 0) or 0) > 0,
                    float(salon_stats_all_time.get('charges', 0) or 0) > 0,
                    int(salon_stats_all_time.get('nb_commandes', 0) or 0) > 0,
                ]):
                    st.info(
                        "ℹ️ Aucune activité sur la période sélectionnée. "
                        "Affichage des KPI du salon en toutes périodes."
                    )
                    salon_stats = salon_stats_all_time

            # Afficher le nom du salon
            st.markdown(f"### 🏢 {salon_stats['nom_salon']} ({salon_id_selected})")
            
            # Métriques principales
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                st.metric("👷 Employés", salon_stats['nb_employes'])
            
            with col2:
                st.metric("🙋 Clients", salon_stats['nb_clients'])
            
            with col3:
                st.metric("📦 Commandes", salon_stats['nb_commandes'])
            
            with col4:
                st.metric("🏢 Quartier", salon_stats.get('quartier', 'N/A'))
            
            st.markdown("---")
            
            # Métriques financières
            col5, col6, col7, col8 = st.columns(4)
            
            with col5:
                st.metric(
                    "💰 CA Total",
                    f"{salon_stats['ca_total']:,.0f} FCFA",
                    help="Chiffre d'affaires total du salon"
                )
            
            with col6:
                st.metric(
                    "💳 Encaissé",
                    f"{salon_stats['avances']:,.0f} FCFA",
                    delta=f"{salon_stats['taux_encaissement']:.1f}%",
                    help="Montant total encaissé"
                )
            
            with col7:
                st.metric(
                    "💸 Charges",
                    f"{salon_stats['charges']:,.0f} FCFA",
                    help="Total des charges du salon"
                )
            
            with col8:
                benefice = salon_stats['benefice']
                st.metric(
                    "📈 Bénéfice brut",
                    f"{benefice:,.0f} FCFA",
                    delta_color="normal" if benefice >= 0 else "inverse",
                    help="CA - Charges"
                )
            
            st.markdown("---")
            
            # Informations supplémentaires
            st.markdown("### 📋 Informations du salon")
            col_info1, col_info2 = st.columns(2)
            
            with col_info1:
                st.markdown(f"**Responsable** : {salon_stats.get('responsable', 'N/A')}")
                st.markdown(f"**Téléphone** : {salon_stats.get('telephone', 'N/A')}")
                st.markdown(f"**Code Admin** : {salon_stats.get('code_admin', 'N/A')}")
            
            with col_info2:
                st.markdown(f"**Reste à encaisser** : {salon_stats['reste']:,.0f} FCFA")
                if salon_stats.get('date_creation'):
                    st.markdown(f"**Date de création** : {salon_stats['date_creation']}")

            with st.expander("🔎 Diagnostic KPI salon (debug)"):
                diag = super_admin_ctrl.diagnostiquer_kpi_salon(
                    salon_id=salon_id_selected,
                    date_debut=date_debut_dt,
                    date_fin=date_fin_dt,
                )
                if diag.get("error"):
                    st.error(f"Erreur diagnostic: {diag['error']}")
                else:
                    st.write(f"Salon: {diag.get('salon_id')}")
                    st.write(
                        "Commandes -> "
                        f"direct: {diag.get('cmd_direct', 0)} | "
                        f"via couturier: {diag.get('cmd_via_couturier', 0)} | "
                        f"via client: {diag.get('cmd_via_client', 0)}"
                    )
                    st.write(
                        "Charges -> "
                        f"direct: {diag.get('charges_direct', 0)} | "
                        f"via couturier: {diag.get('charges_via_couturier', 0)}"
                    )
    
    else:
        # Vue globale (tous les salons)
        st.markdown("### 🌐 Vue globale - Tous les salons")
        
        # Récupérer les statistiques globales (sur la période)
        stats = super_admin_ctrl.obtenir_statistiques_globales(
            date_debut=date_debut_dt,
            date_fin=date_fin_dt,
        )
        
        if not stats:
            st.warning("⚠️ Aucune donnée disponible")
            return
        
        # Métriques principales
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric("🏢 Salons actifs", stats['nb_salons'])
        
        with col2:
            st.metric("👥 Admins", stats['nb_admins'])
        
        with col3:
            st.metric("👷 Employés", stats['nb_employes'])
        
        with col4:
            st.metric("🙋 Clients", stats['nb_clients_total'])
        
        st.markdown("---")
        
        # Métriques financières
        col5, col6, col7, col8 = st.columns(4)
        
        with col5:
            st.metric(
                "💰 CA Total",
                f"{stats['ca_total']:,.0f} FCFA",
                help="Chiffre d'affaires total de tous les salons"
            )
        
        with col6:
            st.metric(
                "💳 Encaissé",
                f"{stats['avances_total']:,.0f} FCFA",
                delta=f"{stats['taux_encaissement']:.1f}%",
                help="Montant total encaissé"
            )
        
        with col7:
            st.metric(
                "💸 Charges",
                f"{stats['charges_total']:,.0f} FCFA",
                help="Total des charges de tous les salons"
            )
        
        with col8:
            benefice = stats['benefice_brut']
            st.metric(
                "📈 Bénéfice brut",
                f"{benefice:,.0f} FCFA",
                delta_color="normal" if benefice >= 0 else "inverse",
                help="CA - Charges"
            )
        
        st.markdown("---")
        
        # Vue comparative détaillée par salon (sur la période)
        st.subheader("🏆 Comparatif des salons (performance globale)")

        stats_par_salon = super_admin_ctrl.obtenir_statistiques_par_salon(
            date_debut=date_debut_dt,
            date_fin=date_fin_dt,
        )
        if not stats_par_salon:
            st.info("ℹ️ Aucune statistique détaillée par salon disponible.")
            return

        df_salons = pd.DataFrame(stats_par_salon)

        # Tableau comparatif principal
        colonnes_comparatif = [
            'salon_id',
            'nom_salon',
            'nb_clients',
            'nb_commandes',
            'ca_total',
            'avances',
            'reste',
            'charges',
            'benefice',
        ]
        colonnes_existantes = [c for c in colonnes_comparatif if c in df_salons.columns]

        if colonnes_existantes:
            df_comp = df_salons[colonnes_existantes].copy()
            df_comp = df_comp.sort_values('ca_total', ascending=False)

            # Renommer les colonnes pour affichage
            mapping_noms = {
                'salon_id': 'Salon ID',
                'nom_salon': 'Salon',
                'nb_clients': 'Clients',
                'nb_commandes': 'Commandes',
                'ca_total': 'CA (FCFA)',
                'avances': 'Total encaissé (FCFA)',
                'reste': 'Reste à encaisser (FCFA)',
                'charges': 'Charges (FCFA)',
                'benefice': 'Bénéfice (FCFA)',
            }
            df_comp = df_comp.rename(columns={k: v for k, v in mapping_noms.items() if k in df_comp.columns})

            st.markdown("#### 📋 Tableau comparatif (tous les salons)")
            st.dataframe(df_comp, use_container_width=True, hide_index=True)

            st.markdown("---")

            # Classements par critère clé
            col_ca, col_cli, col_cmd = st.columns(3)

            with col_ca:
                st.markdown("##### 💰 Classement par CA")
                if 'CA (FCFA)' in df_comp.columns:
                    st.dataframe(
                        df_comp[['Salon', 'CA (FCFA)']].sort_values('CA (FCFA)', ascending=False).head(10),
                        use_container_width=True,
                        hide_index=True,
                    )

            with col_cli:
                st.markdown("##### 🙋 Classement par clients")
                if 'Clients' in df_comp.columns:
                    st.dataframe(
                        df_comp[['Salon', 'Clients']].sort_values('Clients', ascending=False).head(10),
                        use_container_width=True,
                        hide_index=True,
                    )

            with col_cmd:
                st.markdown("##### 📦 Classement par commandes")
                if 'Commandes' in df_comp.columns:
                    st.dataframe(
                        df_comp[['Salon', 'Commandes']].sort_values('Commandes', ascending=False).head(10),
                        use_container_width=True,
                        hide_index=True,
                    )

            st.markdown("---")

            col_enc, col_ben = st.columns(2)

            with col_enc:
                st.markdown("##### 💳 Classement par total encaissé")
                if 'Total encaissé (FCFA)' in df_comp.columns:
                    st.dataframe(
                        df_comp[['Salon', 'Total encaissé (FCFA)']].sort_values('Total encaissé (FCFA)', ascending=False).head(10),
                        use_container_width=True,
                        hide_index=True,
                    )

            with col_ben:
                st.markdown("##### 📈 Classement par bénéfice")
                if 'Bénéfice (FCFA)' in df_comp.columns:
                    st.dataframe(
                        df_comp[['Salon', 'Bénéfice (FCFA)']].sort_values('Bénéfice (FCFA)', ascending=False).head(10),
                        use_container_width=True,
                        hide_index=True,
                    )


def afficher_gestion_salons(salon_model):
    """Onglet 2 : Gestion des salons"""
    
    st.subheader("🏢 Gestion des salons de couture")

    created_salon_flash = st.session_state.pop("super_admin_created_salon", None)
    if created_salon_flash:
        st.success(
            f"✅ Salon créé avec succès ! Salon ID: {created_salon_flash.get('salon_id')} | "
            f"Code admin: {created_salon_flash.get('code_admin')}"
        )

    logo_saved_flash = st.session_state.pop("super_admin_logo_saved", None)
    if logo_saved_flash:
        st.success(
            f"✅ Logo enregistré en base pour le salon {logo_saved_flash} (affichage app et PDFs)."
        )

    logo_warn_flash = st.session_state.pop("super_admin_logo_warn", None)
    if logo_warn_flash:
        if logo_warn_flash is True:
            st.warning(
                "⚠️ Salon créé, mais l’enregistrement du logo a échoué. "
                "Ajoutez-le depuis l’admin du salon (onglet Gestion du logo)."
            )
        else:
            st.warning(
                f"⚠️ Salon créé, mais le logo n’a pas pu être enregistré : {logo_warn_flash}"
            )

    updated_salon_flash = st.session_state.pop("super_admin_updated_salon", None)
    if updated_salon_flash:
        st.success(f"✅ Salon modifié avec succès : {updated_salon_flash}")
    
    # Sous-onglets
    sub_tab1, sub_tab2, sub_tab3 = st.tabs([
        "📋 Liste des salons",
        "➕ Créer un salon",
        "✏️ Modifier un salon"
    ])
    
    # ========================================================================
    # LISTE DES SALONS
    # ========================================================================
    with sub_tab1:
        st.markdown("### 📋 Tous les salons")
        
        salons = salon_model.lister_tous_salons()
        
        if not salons:
            st.info("ℹ️ Aucun salon créé. Créez votre premier salon dans l'onglet 'Créer un salon'")
        else:
            st.success(f"✅ {len(salons)} salon(s) enregistré(s)")
            
            # Tableau des salons
            df_salons = pd.DataFrame(salons)
            
            colonnes = ['salon_id', 'nom_salon', 'quartier', 'responsable', 
                       'code_admin', 'nb_employes', 'nb_clients', 'nb_commandes',
                       'telephone', 'email']
            
            colonnes_existantes = [c for c in colonnes if c in df_salons.columns]
            
            st.dataframe(
                df_salons[colonnes_existantes],
                use_container_width=True,
                hide_index=True
            )
            
            # Détails d'un salon
            st.markdown("---")
            st.markdown("### 🔍 Détails d'un salon")
            
            salon_options = {f"{s['salon_id']} - {s['nom_salon']}": s for s in salons}
            
            selected = st.selectbox(
                "Sélectionner un salon",
                options=list(salon_options.keys()),
                key="select_salon_details"
            )
            
            if selected:
                salon = salon_options[selected]
                
                st.markdown(f"### 🏢 {salon['nom_salon']} ({salon['salon_id']})")
                st.markdown("---")
                
                # Métriques principales
                st.markdown("#### 📊 Statistiques du salon")
                col1, col2, col3, col4 = st.columns(4)
                
                with col1:
                    st.metric("👥 Employés", salon.get('nb_employes', 0))
                
                with col2:
                    st.metric("🙋 Clients", salon.get('nb_clients', 0))
                
                with col3:
                    st.metric("📦 Commandes", salon.get('nb_commandes', 0))
                
                with col4:
                    st.metric("💰 CA Total", f"{salon.get('ca_total', 0):,.0f} FCFA")
                
                st.markdown("---")
                
                # Informations générales
                st.markdown("#### 📋 Informations générales")
                col_a, col_b = st.columns(2)
                
                with col_a:
                    st.markdown("**Informations du salon**")
                    st.write(f"**ID** : {salon['salon_id']}")
                    st.write(f"**Nom** : {salon['nom_salon']}")
                    st.write(f"**Quartier** : {salon.get('quartier', 'N/A')}")
                    st.write(f"**Responsable** : {salon.get('responsable', 'N/A')}")
                
                with col_b:
                    st.markdown("**Contact**")
                    st.write(f"**Téléphone** : {salon.get('telephone', 'N/A')}")
                    st.write(f"**Email** : {salon.get('email', 'N/A')}")
                    st.write(f"**Code Admin** : {salon.get('code_admin', 'N/A')}")
                    statut_salon = "✅ Actif" if salon.get('actif', True) else "⛔ Désactivé"
                    st.write(f"**Statut** : {statut_salon}")

                st.markdown("---")
                st.markdown("#### ⚙️ Actions rapides")
                col_action_1, col_action_2 = st.columns(2)

                if salon.get('actif', True):
                    with col_action_1:
                        if st.button("⛔ Désactiver ce salon", key=f"deactivate_salon_{salon['salon_id']}"):
                            try:
                                ok = salon_model.modifier_salon(salon_id=salon['salon_id'], actif=False)
                                if ok:
                                    st.success(f"Salon {salon['salon_id']} désactivé avec succès.")
                                    st.rerun()
                                else:
                                    st.error("Échec de la désactivation du salon.")
                            except Exception as e:
                                st.error(f"Erreur pendant la désactivation : {e}")
                                st.exception(e)
                else:
                    with col_action_1:
                        if st.button("✅ Réactiver ce salon", key=f"activate_salon_{salon['salon_id']}"):
                            try:
                                ok = salon_model.modifier_salon(salon_id=salon['salon_id'], actif=True)
                                if ok:
                                    st.success(f"Salon {salon['salon_id']} réactivé avec succès.")
                                    st.rerun()
                                else:
                                    st.error("Échec de la réactivation du salon.")
                            except Exception as e:
                                st.error(f"Erreur pendant la réactivation : {e}")
                                st.exception(e)
    
    # ========================================================================
    # CRÉER UN SALON
    # ========================================================================
    with sub_tab2:
        st.markdown("### ➕ Créer un nouveau salon")
        
        # Prévisualiser l'ID du prochain salon (readonly pour l'utilisateur)
        next_id_preview = salon_model.obtenir_prochain_salon_id() or "Jaind_000"

        st.markdown("##### 🖼️ Logo du salon (optionnel)")
        st.caption(
            "Le logo est enregistré en base (`app_logo`), comme sur Render : en-tête de l’app et PDFs pour ce salon. "
            "Formats : PNG, JPG, JPEG. Choisissez le fichier avant de valider le formulaire ci‑dessous."
        )
        uploaded_logo = st.file_uploader(
            "Fichier logo",
            type=["png", "jpg", "jpeg"],
            key="super_admin_create_salon_logo",
            help="Stocké dans PostgreSQL (même mécanisme que la gestion du logo côté admin salon).",
        )
        if uploaded_logo is not None:
            st.image(uploaded_logo, caption="Aperçu", width=160)
        
        with st.form("form_creer_salon", clear_on_submit=True):
            st.markdown("#### 🏢 Informations du salon")
            
            col1, col2 = st.columns(2)
            
            with col1:
                nom_salon = st.text_input("Nom du salon *", placeholder="Ex: Atelier Jaind")
                quartier = st.text_input("Quartier *", placeholder="Ex: Médina")
                responsable = st.text_input("Responsable *", placeholder="Ex: Moustapha DIOP")
            
            with col2:
                telephone = st.text_input("Téléphone *", placeholder="Ex: 771234567")
                email = st.text_input("Email", placeholder="Ex: contact@salon.com")
            
            st.markdown("---")
            st.markdown("#### ✉️ Paramètres email du salon (SMTP)")
            st.caption("Chaque salon peut utiliser sa propre adresse email pour l'envoi automatique des messages clients.")

            col_smtp1, col_smtp2 = st.columns(2)
            with col_smtp1:
                smtp_host = st.text_input("SMTP host", value="smtp.gmail.com", help="Serveur SMTP (Gmail : smtp.gmail.com)")
                smtp_port = st.number_input("SMTP port", value=587, min_value=1, max_value=65535, step=1)
                smtp_use_tls = st.checkbox("Utiliser TLS", value=True)
                smtp_use_ssl = st.checkbox("Utiliser SSL", value=False)
            with col_smtp2:
                smtp_user = st.text_input("Adresse email d'envoi *", placeholder="Ex: mon.salon@gmail.com")
                smtp_password = st.text_input(
                    "Mot de passe d'application *",
                    type="password",
                    help="Pour Gmail, utilisez le mot de passe d'application (16 caractères), pas le mot de passe normal."
                )
                smtp_from = st.text_input(
                    "Adresse From (optionnel)",
                    placeholder="Laisser vide pour utiliser l'adresse d'envoi",
                )

            st.markdown("---")
            st.markdown("#### 🎨 Branding PDF du salon")
            col_pdf1, col_pdf2 = st.columns(2)
            with col_pdf1:
                pdf_slogan = st.text_input(
                    "Slogan PDF",
                    value="L'Elegance Sur Mesure",
                    help="Texte affiche dans les PDF de ce salon.",
                )
            with col_pdf2:
                pdf_theme_color = st.color_picker(
                    "Couleur principale PDF",
                    value="#9B8AB5",
                    help="Couleur appliquee aux bandeaux PDF du salon.",
                )
            
            st.markdown("---")
            st.markdown("#### 👤 Administrateur du salon")
            
            col3, col4 = st.columns(2)
            
            with col3:
                st.text_input(
                    "Salon ID (automatique)",
                    value=next_id_preview,
                    disabled=True,
                    help="ID généré automatiquement (n+1)."
                )
                
                code_admin = st.text_input(
                    "Code de connexion de l'admin *",
                    placeholder="Ex: JAIND_001",
                    help="Ce code servira pour la génération du salon_id (Ex: JAIND_001 → Jaind_001)"
                )
                password_admin = st.text_input(
                    "Mot de passe *",
                    type="password",
                    placeholder="Mot de passe"
                )
            
            with col4:
                nom_admin = st.text_input("Nom de l'admin *", placeholder="Ex: DIOP")
                prenom_admin = st.text_input("Prénom de l'admin *", placeholder="Ex: Moustapha")
            
            submitted = st.form_submit_button("💾 Créer le salon")
            
            if submitted:
                # Validation
                champs_obligatoires = [nom_salon, quartier, responsable, telephone, code_admin, password_admin, nom_admin, prenom_admin, smtp_user, smtp_password]
                if not all(champs_obligatoires):
                    st.error("❌ Veuillez remplir tous les champs obligatoires (*) y compris l'email et le mot de passe d'application du salon.")
                else:
                    # Créer le salon
                    try:
                        result = salon_model.creer_salon_avec_admin(
                            nom_salon=nom_salon,
                            quartier=quartier,
                            responsable=responsable,
                            telephone=telephone,
                            email=email,
                            code_admin=code_admin,
                            password_admin=password_admin,
                            nom_admin=nom_admin,
                            prenom_admin=prenom_admin,
                            smtp_host=smtp_host,
                            smtp_port=int(smtp_port),
                            smtp_user=smtp_user,
                            smtp_password=smtp_password,
                            smtp_from=smtp_from or None,
                            smtp_use_tls=smtp_use_tls,
                            smtp_use_ssl=smtp_use_ssl,
                            pdf_slogan=pdf_slogan,
                            pdf_theme_color=pdf_theme_color,
                            salon_id_force=next_id_preview
                        )
                        
                        if result and result.get('success'):
                            salon_id_new = result.get("salon_id")
                            if uploaded_logo is not None and salon_id_new:
                                try:
                                    logo_model = AppLogoModel(st.session_state.db_connection)
                                    logo_model.creer_tables()
                                    file_bytes = uploaded_logo.getvalue()
                                    file_ext = uploaded_logo.name.split(".")[-1].lower()
                                    mime_map = {
                                        "png": "image/png",
                                        "jpg": "image/jpeg",
                                        "jpeg": "image/jpeg",
                                    }
                                    mime_type = mime_map.get(file_ext, "image/png")
                                    if logo_model.sauvegarder_logo(
                                        salon_id=salon_id_new,
                                        logo_data=file_bytes,
                                        logo_name=uploaded_logo.name,
                                        mime_type=mime_type,
                                        uploaded_by=None,
                                        description="Logo défini à la création du salon (Super Admin)",
                                    ):
                                        st.session_state["super_admin_logo_saved"] = salon_id_new
                                    else:
                                        st.session_state["super_admin_logo_warn"] = True
                                except Exception as logo_err:
                                    st.session_state["super_admin_logo_warn"] = str(logo_err)
                            st.balloons()
                            st.session_state["super_admin_created_salon"] = {
                                "salon_id": result.get("salon_id"),
                                "code_admin": result.get("code_admin"),
                            }
                            st.rerun()
                        elif result:
                            st.error(f"❌ Erreur : {result.get('message', 'Erreur inconnue')}")
                        else:
                            st.error("❌ Erreur inconnue lors de la création (aucune réponse du modèle)")
                    
                    except Exception as e:
                        st.error(f"❌ Erreur lors de la création : {e}")
    
    # ========================================================================
    # MODIFIER UN SALON
    # ========================================================================
    with sub_tab3:
        st.markdown("### ✏️ Modifier un salon")
        
        # Sélectionner un salon à modifier
        salons = salon_model.lister_tous_salons()
        
        if not salons:
            st.warning("⚠️ Aucun salon disponible pour modification")
        else:
            salon_options = {f"{s['salon_id']} - {s['nom_salon']}": s for s in salons}
            
            selected = st.selectbox(
                "Sélectionner un salon à modifier",
                options=list(salon_options.keys()),
                key="select_salon_modify"
            )
            
            if selected:
                salon = salon_options[selected]
                
                st.markdown("---")
                st.markdown(f"### 📝 Modifier : {salon['nom_salon']} ({salon['salon_id']})")
                
                with st.form("form_modifier_salon", clear_on_submit=False):
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        nouveau_nom = st.text_input(
                            "Nom du salon",
                            value=salon.get('nom_salon', ''),
                            help="Nom commercial du salon"
                        )
                        nouveau_quartier = st.text_input(
                            "Quartier",
                            value=salon.get('quartier', ''),
                            help="Quartier/Adresse du salon"
                        )
                        nouveau_responsable = st.text_input(
                            "Responsable",
                            value=salon.get('responsable', ''),
                            help="Nom du responsable"
                        )
                    
                    with col2:
                        nouveau_telephone = st.text_input(
                            "Téléphone",
                            value=salon.get('telephone', ''),
                            help="Numéro de téléphone"
                        )
                        nouveau_email = st.text_input(
                            "Email",
                            value=salon.get('email', ''),
                            help="Adresse email"
                        )
                        statut_actif = st.checkbox(
                            "Salon actif",
                            value=salon.get('actif', True),
                            help="Cocher pour activer, décocher pour désactiver le salon"
                        )

                    st.markdown("#### 🎨 Branding PDF")
                    brand_col1, brand_col2 = st.columns(2)
                    with brand_col1:
                        nouveau_pdf_slogan = st.text_input(
                            "Slogan PDF",
                            value=salon.get('pdf_slogan') or "L'Elegance Sur Mesure",
                            help="Texte affiche dans les PDF du salon.",
                        )
                    with brand_col2:
                        nouveau_pdf_theme_color = st.color_picker(
                            "Couleur PDF",
                            value=salon.get('pdf_theme_color') or "#9B8AB5",
                            help="Couleur principale appliquee aux PDF du salon.",
                        )
                    
                    st.markdown("---")
                    
                    col_submit1, col_submit2 = st.columns(2)
                    
                    with col_submit1:
                        submitted = st.form_submit_button("💾 Enregistrer les modifications")
                    
                    with col_submit2:
                        if st.form_submit_button("❌ Annuler"):
                            st.rerun()
                    
                    if submitted:
                        # Vérifier qu'au moins un champ a été modifié
                        if (nouveau_nom == salon.get('nom_salon') and
                            nouveau_quartier == salon.get('quartier') and
                            nouveau_responsable == salon.get('responsable') and
                            nouveau_telephone == salon.get('telephone') and
                            nouveau_email == salon.get('email') and
                            statut_actif == salon.get('actif', True) and
                            nouveau_pdf_slogan == (salon.get('pdf_slogan') or "L'Elegance Sur Mesure") and
                            nouveau_pdf_theme_color == (salon.get('pdf_theme_color') or "#9B8AB5")):
                            st.info("ℹ️ Aucune modification détectée")
                        else:
                            # Appeler la méthode de modification
                            success = salon_model.modifier_salon(
                                salon_id=salon['salon_id'],
                                nom=nouveau_nom if nouveau_nom != salon.get('nom_salon') else None,
                                quartier=nouveau_quartier if nouveau_quartier != salon.get('quartier') else None,
                                responsable=nouveau_responsable if nouveau_responsable != salon.get('responsable') else None,
                                telephone=nouveau_telephone if nouveau_telephone != salon.get('telephone') else None,
                                email=nouveau_email if nouveau_email != salon.get('email') else None,
                                actif=statut_actif if statut_actif != salon.get('actif', True) else None,
                                pdf_slogan=nouveau_pdf_slogan if nouveau_pdf_slogan != (salon.get('pdf_slogan') or "L'Elegance Sur Mesure") else None,
                                pdf_theme_color=nouveau_pdf_theme_color if nouveau_pdf_theme_color != (salon.get('pdf_theme_color') or "#9B8AB5") else None
                            )
                            
                            if success:
                                st.balloons()
                                st.session_state["super_admin_updated_salon"] = salon['salon_id']
                                st.rerun()
                            else:
                                st.error("❌ Erreur lors de la modification du salon")


def afficher_gestion_utilisateurs(super_admin_ctrl, salon_model, couturier_model):
    """Onglet 3 : Gestion des utilisateurs (admins + employés)"""
    
    st.subheader("👥 Gestion des utilisateurs")
    
    # Sous-onglets
    sub_tab1, sub_tab2, sub_tab3 = st.tabs([
        "📋 Tous les utilisateurs",
        "➕ Créer un admin",
        "➕ Créer un employé"
    ])
    
    # ========================================================================
    # LISTE DES UTILISATEURS
    # ========================================================================
    with sub_tab1:
        st.markdown("### 📋 Tous les utilisateurs")
        
        # Filtre par salon
        salons = salon_model.lister_tous_salons()
        salon_filter_options = ["[Tous les salons]"] + [
            f"{s['salon_id']} - {s['nom_salon']}" for s in salons
        ]
        
        selected_filter = st.selectbox(
            "Filtrer par salon",
            options=salon_filter_options,
            key="filter_users_salon"
        )
        
        # Extraire le salon_id
        salon_id_filter = None
        if selected_filter != "[Tous les salons]":
            salon_id_filter = selected_filter.split(" - ")[0]
        
        # Récupérer les utilisateurs
        users = super_admin_ctrl.obtenir_tous_utilisateurs(salon_id_filter)
        
        if not users:
            st.info("ℹ️ Aucun utilisateur trouvé")
        else:
            st.success(f"✅ {len(users)} utilisateur(s) trouvé(s)")
            
            # Statistiques rapides
            nb_admins = len([u for u in users if u['role'] == 'admin'])
            nb_employes = len([u for u in users if u['role'] == 'employe'])
            
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("👥 Total", len(users))
            with col2:
                st.metric("🔑 Admins", nb_admins)
            with col3:
                st.metric("👷 Employés", nb_employes)
            
            st.markdown("---")
            
            # Tableau des utilisateurs
            df_users = pd.DataFrame(users)
            if 'actif' in df_users.columns:
                df_users['statut'] = df_users['actif'].apply(lambda x: "✅ Actif" if x else "⛔ Désactivé")

            colonnes = ['id', 'code_couturier', 'nom', 'prenom', 'role', 'salon_id',
                        'email', 'telephone', 'statut', 'date_creation']
            colonnes_existantes = [c for c in colonnes if c in df_users.columns]

            st.dataframe(
                df_users[colonnes_existantes],
                use_container_width=True,
                hide_index=True
            )

            st.markdown("---")

            # Actions d'activation / désactivation par utilisateur
            st.markdown("### 🔒 Activer / désactiver un utilisateur")
            for user in users:
                col_u1, col_u2, col_u3, col_u4 = st.columns([3, 2, 2, 2])
                with col_u1:
                    st.write(f"**{user['code_couturier']} - {user['prenom']} {user['nom']}** ({user['role']})")
                with col_u2:
                    st.write("Actif :" if user.get('actif', True) else "Désactivé :")
                with col_u3:
                    if user.get('actif', True):
                        if st.button("⛔ Désactiver", key=f"desactiver_user_{user['id']}"):
                            ok = couturier_model.mettre_a_jour_statut_actif(user['id'], False)
                            if ok:
                                st.success(f"Utilisateur {user['code_couturier']} désactivé.")
                                st.rerun()
                            else:
                                st.error("Erreur lors de la désactivation de l'utilisateur.")
                with col_u4:
                    if not user.get('actif', True):
                        if st.button("✅ Réactiver", key=f"activer_user_{user['id']}"):
                            ok = couturier_model.mettre_a_jour_statut_actif(user['id'], True)
                            if ok:
                                st.success(f"Utilisateur {user['code_couturier']} réactivé.")
                                st.rerun()
                            else:
                                st.error("Erreur lors de l'activation de l'utilisateur.")

            st.markdown("---")
            st.markdown("### 🔑 Réinitialiser le mot de passe d'un employé")
            employes = [u for u in users if u.get('role') == 'employe']

            if not employes:
                st.info("ℹ️ Aucun employé disponible pour une réinitialisation de mot de passe.")
            else:
                employe_options = {
                    f"{u['code_couturier']} - {u.get('prenom', '')} {u.get('nom', '')} ({u.get('salon_id', 'N/A')})": u
                    for u in employes
                }

                with st.form("form_reset_password_employe"):
                    selected_employe_label = st.selectbox(
                        "Employé *",
                        options=list(employe_options.keys()),
                        help="Choisissez l'employé dont vous voulez réinitialiser le mot de passe."
                    )
                    nouveau_password = st.text_input(
                        "Nouveau mot de passe *",
                        type="password",
                        help="Minimum recommandé : 6 caractères."
                    )
                    confirmer_password = st.text_input(
                        "Confirmer le nouveau mot de passe *",
                        type="password"
                    )

                    submitted_reset = st.form_submit_button("🔄 Réinitialiser le mot de passe")

                    if submitted_reset:
                        employe_data = employe_options[selected_employe_label]
                        employe_id = employe_data.get("id")

                        if not nouveau_password or not confirmer_password:
                            st.error("❌ Veuillez renseigner les deux champs de mot de passe.")
                        elif nouveau_password != confirmer_password:
                            st.error("❌ Les mots de passe ne correspondent pas.")
                        elif len(nouveau_password) < 6:
                            st.error("❌ Le mot de passe doit contenir au moins 6 caractères.")
                        elif not employe_id:
                            st.error("❌ Impossible d'identifier l'employé sélectionné.")
                        else:
                            try:
                                ok = couturier_model.reinitialiser_mot_de_passe(
                                    couturier_id=employe_id,
                                    nouveau_password=nouveau_password
                                )
                                if ok:
                                    st.success(
                                        f"✅ Mot de passe réinitialisé pour {employe_data.get('code_couturier')}."
                                    )
                                else:
                                    st.error(
                                        "❌ Échec de la réinitialisation du mot de passe (vérifiez l'état de la base)."
                                    )
                            except Exception as e:
                                st.error(f"❌ Exception pendant la réinitialisation : {e}")
                                st.exception(e)
    
    # ========================================================================
    # CRÉER UN ADMIN
    # ========================================================================
    with sub_tab2:
        st.markdown("### ➕ Créer un administrateur de salon")
        
        st.info("💡 **Astuce** : Utilisez l'onglet 'Créer un salon' pour créer un salon avec son admin en une seule fois")
        
        with st.form("form_creer_admin"):
            # Sélectionner un salon
            salons = salon_model.lister_tous_salons()
            
            if not salons:
                st.warning("⚠️ Aucun salon disponible. Créez d'abord un salon.")
                st.form_submit_button("Créer", disabled=True)
            else:
                salon_options = {f"{s['salon_id']} - {s['nom_salon']}": s['salon_id'] for s in salons}
                
                selected_salon = st.selectbox(
                    "Salon *",
                    options=list(salon_options.keys()),
                    help="Salon auquel cet admin sera rattaché"
                )
                
                col1, col2 = st.columns(2)
                
                with col1:
                    code_couturier = st.text_input("Code de connexion *", placeholder="Ex: ADMIN_002")
                    password = st.text_input("Mot de passe *", type="password")
                
                with col2:
                    nom = st.text_input("Nom *")
                    prenom = st.text_input("Prénom *")
                
                col3, col4 = st.columns(2)
                
                with col3:
                    email = st.text_input("Email")
                
                with col4:
                    telephone = st.text_input("Téléphone")
                
                submitted = st.form_submit_button("💾 Créer l'admin")
                
                if submitted:
                    if not all([selected_salon, code_couturier, password, nom, prenom]):
                        st.error("❌ Veuillez remplir tous les champs obligatoires (*)")
                    else:
                        salon_id = salon_options[selected_salon]
                        try:
                            user_id = couturier_model.creer_utilisateur(
                                code_couturier=code_couturier,
                                password=password,
                                nom=nom,
                                prenom=prenom,
                                role='admin',
                                email=email,
                                telephone=telephone,
                                salon_id=salon_id
                            )
                            
                            if user_id:
                                st.success(f"""
                                ✅ Admin créé avec succès !
                                
                                **ID** : {user_id}  
                                **Code** : {code_couturier}  
                                **Salon** : {salon_id}
                                """)
                                st.balloons()
                            else:
                                detail = getattr(couturier_model, "last_error", None)
                                if detail:
                                    st.error(f"❌ Création admin impossible : {detail}")
                                else:
                                    st.error("❌ Erreur lors de la création (cause non remontée par le modèle).")
                        except Exception as e:
                            st.error(f"❌ Exception inattendue pendant la création admin : {e}")
                            st.exception(e)
    
    # ========================================================================
    # CRÉER UN EMPLOYÉ
    # ========================================================================
    with sub_tab3:
        st.markdown("### ➕ Créer un employé")
        
        with st.form("form_creer_employe"):
            # Sélectionner un salon
            salons = salon_model.lister_tous_salons()
            
            if not salons:
                st.warning("⚠️ Aucun salon disponible. Créez d'abord un salon.")
                st.form_submit_button("Créer", disabled=True)
            else:
                salon_options = {f"{s['salon_id']} - {s['nom_salon']}": s['salon_id'] for s in salons}
                
                selected_salon = st.selectbox(
                    "Salon *",
                    options=list(salon_options.keys()),
                    help="Salon auquel cet employé sera rattaché"
                )
                
                st.info(f"💡 L'employé héritera automatiquement du salon_id : `{salon_options[selected_salon]}`")
                
                col1, col2 = st.columns(2)
                
                with col1:
                    code_couturier = st.text_input(
                        "Code de connexion *",
                        placeholder="Ex: EMP_001",
                        help="Format recommandé : EMP_XXX"
                    )
                    password = st.text_input("Mot de passe *", type="password")
                
                with col2:
                    nom = st.text_input("Nom *")
                    prenom = st.text_input("Prénom *")
                
                col3, col4 = st.columns(2)
                
                with col3:
                    email = st.text_input("Email")
                
                with col4:
                    telephone = st.text_input("Téléphone")
                
                submitted = st.form_submit_button("💾 Créer l'employé")
                
                if submitted:
                    if not all([selected_salon, code_couturier, password, nom, prenom]):
                        st.error("❌ Veuillez remplir tous les champs obligatoires (*)")
                    else:
                        salon_id = salon_options[selected_salon]
                        try:
                            user_id = couturier_model.creer_utilisateur(
                                code_couturier=code_couturier,
                                password=password,
                                nom=nom,
                                prenom=prenom,
                                role='employe',
                                email=email,
                                telephone=telephone,
                                salon_id=salon_id
                            )
                            
                            if user_id:
                                st.success(f"""
                                ✅ Employé créé avec succès !
                                
                                **ID** : {user_id}  
                                **Code** : {code_couturier}  
                                **Salon** : {salon_id}
                                **Role** : Employé
                                
                                L'employé peut maintenant se connecter avec ce code.
                                """)
                                st.balloons()
                            else:
                                detail = getattr(couturier_model, "last_error", None)
                                if detail:
                                    st.error(f"❌ Création employé impossible : {detail}")
                                else:
                                    st.error("❌ Erreur lors de la création (cause non remontée par le modèle).")
                        except Exception as e:
                            st.error(f"❌ Exception inattendue pendant la création employé : {e}")
                            st.exception(e)


def afficher_toutes_commandes(super_admin_ctrl, salon_model):
    """Onglet 4 : Toutes les commandes"""
    
    st.subheader("📦 Toutes les commandes")
    
    # ------------------------------------------------------------------
    # Filtres : salon + période
    # ------------------------------------------------------------------

    # Filtre par salon
    salons = salon_model.lister_tous_salons()
    salon_filter_options = ["[Tous les salons]"] + [
        f"{s['salon_id']} - {s['nom_salon']}" for s in salons
    ]
    
    selected_filter = st.selectbox(
        "Filtrer par salon",
        options=salon_filter_options,
        key="filter_commandes_salon"
    )

    col_date1, col_date2 = st.columns(2)
    with col_date1:
        date_debut = st.date_input(
            "Date de début",
            value=datetime.now().date() - timedelta(days=30),
            key="superadmin_cmd_debut",
        )
    with col_date2:
        date_fin = st.date_input(
            "Date de fin",
            value=datetime.now().date(),
            key="superadmin_cmd_fin",
        )
    
    # Extraire le salon_id
    salon_id_filter = None
    if selected_filter != "[Tous les salons]":
        salon_id_filter = selected_filter.split(" - ")[0]

    def _norm_salon_id(value):
        return str(value or "").strip().lower()
    
    # Récupérer les statistiques réelles du salon (sans limite)
    if salon_id_filter:
        # KPI ciblés du salon sélectionné (logique contrôleur)
        salon_stats = super_admin_ctrl.obtenir_kpis_salon(
            salon_id=salon_id_filter,
            date_debut=datetime.combine(date_debut, datetime.min.time()),
            date_fin=datetime.combine(date_fin, datetime.max.time()),
        )
        
        if salon_stats:
            st.markdown(f"### 🏢 Salon : {salon_stats['nom_salon']} ({salon_id_filter})")
            st.markdown("---")
            
            # Statistiques réelles du salon
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                # Compter toutes les commandes du salon (pas seulement les 200 premières)
                nb_commandes_reel = int(salon_stats.get('nb_commandes', 0))
                st.metric("📦 Commandes", nb_commandes_reel)
            
            with col2:
                ca_total_reel = float(salon_stats.get('ca_total', 0))
                st.metric("💰 CA Total", f"{ca_total_reel:,.0f} FCFA")
            
            with col3:
                avances_total_reel = float(salon_stats.get('avances', 0))
                st.metric("💳 Encaissé", f"{avances_total_reel:,.0f} FCFA")
            
            with col4:
                reste_total_reel = float(salon_stats.get('reste', 0))
                st.metric("⏳ Reste", f"{reste_total_reel:,.0f} FCFA")
            
            st.markdown("---")
        else:
            st.warning(f"⚠️ Aucune statistique disponible pour le salon {salon_id_filter}")
    else:
        # Vue globale - afficher les statistiques de tous les salons
        stats_globales = super_admin_ctrl.obtenir_statistiques_globales(
            date_debut=datetime.combine(date_debut, datetime.min.time()),
            date_fin=datetime.combine(date_fin, datetime.max.time()),
        )
        if stats_globales:
            st.markdown("### 🌐 Vue globale - Tous les salons")
            st.markdown("---")
            
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                st.metric("📦 Commandes", stats_globales.get('nb_commandes_total', 0))
            
            with col2:
                st.metric("💰 CA Total", f"{stats_globales.get('ca_total', 0):,.0f} FCFA")
            
            with col3:
                st.metric("💳 Encaissé", f"{stats_globales.get('avances_total', 0):,.0f} FCFA")
            
            with col4:
                st.metric("⏳ Reste", f"{stats_globales.get('reste_total', 0):,.0f} FCFA")
            
            st.markdown("---")

            # Comparatif des salons sur les commandes et le CA
            stats_par_salon = super_admin_ctrl.obtenir_statistiques_par_salon(
                date_debut=datetime.combine(date_debut, datetime.min.time()),
                date_fin=datetime.combine(date_fin, datetime.max.time()),
            )
            if stats_par_salon:
                df_salons = pd.DataFrame(stats_par_salon)

                colonnes_comp = ['salon_id', 'nom_salon', 'nb_commandes', 'ca_total', 'avances', 'reste']
                colonnes_existantes = [c for c in colonnes_comp if c in df_salons.columns]

                if colonnes_existantes:
                    df_comp = df_salons[colonnes_existantes].copy()
                    df_comp = df_comp.sort_values('ca_total', ascending=False)
                    df_comp = df_comp.rename(columns={
                        'salon_id': 'Salon ID',
                        'nom_salon': 'Salon',
                        'nb_commandes': 'Commandes',
                        'ca_total': 'CA (FCFA)',
                        'avances': 'Encaissé (FCFA)',
                        'reste': 'Reste (FCFA)',
                    })

                    st.markdown("### 🏆 Comparatif des salons (commandes & chiffres d'affaires)")
                    st.dataframe(df_comp, use_container_width=True, hide_index=True)

                    # Nuage de points CA vs Commandes pour voir rapidement les salons vendeurs
                    if all(col in df_salons.columns for col in ['ca_total', 'nb_commandes', 'nom_salon']):
                        st.markdown("#### 💎 CA vs Nombre de commandes (tous les salons)")
                        fig_cmd = px.scatter(
                            df_salons,
                            x='ca_total',
                            y='nb_commandes',
                            size='nb_commandes',
                            hover_name='nom_salon',
                            labels={
                                'ca_total': 'CA (FCFA)',
                                'nb_commandes': 'Nombre de commandes',
                            },
                            title="Salons vendeurs : plus le point est gros et à droite, plus le salon vend",
                        )
                        st.plotly_chart(fig_cmd, use_container_width=True)
    
    # Récupérer les commandes (limitées pour l'affichage) sur la période
    commandes = super_admin_ctrl.obtenir_toutes_commandes(
        salon_id_filter,
        limit=200,
        date_debut=datetime.combine(date_debut, datetime.min.time()),
        date_fin=datetime.combine(date_fin, datetime.max.time()),
    )
    
    if not commandes:
        st.info("ℹ️ Aucune commande trouvée")
    else:
        st.markdown("### 📋 Liste des commandes (200 dernières)")
        st.info(
            "ℹ️ Affichage des 200 dernières commandes sur la période sélectionnée. "
            "Les statistiques ci-dessus sont calculées sur cette même période."
        )
        
        st.markdown("---")
        
        # Tableau des commandes
        df_cmd = pd.DataFrame(commandes)
        if 'est_supprime' in df_cmd.columns:
            df_cmd['statut'] = df_cmd.apply(
                lambda row: "Supprimée (admin)" if bool(row.get('est_supprime', False)) else row.get('statut'),
                axis=1
            )
        
        colonnes = ['id', 'modele', 'prix_total', 'avance', 'reste', 'statut',
                   'date_creation', 'salon_id', 'client_nom', 'client_prenom',
                   'couturier_code', 'date_suppression', 'motif_suppression']
        colonnes_existantes = [c for c in colonnes if c in df_cmd.columns]
        
        st.dataframe(
            df_cmd[colonnes_existantes],
            use_container_width=True,
            hide_index=True,
        )

        # ------------------------------------------------------------------
        # Visualisations claires et nettes pour les commandes
        # ------------------------------------------------------------------
        try:
            df_cmd['date_creation'] = pd.to_datetime(df_cmd['date_creation'])

            # 1) CA par jour sur la période
            st.markdown("#### 📈 Chiffre d'affaires par jour")
            df_ca_jour = (
                df_cmd.groupby(df_cmd['date_creation'].dt.date)['prix_total']
                .sum()
                .reset_index()
                .rename(columns={'date_creation': 'date_creation', 'prix_total': 'prix_total'})
            )

            fig_ca_jour = px.bar(
                df_ca_jour,
                x='date_creation',
                y='prix_total',
                labels={'date_creation': 'Date', 'prix_total': 'CA (FCFA)'},
                title="Évolution du chiffre d'affaires sur la période",
            )
            fig_ca_jour.update_layout(xaxis_tickangle=-45, height=400)
            st.plotly_chart(fig_ca_jour, use_container_width=True)

            st.markdown("---")

            # 2) Répartition des statuts de commandes
            if 'statut' in df_cmd.columns:
                st.markdown("#### 🧩 Répartition des statuts de commandes")
                df_statut = (
                    df_cmd.groupby('statut')['id']
                    .count()
                    .reset_index()
                    .rename(columns={'id': 'nb_commandes'})
                )

                fig_statut = px.pie(
                    df_statut,
                    values='nb_commandes',
                    names='statut',
                    title="Répartition des commandes par statut",
                    hole=0.35,
                )
                st.plotly_chart(fig_statut, use_container_width=True)
        except Exception:
            # En cas de souci de données, on ne bloque pas l'affichage du tableau
            pass


def afficher_demandes_globales_super_admin(commande_model, salon_model):
    """Onglet 6 : Demandes en attente (tous salons) pour le SUPER_ADMIN"""
    
    st.subheader("🔔 Demandes en attente (tous les salons)")
    
    # Identifiant du super admin pour tracer la validation
    super_admin_id = None
    try:
        if st.session_state.get('couturier_data'):
            super_admin_id = st.session_state.couturier_data.get('id')
    except Exception:
        pass

    # Filtres : salon + période
    salons = salon_model.lister_tous_salons()
    salon_options = ["[Tous les salons]"] + [f"{s['salon_id']} - {s['nom_salon']}" for s in salons]
    selected_salon = st.selectbox("Filtrer par salon", options=salon_options, key="superadmin_demandes_salon")

    salon_id_filter = None
    if selected_salon != "[Tous les salons]":
        salon_id_filter = selected_salon.split(" - ")[0]

    col_d1, col_d2 = st.columns(2)
    with col_d1:
        date_debut = st.date_input(
            "Date de début",
            value=datetime.now().date() - timedelta(days=30),
            key="superadmin_demandes_debut"
        )
    with col_d2:
        date_fin = st.date_input(
            "Date de fin",
            value=datetime.now().date(),
            key="superadmin_demandes_fin"
        )

    date_debut_dt = datetime.combine(date_debut, datetime.min.time())
    date_fin_dt = datetime.combine(date_fin, datetime.max.time())

    st.markdown("---")

    # Récupérer les demandes filtrées
    demandes = commande_model.lister_demandes_validation(
        salon_id=salon_id_filter,
        date_debut=date_debut_dt,
        date_fin=date_fin_dt,
    )

    if not demandes:
        st.success("✅ Aucune demande en attente pour ces filtres.")
        return

    nb_paiements = len([d for d in demandes if d['type_action'] == 'paiement'])
    nb_fermetures = len([d for d in demandes if d['type_action'] == 'fermeture_demande'])

    col_m1, col_m2, col_m3 = st.columns(3)
    with col_m1:
        st.metric("📦 Total demandes", len(demandes))
    with col_m2:
        st.metric("💰 Paiements", nb_paiements)
    with col_m3:
        st.metric("🔒 Fermetures", nb_fermetures)

    st.markdown("---")

    for demande in demandes:
        salon_label = demande.get('salon_id', 'N/A')
        if 'salon_nom' in demande and demande['salon_nom']:
            salon_label = f"{demande['salon_id']} - {demande['salon_nom']}"

        with st.expander(
            f"🔔 {demande['type_action'].upper()} - Cmd #{demande['commande_id']} - "
            f"{demande['client_prenom']} {demande['client_nom']} - {demande['modele']} "
            f"(Salon: {salon_label})",
            expanded=False
        ):
            col_info1, col_info2 = st.columns(2)

            with col_info1:
                st.markdown("**📋 Informations demande**")
                st.write(f"**Type :** {demande['type_action']}")
                st.write(f"**Date :** {demande['date_creation']}")
                st.write(f"**Employé :** {demande['couturier_prenom']} {demande['couturier_nom']}")
                if demande.get('commentaire'):
                    st.write(f"**Commentaire :** {demande['commentaire']}")

            with col_info2:
                st.markdown("**📦 Informations commande**")
                st.write(f"**Modèle :** {demande['modele']}")
                st.write(f"**Client :** {demande['client_prenom']} {demande['client_nom']}")
                st.write(f"**Prix total :** {demande['prix_total']:,.0f} FCFA")
                st.write(f"**Avance actuelle :** {demande['avance']:,.0f} FCFA")
                st.write(f"**Reste actuel :** {demande['reste']:,.0f} FCFA")
                st.write(f"**Statut avant :** {demande['statut_avant']}")
                st.write(f"**Statut après :** {demande['statut_apres']}")

            st.markdown("---")

            col_act1, col_act2 = st.columns(2)

            with col_act1:
                with st.form(f"form_valider_super_{demande['id']}", clear_on_submit=True):
                    commentaire_admin = st.text_area(
                        "Commentaire de validation (optionnel)",
                        key=f"comment_val_super_{demande['id']}",
                        height=80
                    )
                    if st.form_submit_button("✅ Valider", type="primary"):
                        try:
                            if commande_model.valider_fermeture(
                                demande['id'],
                                super_admin_id or 0,
                                True,
                                commentaire_admin
                            ):
                                st.success("✅ Demande validée avec succès !")
                                st.balloons()
                                st.rerun()
                            else:
                                st.error("❌ Erreur lors de la validation")
                        except Exception as e:
                            st.error(f"❌ Erreur : {e}")

            with col_act2:
                with st.form(f"form_rejeter_super_{demande['id']}", clear_on_submit=True):
                    commentaire_rejet = st.text_area(
                        "Raison du rejet (optionnel)",
                        key=f"comment_rej_super_{demande['id']}",
                        height=80
                    )
                    if st.form_submit_button("❌ Rejeter"):
                        try:
                            if commande_model.valider_fermeture(
                                demande['id'],
                                super_admin_id or 0,
                                False,
                                commentaire_rejet
                            ):
                                st.warning("⚠️ Demande rejetée")
                                st.rerun()
                            else:
                                st.error("❌ Erreur lors du rejet")
                        except Exception as e:
                            st.error(f"❌ Erreur : {e}")

            st.markdown("---")

def afficher_statistiques_avancees(super_admin_ctrl, salon_model):
    """Onglet 5 : Statistiques avancées avec graphiques professionnels pour investisseurs"""
    
    st.subheader("📈 Statistiques avancées - Analyse financière")

    # ------------------------------------------------------------------
    # Filtre de période pour toutes les visualisations
    # ------------------------------------------------------------------
    col_d1, col_d2 = st.columns(2)
    with col_d1:
        date_debut = st.date_input(
            "Date de début",
            value=datetime.now().date() - timedelta(days=90),
            key="superadmin_stats_debut",
        )
    with col_d2:
        date_fin = st.date_input(
            "Date de fin",
            value=datetime.now().date(),
            key="superadmin_stats_fin",
        )
    
    # Récupérer les données (filtrées par période)
    stats_par_salon = super_admin_ctrl.obtenir_statistiques_par_salon(
        date_debut=datetime.combine(date_debut, datetime.min.time()),
        date_fin=datetime.combine(date_fin, datetime.max.time()),
    )
    
    if not stats_par_salon:
        st.info("ℹ️ Aucune donnée disponible")
        return
    
    df = pd.DataFrame(stats_par_salon)
    
    # Calculer les métriques globales
    ca_total_global = df['ca_total'].sum()
    benefice_total_global = df['benefice'].sum()
    charges_total_global = df['charges'].sum()
    marge_moyenne = (benefice_total_global / ca_total_global * 100) if ca_total_global > 0 else 0
    encaisse_total = df['avances'].sum()
    taux_encaissement_global = (encaisse_total / ca_total_global * 100) if ca_total_global > 0 else 0
    
    # ======================================================================
    # SECTION 1 : INDICATEURS CLÉS DE PERFORMANCE (KPIs)
    # ======================================================================
    st.markdown("### 📊 Indicateurs clés de performance")
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric(
            label="💰 Chiffre d'affaires total",
            value=f"{ca_total_global:,.0f} FCFA",
            delta=None
        )
    
    with col2:
        st.metric(
            label="💵 Bénéfice total",
            value=f"{benefice_total_global:,.0f} FCFA",
            delta=f"Marge: {marge_moyenne:.1f}%"
        )
    
    with col3:
        st.metric(
            label="💸 Charges totales",
            value=f"{charges_total_global:,.0f} FCFA",
            delta=None
        )
    
    with col4:
        st.metric(
            label="💳 Taux d'encaissement",
            value=f"{taux_encaissement_global:.1f}%",
            delta=None
        )
    
    st.markdown("---")
    
    # ======================================================================
    # SECTION 2 : COMPARAISON FINANCIÈRE PAR SALON (Barres groupées)
    # ======================================================================
    st.markdown("### 💼 Comparaison financière des salons")
    
    # Préparer les données pour le graphique groupé
    df_sorted = df.sort_values('ca_total', ascending=False)
    
    fig_financial = go.Figure()
    
    # Barres pour CA
    fig_financial.add_trace(go.Bar(
        name='CA',
        x=df_sorted['nom_salon'],
        y=df_sorted['ca_total'],
        marker_color='#2E86AB',
        text=[f"{x:,.0f}" for x in df_sorted['ca_total']],
        textposition='outside',
        textfont=dict(size=9)
    ))
    
    # Barres pour Encaissé
    fig_financial.add_trace(go.Bar(
        name='Encaissé',
        x=df_sorted['nom_salon'],
        y=df_sorted['avances'],
        marker_color='#06A77D',
        text=[f"{x:,.0f}" for x in df_sorted['avances']],
        textposition='outside',
        textfont=dict(size=9)
    ))
    
    # Barres pour Charges
    fig_financial.add_trace(go.Bar(
        name='Charges',
        x=df_sorted['nom_salon'],
        y=df_sorted['charges'],
        marker_color='#F24236',
        text=[f"{x:,.0f}" for x in df_sorted['charges']],
        textposition='outside',
        textfont=dict(size=9)
    ))
    
    # Barres pour Bénéfice
    fig_financial.add_trace(go.Bar(
        name='Bénéfice',
        x=df_sorted['nom_salon'],
        y=df_sorted['benefice'],
        marker_color='#F18F01',
        text=[f"{x:,.0f}" for x in df_sorted['benefice']],
        textposition='outside',
        textfont=dict(size=9)
    ))
    
    fig_financial.update_layout(
        barmode='group',
        title="Comparaison financière : CA, Encaissé, Charges et Bénéfice par salon",
        xaxis_title="Salon",
        yaxis_title="Montant (FCFA)",
        height=500,
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        xaxis=dict(tickangle=-45)
    )
    
    st.plotly_chart(fig_financial, use_container_width=True)
    
    st.markdown("---")
    
    # ======================================================================
    # SECTION 3 : RÉPARTITION DU CA PAR SALON (Aires empilées)
    # ======================================================================
    st.markdown("### 📈 Répartition du chiffre d'affaires par salon")
    
    fig_stacked = go.Figure()
    
    # Encaissé
    fig_stacked.add_trace(go.Bar(
        name='Encaissé',
        x=df_sorted['nom_salon'],
        y=df_sorted['avances'],
        marker_color='#06A77D',
        text=[f"{x:,.0f}" for x in df_sorted['avances']],
        textposition='inside',
        textfont=dict(size=9, color='white')
    ))
    
    # Reste à encaisser
    fig_stacked.add_trace(go.Bar(
        name='Reste à encaisser',
        x=df_sorted['nom_salon'],
        y=df_sorted['reste'],
        marker_color='#FFC107',
        text=[f"{x:,.0f}" for x in df_sorted['reste']],
        textposition='inside',
        textfont=dict(size=9, color='black')
    ))
    
    fig_stacked.update_layout(
        barmode='stack',
        title="Répartition du CA : Encaissé vs Reste à encaisser",
        xaxis_title="Salon",
        yaxis_title="Montant (FCFA)",
        height=450,
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        xaxis=dict(tickangle=-45)
    )
    
    st.plotly_chart(fig_stacked, use_container_width=True)
    
    st.markdown("---")
    
    # ======================================================================
    # SECTION 4 : MARGES BÉNÉFICIAIRES PAR SALON
    # ======================================================================
    st.markdown("### 📊 Marge bénéficiaire par salon")
    
    # Calculer la marge pour chaque salon
    df_sorted['marge_pct'] = (df_sorted['benefice'] / df_sorted['ca_total'] * 100).round(2)
    df_sorted['marge_pct'] = df_sorted['marge_pct'].fillna(0)
    
    # Trier par marge décroissante
    df_marge = df_sorted.sort_values('marge_pct', ascending=False)
    
    fig_marge = go.Figure()
    
    # Couleurs conditionnelles : vert pour positif, rouge pour négatif
    colors = ['#06A77D' if x >= 0 else '#F24236' for x in df_marge['marge_pct']]
    
    fig_marge.add_trace(go.Bar(
        x=df_marge['nom_salon'],
        y=df_marge['marge_pct'],
        marker_color=colors,
        text=[f"{x:.1f}%" for x in df_marge['marge_pct']],
        textposition='outside',
        textfont=dict(size=10, color='black')
    ))
    
    fig_marge.update_layout(
        title="Marge bénéficiaire (%) = (Bénéfice / CA) × 100",
        xaxis_title="Salon",
        yaxis_title="Marge (%)",
        height=450,
        xaxis=dict(tickangle=-45),
        shapes=[{
            'type': 'line',
            'x0': -0.5,
            'x1': len(df_marge) - 0.5,
            'y0': 0,
            'y1': 0,
            'line': {'color': 'black', 'width': 2, 'dash': 'dash'}
        }]
    )
    
    st.plotly_chart(fig_marge, use_container_width=True)
    
    st.markdown("---")
    
    # ======================================================================
    # SECTION 5 : ÉVOLUTION TEMPORELLE COMPARATIVE
    # ======================================================================
    st.markdown("### 📅 Évolution temporelle comparative des salons")
    
    salons = salon_model.lister_tous_salons()
    salon_options_evo = {f"{s['salon_id']} - {s['nom_salon']}": s['salon_id'] for s in salons}
    
    if not salon_options_evo:
        st.warning("⚠️ Aucun salon disponible")
    else:
        col_sel1, col_sel2 = st.columns(2)
        
        with col_sel1:
            selected_salons_evo = st.multiselect(
                "Sélectionner les salons à comparer (max 5)",
                options=list(salon_options_evo.keys()),
                default=list(salon_options_evo.keys())[:min(3, len(salon_options_evo))] if salon_options_evo else [],
                key="select_salons_evolution",
                help="Sélectionnez jusqu'à 5 salons pour comparer leur évolution"
            )
        
        with col_sel2:
            periode_mois = st.number_input(
                "Période (nombre de mois)",
                min_value=1,
                max_value=24,
                value=6,
                step=1,
                key="periode_mois_evolution",
                help="Nombre de mois à afficher dans le graphique"
            )
        
        if selected_salons_evo and len(selected_salons_evo) <= 5:
            fig_evo_comparative = go.Figure()
            
            # Couleurs pour les différentes lignes
            colors_evo = ['#2E86AB', '#06A77D', '#F18F01', '#F24236', '#9B59B6']
            
            for idx, salon_key in enumerate(selected_salons_evo):
                salon_id_evo = salon_options_evo[salon_key]
                salon_nom = salon_key.split(' - ', 1)[1] if ' - ' in salon_key else salon_id_evo
                
                # Récupérer l'évolution pour ce salon
                evolution = super_admin_ctrl.obtenir_evolution_mensuelle(salon_id_evo, periode_mois)
                
                if evolution:
                    df_evo = pd.DataFrame(evolution)
                    
                    fig_evo_comparative.add_trace(go.Scatter(
                        x=df_evo['mois'],
                        y=df_evo['ca'],
                        mode='lines+markers',
                        name=f'{salon_nom} - CA',
                        line=dict(color=colors_evo[idx % len(colors_evo)], width=3),
                        marker=dict(size=8),
                        legendgroup=salon_nom
                    ))
                    
                    fig_evo_comparative.add_trace(go.Scatter(
                        x=df_evo['mois'],
                        y=df_evo['encaisse'],
                        mode='lines+markers',
                        name=f'{salon_nom} - Encaissé',
                        line=dict(color=colors_evo[idx % len(colors_evo)], width=2, dash='dash'),
                        marker=dict(size=6),
                        legendgroup=salon_nom
                    ))
            
            fig_evo_comparative.update_layout(
                title=f"Évolution du CA et de l'encaissé sur {periode_mois} mois",
                xaxis_title="Mois",
                yaxis_title="Montant (FCFA)",
                height=500,
                hovermode='x unified',
                legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
            )
            
            st.plotly_chart(fig_evo_comparative, use_container_width=True)
        elif selected_salons_evo and len(selected_salons_evo) > 5:
            st.warning("⚠️ Veuillez sélectionner au maximum 5 salons pour une meilleure lisibilité.")
    
    st.markdown("---")
    
    # ======================================================================
    # SECTION 6 : TABLEAU DE SYNTHÈSE FINANCIÈRE
    # ======================================================================
    st.markdown("### 📋 Tableau de synthèse financière")
    
    df_synthese = df_sorted.copy()
    df_synthese['marge_pct'] = (df_synthese['benefice'] / df_synthese['ca_total'] * 100).round(2)
    df_synthese['marge_pct'] = df_synthese['marge_pct'].fillna(0)
    df_synthese['taux_encaissement'] = (df_synthese['avances'] / df_synthese['ca_total'] * 100).round(2)
    df_synthese['taux_encaissement'] = df_synthese['taux_encaissement'].fillna(0)
    
    # Créer le tableau de synthèse
    df_display = pd.DataFrame({
        'Salon': df_synthese['nom_salon'],
        'CA (FCFA)': [f"{x:,.0f}" for x in df_synthese['ca_total']],
        'Encaissé (FCFA)': [f"{x:,.0f}" for x in df_synthese['avances']],
        'Reste (FCFA)': [f"{x:,.0f}" for x in df_synthese['reste']],
        'Charges (FCFA)': [f"{x:,.0f}" for x in df_synthese['charges']],
        'Bénéfice (FCFA)': [f"{x:,.0f}" for x in df_synthese['benefice']],
        'Marge (%)': [f"{x:.2f}%" for x in df_synthese['marge_pct']],
        'Taux encaissement (%)': [f"{x:.2f}%" for x in df_synthese['taux_encaissement']],
        'Clients': df_synthese['nb_clients'],
        'Commandes': df_synthese['nb_commandes']
    })
    
    st.dataframe(df_display, use_container_width=True, hide_index=True)


def afficher_rapports(super_admin_ctrl, salon_model):
    """Onglet 6 : Génération de rapports"""
    
    st.subheader("📄 Rapports et exports")
    
    st.markdown("""
    ### 🎯 Pertinence des rapports
    
    Les rapports permettent d'exporter toutes les données de votre système pour :
    - **Analyse externe** : Utiliser Excel, Power BI, ou d'autres outils d'analyse
    - **Archivage** : Sauvegarder un snapshot de l'état actuel du système
    - **Audit** : Vérifier l'intégrité des données et détecter les anomalies
    - **Reporting** : Générer des rapports pour la direction ou les investisseurs
    - **Backup** : Avoir une copie de toutes les données importantes
    
    ### 📦 Contenu des rapports
    
    Les rapports incluent :
    - **Statistiques globales** : Vue d'ensemble de tous les salons
    - **Statistiques par salon** : Détails de chaque salon (employés, clients, commandes, CA, charges, bénéfices)
    - **Liste des utilisateurs** : Tous les admins et employés avec leurs informations
    - **Liste des commandes** : Toutes les commandes avec détails (client, couturier, montants, statut)
    - **Évolution mensuelle** : Historique du CA et des encaissements par mois
    
    ---
    """)
    
    # Sélection du type de rapport
    type_rapport = st.radio(
        "Type de rapport",
        options=["📊 Rapport global (tous les salons)", "🏢 Rapport par salon"],
        key="type_rapport"
    )
    
    salon_id_rapport = None
    
    if type_rapport == "🏢 Rapport par salon":
        salons = salon_model.lister_tous_salons()
        if not salons:
            st.warning("Aucun salon disponible pour générer un rapport ciblé.")
        else:
            salon_options = {f"{s['salon_id']} - {s['nom_salon']}": s['salon_id'] for s in salons}
            
            selected_salon = st.selectbox(
                "Sélectionner un salon",
                options=list(salon_options.keys()),
                key="select_salon_rapport"
            )
            
            if selected_salon:
                salon_id_rapport = salon_options[selected_salon]
    
    st.markdown("---")
    
    # Aperçu du contenu du rapport
    if salon_id_rapport:
        st.info(f"📊 Le rapport contiendra toutes les données du salon **{salon_id_rapport}**")
    else:
        st.info("📊 Le rapport contiendra toutes les données de **tous les salons**")
    
    st.markdown("""
    #### 📋 Contenu détaillé du rapport :
    
    - ✅ **Statistiques** : Nombre de salons, admins, employés, clients, commandes
    - ✅ **Métriques financières** : CA total, encaissé, charges, bénéfices
    - ✅ **Détails par salon** : Pour chaque salon, toutes les statistiques détaillées
    - ✅ **Liste des utilisateurs** : Tous les admins et employés avec leurs informations
    - ✅ **Liste des commandes** : Toutes les commandes avec détails complets
    - ✅ **Évolution mensuelle** : Historique du CA et des encaissements par mois
    
    ---
    """)
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("#### 📄 Format JSON")
        st.markdown("""
        Le format JSON est idéal pour :
        - Import dans d'autres applications
        - Analyse avec des outils de programmation (Python, JavaScript)
        - Archivage structuré
        """)
        
        if st.button("📥 Générer rapport JSON", use_container_width=True):
            with st.spinner("Génération du rapport..."):
                rapport = super_admin_ctrl.generer_rapport_complet(salon_id_rapport)
                
                # Convertir en JSON
                json_str = json.dumps(rapport, indent=2, default=str, ensure_ascii=False)
                
                st.download_button(
                    label="💾 Télécharger le rapport JSON",
                    data=json_str,
                    file_name=f"rapport_{'global' if not salon_id_rapport else salon_id_rapport}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
                    mime="application/json",
                    use_container_width=True
                )
                
                st.success("✅ Rapport JSON généré avec succès !")
                
                # Aperçu du rapport
                with st.expander("👁️ Aperçu du rapport (premiers éléments)"):
                    st.json({
                        'date_generation': rapport.get('date_generation'),
                        'type': rapport.get('type'),
                        'salon_id': rapport.get('salon_id'),
                        'nombre_salons': len(rapport.get('salons', [])),
                        'nombre_utilisateurs': len(rapport.get('utilisateurs', [])),
                        'nombre_commandes': len(rapport.get('commandes', []))
                    })
    
    with col2:
        st.markdown("#### 📊 Format CSV")
        st.markdown("""
        Le format CSV est idéal pour :
        - Ouverture dans Excel ou Google Sheets
        - Analyse avec des tableurs
        - Import dans des bases de données
        """)
        
        if st.button("📥 Générer rapport CSV", use_container_width=True):
            with st.spinner("Génération du rapport..."):
                rapport = super_admin_ctrl.generer_rapport_complet(salon_id_rapport)
                
                # Convertir les salons en CSV
                if rapport.get('salons'):
                    df_salons = pd.DataFrame(rapport['salons'])
                    csv = df_salons.to_csv(index=False)
                    
                    st.download_button(
                        label="💾 Télécharger le rapport CSV",
                        data=csv,
                        file_name=f"rapport_salons_{'global' if not salon_id_rapport else salon_id_rapport}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                        mime="text/csv",
                        use_container_width=True
                    )
                    
                    st.success("✅ Rapport CSV généré avec succès !")
                    
                    # Aperçu du tableau
                    with st.expander("👁️ Aperçu du tableau (premiers salons)"):
                        st.dataframe(df_salons.head(10), use_container_width=True, hide_index=True)
                else:
                    st.warning("⚠️ Aucun salon à exporter")
