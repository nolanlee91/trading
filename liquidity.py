"""
liquidity.py — Module 6: Liquidity Map / Liquidation zones. BẢN XẤP XỈ.

Không có liquidation heatmap API free. Làm bản đơn giản như user gợi ý:
  - RESTING liquidity (đáng tin): tái dùng EQH/EQL + swing của Module 3 -> ổ stop
    gần nhất trên/dưới giá (nơi thanh khoản nằm chờ).
  - LIQUIDATION cluster (ước lượng): leverage tiers từ giá hiện tại — long bị thanh
    lý DƯỚI giá, short bị thanh lý TRÊN giá. 50-100x ~2%, 25x ~4%, 10x ~10%.
    Cường độ gợi ý theo OI trend (OI tăng = vị thế mới, dễ bị quét).
  - MAGNET bias: giá có xu hướng bị hút về ổ thanh khoản lớn/gần hơn. Tổng hợp
    premium/discount + khoảng cách liquidity 2 phía + funding extreme.

Đây là ƯỚC LƯỢNG, KHÔNG phải heatmap thật — dùng để biết "phía nào là nam châm".
"""

from __future__ import annotations

# Leverage tier -> khoảng cách thanh lý xấp xỉ (bỏ qua maintenance margin cho gọn).
_TIERS = [("50-100x", 0.02), ("25x", 0.04), ("10x", 0.10)]


def _zone_near(levels: list[float], px: float, atr_v: float, below: bool) -> dict | None:
    """Ổ liquidity gần nhất 1 phía: gộp các mức cách nhau <=0.8×ATR thành range."""
    side = sorted([x for x in levels if (x < px if below else x > px)],
                  reverse=below)
    if not side:
        return None
    tol = atr_v * 0.8 if atr_v else px * 0.006
    cluster = [side[0]]
    for lv in side[1:]:
        if abs(lv - cluster[-1]) <= tol:
            cluster.append(lv)
        else:
            break
    lo, hi = min(cluster), max(cluster)
    mid = (lo + hi) / 2
    return {"lo": round(lo, 4), "hi": round(hi, 4), "mid": round(mid, 4),
            "dist_pct": round((mid / px - 1) * 100, 2), "n": len(cluster)}


def liquidity_map(px: float, atr_v: float, ms: dict, oi_trend: str | None,
                  funding_pctl: float | None) -> dict:
    """Trả resting liquidity gần nhất (trên/dưới), liquidation cluster ước lượng, magnet."""
    eqh = ms.get("eqh") or []
    eql = ms.get("eql") or []
    la = ms.get("liquidity_above") or []
    lb = ms.get("liquidity_below") or []

    liq_above = _zone_near(la + eqh, px, atr_v, below=False)
    liq_below = _zone_near(lb + eql, px, atr_v, below=True)

    # Liquidation cluster ước lượng theo leverage tier.
    long_liq = [{"tier": t, "price": round(px * (1 - d), 4), "dist_pct": round(-d * 100, 1)}
                for t, d in _TIERS]      # long bị thanh lý DƯỚI
    short_liq = [{"tier": t, "price": round(px * (1 + d), 4), "dist_pct": round(d * 100, 1)}
                 for t, d in _TIERS]     # short bị thanh lý TRÊN

    # ── Magnet bias ──
    score, why = 0, []
    pdz = ms.get("premium_discount")
    if pdz == "premium":
        score -= 1; why.append("giá ở premium → hút về discount")
    elif pdz == "discount":
        score += 1; why.append("giá ở discount → hút về premium")
    da = liq_above["dist_pct"] if liq_above else None
    db = abs(liq_below["dist_pct"]) if liq_below else None
    if da is not None and db is not None:
        if db < da - 0.1:
            score -= 1; why.append(f"liquidity dưới gần hơn ({db:.1f}% vs {da:.1f}%)")
        elif da < db - 0.1:
            score += 1; why.append(f"liquidity trên gần hơn ({da:.1f}% vs {db:.1f}%)")
    if funding_pctl is not None:
        if funding_pctl >= 85:
            score -= 1; why.append("funding cao (đông long → dễ flush xuống)")
        elif funding_pctl <= 15:
            score += 1; why.append("funding thấp (đông short → dễ squeeze lên)")

    magnet = "downside" if score < 0 else "upside" if score > 0 else "balanced"

    return {"liq_above": liq_above, "liq_below": liq_below,
            "long_liq": long_liq, "short_liq": short_liq,
            "liq_magnet": magnet, "liq_magnet_why": why,
            "liq_oi_note": oi_trend}     # OI tăng = cluster "tươi", dễ bị quét
