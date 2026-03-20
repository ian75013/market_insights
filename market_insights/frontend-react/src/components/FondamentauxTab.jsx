import { T, fmtMcap, pct } from "../styles/theme";
import { Card, Label, Tag, GaugeBar } from "./ui";

export function FondamentauxTab({ data }) {
  const fund = data?.fundamentals;
  const fv = data?.fairValue;
  const ins = data?.insight;
  if (!fund && !fv) return null;

  const f = fund || ins?.fundamentals || {};
  const price = fv?.current_price || 0;
  const fairVal = fv?.fair_value || 0;
  const upside = fv?.upside_pct || 0;
  const confidence = fv?.confidence || 0;
  const factors = fv?.factors || {};

  const mainMetrics = [
    { l: "P/E", v: f.pe || "—" },
    { l: "Fwd P/E", v: f.forward_pe || f.fwd_pe || "—" },
    { l: "Rev. Growth", v: pct(f.revenue_growth), c: (f.revenue_growth || 0) > 0 ? T.green : T.red },
    { l: "EPS Growth", v: pct(f.eps_growth || f.earnings_growth), c: (f.eps_growth || 0) > 0 ? T.green : T.red },
    { l: "Profit Margin", v: pct(f.profit_margin) },
    { l: "ROE", v: pct(f.return_on_equity || f.roe) },
    { l: "Debt/Equity", v: typeof f.debt_to_equity === "number" ? f.debt_to_equity.toFixed(2) : "—",
      c: (f.debt_to_equity || 0) > 1.5 ? T.red : (f.debt_to_equity || 0) > 1 ? T.amber : T.green },
    { l: "Beta", v: typeof f.beta === "number" ? f.beta.toFixed(2) : "—" },
    { l: "Div. Yield", v: pct(f.dividend_yield) },
    { l: "Gross Margin", v: pct(f.gross_margin) },
    { l: "Op. Margin", v: pct(f.operating_margin) },
    { l: "ROA", v: pct(f.return_on_assets) },
  ].filter(m => m.v !== "—" && m.v !== "0.0%");

  return (
    <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr 1fr", gap: 14 }}>
      {/* Header with all metrics */}
      <Card delay={0} style={{ gridColumn: "1 / -1" }}>
        <div style={{ display: "flex", alignItems: "baseline", gap: 12, marginBottom: 12 }}>
          <span style={{ fontSize: 14, fontWeight: 600 }}>{f.name || f.ticker || "—"}</span>
          {f.sector && <Tag color={T.accent}>{f.sector}</Tag>}
          {f.market_cap > 0 && <Tag color={T.muted}>MCap {fmtMcap(f.market_cap)}</Tag>}
          {f._source && <Tag color={T.muted}>Source: {f._source}</Tag>}
        </div>
        <div style={{ display: "grid", gridTemplateColumns: `repeat(${Math.min(6, mainMetrics.length)}, 1fr)`, gap: 10 }}>
          {mainMetrics.map((m, i) => (
            <div key={i} style={{ padding: 10, background: T.panel2, borderRadius: 6, textAlign: "center" }}>
              <div style={{ fontSize: 9, color: T.muted, marginBottom: 4 }}>{m.l}</div>
              <div style={{ fontFamily: T.mono, fontSize: 15, fontWeight: 600, color: m.c || T.text }}>{m.v}</div>
            </div>
          ))}
        </div>
      </Card>

      {/* Fair value factors */}
      <Card delay={150}>
        <Label>Facteurs Fair Value</Label>
        <div style={{ display: "flex", flexDirection: "column", gap: 6, marginTop: 8 }}>
          <GaugeBar
            value={Math.abs(factors.momentum_20 || 0)}
            max={0.3}
            label={`Momentum 20j (${((factors.momentum_20 || 0) * 100).toFixed(1)}%)`}
            color={(factors.momentum_20 || 0) > 0 ? T.green : T.red}
          />
          <GaugeBar
            value={factors.volatility_20 || 0}
            max={0.1}
            label={`Volatilité 20j (${((factors.volatility_20 || 0) * 100).toFixed(1)}%)`}
            color={T.amber}
          />
          <GaugeBar value={confidence} label="Confiance modèle" color={T.accent} />
          <GaugeBar
            value={Math.max(0, factors.revenue_growth || f.revenue_growth || 0)}
            max={0.35}
            label={`Revenue Growth (${((factors.revenue_growth || f.revenue_growth || 0) * 100).toFixed(0)}%)`}
            color={T.green}
          />
        </div>
      </Card>

      {/* Valuation visual */}
      <Card delay={250}>
        <Label>Valorisation vs Modèle</Label>
        <div style={{ display: "flex", flexDirection: "column", gap: 10, marginTop: 8 }}>
          <div style={{ textAlign: "center", padding: 16, background: T.panel2, borderRadius: 8 }}>
            <div style={{ fontSize: 10, color: T.muted }}>Prix actuel</div>
            <div style={{ fontFamily: T.mono, fontSize: 22, fontWeight: 700, marginTop: 4 }}>${price.toFixed(2)}</div>
          </div>
          <div style={{ display: "flex", justifyContent: "center", alignItems: "center", gap: 6 }}>
            <span style={{ fontSize: 18, color: T.muted }}>→</span>
            <span style={{ fontFamily: T.mono, fontSize: 14, fontWeight: 600, color: upside > 0 ? T.green : T.red }}>
              {upside > 0 ? "+" : ""}{upside.toFixed(2)}%
            </span>
          </div>
          <div style={{
            textAlign: "center", padding: 16, borderRadius: 8,
            background: (upside > 0 ? T.green : T.red) + "12",
            border: `1px solid ${(upside > 0 ? T.green : T.red)}25`,
          }}>
            <div style={{ fontSize: 10, color: T.muted }}>Juste valeur (modèle)</div>
            <div style={{ fontFamily: T.mono, fontSize: 22, fontWeight: 700, color: upside > 0 ? T.green : T.red, marginTop: 4 }}>
              ${fairVal.toFixed(2)}
            </div>
          </div>
        </div>
      </Card>

      {/* Data sources */}
      <Card delay={350}>
        <Label>Sources de données</Label>
        <div style={{ display: "flex", flexDirection: "column", gap: 5, marginTop: 8, fontSize: 11 }}>
          {[
            { n: "Yahoo Finance (yfinance)", k: "yahoo" },
            { n: "Alpha Vantage", k: "alpha_vantage" },
            { n: "Financial Modeling Prep", k: "fmp" },
            { n: "SEC EDGAR", k: "sec_edgar" },
            { n: "Sample data (fallback)", k: "sample" },
          ].map((p, i) => {
            const active = f._source === p.k || (!f._source && p.k === "sample");
            return (
              <div key={i} style={{ display: "flex", alignItems: "center", gap: 6, padding: "5px 8px", background: T.panel2, borderRadius: 4 }}>
                <span style={{ width: 5, height: 5, borderRadius: "50%", background: active ? T.green : T.muted }} />
                <span style={{ color: active ? T.text : T.muted }}>{p.n}</span>
                {active && <Tag color={T.green}>actif</Tag>}
              </div>
            );
          })}
        </div>
      </Card>
    </div>
  );
}
