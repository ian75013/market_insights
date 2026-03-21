import { Card, Label, Tag } from "./ui";

export function TechniqueTab({ data }) {
  const ins = data?.insight;
  const comp = data?.comparable || ins?.comparable;
  if (!ins) return null;
  const tech = ins.technicals || {};
  const levels = comp?.levels || {};
  const signals = comp?.signals || {};
  const quotes = comp?.quotes || {};

  const metrics = [
    { l: "RSI 14", v: Number(tech.rsi_14 || 50).toFixed(1), c: tech.rsi_14 > 70 ? "text-red" : tech.rsi_14 < 30 ? "text-green" : "" },
    { l: "Momentum 20", v: ((tech.momentum_20 || 0) * 100).toFixed(2) + "%", c: tech.momentum_20 > 0 ? "text-green" : "text-red" },
    { l: "Volatilité 20", v: ((tech.volatility_20 || 0) * 100).toFixed(2) + "%", c: "" },
    { l: "Trend Signal", v: tech.trend_signal ? "Haussier" : "Baissier", c: tech.trend_signal ? "text-green" : "text-red" },
    { l: "SMA 20", v: Number(tech.sma_20 || 0).toFixed(2), c: "text-amber" },
    { l: "SMA 50", v: Number(tech.sma_50 || 0).toFixed(2), c: "text-red" },
    { l: "SMA 200", v: Number(tech.sma_200 || 0).toFixed(2), c: "muted" },
    { l: "Drawdown", v: ((tech.drawdown || 0) * 100).toFixed(2) + "%", c: "text-red" },
  ];
  const qm = quotes.current_price ? [
    { l: "Cours", v: quotes.current_price }, { l: "Ouverture", v: quotes.open },
    { l: "Haut J.", v: quotes.high }, { l: "Bas J.", v: quotes.low },
    { l: "Variation", v: `${quotes.day_change_pct > 0 ? "+" : ""}${quotes.day_change_pct}%`, c: quotes.day_change_pct > 0 ? "text-green" : "text-red" },
    { l: "Vol. Ratio", v: quotes.volume_ratio?.toFixed(2) },
    { l: "Haut 20j", v: quotes.high_20d }, { l: "Bas 20j", v: quotes.low_20d },
  ] : [];

  return (
    <div className="grid-2">
      <Card delay={0}><Label>Indicateurs Techniques</Label>
        <div className="grid-2 gap-sm">{metrics.map((m, i) => (
          <div key={i} className="metric-box"><div className="m-label">{m.l}</div><div className={`m-value mono ${m.c}`}>{m.v}</div></div>
        ))}</div>
      </Card>
      <Card delay={100}><Label>Cotations du Jour</Label>
        <div className="grid-2 gap-sm">{qm.map((m, i) => (
          <div key={i} className="metric-box"><div className="m-label">{m.l}</div><div className={`m-value mono ${m.c || ""}`}>{m.v}</div></div>
        ))}</div>
      </Card>
      <Card delay={200}><Label>Signaux & Patterns</Label>
        <div className="flex-col gap-xs">
          {[...(signals.patterns || []), ...(signals.candles || [])].map((s, i) => {
            const cls = s.includes("haussier") || s.includes("plus haut") || s.includes("accélération") ? "bull" : s.includes("baissier") || s.includes("excès") ? "bear" : "neut";
            return <div key={i} className={`signal-item ${cls}`}>{s}</div>;
          })}
          {!signals.patterns?.length && !signals.candles?.length && <div className="text-sm muted" style={{ padding: 12 }}>Aucun signal</div>}
        </div>
        {signals.flags && <div className="flex-row gap-xs" style={{ marginTop: 10, flexWrap: "wrap" }}>
          {Object.entries(signals.flags).map(([k, v]) => <Tag key={k} variant={v ? "green" : "muted"}>{k.replace(/_/g, " ")}: {v ? "✓" : "✗"}</Tag>)}
        </div>}
      </Card>
      <Card delay={300}><Label>Niveaux Pivot</Label>
        <div className="flex-col gap-xs">
          {[
            { l: "Objectif 2", v: levels.target_2, c: "text-accent" }, { l: "R1", v: levels.target_1 || levels.resistance, c: "text-red" },
            { l: "R2", v: levels.resistance_2, c: "text-red" }, { l: "Pivot", v: levels.pivot, c: "" },
            { l: "S1", v: levels.support, c: "text-green" }, { l: "S2", v: levels.support_2, c: "text-green" },
            { l: "Invalidation", v: levels.invalidation, c: "text-amber" },
          ].filter(x => x.v != null).map((lv, i) => (
            <div key={i} className="level-row"><span className="text-sm muted">{lv.l}</span><span className={`mono fw-600 ${lv.c}`}>{Number(lv.v).toFixed(2)}</span></div>
          ))}
        </div>
      </Card>
      {comp?.summary && (
        <Card delay={400} className="col-all"><Label>Résumé Technique</Label>
          <div className="grid-4">
            <div><div className="text-xs muted">Opinion</div><div className="text-base fw-600">{comp.summary.opinion}</div></div>
            <div><div className="text-xs muted">Tendance CT</div><div className={`text-base fw-600 ${comp.summary.trend_short?.includes("haussière") ? "text-green" : "text-red"}`}>{comp.summary.trend_short}</div></div>
            <div><div className="text-xs muted">Tendance LT</div><div className={`text-base fw-600 ${comp.summary.trend_long?.includes("haussière") ? "text-green" : "text-red"}`}>{comp.summary.trend_long}</div></div>
            <div><div className="text-xs muted">Score</div><div className="text-base fw-600 mono">{comp.summary.score_technical}</div></div>
          </div>
        </Card>
      )}
    </div>
  );
}
