"""
run_div.py — chạy thử nghiệm phân kỳ RSI 15m trên BTC/ETH/SOL.

  python run_div.py

Tái dùng backtest.run (next-open, trừ fee+slippage+funding) + report.summarize.
In kèm PnL theo năm để xem ổn định out-of-sample hay không.
"""

from __future__ import annotations

import copy
import sys

import yaml

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

from backtest import run
from data import fetch_ohlcv
from divergence import build_divergence_signals
from report import summarize


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
    div = base["divergence"]
    tf = div["timeframe"]

    # Backtest đọc cfg["strategy"][sl_atr_mult/tp_r_mult]; nạp tham số divergence vào đó.
    cfg = copy.deepcopy(base)
    cfg["strategy"]["sl_atr_mult"] = div["sl_atr_mult"]
    cfg["strategy"]["tp_r_mult"] = div["tp_r_mult"]
    cfg["backtest"]["exit_mode"] = "fixed_r"

    print("\n" + "=" * 78)
    print(f"PHÂN KỲ RSI {tf}  (long+short, SL {div['sl_atr_mult']}ATR, TP {div['tp_r_mult']}R)")
    print("=" * 78)
    print(f"{'coin':<10}{'trades':>7}{'win%':>7}{'expR':>8}{'PF':>7}"
          f"{'net%':>8}{'hold%':>9}{'maxDD%':>8}  beat?")

    for sym in d["symbols"]:
        df15 = fetch_ohlcv(
            symbol=sym["name"], exchange=sym["exchange"], market=sym["market"],
            timeframe=tf, since=d["since"], until=d["until"],
            cache_dir=d["cache_dir"], force=False,
        )
        sig = build_divergence_signals(df15, cfg)
        res = run(sig, cfg, market=sym["market"])
        r = summarize(res, sym["name"])
        if r.get("trades", 0) == 0:
            print(f"{sym['name']:<10}{'0':>7}  (no trades)")
            continue
        beat = "✅" if r["beats_hold"] else "❌"
        print(f"{sym['name']:<10}{r['trades']:>7}{r['win_rate']*100:>6.1f}"
              f"{r['expectancy_R']:>8.3f}{r['profit_factor']:>7.2f}"
              f"{r['net_return']*100:>8.1f}{r['buy_and_hold']*100:>9.1f}"
              f"{r['max_drawdown']*100:>8.1f}  {beat}")
        print(f"{'  └ năm:':<10}{pnl_by_year(res['trades'])}")


if __name__ == "__main__":
    main()
