/** Helper functions — no more inline style constants */

export const chgColor = (v) => (v >= 0 ? "text-green" : "text-red");

export const fmtMcap = (v) => {
  if (v == null || v === 0) return "—";
  if (Math.abs(v) >= 1e12) return `$${(v / 1e12).toFixed(2)}T`;
  if (Math.abs(v) >= 1e9) return `$${(v / 1e9).toFixed(1)}B`;
  if (Math.abs(v) >= 1e6) return `$${(v / 1e6).toFixed(1)}M`;
  return `$${v.toFixed(0)}`;
};

export const pct = (v) => (v == null ? "—" : `${(v * 100).toFixed(1)}%`);

export const sevClass = (s) => s === "bullish" ? "bull" : s === "bearish" ? "bear" : "neut";
export const sevTagClass = (s) => s === "bullish" ? "tag-green" : s === "bearish" ? "tag-red" : "tag-amber";
