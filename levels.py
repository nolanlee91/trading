"""
levels.py — Module 2: Support/Resistance thực dụng (thuần tính từ OHLCV).

Không cần data mới. Gom ỨNG VIÊN mức giá từ nhiều nguồn độc lập:
  - Swing high/low (4H và 1D) — fractal.
  - Nến volume-spike (high & low của nến khối lượng bất thường).
  - 30D high / 30D low.
  - Previous day high/low.
  - Previous week high/low.
Rồi CỤM các mức gần nhau (tolerance theo ATR) thành ZONE, chấm STRENGTH = số
nguồn độc lập xác nhận + số lần giá chạm (cap 5). Cuối cùng chọn resistance gần
nhất (trên giá) + support gần nhất (dưới giá) + xác định price location.

Triết lý: mức nào NHIỀU nguồn độc lập cùng chỉ tới thì đáng tin hơn — giống cách
trader vẽ tay: "chỗ này vừa là swing, vừa là đỉnh tuần, vừa có volume".
"""

from __future__ import annotations

import pandas as pd

# Nhãn nguồn -> có phải nguồn "mạnh" (khung lớn) không (để cộng điểm).
_STRONG_SRC = {"30D high", "30D low", "prev week high", "prev week low", "swing 1D"}


def _swings(df: pd.DataFrame, k: int, tf_label: str) -> list[tuple[float, str]]:
    """Fractal swing: high[i] cao nhất trong cửa sổ ±k (swing 1D/4H)."""
    out: list[tuple[float, str]] = []
    hi, lo = df["high"].values, df["low"].values
    n = len(df)
    for i in range(k, n - k):
        win_h = hi[i - k:i + k + 1]
        win_l = lo[i - k:i + k + 1]
        if hi[i] == win_h.max() and (win_h == hi[i]).sum() == 1:
            out.append((float(hi[i]), f"swing {tf_label}"))
        if lo[i] == win_l.min() and (win_l == lo[i]).sum() == 1:
            out.append((float(lo[i]), f"swing {tf_label}"))
    return out


def _candidates(h4: pd.DataFrame, d1: pd.DataFrame) -> list[tuple[float, str]]:
    """Mọi mức ứng viên (price, source_label) từ các nguồn độc lập."""
    c: list[tuple[float, str]] = []
    # Swing gần đây (giới hạn recency để mức còn liên quan).
    c += _swings(h4.iloc[-120:].reset_index(drop=True), 2, "4H")     # ~20 ngày
    c += _swings(d1.iloc[-60:].reset_index(drop=True), 2, "1D")      # ~2 tháng

    # Nến volume-spike (khối lượng > 2× TB20): high & low là mức đáng nhớ.
    for df, tf in ((d1, "1D"), (h4, "4H")):
        v = df["volume"]
        if len(v) >= 21:
            avg = v.rolling(20).mean()
            spike = df[v > 2.0 * avg].iloc[-8:]     # tối đa 8 spike gần nhất/khung
            for _, row in spike.iterrows():
                c.append((float(row["high"]), f"vol spike {tf}"))
                c.append((float(row["low"]), f"vol spike {tf}"))

    # 30D high/low.
    w30 = d1.iloc[-30:]
    if len(w30):
        c.append((float(w30["high"].max()), "30D high"))
        c.append((float(w30["low"].min()), "30D low"))
    # Previous day (nến ngày đã đóng gần nhất = iloc[-2]; iloc[-1] đang hình thành).
    if len(d1) >= 2:
        pd_ = d1.iloc[-2]
        c.append((float(pd_["high"]), "prev day high"))
        c.append((float(pd_["low"]), "prev day low"))
    # Previous week (7 nến ngày đã đóng gần nhất).
    if len(d1) >= 8:
        pw = d1.iloc[-8:-1]
        c.append((float(pw["high"].max()), "prev week high"))
        c.append((float(pw["low"].min()), "prev week low"))
    return c


def _touches(lo: float, hi: float, h4: pd.DataFrame) -> int:
    """Số nến 4H (recency ~120) có high HOẶC low nằm trong [lo,hi] — đo mức độ phản ứng."""
    w = h4.iloc[-120:]
    hin = ((w["high"] >= lo) & (w["high"] <= hi))
    lin = ((w["low"] >= lo) & (w["low"] <= hi))
    return int((hin | lin).sum())


def _cluster(cands: list[tuple[float, str]], tol: float, max_w: float, h4: pd.DataFrame) -> list[dict]:
    """Cụm mức gần nhau (gap <= tol) thành zone; chấm strength. Giới hạn bề rộng zone
    <= max_w để tránh 'dây chuyền' nuốt cả biên (một ladder mức dày sẽ thành nhiều zone)."""
    if not cands:
        return []
    cands = sorted(cands, key=lambda x: x[0])
    zones: list[dict] = []
    cur = {"prices": [cands[0][0]], "sources": [cands[0][1]]}
    for price, src in cands[1:]:
        if price - cur["prices"][-1] <= tol and price - cur["prices"][0] <= max_w:
            cur["prices"].append(price); cur["sources"].append(src)
        else:
            zones.append(cur); cur = {"prices": [price], "sources": [src]}
    zones.append(cur)

    out = []
    for z in zones:
        prices = z["prices"]
        lo, hi = min(prices), max(prices)
        # zone quá mỏng (1 mức) -> cho band ±0.25 tol để thành vùng, không phải vạch.
        if hi - lo < tol * 0.5:
            mid = (lo + hi) / 2
            lo, hi = mid - tol * 0.25, mid + tol * 0.25
        mid = (lo + hi) / 2
        srcs = sorted(set(z["sources"]))
        touches = _touches(lo, hi, h4)
        # Strength = #nguồn độc lập + bonus (chạm nhiều / có nguồn khung lớn), cap 5.
        score = len(srcs)
        if touches >= 4:
            score += 1
        if any(s in _STRONG_SRC for s in srcs):
            score += 1
        strength = max(1, min(5, score))
        out.append({"lo": round(lo, 4), "hi": round(hi, 4), "mid": round(mid, 4),
                    "strength": strength, "sources": srcs, "touches": touches})
    return out


def sr_levels(h4: pd.DataFrame, d1: pd.DataFrame, px: float, atr_v: float) -> dict:
    """Trả resistance gần nhất (trên giá), support gần nhất (dưới giá), price_location,
    và danh sách zone (để UI mở rộng). tol cụm = 0.6×ATR (min 0.35% giá)."""
    tol = max(atr_v * 0.6, px * 0.0035) if atr_v else px * 0.0035
    max_w = max(atr_v * 1.8, px * 0.012) if atr_v else px * 0.012   # zone rộng tối đa ~1.8 ATR
    zones = _cluster(_candidates(h4, d1), tol, max_w, h4)
    for z in zones:
        z["dist_pct"] = round((z["mid"] / px - 1) * 100, 2)

    res_zones = sorted([z for z in zones if z["lo"] > px], key=lambda z: z["lo"])       # trên giá
    sup_zones = sorted([z for z in zones if z["hi"] < px], key=lambda z: -z["hi"])      # dưới giá
    in_zone = next((z for z in zones if z["lo"] <= px <= z["hi"]), None)

    resistance = res_zones[0] if res_zones else None
    support = sup_zones[0] if sup_zones else None

    # ── Price location ──
    if in_zone is not None:
        # đang trong 1 zone: gọi theo phía gần hơn của giá so với biên zone
        loc = "at_resistance" if (px - in_zone["lo"]) >= (in_zone["hi"] - px) else "at_support"
    elif resistance and support:
        pos = (px - support["mid"]) / (resistance["mid"] - support["mid"])
        loc = "premium" if pos > 0.66 else "discount" if pos < 0.33 else "mid"
    elif not resistance and support:
        loc = "breakout"        # không còn kháng cự trên -> phá đỉnh
    elif resistance and not support:
        loc = "breakdown"       # không còn hỗ trợ dưới -> phá đáy
    else:
        loc = "mid"

    def _fmt(z):
        if not z:
            return None
        return {"lo": z["lo"], "hi": z["hi"], "mid": z["mid"], "strength": z["strength"],
                "sources": z["sources"], "touches": z["touches"], "dist_pct": z["dist_pct"]}

    return {"resistance": _fmt(resistance), "support": _fmt(support),
            "in_zone": _fmt(in_zone), "price_location": loc,
            "zones": [_fmt(z) for z in sorted(zones, key=lambda z: z["mid"])]}
