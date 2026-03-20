import { T } from "../styles/theme";

/**
 * Top macro data ribbon.
 * @param {{ macro: object | null }} props
 */
export function MacroRibbon({ macro }) {
  /* Flatten macro data into displayable key-value pairs */
  const items = [];

  if (macro?.data) {
    const d = macro.data;

    /* FRED-style (flat keys) */
    if (typeof d.fed_funds === "number") {
      items.push(["Fed Funds", d.fed_funds]);
      if (d.treasury_10y) items.push(["10Y", d.treasury_10y]);
      if (d.treasury_2y) items.push(["2Y", d.treasury_2y]);
      if (d.cpi_yoy) items.push(["CPI YoY", d.cpi_yoy]);
      if (d.unemployment) items.push(["Unemp.", d.unemployment]);
      if (d.vix) items.push(["VIX", d.vix]);
    }

    /* Sample-style (nested) */
    if (d.rates) {
      items.push(["Fed Funds", d.rates.fed_funds]);
      if (d.rates.treasury_10y) items.push(["10Y", d.rates.treasury_10y]);
      if (d.rates.treasury_2y) items.push(["2Y", d.rates.treasury_2y]);
    }
    if (d.inflation) {
      items.push(["CPI YoY", d.inflation.cpi_yoy]);
    }
    if (d.labor) {
      items.push(["Unemp.", d.labor.unemployment]);
    }
    if (d.sentiment) {
      items.push(["VIX", d.sentiment.vix]);
    }
    if (d.growth) {
      items.push(["GDP", d.growth.gdp_nowcast || d.growth.gdp_real_q]);
    }
  }

  /* Deduplicate by label */
  const seen = new Set();
  const unique = items.filter(([label]) => {
    if (seen.has(label)) return false;
    seen.add(label);
    return true;
  });

  if (unique.length === 0) return null;

  return (
    <div
      style={{
        display: "flex",
        gap: 20,
        padding: "6px 16px",
        background: T.panel,
        borderBottom: `1px solid ${T.border}`,
        overflowX: "auto",
        whiteSpace: "nowrap",
        fontSize: 11,
        fontFamily: T.mono,
      }}
    >
      {unique.map(([label, value]) => (
        <span key={label} style={{ color: T.muted }}>
          {label}{" "}
          <span style={{ color: T.text, fontWeight: 600 }}>
            {typeof value === "number" ? value.toFixed(2) : value}
            {label !== "VIX" ? "%" : ""}
          </span>
        </span>
      ))}
      <span style={{ color: T.muted, marginLeft: "auto", fontSize: 10 }}>
        {macro?.source === "fred" ? "FRED Live" : "Sample Data"}
      </span>
    </div>
  );
}
