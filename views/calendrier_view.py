"""
================================================================================
PAGE UNIFIÉE : MODÈLES RÉALISÉS + CALENDRIER
================================================================================
Onglet 1 : Modèles réalisés par le salon
Onglet 2 : Calendrier des livraisons avec rappels automatiques
"""

import streamlit as st
import pandas as pd
import io
from datetime import datetime, timedelta
from collections import defaultdict

from models.database import CommandeModel, CouturierModel
from utils.role_utils import est_admin, obtenir_salon_id, obtenir_couturier_id
from utils.page_header import afficher_header_page


def afficher_page_calendrier(onglet_admin: bool = False):
    """
    Page unifiée : Modèles réalisés + Calendrier.
    Si onglet_admin=True, affiche sans le header (intégré dans Administration).
    """
    if not st.session_state.get('authentifie', False):
        st.error("❌ Vous devez être connecté pour accéder à cette page")
        return
    if not st.session_state.get('db_connection'):
        st.error("❌ Connexion à la base de données requise")
        return

    couturier_data = st.session_state.get('couturier_data')
    commande_model = CommandeModel(st.session_state.db_connection)
    couturier_model = CouturierModel(st.session_state.db_connection)
    salon_id = obtenir_salon_id(couturier_data)
    couturier_id = obtenir_couturier_id(couturier_data)
    est_admin_user = est_admin(couturier_data)

    # Créer la table rappels si nécessaire
    commande_model.creer_table_rappels_livraison()

    # Rappels automatiques executes une seule fois par session et par jour
    from controllers.rappel_service import executer_rappels_automatiques
    date_key = datetime.now().strftime("%Y-%m-%d")
    rappel_key = f"rappels_auto_executes_{date_key}"
    if rappel_key not in st.session_state:
        nb_rappels, msg_rappels = executer_rappels_automatiques(st.session_state.db_connection)
        st.session_state[rappel_key] = True
        if msg_rappels:
            if nb_rappels > 0:
                st.success(f"✅ {msg_rappels}")
            else:
                st.info(f"ℹ️ {msg_rappels}")

    col_rappel_a, col_rappel_b = st.columns([2, 1])
    with col_rappel_a:
        st.caption("Les rappels sont declenches automatiquement 1 fois/jour par session.")
    with col_rappel_b:
        if st.button("🔔 Relancer les rappels", use_container_width=True, key="btn_relancer_rappels"):
            nb_rappels, msg_rappels = executer_rappels_automatiques(st.session_state.db_connection)
            if msg_rappels:
                if nb_rappels > 0:
                    st.success(f"✅ {msg_rappels}")
                else:
                    st.info(f"ℹ️ {msg_rappels}")

    # Header (uniquement en page standalone)
    if not onglet_admin:
        afficher_header_page(
            "📋 Modèles & Calendrier",
            "Vue des modèles réalisés et du calendrier des livraisons"
        )

    # Onglets principaux
    tab_modeles, tab_calendrier = st.tabs([
        "👗 Modèles réalisés",
        "📅 Mon calendrier",
    ])

    # ========================================================================
    # ONGLET 1 : MODÈLES RÉALISÉS
    # ========================================================================
    with tab_modeles:
        _afficher_modeles_realises(
            commande_model, couturier_model,
            couturier_id, salon_id, est_admin_user
        )

    # ========================================================================
    # ONGLET 2 : CALENDRIER
    # ========================================================================
    with tab_calendrier:
        _afficher_calendrier(
            commande_model, couturier_model,
            couturier_id, salon_id, est_admin_user
        )


def _afficher_modeles_realises(commande_model, couturier_model, couturier_id, salon_id, est_admin_user, key_prefix: str = "modeles"):
    """Affiche uniquement la galerie photos des réalisations."""
    st.markdown("### 📷 Galerie photos des réalisations")

    date_debut = st.date_input(
        "📅 Date de début",
        value=datetime.now().date().replace(day=1, month=1),
        key=f"{key_prefix}_date_debut"
    )
    date_fin = st.date_input(
        "📅 Date de fin",
        value=datetime.now().date(),
        key=f"{key_prefix}_date_fin"
    )

    couturier_id_filtre = couturier_id
    if est_admin_user and salon_id:
        tous_couturiers = couturier_model.lister_tous_couturiers(salon_id=salon_id)
        options = ["👥 Tous les couturiers"] + [
            f"{c['code_couturier']} - {c['prenom']} {c['nom']}"
            for c in tous_couturiers
        ]
        couturier_selectionne = st.selectbox(
            "Filtrer par couturier",
            options=options,
            key=f"{key_prefix}_filtre_couturier"
        )
        if couturier_selectionne and couturier_selectionne != "👥 Tous les couturiers":
            code = couturier_selectionne.split(" - ")[0]
            obj = next((c for c in tous_couturiers if c['code_couturier'] == code), None)
            couturier_id_filtre = obj['id'] if obj else couturier_id
        else:
            couturier_id_filtre = None

    st.markdown("---")

    _afficher_galerie_photos(
        commande_model,
        couturier_id_filtre,
        salon_id,
        datetime.combine(date_debut, datetime.min.time()),
        datetime.combine(date_fin, datetime.max.time()),
        key_prefix=key_prefix,
    )


def _afficher_galerie_photos(commande_model, couturier_id_filtre, salon_id, date_debut, date_fin, key_prefix: str = "modeles"):
    """Galerie photos avec navigation Suivant / En arrière."""
    commandes_img = commande_model.lister_commandes_avec_images(
        couturier_id=couturier_id_filtre,
        tous_les_couturiers=(couturier_id_filtre is None),
        salon_id=salon_id,
        date_debut=date_debut,
        date_fin=date_fin,
    )

    # Construire la liste plate des images (fabric + model)
    images_liste = []
    for cmd in commandes_img:
        client = f"{cmd.get('client_prenom', '')} {cmd.get('client_nom', '')}".strip()
        label_base = f"#{cmd['id']} {cmd.get('modele', 'N/A')} - {client}"
        if cmd.get('fabric_image'):
            images_liste.append({
                'bytes': cmd['fabric_image'],
                'label': f"{label_base} — Tissu",
            })
        if cmd.get('model_image'):
            images_liste.append({
                'bytes': cmd['model_image'],
                'label': f"{label_base} — Modèle",
            })

    if not images_liste:
        st.info("📷 Aucune photo disponible pour cette période.")
        return

    nb_photos = len(images_liste)
    key_idx = f"galerie_photo_idx_{key_prefix}"
    if key_idx not in st.session_state:
        st.session_state[key_idx] = 0

    st.markdown("#### 📷 Galerie photos des réalisations")
    st.caption(f"{nb_photos} photo(s) — Cliquez sur Suivant ou En arrière pour naviguer")

    with st.expander("📷 Voir les photos", expanded=False):
        idx = st.session_state[key_idx] % nb_photos
        img_data = images_liste[idx]

        col_img, _ = st.columns([2, 1])
        with col_img:
            try:
                raw_image = img_data.get('bytes')
                if raw_image is None:
                    st.warning("⚠️ Image vide ou indisponible pour cette commande.")
                else:
                    # PostgreSQL peut renvoyer BYTEA en memoryview selon le driver.
                    if isinstance(raw_image, memoryview):
                        raw_image = raw_image.tobytes()
                    elif isinstance(raw_image, bytearray):
                        raw_image = bytes(raw_image)
                    elif not isinstance(raw_image, bytes):
                        # Fallback défensif pour formats inattendus.
                        raw_image = bytes(raw_image)

                    st.image(raw_image, caption=img_data['label'], use_container_width=True)
            except Exception:
                try:
                    st.image(io.BytesIO(raw_image), caption=img_data['label'], use_container_width=True)
                except Exception as e:
                    st.error(f"❌ Impossible d'afficher l'image : {e}")

        st.caption(f"Photo {idx + 1} / {nb_photos}")

        col_prev, col_spacer, col_next = st.columns([1, 2, 1])
        with col_prev:
            if st.button("⬅️ En arrière", key=f"galerie_prev_{key_prefix}"):
                st.session_state[key_idx] = (st.session_state[key_idx] - 1 + nb_photos) % nb_photos
                st.rerun()
        with col_next:
            if st.button("Suivant ➡️", key=f"galerie_next_{key_prefix}"):
                st.session_state[key_idx] = (st.session_state[key_idx] + 1) % nb_photos
                st.rerun()


def _afficher_calendrier(commande_model, couturier_model, couturier_id, salon_id, est_admin_user):
    """Affiche le calendrier des livraisons avec rappels."""
    st.markdown("### 📅 Calendrier des livraisons")

    aujourd_hui = datetime.now().date()
    date_rappel = aujourd_hui + timedelta(days=2)

    col1, col2, col3 = st.columns(3)
    with col1:
        date_debut = st.date_input(
            "📅 Date de début",
            value=aujourd_hui,
            key="cal_date_debut"
        )
    with col2:
        date_fin = st.date_input(
            "📅 Date de fin",
            value=aujourd_hui + timedelta(days=30),
            key="cal_date_fin"
        )
    with col3:
        couturier_id_filtre = couturier_id
        if est_admin_user and salon_id:
            tous_couturiers = couturier_model.lister_tous_couturiers(salon_id=salon_id)
            options = ["👥 Tous les couturiers"] + [
                f"{c['code_couturier']} - {c['prenom']} {c['nom']}"
                for c in tous_couturiers
            ]
            couturier_selectionne = st.selectbox(
                "Filtrer par couturier",
                options=options,
                key="cal_filtre_couturier"
            )
            if couturier_selectionne and couturier_selectionne != "👥 Tous les couturiers":
                code = couturier_selectionne.split(" - ")[0]
                obj = next((c for c in tous_couturiers if c['code_couturier'] == code), None)
                couturier_id_filtre = obj['id'] if obj else couturier_id
            else:
                couturier_id_filtre = None

    st.markdown("---")

    # Section rappels
    commandes_rappel = commande_model.lister_commandes_calendrier(
        date_debut=date_rappel,
        date_fin=date_rappel,
        couturier_id=couturier_id_filtre,
        tous_les_couturiers=(couturier_id_filtre is None),
        salon_id=salon_id
    )
    commandes_a_rappeler = [
        c for c in commandes_rappel
        if not commande_model.rappel_deja_envoye(c['id'], c['date_livraison'])
    ]

    if commandes_a_rappeler:
        st.info(
            f"**{len(commandes_a_rappeler)} livraison(s)** prévue(s) le **{date_rappel.strftime('%d/%m/%Y')}**. "
            "Les rappels par email sont envoyés automatiquement chaque jour."
        )
        df_rappel = pd.DataFrame(commandes_a_rappeler)
        df_rappel_display = df_rappel[['modele', 'client_prenom', 'client_nom', 'couturier_prenom', 'couturier_nom', 'prix_total']].copy()
        df_rappel_display.columns = ['Modèle', 'Prénom Client', 'Nom Client', 'Prénom Couturier', 'Nom Couturier', 'Prix (FCFA)']
        df_rappel_display['Prix (FCFA)'] = df_rappel_display['Prix (FCFA)'].apply(lambda x: f"{x:,.0f}")
        st.dataframe(df_rappel_display, hide_index=True, use_container_width=True)
    elif commandes_rappel and not commandes_a_rappeler:
        st.success("✅ Rappels pour les livraisons du " + date_rappel.strftime('%d/%m/%Y') + " déjà envoyés.")
    else:
        st.info("ℹ️ Aucune livraison prévue dans 2 jours.")

    st.markdown("---")
    st.markdown("#### 📦 Par date")

    commandes = commande_model.lister_commandes_calendrier(
        date_debut=date_debut,
        date_fin=date_fin,
        couturier_id=couturier_id_filtre,
        tous_les_couturiers=(couturier_id_filtre is None),
        salon_id=salon_id
    )

    if not commandes:
        st.info("Aucune livraison prévue pour cette période.")
        return

    par_date = defaultdict(list)
    for c in commandes:
        dl = c.get('date_livraison')
        if dl:
            key = dl if hasattr(dl, 'strftime') else dl
            par_date[key].append(c)

    for date_liv in sorted(par_date.keys()):
        items = par_date[date_liv]
        date_str = date_liv.strftime('%d/%m/%Y') if hasattr(date_liv, 'strftime') else str(date_liv)
        is_aujourd = date_liv == aujourd_hui
        is_passe = date_liv < aujourd_hui

        if is_aujourd:
            label = f"🟢 **{date_str}** — Aujourd'hui ({len(items)} livraison(s))"
        elif is_passe:
            label = f"⏳ **{date_str}** — Passée ({len(items)} livraison(s))"
        else:
            label = f"📅 **{date_str}** — ({len(items)} livraison(s))"

        with st.expander(label, expanded=(not is_passe)):
            for c in items:
                resp = f"{c.get('couturier_prenom', '')} {c.get('couturier_nom', '')}".strip() or "N/A"
                client = f"{c.get('client_prenom', '')} {c.get('client_nom', '')}".strip()
                st.markdown(
                    f"- **{c.get('modele', 'N/A')}** — Client: {client} | "
                    f"Responsable: {resp} | "
                    f"💰 {c.get('prix_total', 0):,.0f} FCFA"
                )
