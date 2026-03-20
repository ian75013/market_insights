import {
  AreaChart, Area, XAxis, YAxis, Tooltip, ResponsiveContainer,
  ComposedChart, Line, Bar, Cell, ReferenceLine,
} from "recharts";
import { T } from "../styles/theme";

/* ── Price chart with SMA overlays and support/resistance lines ── */

export function PriceChart({ data, support, resistance, showSma = true, height = 260 }) {
  if (!data || data.length === 0) return null;

  const fmtY = (v) =>
    typeof v === "number" ? (v > 1000 ? `${(v / 1000).toFixed(1)}k` : v.toFixed(0)) : v;

  return (
    <ResponsiveContainer width="100%" height={height}>
      <ComposedChart data={data} margin={{ top: 8, right: 8, bottom: 0, left: 0 }}>
        <defs>
          <linearGradient id="areaGrad" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor={T.accent} stopOpacity={0.18} />
            <stop offset="100%" stopColor={T.accent} stopOpacity={0} />
          </linearGradient>
        </defs>

        <XAxis
          dataKey="date"
          tick={{ fontSize: 9, fill: T.muted, fontFamily: T.mono }}
          tickFormatter={(d) => (d ? d.slice(5) : "")}
          interval={Math.max(1, Math.floor(data.length / 8))}
          axisLine={{ stroke: T.border }}
          tickLine={false}
        />
        <YAxis
          domain={["auto", "auto"]}
          tick={{ fontSize: 9, fill: T.muted, fontFamily: T.mono }}
          tickFormatter={fmtY}
          axisLine={false}
          tickLine={false}
          width={52}
        />
        <Tooltip
          contentStyle={{
            background: T.panel2,
            border: `1px solid ${T.border}`,
            borderRadius: 6,
            fontSize: 11,
            fontFamily: T.mono,
          }}
          labelStyle={{ color: T.muted }}
          itemStyle={{ padding: 0 }}
        />

        <Area
          type="monotone"
          dataKey="close"
          stroke={T.accent}
          strokeWidth={1.8}
          fill="url(#areaGrad)"
          dot={false}
          name="Close"
        />

        {showSma && (
          <Line
            type="monotone"
            dataKey="sma_20"
            stroke="#f5a62388"
            strokeWidth={1}
            dot={false}
            strokeDasharray="4 2"
            name="SMA 20"
          />
        )}
        {showSma && (
          <Line
            type="monotone"
            dataKey="sma_50"
            stroke="#ff4d6a55"
            strokeWidth={1}
            dot={false}
            strokeDasharray="6 3"
            name="SMA 50"
          />
        )}

        {support != null && (
          <ReferenceLine y={support} stroke={T.green} strokeDasharray="3 3" strokeWidth={0.8} />
        )}
        {resistance != null && (
          <ReferenceLine y={resistance} stroke={T.red} strokeDasharray="3 3" strokeWidth={0.8} />
        )}
      </ComposedChart>
    </ResponsiveContainer>
  );
}

/* ── Volume chart ────────────────────────────────────────────────── */

export function VolumeChart({ data, height = 60 }) {
  if (!data || data.length === 0) return null;

  return (
    <ResponsiveContainer width="100%" height={height}>
      <ComposedChart data={data} margin={{ top: 0, right: 8, bottom: 0, left: 0 }}>
        <XAxis dataKey="date" hide />
        <YAxis hide />
        <Bar dataKey="volume" radius={[1, 1, 0, 0]}>
          {data.map((e, i) => (
            <Cell key={i} fill={e.close >= e.open ? T.green + "44" : T.red + "44"} />
          ))}
        </Bar>
      </ComposedChart>
    </ResponsiveContainer>
  );
}
