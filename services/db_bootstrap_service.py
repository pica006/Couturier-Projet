"""
Bootstrap DB centralise pour limiter la logique de connexion dans les vues.
"""

from typing import Dict, Tuple, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from models.database import DatabaseConnection


def validate_required_config(config: Dict, required_keys: Tuple[str, ...]) -> list[str]:
    missing = []
    for key in required_keys:
        if not config.get(key):
            missing.append(key)
    return missing


def _appliquer_migrations_schema(db_connection) -> None:
    """
    Applique les migrations de schéma incrémentales.
    Chaque bloc est indépendant (try/except) pour ne jamais bloquer le démarrage.
    """
    try:
        conn = db_connection.get_connection()
        cursor = conn.cursor()

        # ── POINT D-1 : salon_id dans historique_commandes ──────────────────
        try:
            cursor.execute("""
                ALTER TABLE historique_commandes
                ADD COLUMN IF NOT EXISTS salon_id VARCHAR(50) NULL
                REFERENCES salons(salon_id) ON DELETE SET NULL
            """)
            conn.commit()
        except Exception as e:
            try: conn.rollback()
            except Exception: pass
            print(f"Migration historique salon_id (ignorée): {e}")

        try:
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_historique_salon_id
                ON historique_commandes(salon_id)
            """)
            conn.commit()
        except Exception as e:
            try: conn.rollback()
            except Exception: pass

        try:
            cursor.execute("""
                UPDATE historique_commandes h
                SET salon_id = c.salon_id
                FROM commandes c
                WHERE h.commande_id = c.id
                  AND h.salon_id IS NULL
                  AND c.salon_id IS NOT NULL
            """)
            conn.commit()
        except Exception as e:
            try: conn.rollback()
            except Exception: pass
            print(f"Peuplement historique.salon_id (ignoré): {e}")

        # ── POINT D-2 : peupler charges.salon_id NULL ────────────────────────
        try:
            cursor.execute("""
                UPDATE charges ch
                SET salon_id = co.salon_id
                FROM couturiers co
                WHERE ch.couturier_id = co.id
                  AND ch.salon_id IS NULL
                  AND co.salon_id IS NOT NULL
            """)
            conn.commit()
        except Exception as e:
            try: conn.rollback()
            except Exception: pass
            print(f"Peuplement charges.salon_id (ignoré): {e}")

        # ── POINT D-3 : peupler clients.salon_id NULL ────────────────────────
        try:
            cursor.execute("""
                UPDATE clients cl
                SET salon_id = co.salon_id
                FROM couturiers co
                WHERE cl.couturier_id = co.id
                  AND cl.salon_id IS NULL
                  AND co.salon_id IS NOT NULL
            """)
            conn.commit()
        except Exception as e:
            try: conn.rollback()
            except Exception: pass
            print(f"Peuplement clients.salon_id (ignoré): {e}")

        # ── POINT F : colonnes de configuration par salon ────────────────────
        for ddl in [
            "ALTER TABLE salons ADD COLUMN IF NOT EXISTS max_habits_par_jour INTEGER DEFAULT NULL",
            "ALTER TABLE salons ADD COLUMN IF NOT EXISTS delais_par_modele TEXT DEFAULT NULL",
            "ALTER TABLE salons ADD COLUMN IF NOT EXISTS pdf_theme_color VARCHAR(7) DEFAULT NULL",
        ]:
            try:
                cursor.execute(ddl)
                conn.commit()
            except Exception as e:
                try: conn.rollback()
                except Exception: pass
                print(f"Migration colonne salons (ignorée): {e}")

        cursor.close()
    except Exception as e:
        print(f"Erreur générale migrations schéma (ignorée): {e}")
        try: db_connection.get_connection().rollback()
        except Exception: pass


def connect_and_initialize(config: Dict) -> Tuple[bool, Optional["DatabaseConnection"], str]:
    """
    Connecte a la base puis initialise les tables metier.
    Retourne: (ok, db_connection, message_erreur).
    """
    try:
        # Imports paresseux pour eviter le chargement des dependances DB/PDF au demarrage.
        from models.database import DatabaseConnection, ChargesModel
        from controllers.auth_controller import AuthController
        from controllers.commande_controller import CommandeController

        db_connection = DatabaseConnection("postgresql", config)
        if not db_connection.connect():
            return False, None, str(db_connection.last_error or "Erreur inconnue de connexion PostgreSQL")

        auth_controller = AuthController(db_connection)
        auth_controller.initialiser_tables()

        commande_controller = CommandeController(db_connection)
        commande_controller.initialiser_tables()

        charges_model = ChargesModel(db_connection)
        charges_model.creer_tables()

        _appliquer_migrations_schema(db_connection)

        return True, db_connection, ""
    except Exception as e:
        return False, None, f"Echec initialisation DB: {e}"
