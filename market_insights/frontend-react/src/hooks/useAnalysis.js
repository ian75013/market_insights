import { useState, useEffect, useCallback } from "react";
import { loadFullAnalysis, runEtl, getMacro } from "../services/api";

/**
 * Hook: loads all analysis data for a ticker (including candlestick).
 * Returns { data, macro, loading, error, reload, runPipeline }
 */
export function useAnalysis(ticker) {
  const [data, setData] = useState(null);
  const [macro, setMacro] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const load = useCallback(async () => {
    if (!ticker) return;
    setLoading(true);
    setError(null);
    try {
      const result = await loadFullAnalysis(ticker);
      setData(result);
    } catch (err) {
      setError(err.message || "Erreur de chargement");
    } finally {
      setLoading(false);
    }
  }, [ticker]);

  const loadMacro = useCallback(async () => {
    try { setMacro(await getMacro()); } catch { /* non-critical */ }
  }, []);

  useEffect(() => { load(); loadMacro(); }, [load, loadMacro]);

  const runPipeline = useCallback(async (provider = "sample") => {
    setLoading(true);
    setError(null);
    try {
      await runEtl(ticker, provider);
      await load();
    } catch (err) {
      setError(err.message || "Erreur ETL");
      setLoading(false);
    }
  }, [ticker, load]);

  return { data, macro, loading, error, reload: load, runPipeline };
}
