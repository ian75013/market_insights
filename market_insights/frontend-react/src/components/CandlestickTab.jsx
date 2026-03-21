import { useState, useMemo, useCallback } from "react";
import { ComposedChart, XAxis, YAxis, Tooltip, ResponsiveContainer, Bar, Cell, Line, ReferenceLine } from "recharts";
import { Card, Label, Tag } from "./ui";
import { getCandlestick, runEtl } from "../services/api";

const POPULAR = [
  { label: "AAPL", desc: "Apple" }, { label: "MSFT", desc: "Microsoft" }, { label: "NVDA", desc: "Nvidia" },
  { label: "GOOGL", desc: "Alphabet" }, { label: "AMZN", desc: "Amazon" }, { label: "TSLA", desc: "Tesla" },
  { label: "META", desc: "Meta" }, { label: "JPM", desc: "JPMorgan" }, { label: "BTC", desc: "Bitcoin" },
  { label: "ETH", desc: "Ethereum" }, { label: "EURUSD=X", desc: "EUR/USD" },
];
const PROVIDERS = [
  { value: "yahoo", label: "Yahoo Finance" }, { value: "coingecko", label: "CoinGecko (Crypto)" },
  { value: "sample", label: "Sample" }, { value: "stooq", label: "Stooq" }, { value: "auto", label: "Auto" },
];
const CRYPTO_TICKERS = new Set(["BTC","ETH","SOL","ADA","DOGE","DOT","AVAX","MATIC","LINK","UNI","XRP","BNB","ATOM","LTC","NEAR"]);

const fmtDate = (d) => { if (!d) return ""; const p = d.slice(0,10).split("-"); return p.length >= 3 ? `${p[2]}/${p[1]}` : d.slice(5); };
const fmtPrice = (v) => { if (v == null) return "—"; return v >= 1000 ? v.toLocaleString("en-US", { maximumFractionDigits: 0 }) : v.toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 }); };

function CandleShape({ x, y, width, height, payload }) {
  if (!payload || !height) return null;
  const { open, high, low, close } = payload;
  const isUp = close >= open;
  const color = isUp ? "var(--green)" : "var(--red)";
  const barW = Math.max(width * 0.65, 2);
  const cx = x + width / 2;
  const range = Math.max(high - low, 0.001);
  const bodyTop = y + height * ((high - Math.max(open, close)) / range);
  const bodyBot = y + height * ((high - Math.min(open, close)) / range);
  const bodyH = Math.max(bodyBot - bodyTop, 0.5);
  const hasSig = payload.signals?.length > 0;
  const sigColor = hasSig ? (payload.signals[0]?.severity === "bullish" ? "var(--green)" : payload.signals[0]?.severity === "bearish" ? "var(--red)" : "var(--amber)") : null;
  return (
    <g>
      <line x1={cx} x2={cx} y1={y} y2={y+height} stroke={color} strokeOpacity={0.5} strokeWidth={0.8} />
      <rect x={cx-barW/2} width={barW} y={bodyTop} height={bodyH} fill={isUp ? "var(--candle-up-fill,var(--bg))" : color} stroke={color} strokeWidth={0.8} rx={0.5} />
      {hasSig && <polygon points={`${cx},${y-8} ${cx-3},${y-3} ${cx+3},${y-3}`} fill={sigColor} fillOpacity={0.85} />}
    </g>
  );
}

function CandleTooltip({ active, payload }) {
  if (!active || !payload?.[0]) return null;
  const d = payload[0].payload;
  const isUp = d.close >= d.open;
  const chg = d.close && d.open ? ((d.close-d.open)/d.open*100).toFixed(2) : "0.00";
  return (
    <div className="chart-tooltip">
      <div className="muted text-xs" style={{ marginBottom: 6 }}>{fmtDate(d.date)}</div>
      <div className="tooltip-grid">
        <span className="muted">O</span><span>{fmtPrice(d.open)}</span>
        <span className="muted">H</span><span className="text-green">{fmtPrice(d.high)}</span>
        <span className="muted">L</span><span className="text-red">{fmtPrice(d.low)}</span>
        <span className="muted">C</span><span className={`fw-700 ${isUp?"text-green":"text-red"}`}>{fmtPrice(d.close)} ({chg}%)</span>
        <span className="muted">Vol</span><span>{d.volume>=1e6?(d.volume/1e6).toFixed(2)+"M":(d.volume/1e3).toFixed(0)+"K"}</span>
        {d.rsi_14!=null && <><span className="muted">RSI</span><span>{d.rsi_14}</span></>}
      </div>
      {d.signals?.length > 0 && (
        <div style={{ marginTop: 8, borderTop: "1px solid var(--border)", paddingTop: 6 }}>
          {d.signals.map((s,i) => (
            <div key={i} className="flex-row gap-xs" style={{ marginTop: 2 }}>
              <span className="provider-dot" style={{ background: s.severity==="bullish"?"var(--green)":s.severity==="bearish"?"var(--red)":"var(--amber)", width:5, height:5 }} />
              <span className="text-xs">{s.label}</span>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

export function CandlestickTab({ data: parentData, ticker: parentTicker }) {
  const [customTicker, setCustomTicker] = useState("");
  const [provider, setProvider] = useState("yahoo");
  const [chartData, setChartData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [activeTicker, setActiveTicker] = useState("");
  const [filter, setFilter] = useState("all");
  const [etlInfo, setEtlInfo] = useState(null);

  const cs = chartData || parentData?.candlestick;
  const comp = parentData?.comparable || parentData?.insight?.comparable;
  const bars = cs?.bars || [];
  const levels = comp?.levels || {};
  const summary = cs?.signal_summary || {};

  // Detect crypto from ticker (strip -USD suffix)
  const isCryptoTicker = (t) => CRYPTO_TICKERS.has(t.replace(/-.*/, "").toUpperCase());

  const loadChart = useCallback(async (ticker, prov) => {
    if (!ticker) return;
    const t = ticker.trim().toUpperCase();
    // Auto-route crypto to coingecko — backend does it too, but this avoids confusion
    const effectiveProv = (isCryptoTicker(t) && prov !== "sample") ? "coingecko" : prov;
    setLoading(true); setError(null); setActiveTicker(t); setEtlInfo(null);
    try {
      const etlRes = await runEtl(t, effectiveProv);
      setEtlInfo(etlRes);
      // Backend may have normalized the ticker (BTC-USD → BTC)
      const dbTicker = etlRes?.ticker || t;
      setChartData(await getCandlestick(dbTicker));
      setActiveTicker(dbTicker);
    }
    catch (err) { setError(err.message); setChartData(null); }
    finally { setLoading(false); }
  }, []);

  const handleSubmit = (e) => { e?.preventDefault(); loadChart(customTicker || parentTicker, provider); };
  const handleQuick = (t) => { setCustomTicker(t); loadChart(t, provider); };

  const prepared = useMemo(() => bars.map(b => ({ ...b, range: [b.low, b.high] })), [bars]);
  const [yMin, yMax] = useMemo(() => {
    if (!bars.length) return [0, 100];
    const lo = Math.min(...bars.map(b=>b.low)); const hi = Math.max(...bars.map(b=>b.high));
    const pad = (hi-lo)*0.04; return [+(lo-pad).toFixed(2), +(hi+pad).toFixed(2)];
  }, [bars]);

  const allSignals = useMemo(() => { const o=[]; bars.forEach(b=>b.signals?.forEach(s=>o.push({...s,date:b.date,close:b.close}))); return o; }, [bars]);
  const filtered = useMemo(() => filter==="all" ? allSignals : allSignals.filter(s=>s.severity===filter), [allSignals,filter]);
  const typeCounts = useMemo(() => {
    const c={}; filtered.forEach(s=>{c[s.type]=(c[s.type]||0)+1}); return Object.entries(c).sort((a,b)=>b[1]-a[1]);
  }, [filtered]);
  const displayTicker = cs?.ticker || activeTicker || parentTicker || "—";
  const barSize = Math.min(8, Math.max(3, 600 / Math.max(prepared.length, 1)));
  const isCrypto = CRYPTO_TICKERS.has(displayTicker.replace(/-.*/, "").toUpperCase());
  // Dynamic Y-axis width: 52px for stocks, wider for crypto with large prices
  const yAxisWidth = yMax >= 10000 ? 72 : yMax >= 1000 ? 62 : 52;
  const fmtYTick = (v) => v >= 10000 ? `${(v/1000).toFixed(0)}k` : v >= 1000 ? v.toLocaleString("en-US", { maximumFractionDigits: 0 }) : v.toFixed(2);

  return (
    <div className="flex-col">
      {/* Input bar */}
      <Card delay={0}>
        <form onSubmit={handleSubmit} className="flex-row">
          <Label>Charger un graphique</Label>
          <input className="input input-mono flex-1" value={customTicker} onChange={e=>setCustomTicker(e.target.value.toUpperCase())} placeholder="Ticker (AAPL, TSLA, BTC-USD...)" style={{ minWidth: 140 }} />
          <select className="select" value={provider} onChange={e=>setProvider(e.target.value)}>
            {PROVIDERS.map(p=><option key={p.value} value={p.value}>{p.label}</option>)}
          </select>
          <button type="submit" className="btn btn-primary" disabled={loading}>{loading?"Chargement…":"Charger"}</button>
        </form>
        <div className="flex-row gap-xs" style={{ marginTop: 10 }}>
          {POPULAR.map(p => (
            <button key={p.label} className={`quick-pick ${activeTicker===p.label?"active":""}`} onClick={()=>handleQuick(p.label)} disabled={loading}>
              {p.label} <span className="muted" style={{ fontWeight: 400 }}>{p.desc}</span>
            </button>
          ))}
        </div>
        {error && <div className="error-msg" style={{ marginTop: 8 }}>⚠ {error}</div>}
        {etlInfo && !error && (
          <div className="flex-row gap-xs" style={{ marginTop: 8 }}>
            <span className="text-xs muted">Source :</span>
            <Tag variant={etlInfo.provider === "coingecko" ? "accent" : ""}>{etlInfo.provider}</Tag>
            <span className="text-xs muted">{etlInfo.loaded_rows} barres · {etlInfo.elapsed_seconds}s</span>
          </div>
        )}
      </Card>

      {bars.length > 0 ? (
        <div className="grid-sidebar">
          <div className="flex-col">
            <Card delay={50}>
              <div className="card-header">
                <span className="text-base fw-600">{displayTicker} — {bars.length} séances <span className="muted text-xs" style={{ marginLeft: 8 }}>{fmtDate(bars[0].date)} → {fmtDate(bars[bars.length-1].date)}</span></span>
                <div className="flex-row gap-sm mono text-xs">
                  <span className="text-green">▲ Bull</span><span className="text-red">▲ Bear</span>
                  <span className="text-amber">┄ SMA20</span><span style={{ color: "var(--red)", opacity: .5 }}>┄ SMA50</span>
                </div>
              </div>
              <ResponsiveContainer width="100%" height={400}>
                <ComposedChart data={prepared} margin={{ top:20,right:10,bottom:0,left:0 }}>
                  <XAxis dataKey="date" tickFormatter={fmtDate} tick={{ fontSize:12, fill:"var(--muted)", fontFamily:"JetBrains Mono" }} interval={Math.max(1,Math.floor(prepared.length/12))} axisLine={{ stroke:"var(--border)" }} tickLine={false} />
                  <YAxis domain={[yMin,yMax]} tickFormatter={fmtYTick} tick={{ fontSize:12, fill:"var(--muted)", fontFamily:"JetBrains Mono" }} axisLine={false} tickLine={false} width={yAxisWidth} />
                  <Tooltip content={<CandleTooltip />} />
                  <Bar dataKey="range" barSize={barSize} shape={<CandleShape />}>{prepared.map((_,i)=><Cell key={i} />)}</Bar>
                  <Line type="monotone" dataKey="sma_20" stroke="var(--amber)" strokeOpacity={0.65} strokeWidth={1.2} dot={false} strokeDasharray="4 2" />
                  <Line type="monotone" dataKey="sma_50" stroke="var(--red)" strokeOpacity={0.4} strokeWidth={1.2} dot={false} strokeDasharray="6 3" />
                  {levels.support && <ReferenceLine y={levels.support} stroke="var(--green)" strokeOpacity={0.4} strokeDasharray="3 3" strokeWidth={0.7} label={{ value:`S ${fmtPrice(levels.support)}`, position:"left", fill:"var(--green)", fontSize:11 }} />}
                  {levels.resistance && <ReferenceLine y={levels.resistance} stroke="var(--red)" strokeOpacity={0.4} strokeDasharray="3 3" strokeWidth={0.7} label={{ value:`R ${fmtPrice(levels.resistance)}`, position:"left", fill:"var(--red)", fontSize:11 }} />}
                </ComposedChart>
              </ResponsiveContainer>
              <ResponsiveContainer width="100%" height={45}>
                <ComposedChart data={prepared} margin={{ top:0,right:10,bottom:0,left:0 }}>
                  <XAxis dataKey="date" hide /><YAxis hide />
                  <Bar dataKey="volume" barSize={Math.max(2,barSize-2)} radius={[1,1,0,0]}>{prepared.map((e,i)=><Cell key={i} fill={e.close>=e.open?"rgba(0,214,126,.2)":"rgba(255,77,106,.2)"} />)}</Bar>
                </ComposedChart>
              </ResponsiveContainer>
            </Card>
            {filtered.length > 0 && (
              <Card delay={150}><Label>Signaux ({filtered.length})</Label>
                <div className="flex-col gap-xs scroll-y" style={{ maxHeight: 220 }}>
                  {filtered.slice().reverse().map((s,i) => {
                    const cls = s.severity==="bullish"?"bull":s.severity==="bearish"?"bear":"neut";
                    return <div key={i} className={`signal-item ${cls}`}><span className="mono text-xs muted" style={{ minWidth:48 }}>{fmtDate(s.date)}</span><span className="flex-1 text-sm">{s.label}</span><span className="mono text-xs muted">{fmtPrice(s.close)}</span></div>;
                  })}
                </div>
              </Card>
            )}
          </div>
          <div className="flex-col">
            <Card delay={80}><Label>Résumé</Label>
              <div className="grid-3 gap-xs">
                {[{l:"Bull",v:summary.bullish||0,c:"text-green"},{l:"Bear",v:summary.bearish||0,c:"text-red"},{l:"Neutre",v:summary.neutral||0,c:"text-amber"}].map((s,i) => (
                  <div key={i} className="metric-box metric-box-center"><div className={`num num-md ${s.c}`}>{s.v}</div><div className="text-xs muted">{s.l}</div></div>
                ))}
              </div>
            </Card>
            <Card delay={110}><Label>Filtre</Label>
              <div className="flex-row gap-xs">
                {["all","bullish","bearish","neutral"].map(f => (
                  <button key={f} className={`quick-pick ${filter===f?"active":""}`} onClick={()=>setFilter(f)}>{f==="all"?"Tous":f.charAt(0).toUpperCase()+f.slice(1)}</button>
                ))}
              </div>
            </Card>
            <Card delay={140}><Label>Patterns</Label>
              <div className="flex-col gap-xs">{typeCounts.length===0 && <span className="text-sm muted">Aucun signal</span>}
                {typeCounts.map(([type,count],i) => <div key={i} className="level-row"><span className="text-sm">{type.replace(/_/g," ")}</span><span className="mono fw-600 text-accent">{count}</span></div>)}
              </div>
            </Card>
            {levels.support && (
              <Card delay={170}><Label>Niveaux</Label>
                <div className="flex-col gap-xs">
                  {[{l:"Objectif 2",v:levels.target_2,c:"text-accent"},{l:"Résistance",v:levels.resistance,c:"text-red"},{l:"Pivot",v:levels.pivot,c:""},{l:"Support",v:levels.support,c:"text-green"}].filter(x=>x.v).map((lv,i) => (
                    <div key={i} className="level-row"><span className="text-sm muted">{lv.l}</span><span className={`mono fw-600 ${lv.c}`}>{fmtPrice(Number(lv.v))}</span></div>
                  ))}
                </div>
              </Card>
            )}
            <Card delay={200}><Label>Légende</Label>
              <div className="text-xs muted lh-relaxed">
                <div><span className="text-green">▲</span> Haussier (gap up, breakout, marteau, golden cross)</div>
                <div><span className="text-red">▲</span> Baissier (gap down, breakdown, étoile filante, death cross)</div>
                <div><span className="text-amber">▲</span> Neutre (pullback, doji, volume spike)</div>
              </div>
            </Card>
          </div>
        </div>
      ) : !loading && (
        <Card><div className="empty-state"><h3>Saisissez un ticker et cliquez Charger</h3><p>Les données seront récupérées puis affichées en chandeliers annotés.</p></div></Card>
      )}
    </div>
  );
}
