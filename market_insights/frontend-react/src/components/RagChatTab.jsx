import { useState, useEffect, useRef, useCallback } from "react";
import { Card, Label, Tag } from "./ui";
import { ragChat, getLlmProviders, indexRag, getRagStats } from "../services/api";

const PROV_COLORS = { openai:"#10a37f", anthropic:"#d97706", mistral:"#f97316", groq:"#6366f1", ollama:"#22d3ee", lmstudio:"#a78bfa", fallback:"var(--muted)" };

export function RagChatTab({ ticker }) {
  const [providers, setProviders] = useState([]);
  const [backend, setBackend] = useState("");
  const [model, setModel] = useState("");
  const [ragStats, setRagStats] = useState(null);
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [indexing, setIndexing] = useState(false);
  const endRef = useRef(null);

  useEffect(() => {
    getLlmProviders().then(d => {
      setProviders(d.providers || []);
      const first = (d.providers || []).find(p => p.available && p.name !== "fallback");
      if (first) { setBackend(first.name); if (first.models?.length) setModel(first.models[0]); }
      else setBackend("fallback");
    }).catch(() => { setProviders([{ name:"fallback", available:true, models:[] }]); setBackend("fallback"); });
    getRagStats().then(setRagStats).catch(()=>{});
  }, []);

  useEffect(() => { endRef.current?.scrollIntoView({ behavior: "smooth" }); }, [messages]);

  const curProv = providers.find(p => p.name === backend);
  const models = curProv?.models || [];

  const pickBackend = (name) => { setBackend(name); const p = providers.find(x=>x.name===name); if (p?.models?.length) setModel(p.models[0]); else setModel(""); };

  const send = useCallback(async () => {
    const q = input.trim(); if (!q || loading) return;
    setMessages(prev => [...prev, { role:"user", content:q, ts: new Date().toISOString() }]);
    setInput(""); setLoading(true);
    try {
      const resp = await ragChat({ ticker, question:q, llm_backend:backend||undefined, llm_model:model||undefined, language:"fr", top_k:5 });
      setMessages(prev => [...prev, { role:"assistant", content:resp.answer, sources:resp.sources, llm:resp.llm, ts:resp.generated_at }]);
    } catch (err) {
      setMessages(prev => [...prev, { role:"error", content:`Erreur: ${err.message}`, ts: new Date().toISOString() }]);
    } finally { setLoading(false); }
  }, [input, loading, ticker, backend, model]);

  const handleIndex = async () => {
    setIndexing(true);
    try {
      const r = await indexRag(ticker);
      setMessages(prev => [...prev, { role:"system", content:`Index RAG mis à jour: ${r.indexed_chunks} chunks indexés.`, ts: new Date().toISOString() }]);
      setRagStats(await getRagStats());
    } catch (err) { setMessages(prev => [...prev, { role:"error", content:`Erreur: ${err.message}`, ts: new Date().toISOString() }]); }
    finally { setIndexing(false); }
  };

  const quickPrompts = [
    `Quels sont les principaux catalyseurs pour ${ticker} ?`,
    `Quels risques pèsent sur ${ticker} actuellement ?`,
    `Résume la situation fondamentale de ${ticker}.`,
    `Quelle est la tendance technique de ${ticker} ?`,
  ];

  return (
    <div className="grid-sidebar-w">
      {/* Chat */}
      <Card delay={0} className="flex-col" style={{ display:"flex", flexDirection:"column", minHeight:420 }}>
        <div className="card-header">
          <Label>RAG Chat — {ticker}</Label>
          {backend && <Tag variant={backend==="fallback"?"muted":"accent"}>{backend}{model ? ` / ${model.split("/").pop().split("-").slice(0,2).join("-")}` : ""}</Tag>}
        </div>

        <div className="chat-area">
          {messages.length === 0 && (
            <div className="empty-state"><h3>Posez une question sur {ticker}</h3><p className="text-sm">Le RAG récupère les documents indexés et les envoie au LLM sélectionné.</p></div>
          )}
          {messages.map((msg, i) => <Bubble key={i} msg={msg} />)}
          {loading && <div className="bubble bubble-assistant"><span className="loading-pulse text-sm">● Recherche et génération…</span></div>}
          <div ref={endRef} />
        </div>

        {messages.length === 0 && (
          <div className="flex-row gap-xs" style={{ marginBottom: 12, flexWrap: "wrap" }}>
            {quickPrompts.map((q, i) => <button key={i} className="quick-pick" onClick={() => setInput(q)}>{q}</button>)}
          </div>
        )}

        <div className="chat-input-bar">
          <input className="chat-input" value={input} onChange={e=>setInput(e.target.value)} onKeyDown={e=>e.key==="Enter"&&send()} placeholder={`Question sur ${ticker}…`} disabled={loading} />
          <button className="chat-send" onClick={send} disabled={loading || !input.trim()}>Envoyer</button>
        </div>
      </Card>

      {/* Sidebar */}
      <div className="flex-col">
        <Card delay={60}><Label>LLM Provider</Label>
          <div className="flex-col gap-xs">
            {providers.map(p => (
              <button key={p.name} className={`provider-btn ${backend===p.name?"active":""}`} onClick={()=>p.available&&pickBackend(p.name)} disabled={!p.available}>
                <div className="flex-row gap-xs">
                  <span className="provider-dot" style={{ background: p.available ? (PROV_COLORS[p.name]||"var(--green)") : "var(--muted)" }} />
                  <span className="fw-600">{p.name}</span>
                </div>
                <span className="text-xs muted">{p.available ? `${p.models?.length||0} models` : "offline"}</span>
              </button>
            ))}
          </div>
        </Card>

        {models.length > 0 && (
          <Card delay={120}><Label>Modèle</Label>
            <select className="select input-mono" value={model} onChange={e=>setModel(e.target.value)} style={{ width:"100%", marginTop:6 }}>
              {models.map(m => <option key={m} value={m}>{m}</option>)}
            </select>
          </Card>
        )}

        <Card delay={180}><Label>Index RAG</Label>
          {ragStats && <div className="text-sm muted" style={{ marginBottom:8 }}>
            Tickers: {ragStats.tickers_indexed?.join(", ")||"aucun"} · {ragStats.total_chunks||0} chunks
          </div>}
          <button className="btn btn-secondary" onClick={handleIndex} disabled={indexing} style={{ width:"100%" }}>
            {indexing ? "Indexation…" : `Réindexer ${ticker}`}
          </button>
        </Card>

        <Card delay={240}><Label>Guide</Label>
          <div className="text-sm muted lh-relaxed">
            <p style={{ marginBottom:6 }}><strong style={{ color:"var(--text)" }}>Cloud:</strong> Configurez les clés API dans .env</p>
            <p style={{ marginBottom:6 }}><strong style={{ color:"var(--text)" }}>Local:</strong> Lancez <code>ollama serve</code> ou LMStudio</p>
            <p><strong style={{ color:"var(--text)" }}>Fallback:</strong> Retourne le contexte RAG brut</p>
          </div>
        </Card>
      </div>
    </div>
  );
}

function Bubble({ msg }) {
  const cls = msg.role === "user" ? "bubble-user" : msg.role === "error" ? "bubble-error" : msg.role === "system" ? "bubble-system" : "bubble-assistant";
  const labels = { user:"Vous", assistant:"Assistant", error:"Erreur", system:"Système" };
  return (
    <div className={`bubble ${cls}`}>
      <div className="bubble-role">
        <span>{labels[msg.role] || msg.role}</span>
        {msg.llm && <Tag variant="accent">{msg.llm.provider}/{msg.llm.model?.split("/").pop()?.slice(0,20)}</Tag>}
      </div>
      <div>{msg.content}</div>
      {msg.sources?.length > 0 && (
        <div className="bubble-sources">
          <div className="text-xs muted" style={{ marginBottom:4 }}>Sources citées:</div>
          {msg.sources.map((s,i) => (
            <div key={i} className="flex-row gap-xs text-xs">
              <span className="text-accent fw-600">[{i+1}]</span>
              <span className="muted">{s.title}</span>
              <Tag variant="muted">{s.document_type}</Tag>
              <span className="mono text-accent">{s.score}</span>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
