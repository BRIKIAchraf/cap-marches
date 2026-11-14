# Cap Marchés

Cap Marchés est un agent de veille commerciale sur la commande publique. Il
croise les projets d'achats à venir, l'historique des marchés et Sirene, puis
classe chaque signal avec un score hybride explicable et un dossier de preuves.

## Ce qui est implémenté

- moteur de recherche sur `projets_achats_publics`, `marches_publics` et
  `sirene_etablissements` ;
- similarité sémantique locale TF-IDF, ou embeddings multilingues facultatifs ;
- score hybride sur 100 : sens 35, mots-clés 15, territoire 15, budget 15,
  calendrier ou renouvellement 20 ;
- profil d'entreprise persistant servant de mémoire à l'agent ;
- agent outillé avec plan contrôlé, appels bornés et preuves visibles ;
- synthèse Featherless facultative, limitée aux preuves sélectionnées ;
- collecte des retours commerciaux, recherches sauvegardées et export CSV ;
- pipeline d'apprentissage supervisé activable après 100 vrais labels et deux
  classes ;
- SQLite en local, PostgreSQL en production, Docker et CI GitHub Actions.

## Architecture

```text
Streamlit
├── Radar principal       recherche, scoring, export, feedback
├── Profil entreprise     mémoire durable
├── Agent IA              plan → outils → classement → preuves → LLM
└── Apprentissage         contrôle des labels et modèle candidat
        │
        ├── Hémicycle     projets futurs, marchés, Sirene
        ├── DECP          repli historique sans clé
        ├── Semantic      TF-IDF / sentence-transformers
        ├── Scoring       règles métier explicables
        ├── Evidence      faits autorisés et sources
        └── Storage       SQLite / PostgreSQL
```

Le LLM ne recherche pas directement dans Internet et ne modifie pas le score.
Il reçoit au maximum dix dossiers de preuves structurés. Une absence de donnée
doit rester une absence, jamais une invention.

## Démarrage local

Sous Windows :

```powershell
.\start.ps1
```

Installation manuelle :

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
Copy-Item .env.example .env
streamlit run app.py
```

Sans clé, la démonstration utilise des données synthétiques clairement
signalées. L'historique DECP reste accessible sans authentification.

## Configuration

Créez une clé sur <https://hemicycle.ai/compte-api>, copiez `.env.example` vers
`.env`, puis renseignez au minimum :

```text
HEMICYCLE_API_KEY=...
APP_CONTACT=contact@votre-domaine.fr
```

La synthèse narrative est facultative :

```text
FEATHERLESS_API_KEY=...
FEATHERLESS_MODEL=zai-org/GLM-5.2
```

Ne placez jamais `.env`, une clé ou un secret dans GitHub.

### Embeddings multilingues facultatifs

Le fournisseur `tfidf` est rapide, local et sans téléchargement. Pour une
recherche plus sémantique :

```powershell
python -m pip install -r requirements-ai.txt
$env:SEMANTIC_PROVIDER="sentence-transformers"
```

Le modèle par défaut est
`sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2`. Son premier
chargement télécharge les poids ; prévoyez le cache dans l'infrastructure.

## Boucle d'apprentissage

Les boutons de qualification enregistrent `pertinent`, `non_pertinent`,
`a_contacter`, `contacte`, `gagne` ou `perdu`. Le modèle supervisé n'est
entraînable qu'après 100 observations réelles et la présence de résultats
positifs et négatifs. L'entraînement produit un modèle candidat et une métrique
ROC-AUC ; il n'est jamais activé automatiquement. Cette règle évite de fabriquer
une précision artificielle à partir des échantillons de démonstration.

## Tests et qualité

```powershell
python -m compileall -q app.py scoring.py storage.py learning.py services pages tests
python -m unittest discover -s tests -v
git diff --check
```

Les tests couvrent le scoring, le sémantique, l'agent sans réseau, la
persistance, les connecteurs et un parcours Streamlit hors ligne.

## Docker et production

```powershell
docker build -t cap-marches .
docker run --rm -p 8501:8501 --env-file .env cap-marches
```

Pour plusieurs instances, utilisez PostgreSQL :

```text
DATABASE_URL=postgresql+psycopg://user:password@host:5432/cap_marches
```

En production, ajoutez un reverse proxy HTTPS, un coffre de secrets, une
authentification utilisateur, des sauvegardes, une rétention des logs et un
monitoring. Les recherches sauvegardées préparent les alertes, mais aucun email
n'est envoyé automatiquement par ce dépôt.

## Sources et limites

- [Hémicycle · projets d'achats publics](https://hemicycle.ai/bibliotheque/projets_achats_publics)
- [Hémicycle · marchés publics](https://hemicycle.ai/bibliotheque/marches_publics)
- [Hémicycle · Sirene](https://hemicycle.ai/bibliotheque/sirene_etablissements)
- [DECP officielles](https://data.economie.gouv.fr/explore/assets/decp-2022-marches-valides/)
- Licence Ouverte 2.0 (Etalab).

Les requêtes sont limitées à 100 lignes, mises en cache une heure dans
l'interface et identifiées par `User-Agent`. La fin estimée d'un marché est un
calcul `notification + durée` : ce n'est ni une date officielle de nouvel appel
d'offres ni une prédiction certaine.
