import { useState, useMemo, useRef, useEffect } from "react";
import { ComposedChart, XAxis, YAxis, Tooltip, ResponsiveContainer, Bar, Cell, Line, ReferenceLine, ReferenceArea } from "recharts";
import { T } from "../styles/theme";
import { Card, Label, Tag } from "./ui";

/* ── Custom candlestick shape for recharts ───────────────────────── */
function CandleShape({ x, y, width, height, payload }) {
  if (!payload) return null;
  const { open, high, low, close } = payload;
  const isUp = close >= open;
  const color = isUp ? T.green : T.red;
  const bodyTop = Math.min(open, close);
  const bodyBot = Math.max(open, close);
  const hasSignal = payload.signals?.length > 0;

  // scale from data coords to pixel coords
  // recharts passes y/height for the bar, we compute from the low-high range
  const barW = Math.max(width * 0.7, 3);
  const cx = x + width / 2;

  return (
    <g>
      {/* Wick */}
      <line x1={cx} x2={cx} y1={y} y2={y + height} stroke={color} strokeWidth={1} />
      {/* Body */}
      <rect
        x={cx - barW / 2}
        width={barW}
        y={y + height * ((high - bodyBot) / Math.max(high - low, 0.01))}
        height={Math.max(height * (Math.abs(close - open) / Math.max(high - low, 0.01)), 1)}
        fill={isUp ? color : color}
        fillOpacity={isUp ? 0.3 : 0.8}
        stroke={color}
        strokeWidth={0.8}
        rx={1}
      />
      {/* Signal dot */}
      {hasSignal && (
        <circle
          cx={cx}
          cy={y - 6}
          r={3}
          fill={payload.signals[0]?.severity === "bullish" ? T.green : payload.signals[0]?.severity === "bearish" ? T.red : T.amber}
        />
      )}
    </g>
  );
}

/* ── Custom tooltip ──────────────────────────────────────────────── */
function CandleTooltip({ active, payload, label }) {
  if (!active || !payload?.[0]) return null;
  const d = payload[0].payload;
  const isUp = d.close >= d.open;
  return (
    <div style={{
      background: T.panel2, border: `1px solid ${T.border}`, borderRadius: 8,
      padding: "10px 14px", fontSize: 11, fontFamily: T.mono, minWidth: 200,
    }}>
      <div style={{ color: T.muted, marginBottom: 6 }}>{d.date}</div>
      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "3px 16px" }}>
        <span style={{ color: T.muted }}>Open</span><span>{d.open}</span>
        <span style={{ color: T.muted }}>High</span><span>{d.high}</span>
        <span style={{ color: T.muted }}>Low</span><span>{d.low}</span>
        <span style={{ color: T.muted }}>Close</span><span style={{ color: isUp ? T.green : T.red, fontWeight: 600 }}>{d.close}</span>
        <span style={{ color: T.muted }}>Volume</span><span>{(d.volume / 1000).toFixed(0)}K</span>
        {d.rsi_14 && <><span style={{ color: T.muted }}>RSI</span><span>{d.rsi_14}</span></>}
      </div>
      {d.signals?.length > 0 && (
        <div style={{ marginTop: 8, borderTop: `1px solid ${T.border}`, paddingTop: 6 }}>
          {d.signals.map((s, i) => (
            <div key={i} style={{ display: "flex", alignItems: "center", gap: 6, marginBottom: 2 }}>
              <span style={{ width: 6, height: 6, borderRadius: "50%",
                background: s.severity === "bullish" ? T.green : s.severity === "bearish" ? T.red : T.amber
              }} />
              <span style={{ fontSize: 10 }}>{s.label}</span>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

/* ── Signal severity colors ──────────────────────────────────────── */
const SEV = { bullish: T.green, bearish: T.red, neutral: T.amber };

export function CandlestickTab({ data }) {
  const cs = data?.candlestick;
  const comp = data?.comparable || data?.insight?.comparable;
  const [filter, setFilter] = useState("all");

  if (!cs?.bars?.length) {
    return (
      <Card>
        <div style={{ textAlign: "center", padding: 40, color: T.muted }}>
          Aucune donnée chandelier. Lancez l'ETL pour ce ticker.
        </div>
      </Card>
    );
  }

  const bars = cs.bars;
  const levels = comp?.levels || {};
  const summary = cs.signal_summary || {};

  /* ── Prepare data: add range column for recharts bar ─────────── */
  const chartData = useMemo(() =>
    bars.map(b => ({
      ...b,
      range: [b.low, b.high],
      bodyRange: [Math.min(b.open, b.close), Math.max(b.open, b.close)],
    })),
    [bars]
  );

  /* ── Filter signals ─────────────────────────────────────────── */
  const recentSignals = useMemo(() => {
    const all = [];
    bars.forEach(b => b.signals?.forEach(s => all.push({ ...s, date: b.date, close: b.close })));
    if (filter === "all") return all;
    return all.filter(s => s.severity === filter);
  }, [bars, filter]);

  /* ── Signal type counts ─────────────────────────────────────── */
  const typeCounts = useMemo(() => {
    const counts = {};
    recentSignals.forEach(s => { counts[s.type] = (counts[s.type] || 0) + 1; });
    return Object.entries(counts).sort((a, b) => b[1] - a[1]);
  }, [recentSignals]);

  return (
    <div style={{ display: "grid", gridTemplateColumns: "1fr 300px", gap: 14 }}>
      {/* ── Left: Chart ───────────────────────────────────────── */}
      <div style={{ display: "flex", flexDirection: "column", gap: 14 }}>
        <Card delay={0}>
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 8 }}>
            <Label>Chandeliers Japonais — {cs.ticker}</Label>
            <div style={{ display: "flex", gap: 10, fontSize: 10, fontFamily: T.mono }}>
              <span style={{ color: T.green }}>● Haussier</span>
              <span style={{ color: T.red }}>● Baissier</span>
              <span style={{ color: "#f5a623" }}>┄ SMA 20</span>
              <span style={{ color: "#ff4d6a88" }}>┄ SMA 50</span>
            </div>
          </div>

          <ResponsiveContainer width="100%" height={380}>
            <ComposedChart data={chartData} margin={{ top: 16, right: 10, bottom: 0, left: 0 }}>
              <XAxis
                dataKey="date"
                tick={{ fontSize: 9, fill: T.muted, fontFamily: T.mono }}
                tickFormatter={d => d?.slice(5) || ""}
                interval={Math.max(1, Math.floor(chartData.length / 10))}
                axisLine={{ stroke: T.border }}
                tickLine={false}
              />
              <YAxis
                domain={["auto", "auto"]}
                tick={{ fontSize: 9, fill: T.muted, fontFamily: T.mono }}
                axisLine={false}
                tickLine={false}
                width={52}
              />
              <Tooltip content={<CandleTooltip />} />

              {/* Candle bodies as bars */}
              <Bar dataKey="range" barSize={6} shape={<CandleShape />}>
                {chartData.map((e, i) => (
                  <Cell key={i} fill={e.close >= e.open ? T.green : T.red} />
                ))}
              </Bar>

              {/* SMA overlays */}
              <Line type="monotone" dataKey="sma_20" stroke="#f5a62388" strokeWidth={1.2} dot={false} strokeDasharray="4 2" />
              <Line type="monotone" dataKey="sma_50" stroke="#ff4d6a66" strokeWidth={1.2} dot={false} strokeDasharray="6 3" />

              {/* Support / Resistance */}
              {levels.support && <ReferenceLine y={levels.support} stroke={T.green} strokeDasharray="3 3" strokeWidth={0.8} label={{ value: `S ${levels.support}`, position: "left", fill: T.green, fontSize: 9 }} />}
              {levels.resistance && <ReferenceLine y={levels.resistance} stroke={T.red} strokeDasharray="3 3" strokeWidth={0.8} label={{ value: `R ${levels.resistance}`, position: "left", fill: T.red, fontSize: 9 }} />}
            </ComposedChart>
          </ResponsiveContainer>

          {/* Volume bars below */}
          <ResponsiveContainer width="100%" height={50}>
            <ComposedChart data={chartData} margin={{ top: 0, right: 10, bottom: 0, left: 0 }}>
              <XAxis dataKey="date" hide />
              <YAxis hide />
              <Bar dataKey="volume" barSize={5} radius={[1, 1, 0, 0]}>
                {chartData.map((e, i) => (
                  <Cell key={i} fill={e.close >= e.open ? T.green + "33" : T.red + "33"} />
                ))}
              </Bar>
            </ComposedChart>
          </ResponsiveContainer>
        </Card>

        {/* Signal timeline */}
        <Card delay={200}>
          <Label>Chronologie des signaux ({recentSignals.length})</Label>
          <div style={{ maxHeight: 300, overflowY: "auto", display: "flex", flexDirection: "column", gap: 4, marginTop: 8 }}>
            {recentSignals.slice(-30).reverse().map((s, i) => (
              <div key={i} style={{
                display: "flex", alignItems: "center", gap: 8,
                padding: "6px 10px", background: T.panel2, borderRadius: 6,
                borderLeft: `3px solid ${SEV[s.severity] || T.muted}`,
              }}>
                <span style={{ fontSize: 10, color: T.muted, fontFamily: T.mono, minWidth: 72 }}>{s.date?.slice(5)}</span>
                <span style={{ fontSize: 11, flex: 1 }}>{s.label}</span>
                <Tag color={SEV[s.severity]}>{s.type}</Tag>
              </div>
            ))}
          </div>
        </Card>
      </div>

      {/* ── Right: Sidebar ────────────────────────────────────── */}
      <div style={{ display: "flex", flexDirection: "column", gap: 14 }}>
        {/* Signal summary */}
        <Card delay={60}>
          <Label>Résumé Signaux</Label>
          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr 1fr", gap: 8, marginTop: 8 }}>
            {[
              { l: "Bullish", v: summary.bullish || 0, c: T.green },
              { l: "Bearish", v: summary.bearish || 0, c: T.red },
              { l: "Neutral", v: summary.neutral || 0, c: T.amber },
            ].map((s, i) => (
              <div key={i} style={{
                textAlign: "center", padding: "10px 6px", borderRadius: 6,
                background: s.c + "10", border: `1px solid ${s.c}25`,
              }}>
                <div style={{ fontFamily: T.mono, fontSize: 22, fontWeight: 700, color: s.c }}>{s.v}</div>
                <div style={{ fontSize: 9, color: T.muted }}>{s.l}</div>
              </div>
            ))}
          </div>
        </Card>

        {/* Filter */}
        <Card delay={120}>
          <Label>Filtre</Label>
          <div style={{ display: "flex", gap: 4, marginTop: 6, flexWrap: "wrap" }}>
            {["all", "bullish", "bearish", "neutral"].map(f => (
              <button key={f} onClick={() => setFilter(f)} style={{
                padding: "4px 10px", borderRadius: 5, fontSize: 10, fontWeight: 600,
                background: filter === f ? (f === "all" ? T.accent : SEV[f]) + "22" : "transparent",
                color: filter === f ? (f === "all" ? T.accent : SEV[f]) : T.muted,
                border: `1px solid ${filter === f ? (f === "all" ? T.accent : SEV[f]) + "55" : T.border}`,
                cursor: "pointer",
              }}>{f === "all" ? "Tous" : f.charAt(0).toUpperCase() + f.slice(1)}</button>
            ))}
          </div>
        </Card>

        {/* Pattern frequency */}
        <Card delay={180}>
          <Label>Patterns détectés</Label>
          <div style={{ display: "flex", flexDirection: "column", gap: 4, marginTop: 6 }}>
            {typeCounts.slice(0, 10).map(([type, count], i) => (
              <div key={i} style={{ display: "flex", justifyContent: "space-between", padding: "5px 8px", background: T.panel2, borderRadius: 5 }}>
                <span style={{ fontSize: 11 }}>{type.replace(/_/g, " ")}</span>
                <span style={{ fontFamily: T.mono, fontSize: 12, fontWeight: 600, color: T.accent }}>{count}</span>
              </div>
            ))}
            {typeCounts.length === 0 && <div style={{ fontSize: 11, color: T.muted }}>Aucun pattern</div>}
          </div>
        </Card>

        {/* Niveaux */}
        {levels.support && (
          <Card delay={240}>
            <Label>Niveaux clés</Label>
            <div style={{ display: "flex", flexDirection: "column", gap: 4, marginTop: 6 }}>
              {[
                { l: "Objectif 2", v: levels.target_2, c: T.accent },
                { l: "Résistance", v: levels.resistance, c: T.red },
                { l: "Pivot", v: levels.pivot, c: T.text },
                { l: "Support", v: levels.support, c: T.green },
              ].filter(x => x.v).map((lv, i) => (
                <div key={i} style={{ display: "flex", justifyContent: "space-between", padding: "4px 8px", background: T.panel2, borderRadius: 4 }}>
                  <span style={{ fontSize: 10, color: T.muted }}>{lv.l}</span>
                  <span style={{ fontFamily: T.mono, fontSize: 12, fontWeight: 600, color: lv.c }}>{Number(lv.v).toFixed(2)}</span>
                </div>
              ))}
            </div>
          </Card>
        )}
      </div>
    </div>
  );
}
