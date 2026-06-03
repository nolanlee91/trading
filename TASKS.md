# TASKS — Trader Decision Assistant

> Cập nhật 2026-06. `[x]` xong · `[ ]` chưa · `[killed]` đã thử & loại.

## Nghiên cứu (Phase 1-D) ✅ xong
- [x] Edge lab: data/indicators/strategy/backtest/report; chạy BTC/ETH/SOL.
- [x] Chẩn đoán (diagnostics): PnL theo năm, phân bố R, equity PNG.
- [x] Cải thiện (compare): nới SL 1.5→2.5 giúp nhiều nhất.
- [killed] Short · lọc regime · volume · EMA50 · ATR-trailing — wash/tệ hơn.
- [killed] Phân kỳ RSI 15m — cháy −100% vì phí.
- [x] Funding study + decay (study_funding/study_decay): edge yếu, không nhất quán.
- **Verdict:** tín hiệu cơ học đơn lẻ không thắng buy-and-hold → pivot sang HUD.

## Sản phẩm HUD ✅ xong
- [x] `app.py` FastAPI 4 layer: Context / Risk / Checklist / Journal.
- [x] **Bias theo trend 4H** (bullish→long, bearish→short, mixed→đứng ngoài); checklist
  & risk score xoay theo bias.
- [x] Scheduler refresh data thật mỗi 5 phút + nút Refresh có feedback.
- [x] **Tự dò sàn** Bybit→Binance→OKX (chống 451 Binance).
- [x] Sửa bug phân trang (Bybit/OKX trả giá cũ) + bug nút ghi lệnh.
- [x] **Trợ lý Gemini** (`/api/ask`) bám dữ liệu thật, ràng buộc trung thực.
- [x] Giao diện tối ưu **mobile**.
- [x] Tài liệu NotebookLM (`notebooklm/ver1` archive, `ver2` hiện hành).

## Triển khai online ✅ xong
- [x] Deploy Railway (GitHub auto-deploy); tạo domain công khai.
- [x] **Journal PostgreSQL** (dùng chung mọi thiết bị) — tầng DB Postgres-hoặc-SQLite.
- [x] **Ghi lệnh đã đóng nhập tay** (entry/exit thật) cho lệnh quá khứ.

## Tiếp theo (chưa làm)
- [ ] **N-1** Migrate lệnh quá khứ từ SQLite local → Postgres online (hoặc ghi tay trên app).
- [x] **N-2/N-3** Hyperliquid là nguồn chính (OHLCV+funding hourly thật) + thêm HYPE.
  EXCHANGE_PROFILES (chu kỳ funding theo sàn); fix annualize ×(24/h)×365; fallback
  proxy nếu HL không vào. Verify 4 coin OK (BTC 5%/yr, ETH/HYPE 11%, SOL −21%).
- [ ] **N-4** Lưu snapshot context hằng ngày để đối chiếu về sau.
- [ ] **N-5** Thêm ngữ cảnh: volume bất thường, khoảng cách đỉnh/đáy gần nhất, tương quan BTC.
- [ ] **N-6** Khi có nguồn: OI / liquidation (trả phí hoặc tự thu thập forward).

## Nợ kỹ thuật
- [ ] Chưa có test tự động cho từng module.
- [ ] `app.py` dùng `@app.on_event` (deprecated FastAPI mới) → chuyển sang lifespan.
- [ ] PnL journal dùng (entry/exit-1); cân nhắc chuẩn hóa quy ước % cho short.
