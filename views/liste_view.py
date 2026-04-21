"""
Vue de liste des commandes (View dans MVC)
"""
import streamlit as st
import pandas as pd
import os
import re
from datetime import datetime
from controllers.commande_controller import CommandeController
from controllers.pdf_controller import PDFController


def _generer_nom_fichier_pdf(details):
    """Génère le nom du fichier PDF au format {nom_client_numeroCommande_date}"""
    def _sanitize_filename(value: str) -> str:
        if not value:
            return 'unknown'
        value = str(value).strip().replace(' ', '_')
        return re.sub(r"[^A-Za-z0-9_\-]", "", value)
    
    client_nom = _sanitize_filename(str(details.get('client_nom', 'client')))
    client_prenom = _sanitize_filename(str(details.get('client_prenom', '')))
    commande_id = details.get('id', 'N/A')
    
    date_creation = details.get('date_creation', datetime.now())
    if isinstance(date_creation, datetime):
        date_str = date_creation.strftime('%Y%m%d')
    else:
        date_str = datetime.now().strftime('%Y%m%d')
    
    nom_complet = f"{client_prenom}_{client_nom}" if client_prenom else client_nom
    return f"{nom_complet}_{commande_id}_{date_str}.pdf"


def afficher_page_liste_commandes():
    """Affiche la liste des commandes du couturier"""
    
    # En-tête encadré standardisé
    from utils.page_header import afficher_header_page
    afficher_header_page("📜 Mes Commandes", "Gérez et suivez toutes vos commandes")
    
    # Container principal
    with st.container():
        
        # Initialiser les contrôleurs
        commande_controller = CommandeController(st.session_state.db_connection)
        pdf_controller = PDFController(db_connection=st.session_state.db_connection)
        
        # Récupérer les informations de l'utilisateur connecté
        from utils.role_utils import obtenir_salon_id
        couturier_data = st.session_state.couturier_data
        salon_id = obtenir_salon_id(couturier_data)
        code_couturier = couturier_data.get('code_couturier') if couturier_data else None
        
        # Récupérer les commandes (avec cache pour éviter les rechargements)
        if 'commandes_liste' not in st.session_state:
            with st.spinner("Chargement des commandes..."):
                st.session_state.commandes_liste = commande_controller.lister_commandes_couturier(
                    st.session_state.couturier_data['id']
                )
        
        commandes = st.session_state.commandes_liste
    
    if not commandes:
        with st.container():
            st.info("📭 Aucune commande enregistrée pour le moment")
            st.markdown("---")
            if st.button("➕ Créer une nouvelle commande", width='stretch', type="primary"):
                st.session_state.page = 'nouvelle_commande'
                st.rerun()
    else:
        # Statistiques avec style amélioré - OPTIMISÉES
        with st.container():
            st.markdown("### 📊 Statistiques")
            col1, col2, col3, col4, col5 = st.columns(5)
            
            # Calculs de base
            total_commandes = len(commandes)
            total_ca = sum(c['prix_total'] for c in commandes)
            commandes_en_cours = sum(1 for c in commandes if c['statut'] == 'En cours')
            
            # Calculs optimisés avec requêtes SQL directes
            # Terminé : somme des prix_totaux des commandes totalement payées (reste <= 0)
            # Filtrées par salon_id et code_couturier (code employé)
            somme_terminees, nb_terminees = commande_controller.calculer_somme_terminees(
                salon_id=salon_id,
                code_couturier=code_couturier
            )
            
            # Livré : somme des prix_totaux des commandes validées par l'administrateur
            # (dans historique_commandes avec statut_validation = 'validee' et type_action = 'fermeture_demande')
            # Filtrées par salon_id et code_couturier (code employé)
            somme_livrees, nb_livrees = commande_controller.calculer_somme_livrees(
                salon_id=salon_id,
                code_couturier=code_couturier
            )
            
            with col1:
                st.metric("📦 Total", total_commandes, delta=None)
            
            with col2:
                st.metric("💰 CA Total", f"{total_ca:,.0f} FCFA", delta=None)
            
            with col3:
                st.metric("⏳ En cours", commandes_en_cours, delta=None)
            
            with col4:
                # Afficher le nombre en haut et le montant en bas
                st.metric(
                    "✅ Terminé", 
                    f"{nb_terminees} commande{'s' if nb_terminees > 1 else ''}",
                    delta=f"{somme_terminees:,.0f} FCFA",
                    help="Nombre et somme des commandes totalement payées (reste = 0)"
                )
            
            with col5:
                # Afficher le nombre en haut et le montant en bas
                st.metric(
                    "🚚 Livré", 
                    f"{nb_livrees} vêtement{'s' if nb_livrees > 1 else ''}",
                    delta=f"{somme_livrees:,.0f} FCFA",
                    help="Nombre et somme des commandes validées par l'administrateur"
                )
            
            if total_commandes > 0:
                ca_moyen = total_ca / total_commandes
                st.caption(f"💡 Chiffre d'affaires moyen: {ca_moyen:,.0f} FCFA")
        
        st.markdown("---")
        
        # Filtres avec style amélioré
        with st.container():
            st.markdown("### 🔍 Filtres et Recherche")
            col1, col2, col3 = st.columns([2, 2, 1])
            
            with col1:
                filtre_statut = st.selectbox(
                    "📌 Filtrer par statut",
                    options=["Tous", "En cours", "Terminé", "Livré"],
                    index=0,
                    key="filtre_statut_liste"
                )
            
            with col2:
                recherche = st.text_input(
                    "🔎 Rechercher un client",
                    placeholder="Nom ou prénom du client...",
                    key="recherche_client_liste"
                )
            
            with col3:
                st.markdown("<br>", unsafe_allow_html=True)
                if st.button("🔄 Actualiser", width='stretch', key="btn_actualiser_liste"):
                    if 'commandes_liste' in st.session_state:
                        del st.session_state.commandes_liste
                    st.rerun()
            
            # Filtre par période (dates)
            st.markdown("#### 📅 Filtrer par période")
            col_date1, col_date2, col_date3 = st.columns([2, 2, 1])
            
            with col_date1:
                # Date de début
                date_debut = st.date_input(
                    "📅 Date de début",
                    value=None,
                    key="filtre_date_debut_liste",
                    help="Sélectionnez la date de début de la période"
                )
            
            with col_date2:
                # Date de fin
                date_fin = st.date_input(
                    "📅 Date de fin",
                    value=None,
                    key="filtre_date_fin_liste",
                    help="Sélectionnez la date de fin de la période"
                )
            
            with col_date3:
                st.markdown("<br>", unsafe_allow_html=True)
                if st.button("🗑️ Effacer dates", width='stretch', key="btn_effacer_dates"):
                    if 'filtre_date_debut_liste' in st.session_state:
                        del st.session_state.filtre_date_debut_liste
                    if 'filtre_date_fin_liste' in st.session_state:
                        del st.session_state.filtre_date_fin_liste
                    st.rerun()
        
        # Filtrer les commandes
        commandes_filtrees = commandes
        
        # Filtrer par statut
        if filtre_statut != "Tous":
            commandes_filtrees = [c for c in commandes_filtrees if c['statut'] == filtre_statut]
        
        # Filtrer par recherche client
        if recherche:
            recherche_lower = recherche.lower()
            commandes_filtrees = [
                c for c in commandes_filtrees 
                if recherche_lower in c['client_nom'].lower() 
                or recherche_lower in c['client_prenom'].lower()
            ]
        
        # Filtrer par dates
        if date_debut or date_fin:
            commandes_filtrees_temp = []
            for c in commandes_filtrees:
                date_creation = c.get('date_creation')
                
                # Convertir datetime en date si nécessaire
                if date_creation is None:
                    continue
                
                date_commande = None
                
                # Essayer différentes méthodes de conversion
                if isinstance(date_creation, datetime):
                    date_commande = date_creation.date()
                elif hasattr(date_creation, 'date') and callable(getattr(date_creation, 'date')):
                    # Si c'est un objet avec une méthode date() (comme datetime)
                    try:
                        date_commande = date_creation.date()
                    except:
                        pass
                elif isinstance(date_creation, str):
                    # Si c'est une chaîne, essayer de la convertir
                    try:
                        # Essayer différents formats
                        if ' ' in date_creation:
                            date_commande = datetime.strptime(date_creation.split()[0], '%Y-%m-%d').date()
                        else:
                            date_commande = datetime.strptime(date_creation, '%Y-%m-%d').date()
                    except:
                        try:
                            date_commande = datetime.strptime(date_creation, '%Y-%m-%d %H:%M:%S').date()
                        except:
                            continue
                elif hasattr(date_creation, 'year') and hasattr(date_creation, 'month') and hasattr(date_creation, 'day'):
                    # C'est déjà une date
                    date_commande = date_creation
                
                if date_commande is None:
                    continue
                
                # Vérifier si la date est dans la plage
                try:
                    if date_debut and date_fin:
                        # Période complète
                        if date_debut <= date_commande <= date_fin:
                            commandes_filtrees_temp.append(c)
                    elif date_debut:
                        # Seulement date de début
                        if date_commande >= date_debut:
                            commandes_filtrees_temp.append(c)
                    elif date_fin:
                        # Seulement date de fin
                        if date_commande <= date_fin:
                            commandes_filtrees_temp.append(c)
                except (TypeError, ValueError):
                    # Si la comparaison échoue, ignorer cette commande pour le filtre de date
                    continue
            
            commandes_filtrees = commandes_filtrees_temp
        
        # Trier les commandes par date de création (du plus récent au plus ancien)
        def get_date_for_sort(date_creation):
            """Convertit une date en datetime pour le tri"""
            if date_creation is None:
                return datetime.min
            if isinstance(date_creation, datetime):
                return date_creation
            if hasattr(date_creation, 'date') and callable(getattr(date_creation, 'date')):
                try:
                    return datetime.combine(date_creation.date(), datetime.min.time())
                except:
                    return datetime.min
            if isinstance(date_creation, str):
                try:
                    if ' ' in date_creation:
                        return datetime.strptime(date_creation.split()[0], '%Y-%m-%d')
                    else:
                        return datetime.strptime(date_creation, '%Y-%m-%d')
                except:
                    try:
                        return datetime.strptime(date_creation, '%Y-%m-%d %H:%M:%S')
                    except:
                        return datetime.min
            if hasattr(date_creation, 'year') and hasattr(date_creation, 'month') and hasattr(date_creation, 'day'):
                # C'est déjà une date
                try:
                    return datetime.combine(date_creation, datetime.min.time())
                except:
                    return datetime.min
            return datetime.min
        
        try:
            commandes_filtrees = sorted(
                commandes_filtrees,
                key=lambda x: get_date_for_sort(x.get('date_creation')),
                reverse=True
            )
        except (TypeError, ValueError, KeyError):
            # Si le tri échoue, garder l'ordre original
            pass
        
        st.markdown("---")
        
        # Afficher la période sélectionnée si des dates sont choisies
        if date_debut or date_fin:
            periode_info = "📅 Période sélectionnée: "
            if date_debut and date_fin:
                periode_info += f"du {date_debut.strftime('%d/%m/%Y')} au {date_fin.strftime('%d/%m/%Y')}"
            elif date_debut:
                periode_info += f"à partir du {date_debut.strftime('%d/%m/%Y')}"
            elif date_fin:
                periode_info += f"jusqu'au {date_fin.strftime('%d/%m/%Y')}"
            st.info(periode_info)
        
        # Affichage des commandes avec style amélioré
        with st.container():
            st.markdown(f"### 📋 Liste des commandes ({len(commandes_filtrees)})")
            
            if not commandes_filtrees:
                st.warning("⚠️ Aucune commande ne correspond aux filtres sélectionnés")
            else:
                # Créer un DataFrame pour l'affichage avec couleurs selon statut
                df_data = []
                for cmd in commandes_filtrees:
                    # Déterminer l'icône selon le statut
                    statut_icon = {
                        'En cours': '⏳',
                        'Terminé': '✅',
                        'Livré': '🚚'
                    }.get(cmd['statut'], '📋')
                    
                    df_data.append({
                        'N°': cmd['id'],
                        'Client': f"{cmd['client_prenom']} {cmd['client_nom']}",
                        'Modèle': cmd['modele'],
                        'Prix': f"{cmd['prix_total']:,.0f} FCFA",
                        'Statut': f"{statut_icon} {cmd['statut']}",
                        'Date': cmd['date_creation'].strftime('%d/%m/%Y')
                    })
                
                df = pd.DataFrame(df_data)
                
                # Afficher le tableau avec style
                st.dataframe(
                    df,
                    width='stretch',
                    hide_index=True,
                    height=400
                )
        
        st.markdown("---")
        
        # Détails d'une commande avec expander pour plus de dynamisme
        with st.container():
            st.markdown("### 🔎 Détails d'une commande")
            
            commande_ids = [c['id'] for c in commandes_filtrees]
            if not commande_ids:
                st.info("ℹ️ Sélectionnez des filtres pour voir les commandes")
            else:
                # Fonction pour forcer la mise à jour quand la sélection change
                def on_commande_change():
                    # Forcer un rerun pour mettre à jour l'affichage
                    st.rerun()
                
                commande_selectionnee = st.selectbox(
                    "Sélectionnez une commande",
                    options=commande_ids,
                    format_func=lambda x: f"Commande #{x} - {next((c['client_prenom'] + ' ' + c['client_nom'] for c in commandes_filtrees if c['id'] == x), 'N/A')}",
                    key="select_commande_details",
                    on_change=on_commande_change
                )
                
                if commande_selectionnee:
                    # Récupérer les détails complets (toujours récupérer les données fraîches)
                    details = commande_controller.obtenir_details_commande(commande_selectionnee)
                    
                    if details:
                        # Afficher directement sans placeholder pour éviter les problèmes de cache
                        # Utiliser des expanders pour organiser les informations
                        with st.expander("👤 Informations Client", expanded=True):
                            col1, col2 = st.columns(2)
                            
                            with col1:
                                st.markdown(f"**Nom complet:** {details['client_prenom']} {details['client_nom']}")
                                st.markdown(f"**Téléphone:** {details['client_telephone']}")
                            
                            with col2:
                                st.markdown(f"**Email:** {details['client_email'] or 'Non renseigné'}")
                        
                        with st.expander("👔 Détails du Vêtement", expanded=True):
                            col1, col2, col3 = st.columns(3)
                            
                            with col1:
                                st.markdown(f"**Catégorie:** {details['categorie'].capitalize()}")
                            with col2:
                                st.markdown(f"**Sexe:** {details['sexe'].capitalize()}")
                            with col3:
                                st.markdown(f"**Modèle:** {details['modele']}")
                        
                        with st.expander("💰 Informations de Paiement", expanded=True):
                            col1, col2, col3 = st.columns(3)
                            
                            with col1:
                                st.metric("Prix total", f"{details['prix_total']:,.0f} FCFA")
                            with col2:
                                st.metric("Avance", f"{details['avance']:,.0f} FCFA")
                            with col3:
                                st.metric("Reste à payer", f"{details['reste']:,.0f} FCFA", 
                                         delta=f"{((details['reste']/details['prix_total'])*100):.1f}%" if details['prix_total'] > 0 else "0%")
                        
                        with st.expander("📅 Dates et Statut", expanded=False):
                            col1, col2 = st.columns(2)
                            
                            with col1:
                                st.markdown(f"**Date de commande:** {details['date_creation'].strftime('%d/%m/%Y à %H:%M')}")
                                st.markdown(f"**Date de livraison:** {details['date_livraison'].strftime('%d/%m/%Y') if details['date_livraison'] else 'Non définie'}")
                            
                            with col2:
                                # Badge de statut avec couleur
                                statut = details['statut']
                                if statut == 'En cours':
                                    st.markdown(f"**Statut:** ⏳ {statut}")
                                elif statut == 'Terminé':
                                    st.markdown(f"**Statut:** ✅ {statut}")
                                elif statut == 'Livré':
                                    st.markdown(f"**Statut:** 🚚 {statut}")
                                else:
                                    st.markdown(f"**Statut:** {statut}")
                        
                        with st.expander("📏 Mesures", expanded=False):
                            mesures_cols = st.columns(3)
                            mesures_items = list(details['mesures'].items())
                            
                            for idx, (mesure, valeur) in enumerate(mesures_items):
                                col_idx = idx % 3
                                with mesures_cols[col_idx]:
                                    st.metric(mesure, f"{valeur} cm")
                        
                        st.markdown("---")
                        
                        # Actions avec style amélioré
                        st.markdown("#### ⚡ Actions")
                        # Première ligne de boutons
                        col1, col2 = st.columns(2)
                        
                        with col1:
                            if st.button("📄 Générer PDF", width='stretch', type="primary", key=f"btn_gen_pdf_{commande_selectionnee}"):
                                with st.spinner("📄 Génération du PDF en cours..."):
                                    pdf_path = pdf_controller.generer_pdf_commande(details)
                                    
                                    if pdf_path and os.path.exists(pdf_path):
                                        # Générer le nom de fichier personnalisé
                                        nom_fichier = _generer_nom_fichier_pdf(details)
                                        
                                        st.success("✅ PDF généré avec succès!")
                                        
                                        with open(pdf_path, "rb") as pdf_file:
                                            pdf_bytes = pdf_file.read()
                                        
                                        st.download_button(
                                            label="📥 Télécharger le PDF",
                                            data=pdf_bytes,
                                            file_name=nom_fichier,
                                            mime="application/pdf",
                                            width='stretch',
                                            key=f"download_pdf_liste_{commande_selectionnee}",
                                            type="primary"
                                        )
                                        
                                        st.info(f"💾 Nom du fichier: `{nom_fichier}`")
                                    else:
                                        st.error("❌ Erreur lors de la génération du PDF")
                        
                        with col2:
                            if st.button("🔄 Actualiser", width='stretch', key=f"btn_actualiser_details_{commande_selectionnee}"):
                                if 'commandes_liste' in st.session_state:
                                    del st.session_state.commandes_liste
                                st.rerun()
