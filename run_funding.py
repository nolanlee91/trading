"""
run_funding.py — chiến lược funding-extreme (hướng b), bản TRADEABLE.

Logic:
  - Tín hiệu: funding (level hoặc velocity) <= expanding percentile (CHỈ dùng quá
    khứ -> không look-ahead, khác bản study dùng full-sample).
  - Vào LONG ở open nến 1h kế tiếp sau sự kiện funding.
  - Giữ tối đa hold_hours, hoặc thoát sớm khi funding hồi lên >= exit_pct percentile.
  - Không vào lệnh chồng (1 vị thế tại 1 thời điểm).

Chi phí TRUNG THỰC:
  - fee + slippage 2 chiều.
  - Funding THẬT cộng dồn theo từng kỳ 8h trong lúc giữ: long TRẢ khi funding>0,
    NHẬN khi funding<0 (chính là tailwind của setup này).

  python run_funding.py
"""

from __future__ import annotations

import sys

import numpy as np
import pandas as pd
import yaml

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

from data import fetch_ohlcv
from data_funding import fetch_funding


def expanding_signal(fund: pd.DataFrame, fs: dict) -> pd.Series:
    """True tại sự kiện funding cực đoan theo expanding percentile (chỉ quá khứ)."""
    series = fund["funding"].diff() if fs["signal"] == "velocity" else fund["funding"]
    vals = series.values
    n = len(vals)
    sig = np.zeros(n, dtype=bool)
    warmup = fs["warmup_events"]
    for i in range(warmup, n):
        past = vals[:i]                      # KHÔNG gồm điểm hiện tại
        past = past[~np.isnan(past)]
        if len(past) < warmup:
            continue
        thr = np.quantile(past, fs["entry_pct"])
        if not np.isnan(vals[i]) and vals[i] <= thr:
            sig[i] = True
    return pd.Series(sig, index=fund.index)


def exit_threshold_series(fund: pd.DataFrame, fs: dict) -> np.ndarray:
    """Ngưỡng funding để thoát sớm (expanding exit_pct percentile)."""
    vals = fund["funding"].values
    n = len(vals)
    out = np.full(n, np.nan)
    for i in range(fs["warmup_events"], n):
        past = vals[:i][~np.isnan(vals[:i])]
        if len(past):
            out[i] = np.quantile(past, fs["exit_pct"])
    return out


def backtest(fund: pd.DataFrame, df1h: pd.DataFrame, cfg: dict, market: str) -> dict:
    fs = cfg["funding_strategy"]
    c = cfg["costs"]
    fee, slip = c["fee_taker"], c["slippage"]

    sig = expanding_signal(fund, fs).values
    exit_thr = exit_threshold_series(fund, fs)
    f_time = fund["time"].values
    f_rate = fund["funding"].values

    open_s = df1h.set_index("time")["open"].sort_index()
    o_times = open_s.index.values
    o_vals = open_s.values

    equity = cfg["backtest"]["initial_equity"]
    curve, trades = [], []
    hold = np.timedelta64(fs["hold_hours"], "h")
    busy_until = np.datetime64("1970-01-01")  # không vào lệnh chồng

    for i in range(len(fund)):
        if not sig[i] or f_time[i] <= busy_until:
            continue
        # Vào ở open nến 1h ĐẦU TIÊN sau thời điểm funding.
        ei = np.searchsorted(o_times, f_time[i], side="right")
        if ei >= len(o_times):
            break
        entry_t = o_times[ei]
        entry = o_vals[ei] * (1 + slip)
        deadline = entry_t + hold

        # Thoát: hết hold, HOẶC funding hồi lên >= exit threshold (kiểm tại mỗi kỳ 8h).
        exit_t = deadline
        for j in range(i + 1, len(fund)):
            if f_time[j] > deadline:
                break
            if not np.isnan(exit_thr[j]) and f_rate[j] >= exit_thr[j]:
                exit_t = f_time[j]
                break
        xi = np.searchsorted(o_times, exit_t, side="right")
        xi = min(xi, len(o_times) - 1)
        exit_fill = o_vals[xi] * (1 - slip)
        exit_t = o_times[xi]

        # Funding thật cộng dồn trong lúc giữ (long trả khi >0, nhận khi <0).
        mask = (f_time > entry_t) & (f_time <= exit_t)
        funding_frac = float(np.nansum(f_rate[mask]))

        gross_ret = exit_fill / entry - 1
        net_ret = gross_ret - 2 * fee - funding_frac
        pnl = equity * fs["position_frac"] * net_ret
        equity += pnl
        curve.append((exit_t, equity))
        trades.append({
            "entry_time": pd.Timestamp(entry_t), "exit_time": pd.Timestamp(exit_t),
            "gross_ret": gross_ret, "funding_frac": funding_frac,
            "net_ret": net_ret, "pnl": pnl, "equity": equity,
        })
        busy_until = exit_t

    t = pd.DataFrame(trades)
    eq = pd.DataFrame(curve, columns=["time", "equity"])
    first_close = float(df1h.iloc[0]["close"])
    last_close = float(df1h.iloc[-1]["close"])
    return {"trades": t, "equity": eq, "init": cfg["backtest"]["initial_equity"],
            "final": equity, "hold_ret": last_close / first_close - 1}


def report(res: dict, symbol: str) -> None:
    t = res["trades"]
    print("\n" + "=" * 92)
    print(f"FUNDING-EXTREME LONG — {symbol}")
    print("=" * 92)
    if t.empty:
        print("  0 lệnh.")
        return
    n = len(t)
    win = (t["net_ret"] > 0).mean()
    avg = t["net_ret"].mean()
    gw = t.loc[t["pnl"] > 0, "pnl"].sum()
    gl = -t.loc[t["pnl"] <= 0, "pnl"].sum()
    pf = gw / gl if gl > 0 else float("inf")
    net = res["final"] / res["init"] - 1
    peak = res["equity"]["equity"].cummax()
    dd = ((res["equity"]["equity"] - peak) / peak).min()
    beat = "✅" if net > res["hold_ret"] else "❌"
    print(f"  trades {n} | win {win*100:.1f}% | avg net/trade {avg*100:+.2f}% | PF {pf:.2f}")
    print(f"  net {net*100:+.1f}% | buy&hold {res['hold_ret']*100:+.1f}% {beat} | maxDD {dd*100:.1f}%")
    print(f"  funding đóng góp TB/lệnh: {-t['funding_frac'].mean()*100:+.3f}% (dương = nhận)")
    g = t.copy()
    g["year"] = g["entry_time"].dt.year
    by = g.groupby("year").agg(trades=("pnl", "size"), net_pnl=("pnl", "sum"),
                               win=("net_ret", lambda s: (s > 0).mean()))
    print("  theo năm:")
    print(by.round(3).to_string().replace("\n", "\n  "))


def main() -> None:
    with open("config.yaml", "r", encoding="utf-8") as f:
        cfg = yaml.safe_load(f)
    d = cfg["data"]
    pairs = [("BTC/USDT", "BTC/USDT:USDT"), ("ETH/USDT", "ETH/USDT:USDT"),
             ("SOL/USDT", "SOL/USDT:USDT")]
    print(f">> signal={cfg['funding_strategy']['signal']} "
          f"entry_pct={cfg['funding_strategy']['entry_pct']} "
          f"hold={cfg['funding_strategy']['hold_hours']}h")
    for spot, perp in pairs:
        df1h = fetch_ohlcv(symbol=spot, exchange="binance", market="spot",
                           timeframe="1h", since=d["since"], until=d["until"],
                           cache_dir=d["cache_dir"], force=False)
        fund = fetch_funding(perp, "binance", d["since"], d["until"], d["cache_dir"])
        res = backtest(fund, df1h, cfg, "swap")
        report(res, perp)


if __name__ == "__main__":
    main()
