"""
diagnostics.py — Phase A: hiểu VÌ SAO setup thua. Không sửa logic strategy.

In ra:
  1. PnL tách theo năm        -> thua đều hay chỉ 1 regime?
  2. Phân bố R-multiple       -> nhiều lệnh thua nhỏ hay vài lệnh thua to?
  3. PnL theo độ dài giữ lệnh -> giữ lâu có tệ hơn?
  4. 5 lệnh mẫu               -> mắt thường xác nhận entry ở nến SAU signal
Và vẽ equity curve ra PNG mỗi coin.
"""

from __future__ import annotations

import os

import matplotlib
matplotlib.use("Agg")  # không cần màn hình, chỉ xuất file
import matplotlib.pyplot as plt
import pandas as pd

OUT_DIR = "./reports"


def _safe(symbol: str) -> str:
    return symbol.replace("/", "-")


def pnl_by_year(t: pd.DataFrame) -> pd.DataFrame:
    g = t.copy()
    g["year"] = g["entry_time"].dt.year
    out = g.groupby("year").agg(
        trades=("pnl", "size"),
        net_pnl=("pnl", "sum"),
        win_rate=("pnl", lambda s: (s > 0).mean()),
        avg_R=("r_multiple", "mean"),
    )
    return out.round(3)


def r_distribution(t: pd.DataFrame) -> pd.Series:
    bins = [-99, -1.0, -0.5, 0.0, 1.0, 2.0, 99]
    labels = ["≤ -1R", "-1..-0.5R", "-0.5..0R", "0..1R", "1..2R", "> 2R"]
    cut = pd.cut(t["r_multiple"], bins=bins, labels=labels)
    return cut.value_counts().reindex(labels)


def holding_analysis(t: pd.DataFrame) -> pd.DataFrame:
    bins = [0, 4, 12, 24, 72, 1e9]
    labels = ["1-4h", "5-12h", "13-24h", "25-72h", "> 72h"]
    g = t.copy()
    g["bucket"] = pd.cut(g["hours_held"], bins=bins, labels=labels)
    out = g.groupby("bucket", observed=False).agg(
        trades=("pnl", "size"),
        net_pnl=("pnl", "sum"),
        avg_R=("r_multiple", "mean"),
    )
    return out.round(3)


def equity_png(equity_curve: pd.DataFrame, symbol: str) -> str:
    os.makedirs(OUT_DIR, exist_ok=True)
    path = os.path.join(OUT_DIR, f"equity_{_safe(symbol)}.png")
    fig, ax = plt.subplots(figsize=(10, 4))
    ax.plot(equity_curve["time"], equity_curve["equity"], lw=1.2)
    ax.set_title(f"Equity curve — {symbol}")
    ax.set_ylabel("Equity ($)")
    ax.grid(alpha=0.3)
    fig.tight_layout()
    fig.savefig(path, dpi=110)
    plt.close(fig)
    return path


def diagnose(result: dict, symbol: str) -> None:
    t = result["trades"]
    print("\n" + "─" * 64)
    print(f"CHẨN ĐOÁN — {symbol}  ({len(t)} lệnh)")
    print("─" * 64)
    if t.empty:
        print("  Không có lệnh.")
        return

    print("\n• PnL theo năm:")
    print(pnl_by_year(t).to_string())

    print("\n• Phân bố kết quả (R-multiple):")
    dist = r_distribution(t)
    total = len(t)
    for label, count in dist.items():
        c = int(count) if pd.notna(count) else 0
        bar = "█" * round(40 * c / total)
        print(f"    {label:>10} | {c:4d}  {bar}")

    print("\n• PnL theo độ dài giữ lệnh:")
    print(holding_analysis(t).to_string())

    print("\n• 5 lệnh mẫu (xác nhận entry ở nến SAU signal):")
    print("    signal đóng tại = entry_time (entry khớp ở OPEN nến đó)")
    sample = t.head(5)[["entry_time", "exit_time", "entry", "exit", "r_multiple"]]
    for _, r in sample.iterrows():
        sig_open = r["entry_time"] - pd.Timedelta(hours=1)
        print(f"    signal nến mở {sig_open} → đóng {r['entry_time']} "
              f"→ ENTRY {r['entry']:.2f} | exit {r['exit']:.2f} ({r['r_multiple']:+.2f}R)")

    png = equity_png(result["equity_curve"], symbol)
    print(f"\n• Equity curve đã lưu: {png}")
