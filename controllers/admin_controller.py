"""
Contrôleur administration (orchestration UI -> modèles).
"""

from models.database import DatabaseConnection, ClientModel


class AdminController:
    def __init__(self, db_connection: DatabaseConnection):
        self.client_model = ClientModel(db_connection)

    def compter_clients_distincts_salon(self, salon_id: str) -> int:
        return self.client_model.compter_clients_distincts_salon(salon_id)
