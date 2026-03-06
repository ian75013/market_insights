# Market Insights

Projet démonstratif prêt à montrer en entretien pour une plateforme **Market Insights** orientée AI / Data / Backend.

## Fonctionnalités

- Ingestion de données de marché via sources libres et broker IB (adaptateur prévu)
- Pipeline ETL orchestrable avec Airflow
- Nettoyage, normalisation et enrichissement de séries temporelles
- Calcul d'indicateurs techniques
- Modèle maison de juste valeur (baseline explicable)
- RAG sur documents financiers / notes / actualités
- Génération de fiches d'analyse via LLM
- API FastAPI
- Tests unitaires et d'intégration légers
- Docker Compose pour exécution locale

## Architecture

```text
market_insights/
  api/                 # endpoints FastAPI
  core/                # configuration, logging
  db/                  # modèles SQLAlchemy, session
  etl/                 # extract / transform / load + DAG Airflow
  llm/                 # prompts et génération de rapport
  ml/                  # modèle de juste valeur
  rag/                 # vectorisation et retrieval simplifiés
  schemas/             # schémas Pydantic
  services/            # orchestration métier
  tests/               # tests pytest
  data/sample/         # données de démonstration
  scripts/             # scripts CLI
```

## Démarrage rapide

```bash
cp .env.example .env
python -m venv .venv
source .venv/bin/activate  # sous Windows: .venv\Scripts\activate
pip install -r requirements.txt
uvicorn market_insights.api.main:app --reload
```

API docs:

- `http://127.0.0.1:8000/docs`

## Docker

```bash
docker compose up --build
```

## Endpoints principaux

- `GET /health`
- `GET /tickers`
- `POST /etl/run?ticker=AAPL`
- `GET /insights/AAPL`
- `GET /fair-value/AAPL`

## Airflow

Le DAG d'exemple est dans `market_insights/etl/dags/market_insights_dag.py`.

## Juste valeur

Le modèle inclus est une baseline explicable:

- facteur momentum
- facteur value
- facteur volatilité
- facteur croissance

Il peut ensuite être remplacé par:

- XGBoost Regressor
- TFT / LSTM
- modèle multifactoriel cross-sectional

## Limites du repo de démonstration

- l'adaptateur IB ne déclenche pas d'appel réel par défaut
- la couche RAG est volontairement locale et simple pour rester démontrable
- la génération LLM peut fonctionner avec un fallback déterministe si aucune clé n'est fournie

## Idées pour la démo entretien

1. lancer l'API
2. exécuter `POST /etl/run?ticker=AAPL`
3. appeler `GET /insights/AAPL`
4. expliquer la chaîne: extraction -> features -> juste valeur -> RAG -> rédaction

