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

        return True, db_connection, ""
    except Exception as e:
        return False, None, f"Echec initialisation DB: {e}"
