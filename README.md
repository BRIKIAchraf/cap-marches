# Cap Marchés

Cap Marchés transforme trois jeux publics en signaux de prospection
explicables : projets d'achats à venir, marchés déjà notifiés et identité des
acheteurs issue de Sirene.

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

La vue historique fonctionne avec l'API DECP sans clé. La vue prospective
requiert Hémicycle ; sans clé, elle utilise des lignes synthétiques clairement
signalées.
Avant un usage public, renseignez votre adresse dans `APP_CONTACT` du fichier
`.env` afin que les appels de données soient correctement identifiés.

## Connecter Hémicycle

1. Créez une clé sur <https://hemicycle.ai/compte-api>.
2. Copiez `.env.example` vers `.env`, puis renseignez :

```text
HEMICYCLE_API_KEY=votre_cle
HEMICYCLE_API_URL=https://api.hemicycle.ai/v1/jeux/interroger
HEMICYCLE_API_VERSION=2026-10-01
```

L'application emploie deux pages Hémicycle pour une analyse enrichie : une page
du jeu principal et une page Sirene. Chaque page coûte actuellement 1 crédit.

### Jeux exploités

- `projets_achats_publics` : projets annoncés sur APProch avant l'appel
  d'offres, dates, budgets estimés et liens de consultation ;
- `marches_publics` : historique DECP, montants, durées, acheteurs et
  titulaires ;
- `sirene_etablissements` : dénomination, activité et commune de chaque
  acheteur.

## Connecter Featherless

Renseignez dans `.env` :

```text
FEATHERLESS_API_KEY=votre_cle
FEATHERLESS_MODEL=zai-org/GLM-5.2
```

L'IA explique uniquement les cinq meilleurs signaux. Elle ne calcule pas le
classement et reçoit un sous-ensemble limité des champs publics.

## Score

Le score sur 100 est entièrement déterministe. Pour les projets à venir :

- correspondance des mots-clés : 30 points ;
- territoire : 20 points ;
- tranche de montant : 20 points ;
- proximité de la publication : 30 points.

Pour les marchés notifiés :

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

- Hémicycle, projets d'achats publics :
  <https://hemicycle.ai/bibliotheque/projets_achats_publics>
- Hémicycle, marchés publics notifiés :
  <https://hemicycle.ai/bibliotheque/marches_publics>
- Hémicycle, répertoire Sirene :
  <https://hemicycle.ai/bibliotheque/sirene_etablissements>
- Données essentielles de la commande publique :
  <https://data.economie.gouv.fr/explore/assets/decp-2022-marches-valides/>
- API Explore :
  <https://data.economie.gouv.fr/api/explore/v2.1/catalog/datasets/decp-2022-marches-valides/records>
- Licence : Licence Ouverte 2.0 (Etalab).

Le client limite chaque recherche à 100 lignes, met les résultats en cache
pendant une heure et s'identifie par un `User-Agent`. Remplacez le contact du
`User-Agent` via `APP_CONTACT` avant une utilisation publique.

## Démo de trois minutes

1. Ouvrir la vue `Opportunités à venir` et saisir `logiciel RH`.
2. Montrer la date de publication, le budget et le lien de consultation.
3. Montrer le nom de l'acheteur enrichi par Sirene.
4. Passer à l'historique pour expliquer les budgets et renouvellements.
5. Générer la note Featherless et terminer par les sources et limites.

