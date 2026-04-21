# PROMPT 2 — Page : Fermer mes Commandes

## Contexte à coller en début de prompt

```
Tu es un développeur senior Next.js 14. Implémente la page "Fermer mes Commandes"
pour l'application de gestion d'atelier de couture "An's Learning".

Stack : Next.js 14 App Router (TypeScript strict), Tailwind CSS, shadcn/ui,
TanStack Query v5, react-hook-form + zod.

Branding : violet #B19CD9, turquoise #40E0D0, fond #FEFEFE.
Monnaie : FCFA. Format dates : dd/MM/yyyy.

Rôles : employe | admin | super_admin.
```

---

## ONGLET 1 — Modifier Paiements

```
### But
L'employé modifie les données financières d'une commande avant fermeture.
L'admin valide ou rejette la modification.

### Vue employé
- Liste ses commandes statut "En cours" ou "Terminée"
- Colonnes : client + modèle | prix total | avance | reste à payer | bouton Modifier
- Bouton "Modifier" → ouvre modal

### Modal modification paiement (Zod)
Champs :
  prix_total : number, min 0
  avance     : number, min 0, max prix_total
  reste      : calculé auto (readonly, mis à jour en temps réel)
  notes      : string optionnel (textarea)

Validation :
  avance ne peut pas dépasser prix_total

Soumission :
  POST /api/commandes/:id/modifier-paiement
  → crée entrée historique_commandes statut_validation='en_attente'
  → toast "Modification envoyée, en attente validation admin"
  → désactiver le bouton "Modifier" sur cette commande (déjà en attente)

### Vue admin
- Toutes les modifications en attente du salon
- Colonnes : client | couturier | ancien prix | nouveau prix | reste | date demande
- Par ligne :
    Accepter → PUT /api/commandes/:id/valider-paiement { action:'accepter' }
              → met à jour commande, toast vert
    Rejeter  → dialog avec champ commentaire OBLIGATOIRE
              → PUT /api/commandes/:id/valider-paiement { action:'rejeter', commentaire }
              → toast orange
- Badge compteur "X en attente" dans le titre de l'onglet
```

---

## ONGLET 2 — Commandes Terminées

```
### But
Demander la fermeture officielle d'une commande terminée.

### Vue employé
- Liste ses commandes statut = "Terminée"
- Affiche pour chaque commande :
    info client + modèle
    prix total / avance / reste
    date livraison prévue
    badge "En attente validation" si demande déjà soumise
- Bouton "Demander fermeture" (masqué si déjà en attente)
  → confirmation dialog "Confirmer que la commande est terminée et prête à livrer ?"
  → POST /api/commandes/:id/demander-fermeture
  → toast "Demande envoyée à l'admin"

### Vue admin
Section "Demandes de fermeture en attente" :
- Colonnes : client | modèle | couturier | prix | avance | reste | date demande
- Par ligne :
    Approuver → dialog confirmation + commentaire optionnel
              → PUT /api/commandes/:id/fermer { commentaire? }
              → commande passe statut "Livrée"
    Rejeter   → dialog + commentaire OBLIGATOIRE
              → notification au couturier

### Vue super_admin
- Même que admin + filtre par salon
```

---

## ONGLET 3 — Documents PDF

```
### But
Upload et gestion des PDFs finaux des commandes.

### Vue employé
- Liste ses commandes statut "Terminée" ou "Livrée"
- Pour chaque commande :
    Badge vert "PDF présent" si déjà uploadé
    Bouton "Uploader PDF" → Dropzone (PDF uniquement, max 10MB)
      → préview nom fichier
      → bouton "Confirmer upload"
      → POST /api/commandes/:id/upload-pdf (multipart/form-data)
      → toast succès/erreur
    Bouton "Télécharger" si PDF présent → GET /api/commandes/:id/pdf
    Bouton "Supprimer" → confirmation dialog

### Vue admin
- Voit tous les PDFs du salon (toutes commandes, tous employés)
- Peut uploader pour n'importe quelle commande
- Colonnes : commande (client+modèle) | couturier | statut PDF | date upload | actions
- Actions : voir | télécharger | supprimer
```

---

## API Routes

```typescript
// GET  /api/commandes/paiements-en-attente
//      ?salon_id? &couturier_id?
// →    { demandes: DemandePaiement[] }

// POST /api/commandes/:id/modifier-paiement
//      body: { prix_total: number, avance: number, notes?: string }
// →    { success: boolean, historique_id: number }

// PUT  /api/commandes/:id/valider-paiement
//      body: { action: 'accepter'|'rejeter', commentaire?: string }
// →    { success: boolean }

// GET  /api/commandes/fermetures-en-attente
//      ?salon_id? &couturier_id?
// →    { demandes: DemandeFermeture[] }

// POST /api/commandes/:id/demander-fermeture
// →    { success: boolean }

// PUT  /api/commandes/:id/fermer
//      body: { commentaire?: string }
// →    { success: boolean }

// POST /api/commandes/:id/upload-pdf
//      body: FormData (file)
// →    { success: boolean, file_name: string }

// GET  /api/commandes/:id/pdf
// →    PDF blob (Content-Type: application/pdf)

// DELETE /api/commandes/:id/pdf
// →    { success: boolean }
```

---

## Types TypeScript

```typescript
interface DemandePaiement {
  id: number
  commande_id: number
  client_nom: string
  modele: string
  couturier_nom: string
  prix_ancien: number
  prix_nouveau: number
  avance_ancienne: number
  avance_nouvelle: number
  reste: number
  notes?: string
  date_demande: string
  statut_validation: 'en_attente' | 'accepte' | 'rejete'
  commentaire_admin?: string
}

interface DemandeFermeture {
  id: number
  commande_id: number
  client_nom: string
  client_prenom: string
  modele: string
  couturier_nom: string
  prix_total: number
  avance: number
  reste: number
  date_livraison: string
  date_demande: string
  statut_validation: 'en_attente' | 'accepte' | 'rejete'
}
```

---

## Structure des fichiers à créer

```
app/(dashboard)/fermer-commandes/
  page.tsx
  _components/
    OngletPaiements.tsx
    OngletTerminees.tsx
    OngletDocuments.tsx
    ModalModifPaiement.tsx
    CardDemandeFermeture.tsx
    PdfDropzone.tsx
    BadgeStatutValidation.tsx
```

---

## Règles importantes

```
- Un employé ne peut soumettre qu'une demande à la fois par commande
- Désactiver le bouton "Soumettre" si demande déjà en attente
- Admin ne peut pas fermer sa propre commande (vérification côté API)
- Toutes les actions tracées dans historique_commandes
- Afficher le commentaire de rejet visible à l'employé concerné
- Toasts (sonner) pour toutes les actions
- Confirmation dialog pour les actions irréversibles
```
