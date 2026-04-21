# PROMPT 4 — Page : Comptabilité

## Contexte à coller en début de prompt

```
Tu es un développeur senior Next.js 14. Implémente la page "Comptabilité"
pour l'application de gestion d'atelier de couture "An's Learning".

Stack : Next.js 14 App Router (TypeScript strict), Tailwind CSS, shadcn/ui,
TanStack Query v5, Recharts, date-fns.

Branding : violet #B19CD9, turquoise #40E0D0, fond #FEFEFE.
Monnaie : FCFA. Format dates : dd/MM/yyyy.

C'est une page ANALYTIQUE (pas de modification de données).

Rôles :
- employe     → ses commandes uniquement
- admin       → tout le salon + filtre par employé
- super_admin → tous salons + filtre salon + filtre employé
```

---

## SECTION 1 — Sélecteur de période (sticky en haut)

```
Options rapides :
  Aujourd'hui | Cette semaine | Ce mois | Ce trimestre | Cette année | Personnalisé

"Personnalisé" → ouvre un DateRangePicker
Tout le reste de la page se recalcule automatiquement à chaque changement.
```

---

## SECTION 2 — 4 KPI Cards

```
┌─────────────────┐ ┌─────────────────┐ ┌─────────────────┐ ┌─────────────────┐
│  CA Total        │ │  Avances reçues │ │  Reste à encaiss│ │  % Avances / CA │
│  X FCFA          │ │  Y FCFA         │ │  Z FCFA         │ │  XX%            │
│  ↑ +12% vs préc. │ │  ↑ +5%          │ │  ↓ -3%          │ │  ProgressBar    │
└─────────────────┘ └─────────────────┘ └─────────────────┘ └─────────────────┘

Calculs :
  CA Total  = somme prix_total des commandes de la période
  Avances   = somme avance
  Reste     = somme reste (non encaissé)
  % Avances = avances / CA × 100

Variation : comparaison avec la période précédente équivalente
  Flèche verte ↑ si progression | Flèche rouge ↓ si régression
```

---

## SECTION 3 — Analyse par statut

```
Tableau récapitulatif :
  Statut     | Nombre | CA    | Avances | Reste
  En cours   |   N    |   X   |    Y    |   Z
  Terminée   |   N    |   X   |    Y    |   Z
  Livrée     |   N    |   X   |    Y    |   Z
  TOTAL      |   N    |   X   |    Y    |   Z

Donut Chart (Recharts) : répartition nombre commandes par statut
  Couleurs : En cours=#B19CD9 | Terminée=#F97316 | Livrée=#22C55E
```

---

## SECTION 4 — Graphiques analytiques (2 colonnes)

```
Graphique gauche : Évolution CA mensuelle
  LineChart Recharts
  X = 12 derniers mois (Jan → Déc)
  Y = montant FCFA
  Line violette = CA total | Line turquoise = Avances
  Tooltip formaté en FCFA | Légende

Graphique droite : Top modèles par revenus
  HorizontalBarChart
  X = CA généré (FCFA) | Y = nom modèle (top 8)
  Gradient violet
  Tooltip avec nombre de commandes
```

---

## SECTION 5 — Liste clients avec stats

```
En-tête :
  Titre "Mes Clients" (ou "Clients du salon" pour admin)
  Barre de recherche (nom, téléphone)
  Bouton "Exporter CSV"

Colonnes de la table :
  Client | Téléphone | Email | Nb commandes | CA total | Avances
  Reste | Dernière commande

Tri par colonne | Pagination : 10 ou 25 lignes (select)

Badges par client :
  "VIP"     si CA total > 100 000 FCFA
  "Créance" (rouge) si reste > 0
  "Fidèle"  si nb commandes > 3

Clic sur une ligne → Drawer détail client :
  Infos contact
  Historique toutes ses commandes (table)
  Graphique ses paiements dans le temps
  Bouton "Voir commande" sur chaque ligne
```

---

## SECTION 6 — (Admin seulement) Analyse par employé

```
Table récapitulative :
  Employé | Nb commandes | CA | Avances | Reste | Taux encaissement

Clic sur une ligne → modal avec détail des commandes de l'employé
sur la période sélectionnée.
```

---

## SECTION 7 — Export

```
Bouton "Télécharger rapport PDF"
→ POST /api/comptabilite/rapport-pdf
→ PDF contenant : KPIs, tableau commandes, liste clients, graphiques

Bouton "Exporter Excel"
→ GET /api/comptabilite/export-excel
```

---

## API Routes

```typescript
// GET  /api/comptabilite/stats
//      ?date_debut &date_fin &couturier_id? &salon_id?
// →    {
//        kpis: KPIsFinanciers,
//        par_statut: StatutBreakdown[],
//        evolution_mensuelle: MoisData[],
//        top_modeles: ModeleRevenu[],
//        variation_periode_prec: VariationKPIs
//      }

// GET  /api/comptabilite/clients
//      ?date_debut &date_fin &couturier_id? &salon_id?
//      &search? &page? &limit? &sort_by? &sort_order?
// →    { clients: ClientStats[], total: number }

// GET  /api/comptabilite/clients/:id/detail
// →    { client: Client, commandes: Commande[], stats: ClientStats }

// GET  /api/comptabilite/par-employe
//      ?date_debut &date_fin &salon_id
// →    { employes: EmployeStats[] }

// POST /api/comptabilite/rapport-pdf
//      body: { date_debut, date_fin, couturier_id?, salon_id? }
// →    PDF blob

// GET  /api/comptabilite/export-excel
//      ?date_debut &date_fin &couturier_id? &salon_id?
// →    XLSX file
```

---

## Types TypeScript

```typescript
interface KPIsFinanciers {
  ca_total: number
  avances: number
  reste: number
  pct_avances: number
  nb_commandes: number
}

interface VariationKPIs {
  ca_variation_pct: number
  avances_variation_pct: number
  reste_variation_pct: number
}

interface StatutBreakdown {
  statut: string
  count: number
  ca: number
  avances: number
  reste: number
}

interface ClientStats {
  id: number
  nom: string
  prenom: string
  telephone: string
  email?: string
  nb_commandes: number
  ca_total: number
  avances: number
  reste: number
  derniere_commande: string
  is_vip: boolean
  has_creance: boolean
  is_fidele: boolean
}

interface EmployeStats {
  couturier_id: number
  nom: string
  prenom: string
  nb_commandes: number
  ca: number
  avances: number
  reste: number
  taux_encaissement: number
}
```

---

## Structure des fichiers à créer

```
app/(dashboard)/comptabilite/
  page.tsx
  _components/
    PeriodSelector.tsx
    KPICards.tsx
    StatutBreakdown.tsx
    GraphiqueEvolutionCA.tsx
    GraphiqueTopModeles.tsx
    TableClients.tsx
    ClientDetailDrawer.tsx
    AnalyseParEmploye.tsx
    ExportButtons.tsx
```
