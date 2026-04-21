"""
Vue de création de commande (View dans MVC)
"""
import streamlit as st
import os
from datetime import datetime, timedelta
from controllers.commande_controller import CommandeController
from controllers.pdf_controller import PDFController
from controllers.email_controller import EmailController
from config import MODELES, MESURES
from utils.image_optimizer import optimiser_image, obtenir_taille_fichier_mb
from models.salon_model import SalonModel
from utils.role_utils import obtenir_salon_id


def afficher_page_commande():
    """Affiche la page de création de commande"""
    
    # En-tête encadré standardisé
    from utils.page_header import afficher_header_page
    afficher_header_page("➕ Nouvelle Commande", "Créer une nouvelle commande pour un client")
    
    # Initialiser les contrôleurs
    db = st.session_state.db_connection
    commande_controller = CommandeController(db)
    pdf_controller = PDFController(db_connection=db)

    # Récupérer la configuration SMTP du salon courant (multi-tenant)
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
    
    # ========================================================================
    # SECTION 1: INFORMATIONS GÉNÉRALES (Prix, Catégorie, Modèle)
    # ========================================================================
    
    # Container pour les informations générales
    with st.container():
        st.markdown("### 📋 Informations générales")
        
        # Prix et paiement
        col_prix1, col_prix2, col_prix3 = st.columns(3)
        
        # Initialiser les valeurs dans session_state si elles n'existent pas
        if 'prix_total_form' not in st.session_state:
            st.session_state.prix_total_form = 0.0
        if 'avance_form' not in st.session_state:
            st.session_state.avance_form = 0.0
        
        with col_prix1:
            prix_total = st.number_input(
                "💰 Prix total (FCFA) *",
                min_value=0.0,
                value=st.session_state.prix_total_form,
                step=1000.0,
                format="%.2f",
                key="prix_total_outside"
            )
            st.session_state.prix_total_form = prix_total
        
        with col_prix2:
            # Calculer la valeur max pour l'avance
            max_avance = prix_total if prix_total > 0 else 1000000.0
            avance = st.number_input(
                "💵 Avance (FCFA) *",
                min_value=0.0,
                max_value=max_avance,
                value=st.session_state.avance_form,
                step=1000.0,
                format="%.2f",
                key="avance_outside"
            )
            st.session_state.avance_form = avance
            
            # S'assurer que l'avance ne dépasse pas le prix total
            if avance > prix_total and prix_total > 0:
                st.warning("⚠️ L'avance sera limitée au prix total")
                avance = prix_total
                st.session_state.avance_form = avance
        
        with col_prix3:
            # Calculer le reste automatiquement (mise à jour en temps réel)
            reste = max(0.0, prix_total - avance)
            st.session_state.reste_form = reste
            
            # Afficher le reste de manière claire et visible
            st.metric(
                "💳 Reste à payer",
                f"{reste:,.0f} FCFA",
                delta=f"{(avance/prix_total*100):.0f}% payé" if prix_total > 0 else None
            )
        
        st.markdown("<br>", unsafe_allow_html=True)
        
        # Catégorie, Sexe et Modèle sur une seule ligne
        col_cat, col_sexe, col_mod = st.columns([1, 1, 2])
        
        with col_cat:
            categorie = st.selectbox(
                "👔 Catégorie *",
                options=["adulte", "enfant"],
                format_func=lambda x: "👨 Adulte" if x == "adulte" else "👶 Enfant",
                key="select_categorie_commande"
            )
        
        with col_sexe:
            if categorie == "adulte":
                sexe = st.selectbox(
                    "👤 Sexe *",
                    options=["homme", "femme"],
                    format_func=lambda x: "👨 Homme" if x == "homme" else "👩 Femme",
                    key="select_sexe_commande"
                )
            else:
                sexe = st.selectbox(
                    "👤 Sexe *",
                    options=["garcon", "fille"],
                    format_func=lambda x: "👦 Garçon" if x == "garcon" else "👧 Fille",
                    key="select_sexe_commande"
                )
        
        with col_mod:
            # Stocker le modèle dans session_state pour qu'il persiste
            if 'modele_selectionne' not in st.session_state:
                st.session_state.modele_selectionne = MODELES[categorie][sexe][0] if MODELES[categorie][sexe] else ""
            
            # Réinitialiser le modèle si la catégorie ou le sexe change
            if 'categorie_precedente' not in st.session_state:
                st.session_state.categorie_precedente = categorie
                st.session_state.sexe_precedent = sexe
            elif st.session_state.categorie_precedente != categorie or st.session_state.sexe_precedent != sexe:
                st.session_state.categorie_precedente = categorie
                st.session_state.sexe_precedent = sexe
                st.session_state.modele_selectionne = MODELES[categorie][sexe][0] if MODELES[categorie][sexe] else ""
            
            modele = st.selectbox(
                "🎨 Modèle *",
                options=MODELES[categorie][sexe],
                key="select_modele_commande",
                index=MODELES[categorie][sexe].index(st.session_state.modele_selectionne) if st.session_state.modele_selectionne in MODELES[categorie][sexe] else 0
            )
            
            # Mettre à jour session_state si le modèle change
            if st.session_state.modele_selectionne != modele:
                st.session_state.modele_selectionne = modele
                st.rerun()
    
    st.markdown("<br>", unsafe_allow_html=True)
    
    # ========================================================================
    # FORMULAIRE PRINCIPAL
    # ========================================================================
    
    with st.form("nouvelle_commande_form"):
        # Section 1: Informations client
        with st.expander("👤 Informations du client", expanded=True):
            col1, col2 = st.columns(2)
            
            with col1:
                client_nom = st.text_input("Nom *", placeholder="Nom du client", key="client_nom_form")
                client_prenom = st.text_input("Prénom *", placeholder="Prénom du client", key="client_prenom_form")
            
            with col2:
                client_telephone = st.text_input("Téléphone *", placeholder="77 123 45 67", key="client_telephone_form")
                client_email = st.text_input("Email", placeholder="client@email.com (optionnel)", key="client_email_form")
        
        # Section 2: Images (côte à côte pour optimiser l'espace)
        with st.expander("🖼️ Photos du tissu et du modèle", expanded=True):
            col_img1, col_img2 = st.columns(2)
            
            with col_img1:
                st.markdown("#### 📸 Photo du tissu *")
                st.caption("Photo du tissu fourni par le client")
                fabric_image = st.file_uploader(
                    "Charger l'image du tissu",
                    type=['png', 'jpg', 'jpeg'],
                    key="fabric_image",
                    help="Format accepté: PNG, JPG, JPEG"
                )
                if not fabric_image:
                    st.warning("⚠️ Obligatoire")
            
            with col_img2:
                st.markdown("#### 👗 Photo du modèle *")
                st.caption("Photo du modèle souhaité par le client")
                model_image = st.file_uploader(
                    "Charger l'image du modèle",
                    type=['png', 'jpg', 'jpeg'],
                    key="model_image",
                    help="Format accepté: PNG, JPG, JPEG"
                )
                if not model_image:
                    st.warning("⚠️ Obligatoire")
            
            model_type = "image"  # Toujours en mode image
        
        # Section 3: Mesures (selon le modèle choisi)
        modele_actuel = st.session_state.get('modele_selectionne', modele)
        mesures_requises = MESURES.get(modele_actuel, [])
        
        if not mesures_requises:
            mesures_requises = ['Tour de poitrine', 'Tour de taille']  # Mesures par défaut
        
        with st.expander(f"📏 Mesures - {modele_actuel} (en cm)", expanded=True):
            st.caption(f"💡 Mesures spécifiques pour le modèle : **{modele_actuel}**")
            
            mesures_dict = {}
            
            # Afficher les mesures en colonnes (3 colonnes pour optimiser l'espace)
            num_cols = 3
            cols = st.columns(num_cols)
            
            for idx, mesure in enumerate(mesures_requises):
                col_idx = idx % num_cols
                with cols[col_idx]:
                    valeur = st.number_input(
                        mesure,
                        min_value=0.0,
                        max_value=300.0,
                        value=0.0,
                        step=0.5,
                        format="%.1f",
                        key=f"mesure_{modele_actuel}_{mesure}"
                    )
                    mesures_dict[mesure] = valeur
        
        # Section 4: Date de livraison et Options
        col_date, col_options = st.columns([2, 1])
        
        with col_date:
            st.markdown("#### 📅 Date de livraison")
            date_livraison = st.date_input(
                "Date prévue de livraison",
                value=datetime.now() + timedelta(days=7),
                min_value=datetime.now().date(),
                key="date_livraison_form"
            )
        
        with col_options:
            st.markdown("#### 📤 Options")
            st.caption("L'envoi automatique par email est activé si l'email est renseigné.")
        
        # Bouton de soumission
        st.markdown("<br>", unsafe_allow_html=True)
        submit = st.form_submit_button(
            "✅ Enregistrer la commande",
            type="primary"
        )
        
        if submit:
            # Récupérer les valeurs de prix depuis session_state (saisies en dehors du formulaire)
            prix_total = st.session_state.get('prix_total_form', 0.0)
            avance = st.session_state.get('avance_form', 0.0)
            reste = st.session_state.get('reste_form', 0.0)
            
            # Recalculer le reste pour s'assurer qu'il est correct
            reste = max(0.0, prix_total - avance)
            st.session_state.reste_form = reste
            
            # Validation
            erreurs = []
            
            if not client_nom or not client_prenom:
                erreurs.append("Le nom et prénom du client sont obligatoires")
            
            if not client_telephone:
                erreurs.append("Le téléphone du client est obligatoire")
            
            # Validation des images
            if not fabric_image:
                erreurs.append("L'image du tissu du client est obligatoire")
            
            if not model_image:
                erreurs.append("L'image du modèle de vêtement est obligatoire")
            
            if prix_total <= 0:
                erreurs.append("Le prix total doit être supérieur à 0")
            
            if avance < 0:
                erreurs.append("L'avance ne peut pas être négative")
            
            if avance > prix_total:
                erreurs.append("L'avance ne peut pas être supérieure au prix total")
                # Corriger automatiquement
                avance = prix_total
                st.session_state.avance_form = avance
                reste = 0.0
            
            # Vérifier les mesures
            mesures_invalides = [m for m, v in mesures_dict.items() if v <= 0]
            if mesures_invalides:
                erreurs.append(f"Mesures invalides: {', '.join(mesures_invalides)}")
            
            if erreurs:
                for erreur in erreurs:
                    st.error(f"❌ {erreur}")
            else:
                # Créer la commande
                with st.spinner("Enregistrement de la commande..."):
                    client_info = {
                        'nom': client_nom,
                        'prenom': client_prenom,
                        'telephone': client_telephone,
                        'email': client_email if client_email else None
                    }
                    
                    # Récupérer le reste calculé (déjà dans session_state)
                    reste = st.session_state.get('reste_form', max(0.0, prix_total - avance))
                    
                    # S'assurer que le reste est correct
                    reste = max(0.0, float(prix_total) - float(avance))
                    
                    # Créer la commande avec les TROIS valeurs financières
                    # Utiliser le modèle depuis session_state
                    modele_final = st.session_state.get('modele_selectionne', modele)
                    
                    commande_info = {
                        'categorie': categorie,
                        'sexe': sexe,
                        'modele': modele_final,
                        'mesures': mesures_dict,
                        'prix_total': float(prix_total),  # Valeur 0
                        'avance': float(avance),          # Valeur 1
                        'reste': float(reste),           # Valeur 2 - Calculé et envoyé à la BDD
                        'date_livraison': date_livraison.strftime('%Y-%m-%d'),
                        'model_type': model_type
                    }
                    
                    # Sauvegarder les images (OBLIGATOIRES)
                    # Générer un ID temporaire pour les noms de fichiers
                    import time
                    temp_id = int(time.time())
                    
                    # Sauvegarder l'image du tissu (OBLIGATOIRE)
                    fabric_image_path = commande_controller.sauvegarder_image(
                        fabric_image, temp_id, 'fabric'
                    )
                    
                    if not fabric_image_path:
                        st.error("❌ Erreur lors de la sauvegarde de l'image du tissu")
                        st.stop()
                    
                    commande_info['fabric_image_path'] = fabric_image_path
                    
                    # Lire et optimiser l'image du tissu en binaire pour la base de données
                    fabric_image.seek(0)  # Revenir au début du fichier
                    fabric_image_bytes_original = fabric_image.read()
                    
                    # Optimiser l'image pour réduire sa taille (évite l'erreur max_allowed_packet)
                    with st.spinner("🖼️ Optimisation de l'image du tissu..."):
                        fabric_image_bytes = optimiser_image(
                            fabric_image_bytes_original,
                            max_size=(1920, 1920),  # Taille max 1920x1920 pixels
                            quality=85,  # Qualité JPEG 85%
                            max_file_size_mb=2.0  # Taille max 2MB
                        )
                    
                    # Afficher la réduction de taille si optimisation réussie
                    taille_originale = obtenir_taille_fichier_mb(fabric_image_bytes_original)
                    taille_optimisee = obtenir_taille_fichier_mb(fabric_image_bytes)
                    if taille_originale > taille_optimisee:
                        reduction = ((taille_originale - taille_optimisee) / taille_originale) * 100
                        st.info(f"📊 Image optimisée: {taille_originale:.2f} MB → {taille_optimisee:.2f} MB (-{reduction:.1f}%)")
                    
                    commande_info['fabric_image'] = fabric_image_bytes
                    commande_info['fabric_image_name'] = fabric_image.name
                    
                    # Sauvegarder l'image du modèle (OBLIGATOIRE)
                    model_image_path = commande_controller.sauvegarder_image(
                        model_image, temp_id, 'model'
                    )
                    
                    if not model_image_path:
                        st.error("❌ Erreur lors de la sauvegarde de l'image du modèle")
                        st.stop()
                    
                    # Stocker le chemin de l'image du modèle dans la base de données
                    commande_info['model_image_path'] = model_image_path
                    
                    # Lire et optimiser l'image du modèle en binaire pour la base de données
                    model_image.seek(0)  # Revenir au début du fichier
                    model_image_bytes_original = model_image.read()
                    
                    # Optimiser l'image pour réduire sa taille (évite l'erreur max_allowed_packet)
                    with st.spinner("🖼️ Optimisation de l'image du modèle..."):
                        model_image_bytes = optimiser_image(
                            model_image_bytes_original,
                            max_size=(1920, 1920),  # Taille max 1920x1920 pixels
                            quality=85,  # Qualité JPEG 85%
                            max_file_size_mb=2.0  # Taille max 2MB
                        )
                    
                    # Afficher la réduction de taille si optimisation réussie
                    taille_originale = obtenir_taille_fichier_mb(model_image_bytes_original)
                    taille_optimisee = obtenir_taille_fichier_mb(model_image_bytes)
                    if taille_originale > taille_optimisee:
                        reduction = ((taille_originale - taille_optimisee) / taille_originale) * 100
                        st.info(f"📊 Image optimisée: {taille_originale:.2f} MB → {taille_optimisee:.2f} MB (-{reduction:.1f}%)")
                    
                    commande_info['model_image'] = model_image_bytes
                    commande_info['model_image_name'] = model_image.name
                    
                    succes, commande_id, message = commande_controller.creer_commande(
                        st.session_state.couturier_data['id'],
                        client_info,
                        commande_info
                    )
                    
                    if succes:
                        st.success(f"✅ {message}")
                        st.balloons()
                        
                        # Variables pour suivre le statut de chaque fonction
                        statut_fonctions = {
                            'base_donnees': {'succes': True, 'message': '✅ Enregistrement en base de données réussi'},
                            'generation_pdf': {'succes': False, 'message': '', 'pdf_path': None},
                            'upload_pdf': {'succes': False, 'message': '', 'dossier': None},
                            'email': {'succes': False, 'message': ''}
                        }
                        
                        # ============================================================
                        # FONCTION 1 : Enregistrement dans la base de données (DÉJÀ FAIT)
                        # ============================================================
                        # Cette fonction est déjà exécutée avant, donc on marque juste le succès
                        
                        # Récupérer les données complètes de la commande
                        try:
                            commande_data = commande_controller.obtenir_details_commande(commande_id)
                            if not commande_data:
                                statut_fonctions['base_donnees']['succes'] = False
                                statut_fonctions['base_donnees']['message'] = '❌ Erreur: Impossible de récupérer les données de la commande'
                                st.error(statut_fonctions['base_donnees']['message'])
                        except Exception as e:
                            statut_fonctions['base_donnees']['succes'] = False
                            statut_fonctions['base_donnees']['message'] = f'❌ Erreur base de données: {str(e)}'
                            st.error(statut_fonctions['base_donnees']['message'])
                            commande_data = None
                        
                        # ============================================================
                        # FONCTION 2 : Génération et upload du PDF (TOUJOURS EXÉCUTÉE)
                        # ============================================================
                        pdf_path = None
                        
                        # Préparer les données pour le PDF
                        # Récupérer les données du couturier depuis la session
                        couturier_data = st.session_state.couturier_data
                        
                        # Utiliser commande_data si disponible (avec les valeurs de la BDD), sinon utiliser les données du formulaire
                        if commande_data:
                            # Utiliser les données de la BDD (incluant le reste calculé)
                            pdf_data = commande_data.copy()
                            # S'assurer que les chemins d'images sont présents
                            if 'fabric_image_path' not in pdf_data or not pdf_data['fabric_image_path']:
                                pdf_data['fabric_image_path'] = fabric_image_path
                            if 'model_image_path' not in pdf_data or not pdf_data['model_image_path']:
                                pdf_data['model_image_path'] = model_image_path
                            # S'assurer que les noms d'images sont présents
                            if 'fabric_image_name' not in pdf_data or not pdf_data['fabric_image_name']:
                                pdf_data['fabric_image_name'] = fabric_image.name if fabric_image else 'fabric.jpg'
                            if 'model_image_name' not in pdf_data or not pdf_data['model_image_name']:
                                pdf_data['model_image_name'] = model_image.name if model_image else 'model.jpg'
                        else:
                            # Construire pdf_data depuis le formulaire (fallback)
                            pdf_data = {
                                'id': commande_id,
                                'client_nom': client_nom,
                                'client_prenom': client_prenom,
                                'client_telephone': client_telephone,
                                'client_email': client_email if client_email else None,
                                'categorie': categorie,
                                'sexe': sexe,
                                'modele': modele,
                                'mesures': mesures_dict,
                                'prix_total': float(prix_total),
                                'avance': float(avance),
                                'reste': float(reste),  # Reste calculé automatiquement
                                'date_livraison': date_livraison.strftime('%Y-%m-%d'),
                                'statut': 'En cours',
                                'date_creation': datetime.now(),
                                'couturier_nom': couturier_data.get('nom', ''),
                                'couturier_prenom': couturier_data.get('prenom', ''),
                                'couturier_code': couturier_data.get('code_couturier', ''),
                                'fabric_image_path': fabric_image_path,
                                'fabric_image_name': fabric_image.name if fabric_image else 'fabric.jpg',
                                'model_image_path': model_image_path,
                                'model_image_name': model_image.name if model_image else 'model.jpg',
                                'model_type': model_type
                            }
                        
                        # Générer le PDF (TOUJOURS, même si commande_data n'est pas disponible)
                        st.markdown("---")
                        st.markdown("### 📄 Génération du PDF")
                        
                        # Vérifier que pdf_data est bien défini
                        if not pdf_data:
                            statut_fonctions['generation_pdf']['succes'] = False
                            statut_fonctions['generation_pdf']['message'] = '❌ Erreur: Données de commande manquantes pour la génération du PDF'
                            st.error(statut_fonctions['generation_pdf']['message'])
                        else:
                            try:
                                with st.spinner("📄 Génération du PDF en cours..."):
                                    # Vérifier que le dossier de stockage existe
                                    from config import PDF_STORAGE_PATH
                                    if not os.path.exists(PDF_STORAGE_PATH):
                                        os.makedirs(PDF_STORAGE_PATH, exist_ok=True)
                                        st.info(f"📁 Dossier PDF créé: {PDF_STORAGE_PATH}")
                                    
                                    # Vérifier que pdf_data contient les données essentielles
                                    champs_requis = ['id', 'client_nom', 'client_prenom', 'modele', 'prix_total', 'avance']
                                    champs_manquants = [champ for champ in champs_requis if champ not in pdf_data or pdf_data[champ] is None]
                                    if champs_manquants:
                                        raise ValueError(f"Champs manquants dans les données: {', '.join(champs_manquants)}")
                                    
                                    # Générer le PDF
                                    pdf_path = pdf_controller.generer_pdf_commande(pdf_data)
                                    
                                    if pdf_path and os.path.exists(pdf_path):
                                        statut_fonctions['generation_pdf']['succes'] = True
                                        statut_fonctions['generation_pdf']['message'] = f'✅ PDF généré avec succès: {os.path.basename(pdf_path)}'
                                        statut_fonctions['generation_pdf']['pdf_path'] = pdf_path
                                        st.success(statut_fonctions['generation_pdf']['message'])
                                        
                                        # Lire le PDF en bytes et stocker dans session_state (HORS du formulaire)
                                        try:
                                            with open(pdf_path, "rb") as pdf_file:
                                                pdf_bytes = pdf_file.read()
                                            st.session_state['pdf_path_upload'] = pdf_path
                                            st.session_state['pdf_bytes'] = pdf_bytes
                                            st.session_state['pdf_filename'] = os.path.basename(pdf_path)
                                            st.session_state['show_download_section'] = True
                                        except Exception as e:
                                            st.error(f"❌ Erreur lors de l'ouverture du PDF: {str(e)}")
                                    elif pdf_path is None:
                                        # Le contrôleur a retourné None, vérifier s'il y a une erreur stockée
                                        error_msg = pdf_controller.last_error or "Erreur inconnue lors de la génération du PDF"
                                        error_details = pdf_controller.last_error_details or "Aucun détail disponible"
                                        raise Exception(f"{error_msg}\n\n{error_details}")
                                        
                                        # Tentative de téléchargement automatique (optionnel)
                                        try:
                                            import base64
                                            with open(pdf_path, "rb") as _f:
                                                _pdf_bytes = _f.read()
                                            _b64 = base64.b64encode(_pdf_bytes).decode()
                                            _file_name = os.path.basename(pdf_path)
                                            _href = f"data:application/pdf;base64,{_b64}"
                                            st.components.v1.html(
                                                f"""
                                                <html>
                                                <body>
                                                <a id='auto_dl' href='{_href}' download='{_file_name}'></a>
                                                <script>
                                                (function(){{
                                                  var a = document.getElementById('auto_dl');
                                                  if(a){{ 
                                                    setTimeout(function(){{ a.click(); }}, 500);
                                                  }}
                                                }})();
                                                </script>
                                                </body>
                                                </html>
                                                """,
                                                height=0
                                            )
                                        except Exception:
                                            # Le téléchargement automatique est optionnel, on continue même s'il échoue
                                            pass
                                    else:
                                        # Le PDF n'a pas été généré ou n'existe pas
                                        statut_fonctions['generation_pdf']['succes'] = False
                                        if pdf_path:
                                            statut_fonctions['generation_pdf']['message'] = f'❌ Erreur: Le PDF n\'a pas pu être créé. Chemin attendu: {pdf_path}'
                                        else:
                                            statut_fonctions['generation_pdf']['message'] = '❌ Erreur: La génération du PDF a retourné None. Vérifiez les logs pour plus de détails.'
                                        st.error(statut_fonctions['generation_pdf']['message'])
                                        st.warning("💡 Vérifiez que le dossier de stockage PDF existe et que vous avez les permissions d'écriture.")
                            except Exception as e:
                                statut_fonctions['generation_pdf']['succes'] = False
                                error_msg = str(e)
                                statut_fonctions['generation_pdf']['message'] = f'❌ Erreur génération PDF: {error_msg}'
                                st.error(statut_fonctions['generation_pdf']['message'])
                                
                                # Afficher les détails de l'erreur dans un expander
                                with st.expander("🔍 Détails de l'erreur (cliquez pour voir)"):
                                    st.code(error_msg, language='text')
                                    
                                    # Afficher aussi les données envoyées au PDF (pour débogage)
                                    st.markdown("**Données envoyées au contrôleur PDF:**")
                                    st.json({k: str(v)[:100] if len(str(v)) > 100 else v for k, v in pdf_data.items()})
                        
                        # ============================================================
                        # FONCTION 3 : Envoi par Email (AUTOMATIQUE)
                        # ============================================================
                        if client_email:
                            try:
                                if not pdf_path or not os.path.exists(pdf_path):
                                    statut_fonctions['email']['succes'] = False
                                    statut_fonctions['email']['message'] = "⚠️ Email non envoyé : PDF introuvable"
                                    st.warning(statut_fonctions['email']['message'])
                                else:
                                    with st.spinner("📧 Envoi de l'email au client..."):
                                        subject = f"Fiche de commande - {client_prenom} {client_nom}"
                                        body = (
                                            f"Bonjour {client_prenom} {client_nom},\n\n"
                                            "Votre commande a été enregistrée avec succès.\n"
                                            f"Modèle: {modele}\n"
                                            f"Prix total: {prix_total:,.0f} FCFA\n"
                                            f"Avance: {avance:,.0f} FCFA\n"
                                            f"Reste: {reste:,.0f} FCFA\n"
                                            f"Date de livraison: {date_livraison.strftime('%d/%m/%Y')}\n\n"
                                            "Merci pour votre confiance."
                                        )
                                        
                                        succes_email, message_email = email_controller.envoyer_email_avec_message(
                                            client_email,
                                            subject,
                                            body,
                                            attachments=[pdf_path]
                                        )
                                        
                                        if succes_email:
                                            statut_fonctions['email']['succes'] = True
                                            statut_fonctions['email']['message'] = f"✅ {message_email}"
                                            st.success(statut_fonctions['email']['message'])
                                        else:
                                            statut_fonctions['email']['succes'] = False
                                            statut_fonctions['email']['message'] = f"❌ Email non envoyé : {message_email}"
                                            st.error(statut_fonctions['email']['message'])
                            except Exception as e:
                                statut_fonctions['email']['succes'] = False
                                statut_fonctions['email']['message'] = f"❌ Erreur email: {str(e)}"
                                st.error(statut_fonctions['email']['message'])
                        
                        # ============================================================
                        # RÉCAPITULATIF DES FONCTIONS
                        # ============================================================
                        st.markdown("---")
                        st.markdown("### 📊 Statut des opérations")
                        
                        col_stat1, col_stat2 = st.columns(2)
                        
                        with col_stat1:
                            st.markdown("#### ✅ Succès")
                            for fonction, statut in statut_fonctions.items():
                                if statut['succes']:
                                    st.success(f"**{fonction.replace('_', ' ').title()}:** {statut['message']}")
                        
                        with col_stat2:
                            st.markdown("#### ❌ Échecs")
                            echecs = [f for f, s in statut_fonctions.items() if not s['succes']]
                            if echecs:
                                for fonction in echecs:
                                    st.error(f"**{fonction.replace('_', ' ').title()}:** {statut_fonctions[fonction]['message']}")
                            else:
                                st.success("🎉 Toutes les opérations ont réussi!")
                        
                        # Afficher récapitulatif
                        st.markdown("---")
                        st.markdown("### 📋 Récapitulatif")
                        
                        col1, col2 = st.columns(2)
                        
                        with col1:
                            st.info(f"""
                            **Client:** {client_prenom} {client_nom}  
                            **Téléphone:** {client_telephone}  
                            **Modèle:** {modele}
                            """)
                        
                        with col2:
                            st.success(f"""
                            **Prix total:** {prix_total:.2f} FCFA  
                            **Avance:** {avance:.2f} FCFA  
                            **Reste:** {reste:.2f} FCFA  
                            **Livraison:** {date_livraison.strftime('%d/%m/%Y')}
                            """)
                    else:
                        st.error(f"❌ {message}")
    
    # Section de téléchargement du PDF (en dehors du formulaire pour éviter l'erreur st.download_button dans st.form)
    if st.session_state.get('show_download_section', False) and st.session_state.get('pdf_bytes'):
        st.markdown("---")
        st.markdown("### 📥 Télécharger le PDF")
        try:
            st.download_button(
                label="📥 Télécharger le PDF maintenant",
                data=st.session_state['pdf_bytes'],
                file_name=st.session_state.get('pdf_filename', 'commande.pdf'),
                mime="application/pdf",
                width='stretch',
                key="download_pdf_outside",
                type="primary"
            )
        except Exception as e:
            st.error(f"❌ Erreur lors du téléchargement du PDF: {str(e)}")
    
    # Section d'upload du PDF (en dehors du formulaire pour éviter l'erreur st.button dans st.form)
    if st.session_state.get('show_upload_section', False) and st.session_state.get('pdf_path_upload'):
        pdf_path_upload = st.session_state['pdf_path_upload']
        st.markdown("---")
        st.markdown("### 📁 Sauvegarder le PDF dans un dossier personnalisé (optionnel)")
        col_upload1, col_upload2 = st.columns([3, 1])
        
        with col_upload1:
            dossier_upload = st.text_input(
                "Chemin du dossier de destination",
                value=os.path.dirname(pdf_path_upload) if pdf_path_upload else "",
                help="Entrez le chemin complet du dossier (ex: C:/MesDocuments/PDFs ou /home/user/pdfs)",
                key="dossier_upload_input_outside"
            )
        
        with col_upload2:
            st.markdown("<br>", unsafe_allow_html=True)
            if st.button("📤 Copier le PDF", width='stretch', key="btn_upload_pdf_outside"):
                try:
                    if dossier_upload and os.path.exists(dossier_upload):
                        with st.spinner("📤 Copie du PDF..."):
                            pdf_uploaded = pdf_controller.uploader_pdf_dossier(pdf_path_upload, dossier_upload)
                            if pdf_uploaded:
                                st.success(f'✅ PDF copié dans: {pdf_uploaded}')
                                st.balloons()
                            else:
                                st.error('❌ Erreur: Échec de la copie du PDF')
                    elif dossier_upload:
                        st.error(f"❌ Le dossier '{dossier_upload}' n'existe pas. Veuillez créer le dossier ou vérifier le chemin.")
                    else:
                        st.warning("⚠️ Veuillez entrer un chemin de dossier")
                except Exception as e:
                    st.error(f'❌ Erreur copie PDF: {str(e)}')