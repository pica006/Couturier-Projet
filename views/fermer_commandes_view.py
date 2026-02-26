"""
Vue pour permettre aux employés de fermer leurs commandes
"""
import streamlit as st
import os
from models.database import CommandeModel
from controllers.email_controller import EmailController
from models.salon_model import SalonModel
from utils.role_utils import obtenir_salon_id
from utils.role_utils import obtenir_couturier_id, obtenir_salon_id, est_admin


def afficher_page_fermer_commandes():
    """Page permettant aux employés de fermer leurs commandes"""
    
    # En-tête encadré standardisé
    from utils.page_header import afficher_header_page
    afficher_header_page("🔒 Fermer mes commandes", "Gérez les paiements et demandez la fermeture de vos commandes")
    
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
    commande_model = CommandeModel(db)

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
    
    # ========================================================================
    # ONGLET 1 : MODIFIER LES PAIEMENTS (Commandes avec avance)
    # ========================================================================
    with tab1:
        st.markdown("### 💰 Modifier les paiements")
        st.markdown("Liste de vos commandes où une avance a été versée. Vous pouvez modifier directement le prix total, l'avance et le reste à payer.")
        
        # Bouton de rafraîchissement
        col_refresh, _ = st.columns([1, 5])
        with col_refresh:
            if st.button("🔄 Actualiser", key="refresh_commandes_paiement", width='stretch'):
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
        
        # Récupérer les commandes du user avec avance > 0 ET reste > 0
        try:
            cursor = st.session_state.db_connection.get_connection().cursor()
            query = """
                SELECT c.id, c.modele, c.prix_total, c.avance, c.reste, c.statut, 
                       c.date_creation, c.date_livraison,
                       cl.nom, cl.prenom
                FROM commandes c
                JOIN clients cl ON c.client_id = cl.id
                JOIN couturiers co ON c.couturier_id = co.id
                WHERE c.couturier_id = %s 
                  AND co.salon_id = %s
                  AND c.statut != 'Fermé'
                  AND c.avance > 0
                  AND c.reste > 0
            """
            params = [couturier_id, salon_id_user]
            
            db_type = st.session_state.db_connection.db_type
            if date_debut_paiements:
                if db_type == 'mysql':
                    query += " AND DATE(c.date_creation) >= %s"
                else:
                    query += " AND c.date_creation::date >= %s"
                params.append(date_debut_paiements)
            if date_fin_paiements:
                if db_type == 'mysql':
                    query += " AND DATE(c.date_creation) <= %s"
                else:
                    query += " AND c.date_creation::date <= %s"
                params.append(date_fin_paiements)
            
            query += " ORDER BY c.date_creation DESC"
            cursor.execute(query, tuple(params))
            results = cursor.fetchall()
            cursor.close()
            
            commandes_avec_reste = []
            for row in results:
                commandes_avec_reste.append({
                    'id': row[0],
                    'modele': row[1],
                    'prix_total': float(row[2]),
                    'avance': float(row[3]),
                    'reste': float(row[4]),
                    'statut': row[5],
                    'date_creation': row[6],
                    'date_livraison': row[7],
                    'client_nom': row[8],
                    'client_prenom': row[9]
                })
        except Exception as e:
            st.error(f"❌ Erreur lors de la récupération des commandes : {e}")
            commandes_avec_reste = []
        
        if not commandes_avec_reste:
            st.info("📭 Aucune commande avec avance versée et reste à payer pour le moment.")
        else:
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
                    # Affichage des informations de paiement comme dans "mes commandes"
                    with st.expander("💰 Informations de Paiement", expanded=True):
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
                            st.markdown(f"### <span style='color: #F39C12; font-size: 1.5em; font-weight: bold;'>{nouveau_reste:,.0f} FCFA</span>", unsafe_allow_html=True)
                            
                            if nouveau_reste == 0 and reste_a_verser > 0:
                                st.success("✅ Commande entièrement payée")
                            elif nouveau_reste < reste_a_verser:
                                pourcentage_paye = ((nouvelle_avance_ajoutee / reste_a_verser) * 100) if reste_a_verser > 0 else 0
                                st.caption(f"💳 {pourcentage_paye:.0f}% du reste sera payé")
                        
                        submit = st.form_submit_button("💾 Enregistrer les modifications", type="primary", width='stretch')
                        
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
                                            connection = st.session_state.db_connection.get_connection()
                                            cursor = connection.cursor()
                                            # Si le reste est à 0, marquer comme "Terminé" (tout l'argent reçu)
                                            if nouveau_reste <= 0:
                                                cursor.execute(
                                                    "UPDATE commandes SET statut = 'Terminé' WHERE id = %s",
                                                    (commande['id'],)
                                                )
                                                st.info("💡 Commande marquée comme 'Terminée' (tout l'argent reçu). Vous pouvez maintenant demander la livraison dans l'onglet suivant.")
                                            connection.commit()
                                            cursor.close()
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
            couturiers_salon = couturier_model.lister_tous_couturiers(salon_id=salon_id_user)
            
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
        
        # Récupérer les commandes selon le rôle
        if is_admin_user:
            # Admin : voir toutes les commandes terminées du salon (reste = 0, statut = 'Terminé')
            if salon_id_user:
                try:
                    cursor = st.session_state.db_connection.get_connection().cursor()
                    query = """
                        SELECT c.id, c.modele, c.prix_total, c.avance, c.reste, c.statut, 
                               c.date_creation, c.date_livraison,
                               cl.nom, cl.prenom, cl.email, c.couturier_id,
                               co.nom as couturier_nom, co.prenom as couturier_prenom
                        FROM commandes c
                        JOIN clients cl ON c.client_id = cl.id
                        LEFT JOIN couturiers co ON c.couturier_id = co.id
                        WHERE co.salon_id = %s 
                          AND c.reste <= 0
                          AND c.statut = 'Terminé'
                    """
                    params = [salon_id_user]
                    
                    db_type = st.session_state.db_connection.db_type
                    if date_debut_terminees:
                        if db_type == 'mysql':
                            query += " AND DATE(c.date_creation) >= %s"
                        else:
                            query += " AND c.date_creation::date >= %s"
                        params.append(date_debut_terminees)
                    if date_fin_terminees:
                        if db_type == 'mysql':
                            query += " AND DATE(c.date_creation) <= %s"
                        else:
                            query += " AND c.date_creation::date <= %s"
                        params.append(date_fin_terminees)
                    if couturier_id_filter:
                        query += " AND c.couturier_id = %s"
                        params.append(couturier_id_filter)
                    
                    query += " ORDER BY c.date_creation DESC"
                    cursor.execute(query, tuple(params))
                    results = cursor.fetchall()
                    cursor.close()

                    commandes_terminees = []
                    for row in results:
                        commandes_terminees.append({
                            'id': row[0],
                            'modele': row[1],
                            'prix_total': float(row[2]),
                            'avance': float(row[3]),
                            'reste': float(row[4]),
                            'statut': row[5],
                            'date_creation': row[6],
                            'date_livraison': row[7],
                            'client_nom': row[8],
                            'client_prenom': row[9],
                            'client_email': row[10],
                            'couturier_id': row[11],
                            'couturier_nom': row[12],
                            'couturier_prenom': row[13]
                        })

                    # Vérifier les demandes existantes pour chaque commande
                    demandes = commande_model.lister_demandes_validation()
                    for cmd in commandes_terminees:
                        demande_existante = next(
                            (
                                d for d in demandes
                                if d.get('commande_id') == cmd['id']
                                and d.get('type_action') == 'fermeture_demande'
                                and d.get('statut_validation') == 'en_attente'
                            ),
                            None
                        )
                        cmd['demande_existante'] = demande_existante
                except Exception as e:
                    st.error(f"❌ Erreur lors de la récupération des commandes : {e}")
                    commandes_terminees = []
            else:
                commandes_terminees = []
        else:
            # Employé : voir toutes ses commandes totalement payées (reste = 0, statut = 'Terminé')
            try:
                cursor = st.session_state.db_connection.get_connection().cursor()
                query = """
                    SELECT c.id, c.modele, c.prix_total, c.avance, c.reste, c.statut, 
                           c.date_creation, c.date_livraison,
                           cl.nom, cl.prenom
                    FROM commandes c
                    JOIN clients cl ON c.client_id = cl.id
                    JOIN couturiers co ON c.couturier_id = co.id
                    WHERE c.couturier_id = %s 
                      AND co.salon_id = %s
                      AND c.reste <= 0
                      AND c.statut = 'Terminé'
                """
                params = [couturier_id, salon_id_user]
                
                db_type = st.session_state.db_connection.db_type
                if date_debut_terminees:
                    if db_type == 'mysql':
                        query += " AND DATE(c.date_creation) >= %s"
                    else:
                        query += " AND c.date_creation::date >= %s"
                    params.append(date_debut_terminees)
                if date_fin_terminees:
                    if db_type == 'mysql':
                        query += " AND DATE(c.date_creation) <= %s"
                    else:
                        query += " AND c.date_creation::date <= %s"
                    params.append(date_fin_terminees)
                if couturier_id_filter:
                    query += " AND c.couturier_id = %s"
                    params.append(couturier_id_filter)
                
                query += " ORDER BY c.date_creation DESC"
                cursor.execute(query, tuple(params))
                results = cursor.fetchall()
                cursor.close()

                commandes_terminees = []
                for row in results:
                    commandes_terminees.append({
                        'id': row[0],
                        'modele': row[1],
                        'prix_total': float(row[2]),
                        'avance': float(row[3]),
                        'reste': float(row[4]),
                        'statut': row[5],
                        'date_creation': row[6],
                        'date_livraison': row[7],
                        'client_nom': row[8],
                        'client_prenom': row[9]
                    })

                # Vérifier les demandes existantes + historique des demandes pour chaque commande
                demandes = commande_model.lister_demandes_validation()
                historique_counts = {}
                if commandes_terminees:
                    try:
                        ids = [cmd['id'] for cmd in commandes_terminees]
                        placeholders = ", ".join(["%s"] * len(ids))
                        hist_query = f"""
                            SELECT commande_id,
                                   COUNT(*) as total,
                                   SUM(CASE WHEN statut_validation = 'en_attente' THEN 1 ELSE 0 END) as en_attente,
                                   SUM(CASE WHEN statut_validation = 'validee' THEN 1 ELSE 0 END) as validee,
                                   SUM(CASE WHEN statut_validation = 'rejetee' THEN 1 ELSE 0 END) as rejetee
                            FROM historique_commandes
                            WHERE couturier_id = %s
                              AND type_action = 'fermeture_demande'
                              AND commande_id IN ({placeholders})
                            GROUP BY commande_id
                        """
                        cursor = st.session_state.db_connection.get_connection().cursor()
                        cursor.execute(hist_query, tuple([couturier_id] + ids))
                        for row in cursor.fetchall():
                            historique_counts[row[0]] = {
                                'total': int(row[1] or 0),
                                'en_attente': int(row[2] or 0),
                                'validee': int(row[3] or 0),
                                'rejetee': int(row[4] or 0),
                            }
                        cursor.close()
                    except Exception as e:
                        st.warning(f"⚠️ Impossible de charger l'historique des demandes : {e}")

                for cmd in commandes_terminees:
                    demande_existante = next(
                        (
                            d for d in demandes
                            if d.get('commande_id') == cmd['id']
                            and d.get('type_action') == 'fermeture_demande'
                            and d.get('statut_validation') == 'en_attente'
                        ),
                        None
                    )
                    cmd['demande_existante'] = demande_existante
                    cmd['demande_stats'] = historique_counts.get(cmd['id'], {
                        'total': 0,
                        'en_attente': 0,
                        'validee': 0,
                        'rejetee': 0,
                    })
            except Exception as e:
                st.error(f"❌ Erreur lors de la récupération des commandes : {e}")
                commandes_terminees = []
        
        if not commandes_terminees:
            st.info("📭 Aucune commande totalement payée pour le moment.")
        else:
            st.markdown(f"#### 📋 Commandes totalement payées ({len(commandes_terminees)})")
            st.info("💡 Cliquez sur le bouton pour demander la livraison. La commande passera en attente de confirmation par l'administrateur.")
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
                    col_d1, col_d2, col_d3 = st.columns(3)
                    
                    with col_d1:
                        st.metric("💰 Prix total", f"{commande['prix_total']:,.0f} FCFA")
                    with col_d2:
                        st.metric("💵 Avance", f"{commande['avance']:,.0f} FCFA")
                    with col_d3:
                        st.metric("💸 Reste", f"{commande['reste']:,.0f} FCFA")
                    
                    st.markdown("---")
                    
                    # Historique des demandes (employé)
                    total_demandes = 0
                    derniere_demande_status = None
                    try:
                        cursor = st.session_state.db_connection.get_connection().cursor()
                        cursor.execute(
                            """
                            SELECT COUNT(*), MAX(statut_validation)
                            FROM historique_commandes
                            WHERE commande_id = %s
                              AND couturier_id = %s
                              AND type_action = 'fermeture_demande'
                            """,
                            (commande['id'], couturier_id),
                        )
                        row = cursor.fetchone()
                        cursor.close()
                        if row:
                            total_demandes = int(row[0] or 0)
                            derniere_demande_status = row[1]
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
                            width='stretch'
                        ):
                            try:
                                connection = st.session_state.db_connection.get_connection()
                                cursor = connection.cursor()
                                cursor.execute(
                                    "UPDATE commandes SET statut = 'Livré et payé', date_fermeture = NOW() WHERE id = %s",
                                    (commande['id'],)
                                )
                                connection.commit()
                                cursor.close()
                                st.success("✅ Commande validée. Elle apparaît désormais dans l'onglet PDF.")
                                
                                # Envoi d'un email de livraison terminée au client
                                client_email = commande.get('client_email')
                                if not client_email:
                                    st.warning("⚠️ Email de livraison non envoyé : adresse email du client manquante.")
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
                                        succes, message = email_controller.envoyer_email_avec_message(
                                            client_email,
                                            subject,
                                            body
                                        )
                                    if succes:
                                        st.success(f"✅ {message}")
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
                            # Demande déjà envoyée - afficher en orange
                            st.markdown("""
                                <div style='background-color: #FFA500; padding: 1rem; border-radius: 8px; color: white; text-align: center;'>
                                    <strong>🟠 Demande de livraison en attente de confirmation</strong><br>
                                    Votre demande a été envoyée et est en attente de validation par l'administrateur.
                                </div>
                            """, unsafe_allow_html=True)
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
                                    width='stretch',
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
                                            
                                            if result and result.get("id"):
                                                if result.get("created", False):
                                                    st.success(f"🟢 Demande envoyée avec succès (ID: {result['id']}) pour la commande {commande['id']}")
                                                    st.caption("État : envoyée, la ligne va disparaître.")
                                                    st.balloons()
                                                    st.rerun()
                                                else:
                                                    st.warning(f"⚠️ Une demande de fermeture existe déjà pour la commande {commande['id']} (ID demande: {result['id']})")
                                                    st.caption("État : déjà envoyée, la ligne va disparaître.")
                                                    st.rerun()
                                            else:
                                                st.error("❌ Demande non envoyée (aucun ID retourné).")
                                                st.caption("État : échec")
                                        except Exception as e:
                                            st.error(f"❌ Erreur : {e}")
                                else:
                                    st.info("💡 État actuel : demande non envoyée.")
    
    # ========================================================================
    # ONGLET 3 : TÉLÉCHARGER PDFs DES COMMANDES VALIDÉES
    # ========================================================================
    with tab3:
        st.markdown("### 📄 Télécharger les PDFs des commandes validées")
        st.markdown("**Fonctionnalité :** Téléchargez les PDFs des commandes qui ont été **validées par l'administrateur** (statut : Livré et payé). Le PDF indique que la commande est **livrée et terminée**.")
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
            couturiers_salon = couturier_model.lister_tous_couturiers(salon_id=salon_id_user)
            
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
            cursor = st.session_state.db_connection.get_connection().cursor()
            
            if is_admin_user and salon_id_user:
                # Admin : voir toutes les commandes validées du salon (Livré et payé uniquement)
                query = """
                    SELECT c.id, c.modele, c.prix_total, c.avance, c.reste, c.statut, 
                           c.date_creation, c.date_livraison,
                           cl.nom, cl.prenom, cl.telephone, cl.email,
                           c.couturier_id,
                           co.nom as couturier_nom, co.prenom as couturier_prenom,
                           c.pdf_name, c.pdf_path
                    FROM commandes c
                    JOIN clients cl ON c.client_id = cl.id
                    LEFT JOIN couturiers co ON c.couturier_id = co.id
                    WHERE co.salon_id = %s 
                      AND c.statut = 'Livré et payé'
                """
                params = [salon_id_user]
            else:
                # Employé : voir uniquement ses propres commandes validées (Livré et payé uniquement)
                query = """
                    SELECT c.id, c.modele, c.prix_total, c.avance, c.reste, c.statut, 
                           c.date_creation, c.date_livraison,
                           cl.nom, cl.prenom, cl.telephone, cl.email,
                           c.pdf_name, c.pdf_path
                    FROM commandes c
                    JOIN clients cl ON c.client_id = cl.id
                    JOIN couturiers co ON c.couturier_id = co.id
                    WHERE c.couturier_id = %s 
                      AND co.salon_id = %s
                      AND c.statut = 'Livré et payé'
                """
                params = [couturier_id, salon_id_user]
            
            # Ajouter les filtres (adapter selon le SGBD)
            db_type = st.session_state.db_connection.db_type
            if date_debut:
                if db_type == 'mysql':
                    query += " AND DATE(c.date_creation) >= %s"
                else:  # PostgreSQL
                    query += " AND c.date_creation::date >= %s"
                params.append(date_debut)
            
            if date_fin:
                if db_type == 'mysql':
                    query += " AND DATE(c.date_creation) <= %s"
                else:  # PostgreSQL
                    query += " AND c.date_creation::date <= %s"
                params.append(date_fin)
            
            if nom_client_filter:
                query += " AND (cl.nom LIKE %s OR cl.prenom LIKE %s)"
                params.append(f"%{nom_client_filter}%")
                params.append(f"%{nom_client_filter}%")
            
            if is_admin_user and couturier_id_filter:
                query += " AND c.couturier_id = %s"
                params.append(couturier_id_filter)
            
            query += " ORDER BY c.date_creation DESC"
            
            cursor.execute(query, tuple(params))
            results = cursor.fetchall()
            cursor.close()
            
            commandes_terminees = []
            for row in results:
                if is_admin_user and salon_id_user:
                    commandes_terminees.append({
                        'id': row[0],
                        'modele': row[1],
                        'prix_total': float(row[2]),
                        'avance': float(row[3]),
                        'reste': float(row[4]),
                        'statut': row[5],
                        'date_creation': row[6],
                        'date_livraison': row[7],
                        'client_nom': row[8],
                        'client_prenom': row[9],
                        'client_telephone': row[10],
                        'client_email': row[11],
                        'couturier_id': row[12],
                        'couturier_nom': row[13],
                        'couturier_prenom': row[14],
                        'pdf_name': row[15] if len(row) > 15 else None,
                        'pdf_path': row[16] if len(row) > 16 else None
                    })
                else:
                    commandes_terminees.append({
                        'id': row[0],
                        'modele': row[1],
                        'prix_total': float(row[2]),
                        'avance': float(row[3]),
                        'reste': float(row[4]),
                        'statut': row[5],
                        'date_creation': row[6],
                        'date_livraison': row[7],
                        'client_nom': row[8],
                        'client_prenom': row[9],
                        'client_telephone': row[10],
                        'client_email': row[11],
                        'pdf_name': row[12] if len(row) > 12 else None,
                        'pdf_path': row[13] if len(row) > 13 else None
                    })
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
            st.success(f"✅ {len(commandes_terminees)} commande(s) validée(s) trouvée(s)")
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
                        st.markdown(f"**Statut:** ✅ {commande['statut']}")
                    
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
                        # Récupérer les données complètes de la commande
                        commande_complete = commande_model.obtenir_commande(commande_id)
                        
                        if commande_complete:
                            from controllers.pdf_controller import PDFController
                            pdf_controller = PDFController(st.session_state.db_connection)
                            
                            # S'assurer que le statut indique "Livré et payé" dans le PDF
                            # Le PDF affichera toujours "Livré et payé" pour indiquer que la commande est livrée et terminée
                            commande_complete['statut'] = 'Livré et payé'
                            
                            # Générer le PDF
                            pdf_path = pdf_controller.generer_pdf_commande(commande_complete)
                            
                            if pdf_path and os.path.exists(pdf_path):
                                with open(pdf_path, "rb") as pdf_file:
                                    pdf_bytes = pdf_file.read()
                                
                                # Afficher le bouton de téléchargement
                                st.download_button(
                                    label="📥 Télécharger le PDF (Commande livrée et terminée)",
                                    data=pdf_bytes,
                                    file_name=f"Commande_{commande_id}_Livree_Terminee.pdf",
                                    mime="application/pdf",
                                    width='stretch',
                                    key=f"download_pdf_terminée_{commande_id}",
                                    type="primary"
                                )
                                st.caption("💡 Le PDF indique que la commande est **livrée et terminée**")
                            else:
                                st.error("❌ Erreur lors de la génération du PDF")
                        else:
                            st.error("❌ Impossible de récupérer les données de la commande")
                    except Exception as e:
                        st.error(f"❌ Erreur lors de la génération du PDF : {e}")
                        import traceback
                        st.code(traceback.format_exc())
                    
                    st.markdown("---")
