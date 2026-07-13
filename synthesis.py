"""
synthesis.py — Lớp TỔNG HỢP: biến "danh sách chỉ báo" thành "đọc nhanh + nước đi".

Vấn đề bản cũ: card liệt kê 5 block song song, không nói các chỉ báo CỘNG HƯỞNG
hay ĐÁNH NHAU thế nào, không ra nước đi. Module này (rule-based, tất định) làm:
  1. Mỗi layer bỏ 1 PHIẾU có trọng số (bull/bear/neutral) — trọng số theo độ tin
     cậy: cấu trúc/vị trí cao, flow/liquidity thấp (đã gắn nhãn "xấp xỉ").
  2. CONFLUENCE: nhóm chỉ báo cùng hướng tạo thành 1 "câu chuyện".
  3. CONFLICT: cặp lực nặng nhất ngược nhau (vd cấu trúc bearish ⚔ giá ở hỗ trợ).
  4. NARRATIVE: 1 câu đọc nhanh theo mẫu tình huống.
  5. PLAYS: nước đi có điều kiện (trigger → hành động + stop + target) từ zone S/R.

Không phải bot: nước đi là KỊCH BẢN CÓ ĐIỀU KIỆN ("nếu giá làm X thì Y"), tôn trọng
tín hiệu edge yếu — giúp lọc, không hứa thắng.
"""

from __future__ import annotations

_LAYER = {"bias": "Bias 4H", "structure": "Cấu trúc 4H", "location": "Vị trí giá",
          "deriv": "Phái sinh/OI", "flow": "Spot flow", "liquidity": "Liquidity",
          "trend1d": "Khung 1D"}
_DIRW = {"bull": "long", "bear": "short", "neutral": "trung tính"}


def _loc_side(c: dict) -> str:
    loc = c.get("price_location")
    if loc in ("at_support", "discount"):
        return "support"
    if loc in ("at_resistance", "premium"):
        return "resistance"
    if loc in ("breakout", "breakdown"):
        return loc
    return "mid"


def _deriv_note(c: dict) -> str:
    pd, oi = c.get("price_dir"), c.get("oi_trend")
    if pd == "up" and oi == "rising":
        return "có cầu thật (OI tăng)"
    if pd == "up" and oi == "falling":
        return "rally do short covering (yếu)"
    if pd == "down" and oi == "rising":
        return "lực bán thật (short mới)"
    if pd == "down" and oi == "falling":
        return "long deleveraging (có thể washout)"
    return "phái sinh trung tính"


def _votes(c: dict) -> list[dict]:
    """Mỗi layer 1 phiếu {layer, dir, w, note}. dir ∈ bull/bear/neutral."""
    v: list[dict] = []

    def add(layer, d, w, note):
        v.append({"layer": _LAYER[layer], "key": layer, "dir": d, "w": w, "note": note})

    b = c.get("bias")
    add("bias", "bull" if b == "long" else "bear" if b == "short" else "neutral", 2,
        f"trend 4H {c.get('trend_4h')}")

    s4 = (c.get("structure_4h") or {}).get("state")
    add("structure", "bull" if s4 == "bullish" else "bear" if s4 == "bearish" else "neutral", 3,
        f"SMC 4H {s4}")

    side = _loc_side(c)
    loc_dir = "bull" if side in ("support", "breakout") else "bear" if side in ("resistance", "breakdown") else "neutral"
    add("location", loc_dir, 3, f"giá {c.get('price_location')}")

    pd, oi = c.get("price_dir"), c.get("oi_trend")
    if pd == "up" and oi == "rising":
        dd = "bull"
    elif (pd == "down" and oi == "rising") or (pd == "up" and oi == "falling"):
        dd = "bear"
    elif pd == "down" and oi == "falling":
        dd = "bear"
    else:
        dd = "neutral"
    add("deriv", dd, 2, _deriv_note(c))

    sc = c.get("spot_cvd_state")
    add("flow", "bull" if sc == "buying" else "bear" if sc == "selling" else "neutral", 1,
        f"spot {sc or 'n/a'}")

    mag = c.get("liq_magnet")
    add("liquidity", "bull" if mag == "upside" else "bear" if mag == "downside" else "neutral", 1,
        f"magnet {mag}")

    t1 = (c.get("structure_1d") or {}).get("state")
    add("trend1d", "bull" if t1 == "bullish" else "bear" if t1 == "bearish" else "neutral", 1,
        f"SMC 1D {t1}")
    return v


def _net(votes: list[dict]) -> tuple[int, str]:
    s = sum((1 if v["dir"] == "bull" else -1 if v["dir"] == "bear" else 0) * v["w"] for v in votes)
    bias = ("bullish" if s >= 5 else "lean-bull" if s >= 2 else
            "bearish" if s <= -5 else "lean-bear" if s <= -2 else "mixed")
    return s, bias


def _confluence(c: dict) -> list[str]:
    out = []
    oi, sc, fs = c.get("oi_trend"), c.get("spot_cvd_state"), c.get("funding_state")
    side, pd = _loc_side(c), c.get("price_dir")
    if oi == "falling" and sc == "selling" and fs == "positive":
        out.append("OI giảm + spot bán + funding+ → phe long đang tháo chạy")
    if oi == "rising" and sc == "buying":
        out.append("OI tăng + spot mua → cầu thật đang vào")
    if side == "resistance" and pd == "up" and oi == "falling":
        out.append("Giá lên kháng cự bằng short covering → rally cạn hơi")
    if side == "support" and pd == "down" and oi == "falling":
        out.append("Xả vào hỗ trợ mạnh + long deleveraging → có thể quét đáy hơn bán bền")
    if side == "support" and c.get("liq_magnet") == "upside":
        out.append("Ở hỗ trợ + nam châm phía trên → thiên nảy lên")
    return out


def _conflict(votes: list[dict]) -> str | None:
    bull = [v for v in votes if v["dir"] == "bull" and v["w"] >= 2]
    bear = [v for v in votes if v["dir"] == "bear" and v["w"] >= 2]
    if not (bull and bear):
        return None
    a = max(bull, key=lambda v: v["w"])
    b = max(bear, key=lambda v: v["w"])
    return f"{a['layer']} (long) ⚔ {b['layer']} (short)"


def _zstr(z: dict | None) -> str:
    if not z:
        return "?"
    return f"{z['lo']:g}–{z['hi']:g}" if z.get("hi") != z.get("lo") else f"{z['lo']:g}"


def _narrative(c: dict, net_bias: str) -> str:
    side = _loc_side(c)
    sd = (c.get("structure_4h") or {}).get("state")
    dn = _deriv_note(c)
    sup, res = _zstr(c.get("support")), _zstr(c.get("resistance"))
    if side == "support" and sd == "bearish":
        return f"Bò gấu ngắn hạn (4H CHOCH xuống) nhưng giá xả vào hỗ trợ {sup} — {dn}; vùng giằng co, chờ giá chọn phe."
    if side == "resistance" and sd == "bullish":
        return f"Đẩy lên kháng cự {res} nhưng {dn} — coi chừng từ chối; chờ xác nhận trước khi short."
    if side == "support" and sd == "bullish":
        return f"Giá giữ hỗ trợ {sup} thuận cấu trúc tăng — thiên LONG, chờ trigger reclaim."
    if side == "resistance" and sd == "bearish":
        return f"Giá chạm kháng cự {res} thuận cấu trúc giảm — thiên SHORT, {dn}."
    if side == "breakout":
        return f"Phá đỉnh — momentum tăng ({dn}); canh retest giữ để theo."
    if side == "breakdown":
        return f"Phá đáy — momentum giảm ({dn}); canh retest để theo."
    if net_bias in ("bullish", "lean-bull"):
        return f"Thiên LONG nhưng giá lửng giữa vùng ({sup} ↔ {res}) — chờ về hỗ trợ hoặc phá lên."
    if net_bias in ("bearish", "lean-bear"):
        return f"Thiên SHORT nhưng giá lửng giữa vùng ({sup} ↔ {res}) — chờ hồi lên kháng cự hoặc phá xuống."
    return f"Tín hiệu trộn, giá giữa vùng ({sup} ↔ {res}) — đứng ngoài chờ rõ."


def _plays(c: dict) -> list[dict]:
    """Nước đi có điều kiện từ zone S/R + liquidity. trigger → action + stop + target."""
    sup, res = c.get("support"), c.get("resistance")
    la = c.get("liquidity_above") or []
    lb = c.get("liquidity_below") or []
    inval = (c.get("decision") or {}).get("invalidation")
    plays = []
    if sup and res:
        # LONG khi reclaim đỉnh vùng hỗ trợ (giá đang ở/dưới hỗ trợ) hoặc phá kháng cự
        long_trig = f"Đóng H4 > {sup['hi']:g}"
        tgt_up = " / ".join(f"{x:g}" for x in (la[:2] or [res['lo']]))
        plays.append({"trigger": long_trig, "action": "LONG",
                      "detail": f"stop < {sup['lo']:g} · target {tgt_up}"})
        # SHORT khi mất đáy vùng hỗ trợ
        short_trig = f"Đóng H4 < {sup['lo']:g}"
        tgt_dn = " / ".join(f"{x:g}" for x in (lb[:2] or [sup['lo']]))
        stop = f"{inval.split()[-1]}" if inval and "TRÊN" in (inval or "") else f"{res['hi']:g}"
        plays.append({"trigger": short_trig, "action": "SHORT",
                      "detail": f"stop > {stop} · target {tgt_dn}"})
        # Kẹt giữa → đứng ngoài
        plays.append({"trigger": f"Kẹt {sup['hi']:g}–{res['lo']:g}", "action": "ĐỨNG NGOÀI",
                      "detail": "chưa có phe thắng, chờ 1 trong 2 mốc trên"})
    return plays


def synthesize(c: dict, btc: dict) -> dict:
    if c.get("error"):
        return {}
    votes = _votes(c)
    net, net_bias = _net(votes)
    conf = _confluence(c)
    conflict = _conflict(votes)
    narrative = _narrative(c, net_bias)
    plays = _plays(c)

    bull_w = sum(v["w"] for v in votes if v["dir"] == "bull")
    bear_w = sum(v["w"] for v in votes if v["dir"] == "bear")
    return {"net": net, "net_bias": net_bias, "bull_w": bull_w, "bear_w": bear_w,
            "votes": votes, "confluence": conf, "conflict": conflict,
            "narrative": narrative, "plays": plays}
