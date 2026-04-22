"""
================================================================================
MES CHARGES - PAGE DE GESTION COMPLÈTE DES CHARGES
================================================================================
Module optimisé pour gérer toutes les charges de l'atelier de couture
avec graphiques, analyses, et calcul d'impôts automatique.
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
from typing import Optional, Dict
import io
import os
import tempfile
import re

from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib import colors
from reportlab.lib.units import cm
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.utils import ImageReader
from PIL import Image as PILImage
import qrcode

from models.database import ChargesModel
from models.commande_model import CommandeModel
from utils.page_header import afficher_header_page


# ============================================================================
# CONFIGURATION DES CONSTANTES
# ============================================================================

TYPES_CHARGES = {
    "Fixe": "📌 Frais Fixes (loyer, salaires...)",
    "Ponctuelle": "⏱️ Ponctuelles (réparations...)",
    "Commande": "🧾 Commande liée",
    "Salaire": "💰 Salaires"
}

CATEGORIES_CHARGES_GENERAL = {
    "loyer": "🏠 Loyer",
    "electricite": "💡 Électricité / Eau",
    "salaire": "👤 Salaire employé",
    "materiel": "✂️ Matériel / Fournitures",
    "transport": "🚗 Transport / Déplacement",
    "maintenance": "🔧 Maintenance / Réparation",
    "communication": "📱 Téléphone / Internet",
    "autre": "💼 Autre"
}

# Accessoires utilisés pour les charges liées à une commande
CATEGORIES_CHARGES_COMMANDE = {
    "fil": "🧵 Fil",
    "tissu_principal": "🧶 Tissu principal",
    "tissu_secondaire": "🧵 Tissu secondaire",
    "bouton": "🔘 Bouton",
    "fermeture_eclair": "🧷 Fermeture éclair",
    "elastique": "🪢 Élastique",
    "dentelle": "🧵 Dentelle",
    "ruban": "🎀 Ruban",
    "biais": "🧷 Biais",
    "doublure": "🧶 Doublure",
    "perles_strass": "💎 Perles / Strass",
    "broderie": "🧵 Broderie",
    "accessoire_autre": "📎 Autre accessoire"
}

# Dictionnaire global pour l'affichage des libellés
CATEGORIES_CHARGES = {**CATEGORIES_CHARGES_GENERAL, **CATEGORIES_CHARGES_COMMANDE}

# Tranches d'impôts (Chiffre d'affaire -> Impôt) — première tranche correspondante utilisée
TRANCHES_IMPOTS = [
    {"min": 0, "max": 500000, "impot": 5000},
    {"min": 500000, "max": 1000000, "impot": 75000},
    {"min": 1000000, "max": 1500000, "impot": 10000},
    {"min": 1500000, "max": 2000000, "impot": 12500},
    {"min": 2000000, "max": 2500000, "impot": 15000},
    {"min": 2500000, "max": 5000000, "impot": 37500},
    {"min": 5000000, "max": 10000000, "impot": 75000},
    {"min": 10000000, "max": 20000000, "impot": 125000},
    {"min": 20000000, "max": 30000000, "impot": 250000},
    {"min": 30000000, "max": 50000000, "impot": 500000},
]


# ============================================================================
# FONCTIONS UTILITAIRES
# ============================================================================

def calculer_prochaine_reference(
    charges_model: ChargesModel,
    couturier_id: Optional[int],
    salon_id: Optional[str] = None,
) -> int:
    """
    Calcule la prochaine référence (N+1) en se basant sur toutes les charges existantes.
    Extrait les références depuis les descriptions au format "| Réf: {numero}"
    ou depuis la colonne reference si elle existe.
    
    Args:
        charges_model: Instance du modèle ChargesModel
        couturier_id: ID du couturier
        
    Returns:
        Prochaine référence (1 si aucune charge n'existe)
    """
    try:
        # Récupérer toutes les charges (pour le calcul de référence, on prend toutes)
        # Note: Pour le calcul de référence, on prend toutes les charges même si admin
        charges = charges_model.lister_charges(
            couturier_id,
            limit=10000,
            tous_les_couturiers=False,
            salon_id=salon_id
        )
        
        if not charges:
            return 1
        
        # Extraire toutes les références depuis les descriptions
        references = []
        pattern = r'Réf:\s*(\d+)'
        
        for charge in charges:
            # Vérifier d'abord si la colonne reference existe et est remplie
            if 'reference' in charge and charge.get('reference'):
                try:
                    ref_num = int(charge['reference'])
                    references.append(ref_num)
                except (ValueError, TypeError):
                    pass
            
            # Sinon, extraire depuis la description
            description = charge.get('description', '') or ''
            matches = re.findall(pattern, description, re.IGNORECASE)
            for match in matches:
                try:
                    ref_num = int(match)
                    references.append(ref_num)
                except ValueError:
                    continue
        
        # Si aucune référence trouvée, retourner 1
        if not references:
            return 1
        
        # Retourner le maximum + 1
        return max(references) + 1
        
    except Exception as e:
        print(f"Erreur calcul prochaine référence: {e}")
        return 1


def sauvegarder_fichier_charge(uploaded_file, charge_id: int) -> Optional[Dict]:
    """
    Sauvegarde un fichier justificatif pour une charge EN BASE DE DONNÉES.
    Tous les fichiers sont stockés directement dans la BDD (LONGBLOB).
    
    Args:
        uploaded_file: Fichier uploadé par Streamlit
        charge_id: ID de la charge
        
    Returns:
        Dictionnaire avec les informations du fichier sauvegardé ou None
        Format: {
            'file_data': bytes,
            'file_name': str,
            'file_size': int,
            'mime_type': str
        }
    """
    try:
        # Lire le contenu du fichier
        file_data = uploaded_file.getbuffer()
        file_size = len(file_data)
        file_name = uploaded_file.name
        mime_type = uploaded_file.type or 'application/octet-stream'
        
        # Vérifier la taille du fichier (limite MySQL max_allowed_packet)
        if file_size > 16 * 1024 * 1024:  # 16MB
            st.warning(f"⚠️ Fichier volumineux ({file_size / 1024 / 1024:.2f} MB). "
                      f"Assurez-vous que max_allowed_packet est suffisant dans MySQL.")
        
        # Stockage UNIQUEMENT en base de données (BLOB)
        return {
            'file_data': file_data.tobytes(),
            'file_name': file_name,
            'file_size': file_size,
            'mime_type': mime_type
        }
    except Exception as e:
        st.error(f"❌ Erreur lors de la sauvegarde du fichier: {e}")
        return None


# ============================================================================
# FONCTION PRINCIPALE
# ============================================================================

def afficher_page_mes_charges():
    """
    Page principale de gestion des charges avec tabs et analyses complètes
    """
    
    # En-tête encadré standardisé
    from utils.page_header import afficher_header_page
    afficher_header_page("📄 Mes charges", "Gérez toutes vos charges et dépenses")
    
    # Vérification de l'authentification
    if not st.session_state.get('authentifie', False):
        st.error("❌ Vous devez être connecté pour accéder à cette page")
        return
    
    if not st.session_state.get('db_connection'):
        st.error("❌ Connexion à la base de données requise")
        return
    
    # Vérifier le rôle de l'utilisateur
    from utils.role_utils import est_admin, obtenir_couturier_id, obtenir_salon_id
    
    couturier_data = st.session_state.couturier_data
    is_admin = est_admin(couturier_data)
    try:
        salon_id_user = obtenir_salon_id(couturier_data) or ""
    except Exception:
        salon_id_user = ""
    
    # Si admin, filtrer par salon; sinon, par couturier
    couturier_id_connecte = obtenir_couturier_id(couturier_data)
    if couturier_id_connecte is None:
        st.error("❌ Impossible d'identifier votre compte utilisateur. Merci de vous reconnecter.")
        return
    # Filtre liste / périmètre : tout le salon pour l'admin, sinon l'employé connecté
    couturier_id_filtre = None if is_admin else couturier_id_connecte

    charges_model = ChargesModel(st.session_state.db_connection)
    commande_model = CommandeModel(st.session_state.db_connection)
    
    # ========================================================================
    # HEADER DE LA PAGE
    # ========================================================================
    
    # Titre selon le rôle
    if is_admin:
        titre = "💰 Gestion des Charges (Vue Admin)"
        sous_titre = "Vue de toutes les charges de l'entreprise"
    else:
        titre = "💰 Gestion des Charges"
        sous_titre = "Atelier de Couture - Tableau de bord complet"
    
    afficher_header_page(titre, sous_titre)
    
    # ========================================================================
    # TABS PRINCIPAUX
    # ========================================================================
    
    # Sécuriser la présence du salon_id (double assignation défensive)
    salon_id_user = salon_id_user or obtenir_salon_id(couturier_data)
    
    if is_admin:
        tab1, tab2, tab3, tab4 = st.tabs([
            "➕ Ajouter une charge",
            "📋 Liste des charges",
            "📊 Analyses & Graphiques",
            "🧮 Calcul d'impôts"
        ])
    else:
        tab1, tab2 = st.tabs([
            "➕ Ajouter une charge",
            "📋 Liste des charges"
        ])
    
    # ========================================================================
    # TAB 1 : AJOUT D'UNE CHARGE
    # ========================================================================
    
    with tab1:
        afficher_formulaire_ajout_charge(
            charges_model,
            commande_model,
            couturier_id_filtre,
            salon_id_user,
            is_admin=is_admin,
            couturier_id_auteur=couturier_id_connecte,
        )
    
    # ========================================================================
    # TAB 2 : LISTE DES CHARGES
    # ========================================================================
    
    with tab2:
        afficher_liste_charges(charges_model, couturier_id_filtre, is_admin, salon_id_user)
    
    # ========================================================================
    # TAB 3 : ANALYSES ET GRAPHIQUES
    # ========================================================================
    
    if is_admin:
        with tab3:
            afficher_analyses_graphiques(
                charges_model, commande_model, couturier_id_filtre, is_admin, salon_id_user
            )
    
    # ========================================================================
    # TAB 4 : CALCUL D'IMPÔTS
    # ========================================================================
    
    if is_admin:
        with tab4:
            afficher_calcul_impots(
                charges_model, commande_model, couturier_id_filtre, is_admin, salon_id_user
            )


# ============================================================================
# FORMULAIRE D'AJOUT DE CHARGE
# ============================================================================

def afficher_formulaire_ajout_charge(
    charges_model: ChargesModel,
    commande_model: CommandeModel,
    couturier_id_filtre: Optional[int],
    salon_id_user: Optional[str] = None,
    is_admin: bool = False,
    couturier_id_auteur: Optional[int] = None,
):
    """Formulaire d'ajout d'une nouvelle charge"""
    
    st.markdown("### ➕ Nouvelle charge")
    st.markdown("Enregistrez vos dépenses de manière structurée")
    if is_admin:
        st.caption(
            "Les charges sont enregistrées sous votre compte administrateur et restent visibles "
            "pour tout le salon."
        )
    st.markdown("---")

    if not couturier_id_auteur:
        st.error("❌ Impossible d'enregistrer : compte utilisateur invalide.")
        return

    with st.form("form_ajout_charge", clear_on_submit=True):
        # Type de charge (placé plus haut)
        type_options = ["Commande"] if not is_admin else list(TYPES_CHARGES.keys())
        type_charge = st.selectbox(
            "Type de charge *",
            options=type_options,
            format_func=lambda x: TYPES_CHARGES[x],
            help="Sélectionnez le type de charge",
            disabled=not is_admin
        )
        
        col1, col2 = st.columns(2)
        
        with col1:
            # Catégorie
            categories_source = (
                CATEGORIES_CHARGES_COMMANDE if type_charge == "Commande" else CATEGORIES_CHARGES_GENERAL
            )
            categorie = st.selectbox(
                "Catégorie *",
                options=list(categories_source.keys()),
                format_func=lambda x: categories_source[x],
                help="Catégorie de la dépense"
            )
            
            # Montant
            montant = st.number_input(
                "Montant (FCFA) *",
                min_value=0.0,
                step=100.0,
                format="%.2f",
                help="Montant de la charge en Francs CFA"
            )
        
        with col2:
            # Date de la charge
            date_charge = st.date_input(
                "Date de la charge *",
                value=datetime.now().date(),
                help="Date de la dépense"
            )
            
            # Description
            description = st.text_area(
                "Description",
                placeholder="Détails sur la charge (optionnel)",
                height=100,
                help="Informations complémentaires"
            )
        
        # Si type = Commande, afficher liste des commandes
        commande_id = None
        commentaire = ""
        if type_charge == "Commande":
            st.markdown("---")
            st.markdown("#### 🧾 Liaison avec une commande")
            
            col_cmd, col_comment = st.columns(2)
            
            with col_cmd:
                # Récupérer les commandes : pour un non-admin, filtrer uniquement par couturier_id
                # (comme dans la page "Mes commandes") ; pour un admin, filtrer par salon_id
                if couturier_id_filtre is not None:
                    # Non-admin : filtrer uniquement par couturier_id (comme dans "Mes commandes")
                    commandes = commande_model.lister_commandes(
                        couturier_id=couturier_id_filtre,
                        tous_les_couturiers=False,
                        salon_id=salon_id_user
                    )
                else:
                    # Admin : filtrer par salon_id
                    commandes = commande_model.lister_commandes(
                        couturier_id=None,
                        tous_les_couturiers=False,
                        salon_id=salon_id_user
                    )
                
                if commandes:
                    options_commandes = {
                        f"CMD-{c['id']} | {c.get('modele', 'N/A')} - {c.get('client_nom', 'Client')}": c['id']
                        for c in commandes
                    }
                    
                    commande_selectionnee = st.selectbox(
                        "Commande liée *",
                        options=list(options_commandes.keys()),
                        help="Sélectionnez la commande concernée"
                    )
                    
                    commande_id = options_commandes[commande_selectionnee]
                else:
                    st.warning("⚠️ Aucune commande disponible. Créez d'abord une commande.")
            
            with col_comment:
                commentaire = st.text_input(
                    "Commentaire supplémentaire (facultatif)",
                    placeholder="Ex: Facture n°..., Fournisseur...",
                    help="Informations additionnelles"
                )
        else:
            commentaire = st.text_input(
                "Commentaire supplémentaire (facultatif)",
                placeholder="Ex: Facture n°..., Fournisseur...",
                help="Informations additionnelles"
            )
        
        st.markdown("---")
        
        # Boutons
        col_btn1, col_btn2, col_btn3 = st.columns([2, 1, 1])
        
        with col_btn1:
            submit = st.form_submit_button(
                "💾 Enregistrer la charge",
                type="primary"
            )
        
        with col_btn2:
            st.form_submit_button("🔄 Réinitialiser")
        
        # Traitement du formulaire
        if submit:
            # Validation
            erreurs = []
            
            if montant <= 0:
                erreurs.append("Le montant doit être supérieur à 0")
            
            if type_charge == "Commande" and not commande_id:
                erreurs.append("Vous devez sélectionner une commande")
            
            if erreurs:
                for err in erreurs:
                    st.error(f"❌ {err}")
            else:
                # Enregistrement
                with st.spinner("💾 Enregistrement en cours..."):
                    
                    if not is_admin:
                        type_charge = "Commande"

                    # Préparer la description complète
                    desc_complete = description
                    if commentaire:
                        desc_complete = f"{description} | {commentaire}" if description else commentaire
                    
                    charge_id = charges_model.ajouter_charge(
                        couturier_id=couturier_id_auteur,
                        type_charge=type_charge,
                        categorie=categorie,
                        montant=montant,
                        date_charge=date_charge.strftime('%Y-%m-%d'),
                        description=desc_complete,
                        commande_id=commande_id
                    )
                    
                    if charge_id:
                        st.success("✅ Charge enregistrée avec succès !")
                        st.balloons()
                        st.rerun()
                    else:
                        detail = getattr(charges_model, "last_error", None) or ""
                        st.error(
                            "❌ Erreur lors de l'enregistrement"
                            + (f" : {detail}" if detail else "")
                        )


# ============================================================================
# LISTE DES CHARGES
# ============================================================================

def afficher_liste_charges(
    charges_model: ChargesModel,
    couturier_id: Optional[int],
    is_admin: bool = False,
    salon_id_user: Optional[str] = None,
):
    """Affiche la liste complète des charges avec filtres"""
    
    if is_admin:
        st.markdown("### 📋 Liste de toutes les charges de l'entreprise")
    else:
        st.markdown("### 📋 Liste de toutes vos charges")
    st.markdown("---")
    
    # ========================================================================
    # FILTRES
    # ========================================================================
    
    st.markdown("#### 🔍 Filtres")
    
    type_filter = None
    if is_admin:
        col_f1, col_f2, col_f3 = st.columns(3)
        with col_f1:
            date_debut_filter = st.date_input(
                "Date de début",
                value=datetime.now().date() - timedelta(days=30),
                key="liste_date_debut"
            )
        with col_f2:
            date_fin_filter = st.date_input(
                "Date de fin",
                value=datetime.now().date(),
                key="liste_date_fin"
            )
        with col_f3:
            type_filter = st.multiselect(
                "Filtrer par type",
                options=list(TYPES_CHARGES.keys()),
                default=list(TYPES_CHARGES.keys()),
                key="liste_type_filter"
            )
    else:
        col_f1, col_f2 = st.columns(2)
        with col_f1:
            date_debut_filter = st.date_input(
                "Date de début",
                value=datetime.now().date() - timedelta(days=30),
                key="liste_date_debut"
            )
        with col_f2:
            date_fin_filter = st.date_input(
                "Date de fin",
                value=datetime.now().date(),
                key="liste_date_fin"
            )
    
    st.markdown("---")
    
    # ========================================================================
    # RÉCUPÉRATION DES CHARGES
    # ========================================================================
    
    # Filtrer par salon_id ET couturier_id (comme dans la page ajouter et analyse)
    charges = charges_model.lister_charges(
        couturier_id,
        limit=1000,
        tous_les_couturiers=False,
        salon_id=salon_id_user  # Toujours passer salon_id pour filtrer correctement
    )
    
    if not charges:
        st.info("💭 Aucune charge enregistrée pour le moment")
        return
    
    # Filtrer les charges
    df = pd.DataFrame(charges)
    
    # Conversion de date_charge en datetime si c'est une string
    if 'date_charge' in df.columns:
        df['date_charge'] = pd.to_datetime(df['date_charge'])
    
    # Appliquer les filtres
    mask_periode = (
        (df['date_charge'].dt.date >= date_debut_filter) &
        (df['date_charge'].dt.date <= date_fin_filter)
    )
    df_periode = df[mask_periode].copy()
    
    if df_periode.empty:
        st.warning("⚠️ Aucune charge sur cette période")
        return
    
    if is_admin:
        df_filtered = df_periode[df_periode['type'].isin(type_filter)].copy()
    else:
        df_filtered = df_periode[df_periode['type'] == "Commande"].copy()
    
    # ========================================================================
    # KPIs
    # ========================================================================
    
    st.markdown("#### 📊 Statistiques sur la période")
    
    if df_filtered.empty:
        st.warning("⚠️ Aucune charge ne correspond aux filtres sélectionnés")
    else:
        col_k1, col_k2, col_k3, col_k4 = st.columns(4)
        
        with col_k1:
            total_charges = df_filtered['montant'].sum()
            st.metric(
                label="💰 Total des charges",
                value=f"{total_charges:,.0f} FCFA"
            )
        
        with col_k2:
            nb_charges = len(df_filtered)
            st.metric(
                label="📝 Nombre de charges",
                value=f"{nb_charges}"
            )
        
        with col_k3:
            moyenne = df_filtered['montant'].mean()
            st.metric(
                label="📈 Montant moyen",
                value=f"{moyenne:,.0f} FCFA"
            )
        
        with col_k4:
            nb_jours = (date_fin_filter - date_debut_filter).days + 1
            moy_jour = total_charges / nb_jours if nb_jours > 0 else 0
            st.metric(
                label="📅 Moyenne/jour",
                value=f"{moy_jour:,.0f} FCFA"
            )
    
    st.markdown("---")
    
    # ========================================================================
    # TABLEAU
    # ========================================================================
    
    st.markdown("#### 📊 Analyse des charges liées aux commandes")
    
    df_commandes = df_periode[df_periode['type'] == "Commande"].copy()
    
    if df_commandes.empty:
        st.info("💭 Aucune charge liée à une commande sur la période")
    else:
        if 'commande_id' in df_commandes.columns and df_commandes['commande_id'].notna().any():
            df_cmd_commande = (
                df_commandes.groupby('commande_id')['montant'].sum().reset_index()
            )
            df_cmd_commande['commande_label'] = df_cmd_commande['commande_id'].apply(
                lambda x: f"CMD-{int(x)}"
            )
            df_cmd_commande = df_cmd_commande.sort_values('montant', ascending=True).tail(12)
            
            fig_cmd_commande = px.bar(
                df_cmd_commande,
                x='montant',
                y='commande_label',
                orientation='h',
                title="Répartition par commande",
                labels={'montant': 'Montant (FCFA)', 'commande_label': 'Commande'},
                color='montant',
                color_continuous_scale='Blues'
            )
            fig_cmd_commande.update_traces(
                hovertemplate='<b>%{y}</b><br>Montant: %{x:,.0f} FCFA<extra></extra>'
            )
            st.plotly_chart(fig_cmd_commande, use_container_width=True)
        else:
            st.info("ℹ️ Aucune commande liée trouvée dans les charges sélectionnées")
        
        df_cmd_cat = df_commandes.groupby('categorie')['montant'].sum().reset_index()
        df_cmd_cat['categorie_label'] = df_cmd_cat['categorie'].apply(
            lambda x: CATEGORIES_CHARGES.get(x, x)
        )
        
        fig_cmd_cat = px.pie(
            df_cmd_cat,
            values='montant',
            names='categorie_label',
            hole=0.4,
            title="Répartition par catégorie (charges de commande)"
        )
        fig_cmd_cat.update_layout(
            showlegend=True,
            plot_bgcolor='rgba(0,0,0,0)',
            paper_bgcolor='rgba(0,0,0,0)'
        )
        st.plotly_chart(fig_cmd_cat, use_container_width=True)
        
        df_cmd_time = df_commandes.groupby(df_commandes['date_charge'].dt.date)['montant'].sum().reset_index()
        df_cmd_time.columns = ['date', 'montant']
        
        fig_cmd_time = px.line(
            df_cmd_time,
            x='date',
            y='montant',
            markers=True,
            title="Évolution des charges liées aux commandes"
        )
        fig_cmd_time.update_layout(
            hovermode='x unified',
            plot_bgcolor='rgba(0,0,0,0)',
            paper_bgcolor='rgba(0,0,0,0)'
        )
        st.plotly_chart(fig_cmd_time, use_container_width=True)
    
    st.markdown("---")
    
    st.markdown("#### 📄 Détails des charges")
    
    if df_filtered.empty:
        st.info("ℹ️ Aucun détail à afficher avec les filtres actuels")
    else:
        # Préparer le dataframe pour l'affichage
        df_display = df_filtered[['date_charge', 'type', 'categorie', 'description', 'montant']].copy()
        df_display['date_charge'] = df_display['date_charge'].dt.strftime('%d/%m/%Y')
        df_display['montant'] = df_display['montant'].apply(lambda x: f"{x:,.0f} FCFA")
        df_display['type'] = df_display['type'].apply(lambda x: TYPES_CHARGES.get(x, x))
        df_display['categorie'] = df_display['categorie'].apply(lambda x: CATEGORIES_CHARGES.get(x, x))
        
        df_display.columns = ['Date', 'Type', 'Catégorie', 'Description', 'Montant']
        
        st.dataframe(
            df_display,
            use_container_width=True,
            hide_index=True,
            height=400
        )
        
        # ========================================================================
        # EXPORT
        # ========================================================================
        
        st.markdown("---")
        st.markdown("#### 📥 Exporter les données")
        
        col_e1, col_e2, col_e3 = st.columns([1, 1, 2])
        
        with col_e1:
            # Export CSV
            csv = df_display.to_csv(index=False, encoding='utf-8-sig')
            st.download_button(
                label="📄 Télécharger CSV",
                data=csv,
                file_name=f"charges_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                mime="text/csv",
                use_container_width=True
            )
        
        with col_e2:
            # Export Excel
            buffer = io.BytesIO()
            with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
                df_display.to_excel(writer, index=False, sheet_name='Charges')
            
            st.download_button(
                label="📊 Télécharger Excel",
                data=buffer.getvalue(),
                file_name=f"charges_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                use_container_width=True
            )


# ============================================================================
# ANALYSES ET GRAPHIQUES
# ============================================================================

def afficher_analyses_graphiques(
    charges_model: ChargesModel,
    commande_model: CommandeModel,
    couturier_id: Optional[int],
    is_admin: bool = False,
    salon_id_user: Optional[str] = None,
):
    """Affiche les analyses avec graphiques Plotly"""
    
    if is_admin:
        st.markdown("### 📊 Analyses visuelles de toutes les charges")
    else:
        st.markdown("### 📊 Analyses visuelles de vos charges")
    st.markdown("---")
    
    # ========================================================================
    # SÉLECTION DE PÉRIODE
    # ========================================================================
    
    col_p1, col_p2 = st.columns(2)
    
    with col_p1:
        date_debut_analyse = st.date_input(
            "Date de début",
            value=datetime.now().date() - timedelta(days=90),
            key="analyse_date_debut"
        )
    
    with col_p2:
        date_fin_analyse = st.date_input(
            "Date de fin",
            value=datetime.now().date(),
            key="analyse_date_fin"
        )
    
    st.markdown("---")
    
    # Récupérer les charges : filtrer par salon_id ET couturier_id (comme dans la page ajouter)
    charges = charges_model.lister_charges(
        couturier_id,
        limit=1000,
        tous_les_couturiers=False,
        salon_id=salon_id_user  # Toujours passer salon_id pour filtrer correctement
    )
    
    if not charges:
        st.info("💭 Aucune donnée disponible pour l'analyse")
        return
    
    df = pd.DataFrame(charges)
    df['date_charge'] = pd.to_datetime(df['date_charge'])
    
    # Filtrer par période
    mask = (
        (df['date_charge'].dt.date >= date_debut_analyse) &
        (df['date_charge'].dt.date <= date_fin_analyse)
    )
    df_analyse = df[mask].copy()
    
    if df_analyse.empty:
        st.warning("⚠️ Aucune charge sur cette période")
        return
    
    # ========================================================================
    # GRAPHIQUE 1 : RÉPARTITION PAR TYPE (CAMEMBERT)
    # ========================================================================
    
    st.markdown("#### 🥧 Répartition des charges par type")
    
    df_by_type = df_analyse.groupby('type')['montant'].sum().reset_index()
    df_by_type['type_label'] = df_by_type['type'].apply(lambda x: TYPES_CHARGES.get(x, x))
    
    fig_pie = px.pie(
        df_by_type,
        values='montant',
        names='type_label',
        title='Répartition des charges par type',
        color_discrete_sequence=px.colors.qualitative.Set3,
        hole=0.4
    )
    
    fig_pie.update_traces(
        textposition='inside',
        textinfo='percent+label',
        hovertemplate='<b>%{label}</b><br>Montant: %{value:,.0f} FCFA<br>Pourcentage: %{percent}<extra></extra>'
    )
    
    st.plotly_chart(fig_pie, use_container_width=True)
    
    st.markdown("---")
    
    # ========================================================================
    # GRAPHIQUE 2 : RÉPARTITION PAR CATÉGORIE (BARRES HORIZONTALES)
    # ========================================================================
    
    st.markdown("#### 📊 Répartition des charges par catégorie")
    
    df_by_cat = df_analyse.groupby('categorie')['montant'].sum().reset_index()
    df_by_cat['categorie_label'] = df_by_cat['categorie'].apply(lambda x: CATEGORIES_CHARGES.get(x, x))
    df_by_cat = df_by_cat.sort_values('montant', ascending=True)
    
    fig_bar = px.bar(
        df_by_cat,
        x='montant',
        y='categorie_label',
        orientation='h',
        title='Montant par catégorie de charge',
        labels={'montant': 'Montant (FCFA)', 'categorie_label': 'Catégorie'},
        color='montant',
        color_continuous_scale='Viridis'
    )
    
    fig_bar.update_traces(
        hovertemplate='<b>%{y}</b><br>Montant: %{x:,.0f} FCFA<extra></extra>'
    )
    
    st.plotly_chart(fig_bar, use_container_width=True)
    
    st.markdown("---")
    
    # ========================================================================
    # GRAPHIQUE 3 : ÉVOLUTION DANS LE TEMPS (LIGNE)
    # ========================================================================
    
    st.markdown("#### 📈 Évolution des charges dans le temps")
    
    # Grouper par jour
    df_time = df_analyse.groupby(df_analyse['date_charge'].dt.date)['montant'].sum().reset_index()
    df_time.columns = ['date', 'montant']
    
    fig_line = px.line(
        df_time,
        x='date',
        y='montant',
        title='Évolution quotidienne des charges',
        labels={'date': 'Date', 'montant': 'Montant (FCFA)'},
        markers=True
    )
    
    fig_line.update_traces(
        line_color='#B19CD9',
        line_width=3,
        hovertemplate='<b>Date:</b> %{x}<br><b>Montant:</b> %{y:,.0f} FCFA<extra></extra>'
    )
    
    fig_line.update_layout(
        hovermode='x unified',
        plot_bgcolor='rgba(0,0,0,0)',
        paper_bgcolor='rgba(0,0,0,0)'
    )
    
    st.plotly_chart(fig_line, use_container_width=True)
    
    st.markdown("---")
    
    # ========================================================================
    # ANALYSE DES CHARGES LIÉES AUX COMMANDES
    # ========================================================================
    
    st.markdown("#### 🧾 Charges liées aux commandes")
    
    df_cmd = df_analyse[df_analyse['type'] == "Commande"].copy()
    
    if df_cmd.empty:
        st.info("💭 Aucune charge liée à une commande sur la période")
    else:
        # Construire un libellé lisible pour les commandes
        if couturier_id is not None:
            commandes = commande_model.lister_commandes(
                couturier_id=couturier_id,
                tous_les_couturiers=False,
                salon_id=salon_id_user
            )
        else:
            commandes = commande_model.lister_commandes(
                couturier_id=None,
                tous_les_couturiers=False,
                salon_id=salon_id_user
            )
        
        commande_labels = {}
        if commandes:
            commande_labels = {
                c['id']: f"CMD-{c['id']} | {c.get('modele', 'N/A')} - {c.get('client_nom', 'Client')}"
                for c in commandes
            }
        
        if 'commande_id' in df_cmd.columns and df_cmd['commande_id'].notna().any():
            df_cmd_commande = df_cmd.groupby('commande_id')['montant'].sum().reset_index()
            df_cmd_commande['commande_label'] = df_cmd_commande['commande_id'].apply(
                lambda x: commande_labels.get(int(x), f"CMD-{int(x)}")
            )
            df_cmd_commande = df_cmd_commande.sort_values('montant', ascending=True).tail(12)
            
            fig_cmd_commande = px.bar(
                df_cmd_commande,
                x='montant',
                y='commande_label',
                orientation='h',
                title="Répartition des charges par commande",
                labels={'montant': 'Montant (FCFA)', 'commande_label': 'Commande'},
                color='montant',
                color_continuous_scale='Blues'
            )
            fig_cmd_commande.update_traces(
                hovertemplate='<b>%{y}</b><br>Montant: %{x:,.0f} FCFA<extra></extra>'
            )
            st.plotly_chart(fig_cmd_commande, use_container_width=True)
        else:
            st.info("ℹ️ Aucune commande liée trouvée pour cette période")
        
        df_cmd_cat = df_cmd.groupby('categorie')['montant'].sum().reset_index()
        df_cmd_cat['categorie_label'] = df_cmd_cat['categorie'].apply(
            lambda x: CATEGORIES_CHARGES.get(x, x)
        )
        
        fig_cmd_cat = px.pie(
            df_cmd_cat,
            values='montant',
            names='categorie_label',
            hole=0.4,
            title="Répartition par catégorie (charges de commande)"
        )
        fig_cmd_cat.update_layout(
            showlegend=True,
            plot_bgcolor='rgba(0,0,0,0)',
            paper_bgcolor='rgba(0,0,0,0)'
        )
        st.plotly_chart(fig_cmd_cat, use_container_width=True)
    
    st.markdown("---")
    
    # ========================================================================
    # GRAPHIQUE 4 : TOP 10 DES PLUS GROSSES CHARGES
    # ========================================================================
    
    st.markdown("#### 🏆 Top 10 des plus grosses charges")
    
    df_top = df_analyse.nlargest(10, 'montant')[['date_charge', 'type', 'categorie', 'description', 'montant']].copy()
    df_top['date_charge'] = df_top['date_charge'].dt.strftime('%d/%m/%Y')
    df_top['label'] = df_top.apply(
        lambda row: f"{row['date_charge']} - {row['description'][:30] if row['description'] else 'Sans description'}",
        axis=1
    )
    
    fig_top = px.bar(
        df_top,
        x='montant',
        y='label',
        orientation='h',
        title='Les 10 plus grosses dépenses',
        labels={'montant': 'Montant (FCFA)', 'label': ''},
        color='montant',
        color_continuous_scale='Oranges'
    )
    
    fig_top.update_traces(
        hovertemplate='<b>%{y}</b><br>Montant: %{x:,.0f} FCFA<extra></extra>'
    )
    
    st.plotly_chart(fig_top, use_container_width=True)
    
    st.markdown("---")
    
    # ========================================================================
    # RÉCAPITULATIF MENSUEL
    # ========================================================================
    
    st.markdown("#### 📅 Récapitulatif mensuel")
    
    df_mensuel = df_analyse.copy()
    df_mensuel['mois'] = df_mensuel['date_charge'].dt.to_period('M')
    df_monthly = df_mensuel.groupby('mois')['montant'].agg(['sum', 'count', 'mean']).reset_index()
    df_monthly['mois'] = df_monthly['mois'].astype(str)
    df_monthly.columns = ['Mois', 'Total (FCFA)', 'Nombre de charges', 'Montant moyen']
    
    # Formater les montants
    df_monthly['Total (FCFA)'] = df_monthly['Total (FCFA)'].apply(lambda x: f"{x:,.0f}")
    df_monthly['Montant moyen'] = df_monthly['Montant moyen'].apply(lambda x: f"{x:,.0f}")
    
    st.dataframe(df_monthly, use_container_width=True, hide_index=True)


# ============================================================================
# CALCUL D'IMPÔTS
# ============================================================================

def afficher_calcul_impots(
    charges_model: ChargesModel,
    commande_model: CommandeModel,
    couturier_id: Optional[int],
    is_admin: bool = False,
    salon_id_user: Optional[str] = None,
):
    """Calcule les impôts en fonction du chiffre d'affaires"""
    
    st.markdown("### 🧮 Calculateur d'impôts")
    if is_admin:
        st.info("👑 Vue administrateur : Calcul des impôts sur toutes les activités de l'entreprise")
    else:
        st.markdown("Estimez vos impôts en fonction de votre chiffre d'affaires")
    st.markdown("---")
    
    # ========================================================================
    # SÉLECTION DE PÉRIODE
    # ========================================================================
    
    col1, col2 = st.columns(2)
    
    with col1:
        date_debut_impot = st.date_input(
            "Date de début",
            value=datetime.now().replace(day=1).date(),
            key="impot_date_debut"
        )
    
    with col2:
        date_fin_impot = st.date_input(
            "Date de fin",
            value=datetime.now().date(),
            key="impot_date_fin"
        )
    
    st.markdown("---")
    
    # ========================================================================
    # CALCUL DU CHIFFRE D'AFFAIRES
    # ========================================================================
    
    st.markdown("#### 💵 Chiffre d'affaires")
    
    # Récupérer les commandes (filtrées par salon si admin)
    commandes = commande_model.lister_commandes(
        couturier_id=None if is_admin else couturier_id,
        tous_les_couturiers=is_admin,
        salon_id=salon_id_user if is_admin else None
    )
    
    if not commandes:
        st.warning("⚠️ Aucune commande enregistrée")
        ca_total = 0
    else:
        df_cmd = pd.DataFrame(commandes)
        
        # Filtrer par date si date_creation existe
        if 'date_creation' in df_cmd.columns:
            df_cmd['date_creation'] = pd.to_datetime(df_cmd['date_creation'])
            mask_cmd = (
                (df_cmd['date_creation'].dt.date >= date_debut_impot) &
                (df_cmd['date_creation'].dt.date <= date_fin_impot)
            )
            df_cmd_filtered = df_cmd[mask_cmd]
        else:
            df_cmd_filtered = df_cmd
        
        # Calculer le CA (somme des prix_total)
        ca_total = df_cmd_filtered['prix_total'].sum() if 'prix_total' in df_cmd_filtered.columns else 0
    
    col_ca1, col_ca2 = st.columns(2)
    
    with col_ca1:
        st.metric(
            label="📊 Chiffre d'affaires total",
            value=f"{ca_total:,.0f} FCFA"
        )
    
    # Permettre aussi une saisie manuelle
    with col_ca2:
        ca_manuel = st.number_input(
            "Ou saisir manuellement le CA",
            min_value=0.0,
            value=float(ca_total),
            step=100000.0,
            format="%.2f",
            help="Vous pouvez ajuster le montant si nécessaire"
        )
    
    ca_a_utiliser = ca_manuel
    
    st.markdown("---")
    
    # ========================================================================
    # CALCUL DES CHARGES
    # ========================================================================
    
    st.markdown("#### 💰 Total des charges")
    
    date_debut_dt = datetime.combine(date_debut_impot, datetime.min.time())
    date_fin_dt = datetime.combine(date_fin_impot, datetime.max.time())
    
    # Filtrer par salon_id ET couturier_id (comme dans la page ajouter et analyse)
    total_charges = charges_model.total_charges(
        couturier_id,
        date_debut_dt,
        date_fin_dt,
        tous_les_couturiers=False,
        salon_id=salon_id_user  # Toujours passer salon_id pour filtrer correctement
    )
    
    st.metric(
        label="💸 Total des charges",
        value=f"{total_charges:,.0f} FCFA"
    )
    
    st.markdown("---")
    
    # ========================================================================
    # CALCUL DE L'IMPÔT SELON LES TRANCHES
    # ========================================================================
    
    st.markdown("#### 🏦 Calcul de l'impôt")
    
    # Déterminer la tranche
    impot_a_payer = 0
    tranche_applicable = None
    
    for tranche in TRANCHES_IMPOTS:
        if tranche['min'] <= ca_a_utiliser <= tranche['max']:
            impot_a_payer = tranche['impot']
            tranche_applicable = tranche
            break

    lignes_bareme = "\n".join(
        f"- {t['min']:,.0f} – {t['max']:,.0f} FCFA → **{t['impot']:,.0f} FCFA**"
        for t in TRANCHES_IMPOTS
    )
    st.info(f"**Barème des impôts (indicatif)**\n\n{lignes_bareme}")

    st.markdown("---")
    resultat_avant_impot = float(ca_a_utiliser) - float(total_charges)
    c_res1, c_res2, c_res3 = st.columns(3)
    with c_res1:
        st.metric("CA retenu", f"{float(ca_a_utiliser):,.0f} FCFA")
    with c_res2:
        st.metric("Charges sur la période", f"{float(total_charges):,.0f} FCFA")
    with c_res3:
        st.metric("Résultat avant impôt", f"{resultat_avant_impot:,.0f} FCFA")

    if tranche_applicable:
        st.success(
            f"Tranche applicable : {tranche_applicable['min']:,.0f} – "
            f"{tranche_applicable['max']:,.0f} FCFA"
        )
    else:
        st.warning(
            "Aucune tranche du barème ne correspond exactement au montant saisi. "
            "Vérifiez le CA ou complétez les tranches dans le code si besoin."
        )
    st.metric("Impôt estimé", f"{impot_a_payer:,.0f} FCFA")


# ============================================================================
# FONCTIONS UTILITAIRES POUR FICHIERS
# ============================================================================

# Fonction supprimée - utilisez la version optimisée ci-dessus (ligne 67)


def _get_logo_from_db(salon_id: Optional[str] = None) -> Optional[bytes]:
    """
    Récupère le logo depuis la base de données (priorité)
    
    Args:
        salon_id: ID du salon (si None, essaie de le récupérer depuis session)
    
    Returns:
        Bytes du logo ou None si non trouvé
    """
    try:
        if not salon_id and st.session_state.get('couturier_data'):
            from utils.role_utils import obtenir_salon_id
            salon_id = obtenir_salon_id(st.session_state.couturier_data)
        
        if salon_id and st.session_state.get('db_connection'):
            from models.database import AppLogoModel
            logo_model = AppLogoModel(st.session_state.db_connection)
            logo_data = logo_model.recuperer_logo(salon_id)
            
            if logo_data and logo_data.get('logo_data'):
                print(f"✅ Logo récupéré depuis la BDD (Salon ID: {salon_id})")
                return logo_data['logo_data']
    except Exception as e:
        print(f"Erreur récupération logo depuis BDD: {e}")
    
    return None


def _generer_pdf_impots(date_debut,
                        date_fin,
                        ca: float,
                        total_charges: float,
                        impot: float,
                        benefice: float,
                        df_charges: pd.DataFrame) -> Optional[Dict[str, bytes]]:
    """
    Génère un PDF récapitulatif des impôts pour une période donnée.

    Returns:
        dict avec keys: 'filename', 'content' (bytes) ou None en cas d'erreur
    """
    try:
        # Nom de fichier lisible pour le fisc : Releve_Impots_dd-mm-yyyy_au_dd-mm-yyyy.pdf
        date_debut_str = date_debut.strftime('%d-%m-%Y')
        date_fin_str = date_fin.strftime('%d-%m-%Y')
        filename = f"Releve_Impots_{date_debut_str}_au_{date_fin_str}.pdf"
        temp_dir = tempfile.gettempdir()
        filepath = os.path.join(temp_dir, filename)

        # Récupérer le logo et les infos salon depuis la BDD en priorité
        # Récupérer salon_id depuis la session
        salon_id = None
        try:
            if st.session_state.get('couturier_data'):
                from utils.role_utils import obtenir_salon_id
                salon_id = obtenir_salon_id(st.session_state.couturier_data)
        except:
            pass
        logo_filigrane_data = _get_logo_from_db(salon_id)
        # IMPORTANT : pas de fallback vers assets -> si pas de logo en BDD, aucun logo n'est utilisé
        logo_path, logo_filigrane_path = None, None

        # Préparer les lignes de pied de page (informations du salon)
        footer_lines = None
        try:
            if salon_id and st.session_state.get('db_connection'):
                from models.salon_model import SalonModel
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
            print(f"Erreur construction pied de page impôts: {e}")

        def dessiner_filigrane(canvas_obj, doc_obj):
            logo_img = None
            
            # Utiliser le logo depuis la BDD si disponible
            if logo_filigrane_data:
                try:
                    logo_img = PILImage.open(io.BytesIO(logo_filigrane_data))
                    print("✅ Filigrane: Logo chargé depuis la BDD")
                except Exception as e:
                    print(f"Erreur chargement logo filigrane depuis BDD: {e}")
            
            if not logo_img:
                return
            
            try:
                canvas_obj.saveState()
                # Transparence légère
                if hasattr(canvas_obj, "setFillAlpha"):
                    canvas_obj.setFillAlpha(0.08)

                # logo_img est déjà chargé ci-dessus
                logo_img.thumbnail((300, 300), PILImage.Resampling.LANCZOS)

                img_width = logo_img.width * 0.75
                img_height = logo_img.height * 0.75
                # Utiliser la taille réelle de la page (paysage)
                page_width, page_height = doc_obj.pagesize
                x = (page_width - img_width) / 2
                y = (page_height - img_height) / 2

                canvas_obj.drawImage(
                    ImageReader(logo_img),
                    x, y,
                    width=img_width,
                    height=img_height,
                    preserveAspectRatio=True
                )
                canvas_obj.restoreState()
            except Exception as e:
                print(f"Erreur filigrane impôts: {e}")

        def dessiner_footer(canvas_obj, doc_obj):
            if not footer_lines:
                return
            try:
                canvas_obj.saveState()
                page_width, _ = doc_obj.pagesize
                footer_height = 2 * cm
                # Bande de fond sur toute la largeur en bas de page
                canvas_obj.setFillColor(colors.HexColor('#17BEBB'))
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
                print(f"Erreur pied de page impôts: {e}")

        doc = SimpleDocTemplate(
            filepath,
            pagesize=landscape(A4),
            rightMargin=2 * cm,
            leftMargin=2 * cm,
            topMargin=2 * cm,
            bottomMargin=2 * cm,
        )

        elements = []
        styles = getSampleStyleSheet()

        title_style = ParagraphStyle(
            'TitreImpot',
            parent=styles['Heading1'],
            fontSize=20,
            textColor=colors.HexColor('#2C3E50'),
            alignment=1,
            spaceAfter=20
        )

        heading_style = ParagraphStyle(
            'SectionHeading',
            parent=styles['Heading2'],
            fontSize=14,
            textColor=colors.HexColor('#34495E'),
            spaceAfter=10
        )

        # Style pour les descriptions longues (multi-lignes, petite police)
        desc_style = ParagraphStyle(
            'DescCharge',
            parent=styles['Normal'],
            fontSize=8,
            leading=9,
            spaceAfter=0,
            spaceBefore=0
        )

        # Logo centré (uniquement si disponible en BDD)
        if logo_filigrane_data:
            try:
                logo_img = PILImage.open(io.BytesIO(logo_filigrane_data))
                logo_img.thumbnail((200, 200), PILImage.Resampling.LANCZOS)
                logo_table_data = [[Image(ImageReader(logo_img), width=3.5 * cm, height=3.5 * cm)]]
                logo_table = Table(logo_table_data, colWidths=[15 * cm])
                logo_table.setStyle(TableStyle([
                    ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                    ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                ]))
                elements.append(logo_table)
            except Exception as e:
                print(f"Erreur logo impôts (BDD): {e}")

        elements.append(Spacer(1, 0.4 * cm))
        titre = f"RELEVÉ D'IMPÔTS<br/>{date_debut.strftime('%d/%m/%Y')} - {date_fin.strftime('%d/%m/%Y')}"
        elements.append(Paragraph(titre, title_style))
        elements.append(Spacer(1, 0.3 * cm))

        # Récapitulatif financier
        elements.append(Paragraph("Récapitulatif financier", heading_style))

        recap_data = [
            ["Chiffre d'affaires", f"{ca:,.0f} FCFA"],
            ["Total des charges", f"{total_charges:,.0f} FCFA"],
            ["Impôt à payer", f"{impot:,.0f} FCFA"],
            ["Bénéfice net", f"{benefice:,.0f} FCFA"],
        ]

        recap_table = Table(recap_data, colWidths=[7 * cm, 8 * cm])
        recap_table.setStyle(TableStyle([
            ('GRID', (0, 0), (-1, -1), 0.4, colors.grey),
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#ECF0F1')),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('BACKGROUND', (0, 2), (-1, 2), colors.HexColor('#FFF4E6')),
            ('TEXTCOLOR', (0, 2), (-1, 2), colors.HexColor('#F39C12')),
            ('FONTNAME', (0, 2), (-1, 2), 'Helvetica-Bold'),
        ]))
        elements.append(recap_table)
        elements.append(Spacer(1, 0.5 * cm))

        # Tableau des charges
        elements.append(Paragraph("Détail des charges sur la période", heading_style))

        charges_data = [["Date", "Type", "Catégorie", "Description", "Montant (FCFA)"]]

        if not df_charges.empty:
            df_tmp = df_charges.copy()
            df_tmp['date_charge'] = pd.to_datetime(df_tmp['date_charge'])
            df_tmp = df_tmp.sort_values('date_charge')
            for _, row in df_tmp.iterrows():
                date_str = row['date_charge'].strftime('%d/%m/%Y')
                type_str = str(row.get('type', ''))
                cat_str = str(row.get('categorie', ''))
                raw_desc = str(row.get('description', '') or f"Charge {cat_str}")
                # Autoriser le retour à la ligne dans la cellule
                para_desc = Paragraph(raw_desc.replace('\n', '<br/>'), desc_style)
                montant = f"{float(row.get('montant', 0)):,.0f}"
                charges_data.append([date_str, type_str, cat_str, para_desc, montant])
        else:
            charges_data.append(["Aucune charge", "", "", "", ""])

        # Colonnes optimisées pour laisser plus de place à la Description
        charges_table = Table(
            charges_data,
            colWidths=[2.3 * cm, 2.3 * cm, 2.7 * cm, 7.0 * cm, 2.4 * cm]
        )
        charges_table.setStyle(TableStyle([
            ('GRID', (0, 0), (-1, -1), 0.3, colors.grey),
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#3498DB')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 8),
        ]))
        elements.append(charges_table)

        def _on_page(canvas_obj, doc_obj):
            dessiner_filigrane(canvas_obj, doc_obj)
            dessiner_footer(canvas_obj, doc_obj)

        doc.build(
            elements,
            onFirstPage=_on_page,
            onLaterPages=_on_page
        )

        with open(filepath, "rb") as f:
            content = f.read()

        try:
            os.remove(filepath)
        except Exception:
            pass

        return {"filename": filename, "content": content}
    except Exception as e:
        print(f"Erreur génération PDF impôts: {e}")
        return None


def _generer_pdf_analyse_charges(date_debut,
                                 date_fin,
                                 df_details: pd.DataFrame,
                                 df_recap: pd.DataFrame) -> Optional[Dict[str, bytes]]:
    """
    Génère un PDF d'analyse des charges (détails + récap mensuel + évolution graphique)
    en mode paysage avec logo et filigrane.
    """
    try:
        # Nom de fichier lisible
        dd_str = date_debut.strftime('%d-%m-%Y')
        df_str = date_fin.strftime('%d-%m-%Y')
        filename = f"AnalyseDesCharges_Du_{dd_str}_Et_{df_str}.pdf"

        temp_dir = tempfile.gettempdir()
        filepath = os.path.join(temp_dir, filename)

        # Récupérer le logo et les infos salon depuis la BDD en priorité
        salon_id = None
        try:
            if st.session_state.get('couturier_data'):
                from utils.role_utils import obtenir_salon_id
                salon_id = obtenir_salon_id(st.session_state.couturier_data)
        except:
            pass
        logo_filigrane_data = _get_logo_from_db(salon_id)
        # IMPORTANT : pas de fallback vers assets -> si pas de logo en BDD, aucun logo n'est utilisé
        logo_path, logo_filigrane_path = None, None

        # Préparer les lignes de pied de page (informations du salon)
        footer_lines = None
        try:
            if salon_id and st.session_state.get('db_connection'):
                from models.salon_model import SalonModel
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
            print(f"Erreur construction pied de page analyse charges: {e}")

        def dessiner_filigrane(canvas_obj, doc_obj):
            logo_img = None
            
            # Utiliser le logo depuis la BDD si disponible (PRIORITÉ)
            if logo_filigrane_data:
                try:
                    logo_img = PILImage.open(io.BytesIO(logo_filigrane_data))
                    print("✅ Filigrane: Logo chargé depuis la BDD")
                except Exception as e:
                    print(f"Erreur chargement logo filigrane depuis BDD: {e}")
            
            if not logo_img:
                return
            try:
                canvas_obj.saveState()
                if hasattr(canvas_obj, "setFillAlpha"):
                    canvas_obj.setFillAlpha(0.08)

                # logo_img déjà chargé depuis la BDD ci-dessus
                logo_img.thumbnail((400, 400), PILImage.Resampling.LANCZOS)

                img_width = logo_img.width * 0.75
                img_height = logo_img.height * 0.75
                page_width, page_height = doc_obj.pagesize
                x = (page_width - img_width) / 2
                y = (page_height - img_height) / 2

                canvas_obj.drawImage(
                    ImageReader(logo_img),
                    x, y,
                    width=img_width,
                    height=img_height,
                    preserveAspectRatio=True
                )
                canvas_obj.restoreState()
            except Exception as e:
                print(f"Erreur filigrane analyse charges: {e}")

        doc = SimpleDocTemplate(
            filepath,
            pagesize=landscape(A4),
            rightMargin=2 * cm,
            leftMargin=2 * cm,
            topMargin=2 * cm,
            bottomMargin=2 * cm,
        )

        elements = []
        styles = getSampleStyleSheet()

        title_style = ParagraphStyle(
            'TitreAnalyse',
            parent=styles['Heading1'],
            fontSize=20,
            textColor=colors.HexColor('#2C3E50'),
            alignment=1,
            spaceAfter=18
        )

        heading_style = ParagraphStyle(
            'HeadingSection',
            parent=styles['Heading2'],
            fontSize=14,
            textColor=colors.HexColor('#34495E'),
            spaceAfter=10
        )

        cell_style = ParagraphStyle(
            'Cellule',
            parent=styles['Normal'],
            fontSize=8,
            leading=9,
            spaceAfter=0,
            spaceBefore=0
        )

        # Logo centré (uniquement si disponible en BDD)
        if logo_filigrane_data:
            try:
                logo_img = PILImage.open(io.BytesIO(logo_filigrane_data))
                logo_img.thumbnail((220, 220), PILImage.Resampling.LANCZOS)
                logo_table_data = [[Image(ImageReader(logo_img), width=3.5 * cm, height=3.5 * cm)]]
                logo_table = Table(logo_table_data, colWidths=[25 * cm])
                logo_table.setStyle(TableStyle([
                    ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                    ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                ]))
                elements.append(logo_table)
            except Exception as e:
                print(f"Erreur logo analyse charges (BDD): {e}")

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
                print(f"Erreur pied de page analyse charges: {e}")

        elements.append(Spacer(1, 0.4 * cm))
        titre = (
            f"ANALYSE DES CHARGES<br/>"
            f"Période du {date_debut.strftime('%d/%m/%Y')} au {date_fin.strftime('%d/%m/%Y')}"
        )
        elements.append(Paragraph(titre, title_style))
        elements.append(Spacer(1, 0.3 * cm))

        # =========================
        # Tableau DÉTAILS DES CHARGES
        # =========================
        elements.append(Paragraph("Détail des charges", heading_style))

        # Préparer les données du tableau
        details = df_details.copy()
        if not details.empty:
            details = details.sort_values('date_charge')
            # S'assurer du format date texte
            details['date_charge'] = pd.to_datetime(details['date_charge']).dt.strftime('%d/%m/%Y')

            table_data = [
                ["Date", "Type", "Catégorie", "Description", "Montant (FCFA)"]
            ]

            for _, row in details.iterrows():
                date_str = str(row.get('date_charge', ''))
                type_str = str(row.get('type', ''))
                cat_str = str(row.get('categorie', ''))
                desc_raw = str(row.get('description', '') or '')
                desc_para = Paragraph(desc_raw.replace('\n', '<br/>'), cell_style)
                montant = f"{float(row.get('montant', 0.0)):,.0f}"
                table_data.append([date_str, type_str, cat_str, desc_para, montant])
        else:
            table_data = [["Date", "Type", "Catégorie", "Description", "Montant (FCFA)"],
                          ["Aucune charge", "", "", "", ""]]

        details_table = Table(
            table_data,
            colWidths=[2.2 * cm, 2.4 * cm, 2.8 * cm, 11.0 * cm, 3.0 * cm]
        )
        details_table.setStyle(TableStyle([
            ('GRID', (0, 0), (-1, -1), 0.35, colors.grey),
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#3498DB')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 9),
            ('FONTSIZE', (0, 1), (-1, -1), 8),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('TOPPADDING', (0, 0), (-1, -1), 4),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ]))
        elements.append(details_table)
        elements.append(Spacer(1, 0.5 * cm))

        # =========================
        # Tableau RÉCAPITULATIF MENSUEL
        # =========================
        elements.append(Paragraph("Récapitulatif mensuel", heading_style))

        recap = df_recap.copy()
        # recap a pour index les labels de mois
        recap_table_data = [["Mois"] + list(recap.columns)]
        for mois_label, row in recap.iterrows():
            ligne = [str(mois_label)]
            for col in recap.columns:
                val = float(row[col]) if pd.notnull(row[col]) else 0.0
                ligne.append(f"{val:,.0f}")
            recap_table_data.append(ligne)

        recap_table = Table(
            recap_table_data,
            colWidths=[4.0 * cm] + [((24 * cm) - 4.0 * cm) / max(1, len(recap.columns))] * len(recap.columns)
        )
        recap_table.setStyle(TableStyle([
            ('GRID', (0, 0), (-1, -1), 0.35, colors.grey),
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#2ECC71')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 9),
            ('FONTSIZE', (0, 1), (-1, -1), 8),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('TOPPADDING', (0, 0), (-1, -1), 4),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ]))
        elements.append(recap_table)
        elements.append(Spacer(1, 0.5 * cm))

        # =========================
        # GRAPHIQUE D'ÉVOLUTION MENSUELLE
        # =========================
        try:
            import matplotlib.pyplot as plt  # type: ignore
            import re

            # Fonction pour nettoyer les labels en enlevant les emojis
            def nettoyer_label(label):
                """Enlève les emojis et caractères spéciaux d'un label pour matplotlib"""
                if not label:
                    return "Type"
                # Convertir en string
                label_str = str(label)
                # Mapping direct des types connus avec emojis vers leurs versions sans emojis
                mapping = {
                    "⏱️ Charges Ponctuelles (réparations...)": "Charges Ponctuelles",
                    "⏱️ Charges Ponctuelles": "Charges Ponctuelles",
                    "⏱️ Ponctuelles": "Ponctuelles",
                    "🧾 Charges liées à une commande": "Charges liées à une commande",
                    "🧾 Liées commande": "Liées commande",
                    "💰 Salaires": "Salaires",
                    "📌 Charges Fixes (loyer, salaires...)": "Charges Fixes",
                    "📌 Charges Fixes": "Charges Fixes",
                }
                # Vérifier si on a un mapping direct
                if label_str in mapping:
                    return mapping[label_str]
                # Sinon, enlever les emojis avec regex
                # Enlever les emojis (caractères Unicode dans les plages d'emojis)
                label_clean = re.sub(r'[\U0001F300-\U0001F9FF\U00002600-\U000026FF\U00002700-\U000027BF]', '', label_str)
                # Nettoyer les espaces multiples
                label_clean = ' '.join(label_clean.split())
                return label_clean.strip() or "Type"

            # Construire un graphique simple à partir du récap mensuel
            fig, ax = plt.subplots(figsize=(8, 3))

            mois_labels = list(recap.index)
            x = range(len(mois_labels))

            type_cols = [c for c in recap.columns if c != 'Total']
            for col in type_cols:
                y = [float(v) for v in recap[col].values]
                # Nettoyer le label pour enlever les emojis
                label_clean = nettoyer_label(col)
                ax.plot(x, y, marker='o', label=label_clean)

            ax.set_xticks(x)
            ax.set_xticklabels(mois_labels, rotation=45, ha='right')
            ax.set_ylabel("Montant (FCFA)")
            ax.set_title("Évolution mensuelle des charges par type")
            ax.grid(True, axis='y', linestyle='--', alpha=0.4)
            ax.legend(fontsize=7)
            fig.tight_layout()

            img_buffer = io.BytesIO()
            fig.savefig(img_buffer, format='png', dpi=120)
            plt.close(fig)
            img_buffer.seek(0)

            evolution_img = Image(img_buffer, width=24 * cm, height=7 * cm)
            elements.append(Paragraph("Évolution graphique", heading_style))
            elements.append(evolution_img)
        except Exception as e:
            print(f"Erreur génération graphique analyse charges: {e}")

        # Générer le PDF
        def _on_page(canvas_obj, doc_obj):
            dessiner_filigrane(canvas_obj, doc_obj)
            dessiner_footer(canvas_obj, doc_obj)

        doc.build(
            elements,
            onFirstPage=_on_page,
            onLaterPages=_on_page
        )

        with open(filepath, "rb") as f:
            content = f.read()

        try:
            os.remove(filepath)
        except Exception:
            pass

        return {"filename": filename, "content": content}
    except Exception as e:
        print(f"Erreur génération PDF analyse charges: {e}")
        return None


def _generer_pdf_bulletin_salaire(employe_nom: str,
                                  montant: float,
                                  periode,
                                  date_paiement,
                                  mode_paiement: str,
                                  charge_id: int) -> Optional[Dict[str, bytes]]:
    """
    Génère un bulletin de paie PDF pour un employé (simple, mais "entreprise").
    """
    try:
        # Nettoyer le nom de l'employé pour le fichier
        nom_simplifie = re.sub(r"[^A-Za-z0-9_\-]", "", employe_nom.replace(" ", "_")) or "employe"
        periode_str = periode.strftime("%m-%Y")
        filename = f"Bulletin_Paie_{nom_simplifie}_{periode_str}.pdf"

        temp_dir = tempfile.gettempdir()
        filepath = os.path.join(temp_dir, filename)

        # Récupérer le logo depuis la BDD en priorité
        salon_id = None
        try:
            if st.session_state.get('couturier_data'):
                from utils.role_utils import obtenir_salon_id
                salon_id = obtenir_salon_id(st.session_state.couturier_data)
        except:
            pass
        
        logo_filigrane_data = _get_logo_from_db(salon_id)
        # IMPORTANT : pas de fallback vers assets -> si pas de logo en BDD, aucun logo n'est utilisé
        logo_path, logo_filigrane_path = None, None

        # Préparer les lignes de pied de page (informations du salon)
        footer_lines = None
        try:
            if salon_id and st.session_state.get('db_connection'):
                from models.salon_model import SalonModel
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
            print(f"Erreur construction pied de page bulletin salaire: {e}")

        def dessiner_filigrane(canvas_obj, doc_obj):
            logo_img = None
            
            # Utiliser le logo depuis la BDD si disponible (PRIORITÉ)
            if logo_filigrane_data:
                try:
                    logo_img = PILImage.open(io.BytesIO(logo_filigrane_data))
                    print("✅ Filigrane: Logo chargé depuis la BDD")
                except Exception as e:
                    print(f"Erreur chargement logo filigrane depuis BDD: {e}")
            
            if not logo_img:
                return
            try:
                canvas_obj.saveState()
                if hasattr(canvas_obj, "setFillAlpha"):
                    canvas_obj.setFillAlpha(0.08)

                # logo_img déjà chargé depuis la BDD ci-dessus
                logo_img.thumbnail((350, 350), PILImage.Resampling.LANCZOS)

                img_width = logo_img.width * 0.7
                img_height = logo_img.height * 0.7
                page_width, page_height = doc_obj.pagesize
                x = (page_width - img_width) / 2
                y = (page_height - img_height) / 2

                canvas_obj.drawImage(
                    ImageReader(logo_img),
                    x, y,
                    width=img_width,
                    height=img_height,
                    preserveAspectRatio=True
                )
                canvas_obj.restoreState()
            except Exception as e:
                print(f"Erreur filigrane bulletin salaire: {e}")

        doc = SimpleDocTemplate(
            filepath,
            pagesize=landscape(A4),  # Bulletin de paie en orientation paysage
            rightMargin=2 * cm,
            leftMargin=2 * cm,
            topMargin=1.5 * cm,
            bottomMargin=1.5 * cm,
        )

        elements = []
        styles = getSampleStyleSheet()

        title_style = ParagraphStyle(
            'TitreBulletin',
            parent=styles['Heading1'],
            fontSize=20,
            textColor=colors.HexColor('#2C3E50'),
            alignment=1,
            spaceAfter=20
        )

        label_style = ParagraphStyle(
            'Label',
            parent=styles['Normal'],
            fontSize=10,
            textColor=colors.HexColor('#34495E'),
        )

        value_style = ParagraphStyle(
            'Value',
            parent=styles['Normal'],
            fontSize=10,
            textColor=colors.black,
        )

        # En-tête avec logo (BDD uniquement) et informations entreprise
        header_cols = []
        if logo_filigrane_data:
            try:
                logo_img = PILImage.open(io.BytesIO(logo_filigrane_data))
                logo_img.thumbnail((200, 200), PILImage.Resampling.LANCZOS)
                header_logo = Image(ImageReader(logo_img), width=3 * cm, height=3 * cm)
            except Exception:
                header_logo = Paragraph(" ", styles['Normal'])
        else:
            header_logo = Paragraph(" ", styles['Normal'])

        entreprise_info = Paragraph(
            "Atelier de Couture<br/><b>Bulletin de paie</b>",
            ParagraphStyle(
                'Ent',
                parent=styles['Normal'],
                fontSize=11,
                textColor=colors.HexColor('#2C3E50'),
                leading=13,
            )
        )

        header_table = Table(
            [[header_logo, entreprise_info]],
            colWidths=[4 * cm, 18 * cm]
        )
        header_table.setStyle(TableStyle([
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ]))

        elements.append(header_table)
        elements.append(Spacer(1, 0.3 * cm))

        # Titre principal
        elements.append(Paragraph(
            f"BULLETIN DE PAIE - {periode.strftime('%B %Y')}",
            title_style
        ))

        # Informations salarié / bulletin
        date_paiement_str = date_paiement.strftime('%d/%m/%Y')
        table_info = Table(
            [
                [Paragraph("<b>Employé :</b>", label_style), Paragraph(employe_nom, value_style),
                 Paragraph("<b>Référence :</b>", label_style), Paragraph(str(charge_id), value_style)],
                [Paragraph("<b>Période :</b>", label_style), Paragraph(periode.strftime('%B %Y'), value_style),
                 Paragraph("<b>Date de paiement :</b>", label_style), Paragraph(date_paiement_str, value_style)],
                [Paragraph("<b>Mode de paiement :</b>", label_style), Paragraph(mode_paiement, value_style),
                 "", ""],
            ],
            colWidths=[4 * cm, 8 * cm, 4 * cm, 8 * cm]
        )
        table_info.setStyle(TableStyle([
            ('GRID', (0, 0), (-1, -1), 0.3, colors.grey),
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#ECF0F1')),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('TOPPADDING', (0, 0), (-1, -1), 4),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ]))
        elements.append(table_info)
        elements.append(Spacer(1, 0.4 * cm))

        # Récapitulatif de paie simple (brut = net)
        elements.append(Paragraph("Récapitulatif de paie", label_style))

        montant_str = f"{montant:,.0f} FCFA"
        paie_table = Table(
            [
                ["Rubrique", "Base", "Retenues", "Net à payer"],
                ["Salaire mensuel", montant_str, "0 FCFA", montant_str],
            ],
            colWidths=[8 * cm, 6 * cm, 6 * cm, 6 * cm]
        )
        paie_table.setStyle(TableStyle([
            ('GRID', (0, 0), (-1, -1), 0.4, colors.grey),
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#3498DB')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 10),
            ('FONTSIZE', (0, 1), (-1, -1), 10),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('TOPPADDING', (0, 0), (-1, -1), 4),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ]))
        elements.append(paie_table)
        elements.append(Spacer(1, 0.4 * cm))

        # Zone de signature
        sign_table = Table(
            [
                ["Signature de l'employeur", "Signature de l'employé"]
            ],
            colWidths=[10 * cm, 10 * cm]
        )
        sign_table.setStyle(TableStyle([
            ('TOPPADDING', (0, 0), (-1, -1), 20),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 20),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ]))
        elements.append(sign_table)
        elements.append(Spacer(1, 0.3 * cm))

        # QR code avec nom de l'employé et période payée
        try:
            qr_data = {
                "employe": employe_nom,
                "periode": periode.strftime('%Y-%m'),
                "montant": montant,
                "mode_paiement": mode_paiement,
                "date_paiement": date_paiement_str,
                "charge_id": charge_id,
            }
            qr = qrcode.QRCode(
                version=1,
                error_correction=qrcode.constants.ERROR_CORRECT_L,
                box_size=8,
                border=2,
            )
            qr.add_data(qr_data)
            qr.make(fit=True)
            qr_img = qr.make_image(fill_color="black", back_color="white")

            qr_buffer = io.BytesIO()
            qr_img.save(qr_buffer, format='PNG')
            qr_buffer.seek(0)

            qr_table = Table(
                [[Image(qr_buffer, width=3 * cm, height=3 * cm)]],
                colWidths=[20 * cm]
            )
            qr_table.setStyle(TableStyle([
                ('ALIGN', (0, 0), (-1, -1), 'RIGHT'),
            ]))
            elements.append(qr_table)
        except Exception as e:
            print(f"Erreur QR code bulletin salaire: {e}")

        def dessiner_footer(canvas_obj, doc_obj):
            if not footer_lines:
                return
            try:
                canvas_obj.saveState()
                font_name = "Helvetica"
                font_size = 8
                canvas_obj.setFont(font_name, font_size)
                page_width, _ = doc_obj.pagesize
                base_y = 1.2 * cm
                for idx, line in enumerate(footer_lines):
                    text = str(line)
                    text_width = canvas_obj.stringWidth(text, font_name, font_size)
                    x = (page_width - text_width) / 2
                    y = base_y + idx * 0.35 * cm
                    canvas_obj.drawString(x, y, text)
                canvas_obj.restoreState()
            except Exception as e:
                print(f"Erreur pied de page bulletin salaire: {e}")

        # Générer le PDF
        def _on_page(canvas_obj, doc_obj):
            dessiner_filigrane(canvas_obj, doc_obj)
            dessiner_footer(canvas_obj, doc_obj)

        doc.build(
            elements,
            onFirstPage=_on_page,
            onLaterPages=_on_page
        )

        with open(filepath, "rb") as f:
            content = f.read()

        try:
            os.remove(filepath)
        except Exception:
            pass

        return {"filename": filename, "content": content}
    except Exception as e:
        print(f"Erreur génération bulletin salaire: {e}")
        return None


def _formulaire_salaire(charges_model, couturier_id, salon_id_user: Optional[str] = None):
    """Formulaire spécifique pour les salaires"""
    st.markdown("#### 💰 Paiement de Salaire")
    st.info("Enregistrez le paiement du salaire d'un employé")
    
    # Calculer la prochaine référence (N+1) basée sur toutes les charges
    ref_suivante = calculer_prochaine_reference(charges_model, couturier_id, salon_id=salon_id_user)
    
    with st.form("form_salaire", clear_on_submit=True):
        col1, col2 = st.columns(2)
        
        with col1:
            # Récupérer la liste des employés (couturiers)
            from models.database import CouturierModel
            couturier_model = CouturierModel(charges_model.db)
            employes = couturier_model.lister_tous_couturiers(salon_id=salon_id_user)
            
            if employes:
                employe_options = {f"{e['nom']} {e['prenom']}": e['id'] for e in employes}
                employe_selectionne = st.selectbox(
                    "Sélectionner l'employé *",
                    options=list(employe_options.keys()),
                    help="Choisissez l'employé à payer"
                )
                employe_id = employe_options[employe_selectionne]
            else:
                st.warning("⚠️ Aucun employé enregistré dans le système")
                employe_id = None
            
            montant = st.number_input(
                "Montant du salaire (FCFA) *",
                min_value=0.0,
                step=1000.0,
                format="%.2f",
                help="Montant du salaire à verser"
            )
            
            periode = st.date_input(
                "Période concernée (mois payé) *",
                value=datetime.now().date().replace(day=1),
                help="Mois pour lequel le salaire est payé"
            )
        
        with col2:
            date_paiement = st.date_input(
                "Date de paiement *",
                value=datetime.now().date(),
                help="Date du versement du salaire"
            )
            
            mode_paiement = st.selectbox(
                "Mode de paiement",
                options=["Espèces", "Virement bancaire", "Mobile Money", "Chèque"],
                help="Comment le salaire a été versé"
            )
            
            reference = st.text_input(
                "Référence de paiement *",
                value=str(ref_suivante),
                help="Référence de paiement (générée automatiquement N+1, modifiable)"
            )
        
        submit = st.form_submit_button("💾 Enregistrer le salaire", type="primary")
        
        if submit:
            if not employe_id:
                st.error("❌ Veuillez sélectionner un employé")
            elif montant <= 0:
                st.error("❌ Le montant doit être supérieur à 0")
            else:
                periode_str = periode.strftime('%m/%Y')
                description = f"Salaire - Période: {periode_str} - Mode: {mode_paiement}"
                if reference:
                    description += f" | Réf: {reference}"
                
                # Enregistrer la charge avec la référence
                charge_id = charges_model.ajouter_charge(
                    couturier_id=couturier_id,
                    type_charge="Salaire",
                    categorie="salaire",
                    montant=montant,
                    date_charge=date_paiement.strftime('%Y-%m-%d'),
                    description=description,
                    employe_id=employe_id,
                    reference=reference  # Enregistrer dans la colonne reference
                )
                
                if charge_id:
                    st.success(f"✅ Salaire de {montant:,.0f} FCFA enregistré pour {employe_selectionne} !")
                    
                    # Générer et stocker le bulletin de paie PDF dans la session
                    bulletin = _generer_pdf_bulletin_salaire(
                        employe_nom=employe_selectionne,
                        montant=montant,
                        periode=periode,
                        date_paiement=date_paiement,
                        mode_paiement=mode_paiement,
                        charge_id=charge_id
                    )
                    
                    if bulletin:
                        st.session_state["dernier_bulletin_salaire"] = bulletin
                    st.balloons()
                else:
                    st.error("❌ Erreur lors de l'enregistrement")

    # Bouton de téléchargement du bulletin en dehors du formulaire (obligatoire avec Streamlit)
    bulletin_data = st.session_state.get("dernier_bulletin_salaire")
    if bulletin_data:
        st.markdown("#### 📄 Bulletin de paie généré")
        st.download_button(
            label="📄 Télécharger le bulletin de paie (PDF)",
            data=bulletin_data["content"],
            file_name=bulletin_data["filename"],
            mime="application/pdf",
            use_container_width=True,
        )


def _formulaire_ponctuelle(charges_model, couturier_id, salon_id_user: Optional[str] = None):
    
    """Formulaire spécifique pour les charges ponctuelles"""
    st.markdown("#### ⏱️ Charge Ponctuelle")
    st.info("Enregistrez une dépense occasionnelle ou ponctuelle")
    
    # Calculer la prochaine référence (N+1) basée sur toutes les charges
    ref_suivante = calculer_prochaine_reference(charges_model, couturier_id, salon_id=salon_id_user)
    
    with st.form("form_ponctuelle", clear_on_submit=True):
        col1, col2 = st.columns(2)
        FOURNISSEUR_DU_SERVICE_PONCTUEL = [
        "Aucun",
        "BAILLEUR",
        "ENEO",
        "CDE",
        "Orange",
        "MTN",
        "Autre",
    ]
        with col1:
            categorie = st.selectbox(
                "Catégorie de dépense *",
                options=["maintenance", "transport", "materiel", "communication", "autre"],
                format_func=lambda x: CATEGORIES_CHARGES.get(x, x),
                help="Type de dépense ponctuelle"
            )
            
            montant = st.number_input(
                "Montant (FCFA) *",
                min_value=0.0,
                step=100.0,
                format="%.2f",
                help="Montant de la dépense"
            )
            
            description = st.text_area(
                "Description détaillée *",
                placeholder="Décrivez la dépense (ex: Réparation machine à coudre, Achat de fil...)",
                height=100,
                help="Soyez précis pour faciliter le suivi"
            )
        
        with col2:
            date_charge = st.date_input(
                "Date de la dépense *",
                value=datetime.now().date(),
                help="Quand la dépense a été effectuée"
            )

            fournisseur = st.selectbox(
                "Fournisseur Du Service",
                
                options=FOURNISSEUR_DU_SERVICE_PONCTUEL,
                help="À qui la charge est payée"
            )
            
            reference = st.text_input(
                "Référence de paiement *",
                value=str(ref_suivante),
                help="Référence de paiement (générée automatiquement N+1, modifiable)"
            )
            
           
        
        # Upload de fichier justificatif
        st.markdown("---")
        st.markdown("📎 **Justificatif (optionnel)**")
        fichier_uploaded = st.file_uploader(
            "Joindre un document",
            type=["pdf", "jpg", "jpeg", "png", "doc", "docx"],
            help="Facture, reçu, bon de commande, etc. (PDF, Image, Word)",
            key="file_ponctuelle"
        )
        
        submit = st.form_submit_button("💾 Enregistrer la charge", type="primary")
        
        if submit:
            if montant <= 0:
                st.error("❌ Le montant doit être supérieur à 0")
            elif not description or len(description.strip()) < 5:
                st.error("❌ La description doit comporter au moins 5 caractères")
            else:
                desc_complete = description
                if fournisseur and fournisseur != "Aucun":
                    desc_complete = f"{description} | Fournisseur: {fournisseur}"
                if reference:
                    desc_complete += f" | Réf: {reference}"
                
                # Enregistrer la charge avec la référence
                charge_id = charges_model.ajouter_charge(
                    couturier_id=couturier_id,
                    type_charge="Ponctuelle",
                    categorie=categorie,
                    montant=montant,
                    date_charge=date_charge.strftime('%Y-%m-%d'),
                    description=desc_complete,
                    reference=reference  # Enregistrer dans la colonne reference
                )
                
                if charge_id:
                    # Si un fichier a été uploadé, le sauvegarder en BDD
                    if fichier_uploaded:
                        fichier_info = sauvegarder_fichier_charge(fichier_uploaded, charge_id)
                        if fichier_info:
                            charges_model.ajouter_document(
                                charge_id=charge_id,
                                file_name=fichier_info['file_name'],
                                file_data=fichier_info['file_data'],
                                mime_type=fichier_info['mime_type'],
                                file_size=fichier_info['file_size']
                            )
                    
                    st.success(f"✅ Charge ponctuelle de {montant:,.0f} FCFA enregistrée !")
                    if fichier_uploaded:
                        st.info(f"📎 Document joint: {fichier_uploaded.name}")
                    st.balloons()
                    st.rerun()
                else:
                    st.error("❌ Erreur lors de l'enregistrement")


def _formulaire_fixe(charges_model, couturier_id, salon_id_user: Optional[str] = None):
    """Formulaire spécifique pour les charges fixes"""
    st.markdown("#### 📌 Charge Fixe")
    st.info("Enregistrez une dépense récurrente (loyer, électricité, abonnements...)")

    # Calculer la prochaine référence (N+1) basée sur toutes les charges
    ref_suivante = calculer_prochaine_reference(charges_model, couturier_id, salon_id=salon_id_user)

    BENEFICIAIRES_FIXES = [
        "Aucun",
        "BAILLEUR",
        "ENEO",
        "CDE",
        "Orange",
        "MTN",
        "Autre",
    ]

    with st.form("form_fixe", clear_on_submit=True):
        col1, col2 = st.columns(2)
        
        with col1:
            categorie = st.selectbox(
                "Type de charge fixe *",
                options=["loyer", "electricite", "communication", "autre"],
                format_func=lambda x: CATEGORIES_CHARGES.get(x, x),
                help="Nature de la charge fixe"
            )
            
            montant = st.number_input(
                "Montant (FCFA) *",
                min_value=0.0,
                step=100.0,
                format="%.2f",
                help="Montant de la charge"
            )
            
            periodicite = st.selectbox(
                "Périodicité",
                options=["Mensuelle", "Trimestrielle", "Annuelle", "Autre"],
                help="Fréquence de paiement"
            )

            # Période concernée en date (par ex : 1er jour du mois)
            periode_concernee = st.date_input(
                "Période concernée *",
                value=datetime.now().date().replace(day=1),
                help="Période couverte par cette charge"
            )
        
        with col2:
            date_charge = st.date_input(
                "Date de paiement *",
                value=datetime.now().date(),
                help="Date du règlement"
            )
            
            beneficiaire = st.selectbox(
                "Bénéficiaire / Créancier",
                options=BENEFICIAIRES_FIXES,
                help="À qui la charge est payée"
            )
            
            
            reference = st.text_input(
                "Référence de paiement *",
                value=str(ref_suivante),
                help="Référence de paiement (générée automatiquement N+1, modifiable)"
            )
        
        # Upload de fichier justificatif
        st.markdown("---")
        st.markdown("📎 **Justificatif (optionnel)**")
        fichier_uploaded = st.file_uploader(
            "Joindre un document",
            type=["pdf", "jpg", "jpeg", "png", "doc", "docx"],
            help="Facture, quittance, contrat, etc. (PDF, Image, Word)",
            key="file_fixe"
        )
        
        submit = st.form_submit_button("💾 Enregistrer la charge", type="primary")
        
        if submit:
            if montant <= 0:
                st.error("❌ Le montant doit être supérieur à 0")
            else:
                # Construire une description structurée
                periode_str = periode_concernee.strftime('%m/%Y')
                desc_complete = f"Charge {periodicite.lower()} - Période: {periode_str}"
                if beneficiaire and beneficiaire != "Aucun":
                    desc_complete += f" | Bénéficiaire: {beneficiaire}"
                
                if reference:
                    desc_complete += f" | Réf: {reference}"
                
                # Enregistrer la charge avec la référence
                charge_id = charges_model.ajouter_charge(
                    couturier_id=couturier_id,
                    type_charge="Fixe",
                    categorie=categorie,
                    montant=montant,
                    date_charge=date_charge.strftime('%Y-%m-%d'),
                    description=desc_complete,
                    reference=reference  # Enregistrer dans la colonne reference
                )
                
                if charge_id:
                    # Si un fichier a été uploadé, le sauvegarder en BDD
                    if fichier_uploaded:
                        fichier_info = sauvegarder_fichier_charge(fichier_uploaded, charge_id)
                        if fichier_info:
                            charges_model.ajouter_document(
                                charge_id=charge_id,
                                file_name=fichier_info['file_name'],
                                file_data=fichier_info['file_data'],
                                mime_type=fichier_info['mime_type'],
                                file_size=fichier_info['file_size']
                            )
                    
                    st.success(f"✅ Charge fixe de {montant:,.0f} FCFA enregistrée !")
                    if fichier_uploaded:
                        st.info(f"📎 Document joint: {fichier_uploaded.name}")
                    st.balloons()
                    st.rerun()
                else:
                    st.error("❌ Erreur lors de l'enregistrement")


def _formulaire_commande(charges_model, commande_model, couturier_id, salon_id_user: Optional[str] = None):
    """Formulaire spécifique pour les charges liées à une commande"""
    st.markdown("#### 🧾 Charge liée à une Commande")
    st.info("Enregistrez une dépense directement associée à une commande client")
    
    # Calculer la prochaine référence (N+1) basée sur toutes les charges
    ref_suivante = calculer_prochaine_reference(charges_model, couturier_id, salon_id=salon_id_user)
    
    LIEE_AU_COMMANDES = [
        "Aucun",
        "BAILLEUR",
        "ENEO",
        "CDE",
        "Orange",
        "MTN",
        "Autre",
    ]
    
    with st.form("form_commande", clear_on_submit=True):
        # Récupérer la liste des commandes : pour un non-admin, filtrer uniquement par couturier_id
        # (comme dans la page "Mes commandes") ; pour un admin, filtrer par salon_id
        if couturier_id is not None:
            # Non-admin : filtrer uniquement par couturier_id (comme dans "Mes commandes")
            commandes = commande_model.lister_commandes(
                couturier_id=couturier_id,
                tous_les_couturiers=False,
                salon_id=None
            )
        else:
            # Admin : filtrer par salon_id
            commandes = commande_model.lister_commandes(
                couturier_id=None,
                tous_les_couturiers=False,
                salon_id=salon_id_user
            )
        
        if not commandes:
            st.warning("⚠️ Aucune commande disponible. Créez d'abord une commande dans la section 'Nouvelle commande'.")
            commande_id = None
        else:
            # Afficher les commandes avec plus de détails
            options_commandes = {}
            for c in commandes:
                label = f"CMD-{c['id']} | {c.get('modele', 'N/A')} | Client: {c.get('client_nom', '')} {c.get('client_prenom', '')} | {c.get('prix_total', 0):,.0f} FCFA"
                options_commandes[label] = c['id']
            
            commande_selectionnee = st.selectbox(
                "Sélectionner la commande *",
                options=list(options_commandes.keys()),
                help="Choisissez la commande concernée par cette dépense"
            )
            commande_id = options_commandes[commande_selectionnee]
        
        col1, col2 = st.columns(2)
        
        with col1:
            categorie = st.selectbox(
                "Type de dépense *",
                options=["tissu", "materiel", "transport", "autre"],
                format_func=lambda x: CATEGORIES_CHARGES.get(x, x),
                help="Nature de la dépense pour cette commande"
            )
            
            montant = st.number_input(
                "Montant (FCFA) *",
                min_value=0.0,
                step=100.0,
                format="%.2f",
                help="Coût de la dépense"
            )
        
        with col2:
            date_charge = st.date_input(
                "Date de la dépense *",
                value=datetime.now().date(),
                help="Quand la dépense a été effectuée"
            )
            
            fournisseur = st.selectbox(
                "Bénéficiaire / Créancier",
                options=LIEE_AU_COMMANDES,
                help="À qui la charge est payée"
            )
        
        description = st.text_area(
            "Description détaillée *",
            placeholder="Décrivez la dépense liée à cette commande (ex: Achat de tissu pour robe, Transport...)",
            height=100,
            help="Soyez précis pour faciliter le suivi"
        )
        
        reference = st.text_input(
            "Référence de paiement *",
            value=str(ref_suivante),
            help="Référence de paiement (générée automatiquement N+1, modifiable)"
        )
        
      
        
        # Upload de fichier justificatif
        st.markdown("---")
        st.markdown("📎 **Justificatif (optionnel)**")
        fichier_uploaded = st.file_uploader(
            "Joindre un document",
            type=["pdf", "jpg", "jpeg", "png", "doc", "docx"],
            help="Facture d'achat, bon de livraison, etc. (PDF, Image, Word)",
            key="file_commande"
        )
        
        submit = st.form_submit_button("💾 Enregistrer la charge", type="primary")
        
        if submit:
            if not commande_id:
                st.error("❌ Aucune commande sélectionnée")
            elif montant <= 0:
                st.error("❌ Le montant doit être supérieur à 0")
            elif not description or len(description.strip()) < 5:
                st.error("❌ Veuillez fournir une description d'au moins 5 caractères")
            else:
                desc_complete = description
                if fournisseur and fournisseur != "Aucun":
                    desc_complete += f" | Fournisseur: {fournisseur}"
                if reference:
                    desc_complete += f" | Réf: {reference}"
                
                charge_id = charges_model.ajouter_charge(
                    couturier_id=couturier_id,
                    type_charge="Commande",
                    categorie=categorie,
                    montant=montant,
                    date_charge=date_charge.strftime('%Y-%m-%d'),
                    description=desc_complete,
                    commande_id=commande_id,
                    reference=reference  # Enregistrer dans la colonne reference
                )
                
                if charge_id:
                    # Si un fichier a été uploadé, le sauvegarder en BDD
                    if fichier_uploaded:
                        fichier_info = sauvegarder_fichier_charge(fichier_uploaded, charge_id)
                        if fichier_info:
                            charges_model.ajouter_document(
                                charge_id=charge_id,
                                file_name=fichier_info['file_name'],
                                file_data=fichier_info['file_data'],
                                mime_type=fichier_info['mime_type'],
                                file_size=fichier_info['file_size']
                            )
                    
                    st.success(f"✅ Charge de {montant:,.0f} FCFA enregistrée pour la commande CMD-{commande_id} !")
                    if fichier_uploaded:
                        st.info(f"📎 Document joint: {fichier_uploaded.name}")
                    st.balloons()
                    st.rerun()
                else:
                    st.error("❌ Erreur lors de l'enregistrement")


def _liste_charges(charges_model, couturier_id, is_admin=False, salon_id_user: Optional[str] = None):
    st.markdown("### 📊 Analyse des charges")
    if is_admin:
        st.markdown("Visualisez toutes les charges de l'entreprise et leurs évolutions.")
    else:
        st.markdown("Visualisez vos charges et leurs évolutions sur la période sélectionnée.")
    st.markdown("---")

    # -------------------------------------------------------------------------
    # FILTRES PRINCIPAUX
    # -------------------------------------------------------------------------
    col1, col2 = st.columns(2)
    with col1:
        d_debut = st.date_input("Début", value=datetime.now().date()-timedelta(30), key="ld")
    with col2:
        d_fin = st.date_input("Fin", value=datetime.now().date(), key="lf")
    
    # Ligne pour Type et bouton Actualiser
    col_type, col_btn = st.columns([3, 1])
    with col_type:
        t_filter = st.multiselect("Type", list(TYPES_CHARGES.keys()), 
                                  default=list(TYPES_CHARGES.keys()), key="lt",
                                  help="Sélectionnez les types de charges à inclure dans l'analyse")
    with col_btn:
        st.write("")  # Espacement vertical pour aligner avec le multiselect
        st.write("")  # Espacement vertical
        btn_actualiser = st.button("🔄 Actualiser", 
                                   type="primary", 
                                   use_container_width=True,
                                   key="btn_actualiser_analyse",
                                   help="Recalculer les totaux et statistiques avec les filtres sélectionnés")
    
    # Vérifier qu'au moins un type est sélectionné
    if not t_filter:
        st.warning("⚠️ Veuillez sélectionner au moins un type de charge")
        return
    
    # Si le bouton est cliqué, afficher un message de confirmation
    if btn_actualiser:
        st.success("🔄 Recalcul en cours...")
    
    # Filtrer par salon_id ET couturier_id (comme dans la page ajouter et analyse)
    charges = charges_model.lister_charges(
        couturier_id,
        1000,
        tous_les_couturiers=False,
        salon_id=salon_id_user  # Toujours passer salon_id pour filtrer correctement
    )
    if not charges:
        st.info("💭 Aucune charge")
        return
    
    df = pd.DataFrame(charges)
    df['date_charge'] = pd.to_datetime(df['date_charge'])
    
    # Filtrer par dates et par types sélectionnés
    # S'assurer que t_filter est une liste non vide (vérifié ci-dessus)
    # Convertir t_filter en liste si ce n'est pas déjà le cas
    if not isinstance(t_filter, list):
        t_filter = list(t_filter) if t_filter else []
    
    mask = (
        (df['date_charge'].dt.date >= d_debut) & 
        (df['date_charge'].dt.date <= d_fin) & 
        (df['type'].isin(t_filter))
    )
    df_f = df[mask].copy()
    
    # Afficher un indicateur des types sélectionnés (pour debug/confirmation)
    types_labels = [TYPES_CHARGES.get(t, t) for t in t_filter]
    st.info(f"📋 Types sélectionnés : {', '.join(types_labels)}")
    
    if df_f.empty:
        st.warning("⚠️ Aucune charge ne correspond aux critères sélectionnés")
        # Afficher quand même les métriques à 0 pour montrer que le calcul fonctionne
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("💰 Total", "0 FCFA")
        c2.metric("📝 Nombre", "0")
        c3.metric("📈 Moyenne", "0 FCFA")
        c4.metric("📅 Moy/jour", "0 FCFA")
        return
    
    # -------------------------------------------------------------------------
    # INDICATEURS CLÉS (recalculés automatiquement à chaque changement de filtre)
    # -------------------------------------------------------------------------
    # Calculer les statistiques à partir du DataFrame filtré
    total = float(df_f['montant'].sum()) if not df_f.empty else 0.0
    nb = len(df_f)
    moy = float(df_f['montant'].mean()) if not df_f.empty and nb > 0 else 0.0
    nb_jours = max(1, (d_fin - d_debut).days + 1)  # Éviter division par zéro
    moy_j = total / nb_jours if nb_jours > 0 else 0.0
    
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("💰 Total", f"{total:,.0f} FCFA")
    c2.metric("📝 Nombre", f"{nb}")
    c3.metric("📈 Moyenne", f"{moy:,.0f} FCFA")
    c4.metric("📅 Moy/jour", f"{moy_j:,.0f} FCFA")
    
    st.markdown("---")
    # Préparer le DataFrame de détails (non affiché mais utilisé pour export / PDF)
    df_details = df_f[['date_charge', 'type', 'categorie', 'description', 'montant']].copy()

    # -------------------------------------------------------------------------
    # ANALYSES GRAPHIQUES (ancien onglet Analyses)
    # -------------------------------------------------------------------------
    st.markdown("---")
    st.markdown("### 📊 Analyses graphiques")

    da = df_f.copy()
    
    # Pie chart - répartition par type
    df_type = da.groupby('type')['montant'].sum().reset_index()
    fig_pie = px.pie(
        df_type,
        values='montant',
        names='type',
        title='Répartition des charges par type',
        hole=0.4
    )
    st.plotly_chart(fig_pie, use_container_width=True)
    
    # -------------------------------------------------------------------------
    # ÉVOLUTION MENSUELLE DES CHARGES (courbes + récapitulatif)
    # -------------------------------------------------------------------------
    st.markdown("#### 📈 Évolution mensuelle des charges")
    
    # Créer une colonne mois-année pour le groupement
    da['mois_annee'] = da['date_charge'].dt.to_period('M')
    # Créer un label lisible pour chaque mois (format: "Janvier 2024")
    da['mois_label'] = da['date_charge'].dt.strftime('%B %Y')
    # Créer aussi une date de début de mois pour l'ordre chronologique
    da['mois_date'] = da['date_charge'].dt.to_period('M').dt.to_timestamp()
    
    # Grouper par mois et par type de charge
    df_evolution = da.groupby(['mois_date', 'mois_annee', 'mois_label', 'type'])['montant'].sum().reset_index()
    
    # Créer une liste complète de tous les mois entre d_debut et d_fin
    date_debut_mois = pd.to_datetime(d_debut).to_period('M').to_timestamp()
    date_fin_mois = pd.to_datetime(d_fin).to_period('M').to_timestamp()
    
    # Générer tous les mois de la période
    tous_les_mois = pd.period_range(start=date_debut_mois, end=date_fin_mois, freq='M')
    tous_les_mois_dates = [p.to_timestamp() for p in tous_les_mois]
    tous_les_mois_labels = [p.strftime('%B %Y') for p in tous_les_mois]
    
    # Créer le graphique avec une ligne par type de charge
    fig_line = go.Figure()
    
    # Couleurs pour chaque type
    couleurs = {
        'Fixe': '#3498DB',
        'Ponctuelle': '#F39C12',
        'Commande': '#2ECC71',
        'Salaire': '#F39C12'
    }
    
    # Obtenir tous les types de charges possibles
    tous_les_types = list(TYPES_CHARGES.keys())
    
    # Ajouter une trace (ligne) pour chaque type de charge
    for type_charge in tous_les_types:
        # Filtrer les données pour ce type
        df_type_evo = df_evolution[df_evolution['type'] == type_charge].copy()
        
        # Créer un DataFrame complet avec tous les mois (même ceux à 0)
        df_complet = pd.DataFrame({
            'mois_date': tous_les_mois_dates,
            'mois_label': tous_les_mois_labels
        })
        
        # Fusionner avec les données réelles
        df_complet = df_complet.merge(
            df_type_evo[['mois_date', 'montant']],
            on='mois_date',
            how='left'
        )
        
        # Remplir les valeurs manquantes par 0
        df_complet['montant'] = df_complet['montant'].fillna(0)
        
        # Trier par date
        df_complet = df_complet.sort_values('mois_date')
        
        couleur = couleurs.get(type_charge, '#95A5A6')
        label = TYPES_CHARGES.get(type_charge, type_charge)
        
        fig_line.add_trace(go.Scatter(
            x=df_complet['mois_label'],
            y=df_complet['montant'],
            mode='lines+markers',
            name=label,
            line=dict(color=couleur, width=3),
            marker=dict(size=8, color=couleur),
            hovertemplate=f'<b>{label}</b><br>Mois: %{{x}}<br>Montant: %{{y:,.0f}} FCFA<extra></extra>'
        ))
    
    # Mise en forme du graphique
    fig_line.update_layout(
        title='Évolution mensuelle des charges par type',
        xaxis_title='Mois',
        yaxis_title='Montant (FCFA)',
        hovermode='x unified',
        plot_bgcolor='rgba(0,0,0,0)',
        paper_bgcolor='rgba(0,0,0,0)',
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1
        ),
        height=500
    )
    
    st.plotly_chart(fig_line, use_container_width=True)
    
    # -------------------------------------------------------------------------
    # RÉCAPITULATIF MENSUEL
    # -------------------------------------------------------------------------
    st.markdown("#### 📊 Récapitulatif mensuel")
    
    # Créer un DataFrame avec tous les mois de la période
    df_recap_complet = pd.DataFrame({
        'mois_date': tous_les_mois_dates,
        'mois_label': tous_les_mois_labels
    })
    
    # Créer le pivot avec mois_date comme index
    df_recap = df_evolution.pivot_table(
        index='mois_date',
        columns='type',
        values='montant',
        aggfunc='sum',
        fill_value=0
    )
    
    # Fusionner avec la liste complète des mois pour inclure ceux à 0
    df_recap = df_recap_complet.set_index('mois_date').join(df_recap, how='left').fillna(0)
    
    # Ne garder que les types de charges SÉLECTIONNÉS dans le filtre (t_filter)
    # Cela garantit que le total ne compte que les types sélectionnés
    types_a_afficher = [t for t in t_filter if t in df_recap.columns]
    
    # S'assurer que tous les types sélectionnés sont présents (même s'ils n'ont pas de données)
    for type_charge in types_a_afficher:
        if type_charge not in df_recap.columns:
            df_recap[type_charge] = 0
    
    # Réindexer avec mois_label pour l'affichage
    df_recap['mois_label'] = df_recap_complet['mois_label'].values
    df_recap = df_recap.set_index('mois_label')
    
    # Réordonner les colonnes pour avoir uniquement les types sélectionnés, puis le Total
    colonnes_ordre = [col for col in types_a_afficher if col in df_recap.columns]
    df_recap = df_recap[colonnes_ordre]
    
    # Calculer le total UNIQUEMENT sur les colonnes des types sélectionnés
    df_recap['Total'] = df_recap[colonnes_ordre].sum(axis=1)
    
    # Renommer les colonnes avec les labels
    df_recap.columns = [TYPES_CHARGES.get(col, col) if col != 'Total' else 'Total' for col in df_recap.columns]
    
    # Conserver une version numérique pour export / PDF
    df_recap_export = df_recap.copy()
    
    # Formater les valeurs pour l'affichage
    df_recap_display = df_recap_export.copy()
    for col in df_recap_display.columns:
        df_recap_display[col] = df_recap_display[col].apply(lambda x: f"{x:,.0f} FCFA")
    
    st.dataframe(
        df_recap_display,
        use_container_width=True,
        height=300
    )

    # -------------------------------------------------------------------------
    # EXPORTS EXCEL & PDF
    # -------------------------------------------------------------------------
    st.markdown("---")
    st.markdown("### 📥 Export des analyses")
    
    # Export Excel avec plusieurs feuilles (Détails + Récap mensuel)
    excel_buffer = io.BytesIO()
    dd_str = d_debut.strftime("%d-%m-%Y")
    df_str = d_fin.strftime("%d-%m-%Y")
    with pd.ExcelWriter(excel_buffer, engine="openpyxl") as writer:
        # Détails des charges
        df_details_export = df_details.copy()
        df_details_export['date_charge'] = pd.to_datetime(df_details_export['date_charge']).dt.strftime('%Y-%m-%d')
        df_details_export.to_excel(writer, index=False, sheet_name="Details_charges")
        
        # Récapitulatif mensuel
        df_recap_export.to_excel(writer, sheet_name="Recapitulatif_mensuel")
    
    col_excel, col_pdf = st.columns(2)
    with col_excel:
        st.download_button(
            label="📊 Télécharger l'Excel d'analyse",
            data=excel_buffer.getvalue(),
            file_name=f"AnalyseDesCharges_Du_{dd_str}_Et_{df_str}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True,
        )
    
    # Export PDF d'analyse
    pdf_data = _generer_pdf_analyse_charges(d_debut, d_fin, df_details, df_recap_export)
    with col_pdf:
        if pdf_data:
            st.download_button(
                label="📄 Télécharger le PDF d'analyse",
                data=pdf_data["content"],
                file_name=pdf_data["filename"],
                mime="application/pdf",
                use_container_width=True,
            )

def _analyses(charges_model, couturier_id):
    """Ancienne fonction d'analyses – conservée pour compatibilité, mais non utilisée."""
    st.info("Les analyses ont été déplacées dans l'onglet '📊 Analyse'.")

def _calcul_impots(charges_model, commande_model, couturier_id, is_admin=False, salon_id_user: Optional[str] = None):
    st.markdown("### 🧮 Calcul d'impôts")
    if is_admin:
        st.info("👑 Vue administrateur : Calcul des impôts sur toutes les activités de l'entreprise")
    col1, col2 = st.columns(2)
    with col1:
        dd = st.date_input("Début", value=datetime.now().replace(day=1).date(), key="id")
    with col2:
        df = st.date_input("Fin", value=datetime.now().date(), key="if")
    
    # Si admin, récupérer les commandes du salon; sinon, uniquement celles du couturier
    commandes = commande_model.lister_commandes(
        couturier_id=None if is_admin else couturier_id,
        tous_les_couturiers=is_admin,
        salon_id=salon_id_user if is_admin else None
    )

    # Calcul du CA sur la période sélectionnée
    if commandes:
        df_cmd = pd.DataFrame(commandes)
        if 'date_creation' in df_cmd.columns:
            df_cmd['date_creation'] = pd.to_datetime(df_cmd['date_creation'])
            mask_cmd = (
                (df_cmd['date_creation'].dt.date >= dd) &
                (df_cmd['date_creation'].dt.date <= df)
            )
            df_cmd = df_cmd[mask_cmd]
        ca = df_cmd['prix_total'].sum() if 'prix_total' in df_cmd.columns else 0
    else:
        ca = 0

    ca_manuel = st.number_input("Chiffre d'affaires (FCFA)", min_value=0.0, value=float(ca), step=100000.0)
    
    dd_dt = datetime.combine(dd, datetime.min.time())
    df_dt = datetime.combine(df, datetime.max.time())
    # Filtrer par salon_id ET couturier_id (comme dans la page ajouter et analyse)
    total_charges = charges_model.total_charges(
        couturier_id,
        dd_dt,
        df_dt,
        tous_les_couturiers=False,
        salon_id=salon_id_user  # Toujours passer salon_id pour filtrer correctement
    )
    
    st.metric("💵 CA", f"{ca_manuel:,.0f} FCFA")
    st.metric("💸 Charges", f"{total_charges:,.0f} FCFA")
    
    impot = 0
    for t in TRANCHES_IMPOTS:
        if t['min'] <= ca_manuel <= t['max']:
            impot = t['impot']
            break
    
    #st.info(f"**Barème:** 0- 500.000 → 5.000 fcfa | 500.000 -1M → 75.000 fcfa | 1M -1.5M → 10.000 fcfa | 1.5M -2M → 12.500 fcfa | 2M -2.5M → 15.000 fcfa | 20M-30M→ 250.000K | 30M-50M →500K  | ")
    st.info("**Barème:** 0- 500.000 → 5.000 fcfa | 500.000 - 1M → 75.000 fcfa | 1M - 1.5M → 10.000 fcfa | 1.5M - 2M → 12.500 fcfa | 2M - 2.5M → 15.000 fcfa | 2.5M - 5M → 37.500 fcfa | 5M - 10M → 75.000 fcfa | 10M - 20M → 125.000 fcfa | 20M - 30M → 250.000K | 30M - 50M → 500K  | ")

    st.metric("🏦 Impôt à payer", f"{impot:,.0f} FCFA")
    
    benefice = ca_manuel - total_charges - impot
    st.metric("💚 Bénéfice net", f"{benefice:,.0f} FCFA",
              delta=f"{(benefice/ca_manuel*100):.1f}%" if ca_manuel > 0 else None)

    # Préparer les données de charges pour le PDF (sur la même période)
    # Filtrer par salon_id ET couturier_id (comme dans la page ajouter et analyse)
    charges_list = charges_model.lister_charges(
        couturier_id, 
        limit=10000, 
        tous_les_couturiers=False,
        salon_id=salon_id_user  # Toujours passer salon_id pour filtrer correctement
    )
    df_charges = pd.DataFrame(charges_list) if charges_list else pd.DataFrame()
    if not df_charges.empty and 'date_charge' in df_charges.columns:
        df_charges['date_charge'] = pd.to_datetime(df_charges['date_charge'])
        mask = (
            (df_charges['date_charge'].dt.date >= dd) &
            (df_charges['date_charge'].dt.date <= df)
        )
        df_charges = df_charges[mask]

    pdf_data = _generer_pdf_impots(dd, df, ca_manuel, total_charges, impot, benefice, df_charges)
    col_pdf, col_excel = st.columns(2)
    with col_pdf:
        if pdf_data:
            st.download_button(
                label="📄 Télécharger le relevé d'impôts (PDF)",
                data=pdf_data["content"],
                file_name=pdf_data["filename"],
                mime="application/pdf",
                use_container_width=True
            )

    # -------------------------------------------------------------------------
    # Export Excel au format lisible par les comptables / fisc
    # -------------------------------------------------------------------------
    # Feuille 1 : Synthèse (CA, charges, impôt, bénéfice)
    synthese_df = pd.DataFrame(
        [
            {"Libellé": "Chiffre d'affaires", "Montant_FCFA": ca_manuel},
            {"Libellé": "Total des charges", "Montant_FCFA": total_charges},
            {"Libellé": "Impôt à payer", "Montant_FCFA": impot},
            {"Libellé": "Bénéfice net", "Montant_FCFA": benefice},
        ]
    )

    # Feuille 2 : Écritures détaillées (journal type comptable)
    lignes = []

    # Ligne de produit (CA)
    if ca_manuel > 0:
        lignes.append(
            {
                "Date": dd.strftime("%Y-%m-%d"),
                "Type_ecriture": "PRODUIT",
                "Compte": "Classe 7 - Produits",
                "Libellé": f"Chiffre d'affaires période {dd.strftime('%d/%m/%Y')} - {df.strftime('%d/%m/%Y')}",
                "Débit": 0.0,
                "Crédit": float(ca_manuel),
            }
        )

    # Lignes de charges (une ligne par charge)
    if not df_charges.empty:
        for _, row in df_charges.iterrows():
            date_str = pd.to_datetime(row["date_charge"]).strftime("%Y-%m-%d")
            libelle = str(row.get("description", "")) or f"Charge {row.get('categorie', '')}"
            lignes.append(
                {
                    "Date": date_str,
                    "Type_ecriture": "CHARGE",
                    "Compte": "Classe 6 - Charges",
                    "Libellé": libelle[:120],
                    "Débit": float(row.get("montant", 0.0)),
                    "Crédit": 0.0,
                }
            )

    # Ligne d'impôt (charge fiscale)
    if impot > 0:
        lignes.append(
            {
                "Date": df.strftime("%Y-%m-%d"),
                "Type_ecriture": "IMPOT",
                "Compte": "Classe 6 - Impôts et taxes",
                "Libellé": f"Impôt sur la période {dd.strftime('%d/%m/%Y')} - {df.strftime('%d/%m/%Y')}",
                "Débit": float(impot),
                "Crédit": 0.0,
            }
        )

    ecritures_df = pd.DataFrame(lignes) if lignes else pd.DataFrame(
        columns=["Date", "Type_ecriture", "Compte", "Libellé", "Débit", "Crédit"]
    )

    excel_buffer = io.BytesIO()
    dd_str = dd.strftime("%d-%m-%Y")
    df_str = df.strftime("%d-%m-%Y")
    with pd.ExcelWriter(excel_buffer, engine="openpyxl") as writer:
        synthese_df.to_excel(writer, index=False, sheet_name="Synthese")
        ecritures_df.to_excel(writer, index=False, sheet_name="Ecritures")

    with col_excel:
        st.download_button(
            label="📊 Télécharger le fichier Excel comptable",
            data=excel_buffer.getvalue(),
            file_name=f"Releve_Impots_{dd_str}_au_{df_str}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True,
        )