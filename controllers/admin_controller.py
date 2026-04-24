"""
Contrôleur administration (orchestration UI -> modèles).
"""

from datetime import datetime, date
from typing import Any, Dict, List, Optional

import pandas as pd

from models.database import (
    DatabaseConnection,
    ClientModel,
    ChargesModel,
    CouturierModel,
)
from models.commande_model import CommandeModel
from models.salon_model import SalonModel
from utils.role_utils import obtenir_salon_id

# Barème d'impôts (aligné sur admin_view / mes_charges_view)
TRANCHES_IMPOTS = [
    {'min': 0, 'max': 500000, 'impot': 5000},
    {'min': 500000, 'max': 1000000, 'impot': 75000},
    {'min': 1000000, 'max': 1500000, 'impot': 100000},
    {'min': 1500000, 'max': 2000000, 'impot': 125000},
    {'min': 2000000, 'max': 2500000, 'impot': 150000},
    {'min': 2500000, 'max': 5000000, 'impot': 375000},
    {'min': 5000000, 'max': 10000000, 'impot': 750000},
    {'min': 10000000, 'max': 20000000, 'impot': 1250000},
    {'min': 20000000, 'max': 30000000, 'impot': 2500000},
    {'min': 30000000, 'max': 50000000, 'impot': 5000000},
]


class AdminController:
    def __init__(self, db_connection: DatabaseConnection):
        self.db = db_connection
        self.client_model = ClientModel(db_connection)
        self.charges_model = ChargesModel(db_connection)
        self.commande_model = CommandeModel(db_connection)
        self.couturier_model = CouturierModel(db_connection)

    def compter_clients_distincts_salon(self, salon_id: str) -> int:
        return self.client_model.compter_clients_distincts_salon(salon_id)

    def resoudre_salon_id_admin(self, admin_data: Optional[Dict]) -> Optional[str]:
        try:
            salon_id = obtenir_salon_id(admin_data)
            if salon_id:
                return salon_id
            code_admin = (admin_data or {}).get("code_couturier")
            if self.db and code_admin:
                salon_model = SalonModel(self.db)
                salon = salon_model.obtenir_salon_by_code_admin(code_admin)
                if salon and salon.get("salon_id"):
                    return str(salon.get("salon_id")).strip()
        except Exception:
            pass
        return None

    def obtenir_stats_dashboard(
        self, couturier_data: Optional[Dict], salon_id_admin: Optional[str]
    ) -> Dict[str, Any]:
        try:
            return {
                "salon_id": salon_id_admin,
                "couturier_id": (couturier_data or {}).get("id"),
                "est_admin_user": True,
                "key_prefix": "admin_tdb",
            }
        except Exception:
            return {
                "salon_id": salon_id_admin,
                "couturier_id": None,
                "est_admin_user": True,
                "key_prefix": "admin_tdb",
            }

    def estimer_ca_commandes_periode(
        self,
        commande_model: CommandeModel,
        salon_id: str,
        date_debut: date,
        date_fin: date,
    ) -> float:
        try:
            commandes = commande_model.lister_commandes(
                None, tous_les_couturiers=True, salon_id=salon_id
            )
            if not commandes:
                return 0.0
            df_cmd = pd.DataFrame(commandes)
            if "date_creation" not in df_cmd.columns:
                return 0.0
            df_cmd["date_creation"] = pd.to_datetime(df_cmd["date_creation"])
            mask_cmd = (
                (df_cmd["date_creation"].dt.date >= date_debut)
                & (df_cmd["date_creation"].dt.date <= date_fin)
            )
            df_cmd = df_cmd[mask_cmd]
            if "prix_total" not in df_cmd.columns:
                return 0.0
            return float(df_cmd["prix_total"].sum())
        except Exception:
            return 0.0

    def calculer_impots(
        self,
        charges_model: ChargesModel,
        salon_id: str,
        date_debut: date,
        date_fin: date,
        ca_retenu: float,
    ) -> Dict[str, Any]:
        try:
            date_debut_dt = datetime.combine(date_debut, datetime.min.time())
            date_fin_dt = datetime.combine(date_fin, datetime.max.time())
            total_charges = charges_model.total_charges(
                couturier_id=None,
                date_debut=date_debut_dt,
                date_fin=date_fin_dt,
                tous_les_couturiers=True,
                salon_id=salon_id,
            )
            impot = 0.0
            for tranche in TRANCHES_IMPOTS:
                if tranche['min'] <= ca_retenu <= tranche['max']:
                    impot = float(tranche['impot'])
                    break
            if ca_retenu > TRANCHES_IMPOTS[-1]['max']:
                impot = float(TRANCHES_IMPOTS[-1]['impot'])
            benefice_net = float(ca_retenu) - float(total_charges) - impot
            charges_list = charges_model.lister_charges(
                couturier_id=None,
                limit=10000,
                tous_les_couturiers=True,
                salon_id=salon_id,
            )
            df_charges = pd.DataFrame(charges_list) if charges_list else pd.DataFrame()
            if not df_charges.empty and "date_charge" in df_charges.columns:
                df_charges["date_charge"] = pd.to_datetime(df_charges["date_charge"])
                mask = (
                    (df_charges["date_charge"].dt.date >= date_debut)
                    & (df_charges["date_charge"].dt.date <= date_fin)
                )
                df_charges = df_charges[mask]
            return {
                "total_charges": float(total_charges),
                "impot": impot,
                "benefice_net": benefice_net,
                "df_charges": df_charges,
            }
        except Exception:
            return {
                "total_charges": 0.0,
                "impot": 0.0,
                "benefice_net": 0.0,
                "df_charges": pd.DataFrame(),
            }

    def operations_utilisateurs(
        self, couturier_model: CouturierModel, admin_data: Optional[Dict]
    ) -> Dict[str, Any]:
        try:
            salon_id = self.resoudre_salon_id_admin(admin_data)
            return {
                "ok": bool(salon_id),
                "salon_id": salon_id,
                "admin_id": (admin_data or {}).get("id"),
            }
        except Exception:
            return {
                "ok": False,
                "salon_id": None,
                "admin_id": (admin_data or {}).get("id"),
            }

    def executer_creation_utilisateur(
        self,
        couturier_model: CouturierModel,
        admin_data: Optional[Dict],
        code_couturier: str,
        password: str,
        password_confirm: str,
        nom: str,
        prenom: str,
        role: str,
        email: Optional[str],
        telephone: Optional[str],
    ) -> Dict[str, Any]:
        try:
            erreurs: List[str] = []
            if not code_couturier or len(code_couturier.strip()) < 3:
                erreurs.append("Le code de connexion doit contenir au moins 3 caractères")
            if not nom or len(nom.strip()) < 2:
                erreurs.append("Le nom doit contenir au moins 2 caractères")
            if not prenom or len(prenom.strip()) < 2:
                erreurs.append("Le prénom doit contenir au moins 2 caractères")
            if not password or len(password) < 4:
                erreurs.append("Le mot de passe doit contenir au moins 4 caractères")
            if password != password_confirm:
                erreurs.append("Les mots de passe ne correspondent pas")
            if erreurs:
                return {"ok": False, "validation_errors": erreurs}

            code_u = code_couturier.strip().upper()
            existe, _ = couturier_model.verifier_code(code_u)
            if existe:
                return {
                    "ok": False,
                    "validation_errors": [
                        f"Le code '{code_couturier}' existe déjà. Veuillez en choisir un autre."
                    ],
                }

            salon_id = self.resoudre_salon_id_admin(admin_data) or obtenir_salon_id(admin_data)
            if not salon_id:
                return {
                    "ok": False,
                    "flash_error": (
                        "❌ Impossible de déterminer le salon de votre compte admin. "
                        "Déconnectez-vous puis reconnectez-vous."
                    ),
                    "rerun": True,
                }

            user_id = couturier_model.creer_utilisateur(
                code_couturier=code_u,
                password=password,
                nom=nom.strip(),
                prenom=prenom.strip(),
                role=role,
                email=email.strip() if email else None,
                telephone=telephone.strip() if telephone else None,
                salon_id=salon_id,
            )

            if user_id is not None:
                return {
                    "ok": True,
                    "flash_success": f"✅ Utilisateur '{code_u}' créé avec succès !",
                    "rerun": True,
                }
            detail = getattr(couturier_model, "last_error", None)
            if detail:
                return {
                    "ok": False,
                    "flash_error": f"❌ Erreur lors de la création de l'utilisateur : {detail}",
                    "rerun": True,
                }
            return {
                "ok": False,
                "flash_error": "❌ Erreur lors de la création de l'utilisateur",
                "rerun": True,
            }
        except Exception as e:
            return {
                "ok": False,
                "flash_error": f"❌ Exception inattendue pendant la création : {e}",
                "rerun": True,
            }

    def modifier_role_utilisateur(
        self,
        couturier_model: CouturierModel,
        user_id: int,
        role_actuel: str,
        nouveau_role: str,
    ) -> Dict[str, Any]:
        try:
            if nouveau_role == role_actuel:
                return {"ok": True, "unchanged": True}
            if couturier_model.modifier_role(user_id, nouveau_role):
                return {
                    "ok": True,
                    "flash_success": "✅ Rôle modifié avec succès !",
                    "rerun": True,
                }
            return {
                "ok": False,
                "flash_error": "❌ Erreur lors de la modification du rôle",
                "rerun": True,
            }
        except Exception as e:
            return {"ok": False, "flash_error": f"❌ {e}", "rerun": True}

    def desactiver_utilisateur_salon(
        self, couturier_model: CouturierModel, admin_id: Any, selected_user: Dict
    ) -> Dict[str, Any]:
        try:
            if selected_user.get("id") == admin_id:
                return {
                    "ok": False,
                    "flash_error": "❌ Vous ne pouvez pas désactiver votre propre compte.",
                    "rerun": True,
                }
            ok = couturier_model.mettre_a_jour_statut_actif(selected_user["id"], False)
            code = selected_user.get("code_couturier", "")
            if ok:
                return {
                    "ok": True,
                    "flash_success": f"✅ Utilisateur {code} désactivé.",
                    "rerun": True,
                }
            return {
                "ok": False,
                "flash_error": "❌ Erreur lors de la désactivation de l'utilisateur.",
                "rerun": True,
            }
        except Exception as e:
            return {"ok": False, "flash_error": f"❌ {e}", "rerun": True}

    def reactiver_utilisateur_salon(
        self, couturier_model: CouturierModel, selected_user: Dict
    ) -> Dict[str, Any]:
        try:
            ok = couturier_model.mettre_a_jour_statut_actif(selected_user["id"], True)
            code = selected_user.get("code_couturier", "")
            if ok:
                return {
                    "ok": True,
                    "flash_success": f"✅ Utilisateur {code} réactivé.",
                    "rerun": True,
                }
            return {
                "ok": False,
                "flash_error": "❌ Erreur lors de la réactivation de l'utilisateur.",
                "rerun": True,
            }
        except Exception as e:
            return {"ok": False, "flash_error": f"❌ {e}", "rerun": True}

    def supprimer_utilisateur_salon(
        self, couturier_model: CouturierModel, admin_id: Any, selected_user: Dict
    ) -> Dict[str, Any]:
        try:
            if selected_user.get("id") == admin_id:
                return {
                    "ok": False,
                    "flash_error": "❌ Vous ne pouvez pas supprimer votre propre compte.",
                    "rerun": True,
                }
            if selected_user.get("role") == "admin":
                return {
                    "ok": False,
                    "flash_error": (
                        "❌ Suppression d'un autre admin bloquée. Changez d'abord son rôle en employé."
                    ),
                    "rerun": True,
                }
            ok = couturier_model.supprimer_utilisateur(selected_user["id"])
            code = selected_user.get("code_couturier", "")
            if ok:
                return {
                    "ok": True,
                    "flash_success": f"✅ Utilisateur {code} supprimé.",
                    "rerun": True,
                }
            return {
                "ok": False,
                "flash_error": "❌ Erreur lors de la suppression de l'utilisateur.",
                "rerun": True,
            }
        except Exception as e:
            return {"ok": False, "flash_error": f"❌ {e}", "rerun": True}

    def executer_reinitialisation_mot_de_passe(
        self,
        couturier_model: CouturierModel,
        user_id: int,
        nouveau_password: str,
        password_confirm: str,
    ) -> Dict[str, Any]:
        try:
            erreurs: List[str] = []
            if not nouveau_password or len(nouveau_password) < 4:
                erreurs.append("Le mot de passe doit contenir au moins 4 caractères")
            if nouveau_password != password_confirm:
                erreurs.append("Les mots de passe ne correspondent pas")
            if erreurs:
                return {"ok": False, "validation_errors": erreurs}
            if couturier_model.reinitialiser_mot_de_passe(user_id, nouveau_password):
                return {
                    "ok": True,
                    "flash_success": (
                        "✅ Mot de passe réinitialisé avec succès ! "
                        "L'utilisateur devra utiliser ce nouveau mot de passe pour se connecter."
                    ),
                    "rerun": True,
                }
            return {
                "ok": False,
                "flash_error": "❌ Erreur lors de la réinitialisation du mot de passe",
                "rerun": True,
            }
        except Exception as e:
            return {"ok": False, "flash_error": f"❌ {e}", "rerun": True}
