"""
data_flow.py — Module 5: Spot / Perp Flow (CVD proxy). BẢN XẤP XỈ.

Giới hạn data free (đã kiểm chứng): không có CVD chuẩn per-trade lịch sử; Hyperliquid
fetch_trades đòi 'user' param (không lấy được flow toàn thị trường). Cách làm:
  - Lấy MẪU taker buy/sell gần nhất qua fetch_trades (có 'side') trên:
      spot: Bybit -> OKX ;  perp: Bybit.
  - Mỗi mẫu ~vài chục giây trades -> NHIỄU. Nên cache ROLLING ~12 mẫu (1h, refresh
    5') và dùng TỶ LỆ buy (buy/(buy+sell)) — bền với khoảng trống lấy mẫu, không tin
    vào CVD tuyệt đối (bị hụt do gap giữa các lần refresh).
  - Coinbase premium (BTC/ETH): (giá Coinbase - giá tham chiếu)/ref, bps.

Không phải CVD thật; là "ai đang chủ động mua/bán ngay lúc này" (spot vs perp).
"""

from __future__ import annotations

import datetime as dt
import os
from pathlib import Path

import ccxt
import pandas as pd

_EX_CACHE: dict = {}
_SPOT_NAME: str | None = None
KEEP = 12                      # số mẫu rolling giữ lại (≈1h nếu refresh 5')
SPOT_EXCHANGES = ["bybit", "okx"]


def _exchange(name: str, market: str) -> ccxt.Exchange:
    key = (name, market)
    ex = _EX_CACHE.get(key)
    if ex is None:
        ex = getattr(ccxt, name)({"enableRateLimit": True, "options": {"defaultType": market}})
        _EX_CACHE[key] = ex
    return ex


def _spot_name() -> str | None:
    global _SPOT_NAME
    if _SPOT_NAME:
        return _SPOT_NAME
    for name in SPOT_EXCHANGES:
        try:
            ex = _exchange(name, "spot")
            ex.load_markets()
            if ex.fetch_trades("BTC/USDT", limit=10):
                _SPOT_NAME = name
                return name
        except Exception:
            continue
    return None


def _sample(ex: ccxt.Exchange, sym: str) -> tuple[float, float] | None:
    """Tổng khối lượng taker buy/sell trong ~1000 trades gần nhất."""
    trades = ex.fetch_trades(sym, limit=1000)
    if not trades:
        return None
    buy = sell = 0.0
    for t in trades:
        a = t.get("amount") or 0.0
        if t.get("side") == "buy":
            buy += a
        elif t.get("side") == "sell":
            sell += a
    if buy == 0 and sell == 0:
        return None
    return buy, sell


def _state(buy: float, sell: float) -> tuple[str, float]:
    tot = buy + sell
    if tot <= 0:
        return "flat", 0.5
    ratio = buy / tot
    st = "buying" if ratio > 0.56 else "selling" if ratio < 0.44 else "flat"
    return st, ratio


def _roll(cache_dir: str, base: str, new_rows: list[dict]) -> pd.DataFrame:
    """Append mẫu mới vào cache rolling, giữ KEEP mẫu mới nhất mỗi market."""
    path = Path(cache_dir) / f"flow_{base}.parquet"
    cached = pd.read_parquet(path) if path.exists() else None
    new = pd.DataFrame(new_rows)
    df = pd.concat([cached, new], ignore_index=True) if cached is not None and len(cached) else new
    df = (df.sort_values("ts").groupby("market", group_keys=False).tail(KEEP).reset_index(drop=True))
    os.makedirs(cache_dir, exist_ok=True)
    df.to_parquet(path, index=False)
    return df


def fetch_flow(base: str, cache_dir: str, force: bool = False) -> dict:
    """Trả spot/perp state + ratio + delta (rolling), coinbase premium (BTC/ETH), flow_read."""
    now_ms = int(dt.datetime.now(dt.timezone.utc).timestamp() * 1000)
    new_rows: list[dict] = []

    sp = _spot_name()
    if sp:
        try:
            s = _sample(_exchange(sp, "spot"), f"{base}/USDT")
            if s:
                new_rows.append({"market": "spot", "ts": now_ms, "buy": s[0], "sell": s[1]})
        except Exception:
            pass
    try:
        p = _sample(_exchange("bybit", "swap"), f"{base}/USDT:USDT")
        if p:
            new_rows.append({"market": "perp", "ts": now_ms, "buy": p[0], "sell": p[1]})
    except Exception:
        pass

    out = {"spot_state": None, "spot_ratio": None, "perp_state": None, "perp_ratio": None,
           "coinbase_prem_bps": None, "flow_read": "Flow: chưa có data", "spot_cvd_state": None}

    if not new_rows:
        return out

    df = _roll(cache_dir, base, new_rows)
    for mkt in ("spot", "perp"):
        m = df[df["market"] == mkt]
        if len(m):
            st, ratio = _state(float(m["buy"].sum()), float(m["sell"].sum()))
            out[f"{mkt}_state"] = st
            out[f"{mkt}_ratio"] = round(ratio, 2)

    # ── Coinbase premium (BTC/ETH): giá US spot vs tham chiếu (spot đã dò) ──
    if base in ("BTC", "ETH"):
        try:
            cb = _exchange("coinbase", "spot")
            cb.load_markets()
            cb_px = cb.fetch_ticker(f"{base}/USD")["last"]
            ref = _exchange(sp or "bybit", "spot").fetch_ticker(f"{base}/USDT")["last"]
            if cb_px and ref:
                out["coinbase_prem_bps"] = round((cb_px / ref - 1) * 1e4, 1)
        except Exception:
            pass

    # ── Diễn giải spot vs perp ──
    ss, ps = out["spot_state"], out["perp_state"]
    table = {
        ("buying", "buying"): "Cả spot lẫn perp mua — cầu đồng thuận",
        ("buying", "flat"): "Spot mua dẫn — cầu thật (real demand)",
        ("buying", "selling"): "Spot mua nhưng perp bán — phân kỳ",
        ("flat", "buying"): "Perp mua nhưng spot không theo — rally yếu",
        ("selling", "buying"): "Perp đỡ giá, spot xả — thiếu bền",
        ("selling", "selling"): "Cả hai bán — áp lực giảm",
        ("selling", "flat"): "Spot xả dẫn — áp lực bán",
        ("flat", "selling"): "Perp bán dẫn — yếu",
        ("flat", "flat"): "Flow trung tính",
        ("buying", None): "Spot mua", ("selling", None): "Spot bán",
        (None, "buying"): "Perp mua", (None, "selling"): "Perp bán",
    }
    out["flow_read"] = table.get((ss, ps), "Flow trung tính")
    # spot_cvd_state cho Decision/journal: chỉ tính theo SPOT (cầu thật).
    out["spot_cvd_state"] = ss
    return out


if __name__ == "__main__":
    import sys
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    print("spot source:", _spot_name())
    for b in ["BTC", "ETH", "SOL", "HYPE"]:
        f = fetch_flow(b, "./data_cache")
        print(f"{b}: spot={f['spot_state']}({f['spot_ratio']}) perp={f['perp_state']}({f['perp_ratio']}) "
              f"prem={f['coinbase_prem_bps']}bps -> {f['flow_read']}")
