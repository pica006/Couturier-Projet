"""
Fonction utilitaire pour générer l'en-tête encadré standardisé des pages
Style : Dégradé violet clair (#B19CD9) vers bleu turquoise (#40E0D0)
"""

import streamlit as st


def afficher_header_page(titre: str, sous_titre: str = ""):
    """
    Affiche un en-tête encadré avec dégradé violet-bleu standardisé
    
    Args:
        titre: Le titre principal de la page (avec emoji si souhaité)
        sous_titre: Le sous-titre optionnel de la page
    
    Exemple:
        afficher_header_page("➕ Nouvelle Commande", "Créer une nouvelle commande pour un client")
    """
    st.markdown(f"""
        <div style='background: linear-gradient(135deg, #B19CD9 0%, #40E0D0 100%); 
                    padding: 2rem; border-radius: 16px; margin-bottom: 2rem; 
                    box-shadow: 0 4px 8px rgba(0,0,0,0.1); text-align: center;'>
            <h1 style='color: white; margin: 0; font-size: 2.5rem; font-weight: 700; 
                       font-family: Poppins, sans-serif; text-shadow: 0 2px 4px rgba(0,0,0,0.2);'>{titre}</h1>
            {f"<p style='color: rgba(255,255,255,0.95); margin: 0.5rem 0 0 0; font-size: 1.1rem;'>{sous_titre}</p>" if sous_titre else ""}
        </div>
    """, unsafe_allow_html=True)

