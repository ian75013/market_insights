import { useState, useCallback, useEffect } from "react";
import { Pill, VerdictBadge, Num, Tag, Skeleton, ThemeToggle } from "./components/ui";
import { MacroRibbon } from "./components/MacroRibbon";
import { OverviewTab } from "./components/OverviewTab";
import { TechniqueTab } from "./components/TechniqueTab";
import { FondamentauxTab } from "./components/FondamentauxTab";
import { NewsTab } from "./components/NewsTab";
import { CandlestickTab } from "./components/CandlestickTab";
import { RagChatTab } from "./components/RagChatTab";
import { useAnalysis } from "./hooks/useAnalysis";

const TICKERS = ["AAPL", "MSFT", "NVDA", "GOOGL", "AMZN", "META", "TSLA", "JPM", "JNJ", "BTC"];
const TABS = ["overview", "chandeliers", "technique", "fondamentaux", "news", "rag chat"];
const PROVIDERS = ["sample", "yahoo", "coingecko", "stooq", "alpha_vantage", "auto"];

const CRYPTO_SET = new Set(["BTC","ETH","SOL","ADA","DOGE","DOT","AVAX","MATIC","LINK","UNI","XRP","BNB","ATOM","LTC","NEAR"]);
const fmtHeaderPrice = (v) => v >= 1000
  ? v.toLocaleString("en-US", { maximumFractionDigits: 0 })
  : v.toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 });

export default function App() {
  const [ticker, setTicker] = useState("AAPL");
  const [tab, setTab] = useState("overview");
  const [provider, setProvider] = useState("sample");
  const [theme, setTheme] = useState(() => localStorage.getItem("mi-theme") || "light");
  const { data, macro, loading, error, reload, runPipeline } = useAnalysis(ticker);

  useEffect(() => {
    document.documentElement.setAttribute("data-theme", theme);
    localStorage.setItem("mi-theme", theme);
  }, [theme]);

  const toggleTheme = () => setTheme(t => t === "dark" ? "light" : "dark");

  const h = data?.hybrid;
  const fv = data?.fairValue;
  const price = h?.hybrid?.current_price || fv?.current_price || 0;
  const upside = h?.hybrid?.upside_pct || fv?.upside_pct || 0;
  const verdict = h?.verdict || "neutral";
  const tickerName = data?.fundamentals?.name || data?.insight?.fundamentals?.name || ticker;

  const handleEtl = useCallback(() => runPipeline(provider), [runPipeline, provider]);

  return (
    <div className="app-shell">
      <MacroRibbon macro={macro} />

      {/* Header */}
      <div className="header">
        <div className="flex-row">
          <span className="brand">Market Insights</span>
          <span className="brand-sub">v4.0 — RAG + LLM + Chandeliers</span>
          <ThemeToggle theme={theme} onToggle={toggleTheme} />
        </div>
        <div className="flex-row gap-xs">
          {TICKERS.map(t => <Pill key={t} active={t === ticker} onClick={() => setTicker(t)}>{t}</Pill>)}
        </div>
      </div>

      {/* Ticker headline */}
      <div className="header fade-up">
        <div className="flex-row">
          <span className="ticker-name">{ticker}</span>
          <span className="ticker-sub">{tickerName}</span>
        </div>
        <div className="flex-row">
          {price > 0 && <Num v={fmtHeaderPrice(price)} size="lg" prefix={CRYPTO_SET.has(ticker) ? "" : "$"} />}
          {upside !== 0 && (
            <Num v={`${upside > 0 ? "+" : ""}${upside.toFixed(2)}%`} size="sm" className={upside > 0 ? "text-green" : "text-red"} suffix=" FV" />
          )}
          {h && <VerdictBadge verdict={verdict} />}
          {data?.fundamentals?.sector && <Tag variant="accent">{data.fundamentals.sector}</Tag>}
        </div>
      </div>

      {/* Controls */}
      <div className="controls">
        <select className="select" value={provider} onChange={e => setProvider(e.target.value)}>
          {PROVIDERS.map(p => <option key={p} value={p}>{p}</option>)}
        </select>
        <button className="btn btn-primary" onClick={handleEtl} disabled={loading}>
          {loading ? "Chargement…" : "Lancer ETL + Recharger"}
        </button>
        <button className="btn btn-secondary" onClick={reload} disabled={loading}>Recharger</button>
        {error && <span className="error-msg">⚠ {error}</span>}
        {loading && <span className="loading-pulse">Chargement…</span>}
      </div>

      {/* Tabs */}
      <div className="tab-bar">
        {TABS.map(t => (
          <button key={t} className={`tab-btn ${tab === t ? "active" : ""}`} onClick={() => setTab(t)}>
            {t.charAt(0).toUpperCase() + t.slice(1)}
          </button>
        ))}
      </div>

      {/* Content */}
      <div className="page-pad">
        {loading && !data ? (
          <div className="grid-sidebar">
            <div className="flex-col">
              <div className="grid-4">{[1,2,3,4].map(i => <Skeleton key={i} height={70} />)}</div>
              <Skeleton height={200} /><Skeleton height={120} />
            </div>
            <div className="flex-col"><Skeleton height={140} /><Skeleton height={160} /><Skeleton height={100} /></div>
          </div>
        ) : (<>
          {tab === "overview" && <OverviewTab data={data} />}
          {tab === "chandeliers" && <CandlestickTab data={data} ticker={ticker} />}
          {tab === "technique" && <TechniqueTab data={data} />}
          {tab === "fondamentaux" && <FondamentauxTab data={data} />}
          {tab === "news" && <NewsTab data={data} macro={macro} />}
          {tab === "rag chat" && <RagChatTab ticker={ticker} />}
        </>)}
      </div>

      <div className="footer">
        Analyse générée automatiquement à titre informatif · Ne constitue pas un conseil en investissement · Market Insights v4.0
      </div>
    </div>
  );
}
