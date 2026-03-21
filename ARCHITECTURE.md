# Architecture — Market Insights v4

## Vue d'ensemble

```
┌─────────────────────────────────────────────────────────────────────┐
│                        FRONTEND (React + Vite)                      │
│   :3000                                                             │
│                                                                     │
│   ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐│
│   │ Overview  │ │Chandeliers│ │Technique │ │  News    │ │ RAG Chat ││
│   │          │ │  annotés  │ │          │ │          │ │  + LLM   ││
│   └────┬─────┘ └────┬─────┘ └────┬─────┘ └────┬─────┘ └────┬─────┘│
│        │            │            │            │            │       │
│        └────────────┴────────────┴────────────┴────────────┘       │
│                              │  HTTP / JSON                        │
└──────────────────────────────┼──────────────────────────────────────┘
                               │  Vite proxy /api/* → :8000
┌──────────────────────────────┼──────────────────────────────────────┐
│                        BACKEND (FastAPI)                            │
│   :8000                      │                                      │
│                              ▼                                      │
│   ┌─────────────────────────────────────────────────────────────┐   │
│   │                      API Router                             │   │
│   │                                                             │   │
│   │  /chart/candlestick/{t}  ──► Candlestick Engine (14 signals)│   │
│   │  /llm/chat               ──► RAG Chat Pipeline              │   │
│   │  /llm/providers          ──► LLM Registry                   │   │
│   │  /insights/{t}/hybrid    ──► Hybrid Insight Service          │   │
│   │  /fair-value/{t}         ──► Fair Value Model                │   │
│   │  /etl/run                ──► ETL Pipeline                    │   │
│   │  /fundamentals/{t}       ──► Multi-source Connector          │   │
│   │  /news/{t}               ──► Multi-source News               │   │
│   │  /macro                  ──► FRED / Sample                   │   │
│   └─────────────────────────────────────────────────────────────┘   │
│        │              │              │              │                │
│   ┌────▼────┐   ┌─────▼─────┐  ┌────▼────┐  ┌─────▼──────┐        │
│   │ Analysis│   │    RAG    │  │   LLM   │  │Connectors  │        │
│   │ Engine  │   │ Vectoriel │  │  Multi  │  │ Open Data  │        │
│   └─────────┘   └───────────┘  └─────────┘  └────────────┘        │
│        │              │              │              │                │
│   ┌────▼──────────────▼──────────────▼──────────────▼───────────┐   │
│   │                    SQLite + Vector Store                     │   │
│   └─────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────┘
```

---

## 1. Chandeliers annotés

### Backend : `market_insights/analysis/candlestick_engine.py`

L'endpoint `GET /chart/candlestick/{ticker}` retourne un tableau de barres OHLCV
où chaque barre porte ses signaux détectés :

```
Endpoint: GET /chart/candlestick/AAPL

Réponse:
{
  "ticker": "AAPL",
  "bars": [
    {
      "date": "2026-01-15",
      "open": 196.0, "high": 198.5, "low": 195.2, "close": 197.8,
      "volume": 1300000,
      "sma_20": 193.4, "sma_50": 190.1,
      "rsi_14": 62.3,
      "signals": [
        {"type": "pullback_sma20", "label": "Pullback SMA 20", "severity": "neutral"},
        {"type": "volume_spike", "label": "Volume ×2.1", "severity": "neutral", "value": 2.1}
      ]
    },
    ...
  ],
  "signal_summary": {"total": 42, "bullish": 18, "bearish": 12, "neutral": 12}
}
```

#### 14 types de signaux détectés par barre

| Signal | Type | Sévérité | Description |
|--------|------|----------|-------------|
| Gap haussier | `gap_up` | bullish | Low actuel > High précédent |
| Gap baissier | `gap_down` | bearish | High actuel < Low précédent |
| Pullback SMA 20 | `pullback_sma20` | neutral | Close à ±0.8% de la SMA 20 |
| Pullback SMA 50 | `pullback_sma50` | neutral | Close à ±0.8% de la SMA 50 |
| Breakout 20j | `breakout_20d` | bullish | Close > plus haut 20 séances |
| Breakdown 20j | `breakdown_20d` | bearish | Close < plus bas 20 séances |
| Avalement haussier | `bullish_engulfing` | bullish | Bougie qui englobe la baissière précédente |
| Avalement baissier | `bearish_engulfing` | bearish | Bougie qui englobe la haussière précédente |
| Marteau | `hammer` | bullish | Petit corps en haut, longue mèche basse |
| Étoile filante | `shooting_star` | bearish | Petit corps en bas, longue mèche haute |
| Doji | `doji` | neutral | Corps < 8% du range |
| Étoile du matin | `morning_star` | bullish | Pattern 3 bougies (bear → petit corps → bull) |
| Étoile du soir | `evening_star` | bearish | Pattern 3 bougies (bull → petit corps → bear) |
| Volume spike | `volume_spike` | neutral | Volume ≥ 1.8× moyenne 20j |
| RSI surachat | `rsi_overbought` | bearish | RSI ≥ 75 |
| RSI survente | `rsi_oversold` | bullish | RSI ≤ 25 |
| Golden Cross | `golden_cross` | bullish | SMA 20 croise au-dessus de SMA 50 |
| Death Cross | `death_cross` | bearish | SMA 20 croise en dessous de SMA 50 |

### Frontend : `CandlestickTab.jsx`

L'onglet **Chandeliers** dans le dashboard React affiche :
- Graphique en chandeliers japonais avec shapes custom (corps + mèches)
- SMA 20 / SMA 50 en overlay
- Lignes de support / résistance
- Dots colorés sur les bougies portant un signal (vert=bullish, rouge=bearish, ambre=neutral)
- Tooltip détaillé par bougie (OHLCV + RSI + signaux)
- Volume bars colorisées sous le chart
- Chronologie des signaux à gauche avec filtre par sévérité
- Compteur de patterns à droite
- Niveaux pivot clés

---

## 2. RAG Vectoriel + LLM Multi-provider

### Pipeline RAG

```
Question utilisateur
       │
       ▼
┌──────────────┐     ┌──────────────┐     ┌──────────────┐
│  1. Retrieve │────▶│ 2. Augment   │────▶│ 3. Generate  │
│              │     │              │     │              │
│ Vector search│     │ Build prompt │     │ Send to LLM  │
│ + lexical    │     │ with context │     │ (au choix)   │
│ reranking    │     │ + citations  │     │              │
└──────┬───────┘     └──────────────┘     └──────┬───────┘
       │                                         │
       ▼                                         ▼
  VectorStore                              LLM Provider
  (in-memory)                              sélectionné
       │
       │  Indexation automatique
       │  au premier appel
       ▼
  ┌──────────┐
  │ SQLite   │
  │ Documents│
  └──────────┘
```

### Backend RAG : `market_insights/rag/`

| Fichier | Rôle |
|---------|------|
| `embeddings.py` | Moteur d'embeddings (sentence-transformers ou TF-IDF fallback), VectorStore in-memory |
| `store.py` | Retrieval hybride : 70% cosine similarity + 30% lexical BM25, auto-indexation |
| `chat.py` | Pipeline RAG Chat : retrieve → build prompt → call LLM → retourner réponse + sources |
| `chunking.py` | Découpage des documents en chunks (taille et overlap configurables) |

#### Embeddings

```python
# Priorité : sentence-transformers → TF-IDF
RAG_EMBEDDING_MODEL=all-MiniLM-L6-v2   # modèle sentence-transformers
RAG_USE_VECTORS=true                     # false → fallback TF-IDF scikit-learn
```

#### Retrieval hybride

Score final = **0.7 × cosine_similarity** + **0.3 × lexical_score**

Cela combine la compréhension sémantique (le modèle comprend que "croissance" ≈ "growth")
avec la précision lexicale (le terme exact "AAPL" est dans le document).

#### Endpoint

```
POST /llm/chat
{
  "ticker": "AAPL",
  "question": "Quels sont les catalyseurs de croissance ?",
  "llm_backend": "ollama",       ← choix du provider
  "llm_model": "llama3",         ← choix du modèle
  "language": "fr",
  "top_k": 5
}

Réponse:
{
  "answer": "D'après les documents indexés, les principaux catalyseurs...",
  "sources": [
    {"title": "Apple services momentum...", "score": 0.82, "document_type": "news"},
    ...
  ],
  "llm": {"provider": "ollama", "model": "llama3", "usage": {...}}
}
```

### Backend LLM : `market_insights/llm/providers.py`

7 providers avec interface unifiée :

```
┌───────────────────────────────────────────────────────────────┐
│                    BaseLLMProvider                             │
│   .available() → bool                                         │
│   .generate(prompt, system=...) → LLMResponse                 │
│   .models() → list[str]                                       │
└───────────────────┬───────────────────────────────────────────┘
                    │
     ┌──────────────┼──────────────────────────────────────┐
     │              │              │              │         │
┌────▼───┐  ┌──────▼──┐  ┌───────▼──┐  ┌───────▼──┐  ┌───▼────┐
│ OpenAI │  │Anthropic│  │ Mistral  │  │  Groq    │  │Fallback│
│ (API)  │  │ (API)   │  │ (API)    │  │ (API)    │  │(no LLM)│
└────────┘  └─────────┘  └──────────┘  └──────────┘  └────────┘
                                              │
                              ┌────────────────┼──────────────┐
                         ┌────▼────┐                   ┌──────▼───┐
                         │ Ollama  │                   │ LMStudio │
                         │ (local) │                   │ (local)  │
                         │:11434   │                   │:1234     │
                         └─────────┘                   └──────────┘
```

| Provider | Clé nécessaire | Modèles principaux | Local |
|----------|---------------|-------------------|-------|
| **OpenAI** | `OPENAI_API_KEY` | gpt-4o, gpt-4o-mini | Non |
| **Anthropic** | `ANTHROPIC_API_KEY` | claude-sonnet-4-20250514, claude-haiku-4-20250414 | Non |
| **Mistral** | `MISTRAL_API_KEY` | mistral-large, mistral-small | Non |
| **Groq** | `GROQ_API_KEY` | llama-3.3-70b, mixtral-8x7b | Non |
| **Ollama** | Aucune | llama3, mistral, codellama... | Oui (:11434) |
| **LMStudio** | Aucune | Tout modèle GGUF chargé | Oui (:1234) |
| **Fallback** | Aucune | — | Oui (déterministe) |

La détection est automatique : le système interroge chaque provider au démarrage.

```
GET /llm/providers

{
  "providers": [
    {"name": "openai",    "available": true,  "models": ["gpt-4o", "gpt-4o-mini"]},
    {"name": "anthropic", "available": false, "models": []},
    {"name": "ollama",    "available": true,  "models": ["llama3", "mistral"]},
    {"name": "fallback",  "available": true,  "models": []}
  ],
  "active_backend": "ollama"
}
```

### Frontend RAG Chat : `RagChatTab.jsx`

L'onglet **RAG Chat** dans le dashboard affiche :
- Interface de chat (bulles utilisateur / assistant)
- Sélecteur de provider LLM avec indicateur de disponibilité (vert=online, gris=offline)
- Sélecteur de modèle (liste dynamique depuis le backend)
- Sources citées avec score sous chaque réponse
- Quick prompts pré-remplis
- Bouton de réindexation RAG
- Stats du VectorStore
- Guide de configuration

---

## 3. Structure complète des fichiers

```
market_insights-main/
│
├── market_insights/
│   ├── api/
│   │   └── main.py                    ← FastAPI v4 (tous les endpoints)
│   │
│   ├── analysis/
│   │   ├── candlestick_engine.py      ← ★ NOUVEAU: 14 signaux par barre
│   │   ├── feature_engineering.py
│   │   ├── signal_detection.py
│   │   ├── target_engine.py
│   │   └── technical_scoring.py
│   │
│   ├── llm/
│   │   ├── providers.py               ← ★ NOUVEAU: 7 LLM providers
│   │   └── report_generator.py        ← Mis à jour: utilise le LLM si dispo
│   │
│   ├── rag/
│   │   ├── embeddings.py              ← ★ NOUVEAU: sentence-transformers / TF-IDF
│   │   ├── store.py                   ← Mis à jour: retrieval hybride vectoriel
│   │   ├── chat.py                    ← ★ NOUVEAU: pipeline RAG Chat
│   │   └── chunking.py
│   │
│   ├── connectors/open_data/          ← 9 connecteurs (yahoo, alpha_vantage, etc.)
│   ├── core/config.py                 ← Mis à jour: vars LLM + RAG
│   ├── db/                            ← SQLAlchemy models
│   ├── etl/                           ← Pipeline ETL
│   ├── ml/                            ← Fair value model
│   ├── services/                      ← Orchestration
│   ├── tests/                         ← 40 tests
│   │
│   ├── frontend-react/                ← ★ Dashboard React/Vite
│   │   └── src/
│   │       ├── components/
│   │       │   ├── CandlestickTab.jsx ← ★ Onglet chandeliers annotés
│   │       │   ├── RagChatTab.jsx     ← ★ Onglet RAG Chat + LLM
│   │       │   ├── OverviewTab.jsx
│   │       │   ├── TechniqueTab.jsx
│   │       │   ├── FondamentauxTab.jsx
│   │       │   ├── NewsTab.jsx
│   │       │   ├── Charts.jsx
│   │       │   ├── MacroRibbon.jsx
│   │       │   └── ui.jsx
│   │       ├── services/api.js        ← Client API v4
│   │       ├── hooks/useAnalysis.js
│   │       ├── styles/
│   │       └── App.jsx                ← 6 onglets
│   │
│   └── frontend-angular/              ← Dashboard Angular (legacy)
│
├── .env.example                       ← Toutes les variables LLM/RAG
├── requirements.txt
├── Dockerfile
├── docker-compose.yml
├── ARCHITECTURE.md                    ← Ce document
└── README.md
```

---

## 4. Configuration rapide

### Mode minimal (offline, sans LLM)

```env
USE_NETWORK=false
LLM_BACKEND=fallback
RAG_USE_VECTORS=false
```

### Mode local (Ollama)

```bash
# Terminal 1: lancer Ollama
ollama pull llama3
ollama serve

# Terminal 2: .env
USE_NETWORK=false
LLM_BACKEND=ollama
OLLAMA_MODEL=llama3
RAG_USE_VECTORS=true
```

### Mode cloud (OpenAI + données live)

```env
USE_NETWORK=true
DEFAULT_PRICE_PROVIDER=auto
LLM_BACKEND=openai
OPENAI_API_KEY=sk-...
RAG_USE_VECTORS=true
```

---

## 5. Flux de données complet

```
1. ETL: POST /etl/run?ticker=AAPL&provider=auto
   └─► Yahoo Finance → clean → features → SQLite (prices + documents)

2. Index: automatique au premier appel RAG
   └─► Documents SQLite → chunking → embeddings → VectorStore

3. Analyse: GET /insights/AAPL/hybrid
   └─► Prices DB → technicals + fair value + signals + RAG context → résumé

4. Chandeliers: GET /chart/candlestick/AAPL
   └─► Prices DB → features → 14 détecteurs par barre → JSON annotés

5. RAG Chat: POST /llm/chat {ticker, question, llm_backend}
   └─► VectorStore search → prompt augmenté → LLM → réponse + sources
```
