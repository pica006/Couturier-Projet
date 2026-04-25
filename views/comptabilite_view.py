"""
========================================
VUE COMPTABILITÉ (comptabilite_view.py)
========================================

POURQUOI CE FICHIER ?
---------------------
Page de comptabilité et statistiques pour le couturier
Affiche les données financières, statistiques des commandes, etc.

FONCTIONNALITÉS :
-----------------
- Statistiques financières (CA, avances, restes)
- Nombre de commandes par période
- Liste des clients
- Graphiques et rapports
"""

import streamlit as st
from datetime import datetime, timedelta
import pandas as pd
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from models.database import CouturierModel
from models.salon_model import SalonModel
from utils.role_utils import obtenir_salon_id, obtenir_salon_id_resolu, est_admin


def afficher_page_comptabilite():
    """
    Page principale de comptabilité
    Affiche toutes les statistiques et rapports
    """
    
    # En-tête encadré standardisé
    from utils.page_header import afficher_header_page
    afficher_header_page("💰 Comptabilité & Statistiques", "Analyse financière et suivi des revenus")
    
    # Vérifier la connexion
    if not st.session_state.db_connection or not st.session_state.authentifie:
        st.error("❌ Vous devez être connecté pour accéder à cette page")
        return
    
    # Récupérer l'ID du couturier
    couturier_data_session = st.session_state.get('couturier_data') or {}
    couturier_id = couturier_data_session.get('id')
    if not couturier_id:
        st.error("❌ Impossible de récupérer votre identifiant couturier.")
        return
    is_admin_user = est_admin(couturier_data_session)
    salon_id_user = (
        obtenir_salon_id_resolu(couturier_data_session, st.session_state.db_connection)
        if is_admin_user
        else None
    )
    if is_admin_user and not salon_id_user:
        st.warning(
            "⚠️ Aucun salon trouvé pour votre compte admin. "
            "Affichage basculé sur vos propres commandes uniquement."
        )
    couturier_filtre_id = couturier_id
    if is_admin_user and salon_id_user:
        try:
            couturier_model = CouturierModel(st.session_state.db_connection)
            couturiers_salon = couturier_model.lister_tous_couturiers(salon_id=salon_id_user)
        except Exception:
            couturiers_salon = []

        options_couturiers = {"Tous les couturiers du salon": None}
        for c in couturiers_salon:
            cid = c.get("id")
            if cid is None:
                continue
            label = f"{c.get('code_couturier', 'N/A')} - {c.get('prenom', '')} {c.get('nom', '')}".strip()
            options_couturiers[label] = cid

        selected_label = st.selectbox(
            "Filtrer par couturier",
            options=list(options_couturiers.keys()),
            index=0,
            help="Permet de comparer les performances de chaque couturier du salon",
        )
        couturier_filtre_id = options_couturiers.get(selected_label)

    salon_filtre_id = salon_id_user if is_admin_user else None
    # En production, certaines commandes historiques n'ont pas salon_id.
    # Si un couturier précis est sélectionné, on aligne le comportement Airan:
    # scope principal par couturier_id uniquement.
    salon_scope_pour_requetes = (
        salon_filtre_id if (not is_admin_user or couturier_filtre_id is None) else None
    )
    
    # Contrôleur (créé une seule fois)
    try:
        from controllers.comptabilite_controller import ComptabiliteController
        compta_controller = ComptabiliteController(st.session_state.db_connection)
    except Exception as e:
        st.error(f"❌ Impossible d'initialiser la comptabilité : {e}")
        return
    
    # ========================================================================
    # FILTRES DE PÉRIODE (Dates choisies par l'utilisateur)
    # ========================================================================
    
    st.markdown("### 📅 Intervalle d'analyse")
    
    col1, col2 = st.columns(2)
    default_debut = datetime.now().date() - timedelta(days=30)
    default_fin = datetime.now().date()
    with col1:
        date_debut = st.date_input("Date de début", key="date_debut_compta", value=default_debut)
    with col2:
        date_fin = st.date_input("Date de fin", key="date_fin_compta", value=default_fin)
    
    # Normaliser en datetime (début de journée pour début, fin de journée pour fin)
    date_debut_filtre = None
    date_fin_filtre = None
    if date_debut:
        date_debut_filtre = datetime.combine(date_debut, datetime.min.time())
    if date_fin:
        # fin de journée
        date_fin_filtre = datetime.combine(date_fin, datetime.max.time())
    
    # Si l'utilisateur inverse les dates, on corrige silencieusement
    if date_debut_filtre and date_fin_filtre and date_fin_filtre < date_debut_filtre:
        date_debut_filtre, date_fin_filtre = date_fin_filtre, date_debut_filtre
    
    st.markdown("---")

    # ========================================================================
    # RECHERCHE PAR MODÈLE + TRIS (dynamique selon l'intervalle)
    # ========================================================================
    try:
        modeles_disponibles = compta_controller.lister_modeles_par_periode(
            couturier_filtre_id,
            date_debut_filtre,
            date_fin_filtre,
            salon_id=salon_scope_pour_requetes
        )
    except Exception:
        modeles_disponibles = []

    options_modeles = ["Tous"] + modeles_disponibles
    modele_selectionne = st.selectbox(
        "Rechercher un modèle (filtré par dates)",
        options=options_modeles,
        index=0,
        help="Liste des modèles présents sur la période choisie",
        key="compta_modele_filtre",
    )
    modele_filtre = None if modele_selectionne == "Tous" else modele_selectionne
    
    # ========================================================================
    # RÉCUPÉRATION DES DONNÉES
    # ========================================================================
    
    try:
        # Récupérer les statistiques
        stats = compta_controller.obtenir_statistiques(
            couturier_filtre_id,
            date_debut_filtre, 
            date_fin_filtre,
            salon_id=salon_scope_pour_requetes
        ) or {}
        
        # ====================================================================
        # SECTION 1 : CARTES DE STATISTIQUES PRINCIPALES
        # ====================================================================
        
        st.markdown("### 📊 Vue d'ensemble")
        
        col1, col2, col3, col4 = st.columns(4)
        
        ca_total = stats.get('ca_total', 0) or 0
        avances_total = stats.get('avances_total', 0) or 0
        reste_total = stats.get('reste_total', 0) or 0
        taux_avance = stats.get('taux_avance', 0) or 0
        nb_commandes = stats.get('nb_commandes', 0) or 0
        
        with col1:
            st.metric(
                label="💰 Chiffre d'affaires",
                value=f"{ca_total:,.0f} FCFA",
                help="Montant total des commandes"
            )
        
        with col2:
            st.metric(
                label="✅ Avances reçues",
                value=f"{avances_total:,.0f} FCFA",
                delta=f"{taux_avance:.1f}%",
                help="Total des avances perçues"
            )
        
        with col3:
            st.metric(
                label="⏳ Reste à percevoir",
                value=f"{reste_total:,.0f} FCFA",
                delta=f"-{100-taux_avance:.1f}%",
                delta_color="inverse",
                help="Montant restant à encaisser"
            )
        
        with col4:
            st.metric(
                label="📦 Commandes",
                value=nb_commandes,
                help="Nombre total de commandes"
            )

        if is_admin_user and salon_filtre_id:
            st.markdown("### 🏆 Efficacité des couturiers")
            tri_classement = st.selectbox(
                "Trier le classement par",
                options=[
                    "CA décroissant",
                    "CA croissant",
                    "Nombre de commandes décroissant",
                    "Nombre de commandes croissant",
                    "Taux d'avance décroissant",
                    "Taux d'avance croissant",
                    "Reste à percevoir décroissant",
                    "Reste à percevoir croissant",
                    "Nom du couturier A-Z",
                    "Nom du couturier Z-A",
                ],
                index=0,
                key="compta_tri_classement_salon",
            )
            classement = compta_controller.classement_efficacite_couturiers(
                salon_id=salon_filtre_id,
                date_debut=date_debut_filtre,
                date_fin=date_fin_filtre,
            )
            if classement:
                df_ranking = pd.DataFrame(classement)
                df_ranking["Couturier"] = (
                    df_ranking["code_couturier"].fillna("N/A")
                    + " - "
                    + df_ranking["prenom"].fillna("")
                    + " "
                    + df_ranking["nom"].fillna("")
                ).str.strip()
                nom_tri = (df_ranking["nom"].fillna("") + " " + df_ranking["prenom"].fillna("")).str.strip()
                sort_map = {
                    "CA décroissant": (["ca_total"], [False]),
                    "CA croissant": (["ca_total"], [True]),
                    "Nombre de commandes décroissant": (["nb_commandes"], [False]),
                    "Nombre de commandes croissant": (["nb_commandes"], [True]),
                    "Taux d'avance décroissant": (["taux_avance"], [False]),
                    "Taux d'avance croissant": (["taux_avance"], [True]),
                    "Reste à percevoir décroissant": (["reste_total"], [False]),
                    "Reste à percevoir croissant": (["reste_total"], [True]),
                    "Nom du couturier A-Z": (["nom_tri"], [True]),
                    "Nom du couturier Z-A": (["nom_tri"], [False]),
                }
                cols, asc = sort_map.get(tri_classement, (["ca_total"], [False]))
                if "nom_tri" in cols:
                    df_ranking = df_ranking.assign(nom_tri=nom_tri)
                df_ranking = df_ranking.sort_values(by=cols, ascending=asc).reset_index(drop=True)
                df_ranking["Rang"] = df_ranking.index + 1
                top = df_ranking.iloc[0]
                st.success(
                    f"Leader période: {top['Couturier']} | "
                    f"CA {top['ca_total']:,.0f} FCFA | "
                    f"{int(top['nb_commandes'])} commandes"
                )
                df_display_rank = df_ranking[
                    ["Rang", "Couturier", "nb_commandes", "ca_total", "avances_total", "reste_total", "taux_avance"]
                ].copy()
                df_display_rank.columns = [
                    "Rang",
                    "Couturier",
                    "Commandes",
                    "CA (FCFA)",
                    "Avances (FCFA)",
                    "Reste (FCFA)",
                    "Taux avance (%)",
                ]
                for col in ["CA (FCFA)", "Avances (FCFA)", "Reste (FCFA)"]:
                    df_display_rank[col] = df_display_rank[col].apply(lambda x: f"{x:,.0f}")
                df_display_rank["Taux avance (%)"] = df_display_rank["Taux avance (%)"].apply(lambda x: f"{x:.1f}")
                st.dataframe(df_display_rank, use_container_width=True, hide_index=True)
            else:
                st.info("Aucune donnée de classement disponible pour la période.")
        
        st.markdown("---")
        
        # ====================================================================
        # SECTION 2 : MODÈLES POPULAIRES & RÉPARTITION ARGENT REÇU
        # ====================================================================
        
        st.markdown("### 📈 Modèles et revenus")
        
        # Helper pour placer la légende intelligemment
        def _place_legend(ax, wedges, labels, title):
            max_inline = 6
            if len(labels) > max_inline:
                ax.legend(wedges, labels, title=title, loc="lower center", bbox_to_anchor=(0.5, -0.15), ncol=min(len(labels), 3))
            else:
                ax.legend(wedges, labels, title=title, loc="center left", bbox_to_anchor=(1, 0.5))
        
        # Petit helper pour afficher % + valeur absolue sur le camembert
        def _make_autopct(values, formatter=None):
            total = sum(values) if values else 0
            def _autopct(pct):
                if total == 0:
                    return "0%\n0"
                val = pct * total / 100.0
                if formatter:
                    return f"{pct:.1f}%\n{formatter(val)}"
                # valeurs entières par défaut
                return f"{pct:.1f}%\n{int(round(val))}"
            return _autopct

        top_modeles = compta_controller.top_modeles(
            couturier_filtre_id,
            statut=None,
            modele=modele_filtre,
            date_debut=date_debut_filtre,
            date_fin=date_fin_filtre,
            limit=10,
            salon_id=salon_scope_pour_requetes,
        )
        repartition = compta_controller.repartition_argent_par_modele(
            couturier_filtre_id,
            date_debut=date_debut_filtre,
            date_fin=date_fin_filtre,
            limit=10,
            salon_id=salon_scope_pour_requetes,
            modele=modele_filtre,
        )

        col1, col2 = st.columns(2)
        
        # Graphique 1 : Modèles les plus populaires (camembert par nombre de commandes)
        with col1:
            st.markdown("#### Modèles les plus populaires")
            if top_modeles:
                labels = [m for m, _ in top_modeles]
                counts = [c for _, c in top_modeles]
                if counts and sum(counts) > 0:
                    colors = plt.cm.Pastel1(range(len(labels)))
                    fig1, ax1 = plt.subplots()
                    wedges1, texts1, autotexts1 = ax1.pie(
                        counts,
                        labels=None,
                        autopct=_make_autopct(counts, formatter=lambda v: f"{int(round(v))} commandes"),
                        startangle=90,
                        colors=colors,
                        pctdistance=0.75,
                        textprops={"fontsize": 9}
                    )
                    ax1.axis('equal')
                    legend_labels1 = [f"{l} ({c})" for l, c in zip(labels, counts)]
                    _place_legend(ax1, wedges1, legend_labels1, "Modèles")
                    ax1.set_title("Top modèles par volume")
                    plt.tight_layout()
                    st.pyplot(fig1, use_container_width=True)
                    plt.close(fig1)
                else:
                    st.info("Aucune donnée disponible")
            else:
                st.info("Aucune donnée disponible")

        # Graphique 2 : Répartition de l'argent reçu par modèle (camembert somme des avances)
        with col2:
            st.markdown("#### Répartition de l'argent reçu par modèle")
            if repartition:
                labels_r = [m for m, _ in repartition]
                montants = [float(s) for _, s in repartition]
                if montants and sum(montants) > 0:
                    colors2 = plt.cm.Pastel2(range(len(labels_r)))
                    fig2, ax2 = plt.subplots()
                    wedges2, texts2, autotexts2 = ax2.pie(
                        montants,
                        labels=None,
                        autopct=_make_autopct(montants, formatter=lambda v: f"{v:,.0f} FCFA"),
                        startangle=90,
                        colors=colors2,
                        pctdistance=0.75,
                        textprops={"fontsize": 9}
                    )
                    ax2.axis('equal')
                    legend_labels2 = [f"{l} ({m:,.0f} FCFA)" for l, m in zip(labels_r, montants)]
                    _place_legend(ax2, wedges2, legend_labels2, "Modèles")
                    ax2.set_title("Somme des avances par modèle")
                    plt.tight_layout()
                    st.pyplot(fig2, use_container_width=True)
                    plt.close(fig2)
                else:
                    st.info("Aucune donnée disponible")
            else:
                st.info("Aucune donnée disponible")

        st.markdown("#### Schéma en barres (aperçu rapide)")
        bar_left, bar_right = st.columns(2)
        with bar_left:
            if top_modeles:
                df_bar_vol = pd.DataFrame(top_modeles, columns=["Modèle", "Commandes"])
                st.bar_chart(df_bar_vol.set_index("Modèle"), use_container_width=True)
            else:
                st.caption("Pas de données pour le volume par modèle.")
        with bar_right:
            if repartition:
                df_bar_av = pd.DataFrame(repartition, columns=["Modèle", "Avances (FCFA)"])
                df_bar_av["Avances (FCFA)"] = df_bar_av["Avances (FCFA)"].astype(float)
                st.bar_chart(df_bar_av.set_index("Modèle"), use_container_width=True)
            else:
                st.caption("Pas de données pour les avances par modèle.")

        # Graphiques modèles (3 et 4 côte à côte)
        st.markdown("### 👗 Modèles (détaillé)")
        col_cat1, col_cat2 = st.columns(2)

        # Graphique 3 : Répartition de l'argent reçu par modèle (camembert)
        with col_cat1:
            st.markdown("#### Montants perçus par modèle")
            repartition_cat = repartition
            if repartition_cat:
                labels_c = [c for c, _ in repartition_cat]
                montants_c = [float(s) for _, s in repartition_cat]
                if montants_c and sum(montants_c) > 0:
                    colors3 = plt.cm.Set3(range(len(labels_c)))
                    fig3, ax3 = plt.subplots()
                    wedges3, texts3, autotexts3 = ax3.pie(
                        montants_c,
                        labels=None,
                        autopct=_make_autopct(montants_c, formatter=lambda v: f"{v:,.0f} FCFA"),
                        startangle=90,
                        colors=colors3,
                        pctdistance=0.75,
                        textprops={"fontsize": 9}
                    )
                    ax3.axis('equal')
                    legend_labels3 = [f"{l} ({m:,.0f} FCFA)" for l, m in zip(labels_c, montants_c)]
                    _place_legend(ax3, wedges3, legend_labels3, "Modèles")
                    ax3.set_title("Montants perçus par modèle")
                    plt.tight_layout()
                    st.pyplot(fig3, use_container_width=True)
                    plt.close(fig3)
                else:
                    st.info("Aucune donnée disponible pour les modèles (montants perçus)")
            else:
                st.info("Aucune donnée disponible pour les modèles (montants perçus)")

        # Graphique 4 : Reste à percevoir par modèle (+ nb vêtements)
        with col_cat2:
            st.markdown("#### Reste à percevoir par modèle")
            reste_cat = compta_controller.reste_par_modele(
                couturier_filtre_id,
                date_debut=date_debut_filtre,
                date_fin=date_fin_filtre,
                limit=10,
                salon_id=salon_scope_pour_requetes,
                modele=modele_filtre,
            )
            if reste_cat:
                labels_rc = [c for c, _, _ in reste_cat]
                montants_rc = [float(s) for _, s, _ in reste_cat]
                counts_rc = [int(n) for _, _, n in reste_cat]
                if montants_rc and sum(montants_rc) > 0:
                    colors4 = plt.cm.Set2(range(len(labels_rc)))
                    fig4, ax4 = plt.subplots()
                    wedges4, texts4, autotexts4 = ax4.pie(
                        montants_rc,
                        labels=None,
                        autopct=_make_autopct(montants_rc, formatter=lambda v: f"{v:,.0f} FCFA"),
                        startangle=90,
                        colors=colors4,
                        pctdistance=0.75,
                        textprops={"fontsize": 9}
                    )
                    ax4.axis('equal')
                    legend_labels4 = [f"{l} ({m:,.0f} FCFA, {n} vêtements)" for l, m, n in zip(labels_rc, montants_rc, counts_rc)]
                    _place_legend(ax4, wedges4, legend_labels4, "Modèles")
                    ax4.set_title("Reste à percevoir par modèle")
                    plt.tight_layout()
                    st.pyplot(fig4, use_container_width=True)
                    plt.close(fig4)
                else:
                    st.info("Aucune donnée disponible pour les modèles (reste à percevoir)")
            else:
                st.info("Aucune donnée disponible pour les modèles (reste à percevoir)")
        
        st.markdown("---")
        
        # ====================================================================
        # SECTION 3 : LISTE DES CLIENTS
        # ====================================================================
        
        st.markdown("### 👥 Clients")
        tri_client_label = st.selectbox(
            "Trier les clients par",
            options=[
                "CA decroissant",
                "CA croissant",
                "Reste a payer decroissant",
                "Reste a payer croissant",
                "Nombre de commandes decroissant",
                "Nombre de commandes croissant",
                "Nom A-Z",
                "Nom Z-A",
            ],
            index=0,
            key="compta_tri_clients",
        )
        tri_client_map = {
            "CA decroissant": "ca_desc",
            "CA croissant": "ca_asc",
            "Reste a payer decroissant": "reste_desc",
            "Reste a payer croissant": "reste_asc",
            "Nombre de commandes decroissant": "nb_desc",
            "Nombre de commandes croissant": "nb_asc",
            "Nom A-Z": "nom_asc",
            "Nom Z-A": "nom_desc",
        }
        
        # Récupérer la liste des clients (tri géré côté contrôleur)
        clients = compta_controller.obtenir_liste_clients_triee(
            couturier_id=couturier_filtre_id,
            salon_id=salon_scope_pour_requetes,
            tri=tri_client_map[tri_client_label],
        )
        
        if clients:
            # Créer un DataFrame pour affichage
            df_clients = pd.DataFrame(clients)
            
            # Renommer les colonnes
            df_clients.columns = ['Nom', 'Prénom', 'Téléphone', 'Nb Commandes', 'CA Total', 'Reste à payer']
            
            # Formater les montants
            df_clients['CA Total'] = df_clients['CA Total'].apply(lambda x: f"{x:,.0f} FCFA")
            df_clients['Reste à payer'] = df_clients['Reste à payer'].apply(lambda x: f"{x:,.0f} FCFA")
            
            # Afficher le tableau
            st.dataframe(
                df_clients,
                use_container_width=True,
                hide_index=True
            )
            
            # Bouton d'export
            col1, col2, col3 = st.columns([1, 1, 2])
            with col1:
                csv = df_clients.to_csv(index=False).encode('utf-8')
                st.download_button(
                    label="📥 Exporter en CSV",
                    data=csv,
                    file_name=f"clients_{datetime.now().strftime('%Y%m%d')}.csv",
                    mime="text/csv"
                )
        else:
            st.info("Aucun client enregistré")
        
        st.markdown("---")
        
        # ====================================================================
        # SECTION 4 : COMMANDES À RELANCER
        # ====================================================================
        
        st.markdown("### 🔔 Commandes à relancer")
        tri_relance_label = st.selectbox(
            "Trier les relances par",
            options=[
                "Date recente",
                "Date ancienne",
                "Reste decroissant",
                "Reste croissant",
                "Nom client A-Z",
                "Nom client Z-A",
            ],
            index=0,
            key="compta_tri_relances",
        )
        tri_relance_map = {
            "Date recente": "date_desc",
            "Date ancienne": "date_asc",
            "Reste decroissant": "reste_desc",
            "Reste croissant": "reste_asc",
            "Nom client A-Z": "nom_asc",
            "Nom client Z-A": "nom_desc",
        }
        # Configurer l'email pour le salon courant
        db = st.session_state.db_connection
        smtp_config = None
        try:
            if st.session_state.get("couturier_data"):
                salon_id = obtenir_salon_id(st.session_state.couturier_data)
                if not salon_id:
                    salon_id = obtenir_salon_id_resolu(st.session_state.couturier_data, db)
                if salon_id:
                    salon_model = SalonModel(db)
                    smtp_config = salon_model.obtenir_config_email_salon(salon_id)
        except Exception:
            smtp_config = None

        # Récupérer les commandes avec reste à payer (tri géré côté contrôleur)
        commandes_relance = compta_controller.obtenir_commandes_a_relancer(
            couturier_id=couturier_filtre_id,
            salon_id=salon_scope_pour_requetes,
            tri=tri_relance_map[tri_relance_label],
        )
        
        if commandes_relance:
            for idx, cmd in enumerate(commandes_relance):
                expander_label = (
                    f"📦 Commande #{cmd['id']} - {cmd['client_nom']} {cmd['client_prenom']} "
                    f"(#{idx + 1})"
                )
                with st.expander(expander_label):
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        st.write(f"**Modèle :** {cmd['modele']}")
                        st.write(f"**Prix total :** {cmd['prix_total']:,.0f} FCFA")
                        st.write(f"**Avance :** {cmd['avance']:,.0f} FCFA")
                    
                    with col2:
                        st.write(f"**Reste :** {cmd['reste']:,.0f} FCFA")
                        st.write(f"**Téléphone :** {cmd['client_telephone']}")
                        st.write(f"**Email :** {cmd.get('client_email') or 'Non renseigné'}")
                        st.write(f"**Date :** {cmd['date_creation']}")
                    
                    st.markdown("---")
                    if st.button(
                        "Envoyer un rappel par email",
                        key=f"relance_email_{cmd['id']}_{idx}",
                        use_container_width=True
                    ):
                        client_email = cmd.get('client_email')
                        if not client_email:
                            st.error("❌ Email de rappel non envoyé : adresse email du client manquante.")
                        else:
                            with st.spinner("📧 Envoi du rappel par email..."):
                                succes, message = compta_controller.envoyer_rappel_email_commande(
                                    commande=cmd,
                                    smtp_config=smtp_config,
                                )
                            if succes:
                                st.success(message)
                            else:
                                st.error(message)
                    
        else:
            st.success("✅ Aucune commande à relancer - Tous les paiements sont à jour !")
    
    except Exception as e:
        st.error(f"❌ Erreur lors du chargement des données : {e}")
        import traceback
        st.code(traceback.format_exc())


