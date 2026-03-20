# Market Insights — React Dashboard

Terminal de recherche financière de type Bloomberg/Refinitiv connecté à l'API Market Insights v3.

## Quick Start

```bash
npm install
npm run dev
# → http://localhost:3000
```

Le backend doit tourner sur `http://127.0.0.1:8000` — Vite proxy automatiquement `/api/*`.

## Architecture

```
src/
  services/api.js       ← Client API (tous les endpoints v3)
  hooks/useAnalysis.js  ← Hook React pour le chargement de données
  styles/
    theme.js            ← Design tokens (couleurs, typo, helpers)
    global.css          ← Reset + animations + fonts
  components/
    ui.jsx              ← Primitives (Card, Label, Tag, Pill, Gauge, Badge...)
    Charts.jsx          ← PriceChart + VolumeChart (recharts)
    MacroRibbon.jsx     ← Barre macro en haut
    OverviewTab.jsx     ← Vue d'ensemble (KPIs, résumé, fair value, signals, news)
    TechniqueTab.jsx    ← Indicateurs techniques, signaux, niveaux pivot
    FondamentauxTab.jsx ← Métriques fondamentales, valorisation, sources
    NewsTab.jsx         ← Feed news, sentiment, macro context
  App.jsx               ← Root component (routing interne, ticker selector)
  main.jsx              ← Entry point
```

## Endpoints consommés

| Endpoint | Composant |
|---|---|
| `GET /insights/{ticker}/hybrid` | OverviewTab |
| `GET /fair-value/{ticker}` | OverviewTab, FondamentauxTab |
| `GET /insights/{ticker}/comparable` | TechniqueTab |
| `GET /insights/{ticker}` | TechniqueTab, OverviewTab |
| `GET /rag/sources/{ticker}` | OverviewTab |
| `GET /fundamentals/{ticker}` | FondamentauxTab |
| `GET /news/{ticker}` | NewsTab |
| `GET /macro` | MacroRibbon, NewsTab |
| `POST /etl/run` | App (bouton ETL) |

## Intégration dans le repo principal

```bash
# Depuis la racine du projet market_insights :
cp -r frontend-react market_insights/frontend-react
```

Puis dans le `README.md` principal, ajouter :

```bash
cd market_insights/frontend-react
npm install && npm run dev
```

## Production build

```bash
npm run build
# Output dans dist/ — servir avec n'importe quel serveur statique
```

Pour pointer vers une autre URL backend :

```bash
VITE_API_BASE=https://api.example.com npm run build
```

## Stack

- **React 18** + hooks
- **Recharts** pour les graphiques
- **Vite** pour le bundling
- **DM Sans** + **JetBrains Mono** (Google Fonts)
- Dark theme terminal financier
