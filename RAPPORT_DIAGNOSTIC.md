# Rapport de Diagnostic — Application Couturier Multi-Tenant
**Date :** 22 avril 2026
**Approche :** Audit complet (lecture seule), puis correctifs minimaux ciblés.
**Priorité absolue :** Zéro régression, compatibilité totale avec l'existant.

---

## RÉSUMÉ EXÉCUTIF

| Point | Domaine | État | Corrections appliquées |
|-------|---------|------|------------------------|
| A | Dashboard SuperAdmin | ⚠️ 1 code mort, 1 asymétrie charges | 1 fix appliqué |
| B | Détail commande vide | 🔴 Bug reproductible (INNER JOIN) | 1 fix appliqué |
| C | PDF + QR Code | ✅ Fonctionnel, 2 remarques | Aucune (non-bloquant) |
| D | Remontée données employé→admin→superadmin | ⚠️ salon_id nullable sur charges/clients | Recommandations SQL |
| E | Fermer mes commandes | ⚠️ historique non mis à jour | 1 fix appliqué |
| F | Modèles & Calendrier + configs | ⚠️ Features manquantes | Migration SQL fournie |

**Corrections appliquées dans ce rapport : 3**

---

## A — Dashboard SuperAdmin

### État actuel
Les 7 sous-onglets sont tous implémentés dans super_admin_dashboard.py :
- tabs[0] -> afficher_vue_ensemble()
- tabs[1] -> afficher_gestion_salons()
- tabs[2] -> afficher_gestion_utilisateurs()
- tabs[3] -> afficher_toutes_commandes()
- tabs[4] -> afficher_statistiques_avancees()
- tabs[5] -> afficher_demandes_globales_super_admin()  (ligne 1430, existe)
- tabs[6] -> afficher_rapports()

### Problème A-1 — Code mort dans obtenir_tous_utilisateurs()

**Fichier :** controllers/super_admin_controller.py, ligne 393 (avant fix)
**Cause :** La ligne `where_clause = "WHERE salon_id = %s"` était immédiatement écrasée
par le bloc conditionnel suivant. Pas de bug fonctionnel, mais code trompeur.
**Correction APPLIQUÉE :** Suppression de la ligne morte. Le params.append(salon_id)
et la vraie clause WHERE sont conservés intacts.

### Problème A-2 — Asymétrie agrégation charges (sans période vs avec période)

**Fichier :** controllers/super_admin_controller.py, ligne 77
**Cause :** Sans période = toutes les charges (historique complet). Avec période =
charges filtrées par date_charge. Cohérent en soi mais surprenant visuellement.
**Note :** La table charges n'a pas de colonne est_supprime, donc aucun filtre
de ce type n'est nécessaire ici.
**Correction :** Non appliquée (comportement existant voulu, risque de régression).

### Plan de test A
1. Connexion SUPER_ADMIN.
2. Cliquer sur chaque onglet -> vérifier absence de NameError.
3. Onglet "Gérer utilisateurs" -> filtrer par salon -> vérifier isolation correcte.
4. Onglet "Vue d'ensemble" -> alterner sans/avec période -> vérifier cohérence.
5. Onglet "Demandes (global)" -> vérifier affichage des demandes multi-salons.

---

## B — Détail commande vide (Mes commandes)

### Flux actuel
1. lister_commandes_couturier(id) -> liste (utilise LEFT JOIN couturiers)
2. Sélection selectbox -> obtenir_details_commande(commande_id)
3. obtenir_commande() -> 3 requêtes en cascade (full, no_pdf, legacy)

### Problème B-1 — INNER JOIN dans obtenir_commande() (BUG PRINCIPAL)

**Fichier :** models/database.py, lignes 1100-1101, 1121-1122, 1142-1143 (avant fix)
**Cause :** Les 3 variantes de requête utilisaient JOIN (INNER JOIN implicite) sur
clients et couturiers. Si une commande a un client_id pointant vers un client
supprimé physiquement, la jointure retourne 0 lignes -> result = None -> la vue
affiche "Impossible de charger les détails".
**Paradoxe :** lister_commandes_couturier() utilise LEFT JOIN couturiers dans
plusieurs variantes, donc la commande apparaît dans la liste mais ne peut pas
être détaillée.
**Correction APPLIQUÉE :** Les 6 lignes JOIN -> LEFT JOIN dans les 3 requêtes de
obtenir_commande(). Les colonnes client/couturier sont NULL si la relation est
absente mais le détail s'affiche. La vue gère les None avec .get().

### Problème B-2 — Validation mesures : TypeError potentiel sur None

**Fichier :** views/commande_view.py
**Cause :** `mesures_invalides = [m for m, v in mesures_dict.items() if v <= 0]`
lève TypeError si v = None.
**Correction recommandée (non appliquée, hors scope immédiat) :**
  mesures_invalides = [m for m, v in mesures_dict.items() if v is None or v <= 0]

### Plan de test B
1. Connexion employé -> "Mes Commandes".
2. Sélectionner chaque commande -> vérifier affichage des détails.
3. Cas limite : commande avec client absent -> vérifier que les champs disponibles
   s'affichent quand même (modèle, prix, dates).
4. Cliquer "Générer PDF" -> vérifier que le PDF est produit.

---

## C — Nouvelle commande + PDF + QR Code

### État actuel (fonctionnel)

QR Code : JSON complet avec infos client, financier, couturier, dates, statut.
La fonction _json_sanitize_qr() est robuste (Decimal, datetime, bytes gérés).

PDF : Palette mauve/or cohérente, pas de salon_id technique dans le corps.
L'ID de commande (référence interne) est affiché volontairement comme numéro.
Filigrane : désactivé dans PDF commande, présent à 10% dans PDF livraison.
Logo : multi-tenant via table app_logo (par salon_id), fallback assets/logo.*.

### Remarque C-1 — Données confidentielles dans le QR

Fichier : controllers/pdf_controller.py, lignes 775-813
Constat : Téléphone et email du client encodés en clair. Acceptable pour
usage interne salon. Si confidentialité requise, encoder uniquement
{"commande_id": X} et re-consulter la BDD.
Correction : Non appliquée (comportement intentionnel).

### Remarque C-2 — Pas de thème couleur par salon

Constat : Couleurs hardcodées (#9B8AB5, #E8DCC4). Tous salons = même thème.
Correction : Migration SQL fournie au Point F.

### Plan de test C
1. Créer commande -> vérifier génération PDF.
2. Scanner QR -> vérifier JSON lisible avec infos correctes.
3. Vérifier visuellement que logo/filigrane ne masquent aucun texte.
4. Vérifier absence du code salon dans le corps du PDF.

---

## D — Remontée des données : Employé -> Admin salon -> Super Admin

### État actuel (globalement correct)

- Toutes commandes ont salon_id NOT NULL (FK vers salons). OK.
- Admin filtre via sous-requête : WHERE couturier_id IN (SELECT id FROM couturiers WHERE salon_id = %s). OK.
- Superadmin appelle sans filtre salon_id -> agrégation globale. OK.
- Calendrier et galerie filtrent par salon_id. OK.

### Problème D-1 — charges.salon_id et clients.salon_id sont nullable

Fichier : database_schema.sql
Cause : Colonnes salon_id définies comme NULL dans ces tables. Un enregistrement
créé sans propagation du salon_id devient "orphelin" du filtre multi-tenant.
Impact : Ces enregistrements n'apparaissent pas dans les vues admin/superadmin.

Recommandation SQL (exécuter après vérification des données) :

  -- Peupler les NULL existants
  UPDATE charges SET salon_id = (
      SELECT c.salon_id FROM couturiers c WHERE c.id = charges.couturier_id
  ) WHERE salon_id IS NULL AND couturier_id IS NOT NULL;

  UPDATE clients SET salon_id = (
      SELECT c.salon_id FROM couturiers c WHERE c.id = clients.couturier_id
  ) WHERE salon_id IS NULL AND couturier_id IS NOT NULL;

### Problème D-2 — historique_commandes sans colonne salon_id

Fichier : database_schema.sql, table historique_commandes
Cause : Pas de salon_id direct. Filtrage via double jointure historique->commande->couturier->salon.
Impact : Requêtes plus complexes, risque cross-tenant si jointure omise.

Recommandation SQL :

  ALTER TABLE historique_commandes ADD COLUMN IF NOT EXISTS salon_id VARCHAR(50) NULL
      REFERENCES salons(salon_id) ON DELETE SET NULL;

  UPDATE historique_commandes SET salon_id = (
      SELECT c.salon_id FROM commandes c WHERE c.id = historique_commandes.commande_id
  ) WHERE salon_id IS NULL;

  CREATE INDEX IF NOT EXISTS idx_historique_salon_id ON historique_commandes(salon_id);

### Plan de test D
1. Employé salon A : créer 1 commande + 1 charge.
2. Admin salon A : vérifier présence des 2 enregistrements.
3. Admin salon B : vérifier ABSENCE des données du salon A.
4. SuperAdmin : vérifier vision globale des deux salons.

---

## E — Onglet "Fermer mes commandes"

### État actuel du flux
1. Employé (reste=0) -> bouton "Envoyer la demande" -> INSERT historique_commandes
   (type_action='fermeture_demande', statut_validation='en_attente').
2. Admin voit la demande -> bouton "Valider et passer en Livré et payé".
3. valider_commande_livree_payee() -> UPDATE commandes.statut = 'Livré et payé'.
4. SuperAdmin voit toutes les demandes dans l'onglet "Demandes (global)".

Condition reste > 0 : Le bouton est déjà masqué (non rendu) quand reste > 0.01.
Anti-doublon : Vérification applicative (SELECT avant INSERT). Fonctionnel.

### Problème E-1 — valider_commande_livree_payee() ne met pas à jour historique

Fichier : models/database.py, fonction valider_commande_livree_payee() (avant fix)
Cause : La fonction mettait à jour commandes.statut mais laissait
historique_commandes.statut_validation à 'en_attente'. Après validation admin,
la demande restait visible dans l'onglet "Demandes en attente" du SuperAdmin.

Correction APPLIQUÉE : Ajout d'un UPDATE historique_commandes encapsulé dans
try/except non-bloquant. Si la table est absente (edge case), l'erreur est loggée
mais la validation de la commande réussit quand même.

Code ajouté dans valider_commande_livree_payee() :

  # Mettre à jour le statut de la demande dans historique (si en attente)
  try:
      cursor.execute(
          """UPDATE historique_commandes
               SET statut_validation = 'validee', date_validation = NOW()
               WHERE commande_id = %s
                 AND type_action = 'fermeture_demande'
                 AND statut_validation = 'en_attente'""",
          (commande_id,),
      )
  except Exception as _e_hist:
      print(f"Avertissement historique valider_livree_payee: {_e_hist}")

### Nettoyage des données historiques existantes

Les demandes créées AVANT ce déploiement restent en 'en_attente' même si la
commande est déjà en 'Livré et payé'. Exécuter ce correctif SQL une fois :

  UPDATE historique_commandes h
  SET statut_validation = 'validee', date_validation = NOW()
  FROM commandes c
  WHERE h.commande_id = c.id
    AND h.type_action = 'fermeture_demande'
    AND h.statut_validation = 'en_attente'
    AND c.statut = 'Livré et payé';

### Plan de test E
1. Commande avec reste=0 -> onglet "Fermer mes commandes" -> bouton visible.
2. Envoyer la demande -> statut passe en "Demande en attente".
3. Retenter l'envoi -> vérifier qu'aucun doublon n'est créé.
4. Admin valide -> commandes.statut = 'Livré et payé'.
5. SuperAdmin onglet "Demandes (global)" -> vérifier que la demande N'APPARAIT PLUS
   dans les demandes en attente (correction E-1).

---

## F — Modèles & Calendrier + Configurations métier

### État actuel

Galerie photos : Fonctionne via calendrier_view.py, filtré par salon_id.
Calendrier : Fonctionne avec filtre salon_id, tri urgence, filtres date+couturier.
Configurations manquantes : Aucune colonne max_habits_par_jour,
delais_par_modele, pdf_theme_color dans le schéma actuel.

### Migration SQL — Fonctionnalités manquantes (à exécuter manuellement)

  -- Limite quotidienne de livraisons (NULL = illimité)
  ALTER TABLE salons
      ADD COLUMN IF NOT EXISTS max_habits_par_jour INTEGER DEFAULT NULL;

  -- Délais par type de modèle (JSON texte)
  -- Format : {"pantalon": 5, "boubou": 7, "jupe": 3, "robe": 6}
  -- NULL = pas de délai configuré
  ALTER TABLE salons
      ADD COLUMN IF NOT EXISTS delais_par_modele TEXT DEFAULT NULL;

  -- Couleur principale PDF (hex 7 chars, ex: #1A73E8)
  -- NULL ou code invalide = fallback sur #9B8AB5 (mauve défaut)
  ALTER TABLE salons
      ADD COLUMN IF NOT EXISTS pdf_theme_color VARCHAR(7) DEFAULT NULL;

### Utilisation Python — obtenir_config_salon() (à ajouter dans salon_model.py)

  def obtenir_config_salon(self, salon_id: str) -> dict:
      import re, json
      try:
          cursor = self.db.get_connection().cursor()
          cursor.execute("""
              SELECT max_habits_par_jour, delais_par_modele, pdf_theme_color
              FROM salons WHERE salon_id = %s
          """, (salon_id,))
          row = cursor.fetchone()
          cursor.close()
      except Exception:
          row = None
      delais = {}
      pdf_color = "#9B8AB5"  # fallback mauve
      max_par_jour = None
      if row:
          max_par_jour = row[0]
          if row[1]:
              try:
                  delais = json.loads(row[1])
              except Exception:
                  delais = {}
          if row[2] and re.match(r'^#[0-9A-Fa-f]{6}$', str(row[2])):
              pdf_color = row[2]
      return {
          'max_habits_par_jour': max_par_jour,
          'delais_par_modele': delais,
          'pdf_theme_color': pdf_color,
      }

### Plan de test F
1. Exécuter la migration SQL ci-dessus.
2. Admin : configurer max_habits_par_jour = 4 pour son salon.
3. Créer 5 commandes le même jour -> vérifier que la 5e propose une date décalée.
4. Configurer delais_par_modele = {"pantalon": 5, "boubou": 8}.
5. Créer commande "pantalon" -> vérifier date suggérée = J+5.
6. Configurer pdf_theme_color = "#1A73E8" -> générer PDF -> vérifier bandeaux bleus.
7. Saisir code invalide (#ZZZZZZ) -> vérifier fallback mauve dans le PDF.

---

## Récapitulatif — Fichiers modifiés

| Fichier | Modification | Fix |
|---------|-------------|-----|
| models/database.py | obtenir_commande() : 6 JOIN -> LEFT JOIN | Fix 1 |
| models/database.py | valider_commande_livree_payee() : UPDATE historique | Fix 2 |
| controllers/super_admin_controller.py | obtenir_tous_utilisateurs() : dead code | Fix 3 |

## Ce qui a été volontairement laissé inchangé

| Sujet | Raison |
|-------|--------|
| QR Code avec données client complètes | Fonctionnel, intentionnel |
| Couleurs PDF hardcodées | Dépend de la migration F (non déployée) |
| Anti-doublon demandes (applicatif) | Fonctionne, contrainte SQL = risque si données incohérentes |
| mesures_invalides validation None | Mineur, hors scope immédiat |
| charges.salon_id nullable | Requiert migration + vérification données prod |

## Risques résiduels

1. Données historiques incohérentes (avant déploiement) : Exécuter le SQL de
   nettoyage fourni à la section E pour synchroniser les statuts existants.
2. Commandes avec client/couturier supprimé (après Fix 1) : Champs client
   apparaissent vides (None) mais la commande reste visible. Acceptable.
3. Migration F non exécutée : Les fonctionnalités max_habits et thème PDF
   restent inopérantes jusqu'à exécution du ALTER TABLE.
