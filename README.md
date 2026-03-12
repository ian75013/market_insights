# Market Insights — repo

Projet **AI / Data / Backend** pour une plateforme de recherche actions.

Cette version ajoute plusieurs blocs majeurs :

- **connecteurs IBKR / TWS / IB Gateway** avec fallback local pour la démo
- **connecteurs vers des données libres de droits ou librement accessibles** (prix, macro, filings, news RSS)
- **RAG plus crédible** avec documents versionnés, chunking, retrieval hybride simple et citations
- **générateur d’analyses comparable** pour produire une fiche technique structurée
- **Hybrid Insight Engine** combinant technique, fair value, comparable insight et RAG
- **dashboard Angular** pour piloter l’ETL et visualiser les analyses

## Cas d'usage couverts

1. **Analyse pré-calculée ou à la demande d'une action**
   - ingestion des prix et métadonnées
   - calcul de features techniques
   - récupération de contexte documentaire
   - génération d'une fiche d'analyse sourcée

2. **Modèle maison de juste valeur**
   - baseline explicable et démontrable
   - score de sous/sur-évaluation
   - possibilité de remplacer ensuite par XGBoost / LightGBM / modèle multifactoriel

3. **Analyse hybride**
   - fusion entre signaux techniques, juste valeur et contexte documentaire
   - résumé exécutif
   - verdict haussier / neutre / baissier
   - catalyseurs, risques et sources

## Architecture

```text
market_insights/
  api/                    # FastAPI
  connectors/
    ibkr/                 # IB Gateway / TWS
    open_data/            # Stooq / FRED / SEC / RSS / sample
  db/                     # SQLAlchemy
  etl/                    # extract / transform / load
  llm/                    # génération narrative
  ml/                     # modèle de juste valeur
  rag/                    # docs, chunking, retrieval, citations
  schemas/                # Pydantic
  services/               # orchestration métier
  scripts/                # seed/demo
  tests/                  # tests pytest
  frontend-angular/       # dashboard Angular
```

## Sources de données prévues

### Broker

- **IBKR** via `ib_insync` si disponible et si TWS / IB Gateway tourne localement
- fallback automatique vers données d'exemple pour la démo entretien

### Données libres / librement accessibles

- **Stooq** : prix EOD (CSV)
- **FRED** : séries macro
- **SEC EDGAR** : filings / facts / company submissions
- **RSS** : flux d'actualités financières
- **sample local** : démonstration sans réseau

> Les connecteurs HTTP sont écrits de façon à pouvoir être branchés réellement, tout en gardant une démo locale stable.

## Démarrage local

```bash
cp .env.example .env
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python -m market_insights.scripts.seed_demo_data
uvicorn market_insights.api.main:app --reload
```

Swagger :

- `http://127.0.0.1:8000/docs`

## Docker

```bash
docker compose up --build
```

## Endpoints utiles

- `GET /health`
- `GET /sources`
- `POST /etl/run?ticker=AAPL&provider=sample`
- `POST /etl/run?ticker=AAPL&provider=ibkr`
- `GET /fair-value/AAPL`
- `GET /insights/AAPL`
- `GET /insights/AAPL/comparable`
- `GET /insights/AAPL/hybrid`
- `GET /rag/sources/AAPL`

## Variables d'environnement utiles

```env
OPENAI_API_KEY=
LLM_BACKEND=fallback
IB_HOST=127.0.0.1
IB_PORT=7497
IB_CLIENT_ID=1
USE_NETWORK=false
DEFAULT_PRICE_PROVIDER=sample
```

## Comment présenter ce repo en entretien

### 1. Data ingestion

- expliquer qu'on sépare `broker data` et `open data connectors`
- montrer que le fallback `sample` permet une démo stable
- expliquer que le passage en prod consiste surtout à activer `USE_NETWORK=true`

### 2. ETL

- **bronze** : extraction brute
- **silver** : nettoyage
- **gold** : features techniques + agrégats utilisables par l'API et le modèle

### 3. RAG

- documents versionnés, chunking, citations
- retrieval hybride léger : score lexical + similarité sur termes
- génération d'une fiche avec sources renvoyées au front

### 4. Modèle de juste valeur

- baseline explicable aujourd'hui
- extension future vers modèle multifactoriel / gradient boosting

### 5. Hybrid Insight Engine

- fusionne la technique, la juste valeur, l'analyse comparable et le RAG
- produit un résumé exécutif exploitable côté front
- permet de distinguer :
  - la **donnée calculée**
  - le **contexte documentaire**
  - la **narration générée**

## Demo mode

No external market data account is required for the interview demo. Use `provider=sample` or keep `USE_NETWORK=false` to run the full flow offline with bundled sample data.

## Générateur d'analyses comparable

Cette version ajoute un moteur déterministe qui produit une fiche structurée inspirée des analyses techniques publiées sur des sites spécialisés, sans recopier leur contenu :

- résumé d'analyse
- opinion conditionnelle
- objectifs de prix
- cotations
- technique
- niveaux support / résistance
- signaux détectés
- enrichissement RAG
- disclaimer

Principe de conception :

- les chiffres sont calculés par le moteur Python
- le LLM ne fait que rédiger
- le RAG enrichit le contexte mais ne décide pas des niveaux

## Hybrid Insight

Le endpoint hybride agrège plusieurs blocs dans une réponse unique :

- **technical insight**
- **comparable insight**
- **fair value**
- **RAG sources**
- **executive summary**
- **verdict**
- **catalysts**
- **risks**

Objectif :

- fournir une fiche plus proche d'une vraie plateforme de recherche actions
- garder une séparation claire entre calcul, enrichissement documentaire et rendu

## Angular Frontend

Le projet inclut un petit front Angular dans `frontend-angular/` permettant :

- de lancer l’ETL
- de consulter l’analyse simple
- de consulter l’analyse comparable
- de consulter l’analyse hybride
- d’afficher la fair value
- d’afficher les sources RAG

### Upgrade script

```bash
bash market-insights-hybrid-front-upgrade.sh .
```

### Run backend

```bash
pip install -r requirements.txt
uvicorn market_insights.api.main:app --reload
```

### Run frontend

```bash
cd market_insights/frontend-angular
npm install
npm start
```

Open `http://localhost:4200`.

The dashboard consumes:

- `/insights/{ticker}`
- `/insights/{ticker}/comparable`
- `/insights/{ticker}/hybrid`
- `/fair-value/{ticker}`
- `/rag/sources/{ticker}`

## Prochaines évolutions réalistes

- brancher réellement `ib_insync`
- stocker embeddings dans **pgvector**
- ajouter un reranker cross-encoder
- ajouter un DAG Airflow nightly pour recalculs et indexation
- ajouter un scoring sectoriel / peer group
- ajouter un vrai rendu HTML/PDF des fiches
- brancher un vrai chart frontend type Lightweight Charts ou TradingView

## Positionnement du projet

Ce repo peut être présenté comme un projet :

- **Backend AI Engineer**
- **Data / ETL Engineer**
- **LLM / RAG Engineer**
- **Quant / Market Intelligence Prototype**

Il montre la capacité à :

- connecter plusieurs sources de données
- construire une chaîne ETL stable
- exposer une API propre
- enrichir une analyse avec un RAG
- produire un front de démonstration cohérent