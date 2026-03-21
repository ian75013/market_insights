import { fmtMcap, pct } from "../styles/theme";
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
    { l: "P/E", v: f.pe || "—" }, { l: "Fwd P/E", v: f.forward_pe || f.fwd_pe || "—" },
    { l: "Rev. Growth", v: pct(f.revenue_growth), c: (f.revenue_growth || 0) > 0 ? "text-green" : "text-red" },
    { l: "EPS Growth", v: pct(f.eps_growth || f.earnings_growth), c: (f.eps_growth || 0) > 0 ? "text-green" : "text-red" },
    { l: "Profit Margin", v: pct(f.profit_margin) }, { l: "ROE", v: pct(f.return_on_equity || f.roe) },
    { l: "D/E", v: typeof f.debt_to_equity === "number" ? f.debt_to_equity.toFixed(2) : "—", c: (f.debt_to_equity||0)>1.5?"text-red":(f.debt_to_equity||0)>1?"text-amber":"text-green" },
    { l: "Beta", v: typeof f.beta === "number" ? f.beta.toFixed(2) : "—" },
    { l: "Div. Yield", v: pct(f.dividend_yield) }, { l: "Gross Margin", v: pct(f.gross_margin) },
    { l: "Op. Margin", v: pct(f.operating_margin) }, { l: "ROA", v: pct(f.return_on_assets) },
  ].filter(m => m.v !== "—" && m.v !== "0.0%");

  return (
    <div className="grid-3">
      <Card delay={0} className="col-all">
        <div className="flex-row" style={{ marginBottom: 14 }}>
          <span className="text-lg fw-600">{f.name || f.ticker || "—"}</span>
          {f.sector && <Tag variant="accent">{f.sector}</Tag>}
          {f.market_cap > 0 && <Tag variant="muted">MCap {fmtMcap(f.market_cap)}</Tag>}
          {f._source && <Tag variant="muted">Source: {f._source}</Tag>}
        </div>
        <div className="grid-6 gap-sm">
          {mainMetrics.map((m, i) => (
            <div key={i} className="metric-box metric-box-center"><div className="m-label">{m.l}</div><div className={`m-value mono ${m.c||""}`}>{m.v}</div></div>
          ))}
        </div>
      </Card>

      <Card delay={150}><Label>Facteurs Fair Value</Label>
        <GaugeBar value={Math.abs(factors.momentum_20||0)} max={0.3} label={`Momentum (${((factors.momentum_20||0)*100).toFixed(1)}%)`} colorClass={(factors.momentum_20||0)>0?"text-green":"text-red"} />
        <GaugeBar value={factors.volatility_20||0} max={0.1} label={`Volatilité (${((factors.volatility_20||0)*100).toFixed(1)}%)`} colorClass="text-amber" />
        <GaugeBar value={confidence} label="Confiance modèle" colorClass="text-accent" />
        <GaugeBar value={Math.max(0,factors.revenue_growth||f.revenue_growth||0)} max={0.35} label={`Rev Growth (${((factors.revenue_growth||f.revenue_growth||0)*100).toFixed(0)}%)`} colorClass="text-green" />
      </Card>

      <Card delay={250}><Label>Valorisation vs Modèle</Label>
        <div className="flex-col gap-sm">
          <div className="metric-box metric-box-center"><div className="m-label">Prix actuel</div><div className="num num-lg">${price.toFixed(2)}</div></div>
          <div className="center"><span className="muted text-lg">→</span> <span className={`mono fw-600 ${upside>0?"text-green":"text-red"}`}>{upside>0?"+":""}{upside.toFixed(2)}%</span></div>
          <div className="metric-box metric-box-center" style={{ background: upside>0?"rgba(0,214,126,.06)":"rgba(255,77,106,.06)", border: `1px solid ${upside>0?"rgba(0,214,126,.15)":"rgba(255,77,106,.15)"}` }}>
            <div className="m-label">Juste valeur (modèle)</div><div className={`num num-lg ${upside>0?"text-green":"text-red"}`}>${fairVal.toFixed(2)}</div>
          </div>
        </div>
      </Card>

      <Card delay={350}><Label>Sources de données</Label>
        <div className="flex-col gap-xs">
          {[{n:"Yahoo Finance",k:"yahoo"},{n:"Alpha Vantage",k:"alpha_vantage"},{n:"FMP",k:"fmp"},{n:"SEC EDGAR",k:"sec_edgar"},{n:"Sample",k:"sample"}].map((p,i) => {
            const active = f._source === p.k || (!f._source && p.k === "sample");
            return <div key={i} className="level-row"><span className={active?"text-sm":"text-sm muted"}>{p.n}</span>{active && <Tag variant="green">actif</Tag>}</div>;
          })}
        </div>
      </Card>
    </div>
  );
}
