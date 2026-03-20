import { T } from "../styles/theme";

/* ── Card ────────────────────────────────────────────────────────── */

export function Card({ children, style, delay = 0 }) {
  return (
    <div
      className="fade-up"
      style={{
        background: T.panel,
        border: `1px solid ${T.border}`,
        borderRadius: 10,
        padding: "16px 18px",
        animationDelay: `${delay}ms`,
        ...style,
      }}
    >
      {children}
    </div>
  );
}

/* ── Label ───────────────────────────────────────────────────────── */

export function Label({ children }) {
  return (
    <div
      style={{
        fontSize: 10,
        fontWeight: 600,
        color: T.muted,
        textTransform: "uppercase",
        letterSpacing: "0.1em",
        marginBottom: 4,
      }}
    >
      {children}
    </div>
  );
}

/* ── Num (monospace number display) ──────────────────────────────── */

export function Num({ v, prefix = "", suffix = "", color, size = 22 }) {
  return (
    <span
      style={{
        fontFamily: T.mono,
        fontSize: size,
        fontWeight: 600,
        color: color || T.text,
      }}
    >
      {prefix}
      {v}
      {suffix}
    </span>
  );
}

/* ── Tag ─────────────────────────────────────────────────────────── */

export function Tag({ children, color = T.muted }) {
  return (
    <span
      style={{
        display: "inline-block",
        padding: "3px 8px",
        borderRadius: 4,
        fontSize: 10,
        fontWeight: 600,
        background: color + "18",
        color,
        border: `1px solid ${color}30`,
        fontFamily: T.mono,
      }}
    >
      {children}
    </span>
  );
}

/* ── Pill (ticker selector button) ───────────────────────────────── */

export function Pill({ children, active, onClick }) {
  return (
    <button
      onClick={onClick}
      style={{
        padding: "6px 14px",
        borderRadius: 6,
        fontSize: 12,
        fontWeight: 600,
        fontFamily: T.sans,
        background: active ? T.accent + "22" : "transparent",
        color: active ? T.accent : T.muted,
        border: `1px solid ${active ? T.accent + "55" : T.border}`,
        cursor: "pointer",
        transition: "all .15s",
      }}
    >
      {children}
    </button>
  );
}

/* ── Verdict badge (BULLISH / BEARISH / NEUTRAL) ─────────────────── */

const VERDICT_MAP = {
  bullish: { color: T.green, label: "BULLISH" },
  bearish: { color: T.red, label: "BEARISH" },
  neutral: { color: T.amber, label: "NEUTRAL" },
};

export function VerdictBadge({ verdict }) {
  const { color: c, label } = VERDICT_MAP[verdict] || VERDICT_MAP.neutral;
  return (
    <span
      style={{
        display: "inline-flex",
        alignItems: "center",
        gap: 6,
        padding: "4px 12px",
        borderRadius: 5,
        background: c + "15",
        border: `1px solid ${c}40`,
        color: c,
        fontSize: 12,
        fontWeight: 700,
        fontFamily: T.mono,
        letterSpacing: "0.05em",
      }}
    >
      <span
        style={{
          width: 7,
          height: 7,
          borderRadius: "50%",
          background: c,
          animation: "pulse 2s infinite",
        }}
      />
      {label}
    </span>
  );
}

/* ── Gauge bar ───────────────────────────────────────────────────── */

export function GaugeBar({ value, max = 1, label, color = T.accent }) {
  const pctVal = Math.min(100, (value / max) * 100);
  return (
    <div style={{ marginBottom: 8 }}>
      <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 3 }}>
        <span style={{ fontSize: 10, color: T.muted, fontWeight: 500 }}>{label}</span>
        <span style={{ fontSize: 11, color, fontFamily: T.mono, fontWeight: 600 }}>
          {(value * 100).toFixed(0)}%
        </span>
      </div>
      <div
        style={{
          height: 4,
          background: T.panel2,
          borderRadius: 2,
          overflow: "hidden",
        }}
      >
        <div
          style={{
            width: `${pctVal}%`,
            height: "100%",
            background: `linear-gradient(90deg, ${color}88, ${color})`,
            borderRadius: 2,
            transition: "width .6s ease",
          }}
        />
      </div>
    </div>
  );
}

/* ── Loading skeleton ────────────────────────────────────────────── */

export function Skeleton({ width = "100%", height = 20 }) {
  return (
    <div
      className="skeleton"
      style={{ width, height, borderRadius: 6 }}
    />
  );
}
