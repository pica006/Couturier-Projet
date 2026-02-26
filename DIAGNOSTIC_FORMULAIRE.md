# Diagnostic : formulaire lent (4-13 secondes par requête)

## Problème identifié dans les logs Render

Les requêtes `/_stcore/stream` prennent **4 à 13 secondes**. C'est le temps d'exécution du script Python à chaque chargement. Pendant ce temps, la page semble "en veille" puis revient.

## Solution déployée

### Cache de l'image de fond
L'image `background_dark.png` était chargée et encodée en base64 **à chaque requête**. C'est maintenant mis en cache avec `@st.cache_data`.

**Fichier modifié :** `views/auth_view.py`

---

## Fichiers modifiés pour cette solution

| Fichier | Modification |
|---------|--------------|
| `views/auth_view.py` | Cache `_load_wallpaper_data_uri()` pour l'image de fond |
| `app.py` | Aucune (revert des changements précédents) |
| `.streamlit/config.toml` | Aucune (revert des changements précédents) |

---

## Si c'est encore lent

La connexion à PostgreSQL sur Render peut prendre 2-5 secondes au premier chargement. C'est normal.

Si les requêtes restent > 5 secondes après déploiement :
1. Vérifier la taille de `assets/background_dark.png` (idéalement < 500 Ko)
2. S'assurer que l'app et la base PostgreSQL sont dans la même région Render
