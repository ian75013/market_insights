import { useState, useMemo, useCallback, useEffect } from "react";
import { ComposedChart, XAxis, YAxis, Tooltip, ResponsiveContainer, Bar, Cell, Line, ReferenceLine } from "recharts";
import { T } from "../styles/theme";
import { Card, Label, Tag } from "./ui";
import { getCandlestick, runEtl } from "../services/api";

const SEV = { bullish: T.green, bearish: T.red, neutral: T.amber };

const POPULAR = [
  { label: "AAPL", desc: "Apple" },
  { label: "MSFT", desc: "Microsoft" },
  { label: "NVDA", desc: "Nvidia" },
  { label: "GOOGL", desc: "Alphabet" },
  { label: "AMZN", desc: "Amazon" },
  { label: "TSLA", desc: "Tesla" },
  { label: "META", desc: "Meta" },
  { label: "JPM", desc: "JPMorgan" },
  { label: "BTC-USD", desc: "Bitcoin" },
  { label: "EURUSD=X", desc: "EUR/USD" },
];

const PROVIDERS = [
  { value: "yahoo", label: "Yahoo Finance" },
  { value: "sample", label: "Sample (offline)" },
  { value: "stooq", label: "Stooq" },
  { value: "alpha_vantage", label: "Alpha Vantage" },
  { value: "auto", label: "Auto (meilleur dispo)" },
];

/* ── Candle shape ────────────────────────────────────────────────── */
function CandleShape({ x, y, width, height, payload }) {
  if (!payload || !height) return null;
  const { open, high, low, close } = payload;
  const isUp = close >= open;
  const color = isUp ? T.green : T.red;
  const barW = Math.max(width * 0.65, 2);
  const cx = x + width / 2;
  const range = Math.max(high - low, 0.001);
  const bodyTop = y + height * ((high - Math.max(open, close)) / range);
  const bodyBot = y + height * ((high - Math.min(open, close)) / range);
  const bodyH = Math.max(bodyBot - bodyTop, 0.5);
  const hasSignal = payload.signals?.length > 0;
  const sigColor = hasSignal ? (SEV[payload.signals[0]?.severity] || T.amber) : null;

  return (
    <g>
      <line x1={cx} x2={cx} y1={y} y2={y + height} stroke={color + "88"} strokeWidth={0.8} />
      <rect x={cx - barW / 2} width={barW} y={bodyTop} height={bodyH}
        fill={isUp ? T.bg : color} stroke={color} strokeWidth={0.8} rx={0.5} />
      {hasSignal && (
        <polygon points={`${cx},${y - 8} ${cx - 3},${y - 3} ${cx + 3},${y - 3}`}
          fill={sigColor} fillOpacity={0.85} />
      )}
    </g>
  );
}

/* ── Tooltip ──────────────────────────────────────────────────────── */
function CandleTooltip({ active, payload }) {
  if (!active || !payload?.[0]) return null;
  const d = payload[0].payload;
  const isUp = d.close >= d.open;
  const chg = d.close && d.open ? ((d.close - d.open) / d.open * 100).toFixed(2) : "0.00";
  return (
    <div style={{ background: T.panel2 + "f0", border: `1px solid ${T.border}`, borderRadius: 8,
      padding: "10px 14px", fontSize: 11, fontFamily: T.mono, minWidth: 180, backdropFilter: "blur(8px)" }}>
      <div style={{ color: T.muted, marginBottom: 6, fontSize: 10 }}>{fmtDate(d.date)}</div>
      <div style={{ display: "grid", gridTemplateColumns: "auto 1fr", gap: "2px 14px" }}>
        <span style={{ color: T.muted }}>O</span><span>{d.open}</span>
        <span style={{ color: T.muted }}>H</span><span style={{ color: T.green }}>{d.high}</span>
        <span style={{ color: T.muted }}>L</span><span style={{ color: T.red }}>{d.low}</span>
        <span style={{ color: T.muted }}>C</span>
        <span style={{ color: isUp ? T.green : T.red, fontWeight: 700 }}>{d.close} ({chg}%)</span>
        <span style={{ color: T.muted }}>Vol</span><span>{d.volume >= 1e6 ? (d.volume / 1e6).toFixed(2) + "M" : (d.volume / 1e3).toFixed(0) + "K"}</span>
        {d.rsi_14 != null && <><span style={{ color: T.muted }}>RSI</span><span>{d.rsi_14}</span></>}
      </div>
      {d.signals?.length > 0 && (
        <div style={{ marginTop: 8, borderTop: `1px solid ${T.border}`, paddingTop: 6 }}>
          {d.signals.map((s, i) => (
            <div key={i} style={{ display: "flex", alignItems: "center", gap: 5, marginTop: 2 }}>
              <span style={{ width: 5, height: 5, borderRadius: "50%", background: SEV[s.severity] || T.amber, flexShrink: 0 }} />
              <span style={{ fontSize: 10 }}>{s.label}</span>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

function fmtDate(d) {
  if (!d) return "";
  const short = d.slice(0, 10);
  const parts = short.split("-");
  return parts.length >= 3 ? `${parts[2]}/${parts[1]}` : short.slice(5);
}

/* ── Main component ──────────────────────────────────────────────── */
export function CandlestickTab({ data: parentData, ticker: parentTicker }) {
  const [customTicker, setCustomTicker] = useState("");
  const [provider, setProvider] = useState("yahoo");
  const [chartData, setChartData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [activeTicker, setActiveTicker] = useState("");
  const [filter, setFilter] = useState("all");

  // Use parent data if no custom chart loaded
  const cs = chartData || parentData?.candlestick;
  const comp = parentData?.comparable || parentData?.insight?.comparable;

  // Load a chart: ETL + fetch candlestick
  const loadChart = useCallback(async (ticker, prov) => {
    if (!ticker) return;
    const t = ticker.trim().toUpperCase();
    setLoading(true);
    setError(null);
    setActiveTicker(t);
    try {
      await runEtl(t, prov);
      const result = await getCandlestick(t);
      setChartData(result);
    } catch (err) {
      setError(err.message);
      setChartData(null);
    } finally {
      setLoading(false);
    }
  }, []);

  const handleSubmit = (e) => {
    e?.preventDefault();
    loadChart(customTicker || parentTicker, provider);
  };

  const handleQuickPick = (t) => {
    setCustomTicker(t);
    loadChart(t, provider);
  };

  // Chart data preparation
  const bars = cs?.bars || [];
  const levels = comp?.levels || {};
  const summary = cs?.signal_summary || {};

  const preparedData = useMemo(() =>
    bars.map(b => ({ ...b, range: [b.low, b.high] })),
    [bars]
  );

  const [yMin, yMax] = useMemo(() => {
    if (!bars.length) return [0, 100];
    const lows = bars.map(b => b.low).filter(Boolean);
    const highs = bars.map(b => b.high).filter(Boolean);
    const lo = Math.min(...lows);
    const hi = Math.max(...highs);
    const pad = (hi - lo) * 0.04;
    return [+(lo - pad).toFixed(2), +(hi + pad).toFixed(2)];
  }, [bars]);

  const allSignals = useMemo(() => {
    const out = [];
    bars.forEach(b => b.signals?.forEach(s => out.push({ ...s, date: b.date, close: b.close })));
    return out;
  }, [bars]);

  const filteredSignals = useMemo(() => {
    if (filter === "all") return allSignals;
    return allSignals.filter(s => s.severity === filter);
  }, [allSignals, filter]);

  const typeCounts = useMemo(() => {
    const counts = {};
    filteredSignals.forEach(s => { counts[s.type] = (counts[s.type] || 0) + 1; });
    return Object.entries(counts).sort((a, b) => b[1] - a[1]);
  }, [filteredSignals]);

  const displayTicker = cs?.ticker || activeTicker || parentTicker || "—";

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 14 }}>

      {/* ── Barre de saisie ───────────────────────────────────── */}
      <Card delay={0}>
        <div style={{ display: "flex", alignItems: "center", gap: 10, flexWrap: "wrap" }}>
          <Label>Charger un graphique</Label>
          <form onSubmit={handleSubmit} style={{ display: "flex", gap: 6, flex: 1, minWidth: 200 }}>
            <input
              value={customTicker}
              onChange={e => setCustomTicker(e.target.value.toUpperCase())}
              placeholder="Ticker (AAPL, TSLA, BTC-USD...)"
              style={{
                flex: 1, padding: "7px 12px", borderRadius: 6, border: `1px solid ${T.border}`,
                background: T.panel2, color: T.text, fontSize: 13, fontFamily: T.mono,
                outline: "none", minWidth: 120,
              }}
            />
            <select value={provider} onChange={e => setProvider(e.target.value)} style={{
              padding: "7px 10px", borderRadius: 6, border: `1px solid ${T.border}`,
              background: T.panel2, color: T.text, fontSize: 11,
            }}>
              {PROVIDERS.map(p => <option key={p.value} value={p.value}>{p.label}</option>)}
            </select>
            <button type="submit" disabled={loading} style={{
              padding: "7px 18px", borderRadius: 6, border: "none",
              background: loading ? T.panel2 : "linear-gradient(135deg, #1d4ed8, #0891b2)",
              color: "#fff", fontSize: 12, fontWeight: 700, cursor: loading ? "wait" : "pointer",
              whiteSpace: "nowrap",
            }}>{loading ? "Chargement…" : "Charger"}</button>
          </form>
        </div>

        {/* Quick picks */}
        <div style={{ display: "flex", gap: 4, marginTop: 10, flexWrap: "wrap" }}>
          {POPULAR.map(p => (
            <button key={p.label} onClick={() => handleQuickPick(p.label)} disabled={loading}
              style={{
                padding: "4px 10px", borderRadius: 5, fontSize: 10, fontWeight: 600,
                background: activeTicker === p.label ? T.accent + "22" : T.panel2,
                color: activeTicker === p.label ? T.accent : T.muted,
                border: `1px solid ${activeTicker === p.label ? T.accent + "55" : T.border}`,
                cursor: loading ? "wait" : "pointer",
              }}>
              {p.label} <span style={{ color: T.muted, fontWeight: 400 }}>{p.desc}</span>
            </button>
          ))}
        </div>

        {error && <div style={{ marginTop: 8, fontSize: 11, color: T.red }}>⚠ {error}</div>}
      </Card>

      {/* ── Chart + sidebar ───────────────────────────────────── */}
      {bars.length > 0 ? (
        <div style={{ display: "grid", gridTemplateColumns: "1fr 260px", gap: 14 }}>
          {/* Left */}
          <div style={{ display: "flex", flexDirection: "column", gap: 14 }}>
            <Card delay={50}>
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 8 }}>
                <span style={{ fontSize: 12, fontWeight: 600 }}>
                  {displayTicker} — {bars.length} séances
                  {bars.length > 0 && <span style={{ color: T.muted, fontWeight: 400, marginLeft: 8, fontSize: 10 }}>
                    {fmtDate(bars[0].date)} → {fmtDate(bars[bars.length - 1].date)}
                  </span>}
                </span>
                <div style={{ display: "flex", gap: 10, fontSize: 10, fontFamily: T.mono }}>
                  <span style={{ color: T.green }}>▲ Bull</span>
                  <span style={{ color: T.red }}>▲ Bear</span>
                  <span style={{ color: "#f5a623" }}>┄ SMA20</span>
                  <span style={{ color: "#ff4d6a88" }}>┄ SMA50</span>
                </div>
              </div>

              <ResponsiveContainer width="100%" height={400}>
                <ComposedChart data={preparedData} margin={{ top: 20, right: 10, bottom: 0, left: 0 }}>
                  <XAxis dataKey="date" tickFormatter={fmtDate}
                    tick={{ fontSize: 9, fill: T.muted, fontFamily: T.mono }}
                    interval={Math.max(1, Math.floor(preparedData.length / 12))}
                    axisLine={{ stroke: T.border }} tickLine={false} />
                  <YAxis domain={[yMin, yMax]}
                    tick={{ fontSize: 9, fill: T.muted, fontFamily: T.mono }}
                    axisLine={false} tickLine={false} width={52} />
                  <Tooltip content={<CandleTooltip />} />

                  <Bar dataKey="range" barSize={Math.min(8, Math.max(3, 600 / preparedData.length))} shape={<CandleShape />}>
                    {preparedData.map((_, i) => <Cell key={i} />)}
                  </Bar>
                  <Line type="monotone" dataKey="sma_20" stroke="#f5a623aa" strokeWidth={1.2} dot={false} strokeDasharray="4 2" />
                  <Line type="monotone" dataKey="sma_50" stroke="#ff4d6a77" strokeWidth={1.2} dot={false} strokeDasharray="6 3" />

                  {levels.support && <ReferenceLine y={levels.support} stroke={T.green + "66"} strokeDasharray="3 3" strokeWidth={0.7}
                    label={{ value: `S ${levels.support}`, position: "left", fill: T.green, fontSize: 9, fontFamily: T.mono }} />}
                  {levels.resistance && <ReferenceLine y={levels.resistance} stroke={T.red + "66"} strokeDasharray="3 3" strokeWidth={0.7}
                    label={{ value: `R ${levels.resistance}`, position: "left", fill: T.red, fontSize: 9, fontFamily: T.mono }} />}
                </ComposedChart>
              </ResponsiveContainer>

              <ResponsiveContainer width="100%" height={45}>
                <ComposedChart data={preparedData} margin={{ top: 0, right: 10, bottom: 0, left: 0 }}>
                  <XAxis dataKey="date" hide /><YAxis hide />
                  <Bar dataKey="volume" barSize={Math.min(6, Math.max(2, 600 / preparedData.length))} radius={[1, 1, 0, 0]}>
                    {preparedData.map((e, i) => <Cell key={i} fill={e.close >= e.open ? T.green + "33" : T.red + "33"} />)}
                  </Bar>
                </ComposedChart>
              </ResponsiveContainer>
            </Card>

            {/* Signal timeline */}
            {filteredSignals.length > 0 && (
              <Card delay={150}>
                <Label>Signaux ({filteredSignals.length})</Label>
                <div style={{ maxHeight: 220, overflowY: "auto", display: "flex", flexDirection: "column", gap: 3, marginTop: 6 }}>
                  {filteredSignals.slice().reverse().map((s, i) => (
                    <div key={i} style={{
                      display: "flex", alignItems: "center", gap: 8,
                      padding: "4px 10px", background: T.panel2, borderRadius: 5,
                      borderLeft: `3px solid ${SEV[s.severity] || T.muted}`, fontSize: 11,
                    }}>
                      <span style={{ color: T.muted, fontFamily: T.mono, minWidth: 44, fontSize: 10 }}>{fmtDate(s.date)}</span>
                      <span style={{ flex: 1 }}>{s.label}</span>
                      <span style={{ fontFamily: T.mono, fontSize: 10, color: T.muted }}>{s.close}</span>
                    </div>
                  ))}
                </div>
              </Card>
            )}
          </div>

          {/* Right sidebar */}
          <div style={{ display: "flex", flexDirection: "column", gap: 14 }}>
            <Card delay={80}>
              <Label>Résumé</Label>
              <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr 1fr", gap: 5, marginTop: 6 }}>
                {[
                  { l: "Bull", v: summary.bullish || 0, c: T.green },
                  { l: "Bear", v: summary.bearish || 0, c: T.red },
                  { l: "Neutre", v: summary.neutral || 0, c: T.amber },
                ].map((s, i) => (
                  <div key={i} style={{ textAlign: "center", padding: "7px 3px", borderRadius: 6, background: s.c + "10", border: `1px solid ${s.c}20` }}>
                    <div style={{ fontFamily: T.mono, fontSize: 18, fontWeight: 700, color: s.c }}>{s.v}</div>
                    <div style={{ fontSize: 9, color: T.muted }}>{s.l}</div>
                  </div>
                ))}
              </div>
            </Card>

            <Card delay={110}>
              <Label>Filtre</Label>
              <div style={{ display: "flex", gap: 4, marginTop: 6, flexWrap: "wrap" }}>
                {["all", "bullish", "bearish", "neutral"].map(f => (
                  <button key={f} onClick={() => setFilter(f)} style={{
                    padding: "4px 9px", borderRadius: 5, fontSize: 10, fontWeight: 600,
                    background: filter === f ? (f === "all" ? T.accent : SEV[f]) + "22" : "transparent",
                    color: filter === f ? (f === "all" ? T.accent : SEV[f]) : T.muted,
                    border: `1px solid ${filter === f ? (f === "all" ? T.accent : SEV[f]) + "55" : T.border}`,
                    cursor: "pointer",
                  }}>{f === "all" ? "Tous" : f.charAt(0).toUpperCase() + f.slice(1)}</button>
                ))}
              </div>
            </Card>

            <Card delay={140}>
              <Label>Patterns</Label>
              <div style={{ display: "flex", flexDirection: "column", gap: 3, marginTop: 6 }}>
                {typeCounts.length === 0 && <div style={{ fontSize: 11, color: T.muted, padding: 6 }}>Aucun signal</div>}
                {typeCounts.map(([type, count], i) => (
                  <div key={i} style={{ display: "flex", justifyContent: "space-between", alignItems: "center", padding: "3px 8px", background: T.panel2, borderRadius: 4 }}>
                    <span style={{ fontSize: 10 }}>{type.replace(/_/g, " ")}</span>
                    <span style={{ fontFamily: T.mono, fontSize: 11, fontWeight: 600, color: T.accent }}>{count}</span>
                  </div>
                ))}
              </div>
            </Card>

            {levels.support && (
              <Card delay={170}>
                <Label>Niveaux</Label>
                <div style={{ display: "flex", flexDirection: "column", gap: 3, marginTop: 6 }}>
                  {[
                    { l: "Objectif 2", v: levels.target_2, c: T.accent },
                    { l: "Résistance", v: levels.resistance, c: T.red },
                    { l: "Pivot", v: levels.pivot, c: T.text },
                    { l: "Support", v: levels.support, c: T.green },
                  ].filter(x => x.v).map((lv, i) => (
                    <div key={i} style={{ display: "flex", justifyContent: "space-between", padding: "3px 8px", background: T.panel2, borderRadius: 4 }}>
                      <span style={{ fontSize: 10, color: T.muted }}>{lv.l}</span>
                      <span style={{ fontFamily: T.mono, fontSize: 11, fontWeight: 600, color: lv.c }}>{Number(lv.v).toFixed(2)}</span>
                    </div>
                  ))}
                </div>
              </Card>
            )}

            <Card delay={200}>
              <Label>Légende</Label>
              <div style={{ fontSize: 10, color: T.muted, lineHeight: 1.7, marginTop: 4 }}>
                <div><span style={{ color: T.green }}>▲</span> Haussier (gap up, breakout, marteau, golden cross)</div>
                <div><span style={{ color: T.red }}>▲</span> Baissier (gap down, breakdown, étoile filante, death cross)</div>
                <div><span style={{ color: T.amber }}>▲</span> Neutre (pullback, doji, volume spike)</div>
              </div>
            </Card>
          </div>
        </div>
      ) : !loading && (
        <Card>
          <div style={{ textAlign: "center", padding: 40, color: T.muted }}>
            <div style={{ fontSize: 14, marginBottom: 8 }}>Saisissez un ticker et cliquez Charger</div>
            <div style={{ fontSize: 12 }}>Les données seront récupérées via {provider === "yahoo" ? "Yahoo Finance" : provider} puis affichées en chandeliers annotés.</div>
          </div>
        </Card>
      )}
    </div>
  );
}
