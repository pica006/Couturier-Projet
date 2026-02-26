"""Contrôleur pour la comptabilité"""
from typing import Dict, List, Optional
from datetime import datetime
from models.database import DatabaseConnection


class ComptabiliteController:
    def __init__(self, db_connection: DatabaseConnection):
        self.db = db_connection
    
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
            if couturier_id is not None:
                where_clause = "WHERE couturier_id = %s"
                params: list = [couturier_id]
            elif salon_id is not None:
                where_clause = "WHERE couturier_id IN (SELECT id FROM couturiers WHERE salon_id = %s)"
                params = [salon_id]
            else:
                return {'nb_commandes': 0, 'ca_total': 0, 'avances_total': 0, 'reste_total': 0, 'taux_avance': 0, 'commandes_par_statut': {}, 'top_modeles': []}

            if date_debut:
                where_clause += " AND date_creation >= %s"
                params.append(date_debut)
            if date_fin:
                where_clause += " AND date_creation <= %s"
                params.append(date_fin)

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
    
    def obtenir_liste_clients(self, couturier_id: int) -> List:
        """Récupère la liste des clients avec leurs stats"""
        try:
            cursor = self.db.get_connection().cursor()
            query = """
                SELECT c.nom, c.prenom, c.telephone, 
                       COUNT(cmd.id) as nb_commandes,
                       COALESCE(SUM(cmd.prix_total), 0) as ca_total,
                       COALESCE(SUM(cmd.reste), 0) as reste_total
                FROM clients c
                LEFT JOIN commandes cmd ON c.id = cmd.client_id
                WHERE c.couturier_id = %s
                GROUP BY c.id, c.nom, c.prenom, c.telephone
                ORDER BY ca_total DESC
            """
            cursor.execute(query, (couturier_id,))
            clients = cursor.fetchall()
            cursor.close()
            return clients
        except Exception as e:
            print(f"Erreur clients: {e}")
            return []
    
    def obtenir_commandes_a_relancer(self, couturier_id: int) -> List[Dict]:
        """Récupère les commandes avec reste à payer (pour relance client).
        
        Inclut le chemin PDF si disponible pour pouvoir l'ajouter en pièce jointe.
        """
        try:
            cursor = self.db.get_connection().cursor()
            query = """
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
                ORDER BY cmd.date_creation DESC
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
            if couturier_id is not None:
                where = ["couturier_id = %s"]
                params: list = [couturier_id]
            elif salon_id is not None:
                where = ["couturier_id IN (SELECT id FROM couturiers WHERE salon_id = %s)"]
                params = [salon_id]
            else:
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
                f"SELECT modele, COUNT(*) FROM commandes{where_clause} "
                "GROUP BY modele ORDER BY COUNT(*) DESC LIMIT %s"
            )
            params.append(limit)
            cursor.execute(query, tuple(params))
            rows = cursor.fetchall()
            cursor.close()
            return rows
        except Exception as e:
            print(f"Erreur top modèles: {e}")
            return []

    def repartition_argent_par_modele(self, couturier_id: int,
                                      date_debut: Optional[datetime] = None,
                                      date_fin: Optional[datetime] = None,
                                      limit: int = 10):
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
                f"SELECT modele, COALESCE(SUM(avance), 0) as somme_avances FROM commandes{where_clause} "
                "GROUP BY modele ORDER BY somme_avances DESC LIMIT %s"
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

    def lister_modeles_par_periode(self, couturier_id: int,
                                   date_debut: Optional[datetime] = None,
                                   date_fin: Optional[datetime] = None) -> List[str]:
        """Liste les modèles existants dans la période, triés par fréquence décroissante."""
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
                f"SELECT modele, COUNT(*) as n FROM commandes{where_clause} GROUP BY modele ORDER BY n DESC"
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

    def reste_par_modele(self, couturier_id: int,
                          date_debut: Optional[datetime] = None,
                          date_fin: Optional[datetime] = None,
                          limit: Optional[int] = None):
        """Retourne la somme du reste à percevoir par modèle, avec le nombre de vêtements.

        Returns:
            List[Tuple[str, float, int]]: (modele, somme_reste, count)
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
                f"SELECT modele, COALESCE(SUM(reste), 0) as somme_reste, COUNT(*) as nb_items FROM commandes{where_clause} "
                "GROUP BY modele ORDER BY somme_reste DESC"
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

    
