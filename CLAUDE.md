# CLAUDE.md - Projet Couturier / An's Learning

Ce document donne le contexte indispensable à tout agent (Claude Code, Cowork,
Agent SDK) qui intervient sur ce dépôt. Il décrit l'architecture, les
commandes, les conventions et les pièges connus.

## 1. Vue d'ensemble

**An's Learning** (alias "Gestion Couturier") est une application web
Streamlit multi-salons de gestion d'atelier de couture : commandes, clients,
modèles, comptabilité, rappels automatiques, charges, PDF factures/livraison,
envoi d'emails.

- Langage : Python 3.11+
- Framework : Streamlit 1.29
- Base de données : PostgreSQL (local ou Render)
- Architecture : MVC strict (Models / Views / Controllers)
- Déploiement : Render (voir `render.yaml`, `DEPLOY_RENDER.md`)

## 2. Architecture MVC

```
app.py                  # Point d'entrée Streamlit + routing + CSS globale
config.py               # Constantes, EMAIL_CONFIG, DB config, branding
models/
  database.py           # Modèles BDD (CommandeModel, ClientModel, ...)
  salon_model.py        # Multi-salons (config SMTP par salon, abonnements)
controllers/
  auth_controller.py    # Login / logout / hash bcrypt
  commande_controller.py
  comptabilite_controller.py
  email_controller.py   # SMTP (Gmail, Outlook, SendGrid, ...)
  pdf_controller.py     # Génération PDF (reportlab)
  rappel_service.py     # Rappels J-2 auto
  admin_controller.py / super_admin_controller.py
views/
  auth_view.py          # Page login (thème premium glass)
  commande_view.py, liste_view.py, fermer_commandes_view.py
  comptabilite_view.py, mes_charges_view.py
  dashboard_view.py, calendrier_view.py
  admin_view.py, super_admin_dashboard.py, salons_view.py
services/
  db_bootstrap_service.py
  session_service.py    # initialize_session_state / sanitize_session_state
utils/
  theme.py              # CSS login + sidebar (premium_glass / ultra_minimal)
  bottom_nav.py         # Footer app
  page_header.py, permissions.py, role_utils.py, security.py, ui.py
assets/                 # logos, images de fond par page
pdfs/                   # sorties PDF générées
```

Règle d'or : les vues (`views/*.py`) ne parlent jamais directement à `psycopg2`.
Elles passent par les contrôleurs, qui instancient les modèles. Les modèles
ouvrent / ferment les curseurs.

## 3. Démarrage local

```bash
# 1. Installer les dépendances
pip install -r requirements.txt

# 2. Copier la config exemple et la remplir
cp .env.example .env
# Editer .env :
#   DATABASE_HOST, DATABASE_PORT, DATABASE_NAME, DATABASE_USER, DATABASE_PASSWORD
#   EMAIL_HOST=smtp.gmail.com
#   EMAIL_PORT=587
#   EMAIL_USER=<votre.email@gmail.com>
#   EMAIL_PASSWORD=<mot de passe d'application 16 caracteres>
#   EMAIL_FROM=<idem user>

# 3. Lancer
streamlit run app.py
```

Comptes de démo : voir `database_seed.sql`. Le premier démarrage crée les
tables via `auth_controller.initialiser_tables()` et
`commande_controller.initialiser_tables()`.

## 4. Envoi d'email (SMTP) - IMPORTANT

Le module `controllers/email_controller.py` a été réécrit pour être robuste :

- Retry automatique avec backoff (2 retries par défaut).
- Alternative MIME texte + HTML (les clients mail modernes affichent l'HTML).
- Pièces jointes PDF encodées correctement (RFC 2231, accents préservés).
- Validation d'adresse email avant l'envoi.
- Auto-détection port 465 → SSL.
- API publique conservée : `envoyer_email(to, subject, body, attachments)`,
  `envoyer_email_avec_message(...)` → `(bool, str)`,
  `verifier_configuration()` → `(bool, str)`, `tester_connexion()`.

### Gmail : mot de passe d'application

Gmail refuse les mots de passe classiques. Il faut :
1. Activer la double authentification sur le compte Google.
2. Créer un mot de passe d'application (16 caractères) :
   <https://myaccount.google.com/apppasswords>
3. Copier ce mot de passe dans `EMAIL_PASSWORD` (sans espace).

### Outlook / Office 365

Même principe : créer un mot de passe d'application. Host :
`smtp.office365.com` port `587` avec STARTTLS.

### Par salon (multi-tenant)

Chaque salon peut définir ses propres identifiants SMTP en base (voir
`SalonModel.obtenir_config_email_salon`). La priorité est :
1. Config SMTP du salon (si `host` + `user` + `password` renseignés).
2. Sinon `EMAIL_CONFIG` global (`config.py`).
3. Sinon variables d'environnement (`EMAIL_USER`, `EMAIL_PASSWORD`).

## 5. Génération PDF

`controllers/pdf_controller.py` utilise `reportlab`. Les PDF sont stockés dans
`pdfs/` (chemin défini dans `config.py` : `PDF_STORAGE_PATH`). Les vues
récupèrent `pdf_path` depuis la commande et le passent en pièce jointe à
`EmailController.envoyer_email_avec_message`.

Points d'attention :
- Le logo utilisé est `assets/logo.*` (png/jpg/jpeg, auto-détecté).
- Les polices par défaut de reportlab gèrent mal certains caractères. Pour
  tout accent spécial, utiliser `Helvetica` (inclus) ou enregistrer une font TTF.

## 6. Rappels automatiques

`controllers/rappel_service.py` envoie un email 2 jours avant la date de
livraison. Appelé au chargement de `views/calendrier_view.py`. Il utilise
`EmailController` avec la config SMTP du salon.

## 7. Commandes utiles

```bash
# Compiler tous les .py (fail-fast)
python -m compileall -q .

# Lancer en mode dev avec auto-reload
streamlit run app.py --server.runOnSave true

# Mode "visuel safe" (désactive les CSS lourds)
VISUAL_SAFE_MODE=1 streamlit run app.py

# Tester l'envoi SMTP (script one-liner)
python -c "from controllers.email_controller import EmailController; \
  ok, msg = EmailController().tester_connexion(); print(ok, msg)"

# Déploiement Render (voir render.yaml + DEPLOY_RENDER.md)
```

## 8. Conventions de code

- Noms de variables, classes, méthodes, commentaires : **français**.
- Docstrings : français acceptable. Penser aux cas "pas de DB" au démarrage
  (cf. `db_bootstrap_service.py`).
- Éviter d'injecter du JS custom dans Streamlit : ça déclenche l'erreur
  `removeChild` (bug Streamlit connu). CSS uniquement.
- Les imports de vues doivent être **lazy** (dans `app.py`, import à l'intérieur
  de la fonction) pour ne pas allonger le cold start Render.
- Les pièces jointes PDF sont toujours passées en chemin absolu (str ou Path).

## 9. Style graphique

- Palette "premium glass" : violet `#6C63FF` → turquoise `#00C9A7`, fond lavande
  → cyan `linear-gradient(135deg, #E0C3FC, #8EC5FC)`.
- Carte glass : `rgba(255,255,255,0.88)` + `backdrop-filter: blur(24px)`.
- Polices : Inter (corps) + Poppins (titres), chargées via Google Fonts.
- CSS défini dans :
  - `utils/theme.py` pour la page login et la sidebar.
  - `app.py` pour le CSS global (après authentification).
- Variante "ultra_minimal" disponible via `THEME=ultra_minimal` en env.

## 10. Pièges connus à surveiller

| Symptôme | Cause | Fix |
|---|---|---|
| Email non envoyé "Auth error" | Mot de passe Gmail classique | Créer un mot de passe d'application |
| Email sans pièce jointe | Chemin PDF invalide / fichier supprimé | Vérifier `pdf_path` renvoyé par la commande |
| `removeChild` en console Streamlit | JS custom ou rerun massif | Pas de JS, limiter les `st.rerun` |
| Cold start Render long | Imports non lazy | Importer les vues dans la fonction, pas au top |
| Accents cassés dans PDF | Font reportlab par défaut | Forcer Helvetica ou TTF |
| CSS cassé sur Android | `backdrop-filter` non supporté | Fallback `background: white` |
| Port 465 ne marche pas | use_tls activé avec SSL | Le contrôleur force `use_ssl=True, use_tls=False` quand port=465 |

## 11. Tests rapides (sanity check)

```bash
# Doit afficher "OK" pour tous les modules critiques
python -c "import app"                             # routing + CSS
python -c "from controllers.email_controller import EmailController; print('OK email')"
python -c "from controllers.pdf_controller import PDFController; print('OK pdf')"
python -c "from controllers.rappel_service import executer_rappels_automatiques; print('OK rappels')"
python -c "from utils.theme import get_login_css; print('OK theme')"
```

## 12. Où poser la prochaine feature ?

- **Nouveau champ commande** : `models/database.py` (migration + CRUD) +
  `controllers/commande_controller.py` + `views/commande_view.py` +
  mise à jour `controllers/pdf_controller.py` si imprimé.
- **Nouveau type d'email** : toujours passer par `EmailController`. Ne pas
  réimporter `smtplib` directement ailleurs.
- **Nouvelle page** : créer `views/xxx_view.py`, ajouter l'import lazy dans
  `app.py::_render_authenticated_page`, ajouter le bouton dans la sidebar.
- **Nouveau rôle** : `utils/permissions.py` + `utils/role_utils.py`.
