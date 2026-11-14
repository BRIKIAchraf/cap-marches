# Cap Marchés

Cap Marchés transforme les données de marchés publics en signaux de
prospection explicables : acheteurs pertinents, budgets observés et fenêtres de
renouvellement estimées.

## Démarrage rapide

Sous Windows, la commande suivante crée l'environnement, installe les
dépendances et lance l'application :

```powershell
.\start.ps1
```

Ou, manuellement :

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
Copy-Item .env.example .env
streamlit run app.py
```

L'application fonctionne immédiatement avec l'API DECP sans clé. Le mode
`Démonstration hors ligne` utilise des lignes synthétiques clairement signalées.
Avant un usage public, renseignez votre adresse dans `APP_CONTACT` du fichier
`.env` afin que les appels de données soient correctement identifiés.

## Connecter Hémicycle

1. Ajoutez `https://api.hemicycle.ai/mcp` à votre assistant.
2. Demandez :

   > Appelle guide. Je construis un radar commercial à partir des marchés
   > publics DECP. Donne le nom exact de l'outil, ses paramètres, son coût, sa
   > source, sa licence et un exemple de réponse minimal.

3. Créez une clé API Hémicycle.
4. Copiez `.env.example` vers `.env`, puis renseignez :

```text
HEMICYCLE_API_KEY=votre_cle
HEMICYCLE_RECORDS_URL=url_exacte_retournee_par_guide
```

L'adaptateur générique envoie `query` et `limit`. Si l'outil indiqué par
`guide` emploie d'autres noms, modifiez seulement `services/hemicycle.py`.

## Connecter Featherless

Renseignez dans `.env` :

```text
FEATHERLESS_API_KEY=votre_cle
FEATHERLESS_MODEL=zai-org/GLM-5.2
```

L'IA explique uniquement les cinq meilleurs signaux. Elle ne calcule pas le
classement et reçoit un sous-ensemble limité des champs publics.

## Score

Le score sur 100 est entièrement déterministe :

- correspondance des mots-clés : 30 points ;
- territoire : 20 points ;
- montant ciblé : 20 points ;
- fin de contrat estimée : 30 points.

La date de fin est une estimation : `date de notification + durée en mois`.
Elle ne constitue ni une date d'appel d'offres ni une prédiction certaine.

## Tests

```powershell
python -m unittest discover -s tests -v
```

## Sources et réutilisation

- Hémicycle : source et licence retournées par l'outil `guide`.
- Données essentielles de la commande publique :
  <https://data.economie.gouv.fr/explore/assets/decp-2022-marches-valides/>
- API Explore :
  <https://data.economie.gouv.fr/api/explore/v2.1/catalog/datasets/decp-2022-marches-valides/records>
- Licence : Licence Ouverte 2.0 (Etalab).

Le client limite chaque recherche à 100 lignes, met les résultats en cache
pendant une heure et s'identifie par un `User-Agent`. Remplacez le contact du
`User-Agent` via `APP_CONTACT` avant une utilisation publique.

## Démo de trois minutes

1. Saisir une offre, par exemple `logiciel RH`.
2. Lancer l'analyse et montrer les quatre indicateurs.
3. Ouvrir le meilleur score et expliquer ses quatre composantes.
4. Générer la note Featherless.
5. Terminer par la source, la licence et les limites de l'estimation.

