"""
compare.py — chạy 4 biến thể strategy trên BTC/ETH/SOL, so sánh + tách theo năm.

  python compare.py

Mỗi biến thể = config gốc + ĐÚNG MỘT thay đổi (để biết thay đổi đó gây tác dụng gì).
Tách theo năm = lăng kính out-of-sample thô: edge ổn định hay chỉ ăn 2023?
Walk-forward đầy đủ làm ở bước sau; đây là sàng lọc trước.
"""

from __future__ import annotations

import copy
import sys

import yaml

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

from backtest import run
from data import fetch_ohlcv
from report import summarize
from strategy import build_signals

# Mỗi biến thể: tên -> các giá trị ghi đè (deep-merge vào config gốc).
VARIANTS = {
    "Base (2R, EMA20)":   {},
    "Base + Volume":      {"strategy": {"volume_filter": True, "volume_mult": 1.0}},
    "Base + EMA50 pull":  {"strategy": {"pullback_ema_len": 50}},
    "Base + ATR trail":   {"backtest": {"exit_mode": "atr_trailing"}},
}


def deep_merge(base: dict, over: dict) -> dict:
    out = copy.deepcopy(base)
    for k, v in over.items():
        if isinstance(v, dict) and isinstance(out.get(k), dict):
            out[k] = deep_merge(out[k], v)
        else:
            out[k] = v
    return out


def pnl_by_year(trades) -> dict:
    if trades.empty:
        return {}
    g = trades.copy()
    g["year"] = g["entry_time"].dt.year
    return {int(y): round(s, 1) for y, s in g.groupby("year")["pnl"].sum().items()}


def main() -> None:
    with open("config.yaml", "r", encoding="utf-8") as f:
        base = yaml.safe_load(f)

    d = base["data"]
    # Tải data 1 lần, dùng lại cho mọi biến thể.
    cache = {}
    for sym in d["symbols"]:
        common = dict(
            symbol=sym["name"], exchange=sym["exchange"], market=sym["market"],
            since=d["since"], until=d["until"], cache_dir=d["cache_dir"], force=False,
        )
        cache[sym["name"]] = (
            fetch_ohlcv(timeframe=d["entry_timeframe"], **common),
            fetch_ohlcv(timeframe=d["trend_timeframe"], **common),
            sym["market"],
        )

    for vname, over in VARIANTS.items():
        cfg = deep_merge(base, over)
        print("\n" + "=" * 78)
        print(f"BIẾN THỂ: {vname}")
        print("=" * 78)
        print(f"{'coin':<10}{'trades':>7}{'win%':>7}{'expR':>8}{'PF':>7}"
              f"{'net%':>8}{'hold%':>9}{'maxDD%':>8}  beat?")
        for name, (df_1h, df_4h, market) in cache.items():
            sig = build_signals(df_1h, df_4h, cfg)
            res = run(sig, cfg, market=market)
            r = summarize(res, name)
            if r.get("trades", 0) == 0:
                print(f"{name:<10}{'0':>7}  (no trades)")
                continue
            beat = "✅" if r["beats_hold"] else "❌"
            print(f"{name:<10}{r['trades']:>7}{r['win_rate']*100:>6.1f}"
                  f"{r['expectancy_R']:>8.3f}{r['profit_factor']:>7.2f}"
                  f"{r['net_return']*100:>8.1f}{r['buy_and_hold']*100:>9.1f}"
                  f"{r['max_drawdown']*100:>8.1f}  {beat}")
            print(f"{'  └ năm:':<10}{pnl_by_year(res['trades'])}")


if __name__ == "__main__":
    main()
