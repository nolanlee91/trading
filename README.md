# Trading Brain → Trader Decision Assistant

> **Trạng thái (2026-06):** đã pivot từ "edge lab" thành **Trader Decision Assistant
> (HUD)** và **deploy online** (Railway + PostgreSQL), dùng chung mọi thiết bị. KHÔNG
> phải bot. Tài liệu giải thích cho người đọc/NotebookLM: `notebooklm/ver2/`.

## Sản phẩm: web app HUD (`app.py`)

```bash
cd trading-brain
python -m venv .venv && .venv\Scripts\activate
pip install -r requirements.txt
uvicorn app:app --reload          # http://localhost:8000
```
Online: deploy Railway (xem `DEPLOY.md`) → mở URL trên điện thoại/laptop.

### 4 layer (chi tiết: `notebooklm/ver2/02-chi-so-va-y-nghia.md`)
1. **Context** — trend 4H/1D, funding percentile, RSI, distance EMA (ATR), ATR%.
2. **Risk Score** — điểm rủi ro vào lệnh THEO BIAS (0-9): 0-2 bình thường, 3-5 cẩn thận, 6+ rủi ro cao.
3. **Checklist** — 5 điều kiện thuận lợi theo bias (long/short), ✓/✗ + tally X/5.
4. **Journal** — ghi lệnh + context + PnL → tìm edge cá nhân. Lưu PostgreSQL (dùng chung thiết bị); có cả "ghi lệnh đã đóng" nhập tay.

### Tính năng khác
- **Bias** theo trend 4H: bullish→long, bearish→short, mixed→đứng ngoài.
- **Tự dò sàn** Bybit→Binance→OKX (tránh 451 Binance ở mạng công ty/cloud).
- **Trợ lý Gemini**: hỏi-đáp bám dữ liệu thật (cần `GEMINI_API_KEY`).
- Tự refresh data mỗi 5 phút; giao diện tối ưu mobile.

## Vì sao là HUD chứ không phải bot
Nghiên cứu cho thấy **mọi chiến lược cơ học đơn lẻ đều không thắng buy-and-hold**:
trend-following (hòa, beta), short/regime (tệ hơn), phân kỳ 15m (cháy vì phí),
funding-squeeze (yếu). Verdict chi tiết: `notebooklm/ver2/04-do-dang-tin.md`. → Giá
trị thật chuyển sang hỗ trợ quyết định + journal tìm edge cá nhân.

## Bản đồ file

**Web app:**
```
app.py          FastAPI: 4 layer HUD (bias-aware) + refresh 5' + journal (Postgres/SQLite)
                + ghi tay + trợ lý Gemini + trang HTML mobile + tự dò sàn
Procfile · .python-version · DEPLOY.md   (deploy Railway + Postgres + biến môi trường)
```
**Dữ liệu:** `data.py` (OHLCV) · `data_funding.py` (funding) · `indicators.py` (EMA/RSI/ATR).
**Nghiên cứu:** `strategy.py` `backtest.py` `report.py` `diagnostics.py` `compare.py`
`divergence.py` `run_funding.py` `study_funding.py` `study_decay.py` `main.py` `config.yaml`.
**Tài liệu:** `notebooklm/ver2/` (nạp NotebookLM) · `KE-HOACH.md` `PRD.md` `ARCHITECTURE.md` `TASKS.md`.

## Nguyên tắc xuyên suốt
Next-open execution · không look-ahead · trừ đủ phí · expanding percentile · so
buy-and-hold + tách alpha/drift · walk-forward/per-year soi decay · không vặn tham số rồi tin.
