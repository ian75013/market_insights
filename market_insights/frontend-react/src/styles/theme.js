/** Bloomberg/Refinitiv-inspired terminal design tokens */

export const T = {
  /* ── Backgrounds ──────────────────────────── */
  bg:       "#080c18",
  panel:    "#0d1225",
  panel2:   "#111a32",
  border:   "#1c2847",

  /* ── Text ─────────────────────────────────── */
  text:     "#dfe6f5",
  muted:    "#7b8aad",

  /* ── Accent ───────────────────────────────── */
  accent:   "#3ec6e0",
  accentDim:"#1a5c6e",

  /* ── Semantic ─────────────────────────────── */
  green:    "#00d67e",
  red:      "#ff4d6a",
  amber:    "#f5a623",

  /* ── Typography ───────────────────────────── */
  mono:     "'JetBrains Mono', 'Fira Code', 'SF Mono', monospace",
  sans:     "'DM Sans', 'Instrument Sans', system-ui, sans-serif",
};

/** Color for a price change value */
export const chgColor = (v) => (v >= 0 ? T.green : T.red);

/** Format large numbers ($2.3T, $150.5B) */
export const fmtMcap = (v) => {
  if (v == null || v === 0) return "—";
  if (Math.abs(v) >= 1e12) return `$${(v / 1e12).toFixed(2)}T`;
  if (Math.abs(v) >= 1e9) return `$${(v / 1e9).toFixed(1)}B`;
  if (Math.abs(v) >= 1e6) return `$${(v / 1e6).toFixed(1)}M`;
  return `$${v.toFixed(0)}`;
};

/** Format percentage from decimal */
export const pct = (v) => (v == null ? "—" : `${(v * 100).toFixed(1)}%`);
