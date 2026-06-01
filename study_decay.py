"""
study_decay.py — edge funding-squeeze còn sống trong dữ liệu GẦN ĐÂY không?

Chia 2 nửa thời gian trên cấu hình tốt nhất (signal=level):
  PERIOD A: 2023-2024  (quá khứ / "train")
  PERIOD B: 2025-2026  (gần đây / "thực tế")

So per-trade net return của chiến lược vs BASELINE (forward 72h trung bình của
thị trường cùng kỳ). Nếu avgNet > baseline -> còn edge TIMING. Nếu ~= baseline
-> chỉ là drift. Nếu period B sập -> edge đã chết.

  python study_decay.py
"""

from __future__ import annotations

import sys

import pandas as pd
import yaml

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

from data import fetch_ohlcv
from data_funding import fetch_funding
from run_funding import backtest

CUTOFF = pd.Timestamp("2025-01-01", tz="UTC")


def baseline_72h(df1h: pd.DataFrame, fund: pd.DataFrame, lo, hi) -> float:
    """Forward 72h return trung bình của thị trường (drift) trong [lo, hi)."""
    close_s = df1h.set_index("time")["close"].sort_index()
    ev = fund[(fund["time"] >= lo) & (fund["time"] < hi)].copy()
    if ev.empty:
        return float("nan")
    base = ev["time"].map(close_s.asof)
    fwd = ev["time"].map(lambda t: close_s.asof(t + pd.Timedelta(hours=72)))
    return float((fwd / base - 1).mean()) * 100


def metrics(t: pd.DataFrame) -> dict:
    if t.empty:
        return {"n": 0}
    pos = t.loc[t["net_ret"] > 0, "net_ret"].sum()
    neg = -t.loc[t["net_ret"] <= 0, "net_ret"].sum()
    return {
        "n": len(t),
        "win": (t["net_ret"] > 0).mean() * 100,
        "avg": t["net_ret"].mean() * 100,
        "pf": (pos / neg) if neg > 0 else float("inf"),
        "sum": t["net_ret"].sum() * 100,
    }


def show(label: str, m: dict, base: float) -> None:
    if m["n"] == 0:
        print(f"    {label:<16} n=0")
        return
    edge = m["avg"] - base
    verdict = "✅ trên drift" if edge > 0.05 else ("≈ drift" if edge > -0.05 else "❌ dưới drift")
    print(f"    {label:<16} n={m['n']:>3} | win {m['win']:4.1f}% | avgNet {m['avg']:+.2f}% "
          f"| PF {m['pf']:.2f} | Σnet {m['sum']:+6.1f}% | baseline72h {base:+.2f}% -> {verdict}")


def main() -> None:
    with open("config.yaml", "r", encoding="utf-8") as f:
        cfg = yaml.safe_load(f)
    d = cfg["data"]
    print(f">> signal={cfg['funding_strategy']['signal']} "
          f"entry_pct={cfg['funding_strategy']['entry_pct']} | cutoff {CUTOFF.date()}")
    pairs = [("BTC/USDT", "BTC/USDT:USDT"), ("ETH/USDT", "ETH/USDT:USDT"),
             ("SOL/USDT", "SOL/USDT:USDT")]
    for spot, perp in pairs:
        df1h = fetch_ohlcv(symbol=spot, exchange="binance", market="spot",
                           timeframe="1h", since=d["since"], until=d["until"],
                           cache_dir=d["cache_dir"], force=False)
        fund = fetch_funding(perp, "binance", d["since"], d["until"], d["cache_dir"])
        res = backtest(fund, df1h, cfg, "swap")
        t = res["trades"].copy()
        t["entry_time"] = pd.to_datetime(t["entry_time"], utc=True)  # đồng bộ tz với CUTOFF
        a = t[t["entry_time"] < CUTOFF]
        b = t[t["entry_time"] >= CUTOFF]
        print(f"\n{perp}")
        show("A 2023-2024", metrics(a), baseline_72h(df1h, fund, fund['time'].min(), CUTOFF))
        show("B 2025-2026", metrics(b), baseline_72h(df1h, fund, CUTOFF, fund['time'].max()))


if __name__ == "__main__":
    main()
