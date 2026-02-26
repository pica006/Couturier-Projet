"""
Service de rappels automatiques (J-2 avant livraison).
Envoie email sans intervention manuelle.
"""
from datetime import datetime, timedelta

from models.database import CommandeModel
from models.salon_model import SalonModel
from controllers.email_controller import EmailController


def executer_rappels_automatiques(db_connection) -> tuple:
    """
    Envoie les rappels (email + SMS) pour les livraisons dans 2 jours.
    Appelé automatiquement au chargement du calendrier.
    
    Returns:
        (nb_envoyes, message)
    """

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
        return 0, "Aucun rappel a envoyer pour aujourd'hui."

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

    if envoyes > 0:
        msg = f"{envoyes} rappel(s) envoyé(s) automatiquement par email."
        if erreurs:
            msg += f" Non envoyés: {', '.join(erreurs[:5])}"
        return envoyes, msg
    return 0, f"Aucun rappel envoyé. Vérifiez la config email du salon (SMTP). Erreurs: {', '.join(erreurs[:5])}"
