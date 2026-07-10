"""
data_oi.py — kéo lịch sử OPEN INTEREST bằng CCXT, cache Parquet.

Vì sao tách riêng khỏi data.py: sàn giá chính của app là Hyperliquid, nhưng
Hyperliquid KHÔNG hỗ trợ fetch_open_interest_history (đã kiểm chứng). OI lịch sử
chỉ có ở các sàn perp lớn — Bybit (sạch, có amount), Binance (hay bị 451), OKX
(chỉ có value $). Vì OI trend (tăng/giảm) tương quan rất cao giữa các sàn, ta dùng
1 sàn phái sinh làm PROXY cho "OI của đám đông", độc lập với sàn giá.

Mỗi bản ghi chuẩn hoá: time (UTC), oi (ưu tiên openInterestAmount, fallback
openInterestValue nếu sàn chỉ trả giá trị $ như OKX).
"""

from __future__ import annotations

import os
import time
from pathlib import Path

import ccxt
import pandas as pd

# Sàn có OI lịch sử, theo thứ tự ưu tiên. KHÔNG có Hyperliquid (không hỗ trợ).
DERIV_EXCHANGES = ["bybit", "binance", "okx"]
_EX_CACHE: dict = {}
_RESOLVED: str | None = None


def _exchange(name: str) -> ccxt.Exchange:
    ex = _EX_CACHE.get(name)
    if ex is None:
        ex = getattr(ccxt, name)({"enableRateLimit": True, "options": {"defaultType": "swap"}})
        _EX_CACHE[name] = ex
    return ex


def deriv_exchange() -> str | None:
    """Dò 1 lần sàn phái sinh trả được OI lịch sử cho BTC, cache lại. None nếu không sàn nào vào được."""
    global _RESOLVED
    if _RESOLVED:
        return _RESOLVED
    for name in DERIV_EXCHANGES:
        try:
            ex = _exchange(name)
            ex.load_markets()
            h = ex.fetch_open_interest_history("BTC/USDT:USDT", "1h", limit=3)
            if h:
                _RESOLVED = name
                return name
        except Exception:
            continue
    return None


def _oi_val(r: dict) -> float | None:
    v = r.get("openInterestAmount")
    if v is None:
        v = r.get("openInterestValue")   # OKX: chỉ có value $
    try:
        return float(v) if v is not None else None
    except (TypeError, ValueError):
        return None


def fetch_oi(
    base: str,               # base asset, vd "BTC"
    cache_dir: str,
    timeframe: str = "1h",
    lookback: int = 200,     # số điểm gần nhất mỗi lần kéo (OI history sàn giữ hạn chế)
    force: bool = False,
) -> pd.DataFrame:
    """Trả df[time, oi] cho base. df rỗng nếu không sàn nào có OI cho base (vd HYPE
    không niêm yết trên sàn proxy). Merge vào cache Parquet để dựng dần lịch sử."""
    ex_name = deriv_exchange()
    if not ex_name:
        return pd.DataFrame(columns=["time", "oi"])

    symbol = f"{base}/USDT:USDT"
    safe = f"{base}-USDT_USDT"
    path = Path(cache_dir) / f"{ex_name}_oi_{safe}_{timeframe}.parquet"

    cached = None
    if path.exists() and not force:
        cached = pd.read_parquet(path)

    try:
        ex = _exchange(ex_name)
        ex.load_markets()
        raw = ex.fetch_open_interest_history(symbol, timeframe, limit=lookback)
    except Exception:
        # base không có trên sàn proxy (vd HYPE) hoặc lỗi tạm thời -> trả cache nếu có.
        return cached if cached is not None else pd.DataFrame(columns=["time", "oi"])

    rows = [{"time": r["timestamp"], "oi": _oi_val(r)} for r in raw if _oi_val(r) is not None]
    new = pd.DataFrame(rows, columns=["time", "oi"])
    if len(new):
        new["time"] = pd.to_datetime(new["time"], unit="ms", utc=True)

    if cached is not None and len(cached):
        df = pd.concat([cached, new], ignore_index=True) if len(new) else cached
    else:
        df = new
    df = df.drop_duplicates(subset="time", keep="last").sort_values("time").reset_index(drop=True)

    if len(df):
        os.makedirs(cache_dir, exist_ok=True)
        df.to_parquet(path, index=False)
    return df


if __name__ == "__main__":
    import sys
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    print("resolved deriv exchange:", deriv_exchange())
    for b in ["BTC", "ETH", "SOL", "HYPE"]:
        d = fetch_oi(b, "./data_cache")
        if len(d):
            print(f"{b}: {len(d)} điểm | {d['time'].min()} -> {d['time'].max()} | oi cuối {d['oi'].iloc[-1]:,.0f}")
        else:
            print(f"{b}: KHÔNG có OI (không niêm yết trên sàn proxy)")
