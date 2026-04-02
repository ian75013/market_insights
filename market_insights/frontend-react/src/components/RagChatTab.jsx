import { useState, useEffect, useRef, useCallback } from "react";
import { Card, Label, Tag } from "./ui";
import { ragChatStream, getLlmProviders, indexRag, getRagStats } from "../services/api";

const PROV_COLORS = { litellm:"#111827", openai:"#10a37f", anthropic:"#d97706", mistral:"#f97316", groq:"#6366f1", lmstudio:"#a78bfa", fallback:"var(--muted)" };
const FORCED_LITELLM_MODEL = "llama3.2:1b";

function visibleProviders(providers) {
  return providers.filter(provider => provider.name !== "ollama");
}

function preferredModel(provider) {
  if (!provider?.models?.length) return "";
  if (provider.name === "litellm") {
    return FORCED_LITELLM_MODEL;
  }
  return provider.models[0];
}

function preferredProvider(providers) {
  const available = providers.filter(provider => provider.available);
  return (
    available.find(provider => provider.name === "litellm") ||
    available.find(provider => provider.name !== "fallback") ||
    available.find(provider => provider.name === "fallback") ||
    null
  );
}

export function RagChatTab({ ticker }) {
  const [providers, setProviders] = useState([]);
  const [backend, setBackend] = useState("");
  const [model, setModel] = useState("");
  const [ragStats, setRagStats] = useState(null);
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [status, setStatus] = useState("");
  const [indexing, setIndexing] = useState(false);
  const [streamText, setStreamText] = useState("");
  const [streamSources, setStreamSources] = useState([]);
  const endRef = useRef(null);

  useEffect(() => {
    getLlmProviders().then(d => {
      const nextProviders = visibleProviders(d.providers || []);
      setProviders(nextProviders);
      const first = preferredProvider(nextProviders);
      if (first) { setBackend(first.name); setModel(preferredModel(first)); }
      else setBackend("fallback");
    }).catch(() => { setProviders([{ name:"fallback", available:true, models:[] }]); setBackend("fallback"); });
    getRagStats().then(setRagStats).catch(()=>{});
  }, []);

  useEffect(() => { endRef.current?.scrollIntoView({ behavior: "smooth" }); }, [messages, streamText, status]);

  const curProv = providers.find(p => p.name === backend);
  const models = curProv?.models || [];
  const modelOptions = (backend === "litellm" && models.length > 0)
    ? models.map(m => ({ value: m, disabled: m !== FORCED_LITELLM_MODEL }))
    : models.map(m => ({ value: m, disabled: false }));
  const pickBackend = (name) => {
    setBackend(name);
    const p = providers.find(x => x.name === name);
    if (p?.models?.length) setModel(preferredModel(p));
    else setModel("");
  };

  useEffect(() => {
    if (backend === "litellm" && model !== FORCED_LITELLM_MODEL) {
      setModel(FORCED_LITELLM_MODEL);
    }
  }, [backend, model]);

  const send = useCallback(async () => {
    const q = input.trim(); if (!q || loading) return;
    setMessages(prev => [...prev, { role:"user", content:q }]);
    setInput(""); setLoading(true); setStatus(""); setStreamText(""); setStreamSources([]);

    let finalText = "";
    let finalSources = [];
    let llmInfo = {};

    try {
      await ragChatStream(
        { ticker, question: q, llm_backend: backend || undefined, llm_model: model || undefined, language: "fr", top_k: 5 },
        (event, data) => {
          switch (event) {
            case "status":
              setStatus(data.message);
              break;
            case "sources":
              finalSources = data;
              setStreamSources(data);
              break;
            case "token":
              finalText += data.text;
              setStreamText(prev => prev + data.text);
              break;
            case "done":
              llmInfo = data;
              break;
          }
        }
      );
      setMessages(prev => [...prev, { role: "assistant", content: finalText, sources: finalSources, llm: llmInfo }]);
    } catch (err) {
      setMessages(prev => [...prev, { role: "error", content: err.message }]);
    } finally {
      setLoading(false); setStatus(""); setStreamText(""); setStreamSources([]);
    }
  }, [input, loading, ticker, backend, model]);

  const handleIndex = async () => {
    setIndexing(true);
    try {
      const r = await indexRag(ticker);
      setMessages(prev => [...prev, { role: "system", content: `Index RAG mis à jour: ${r.indexed_chunks} chunks indexés.` }]);
      setRagStats(await getRagStats());
    } catch (err) { setMessages(prev => [...prev, { role: "error", content: err.message }]); }
    finally { setIndexing(false); }
  };

  const quickPrompts = [
    `Quels sont les catalyseurs pour ${ticker} ?`,
    `Quels risques pèsent sur ${ticker} ?`,
    `Résume la situation fondamentale de ${ticker}.`,
    `Tendance technique de ${ticker} ?`,
  ];

  return (
    <div className="grid-sidebar-w">
      <Card delay={0} className="flex-col" style={{ display:"flex", flexDirection:"column", minHeight:440 }}>
        <div className="card-header">
          <Label>RAG Chat — {ticker}</Label>
          {backend && <Tag variant={backend==="fallback"?"muted":"accent"}>{backend}{model ? ` / ${model.split("/").pop().split("-").slice(0,2).join("-")}` : ""}</Tag>}
        </div>

        <div className="chat-area">
          {messages.length === 0 && !loading && (
            <div className="empty-state"><h3>Posez une question sur {ticker}</h3><p className="text-sm">Le RAG récupère les documents indexés et les envoie au LLM.</p></div>
          )}
          {messages.map((msg, i) => <Bubble key={i} msg={msg} />)}

          {/* Live streaming zone */}
          {loading && (
            <div className="bubble bubble-assistant">
              {status && (
                <div className="flex-row gap-xs" style={{ marginBottom: streamText ? 8 : 0 }}>
                  <span className="loading-pulse" style={{ fontSize: "1.1em" }}>●</span>
                  <span className="text-sm muted">{status}</span>
                </div>
              )}
              {streamSources.length > 0 && !streamText && (
                <div className="text-xs muted" style={{ marginBottom: 6 }}>
                  Sources: {streamSources.map(s => s.title).join(", ")}
                </div>
              )}
              {streamText && <div className="text-base lh-relaxed">{streamText}<span className="loading-pulse">▊</span></div>}
            </div>
          )}
          <div ref={endRef} />
        </div>

        {messages.length === 0 && !loading && (
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
            <select
              className="select input-mono"
              value={backend === "litellm" ? FORCED_LITELLM_MODEL : model}
              onChange={e => {
                if (backend !== "litellm") setModel(e.target.value);
              }}
              style={{ width:"100%", marginTop:6 }}
            >
              {backend === "litellm" && !models.includes(FORCED_LITELLM_MODEL) && (
                <option value={FORCED_LITELLM_MODEL}>{FORCED_LITELLM_MODEL} (forced)</option>
              )}
              {modelOptions.map(m => (
                <option key={m.value} value={m.value} disabled={m.disabled}>{m.value}</option>
              ))}
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
            <p style={{ marginBottom:6 }}><strong style={{ color:"var(--text)" }}>LiteLLM:</strong> provider par défaut, gateway partagé vers le modèle local</p>
            <p style={{ marginBottom:6 }}><strong style={{ color:"var(--text)" }}>Cloud:</strong> Clés API dans .env</p>
            <p style={{ marginBottom:6 }}><strong style={{ color:"var(--text)" }}>Local:</strong> utilise le modèle via LiteLLM gateway ou LMStudio</p>
            <p><strong style={{ color:"var(--text)" }}>Fallback:</strong> Contexte RAG brut</p>
          </div>
        </Card>
      </div>
    </div>
  );
}

function Bubble({ msg }) {
  const cls = msg.role === "user" ? "bubble-user" : msg.role === "error" ? "bubble-error" : msg.role === "system" ? "bubble-system" : "bubble-assistant";
  const labels = { user:"Vous", assistant:"Assistant", error:"Erreur", system:"Système" };

  /* Render text with [Source: X] highlighted */
  const renderText = (text) => {
    if (!text) return null;
    const parts = text.split(/(\[(?:Source\s*:\s*)?[^\]]+\])/g);
    return parts.map((p, i) => {
      if (/^\[/.test(p)) {
        return <span key={i} className="tag tag-accent" style={{ cursor: "default", margin: "0 2px" }}>{p}</span>;
      }
      return <span key={i}>{p}</span>;
    });
  };

  return (
    <div className={`bubble ${cls}`}>
      <div className="bubble-role">
        <span>{labels[msg.role] || msg.role}</span>
        {msg.llm?.provider && <Tag variant="accent">{msg.llm.provider}</Tag>}
      </div>
      <div className="text-base lh-relaxed">{renderText(msg.content)}</div>
      {msg.sources?.length > 0 && (
        <div className="bubble-sources">
          <div className="text-xs muted" style={{ marginBottom: 6 }}>Sources utilisées :</div>
          {msg.sources.map((s, i) => (
            <div key={i} className="source-item" style={{ marginBottom: 6 }}>
              <div className="flex-row gap-xs">
                <span className="text-accent fw-700">[{i + 1}]</span>
                {s.url ? (
                  <a href={s.url} target="_blank" rel="noopener noreferrer" className="text-accent fw-600" style={{ textDecoration: "none" }}>
                    {s.title || "Source"} ↗
                  </a>
                ) : (
                  <span className="fw-600">{s.title || "Source"}</span>
                )}
                <Tag variant="muted">{s.document_type}</Tag>
                <span className="mono text-xs text-accent">{s.score}</span>
              </div>
              {s.preview && <div className="text-xs muted" style={{ marginTop: 3 }}>{s.preview}</div>}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

