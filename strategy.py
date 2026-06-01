"""
strategy.py — trend-continuation pullback.

Sinh tín hiệu trên nến ĐÃ ĐÓNG. Mỗi tín hiệu gắn vào 1H candle index `i`
nghĩa là: tín hiệu xác nhận ở close của nến i  ->  backtest.py sẽ vào lệnh
ở OPEN của nến i+1. strategy.py KHÔNG được nhìn nến i+1 trở đi.

Chống look-ahead khi ghép 4H vào 1H:
  Với mỗi 1H candle đóng tại close_time t, ta chỉ được dùng 4H candle nào
  đã đóng <= t. Dùng merge_asof (backward) trên close_time để map an toàn.
"""

from __future__ import annotations

import pandas as pd

from indicators import atr, ema, rsi

_TF_MS = {"1h": 3_600_000, "4h": 14_400_000}


def _with_close_time(df: pd.DataFrame, tf: str) -> pd.DataFrame:
    df = df.copy()
    df["close_time"] = df["time"] + pd.to_timedelta(_TF_MS[tf], unit="ms")
    return df


def build_signals(df_1h: pd.DataFrame, df_4h: pd.DataFrame, cfg: dict) -> pd.DataFrame:
    s = cfg["strategy"]

    # ── Trend trên 4H ──
    reg = cfg.get("regime", {})
    h4 = _with_close_time(df_4h, "4h")
    h4["ema_fast"] = ema(h4["close"], s["ema_fast"])
    h4["ema_mid"] = ema(h4["close"], s["ema_mid"])
    h4["ema_slow"] = ema(h4["close"], s["ema_slow"])
    stack_up = (h4["ema_fast"] > h4["ema_mid"]) & (h4["ema_mid"] > h4["ema_slow"])
    stack_dn = (h4["ema_fast"] < h4["ema_mid"]) & (h4["ema_mid"] < h4["ema_slow"])

    # Lọc regime: EMA20 và EMA200 phải giãn đủ rộng (trend mạnh, không sideway).
    ema_spread = ((h4["ema_fast"] - h4["ema_slow"]) / h4["ema_slow"]).abs()
    if reg.get("enabled", False):
        strong = ema_spread >= reg.get("ema_spread_min", 0.0)
    else:
        strong = True
    h4["trend_up"] = stack_up & strong
    h4["trend_dn"] = stack_dn & strong
    trend = h4[["close_time", "trend_up", "trend_dn"]].dropna()

    # ── Entry features trên 1H ──
    h1 = _with_close_time(df_1h, "1h")
    h1["rsi"] = rsi(h1["close"], s["rsi_len"])
    h1["atr"] = atr(h1["high"], h1["low"], h1["close"], s["atr_len"])
    # Vùng pullback: EMA20 hay EMA50 tùy config.
    h1["pull_ema"] = ema(h1["close"], s.get("pullback_ema_len", s["ema_fast"]))
    h1["vol_ma"] = h1["volume"].rolling(s.get("volume_ma_len", 20)).mean()

    # Ghép trend 4H đã đóng vào từng nến 1H (backward = chỉ lấy 4H quá khứ).
    h1 = pd.merge_asof(
        h1.sort_values("close_time"),
        trend.sort_values("close_time"),
        on="close_time",
        direction="backward",
    )

    # ── Điều kiện entry (đánh giá tại close của nến 1H) ──
    pull_ema = h1["pull_ema"]   # vùng hồi (EMA20 hoặc EMA50 tùy config)
    tol = s["pullback_tol"]

    # Lọc volume (tùy chọn): volume nến > mult * MA(volume).
    if s.get("volume_filter", False):
        vol_ok = h1["volume"] > s.get("volume_mult", 1.0) * h1["vol_ma"]
    else:
        vol_ok = pd.Series(True, index=h1.index)

    # LONG: uptrend, giá hồi xuống chạm EMA rồi đóng lại TRÊN, RSI > ngưỡng.
    long_touch = h1["low"] <= pull_ema * (1 + tol)
    long_reclaim = h1["close"] > pull_ema
    long_rsi = h1["rsi"] > s["rsi_min"]
    h1["long_signal"] = (
        s.get("allow_long", True)
        & h1["trend_up"].fillna(False) & long_touch & long_reclaim & long_rsi & vol_ok
    )

    # SHORT: downtrend, giá hồi lên chạm EMA rồi đóng lại DƯỚI, RSI < (100-ngưỡng).
    short_touch = h1["high"] >= pull_ema * (1 - tol)
    short_reject = h1["close"] < pull_ema
    short_rsi = h1["rsi"] < (100 - s["rsi_min"])
    h1["short_signal"] = (
        s.get("allow_short", False)
        & h1["trend_dn"].fillna(False) & short_touch & short_reject & short_rsi & vol_ok
    )
    return h1
