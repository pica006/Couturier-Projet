# PROMPT 3 — Page : Mes Frais (Charges)

## Contexte à coller en début de prompt

```
Tu es un développeur senior Next.js 14. Implémente la page "Mes Frais"
pour l'application de gestion d'atelier de couture "An's Learning".

Stack : Next.js 14 App Router (TypeScript strict), Tailwind CSS, shadcn/ui,
TanStack Query v5, react-hook-form + zod, react-dropzone, Recharts.

Branding : violet #B19CD9, turquoise #40E0D0, fond #FEFEFE.
Monnaie : FCFA. Format dates : dd/MM/yyyy.

Rôles :
- employe     → ses charges uniquement
- admin       → toutes les charges du salon + filtre par employé
- super_admin → toutes charges tous salons
```

---

## ONGLET 1 — Ajouter une Charge

```
### Formulaire (react-hook-form + Zod)

Schéma de validation :
  type      : 'Fixe' | 'Ponctuelle' | 'Salaire' | 'Commande'
  categorie : selon le type (voir ci-dessous)
  montant   : number, positif obligatoire
  date_charge : date, par défaut aujourd'hui
  reference : string optionnel (libellé ex: "Loyer Janvier 2025")
  notes     : string max 500 optionnel
  commande_id : number optionnel (uniquement si type = 'Commande')

### Catégories par type
  Fixe       → Loyer, Électricité, Internet, Abonnement
  Ponctuelle → Matériel, Transport, Communication, Fournitures, Autre
  Salaire    → Salaire employé
  Commande   → Tissu, Accessoires, Sous-traitance

### Champ conditionnel : type = 'Commande'
- Afficher un select "Lier à une commande"
- Liste des commandes en cours du couturier (client + modèle)
- Appel : GET /api/commandes?statut=En cours&couturier_id=...

### Justificatif (Dropzone)
- Formats acceptés : PDF, JPG, PNG — max 5MB
- Prévisualisation si image
- Bouton supprimer le fichier sélectionné

### Soumission
POST /api/charges
→ Réinitialise le formulaire
→ Toast "Charge ajoutée avec succès"
```

---

## ONGLET 2 — Voir / Modifier mes Charges

```
### Filtres en haut
- Période (DateRangePicker)
- Type : Fixe / Ponctuelle / Salaire / Commande / Tous
- Catégorie : select
- (admin+) Employé : dropdown couturiers du salon

### Cards statistiques
- Total charges sur la période : X FCFA  (card violette)
- Charge la plus élevée : catégorie + montant
- Nombre total de charges
- Donut Chart (Recharts) : répartition par type en %

### Table des charges
Colonnes :
  # | Date | Type | Catégorie | Libellé | Montant (FCFA) | Justificatif | Actions

- Montant formaté avec séparateur milliers
- Justificatif : icône cliquable si présent, tiret sinon
- Actions :
    Crayon → modal édition (même form pré-rempli)
             PUT /api/charges/:id → toast "Charge modifiée"
    Poubelle → confirmation dialog
              DELETE /api/charges/:id → toast + refresh liste

### Graphique évolution (sous le tableau)
AreaChart Recharts : total des charges sur les 6 derniers mois
X = mois | Y = montant FCFA | Couleur = #B19CD9
```

---

## ONGLET 3 — Calcul Taxes & Rapports

```
### Sélecteur de période
Options : Année courante (défaut) | Trimestre | Personnalisée (DateRangePicker)

### Récapitulatif financier (cards en grid)
- Chiffre d'affaires brut (somme prix_total commandes période)
- Total charges
- Résultat net (CA - charges)
- Impôt estimé
- Résultat après impôt

### Barème d'imposition FCFA (affiché visuellement)
  Tranche 1 : 0 – 1 000 000 FCFA          → Exonéré
  Tranche 2 : 1 000 001 – 5 000 000 FCFA  → 35 000 FCFA
  Tranche 3 : 5 000 001 – 7 000 000 FCFA  → 78 000 FCFA
  Tranche 4 : > 7 000 000 FCFA            → Calcul proportionnel

→ Mettre en surbrillance (bordure violette) la tranche applicable

### Bouton "Calculer"
GET /api/charges/calcul-taxes?date_debut=...&date_fin=...&couturier_id=...
→ Affiche résultats + indique la tranche

### Répartition des charges
PieChart Recharts par catégorie avec légende et pourcentages.

### Génération rapport PDF
Bouton "Générer rapport PDF"
→ POST /api/charges/rapport-pdf { periode, couturier_id }
→ Télécharge PDF contenant :
    En-tête salon (logo, nom, adresse)
    Période couverte
    Tableau récapitulatif revenus
    Tableau détaillé charges par catégorie
    Calcul fiscal avec barème
    Résultat net
    Footer date génération

Bouton "Exporter CSV"
→ GET /api/charges/export-csv?date_debut=...&date_fin=...
```

---

## API Routes

```typescript
// GET    /api/charges
//        ?couturier_id? &salon_id? &date_debut? &date_fin?
//        &type? &categorie? &page? &limit?
// →      { charges: Charge[], total: number, stats: StatsCharges }

// POST   /api/charges
//        body: ChargeCreate
// →      { success: boolean, charge: Charge }

// PUT    /api/charges/:id
//        body: Partial<ChargeCreate>
// →      { success: boolean, charge: Charge }

// DELETE /api/charges/:id
// →      { success: boolean }

// GET    /api/charges/calcul-taxes
//        ?couturier_id? &salon_id? &date_debut &date_fin
// →      { ca_brut, total_charges, resultat_net, impot,
//           resultat_apres_impot, tranche: 1|2|3|4, tranche_label }

// POST   /api/charges/rapport-pdf
//        body: { periode: { debut, fin }, couturier_id? }
// →      PDF blob

// GET    /api/charges/export-csv
//        ?couturier_id? &salon_id? &date_debut? &date_fin?
// →      CSV file

// POST   /api/charges/:id/justificatif
//        body: FormData
// →      { success: boolean }

// GET    /api/charges/:id/justificatif
// →      file blob
```

---

## Types TypeScript

```typescript
interface Charge {
  id: number
  couturier_id: number
  salon_id: string
  type: 'Fixe' | 'Ponctuelle' | 'Salaire' | 'Commande'
  categorie: string
  montant: number
  date_charge: string
  reference?: string
  notes?: string
  commande_id?: number
  has_justificatif: boolean
  date_creation: string
  couturier_nom?: string   // admin/super_admin
}

interface StatsCharges {
  total: number
  count: number
  top_categorie: string
  top_montant: number
  par_type: { type: string; montant: number; pct: number }[]
  par_categorie: { categorie: string; montant: number }[]
  evolution_6mois: { mois: string; montant: number }[]
}

interface ResultatFiscal {
  ca_brut: number
  total_charges: number
  resultat_net: number
  impot: number
  resultat_apres_impot: number
  tranche: 1 | 2 | 3 | 4
  tranche_label: string
}
```

---

## Structure des fichiers à créer

```
app/(dashboard)/mes-frais/
  page.tsx
  _components/
    OngletAjouter.tsx
    OngletVoirCharges.tsx
    OngletTaxesRapports.tsx
    FormulaireCharge.tsx
    TableCharges.tsx
    StatsChargesCards.tsx
    BaremeFiscal.tsx
    GraphiqueEvolution.tsx
    PdfDropzone.tsx
```
