# PROMPT 5 — Page : Mes Commandes (liste + création)

## Contexte à coller en début de prompt

```
Tu es un développeur senior Next.js 14. Implémente les pages "Mes Commandes"
(liste + création + détail + édition) pour l'application de gestion
d'atelier de couture "An's Learning".

Stack : Next.js 14 App Router (TypeScript strict), Tailwind CSS, shadcn/ui,
TanStack Query v5, react-hook-form + zod, react-dropzone, jspdf + html2canvas.

Branding : violet #B19CD9, turquoise #40E0D0, fond #FEFEFE.
Monnaie : FCFA. Format dates : dd/MM/yyyy.

Rôles :
- employe     → ses propres commandes uniquement
- admin       → toutes les commandes du salon
- super_admin → toutes les commandes tous salons
```

---

## PAGE A — Liste des Commandes `/commandes`

```
### Filtres (barre horizontale)
- Recherche texte (nom client, téléphone)
- Statut : En cours / Terminée / Livrée / Tous
- Date livraison : DateRangePicker
- Modèle : select (liste des modèles disponibles)
- Catégorie : Adulte / Enfant / Tous
- (admin+)       Employé : select couturiers du salon
- (super_admin+) Salon   : select tous les salons

### 4 Cards statistiques (filtrées selon filtres actifs)
  Commandes totales | En cours | Terminées | CA total période

### Toggle d'affichage : Liste ↔ Grid

Vue Liste (table) :
  Colonnes : # | Client | Modèle | Catégorie | Prix | Avance | Reste
             | Statut | Date livraison | Actions
  - Badge statut coloré
  - Reste : rouge si > 0, vert si = 0
  - Tri par colonne | Pagination 20/page

Vue Grid (cards) :
  Par commande :
    Avatar initiales client (cercle violet)
    Nom client + modèle
    Miniature tissu (si image présente)
    Badge statut
    Date livraison
    Reste à payer (badge rouge si > 0, vert si = 0)
    Boutons : Voir | Éditer | Fermer

### Actions par commande
  "Voir détail"         → /commandes/:id
  "Éditer"              → /commandes/:id/edit  (si statut != 'Livrée')
  "Télécharger PDF"     → GET /api/commandes/:id/pdf
  "Demander fermeture"  → si statut = 'Terminée'
  "Supprimer"           → admin seulement, confirmation dialog
                          DELETE /api/commandes/:id
```

---

## PAGE B — Détail d'une commande `/commandes/:id`

```
### En-tête
  Numéro commande (grand) | Badge statut | Date création + Date livraison
  Boutons : Éditer | Télécharger PDF | Demander fermeture

### Section Client
  Nom complet | Téléphone | Email
  Lien "Voir historique client"

### Section Vêtement
  Catégorie + Sexe + Modèle
  Tableau mesures (depuis champ JSONB) :
    Mesure          | Valeur (cm)
    Épaules         | 42
    Tour de taille  | 80
    ...

### Section Financière
  Prix total : X FCFA
  Avance payée : Y FCFA
  Reste à payer : Z FCFA  (rouge si > 0)
  ProgressBar paiement : Y/X %
  Historique paiements depuis historique_commandes

### Section Images
  Photo tissu  → thumbnail cliquable → lightbox
  Photo modèle → idem
  Bouton "Ajouter image" si absente

### Section Notes
  Affichage notes libres
```

---

## PAGE C/D — Créer `/commandes/nouvelle` & Éditer `/commandes/:id/edit`

```
Même composant FormCommande en mode création ou édition.
Le formulaire est divisé en 5 ÉTAPES (stepper visuel).

Règles stepper :
  - Validation Zod par étape (impossible d'avancer si erreur)
  - Indicateur visuel étapes complètes (checkmark vert)
  - Boutons Précédent / Suivant
  - Sauvegarde brouillon auto en localStorage toutes les 30 secondes
```

### Étape 1 — Informations générales

```
Schéma Zod :
  prix_total     : number, positif obligatoire
  avance         : number, min 0
  reste          : calculé auto = prix_total - avance (readonly)
  date_livraison : date, min = demain
  notes          : string max 1000 optionnel

Champs UI :
  Prix total (FCFA input numérique)
  Avance (FCFA input numérique)
  Reste à payer → calculé en temps réel, readonly, fond vert si 0 / rouge si > 0
  Date de livraison (DatePicker, min demain)
  Notes (textarea)
```

### Étape 2 — Client

```
Schéma Zod :
  client_mode    : 'existant' | 'nouveau'
  client_id      : number optionnel   (si existant)
  client_nom     : string min 2 optionnel (si nouveau)
  client_prenom  : string optionnel
  client_telephone : string min 8 optionnel
  client_email   : string email optionnel

UI :
  Toggle "Client existant" / "Nouveau client"

  Si existant :
    Combobox searchable (taper nom ou téléphone)
    → Autocomplete via GET /api/clients/search?q=...
    → Affiche clients matchants en dropdown
    → Sélection → affiche fiche client en read-only

  Si nouveau :
    Champs : Nom | Prénom | Téléphone | Email
```

### Étape 3 — Modèle & Mesures

```
Schéma Zod :
  categorie : 'adulte' | 'enfant'
  sexe      : 'homme' | 'femme'
  modele    : string, obligatoire
  mesures   : Record<string, number>  (clé = nom mesure, valeur = cm)

UI :
  1. Select catégorie (Adulte/Enfant) → met à jour la liste de modèles
  2. Select sexe (Homme/Femme)        → met à jour la liste de modèles
  3. Select modèle → filtré par catégorie + sexe depuis le catalogue

  4. CHAMPS MESURES DYNAMIQUES
     Selon le modèle choisi, afficher les mesures requises.
     Chaque mesure = input numérique (cm) avec son label.

     Exemples de modèles et leurs mesures :
     "Costume 3 pièces" (adulte homme) :
       Épaules | Poitrine | Tour de taille | Tour de hanches | Longueur veste
       Tour de bras | Longueur manche | Entrejambe | Longueur pantalon
       Tour de cuisse | Tour mollet

     "Robe de soirée" (adulte femme) :
       Épaules | Poitrine | Tour de taille | Tour de hanches
       Longueur robe | Tour de bras | Longueur manche

     [Recréer le catalogue complet depuis config.py]

Créer le fichier lib/modeles-catalogue.ts :
  const MODELES_CATALOGUE = {
    adulte: {
      homme: [ { nom: string, mesures: string[] }, ... ],
      femme: [ ... ]
    },
    enfant: {
      garcon: [ ... ],
      fille:  [ ... ]
    }
  }
```

### Étape 4 — Images

```
Zone upload tissu (react-dropzone) :
  Formats : JPG, PNG, WEBP | Max : 5MB
  Prévisualisation après sélection
  Bouton supprimer

Zone upload modèle (optionnel) :
  Même comportement
```

### Étape 5 — Résumé & Confirmation

```
Récapitulatif complet en lecture seule de toutes les étapes.
Preview PDF générée automatiquement :
  GET /api/commandes/preview-pdf?[toutes les données]

Checkbox "Je confirme les informations"
Bouton "Créer la commande" (vert) ou "Sauvegarder les modifications"
  → POST /api/commandes   (création)
  → PUT  /api/commandes/:id (édition)
  → Redirect vers /commandes/:id après succès
```

---

## API Routes

```typescript
// GET    /api/commandes
//        ?statut? &date_debut? &date_fin? &modele? &categorie?
//        &couturier_id? &salon_id? &search? &page? &limit?
// →      { commandes: Commande[], total: number, stats: StatsCommandes }

// GET    /api/commandes/:id
// →      { commande: CommandeDetail }

// POST   /api/commandes
//        body: CommandeCreate
// →      { success: boolean, commande: Commande }

// PUT    /api/commandes/:id
//        body: Partial<CommandeCreate>
// →      { success: boolean, commande: Commande }

// DELETE /api/commandes/:id   (admin seulement)
// →      { success: boolean }

// GET    /api/commandes/preview-pdf
//        ?[toutes les données commande en query params]
// →      PDF blob preview

// GET    /api/commandes/:id/pdf
// →      PDF blob final

// GET    /api/clients/search
//        ?q=string
// →      { clients: { id, nom, prenom, telephone, email }[] }

// POST   /api/commandes/:id/images/tissu
//        body: FormData
// →      { success: boolean, path: string }
```

---

## Types TypeScript

```typescript
interface Commande {
  id: number
  client_id: number
  couturier_id: number
  salon_id: string
  client_nom: string
  client_prenom: string
  client_telephone: string
  categorie: 'adulte' | 'enfant'
  sexe: 'homme' | 'femme'
  modele: string
  mesures: Record<string, number>
  prix_total: number
  avance: number
  reste: number
  date_livraison: string
  statut: 'En cours' | 'Terminée' | 'Livrée'
  notes?: string
  has_image_tissu: boolean
  has_image_modele: boolean
  has_pdf: boolean
  date_creation: string
  couturier_nom?: string   // admin/super_admin
}

interface StatsCommandes {
  total: number
  en_cours: number
  terminees: number
  livrees: number
  ca_total: number
}
```

---

## Structure des fichiers à créer

```
app/(dashboard)/commandes/
  page.tsx                    ← liste
  nouvelle/
    page.tsx                  ← création
  [id]/
    page.tsx                  ← détail
    edit/
      page.tsx                ← édition
  _components/
    FiltresCommandes.tsx
    TableCommandes.tsx
    GridCommandes.tsx
    CardCommande.tsx
    DetailCommande.tsx
    FormCommande/
      index.tsx               ← stepper parent
      Etape1Infos.tsx
      Etape2Client.tsx
      Etape3Mesures.tsx
      Etape4Images.tsx
      Etape5Resume.tsx
      ClientCombobox.tsx
      MesuresDynamiques.tsx

lib/
  modeles-catalogue.ts        ← catalogue complet des modèles
```
