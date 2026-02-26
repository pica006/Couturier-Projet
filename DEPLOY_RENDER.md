# Déploiement sur Render – An's Learning / Gestion Couturier

Ce guide décrit comment déployer l'application Streamlit sur Render.

---

## 0. Checklist avant déploiement

Cochez chaque étape avant de déployer :

### Nettoyage (déjà fait)
- [x] Dossier `supp/` créé : `pdfs/`, `charges_docs/`, `brouillon/`, docs déplacés dedans
- [x] `.gitignore` mis à jour : `supp/`, `pdfs/`, `charges_docs/`, `data/` exclus
- [x] `data/` recréé à la racine (vide, pour les rappels)

### À faire par vous

1. **Si Git est déjà initialisé** : retirer les dossiers maintenant ignorés du suivi Git :
   ```bash
   git rm -r --cached supp/ pdfs/ charges_docs/ data/ 2>nul
   git commit -m "Exclure supp, pdfs, charges_docs, data du déploiement"
   ```

2. **Fichier à la racine** : déplacez manuellement `✨ 1. SpiritStitch.txt` vers `supp/` si vous ne voulez pas le déployer.

3. **Initialiser Git** (si pas encore fait) :
   ```bash
   git init
   git add .
   git commit -m "Prêt pour déploiement Render"
   ```

4. **Pousser vers GitHub/GitLab/Bitbucket** :
   ```bash
   git remote add origin https://votre-repo.git
   git branch -M main
   git push -u origin main
   ```

5. **Sur Render** : créer le Blueprint ou configurer manuellement (voir sections ci-dessous).

6. **Après déploiement** : exécuter `database_schema.sql` puis `database_seed.sql` pour les données de démo (optionnel).

---

## 1. Prérequis

- Un compte [Render](https://render.com)
- Un dépôt Git (GitHub, GitLab ou Bitbucket) contenant le projet
- Le projet doit être poussé sur le dépôt distant

---

## 2. Méthode A : Blueprint (render.yaml)

Le fichier `render.yaml` à la racine du projet permet un déploiement en une seule étape.

### Étapes

1. Connectez votre dépôt Git à Render
2. Créez un **Blueprint** : Dashboard Render → **New** → **Blueprint**
3. Choisissez le dépôt et la branche
4. Render détecte `render.yaml` et crée :
   - un **Web Service** (application Streamlit)
   - une base **PostgreSQL** (si configurée)

### Variables d'environnement

Les variables liées à la base de données sont configurées automatiquement via `fromDatabase` dans `render.yaml`. Il suffit de créer la base `db-couturier` avec le même nom.

### Base de données

- La base est créée automatiquement par le blueprint
- Les tables sont créées au premier lancement via `initialiser_tables()`
- Pour des données de démo : exécutez `database_schema.sql` puis `database_seed.sql` dans Render Shell (ou via psql)

---

## 3. Méthode B : Configuration manuelle

### 3.1 Créer la base PostgreSQL

1. Dashboard Render → **New** → **PostgreSQL**
2. Nom : `db-couturier`
3. Database : `db_couturier`
4. User : `couturier_user`
5. Région : identique à l’application (ex. Frankfurt)

### 3.2 Créer le Web Service

1. Dashboard Render → **New** → **Web Service**
2. Connectez le dépôt Git
3. Configuration :
   - **Name** : `couturier-app`
   - **Region** : Frankfurt (ou la même que la base)
   - **Branch** : `main` (ou votre branche)
   - **Runtime** : Python 3
   - **Build Command** : `pip install -r requirements.txt`
   - **Start Command** : `streamlit run app.py --server.port=$PORT --server.address=0.0.0.0 --server.headless=true`

### 3.3 Variables d'environnement

Dans **Environment** du service, ajoutez :

| Clé | Valeur |
|-----|--------|
| `RENDER` | `true` |
| `DATABASE_HOST` | *(Internal Hostname de la base)* |
| `DATABASE_PORT` | *(Internal Port)* |
| `DATABASE_NAME` | `db_couturier` |
| `DATABASE_USER` | *(user de la base)* |
| `DATABASE_PASSWORD` | *(password de la base)* |

Pour les valeurs de la base : **Dashboard** → base PostgreSQL → **Info** → **Internal Database URL** ou propriétés individuelles.

---

## 4. Initialisation de la base de données

### Première exécution

L’application crée automatiquement les tables au premier accès (via `AuthController` et `CommandeController`).

### Données de démo

Pour insérer les données de test :

1. Ouvrez **Shell** du service Web ou utilisez **psql** avec l’URL de la base
2. Exécutez dans l’ordre :
   - `database_schema.sql`
   - `database_seed.sql`

Ou via Render Dashboard → base PostgreSQL → **Connect** → **External Connection** → utiliser psql avec l’URL affichée.

### Comptes de démo

| Code | Mot de passe | Rôle |
|------|--------------|------|
| `COUT001` | `admin123` | admin |
| `COUT002` | `emp123` | employe |
| `SUPERADMIN` | `super123` | super_admin |

---

## 5. Problèmes courants

### Erreur de connexion à la base

- Vérifiez que les variables `DATABASE_HOST`, `DATABASE_USER`, `DATABASE_PASSWORD` sont correctes
- Vérifiez que l’app et la base sont dans la même région Render
- Si SSL pose problème : ajoutez `DATABASE_SSLMODE=prefer` ou `disable` dans les variables d’environnement

### L’application ne démarre pas

- Contrôlez les logs de build : `pip install -r requirements.txt` doit réussir
- Vérifiez la version Python : `.python-version` fixe 3.11.9
- Vérifiez que `app.py` est bien à la racine et que le **Start Command** est correct

### Port non défini

- Render injecte automatiquement `PORT` ; ne pas le définir manuellement
- La commande de démarrage utilise `$PORT`

### Fichiers temporaires (PDF, charges)

- Les dossiers `pdfs/` et `charges_docs/` sont **éphémères** sur Render (filesystem non persistant)
- Les fichiers sont perdus à chaque redéploiement ou redémarrage
- Pour une persistance réelle : utiliser un stockage externe (S3, etc.) ou stocker en base (BYTEA)

---

## 6. Structure des fichiers de déploiement

```
CouturierProjet/
├── app.py              # Point d'entrée principal
├── render.yaml          # Blueprint Render (app + DB)
├── requirements.txt    # Dépendances Python
├── .python-version     # Version Python 3.11.9
├── .streamlit/
│   └── config.toml    # Config Streamlit production
├── database_schema.sql # Schéma SQL (optionnel, tables créées auto)
├── database_seed.sql   # Données de démo (optionnel)
└── DEPLOY_RENDER.md   # Ce guide
```

---

## 7. Sécurité

- Ne jamais commiter `.env` ou des mots de passe
- Utiliser les variables d’environnement Render pour les secrets
- En production : changer les mots de passe des comptes de démo
- Vérifier que `enableXsrfProtection = true` dans `.streamlit/config.toml`

---

## 8. Coûts Render

- **Plan gratuit** : Web Service gratuit (spin down après inactivité) ; base PostgreSQL gratuite 90 jours
- **Plan Starter** : services toujours actifs, base persistante
- Consultez [Render Pricing](https://render.com/pricing) pour les détails

---

## 9. Support

- [Documentation Render](https://render.com/docs)
- [Streamlit sur Render](https://docs.streamlit.io/deploy/streamlit-community-cloud/deploy-your-app)
