"""
Module unique "airan" pour une page Comptabilite complete:
- statistiques
- tris clients
- commandes a relancer
- bouton d'envoi de rappel email
"""

from datetime import datetime, timedelta
from typing import Dict, List, Optional

import matplotlib.pyplot as plt
import pandas as pd
import streamlit as st

from controllers.email_controller import EmailController
from models.salon_model import SalonModel
from utils.role_utils import obtenir_salon_id


class AiranComptabiliteController:
    """Controller local pour concentrer toute la logique dans un seul fichier."""

    def __init__(self, db_connection):
        self.db = db_connection

    def _build_where(
        self,
        couturier_id: int,
        date_debut: Optional[datetime] = None,
        date_fin: Optional[datetime] = None,
    ):
        where = ["couturier_id = %s"]
        params: List = [couturier_id]
        if date_debut:
            where.append("date_creation >= %s")
            params.append(date_debut)
        if date_fin:
            where.append("date_creation <= %s")
            params.append(date_fin)
        return " WHERE " + " AND ".join(where), params

    def obtenir_statistiques(
        self,
        couturier_id: int,
        date_debut: Optional[datetime] = None,
        date_fin: Optional[datetime] = None,
    ) -> Dict:
        try:
            cursor = self.db.get_connection().cursor()
            where_clause, params = self._build_where(couturier_id, date_debut, date_fin)
            query = (
                f"SELECT COUNT(*), COALESCE(SUM(prix_total), 0), COALESCE(SUM(avance), 0), "
                f"COALESCE(SUM(reste), 0) FROM commandes{where_clause}"
            )
            cursor.execute(query, tuple(params))
            result = cursor.fetchone()
            cursor.close()

            nb_commandes = int(result[0] or 0)
            ca_total = float(result[1] or 0)
            avances_total = float(result[2] or 0)
            reste_total = float(result[3] or 0)
            taux_avance = (avances_total / ca_total * 100) if ca_total > 0 else 0.0

            return {
                "nb_commandes": nb_commandes,
                "ca_total": ca_total,
                "avances_total": avances_total,
                "reste_total": reste_total,
                "taux_avance": taux_avance,
            }
        except Exception as e:
            print(f"Erreur obtenir_statistiques: {e}")
            return {
                "nb_commandes": 0,
                "ca_total": 0.0,
                "avances_total": 0.0,
                "reste_total": 0.0,
                "taux_avance": 0.0,
            }

    def lister_modeles_par_periode(
        self,
        couturier_id: int,
        date_debut: Optional[datetime] = None,
        date_fin: Optional[datetime] = None,
    ) -> List[str]:
        try:
            cursor = self.db.get_connection().cursor()
            where_clause, params = self._build_where(couturier_id, date_debut, date_fin)
            query = (
                f"SELECT modele, COUNT(*) AS n FROM commandes{where_clause} "
                f"GROUP BY modele ORDER BY n DESC"
            )
            cursor.execute(query, tuple(params))
            rows = cursor.fetchall()
            cursor.close()
            return [r[0] for r in rows]
        except Exception as e:
            print(f"Erreur lister_modeles_par_periode: {e}")
            return []

    def top_modeles(
        self,
        couturier_id: int,
        date_debut: Optional[datetime] = None,
        date_fin: Optional[datetime] = None,
        limit: int = 10,
    ):
        try:
            cursor = self.db.get_connection().cursor()
            where_clause, params = self._build_where(couturier_id, date_debut, date_fin)
            query = (
                f"SELECT modele, COUNT(*) FROM commandes{where_clause} "
                f"GROUP BY modele ORDER BY COUNT(*) DESC LIMIT %s"
            )
            params.append(limit)
            cursor.execute(query, tuple(params))
            rows = cursor.fetchall()
            cursor.close()
            return rows
        except Exception as e:
            print(f"Erreur top_modeles: {e}")
            return []

    def repartition_argent_par_modele(
        self,
        couturier_id: int,
        date_debut: Optional[datetime] = None,
        date_fin: Optional[datetime] = None,
        limit: int = 10,
    ):
        try:
            cursor = self.db.get_connection().cursor()
            where_clause, params = self._build_where(couturier_id, date_debut, date_fin)
            query = (
                f"SELECT modele, COALESCE(SUM(avance), 0) AS somme_avances FROM commandes{where_clause} "
                f"GROUP BY modele ORDER BY somme_avances DESC LIMIT %s"
            )
            params.append(limit)
            cursor.execute(query, tuple(params))
            rows = cursor.fetchall()
            cursor.close()
            return rows
        except Exception as e:
            print(f"Erreur repartition_argent_par_modele: {e}")
            return []

    def obtenir_liste_clients_triee(self, couturier_id: int, tri: str = "ca_desc"):
        try:
            cursor = self.db.get_connection().cursor()

            order_map = {
                "ca_desc": "ca_total DESC",
                "ca_asc": "ca_total ASC",
                "reste_desc": "reste_total DESC",
                "reste_asc": "reste_total ASC",
                "nb_desc": "nb_commandes DESC",
                "nb_asc": "nb_commandes ASC",
                "nom_asc": "c.nom ASC, c.prenom ASC",
                "nom_desc": "c.nom DESC, c.prenom DESC",
            }
            order_by = order_map.get(tri, "ca_total DESC")

            query = f"""
                SELECT c.nom, c.prenom, c.telephone,
                       COUNT(cmd.id) AS nb_commandes,
                       COALESCE(SUM(cmd.prix_total), 0) AS ca_total,
                       COALESCE(SUM(cmd.reste), 0) AS reste_total
                FROM clients c
                LEFT JOIN commandes cmd ON c.id = cmd.client_id
                WHERE c.couturier_id = %s
                GROUP BY c.id, c.nom, c.prenom, c.telephone
                ORDER BY {order_by}
            """
            cursor.execute(query, (couturier_id,))
            rows = cursor.fetchall()
            cursor.close()
            return rows
        except Exception as e:
            print(f"Erreur obtenir_liste_clients_triee: {e}")
            return []

    def obtenir_commandes_a_relancer(self, couturier_id: int):
        try:
            cursor = self.db.get_connection().cursor()
            query = """
                SELECT cmd.id, cmd.modele, cmd.prix_total, cmd.avance, cmd.reste, cmd.date_creation,
                       c.nom AS client_nom, c.prenom AS client_prenom, c.telephone AS client_telephone,
                       c.email AS client_email, cmd.pdf_path
                FROM commandes cmd
                JOIN clients c ON cmd.client_id = c.id
                WHERE cmd.couturier_id = %s AND cmd.reste > 0
                ORDER BY cmd.date_creation DESC
            """
            cursor.execute(query, (couturier_id,))
            rows = cursor.fetchall()
            cursor.close()
            data = []
            for row in rows:
                data.append(
                    {
                        "id": row[0],
                        "modele": row[1],
                        "prix_total": float(row[2] or 0),
                        "avance": float(row[3] or 0),
                        "reste": float(row[4] or 0),
                        "date_creation": row[5],
                        "client_nom": row[6],
                        "client_prenom": row[7],
                        "client_telephone": row[8],
                        "client_email": row[9],
                        "pdf_path": row[10] if len(row) > 10 else None,
                    }
                )
            return data
        except Exception as e:
            print(f"Erreur obtenir_commandes_a_relancer: {e}")
            return []


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


def afficher_page_comptabilite_airan():
    """Page Comptabilite complete dans le fichier airan.py."""
    st.title("Comptabilite - Airan")

    if not st.session_state.get("db_connection") or not st.session_state.get("authentifie"):
        st.error("Vous devez etre connecte pour acceder a cette page.")
        return

    couturier_data = st.session_state.get("couturier_data") or {}
    couturier_id = couturier_data.get("id")
    if not couturier_id:
        st.error("Impossible de retrouver l'identifiant couturier.")
        return

    controller = AiranComptabiliteController(st.session_state.db_connection)

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

    stats = controller.obtenir_statistiques(couturier_id, date_debut_filtre, date_fin_filtre)
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.metric("Chiffre d'affaires", f"{stats['ca_total']:,.0f} FCFA")
    with c2:
        st.metric("Avances recues", f"{stats['avances_total']:,.0f} FCFA", f"{stats['taux_avance']:.1f}%")
    with c3:
        st.metric("Reste a percevoir", f"{stats['reste_total']:,.0f} FCFA")
    with c4:
        st.metric("Commandes", stats["nb_commandes"])

    st.markdown("---")
    st.markdown("### Modeles et revenus")
    g1, g2 = st.columns(2)

    with g1:
        st.markdown("#### Top modeles")
        top = controller.top_modeles(couturier_id, date_debut_filtre, date_fin_filtre, limit=10)
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
                st.pyplot(fig1, width="stretch")
                plt.close(fig1)
            else:
                st.info("Aucune donnee disponible.")
        else:
            st.info("Aucune donnee disponible.")

    with g2:
        st.markdown("#### Repartition des avances par modele")
        rep = controller.repartition_argent_par_modele(couturier_id, date_debut_filtre, date_fin_filtre, limit=10)
        if rep:
            labels = [r[0] for r in rep]
            montants = [float(r[1]) for r in rep]
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
                st.pyplot(fig2, width="stretch")
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
    clients = controller.obtenir_liste_clients_triee(couturier_id, tri=tri_client_map[tri_client_label])
    if clients:
        df = pd.DataFrame(clients, columns=["Nom", "Prenom", "Telephone", "Nb Commandes", "CA Total", "Reste a payer"])
        df["CA Total"] = df["CA Total"].apply(lambda x: f"{float(x):,.0f} FCFA")
        df["Reste a payer"] = df["Reste a payer"].apply(lambda x: f"{float(x):,.0f} FCFA")
        st.dataframe(df, hide_index=True, width="stretch")
        st.download_button(
            "Exporter clients CSV",
            df.to_csv(index=False).encode("utf-8"),
            file_name=f"clients_airan_{datetime.now().strftime('%Y%m%d')}.csv",
            mime="text/csv",
        )
    else:
        st.info("Aucun client enregistre.")

