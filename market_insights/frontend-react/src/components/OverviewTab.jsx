import { T, chgColor } from "../styles/theme";
import { Card, Label, Num, Tag, VerdictBadge, GaugeBar } from "./ui";
import { PriceChart, VolumeChart } from "./Charts";

/**
 * Extract price series suitable for charting from the insight response.
 * The API doesn't return a price array directly on /hybrid,
 * so we build a mini-series from the comparable quotes + technicals.
 * When the backend evolves to return full price series, swap this out.
 */
function extractChartData(insight) {
  /* If we have comparable → quotes, that's our best source */
  const comp = insight?.comparable || insight?.technical?.comparable;
  if (comp?.quotes) {
    return null; /* no time series in current API — chart will show placeholder */
  }
  return null;
}

export function OverviewTab({ data }) {
  const h = data?.hybrid;
  const fv = data?.fairValue;
  const comp = data?.comparable || h?.comparable;
  const ins = data?.insight;
  const src = data?.sources;
  const news = data?.news;

  if (!h) return <EmptyState />;

  const price = h.hybrid?.current_price || fv?.current_price || 0;
  const fairVal = h.fair_value?.fair_value || fv?.fair_value || 0;
  const upside = h.hybrid?.upside_pct || fv?.upside_pct || 0;
  const confidence = h.hybrid?.confidence || fv?.confidence || 0;
  const verdict = h.verdict || "neutral";
  const score = ins?.score || 0;
  const rsi = ins?.technicals?.rsi_14 || 50;
  const levels = comp?.levels || {};
  const signals = comp?.signals || {};

  return (
    <div style={{ display: "grid", gridTemplateColumns: "1fr 320px", gap: 14 }}>
      {/* ── Left column ──────────────────────────────────────── */}
      <div style={{ display: "flex", flexDirection: "column", gap: 14 }}>
        {/* KPI row */}
        <div style={{ display: "grid", gridTemplateColumns: "repeat(4, 1fr)", gap: 10 }}>
          {[
            { l: "Juste Valeur", v: `$${fairVal.toFixed(2)}`, c: upside > 0 ? T.green : T.red },
            { l: "Upside Modèle", v: `${upside > 0 ? "+" : ""}${upside.toFixed(2)}%`, c: upside > 0 ? T.green : T.red },
            { l: "Score Global", v: score.toFixed(2), c: score >= 0.6 ? T.green : score >= 0.45 ? T.amber : T.red },
            { l: "RSI 14", v: rsi.toFixed(1), c: rsi > 70 ? T.red : rsi < 30 ? T.green : T.text },
          ].map((k, i) => (
            <Card key={i} delay={60 + i * 50}>
              <Label>{k.l}</Label>
              <Num v={k.v} color={k.c} size={20} />
            </Card>
          ))}
        </div>

        {/* Executive summary */}
        <Card delay={300}>
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 8 }}>
            <span style={{ fontSize: 12, fontWeight: 600 }}>Résumé Exécutif</span>
            <VerdictBadge verdict={verdict} />
          </div>
          <p style={{ fontSize: 13, lineHeight: 1.65, color: T.muted }}>
            {h.executive_summary || "Analyse en cours de chargement…"}
          </p>
        </Card>

        {/* Technical narrative */}
        {comp?.narrative && (
          <Card delay={400}>
            <Label>Narrative Technique</Label>
            <p style={{ fontSize: 12, lineHeight: 1.6, color: T.muted, marginTop: 6 }}>
              {comp.narrative}
            </p>
          </Card>
        )}

        {/* RAG sources */}
        {src?.sources?.length > 0 && (
          <Card delay={500}>
            <Label>Sources RAG ({src.sources.length})</Label>
            <div style={{ display: "flex", flexDirection: "column", gap: 6, marginTop: 6 }}>
              {src.sources.slice(0, 5).map((s, i) => (
                <div
                  key={i}
                  style={{
                    padding: "8px 10px",
                    background: T.panel2,
                    borderRadius: 6,
                    borderLeft: `2px solid ${T.accent}44`,
                  }}
                >
                  <div style={{ fontSize: 11, fontWeight: 600 }}>{s.title || s.source || "Source"}</div>
                  <div style={{ fontSize: 10, color: T.muted, marginTop: 2 }}>
                    {s.document_type} · score: {s.score}
                  </div>
                </div>
              ))}
            </div>
          </Card>
        )}
      </div>

      {/* ── Right sidebar ────────────────────────────────────── */}
      <div style={{ display: "flex", flexDirection: "column", gap: 14 }}>
        {/* Fair value model */}
        <Card delay={80}>
          <Label>Modèle Fair Value</Label>
          <div style={{ marginTop: 6 }}>
            <GaugeBar value={confidence} label="Confiance" color={T.accent} />
            <GaugeBar
              value={ins?.scores?.trend_score || 0.5}
              label="Score Tendance"
              color={ins?.technicals?.trend_signal ? T.green : T.red}
            />
            <GaugeBar
              value={score}
              label="Score Global"
              color={score >= 0.6 ? T.green : T.amber}
            />
          </div>
          <div style={{ marginTop: 8, fontSize: 10, color: T.muted }}>
            Méthode : {fv?.method || "baseline multifactoriel"}
          </div>
        </Card>

        {/* Technical levels */}
        <Card delay={160}>
          <Label>Niveaux Techniques</Label>
          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 8, marginTop: 8 }}>
            {[
              { l: "Support", v: levels.support, c: T.green },
              { l: "Résistance", v: levels.resistance, c: T.red },
              { l: "Pivot", v: levels.pivot, c: T.text },
              { l: "Objectif 2", v: levels.target_2, c: T.accent },
            ].map((lv, i) => (
              <div
                key={i}
                style={{
                  padding: "8px 10px",
                  background: T.panel2,
                  borderRadius: 6,
                  border: `1px solid ${T.border}`,
                }}
              >
                <div style={{ fontSize: 9, color: T.muted, marginBottom: 2 }}>{lv.l}</div>
                <div style={{ fontFamily: T.mono, fontSize: 14, fontWeight: 600, color: lv.c }}>
                  {lv.v != null ? Number(lv.v).toFixed(2) : "—"}
                </div>
              </div>
            ))}
          </div>
        </Card>

        {/* Signals */}
        <Card delay={240}>
          <Label>Signaux Détectés</Label>
          <div style={{ display: "flex", flexWrap: "wrap", gap: 5, marginTop: 6 }}>
            {(signals.patterns || []).map((s, i) => (
              <Tag key={`p${i}`} color={s.includes("haussier") || s.includes("plus haut") ? T.green : s.includes("baissier") ? T.red : T.amber}>
                {s}
              </Tag>
            ))}
            {(signals.candles || []).map((s, i) => (
              <Tag key={`c${i}`} color={s.includes("haussier") ? T.green : s.includes("baissier") ? T.red : T.amber}>
                {s}
              </Tag>
            ))}
            {(signals.patterns?.length || 0) + (signals.candles?.length || 0) === 0 && (
              <Tag color={T.muted}>Aucun signal majeur</Tag>
            )}
          </div>
        </Card>

        {/* Catalysts & risks */}
        {h.rag && (
          <>
            <Card delay={320}>
              <Label>Catalyseurs</Label>
              <div style={{ display: "flex", flexDirection: "column", gap: 4, marginTop: 4 }}>
                {(h.rag.top_catalysts || []).map((c, i) => (
                  <div key={i} style={{ fontSize: 11, padding: "4px 8px", background: T.green + "10", borderRadius: 4, borderLeft: `2px solid ${T.green}44` }}>
                    {c}
                  </div>
                ))}
              </div>
            </Card>
            <Card delay={400}>
              <Label>Risques</Label>
              <div style={{ display: "flex", flexDirection: "column", gap: 4, marginTop: 4 }}>
                {(h.rag.top_risks || []).map((r, i) => (
                  <div key={i} style={{ fontSize: 11, padding: "4px 8px", background: T.red + "10", borderRadius: 4, borderLeft: `2px solid ${T.red}44` }}>
                    {r}
                  </div>
                ))}
              </div>
            </Card>
          </>
        )}

        {/* News preview */}
        {news?.items?.length > 0 && (
          <Card delay={480}>
            <Label>Dernières News</Label>
            <div style={{ display: "flex", flexDirection: "column", gap: 6, marginTop: 6 }}>
              {news.items.slice(0, 3).map((n, i) => (
                <div
                  key={i}
                  style={{
                    padding: "6px 8px",
                    background: T.panel2,
                    borderRadius: 5,
                    borderLeft: `2px solid ${T.accent}44`,
                  }}
                >
                  <div style={{ fontSize: 11, lineHeight: 1.35 }}>{n.title}</div>
                  <div style={{ fontSize: 9, color: T.muted, marginTop: 2 }}>{n.published_at}</div>
                </div>
              ))}
            </div>
          </Card>
        )}
      </div>
    </div>
  );
}

function EmptyState() {
  return (
    <Card>
      <div style={{ textAlign: "center", padding: 40, color: T.muted }}>
        <div style={{ fontSize: 14, marginBottom: 8 }}>Aucune donnée disponible</div>
        <div style={{ fontSize: 12 }}>Lancez d'abord l'ETL pour ce ticker, puis rechargez l'analyse.</div>
      </div>
    </Card>
  );
}
