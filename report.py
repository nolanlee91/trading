"""
report.py — winrate / expectancy / profit factor / max DD / net return / vs buy-and-hold.

Luôn in SỐ LỆNH (ít lệnh = đừng tin) và so với buy-and-hold (long-only trong
bull rất dễ "thắng" mà vẫn thua hold).
"""

from __future__ import annotations

import pandas as pd


def _max_drawdown(equity: pd.Series) -> float:
    if equity.empty:
        return 0.0
    peak = equity.cummax()
    dd = (equity - peak) / peak
    return float(dd.min())  # số âm, vd -0.23 = -23%


def summarize(result: dict, symbol: str) -> dict:
    t = result["trades"]
    init = result["initial_equity"]
    final = result["final_equity"]

    n = len(t)
    if n == 0:
        return {
            "symbol": symbol, "trades": 0,
            "note": "Không có lệnh nào — setup quá chặt hoặc data thiếu.",
        }

    wins = t[t["pnl"] > 0]
    losses = t[t["pnl"] <= 0]
    gross_win = wins["pnl"].sum()
    gross_loss = -losses["pnl"].sum()

    win_rate = len(wins) / n
    expectancy_r = t["r_multiple"].mean()          # kỳ vọng tính bằng R
    profit_factor = (gross_win / gross_loss) if gross_loss > 0 else float("inf")
    net_return = final / init - 1
    buy_hold = result["last_close"] / result["first_close"] - 1
    max_dd = _max_drawdown(result["equity_curve"]["equity"])

    return {
        "symbol": symbol,
        "trades": n,
        "win_rate": round(win_rate, 4),
        "expectancy_R": round(expectancy_r, 4),
        "profit_factor": round(profit_factor, 3),
        "net_return": round(net_return, 4),
        "buy_and_hold": round(buy_hold, 4),
        "beats_hold": net_return > buy_hold,
        "max_drawdown": round(max_dd, 4),
        "total_fees": round(float(t["fee"].sum()), 2),
        "total_funding": round(float(t["funding"].sum()), 2),
    }


def print_report(rows: list[dict]) -> None:
    print("\n" + "=" * 72)
    print("PHASE 1 — EDGE LAB REPORT  (fee + slippage + funding đã trừ)")
    print("=" * 72)
    for r in rows:
        print()
        if r.get("trades", 0) == 0:
            print(f"  {r['symbol']:<10} | {r.get('note', '0 trades')}")
            continue
        flag = "✅ beats hold" if r["beats_hold"] else "❌ thua buy-and-hold"
        print(f"  {r['symbol']}")
        print(f"    trades         : {r['trades']}"
              + ("   ⚠️ <100, chưa đủ ý nghĩa thống kê" if r["trades"] < 100 else ""))
        print(f"    win rate       : {r['win_rate']*100:.1f}%")
        print(f"    expectancy     : {r['expectancy_R']:+.3f} R / trade")
        print(f"    profit factor  : {r['profit_factor']}")
        print(f"    net return     : {r['net_return']*100:+.1f}%")
        print(f"    buy & hold     : {r['buy_and_hold']*100:+.1f}%   -> {flag}")
        print(f"    max drawdown   : {r['max_drawdown']*100:.1f}%")
        print(f"    fees / funding : {r['total_fees']} / {r['total_funding']}")
    print("\n" + "=" * 72)
