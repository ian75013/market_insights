/**
 * Market Insights API client v4.
 * Vite proxies /api/* → http://127.0.0.1:8000/*
 */

const BASE = import.meta.env.VITE_API_BASE || "/api";

async function request(path, options = {}) {
  const url = `${BASE}${path}`;
  const res = await fetch(url, {
    headers: { "Content-Type": "application/json", ...options.headers },
    ...options,
  });
  if (!res.ok) {
    const detail = await res.json().catch(() => ({}));
    throw new Error(detail?.detail || `HTTP ${res.status}`);
  }
  return res.json();
}

/* ━━ System ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ */
export const getHealth = () => request("/health");
export const getSources = () => request("/sources");
export const getProviders = () => request("/providers");
export const getCacheStats = () => request("/cache/stats");
export const clearCache = (prefix = "") => request(`/cache/clear?prefix=${encodeURIComponent(prefix)}`, { method: "POST" });

/* ━━ ETL ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ */
export const runEtl = (ticker, provider = "sample") => request(`/etl/run?ticker=${encodeURIComponent(ticker)}&provider=${encodeURIComponent(provider)}`, { method: "POST" });
export const runBatchEtl = (tickers, provider = "sample") => request(`/etl/batch?tickers=${encodeURIComponent(tickers.join(","))}&provider=${encodeURIComponent(provider)}`, { method: "POST" });

/* ━━ Analysis ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ */
export const getFairValue = (ticker) => request(`/fair-value/${encodeURIComponent(ticker)}`);
export const getInsight = (ticker) => request(`/insights/${encodeURIComponent(ticker)}`);
export const getComparable = (ticker) => request(`/insights/${encodeURIComponent(ticker)}/comparable`);
export const getHybrid = (ticker) => request(`/insights/${encodeURIComponent(ticker)}/hybrid`);

/* ━━ Candlestick ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ */
export const getCandlestick = (ticker) => request(`/chart/candlestick/${encodeURIComponent(ticker)}`);

/* ━━ Data ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ */
export const getRagSources = (ticker) => request(`/rag/sources/${encodeURIComponent(ticker)}`);
export const getFundamentals = (ticker) => request(`/fundamentals/${encodeURIComponent(ticker)}`);
export const getNews = (ticker, limit = 10) => request(`/news/${encodeURIComponent(ticker)}?limit=${limit}`);
export const getMacro = () => request("/macro");

/* ━━ LLM / RAG Chat ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ */
export const getLlmProviders = () => request("/llm/providers");
export const ragChat = ({ ticker, question, llm_backend, llm_model, language = "fr", top_k = 5 }) =>
  request("/llm/chat", {
    method: "POST",
    body: JSON.stringify({ ticker, question, llm_backend, llm_model, language, top_k }),
  });
export const indexRag = (ticker) => request(`/rag/index/${encodeURIComponent(ticker)}`, { method: "POST" });
export const getRagStats = () => request("/rag/stats");

/* ━━ Aggregate loader ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ */
export async function loadFullAnalysis(ticker) {
  const [hybrid, fairValue, comparable, insight, sources, fundamentals, news, candlestick] =
    await Promise.allSettled([
      getHybrid(ticker), getFairValue(ticker), getComparable(ticker),
      getInsight(ticker), getRagSources(ticker), getFundamentals(ticker),
      getNews(ticker), getCandlestick(ticker),
    ]);
  return {
    hybrid: hybrid.status === "fulfilled" ? hybrid.value : null,
    fairValue: fairValue.status === "fulfilled" ? fairValue.value : null,
    comparable: comparable.status === "fulfilled" ? comparable.value : null,
    insight: insight.status === "fulfilled" ? insight.value : null,
    sources: sources.status === "fulfilled" ? sources.value : null,
    fundamentals: fundamentals.status === "fulfilled" ? fundamentals.value : null,
    news: news.status === "fulfilled" ? news.value : null,
    candlestick: candlestick.status === "fulfilled" ? candlestick.value : null,
  };
}

/* ━━ Streaming chat (SSE) ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ */
export async function ragChatStream({ ticker, question, llm_backend, llm_model, language = "fr", top_k = 5 }, onEvent) {
  const url = `${BASE}/llm/chat/stream`;
  const res = await fetch(url, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ ticker, question, llm_backend, llm_model, language, top_k }),
  });
  if (!res.ok) {
    const detail = await res.json().catch(() => ({}));
    throw new Error(detail?.detail || `HTTP ${res.status}`);
  }
  const reader = res.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });
    const lines = buffer.split("\n");
    buffer = lines.pop() || "";
    let eventType = "";
    for (const line of lines) {
      if (line.startsWith("event: ")) {
        eventType = line.slice(7).trim();
      } else if (line.startsWith("data: ") && eventType) {
        try {
          const data = JSON.parse(line.slice(6));
          onEvent(eventType, data);
        } catch { /* skip malformed */ }
        eventType = "";
      }
    }
  }
}
