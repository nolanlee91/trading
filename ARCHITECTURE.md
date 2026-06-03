# ARCHITECTURE — Trader Decision Assistant

> Cập nhật 2026-06. (A) web app HUD đang chạy online; (B) bộ nghiên cứu kiểm chứng tín hiệu.

## A. Web app HUD (`app.py`, deploy Railway)

```
          CCXT ──► tự dò sàn: Bybit → Binance → OKX  (tránh 451)
            │        (OHLCV 4H/1D + funding)
            ▼
   data.py / data_funding.py ──► Parquet cache
            │
            ▼
   analyze_coin()  ── indicators.py (EMA/RSI/ATR)
            │   tính: trend 4H/1D, funding pctl, BIAS, risk score, checklist, flags
            ▼
   SNAPSHOT (in-memory) ◄── APScheduler refresh mỗi 5 phút
            │
   ┌────────┼─────────────┬───────────────┐
   ▼        ▼             ▼               ▼
 /api/    /api/ask     /api/journal/*   / (trang HTML mobile)
 dashboard (Gemini)    (open/close/      người dùng đọc + ghi lệnh
                        manual/list/stats)
                            │
                            ▼
                 Journal: PostgreSQL (nếu có DATABASE_URL)
                          hoặc SQLite (local)
```

### Thành phần `app.py`
| Phần | Vai trò |
|---|---|
| `data_exchange()` | Dò 1 lần sàn vào được, cache (chống 451 Binance) |
| `analyze_coin()` | Tính 4 layer cho 1 coin, có **BIAS** theo trend 4H |
| `refresh()` + APScheduler | Kéo data thật mỗi 5 phút → cập nhật SNAPSHOT |
| `/api/dashboard` | Trả JSON snapshot |
| `ask_gemini()` + `/api/ask` | Trợ lý hỏi-đáp, prompt ràng buộc trung thực |
| `_conn/run_query/run_write` | Tầng DB trừu tượng: PostgreSQL hoặc SQLite |
| `/api/journal/*` | open / close / **manual** (ghi tay) / list / stats |
| `/` | Trang HTML+JS mobile (bias chip, checklist, journal, chat) |

### Quyết định kỹ thuật (web)
| Quyết định | Lý do |
|---|---|
| 1 service Python (FastAPI serve cả API lẫn HTML) | 1 deploy, không cần build React riêng |
| Scheduler trong process | Tự refresh, không cần cron ngoài |
| Tự dò sàn | Binance hay bị 451 ở mạng công ty/cloud |
| Journal Postgres-hoặc-SQLite | Online dùng chung nhiều thiết bị (Postgres); local đơn giản (SQLite) |
| BIAS theo trend 4H | "Đừng đánh ngược trend lớn"; checklist & risk xoay theo bias |
| Funding percentile cửa sổ 1 năm | Phản ánh regime hiện tại |

## B. Bộ nghiên cứu (kiểm chứng tín hiệu)
```
config.yaml ─► data/data_funding ─► Parquet
        ├─ strategy.py / divergence.py  → tín hiệu (nến đã đóng)
        ├─ backtest.py / run_funding.py → next-open, trừ fee+slippage+funding
        └─ report / diagnostics / study_decay → metrics, alpha vs drift, decay
```
Nguyên tắc: next-open execution · merge_asof backward khi ghép khung · expanding
percentile · chỉ dùng dữ liệu quá khứ tại mỗi thời điểm.

## C. Triển khai
- GitHub → Railway (auto-deploy). PostgreSQL = service riêng; app nhận qua
  `DATABASE_URL=${{Postgres.DATABASE_URL}}`.
- Biến môi trường: `DATABASE_URL` (journal), `GEMINI_API_KEY` (chat), `DATA_EXCHANGE`
  (ép sàn, tùy chọn). Chi tiết: `DEPLOY.md`.

## D. Hướng mở rộng
- Thêm coin/sàn: thêm `PAIRS` (HYPE cần verify CCXT Hyperliquid).
- OI/liquidation: cần nguồn trả phí hoặc tự thu thập forward.
- Tín hiệu mới: kiểm chứng bằng bộ nghiên cứu (B) trước khi thêm vào `analyze_coin`.

## E. Stack
Python 3.12 · FastAPI · uvicorn · APScheduler · CCXT · pandas · pyarrow · PyYAML ·
psycopg2 (Postgres) / sqlite3 (local) · matplotlib (diagnostics).
