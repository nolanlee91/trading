"""
indicators.py — EMA / RSI / ATR tự viết, không dùng TA-Lib hay pandas-ta.

Tự viết để kiểm soát chính xác công thức (vd RSI dùng Wilder smoothing).
Mọi hàm trả về Series cùng index với input; KHÔNG dùng dữ liệu tương lai.
"""

from __future__ import annotations

import pandas as pd


def ema(series: pd.Series, length: int) -> pd.Series:
    # EMA chuẩn: alpha = 2/(n+1). adjust=False để giống nền tảng chart.
    return series.ewm(span=length, adjust=False).mean()


def rsi(close: pd.Series, length: int = 14) -> pd.Series:
    # Wilder's RSI: smoothing bằng EMA alpha=1/n (alpha = 1/length).
    delta = close.diff()
    gain = delta.clip(lower=0.0)
    loss = (-delta).clip(lower=0.0)
    avg_gain = gain.ewm(alpha=1 / length, adjust=False).mean()
    avg_loss = loss.ewm(alpha=1 / length, adjust=False).mean()
    rs = avg_gain / avg_loss.replace(0.0, float("nan"))
    out = 100 - (100 / (1 + rs))
    # avg_loss == 0 -> RSI = 100 (toàn bộ là gain)
    out = out.where(avg_loss != 0, 100.0)
    return out


def atr(high: pd.Series, low: pd.Series, close: pd.Series, length: int = 14) -> pd.Series:
    # True Range rồi Wilder smoothing (alpha = 1/length).
    prev_close = close.shift(1)
    tr = pd.concat(
        [(high - low), (high - prev_close).abs(), (low - prev_close).abs()],
        axis=1,
    ).max(axis=1)
    return tr.ewm(alpha=1 / length, adjust=False).mean()
