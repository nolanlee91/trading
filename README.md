# Trading Brain → Trader Decision Assistant

> **Trạng thái (2026-07):** đã pivot từ "edge lab" thành **Trader Decision Assistant
> (HUD)** và **deploy online** (Railway + PostgreSQL), dùng chung mọi thiết bị. KHÔNG
> phải bot. Nâng từ 4 layer → **7 layer + Decision State** (SMC/derivatives/flow/
> liquidity). Tài liệu giải thích cho người đọc/NotebookLM: `notebooklm/ver2/`.

## Sản phẩm: web app HUD (`app.py`)

```bash
cd trading-brain
python -m venv .venv && .venv\Scripts\activate
pip install -r requirements.txt
uvicorn app:app --reload          # http://localhost:8000
```
Online: deploy Railway (xem `DEPLOY.md`) → mở URL trên điện thoại/laptop.

### 7 layer + Decision State (chi tiết: `HUONG-DAN-SU-DUNG.md`)
1. **Trend / Context** — trend 4H/1D (EMA 20/50/200), funding percentile, RSI, distance EMA (ATR), ATR%, bias, risk score (0-9), checklist 5 điều kiện.
2. **Structure / Location** (`levels.py`) — support/resistance + supply/demand: gom mức từ swing/volume-spike/30D/prev day-week high-low → zone có strength (X/5) + price location.
3. **Market Structure / SMC** (`structure.py`) — swing 4H/1D, BOS/CHOCH, range, EQH/EQL, FVG/IFVG, premium/discount, invalidation, nearest liquidity.
4. **Derivatives** (`data_oi.py`) — Price × OI × Funding: new longs / short covering / new shorts / long closing.
5. **Spot / Perp Flow** (`data_flow.py`) — taker buy/sell (CVD proxy) spot vs perp + Coinbase premium. *Bản xấp xỉ.*
6. **Liquidity Map** (`liquidity.py`) — resting liquidity gần nhất + liquidation cluster (leverage tiers) + magnet bias. *Bản xấp xỉ.*
7. **Journal** — ghi lệnh + **11 field bối cảnh** (structure, location, oi/funding/flow state, liquidity, btc_regime, entry_type) + PnL → tìm edge cá nhân. PostgreSQL/SQLite.

**Decision State** (`decision.py`) — Layer tổng hợp: hợp nhất 6 layer thành 1 kết luận
`SHORT/LONG SETUP — Anticipation/Confirmation` + checklist 7 điều kiện (≥5/7 = setup đẹp)
+ reasons + invalidation. Gate bằng "giá phải ở zone"; phân biệt "2 chiều xung đột".

### Tính năng khác
- **Bias** theo trend 4H: bullish→long, bearish→short, mixed→đứng ngoài.
- **Tự dò sàn** Hyperliquid→Bybit→Binance→OKX (sàn user trade thật; tránh 451 Binance). OI/flow lấy riêng từ Bybit (Hyperliquid không có OI history).
- **Trợ lý Gemini**: hỏi-đáp bám dữ liệu thật, thấy đủ 7 layer (cần `GEMINI_API_KEY`).
- Tự refresh data mỗi 5 phút; giao diện tối ưu mobile.

## Vì sao là HUD chứ không phải bot
Nghiên cứu cho thấy **mọi chiến lược cơ học đơn lẻ đều không thắng buy-and-hold**:
trend-following (hòa, beta), short/regime (tệ hơn), phân kỳ 15m (cháy vì phí),
funding-squeeze (yếu). Verdict chi tiết: `notebooklm/ver2/04-do-dang-tin.md`. → Giá
trị thật chuyển sang hỗ trợ quyết định + journal tìm edge cá nhân.

## Bản đồ file

**Web app:**
```
app.py          FastAPI: 7 layer HUD + Decision State + refresh 5' + journal (Postgres/SQLite)
                + ghi tay + entry_type + trợ lý Gemini + trang HTML mobile + tự dò sàn
index.html      Giao diện multi-screen (Market/Journal/Snapshots/Assistant), mobile-first
Procfile · .python-version · DEPLOY.md   (deploy Railway + Postgres + biến môi trường)
```
**Dữ liệu:** `data.py` (OHLCV) · `data_funding.py` (funding) · `data_oi.py` (open interest, Bybit) ·
`data_flow.py` (taker buy/sell, CVD proxy) · `indicators.py` (EMA/RSI/ATR).
**Phân tích HUD:** `levels.py` (S/R) · `structure.py` (SMC) · `liquidity.py` (liquidation map) ·
`decision.py` (Decision State tổng hợp). Mỗi module chạy độc lập được (`python <module>.py`).
**Nghiên cứu:** `strategy.py` `backtest.py` `report.py` `diagnostics.py` `compare.py`
`divergence.py` `run_funding.py` `study_funding.py` `study_decay.py` `main.py` `config.yaml`.
**Tài liệu:** `notebooklm/ver2/` (nạp NotebookLM) · `KE-HOACH.md` `PRD.md` `ARCHITECTURE.md` `TASKS.md`.

## Nguyên tắc xuyên suốt
Next-open execution · không look-ahead · trừ đủ phí · expanding percentile · so
buy-and-hold + tách alpha/drift · walk-forward/per-year soi decay · không vặn tham số rồi tin.
