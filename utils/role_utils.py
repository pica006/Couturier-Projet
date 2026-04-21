"""
Utilitaires pour la gestion des rôles (admin/employe)
"""
from typing import Optional


def est_admin(couturier_data: Optional[dict]) -> bool:
    """
    Vérifie si l'utilisateur connecté est un administrateur
    
    Args:
        couturier_data: Données du couturier depuis st.session_state.couturier_data
        
    Returns:
        True si admin, False sinon
    """
    if not couturier_data:
        return False
    
    role = couturier_data.get('role', 'employe')
    return role == 'admin'


def est_employe(couturier_data: Optional[dict]) -> bool:
    """
    Vérifie si l'utilisateur connecté est un employé
    
    Args:
        couturier_data: Données du couturier depuis st.session_state.couturier_data
        
    Returns:
        True si employé, False sinon
    """
    if not couturier_data:
        return False
    
    role = couturier_data.get('role', 'employe')
    return role == 'employe'


def obtenir_couturier_id(couturier_data: Optional[dict]) -> Optional[int]:
    """
    Récupère l'ID du couturier connecté
    
    Args:
        couturier_data: Données du couturier depuis st.session_state.couturier_data
        
    Returns:
        ID du couturier ou None
    """
    if not couturier_data:
        return None
    
    return couturier_data.get('id')


def obtenir_salon_id(couturier_data: Optional[dict]) -> Optional[str]:
    """
    Récupère l'ID du salon auquel appartient l'utilisateur connecté (multi-tenant)
    
    Args:
        couturier_data: Données du couturier depuis st.session_state.couturier_data
        
    Returns:
        ID du salon (VARCHAR) ou None
    """
    if not couturier_data:
        return None
    
    salon_id = couturier_data.get('salon_id')
    if salon_id is not None and str(salon_id).strip() != '':
        return str(salon_id).strip()
    return None


def obtenir_salon_id_resolu(couturier_data: Optional[dict], db_connection) -> Optional[str]:
    """
    Comme obtenir_salon_id, mais recharge salon_id depuis la table couturiers si la session
    ne l'a pas (évite l'ancien fallback admin qui utilisait l'id couturier comme salon_id).
    """
    sid = obtenir_salon_id(couturier_data)
    if sid:
        return sid
    if not couturier_data or not db_connection:
        return None
    cid = couturier_data.get('id')
    if not cid:
        return None
    try:
        cursor = db_connection.get_connection().cursor()
        cursor.execute('SELECT salon_id FROM couturiers WHERE id = %s', (cid,))
        row = cursor.fetchone()
        cursor.close()
        if row and row[0] is not None and str(row[0]).strip() != '':
            return str(row[0]).strip()
    except Exception:
        pass
    return None

