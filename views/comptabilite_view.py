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
import matplotlib.pyplot as plt
from controllers.email_controller import EmailController
from models.salon_model import SalonModel
from utils.role_utils import obtenir_salon_id


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
    couturier_id = st.session_state.couturier_data['id']
    
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
    # RECHERCHE PAR MODÈLE (dynamique selon l'intervalle)
    # ========================================================================
    try:
        modeles_disponibles = compta_controller.lister_modeles_par_periode(
            couturier_id,
            date_debut_filtre,
            date_fin_filtre
        )
    except Exception:
        modeles_disponibles = []

    options_modeles = ["Tous"] + modeles_disponibles
    modele_selectionne = st.selectbox(
        "Rechercher un modèle (filtré par dates)",
        options=options_modeles,
        index=0,
        help="Liste des modèles présents sur la période choisie"
    )
    
    # ========================================================================
    # RÉCUPÉRATION DES DONNÉES
    # ========================================================================
    
    try:
        # Récupérer les statistiques
        stats = compta_controller.obtenir_statistiques(
            couturier_id, 
            date_debut_filtre, 
            date_fin_filtre
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

        col1, col2 = st.columns(2)
        
        # Graphique 1 : Modèles les plus populaires (camembert par nombre de commandes)
        with col1:
            st.markdown("#### Modèles les plus populaires")
            top_modeles = compta_controller.top_modeles(
                couturier_id,
                statut=None,
                date_debut=date_debut_filtre,
                date_fin=date_fin_filtre,
                limit=10
            )
            if top_modeles:
                labels = [m for m, _ in top_modeles]
                counts = [c for _, c in top_modeles]
                # Filtre éventuel par modèle sélectionné
                if modele_selectionne != "Tous":
                    filt = [(l, c) for l, c in zip(labels, counts) if l == modele_selectionne]
                    if filt:
                        labels, counts = [filt[0][0]], [filt[0][1]]
                    else:
                        labels, counts = [], []
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
                    st.pyplot(fig1, width='stretch')
                    plt.close(fig1)
                else:
                    st.info("Aucune donnée disponible")
            else:
                st.info("Aucune donnée disponible")

        # Graphique 2 : Répartition de l'argent reçu par modèle (camembert somme des avances)
        with col2:
            st.markdown("#### Répartition de l'argent reçu par modèle")
            repartition = compta_controller.repartition_argent_par_modele(
                couturier_id,
                date_debut=date_debut_filtre,
                date_fin=date_fin_filtre,
                limit=10
            )
            if repartition:
                labels_r = [m for m, _ in repartition]
                montants = [float(s) for _, s in repartition]
                if modele_selectionne != "Tous":
                    filt = [(l, m) for l, m in zip(labels_r, montants) if l == modele_selectionne]
                    if filt:
                        labels_r, montants = [filt[0][0]], [filt[0][1]]
                    else:
                        labels_r, montants = [], []
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
                    st.pyplot(fig2, width='stretch')
                    plt.close(fig2)
                else:
                    st.info("Aucune donnée disponible")
            else:
                st.info("Aucune donnée disponible")

        # Graphiques modèles (3 et 4 côte à côte)
        st.markdown("### 👗 Modèles (détaillé)")
        col_cat1, col_cat2 = st.columns(2)

        # Graphique 3 : Répartition de l'argent reçu par modèle (camembert)
        with col_cat1:
            st.markdown("#### Montants perçus par modèle")
            repartition_cat = compta_controller.repartition_argent_par_modele(
                couturier_id,
                date_debut=date_debut_filtre,
                date_fin=date_fin_filtre,
                limit=10
            )
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
                    st.pyplot(fig3, width='stretch')
                    plt.close(fig3)
                else:
                    st.info("Aucune donnée disponible pour les modèles (montants perçus)")
            else:
                st.info("Aucune donnée disponible pour les modèles (montants perçus)")

        # Graphique 4 : Reste à percevoir par modèle (+ nb vêtements)
        with col_cat2:
            st.markdown("#### Reste à percevoir par modèle")
            reste_cat = compta_controller.reste_par_modele(
                couturier_id,
                date_debut=date_debut_filtre,
                date_fin=date_fin_filtre,
                limit=10
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
                    st.pyplot(fig4, width='stretch')
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
        
        # Récupérer la liste des clients
        clients = compta_controller.obtenir_liste_clients(couturier_id)
        
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
                width='stretch',
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
        # Configurer l'email pour le salon courant
        db = st.session_state.db_connection
        smtp_config = None
        try:
            if st.session_state.get("couturier_data"):
                salon_id = obtenir_salon_id(st.session_state.couturier_data)
                if salon_id:
                    salon_model = SalonModel(db)
                    smtp_config = salon_model.obtenir_config_email_salon(salon_id)
        except Exception:
            smtp_config = None

        email_controller = EmailController(smtp_config=smtp_config)
        
        # Récupérer les commandes avec reste à payer
        commandes_relance = compta_controller.obtenir_commandes_a_relancer(couturier_id)
        
        if commandes_relance:
            for cmd in commandes_relance:
                with st.expander(f"📦 Commande #{cmd['id']} - {cmd['client_nom']} {cmd['client_prenom']}"):
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
                        "📧 Envoyer un rappel par email",
                        key=f"relance_email_{cmd['id']}",
                        width='stretch'
                    ):
                        client_email = cmd.get('client_email')
                        if not client_email:
                            st.error("❌ Email de rappel non envoyé : adresse email du client manquante.")
                        else:
                            subject = f"Rappel de paiement - Commande #{cmd['id']}"
                            body = (
                                f"Bonjour {cmd.get('client_prenom', '')} {cmd.get('client_nom', '')},\n\n"
                                f"Nous vous rappelons le solde de votre commande.\n\n"
                                f"Commande: #{cmd['id']}\n"
                                f"Modèle: {cmd.get('modele', 'N/A')}\n"
                                f"Prix total: {cmd.get('prix_total', 0):,.0f} FCFA\n"
                                f"Avance: {cmd.get('avance', 0):,.0f} FCFA\n"
                                f"Reste à payer: {cmd.get('reste', 0):,.0f} FCFA\n\n"
                                "Vous trouverez en pièce jointe votre fiche de commande (PDF), "
                                "si elle a été générée lors de l'enregistrement.\n\n"
                                "Merci pour votre confiance."
                            )
                            pdf_path = cmd.get('pdf_path')
                            attachments = [pdf_path] if pdf_path else None
                            with st.spinner("📧 Envoi du rappel par email..."):
                                succes, message = email_controller.envoyer_email_avec_message(
                                    client_email,
                                    subject,
                                    body,
                                    attachments=attachments
                                )
                            if succes:
                                st.success(f"✅ {message}")
                            else:
                                st.error(f"❌ Email de rappel non envoyé : {message}")
                    
        else:
            st.success("✅ Aucune commande à relancer - Tous les paiements sont à jour !")
    
    except Exception as e:
        st.error(f"❌ Erreur lors du chargement des données : {e}")
        import traceback
        st.code(traceback.format_exc())


