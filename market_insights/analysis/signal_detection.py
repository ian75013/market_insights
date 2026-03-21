from __future__ import annotations

import pandas as pd


def detect_signals(df: pd.DataFrame) -> dict:
    latest = df.iloc[-1]
    prev = df.iloc[-2] if len(df) > 1 else latest

    close = float(latest["close"])
    open_ = float(latest["open"])
    high = float(latest["high"])
    low = float(latest["low"])
    prev_close = float(prev["close"])

    bullish_candle = close > open_ and (close - open_) > 0.4 * max(high - low, 1e-9)
    bearish_candle = close < open_ and (open_ - close) > 0.4 * max(high - low, 1e-9)
    bullish_engulfing = (
        close > open_
        and prev_close < float(prev["open"])
        and close >= float(prev["open"])
    )

    breakout_20d = close >= float(df["high"].tail(20).max()) * 0.997
    pullback_to_sma20 = abs(close - float(latest["sma_20"])) / max(close, 1e-9) <= 0.01
    excess_rsi = float(latest["rsi_14"]) >= 70
    oversold_rsi = float(latest["rsi_14"]) <= 30
    volume_spike = float(latest["volume"]) >= 1.5 * float(df["volume"].tail(20).mean())
    gap_up = float(latest["low"]) > float(prev["high"])
    gap_down = float(latest["high"]) < float(prev["low"])

    patterns: list[str] = []
    candles: list[str] = []

    if breakout_20d:
        patterns.append("proximité plus haut 20 séances")
    if pullback_to_sma20:
        patterns.append("pullback proche moyenne mobile 20")
    if volume_spike:
        patterns.append("accélération des volumes")
    if gap_up:
        patterns.append("gap haussier")
    if gap_down:
        patterns.append("gap baissier")

    if bullish_engulfing:
        candles.append("avalement haussier")
    elif bullish_candle:
        candles.append("bougie haussière large")
    elif bearish_candle:
        candles.append("bougie baissière large")

    if excess_rsi:
        candles.append("excès haussier RSI")
    if oversold_rsi:
        candles.append("excès baissier RSI")

    return {
        "patterns": patterns,
        "candles": candles,
        "flags": {
            "breakout_20d": breakout_20d,
            "pullback_to_sma20": pullback_to_sma20,
            "volume_spike": volume_spike,
            "gap_up": gap_up,
            "gap_down": gap_down,
            "excess_rsi": excess_rsi,
            "oversold_rsi": oversold_rsi,
        },
    }
