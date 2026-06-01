"""
backtest.py — next-open execution, trừ fee + slippage + funding (hourly).

Rule bắt buộc (Phase 1 spec):
  1. Signal tính sau khi nến đóng         -> strategy.build_signals
  2. Entry khớp ở OPEN nến kế tiếp         -> entry = open[i+1]
  3. Không dùng close nến signal để vào    -> không bao giờ đọc close[i] làm giá vào
  4/5. Report đầy đủ + vs buy-and-hold     -> report.py
  6. HYPE test riêng                        -> config (symbol list)

Khi SL và TP cùng nằm trong 1 nến -> giả định chạm SL trước (worst-case),
bật/tắt bằng backtest.sl_first_on_ambiguous.
"""

from __future__ import annotations

import pandas as pd


def run(signals: pd.DataFrame, cfg: dict, market: str) -> dict:
    s, c, b = cfg["strategy"], cfg["costs"], cfg["backtest"]
    fee, slip = c["fee_taker"], c["slippage"]
    fund_h = c["funding_hourly"] if market == c["funding_applies_to"] else 0.0
    sl_first = b["sl_first_on_ambiguous"]

    df = signals.reset_index(drop=True)
    n = len(df)
    trades: list[dict] = []
    equity = b["initial_equity"]
    equity_curve: list[tuple[pd.Timestamp, float]] = []

    i = 0
    while i < n - 1:
        row = df.iloc[i]
        is_long = bool(row.get("long_signal", False))
        is_short = bool(row.get("short_signal", False))
        if (not is_long and not is_short) or pd.isna(row["atr"]) or row["atr"] <= 0:
            i += 1
            continue
        side = "long" if is_long else "short"      # long ưu tiên nếu trùng (hiếm)
        sign = 1 if side == "long" else -1

        # ── Vào lệnh ở OPEN nến kế tiếp (i+1); slippage luôn bất lợi ──
        entry_idx = i + 1
        entry = df.iloc[entry_idx]["open"] * (1 + sign * slip)
        atr_v = row["atr"]
        sl = entry - sign * s["sl_atr_mult"] * atr_v   # long: dưới; short: trên
        risk_per_unit = abs(entry - sl)
        if risk_per_unit <= 0:
            i += 1
            continue
        tp = entry + sign * s["tp_r_mult"] * risk_per_unit

        # Position sizing theo % rủi ro / khoảng cách SL.
        qty = (equity * b["risk_per_trade"]) / risk_per_unit
        notional = entry * qty

        exit_mode = b.get("exit_mode", "fixed_r")
        trail_mult = b.get("trail_atr_mult", s["sl_atr_mult"])

        # ── Đi tới từng nến tiếp theo tìm điểm thoát ──
        exit_price = exit_time = None
        hours_held = 0
        stop = sl  # với atr_trailing, stop sẽ siết dần theo giá
        for j in range(entry_idx, n):
            bar = df.iloc[j]
            hours_held += 1

            if exit_mode == "atr_trailing":
                # Kiểm tra stop HIỆN TẠI (tính từ các nến TRƯỚC) trước, rồi mới siết
                # -> không dùng high/low của chính nến này để đặt stop rồi thoát cùng nến.
                if side == "long" and bar["low"] <= stop:
                    exit_price, exit_time = stop, bar["time"]
                    break
                if side == "short" and bar["high"] >= stop:
                    exit_price, exit_time = stop, bar["time"]
                    break
                atr_j = bar["atr"] if pd.notna(bar["atr"]) else atr_v
                if side == "long":
                    stop = max(stop, bar["high"] - trail_mult * atr_j)
                else:
                    stop = min(stop, bar["low"] + trail_mult * atr_j)
                continue

            # fixed_r: SL cố định + TP cố định
            if side == "long":
                hit_sl, hit_tp = bar["low"] <= sl, bar["high"] >= tp
            else:
                hit_sl, hit_tp = bar["high"] >= sl, bar["low"] <= tp
            if hit_sl and hit_tp:
                exit_price = sl if sl_first else tp
            elif hit_sl:
                exit_price = sl
            elif hit_tp:
                exit_price = tp
            if exit_price is not None:
                exit_time = bar["time"]
                break
        if exit_price is None:  # còn mở ở cuối data -> đóng tại close cuối
            exit_price = df.iloc[-1]["close"]
            exit_time = df.iloc[-1]["time"]
            hours_held = n - entry_idx

        exit_fill = exit_price * (1 - sign * slip)

        gross = sign * (exit_fill - entry) * qty
        fee_cost = (entry + exit_fill) * qty * fee
        # Long TRẢ funding khi rate>0; short NHẬN funding. -> sign quyết định dấu.
        funding_cost = sign * notional * fund_h * hours_held
        pnl = gross - fee_cost - funding_cost
        equity += pnl
        equity_curve.append((exit_time, equity))

        trades.append({
            "side": side,
            "entry_time": df.iloc[entry_idx]["time"],
            "exit_time": exit_time,
            "entry": entry, "exit": exit_fill, "sl": sl, "tp": tp,
            "qty": qty, "hours_held": hours_held,
            "gross": gross, "fee": fee_cost, "funding": funding_cost,
            "pnl": pnl, "r_multiple": pnl / (risk_per_unit * qty),
            "equity": equity,
        })

        # Không vào lệnh chồng: nhảy tới sau khi đã thoát.
        i = df.index[df["time"] == exit_time][0] + 1

    return {
        "trades": pd.DataFrame(trades),
        "equity_curve": pd.DataFrame(equity_curve, columns=["time", "equity"]),
        "initial_equity": b["initial_equity"],
        "final_equity": equity,
        "first_close": float(df.iloc[0]["close"]),
        "last_close": float(df.iloc[-1]["close"]),
    }
