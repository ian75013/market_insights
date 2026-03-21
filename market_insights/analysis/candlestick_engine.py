"""Candlestick annotation engine — calibré pour données réelles.

Seuils ajustés pour ne déclencher que les signaux réellement significatifs
sur des données de marché live (Yahoo Finance, Stooq, etc.).
"""

from __future__ import annotations

import pandas as pd
import numpy as np

from market_insights.etl.transformers.features import compute_features


def annotate_candlesticks(df: pd.DataFrame) -> list[dict]:
    """Take a raw price DataFrame and return annotated candlestick data."""
    df = compute_features(df.copy())
    df = df.sort_values("date").reset_index(drop=True)

    bars = []
    for i in range(len(df)):
        row = df.iloc[i]
        prev = df.iloc[i - 1] if i > 0 else row
        prev2 = df.iloc[i - 2] if i > 1 else prev

        o, h, l, c = float(row["open"]), float(row["high"]), float(row["low"]), float(row["close"])
        po, ph, pl, pc = float(prev["open"]), float(prev["high"]), float(prev["low"]), float(prev["close"])
        vol = float(row["volume"])
        body = abs(c - o)
        rng = max(h - l, 1e-9)
        body_pct = body / rng

        signals: list[dict] = []

        # ── Gap (seuil 0.5% minimum pour être significatif) ──────
        if i > 0:
            if l > ph and (l - ph) / ph > 0.005:
                gap_pct = round((l - ph) / ph * 100, 2)
                signals.append({"type": "gap_up", "label": f"Gap haussier +{gap_pct}%", "severity": "bullish", "value": gap_pct})
            if h < pl and (pl - h) / pl > 0.005:
                gap_pct = round((pl - h) / pl * 100, 2)
                signals.append({"type": "gap_down", "label": f"Gap baissier -{gap_pct}%", "severity": "bearish", "value": gap_pct})

        # ── Pullback to SMA (contact précis ≤ 0.3%) ─────────────
        sma20 = float(row.get("sma_20", 0))
        sma50 = float(row.get("sma_50", 0))
        if i >= 20 and sma20 > 0:
            # Le prix doit toucher la SMA par le haut ou le bas (mèche)
            if l <= sma20 <= h and abs(c - sma20) / max(c, 1e-9) <= 0.003:
                signals.append({"type": "pullback_sma20", "label": "Pullback SMA 20", "severity": "neutral", "value": round(sma20, 2)})
        if i >= 50 and sma50 > 0:
            if l <= sma50 <= h and abs(c - sma50) / max(c, 1e-9) <= 0.003:
                signals.append({"type": "pullback_sma50", "label": "Pullback SMA 50", "severity": "neutral", "value": round(sma50, 2)})

        # ── Breakout / Breakdown (close au-delà du range, pas juste proche) ─
        if i >= 20:
            hi20 = float(df["high"].iloc[max(0, i - 20):i].max())
            lo20 = float(df["low"].iloc[max(0, i - 20):i].min())
            if c > hi20 and (c - hi20) / hi20 > 0.002:
                signals.append({"type": "breakout_20d", "label": "Breakout 20j", "severity": "bullish", "value": round(hi20, 2)})
            if c < lo20 and (lo20 - c) / lo20 > 0.002:
                signals.append({"type": "breakdown_20d", "label": "Breakdown 20j", "severity": "bearish", "value": round(lo20, 2)})

        # ── Engulfing (vrai engulfing : corps englobe corps) ─────
        if i > 0:
            prev_body = abs(pc - po)
            if (c > o and pc < po                         # bull après bear
                    and o <= min(pc, po) and c >= max(pc, po)  # corps englobe
                    and body > prev_body * 1.1             # plus grand de 10%
                    and body_pct > 0.5):                   # corps substantiel
                signals.append({"type": "bullish_engulfing", "label": "Avalement haussier", "severity": "bullish"})
            if (c < o and pc > po
                    and o >= max(pc, po) and c <= min(pc, po)
                    and body > prev_body * 1.1
                    and body_pct > 0.5):
                signals.append({"type": "bearish_engulfing", "label": "Avalement baissier", "severity": "bearish"})

        # ── Hammer (après une baisse d'au moins 3 jours) ─────────
        lower_shadow = min(o, c) - l
        upper_shadow = h - max(o, c)
        if i >= 3:
            recent_trend = float(df["close"].iloc[max(0, i-3)] - c)
            if (body_pct < 0.25
                    and lower_shadow > 2.5 * body
                    and upper_shadow < body * 0.3
                    and recent_trend > 0):  # prix en baisse avant
                signals.append({"type": "hammer", "label": "Marteau", "severity": "bullish"})

        # ── Shooting star (après une hausse d'au moins 3 jours) ──
        if i >= 3:
            recent_trend = float(c - df["close"].iloc[max(0, i-3)])
            if (body_pct < 0.25
                    and upper_shadow > 2.5 * body
                    and lower_shadow < body * 0.3
                    and recent_trend > 0):  # prix en hausse avant
                signals.append({"type": "shooting_star", "label": "Étoile filante", "severity": "bearish"})

        # ── Doji (corps < 5% du range ET range significatif) ─────
        avg_range = float(df["high"].iloc[max(0,i-10):i+1].mean() - df["low"].iloc[max(0,i-10):i+1].mean()) if i >= 2 else rng
        if body_pct < 0.05 and rng > avg_range * 0.5:
            signals.append({"type": "doji", "label": "Doji", "severity": "neutral"})

        # ── Morning / Evening star (conditions strictes) ─────────
        if i >= 2:
            p2o, p2h, p2l, p2c = float(prev2["open"]), float(prev2["high"]), float(prev2["low"]), float(prev2["close"])
            p2_body = abs(p2c - p2o)
            prev_body_small = abs(pc - po)
            # Morning star
            if (p2c < p2o and p2_body / max(p2h - p2l, 1e-9) > 0.5       # J-2 forte baissière
                    and prev_body_small < p2_body * 0.3                     # J-1 petit corps
                    and c > o and body > p2_body * 0.5                      # J0 forte haussière
                    and c > (p2o + p2c) / 2):                               # close dépasse milieu J-2
                signals.append({"type": "morning_star", "label": "Étoile du matin", "severity": "bullish"})
            # Evening star
            if (p2c > p2o and p2_body / max(p2h - p2l, 1e-9) > 0.5
                    and prev_body_small < p2_body * 0.3
                    and c < o and body > p2_body * 0.5
                    and c < (p2o + p2c) / 2):
                signals.append({"type": "evening_star", "label": "Étoile du soir", "severity": "bearish"})

        # ── Volume spike (seuil 2.5× au lieu de 1.8×) ───────────
        if i >= 20:
            vol_avg = float(df["volume"].iloc[max(0, i - 20):i].mean())
            if vol_avg > 0 and vol >= 2.5 * vol_avg:
                signals.append({"type": "volume_spike", "label": f"Volume ×{vol / vol_avg:.1f}", "severity": "neutral", "value": round(vol / vol_avg, 1)})

        # ── RSI extremes (80/20 au lieu de 75/25) ────────────────
        rsi = float(row.get("rsi_14", 50))
        if rsi >= 80:
            signals.append({"type": "rsi_overbought", "label": f"RSI surachat ({rsi:.0f})", "severity": "bearish", "value": round(rsi, 1)})
        elif rsi <= 20:
            signals.append({"type": "rsi_oversold", "label": f"RSI survente ({rsi:.0f})", "severity": "bullish", "value": round(rsi, 1)})

        # ── SMA crossovers ───────────────────────────────────────
        if i > 0 and sma20 > 0 and sma50 > 0:
            prev_sma20 = float(prev.get("sma_20", 0))
            prev_sma50 = float(prev.get("sma_50", 0))
            if prev_sma20 > 0 and prev_sma50 > 0:
                if prev_sma20 <= prev_sma50 and sma20 > sma50:
                    signals.append({"type": "golden_cross", "label": "Golden Cross (SMA 20/50)", "severity": "bullish"})
                if prev_sma20 >= prev_sma50 and sma20 < sma50:
                    signals.append({"type": "death_cross", "label": "Death Cross (SMA 20/50)", "severity": "bearish"})

        bar = {
            "date": row["date"].isoformat() if hasattr(row["date"], "isoformat") else str(row["date"]),
            "open": round(o, 2),
            "high": round(h, 2),
            "low": round(l, 2),
            "close": round(c, 2),
            "volume": round(vol),
            "sma_20": round(sma20, 2) if sma20 else None,
            "sma_50": round(sma50, 2) if sma50 else None,
            "sma_200": round(float(row.get("sma_200", 0)), 2) or None,
            "rsi_14": round(rsi, 2),
            "signals": signals,
        }
        bars.append(bar)

    return bars
