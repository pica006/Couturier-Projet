"""
Vue pour la gestion des salons (SUPER_ADMIN uniquement)
"""
import streamlit as st
from models.salon_model import SalonModel
from utils.permissions import est_super_admin
import pandas as pd


def afficher_page_salons():
    """
    Page de gestion des salons (accessible uniquement au SUPER_ADMIN)
    """
    # Vérifier les permissions
    if not est_super_admin():
        st.error("❌ Accès refusé : Cette page est réservée au Super Administrateur")
        return
    
    # En-tête encadré standardisé
    from utils.page_header import afficher_header_page
    afficher_header_page("🏢 Gestion des Salons de Couture", "Créez et gérez vos salons de couture")
    
    # Récupérer la connexion
    if 'db_connection' not in st.session_state:
        st.error("❌ Erreur : Connexion à la base de données non établie")
        return
    
    salon_model = SalonModel(st.session_state.db_connection)
    
    # Onglets
    tab1, tab2, tab3 = st.tabs([
        "📋 Liste des salons",
        "➕ Créer un salon",
        "📊 Statistiques globales"
    ])
    
    # ========================================================================
    # ONGLET 1 : LISTE DES SALONS
    # ========================================================================
    with tab1:
        st.subheader("📋 Tous les salons")
        
        # Récupérer la liste des salons
        salons = salon_model.lister_tous_salons()
        
        if not salons:
            st.info("ℹ️ Aucun salon créé pour le moment")
            st.write("Utilisez l'onglet **'➕ Créer un salon'** pour ajouter votre premier salon")
        else:
            st.success(f"✅ {len(salons)} salon(s) actif(s)")
            
            # Afficher sous forme de tableau
            df_salons = pd.DataFrame(salons)
            
            # Sélection des colonnes à afficher
            colonnes_affichage = [
                'salon_id', 'nom_salon', 'quartier', 'responsable',
                'code_admin', 'admin_nom', 'admin_prenom',
                'nb_employes', 'nb_clients', 'nb_commandes',
                'telephone', 'email'
            ]
            
            # Vérifier que les colonnes existent
            colonnes_existantes = [col for col in colonnes_affichage if col in df_salons.columns]
            
            st.dataframe(
                df_salons[colonnes_existantes],
                width='stretch',
                hide_index=True
            )
            
            # Détails d'un salon sélectionné
            st.markdown("---")
            st.subheader("📌 Détails d'un salon")
            
            salon_options = {
                f"{s['salon_id']} - {s['nom_salon']}": s for s in salons
            }
            
            selected = st.selectbox(
                "Sélectionner un salon",
                options=list(salon_options.keys()),
                key="select_salon_detail"
            )
            
            if selected:
                salon = salon_options[selected]
                
                col1, col2, col3 = st.columns(3)
                
                with col1:
                    st.metric("👥 Employés", salon['nb_employes'])
                
                with col2:
                    st.metric("🙋 Clients", salon['nb_clients'])
                
                with col3:
                    st.metric("📦 Commandes", salon['nb_commandes'])
                
                st.markdown("---")
                
                col_a, col_b = st.columns(2)
                
                with col_a:
                    st.write("**📍 Informations du salon**")
                    st.write(f"**Nom** : {salon['nom_salon']}")
                    st.write(f"**Quartier** : {salon['quartier']}")
                    st.write(f"**Responsable** : {salon['responsable']}")
                    st.write(f"**Téléphone** : {salon['telephone']}")
                    st.write(f"**Email** : {salon['email']}")
                
                with col_b:
                    slogan_affiche = salon.get('pdf_slogan') or "L'Elegance Sur Mesure"
                    st.write("**👤 Administrateur**")
                    st.write(f"**Code** : {salon['code_admin']}")
                    st.write(f"**Nom** : {salon['admin_nom']} {salon['admin_prenom']}")
                    st.write(f"**Date de création** : {salon['date_creation']}")
                    st.write(f"**Slogan PDF** : {slogan_affiche}")
                    st.write(f"**Couleur PDF** : {salon.get('pdf_theme_color') or '#9B8AB5'}")

                st.markdown("### ✏️ Éditer branding PDF du salon")
                with st.form(f"form_edit_pdf_branding_{salon['salon_id']}"):
                    edit_slogan = st.text_input(
                        "Slogan PDF",
                        value=salon.get('pdf_slogan') or "L'Elegance Sur Mesure",
                        key=f"edit_slogan_{salon['salon_id']}",
                    )
                    edit_color = st.color_picker(
                        "Couleur PDF",
                        value=salon.get('pdf_theme_color') or "#9B8AB5",
                        key=f"edit_color_{salon['salon_id']}",
                    )
                    submit_edit_branding = st.form_submit_button("💾 Enregistrer branding PDF")

                if submit_edit_branding:
                    ok = salon_model.modifier_salon(
                        salon_id=salon['salon_id'],
                        pdf_slogan=edit_slogan,
                        pdf_theme_color=edit_color,
                    )
                    if ok:
                        st.success("✅ Branding PDF du salon mis à jour.")
                        st.rerun()
                    else:
                        st.error("❌ Impossible de mettre à jour le branding PDF du salon.")
    
    # ========================================================================
    # ONGLET 2 : CRÉER UN SALON
    # ========================================================================
    with tab2:
        st.subheader("➕ Créer un nouveau salon")
        
        st.info("""
        ℹ️ **Instructions** :
        - Remplissez les informations du salon
        - Définissez un code de connexion unique pour l'administrateur
        - Un compte admin sera automatiquement créé pour gérer ce salon
        """)
        
        with st.form("form_creer_salon"):
            st.markdown("### 🏢 Informations du salon")
            
            col1, col2 = st.columns(2)
            
            with col1:
                nom_salon = st.text_input(
                    "Nom du salon *",
                    placeholder="Ex: Atelier Jaind",
                    help="Nom commercial du salon de couture"
                )
                quartier = st.text_input(
                    "Quartier / Adresse *",
                    placeholder="Ex: Médina, Dakar",
                    help="Localisation du salon"
                )
                responsable = st.text_input(
                    "Nom complet du responsable *",
                    placeholder="Ex: Moustapha DIOP",
                    help="Personne responsable du salon"
                )
            
            with col2:
                telephone = st.text_input(
                    "Téléphone *",
                    placeholder="Ex: 771234567",
                    help="Numéro de téléphone du salon"
                )
                email = st.text_input(
                    "Email",
                    placeholder="Ex: contact@salon.com",
                    help="Email du salon (optionnel)"
                )

            st.markdown("---")
            st.markdown("### ✉️ Paramètres email du salon (SMTP)")
            st.caption("Chaque salon utilise son propre compte email pour l'envoi automatique.")

            col_smtp1, col_smtp2 = st.columns(2)
            with col_smtp1:
                smtp_host = st.text_input(
                    "SMTP host",
                    value="smtp.gmail.com",
                    help="Serveur SMTP (Gmail : smtp.gmail.com)",
                )
                smtp_port = st.number_input(
                    "SMTP port",
                    value=587,
                    min_value=1,
                    max_value=65535,
                    step=1,
                )
                smtp_use_tls = st.checkbox("Utiliser TLS", value=True)
                smtp_use_ssl = st.checkbox("Utiliser SSL", value=False)

            with col_smtp2:
                smtp_user = st.text_input(
                    "Adresse email d'envoi *",
                    placeholder="Ex: mon.salon@gmail.com",
                )
                smtp_password = st.text_input(
                    "Mot de passe d'application *",
                    type="password",
                    help="Pour Gmail, utilisez le mot de passe d'application (16 caractères), pas le mot de passe normal.",
                )
                smtp_from = st.text_input(
                    "Adresse From (optionnel)",
                    placeholder="Laisser vide pour utiliser l'adresse d'envoi",
                )

            st.markdown("---")
            st.markdown("### 🎨 Branding PDF du salon")
            col_pdf1, col_pdf2 = st.columns(2)
            with col_pdf1:
                pdf_slogan = st.text_input(
                    "Slogan PDF",
                    value="L'Elegance Sur Mesure",
                    help="Texte affiche dans l'en-tete et le pied des PDF du salon.",
                )
            with col_pdf2:
                pdf_theme_color = st.color_picker(
                    "Couleur principale PDF",
                    value="#9B8AB5",
                    help="Couleur de theme appliquee aux bandeaux PDF de ce salon.",
                )
            
            st.markdown("---")
            st.markdown("### 👤 Administrateur du salon")
            
            col3, col4 = st.columns(2)
            
            with col3:
                code_admin = st.text_input(
                    "Code de connexion de l'admin *",
                    placeholder="Ex: Jaind_001",
                    help="Code unique pour se connecter"
                ).upper()
                
                nom_admin = st.text_input(
                    "Nom de l'admin *",
                    placeholder="Ex: DIOP"
                )
            
            with col4:
                password_admin = st.text_input(
                    "Mot de passe *",
                    type="password",
                    help="Mot de passe de connexion"
                )
                
                prenom_admin = st.text_input(
                    "Prénom de l'admin *",
                    placeholder="Ex: Moustapha"
                )
            
            submitted = st.form_submit_button("💾 Créer le salon")
            
            if submitted:
                # Validation
                champs_obligatoires = [
                    nom_salon,
                    quartier,
                    responsable,
                    telephone,
                    code_admin,
                    password_admin,
                    nom_admin,
                    prenom_admin,
                    smtp_user,
                    smtp_password,
                ]
                if not all(champs_obligatoires):
                    st.error("❌ Veuillez remplir tous les champs obligatoires (*) y compris l'email et le mot de passe d'application du salon.")
                else:
                    # Créer le salon
                    with st.spinner("🔄 Création du salon en cours..."):
                        result = salon_model.creer_salon_avec_admin(
                            nom_salon=nom_salon,
                            quartier=quartier,
                            responsable=responsable,
                            telephone=telephone,
                            email=email if email else '',
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
                        )
                    
                    if result:
                        st.success(f"""
                        ✅ {result['message']}
                        
                        **📌 Informations du salon créé** :
                        - **Salon ID** : {result['salon_id']}
                        - **Admin ID** : {result['admin_id']}
                        - **Nom** : {result['nom_salon']}
                        
                        **🔑 Identifiants de connexion de l'admin** :
                        - **Code** : {result['code_admin']}
                        - **Mot de passe** : {password_admin}
                        
                        ⚠️ **Notez ces identifiants** et transmettez-les à l'administrateur du salon !
                        """)
                        
                        st.balloons()
                    else:
                        st.error("❌ Erreur lors de la création du salon. Vérifiez que le code admin n'existe pas déjà.")
    
    # ========================================================================
    # ONGLET 3 : STATISTIQUES GLOBALES
    # ========================================================================
    with tab3:
        st.subheader("📊 Statistiques globales")
        
        salons = salon_model.lister_tous_salons()
        
        if not salons:
            st.info("ℹ️ Aucune statistique disponible")
        else:
            # KPIs globaux
            col1, col2, col3, col4 = st.columns(4)
            
            total_salons = len(salons)
            total_employes = sum(s['nb_employes'] for s in salons)
            total_clients = sum(s['nb_clients'] for s in salons)
            total_commandes = sum(s['nb_commandes'] for s in salons)
            
            with col1:
                st.metric("🏢 Salons actifs", total_salons)
            
            with col2:
                st.metric("👥 Total employés", total_employes)
            
            with col3:
                st.metric("🙋 Total clients", total_clients)
            
            with col4:
                st.metric("📦 Total commandes", total_commandes)
            
            st.markdown("---")
            
            # Graphique de répartition
            st.subheader("📈 Répartition par salon")
            
            df_stats = pd.DataFrame(salons)
            
            # Graphique en barres
            chart_data = df_stats[['nom_salon', 'nb_employes', 'nb_clients', 'nb_commandes']].set_index('nom_salon')
            
            st.bar_chart(chart_data)
            
            st.markdown("---")
            
            # Tableau récapitulatif
            st.subheader("📋 Tableau récapitulatif")
            
            df_display = df_stats[[
                'salon_id', 'nom_salon', 'quartier', 
                'nb_employes', 'nb_clients', 'nb_commandes'
            ]].copy()
            
            df_display.columns = [
                'ID', 'Salon', 'Quartier',
                'Employés', 'Clients', 'Commandes'
            ]
            
            st.dataframe(df_display, use_container_width=True, hide_index=True)

