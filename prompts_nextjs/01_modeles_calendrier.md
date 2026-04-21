# PROMPT 1 — Page : Modèles & Calendrier

## Contexte à coller en début de prompt

```
Tu es un développeur senior Next.js 14. Implémente la page "Modèles & Calendrier"
pour l'application de gestion d'atelier de couture "An's Learning".

Stack : Next.js 14 App Router (TypeScript strict), Tailwind CSS, shadcn/ui,
TanStack Query v5, date-fns, Recharts, Framer Motion.

Branding : violet #B19CD9, turquoise #40E0D0, fond #FEFEFE, police Inter.
Monnaie : FCFA. Format dates : dd/MM/yyyy.

Rôles : employe | admin | super_admin.
```

---

## ONGLET 1 — Modèles Réalisés

```
### Accès par rôle
- employe     → ses commandes terminées uniquement
- admin       → toutes commandes terminées du salon + filtre par employé
- super_admin → tout + filtre par salon puis par employé

### Données à afficher (commandes WHERE statut IN ('Terminée','Livrée'))
Colonnes du tableau :
- Modèle | Client | Catégorie (Adulte/Enfant) | Sexe | Date création
- Date livraison | Statut (badge : Terminée=violet, Livrée=vert)
- Couturier (admin/super_admin seulement)

### Cards statistiques (en haut)
- Nombre total de modèles réalisés
- Modèle le plus fréquent (texte + count)
- Taux de complétion = Livrées / (Terminées + Livrées) en %
- Répartition Adulte/Enfant (progress bar)

### Graphique
BarChart horizontal Recharts — top 5 modèles les plus réalisés
X = nombre commandes | Y = nom modèle | Couleur = #B19CD9

### Filtres disponibles
- Période (DateRangePicker)
- Catégorie : Adulte / Enfant / Tous
- Sexe : Homme / Femme / Tous
- Statut : Terminée / Livrée / Tous
- (admin+) Employé : select dropdown couturiers du salon
- (super_admin+) Salon : select dropdown

### Tableau
- Paginé 20 lignes/page, tri par colonne
- Bouton Export CSV en haut à droite
- Clic sur une ligne → Drawer latéral :
  mesures JSONB formatées en tableau, images si présentes,
  historique paiements
```

---

## ONGLET 2 — Calendrier de Livraisons

```
### Vue calendrier mensuel
- Navigation mois précédent / suivant
- Chaque jour avec livraison : badge coloré selon statut
    En cours  → #B19CD9 (violet)
    Terminée  → #F97316 (orange)
    Livrée    → #22C55E (vert)
    En retard (date passée + statut != Livrée) → #EF4444 (rouge)
- Clic sur un jour → popover listant les commandes du jour

### Liste livraisons à venir (30 jours)
Table triée par date croissante :
Date livraison | Client | Modèle | Statut | Couturier (admin) | Actions

Actions par ligne :
- "Marquer Livré"   → si statut=Terminée (employe/admin)
                     → PUT /api/commandes/:id/livrer
- "Voir détail"     → ouvre drawer commande
- "Envoyer rappel" → si dans les 48h
                     → POST /api/reminders/send { commande_id }
                     → toast succès/erreur

### Alertes livraisons urgentes (banner en haut)
- En retard (date_livraison < aujourd'hui, statut != Livrée)
  → banner rouge + liste cliquable
- À livrer dans 48h
  → banner orange + bouton rappel direct

### Accès par rôle (calendrier)
- employe     → ses livraisons uniquement
- admin       → toutes les livraisons du salon
- super_admin → filtre par salon + vue globale
```

---

## API Routes

```typescript
// GET  /api/calendrier/modeles
//      ?couturier_id? &salon_id? &date_debut? &date_fin?
//      &categorie? &sexe? &statut? &page? &limit?
// →    { modeles: CommandeResume[], total: number, stats: StatsModeles }

// GET  /api/calendrier/livraisons
//      ?mois? &annee? &couturier_id? &salon_id?
// →    { livraisons: LivraisonCalendrier[] }

// POST /api/reminders/send
//      body: { commande_id: number }
// →    { success: boolean, message: string }

// PUT  /api/commandes/:id/livrer
//      body: { couturier_id: number }
// →    { success: boolean, commande: Commande }
```

---

## Types TypeScript

```typescript
interface CommandeResume {
  id: number
  client_nom: string
  client_prenom: string
  modele: string
  categorie: 'adulte' | 'enfant'
  sexe: 'homme' | 'femme'
  statut: 'En cours' | 'Terminée' | 'Livrée'
  date_livraison: string   // ISO
  date_creation: string
  couturier_nom?: string   // admin/super_admin
  salon_nom?: string       // super_admin
}

interface StatsModeles {
  total: number
  modele_top: string
  modele_top_count: number
  taux_completion: number
  adulte_pct: number
  enfant_pct: number
  top5_modeles: { modele: string; count: number }[]
}

interface LivraisonCalendrier {
  id: number
  date_livraison: string
  client_nom: string
  modele: string
  statut: string
  couturier_id: number
  en_retard: boolean
  rappel_possible: boolean
}
```

---

## Structure des fichiers à créer

```
app/(dashboard)/calendrier/
  page.tsx
  _components/
    ModelesList.tsx
    ModeleStats.tsx
    LivraisonCalendar.tsx
    LivraisonTable.tsx
    AlertesBanner.tsx
    CommandeDetailDrawer.tsx

hooks/
  useCalendrier.ts
  useLivraisons.ts

types/
  calendrier.ts
```

---

## Contraintes importantes

```
- Loading skeletons pendant fetch
- Empty states illustrés (no data)
- Confirmation dialog avant "Marquer Livré"
- Toasts (sonner) pour les actions
- Responsive mobile (tableau scrollable horizontalement)
- Vérifier le rôle depuis le contexte auth avant chaque action
```
