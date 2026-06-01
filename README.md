# Trading Brain → Trader Decision Assistant

> **Trạng thái hiện tại (2026-06):** dự án đã đi qua giai đoạn "edge lab" (tìm chiến
> lược tự động) và **pivot thành một Trader Decision Assistant (HUD)** — web app hỗ
> trợ quyết định swing discretionary + nhật ký tìm edge cá nhân. KHÔNG phải bot.
>
> Tài liệu giải thích đầy đủ cho người đọc/NotebookLM nằm trong `notebooklm/`.

## Sản phẩm chính: web app HUD (`app.py`)

```bash
cd trading-brain
python -m venv .venv
.venv\Scripts\activate                 # Windows PowerShell
pip install -r requirements.txt
uvicorn app:app --reload               # mở http://localhost:8000
```

4 layer:
1. **Context** — trend 4H/1D, funding percentile, RSI, distance EMA, ATR.
2. **Risk Score** — điểm rủi ro vào-long-ngay (0-2 bình thường / 3-5 cẩn thận / 6+ rủi ro cao).
3. **Checklist** — điều kiện thuận lợi cho long, ✓/✗ + tally X/5.
4. **Journal** — ghi lệnh thật + context lúc vào + PnL → sau 200-300 lệnh phân tích edge cá nhân.

Tự kéo data thật mỗi 5 phút. Deploy Railway: xem `DEPLOY.md`.

## Vì sao là HUD chứ không phải bot

Cả giai đoạn nghiên cứu cho thấy **mọi chiến lược cơ học đơn lẻ đều không có edge bền
thắng buy-and-hold**: trend-following (hòa, chủ yếu beta), short/regime (tệ hơn),
phân kỳ 15m (cháy vì phí), funding-squeeze (yếu, không nhất quán). Verdict chi tiết
trong `notebooklm/04-do-dang-tin.md`. → Giá trị thật chuyển sang **hỗ trợ quyết định +
tìm edge cá nhân (journal)**.

## Bản đồ file

**Web app (sản phẩm):**
```
app.py          FastAPI: 4 layer HUD + scheduler refresh 5' + journal SQLite + trang HTML
Procfile        lệnh chạy cho Railway
.python-version pin Python 3.12
DEPLOY.md       hướng dẫn deploy Railway (+ giữ journal bằng Volume)
```

**Dữ liệu:**
```
data.py         CCXT → OHLCV → Parquet cache
data_funding.py CCXT fetch_funding_rate_history → Parquet
indicators.py   EMA / RSI(Wilder) / ATR tự viết
```

**Nghiên cứu (kiểm chứng ý tưởng trước khi tin):**
```
strategy.py     trend+pullback (long/short, núm volume/EMA50/regime)
backtest.py     next-open execution, fixed_r | atr_trailing, trừ fee+slippage+funding
report.py       winrate/expectancy/PF/DD/net vs buy-and-hold
diagnostics.py  PnL theo năm + phân bố R + equity PNG
compare.py      so 4 biến thể strategy
run_funding.py  chiến lược funding-extreme (expanding percentile, funding thật)
study_funding.py signal study: funding cực đoan vs forward return
study_decay.py  tách 2023-24 vs 2025-26, so alpha vs drift
main.py         orchestrate backtest theo config.yaml
config.yaml     mọi tham số & giả định chi phí
```

**Tài liệu:**
```
notebooklm/     5 file md tự-chứa cho NotebookLM (tổng quan, data, hỗ trợ, dùng, độ tin)
KE-HOACH.md     kế hoạch + kết quả nghiên cứu
PRD.md          yêu cầu sản phẩm
ARCHITECTURE.md kiến trúc hệ thống
TASKS.md        checklist + trạng thái
```

## Nguyên tắc xuyên suốt (chống tự lừa)

Next-open execution · không look-ahead · trừ đủ phí · expanding percentile · luôn so
buy-and-hold + tách alpha/drift · walk-forward/per-year để soi decay · không vặn tham
số rồi tin.
