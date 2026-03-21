import { Card, Label, Num, Tag, VerdictBadge, GaugeBar } from "./ui";
import { sevTagClass } from "../styles/theme";

export function OverviewTab({ data }) {
  const h = data?.hybrid;
  const fv = data?.fairValue;
  const comp = data?.comparable || h?.comparable;
  const ins = data?.insight;
  const src = data?.sources;
  const news = data?.news;
  if (!h) return <Card><div className="empty-state"><h3>Aucune donnée</h3><p>Lancez l'ETL puis rechargez.</p></div></Card>;

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
    <div className="grid-sidebar">
      <div className="flex-col">
        {/* KPIs */}
        <div className="grid-4">
          {[
            { l: "Juste Valeur", v: `$${fairVal.toFixed(2)}`, cls: upside > 0 ? "text-green" : "text-red" },
            { l: "Upside Modèle", v: `${upside > 0 ? "+" : ""}${upside.toFixed(2)}%`, cls: upside > 0 ? "text-green" : "text-red" },
            { l: "Score Global", v: score.toFixed(2), cls: score >= 0.6 ? "text-green" : score >= 0.45 ? "text-amber" : "text-red" },
            { l: "RSI 14", v: rsi.toFixed(1), cls: rsi > 70 ? "text-red" : rsi < 30 ? "text-green" : "" },
          ].map((k, i) => (
            <Card key={i} delay={60 + i * 50}><Label>{k.l}</Label><Num v={k.v} className={k.cls} size="md" /></Card>
          ))}
        </div>

        {/* Summary */}
        <Card delay={300}>
          <div className="card-header"><span className="text-base fw-600">Résumé Exécutif</span><VerdictBadge verdict={verdict} /></div>
          <p className="text-base muted lh-relaxed">{h.executive_summary || "Analyse en cours…"}</p>
        </Card>

        {comp?.narrative && (
          <Card delay={400}><Label>Narrative Technique</Label><p className="text-sm muted lh-relaxed">{comp.narrative}</p></Card>
        )}

        {src?.sources?.length > 0 && (
          <Card delay={500}>
            <Label>Sources RAG ({src.sources.length})</Label>
            <div className="flex-col gap-xs">
              {src.sources.slice(0, 5).map((s, i) => (
                <div key={i} className="source-item">
                  <div className="text-sm fw-600">{s.title || s.source || "Source"}</div>
                  <div className="text-xs muted">{s.document_type} · score: {s.score}</div>
                </div>
              ))}
            </div>
          </Card>
        )}
      </div>

      {/* Sidebar */}
      <div className="flex-col">
        <Card delay={80}>
          <Label>Modèle Fair Value</Label>
          <GaugeBar value={confidence} label="Confiance" colorClass="text-accent" />
          <GaugeBar value={ins?.scores?.trend_score || 0.5} label="Score Tendance" colorClass={ins?.technicals?.trend_signal ? "text-green" : "text-red"} />
          <GaugeBar value={score} label="Score Global" colorClass={score >= 0.6 ? "text-green" : "text-amber"} />
          <div className="text-xs muted">{fv?.method || "baseline multifactoriel"}</div>
        </Card>

        <Card delay={160}>
          <Label>Niveaux Techniques</Label>
          <div className="grid-2 gap-sm">
            {[
              { l: "Support", v: levels.support, c: "text-green" }, { l: "Résistance", v: levels.resistance, c: "text-red" },
              { l: "Pivot", v: levels.pivot, c: "" }, { l: "Objectif 2", v: levels.target_2, c: "text-accent" },
            ].map((lv, i) => (
              <div key={i} className="metric-box">
                <div className="m-label">{lv.l}</div>
                <div className={`m-value mono ${lv.c}`}>{lv.v != null ? Number(lv.v).toFixed(2) : "—"}</div>
              </div>
            ))}
          </div>
        </Card>

        <Card delay={240}>
          <Label>Signaux Détectés</Label>
          <div className="flex-row gap-xs" style={{ flexWrap: "wrap", marginTop: 6 }}>
            {(signals.patterns || []).map((s, i) => <Tag key={`p${i}`} variant={s.includes("haussier") || s.includes("plus haut") ? "green" : s.includes("baissier") ? "red" : "amber"}>{s}</Tag>)}
            {(signals.candles || []).map((s, i) => <Tag key={`c${i}`} variant={s.includes("haussier") ? "green" : s.includes("baissier") ? "red" : "amber"}>{s}</Tag>)}
            {!(signals.patterns?.length || signals.candles?.length) && <Tag variant="muted">Aucun signal majeur</Tag>}
          </div>
        </Card>

        {h.rag && (<>
          <Card delay={320}><Label>Catalyseurs</Label><div className="flex-col gap-xs">
            {(h.rag.top_catalysts || []).map((c, i) => <div key={i} className="signal-item bull text-sm">{c}</div>)}
          </div></Card>
          <Card delay={400}><Label>Risques</Label><div className="flex-col gap-xs">
            {(h.rag.top_risks || []).map((r, i) => <div key={i} className="signal-item bear text-sm">{r}</div>)}
          </div></Card>
        </>)}

        {news?.items?.length > 0 && (
          <Card delay={480}><Label>Dernières News</Label><div className="flex-col gap-xs">
            {news.items.slice(0, 3).map((n, i) => (
              <div key={i} className="source-item"><div className="text-sm">{n.title}</div><div className="text-xs muted">{n.published_at}</div></div>
            ))}
          </div></Card>
        )}
      </div>
    </div>
  );
}
