"""Contrôleur pour la comptabilité"""
from typing import Dict, List, Optional, Tuple
from datetime import datetime
from models.database import DatabaseConnection
from controllers.email_controller import EmailController


class ComptabiliteController:
    TRI_CLIENTS_ORDER_BY = {
        "ca_desc": "ca_total DESC",
        "ca_asc": "ca_total ASC",
        "reste_desc": "reste_total DESC",
        "reste_asc": "reste_total ASC",
        "nb_desc": "nb_commandes DESC",
        "nb_asc": "nb_commandes ASC",
        "nom_asc": "c.nom ASC, c.prenom ASC",
        "nom_desc": "c.nom DESC, c.prenom DESC",
    }
    TRI_RELANCES_ORDER_BY = {
        "date_desc": "cmd.date_creation DESC",
        "date_asc": "cmd.date_creation ASC",
        "reste_desc": "cmd.reste DESC",
        "reste_asc": "cmd.reste ASC",
        "nom_asc": "c.nom ASC, c.prenom ASC",
        "nom_desc": "c.nom DESC, c.prenom DESC",
    }

    def __init__(self, db_connection: DatabaseConnection):
        self.db = db_connection

    def _build_scope_where(
        self,
        couturier_id: Optional[int] = None,
        salon_id: Optional[str] = None,
    ) -> tuple[list[str], list]:
        """Construit un filtre de portée robuste (couturier ou salon)."""
        if couturier_id is not None and salon_id is not None:
            return (["couturier_id = %s", "salon_id = %s"], [couturier_id, salon_id])
        if couturier_id is not None:
            return (["couturier_id = %s"], [couturier_id])
        if salon_id is not None:
            # Priorité à la colonne commandes.salon_id.
            # Fallback via couturiers pour compatibilité des anciennes données.
            return (
                [
                    "(salon_id = %s OR couturier_id IN (SELECT id FROM couturiers WHERE salon_id = %s))"
                ],
                [salon_id, salon_id],
            )
        return ([], [])
    
    def obtenir_statistiques(
        self,
        couturier_id: Optional[int] = None,
        date_debut: Optional[datetime] = None,
        date_fin: Optional[datetime] = None,
        salon_id: Optional[str] = None,
    ) -> Dict:
        """Calcule les statistiques financières (par couturier ou par salon)."""
        try:
            cursor = self.db.get_connection().cursor()
            where, params = self._build_scope_where(couturier_id=couturier_id, salon_id=salon_id)
            if not where:
                return {'nb_commandes': 0, 'ca_total': 0, 'avances_total': 0, 'reste_total': 0, 'taux_avance': 0, 'commandes_par_statut': {}, 'top_modeles': []}

            if date_debut:
                where.append("date_creation >= %s")
                params.append(date_debut)
            if date_fin:
                where.append("date_creation <= %s")
                params.append(date_fin)
            where_clause = "WHERE " + " AND ".join(where)

            # Stats financières
            query = f"SELECT COUNT(*), COALESCE(SUM(prix_total), 0), COALESCE(SUM(avance), 0), COALESCE(SUM(reste), 0) FROM commandes {where_clause}"
            cursor.execute(query, params)
            result = cursor.fetchone()
            
            nb_commandes = result[0]
            ca_total = float(result[1])
            avances_total = float(result[2])
            reste_total = float(result[3])
            taux_avance = (avances_total / ca_total * 100) if ca_total > 0 else 0
            
            # Stats par statut
            query = f"SELECT statut, COUNT(*) FROM commandes {where_clause} GROUP BY statut"
            cursor.execute(query, params)
            commandes_par_statut = {statut: count for statut, count in cursor.fetchall()}
            
            # Top modèles
            query = f"SELECT modele, COUNT(*) FROM commandes {where_clause} GROUP BY modele ORDER BY COUNT(*) DESC LIMIT 10"
            cursor.execute(query, params)
            top_modeles = cursor.fetchall()
            
            cursor.close()
            
            return {
                'nb_commandes': nb_commandes,
                'ca_total': ca_total,
                'avances_total': avances_total,
                'reste_total': reste_total,
                'taux_avance': taux_avance,
                'commandes_par_statut': commandes_par_statut,
                'top_modeles': top_modeles
            }
        except Exception as e:
            print(f"Erreur stats: {e}")
            return {'nb_commandes': 0, 'ca_total': 0, 'avances_total': 0, 'reste_total': 0, 'taux_avance': 0, 'commandes_par_statut': {}, 'top_modeles': []}
    
    def obtenir_liste_clients_triee(
        self,
        couturier_id: Optional[int] = None,
        salon_id: Optional[str] = None,
        tri: str = "ca_desc",
    ) -> List:
        """Récupère la liste des clients avec tri SQL contrôlé."""
        try:
            cursor = self.db.get_connection().cursor()
            order_by = self.TRI_CLIENTS_ORDER_BY.get(tri, self.TRI_CLIENTS_ORDER_BY["ca_desc"])
            if salon_id is not None and couturier_id is not None:
                query = f"""
                    SELECT c.nom, c.prenom, c.telephone,
                           COUNT(cmd.id) as nb_commandes,
                           COALESCE(SUM(cmd.prix_total), 0) as ca_total,
                           COALESCE(SUM(cmd.reste), 0) as reste_total
                    FROM clients c
                    LEFT JOIN commandes cmd ON c.id = cmd.client_id
                    WHERE c.salon_id = %s AND c.couturier_id = %s
                    GROUP BY c.id, c.nom, c.prenom, c.telephone
                    ORDER BY {order_by}
                """
                cursor.execute(query, (salon_id, couturier_id))
            elif salon_id is not None:
                query = f"""
                    SELECT c.nom, c.prenom, c.telephone, 
                           COUNT(cmd.id) as nb_commandes,
                           COALESCE(SUM(cmd.prix_total), 0) as ca_total,
                           COALESCE(SUM(cmd.reste), 0) as reste_total
                    FROM clients c
                    LEFT JOIN commandes cmd ON c.id = cmd.client_id
                    WHERE c.salon_id = %s
                    GROUP BY c.id, c.nom, c.prenom, c.telephone
                    ORDER BY {order_by}
                """
                cursor.execute(query, (salon_id,))
            else:
                query = f"""
                    SELECT c.nom, c.prenom, c.telephone, 
                           COUNT(cmd.id) as nb_commandes,
                           COALESCE(SUM(cmd.prix_total), 0) as ca_total,
                           COALESCE(SUM(cmd.reste), 0) as reste_total
                    FROM clients c
                    LEFT JOIN commandes cmd ON c.id = cmd.client_id
                    WHERE c.couturier_id = %s
                    GROUP BY c.id, c.nom, c.prenom, c.telephone
                    ORDER BY {order_by}
                """
                cursor.execute(query, (couturier_id,))
            clients = cursor.fetchall()
            cursor.close()
            return clients
        except Exception as e:
            print(f"Erreur clients: {e}")
            return []

    def obtenir_liste_clients(self, couturier_id: Optional[int] = None, salon_id: Optional[str] = None) -> List:
        """Compatibilité: conserve la méthode historique avec tri par CA décroissant."""
        return self.obtenir_liste_clients_triee(couturier_id=couturier_id, salon_id=salon_id, tri="ca_desc")
    
    def obtenir_commandes_a_relancer(
        self,
        couturier_id: Optional[int] = None,
        salon_id: Optional[str] = None,
        tri: str = "date_desc",
    ) -> List[Dict]:
        """Récupère les commandes avec reste à payer (pour relance client).
        
        Inclut le chemin PDF si disponible pour pouvoir l'ajouter en pièce jointe.
        """
        try:
            cursor = self.db.get_connection().cursor()
            order_by = self.TRI_RELANCES_ORDER_BY.get(tri, self.TRI_RELANCES_ORDER_BY["date_desc"])
            if salon_id is not None and couturier_id is not None:
                query = f"""
                    SELECT cmd.id,
                           cmd.modele,
                           cmd.prix_total,
                           cmd.avance,
                           cmd.reste,
                           cmd.date_creation,
                           c.nom   AS client_nom,
                           c.prenom AS client_prenom,
                           c.telephone AS client_telephone,
                           c.email AS client_email,
                           cmd.pdf_path
                    FROM commandes cmd
                    JOIN clients c ON cmd.client_id = c.id
                    WHERE cmd.salon_id = %s AND cmd.couturier_id = %s AND cmd.reste > 0
                    ORDER BY {order_by}
                """
                cursor.execute(query, (salon_id, couturier_id))
            elif salon_id is not None:
                query = f"""
                    SELECT cmd.id,
                           cmd.modele,
                           cmd.prix_total,
                           cmd.avance,
                           cmd.reste,
                           cmd.date_creation,
                           c.nom   AS client_nom,
                           c.prenom AS client_prenom,
                           c.telephone AS client_telephone,
                           c.email AS client_email,
                           cmd.pdf_path
                    FROM commandes cmd
                    JOIN clients c ON cmd.client_id = c.id
                    WHERE cmd.salon_id = %s AND cmd.reste > 0
                    ORDER BY {order_by}
                """
                cursor.execute(query, (salon_id,))
            else:
                query = f"""
                    SELECT cmd.id,
                           cmd.modele,
                           cmd.prix_total,
                           cmd.avance,
                           cmd.reste,
                           cmd.date_creation,
                           c.nom   AS client_nom,
                           c.prenom AS client_prenom,
                           c.telephone AS client_telephone,
                           c.email AS client_email,
                           cmd.pdf_path
                    FROM commandes cmd
                    JOIN clients c ON cmd.client_id = c.id
                    WHERE cmd.couturier_id = %s AND cmd.reste > 0
                    ORDER BY {order_by}
                """
                cursor.execute(query, (couturier_id,))
            results = cursor.fetchall()
            cursor.close()
            
            commandes = []
            for row in results:
                commandes.append({
                    'id': row[0],
                    'modele': row[1],
                    'prix_total': float(row[2]),
                    'avance': float(row[3]),
                    'reste': float(row[4]),
                    'date_creation': row[5],
                    'client_nom': row[6],
                    'client_prenom': row[7],
                    'client_telephone': row[8],
                    'client_email': row[9],
                    'pdf_path': row[10] if len(row) > 10 else None,
                })
            return commandes
        except Exception as e:
            print(f"Erreur commandes relance: {e}")
            return []

    def envoyer_rappel_email_commande(
        self,
        commande: Dict,
        smtp_config: Optional[Dict] = None,
    ) -> Tuple[bool, str]:
        """Envoie un rappel email pour une commande donnée."""
        client_email = commande.get("client_email")
        if not client_email:
            return False, "Adresse email du client manquante."

        subject = f"Rappel de paiement - Commande #{commande.get('id')}"
        body = (
            f"Bonjour {commande.get('client_prenom', '')} {commande.get('client_nom', '')},\n\n"
            "Nous vous rappelons le solde de votre commande.\n\n"
            f"Commande: #{commande.get('id')}\n"
            f"Modèle: {commande.get('modele', 'N/A')}\n"
            f"Prix total: {float(commande.get('prix_total', 0) or 0):,.0f} FCFA\n"
            f"Avance: {float(commande.get('avance', 0) or 0):,.0f} FCFA\n"
            f"Reste à payer: {float(commande.get('reste', 0) or 0):,.0f} FCFA\n\n"
            "Vous trouverez en pièce jointe votre fiche de commande (PDF), "
            "si elle a été générée lors de l'enregistrement.\n\n"
            "Merci pour votre confiance."
        )
        attachment_path = commande.get("pdf_path")
        attachments = [attachment_path] if attachment_path else None

        email_controller = EmailController(smtp_config=smtp_config)
        return email_controller.envoyer_email_avec_message(
            client_email,
            subject,
            body,
            attachments=attachments,
        )

    def classement_efficacite_couturiers(
        self,
        salon_id: str,
        date_debut: Optional[datetime] = None,
        date_fin: Optional[datetime] = None,
    ) -> List[Dict]:
        """Retourne un classement des couturiers d'un salon sur la période."""
        try:
            cursor = self.db.get_connection().cursor()
            join_filters = []
            join_params: list = []
            if date_debut:
                join_filters.append("cmd.date_creation >= %s")
                join_params.append(date_debut)
            if date_fin:
                join_filters.append("cmd.date_creation <= %s")
                join_params.append(date_fin)
            join_clause = " AND " + " AND ".join(join_filters) if join_filters else ""

            query = f"""
                SELECT co.id,
                       co.code_couturier,
                       co.nom,
                       co.prenom,
                       COUNT(cmd.id) AS nb_commandes,
                       COALESCE(SUM(cmd.prix_total), 0) AS ca_total,
                       COALESCE(SUM(cmd.avance), 0) AS avances_total,
                       COALESCE(SUM(cmd.reste), 0) AS reste_total
                FROM couturiers co
                LEFT JOIN commandes cmd
                    ON cmd.couturier_id = co.id
                    AND cmd.salon_id = co.salon_id
                    {join_clause}
                WHERE co.salon_id = %s
                GROUP BY co.id, co.code_couturier, co.nom, co.prenom
                ORDER BY ca_total DESC, nb_commandes DESC
            """
            cursor.execute(query, tuple(join_params + [salon_id]))
            rows = cursor.fetchall()
            cursor.close()

            classement = []
            for row in rows:
                ca = float(row[5] or 0)
                avances = float(row[6] or 0)
                taux_avance = (avances / ca * 100) if ca > 0 else 0.0
                classement.append(
                    {
                        "couturier_id": row[0],
                        "code_couturier": row[1],
                        "nom": row[2],
                        "prenom": row[3],
                        "nb_commandes": int(row[4] or 0),
                        "ca_total": ca,
                        "avances_total": avances,
                        "reste_total": float(row[7] or 0),
                        "taux_avance": taux_avance,
                    }
                )
            return classement
        except Exception as e:
            print(f"Erreur classement efficacité couturiers: {e}")
            return []

    def top_modeles(
        self,
        couturier_id: Optional[int] = None,
        statut: Optional[str] = None,
        date_debut: Optional[datetime] = None,
        date_fin: Optional[datetime] = None,
        limit: int = 10,
        salon_id: Optional[str] = None,
    ):
        """Retourne le top des modèles (par couturier ou par salon)."""
        try:
            cursor = self.db.get_connection().cursor()
            where, params = self._build_scope_where(couturier_id=couturier_id, salon_id=salon_id)
            if not where:
                return []
            if statut:
                where.append("statut = %s")
                params.append(statut)
            if date_debut:
                where.append("date_creation >= %s")
                params.append(date_debut)
            if date_fin:
                where.append("date_creation <= %s")
                params.append(date_fin)
            where_clause = " WHERE " + " AND ".join(where)
            query = (
                "SELECT COALESCE(NULLIF(TRIM(modele), ''), 'Non renseigné') as modele_label, COUNT(*) "
                f"FROM commandes{where_clause} "
                "GROUP BY modele_label ORDER BY COUNT(*) DESC LIMIT %s"
            )
            params.append(limit)
            cursor.execute(query, tuple(params))
            rows = cursor.fetchall()
            cursor.close()
            return rows
        except Exception as e:
            print(f"Erreur top modèles: {e}")
            return []

    def repartition_argent_par_modele(self, couturier_id: Optional[int] = None,
                                      date_debut: Optional[datetime] = None,
                                      date_fin: Optional[datetime] = None,
                                      limit: int = 10,
                                      salon_id: Optional[str] = None):
        """Retourne la somme des avances reçues par modèle, triée décroissante.

        Args:
            couturier_id: identifiant du couturier
            date_debut: borne de début (inclus)
            date_fin: borne de fin (inclus)
            limit: nombre maximal de lignes

        Returns:
            List[Tuple[str, float]]: (modele, somme_avances)
        """
        try:
            cursor = self.db.get_connection().cursor()
            where, params = self._build_scope_where(couturier_id=couturier_id, salon_id=salon_id)
            if not where:
                return []
            if date_debut:
                where.append("date_creation >= %s")
                params.append(date_debut)
            if date_fin:
                where.append("date_creation <= %s")
                params.append(date_fin)
            where_clause = " WHERE " + " AND ".join(where)
            query = (
                "SELECT COALESCE(NULLIF(TRIM(modele), ''), 'Non renseigné') as modele_label, "
                "COALESCE(SUM(avance), 0) as somme_avances "
                f"FROM commandes{where_clause} "
                "GROUP BY modele_label ORDER BY somme_avances DESC LIMIT %s"
            )
            params.append(limit)
            cursor.execute(query, tuple(params))
            rows = cursor.fetchall()
            cursor.close()
            return rows
        except Exception as e:
            print(f"Erreur répartition argent par modèle: {e}")
            return []

    def repartition_argent_par_categorie(self, couturier_id: int,
                                         date_debut: Optional[datetime] = None,
                                         date_fin: Optional[datetime] = None,
                                         limit: Optional[int] = None):
        """Retourne la somme des avances reçues par catégorie.

        Args:
            couturier_id: identifiant du couturier
            date_debut: borne de début (inclus)
            date_fin: borne de fin (inclus)
            limit: nombre maximal de lignes (optionnel)

        Returns:
            List[Tuple[str, float]]: (categorie, somme_avances)
        """
        try:
            cursor = self.db.get_connection().cursor()
            where = ["couturier_id = %s"]
            params: list = [couturier_id]
            if date_debut:
                where.append("date_creation >= %s")
                params.append(date_debut)
            if date_fin:
                where.append("date_creation <= %s")
                params.append(date_fin)
            where_clause = " WHERE " + " AND ".join(where)
            query = (
                f"SELECT categorie, COALESCE(SUM(avance), 0) as somme_avances FROM commandes{where_clause} "
                "GROUP BY categorie ORDER BY somme_avances DESC"
            )
            if limit is not None:
                query += " LIMIT %s"
                params.append(limit)
            cursor.execute(query, tuple(params))
            rows = cursor.fetchall()
            cursor.close()
            return rows
        except Exception as e:
            print(f"Erreur répartition argent par catégorie: {e}")
            return []

    def lister_modeles_par_periode(self, couturier_id: Optional[int] = None,
                                   date_debut: Optional[datetime] = None,
                                   date_fin: Optional[datetime] = None,
                                   salon_id: Optional[str] = None) -> List[str]:
        """Liste les modèles existants dans la période, triés par fréquence décroissante."""
        try:
            cursor = self.db.get_connection().cursor()
            where, params = self._build_scope_where(couturier_id=couturier_id, salon_id=salon_id)
            if not where:
                return []
            if date_debut:
                where.append("date_creation >= %s")
                params.append(date_debut)
            if date_fin:
                where.append("date_creation <= %s")
                params.append(date_fin)
            where_clause = " WHERE " + " AND ".join(where)
            query = (
                "SELECT COALESCE(NULLIF(TRIM(modele), ''), 'Non renseigné') as modele_label, COUNT(*) as n "
                f"FROM commandes{where_clause} GROUP BY modele_label ORDER BY n DESC"
            )
            cursor.execute(query, tuple(params))
            rows = cursor.fetchall()
            cursor.close()
            return [r[0] for r in rows]
        except Exception as e:
            print(f"Erreur liste modèles par période: {e}")
            return []

    def reste_par_categorie(self, couturier_id: int,
                             date_debut: Optional[datetime] = None,
                             date_fin: Optional[datetime] = None,
                             limit: Optional[int] = None):
        """Retourne la somme du reste à percevoir par catégorie, avec le nombre de vêtements.

        Returns:
            List[Tuple[str, float, int]]: (categorie, somme_reste, count)
        """
        try:
            cursor = self.db.get_connection().cursor()
            where = ["couturier_id = %s"]
            params: list = [couturier_id]
            if date_debut:
                where.append("date_creation >= %s")
                params.append(date_debut)
            if date_fin:
                where.append("date_creation <= %s")
                params.append(date_fin)
            where_clause = " WHERE " + " AND ".join(where)
            query = (
                f"SELECT categorie, COALESCE(SUM(reste), 0) as somme_reste, COUNT(*) as nb_items FROM commandes{where_clause} "
                "GROUP BY categorie ORDER BY somme_reste DESC"
            )
            if limit is not None:
                query += " LIMIT %s"
                params.append(limit)
            cursor.execute(query, tuple(params))
            rows = cursor.fetchall()
            cursor.close()
            return rows
        except Exception as e:
            print(f"Erreur reste par catégorie: {e}")
            return []

    def reste_par_modele(self, couturier_id: Optional[int] = None,
                          date_debut: Optional[datetime] = None,
                          date_fin: Optional[datetime] = None,
                          limit: Optional[int] = None,
                          salon_id: Optional[str] = None):
        """Retourne la somme du reste à percevoir par modèle, avec le nombre de vêtements.

        Returns:
            List[Tuple[str, float, int]]: (modele, somme_reste, count)
        """
        try:
            cursor = self.db.get_connection().cursor()
            where, params = self._build_scope_where(couturier_id=couturier_id, salon_id=salon_id)
            if not where:
                return []
            if date_debut:
                where.append("date_creation >= %s")
                params.append(date_debut)
            if date_fin:
                where.append("date_creation <= %s")
                params.append(date_fin)
            where_clause = " WHERE " + " AND ".join(where)
            query = (
                "SELECT COALESCE(NULLIF(TRIM(modele), ''), 'Non renseigné') as modele_label, "
                f"COALESCE(SUM(reste), 0) as somme_reste, COUNT(*) as nb_items FROM commandes{where_clause} "
                "GROUP BY modele_label ORDER BY somme_reste DESC"
            )
            if limit is not None:
                query += " LIMIT %s"
                params.append(limit)
            cursor.execute(query, tuple(params))
            rows = cursor.fetchall()
            cursor.close()
            return rows
        except Exception as e:
            print(f"Erreur reste par modèle: {e}")
            return []

    
