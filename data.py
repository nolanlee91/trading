"""
data.py — kéo OHLCV bằng CCXT, cache ra Parquet.

Quy ước cột: time (UTC, đã đóng nến), open, high, low, close, volume.
'time' là thời điểm MỞ nến. Một nến chỉ coi là "đã đóng" khi time + tf <= now.
data.py không hề biết gì về chiến lược — chỉ lo dữ liệu sạch.
"""

from __future__ import annotations

import os
import time
from pathlib import Path

import ccxt
import pandas as pd

_TF_MS = {
    "1m": 60_000, "5m": 300_000, "15m": 900_000, "30m": 1_800_000,
    "1h": 3_600_000, "4h": 14_400_000, "1d": 86_400_000,
}


_EX_CACHE: dict = {}


def _exchange(name: str, market: str) -> ccxt.Exchange:
    """Tái dùng instance theo (sàn, market) -> load_markets() chỉ chạy 1 lần (Hyperliquid
    load cả sàn rất chậm; tạo mới mỗi call khiến refresh chậm hàng chục giây)."""
    key = (name, market)
    ex = _EX_CACHE.get(key)
    if ex is None:
        klass = getattr(ccxt, name)
        opts = {"enableRateLimit": True}
        if market in ("swap", "future"):
            opts["options"] = {"defaultType": "swap"}
        ex = klass(opts)
        _EX_CACHE[key] = ex
    return ex


def _cache_path(cache_dir: str, exchange: str, symbol: str, tf: str) -> Path:
    safe = symbol.replace("/", "-")
    return Path(cache_dir) / f"{exchange}_{safe}_{tf}.parquet"


def fetch_ohlcv(
    symbol: str,
    exchange: str,
    market: str,
    timeframe: str,
    since: str,
    until: str | None,
    cache_dir: str,
    force: bool = False,
) -> pd.DataFrame:
    """Tải OHLCV (paginate qua giới hạn 1000 nến/req của sàn). Cache Parquet."""
    path = _cache_path(cache_dir, exchange, symbol, timeframe)

    # TĂNG DẦN (incremental): nếu đã có cache và không ép rebuild, chỉ kéo nến MỚI
    # từ mốc cuối cache trở đi rồi nối — tránh tải lại 450 ngày mỗi lần (rất chậm).
    cached = None
    if path.exists() and not force:
        cached = pd.read_parquet(path)

    ex = _exchange(exchange, market)
    ex.load_markets()
    tf_ms = _TF_MS[timeframe]
    until_ms = ex.parse8601(until) if until else ex.milliseconds()
    if cached is not None and len(cached):
        # bắt đầu từ nến cuối (kéo lại để cập nhật nến đang hình thành + nến mới)
        start_ms = int(cached["time"].iloc[-1].value // 1_000_000)
    else:
        start_ms = ex.parse8601(since)

    # Phân trang tới khi chạm hiện tại. KHÔNG dùng "len(batch)<limit -> break" vì
    # nhiều sàn (Bybit/OKX) giới hạn ~200 nến/lần -> sẽ dừng sớm và trả data CŨ.
    rows: list[list] = []
    cursor = start_ms
    last_ts = None
    while cursor < until_ms:
        batch = ex.fetch_ohlcv(symbol, timeframe, since=cursor, limit=1000)
        if not batch:
            break
        rows.extend(batch)
        newest = batch[-1][0]
        if last_ts is not None and newest <= last_ts:   # không tiến triển -> dừng
            break
        last_ts = newest
        cursor = newest + tf_ms
        time.sleep(ex.rateLimit / 1000)

    new = pd.DataFrame(rows, columns=["time", "open", "high", "low", "close", "volume"])
    new["time"] = pd.to_datetime(new["time"], unit="ms", utc=True)
    if cached is not None and len(cached):
        df = pd.concat([cached, new], ignore_index=True)
    else:
        df = new
    df = df.drop_duplicates(subset="time", keep="last").sort_values("time").reset_index(drop=True)

    os.makedirs(cache_dir, exist_ok=True)
    df.to_parquet(path, index=False)
    return _trim(df, since, until)


def _trim(df: pd.DataFrame, since: str, until: str | None) -> pd.DataFrame:
    lo = pd.Timestamp(since)
    df = df[df["time"] >= lo]
    if until:
        df = df[df["time"] <= pd.Timestamp(until)]
    return df.reset_index(drop=True)
