# ARCHITECTURE — Trader Decision Assistant

> Cập nhật 2026-07. (A) web app HUD **7 layer + Decision State** đang chạy online; (B) bộ nghiên cứu kiểm chứng tín hiệu.

## A. Web app HUD (`app.py`, deploy Railway)

```
   CCXT ─► giá/funding: Hyperliquid → Bybit → Binance → OKX (sàn user; tránh 451)
        ├► OI history:  Bybit → Binance → OKX   (Hyperliquid KHÔNG có OI history)
        └► taker flow:  fetch_trades spot Bybit→OKX, perp Bybit + Coinbase premium
            │
            ▼
   data.py / data_funding.py / data_oi.py / data_flow.py ──► Parquet cache
            │
            ▼
   analyze_coin()  ── indicators.py (EMA/RSI/ATR) + các module phân tích:
            │   L1 Trend/risk/checklist  ·  L2 levels.py (S/R)  ·  L3 structure.py (SMC)
            │   L4 derivatives (OI×funding×price)  ·  L5 data_flow (CVD proxy)
            │   L6 liquidity.py (liquidation map)
            ▼
   refresh(): analyze 4 coin → btc_regime → decision.py (Layer 7 tổng hợp mỗi coin)
            ▼
   SNAPSHOT (in-memory) ◄── APScheduler refresh mỗi 5 phút
            │
   ┌────────┼─────────────┬───────────────┐
   ▼        ▼             ▼               ▼
 /api/    /api/ask     /api/journal/*   / (index.html mobile)
 dashboard (Gemini)    (open/close/      Decision banner + 6 block/coin
 (7 layer) thấy 7 layer  manual/list/stats) + ghi lệnh (entry_type)
                            │
                            ▼
                 Journal: PostgreSQL (nếu có DATABASE_URL) hoặc SQLite (local)
                 — lưu 11 field bối cảnh + entry_type mỗi lệnh
```

### Thành phần `app.py`
| Phần | Vai trò |
|---|---|
| `data_exchange()` / `deriv_exchange()` / `_spot_name()` | Dò sàn cho giá / OI / taker-flow (mỗi loại nguồn riêng) |
| `analyze_coin()` | Tính **6 layer** cho 1 coin (trend/risk + levels + structure + derivatives + flow + liquidity) |
| `_derivatives_read()` | L4: diễn giải Price × OI × Funding |
| `_btc_regime()` + `decision_state()` | L7: btc_regime dùng chung → Decision State mỗi coin |
| `refresh()` + APScheduler | Kéo data mỗi 5 phút → analyze → decision → SNAPSHOT |
| `/api/dashboard` | Trả JSON snapshot (đủ 7 layer + decision) |
| `ask_gemini()` + `/api/ask` | Trợ lý hỏi-đáp, context gồm cả 7 layer, prompt ràng buộc trung thực |
| `_conn/run_query/run_write` + `init_db()` | Tầng DB trừu tượng; auto-ALTER thêm cột bối cảnh mới |
| `/api/journal/*` | open / close / **manual** / list / stats (lưu 11 field ctx + entry_type) |
| `/` | `index.html`: Decision banner + 6 block chi tiết/coin, mobile |

### Quyết định kỹ thuật (web)
| Quyết định | Lý do |
|---|---|
| 1 service Python (FastAPI serve cả API lẫn HTML) | 1 deploy, không cần build React riêng |
| Scheduler trong process | Tự refresh, không cần cron ngoài |
| Tự dò sàn | Binance hay bị 451 ở mạng công ty/cloud |
| Journal Postgres-hoặc-SQLite | Online dùng chung nhiều thiết bị (Postgres); local đơn giản (SQLite) |
| BIAS theo trend 4H | "Đừng đánh ngược trend lớn"; checklist & risk xoay theo bias |
| Funding percentile cửa sổ 1 năm | Phản ánh regime hiện tại |
| OI/flow lấy nguồn RIÊNG (Bybit), không theo sàn giá | Hyperliquid không có OI history; taker-flow cần fetch_trades có `side` |
| Module hoá (levels/structure/liquidity/decision.py) | Mỗi layer test độc lập được (`python <module>.py`); `analyze_coin` chỉ ghép |
| Decision State gate bằng "giá ở zone" + margin | Nhiều điều kiện dùng chung 2 chiều → chỉ điểm cao chưa đủ; phải đang ở vùng vào lệnh |
| CVD/liquidation = bản XẤP XỈ, gắn nhãn rõ | Không có heatmap/CVD chuẩn free; trung thực hơn là giả chính xác |

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
- Thêm coin: sửa `COINS`/`DISPLAY` (HYPE chỉ trên Hyperliquid; OI/flow lấy Bybit).
- **CVD/liquidation chuẩn** (nâng M5/M6 từ xấp xỉ): cần nguồn trả phí (heatmap) hoặc
  tự thu thập per-trade forward (accumulate CVD liên tục thay vì lấy mẫu 5').
- Tín hiệu mới: kiểm chứng bằng bộ nghiên cứu (B) trước khi thêm vào `analyze_coin`.
- Journal stats: bổ sung bucket theo field mới (structure/entry_type/magnet/flow) để
  soi edge cá nhân (vd "short anticipation at supply + funding+ + OI falling").

## E. Stack
Python 3.12 · FastAPI · uvicorn · APScheduler · CCXT · pandas · pyarrow · PyYAML ·
psycopg2 (Postgres) / sqlite3 (local) · matplotlib (diagnostics).
