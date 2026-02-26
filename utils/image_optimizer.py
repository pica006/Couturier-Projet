"""
Module d'optimisation d'images pour réduire leur taille avant insertion en base de données
"""

import io
from PIL import Image
from typing import Optional, Tuple


def optimiser_image(image_bytes: bytes, max_size: Tuple[int, int] = (1920, 1920), 
                    quality: int = 85, max_file_size_mb: float = 2.0) -> Optional[bytes]:
    """
    Optimise une image pour réduire sa taille avant insertion en base de données.
    
    Args:
        image_bytes: Image en bytes (format original)
        max_size: Taille maximale (largeur, hauteur) en pixels. Par défaut 1920x1920
        quality: Qualité JPEG (1-100). Par défaut 85 (bon compromis qualité/taille)
        max_file_size_mb: Taille maximale du fichier en MB. Par défaut 2MB
        
    Returns:
        Image optimisée en bytes, ou None en cas d'erreur
    """
    try:
        # Ouvrir l'image depuis les bytes
        image = Image.open(io.BytesIO(image_bytes))
        
        # Convertir en RGB si nécessaire (pour JPEG)
        if image.mode in ('RGBA', 'LA', 'P'):
            # Créer un fond blanc pour les images avec transparence
            background = Image.new('RGB', image.size, (255, 255, 255))
            if image.mode == 'P':
                image = image.convert('RGBA')
            background.paste(image, mask=image.split()[-1] if image.mode in ('RGBA', 'LA') else None)
            image = background
        elif image.mode != 'RGB':
            image = image.convert('RGB')
        
        # Redimensionner si l'image est trop grande
        original_size = image.size
        if original_size[0] > max_size[0] or original_size[1] > max_size[1]:
            image.thumbnail(max_size, Image.Resampling.LANCZOS)
        
        # Optimiser la qualité jusqu'à atteindre la taille cible
        output = io.BytesIO()
        current_quality = quality
        min_quality = 60  # Qualité minimale acceptable
        
        while current_quality >= min_quality:
            output.seek(0)
            output.truncate(0)
            
            # Sauvegarder en JPEG avec la qualité actuelle
            image.save(output, format='JPEG', quality=current_quality, optimize=True)
            
            # Vérifier la taille
            file_size_mb = len(output.getvalue()) / (1024 * 1024)
            
            if file_size_mb <= max_file_size_mb:
                break
            
            # Réduire la qualité si trop gros
            current_quality -= 5
        
        return output.getvalue()
        
    except Exception as e:
        print(f"Erreur optimisation image: {e}")
        # En cas d'erreur, retourner l'image originale
        return image_bytes


def obtenir_taille_image(image_bytes: bytes) -> Tuple[int, int]:
    """
    Obtient les dimensions d'une image.
    
    Args:
        image_bytes: Image en bytes
        
    Returns:
        Tuple (largeur, hauteur) en pixels
    """
    try:
        image = Image.open(io.BytesIO(image_bytes))
        return image.size
    except Exception as e:
        print(f"Erreur lecture taille image: {e}")
        return (0, 0)


def obtenir_taille_fichier_mb(image_bytes: bytes) -> float:
    """
    Obtient la taille d'une image en MB.
    
    Args:
        image_bytes: Image en bytes
        
    Returns:
        Taille en MB
    """
    return len(image_bytes) / (1024 * 1024)

