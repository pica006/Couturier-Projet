"""
Contrôleur pour le Super Administrateur (Vue 360° multi-salons)
"""
from typing import Optional, Dict, List
from models.database import DatabaseConnection
from datetime import datetime, timedelta


class SuperAdminController:
    """Contrôleur pour les fonctionnalités du SUPER_ADMIN"""
    
    def __init__(self, db_connection: DatabaseConnection):
        self.db = db_connection

    def obtenir_statistiques_globales(
        self,
        date_debut: Optional[datetime] = None,
        date_fin: Optional[datetime] = None,
    ) -> Dict:
        """
        Récupère les statistiques globales de TOUS les salons
        (optionnellement filtrées par période)
        
        Returns:
            Dict avec toutes les métriques globales
        """
        try:
            # Si aucune période n'est fournie -> comportement historique (toutes les données)
            if not date_debut and not date_fin:
                cursor = self.db.get_connection().cursor()

                # Nombre total de salons actifs
                cursor.execute("SELECT COUNT(*) FROM salons WHERE actif = TRUE OR actif IS NULL")
                nb_salons = cursor.fetchone()[0]

                # Nombre total d'utilisateurs par rôle
                cursor.execute("""
                    SELECT 
                        role,
                        COUNT(*) as nb
                    FROM couturiers 
                    WHERE role != 'SUPER_ADMIN'
                    GROUP BY role
                """)
                users_by_role = {row[0]: row[1] for row in cursor.fetchall()}

                # Nombre total de clients
                cursor.execute("SELECT COUNT(*) FROM clients")
                nb_clients_total = cursor.fetchone()[0]

                # Nombre total de commandes
                cursor.execute("SELECT COUNT(*) FROM commandes")
                nb_commandes_total = cursor.fetchone()[0]

                # Chiffre d'affaires total
                cursor.execute("SELECT COALESCE(SUM(prix_total), 0) FROM commandes")
                ca_total = float(cursor.fetchone()[0])

                # Total des avances
                cursor.execute("SELECT COALESCE(SUM(avance), 0) FROM commandes")
                avances_total = float(cursor.fetchone()[0])

                # Total des restes
                cursor.execute("SELECT COALESCE(SUM(reste), 0) FROM commandes")
                reste_total = float(cursor.fetchone()[0])

                # Total des charges
                cursor.execute("SELECT COALESCE(SUM(montant), 0) FROM charges")
                charges_total = float(cursor.fetchone()[0])

                cursor.close()
            else:
                # Avec période : on agrège à partir des stats par salon filtrées par période
                stats_salons = self.obtenir_statistiques_par_salon(date_debut=date_debut, date_fin=date_fin)
                nb_salons = len(stats_salons)

                # Nombre total d'utilisateurs par rôle (pas filtré par date)
                cursor = self.db.get_connection().cursor()
                cursor.execute("""
                    SELECT 
                        role,
                        COUNT(*) as nb
                    FROM couturiers 
                    WHERE role != 'SUPER_ADMIN'
                    GROUP BY role
                """)
                users_by_role = {row[0]: row[1] for row in cursor.fetchall()}

                cursor.execute("SELECT COUNT(*) FROM clients")
                nb_clients_total = cursor.fetchone()[0]
                cursor.close()

                nb_commandes_total = sum(s.get('nb_commandes', 0) for s in stats_salons)
                ca_total = sum(s.get('ca_total', 0.0) for s in stats_salons)
                avances_total = sum(s.get('avances', 0.0) for s in stats_salons)
                reste_total = sum(s.get('reste', 0.0) for s in stats_salons)
                charges_total = sum(s.get('charges', 0.0) for s in stats_salons)

            return {
                'nb_salons': nb_salons,
                'nb_admins': users_by_role.get('admin', 0),
                'nb_employes': users_by_role.get('employe', 0),
                'nb_clients_total': nb_clients_total,
                'nb_commandes_total': nb_commandes_total,
                'ca_total': ca_total,
                'avances_total': avances_total,
                'reste_total': reste_total,
                'charges_total': charges_total,
                'benefice_brut': ca_total - charges_total,
                'taux_encaissement': (avances_total / ca_total * 100) if ca_total > 0 else 0,
            }
        except Exception as e:
            print(f"Erreur statistiques globales: {e}")
            return {}
    
    def obtenir_statistiques_par_salon(
        self,
        date_debut: Optional[datetime] = None,
        date_fin: Optional[datetime] = None,
    ) -> List[Dict]:
        """
        Récupère les statistiques détaillées pour chaque salon
        (optionnellement filtrées par période sur commandes & charges)
        
        Returns:
            Liste de Dict avec les stats de chaque salon
        """
        try:
            cursor = self.db.get_connection().cursor()

            # 1) Infos de base sur les salons + nb_employés + nb_clients (non filtrés par date)
            query_salons = """
                SELECT 
                    s.salon_id,
                    s.nom as nom_salon,
                    s.quartier,
                    s.responsable,
                    s.telephone,
                    s.email,
                    s.code_admin,
                    s.actif,
                    s.date_creation,
                    COUNT(DISTINCT CASE WHEN co.role = 'employe' THEN co.id END) as nb_employes,
                    COUNT(DISTINCT cl.id) as nb_clients
                FROM salons s
                LEFT JOIN couturiers co ON co.salon_id = s.salon_id
                LEFT JOIN clients cl ON cl.salon_id = s.salon_id
                WHERE s.actif = TRUE OR s.actif IS NULL
                GROUP BY s.salon_id, s.nom, s.quartier, s.responsable, s.telephone, s.email, s.code_admin, s.actif, s.date_creation
                ORDER BY s.date_creation DESC NULLS LAST
            """

            cursor.execute(query_salons)
            rows_salons = cursor.fetchall()

            # Construire un dict de base par salon
            salons_map: Dict[str, Dict] = {}
            for row in rows_salons:
                salons_map[row[0]] = {
                    'salon_id': row[0],
                    'nom_salon': row[1],
                    'quartier': row[2],
                    'responsable': row[3],
                    'telephone': row[4],
                    'email': row[5],
                    'code_admin': row[6],
                    'actif': row[7],
                    'date_creation': row[8],
                    'nb_employes': row[9] or 0,
                    'nb_clients': row[10] or 0,
                    # Valeurs par défaut pour les métriques financières
                    'nb_commandes': 0,
                    'ca_total': 0.0,
                    'avances': 0.0,
                    'reste': 0.0,
                    'charges': 0.0,
                    'benefice': 0.0,
                    'taux_encaissement': 0.0,
                }

            # Préparer les filtres de période pour commandes & charges
            cmd_where = []
            ch_where = []
            cmd_params: List = []
            ch_params: List = []

            if date_debut:
                cmd_where.append("date_creation >= %s")
                ch_where.append("date_charge >= %s")
                cmd_params.append(date_debut)
                ch_params.append(date_debut)
            if date_fin:
                cmd_where.append("date_creation <= %s")
                ch_where.append("date_charge <= %s")
                cmd_params.append(date_fin)
                ch_params.append(date_fin)

            # 2) Agrégats commandes par salon (filtrés par période si fournie)
            where_cmd_clause = ""
            if cmd_where:
                where_cmd_clause = "WHERE " + " AND ".join(cmd_where)

            query_cmd = f"""
                SELECT 
                    salon_id,
                    COUNT(DISTINCT id) as nb_commandes,
                    COALESCE(SUM(prix_total), 0) as ca_total,
                    COALESCE(SUM(avance), 0) as avances,
                    COALESCE(SUM(reste), 0) as reste
                FROM commandes
                {where_cmd_clause}
                GROUP BY salon_id
            """
            cursor.execute(query_cmd, tuple(cmd_params))
            rows_cmd = cursor.fetchall()

            for row in rows_cmd:
                salon_id = row[0]
                if salon_id in salons_map:
                    salons_map[salon_id]['nb_commandes'] = row[1] or 0
                    salons_map[salon_id]['ca_total'] = float(row[2] or 0.0)
                    salons_map[salon_id]['avances'] = float(row[3] or 0.0)
                    salons_map[salon_id]['reste'] = float(row[4] or 0.0)

            # 3) Agrégats charges par salon (filtrés par période si fournie)
            where_ch_clause = ""
            if ch_where:
                where_ch_clause = "WHERE " + " AND ".join(ch_where)

            query_ch = f"""
                SELECT 
                    salon_id,
                    COALESCE(SUM(montant), 0) as charges
                FROM charges
                {where_ch_clause}
                GROUP BY salon_id
            """
            cursor.execute(query_ch, tuple(ch_params))
            rows_ch = cursor.fetchall()

            for row in rows_ch:
                salon_id = row[0]
                if salon_id in salons_map:
                    salons_map[salon_id]['charges'] = float(row[1] or 0.0)

            cursor.close()

            # Finaliser les métriques dérivées (bénéfice, taux d'encaissement)
            salons: List[Dict] = []
            for salon in salons_map.values():
                ca_total = salon['ca_total']
                charges = salon['charges']
                avances = salon['avances']

                benefice = ca_total - charges
                taux_encaissement = (avances / ca_total * 100) if ca_total > 0 else 0.0

                salon['benefice'] = benefice
                salon['taux_encaissement'] = taux_encaissement

                salons.append(salon)

            return salons
        except Exception as e:
            print(f"Erreur statistiques par salon: {e}")
            import traceback
            traceback.print_exc()
            return []
    
    def obtenir_top_salons(self, critere: str = 'ca', limit: int = 5) -> List[Dict]:
        """
        Récupère le top N des salons selon un critère
        
        Args:
            critere: 'ca' (chiffre d'affaires), 'commandes', 'clients', 'benefice'
            limit: Nombre de salons à retourner
            
        Returns:
            Liste des top salons
        """
        salons = self.obtenir_statistiques_par_salon()
        
        if critere == 'ca':
            salons.sort(key=lambda x: x['ca_total'], reverse=True)
        elif critere == 'commandes':
            salons.sort(key=lambda x: x['nb_commandes'], reverse=True)
        elif critere == 'clients':
            salons.sort(key=lambda x: x['nb_clients'], reverse=True)
        elif critere == 'benefice':
            salons.sort(key=lambda x: x['benefice'], reverse=True)
        
        return salons[:limit]
    
    def obtenir_evolution_mensuelle(
        self,
        salon_id: Optional[str] = None,
        mois: int = 6,
    ) -> List[Dict]:
        """
        Récupère l'évolution mensuelle du CA (global ou par salon)
        
        Args:
            salon_id: ID du salon (None = tous les salons)
            mois: Nombre de mois à afficher
            
        Returns:
            Liste des données mensuelles
        """
        try:
            cursor = self.db.get_connection().cursor()
            
            # Générer les dates
            today = datetime.now()
            start_date = today - timedelta(days=mois*30)
            
            where_clause = ""
            params = [start_date]
            if salon_id:
                where_clause = "AND salon_id = %s"
                params.append(salon_id)
            
            # Adapter la requête selon le SGBD
            if self.db.db_type == 'mysql':
                query = f"""
                    SELECT 
                        DATE_FORMAT(date_creation, '%Y-%m') as mois,
                        COUNT(*) as nb_commandes,
                        COALESCE(SUM(prix_total), 0) as ca,
                        COALESCE(SUM(avance), 0) as encaisse,
                        COALESCE(SUM(reste), 0) as reste
                    FROM commandes
                    WHERE date_creation >= %s {where_clause}
                    GROUP BY DATE_FORMAT(date_creation, '%Y-%m')
                    ORDER BY mois ASC
                """
            else:  # PostgreSQL
                query = f"""
                    SELECT 
                        TO_CHAR(date_creation, 'YYYY-MM') as mois,
                        COUNT(*) as nb_commandes,
                        COALESCE(SUM(prix_total), 0) as ca,
                        COALESCE(SUM(avance), 0) as encaisse,
                        COALESCE(SUM(reste), 0) as reste
                    FROM commandes
                    WHERE date_creation >= %s {where_clause}
                    GROUP BY TO_CHAR(date_creation, 'YYYY-MM')
                    ORDER BY mois ASC
                """
            
            cursor.execute(query, params)
            results = cursor.fetchall()
            cursor.close()
            
            return [
                {
                    'mois': row[0],
                    'nb_commandes': row[1],
                    'ca': float(row[2]),
                    'encaisse': float(row[3]),
                    'reste': float(row[4])
                }
                for row in results
            ]
        except Exception as e:
            print(f"Erreur évolution mensuelle: {e}")
            return []
    
    def obtenir_tous_utilisateurs(self, salon_id: Optional[str] = None) -> List[Dict]:
        """
        Liste tous les utilisateurs (filtrable par salon)
        
        Args:
            salon_id: ID du salon (None = tous)
            
        Returns:
            Liste des utilisateurs
        """
        try:
            cursor = self.db.get_connection().cursor()
            
            where_clause = ""
            params = []
            if salon_id:
                where_clause = "WHERE salon_id = %s"
                params.append(salon_id)
            
            # Filtrer les SUPER_ADMIN et ajouter la clause WHERE si nécessaire
            if salon_id:
                where_clause = "WHERE salon_id = %s AND role != 'SUPER_ADMIN'"
            else:
                where_clause = "WHERE role != 'SUPER_ADMIN'"
            
            query = f"""
                SELECT 
                    id, code_couturier, nom, prenom, role, salon_id,
                    email, telephone, actif, date_creation
                FROM couturiers
                {where_clause}
                ORDER BY role, date_creation DESC
            """
            
            cursor.execute(query, tuple(params))
            results = cursor.fetchall()
            cursor.close()
            
            return [
                {
                    'id': row[0],
                    'code_couturier': row[1],
                    'nom': row[2],
                    'prenom': row[3],
                    'role': row[4],
                    'salon_id': row[5],
                    'email': row[6],
                    'telephone': row[7],
                    'actif': bool(row[8]),
                    'date_creation': row[9]
                }
                for row in results
            ]
        except Exception as e:
            print(f"Erreur liste utilisateurs: {e}")
            return []
    
    def obtenir_toutes_commandes(
        self,
        salon_id: Optional[str] = None,
        limit: int = 100,
        date_debut: Optional[datetime] = None,
        date_fin: Optional[datetime] = None,
    ) -> List[Dict]:
        """
        Liste toutes les commandes (filtrable par salon)
        
        Args:
            salon_id: ID du salon (None = toutes)
            limit: Nombre maximum de commandes
            
        Returns:
            Liste des commandes
        """
        try:
            cursor = self.db.get_connection().cursor()
            
            where_parts = []
            params: List = []

            if salon_id:
                where_parts.append("cmd.salon_id = %s")
                params.append(salon_id)

            if date_debut:
                where_parts.append("cmd.date_creation >= %s")
                params.append(date_debut)

            if date_fin:
                where_parts.append("cmd.date_creation <= %s")
                params.append(date_fin)

            where_clause = ""
            if where_parts:
                where_clause = "WHERE " + " AND ".join(where_parts)
            
            # Utiliser LIMIT avec la bonne syntaxe selon le SGBD
            if self.db.db_type == 'mysql':
                limit_clause = "LIMIT %s"
            else:  # PostgreSQL
                limit_clause = "LIMIT %s"
            
            params.append(limit)
            
            query = f"""
                SELECT 
                    cmd.id, cmd.modele, cmd.prix_total, cmd.avance, cmd.reste,
                    cmd.statut, cmd.date_creation, cmd.salon_id,
                    cl.nom as client_nom, cl.prenom as client_prenom,
                    co.code_couturier, co.nom as couturier_nom
                FROM commandes cmd
                JOIN clients cl ON cmd.client_id = cl.id
                JOIN couturiers co ON cmd.couturier_id = co.id
                {where_clause}
                ORDER BY cmd.date_creation DESC
                {limit_clause}
            """
            
            cursor.execute(query, tuple(params))
            results = cursor.fetchall()
            cursor.close()
            
            return [
                {
                    'id': row[0],
                    'modele': row[1],
                    'prix_total': float(row[2]),
                    'avance': float(row[3]),
                    'reste': float(row[4]),
                    'statut': row[5],
                    'date_creation': row[6],
                    'salon_id': row[7],
                    'client_nom': row[8],
                    'client_prenom': row[9],
                    'couturier_code': row[10],
                    'couturier_nom': row[11]
                }
                for row in results
            ]
        except Exception as e:
            print(f"Erreur liste commandes: {e}")
            return []
    
    def generer_rapport_complet(self, salon_id: Optional[str] = None) -> Dict:
        """
        Génère un rapport complet (export JSON/CSV)
        
        Args:
            salon_id: ID du salon (None = rapport global)
            
        Returns:
            Dict avec toutes les données du rapport
        """
        rapport = {
            'date_generation': datetime.now().isoformat(),
            'salon_id': salon_id,
            'type': 'global' if not salon_id else 'salon_specifique',
            'statistiques': self.obtenir_statistiques_globales() if not salon_id else None,
            'salons': self.obtenir_statistiques_par_salon(),
            'utilisateurs': self.obtenir_tous_utilisateurs(salon_id),
            'commandes': self.obtenir_toutes_commandes(salon_id, limit=1000),
            'evolution_mensuelle': self.obtenir_evolution_mensuelle(salon_id)
        }
        
        return rapport

