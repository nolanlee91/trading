"""
structure.py — Module 3: Market Structure / SMC (thuần tính từ OHLCV).

Tự động detect trên từng khung (4H, 1D):
  - Swing high/low (fractal, có index -> dựng CHUỖI pivot thứ tự thời gian).
  - Cấu trúc: bullish (HH+HL) / bearish (LH+LL) / ranging.
  - BOS (break of structure = tiếp diễn) vs CHOCH (change of character = đảo).
  - Range high/low (biên dealing range hiện tại).
  - Equal high/low (EQH/EQL = ổ thanh khoản).
  - FVG / IFVG (fair value gap 3 nến; IFVG = gap đã bị lấp/đảo).
  - Supply/demand zone (order block gần nhất) + current zone.
  - Premium/discount theo dealing range.

Khác Module 2 (levels.py = mức tĩnh + strength): Module 3 đọc DÒNG CHẢY cấu trúc
(giá đang tiếp diễn hay đảo, invalidation ở đâu, thanh khoản gần nhất).
"""

from __future__ import annotations

import pandas as pd


def _pivots(df: pd.DataFrame, k: int = 2) -> list[dict]:
    """Chuỗi pivot xen kẽ H/L theo thời gian (fractal ±k). Khi 2 pivot cùng loại
    liên tiếp -> giữ cái cực trị hơn (dọn để cấu trúc luôn H,L,H,L...)."""
    hi, lo = df["high"].values, df["low"].values
    n = len(df)
    raw: list[dict] = []
    for i in range(k, n - k):
        wh, wl = hi[i - k:i + k + 1], lo[i - k:i + k + 1]
        if hi[i] == wh.max() and (wh == hi[i]).sum() == 1:
            raw.append({"idx": i, "price": float(hi[i]), "kind": "H"})
        if lo[i] == wl.min() and (wl == lo[i]).sum() == 1:
            raw.append({"idx": i, "price": float(lo[i]), "kind": "L"})
    raw.sort(key=lambda p: (p["idx"], 0 if p["kind"] == "H" else 1))
    # dọn xen kẽ
    clean: list[dict] = []
    for p in raw:
        if clean and clean[-1]["kind"] == p["kind"]:
            prev = clean[-1]
            better = p["price"] > prev["price"] if p["kind"] == "H" else p["price"] < prev["price"]
            if better:
                clean[-1] = p
        else:
            clean.append(p)
    return clean


def _structure(df: pd.DataFrame, k: int, closes) -> dict:
    """Trạng thái cấu trúc + sự kiện BOS/CHOCH cuối + invalidation (theo close-break)."""
    piv = _pivots(df, k)
    if len(piv) < 3:
        return {"state": "ranging", "event": None, "invalidation": None,
                "range_hi": None, "range_lo": None, "piv": piv}

    # ── Walk close-break: pivot "kích hoạt" ở idx xác nhận (idx + k) ──
    conf: dict = {}
    for p in piv:
        conf.setdefault(p["idx"] + k, []).append(p)
    trend = None
    event = None
    active_h = active_l = None          # pivot đang chờ bị phá
    protect_h = protect_l = None        # pivot đối diện được "bảo vệ" (cho invalidation)
    for i in range(len(df)):
        for p in conf.get(i, []):
            if p["kind"] == "H":
                active_h = p
                if trend == "bull":
                    protect_l = active_l or protect_l   # HL mới -> nâng mức bảo vệ
            else:
                active_l = p
                if trend == "bear":
                    protect_h = active_h or protect_h
        c = closes[i]
        if active_h and c > active_h["price"]:
            event = "BOS" if trend == "bull" else "CHOCH"
            protect_l = active_l or protect_l
            trend, active_h = "bull", None
        elif active_l and c < active_l["price"]:
            event = "BOS" if trend == "bear" else "CHOCH"
            protect_h = active_h or protect_h
            trend, active_l = "bear", None

    state = "bullish" if trend == "bull" else "bearish" if trend == "bear" else "ranging"
    inval = protect_l["price"] if trend == "bull" and protect_l else \
            protect_h["price"] if trend == "bear" and protect_h else None

    # Dealing range = swing cao nhất & thấp nhất trong ~8 pivot gần nhất
    recent = piv[-8:]
    range_hi = max(p["price"] for p in recent if p["kind"] == "H") if any(p["kind"] == "H" for p in recent) else None
    range_lo = min(p["price"] for p in recent if p["kind"] == "L") if any(p["kind"] == "L" for p in recent) else None

    return {"state": state, "event": event, "invalidation": inval,
            "range_hi": range_hi, "range_lo": range_lo, "piv": piv}


def _equal_levels(piv: list[dict], atr_v: float) -> dict:
    """EQH/EQL: 2+ swing cùng loại gần bằng nhau (<=0.15×ATR) = ổ thanh khoản."""
    tol = atr_v * 0.15 if atr_v else 0
    highs = [p["price"] for p in piv if p["kind"] == "H"]
    lows = [p["price"] for p in piv if p["kind"] == "L"]
    eqh = [round((a + b) / 2, 4) for a, b in zip(highs, highs[1:]) if abs(a - b) <= tol]
    eql = [round((a + b) / 2, 4) for a, b in zip(lows, lows[1:]) if abs(a - b) <= tol]
    return {"eqh": eqh, "eql": eql}


def _fvg(df: pd.DataFrame, px: float, lookback: int = 50) -> dict:
    """FVG 3 nến gần nhất còn CHƯA lấp: gap tăng (demand, dưới giá) & gap giảm (supply, trên giá)."""
    w = df.iloc[-lookback:].reset_index(drop=True)
    hi, lo = w["high"].values, w["low"].values
    up = None    # bullish FVG [high[i-1], low[i+1]] khi low[i+1] > high[i-1]
    dn = None    # bearish FVG [high[i+1], low[i-1]] khi low[i-1] > high[i+1]
    for i in range(1, len(w) - 1):
        if lo[i + 1] > hi[i - 1]:
            g_lo, g_hi = float(hi[i - 1]), float(lo[i + 1])
            filled = float(w["low"].iloc[i + 2:].min()) <= g_lo if i + 2 < len(w) else False
            if not filled and g_hi < px:      # còn dưới giá -> demand chưa test
                up = {"lo": round(g_lo, 4), "hi": round(g_hi, 4)}
        if lo[i - 1] > hi[i + 1]:
            g_lo, g_hi = float(hi[i + 1]), float(lo[i - 1])
            filled = float(w["high"].iloc[i + 2:].max()) >= g_hi if i + 2 < len(w) else False
            if not filled and g_lo > px:      # còn trên giá -> supply chưa test
                dn = {"lo": round(g_lo, 4), "hi": round(g_hi, 4)}
    return {"fvg_up": up, "fvg_down": dn}


def _thin(levels: list[float], min_gap: float, n: int = 3) -> list[float]:
    """Giữ mức có ý nghĩa: bỏ mức cách mức đã giữ < min_gap (gộp micro-swing). Đầu vào
    đã sắp theo 'gần giá nhất trước'. Trả tối đa n mức."""
    kept: list[float] = []
    for lv in levels:
        if all(abs(lv - k) >= min_gap for k in kept):
            kept.append(lv)
        if len(kept) >= n:
            break
    return kept


def market_structure(h4: pd.DataFrame, d1: pd.DataFrame, px: float, atr_v: float) -> dict:
    """Gộp toàn bộ Module 3. Trả structure 4H/1D, current_zone, invalidation,
    premium/discount, thanh khoản gần nhất (trên/dưới), FVG gần nhất."""
    s4 = _structure(h4, 3, h4["close"].values)   # k=3: bớt nhiễu micro-swing trên 4H
    s1 = _structure(d1, 2, d1["close"].values)
    piv4 = s4["piv"]
    eq = _equal_levels(piv4, atr_v)
    fvg = _fvg(h4, px)

    # ── Premium/discount theo dealing range 4H ──
    rh, rl = s4["range_hi"], s4["range_lo"]
    if rh and rl and rh > rl:
        pos = (px - rl) / (rh - rl)
        pd_zone = "premium" if pos > 0.6 else "discount" if pos < 0.4 else "equilibrium"
    else:
        pos, pd_zone = 0.5, "equilibrium"

    # ── Thanh khoản gần nhất: swing highs trên giá / swing lows dưới giá (đã lọc micro) ──
    min_gap = max(atr_v * 0.5, px * 0.004) if atr_v else px * 0.004
    highs_above = sorted({round(p["price"], 4) for p in piv4 if p["kind"] == "H" and p["price"] > px})
    lows_below = sorted({round(p["price"], 4) for p in piv4 if p["kind"] == "L" and p["price"] < px}, reverse=True)
    liq_above = _thin(highs_above, min_gap)
    liq_below = _thin(lows_below, min_gap)

    # ── Current zone: kết hợp cấu trúc + premium/discount + FVG/EQ ──
    if fvg["fvg_down"] and fvg["fvg_down"]["lo"] <= px * 1.002:
        current_zone = "H4 Supply (FVG)"
    elif fvg["fvg_up"] and fvg["fvg_up"]["hi"] >= px * 0.998:
        current_zone = "H4 Demand (FVG)"
    elif pd_zone == "premium":
        current_zone = "H4 Premium (supply-side)"
    elif pd_zone == "discount":
        current_zone = "H4 Discount (demand-side)"
    else:
        current_zone = "H4 Equilibrium"

    return {
        "structure_4h": {"state": s4["state"], "event": s4["event"], "invalidation": s4["invalidation"]},
        "structure_1d": {"state": s1["state"], "event": s1["event"]},
        "range_hi": round(rh, 4) if rh else None, "range_lo": round(rl, 4) if rl else None,
        "premium_discount": pd_zone, "range_pos": round(pos, 2),
        "current_zone": current_zone,
        "liquidity_above": liq_above, "liquidity_below": liq_below,
        "eqh": eq["eqh"][-2:], "eql": eq["eql"][-2:],
        "fvg_up": fvg["fvg_up"], "fvg_down": fvg["fvg_down"],
    }
