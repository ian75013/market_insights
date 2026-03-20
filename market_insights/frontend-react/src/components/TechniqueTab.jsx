import { T } from "../styles/theme";
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
    { l: "RSI 14", v: Number(tech.rsi_14 || 50).toFixed(1), c: tech.rsi_14 > 70 ? T.red : tech.rsi_14 < 30 ? T.green : T.text },
    { l: "Momentum 20", v: ((tech.momentum_20 || 0) * 100).toFixed(2) + "%", c: tech.momentum_20 > 0 ? T.green : T.red },
    { l: "Volatilité 20", v: ((tech.volatility_20 || 0) * 100).toFixed(2) + "%", c: T.text },
    { l: "Trend Signal", v: tech.trend_signal ? "Haussier" : "Baissier", c: tech.trend_signal ? T.green : T.red },
    { l: "SMA 20", v: Number(tech.sma_20 || 0).toFixed(2), c: T.amber },
    { l: "SMA 50", v: Number(tech.sma_50 || 0).toFixed(2), c: T.red },
    { l: "SMA 200", v: Number(tech.sma_200 || 0).toFixed(2), c: T.muted },
    { l: "Drawdown", v: ((tech.drawdown || 0) * 100).toFixed(2) + "%", c: T.red },
  ];

  const quotesMetrics = quotes.current_price ? [
    { l: "Cours", v: quotes.current_price },
    { l: "Ouverture", v: quotes.open },
    { l: "Haut J.", v: quotes.high },
    { l: "Bas J.", v: quotes.low },
    { l: "Variation J.", v: `${quotes.day_change_pct > 0 ? "+" : ""}${quotes.day_change_pct}%`, c: quotes.day_change_pct > 0 ? T.green : T.red },
    { l: "Volume Ratio", v: quotes.volume_ratio?.toFixed(2) },
    { l: "Plus haut 20j", v: quotes.high_20d },
    { l: "Plus bas 20j", v: quotes.low_20d },
  ] : [];

  return (
    <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 14 }}>
      {/* Indicators */}
      <Card delay={0}>
        <Label>Indicateurs Techniques</Label>
        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 10, marginTop: 10 }}>
          {metrics.map((m, i) => (
            <div key={i} style={{ padding: "10px 12px", background: T.panel2, borderRadius: 6 }}>
              <div style={{ fontSize: 9, color: T.muted }}>{m.l}</div>
              <div style={{ fontFamily: T.mono, fontSize: 16, fontWeight: 600, color: m.c, marginTop: 2 }}>{m.v}</div>
            </div>
          ))}
        </div>
      </Card>

      {/* Quotes */}
      <Card delay={100}>
        <Label>Cotations du Jour</Label>
        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 10, marginTop: 10 }}>
          {quotesMetrics.map((m, i) => (
            <div key={i} style={{ padding: "10px 12px", background: T.panel2, borderRadius: 6 }}>
              <div style={{ fontSize: 9, color: T.muted }}>{m.l}</div>
              <div style={{ fontFamily: T.mono, fontSize: 16, fontWeight: 600, color: m.c || T.text, marginTop: 2 }}>{m.v}</div>
            </div>
          ))}
        </div>
      </Card>

      {/* Signals */}
      <Card delay={200}>
        <Label>Signaux & Patterns</Label>
        <div style={{ display: "flex", flexDirection: "column", gap: 8, marginTop: 8 }}>
          {[...(signals.patterns || []), ...(signals.candles || [])].map((s, i) => (
            <div key={i} style={{ display: "flex", alignItems: "center", gap: 8, padding: "8px 12px", background: T.panel2, borderRadius: 6 }}>
              <span style={{ width: 8, height: 8, borderRadius: "50%",
                background: s.includes("haussier") || s.includes("plus haut") || s.includes("accélération") ? T.green : s.includes("baissier") || s.includes("excès") ? T.red : T.amber
              }} />
              <span style={{ fontSize: 12 }}>{s}</span>
            </div>
          ))}
          {!signals.patterns?.length && !signals.candles?.length && (
            <div style={{ fontSize: 12, color: T.muted, padding: 12 }}>Aucun signal détecté</div>
          )}
        </div>
        {/* Flags */}
        {signals.flags && (
          <div style={{ display: "flex", flexWrap: "wrap", gap: 5, marginTop: 10 }}>
            {Object.entries(signals.flags).map(([k, v]) => (
              <Tag key={k} color={v ? T.green : T.muted}>{k.replace(/_/g, " ")}: {v ? "✓" : "✗"}</Tag>
            ))}
          </div>
        )}
      </Card>

      {/* Levels */}
      <Card delay={300}>
        <Label>Niveaux Pivot</Label>
        <div style={{ display: "flex", flexDirection: "column", gap: 6, marginTop: 8 }}>
          {[
            { l: "Objectif 2", v: levels.target_2, c: T.accent },
            { l: "Objectif 1 / R1", v: levels.target_1 || levels.resistance, c: T.red },
            { l: "Résistance 2", v: levels.resistance_2, c: T.red },
            { l: "Pivot", v: levels.pivot, c: T.text },
            { l: "Support S1", v: levels.support, c: T.green },
            { l: "Support S2", v: levels.support_2, c: T.green },
            { l: "Invalidation", v: levels.invalidation, c: T.amber },
          ].filter(x => x.v != null).map((lv, i) => (
            <div key={i} style={{ display: "flex", justifyContent: "space-between", padding: "6px 10px", background: T.panel2, borderRadius: 5 }}>
              <span style={{ fontSize: 11, color: T.muted }}>{lv.l}</span>
              <span style={{ fontFamily: T.mono, fontSize: 13, fontWeight: 600, color: lv.c }}>{Number(lv.v).toFixed(2)}</span>
            </div>
          ))}
        </div>
      </Card>

      {/* Summary */}
      {comp?.summary && (
        <Card delay={400} style={{ gridColumn: "1 / -1" }}>
          <Label>Résumé Technique</Label>
          <div style={{ display: "grid", gridTemplateColumns: "repeat(4, 1fr)", gap: 12, marginTop: 8 }}>
            <div>
              <div style={{ fontSize: 10, color: T.muted }}>Opinion</div>
              <div style={{ fontSize: 13, fontWeight: 600, marginTop: 2 }}>{comp.summary.opinion}</div>
            </div>
            <div>
              <div style={{ fontSize: 10, color: T.muted }}>Tendance CT</div>
              <div style={{ fontSize: 13, fontWeight: 600, marginTop: 2, color: comp.summary.trend_short?.includes("haussière") ? T.green : T.red }}>{comp.summary.trend_short}</div>
            </div>
            <div>
              <div style={{ fontSize: 10, color: T.muted }}>Tendance LT</div>
              <div style={{ fontSize: 13, fontWeight: 600, marginTop: 2, color: comp.summary.trend_long?.includes("haussière") ? T.green : T.red }}>{comp.summary.trend_long}</div>
            </div>
            <div>
              <div style={{ fontSize: 10, color: T.muted }}>Score Technique</div>
              <div style={{ fontSize: 13, fontWeight: 600, marginTop: 2, fontFamily: T.mono }}>{comp.summary.score_technical}</div>
            </div>
          </div>
        </Card>
      )}
    </div>
  );
}
