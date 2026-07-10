"""
app.py — Trader Decision Assistant (HUD), không phải bot.

4 layer:
  L1 Context   : trend 4H/1D, funding percentile, RSI, distance EMA, ATR.
  L2 Risk Score: cộng điểm rủi ro khi VÀO LONG ngay bây giờ (0-2 bình thường,
                 3-5 cẩn thận, 6+ rủi ro cao).
  L3 Checklist : các điều kiện thuận lợi cho long, hiện ✓/✗ + tally X/5.
  L4 Journal   : ghi lệnh thật + context lúc vào + PnL -> sau 200-300 lệnh tìm
                 EDGE CÁ NHÂN (anh thắng/cháy ở bối cảnh nào). SQLite, bền.

Chạy local:  uvicorn app:app --reload
Railway:     uvicorn app:app --host 0.0.0.0 --port $PORT  (xem Procfile)
             Gắn Volume + đặt DB_PATH=/data/journal.db để journal không mất khi redeploy.
"""

from __future__ import annotations

import datetime as dt
import json
import os
import sqlite3
import threading
import time
import urllib.error
import urllib.request

import ccxt
from apscheduler.schedulers.background import BackgroundScheduler
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse

from data import fetch_ohlcv
from data_flow import fetch_flow
from data_funding import fetch_funding
from data_oi import fetch_oi
from decision import decision_state
from indicators import atr, ema, rsi
from levels import sr_levels
from liquidity import liquidity_map
from structure import market_structure

# Coin theo BASE asset; nhãn hiển thị (cũng là key journal) giữ ổn định để không
# phá các lệnh đã ghi. HYPE chỉ có trên Hyperliquid (sàn user trade thật).
COINS = ["BTC", "ETH", "SOL", "HYPE"]
DISPLAY = {"BTC": "BTC/USDT", "ETH": "ETH/USDT", "SOL": "SOL/USDT", "HYPE": "HYPE/USDC"}

# Mỗi sàn: cách dựng symbol OHLCV/funding từ base, loại market, và CHU KỲ FUNDING
# (giờ) — Hyperliquid trả funding mỗi 1h, các sàn perp khác 8h. Chu kỳ này quyết
# định cách quy đổi sang %/năm và cửa sổ đo vận tốc funding.
EXCHANGE_PROFILES = {
    # Hyperliquid: dùng chính symbol perp USDC cho cả giá lẫn funding (đúng sàn user đánh).
    "hyperliquid": {"ohlcv": lambda b: f"{b}/USDC:USDC", "funding": lambda b: f"{b}/USDC:USDC",
                    "market": "swap", "funding_h": 1},
    "bybit":   {"ohlcv": lambda b: f"{b}/USDT", "funding": lambda b: f"{b}/USDT:USDT",
                "market": "spot", "funding_h": 8},
    "binance": {"ohlcv": lambda b: f"{b}/USDT", "funding": lambda b: f"{b}/USDT:USDT",
                "market": "spot", "funding_h": 8},
    "okx":     {"ohlcv": lambda b: f"{b}/USDT", "funding": lambda b: f"{b}/USDT:USDT",
                "market": "spot", "funding_h": 8},
}

CACHE = "./data_cache"
LOOKBACK_DAYS = 450
FUNDING_PCT_DAYS = 365
DB_PATH = os.environ.get("DB_PATH", "journal.db")
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")          # đặt biến môi trường, KHÔNG hardcode
GEMINI_MODEL = os.environ.get("GEMINI_MODEL", "gemini-2.5-flash")  # đổi qua env GEMINI_MODEL

# Ưu tiên Hyperliquid (sàn user trade) → fallback proxy nếu HL không vào được
# (Binance hay bị 451 ở mạng công ty/cloud). Ép 1 sàn bằng env DATA_EXCHANGE.
DATA_EXCHANGES = ([os.environ["DATA_EXCHANGE"]] if os.environ.get("DATA_EXCHANGE")
                  else ["hyperliquid", "bybit", "binance", "okx"])
_RESOLVED_EX = None

# Journal: dùng PostgreSQL nếu có DATABASE_URL (Railway -> dùng chung mọi thiết bị,
# 1 database). Fallback SQLite khi chạy local (không có DATABASE_URL).
USE_PG = bool(os.environ.get("DATABASE_URL"))
if USE_PG:
    import psycopg2
    import psycopg2.extras
PH = "%s" if USE_PG else "?"   # placeholder tham số khác nhau giữa 2 backend

SNAPSHOT: dict = {"asof": None, "status": "đang tải lần đầu...", "coins": []}
_LOCK = threading.Lock()


# ─────────────────────────── Layer 1-3: phân tích ───────────────────────────
def _trend(c, e20, e50, e200) -> str:
    if e20 > e50 > e200:
        return "bullish"
    if e20 < e50 < e200:
        return "bearish"
    return "mixed"


def _since(days: int) -> str:
    d = dt.datetime.now(dt.timezone.utc) - dt.timedelta(days=days)
    return d.strftime("%Y-%m-%dT%H:%M:%SZ")


def data_exchange() -> str:
    """Dò 1 lần sàn nào vào được (ưu tiên Hyperliquid, tránh 451 Binance), cache lại."""
    global _RESOLVED_EX
    if _RESOLVED_EX:
        return _RESOLVED_EX
    for name in DATA_EXCHANGES:
        prof = EXCHANGE_PROFILES.get(name)
        if not prof:
            continue
        try:
            probe = prof["ohlcv"]("BTC")     # symbol BTC theo đúng quy ước sàn đó
            getattr(ccxt, name)({"enableRateLimit": True}).fetch_ohlcv(probe, "4h", limit=1)
            _RESOLVED_EX = name
            return name
        except Exception:
            continue
    _RESOLVED_EX = DATA_EXCHANGES[0]   # fallback: vẫn trả 1 tên để báo lỗi rõ ràng
    return _RESOLVED_EX


def _btc_ref_d1():
    """Chuỗi đóng cửa 1D của BTC để tính tương quan (đọc cache; BTC đã được
    phân tích đầu danh sách nên parquet sẵn có). force=False để khỏi tải lại."""
    ex = data_exchange()
    prof = EXCHANGE_PROFILES[ex]
    d = fetch_ohlcv(symbol=prof["ohlcv"]("BTC"), exchange=ex, market=prof["market"],
                    timeframe="1d", since=_since(LOOKBACK_DAYS), until=None,
                    cache_dir=CACHE, force=False)
    return d["close"]


def _derivatives_read(oi_df, price_now: float, price_24h: float | None, funding_ann: float) -> dict:
    """Module 1 — diễn giải combo Price × OI × Funding (không chỉ hiện số funding).

    Logic kinh điển của thị trường phái sinh:
      giá LÊN + OI TĂNG  = new longs (cầu thật)
      giá LÊN + OI GIẢM  = short covering (rally yếu, không phải cầu thật)
      giá XUỐNG + OI TĂNG = new shorts (lực bán thật)
      giá XUỐNG + OI GIẢM = long closing / deleveraging (xả đòn bẩy)
    OI trend đo bằng % đổi trung bình 24h gần nhất so với 24h trước (proxy Bybit).
    """
    # ── OI trend: so trung bình ~24h gần nhất với ~24h trước (điểm 1h) ──
    oi_now = oi_trend = None
    oi_chg = 0.0
    if oi_df is not None and len(oi_df) >= 48:
        s = oi_df["oi"]
        recent = float(s.iloc[-24:].mean())
        prior = float(s.iloc[-48:-24].mean())
        oi_now = float(s.iloc[-1])
        oi_chg = (recent / prior - 1) * 100 if prior else 0.0
        oi_trend = "rising" if oi_chg > 2 else "falling" if oi_chg < -2 else "flat"

    # ── Price direction 24h ──
    if price_24h:
        pchg = (price_now / price_24h - 1) * 100
        price_dir = "up" if pchg > 0.75 else "down" if pchg < -0.75 else "sideway"
    else:
        pchg, price_dir = 0.0, "sideway"

    # ── Funding state (theo %/năm, deadband 2%) ──
    funding_state = ("positive" if funding_ann > 2 else "negative" if funding_ann < -2 else "neutral")

    # ── Diễn giải combo ──
    if oi_trend is None:
        read = "OI không có dữ liệu"
    else:
        table = {
            ("up", "rising"): "New longs — cầu thật đang vào",
            ("up", "falling"): "Short covering — rally yếu, KHÔNG phải cầu thật",
            ("up", "flat"): "Giá lên nhưng OI đứng — thiếu lực xác nhận",
            ("down", "rising"): "New shorts — lực bán thật đang vào",
            ("down", "falling"): "Long closing / deleveraging — xả đòn bẩy",
            ("down", "flat"): "Giá xuống, OI đứng — chưa rõ lực",
            ("sideway", "rising"): "Tích luỹ vị thế 2 chiều — chờ phá biên",
            ("sideway", "falling"): "Giảm đòn bẩy, đi ngang",
            ("sideway", "flat"): "Trầm lắng — không có tín hiệu phái sinh",
        }
        read = table.get((price_dir, oi_trend), "—")

    return {"oi_now": round(oi_now) if oi_now is not None else None,
            "oi_trend": oi_trend, "oi_chg_pct": round(oi_chg, 1),
            "price_dir": price_dir, "price_chg_24h": round(pchg, 1),
            "funding_state": funding_state, "deriv_read": read}


def analyze_coin(symbol: str, force: bool) -> dict:
    """symbol = nhãn hiển thị (vd 'BTC/USDT'); base lấy phần trước '/'."""
    base = symbol.split("/")[0]
    ex = data_exchange()
    prof = EXCHANGE_PROFILES[ex]
    fund_h = prof["funding_h"]                       # chu kỳ funding của sàn (giờ)
    ohlcv_sym = prof["ohlcv"](base)
    fund_sym = prof["funding"](base)

    fb = dict(symbol=ohlcv_sym, exchange=ex, market=prof["market"],
              since=_since(LOOKBACK_DAYS), until=None, cache_dir=CACHE, force=force)
    h4 = fetch_ohlcv(timeframe="4h", **fb)
    d1 = fetch_ohlcv(timeframe="1d", **fb)
    fund = fetch_funding(fund_sym, ex, _since(FUNDING_PCT_DAYS + 30), None, CACHE, force=force)

    e20 = ema(h4["close"], 20); e50 = ema(h4["close"], 50); e200 = ema(h4["close"], 200)
    r = rsi(h4["close"], 14); a = atr(h4["high"], h4["low"], h4["close"], 14)
    px = float(h4["close"].iloc[-1]); atr_v = float(a.iloc[-1]); r_now = float(r.iloc[-1])
    dist_atr = (px - float(e20.iloc[-1])) / atr_v if atr_v else 0.0
    t4 = _trend(px, e20.iloc[-1], e50.iloc[-1], e200.iloc[-1])

    de20 = ema(d1["close"], 20); de50 = ema(d1["close"], 50); de200 = ema(d1["close"], 200)
    t1d = _trend(d1["close"].iloc[-1], de20.iloc[-1], de50.iloc[-1], de200.iloc[-1])
    ret7 = float(d1["close"].iloc[-1] / d1["close"].iloc[-8] - 1)

    # ── N-5: ngữ cảnh bổ sung (volume bất thường, vị trí trong biên 30 ngày, corr BTC) ──
    vol = d1["volume"]
    vavg = float(vol.iloc[-21:-1].mean()) if len(vol) >= 21 else float(vol.mean())
    vol_ratio = round(float(vol.iloc[-1]) / vavg, 2) if vavg else 1.0   # >1 = sôi động hơn TB
    win = d1.iloc[-30:]
    hi30 = float(win["high"].max()); lo30 = float(win["low"].min())
    to_high = round((px / hi30 - 1) * 100, 1)   # % so với ĐỈNH 30N (âm = dưới đỉnh)
    to_low = round((px / lo30 - 1) * 100, 1)    # % so với ĐÁY 30N (dương = trên đáy)
    if base == "BTC":
        corr_btc = 1.0
    else:
        try:
            ra = d1["close"].pct_change().dropna().iloc[-30:].reset_index(drop=True)
            rb = _btc_ref_d1().pct_change().dropna().iloc[-30:].reset_index(drop=True)
            n = min(len(ra), len(rb))
            corr_btc = round(float(ra.iloc[-n:].reset_index(drop=True)
                                   .corr(rb.iloc[-n:].reset_index(drop=True))), 2) if n >= 10 else None
        except Exception:
            corr_btc = None

    f_win = fund[fund["time"] >= fund["time"].max() - dt.timedelta(days=FUNDING_PCT_DAYS)]
    f_now = float(fund["funding"].iloc[-1])
    f_pctl = float((f_win["funding"] < f_now).mean() * 100)
    # %/năm = rate mỗi kỳ × số kỳ/ngày × 365. Số kỳ/ngày = 24/chu_kỳ_giờ (HL 1h→24, perp 8h→3).
    ann = f_now * (24 / fund_h) * 365 * 100
    # Vận tốc: so trung bình ~3 ngày gần nhất với 3 ngày trước đó (cùng horizon mọi sàn).
    w = max(2, round(3 * 24 / fund_h))               # số điểm funding ~ 3 ngày
    fr = fund["funding"]
    vel = ("tăng" if len(fr) >= 2 * w and fr.iloc[-w:].mean() > fr.iloc[-2 * w:-w].mean()
           else "giảm")
    # Velocity dạng SỐ (đổi annualized %/năm giữa 2 cửa sổ ~3 ngày) cho UI.
    vel_num = (round((fr.iloc[-w:].mean() - fr.iloc[-2 * w:-w].mean()) * (24 / fund_h) * 365 * 100, 2)
               if len(fr) >= 2 * w else 0.0)

    # ── Module 1: Derivatives Read (Price × OI × Funding) ──
    try:
        oi_df = fetch_oi(base, CACHE, force=force)
    except Exception:
        oi_df = None
    px_24h = float(h4["close"].iloc[-7]) if len(h4) >= 7 else None   # 6 nến 4H = 24h
    deriv = _derivatives_read(oi_df, px, px_24h, ann)

    # ── Module 2: Support/Resistance + Supply/Demand (thuần tính từ OHLCV) ──
    try:
        sr = sr_levels(h4, d1, px, atr_v)
    except Exception:
        sr = {"resistance": None, "support": None, "in_zone": None,
              "price_location": "mid", "zones": []}

    # ── Module 3: Market Structure / SMC (thuần tính từ OHLCV) ──
    try:
        ms = market_structure(h4, d1, px, atr_v)
    except Exception:
        ms = {"structure_4h": {"state": "ranging", "event": None, "invalidation": None},
              "structure_1d": {"state": "ranging", "event": None}, "current_zone": None,
              "premium_discount": "equilibrium", "range_pos": 0.5, "range_hi": None,
              "range_lo": None, "liquidity_above": [], "liquidity_below": [],
              "eqh": [], "eql": [], "fvg_up": None, "fvg_down": None}

    # ── Module 5: Spot/Perp Flow (CVD proxy — xấp xỉ, lấp điều kiện #6 Decision) ──
    try:
        flow = fetch_flow(base, CACHE, force=force)
    except Exception:
        flow = {"spot_state": None, "spot_ratio": None, "perp_state": None, "perp_ratio": None,
                "coinbase_prem_bps": None, "flow_read": "Flow: chưa có data", "spot_cvd_state": None}

    # ── Module 6: Liquidity Map / Liquidation zones (xấp xỉ; tái dùng EQH/EQL của M3) ──
    try:
        liq = liquidity_map(px, atr_v, ms, deriv["oi_trend"], f_pctl)
    except Exception:
        liq = {"liq_above": None, "liq_below": None, "long_liq": [], "short_liq": [],
               "liq_magnet": "balanced", "liq_magnet_why": [], "liq_oi_note": None}

    # Bias = đánh THEO trend 4H (đừng đánh ngược trend lớn).
    bias = "long" if t4 == "bullish" else "short" if t4 == "bearish" else "neutral"

    # ── L2: Risk score — rủi ro khi vào lệnh THEO BIAS ngay bây giờ ──
    risk, why = 0, []
    if bias == "long":
        if f_pctl >= 95: risk += 2; why.append("funding >95pct (đông long)")
        if r_now >= 75: risk += 2; why.append("RSI >75 (quá mua)")
        if dist_atr >= 2: risk += 3; why.append("giá >2 ATR TRÊN EMA20 (căng lên, dễ hồi xuống)")
        if t1d == "bearish": risk += 2; why.append("1D ngược bias (bearish)")
    elif bias == "short":
        if f_pctl <= 5: risk += 2; why.append("funding <5pct (đông short -> dễ squeeze LÊN)")
        if r_now <= 25: risk += 2; why.append("RSI <25 (quá bán -> dễ nảy lên)")
        if dist_atr <= -2: risk += 3; why.append("giá <-2 ATR DƯỚI EMA20 (căng xuống, dễ hồi lên)")
        if t1d == "bullish": risk += 2; why.append("1D ngược bias (bullish)")
    else:
        risk = 6; why.append("trend 4H không rõ -> không có bias, nên đứng ngoài")
    band = "Bình thường" if risk <= 2 else ("Cẩn thận" if risk <= 5 else "Rủi ro cao")

    # ── L3: Checklist theo BIAS (điều kiện thuận lợi để vào lệnh thuận trend) ──
    if bias == "long":
        checklist = [
            {"label": "4H bullish", "ok": t4 == "bullish"},
            {"label": "1D không bearish", "ok": t1d != "bearish"},
            {"label": "Giá gần/dưới EMA20 (pullback để mua)", "ok": dist_atr < 0.5},
            {"label": "RSI không quá nóng (<70)", "ok": r_now < 70},
            {"label": "Funding không đông long (<85pct)", "ok": f_pctl < 85},
        ]
    elif bias == "short":
        checklist = [
            {"label": "4H bearish", "ok": t4 == "bearish"},
            {"label": "1D không bullish", "ok": t1d != "bullish"},
            {"label": "Giá gần/trên EMA20 (hồi lên kháng cự để bán)", "ok": dist_atr > -0.5},
            {"label": "RSI không quá bán (>30)", "ok": r_now > 30},
            {"label": "Funding không đông short (>15pct)", "ok": f_pctl > 15},
        ]
    else:
        checklist = [{"label": "Trend 4H rõ ràng (bull/bear)", "ok": False}]
    n_ok = sum(1 for c in checklist if c["ok"])

    flags = []
    if f_pctl <= 10:
        flags.append("Funding cực ÂM (đông short) — bối cảnh squeeze LÊN (edge yếu)")
    elif f_pctl >= 90:
        flags.append("Funding cực DƯƠNG (đông long) — rủi ro flush XUỐNG")
    if dist_atr >= 1.5:
        flags.append(f"Giá căng +{dist_atr:.1f} ATR trên EMA20 — chờ hồi hơn đuổi")
    elif dist_atr <= -1.5:
        flags.append(f"Giá {dist_atr:.1f} ATR dưới EMA20 — quá bán ngắn hạn")
    if vol_ratio >= 2:
        flags.append(f"Volume 1D ×{vol_ratio} trung bình — biến động bất thường")
    if to_high >= -2:
        flags.append(f"Sát ĐỈNH 30 ngày (cách {to_high}%) — coi chừng kháng cự")
    elif to_low <= 2:
        flags.append(f"Sát ĐÁY 30 ngày (+{to_low}%) — coi chừng hỗ trợ/đảo chiều")
    # Cờ phái sinh: các combo "bẫy" đáng chú ý nhất
    if deriv["price_dir"] == "up" and deriv["oi_trend"] == "falling" and deriv["funding_state"] == "positive":
        flags.append("Short covering + funding dương — rally do đóng short, không phải cầu thật")
    elif deriv["price_dir"] == "down" and deriv["oi_trend"] == "rising" and deriv["funding_state"] == "negative":
        flags.append("New shorts + funding âm — đông short, coi chừng squeeze LÊN")
    # Cờ vị trí giá (Module 2)
    _res, _sup, _iz = sr["resistance"], sr["support"], sr["in_zone"]
    if sr["price_location"] == "at_resistance" and _iz and _iz["strength"] >= 4:
        flags.append(f"Giá tại KHÁNG CỰ mạnh {_iz['lo']:g}–{_iz['hi']:g} ({_iz['strength']}/5) — vùng bán ưu tiên")
    elif sr["price_location"] == "at_support" and _iz and _iz["strength"] >= 4:
        flags.append(f"Giá tại HỖ TRỢ mạnh {_iz['lo']:g}–{_iz['hi']:g} ({_iz['strength']}/5) — vùng mua ưu tiên")
    elif sr["price_location"] == "breakout":
        flags.append("Phá đỉnh — không còn kháng cự phía trên trong tầm nhìn")
    elif sr["price_location"] == "breakdown":
        flags.append("Phá đáy — không còn hỗ trợ phía dưới trong tầm nhìn")
    # Cờ cấu trúc (Module 3)
    if ms["structure_4h"]["event"] == "CHOCH":
        flags.append(f"4H CHOCH ({ms['structure_4h']['state']}) — cấu trúc vừa đổi tính chất, tín hiệu sớm")
    if ms["current_zone"] and "FVG" in ms["current_zone"]:
        flags.append(f"Giá trong {ms['current_zone']} — vùng imbalance chưa test")
    # Cờ flow (Module 5): perp mua nhưng spot không theo = rally yếu
    if flow["perp_state"] == "buying" and flow["spot_state"] in ("flat", "selling"):
        flags.append("Perp mua nhưng spot không theo — rally do perp, thiếu cầu spot thật")
    elif flow["spot_state"] == "buying" and deriv["oi_trend"] == "rising":
        flags.append("Spot mua + OI tăng — cầu thật (real demand)")
    # Cờ nam châm thanh khoản (Module 6)
    if liq["liq_magnet"] == "downside" and liq["liq_below"]:
        flags.append(f"Nam châm thanh khoản phía DƯỚI ({liq['liq_below']['lo']:g}–{liq['liq_below']['hi']:g})")
    elif liq["liq_magnet"] == "upside" and liq["liq_above"]:
        flags.append(f"Nam châm thanh khoản phía TRÊN ({liq['liq_above']['lo']:g}–{liq['liq_above']['hi']:g})")

    return {"symbol": symbol, "price": px, "trend_4h": t4, "trend_1d": t1d,
            "dist_atr": round(dist_atr, 2), "rsi": round(r_now, 0),
            "ret7": round(ret7 * 100, 1), "funding": round(f_now * 100, 4),
            "funding_ann": round(ann, 0), "funding_pctl": round(f_pctl, 0),
            "funding_vel": vel, "funding_vel_num": vel_num, "atr_pct": round(atr_v / px * 100, 1),
            "vol_ratio": vol_ratio, "to_high": to_high, "to_low": to_low, "corr_btc": corr_btc,
            "bias": bias, "risk_score": risk, "risk_band": band, "risk_why": why,
            "checklist": checklist, "checklist_ok": n_ok, "checklist_n": len(checklist),
            "flags": flags, **deriv,
            "price_location": sr["price_location"], "resistance": sr["resistance"],
            "support": sr["support"], "in_zone": sr["in_zone"], "sr_zones": sr["zones"],
            **ms, **flow, **liq}


def _btc_regime(btc: dict) -> dict:
    """Rút gọn bối cảnh BTC để mọi coin dùng chung trong Decision State (Layer 7)."""
    s4 = btc.get("structure_4h") or {}
    return {"trend_4h": btc.get("trend_4h"), "trend_1d": btc.get("trend_1d"),
            "structure_4h": s4.get("state"), "event": s4.get("event"),
            "price_location": btc.get("price_location"),
            "premium_discount": btc.get("premium_discount"),
            "liquidity_above": btc.get("liquidity_above"),
            "liquidity_below": btc.get("liquidity_below"), "bias": btc.get("bias")}


def refresh(force: bool = False) -> None:
    coins = []
    for base in COINS:
        label = DISPLAY[base]
        try:
            coins.append(analyze_coin(label, force))
        except Exception as e:
            coins.append({"symbol": label, "error": str(e)})
    # Layer 7: Decision State — cần BTC trước để làm btc_regime cho các coin khác.
    btc = next((c for c in coins if c.get("symbol", "").startswith("BTC") and not c.get("error")), None)
    regime = _btc_regime(btc) if btc else {}
    for c in coins:
        if c.get("error"):
            continue
        c["btc_regime"] = "" if c is btc else f"{regime.get('structure_4h')}/{regime.get('price_location')}"
        c["decision"] = decision_state(c, {} if c is btc else regime)
    with _LOCK:
        SNAPSHOT["coins"] = coins
        SNAPSHOT["asof"] = dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
        SNAPSHOT["status"] = "ok"
        SNAPSHOT["source"] = _RESOLVED_EX or "?"
    snapshot_daily(coins)   # N-4: chụp bối cảnh 1 lần/ngày (idempotent)


_REFRESHING = False


def trigger_refresh() -> None:
    """Kích refresh CHẠY NỀN (không block request). Tránh nút Refresh treo 30-60s ->
    frontend timeout -> hiện nhầm 'backend unreachable'. Chỉ 1 lần chạy đồng thời."""
    global _REFRESHING
    if _REFRESHING:
        return
    _REFRESHING = True

    def _run():
        global _REFRESHING
        try:
            refresh()
        finally:
            _REFRESHING = False

    threading.Thread(target=_run, daemon=True).start()


def _zone_str(z: dict | None) -> str | None:
    """Zone -> 'lo-hi (str/5)' để lưu journal gọn (Module 2)."""
    if not z:
        return None
    return f"{z['lo']:g}-{z['hi']:g} ({z['strength']}/5)"


def _struct_str(s: dict | None) -> str | None:
    """Structure dict -> 'bullish/BOS' cho journal (Module 3)."""
    if not s or not s.get("state"):
        return None
    return f"{s['state']}/{s['event']}" if s.get("event") else s["state"]


def _liq_str(levels: list | None) -> str | None:
    """[1720,1650,1500] -> '1720/1650/1500'."""
    if not levels:
        return None
    return "/".join(f"{v:g}" for v in levels)


def _ctx_for(symbol: str) -> dict:
    with _LOCK:
        for c in SNAPSHOT["coins"]:
            if c.get("symbol") == symbol:
                return c
    return {}


# ─────────────────────────── Trợ lý hỏi-đáp (Gemini) ───────────────────────────
GEMINI_SYS = """Bạn là trợ lý PHÂN TÍCH BỐI CẢNH giao dịch crypto cho một trader swing
discretionary, KHÔNG phải cố vấn đầu tư. Quy tắc bắt buộc:
- CHỈ dùng dữ liệu JSON được cung cấp. KHÔNG bịa số.
- Các tín hiệu (trend, funding, RSI) có EDGE YẾU đã được kiểm chứng — TUYỆT ĐỐI không
  dự báo giá tự tin, không nói chắc chắn lên/xuống.
- Trả lời như NGỮ CẢNH hỗ trợ quyết định: nêu yếu tố ủng hộ và rủi ro cho cả 2 chiều.
- Luôn nhắc người dùng tự quyết định và quản trị rủi ro/đòn bẩy.
- Ngắn gọn, tiếng Việt, cụ thể bằng số. Nếu hỏi về vị thế (vd short từ giá X), tính
  trạng thái lãi/lỗ và mức giá quan trọng (EMA20 = kháng cự/hỗ trợ) từ dữ liệu."""


def _gemini_context() -> str:
    """Bối cảnh GỌN cho Gemini (chỉ field cốt lõi) — giảm token để đỡ chạm quota/TPM."""
    with _LOCK:
        coins = SNAPSHOT.get("coins", [])
        asof = SNAPSHOT.get("asof")
        source = SNAPSHOT.get("source")
    slim = []
    for c in coins:
        if c.get("error"):
            slim.append({"symbol": c.get("symbol"), "error": c["error"]})
            continue
        row = {k: c.get(k) for k in (
            "symbol", "price", "bias", "risk_score", "risk_band", "trend_4h", "trend_1d",
            "rsi", "funding_pctl", "funding_ann", "funding_vel", "dist_atr", "atr_pct",
            "vol_ratio", "to_high", "to_low", "corr_btc", "checklist_ok", "checklist_n",
            "oi_trend", "oi_chg_pct", "price_dir", "funding_state", "deriv_read",
            "price_location", "resistance", "support",
            "structure_4h", "structure_1d", "current_zone", "premium_discount",
            "liquidity_above", "liquidity_below", "fvg_up", "fvg_down", "btc_regime",
            "spot_state", "perp_state", "flow_read", "coinbase_prem_bps",
            "liq_above", "liq_below", "liq_magnet",
            "flags")}
        d = c.get("decision") or {}
        row["decision"] = d.get("label")
        row["setup_score"] = f"{d.get('score')}/{d.get('max')}" if d else None
        row["invalidation"] = d.get("invalidation")
        slim.append(row)
    return json.dumps({"asof": asof, "source": source, "coins": slim}, ensure_ascii=False)


def ask_gemini(question: str) -> str:
    if not GEMINI_API_KEY:
        return ("Chưa cấu hình GEMINI_API_KEY. Lấy key free tại Google AI Studio, rồi đặt "
                "biến môi trường GEMINI_API_KEY (local: $env:GEMINI_API_KEY='...'; Railway: "
                "thêm ở mục Variables) và khởi động lại.")
    ctx = _gemini_context()
    body = {
        "systemInstruction": {"parts": [{"text": GEMINI_SYS}]},
        "contents": [{"parts": [{"text":
            f"Dữ liệu thị trường hiện tại (JSON):\n{ctx}\n\nCâu hỏi của trader: {question}"}]}],
        "generationConfig": {"temperature": 0.4},
    }
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{GEMINI_MODEL}:generateContent"
    data_bytes = json.dumps(body).encode("utf-8")

    # Thử tối đa 2 lần: lỗi tạm thời (429 quota/phút, 503 quá tải) chờ rồi thử lại 1 lần.
    for attempt in range(2):
        req = urllib.request.Request(
            url, data=data_bytes, method="POST",
            headers={"Content-Type": "application/json", "x-goog-api-key": GEMINI_API_KEY})
        try:
            with urllib.request.urlopen(req, timeout=40) as r:
                data = json.loads(r.read())
            return data["candidates"][0]["content"]["parts"][0]["text"]
        except urllib.error.HTTPError as e:
            if e.code in (429, 503) and attempt == 0:
                time.sleep(6)
                continue
            if e.code == 429:
                return ("⚠️ Gemini hết quota (429). Đây là giới hạn free-tier của Google, "
                        "không phải lỗi app. Cách xử lý: (1) đợi ~1 phút rồi hỏi lại (nếu là "
                        "giới hạn theo PHÚT); (2) nếu hết hạn mức NGÀY, đợi reset (nửa đêm giờ "
                        "US Pacific) hoặc BẬT BILLING cho project của API key này (429 kèm "
                        "'billing' nghĩa là key đang ở free-tier); (3) đổi model bằng biến "
                        "môi trường GEMINI_MODEL (vd 'gemini-2.5-flash', 'gemini-2.0-flash-lite'). "
                        "Các chỉ số/checklist trên dashboard vẫn hoạt động bình thường.")
            return f"Lỗi Gemini API ({e.code}): {e.read().decode('utf-8', 'ignore')[:200]}"
        except Exception as e:
            return f"Lỗi gọi Gemini: {e}"
    return "⚠️ Gemini tạm thời không phản hồi (quota/quá tải). Thử lại sau ít phút."


# ─────────────────── Layer 4: Journal (PostgreSQL hoặc SQLite) ───────────────────
def _conn():
    if USE_PG:
        return psycopg2.connect(os.environ["DATABASE_URL"])
    c = sqlite3.connect(DB_PATH)
    c.row_factory = sqlite3.Row
    return c


def run_write(sql: str, params=(), returning: bool = False):
    conn = _conn()
    try:
        cur = conn.cursor()
        cur.execute(sql, params)
        rid = cur.fetchone()[0] if returning else (None if USE_PG else cur.lastrowid)
        conn.commit()
        return rid
    finally:
        conn.close()


def run_query(sql: str, params=()) -> list:
    conn = _conn()
    try:
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) if USE_PG else conn.cursor()
        cur.execute(sql, params)
        return [dict(r) for r in cur.fetchall()]
    finally:
        conn.close()


def _existing_cols(table: str) -> set:
    """Tên cột hiện có của 1 bảng (để ALTER thêm cột còn thiếu, chạy cả 2 backend)."""
    if USE_PG:
        rows = run_query("SELECT column_name FROM information_schema.columns "
                         f"WHERE table_name={PH}", (table,))
        return {r["column_name"] for r in rows}
    return {r["name"] for r in run_query(f"PRAGMA table_info({table})")}


def init_db() -> None:
    id_type = "SERIAL PRIMARY KEY" if USE_PG else "INTEGER PRIMARY KEY AUTOINCREMENT"
    num = "DOUBLE PRECISION" if USE_PG else "REAL"
    run_write(f"""CREATE TABLE IF NOT EXISTS trades(
        id {id_type}, ts_open TEXT, symbol TEXT, side TEXT, reason TEXT,
        ctx_price {num}, ctx_funding_pctl {num}, ctx_trend4h TEXT,
        ctx_trend1d TEXT, ctx_rsi {num}, ctx_dist_atr {num},
        ts_close TEXT, exit_price {num}, pnl_pct {num}, status TEXT)""")

    # N-5 persist: thêm cột ngữ cảnh mới vào bảng trades đã tồn tại (SQLite không
    # hỗ trợ ADD COLUMN IF NOT EXISTS -> tự kiểm cột rồi mới ALTER). Cột cũ giữ NULL.
    have = _existing_cols("trades")
    for col in ("ctx_vol_ratio", "ctx_to_high", "ctx_to_low", "ctx_corr_btc"):
        if col not in have:
            run_write(f"ALTER TABLE trades ADD COLUMN {col} {num}")
    # Module 1: cột ngữ cảnh phái sinh (TEXT — trạng thái, không phải số).
    for col in ("ctx_oi_trend", "ctx_funding_state", "ctx_price_dir"):
        if col not in have:
            run_write(f"ALTER TABLE trades ADD COLUMN {col} TEXT")
    # Module 2: cột ngữ cảnh S/R (TEXT — vị trí + vùng gần nhất dạng "lo-hi (str/5)").
    for col in ("ctx_price_location", "ctx_nearest_res", "ctx_nearest_sup"):
        if col not in have:
            run_write(f"ALTER TABLE trades ADD COLUMN {col} TEXT")
    # Module 3: cột ngữ cảnh cấu trúc/SMC (TEXT).
    for col in ("ctx_structure_4h", "ctx_structure_1d", "ctx_current_zone",
                "ctx_liq_above", "ctx_liq_below"):
        if col not in have:
            run_write(f"ALTER TABLE trades ADD COLUMN {col} TEXT")
    # Layer 7: btc_regime (ctx) + entry_type (anticipation/confirmation — attr của lệnh).
    for col in ("ctx_btc_regime", "entry_type"):
        if col not in have:
            run_write(f"ALTER TABLE trades ADD COLUMN {col} TEXT")
    # Module 5: spot flow state (ctx).
    if "ctx_spot_cvd_state" not in have:
        run_write("ALTER TABLE trades ADD COLUMN ctx_spot_cvd_state TEXT")
    # Module 6: liquidity magnet (ctx).
    if "ctx_liq_magnet" not in have:
        run_write("ALTER TABLE trades ADD COLUMN ctx_liq_magnet TEXT")

    # N-4: ảnh chụp bối cảnh thị trường mỗi ngày (kể cả ngày KHÔNG vào lệnh) để
    # sau này so "ngày đánh vs ngày bỏ qua". 1 dòng / coin / ngày (snap_date UTC).
    run_write(f"""CREATE TABLE IF NOT EXISTS daily_snapshots(
        id {id_type}, snap_date TEXT, ts TEXT, symbol TEXT, price {num},
        trend4h TEXT, trend1d TEXT, rsi {num}, dist_atr {num},
        funding_pctl {num}, funding_ann {num}, vol_ratio {num},
        to_high {num}, to_low {num}, corr_btc {num}, bias TEXT, risk_score {num})""")


def snapshot_daily(coins: list) -> None:
    """Ghi snapshot bối cảnh 1 lần/ngày/coin (idempotent: bỏ qua nếu hôm nay đã có)."""
    today = dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%d")
    now = dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%d %H:%M")
    for c in coins:
        if c.get("error"):
            continue
        try:
            dup = run_query(f"SELECT 1 FROM daily_snapshots WHERE snap_date={PH} AND symbol={PH}",
                            (today, c["symbol"]))
            if dup:
                continue
            run_write(
                "INSERT INTO daily_snapshots(snap_date,ts,symbol,price,trend4h,trend1d,rsi,"
                "dist_atr,funding_pctl,funding_ann,vol_ratio,to_high,to_low,corr_btc,bias,risk_score) "
                f"VALUES({','.join([PH] * 16)})",
                (today, now, c["symbol"], c.get("price"), c.get("trend_4h"), c.get("trend_1d"),
                 c.get("rsi"), c.get("dist_atr"), c.get("funding_pctl"), c.get("funding_ann"),
                 c.get("vol_ratio"), c.get("to_high"), c.get("to_low"), c.get("corr_btc"),
                 c.get("bias"), c.get("risk_score")))
        except Exception:
            pass   # snapshot không bao giờ được làm hỏng refresh data


def _rsi_bucket(v):
    if v is None: return "?"
    return "<35" if v < 35 else "35-50" if v < 50 else "50-65" if v < 65 else "65-75" if v < 75 else ">75"


def _fpctl_bucket(v):
    if v is None: return "?"
    return "<25" if v < 25 else "25-50" if v < 50 else "50-75" if v < 75 else "75-90" if v < 90 else ">90"


def _vol_bucket(v):
    if v is None: return "?"
    return "thấp<0.8" if v < 0.8 else "BT0.8-1.5" if v < 1.5 else "cao1.5-2.5" if v < 2.5 else "spike>2.5"


# ── Lớp dịch cho UI (index.html): nội bộ dùng tiếng Việt/bullish, UI cần từ vựng riêng ──
_TREND_UI = {"bullish": "up", "bearish": "down", "mixed": "flat"}
_BIAS_UI = {"long": "LONG", "short": "SHORT", "neutral": "NEUTRAL"}
_BAND_UI = {"Bình thường": "low", "Cẩn thận": "medium", "Rủi ro cao": "high"}


def _iso(ts: str) -> str:
    """'2026-06-02 15:49' (UTC) -> ISO '2026-06-02T15:49:00Z' để JS new Date() đọc đúng."""
    if not ts:
        return ts
    t = ts.replace(" ", "T")
    if len(t) == 16:           # thiếu giây
        t += ":00"
    return t + ("Z" if not t.endswith("Z") else "")


def _coin_view(c: dict) -> dict:
    """Dịch 1 coin trong SNAPSHOT sang từ vựng UI."""
    if c.get("error"):
        return {"symbol": c.get("symbol"), "error": c["error"]}
    v = dict(c)
    v["trend_4h"] = _TREND_UI.get(c.get("trend_4h"), "flat")
    v["trend_1d"] = _TREND_UI.get(c.get("trend_1d"), "flat")
    v["bias"] = _BIAS_UI.get(c.get("bias"), "NEUTRAL")
    v["risk_band"] = _BAND_UI.get(c.get("risk_band"), "medium")
    v["funding"] = (c.get("funding") or 0) / 100.0   # UI nhân lại ×100; nội bộ đã ×100
    v["funding_vel"] = c.get("funding_vel_num", 0.0)  # UI cần SỐ
    return v


def _trade_view(r: dict) -> dict:
    """Dịch 1 dòng bảng trades sang shape UI mong đợi."""
    t4, t1d = r.get("ctx_trend4h") or "?", r.get("ctx_trend1d") or "?"
    fp, rs = r.get("ctx_funding_pctl"), r.get("ctx_rsi")
    ctx = (f"Funding {('?' if fp is None else round(fp))}p · "
           f"RSI {('?' if rs is None else round(rs))} · Trend {t4}/{t1d}")
    return {"id": r.get("id"), "symbol": r.get("symbol"), "side": (r.get("side") or "").lower(),
            "status": r.get("status"), "entry": r.get("ctx_price"), "exit": r.get("exit_price"),
            "pnl": r.get("pnl_pct"), "reason": r.get("reason"), "context": ctx}


# ─────────────────────────── FastAPI ───────────────────────────
app = FastAPI(title="Trader Decision Assistant")


@app.on_event("startup")
def _startup() -> None:
    init_db()
    threading.Thread(target=refresh, daemon=True).start()
    sched = BackgroundScheduler(timezone="UTC")
    sched.add_job(refresh, "interval", minutes=5, max_instances=1, coalesce=True)
    sched.start()


@app.get("/api/dashboard")
def api_dashboard(refresh_now: bool = False) -> JSONResponse:
    if refresh_now:
        trigger_refresh()       # chạy nền, trả ngay snapshot hiện có
    with _LOCK:
        asof = _iso((SNAPSHOT.get("asof") or "").replace(" UTC", ""))
        out = {"asof": asof, "status": SNAPSHOT.get("status"),
               "source": SNAPSHOT.get("source"), "refreshing": _REFRESHING,
               "coins": [_coin_view(c) for c in SNAPSHOT.get("coins", [])]}
    return JSONResponse(out)


@app.post("/api/journal/open")
async def journal_open(req: Request) -> JSONResponse:
    b = await req.json()
    ctx = _ctx_for(b["symbol"])
    now = dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%d %H:%M")
    sql = ("INSERT INTO trades(ts_open,symbol,side,reason,ctx_price,ctx_funding_pctl,"
           "ctx_trend4h,ctx_trend1d,ctx_rsi,ctx_dist_atr,"
           "ctx_vol_ratio,ctx_to_high,ctx_to_low,ctx_corr_btc,"
           "ctx_oi_trend,ctx_funding_state,ctx_price_dir,"
           "ctx_price_location,ctx_nearest_res,ctx_nearest_sup,"
           "ctx_structure_4h,ctx_structure_1d,ctx_current_zone,ctx_liq_above,ctx_liq_below,"
           "ctx_btc_regime,entry_type,ctx_spot_cvd_state,ctx_liq_magnet,status) "
           f"VALUES({','.join([PH] * 29)},'open')")
    entry_type = b.get("entry_type") or (ctx.get("decision") or {}).get("stage")
    params = (now, b["symbol"], b.get("side", "long").lower(), b.get("reason", ""),
              ctx.get("price"), ctx.get("funding_pctl"), ctx.get("trend_4h"),
              ctx.get("trend_1d"), ctx.get("rsi"), ctx.get("dist_atr"),
              ctx.get("vol_ratio"), ctx.get("to_high"), ctx.get("to_low"), ctx.get("corr_btc"),
              ctx.get("oi_trend"), ctx.get("funding_state"), ctx.get("price_dir"),
              ctx.get("price_location"), _zone_str(ctx.get("resistance")), _zone_str(ctx.get("support")),
              _struct_str(ctx.get("structure_4h")), _struct_str(ctx.get("structure_1d")),
              ctx.get("current_zone"), _liq_str(ctx.get("liquidity_above")), _liq_str(ctx.get("liquidity_below")),
              ctx.get("btc_regime"), entry_type, ctx.get("spot_cvd_state"), ctx.get("liq_magnet"))
    rid = run_write(sql + " RETURNING id", params, returning=True) if USE_PG else run_write(sql, params)
    return JSONResponse({"id": rid})


@app.post("/api/journal/close")
async def journal_close(req: Request) -> JSONResponse:
    b = await req.json()
    now = dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%d %H:%M")
    rows = run_query(f"SELECT * FROM trades WHERE id={PH}", (b["id"],))
    if not rows:
        return JSONResponse({"error": "not found"}, status_code=404)
    row = rows[0]
    entry, exitp = row["ctx_price"], float(b["exit_price"])
    pnl = (exitp / entry - 1) if row["side"] == "long" else (entry / exitp - 1)
    run_write(f"UPDATE trades SET ts_close={PH},exit_price={PH},pnl_pct={PH},status='closed' WHERE id={PH}",
              (now, exitp, round(pnl * 100, 2), b["id"]))
    return JSONResponse({"ok": True, "pnl_pct": round(pnl * 100, 2)})


@app.post("/api/journal/manual")
async def journal_manual(req: Request) -> JSONResponse:
    """Ghi 1 lệnh ĐÃ ĐÓNG nhập tay (entry/exit thật) — cho lệnh quá khứ/ngoài app."""
    b = await req.json()
    side = b.get("side", "short").lower()
    entry, exitp = float(b["entry"]), float(b["exit"])
    pnl = (exitp / entry - 1) if side == "long" else (entry / exitp - 1)
    ctx = _ctx_for(b.get("symbol", "")) or {}
    now = dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%d %H:%M")
    sql = ("INSERT INTO trades(ts_open,symbol,side,reason,ctx_price,ctx_funding_pctl,"
           "ctx_trend4h,ctx_trend1d,ctx_rsi,ctx_dist_atr,"
           "ctx_vol_ratio,ctx_to_high,ctx_to_low,ctx_corr_btc,"
           "ctx_oi_trend,ctx_funding_state,ctx_price_dir,"
           "ctx_price_location,ctx_nearest_res,ctx_nearest_sup,"
           "ctx_structure_4h,ctx_structure_1d,ctx_current_zone,ctx_liq_above,ctx_liq_below,"
           "ctx_btc_regime,entry_type,ctx_spot_cvd_state,ctx_liq_magnet,"
           "ts_close,exit_price,pnl_pct,status) "
           f"VALUES({','.join([PH] * 32)},'closed')")
    params = (now, b.get("symbol", ""), side, b.get("reason", "") + " [nhập tay]",
              entry, ctx.get("funding_pctl"), ctx.get("trend_4h"), ctx.get("trend_1d"),
              ctx.get("rsi"), ctx.get("dist_atr"),
              ctx.get("vol_ratio"), ctx.get("to_high"), ctx.get("to_low"), ctx.get("corr_btc"),
              ctx.get("oi_trend"), ctx.get("funding_state"), ctx.get("price_dir"),
              ctx.get("price_location"), _zone_str(ctx.get("resistance")), _zone_str(ctx.get("support")),
              _struct_str(ctx.get("structure_4h")), _struct_str(ctx.get("structure_1d")),
              ctx.get("current_zone"), _liq_str(ctx.get("liquidity_above")), _liq_str(ctx.get("liquidity_below")),
              ctx.get("btc_regime"), b.get("entry_type"), ctx.get("spot_cvd_state"), ctx.get("liq_magnet"),
              now, exitp, round(pnl * 100, 2))
    rid = run_write(sql + " RETURNING id", params, returning=True) if USE_PG else run_write(sql, params)
    return JSONResponse({"id": rid, "pnl_pct": round(pnl * 100, 2)})


@app.get("/api/journal")
def journal_list() -> JSONResponse:
    rows = run_query("SELECT * FROM trades ORDER BY id DESC")
    return JSONResponse({"trades": [_trade_view(r) for r in rows]})


@app.get("/api/journal/stats")
def journal_stats() -> JSONResponse:
    allrows = run_query("SELECT * FROM trades")
    closed = [r for r in allrows if r.get("status") == "closed" and r.get("pnl_pct") is not None]
    total, n = len(allrows), len(closed)
    openc = sum(1 for r in allrows if r.get("status") == "open")
    EMPTY = "—"
    if n == 0:
        return JSONResponse({
            "total": total, "win_rate": 0, "avg_pnl": 0, "open": openc, "closed": 0,
            "best_funding_bucket": EMPTY, "worst_funding_bucket": EMPTY,
            "best_trend_regime": EMPTY, "worst_trend_regime": EMPTY,
            "best_rsi_bucket": EMPTY, "worst_rsi_bucket": EMPTY,
            "best_volume_bucket": EMPTY, "worst_volume_bucket": EMPTY})

    def best_worst(keyfn):
        groups = {}
        for r in closed:
            groups.setdefault(keyfn(r), []).append(r["pnl_pct"])
        avgs = {k: sum(v) / len(v) for k, v in groups.items()}
        return (max(avgs, key=avgs.get), min(avgs, key=avgs.get))

    bf = best_worst(lambda r: _fpctl_bucket(r.get("ctx_funding_pctl")))
    bt = best_worst(lambda r: r.get("ctx_trend4h") or "?")
    br = best_worst(lambda r: _rsi_bucket(r.get("ctx_rsi")))
    bv = best_worst(lambda r: _vol_bucket(r.get("ctx_vol_ratio")))
    wins = sum(1 for r in closed if r["pnl_pct"] > 0)
    return JSONResponse({
        "total": total, "win_rate": round(wins / n * 100, 1),
        "avg_pnl": round(sum(r["pnl_pct"] for r in closed) / n, 2), "open": openc, "closed": n,
        "best_funding_bucket": bf[0], "worst_funding_bucket": bf[1],
        "best_trend_regime": bt[0], "worst_trend_regime": bt[1],
        "best_rsi_bucket": br[0], "worst_rsi_bucket": br[1],
        "best_volume_bucket": bv[0], "worst_volume_bucket": bv[1]})


@app.get("/api/snapshots")
def snapshots_list(days: int = 30) -> JSONResponse:
    since = (dt.datetime.now(dt.timezone.utc) - dt.timedelta(days=days)).strftime("%Y-%m-%d")
    rows = run_query(f"SELECT * FROM daily_snapshots WHERE snap_date>={PH} "
                     "ORDER BY snap_date DESC, symbol", (since,))
    by_day: dict = {}
    for r in rows:
        by_day.setdefault(r["snap_date"], []).append(r)
    snaps = []
    for day, rs in by_day.items():
        longs = sum(1 for r in rs if r.get("bias") == "long")
        shorts = sum(1 for r in rs if r.get("bias") == "short")
        neutral = len(rs) - longs - shorts
        regime = ("bull" if longs > shorts and longs >= 2
                  else "bear" if shorts > longs and shorts >= 2 else "mixed")
        coins = [{"s": (r.get("symbol") or "").split("/")[0],
                  "b": _BIAS_UI.get(r.get("bias"), "NEUTRAL"),
                  "r": int(r.get("risk_score") or 0)}
                 for r in rs]
        snaps.append({"asof": _iso(rs[0].get("ts") or (day + " 00:00")),
                      "regime": regime, "coins": coins,
                      "summary": f"<b>{longs} long · {shorts} short · {neutral} trung lập.</b>"})
    return JSONResponse({"snapshots": snaps})


@app.post("/api/ask")
async def api_ask(req: Request) -> JSONResponse:
    b = await req.json()
    return JSONResponse({"answer": ask_gemini(b.get("question", ""))})


_INDEX_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "index.html")


@app.get("/", response_class=HTMLResponse)
def index() -> str:
    try:
        with open(_INDEX_PATH, encoding="utf-8") as f:
            return f.read()
    except FileNotFoundError:
        return PAGE   # fallback: bản HUD cũ nếu thiếu file thiết kế


PAGE = """<!doctype html><html lang="vi"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Trader Decision Assistant</title><style>
*{box-sizing:border-box}body{margin:0 auto;background:#0e1117;color:#e6e6e6;
font-family:system-ui,Segoe UI,Roboto,sans-serif;padding:14px;max-width:780px;-webkit-text-size-adjust:100%}
h1{font-size:19px;margin:4px 0}h2{font-size:15px;margin:18px 0 6px;color:#9aa4b2}
.sub{color:#8b95a5;font-size:12px;margin-bottom:12px}
.card{background:#161b22;border:1px solid #232a33;border-radius:12px;padding:14px;margin:10px 0}
.row{display:flex;justify-content:space-between;align-items:center;gap:8px}
.sym{font-weight:700;font-size:17px}.px{font-variant-numeric:tabular-nums;color:#cbd5e1;font-size:15px}
.grid{display:grid;grid-template-columns:1fr 1fr;gap:6px 14px;margin:8px 0;font-size:13px}
.k{color:#8b95a5}.bull{color:#3fb950}.bear{color:#f85149}.mixed{color:#d29922}
.badge{display:inline-block;padding:4px 10px;border-radius:20px;font-size:12px;font-weight:700}
.b-ok{background:#13361f;color:#3fb950}.b-warn{background:#3a3214;color:#d29922}.b-bad{background:#3d1719;color:#f85149}
.chk{font-size:13px;margin:3px 0}.y{color:#3fb950}.n{color:#f85149}
.flag{font-size:12px;color:#e3b341;margin:3px 0}
.read{font-size:13px;margin-top:8px;border-top:1px solid #232a33;padding-top:8px;color:#c9d1d9}
.warn{background:#1d2530;border-radius:8px;padding:8px;font-size:11px;color:#8b95a5;margin-bottom:12px}
button{background:#21262d;color:#e6e6e6;border:1px solid #30363d;border-radius:8px;padding:11px 14px;font-size:14px;cursor:pointer;min-height:44px}
input,select,textarea{background:#0e1117;color:#e6e6e6;border:1px solid #30363d;border-radius:8px;padding:10px;font-size:16px;min-height:44px}
.tw{overflow-x:auto;-webkit-overflow-scrolling:touch}
table{width:100%;border-collapse:collapse;font-size:12px;white-space:nowrap}
td,th{border-bottom:1px solid #232a33;padding:7px 6px;text-align:left}
.form{display:flex;flex-wrap:wrap;gap:8px;align-items:center}
.small{font-size:11px;color:#8b95a5}
@media(max-width:520px){
 .grid{grid-template-columns:1fr;gap:4px}
 .form{flex-direction:column;align-items:stretch}
 .form>*{width:100%}
 button{width:100%}
}
</style></head><body>
<h1>🎯 Trader Decision Assistant</h1>
<div class="sub" id="asof">đang tải...</div>
<div class="warn">⚠️ HUD hỗ trợ quyết định, KHÔNG phải lệnh mua/bán. Tín hiệu thị trường có edge yếu.
Giá trị thật nằm ở JOURNAL: ghi lệnh của chính anh để tìm EDGE CÁ NHÂN.</div>
<div id="app"></div>

<h2>💬 Hỏi trợ lý (Gemini) — bám dữ liệu thật</h2>
<div class="card">
 <div class="form">
  <input id="q" placeholder="vd: ETH đang thế nào? tôi đang short x5 từ 2080" style="flex:1;min-width:220px">
  <button onclick="ask()">Hỏi</button>
 </div>
 <div id="ans" class="read" style="white-space:pre-wrap"></div>
 <div class="small">Trả lời chỉ dựa trên dữ liệu hiện tại; tín hiệu edge yếu, KHÔNG phải lệnh.</div>
</div>

<h2>📓 Journal — ghi lệnh</h2>
<div class="card"><div class="form">
 <select id="j-sym"><option>BTC/USDT</option><option>ETH/USDT</option><option>SOL/USDT</option><option>HYPE/USDC</option></select>
 <select id="j-side"><option>long</option><option>short</option></select>
 <input id="j-reason" placeholder="Lý do vào (vd: pullback EMA20, funding âm)" style="flex:1;min-width:180px">
 <button onclick="openTrade()">＋ Ghi lệnh (chụp context hiện tại)</button>
</div><div class="small">Khi ghi, hệ thống tự lưu trend/funding/RSI/EMA tại thời điểm này.</div></div>

<div class="card"><div class="small" style="margin-bottom:6px">Hoặc ghi lệnh ĐÃ ĐÓNG (nhập tay entry/exit thật — cho lệnh quá khứ):</div>
<div class="form">
 <select id="m-sym"><option>ETH/USDT</option><option>BTC/USDT</option><option>SOL/USDT</option><option>HYPE/USDC</option></select>
 <select id="m-side"><option>short</option><option>long</option></select>
 <input id="m-entry" inputmode="decimal" placeholder="Giá vào (vd 2080)">
 <input id="m-exit" inputmode="decimal" placeholder="Giá ra (vd 1912)">
 <input id="m-reason" placeholder="Ghi chú" style="flex:1;min-width:140px">
 <button onclick="logManual()">✓ Ghi lệnh đã đóng</button>
</div></div>

<h2>📈 Lệnh & PnL</h2>
<div class="card" id="trades">chưa có lệnh.</div>

<h2>🧠 Edge cá nhân (cần đủ lệnh mới đáng tin)</h2>
<div class="card" id="stats">chưa có dữ liệu.</div>

<button id="refreshBtn" onclick="loadAll(true)">⟳ Refresh data</button>
<script>
const cls=t=>t==='bullish'?'bull':t==='bearish'?'bear':'mixed';
const bandCls=b=>b==='Bình thường'?'b-ok':b==='Cẩn thận'?'b-warn':'b-bad';
const biasCls=b=>b==='long'?'b-ok':b==='short'?'b-bad':'b-warn';
const biasTxt=b=>b==='long'?'BIAS: LONG':b==='short'?'BIAS: SHORT':'BIAS: ĐỨNG NGOÀI';
function card(c){
 if(c.error)return `<div class="card"><span class="sym">${c.symbol}</span> — lỗi: ${c.error}</div>`;
 const chk=c.checklist.map(x=>`<div class="chk"><span class="${x.ok?'y':'n'}">${x.ok?'✓':'✗'}</span> ${x.label}</div>`).join('');
 const flags=(c.flags||[]).map(f=>`<div class="flag">• ${f}</div>`).join('');
 return `<div class="card">
  <div class="row"><span class="sym">${c.symbol}</span>
   <span class="px">$${c.price.toLocaleString()}</span></div>
  <div style="margin:6px 0"><span class="badge ${biasCls(c.bias)}">${biasTxt(c.bias)}</span>
   &nbsp;<span class="badge ${bandCls(c.risk_band)}">Risk vào lệnh ${c.risk_score} · ${c.risk_band}</span></div>
  <div class="grid">
   <div><span class="k">Trend 4H/1D:</span> <span class="${cls(c.trend_4h)}">${c.trend_4h}</span> / <span class="${cls(c.trend_1d)}">${c.trend_1d}</span></div>
   <div><span class="k">Giá vs EMA20:</span> ${c.dist_atr>0?'+':''}${c.dist_atr} ATR</div>
   <div><span class="k">RSI / 7d:</span> ${c.rsi} / ${c.ret7>0?'+':''}${c.ret7}%</div>
   <div><span class="k">Funding:</span> ${c.funding_pctl}pct (${c.funding_vel})</div>
   <div><span class="k">Volume 1D:</span> ×${c.vol_ratio} TB</div>
   <div><span class="k">Biên 30N:</span> đỉnh ${c.to_high}% · đáy +${c.to_low}%</div>
   <div><span class="k">Corr BTC:</span> ${c.corr_btc==null?'—':c.corr_btc}</div>
  </div>
  <div class="small">Checklist ${c.bias==='long'?'mua':c.bias==='short'?'bán':'(chưa có bias)'}: ${c.checklist_ok}/${c.checklist_n} thuận lợi</div>
  ${chk}${flags}</div>`;
}
async function loadDash(force){
 const a=document.getElementById('asof');const btn=document.getElementById('refreshBtn');
 if(force){a.textContent='⏳ Đang kéo data mới (~30-60s)...';if(btn){btn.disabled=true;btn.textContent='⏳ Đang làm mới...';}}
 try{
  const r=await fetch('/api/dashboard'+(force?'?refresh_now=true':''));const d=await r.json();
  a.textContent=d.status==='ok'?('✅ Cập nhật: '+d.asof+' · nguồn '+(d.source||'?')):d.status;
  document.getElementById('app').innerHTML=(d.coins||[]).map(card).join('');
 }finally{ if(btn){btn.disabled=false;btn.textContent='⟳ Refresh data';} }
}
async function loadTrades(){
 const rows=await (await fetch('/api/journal')).json();
 if(!rows.length){document.getElementById('trades').textContent='chưa có lệnh.';return;}
 let h='<table><tr><th>#</th><th>coin</th><th>side</th><th>vào</th><th>ctx</th><th>PnL</th><th></th></tr>';
 for(const t of rows){
  const ctx=`${t.ctx_trend4h||'?'} · f${t.ctx_funding_pctl??'?'} · RSI${t.ctx_rsi??'?'}`;
  const pnl=t.status==='closed'?`<span class="${t.pnl_pct>0?'y':'n'}">${t.pnl_pct>0?'+':''}${t.pnl_pct}%</span>`:'<i>mở</i>';
  const act=t.status==='open'?`<button onclick="closeTrade(${t.id})">Đóng</button>`:'';
  h+=`<tr><td>${t.id}</td><td>${t.symbol}</td><td>${t.side}</td><td>${t.ts_open}<br><span class="small">$${t.ctx_price?.toLocaleString()||'?'}</span></td><td class="small">${ctx}</td><td>${pnl}</td><td>${act}</td></tr>`;
 }
 document.getElementById('trades').innerHTML='<div class="tw">'+h+'</table></div>';
}
async function loadStats(){
 const s=await (await fetch('/api/journal/stats')).json();
 if(!s.n){document.getElementById('stats').textContent='chưa có lệnh đã đóng.';return;}
 const tbl=(o)=>'<div class="tw"><table><tr><th>nhóm</th><th>n</th><th>win%</th><th>avg PnL</th></tr>'+
  Object.entries(o).map(([k,v])=>`<tr><td>${k}</td><td>${v.n}</td><td>${v.win}%</td><td class="${v.avg>0?'y':'n'}">${v.avg>0?'+':''}${v.avg}%</td></tr>`).join('')+'</table></div>';
 let h=`<div class="small">Tổng ${s.n} lệnh đã đóng · win ${s.win}% · avg ${s.avg_pnl}%`;
 h+= s.n<30?' — ⚠️ <30 lệnh, chưa đủ tin.':'';
 h+='</div><h3 style="font-size:13px;margin:10px 0 4px">Theo funding percentile</h3>'+tbl(s.by_funding);
 h+='<h3 style="font-size:13px;margin:10px 0 4px">Theo trend 4H</h3>'+tbl(s.by_trend4h);
 h+='<h3 style="font-size:13px;margin:10px 0 4px">Theo RSI</h3>'+tbl(s.by_rsi);
 document.getElementById('stats').innerHTML=h;
}
const byId=id=>document.getElementById(id);
async function openTrade(){
 const body={symbol:byId('j-sym').value,side:byId('j-side').value,reason:byId('j-reason').value};
 await fetch('/api/journal/open',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)});
 byId('j-reason').value='';loadTrades();loadStats();
}
async function logManual(){
 const entry=parseFloat(byId('m-entry').value),exit=parseFloat(byId('m-exit').value);
 if(!entry||!exit){alert('Nhập giá vào & giá ra');return;}
 await fetch('/api/journal/manual',{method:'POST',headers:{'Content-Type':'application/json'},
  body:JSON.stringify({symbol:byId('m-sym').value,side:byId('m-side').value,entry,exit,reason:byId('m-reason').value})});
 byId('m-entry').value='';byId('m-exit').value='';byId('m-reason').value='';loadTrades();loadStats();
}
async function closeTrade(id){
 const px=prompt('Giá thoát?');if(!px)return;
 await fetch('/api/journal/close',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({id,exit_price:parseFloat(px)})});
 loadTrades();loadStats();
}
async function ask(){
 const q=document.getElementById('q').value;if(!q)return;
 document.getElementById('ans').textContent='đang hỏi Gemini...';
 try{const r=await fetch('/api/ask',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({question:q})});
  const d=await r.json();document.getElementById('ans').textContent=d.answer;}
 catch(e){document.getElementById('ans').textContent='Lỗi: '+e;}
}
function loadAll(force){loadDash(force);loadTrades();loadStats();}
loadAll(false);setInterval(()=>loadDash(false),300000);
</script></body></html>"""
