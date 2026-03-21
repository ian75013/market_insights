import { useState, useEffect, useRef, useCallback } from "react";
import { T } from "../styles/theme";
import { Card, Label, Tag, Skeleton } from "./ui";
import { ragChat, getLlmProviders, indexRag, getRagStats } from "../services/api";

/* ── Severity / provider color mapping ───────────────────────────── */
const PROV_COLORS = {
  openai: "#10a37f",
  anthropic: "#d97706",
  mistral: "#f97316",
  groq: "#6366f1",
  ollama: "#22d3ee",
  lmstudio: "#a78bfa",
  fallback: T.muted,
};

export function RagChatTab({ ticker }) {
  const [providers, setProviders] = useState([]);
  const [selectedBackend, setSelectedBackend] = useState("");
  const [selectedModel, setSelectedModel] = useState("");
  const [ragStats, setRagStats] = useState(null);
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [indexing, setIndexing] = useState(false);
  const chatEndRef = useRef(null);

  /* ── Load providers on mount ───────────────────────────────────── */
  useEffect(() => {
    getLlmProviders()
      .then((data) => {
        setProviders(data.providers || []);
        /* Auto-select first available provider */
        const first = (data.providers || []).find((p) => p.available && p.name !== "fallback");
        if (first) {
          setSelectedBackend(first.name);
          if (first.models?.length) setSelectedModel(first.models[0]);
        } else {
          setSelectedBackend("fallback");
        }
      })
      .catch(() => {
        setProviders([{ name: "fallback", available: true, models: [] }]);
        setSelectedBackend("fallback");
      });

    getRagStats().then(setRagStats).catch(() => {});
  }, []);

  /* ── Scroll to bottom ──────────────────────────────────────────── */
  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  /* ── Get models for selected provider ──────────────────────────── */
  const currentProvider = providers.find((p) => p.name === selectedBackend);
  const availableModels = currentProvider?.models || [];

  /* ── Handle provider change ────────────────────────────────────── */
  const handleBackendChange = (name) => {
    setSelectedBackend(name);
    const prov = providers.find((p) => p.name === name);
    if (prov?.models?.length) {
      setSelectedModel(prov.models[0]);
    } else {
      setSelectedModel("");
    }
  };

  /* ── Send message ──────────────────────────────────────────────── */
  const send = useCallback(async () => {
    const q = input.trim();
    if (!q || loading) return;

    const userMsg = { role: "user", content: q, timestamp: new Date().toISOString() };
    setMessages((prev) => [...prev, userMsg]);
    setInput("");
    setLoading(true);

    try {
      const resp = await ragChat({
        ticker,
        question: q,
        llm_backend: selectedBackend || undefined,
        llm_model: selectedModel || undefined,
        language: "fr",
        top_k: 5,
      });

      const assistantMsg = {
        role: "assistant",
        content: resp.answer,
        sources: resp.sources,
        llm: resp.llm,
        timestamp: resp.generated_at,
      };
      setMessages((prev) => [...prev, assistantMsg]);
    } catch (err) {
      setMessages((prev) => [
        ...prev,
        { role: "error", content: `Erreur: ${err.message}`, timestamp: new Date().toISOString() },
      ]);
    } finally {
      setLoading(false);
    }
  }, [input, loading, ticker, selectedBackend, selectedModel]);

  /* ── Index RAG ─────────────────────────────────────────────────── */
  const handleIndex = async () => {
    setIndexing(true);
    try {
      const result = await indexRag(ticker);
      setMessages((prev) => [
        ...prev,
        {
          role: "system",
          content: `Index RAG mis à jour pour ${ticker}: ${result.indexed_chunks} chunks indexés.`,
          timestamp: new Date().toISOString(),
        },
      ]);
      const stats = await getRagStats();
      setRagStats(stats);
    } catch (err) {
      setMessages((prev) => [
        ...prev,
        { role: "error", content: `Erreur indexation: ${err.message}`, timestamp: new Date().toISOString() },
      ]);
    } finally {
      setIndexing(false);
    }
  };

  /* ── Quick prompts ─────────────────────────────────────────────── */
  const quickPrompts = [
    `Quels sont les principaux catalyseurs pour ${ticker} ?`,
    `Quels risques pèsent sur ${ticker} actuellement ?`,
    `Résume la situation fondamentale de ${ticker}.`,
    `Quelle est la tendance technique de ${ticker} ?`,
  ];

  return (
    <div style={{ display: "grid", gridTemplateColumns: "1fr 300px", gap: 14 }}>
      {/* ── Left: Chat ────────────────────────────────────────── */}
      <div style={{ display: "flex", flexDirection: "column", gap: 14 }}>
        {/* Chat messages */}
        <Card delay={0} style={{ flex: 1, display: "flex", flexDirection: "column", minHeight: 400 }}>
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 10 }}>
            <Label>RAG Chat — {ticker}</Label>
            <div style={{ display: "flex", gap: 6, alignItems: "center" }}>
              {selectedBackend && (
                <Tag color={PROV_COLORS[selectedBackend] || T.muted}>
                  {selectedBackend}
                  {selectedModel ? ` / ${selectedModel.split("/").pop().split("-").slice(0, 2).join("-")}` : ""}
                </Tag>
              )}
            </div>
          </div>

          {/* Messages area */}
          <div
            style={{
              flex: 1,
              overflowY: "auto",
              display: "flex",
              flexDirection: "column",
              gap: 10,
              marginBottom: 12,
              maxHeight: 450,
              padding: "4px 0",
            }}
          >
            {messages.length === 0 && (
              <div style={{ textAlign: "center", padding: 40, color: T.muted }}>
                <div style={{ fontSize: 14, marginBottom: 10 }}>Posez une question sur {ticker}</div>
                <div style={{ fontSize: 11 }}>
                  Le RAG récupère les documents indexés et les envoie au LLM sélectionné pour générer une réponse sourcée.
                </div>
              </div>
            )}

            {messages.map((msg, i) => (
              <MessageBubble key={i} msg={msg} />
            ))}

            {loading && (
              <div style={{ padding: "12px 16px", background: T.panel2, borderRadius: 10, maxWidth: "80%" }}>
                <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
                  <span style={{ animation: "pulse 1.2s infinite", color: T.accent, fontSize: 12 }}>●</span>
                  <span style={{ fontSize: 12, color: T.muted }}>Recherche dans les documents et génération...</span>
                </div>
              </div>
            )}

            <div ref={chatEndRef} />
          </div>

          {/* Quick prompts */}
          {messages.length === 0 && (
            <div style={{ display: "flex", flexWrap: "wrap", gap: 6, marginBottom: 10 }}>
              {quickPrompts.map((q, i) => (
                <button
                  key={i}
                  onClick={() => { setInput(q); }}
                  style={{
                    padding: "6px 12px",
                    borderRadius: 8,
                    border: `1px solid ${T.border}`,
                    background: T.panel2,
                    color: T.muted,
                    fontSize: 11,
                    cursor: "pointer",
                    transition: "all .15s",
                  }}
                >
                  {q}
                </button>
              ))}
            </div>
          )}

          {/* Input bar */}
          <div style={{ display: "flex", gap: 8 }}>
            <input
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && send()}
              placeholder={`Posez une question sur ${ticker}...`}
              disabled={loading}
              style={{
                flex: 1,
                padding: "10px 14px",
                borderRadius: 8,
                border: `1px solid ${T.border}`,
                background: T.panel2,
                color: T.text,
                fontSize: 13,
                fontFamily: T.sans,
                outline: "none",
              }}
            />
            <button
              onClick={send}
              disabled={loading || !input.trim()}
              style={{
                padding: "10px 20px",
                borderRadius: 8,
                border: "none",
                background: loading ? T.panel2 : `linear-gradient(135deg, #1d4ed8, #0891b2)`,
                color: "#fff",
                fontSize: 13,
                fontWeight: 700,
                cursor: loading ? "wait" : "pointer",
                fontFamily: T.sans,
                opacity: loading || !input.trim() ? 0.5 : 1,
              }}
            >
              Envoyer
            </button>
          </div>
        </Card>
      </div>

      {/* ── Right: Config sidebar ─────────────────────────────── */}
      <div style={{ display: "flex", flexDirection: "column", gap: 14 }}>
        {/* Provider selector */}
        <Card delay={60}>
          <Label>LLM Provider</Label>
          <div style={{ display: "flex", flexDirection: "column", gap: 4, marginTop: 8 }}>
            {providers.map((p) => (
              <button
                key={p.name}
                onClick={() => p.available && handleBackendChange(p.name)}
                style={{
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "space-between",
                  padding: "8px 10px",
                  borderRadius: 6,
                  border: `1px solid ${selectedBackend === p.name ? (PROV_COLORS[p.name] || T.accent) + "55" : T.border}`,
                  background: selectedBackend === p.name ? (PROV_COLORS[p.name] || T.accent) + "12" : T.panel2,
                  color: p.available ? T.text : T.muted,
                  cursor: p.available ? "pointer" : "not-allowed",
                  opacity: p.available ? 1 : 0.5,
                  fontSize: 12,
                  fontFamily: T.sans,
                  textAlign: "left",
                }}
              >
                <div style={{ display: "flex", alignItems: "center", gap: 6 }}>
                  <span
                    style={{
                      width: 7,
                      height: 7,
                      borderRadius: "50%",
                      background: p.available ? (PROV_COLORS[p.name] || T.green) : T.muted,
                    }}
                  />
                  <span style={{ fontWeight: 600 }}>{p.name}</span>
                </div>
                {p.available ? (
                  <span style={{ fontSize: 9, color: T.muted }}>{p.models?.length || 0} models</span>
                ) : (
                  <span style={{ fontSize: 9, color: T.red }}>offline</span>
                )}
              </button>
            ))}
          </div>
        </Card>

        {/* Model selector */}
        {availableModels.length > 0 && (
          <Card delay={120}>
            <Label>Modèle</Label>
            <select
              value={selectedModel}
              onChange={(e) => setSelectedModel(e.target.value)}
              style={{
                width: "100%",
                padding: "8px 10px",
                borderRadius: 6,
                border: `1px solid ${T.border}`,
                background: T.panel2,
                color: T.text,
                fontSize: 11,
                fontFamily: T.mono,
                marginTop: 6,
              }}
            >
              {availableModels.map((m) => (
                <option key={m} value={m}>
                  {m}
                </option>
              ))}
            </select>
          </Card>
        )}

        {/* RAG Index */}
        <Card delay={180}>
          <Label>Index RAG</Label>
          <div style={{ marginTop: 6 }}>
            {ragStats && (
              <div style={{ fontSize: 11, color: T.muted, marginBottom: 8 }}>
                <div>Tickers indexés: {ragStats.tickers_indexed?.join(", ") || "aucun"}</div>
                <div>Total chunks: {ragStats.total_chunks || 0}</div>
              </div>
            )}
            <button
              onClick={handleIndex}
              disabled={indexing}
              style={{
                width: "100%",
                padding: "8px 12px",
                borderRadius: 6,
                border: `1px solid ${T.border}`,
                background: T.panel2,
                color: indexing ? T.muted : T.text,
                fontSize: 11,
                fontWeight: 600,
                cursor: indexing ? "wait" : "pointer",
                fontFamily: T.sans,
              }}
            >
              {indexing ? "Indexation en cours..." : `Réindexer ${ticker}`}
            </button>
          </div>
        </Card>

        {/* Guide */}
        <Card delay={240}>
          <Label>Guide</Label>
          <div style={{ fontSize: 11, color: T.muted, lineHeight: 1.6, marginTop: 4 }}>
            <p style={{ marginBottom: 6 }}>
              <strong style={{ color: T.text }}>Cloud:</strong> Configurez les clés API dans <code>.env</code> (OPENAI_API_KEY, ANTHROPIC_API_KEY, etc.)
            </p>
            <p style={{ marginBottom: 6 }}>
              <strong style={{ color: T.text }}>Local:</strong> Lancez Ollama (<code>ollama serve</code>) ou LMStudio, ils seront détectés automatiquement.
            </p>
            <p>
              <strong style={{ color: T.text }}>Fallback:</strong> Sans LLM, le contexte RAG est retourné tel quel.
            </p>
          </div>
        </Card>
      </div>
    </div>
  );
}

/* ── Message bubble component ────────────────────────────────────── */

function MessageBubble({ msg }) {
  const isUser = msg.role === "user";
  const isError = msg.role === "error";
  const isSystem = msg.role === "system";

  const bgColor = isUser
    ? T.accent + "18"
    : isError
    ? T.red + "15"
    : isSystem
    ? T.amber + "12"
    : T.panel2;

  const borderColor = isUser ? T.accent + "40" : isError ? T.red + "30" : isSystem ? T.amber + "30" : T.border;

  return (
    <div
      style={{
        alignSelf: isUser ? "flex-end" : "flex-start",
        maxWidth: isUser ? "70%" : "90%",
        padding: "10px 14px",
        borderRadius: 10,
        background: bgColor,
        border: `1px solid ${borderColor}`,
      }}
    >
      {/* Role label */}
      <div style={{ fontSize: 9, color: T.muted, marginBottom: 4, display: "flex", justifyContent: "space-between" }}>
        <span>{isUser ? "Vous" : isError ? "Erreur" : isSystem ? "Système" : "Assistant"}</span>
        {msg.llm && (
          <Tag color={PROV_COLORS[msg.llm.provider] || T.muted}>
            {msg.llm.provider}/{msg.llm.model?.split("/").pop()?.slice(0, 20)}
          </Tag>
        )}
      </div>

      {/* Content */}
      <div style={{ fontSize: 13, lineHeight: 1.6, whiteSpace: "pre-wrap", color: isError ? T.red : T.text }}>
        {msg.content}
      </div>

      {/* Sources */}
      {msg.sources?.length > 0 && (
        <div style={{ marginTop: 8, borderTop: `1px solid ${T.border}`, paddingTop: 8 }}>
          <div style={{ fontSize: 9, color: T.muted, marginBottom: 4 }}>Sources citées:</div>
          <div style={{ display: "flex", flexDirection: "column", gap: 3 }}>
            {msg.sources.map((s, i) => (
              <div key={i} style={{ fontSize: 10, display: "flex", alignItems: "center", gap: 6 }}>
                <span style={{ color: T.accent, fontWeight: 600 }}>[{i + 1}]</span>
                <span style={{ color: T.muted }}>{s.title}</span>
                <Tag color={T.muted}>{s.document_type}</Tag>
                <span style={{ fontFamily: T.mono, fontSize: 9, color: T.accent }}>{s.score}</span>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
