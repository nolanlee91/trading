# ARCHITECTURE — Trader Decision Assistant

> Bản cập nhật 2026-06. Gồm 2 phần: (A) web app HUD đang chạy, (B) bộ nghiên cứu
> dùng để kiểm chứng tín hiệu trước khi đưa vào HUD.

## A. Web app HUD (sản phẩm)

```
                 CCXT ──► Binance (OHLCV 4H/1D + funding)
                   │
                   ▼
        data.py / data_funding.py ──► Parquet cache
                   │
                   ▼
        app.analyze_coin()  ── indicators.py (EMA/RSI/ATR)
                   │   (tính: trend, funding pctl, risk score, checklist, flags)
                   ▼
        SNAPSHOT (in-memory)  ◄── APScheduler refresh mỗi 5 phút
                   │
        ┌──────────┴───────────┐
        ▼                      ▼
   GET /api/dashboard     GET / (trang HTML mobile)
        │                      │
        ▼                      ▼
   Journal API           Người dùng đọc + ghi lệnh
   (SQLite: trades)
```

### Thành phần `app.py`
| Phần | Vai trò |
|---|---|
| `analyze_coin()` | Tính 4 layer cho 1 coin (Context/Risk/Checklist + flags) |
| `refresh()` + APScheduler | Kéo data thật mỗi 5 phút → cập nhật SNAPSHOT |
| `/api/dashboard` | Trả JSON snapshot |
| `/api/journal/*` | open / close / list / stats — nhật ký SQLite |
| `/` | Trang HTML+JS (mobile, tự refresh 5') |
| `init_db()` + SQLite | Bảng `trades`: context lúc vào + PnL khi đóng |

### Quyết định kỹ thuật (web)
| Quyết định | Lý do |
|---|---|
| 1 service Python (FastAPI serve cả API lẫn HTML) | 1 deploy, gọn, không cần build React riêng |
| Scheduler trong process | Tự refresh, không cần cron ngoài |
| SQLite cho journal | Không thêm dependency; Railway giữ bền bằng Volume + `DB_PATH` |
| Funding percentile theo cửa sổ 1 năm | Phản ánh regime hiện tại |
| LOOKBACK 450 ngày | Đủ EMA200 trên 1D, nạp nhanh |

## B. Bộ nghiên cứu (kiểm chứng tín hiệu)

```
config.yaml ─► data.py/data_funding.py ─► Parquet
                       │
            ┌──────────┼───────────────┐
            ▼          ▼                ▼
       strategy.py  divergence.py   (funding signal)
            │          │                │
            ▼          ▼                ▼
                   backtest.py / run_funding.py
            (next-open, trừ fee+slippage+funding, fixed_r|trailing)
                       │
            ┌──────────┼───────────────┐
            ▼          ▼                ▼
       report.py  diagnostics.py   study_decay.py
       (metrics)  (PnL năm, R, PNG) (alpha vs drift, decay)
```

### Trách nhiệm module
| Module | Làm | KHÔNG làm |
|---|---|---|
| `data.py`/`data_funding.py` | tải + cache dữ liệu sạch | không biết strategy |
| `indicators.py` | EMA/RSI/ATR | không quyết định |
| `strategy.py`/`divergence.py` | sinh tín hiệu trên nến đã đóng | không khớp lệnh |
| `backtest.py`/`run_funding.py` | mô phỏng khớp lệnh + chi phí | không tải data |
| `report.py`/`diagnostics.py`/`study_decay.py` | đo & trình bày | không sửa kết quả |

### Nguyên tắc chống nhìn trước (xuyên suốt)
Next-open execution · merge_asof backward khi ghép khung · expanding percentile cho
funding · chỉ dùng dữ liệu quá khứ tại mỗi thời điểm.

## C. Hướng mở rộng đã thiết kế sẵn
- Thêm coin/sàn: thêm vào `PAIRS` trong `app.py` (HYPE cần verify CCXT Hyperliquid).
- Journal bền hơn: đổi SQLite → PostgreSQL (Railway) khi cần lịch sử lớn / nhiều thiết bị.
- Tín hiệu mới: kiểm chứng bằng bộ nghiên cứu (B) trước, đạt mới thêm vào `analyze_coin`.
- OI/liquidation: cần nguồn trả phí hoặc tự thu thập forward.

## D. Stack
Python 3.12 · FastAPI · uvicorn · APScheduler · CCXT · pandas · pyarrow · PyYAML ·
SQLite (stdlib) · matplotlib (chỉ cho diagnostics).
