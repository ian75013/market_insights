# Market Insights v3 — Multi-Source Financial Research Platform

Projet **Backend AI / Data Engineering / Quant** pour une plateforme de recherche actions et crypto.

## Nouveautés v3

### Connecteurs open data réellement fonctionnels

| Provider | Type | Clé API | Données |
|---|---|---|---|
| **Yahoo Finance** (yfinance) | Prix + Fondamentaux | Non | OHLCV, P/E, margins, sector, market cap, description |
| **Alpha Vantage** | Prix + Fondamentaux + News | Oui (gratuite) | Daily adjusted, company overview, news sentiment |
| **Financial Modeling Prep** | Fondamentaux + Ratios | Oui (gratuite) | Profile, ratios TTM, earnings calendar |
| **FRED** | Macro | Oui (gratuite) | Fed funds, CPI, GDP, unemployment, VIX, M2, etc. |
| **SEC EDGAR** | Filings | Non | Company facts US-GAAP (revenue, EPS, assets, equity) |
| **CoinGecko** | Crypto | Non | OHLC, market cap, supply, descriptions |
| **Stooq** | Prix EOD | Non | CSV daily prices |
| **RSS** (Google News) | News | Non | Headlines + summaries |
| **IBKR** (TWS/Gateway) | Prix live | Non (compte) | Historical bars via ib_insync |

### Architecture améliorée

- **Cache TTL** thread-safe avec invalidation par préfixe (évite le rate-limiting)
- **Cascade multi-source** : chaque type de donnée a un ordre de résolution configurable
- **Provider auto** : `provider=auto` essaie Yahoo → Stooq → Alpha Vantage → CoinGecko → Sample
- **Batch ETL** : ingestion parallèle de plusieurs tickers
- **10 tickers sample** enrichis (AAPL, MSFT, NVDA, GOOGL, AMZN, META, TSLA, JPM, JNJ, BTC)
- **Données macro enrichies** (taux, inflation, emploi, sentiment, housing, monnaie)
- **33 tests** passant en CI

### Nouveaux endpoints API

| Endpoint | Description |
|---|---|
| `GET /providers` | Statut live de chaque provider (clé configurée, réseau actif) |
| `POST /etl/batch?tickers=AAPL,MSFT,NVDA` | ETL multi-tickers en un appel |
| `GET /fundamentals/{ticker}` | Fondamentaux multi-source |
| `GET /news/{ticker}` | News multi-source |
| `GET /macro` | Dashboard macro (FRED ou sample) |
| `GET /cache/stats` | Monitoring du cache |
| `POST /cache/clear?prefix=...` | Invalidation du cache |

## Architecture

```text
market_insights/
  api/                          # FastAPI v3
  connectors/
    ibkr/                       # IB Gateway / TWS
    open_data/
      alpha_vantage.py          # Prix, overview, news sentiment
      base.py                   # HTTP client avec retry + cache
      coingecko.py              # Crypto OHLC, info, global market
      fmp.py                    # Profile, ratios TTM, earnings
      fundamentals.py           # Multi-source cascade connector
      macro.py                  # FRED API + sample
      news.py                   # Multi-source (AV, RSS, sample)
      prices.py                 # Sample + Stooq
      yahoo.py                  # yfinance prices + fundamentals
  core/
    cache.py                    # TTL cache + decorator
    config.py                   # Pydantic settings (env vars)
    logging.py
  db/                           # SQLAlchemy models + session
  etl/                          # Extract → Clean → Features → Load
  llm/                          # Report generation
  ml/                           # Fair value model (baseline multifactor)
  rag/                          # Chunking, retrieval, citations
  schemas/                      # Pydantic response models
  services/
    etl_service.py              # ETL orchestration + batch
    market_service.py           # Insight generation
    hybrid_insight_service.py   # Fusion technique + fair value + RAG
  scripts/                      # Seed + demo
  tests/                        # 33 tests pytest
  data/sample/                  # 10 tickers × 55 jours
  frontend-angular/             # Dashboard Angular
```

## Cascade de résolution des données

### Prix
```
provider=auto → Yahoo Finance → Stooq → Alpha Vantage → CoinGecko → Sample
```

### Fondamentaux
```
MultiFundamentalsConnector → Yahoo Finance → Alpha Vantage → FMP → SEC EDGAR → Sample
```

### News
```
MultiNewsConnector → Alpha Vantage (sentiment) → RSS (Google News) → Sample
```

### Macro
```
FRED (si clé + réseau) → Sample enrichi
```

## Démarrage rapide

### Mode offline (démo entretien)

```bash
cp .env.example .env
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python -m market_insights.scripts.seed_demo_data
uvicorn market_insights.api.main:app --reload
```

Swagger : http://127.0.0.1:8000/docs

### Mode réseau (données réelles)

```bash
# Dans .env :
USE_NETWORK=true
DEFAULT_PRICE_PROVIDER=auto
ALPHA_VANTAGE_API_KEY=your_key_here
FRED_API_KEY=your_key_here
FMP_API_KEY=your_key_here

uvicorn market_insights.api.main:app --reload
```

### Docker

```bash
docker compose up --build
```

## Tests

```bash
pytest -v
# 33 passed
```

## Variables d'environnement

| Variable | Défaut | Description |
|---|---|---|
| `USE_NETWORK` | `false` | Active les appels HTTP vers les providers |
| `DEFAULT_PRICE_PROVIDER` | `sample` | Provider par défaut (`sample`, `yahoo`, `auto`...) |
| `ALPHA_VANTAGE_API_KEY` | `` | Clé gratuite Alpha Vantage |
| `FRED_API_KEY` | `` | Clé gratuite FRED |
| `FMP_API_KEY` | `` | Clé gratuite Financial Modeling Prep |
| `SEC_USER_AGENT` | `MarketInsights/1.0...` | Header requis par SEC EDGAR |
| `CACHE_TTL_PRICES` | `900` | TTL cache prix (secondes) |
| `CACHE_TTL_FUNDAMENTALS` | `3600` | TTL cache fondamentaux |
| `CACHE_TTL_MACRO` | `1800` | TTL cache macro |
| `CACHE_TTL_NEWS` | `600` | TTL cache news |

## Endpoints complets

### Système
- `GET /health` — statut + version + config réseau
- `GET /sources` — liste des providers par catégorie
- `GET /providers` — statut live de chaque provider
- `GET /cache/stats` — métriques du cache
- `POST /cache/clear?prefix=...` — invalidation

### ETL
- `POST /etl/run?ticker=AAPL&provider=sample` — pipeline single
- `POST /etl/batch?tickers=AAPL,MSFT,NVDA&provider=auto` — pipeline batch

### Analyse
- `GET /fair-value/{ticker}` — juste valeur + facteurs
- `GET /insights/{ticker}` — analyse complète
- `GET /insights/{ticker}/comparable` — fiche technique structurée
- `GET /insights/{ticker}/hybrid` — fusion technique + fair value + RAG

### Données
- `GET /fundamentals/{ticker}` — fondamentaux multi-source
- `GET /news/{ticker}?limit=10` — news multi-source
- `GET /macro` — dashboard macro
- `GET /rag/sources/{ticker}` — sources documentaires RAG

## Comment présenter ce repo en entretien

### 1. Data Engineering
- Montrer les connecteurs multi-source avec cascade et fallback
- Expliquer le cache TTL pour respecter les rate limits
- Pipeline ETL bronze → silver → gold avec batch support

### 2. Backend Architecture
- FastAPI avec dependency injection (SQLAlchemy sessions)
- Configuration par variables d'environnement (12-factor)
- Séparation nette : connectors / services / API / schemas

### 3. Open Data Integration
- 9 providers réels intégrés (pas juste des stubs)
- Résolution automatique par priorité
- Chaque provider est testable individuellement

### 4. AI / RAG
- Documents versionnés, chunking, retrieval lexical hybride
- Citations traçables dans les analyses
- LLM en mode fallback déterministe (pas de dépendance OpenAI)

### 5. Modèle quantitatif
- Fair value baseline multifactorielle (momentum, volatilité, fondamentaux)
- Score de confiance calibré
- Extensible vers XGBoost / LightGBM

### 6. Qualité
- 33 tests automatisés
- CI GitHub Actions
- Type hints complets
- Logging structuré

## Évolutions réalistes

- [ ] pgvector pour embeddings RAG
- [ ] Reranker cross-encoder (sentence-transformers)
- [ ] DAG Airflow pour recalculs nightly
- [ ] Scoring sectoriel / peer group
- [ ] Export PDF des fiches d'analyse
- [ ] Chart frontend Lightweight Charts / TradingView
- [ ] WebSocket pour prix live
- [ ] Rate limiter par provider avec circuit breaker
