"""
Vue comptabilite: UI Streamlit uniquement, logique metier cote controller.
Parite fonctionnelle avec airan.py.
"""

from datetime import datetime, timedelta

import matplotlib
import pandas as pd
import streamlit as st

matplotlib.use("Agg")
import matplotlib.pyplot as plt

from controllers.comptabilite_controller import ComptabiliteController


def _make_autopct(values, formatter=None):
    total = sum(values) if values else 0

    def _autopct(pct):
        if total == 0:
            return "0%\n0"
        val = pct * total / 100.0
        if formatter:
            return f"{pct:.1f}%\n{formatter(val)}"
        return f"{pct:.1f}%\n{int(round(val))}"

    return _autopct


def _place_legend(ax, wedges, labels, title):
    if len(labels) > 6:
        ax.legend(wedges, labels, title=title, loc="lower center", bbox_to_anchor=(0.5, -0.15), ncol=3)
    else:
        ax.legend(wedges, labels, title=title, loc="center left", bbox_to_anchor=(1, 0.5))


def afficher_page_comptabilite():
    st.title("Comptabilite - Airan")

    if not st.session_state.get("db_connection") or not st.session_state.get("authentifie"):
        st.error("Vous devez etre connecte pour acceder a cette page.")
        return

    couturier_data = st.session_state.get("couturier_data") or {}
    couturier_id = couturier_data.get("id")
    if not couturier_id:
        st.error("Impossible de retrouver l'identifiant couturier.")
        return

    controller = ComptabiliteController(st.session_state.db_connection)

    st.markdown("### Intervalle d'analyse")
    col_d1, col_d2 = st.columns(2)
    default_debut = datetime.now().date() - timedelta(days=30)
    default_fin = datetime.now().date()

    with col_d1:
        date_debut = st.date_input("Date debut", value=default_debut, key="airan_date_debut")
    with col_d2:
        date_fin = st.date_input("Date fin", value=default_fin, key="airan_date_fin")

    date_debut_filtre = datetime.combine(date_debut, datetime.min.time()) if date_debut else None
    date_fin_filtre = datetime.combine(date_fin, datetime.max.time()) if date_fin else None
    if date_debut_filtre and date_fin_filtre and date_fin_filtre < date_debut_filtre:
        date_debut_filtre, date_fin_filtre = date_fin_filtre, date_debut_filtre

    modeles = controller.lister_modeles_par_periode(couturier_id, date_debut_filtre, date_fin_filtre)
    modele_selectionne = st.selectbox("Filtrer par modele", ["Tous"] + modeles, key="airan_modele")

    stats = controller.obtenir_statistiques(couturier_id, date_debut_filtre, date_fin_filtre) or {}
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.metric("Chiffre d'affaires", f"{float(stats.get('ca_total', 0) or 0):,.0f} FCFA")
    with c2:
        st.metric(
            "Avances recues",
            f"{float(stats.get('avances_total', 0) or 0):,.0f} FCFA",
            f"{float(stats.get('taux_avance', 0) or 0):.1f}%",
        )
    with c3:
        st.metric("Reste a percevoir", f"{float(stats.get('reste_total', 0) or 0):,.0f} FCFA")
    with c4:
        st.metric("Commandes", int(stats.get("nb_commandes", 0) or 0))

    st.markdown("---")
    st.markdown("### Modeles et revenus")
    g1, g2 = st.columns(2)

    with g1:
        st.markdown("#### Top modeles")
        top = controller.top_modeles(
            couturier_id=couturier_id,
            date_debut=date_debut_filtre,
            date_fin=date_fin_filtre,
            limit=10,
        )
        if top:
            labels = [r[0] for r in top]
            counts = [int(r[1]) for r in top]
            if modele_selectionne != "Tous":
                filt = [(l, c) for l, c in zip(labels, counts) if l == modele_selectionne]
                labels = [filt[0][0]] if filt else []
                counts = [filt[0][1]] if filt else []
            if counts and sum(counts) > 0:
                fig1, ax1 = plt.subplots()
                wedges, _, _ = ax1.pie(
                    counts,
                    labels=None,
                    autopct=_make_autopct(counts, formatter=lambda v: f"{int(round(v))} cmd"),
                    startangle=90,
                    pctdistance=0.75,
                )
                ax1.axis("equal")
                _place_legend(ax1, wedges, [f"{l} ({c})" for l, c in zip(labels, counts)], "Modeles")
                st.pyplot(fig1, use_container_width=True)
                plt.close(fig1)
            else:
                st.info("Aucune donnee disponible.")
        else:
            st.info("Aucune donnee disponible.")

    with g2:
        st.markdown("#### Repartition des avances par modele")
        rep = controller.repartition_argent_par_modele(
            couturier_id=couturier_id,
            date_debut=date_debut_filtre,
            date_fin=date_fin_filtre,
            limit=10,
        )
        if rep:
            labels = [r[0] for r in rep]
            montants = [float(r[1] or 0) for r in rep]
            if modele_selectionne != "Tous":
                filt = [(l, m) for l, m in zip(labels, montants) if l == modele_selectionne]
                labels = [filt[0][0]] if filt else []
                montants = [filt[0][1]] if filt else []
            if montants and sum(montants) > 0:
                fig2, ax2 = plt.subplots()
                wedges, _, _ = ax2.pie(
                    montants,
                    labels=None,
                    autopct=_make_autopct(montants, formatter=lambda v: f"{v:,.0f} FCFA"),
                    startangle=90,
                    pctdistance=0.75,
                )
                ax2.axis("equal")
                _place_legend(ax2, wedges, [f"{l} ({m:,.0f})" for l, m in zip(labels, montants)], "Modeles")
                st.pyplot(fig2, use_container_width=True)
                plt.close(fig2)
            else:
                st.info("Aucune donnee disponible.")
        else:
            st.info("Aucune donnee disponible.")

    st.markdown("---")
    st.markdown("### Clients")
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
        key="airan_tri_clients",
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
    clients = controller.obtenir_liste_clients_triee(couturier_id=couturier_id, tri=tri_client_map[tri_client_label])
    if clients:
        df = pd.DataFrame(clients, columns=["Nom", "Prenom", "Telephone", "Nb Commandes", "CA Total", "Reste a payer"])
        df["CA Total"] = df["CA Total"].apply(lambda x: f"{float(x or 0):,.0f} FCFA")
        df["Reste a payer"] = df["Reste a payer"].apply(lambda x: f"{float(x or 0):,.0f} FCFA")
        st.dataframe(df, hide_index=True, use_container_width=True)
        st.download_button(
            "Exporter clients CSV",
            df.to_csv(index=False).encode("utf-8"),
            file_name=f"clients_airan_{datetime.now().strftime('%Y%m%d')}.csv",
            mime="text/csv",
        )
    else:
        st.info("Aucun client enregistre.")



