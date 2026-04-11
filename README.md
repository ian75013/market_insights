# Market Insights v4

Plateforme de recherche actions avec **chandeliers annotés**, **RAG vectoriel** et **7 providers LLM**.

## Démarrage

### Docker (recommandé)

```bash
docker compose up --build
```
→ API : http://localhost:8000/docs · Frontend : http://localhost:3080

**LLM par défaut** — le compose utilise ton gateway LiteLLM partagé sur le réseau Docker `litellm-gateway-vps_llmnet`, avec `local-private` comme modèle par défaut.

Prérequis : la stack LiteLLM doit déjà tourner avec le profil `local-llm`.

```bash
cd ../litellm-gateway-vps/litellm-gateway-vps
bash scripts/dev_up.sh
cd ../../market_insights
docker compose up --build
```

Raccourci recommandé depuis `market_insights`:

```bash
bash scripts/dev_up_litellm.sh
```

Le script vérifie que le gateway LiteLLM est prêt avant de lancer le compose du projet.

Mode détaché avec healthchecks post-start:

```bash
DETACH=true bash scripts/dev_up_litellm.sh
```

Mode détaché avec test e2e `/llm/chat` en plus:

```bash
DETACH=true RUN_E2E_CHAT_TEST=true bash scripts/dev_up_litellm.sh
```

**Ollama en infra uniquement** — le profil `standalone-ollama` reste disponible pour les besoins d'infrastructure ou de debug, mais l'application n'expose plus `ollama` comme provider sélectionnable. Le chemin normal passe par LiteLLM.

```bash
docker compose --profile standalone-ollama up --build
```

Parametres de demarrage robustes (via variables d'environnement):

- `MI_RUN_SEED` : execute le seed au boot (`true` en dev, `false` recommande en prod)
- `MI_WAIT_DNS` : active un precheck DNS au demarrage (`true` recommande)
- `MI_API_RELOAD` : mode reload Uvicorn (dev uniquement)
- `MI_API_WORKERS` : nombre de workers Uvicorn (prod)
- `LLM_BACKEND` : provider LLM (`litellm` par défaut)
- `LLM_MODEL` : modèle (`local-private` par défaut via LiteLLM)

En production, lancer de preference sans seed automatique:

```bash
MI_RUN_SEED=false docker compose -f docker-compose.prod.yml up -d --build
```

### Airflow ETL (nouvelle orchestration)

Le projet inclut maintenant un orchestrateur Airflow prêt pour la prod via `docker-compose.airflow.yml`.

Lancement local avec stack prod + Airflow:

```bash
docker compose -f docker-compose.prod.yml -f docker-compose.airflow.yml up -d --build
```

Services ajoutés:

- `mi-airflow-db` (Postgres metadata Airflow)
- `mi-airflow-scheduler`
- `mi-airflow-webserver`

Variables minimales à définir dans `.env`:

- `AIRFLOW_FERNET_KEY`
- `AIRFLOW_SECRET_KEY`
- `AIRFLOW_ADMIN_PASSWORD`

Le DAG principal `market_insights_daily` exécute les ETL par ticker en parallèle puis déclenche le refresh RAG.

### Airflow sur VPN (recommandé)

Pour exposer l'UI Airflow uniquement sur ton VPN, fixe l'IP de bind:

```dotenv
AIRFLOW_WEBSERVER_BIND=10.8.0.2
```

Le port 8080 n'est alors plus exposé publiquement sur l'IP serveur. Depuis un client connecté au VPN:

```bash
http://10.8.0.2:8080
```

Si tu ne veux aucun bind réseau direct, garde `AIRFLOW_WEBSERVER_BIND=127.0.0.1` et passe par un tunnel SSH:

```bash
ssh -L 8080:127.0.0.1:8080 user@ton-vps
```

Changer le modèle LiteLLM par défaut:

```bash
LLM_MODEL=cheap-chat docker compose up --build
```

Le profil `standalone-ollama` reste réservé aux usages d'infrastructure et de debug.

Note importante sur Docker Compose : une variable exportée dans le shell a priorité sur `.env`. Si tu as déjà exporté `LITELLM_BASE_URL` ou `LITELLM_API_KEY` dans ton terminal, elle peut surcharger la configuration attendue du projet.

### Sans Docker

```bash
pip install -r requirements.txt
python -m market_insights.scripts.seed_demo_data
uvicorn market_insights.api.main:app --reload
```
→ http://127.0.0.1:8000/docs

```bash
cd market_insights/frontend-react
npm install
npm run dev
```
→ http://localhost:3080 (6 onglets : Overview, Chandeliers, Technique, Fondamentaux, News, RAG Chat)

## Chandeliers annotés

`GET /chart/candlestick/AAPL` retourne les barres OHLCV avec 14 signaux détectés par bougie :
gap up/down, pullback SMA, breakout/breakdown, avalement, marteau, étoile filante, doji, étoile du matin/soir, volume spike, RSI extrêmes, golden/death cross.

## RAG Chat + LLM

`POST /llm/chat` utilise LiteLLM par défaut. Démarrage rapide avec LiteLLM :

```bash
cd ../litellm-gateway-vps/litellm-gateway-vps
bash scripts/dev_up.sh
# .env : LLM_BACKEND=litellm
```

7 providers exposés : LiteLLM, OpenAI, Anthropic, Mistral, Groq, LMStudio, Fallback.
`GET /llm/providers` liste uniquement les providers sélectionnables dans l'application.

## Tests

```bash
pytest -v   # 40 passed
```

Voir **ARCHITECTURE.md** pour les schémas et le détail technique.
Pour les commandes Docker prêtes à l'emploi, voir **README_DOCKER.md**.
Pour l'orchestration ETL Airflow (incluant VPN), voir **doc/AIRFLOW_ETL.md**.
), `generate(prompt, system=...)` (envoyer un prompt et recevoir une réponse), `models()` (lister les modèles disponibles). Chaque provider hérite de cette interface.

L'endpoint `GET /llm/providers` interroge chaque provider en temps réel et retourne son statut de disponibilité ainsi que la liste de ses modèles. Le frontend utilise cette information pour afficher un indicateur vert (en ligne) ou gris (hors ligne) à côté de chaque provider dans le sélecteur.

### Les 7 providers exposés

**LiteLLM** — Nécessite une URL OpenAI-compatible (`LITELLM_BASE_URL`) et une clé (`LITELLM_API_KEY`). Dans cette configuration, Market Insights appelle ton gateway partagé sur `http://litellm:4000` et récupère dynamiquement les modèles exposés, dont `local-private`.

**OpenAI** — Nécessite une clé API (`OPENAI_API_KEY`). Modèles disponibles : gpt-4o, gpt-4o-mini, gpt-4-turbo, gpt-3.5-turbo. Le provider utilise la librairie officielle `openai`. La clé est vérifiée au démarrage : si elle est absente, le provider est marqué comme indisponible.

**Anthropic** — Nécessite une clé API (`ANTHROPIC_API_KEY`). Modèles disponibles : claude-sonnet-4-20250514, claude-haiku-4-20250414, claude-3-5-sonnet-20241022. Utilise la librairie officielle `anthropic`. Le prompt système est passé via le paramètre `system` de l'API Messages.

**Mistral** — Nécessite une clé API (`MISTRAL_API_KEY`). Modèles disponibles : mistral-large-latest, mistral-medium-latest, mistral-small-latest, open-mistral-nemo. Les appels passent par l'API REST directement via httpx (pas de SDK dédié requis).

**Groq** — Nécessite une clé API (`GROQ_API_KEY`). Modèles disponibles : llama-3.3-70b-versatile, llama-3.1-8b-instant, mixtral-8x7b-32768, gemma2-9b-it. Groq fournit un free tier généreux. L'API est compatible OpenAI, les appels passent par httpx.

**LMStudio** — Aucune clé nécessaire. LMStudio tourne en local sur le port 1234 et expose une API compatible OpenAI. Le provider vérifie la disponibilité en appelant `GET /v1/models`. Tout modèle GGUF chargé dans LMStudio est automatiquement détecté.

**Fallback** — Toujours disponible. Ne fait aucun appel LLM. Retourne le contexte RAG brut tel quel. C'est le mode par défaut quand aucun LLM n'est configuré. Utile pour la démo offline ou le debug.

### Changement de provider à la volée

Dans l'onglet RAG Chat du dashboard, le panneau de droite liste les providers exposés avec leur statut. `litellm` est sélectionné par défaut. `ollama` n'est pas proposé car le modèle local est censé être consommé via le gateway LiteLLM. Le sélecteur de modèle en dessous s'adapte automatiquement à la liste des modèles du provider choisi. Aucun redémarrage n'est nécessaire.

### Exemple d'appel API

```bash
curl -X POST http://127.0.0.1:8000/llm/chat \
  -H "Content-Type: application/json" \
  -d '{
    "ticker": "AAPL",
    "question": "Quels sont les principaux risques pour Apple ?",
    "llm_backend": "litellm",
    "llm_model": "local-private",
    "language": "fr",
    "top_k": 5
  }'
```

La réponse contient le champ `answer` (texte généré), `sources` (documents RAG utilisés avec scores) et `llm` (provider, modèle et tokens consommés).

---

## Pipeline ETL et connecteurs de données

### Principe

Le pipeline ETL s'exécute via `POST /etl/run?ticker=AAPL&provider=sample`. Il enchaîne quatre étapes : extraction des prix bruts depuis le provider sélectionné, nettoyage (suppression des doublons, remplissage des valeurs manquantes, validation des plages), calcul des features techniques (SMA 20/50/200, RSI 14, momentum 20j, volatilité 20j, trend signal, drawdown), et chargement dans SQLite (prix et documents). Les documents fondamentaux et news sont également ingérés lors de cette étape pour alimenter le RAG.

Le mode batch permet de traiter plusieurs tickers en un appel : `POST /etl/batch?tickers=AAPL,MSFT,NVDA&provider=auto`.

### Connecteurs de prix

Le routeur de prix (`PriceProviderRouter`) supporte 7 providers. Le mode `auto` détecte automatiquement les crypto-monnaies et adapte la cascade : pour les cryptos → CoinGecko en priorité, puis Sample ; pour les actions → Yahoo Finance, Stooq, Alpha Vantage, puis Sample. **Tous les endpoints normalisent les tickers crypto** (`BTC-USD` → `BTC`, `ETH-EUR` → `ETH`) via `canonical_ticker()` pour garantir la cohérence en base de données.

**sample** — Données embarquées dans `data/sample/prices.csv`. 10 tickers, 55 jours chacun. Aucune connexion réseau requise. C'est le provider par défaut.

**yahoo** — Yahoo Finance via la librairie yfinance. Pas de clé API. Prix journaliers ajustés, historique jusqu'à 2 ans. Requiert `USE_NETWORK=true`.

**stooq** — Stooq.com, prix EOD en CSV. Pas de clé API. Fonctionne pour les tickers US et européens. Requiert `USE_NETWORK=true`.

**alpha_vantage** — Alpha Vantage, prix journaliers ajustés. Nécessite `ALPHA_VANTAGE_API_KEY` (gratuite, 25 requêtes/jour).

**coingecko** — CoinGecko pour les crypto-monnaies. Pas de clé API. Données OHLC via `/coins/{id}/ohlc` et **volume quotidien** via `/coins/{id}/market_chart` (les deux endpoints sont fusionnés automatiquement). Le mapping ticker→coin_id est intégré pour les 15 cryptos les plus courantes (BTC, ETH, SOL, ADA, DOGE, DOT, AVAX, MATIC, LINK, UNI, XRP, BNB, ATOM, LTC, NEAR). **Le routeur redirige automatiquement** les tickers crypto vers CoinGecko même si l'utilisateur sélectionne Yahoo ou Stooq, car ces providers retournent des données incorrectes pour les tickers crypto nus (ex. `yf.Ticker("BTC")` retourne un ETF/trust à ~$31, pas Bitcoin à ~$84,000).

**ibkr** — Interactive Brokers via ib_insync. Nécessite TWS ou IB Gateway en local. Si la connexion échoue, le provider bascule sur les données sample.

### Crypto — routage intelligent

Le système détecte automatiquement les crypto-monnaies via deux fonctions centralisées dans `coingecko.py` :

- `is_crypto_ticker(ticker)` — reconnaît les tickers directs (`BTC`, `ETH`, `SOL`…) et les paires Yahoo-style (`BTC-USD`, `ETH-EUR`…)
- `normalize_crypto_ticker(ticker)` — normalise vers le ticker canonique : `BTC-USD` → `BTC`, `ETH-EUR` → `ETH`

**Pourquoi ?** Sur Yahoo Finance, `yf.Ticker("BTC")` retourne les données du Grayscale Bitcoin Mini Trust (~$31), pas du Bitcoin réel (~$84,000). Stooq et Alpha Vantage ont le même problème avec les tickers crypto nus. CoinGecko est la seule source gratuite fiable pour les prix crypto OHLCV.

**Mécanisme de redirection :**

1. **Crypto guard** — Si un ticker crypto est détecté et que le provider demandé est `yahoo`, `stooq` ou `alpha_vantage`, le routeur redirige silencieusement vers CoinGecko (log info émis).
2. **Auto-resolve** — En mode `auto`, les cryptos essaient CoinGecko en premier (puis Sample en fallback), tandis que les actions suivent la cascade Yahoo → Stooq → Alpha → Sample.
3. **Normalisation globale** — `canonical_ticker()` est appliqué sur tous les endpoints API (`/chart/candlestick/{ticker}`, `/fair-value/{ticker}`, `/insights/{ticker}`, etc.) pour que la requête DB utilise toujours le même ticker que l'ETL a stocké.
4. **Volume** — L'endpoint OHLC de CoinGecko ne fournit pas le volume. Le connecteur effectue un second appel à `/coins/{id}/market_chart?interval=daily` pour récupérer les volumes quotidiens et les fusionne par date (best effort, pas de blocage si ça échoue).
5. **Frontend** — Le `CandlestickTab` détecte les tickers crypto côté client et route automatiquement vers CoinGecko. Un badge "Source : coingecko" s'affiche après le chargement avec le nombre de barres et le temps d'exécution. L'axe Y s'adapte dynamiquement aux grands prix (format `84k` au lieu de `84302.50`).

### Connecteurs de fondamentaux

Le `MultiFundamentalsConnector` essaie les sources dans l'ordre : Yahoo Finance (yfinance), Alpha Vantage (overview), Financial Modeling Prep (profil + ratios), SEC EDGAR (company facts US-GAAP), puis Sample. La première source qui retourne des données valides est utilisée.

### Connecteurs de news

Le `MultiNewsConnector` essaie Alpha Vantage (news avec score de sentiment), puis les flux RSS (Google News), puis les données sample.

### Connecteur macro

Le `FREDConnector` récupère 16 séries macro depuis l'API FRED (fed funds, 10Y, 2Y, 3M, CPI, GDP, chômage, VIX, PCE core, housing starts, retail sales, industrial production, consumer sentiment, initial claims, M2, S&P 500). Si la clé `FRED_API_KEY` n'est pas configurée ou si le réseau est désactivé, les données macro sample sont utilisées.

### Cache

Toutes les requêtes HTTP vers les providers externes passent par un cache TTL thread-safe. Chaque type de donnée a son propre TTL configurable : prix (15 min), fondamentaux (1 h), macro (30 min), news (10 min). Le cache peut être consulté via `GET /cache/stats` et vidé via `POST /cache/clear`.

---

## Modèle de juste valeur

Le `BaselineFairValueModel` dans `ml/fair_value.py` est un modèle multifactoriel explicable qui estime la juste valeur d'un titre en combinant quatre composantes :

**Growth boost** — Amplifie le prix en fonction de la croissance du chiffre d'affaires (pondération 0.20) et de la croissance EPS (pondération 0.12).

**Momentum boost** — Intègre le momentum sur 20 séances (pondération 0.25) et le signal de tendance (SMA 20 vs SMA 50, pondération 0.03).

**Risk penalty** — Pénalise en fonction de la volatilité sur 20 séances (jusqu'à -10.5%) et du ratio dette/equity au-delà de 1.0 (jusqu'à -6%).

**RSI penalty** — Applique un léger ajustement si le RSI 14 est en zone extrême : -2% au-dessus de 70, +2% en dessous de 35.

Le score de confiance est calibré entre 0.35 et 0.92 en fonction du trend, de la croissance et de la volatilité. Le verdict hybride (bullish, bearish, neutral) combine l'upside du modèle avec le score de tendance technique.

---

## API — liste complète des endpoints

### Système

| Méthode | Endpoint | Description |
|---------|----------|-------------|
| GET | `/health` | Statut, version, config réseau |
| GET | `/sources` | Liste des providers par catégorie |
| GET | `/providers` | Statut live de chaque provider + clés configurées |
| GET | `/cache/stats` | Nombre de clés en cache, clés expirées |
| POST | `/cache/clear?prefix=` | Invalider le cache (tout ou par préfixe) |

### ETL

| Méthode | Endpoint | Description |
|---------|----------|-------------|
| POST | `/etl/run?ticker=AAPL&provider=sample` | Pipeline ETL pour un ticker |
| POST | `/etl/batch?tickers=AAPL,MSFT&provider=auto` | Pipeline ETL pour plusieurs tickers |

### Analyse

| Méthode | Endpoint | Description |
|---------|----------|-------------|
| GET | `/fair-value/{ticker}` | Juste valeur, upside, confiance, facteurs |
| GET | `/insights/{ticker}` | Analyse complète (score, technicals, fondamentaux, RAG, comparable) |
| GET | `/insights/{ticker}/comparable` | Fiche technique structurée (opinion, niveaux, signaux, narrative) |
| GET | `/insights/{ticker}/hybrid` | Fusion technique + fair value + RAG + verdict |

### Chandeliers

| Méthode | Endpoint | Description |
|---------|----------|-------------|
| GET | `/chart/candlestick/{ticker}` | Barres OHLCV avec signaux annotés par bougie |

### Données

| Méthode | Endpoint | Description |
|---------|----------|-------------|
| GET | `/fundamentals/{ticker}` | Fondamentaux multi-source |
| GET | `/news/{ticker}?limit=10` | News multi-source |
| GET | `/macro` | Dashboard macro (FRED ou sample) |
| GET | `/rag/sources/{ticker}` | Documents RAG indexés pour un ticker |
| POST | `/rag/index/{ticker}` | Forcer la réindexation vectorielle |
| GET | `/rag/stats` | Stats du VectorStore (tickers indexés, nombre de chunks) |

### LLM

| Méthode | Endpoint | Description |
|---------|----------|-------------|
| GET | `/llm/providers` | Liste des 7 providers exposés avec disponibilité et modèles |
| POST | `/llm/chat` | Chat RAG : question + ticker + choix du provider/modèle |

Le body de `/llm/chat` attend un JSON :
```json
{
  "question": "Quels catalyseurs pour la croissance ?",
  "ticker": "AAPL",
  "llm_backend": "litellm",
  "llm_model": "local-private",
  "language": "fr",
  "top_k": 5
}
```

---

## Variables d'environnement

Toutes les variables sont optionnelles. Le fichier `.env.example` fournit les valeurs par défaut.

### Application

| Variable | Défaut | Description |
|----------|--------|-------------|
| `APP_ENV` | `dev` | Environnement (`dev`, `staging`, `prod`). En mode `dev`, les logs sont plus verbeux. |
| `APP_NAME` | `Market Insights` | Nom affiché dans les logs et le header API. |
| `DATABASE_URL` | `sqlite:///./market_insights.db` | URL de connexion SQLAlchemy. Supporte SQLite (fichier local) et PostgreSQL (`postgresql://user:pass@host/db`). |

### Réseau et routage

| Variable | Défaut | Description |
|----------|--------|-------------|
| `USE_NETWORK` | `false` | Active ou désactive les appels HTTP vers les APIs externes. Quand `false`, seules les données sample sont utilisées. Mettre à `true` pour utiliser Yahoo Finance, Alpha Vantage, FRED, etc. |
| `DEFAULT_PRICE_PROVIDER` | `sample` | Provider de prix par défaut quand aucun n'est spécifié dans l'appel ETL. Valeurs possibles : `sample`, `yahoo`, `stooq`, `alpha_vantage`, `coingecko`, `ibkr`, `auto`. Le mode `auto` essaie les providers dans l'ordre de priorité jusqu'à ce qu'un retourne des données. |

### Interactive Brokers

| Variable | Défaut | Description |
|----------|--------|-------------|
| `IB_HOST` | `127.0.0.1` | Adresse du serveur TWS ou IB Gateway. |
| `IB_PORT` | `7497` | Port de connexion. 7497 pour TWS paper, 7496 pour TWS live, 4001/4002 pour IB Gateway. |
| `IB_CLIENT_ID` | `1` | Identifiant client pour la connexion TWS. Doit être unique par connexion simultanée. |

### Clés API data

| Variable | Défaut | Description |
|----------|--------|-------------|
| `ALPHA_VANTAGE_API_KEY` | `` | Clé API Alpha Vantage. Gratuite sur https://www.alphavantage.co/support/#api-key. Limite : 25 requêtes/jour. Donne accès aux prix ajustés, à l'overview société et au news sentiment. |
| `FRED_API_KEY` | `` | Clé API FRED (Federal Reserve Economic Data). Gratuite sur https://fred.stlouisfed.org/docs/api/api_key.html. Donne accès à 16 séries macro (fed funds, CPI, GDP, unemployment, VIX, etc.). |
| `FMP_API_KEY` | `` | Clé API Financial Modeling Prep. Gratuite sur https://site.financialmodelingprep.com/developer/docs. Limite : 250 requêtes/jour. Donne accès au profil société, ratios TTM et calendrier earnings. |
| `SEC_USER_AGENT` | `MarketInsights/1.0 contact@example.com` | Header User-Agent requis par SEC EDGAR. L'API SEC exige une identification avec un email de contact. Pas de clé API mais le header est obligatoire. |

### LLM — configuration générale

| Variable | Défaut | Description |
|----------|--------|-------------|
| `LLM_BACKEND` | `litellm` | Provider LLM par défaut utilisé pour la génération de rapports et le RAG chat. Valeurs exposées par l'application : `litellm`, `openai`, `anthropic`, `mistral`, `groq`, `lmstudio`, `fallback`. `ollama` n'est pas sélectionnable dans l'application et doit passer par LiteLLM si tu veux réutiliser le même modèle derrière un gateway. |
| `LLM_MODEL` | `` | Nom du modèle à utiliser. Si vide, chaque provider utilise son modèle par défaut (`local-private` pour LiteLLM, `gpt-4o-mini` pour OpenAI, `claude-sonnet-4-20250514` pour Anthropic, etc.). Permet de forcer un modèle spécifique, par exemple `local-private` ou `mistral-large-latest`. |
| `LLM_TEMPERATURE` | `0.3` | Température de génération (0.0 = déterministe, 1.0 = créatif). La valeur 0.3 est un bon compromis pour des analyses financières factuelles. |
| `LLM_MAX_TOKENS` | `1500` | Nombre maximum de tokens dans la réponse générée. Augmenter pour des analyses plus longues, réduire pour économiser les tokens sur les APIs payantes. |

### LLM — clés cloud

| Variable | Défaut | Description |
|----------|--------|-------------|
| `OPENAI_API_KEY` | `` | Clé API OpenAI. Obtenir sur https://platform.openai.com/api-keys. Facturation à l'usage. Si absente, le provider OpenAI est marqué comme indisponible. |
| `ANTHROPIC_API_KEY` | `` | Clé API Anthropic. Obtenir sur https://console.anthropic.com. Facturation à l'usage. |
| `MISTRAL_API_KEY` | `` | Clé API Mistral. Obtenir sur https://console.mistral.ai. Free tier disponible pour les petits modèles. |
| `GROQ_API_KEY` | `` | Clé API Groq. Obtenir sur https://console.groq.com. Free tier généreux (modèles open source accélérés sur hardware Groq). |

### LLM — providers locaux

| Variable | Défaut | Description |
|----------|--------|-------------|
| `OLLAMA_BASE_URL` | `http://localhost:11434` | URL du serveur Ollama. Installer Ollama depuis https://ollama.ai puis lancer `ollama serve`. Le provider teste automatiquement la connectivité au démarrage. |
| `OLLAMA_MODEL` | `llama3` | Modèle Ollama par défaut. Doit être installé via `ollama pull <model>`. Modèles recommandés : `llama3` (8B, rapide), `llama3:70b` (meilleure qualité), `mistral` (7B, bon en français), `codellama` (pour le code). La liste des modèles installés est récupérée dynamiquement. |
| `LMSTUDIO_BASE_URL` | `http://localhost:1234` | URL du serveur LMStudio. LMStudio expose une API compatible OpenAI sur ce port quand un modèle est chargé. |
| `LMSTUDIO_MODEL` | `default` | Modèle LMStudio. Correspond au modèle GGUF actuellement chargé dans l'interface LMStudio. La valeur `default` utilise le premier modèle disponible. |

### RAG

| Variable | Défaut | Description |
|----------|--------|-------------|
| `RAG_EMBEDDING_MODEL` | `all-MiniLM-L6-v2` | Nom du modèle sentence-transformers pour les embeddings. `all-MiniLM-L6-v2` est compact (80 Mo) et rapide. Pour une meilleure qualité : `all-mpnet-base-v2` (420 Mo). Le modèle est téléchargé automatiquement au premier appel. |
| `RAG_USE_VECTORS` | `true` | Active les embeddings vectoriels sentence-transformers. Si `false`, le système utilise un TF-IDF scikit-learn comme fallback (pas de téléchargement de modèle, mais qualité de recherche inférieure car pas de compréhension sémantique). Mettre à `false` pour une démo légère sans dépendance lourde. |
| `RAG_TOP_K` | `5` | Nombre de chunks retournés par la recherche RAG. Augmenter pour plus de contexte dans le prompt LLM (au prix d'un prompt plus long et donc plus de tokens consommés). |
| `RAG_CHUNK_SIZE` | `400` | Taille en caractères de chaque chunk de document. Des chunks plus petits donnent une recherche plus précise mais moins de contexte par chunk. Des chunks plus grands donnent plus de contexte mais risquent de diluer la pertinence. |
| `RAG_CHUNK_OVERLAP` | `60` | Chevauchement en caractères entre deux chunks consécutifs. Évite de couper une phrase importante à la frontière de deux chunks. |

### Cache

| Variable | Défaut | Description |
|----------|--------|-------------|
| `CACHE_TTL_PRICES` | `900` | Durée de vie du cache pour les prix, en secondes (15 minutes). Les appels aux APIs de prix (Yahoo, Stooq, Alpha Vantage) sont mis en cache pour éviter le rate limiting. |
| `CACHE_TTL_FUNDAMENTALS` | `3600` | Durée de vie du cache pour les fondamentaux (1 heure). Les données fondamentales changent rarement en intraday. |
| `CACHE_TTL_MACRO` | `1800` | Durée de vie du cache pour les données macro (30 minutes). Les séries FRED sont publiées quotidiennement ou mensuellement. |
| `CACHE_TTL_NEWS` | `600` | Durée de vie du cache pour les news (10 minutes). Les news sont plus fréquentes, le cache est donc plus court. |

---

## Tests

```bash
pytest -v
```

Le projet comporte 40 tests répartis dans 15 fichiers :

- `test_api.py` — Endpoints HTTP (health, ETL, insight, hybrid, comparable, fundamentals, macro, cache)
- `test_candlestick.py` — Moteur d'annotation (retour de barres, détection de signaux)
- `test_llm.py` — Providers LLM (fallback, unknown backend, list_providers)
- `test_rag_vector.py` — Indexation et retrieval vectoriel
- `test_rag.py` — Retrieval lexical
- `test_cache.py` — Cache TTL (set/get, expiry, invalidation, stats, décorateur)
- `test_cleaning.py` — Nettoyage des données (doublons, valeurs manquantes)
- `test_features.py` — Calcul des features techniques
- `test_signal_engine.py` — Détection de signaux et niveaux pivot
- `test_fair_value.py` — Modèle de juste valeur
- `test_connectors.py` — Connecteurs de prix (sample, IBKR fallback)
- `test_providers.py` — Routeur de providers
- `test_fundamentals.py` — Fondamentaux sample (10 tickers)
- `test_macro.py` — Données macro sample
- `test_comparable_insight.py` — Endpoint comparable

---

## Docker

Deux fichiers Compose selon l'environnement :

### Développement

```bash
docker compose up --build
```

`docker-compose.yml` lance une stack légère sans PostgreSQL ni nginx :

- **API** — SQLite, `uvicorn --reload` (hot-reload), code monté en volume, seed automatique des données de démo. Port 8000.
- **Frontend** — Vite dev server avec HMR, `node_modules` isolés dans un volume Docker. Port 3080.

→ API : http://localhost:8000/docs
→ Frontend : http://localhost:3080

Le proxy Vite redirige `/api/*` vers le conteneur API. La cible est configurable via `VITE_PROXY_TARGET` (défaut : `http://api:8000` en Docker, `http://127.0.0.1:8000` en local hors Docker).

### Production

```bash
docker compose -f docker-compose.prod.yml up -d --build
```

`docker-compose.prod.yml` lance la stack complète :

- **PostgreSQL 16** — Données persistées dans un volume `pg-data`. Healthcheck `pg_isready`.
- **API** — 2 workers uvicorn, `DATABASE_URL` pointant vers PostgreSQL, seed automatique.
- **Frontend** — Build React statique servi par un nginx interne (multi-stage Dockerfile).
- **Nginx** — Reverse proxy, terminaison SSL (Let's Encrypt), redirection HTTP→HTTPS.
- **Certbot** — Renouvellement automatique des certificats toutes les 12h.

Requiert un fichier `.env` avec au minimum `POSTGRES_PASSWORD`. Voir `doc/DEPLOIEMENT_OVH.md` pour le premier déploiement et l'obtention du certificat SSL.

---

## Présentation en entretien

Ce projet peut être présenté selon plusieurs angles selon le poste visé.

**Backend / API Engineer** — Architecture FastAPI propre avec dependency injection, séparation en couches (connectors, services, API, schemas), configuration 12-factor par variables d'environnement, cache thread-safe, pipeline ETL structuré, 40 tests automatisés.

**Data / ETL Engineer** — Pipeline bronze (extraction brute) → silver (nettoyage) → gold (features). 9 connecteurs open data avec cascade et fallback automatique. Batch processing. Routage de providers configurable avec détection intelligente des cryptos et redirection automatique vers CoinGecko. Normalisation des tickers pour cohérence DB.

**AI / LLM / RAG Engineer** — RAG vectoriel avec embeddings sentence-transformers, retrieval hybride (cosine + lexical), pipeline de chat avec citations. Abstraction LLM supportant 7 providers (cloud et locaux) avec détection automatique de disponibilité et changement à la volée.

**Quant / Market Intelligence** — Moteur de détection de 14 signaux techniques sur chandeliers japonais. Modèle de juste valeur multifactoriel explicable. Score de confiance calibré. Niveaux pivot et support/résistance calculés.

**Frontend / Fullstack** — Dashboard React avec 6 onglets, graphiques en chandeliers annotés (custom shapes Recharts), interface de chat RAG interactive, sélecteur de LLM avec feedback de disponibilité en temps réel. Formatage intelligent des prix (séparateurs de milliers, axe Y adaptatif pour les cryptos à 5+ chiffres). Détection automatique des tickers crypto côté client avec badge source visible.
