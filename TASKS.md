# TASKS — Trading Brain → Trader Decision Assistant

> Cập nhật 2026-06. Quy ước: `[ ]` chưa làm · `[~]` đang làm · `[x]` xong · `[killed]` đã thử & loại.
> Giai đoạn nghiên cứu (Phase 1-D) đã xong; sản phẩm pivot sang HUD (Phase HUD).

---

## Phase 1 — Edge Lab  ✅ xong
- [x] data.py / indicators.py / strategy.py / backtest.py / report.py / main.py / config.yaml
- [x] Chạy thật BTC/ETH/SOL; fix UTF-8 console
- **Verdict:** baseline trend+pullback âm kỳ vọng.

## Phase A — Chẩn đoán  ✅ xong
- [x] PnL theo năm, phân bố R, equity PNG, PnL theo độ dài giữ lệnh, re-confirm no look-ahead (`diagnostics.py`)
- **Verdict:** thua vì SL quá chặt (1.5 ATR) → lệnh 1-4h chảy máu; lợi nhuận dồn ở lệnh giữ 25h+.

## Phase B — Cải thiện  ✅ xong (qua `compare.py`)
- [x] Nới SL 1.5→2.5 ATR (giúp nhiều nhất; BTC +5%)
- [killed] Short — tệ hơn (bơi ngược bull + squeeze)
- [killed] Lọc regime EMA-spread — không hiệu quả (lọc nhầm lệnh cuối sóng)
- [killed] Volume filter / EMA50 pullback / ATR trailing — wash, coin-dependent
- [killed] Phân kỳ RSI 15m (`divergence.py`) — **cháy −100% vì phí**
- **Verdict:** không biến thể nào thắng buy-and-hold; lợi nhuận chủ yếu là beta.

## Phase C/D — Walk-forward & quyết định  ✅ xong
- [x] Tách 2023-24 vs 2025-26, so alpha vs drift (`study_decay.py`)
- [x] Nghiên cứu funding (`study_funding.py`, `run_funding.py`): edge yếu, không nhất quán
- **Verdict (cổng quyết định):** tín hiệu cơ học đơn lẻ không có alpha bền → pivot sang HUD.

## Phase HUD — Trader Decision Assistant  ✅ xong
- [x] **H-1** `app.py` FastAPI: L1 Context (trend/funding pctl/RSI/distEMA/ATR)
- [x] **H-2** L2 Risk Score (0-9) + lý do
- [x] **H-3** L3 Checklist long (✓/✗, tally X/5)
- [x] **H-4** L4 Journal SQLite: open/close/list/stats + edge cá nhân theo funding/trend/RSI
- [x] **H-5** Scheduler refresh data thật mỗi 5 phút
- [x] **H-6** Trang HTML mobile + test end-to-end
- [x] **H-7** Deploy-ready: Procfile, .python-version, .gitignore, DEPLOY.md
- [x] **H-8** Tài liệu NotebookLM (`notebooklm/`)

---

## Tiếp theo (chưa làm)
- [ ] **N-1** Chủ deploy lên Railway (cần tài khoản chủ) + gắn Volume giữ journal.
- [ ] **N-2** Thêm HYPE/Hyperliquid: verify CCXT lấy OHLCV + funding hourly.
- [ ] **N-3** Đổi journal SQLite → PostgreSQL (Railway) nếu cần đa thiết bị / lịch sử lớn.
- [ ] **N-4** Lưu snapshot context hằng ngày để đối chiếu về sau.
- [ ] **N-5** Thêm ngữ cảnh: volume bất thường, khoảng cách đỉnh/đáy gần nhất, tương quan BTC.
- [ ] **N-6** Khi có nguồn: OI / liquidation (trả phí hoặc tự thu thập forward).

## Nợ kỹ thuật
- [ ] Chưa có test tự động cho từng module.
- [ ] `app.py` dùng `@app.on_event` (deprecated ở FastAPI mới) — chuyển sang lifespan khi rảnh.
- [ ] Funding trong backtest nghiên cứu vẫn có nhánh hằng số (run_funding dùng funding thật).
