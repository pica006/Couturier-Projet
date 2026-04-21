"""
Vue pour permettre aux employés de fermer leurs commandes
"""
import streamlit as st
import os
from datetime import date, datetime
from controllers.commande_controller import CommandeController
from controllers.email_controller import EmailController
from models.salon_model import SalonModel
from utils.role_utils import obtenir_couturier_id, obtenir_salon_id, est_admin


def afficher_page_fermer_commandes():
    """Page permettant aux employés de fermer leurs commandes"""
    
    # En-tête encadré standardisé
    from utils.page_header import afficher_header_page
    afficher_header_page("🔒 Fermer mes commandes", "Gérez les paiements et demandez la fermeture de vos commandes")

    st.info(
        "**Parcours prévu :** 1) L’employé règle le **reste à payer** (onglet paiements) → statut **Terminé** quand tout est payé. "
        "2) Il demande la **livraison** (onglet commandes terminées) → une entrée **en attente** apparaît chez l’**admin** "
        "(Administration → Gestion des commandes → Demandes en attente). "
        "3) L’admin **valide** → statut **Livré et payé** et PDF côté client si configuré."
    )
    
    # Récupérer les données du couturier depuis la session
    couturier_data = st.session_state.get('couturier_data')
    if not couturier_data:
        st.error("❌ Erreur : Vous devez être connecté")
        return
    
    couturier_id = obtenir_couturier_id(couturier_data)
    if not couturier_id:
        st.error("❌ Erreur : Impossible de récupérer votre identifiant")
        return
    
    # Obtenir le salon_id pour filtrer les commandes
    try:
        salon_id_user = obtenir_salon_id(couturier_data)
    except Exception:
        salon_id_user = None
    
    if not salon_id_user:
        st.error("❌ Erreur : impossible de récupérer votre salon. Merci de vous reconnecter.")
        return
    
    is_admin_user = est_admin(couturier_data)
    
    db = st.session_state.db_connection
    commande_controller = CommandeController(db)
    commande_model = commande_controller.commande_model

    # Configurer l'email pour le salon courant
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
    
    # Onglets
    tab1, tab2, tab3 = st.tabs([
        "📝 Modifier les paiements", 
        "✅ Commandes terminées (en attente de livraison)", 
        "📄 Upload PDFs des commandes terminées"
    ])

    def _badge_statut(statut: str) -> str:
        s = (statut or "").strip().lower()
        if s == "en cours":
            return "⏳ En cours"
        if s == "terminé":
            return "✅ Terminé"
        if s == "livré et payé":
            return "🚚 Livré et payé"
        if s == "supprimée":
            return "🗑️ Supprimée"
        return f"📌 {statut or 'Inconnu'}"

    def _to_date(value):
        if value is None:
            return None
        if isinstance(value, datetime):
            return value.date()
        if isinstance(value, date):
            return value
        if isinstance(value, str):
            raw = value.strip()
            for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%Y-%m-%d %H:%M:%S", "%d-%m-%Y"):
                try:
                    return datetime.strptime(raw, fmt).date()
                except ValueError:
                    continue
        return None

    def _meta_urgence(commande):
        # Priorité globale: rouge (0) > orange (1) > vert (2)
        date_livraison = _to_date(commande.get("date_livraison"))
        reste = float(commande.get("reste", 0) or 0)
        today = date.today()
        jours = None if date_livraison is None else (date_livraison - today).days

        if jours is not None and jours < 0:
            return {
                "niveau": "rouge",
                "emoji": "🔴",
                "label": f"En retard de {abs(jours)} jour(s)",
                "priorite": 0,
                "jours": jours,
            }
        if jours is not None and jours <= 2:
            return {
                "niveau": "orange",
                "emoji": "🟠",
                "label": "Échéance proche (0-2 jours)",
                "priorite": 1,
                "jours": jours,
            }
        if reste > 0:
            return {
                "niveau": "orange",
                "emoji": "🟠",
                "label": "Paiement à finaliser",
                "priorite": 1,
                "jours": 9999 if jours is None else jours,
            }
        return {
            "niveau": "vert",
            "emoji": "🟢",
            "label": "Situation stable",
            "priorite": 2,
            "jours": 9999 if jours is None else jours,
        }

    def _trier_commandes_urgentes(commandes):
        def _safe_int(value, default=0):
            try:
                return int(value)
            except Exception:
                return default

        return sorted(
            commandes,
            key=lambda c: (
                _meta_urgence(c)["priorite"],
                _meta_urgence(c)["jours"],
                -float(c.get("reste", 0) or 0),
                _safe_int(c.get("id", 0) or 0),
            ),
        )

    def _bandeau_urgence(commande):
        meta = _meta_urgence(commande)
        message = f"{meta['emoji']} **Priorité {meta['niveau'].upper()}** — {meta['label']}"
        if meta["niveau"] == "rouge":
            st.error(message)
        elif meta["niveau"] == "orange":
            st.warning(message)
        else:
            st.success(message)
    
    # ========================================================================
    # ONGLET 1 : MODIFIER LES PAIEMENTS (Commandes avec avance)
    # ========================================================================
    with tab1:
        st.markdown("### 💰 Modifier les paiements")
        st.markdown("Liste de vos commandes où une avance a été versée. Vous pouvez modifier directement le prix total, l'avance et le reste à payer.")
        st.caption("Objectif : solder le reste à payer. Une commande soldée passe automatiquement au statut **Terminé**.")
        
        # Bouton de rafraîchissement
        col_refresh, _ = st.columns([1, 5])
        with col_refresh:
            if st.button("🔄 Actualiser", key="refresh_commandes_paiement", use_container_width=True):
                st.rerun()
        
        st.markdown("---")
        
        # Filtres de période
        col_filter1, col_filter2 = st.columns(2)
        with col_filter1:
            date_debut_paiements = st.date_input(
                "📅 Date de début",
                value=None,
                key="filter_date_debut_paiements"
            )
        with col_filter2:
            date_fin_paiements = st.date_input(
                "📅 Date de fin",
                value=None,
                key="filter_date_fin_paiements"
            )
        
        st.markdown("---")
        
        # Récupérer les commandes du user avec avance > 0 ET reste > 0 (via controller/model)
        try:
            commandes_avec_reste = commande_controller.lister_commandes_paiements_a_completer(
                couturier_id=couturier_id,
                salon_id=salon_id_user,
                date_debut=date_debut_paiements,
                date_fin=date_fin_paiements,
            )
        except Exception as e:
            st.error(f"❌ Erreur lors de la récupération des commandes : {e}")
            commandes_avec_reste = []
        
        if not commandes_avec_reste:
            st.info("📭 Aucune commande avec avance versée et reste à payer pour le moment.")
        else:
            commandes_avec_reste = _trier_commandes_urgentes(commandes_avec_reste)
            total_reste = sum(float(c.get("reste", 0) or 0) for c in commandes_avec_reste)
            st.info(
                f"💡 **{len(commandes_avec_reste)} commande(s)** à compléter, "
                f"pour un **reste total de {total_reste:,.0f} FCFA**."
            )
            st.caption("Code couleur global: 🔴 urgence forte | 🟠 à traiter rapidement | 🟢 stable")
            st.markdown(f"#### 📋 Liste des commandes ({len(commandes_avec_reste)})")
            
            # Afficher chaque commande avec possibilité de modification
            for idx, commande in enumerate(commandes_avec_reste):
                client_nom = commande.get('client_nom', '')
                client_prenom = commande.get('client_prenom', '')
                modele = commande.get('modele', 'N/A')
                
                with st.expander(
                    f"📦 Commande #{commande['id']} - {client_prenom} {client_nom} - {modele}",
                    expanded=False
                ):
                    _bandeau_urgence(commande)
                    # NOTE: Streamlit n'autorise pas les expanders imbriqués.
                    st.markdown("#### 💰 Informations de Paiement")
                    col_info1, col_info2, col_info3 = st.columns(3)
                    
                    with col_info1:
                        st.metric("Prix total", f"{commande['prix_total']:,.0f} FCFA")
                    with col_info2:
                        st.metric("Avance", f"{commande['avance']:,.0f} FCFA")
                    with col_info3:
                        pourcentage_reste = ((commande['reste']/commande['prix_total'])*100) if commande['prix_total'] > 0 else 0
                        st.metric("Reste à payer", f"{commande['reste']:,.0f} FCFA", 
                                 delta=f"{pourcentage_reste:.1f}%")
                    
                    st.markdown("---")
                    st.markdown("#### ✏️ Modifier les montants")
                    
                    # Calculer les valeurs initiales
                    reste_actuel = float(commande['reste'])  # Ce qui reste à verser
                    avance_actuelle = float(commande['avance'])  # Avance déjà versée
                    prix_total_actuel = float(commande['prix_total'])  # Prix total de la commande
                    
                    # Formulaire de modification
                    with st.form(f"form_modifier_prix_{commande['id']}", clear_on_submit=False):
                        col_edit1, col_edit2, col_edit3 = st.columns(3)
                        
                        with col_edit1:
                            # Prix total = reste actuel à verser
                            reste_a_verser = st.number_input(
                                "Reste à verser (FCFA) *",
                                min_value=0.0,
                                value=float(reste_actuel),
                                step=1000.0,
                                format="%.2f",
                                key=f"reste_verser_{commande['id']}",
                                help="Montant restant à payer"
                            )
                        
                        with col_edit2:
                            # Avance = nouvelle avance à ajouter (champ vide)
                            nouvelle_avance_ajoutee = st.number_input(
                                "Nouvelle avance (FCFA) *",
                                min_value=0.0,
                                max_value=float(reste_a_verser),
                                value=0.0,
                                step=1000.0,
                                format="%.2f",
                                key=f"avance_{commande['id']}",
                                help="Montant de la nouvelle avance à ajouter"
                            )
                            
                            # Afficher l'avance totale après ajout
                            avance_totale = avance_actuelle + nouvelle_avance_ajoutee
                            st.caption(f"💵 Avance totale après ajout : {avance_totale:,.0f} FCFA")
                        
                        with col_edit3:
                            # Reste à payer = calcul automatique
                            nouveau_reste = max(0.0, reste_a_verser - nouvelle_avance_ajoutee)
                            
                            st.markdown("**Reste à payer**")
                            st.metric("Montant restant", f"{nouveau_reste:,.0f} FCFA")
                            
                            if nouveau_reste == 0 and reste_a_verser > 0:
                                st.success("✅ Commande entièrement payée")
                            elif nouveau_reste < reste_a_verser:
                                pourcentage_paye = ((nouvelle_avance_ajoutee / reste_a_verser) * 100) if reste_a_verser > 0 else 0
                                st.caption(f"💳 {pourcentage_paye:.0f}% du reste sera payé")
                        
                        submit = st.form_submit_button("💾 Enregistrer les modifications", type="primary")
                        
                        if submit:
                            # Validation
                            if nouvelle_avance_ajoutee > reste_a_verser:
                                st.error("❌ La nouvelle avance ne peut pas être supérieure au reste à verser")
                            elif nouveau_reste < 0:
                                st.error("❌ Le reste ne peut pas être négatif")
                            else:
                                # Afficher un spinner pendant la mise à jour
                                with st.spinner("💾 Enregistrement des modifications..."):
                                    # Calculer les nouvelles valeurs
                                    nouvelle_avance_totale = avance_actuelle + nouvelle_avance_ajoutee
                                    nouveau_prix_total = prix_total_actuel  # Le prix total reste le même
                                    
                                    # Mettre à jour dans la base de données
                                    success = commande_model.modifier_prix_commande(
                                        commande['id'],
                                        nouveau_prix_total,
                                        nouvelle_avance_totale,
                                        nouveau_reste
                                    )
                                    
                                    # Mettre à jour le statut si nécessaire
                                    if success:
                                        try:
                                            # Si le reste est à 0, marquer comme "Terminé" (tout l'argent reçu)
                                            if nouveau_reste <= 0:
                                                commande_controller.mettre_a_jour_statut_si_soldee(
                                                    commande_id=commande['id'],
                                                    nouveau_reste=nouveau_reste,
                                                )
                                                st.info("💡 Commande marquée comme 'Terminée' (tout l'argent reçu). Vous pouvez maintenant demander la livraison dans l'onglet suivant.")
                                        except Exception as e:
                                            st.warning(f"⚠️ Les montants ont été mis à jour mais erreur lors de la mise à jour du statut : {e}")
                                
                                if success:
                                    st.success("✅ Modifications enregistrées avec succès !")
                                    st.success(f"💰 Prix total : {nouveau_prix_total:,.0f} FCFA | 💵 Avance totale : {nouvelle_avance_totale:,.0f} FCFA | 💸 Reste : {nouveau_reste:,.0f} FCFA")
                                    st.balloons()
                                    st.rerun()
                                else:
                                    st.error("❌ Erreur lors de l'enregistrement des modifications. Vérifiez les logs pour plus de détails.")
                                    st.error(f"Détails : Commande ID={commande['id']}, Prix={nouveau_prix_total}, Avance={nouvelle_avance_totale}, Reste={nouveau_reste}")
                    
                    st.markdown("---")
    
    # ========================================================================
    # ONGLET 2 : COMMANDES TERMINÉES (EN ATTENTE DE LIVRAISON)
    # ========================================================================
    with tab2:
        st.markdown("### ✅ Commandes terminées (en attente de livraison)")
        st.markdown("**Logique :** Une commande est **terminée** lorsque tout l'argent a été reçu (reste = 0). Elle passe en **livrée** uniquement lorsque l'administrateur du salon valide la commande dans son profil.")
        st.markdown("---")
        
        # Filtres de période
        col_filter1, col_filter2 = st.columns(2)
        with col_filter1:
            date_debut_terminees = st.date_input(
                "📅 Date de début",
                value=None,
                key="filter_date_debut_terminees"
            )
        with col_filter2:
            date_fin_terminees = st.date_input(
                "📅 Date de fin",
                value=None,
                key="filter_date_fin_terminees"
            )
        
        couturier_id_filter = None
        if is_admin_user and salon_id_user:
            from models.database import CouturierModel
            couturier_model = CouturierModel(st.session_state.db_connection)
            couturiers_salon = couturier_model.lister_tous_couturiers(salon_id=salon_id_user) or []
            
            options_couturiers = ["👥 Tous les couturiers"] + [
                f"{c['code_couturier']} - {c['prenom']} {c['nom']}"
                for c in couturiers_salon
            ]
            couturier_selectionne_terminees = st.selectbox(
                "👤 Filtrer par couturier (optionnel)",
                options=options_couturiers,
                key="filter_couturier_terminees"
            )
            if couturier_selectionne_terminees != "👥 Tous les couturiers":
                code_selectionne = couturier_selectionne_terminees.split(" - ")[0]
                couturier_obj = next(
                    (c for c in couturiers_salon if c['code_couturier'] == code_selectionne),
                    None
                )
                if couturier_obj:
                    couturier_id_filter = couturier_obj['id']
        
        st.markdown("---")
        
        # Récupérer les commandes terminées (reste = 0) mais pas encore livrées
        from models.database import CouturierModel
        couturier_model = CouturierModel(st.session_state.db_connection)
        
        # Récupérer les commandes selon le rôle (orchestration via controller)
        try:
            commandes_terminees = commande_controller.lister_commandes_terminees_pour_livraison(
                salon_id=salon_id_user,
                date_debut=date_debut_terminees,
                date_fin=date_fin_terminees,
                couturier_id=couturier_id,
                couturier_id_filter=couturier_id_filter,
                vue_admin=is_admin_user,
            )

            demandes = commande_model.lister_demandes_validation()
            if not is_admin_user and commandes_terminees:
                ids = [cmd["id"] for cmd in commandes_terminees]
                historique_counts = commande_controller.get_historique_demandes_par_commandes(
                    couturier_id=couturier_id,
                    commande_ids=ids,
                )
            else:
                historique_counts = {}

            for cmd in commandes_terminees:
                # lister_demandes_validation() ne renvoie que des lignes en_attente (filtre SQL)
                demande_existante = next(
                    (
                        d for d in demandes
                        if d.get("commande_id") == cmd["id"]
                        and d.get("type_action") == "fermeture_demande"
                    ),
                    None,
                )
                cmd["demande_existante"] = demande_existante
                if not is_admin_user:
                    cmd["demande_stats"] = historique_counts.get(
                        cmd["id"],
                        {"total": 0, "en_attente": 0, "validee": 0, "rejetee": 0},
                    )
        except Exception as e:
            st.error(f"❌ Erreur lors de la récupération des commandes : {e}")
            commandes_terminees = []
        
        if not commandes_terminees:
            st.info("📭 Aucune commande totalement payée pour le moment.")
        else:
            commandes_terminees = _trier_commandes_urgentes(commandes_terminees)
            st.markdown(f"#### 📋 Commandes totalement payées ({len(commandes_terminees)})")
            st.info("💡 Cliquez sur le bouton pour demander la livraison. La commande passera en attente de confirmation par l'administrateur.")
            st.caption("Tri automatique appliqué: les commandes les plus urgentes sont affichées en haut.")
            st.markdown("---")
            
            for commande in commandes_terminees:
                client_nom = commande.get('client_nom', '')
                client_prenom = commande.get('client_prenom', '')
                modele = commande.get('modele', 'N/A')
                demande_existante = commande.get('demande_existante')
                
                # Afficher le nom du couturier si admin
                couturier_info = ""
                if is_admin_user and commande.get('couturier_nom'):
                    couturier_info = f" - {commande.get('couturier_prenom', '')} {commande.get('couturier_nom', '')}"
                
                with st.expander(
                    f"📦 Commande #{commande['id']} - {client_prenom} {client_nom} - {modele}{couturier_info}",
                    expanded=True
                ):
                    _bandeau_urgence(commande)
                    col_d1, col_d2, col_d3 = st.columns(3)
                    
                    with col_d1:
                        st.metric("💰 Prix total", f"{commande['prix_total']:,.0f} FCFA")
                    with col_d2:
                        st.metric("💵 Avance", f"{commande['avance']:,.0f} FCFA")
                    with col_d3:
                        st.metric("💸 Reste", f"{commande['reste']:,.0f} FCFA")
                    st.caption(f"Statut actuel : **{_badge_statut(commande.get('statut', ''))}**")
                    
                    st.markdown("---")
                    
                    # Historique des demandes (employé)
                    total_demandes = 0
                    derniere_demande_status = None
                    try:
                        resume_demande = commande_controller.get_resume_demande_fermeture_commande(
                            commande_id=commande["id"],
                            couturier_id=couturier_id,
                        )
                        total_demandes = int(resume_demande.get("total", 0))
                        derniere_demande_status = resume_demande.get("dernier_statut")
                    except Exception:
                        total_demandes = 0
                        derniere_demande_status = None

                    if not is_admin_user:
                        if total_demandes > 0:
                            st.info(f"ℹ️ Vous avez déjà envoyé {total_demandes} demande(s) de fermeture.")
                            if derniere_demande_status:
                                st.caption(f"Dernier statut : {derniere_demande_status}")
                        else:
                            st.caption("Aucune demande de fermeture envoyée pour cette commande.")

                    # Actions selon le rôle
                    if is_admin_user:
                        # Admin : peut valider directement depuis cet onglet pour la rendre téléchargeable
                        if demande_existante:
                            st.warning(f"🟠 Demande de livraison en attente depuis : {demande_existante.get('date_creation', 'N/A')}")
                        else:
                            st.info("💡 Aucune demande de livraison pour cette commande. Vous pouvez valider directement ci-dessous.")

                        if st.button(
                            "✅ Valider et passer en 'Livré et payé' (PDF dispo)",
                            key=f"admin_valider_livraison_{commande['id']}",
                            type="primary",
                            use_container_width=True
                        ):
                            try:
                                success_validation = commande_controller.valider_commande_livree_payee(
                                    commande_id=commande["id"]
                                )
                                if not success_validation:
                                    st.error("❌ Erreur lors de la validation.")
                                    continue

                                st.success("✅ Commande validée. Elle apparaît désormais dans l'onglet PDF.")
                                
                                # Envoi d'un email de livraison terminée au client
                                commande_email = commande_model.obtenir_commande(commande["id"]) or {}
                                client_email = (
                                    commande_email.get("client_email")
                                    or commande.get("client_email")
                                )
                                if not client_email:
                                    st.warning("⚠️ Email de livraison non envoyé : adresse email du client manquante.")
                                else:
                                    salon_id_email = (
                                        commande_email.get("salon_id")
                                        or commande.get("salon_id")
                                        or salon_id_user
                                    )
                                    email_controller_envoi = email_controller
                                    try:
                                        salon_model_email = SalonModel(db)

                                        # Fallback robuste: retrouver le salon via couturier_id si salon_id absent
                                        if not salon_id_email and commande_email.get("couturier_id"):
                                            try:
                                                from models.database import CouturierModel
                                                couturier_model_email = CouturierModel(db)
                                                couturier_info = couturier_model_email.obtenir_couturier_par_id(
                                                    commande_email.get("couturier_id")
                                                )
                                                if couturier_info:
                                                    salon_id_email = couturier_info.get("salon_id")
                                            except Exception:
                                                salon_id_email = salon_id_user

                                        if salon_id_email:
                                            smtp_config_email = salon_model_email.obtenir_config_email_salon(salon_id_email) or {}
                                            salon_info_email = salon_model_email.obtenir_salon_by_id(salon_id_email) or {}

                                            # Compléter explicitement depuis la BDD si des champs SMTP sont vides
                                            smtp_user = (salon_info_email.get("smtp_user") or "").strip()
                                            smtp_password = salon_info_email.get("smtp_password")
                                            smtp_from = (salon_info_email.get("smtp_from") or "").strip()
                                            salon_email = (salon_info_email.get("email") or "").strip()
                                            smtp_host = (salon_info_email.get("smtp_host") or "").strip()
                                            smtp_port = salon_info_email.get("smtp_port")

                                            if smtp_host:
                                                smtp_config_email["host"] = smtp_host
                                            if smtp_port is not None and str(smtp_port).strip() != "":
                                                try:
                                                    smtp_config_email["port"] = int(smtp_port)
                                                except Exception:
                                                    pass

                                            smtp_config_email["user"] = smtp_config_email.get("user") or smtp_user or salon_email
                                            smtp_config_email["password"] = smtp_config_email.get("password") or smtp_password
                                            smtp_config_email["from_email"] = (
                                                smtp_config_email.get("from_email")
                                                or smtp_from
                                                or smtp_user
                                                or salon_email
                                            )
                                            smtp_config_email["enabled"] = True

                                            email_controller_envoi = EmailController(smtp_config=smtp_config_email)
                                        else:
                                            # Dernier fallback: lire la config SMTP du salon directement via la commande
                                            conn = db.get_connection()
                                            cursor = conn.cursor()
                                            try:
                                                cursor.execute(
                                                    """
                                                    SELECT
                                                        s.smtp_host,
                                                        s.smtp_port,
                                                        s.smtp_user,
                                                        s.smtp_password,
                                                        s.smtp_from,
                                                        s.smtp_use_tls,
                                                        s.smtp_use_ssl,
                                                        s.email
                                                    FROM commandes c
                                                    JOIN salons s ON s.salon_id = c.salon_id
                                                    WHERE c.id = %s
                                                    """,
                                                    (commande["id"],)
                                                )
                                                row = cursor.fetchone()
                                                if row:
                                                    smtp_config_email = {
                                                        "enabled": True,
                                                        "host": row[0],
                                                        "port": row[1],
                                                        "user": row[2] or row[7],
                                                        "password": row[3],
                                                        "from_email": row[4] or row[2] or row[7],
                                                        "use_tls": row[5],
                                                        "use_ssl": row[6],
                                                    }
                                                    email_controller_envoi = EmailController(smtp_config=smtp_config_email)
                                            finally:
                                                cursor.close()
                                    except Exception:
                                        email_controller_envoi = email_controller

                                    ok_config, msg_config = email_controller_envoi.verifier_configuration()
                                    if not ok_config:
                                        # Salon incomplet : tenter la config globale (.env / EMAIL_CONFIG)
                                        email_controller_envoi = EmailController(smtp_config=None)
                                        ok_config, msg_config = email_controller_envoi.verifier_configuration()
                                    if not ok_config:
                                        st.error(
                                            f"❌ Email de livraison non envoyé : {msg_config} "
                                            "(la commande est bien passée en « Livré et payé »)."
                                        )
                                    else:
                                        subject = f"Commande #{commande['id']} livrée et terminée"
                                        date_livraison = commande.get('date_livraison')
                                        date_livraison_txt = (
                                            date_livraison.strftime('%d/%m/%Y')
                                            if hasattr(date_livraison, 'strftime')
                                            else str(date_livraison) if date_livraison else "Non définie"
                                        )
                                        body = (
                                            f"Bonjour {commande.get('client_prenom', '')} {commande.get('client_nom', '')},\n\n"
                                            "Votre commande est maintenant livrée et terminée.\n\n"
                                            f"Commande: #{commande['id']}\n"
                                            f"Modèle: {commande.get('modele', 'N/A')}\n"
                                            f"Date de livraison: {date_livraison_txt}\n\n"
                                            "Merci pour votre confiance."
                                        )
                                        with st.spinner("📧 Envoi de l'email de livraison..."):
                                            attachments = []
                                            try:
                                                from controllers.pdf_controller import PDFController
                                                pdf_controller = PDFController(st.session_state.db_connection)
                                                commande_pdf = commande_email or commande_model.obtenir_commande(commande["id"])
                                                if commande_pdf:
                                                    commande_pdf["statut"] = "Livré et payé"
                                                    pdf_livraison_path = pdf_controller.generer_pdf_livraison(commande_pdf)
                                                    if pdf_livraison_path and os.path.exists(pdf_livraison_path):
                                                        attachments.append(pdf_livraison_path)
                                            except Exception:
                                                attachments = []

                                            succes, message = email_controller_envoi.envoyer_email_avec_message(
                                                client_email,
                                                subject,
                                                body,
                                                attachments=attachments
                                            )
                                        if succes:
                                            if attachments:
                                                st.success(f"✅ {message} PDF joint envoyé au client.")
                                            else:
                                                st.success(f"✅ {message}")
                                                st.warning("⚠️ Email envoyé sans PDF joint (génération du PDF indisponible).")
                                        else:
                                            st.error(f"❌ Email de livraison non envoyé : {message}")
                                st.rerun()
                            except Exception as e:
                                st.error(f"❌ Erreur lors de la validation : {e}")
                    else:
                        # Employé : peut demander la livraison
                        demande_stats = commande.get('demande_stats', {})
                        total_demandes = demande_stats.get('total', 0)
                        en_attente = demande_stats.get('en_attente', 0)
                        validee = demande_stats.get('validee', 0)
                        rejetee = demande_stats.get('rejetee', 0)

                        if total_demandes > 0:
                            st.info(
                                f"📊 Historique des demandes : "
                                f"{total_demandes} au total | "
                                f"🟠 en attente: {en_attente} | "
                                f"✅ validées: {validee} | "
                                f"❌ rejetées: {rejetee}"
                            )
                        else:
                            st.caption("📊 Aucune demande de fermeture envoyée pour cette commande.")

                        if demande_existante:
                            # Demande déjà envoyée
                            st.warning(
                                "🟠 Demande de livraison en attente de confirmation. "
                                "Votre demande est en attente de validation par l'administrateur."
                            )
                            if demande_existante.get('date_creation'):
                                st.caption(f"📅 Demande envoyée le : {demande_existante.get('date_creation')}")
                        else:
                            # Pas encore de demande - afficher le bouton
                            if commande.get('reste', 0) > 0.01:
                                st.warning(f"⚠️ Le reste à payer est de {commande['reste']:,.0f} FCFA. Veuillez d'abord modifier le paiement dans l'onglet précédent.")
                            else:
                                # Bouton pour demander la livraison (état = non envoyée)
                                button_key = f"demander_livraison_{commande['id']}"
                                if st.button(
                                    "📤 Demande non envoyée (cliquer pour envoyer)",
                                    key=button_key,
                                    use_container_width=True,
                                    type="primary"
                                ):
                                    # Créer la demande de livraison
                                    with st.spinner("🔄 Envoi de la demande de livraison..."):
                                        try:
                                            result = commande_model.demander_fermeture(
                                                commande['id'],
                                                couturier_id,
                                                "Demande de livraison de la commande"
                                            )

                                            result_id = None
                                            created = True
                                            if isinstance(result, dict):
                                                result_id = result.get("id")
                                                created = bool(result.get("created", False))
                                            elif isinstance(result, int):
                                                result_id = result
                                                created = True

                                            if result_id:
                                                if created:
                                                    st.success(
                                                        f"🟢 Demande envoyée avec succès (ID: {result_id}) "
                                                        f"pour la commande {commande['id']}"
                                                    )
                                                    st.caption("État : envoyée, la ligne va disparaître.")
                                                    st.balloons()
                                                else:
                                                    st.warning(
                                                        f"⚠️ Une demande de fermeture existe déjà pour la commande "
                                                        f"{commande['id']} (ID demande: {result_id})"
                                                    )
                                                    st.caption("État : déjà envoyée, la ligne va disparaître.")
                                                st.rerun()

                                            # Fallback robuste : vérifier si une demande en attente existe maintenant
                                            demandes_apres = commande_model.lister_demandes_validation() or []
                                            deja_en_attente = next(
                                                (
                                                    d for d in demandes_apres
                                                    if d.get("commande_id") == commande["id"]
                                                    and d.get("type_action") == "fermeture_demande"
                                                    and d.get("statut_validation") == "en_attente"
                                                ),
                                                None,
                                            )
                                            if deja_en_attente:
                                                st.warning(
                                                    f"⚠️ Une demande existe déjà (ID: {deja_en_attente.get('id')})."
                                                )
                                                st.caption("État : déjà envoyée, la ligne va disparaître.")
                                                st.rerun()

                                            st.error(
                                                "❌ Demande non envoyée. Vérifiez que la commande est totalement soldée "
                                                "et réessayez."
                                            )
                                            st.caption("État : échec")
                                        except Exception as e:
                                            st.error(f"❌ Erreur : {e}")
                                else:
                                    st.info("💡 État actuel : demande non envoyée.")
                    if commande.get("statut"):
                        st.caption(f"État commande : **{_badge_statut(commande.get('statut'))}**")
    
    # ========================================================================
    # ONGLET 3 : TÉLÉCHARGER PDFs DES COMMANDES VALIDÉES
    # ========================================================================
    with tab3:
        st.markdown("### 📄 Télécharger les PDFs des commandes validées")
        st.markdown("**Fonctionnalité :** Téléchargez les PDFs des commandes qui ont été **validées par l'administrateur** (statut : Livré et payé). Le PDF indique que la commande est **livrée et terminée**.")
        st.caption("Seules les commandes au statut **Livré et payé** sont affichées ici.")
        st.markdown("---")
        
        # Filtres
        col_filter1, col_filter2, col_filter3 = st.columns(3)
        
        with col_filter1:
            date_debut = st.date_input(
                "📅 Date de début",
                value=None,
                key="filter_date_debut_cloture"
            )
        
        with col_filter2:
            date_fin = st.date_input(
                "📅 Date de fin",
                value=None,
                key="filter_date_fin_cloture"
            )
        
        with col_filter3:
            nom_client_filter = st.text_input(
                "🔍 Nom du client (optionnel)",
                value="",
                key="filter_nom_client_cloture",
                placeholder="Rechercher par nom ou prénom"
            )
        
        couturier_id_filter = None
        if is_admin_user and salon_id_user:
            from models.database import CouturierModel
            couturier_model = CouturierModel(st.session_state.db_connection)
            couturiers_salon = couturier_model.lister_tous_couturiers(salon_id=salon_id_user) or []
            
            options_couturiers = ["👥 Tous les couturiers"] + [
                f"{c['code_couturier']} - {c['prenom']} {c['nom']}"
                for c in couturiers_salon
            ]
            couturier_selectionne_pdf = st.selectbox(
                "👤 Filtrer par couturier (optionnel)",
                options=options_couturiers,
                key="filter_couturier_pdf_cloture"
            )
            if couturier_selectionne_pdf != "👥 Tous les couturiers":
                code_selectionne = couturier_selectionne_pdf.split(" - ")[0]
                couturier_obj = next(
                    (c for c in couturiers_salon if c['code_couturier'] == code_selectionne),
                    None
                )
                if couturier_obj:
                    couturier_id_filter = couturier_obj['id']
        
        st.markdown("---")
        
        # Récupérer les commandes terminées selon le rôle (Terminé ou Livré et payé)
        commandes_terminees = []
        try:
            commandes_terminees = commande_controller.lister_commandes_livrees_pour_pdf(
                salon_id=salon_id_user,
                couturier_id=couturier_id,
                vue_admin=is_admin_user,
                date_debut=date_debut,
                date_fin=date_fin,
                nom_client_filter=nom_client_filter,
                couturier_id_filter=couturier_id_filter,
            )
        except Exception as e:
            st.error(f"❌ Erreur lors de la récupération des commandes terminées : {e}")
            commandes_terminees = []
        
        # Afficher le nombre de commandes trouvées
        st.caption(f"🔍 {len(commandes_terminees)} commande(s) terminée(s) trouvée(s)")
        
        if not commandes_terminees:
            st.warning("📭 Aucune commande validée pour le moment.")
            st.info("💡 Seules les commandes avec le statut 'Livré et payé' (validées par l'administrateur) apparaissent ici.")
            if date_debut or date_fin or nom_client_filter:
                st.info(f"💡 Filtres appliqués : Date début={date_debut}, Date fin={date_fin}, Nom client='{nom_client_filter}'")
        else:
            commandes_terminees = _trier_commandes_urgentes(commandes_terminees)
            total_ca_pdf = sum(float(c.get("prix_total", 0) or 0) for c in commandes_terminees)
            st.success(f"✅ {len(commandes_terminees)} commande(s) validée(s) trouvée(s)")
            st.info(f"📊 Montant cumulé des commandes listées : **{total_ca_pdf:,.0f} FCFA**")
            st.caption("Tri automatique appliqué: priorité visuelle rouge/orange/vert.")
            st.markdown(f"#### 📋 Commandes validées (Livré et payé) ({len(commandes_terminees)})")
            
            for commande in commandes_terminees:
                client_nom = commande.get('client_nom', '')
                client_prenom = commande.get('client_prenom', '')
                modele = commande.get('modele', 'N/A')
                
                # Afficher le nom du couturier si admin
                couturier_info = ""
                if is_admin_user and commande.get('couturier_nom'):
                    couturier_info = f" - {commande.get('couturier_prenom', '')} {commande.get('couturier_nom', '')}"
                
                with st.expander(
                    f"📦 Commande #{commande['id']} - {client_prenom} {client_nom} - {modele}{couturier_info}",
                    expanded=True
                ):
                    _bandeau_urgence(commande)
                    # Informations principales du client
                    st.markdown("### 👤 Informations Client")
                    col_client1, col_client2 = st.columns(2)
                    with col_client1:
                        st.markdown(f"**Nom complet:** {client_prenom} {client_nom}")
                        st.markdown(f"**Téléphone:** {commande.get('client_telephone', 'Non renseigné')}")
                    with col_client2:
                        st.markdown(f"**Email:** {commande.get('client_email', 'Non renseigné')}")
                        if commande.get('date_livraison'):
                            date_liv = commande['date_livraison']
                            if hasattr(date_liv, 'strftime'):
                                st.markdown(f"**Date de livraison:** {date_liv.strftime('%d/%m/%Y')}")
                            else:
                                st.markdown(f"**Date de livraison:** {date_liv}")
                    
                    st.markdown("---")
                    
                    # Informations de paiement
                    st.markdown("### 💰 Informations de Paiement")
                    col_paiement1, col_paiement2, col_paiement3 = st.columns(3)
                    
                    with col_paiement1:
                        st.metric("Prix total", f"{commande['prix_total']:,.0f} FCFA")
                    with col_paiement2:
                        st.metric("Avance", f"{commande['avance']:,.0f} FCFA")
                    with col_paiement3:
                        pourcentage_reste = ((commande['reste']/commande['prix_total'])*100) if commande['prix_total'] > 0 else 0
                        st.metric("Reste", f"{commande['reste']:,.0f} FCFA", 
                                 delta=f"{pourcentage_reste:.1f}%")
                    
                    st.markdown("---")
                    
                    # Dates et Statut
                    col_date1, col_date2 = st.columns(2)
                    with col_date1:
                        date_creation = commande.get('date_creation')
                        if date_creation:
                            if hasattr(date_creation, 'strftime'):
                                st.markdown(f"**Date de commande:** {date_creation.strftime('%d/%m/%Y à %H:%M')}")
                            else:
                                st.markdown(f"**Date de commande:** {date_creation}")
                    with col_date2:
                        st.markdown(f"**Statut:** {_badge_statut(commande.get('statut', ''))}")
                    
                    st.markdown("---")
                    
                    # Section Télécharger PDF
                    st.markdown("### 📥 Télécharger le PDF de la commande")
                    commande_id = commande['id']
                    
                    # Informations sur le statut
                    statut_commande = commande.get('statut', '')
                    if statut_commande == 'Livré et payé':
                        st.success("✅ Commande **livrée et terminée** - PDF disponible")
                    elif statut_commande == 'Terminé':
                        st.info("ℹ️ Commande **terminée** - PDF disponible (indique livrée et terminée)")
                    
                    # Générer le PDF automatiquement et afficher le bouton de téléchargement
                    try:
                        pdf_path = commande.get("pdf_path")
                        if pdf_path and os.path.exists(pdf_path):
                            with open(pdf_path, "rb") as pdf_file:
                                pdf_bytes = pdf_file.read()
                        else:
                            # Fallback : régénération si le fichier n'est pas présent sur disque
                            commande_complete = commande_model.obtenir_commande(commande_id)
                            if not commande_complete:
                                st.error("❌ Impossible de récupérer les données de la commande")
                                continue

                            from controllers.pdf_controller import PDFController
                            pdf_controller = PDFController(st.session_state.db_connection)
                            commande_complete['statut'] = 'Livré et payé'
                            pdf_path = pdf_controller.generer_pdf_commande(commande_complete)
                            if not pdf_path or not os.path.exists(pdf_path):
                                st.error("❌ Erreur lors de la génération du PDF")
                                continue
                            with open(pdf_path, "rb") as pdf_file:
                                pdf_bytes = pdf_file.read()

                        st.download_button(
                            label="📥 Télécharger le PDF (Commande livrée et terminée)",
                            data=pdf_bytes,
                            file_name=f"Commande_{commande_id}_Livree_Terminee.pdf",
                            mime="application/pdf",
                            use_container_width=True,
                            key=f"download_pdf_terminée_{commande_id}",
                            type="primary"
                        )
                        st.caption("💡 Le PDF indique que la commande est **livrée et terminée**")
                    except Exception as e:
                        st.error(f"❌ Erreur lors de la génération du PDF : {e}")
                        import traceback
                        st.code(traceback.format_exc())
                    
                    st.markdown("---")
