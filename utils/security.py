"""
Utilitaires de securite pour la gestion des mots de passe.
"""

from typing import Optional

import bcrypt


def hash_password(password: str) -> str:
    """
    Hash un mot de passe en bcrypt.
    """
    if not isinstance(password, str) or not password:
        raise ValueError("Le mot de passe ne peut pas etre vide.")
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(plain_password: str, stored_password: Optional[str]) -> bool:
    """
    Verifie un mot de passe avec retro-compatibilite:
    - Si le mot de passe stocke est bcrypt, verification bcrypt.
    - Sinon, comparaison directe (legacy), pour migrer progressivement.
    """
    if not plain_password or not stored_password:
        return False

    stored = str(stored_password)
    # Prefixes bcrypt usuels: $2a$, $2b$, $2y$
    if stored.startswith("$2"):
        try:
            return bcrypt.checkpw(plain_password.encode("utf-8"), stored.encode("utf-8"))
        except Exception:
            return False
    return plain_password == stored
