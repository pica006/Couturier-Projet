"""
Service de rappels automatiques (J-2 avant livraison).
Envoie email + SMS sans intervention manuelle.
"""
import os
from datetime import datetime, timedelta
from collections import defaultdict

from models.database import CommandeModel
from models.salon_model import SalonModel
from controllers.email_controller import EmailController

# Fichier pour éviter d'envoyer 2 fois le même jour
RAPPELS_LAST_RUN_FILE = os.path.join(
    os.path.dirname(os.path.dirname(__file__)), "data", "rappels_last_run.txt"
)


def _date_aujourd_hui_str() -> str:
    return datetime.now().strftime("%Y-%m-%d")


def _deja_execute_aujourd_hui() -> bool:
    """Vérifie si les rappels ont déjà été envoyés aujourd'hui."""
    try:
        if os.path.exists(RAPPELS_LAST_RUN_FILE):
            with open(RAPPELS_LAST_RUN_FILE, "r") as f:
                return f.read().strip() == _date_aujourd_hui_str()
    except Exception:
        pass
    return False


def _marquer_execute():
    """Marque que les rappels ont été envoyés aujourd'hui."""
    try:
        os.makedirs(os.path.dirname(RAPPELS_LAST_RUN_FILE), exist_ok=True)
        with open(RAPPELS_LAST_RUN_FILE, "w") as f:
            f.write(_date_aujourd_hui_str())
    except Exception:
        pass


def executer_rappels_automatiques(db_connection) -> tuple:
    """
    Envoie les rappels (email + SMS) pour les livraisons dans 2 jours.
    Appelé automatiquement au chargement du calendrier.
    
    Returns:
        (nb_envoyes, message) ou (0, None) si déjà exécuté / rien à faire
    """
    if _deja_execute_aujourd_hui():
        return 0, None

    aujourd_hui = datetime.now().date()
    date_rappel = aujourd_hui + timedelta(days=2)

    commande_model = CommandeModel(db_connection)
    salon_model = SalonModel(db_connection)
    commande_model.creer_table_rappels_livraison()

    # Toutes les commandes à rappeler (tous salons, sans filtre)
    commandes = commande_model.lister_commandes_calendrier(
        date_debut=date_rappel,
        date_fin=date_rappel,
        couturier_id=None,
        tous_les_couturiers=True,
        salon_id=None,
    )

    commandes_a_rappeler = [
        c for c in commandes
        if not commande_model.rappel_deja_envoye(c["id"], c["date_livraison"])
    ]

    if not commandes_a_rappeler:
        _marquer_execute()
        return 0, None

    envoyes = 0
    erreurs = []

    for c in commandes_a_rappeler:
        date_liv = c.get("date_livraison")
        date_str = date_liv.strftime("%d/%m/%Y") if hasattr(date_liv, "strftime") else str(date_liv)
        msg_texte = (
            f"Rappel: Livraison le {date_str} - {c.get('modele', 'N/A')} - "
            f"Client: {c.get('client_prenom', '')} {c.get('client_nom', '')}"
        )

        salon_id = c.get("couturier_salon_id")
        ok_envoye = False

        # Email uniquement (gratuit avec SMTP)
        if salon_id:
            smtp_config = salon_model.obtenir_config_email_salon(salon_id)
            if smtp_config:
                email_ctrl = EmailController(smtp_config)
                to_email = c.get("couturier_email")
                if to_email and email_ctrl.envoyer_email(
                    to_email,
                    f"Rappel: Livraison le {date_str}",
                    f"Bonjour {c.get('couturier_prenom', '')} {c.get('couturier_nom', '')},\n\n{msg_texte}\n\nCordialement.",
                ):
                    ok_envoye = True

        if ok_envoye:
            commande_model.enregistrer_rappel_envoye(c["id"], c["couturier_id"], date_liv)
            envoyes += 1
        else:
            erreurs.append(f"#{c['id']}")

    _marquer_execute()

    if envoyes > 0:
        msg = f"{envoyes} rappel(s) envoyé(s) automatiquement par email."
        if erreurs:
            msg += f" Non envoyés: {', '.join(erreurs[:5])}"
        return envoyes, msg
    return 0, f"Aucun rappel envoyé. Vérifiez la config email du salon (SMTP). Erreurs: {', '.join(erreurs[:5])}"
