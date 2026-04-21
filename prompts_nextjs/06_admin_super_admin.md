# PROMPT 6 — Admin Dashboard & Super Admin Dashboard

## Contexte à coller en début de prompt

```
Tu es un développeur senior Next.js 14. Implémente les tableaux de bord
"Administration" (/admin) et "Super Administration" (/super-admin)
pour l'application de gestion d'atelier de couture "An's Learning".

Stack : Next.js 14 App Router (TypeScript strict), Tailwind CSS, shadcn/ui,
TanStack Query v5, react-hook-form + zod, Recharts.

Branding : violet #B19CD9, turquoise #40E0D0, fond #FEFEFE.
Monnaie : FCFA. Format dates : dd/MM/yyyy.

Protection des routes :
  /admin       → rôles 'admin' et 'super_admin' uniquement
  /super-admin → rôle 'super_admin' uniquement
  Toute autre tentative d'accès → redirect /dashboard
```

---

# PARTIE A — TABLEAU DE BORD ADMIN `/admin`

---

## ONGLET 1 — Vue d'ensemble salon

```
### Bandeau infos salon (en haut)
  Logo du salon | Nom | Quartier | Responsable | Téléphone
  Badge actif/inactif
  Bouton "Paramètres salon" → ouvre l'onglet Paramètres

### 5 KPI Cards (filtrables par période)
  Employés actifs | Total commandes salon | CA mois en cours
  CA total salon  | Fermetures en attente (badge rouge si > 0)

### Graphique activité salon (6 derniers mois)
  GroupedBarChart Recharts
  Un groupe par mois
  Bar 1 = nombre commandes | Bar 2 = CA (FCFA)
  Légende

### Tableau classement employés (ce mois)
  Rang | Employé | Commandes | CA | Taux complétion
  Icône trophée 🏆 pour le rang #1
```

---

## ONGLET 2 — Employés

```
### En-tête
  Titre "Employés du salon" + badge count
  Bouton "Ajouter un employé" → ouvre modal

### Table des employés
Colonnes :
  Initiales/Photo | Nom | Code couturier | Email | Téléphone
  Rôle | Statut | Commandes | CA | Actions

  Badge rôle   : employe (violet clair) | admin (violet foncé)
  Badge statut : actif (vert) | inactif (rouge)

Actions par ligne :
  Voir détail      → modal stats complètes de l'employé
  Éditer           → modal édition
  Activer/Désactiver → toggle avec confirmation dialog
  Réinitialiser mdp → génère mdp temporaire aléatoire

### Modal Créer / Éditer Employé (react-hook-form + Zod)
Schéma :
  nom              : string min 2
  prenom           : string min 2
  email            : string email optionnel
  telephone        : string min 8
  code_couturier   : string min 4 max 20
  password         : string min 6 (optionnel en édition)
  role             : 'employe' fixe (admin ne peut créer qu'un employé)

UX :
  code_couturier auto-suggéré : prenom.nom (modifiable)
  Password : généré aléatoirement + toggle visible/masqué
  Bouton "Copier code + mdp" → clipboard
  POST /api/employes  (création)
  PUT  /api/employes/:id (édition)

### Modal Détail Employé
  Infos personnelles
  Stats période sélectionnée : nb commandes | CA | Avances | Reste
  Mini graphique 6 derniers mois (LineChart)
  Tableau 5 dernières commandes
  Bouton "Voir toutes ses commandes" → /commandes?couturier_id=X
```

---

## ONGLET 3 — Toutes les Commandes du salon

```
Identique à la page /commandes MAIS :
  Filtre par employé ajouté
  Colonne "Couturier" visible
  Admin peut voir ET éditer toutes les commandes du salon
  Badge orange "Fermeture en attente" sur les lignes concernées
    → bouton "Approuver fermeture" directement depuis ce tableau

Actions supplémentaires :
  "Transférer commande" → réassigner à un autre employé
    dialog : select employé + bouton confirmer
    PUT /api/commandes/:id/transferer { nouveau_couturier_id }
```

---

## ONGLET 4 — Clients du salon

```
Table de tous les clients (tous employés) :
  Client | Téléphone | Email | Nb commandes | CA total
  Reste total | Dernier contact | Employé référent

Recherche par nom / téléphone
Clic sur une ligne → Drawer historique toutes commandes du client

Bouton "Fusionner clients" (si doublon détecté) :
  Sélectionner 2 clients → fusion des commandes sur le plus ancien
  DELETE /api/clients/fusionner { client_a_garder_id, client_a_supprimer_id }
```

---

## ONGLET 5 — Charges du salon

```
Identique à la page /mes-frais MAIS scope = tout le salon :
  Toutes les charges de tous les employés
  Filtre par employé
  Graphiques à l'échelle du salon
  Calcul fiscal global du salon
  Bouton "Rapport salon complet" → PDF + Excel
```

---

## ONGLET 6 — Paramètres du salon

```
### Section : Identité visuelle
  Upload logo (JPG/PNG max 2MB)
  → Prévisualisation avant upload
  → POST /api/salons/:id/logo (FormData)
  Champs : Nom salon | Quartier | Responsable | Téléphone | Email

### Section : Configuration email SMTP (Zod)
  smtp_host     : string
  smtp_port     : number int 1-65535
  smtp_user     : string email
  smtp_password : string (masqué par défaut)

  Bouton "Tester la connexion"
  → POST /api/salons/:id/test-smtp
  → Toast vert "Connexion réussie" ou rouge avec message d'erreur

### Section : Rappels automatiques
  Toggle activer/désactiver rappels livraison
  Délai : X heures avant livraison (défaut 48h)
  Template email (textarea)
    Variables disponibles : {{client}} {{date}} {{modele}} {{couturier}}
  PUT /api/salons/:id/rappels
```

---

# PARTIE B — TABLEAU DE BORD SUPER ADMIN `/super-admin`

---

## ONGLET 1 — Vue d'ensemble globale

```
### 6 KPI Cards (tous salons, tous temps)
  Salons actifs | Utilisateurs total | Commandes totales
  CA Global (FCFA) | Charges totales (FCFA) | Résultat net global (FCFA)

### Top 5 salons par CA (ce mois)
  HorizontalBarChart Recharts : nom salon + CA

### Feed activité récente (chronologique)
  Nouvelles commandes (tous salons)
  Nouvelles inscriptions
  Demandes de fermeture en attente
```

---

## ONGLET 2 — Gérer les Salons

```
### Table des salons
  Logo | Salon | Quartier | Responsable | Nb employés
  Nb commandes | CA | Statut | Actions

  Toggle actif/inactif par ligne
  Badge rouge si salon inactif
  Ligne expandable → stats détaillées du salon

### Créer un salon (bouton en haut)
Modal form (Zod) :
  salon_id         : string min 3 max 50, regex /^[a-z0-9-]+$/
                     Auto-généré depuis le nom (slug) mais modifiable
  nom              : string min 2
  quartier         : string
  responsable      : string
  telephone        : string
  email            : string email optionnel
  admin_id         : number optionnel (assigner admin existant)

Option dans le modal : "Créer un admin en même temps"
  → formulaire imbriqué pour l'admin
  POST /api/super-admin/salons

### Modifier un salon
  Même form pré-rempli
  + Section "Changer d'admin" → select parmi les admins du système
  PUT /api/super-admin/salons/:id
```

---

## ONGLET 3 — Gérer les Utilisateurs

```
### Filtres
  Salon : select tous les salons
  Rôle  : employe / admin / super_admin / tous
  Statut : actif / inactif / tous
  Recherche : nom, code couturier, email

### Table utilisateurs
  Utilisateur | Code | Email | Rôle | Salon
  Statut | Dernière connexion | Actions

Actions par ligne :
  Éditer             → modal form complet
  Changer rôle       → select inline dans la table
  Changer salon      → select inline dans la table
  Activer/Désactiver → toggle
  Réinitialiser mdp

### Créer un Admin (bouton dédié)
Modal form (Zod) :
  nom, prenom, email (obligatoire), telephone
  code_couturier : string min 4
  password       : string min 8
  salon_id       : string OBLIGATOIRE (select salon)
  role           : 'admin' fixe
  POST /api/super-admin/users/admin
```

---

## ONGLET 4 — Toutes les Commandes

```
Identique à l'onglet commandes admin MAIS :
  Filtre salon en premier (select obligatoire ou "Tous")
  Filtre par admin/employé ensuite
  Vue lecture seule (pas d'actions de modification depuis ici)
  Bouton "Exporter tout" → CSV/Excel global
```

---

## ONGLET 5 — Statistiques avancées

```
### Revenue par salon
  ComposedChart Recharts
  Line par salon (couleur différente par salon, palette auto)
  Toggle salons dans la légende

### Analyse comparative 2 salons
  RadarChart Recharts
  5 métriques : CA | Commandes | Clients | Charges | Résultat
  Sélectionner 2 salons via 2 dropdowns

### Tendances globales
  AreaChart : évolution CA global 12 mois
  Breakdown : Adulte vs Enfant vs par modèle (toggle)

### Export
  Bouton "Rapport global PDF"  → POST /api/super-admin/rapports/global
  Bouton "Export Excel détaillé" → GET /api/super-admin/export-excel
```

---

## ONGLET 6 — Demandes en attente (globales)

```
### Section A : Fermetures en attente
  Table : Salon | Couturier | Client | Modèle | CA | Date demande | Actions
  Approuver directement (avec commentaire optionnel)
  Rejeter (commentaire OBLIGATOIRE)
  Badge count dans le titre si > 0

### Section B : Modifications paiement en attente
  Même structure
  Badge count séparé
```

---

## ONGLET 7 — Rapports

```
### Rapport par salon
  Select salon + Select période
  Bouton "Générer rapport salon" → PDF contenant :
    Logo + infos salon
    KPIs de la période
    Liste commandes détaillée
    Analyse par employé
    Charges et calcul taxes

### Rapport global
  Select période
  Bouton "Générer rapport global" → PDF multi-salons comparatif

### Historique des rapports générés
  Table des N derniers rapports
  Colonnes : type | salon | période | date génération | actions
  Bouton "Re-télécharger" sur chaque ligne
```

---

## Middleware de protection des routes

```typescript
// middleware.ts  (à la racine du projet Next.js)
import { NextResponse } from 'next/server'
import type { NextRequest } from 'next/server'

export function middleware(request: NextRequest) {
  const { pathname } = request.nextUrl
  const userRole = request.cookies.get('user_role')?.value
  const userId   = request.cookies.get('user_id')?.value

  // Non connecté → login
  if (!userId) {
    return NextResponse.redirect(new URL('/login', request.url))
  }

  // /super-admin → super_admin uniquement
  if (pathname.startsWith('/super-admin') && userRole !== 'super_admin') {
    return NextResponse.redirect(new URL('/dashboard', request.url))
  }

  // /admin → admin ou super_admin uniquement
  if (pathname.startsWith('/admin') &&
      !['admin', 'super_admin'].includes(userRole || '')) {
    return NextResponse.redirect(new URL('/dashboard', request.url))
  }

  return NextResponse.next()
}

export const config = {
  matcher: ['/admin/:path*', '/super-admin/:path*', '/commandes/:path*']
}
```

---

## API Routes

```typescript
// === SALON (admin) ===
// GET    /api/salons/:id/stats     ?date_debut &date_fin
// PUT    /api/salons/:id
// POST   /api/salons/:id/logo      FormData
// POST   /api/salons/:id/test-smtp
// PUT    /api/salons/:id/rappels

// === EMPLOYÉS (admin) ===
// GET    /api/employes             ?salon_id &page &limit
// POST   /api/employes
// PUT    /api/employes/:id
// PUT    /api/employes/:id/toggle-actif
// POST   /api/employes/:id/reset-password
// GET    /api/employes/:id/stats   ?date_debut &date_fin

// === COMMANDES (admin) ===
// PUT    /api/commandes/:id/transferer   body: { nouveau_couturier_id }

// === CLIENTS (admin) ===
// DELETE /api/clients/fusionner
//        body: { client_a_garder_id, client_a_supprimer_id }

// === SUPER ADMIN ===
// GET    /api/super-admin/overview
// GET    /api/super-admin/salons
// POST   /api/super-admin/salons
// PUT    /api/super-admin/salons/:id
// PUT    /api/super-admin/salons/:id/toggle-actif
// GET    /api/super-admin/users     ?salon_id &role &statut &search &page
// POST   /api/super-admin/users/admin
// PUT    /api/super-admin/users/:id/role
// PUT    /api/super-admin/users/:id/salon
// GET    /api/super-admin/stats-avancees  ?date_debut &date_fin
// GET    /api/super-admin/demandes-en-attente
// POST   /api/super-admin/rapports/salon  body: { salon_id, periode }
// POST   /api/super-admin/rapports/global body: { periode }
// GET    /api/super-admin/export-excel    ?date_debut &date_fin
```

---

## Structure des fichiers à créer

```
app/
  (dashboard)/
    admin/
      page.tsx
      _components/
        VueEnsembleSalon.tsx
        OngletEmployes.tsx
        OngletCommandesSalon.tsx
        OngletClientsSalon.tsx
        OngletChargesSalon.tsx
        OngletParametres.tsx
        ModalEmploye.tsx
        DrawerDetailEmploye.tsx
        SmtpForm.tsx

    super-admin/
      page.tsx
      _components/
        OngletOverview.tsx
        OngletSalons.tsx
        OngletUtilisateurs.tsx
        OngletToutesCommandes.tsx
        OngletStatsAvancees.tsx
        OngletDemandesGlobales.tsx
        OngletRapports.tsx
        ModalCreerSalon.tsx
        ModalCreerAdmin.tsx
        GraphiqueComparatif.tsx

middleware.ts
```

---

## Règles de sécurité importantes

```
- Données super_admin jamais en clair dans cookies ou localStorage
- Toutes les opérations sensibles (changer rôle, supprimer) double-vérifiées
  côté API avec le JWT (ne pas faire confiance uniquement au cookie)
- Un admin NE PEUT PAS élever son propre rôle
- Un admin NE PEUT PAS lire les données d'un autre salon
  → vérifier salon_id dans chaque requête SQL
- Un admin NE PEUT PAS créer un autre admin (uniquement des employés)
- Logs d'audit pour toutes les actions admin/super_admin
  (table historique ou table audit_logs)
```
