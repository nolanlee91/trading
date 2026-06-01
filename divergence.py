"""
divergence.py — phân kỳ RSI khung 15m (mean-reversion / đảo chiều).

Định nghĩa CHỐT CỨNG (không vặn để khỏi overfit):
  - Pivot low  = low thấp nhất trong cửa sổ ±k nến  -> xác nhận tại bar idx+k.
  - Pivot high = high cao nhất trong cửa sổ ±k nến  -> xác nhận tại bar idx+k.
  - Phân kỳ TĂNG (long):  giá đáy thấp hơn  + RSI đáy CAO hơn.
  - Phân kỳ GIẢM (short): giá đỉnh cao hơn  + RSI đỉnh THẤP hơn.
  So với pivot LIỀN TRƯỚC cùng loại, cách nhau <= max_gap nến.

Chống look-ahead: pivot tại idx chỉ biết được sau k nến tương lai, nên tín hiệu
chỉ bắn ở bar c = idx+k (đã thấy đủ k nến). backtest vào lệnh ở open nến c+1.
"""

from __future__ import annotations

import pandas as pd

from indicators import atr, rsi


def build_divergence_signals(df15: pd.DataFrame, cfg: dict) -> pd.DataFrame:
    d = cfg["divergence"]
    k = d["pivot_k"]
    max_gap = d["max_gap"]
    w = 2 * k + 1

    df = df15.copy().reset_index(drop=True)
    df["rsi"] = rsi(df["close"], d["rsi_len"])
    df["atr"] = atr(df["high"], df["low"], df["close"], d["atr_len"])

    # Pivot: cực trị trong cửa sổ trung tâm ±k (center=True). NaN ở rìa -> False.
    piv_low = df["low"] == df["low"].rolling(w, center=True).min()
    piv_high = df["high"] == df["high"].rolling(w, center=True).max()

    n = len(df)
    low, high, rsival = df["low"].values, df["high"].values, df["rsi"].values
    long_sig = [False] * n
    short_sig = [False] * n

    # ── Phân kỳ tăng từ chuỗi pivot low ──
    if d.get("allow_long", True):
        lows = [i for i in range(n) if bool(piv_low.iloc[i])]
        for a, b in zip(lows, lows[1:]):
            if 0 < b - a <= max_gap and low[b] < low[a] and rsival[b] > rsival[a]:
                c = b + k
                if c < n:
                    long_sig[c] = True

    # ── Phân kỳ giảm từ chuỗi pivot high ──
    if d.get("allow_short", True):
        highs = [i for i in range(n) if bool(piv_high.iloc[i])]
        for a, b in zip(highs, highs[1:]):
            if 0 < b - a <= max_gap and high[b] > high[a] and rsival[b] < rsival[a]:
                c = b + k
                if c < n:
                    short_sig[c] = True

    df["long_signal"] = long_sig
    df["short_signal"] = short_sig
    return df
