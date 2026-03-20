import { T } from "../styles/theme";
import { Card, Label, Tag } from "./ui";

export function NewsTab({ data, macro }) {
  const news = data?.news;
  const items = news?.items || [];

  /* Compute aggregate sentiment if available */
  const sentiments = items.filter((n) => n.sentiment_score != null).map((n) => n.sentiment_score);
  const avgSentiment = sentiments.length > 0
    ? sentiments.reduce((a, b) => a + b, 0) / sentiments.length
    : null;

  return (
    <div style={{ display: "grid", gridTemplateColumns: "1fr 300px", gap: 14 }}>
      {/* ── News feed ───────────────────────────────────────── */}
      <Card delay={0}>
        <Label>
          News Feed — {news?.ticker || "…"} ({items.length} articles)
        </Label>
        {items.length === 0 ? (
          <div style={{ padding: 30, textAlign: "center", color: T.muted, fontSize: 13 }}>
            Aucune news disponible. Activez <code>USE_NETWORK=true</code> et configurez Alpha Vantage pour du sentiment live.
          </div>
        ) : (
          <div style={{ display: "flex", flexDirection: "column", gap: 8, marginTop: 10 }}>
            {items.map((n, i) => {
              const s = n.sentiment_score;
              const borderColor = s != null ? (s > 0.15 ? T.green : s < -0.1 ? T.red : T.amber) : T.accent + "44";
              return (
                <div
                  key={i}
                  className="fade-up"
                  style={{
                    animationDelay: `${i * 60}ms`,
                    padding: "12px 14px",
                    background: T.panel2,
                    borderRadius: 8,
                    borderLeft: `3px solid ${borderColor}`,
                  }}
                >
                  <div style={{ fontSize: 13, fontWeight: 600, lineHeight: 1.4, marginBottom: 4 }}>
                    {n.title}
                  </div>
                  {n.content && (
                    <div style={{ fontSize: 11, color: T.muted, lineHeight: 1.5, marginBottom: 6 }}>
                      {n.content.slice(0, 200)}{n.content.length > 200 ? "…" : ""}
                    </div>
                  )}
                  <div style={{ display: "flex", gap: 8, alignItems: "center", fontSize: 10 }}>
                    <span style={{ color: T.muted }}>{n.published_at}</span>
                    {n.source && <Tag color={T.muted}>{n.source}</Tag>}
                    {s != null && (
                      <Tag color={s > 0.15 ? T.green : s < -0.1 ? T.red : T.amber}>
                        Sentiment: {s > 0 ? "+" : ""}{s.toFixed(3)}
                      </Tag>
                    )}
                    {n.sentiment_label && (
                      <Tag color={T.muted}>{n.sentiment_label}</Tag>
                    )}
                  </div>
                  {n.link && (
                    <a
                      href={n.link}
                      target="_blank"
                      rel="noopener noreferrer"
                      style={{ fontSize: 10, color: T.accent, textDecoration: "none", marginTop: 4, display: "inline-block" }}
                    >
                      Lire l'article →
                    </a>
                  )}
                </div>
              );
            })}
          </div>
        )}
      </Card>

      {/* ── Sidebar ─────────────────────────────────────────── */}
      <div style={{ display: "flex", flexDirection: "column", gap: 14 }}>
        {/* Aggregate sentiment */}
        {avgSentiment != null && (
          <Card delay={100}>
            <Label>Sentiment Agrégé</Label>
            <div style={{ marginTop: 8 }}>
              {(() => {
                const c = avgSentiment > 0.1 ? T.green : avgSentiment < -0.1 ? T.red : T.amber;
                return (
                  <div style={{
                    textAlign: "center", padding: 16, borderRadius: 8,
                    background: c + "12", border: `1px solid ${c}30`,
                  }}>
                    <div style={{ fontFamily: T.mono, fontSize: 28, fontWeight: 700, color: c }}>
                      {avgSentiment > 0 ? "+" : ""}{avgSentiment.toFixed(3)}
                    </div>
                    <div style={{ fontSize: 10, color: T.muted, marginTop: 4 }}>
                      {avgSentiment > 0.15 ? "Positif" : avgSentiment < -0.1 ? "Négatif" : "Neutre"} ({sentiments.length} scored)
                    </div>
                  </div>
                );
              })()}
            </div>
          </Card>
        )}

        {/* Providers */}
        <Card delay={200}>
          <Label>Providers News</Label>
          <div style={{ display: "flex", flexDirection: "column", gap: 5, marginTop: 8, fontSize: 11 }}>
            {[
              { n: "Alpha Vantage Sentiment", desc: "Nécessite ALPHA_VANTAGE_API_KEY" },
              { n: "Google News RSS", desc: "Gratuit, pas de clé" },
              { n: "Sample data", desc: "Fallback offline" },
            ].map((p, i) => (
              <div key={i} style={{ padding: "5px 8px", background: T.panel2, borderRadius: 4 }}>
                <div style={{ fontWeight: 600 }}>{p.n}</div>
                <div style={{ fontSize: 9, color: T.muted }}>{p.desc}</div>
              </div>
            ))}
          </div>
        </Card>

        {/* Macro context */}
        {macro?.data && (
          <Card delay={300}>
            <Label>Contexte Macro</Label>
            <div style={{ display: "flex", flexDirection: "column", gap: 4, marginTop: 6, fontSize: 11, fontFamily: T.mono }}>
              {Object.entries(flattenMacro(macro.data)).map(([k, v]) => (
                <div key={k} style={{ display: "flex", justifyContent: "space-between", padding: "3px 6px" }}>
                  <span style={{ color: T.muted }}>{k}</span>
                  <span style={{ fontWeight: 600 }}>{typeof v === "number" ? v.toFixed(2) : v}</span>
                </div>
              ))}
            </div>
            <div style={{ marginTop: 6, fontSize: 9, color: T.muted }}>
              Source: {macro.source === "fred" ? "FRED (live)" : "Sample data"}
            </div>
          </Card>
        )}
      </div>
    </div>
  );
}

/** Flatten nested macro structure into key-value for display */
function flattenMacro(data) {
  const result = {};
  if (typeof data.fed_funds === "number") {
    /* Already flat (FRED style) */
    return data;
  }
  /* Nested sample style */
  for (const [section, vals] of Object.entries(data)) {
    if (typeof vals === "object" && vals !== null) {
      for (const [k, v] of Object.entries(vals)) {
        result[k] = v;
      }
    }
  }
  return result;
}
