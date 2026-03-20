import { useState, useCallback } from "react";
import { T } from "./styles/theme";
import { Pill, VerdictBadge, Num, Tag, Skeleton } from "./components/ui";
import { MacroRibbon } from "./components/MacroRibbon";
import { OverviewTab } from "./components/OverviewTab";
import { TechniqueTab } from "./components/TechniqueTab";
import { FondamentauxTab } from "./components/FondamentauxTab";
import { NewsTab } from "./components/NewsTab";
import { useAnalysis } from "./hooks/useAnalysis";

const TICKERS = ["AAPL", "MSFT", "NVDA", "GOOGL", "AMZN", "META", "TSLA", "JPM", "JNJ", "BTC"];
const TABS = ["overview", "technique", "fondamentaux", "news"];
const PROVIDERS = ["sample", "yahoo", "stooq", "alpha_vantage", "auto"];

export default function App() {
  const [ticker, setTicker] = useState("AAPL");
  const [tab, setTab] = useState("overview");
  const [provider, setProvider] = useState("sample");
  const { data, macro, loading, error, reload, runPipeline } = useAnalysis(ticker);

  const h = data?.hybrid;
  const fv = data?.fairValue;
  const price = h?.hybrid?.current_price || fv?.current_price || 0;
  const upside = h?.hybrid?.upside_pct || fv?.upside_pct || 0;
  const verdict = h?.verdict || "neutral";
  const tickerName = data?.fundamentals?.name || data?.insight?.fundamentals?.name || ticker;

  const handleEtl = useCallback(() => runPipeline(provider), [runPipeline, provider]);

  return (
    <div style={{ minHeight: "100vh", background: T.bg, color: T.text, fontFamily: T.sans }}>
      {/* ── Macro ribbon ─────────────────────────────────────── */}
      <MacroRibbon macro={macro} />

      {/* ── Header ───────────────────────────────────────────── */}
      <div
        style={{
          padding: "12px 20px 0",
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          flexWrap: "wrap",
          gap: 10,
        }}
      >
        <div style={{ display: "flex", alignItems: "baseline", gap: 12 }}>
          <span style={{ fontSize: 11, color: T.accent, fontWeight: 700, letterSpacing: "0.15em", textTransform: "uppercase" }}>
            Market Insights
          </span>
          <span style={{ fontSize: 10, color: T.muted }}>v3.0 — Multi-Source Research Terminal</span>
        </div>
        <div style={{ display: "flex", gap: 4, overflowX: "auto" }}>
          {TICKERS.map((t) => (
            <Pill key={t} active={t === ticker} onClick={() => setTicker(t)}>
              {t}
            </Pill>
          ))}
        </div>
      </div>

      {/* ── Ticker headline ──────────────────────────────────── */}
      <div
        className="fade-up"
        style={{
          padding: "14px 20px 4px",
          display: "flex",
          alignItems: "baseline",
          gap: 14,
          flexWrap: "wrap",
        }}
      >
        <div>
          <span style={{ fontSize: 24, fontWeight: 700 }}>{ticker}</span>
          <span style={{ fontSize: 13, color: T.muted, marginLeft: 8 }}>{tickerName}</span>
        </div>
        {price > 0 && (
          <div style={{ display: "flex", alignItems: "baseline", gap: 10 }}>
            <Num v={price.toFixed(2)} size={28} prefix={ticker === "BTC" ? "" : "$"} />
            {upside !== 0 && (
              <Num
                v={`${upside > 0 ? "+" : ""}${upside.toFixed(2)}`}
                suffix="% FV"
                size={13}
                color={upside > 0 ? T.green : T.red}
              />
            )}
          </div>
        )}
        {h && <VerdictBadge verdict={verdict} />}
        {data?.fundamentals?.sector && <Tag color={T.accent}>{data.fundamentals.sector}</Tag>}
      </div>

      {/* ── Controls ─────────────────────────────────────────── */}
      <div
        style={{
          padding: "8px 20px",
          display: "flex",
          alignItems: "center",
          gap: 8,
          flexWrap: "wrap",
        }}
      >
        <select
          value={provider}
          onChange={(e) => setProvider(e.target.value)}
          style={{
            padding: "5px 10px",
            borderRadius: 6,
            border: `1px solid ${T.border}`,
            background: T.panel2,
            color: T.text,
            fontSize: 11,
            fontFamily: T.sans,
          }}
        >
          {PROVIDERS.map((p) => (
            <option key={p} value={p}>{p}</option>
          ))}
        </select>
        <button
          onClick={handleEtl}
          disabled={loading}
          style={{
            padding: "5px 14px",
            borderRadius: 6,
            border: "none",
            background: `linear-gradient(135deg, #1d4ed8, #0891b2)`,
            color: "#fff",
            fontSize: 11,
            fontWeight: 700,
            cursor: loading ? "wait" : "pointer",
            opacity: loading ? 0.6 : 1,
            fontFamily: T.sans,
          }}
        >
          {loading ? "Chargement…" : "Lancer ETL + Recharger"}
        </button>
        <button
          onClick={reload}
          disabled={loading}
          style={{
            padding: "5px 14px",
            borderRadius: 6,
            border: `1px solid ${T.border}`,
            background: T.panel2,
            color: T.text,
            fontSize: 11,
            fontWeight: 600,
            cursor: "pointer",
            fontFamily: T.sans,
          }}
        >
          Recharger l'analyse
        </button>
        {error && (
          <span style={{ fontSize: 11, color: T.red, marginLeft: 8 }}>⚠ {error}</span>
        )}
        {loading && (
          <span style={{ fontSize: 11, color: T.amber, animation: "pulse 1.5s infinite" }}>
            Chargement en cours…
          </span>
        )}
      </div>

      {/* ── Tab bar ──────────────────────────────────────────── */}
      <div
        style={{
          padding: "0 20px",
          display: "flex",
          gap: 2,
          borderBottom: `1px solid ${T.border}`,
          marginBottom: 14,
        }}
      >
        {TABS.map((t) => (
          <button
            key={t}
            onClick={() => setTab(t)}
            style={{
              padding: "8px 16px",
              fontSize: 12,
              fontWeight: 600,
              fontFamily: T.sans,
              background: "transparent",
              border: "none",
              borderBottom: `2px solid ${tab === t ? T.accent : "transparent"}`,
              color: tab === t ? T.text : T.muted,
              cursor: "pointer",
              transition: "all .15s",
            }}
          >
            {t.charAt(0).toUpperCase() + t.slice(1)}
          </button>
        ))}
      </div>

      {/* ── Content ──────────────────────────────────────────── */}
      <div style={{ padding: "0 20px 30px" }}>
        {loading && !data ? (
          <LoadingSkeleton />
        ) : (
          <>
            {tab === "overview" && <OverviewTab data={data} />}
            {tab === "technique" && <TechniqueTab data={data} />}
            {tab === "fondamentaux" && <FondamentauxTab data={data} />}
            {tab === "news" && <NewsTab data={data} macro={macro} />}
          </>
        )}
      </div>

      {/* ── Footer ───────────────────────────────────────────── */}
      <div
        style={{
          padding: "12px 20px",
          borderTop: `1px solid ${T.border}`,
          fontSize: 10,
          color: T.muted,
          textAlign: "center",
          fontFamily: T.mono,
        }}
      >
        Analyse générée automatiquement à titre informatif · Ne constitue pas un conseil en investissement
        · Market Insights v3.0 — 9 open data providers · FastAPI + SQLAlchemy + RAG
      </div>
    </div>
  );
}

function LoadingSkeleton() {
  return (
    <div style={{ display: "grid", gridTemplateColumns: "1fr 320px", gap: 14 }}>
      <div style={{ display: "flex", flexDirection: "column", gap: 14 }}>
        <div style={{ display: "grid", gridTemplateColumns: "repeat(4, 1fr)", gap: 10 }}>
          {[1, 2, 3, 4].map((i) => (
            <Skeleton key={i} height={70} />
          ))}
        </div>
        <Skeleton height={200} />
        <Skeleton height={120} />
      </div>
      <div style={{ display: "flex", flexDirection: "column", gap: 14 }}>
        <Skeleton height={140} />
        <Skeleton height={160} />
        <Skeleton height={100} />
      </div>
    </div>
  );
}
