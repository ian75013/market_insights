import { Card, Label, Tag } from "./ui";

export function NewsTab({ data, macro }) {
  const news = data?.news;
  const items = news?.items || [];
  const sentiments = items.filter(n => n.sentiment_score != null).map(n => n.sentiment_score);
  const avg = sentiments.length ? sentiments.reduce((a,b) => a+b, 0) / sentiments.length : null;

  return (
    <div className="grid-sidebar-w">
      <Card delay={0}>
        <Label>News Feed — {news?.ticker || "…"} ({items.length} articles)</Label>
        {items.length === 0 ? (
          <div className="empty-state"><p>Aucune news. Activez USE_NETWORK=true et configurez Alpha Vantage pour du sentiment live.</p></div>
        ) : (
          <div className="flex-col gap-sm">
            {items.map((n, i) => {
              const s = n.sentiment_score;
              const cls = s != null ? (s > 0.15 ? "positive" : s < -0.1 ? "negative" : "neutral-s") : "";
              return (
                <div key={i} className={`news-item ${cls} fade-up`} style={{ animationDelay: `${i * 60}ms` }}>
                  <div className="text-base fw-600" style={{ lineHeight: 1.4, marginBottom: 5 }}>{n.title}</div>
                  {n.content && <div className="text-sm muted lh-relaxed" style={{ marginBottom: 8 }}>{n.content.slice(0, 200)}{n.content.length > 200 ? "…" : ""}</div>}
                  <div className="flex-row gap-sm">
                    <span className="text-xs muted">{n.published_at}</span>
                    {n.source && <Tag variant="muted">{n.source}</Tag>}
                    {s != null && <Tag variant={s > 0.15 ? "green" : s < -0.1 ? "red" : "amber"}>Sentiment: {s > 0 ? "+" : ""}{s.toFixed(3)}</Tag>}
                  </div>
                  {n.link && <a href={n.link} target="_blank" rel="noopener noreferrer" className="text-xs text-accent" style={{ marginTop: 4, display: "inline-block", textDecoration: "none" }}>Lire →</a>}
                </div>
              );
            })}
          </div>
        )}
      </Card>

      <div className="flex-col">
        {avg != null && (
          <Card delay={100}><Label>Sentiment Agrégé</Label>
            <div className="metric-box metric-box-center" style={{ background: avg>0.1?"rgba(0,214,126,.06)":avg<-0.1?"rgba(255,77,106,.06)":"rgba(245,166,35,.06)", marginTop: 8 }}>
              <div className={`num num-xl ${avg > 0.1 ? "text-green" : avg < -0.1 ? "text-red" : "text-amber"}`}>{avg > 0 ? "+" : ""}{avg.toFixed(3)}</div>
              <div className="text-xs muted" style={{ marginTop: 4 }}>{avg > 0.15 ? "Positif" : avg < -0.1 ? "Négatif" : "Neutre"} ({sentiments.length} scored)</div>
            </div>
          </Card>
        )}
        <Card delay={200}><Label>Providers News</Label>
          <div className="flex-col gap-xs">
            {[{ n: "Alpha Vantage Sentiment", d: "Nécessite clé API" }, { n: "Google News RSS", d: "Gratuit" }, { n: "Sample data", d: "Fallback offline" }].map((p, i) => (
              <div key={i} className="metric-box"><div className="fw-600 text-sm">{p.n}</div><div className="text-xs muted">{p.d}</div></div>
            ))}
          </div>
        </Card>
        {macro?.data && (
          <Card delay={300}><Label>Contexte Macro</Label>
            <div className="flex-col gap-xs mono text-sm">
              {Object.entries(flattenMacro(macro.data)).map(([k, v]) => (
                <div key={k} className="level-row"><span className="muted">{k}</span><span className="fw-600">{typeof v === "number" ? v.toFixed(2) : v}</span></div>
              ))}
            </div>
            <div className="text-xs muted" style={{ marginTop: 8 }}>Source: {macro.source === "fred" ? "FRED (live)" : "Sample"}</div>
          </Card>
        )}
      </div>
    </div>
  );
}

function flattenMacro(data) {
  if (typeof data.fed_funds === "number") return data;
  const r = {};
  for (const [, vals] of Object.entries(data)) {
    if (typeof vals === "object" && vals) for (const [k, v] of Object.entries(vals)) r[k] = v;
  }
  return r;
}
