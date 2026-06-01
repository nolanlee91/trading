"""
dashboard.py — TRỢ LÝ QUYẾT ĐỊNH swing (không phải bot, không ra lệnh).

Mỗi coin hiện NGỮ CẢNH để con người tự quyết:
  - Trend 4H + 1D (EMA stack)
  - Funding hiện tại + percentile lịch sử (đám đông đang lệch đâu)
  - Funding velocity (đang đổi nhanh không)
  - Độ căng giá so EMA20 (tính bằng ATR)
  - Momentum (RSI) + return 7 ngày
  - Cờ cảnh báo + 1 dòng "đọc" heuristic

KHÔNG bịa "confidence 82%". Đây là ngữ cảnh; quyết định là của anh.

  python dashboard.py            # dùng cache
  python dashboard.py --refresh  # kéo data mới nhất
"""

from __future__ import annotations

import argparse
import sys

import yaml

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

from data import fetch_ohlcv
from data_funding import fetch_funding
from indicators import atr, ema, rsi


def trend_state(c, e20, e50, e200) -> str:
    if e20 > e50 > e200:
        return "bullish"
    if e20 < e50 < e200:
        return "bearish"
    return "mixed"


def analyze(spot, perp, cfg, force):
    d = cfg["data"]
    fb = dict(symbol=spot, exchange="binance", market="spot",
              since=d["since"], until=d["until"], cache_dir=d["cache_dir"], force=force)
    h4 = fetch_ohlcv(timeframe="4h", **fb)
    d1 = fetch_ohlcv(timeframe="1d", **fb)
    fund = fetch_funding(perp, "binance", d["since"], d["until"], d["cache_dir"], force=force)

    # 4H features
    e20 = ema(h4["close"], 20); e50 = ema(h4["close"], 50); e200 = ema(h4["close"], 200)
    r = rsi(h4["close"], 14); a = atr(h4["high"], h4["low"], h4["close"], 14)
    px = h4["close"].iloc[-1]
    dist_atr = (px - e20.iloc[-1]) / a.iloc[-1]
    t4 = trend_state(px, e20.iloc[-1], e50.iloc[-1], e200.iloc[-1])

    # 1D trend
    de20 = ema(d1["close"], 20); de50 = ema(d1["close"], 50); de200 = ema(d1["close"], 200)
    t1d = trend_state(d1["close"].iloc[-1], de20.iloc[-1], de50.iloc[-1], de200.iloc[-1])
    ret7 = d1["close"].iloc[-1] / d1["close"].iloc[-8] - 1

    # Funding
    f_now = fund["funding"].iloc[-1]
    f_pctl = (fund["funding"] < f_now).mean() * 100
    ann = f_now * 3 * 365 * 100
    f_recent = fund["funding"].iloc[-9:].mean()      # ~3 ngày
    f_prev = fund["funding"].iloc[-18:-9].mean()
    vel = "tăng" if f_recent > f_prev else "giảm"

    # ── Cờ cảnh báo (rule-based, bảo thủ) ──
    flags = []
    if f_pctl <= 10:
        flags.append("Funding cực ÂM (đông short) — bối cảnh squeeze LÊN (edge yếu theo nghiên cứu)")
    elif f_pctl >= 90:
        flags.append("Funding cực DƯƠNG (đông long) — rủi ro flush XUỐNG nếu tin xấu")
    if dist_atr >= 1.5:
        flags.append(f"Giá căng +{dist_atr:.1f} ATR trên EMA20 — chờ hồi hơn đuổi")
    elif dist_atr <= -1.5:
        flags.append(f"Giá thấp {dist_atr:.1f} ATR dưới EMA20 — quá bán ngắn hạn")
    if r.iloc[-1] >= 70:
        flags.append(f"RSI {r.iloc[-1]:.0f} quá mua (4H)")
    elif r.iloc[-1] <= 30:
        flags.append(f"RSI {r.iloc[-1]:.0f} quá bán (4H)")
    if t4 == "mixed":
        flags.append("Trend 4H không rõ — cân nhắc đứng ngoài")

    # ── Dòng "đọc" heuristic ──
    if t4 == "bullish" and -1.5 < dist_atr < 0.5 and f_pctl < 85:
        read = "Uptrend + giá gần EMA20 → vùng vào long cổ điển (nếu hợp kế hoạch của anh)."
    elif t4 == "bullish" and dist_atr >= 1.5:
        read = "Uptrend nhưng căng → chờ pullback, đừng đuổi."
    elif t4 == "bearish":
        read = "Downtrend → long ngược trend rủi ro cao; ưu tiên đứng ngoài/chờ."
    elif f_pctl <= 10 and t4 != "bearish":
        read = "Funding cực âm + trend không xấu → có thể đón squeeze, nhưng edge yếu, size nhỏ."
    else:
        read = "Ngữ cảnh hỗn hợp → không có lợi thế rõ; kiên nhẫn thường tốt hơn."

    return dict(spot=spot, px=px, t4=t4, t1d=t1d, dist_atr=dist_atr,
                rsi=r.iloc[-1], ret7=ret7, f_now=f_now, f_pctl=f_pctl, ann=ann,
                vel=vel, atr_pct=a.iloc[-1] / px * 100, flags=flags, read=read,
                asof=h4["time"].iloc[-1])


def card(x) -> None:
    print("\n" + "─" * 70)
    print(f"  {x['spot']}   ${x['px']:,.2f}      (cập nhật {x['asof']})")
    print("─" * 70)
    print(f"  Trend      : 4H {x['t4']:<8} | 1D {x['t1d']}")
    print(f"  Giá vs EMA : {x['dist_atr']:+.1f} ATR so EMA20 (4H)")
    print(f"  Momentum   : RSI {x['rsi']:.0f} (4H) | 7 ngày {x['ret7']*100:+.1f}%")
    print(f"  Funding    : {x['f_now']*100:+.4f}%/8h (~{x['ann']:+.0f}%/năm) "
          f"| percentile {x['f_pctl']:.0f}% | đang {x['vel']}")
    print(f"  Volatility : ATR {x['atr_pct']:.1f}%/nến 4H")
    if x["flags"]:
        print("  Cờ:")
        for f in x["flags"]:
            print(f"    • {f}")
    print(f"  → Đọc (heuristic): {x['read']}")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--refresh", action="store_true", help="kéo data mới nhất")
    args = ap.parse_args()
    with open("config.yaml", "r", encoding="utf-8") as f:
        cfg = yaml.safe_load(f)

    print("\n" + "=" * 70)
    print("  SWING DASHBOARD — đây là NGỮ CẢNH, không phải lệnh. Anh quyết định.")
    print("=" * 70)
    for spot, perp in [("BTC/USDT", "BTC/USDT:USDT"), ("ETH/USDT", "ETH/USDT:USDT"),
                       ("SOL/USDT", "SOL/USDT:USDT")]:
        card(analyze(spot, perp, cfg, args.refresh))


if __name__ == "__main__":
    main()
