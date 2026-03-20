/**
 * Market Insights API client.
 *
 * In dev mode, Vite proxies /api/* → http://127.0.0.1:8000/*
 * In production, set VITE_API_BASE to the real API URL.
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

export const clearCache = (prefix = "") =>
  request(`/cache/clear?prefix=${encodeURIComponent(prefix)}`, { method: "POST" });

/* ━━ ETL ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ */

export const runEtl = (ticker, provider = "sample") =>
  request(`/etl/run?ticker=${encodeURIComponent(ticker)}&provider=${encodeURIComponent(provider)}`, {
    method: "POST",
  });

export const runBatchEtl = (tickers, provider = "sample") =>
  request(
    `/etl/batch?tickers=${encodeURIComponent(tickers.join(","))}&provider=${encodeURIComponent(provider)}`,
    { method: "POST" }
  );

/* ━━ Analysis ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ */

export const getFairValue = (ticker) => request(`/fair-value/${encodeURIComponent(ticker)}`);

export const getInsight = (ticker) => request(`/insights/${encodeURIComponent(ticker)}`);

export const getComparable = (ticker) => request(`/insights/${encodeURIComponent(ticker)}/comparable`);

export const getHybrid = (ticker) => request(`/insights/${encodeURIComponent(ticker)}/hybrid`);

/* ━━ Data ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ */

export const getRagSources = (ticker) => request(`/rag/sources/${encodeURIComponent(ticker)}`);

export const getFundamentals = (ticker) => request(`/fundamentals/${encodeURIComponent(ticker)}`);

export const getNews = (ticker, limit = 10) =>
  request(`/news/${encodeURIComponent(ticker)}?limit=${limit}`);

export const getMacro = () => request("/macro");

/* ━━ Aggregate loader ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ */

/**
 * Load all analysis data for a ticker in parallel.
 * Returns { hybrid, fairValue, comparable, insight, sources, fundamentals, news }.
 */
export async function loadFullAnalysis(ticker) {
  const [hybrid, fairValue, comparable, insight, sources, fundamentals, news] =
    await Promise.allSettled([
      getHybrid(ticker),
      getFairValue(ticker),
      getComparable(ticker),
      getInsight(ticker),
      getRagSources(ticker),
      getFundamentals(ticker),
      getNews(ticker),
    ]);

  return {
    hybrid: hybrid.status === "fulfilled" ? hybrid.value : null,
    fairValue: fairValue.status === "fulfilled" ? fairValue.value : null,
    comparable: comparable.status === "fulfilled" ? comparable.value : null,
    insight: insight.status === "fulfilled" ? insight.value : null,
    sources: sources.status === "fulfilled" ? sources.value : null,
    fundamentals: fundamentals.status === "fulfilled" ? fundamentals.value : null,
    news: news.status === "fulfilled" ? news.value : null,
  };
}
