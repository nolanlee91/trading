"""
decision.py — Layer 7: Decision State (tổng hợp 7 layer thành 1 kết luận).

Không thêm data mới — CHỈ hợp nhất output các module đã có (trend, risk, derivatives
[M1], support/resistance [M2], market structure [M3], btc_regime) thành:
  - direction (short/long/none) + stage (anticipation/confirmation)
  - checklist 7 điều kiện theo hướng (đạt >=5/7 mới là setup đẹp — theo yêu cầu user)
  - reasons + invalidation

Triết lý user:
  SHORT anticipation = giá tại H4 supply + funding dương + OI không đỡ rally thật
    + BTC không phá lên, KỂ CẢ khi cấu trúc H4 chưa xác nhận bearish (vào sớm).
  Confirmation = cấu trúc đã theo hướng (state khớp direction).

Điều kiện "spot flow weak" phụ thuộc Module 5 (chưa có) -> để UNKNOWN (None), hiện
"?" và KHÔNG tính là đạt. Vì vậy điểm tối đa hiện thời là 6/7.
"""

from __future__ import annotations


def _short_conditions(c: dict, btc: dict) -> list[dict]:
    loc = c.get("price_location")
    pdz = c.get("premium_discount")
    s4 = c.get("structure_4h") or {}
    cur = c.get("current_zone") or ""
    fs = c.get("funding_state")
    oi, pdir = c.get("oi_trend"), c.get("price_dir")

    at_supply = loc in ("at_resistance", "premium") or "Supply" in cur or "Premium" in cur
    struct_bear = s4.get("state") == "bearish" or (s4.get("event") == "CHOCH" and pdz == "premium")
    funding_pos = fs == "positive"
    oi_not_long = not (pdir == "up" and oi == "rising")     # không có "new longs" cầu thật
    btc_break_up = (btc.get("price_location") == "breakout"
                    or (btc.get("structure_4h") == "bullish" and btc.get("event") == "BOS"
                        and btc.get("premium_discount") == "premium"))
    btc_ok = not btc_break_up
    clear_inval = s4.get("invalidation") is not None or c.get("resistance") is not None
    scvd = c.get("spot_cvd_state")
    spot_weak = None if scvd is None else scvd in ("selling", "flat")   # spot KHÔNG mua chủ động

    return [
        {"label": "Giá tại H4/D1 supply (resistance/premium)", "ok": at_supply},
        {"label": "Cấu trúc H4 bearish hoặc lower-high (CHOCH ở premium)", "ok": struct_bear},
        {"label": "Funding dương (long đang trả phí)", "ok": funding_pos},
        {"label": "OI không đỡ rally long thật", "ok": oi_not_long},
        {"label": "BTC không phá lên kháng cự chính", "ok": btc_ok},
        {"label": "Spot flow yếu / không mua chủ động", "ok": spot_weak},   # Module 5
        {"label": "Có invalidation rõ phía trên vùng", "ok": clear_inval},
    ]


def _long_conditions(c: dict, btc: dict) -> list[dict]:
    loc = c.get("price_location")
    pdz = c.get("premium_discount")
    s4 = c.get("structure_4h") or {}
    cur = c.get("current_zone") or ""
    fs = c.get("funding_state")
    oi, pdir = c.get("oi_trend"), c.get("price_dir")

    at_demand = loc in ("at_support", "discount") or "Demand" in cur or "Discount" in cur
    struct_bull = s4.get("state") == "bullish" or (s4.get("event") == "CHOCH" and pdz == "discount")
    funding_neg = fs in ("negative", "neutral")   # không quá đông long
    oi_not_short = not (pdir == "down" and oi == "rising")   # không có "new shorts" bán thật
    btc_break_dn = (btc.get("price_location") == "breakdown"
                    or (btc.get("structure_4h") == "bearish" and btc.get("event") == "BOS"
                        and btc.get("premium_discount") == "discount"))
    btc_ok = not btc_break_dn
    clear_inval = s4.get("invalidation") is not None or c.get("support") is not None
    scvd = c.get("spot_cvd_state")
    spot_ok = None if scvd is None else scvd in ("buying", "flat")   # spot KHÔNG bán tháo

    return [
        {"label": "Giá tại H4/D1 demand (support/discount)", "ok": at_demand},
        {"label": "Cấu trúc H4 bullish hoặc higher-low (CHOCH ở discount)", "ok": struct_bull},
        {"label": "Funding không đông long (âm/trung tính)", "ok": funding_neg},
        {"label": "OI không đỡ bán short thật", "ok": oi_not_short},
        {"label": "BTC không phá xuống hỗ trợ chính", "ok": btc_ok},
        {"label": "Spot flow không bán tháo / có cầu", "ok": spot_ok},   # Module 5
        {"label": "Có invalidation rõ phía dưới vùng", "ok": clear_inval},
    ]


def _score(conds: list[dict]) -> int:
    return sum(1 for x in conds if x["ok"] is True)


def decision_state(c: dict, btc: dict) -> dict:
    """Tổng hợp -> dict Decision State. `btc` = btc_regime (rỗng {} cho chính BTC)."""
    if c.get("error"):
        return {}
    shorts = _short_conditions(c, btc)
    longs = _long_conditions(c, btc)
    ss, ls = _score(shorts), _score(longs)

    # Chọn hướng: bên nào nhiều điều kiện đạt hơn (dùng CHECKLIST của bên đó để hiển thị).
    tie = ss == ls
    if ss >= ls:
        direction, conds, score = "short", shorts, ss
    else:
        direction, conds, score = "long", longs, ls

    # Gate SETUP bằng điều kiện #1 (giá PHẢI ở đúng zone) + phải hơn phía kia >=1 điểm.
    # Nhiều điều kiện dùng chung (invalidation/BTC/OI-not) đúng cho cả 2 chiều -> chỉ
    # riêng điểm cao KHÔNG đủ; phải đang Ở vùng vào lệnh mới là setup hành động được.
    at_zone = conds[0]["ok"] is True
    struct_ok = conds[1]["ok"] is True
    margin = abs(ss - ls)
    if tie or margin == 0:
        grade, direction = "none", "none"          # 2 chiều ngang nhau -> không có lợi thế
    elif score >= 4 and at_zone:
        grade = "setup"
    elif score >= 4 and struct_ok:
        grade = "watch"                            # thiên hướng rõ nhưng giá CHƯA tới zone
    elif score >= 3:
        grade = "watch"
    else:
        grade, direction = "none", "none"

    # Stage: confirmation nếu cấu trúc H4 đã KHỚP hướng; ngược lại anticipation (vào sớm).
    s4state = (c.get("structure_4h") or {}).get("state")
    if direction == "none":
        stage = None
    elif (direction == "short" and s4state == "bearish") or (direction == "long" and s4state == "bullish"):
        stage = "confirmation"
    else:
        stage = "anticipation"

    # Label
    if direction == "none":
        label = ("NO SETUP — tín hiệu 2 chiều xung đột" if tie and max(ss, ls) >= 4
                 else "NO SETUP — đứng ngoài")
    else:
        head = "SHORT" if direction == "short" else "LONG"
        verb = "SETUP" if grade == "setup" else "WATCH"
        label = f"{head} {verb} — {stage.capitalize()}"

    # Reasons (bullet, chỉ nêu yếu tố nổi bật)
    reasons = []
    if direction != "none":
        s4 = c.get("structure_4h") or {}
        reasons.append(f"H4 {s4.get('state')}" + (f" ({s4.get('event')})" if s4.get("event") else ""))
        reasons.append(f"Giá: {c.get('price_location')}" + (f" · {c.get('current_zone')}" if c.get("current_zone") else ""))
        reasons.append(f"Funding {c.get('funding_state')} · OI {c.get('oi_trend')} · {c.get('deriv_read')}")
        if btc:
            side = "below" if direction == "short" else "above"
            liq = btc.get("liquidity_below") if direction == "short" else btc.get("liquidity_above")
            reasons.append(f"BTC {btc.get('structure_4h')}/{btc.get('price_location')}"
                           + (f" · liquidity {side} {('/'.join(f'{v:g}' for v in liq))}" if liq else ""))
        reasons.append(f"Spot flow: {c.get('flow_read') or 'chưa có data'}")
        if c.get("liq_magnet") and c.get("liq_magnet") != "balanced":
            reasons.append(f"Liquidity magnet: {c.get('liq_magnet')}")

    # Invalidation — phải nằm ĐÚNG PHÍA đối diện hướng lệnh (short: TRÊN giá; long: DƯỚI).
    # structure_4h.invalidation chỉ hợp lệ khi cấu trúc CÙNG hướng lệnh (bearish->short =
    # protected lower-high ở TRÊN; bullish->long = protected higher-low ở DƯỚI). Nếu ngược
    # hướng (vd short khi cấu trúc bullish) thì mốc đó nằm SAI phía -> fallback zone S/R.
    px = c.get("price")
    s4 = c.get("structure_4h") or {}
    sinval = s4.get("invalidation")
    if direction == "short":
        lvl = sinval if (s4.get("state") == "bearish" and sinval and px and sinval > px) else None
        lvl = lvl or (c.get("resistance") or {}).get("hi") or (c.get("in_zone") or {}).get("hi")
        invalidation = f"H4 đóng nến TRÊN {lvl:g}" if lvl and (not px or lvl > px) else None
    elif direction == "long":
        lvl = sinval if (s4.get("state") == "bullish" and sinval and px and sinval < px) else None
        lvl = lvl or (c.get("support") or {}).get("lo") or (c.get("in_zone") or {}).get("lo")
        invalidation = f"H4 đóng nến DƯỚI {lvl:g}" if lvl and (not px or lvl < px) else None
    else:
        invalidation = None

    return {"direction": direction, "stage": stage, "label": label, "grade": grade,
            "score": score, "max": 7, "checklist_ok": score,
            "reasons": reasons, "invalidation": invalidation, "checklist": conds}
