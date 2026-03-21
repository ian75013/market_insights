/** Shared UI primitives — all styled via CSS classes */

export function Card({ children, className = "", delay = 0 }) {
  return (
    <div className={`card fade-up ${className}`} style={delay ? { animationDelay: `${delay}ms` } : undefined}>
      {children}
    </div>
  );
}

export function Label({ children }) {
  return <div className="label">{children}</div>;
}

export function Num({ v, prefix = "", suffix = "", className = "", size = "md" }) {
  return <span className={`num num-${size} ${className}`}>{prefix}{v}{suffix}</span>;
}

export function Tag({ children, variant = "muted" }) {
  return <span className={`tag tag-${variant}`}>{children}</span>;
}

export function Pill({ children, active, onClick }) {
  return <button className={`pill ${active ? "active" : ""}`} onClick={onClick}>{children}</button>;
}

export function VerdictBadge({ verdict }) {
  const labels = { bullish: "BULLISH", bearish: "BEARISH", neutral: "NEUTRAL" };
  return (
    <span className={`verdict verdict-${verdict || "neutral"}`}>
      <span className="dot" />
      {labels[verdict] || labels.neutral}
    </span>
  );
}

export function GaugeBar({ value, max = 1, label, colorClass = "text-accent" }) {
  const pctVal = Math.min(100, (value / max) * 100);
  const color = colorClass.includes("green") ? "var(--green)" : colorClass.includes("red") ? "var(--red)" : colorClass.includes("amber") ? "var(--amber)" : "var(--accent)";
  return (
    <div className="gauge">
      <div className="gauge-header">
        <span className="gauge-label">{label}</span>
        <span className={`gauge-value ${colorClass}`}>{(value * 100).toFixed(0)}%</span>
      </div>
      <div className="gauge-track">
        <div className="gauge-fill" style={{ width: `${pctVal}%`, background: `linear-gradient(90deg, ${color}88, ${color})` }} />
      </div>
    </div>
  );
}

export function Skeleton({ width = "100%", height = 20 }) {
  return <div className="skeleton" style={{ width, height }} />;
}

export function ThemeToggle({ theme, onToggle }) {
  return (
    <div className="theme-toggle" onClick={onToggle} title={theme === "dark" ? "Passer en clair" : "Passer en sombre"}>
      <span className="icon icon-moon">🌙</span>
      <span className="icon icon-sun">☀️</span>
      <div className="knob" />
    </div>
  );
}
