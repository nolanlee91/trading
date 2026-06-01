"""
study_funding.py — SIGNAL STUDY (không phải strategy).

Câu hỏi: funding cực đoan -> 24h/48h/72h sau giá thường làm gì?
So sánh forward return của các bucket funding cực đoan vs baseline (toàn bộ).
Nếu bucket cực đoan KHÔNG khác baseline -> funding chỉ là nhiễu, bỏ.

Lưu ý: đây là phân tích MÔ TẢ (chưa trừ phí). Ngưỡng percentile dùng full-sample
để mô tả quan hệ; khi chuyển sang signal giao dịch thật phải đổi sang expanding.
"""

from __future__ import annotations

import sys

import pandas as pd
import yaml

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

from data import fetch_ohlcv
from data_funding import fetch_funding

HORIZONS = [24, 48, 72]


def fwd_returns(fund: pd.DataFrame, close_s: pd.Series) -> pd.DataFrame:
    ev = fund.copy()
    ev["price"] = ev["time"].map(close_s.asof)
    for h in HORIZONS:
        fwd = ev["time"].map(lambda t, h=h: close_s.asof(t + pd.Timedelta(hours=h)))
        ev[f"r{h}"] = fwd / ev["price"] - 1
    ev["dfund"] = ev["funding"].diff()   # funding velocity (thay đổi so 8h trước)
    return ev.dropna(subset=[f"r{h}" for h in HORIZONS])


def _line(label: str, sub: pd.DataFrame, base: pd.DataFrame) -> str:
    if len(sub) == 0:
        return f"  {label:<22} n=0"
    parts = [f"  {label:<22} n={len(sub):>4}"]
    for h in HORIZONS:
        m = sub[f"r{h}"].mean() * 100
        win = (sub[f"r{h}"] > 0).mean() * 100
        bm = base[f"r{h}"].mean() * 100
        edge = m - bm                     # chênh so với baseline cùng horizon
        parts.append(f"{h}h: {m:+5.2f}% (win {win:4.1f}%, vs base {edge:+5.2f})")
    return " | ".join(parts)


def study(symbol_spot: str, symbol_perp: str, exchange: str, cfg: dict) -> None:
    d = cfg["data"]
    df1h = fetch_ohlcv(
        symbol=symbol_spot, exchange=exchange, market="spot", timeframe="1h",
        since=d["since"], until=d["until"], cache_dir=d["cache_dir"], force=False,
    )
    fund = fetch_funding(symbol_perp, exchange, d["since"], d["until"], d["cache_dir"])
    close_s = df1h.set_index("time")["close"].sort_index()
    ev = fwd_returns(fund, close_s)

    print("\n" + "=" * 100)
    print(f"{symbol_perp}  |  {len(ev)} sự kiện funding (8h)")
    print("=" * 100)

    print(_line("BASELINE (tất cả)", ev, ev))
    print("  ── Funding LEVEL cực âm (đám đông short) → kỳ vọng squeeze LÊN:")
    for p in (0.10, 0.05, 0.01):
        thr = ev["funding"].quantile(p)
        print(_line(f"funding ≤ {p*100:.0f}pct ({thr*100:+.3f}%)", ev[ev["funding"] <= thr], ev))
    print("  ── Funding LEVEL cực dương (đám đông long) → kỳ vọng flush XUỐNG:")
    for p in (0.90, 0.95, 0.99):
        thr = ev["funding"].quantile(p)
        print(_line(f"funding ≥ {p*100:.0f}pct ({thr*100:+.3f}%)", ev[ev["funding"] >= thr], ev))
    print("  ── Funding VELOCITY lao dốc nhanh nhất (Δ so 8h trước):")
    for p in (0.10, 0.05, 0.01):
        thr = ev["dfund"].quantile(p)
        print(_line(f"Δfunding ≤ {p*100:.0f}pct", ev[ev["dfund"] <= thr], ev))


def main() -> None:
    with open("config.yaml", "r", encoding="utf-8") as f:
        cfg = yaml.safe_load(f)
    pairs = [("BTC/USDT", "BTC/USDT:USDT"), ("ETH/USDT", "ETH/USDT:USDT"),
             ("SOL/USDT", "SOL/USDT:USDT")]
    for spot, perp in pairs:
        study(spot, perp, "binance", cfg)


if __name__ == "__main__":
    main()
