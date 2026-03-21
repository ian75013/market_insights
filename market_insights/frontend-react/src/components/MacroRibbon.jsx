export function MacroRibbon({ macro }) {
  const items = [];
  if (macro?.data) {
    const d = macro.data;
    if (typeof d.fed_funds === "number") {
      if (d.fed_funds) items.push(["Fed Funds", d.fed_funds]);
      if (d.treasury_10y) items.push(["10Y", d.treasury_10y]);
      if (d.cpi_yoy) items.push(["CPI", d.cpi_yoy]);
      if (d.unemployment) items.push(["Unemp.", d.unemployment]);
      if (d.vix) items.push(["VIX", d.vix]);
    }
    if (d.rates) {
      items.push(["Fed Funds", d.rates.fed_funds]);
      if (d.rates.treasury_10y) items.push(["10Y", d.rates.treasury_10y]);
    }
    if (d.inflation) items.push(["CPI", d.inflation.cpi_yoy]);
    if (d.labor) items.push(["Unemp.", d.labor.unemployment]);
    if (d.sentiment) items.push(["VIX", d.sentiment.vix]);
    if (d.growth) items.push(["GDP", d.growth.gdp_nowcast || d.growth.gdp_real_q]);
  }
  const seen = new Set();
  const unique = items.filter(([l]) => { if (seen.has(l)) return false; seen.add(l); return true; });
  if (!unique.length) return null;

  return (
    <div className="macro-ribbon">
      {unique.map(([label, value]) => (
        <span key={label} className="muted">
          {label} <span className="fw-700" style={{ color: "var(--text)" }}>{typeof value === "number" ? value.toFixed(2) : value}{label !== "VIX" ? "%" : ""}</span>
        </span>
      ))}
      <span className="muted" style={{ marginLeft: "auto" }}>{macro?.source === "fred" ? "FRED Live" : "Sample"}</span>
    </div>
  );
}
