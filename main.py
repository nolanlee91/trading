"""
main.py — chạy toàn bộ Phase 1 cho từng symbol.

  python main.py            # dùng config.yaml
  python main.py --force    # bỏ cache, tải lại data

BTC/ETH/SOL chạy chung; HYPE (nếu bật trong config) chạy với nguồn riêng.
"""

from __future__ import annotations

import argparse
import sys

import yaml

# Console Windows mặc định cp1252 -> in tiếng Việt/emoji sẽ crash. Ép UTF-8.
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

from backtest import run
from data import fetch_ohlcv
from diagnostics import diagnose
from report import print_report, summarize
from strategy import build_signals


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", default="config.yaml")
    ap.add_argument("--force", action="store_true", help="bỏ cache, tải lại data")
    ap.add_argument("--diagnose", action="store_true", help="Phase A: chẩn đoán vì sao thua")
    args = ap.parse_args()

    with open(args.config, "r", encoding="utf-8") as f:
        cfg = yaml.safe_load(f)

    d = cfg["data"]
    rows = []
    results = []
    for sym in d["symbols"]:
        print(f"[*] {sym['name']} @ {sym['exchange']} ...")
        common = dict(
            symbol=sym["name"], exchange=sym["exchange"], market=sym["market"],
            since=d["since"], until=d["until"], cache_dir=d["cache_dir"],
            force=args.force,
        )
        df_4h = fetch_ohlcv(timeframe=d["trend_timeframe"], **common)
        df_1h = fetch_ohlcv(timeframe=d["entry_timeframe"], **common)

        signals = build_signals(df_1h, df_4h, cfg)
        result = run(signals, cfg, market=sym["market"])
        rows.append(summarize(result, sym["name"]))
        results.append((sym["name"], result))

    print_report(rows)

    if args.diagnose:
        for name, result in results:
            diagnose(result, name)


if __name__ == "__main__":
    main()
