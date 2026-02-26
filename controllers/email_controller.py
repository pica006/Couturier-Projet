"""
Contrôleur d'envoi d'e-mails (SMTP)
"""
import os
import smtplib
from email.message import EmailMessage
from typing import Optional, List
from pathlib import Path
import logging

from config import EMAIL_CONFIG


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class EmailController:
    """Gère l'envoi d'e-mails via SMTP (multi-salons).

    PRIORITÉ :
    1. Configuration spécifique au salon (passée en paramètre)
    2. Configuration globale EMAIL_CONFIG / variables d'environnement (fallback)
    """

    def __init__(self, smtp_config: Optional[dict] = None):
        # Base = configuration globale (fallback)
        base = dict(EMAIL_CONFIG) if EMAIL_CONFIG else {}

        # Surcharger avec la configuration spécifique au salon si fournie
        if smtp_config:
            for key, value in smtp_config.items():
                if value not in (None, ""):
                    base[key] = value

        # Charger config finale
        self.enabled = bool(base.get("enabled", False))
        self.host = base.get("host", "") or os.getenv("EMAIL_HOST", "")
        self.port = int(base.get("port", 587) or 587)
        self.user = base.get("user", "") or os.getenv("EMAIL_USER", "")
        self.password = base.get("password", "") or os.getenv("EMAIL_PASSWORD", "")
        self.from_email = base.get("from_email", "") or os.getenv("EMAIL_FROM", self.user)
        self.use_tls = bool(base.get("use_tls", True))
        self.use_ssl = bool(base.get("use_ssl", False))

    def _verifier_configuration(self) -> bool:
        return self.enabled and self.host and self.port and self.user and self.password and self.from_email

    def verifier_configuration(self) -> tuple[bool, str]:
        """Retourne (ok, message) pour afficher une explication claire en UI."""
        if not self.enabled:
            return False, "Envoi email désactivé dans la configuration."
        missing = []
        if not self.host:
            missing.append("host")
        if not self.port:
            missing.append("port")
        if not self.user:
            missing.append("user")
        if not self.password:
            missing.append("password")
        if not self.from_email:
            missing.append("from_email")
        if missing:
            return False, f"Configuration email incomplète : {', '.join(missing)}."
        return True, "Configuration email OK."

    def envoyer_email(self, to_email: str, subject: str, body: str,
                      attachments: Optional[List[str]] = None) -> bool:
        """
        Envoie un e-mail avec pièces jointes optionnelles.
        """
        try:
            if not self._verifier_configuration():
                logger.warning("⚠️ Configuration email manquante ou désactivée.")
                return False

            if not to_email:
                return False

            msg = EmailMessage()
            msg["Subject"] = subject
            msg["From"] = self.from_email
            msg["To"] = to_email
            msg.set_content(body)

            # Ajouter pièces jointes
            for file_path in attachments or []:
                path = Path(file_path)
                if not path.is_file():
                    continue
                with open(path, "rb") as f:
                    data = f.read()
                msg.add_attachment(
                    data,
                    maintype="application",
                    subtype="pdf",
                    filename=path.name
                )

            # Connexion SMTP
            if self.use_ssl:
                with smtplib.SMTP_SSL(self.host, self.port) as server:
                    server.login(self.user, self.password)
                    server.send_message(msg)
            else:
                with smtplib.SMTP(self.host, self.port) as server:
                    server.ehlo()
                    if self.use_tls:
                        server.starttls()
                        server.ehlo()
                    server.login(self.user, self.password)
                    server.send_message(msg)

            logger.info(f"✅ Email envoyé à {to_email}")
            return True

        except Exception as e:
            logger.error(f"❌ Erreur envoi email: {e}")
            return False

    def envoyer_email_avec_message(self, to_email: str, subject: str, body: str,
                                   attachments: Optional[List[str]] = None) -> tuple[bool, str]:
        """Envoie un e-mail et retourne un message explicite pour l'UI."""
        ok_config, msg_config = self.verifier_configuration()
        if not ok_config:
            return False, msg_config
        if not to_email:
            return False, "Adresse email du client manquante."
        try:
            succes, erreur = self._envoyer_email_detail(to_email, subject, body, attachments)
            if succes:
                return True, "Email envoyé avec succès."
            if erreur:
                return False, erreur
            return False, "Email non envoyé. Vérifiez la configuration SMTP et la connexion."
        except Exception as e:
            return False, f"Erreur lors de l'envoi de l'email : {e}"

    def _envoyer_email_detail(self, to_email: str, subject: str, body: str,
                              attachments: Optional[List[str]] = None) -> tuple[bool, str]:
        """Envoie un e-mail et retourne (succes, erreur) sans masquer l'exception SMTP."""
        msg = EmailMessage()
        msg["Subject"] = subject
        msg["From"] = self.from_email
        msg["To"] = to_email
        msg.set_content(body)

        for file_path in attachments or []:
            path = Path(file_path)
            if not path.is_file():
                continue
            with open(path, "rb") as f:
                data = f.read()
            msg.add_attachment(
                data,
                maintype="application",
                subtype="pdf",
                filename=path.name
            )

        try:
            if self.use_ssl:
                with smtplib.SMTP_SSL(self.host, self.port) as server:
                    server.login(self.user, self.password)
                    server.send_message(msg)
            else:
                with smtplib.SMTP(self.host, self.port) as server:
                    server.ehlo()
                    if self.use_tls:
                        server.starttls()
                        server.ehlo()
                    server.login(self.user, self.password)
                    server.send_message(msg)
            logger.info(f"✅ Email envoyé à {to_email}")
            return True, ""
        except smtplib.SMTPAuthenticationError as e:
            return False, (
                "Authentification SMTP échouée. Pour Gmail, utilisez un mot de passe "
                "d'application et vérifiez l'email/mot de passe."
            )
        except smtplib.SMTPConnectError as e:
            return False, f"Impossible de se connecter au serveur SMTP ({self.host}:{self.port})."
        except smtplib.SMTPException as e:
            return False, f"Erreur SMTP: {e}"
        except Exception as e:
            return False, f"Erreur inattendue: {e}"

