"""
Utilitaires pour la gestion des permissions multi-salon
"""
import streamlit as st
from typing import Dict, Optional


def obtenir_permissions_utilisateur(user_data: Dict) -> Dict:
    """
    Détermine les permissions de l'utilisateur selon son rôle
    
    Args:
        user_data: Données de l'utilisateur connecté (depuis session_state)
        
    Returns:
        Dict avec les permissions
    """
    role = user_data.get('role', 'employe')
    salon_id = user_data.get('salon_id')
    
    if role == 'SUPER_ADMIN':
        return {
            'can_view_all_salons': True,
            'can_create_salon': True,
            'can_create_admin': True,
            'can_create_employe': False,  # Le SUPER_ADMIN crée des admins, pas des employés
            'can_switch_salon': True,
            'can_manage_all_data': True,
            'current_salon_filter': None,  # None = voir tout par défaut
            'role_display': '👑 Super Administrateur'
        }
    elif role == 'admin':
        return {
            'can_view_all_salons': False,
            'can_create_salon': False,
            'can_create_admin': False,
            'can_create_employe': True,
            'can_switch_salon': False,
            'can_manage_all_data': False,
            'current_salon_filter': salon_id,
            'role_display': f'🏢 Administrateur (Salon {salon_id})'
        }
    else:  # employe
        return {
            'can_view_all_salons': False,
            'can_create_salon': False,
            'can_create_admin': False,
            'can_create_employe': False,
            'can_switch_salon': False,
            'can_manage_all_data': False,
            'current_salon_filter': salon_id,
            'role_display': f'👤 Employé (Salon {salon_id})'
        }


def get_salon_filter() -> Optional[int]:
    """
    Récupère le filtre salon actuel selon l'utilisateur connecté
    
    Returns:
        salon_id pour filtrer, ou None pour voir tout (SUPER_ADMIN)
    """
    if 'couturier_data' not in st.session_state:
        return None
    
    user = st.session_state.couturier_data
    role = user.get('role', 'employe')
    
    if role == 'SUPER_ADMIN':
        # Si le SUPER_ADMIN s'est "placé" sur un salon
        return st.session_state.get('active_salon_filter', None)
    else:
        # Admin ou employé : toujours filtrer par leur salon
        return user.get('salon_id')


def est_super_admin() -> bool:
    """Vérifie si l'utilisateur est SUPER_ADMIN"""
    if 'couturier_data' not in st.session_state:
        return False
    role = st.session_state.couturier_data.get('role', '')
    # Normaliser le rôle pour gérer les variations de casse
    role_normalise = str(role).upper().strip()
    return role_normalise == 'SUPER_ADMIN'


def peut_creer_salon() -> bool:
    """Vérifie si l'utilisateur peut créer des salons"""
    return est_super_admin()


def peut_creer_admin() -> bool:
    """Vérifie si l'utilisateur peut créer des admins"""
    return est_super_admin()


def peut_creer_employe() -> bool:
    """Vérifie si l'utilisateur peut créer des employés"""
    if 'couturier_data' not in st.session_state:
        return False
    role = st.session_state.couturier_data.get('role')
    return role == 'admin'

