"""Candlestick annotation engine.

Produces per-bar signal annotations for chart rendering:
- gap_up, gap_down
- pullback_to_sma (20, 50)
- breakout (20d high)
- breakdown (20d low)
- bullish/bearish engulfing
- hammer, shooting_star, doji
- volume_spike
- RSI extremes
- SMA crossovers (golden cross, death cross)

Returns a list of OHLCV bars augmented with signal annotations.
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

        # ── Gap ──────────────────────────────────────────────────
        if i > 0:
            if l > ph:
                gap_pct = round((l - ph) / ph * 100, 2)
                signals.append({"type": "gap_up", "label": f"Gap haussier +{gap_pct}%", "severity": "bullish", "value": gap_pct})
            if h < pl:
                gap_pct = round((pl - h) / pl * 100, 2)
                signals.append({"type": "gap_down", "label": f"Gap baissier -{gap_pct}%", "severity": "bearish", "value": gap_pct})

        # ── Pullback to SMA ──────────────────────────────────────
        sma20 = float(row.get("sma_20", 0))
        sma50 = float(row.get("sma_50", 0))
        if sma20 > 0 and abs(c - sma20) / max(c, 1e-9) <= 0.008:
            signals.append({"type": "pullback_sma20", "label": "Pullback SMA 20", "severity": "neutral", "value": round(sma20, 2)})
        if sma50 > 0 and abs(c - sma50) / max(c, 1e-9) <= 0.008:
            signals.append({"type": "pullback_sma50", "label": "Pullback SMA 50", "severity": "neutral", "value": round(sma50, 2)})

        # ── Breakout / Breakdown ─────────────────────────────────
        if i >= 20:
            hi20 = float(df["high"].iloc[max(0, i - 20):i].max())
            lo20 = float(df["low"].iloc[max(0, i - 20):i].min())
            if c > hi20:
                signals.append({"type": "breakout_20d", "label": "Breakout 20j", "severity": "bullish", "value": round(hi20, 2)})
            if c < lo20:
                signals.append({"type": "breakdown_20d", "label": "Breakdown 20j", "severity": "bearish", "value": round(lo20, 2)})

        # ── Candle patterns ──────────────────────────────────────
        upper_shadow = h - max(o, c)
        lower_shadow = min(o, c) - l

        # Engulfing
        if i > 0:
            if c > o and pc < po and c >= po and o <= pc:
                signals.append({"type": "bullish_engulfing", "label": "Avalement haussier", "severity": "bullish"})
            if c < o and pc > po and c <= po and o >= pc:
                signals.append({"type": "bearish_engulfing", "label": "Avalement baissier", "severity": "bearish"})

        # Hammer (small body at top, long lower shadow)
        if body_pct < 0.30 and lower_shadow > 2 * body and upper_shadow < body * 0.5 and c >= o:
            signals.append({"type": "hammer", "label": "Marteau", "severity": "bullish"})

        # Shooting star (small body at bottom, long upper shadow)
        if body_pct < 0.30 and upper_shadow > 2 * body and lower_shadow < body * 0.5 and c <= o:
            signals.append({"type": "shooting_star", "label": "Étoile filante", "severity": "bearish"})

        # Doji
        if body_pct < 0.08:
            signals.append({"type": "doji", "label": "Doji", "severity": "neutral"})

        # Morning / evening star (3-bar patterns)
        if i >= 2:
            p2o, p2c = float(prev2["open"]), float(prev2["close"])
            # Morning star: bearish → small body → bullish
            if p2c < p2o and abs(pc - po) / max(abs(p2c - p2o), 1e-9) < 0.3 and c > o and c > (p2o + p2c) / 2:
                signals.append({"type": "morning_star", "label": "Étoile du matin", "severity": "bullish"})
            # Evening star
            if p2c > p2o and abs(pc - po) / max(abs(p2c - p2o), 1e-9) < 0.3 and c < o and c < (p2o + p2c) / 2:
                signals.append({"type": "evening_star", "label": "Étoile du soir", "severity": "bearish"})

        # ── Volume spike ─────────────────────────────────────────
        if i >= 20:
            vol_avg = float(df["volume"].iloc[max(0, i - 20):i].mean())
            if vol_avg > 0 and vol >= 1.8 * vol_avg:
                signals.append({"type": "volume_spike", "label": f"Volume ×{vol / vol_avg:.1f}", "severity": "neutral", "value": round(vol / vol_avg, 1)})

        # ── RSI extremes ─────────────────────────────────────────
        rsi = float(row.get("rsi_14", 50))
        if rsi >= 75:
            signals.append({"type": "rsi_overbought", "label": f"RSI surachat ({rsi:.0f})", "severity": "bearish", "value": round(rsi, 1)})
        elif rsi <= 25:
            signals.append({"type": "rsi_oversold", "label": f"RSI survente ({rsi:.0f})", "severity": "bullish", "value": round(rsi, 1)})

        # ── SMA crossovers ───────────────────────────────────────
        if i > 0 and sma20 > 0 and sma50 > 0:
            prev_sma20 = float(prev.get("sma_20", 0))
            prev_sma50 = float(prev.get("sma_50", 0))
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
