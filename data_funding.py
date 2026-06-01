"""
data_funding.py — kéo lịch sử FUNDING RATE bằng CCXT (miễn phí, lịch sử sâu).

Binance perp trả funding mỗi 8h. Mỗi bản ghi: time, fundingRate (vd 0.0001 = 0.01%).
Cache Parquet như OHLCV. Đây là dữ liệu duy nhất của nhóm funding/OI/liq có lịch
sử dài + free -> điểm khởi đầu cho hướng (b).
"""

from __future__ import annotations

import os
import time
from pathlib import Path

import ccxt
import pandas as pd


def fetch_funding(
    symbol: str,            # symbol perp, vd "BTC/USDT:USDT"
    exchange: str,
    since: str,
    until: str | None,
    cache_dir: str,
    force: bool = False,
) -> pd.DataFrame:
    safe = symbol.replace("/", "-").replace(":", "_")
    path = Path(cache_dir) / f"{exchange}_funding_{safe}.parquet"
    if path.exists() and not force:
        return pd.read_parquet(path)

    ex = getattr(ccxt, exchange)({"enableRateLimit": True, "options": {"defaultType": "swap"}})
    ex.load_markets()
    since_ms = ex.parse8601(since)
    until_ms = ex.parse8601(until) if until else ex.milliseconds()

    # Phân trang tới hiện tại; không dựa vào kích thước batch (sàn giới hạn page khác nhau).
    rows: list[dict] = []
    cursor = since_ms
    last_ts = None
    while cursor < until_ms:
        batch = ex.fetch_funding_rate_history(symbol, since=cursor, limit=1000)
        if not batch:
            break
        rows.extend(batch)
        newest = batch[-1]["timestamp"]
        if last_ts is not None and newest <= last_ts:   # không tiến triển -> dừng
            break
        last_ts = newest
        cursor = newest + 1
        time.sleep(ex.rateLimit / 1000)

    df = pd.DataFrame([
        {"time": r["timestamp"], "funding": r["fundingRate"]} for r in rows
    ])
    df = df.drop_duplicates(subset="time").sort_values("time").reset_index(drop=True)
    df["time"] = pd.to_datetime(df["time"], unit="ms", utc=True)

    os.makedirs(cache_dir, exist_ok=True)
    df.to_parquet(path, index=False)
    return df


if __name__ == "__main__":
    # Demo: kéo funding BTC/ETH/SOL từ Binance, in thống kê để kiểm chứng.
    import sys
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")

    for sym in ["BTC/USDT:USDT", "ETH/USDT:USDT", "SOL/USDT:USDT"]:
        df = fetch_funding(sym, "binance", "2023-01-01T00:00:00Z", None, "./data_cache")
        ann = df["funding"].mean() * 3 * 365 * 100  # 8h -> 3 lần/ngày, %/năm
        print(f"\n{sym}: {len(df)} bản ghi | {df['time'].min().date()} -> {df['time'].max().date()}")
        print(f"  funding 8h: min {df['funding'].min()*100:+.4f}%  "
              f"max {df['funding'].max()*100:+.4f}%  mean {df['funding'].mean()*100:+.4f}%")
        print(f"  ~ annualized mean: {ann:+.1f}%/năm")
        print(df.tail(3).to_string(index=False))
