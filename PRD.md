# PRD — Trader Decision Assistant (Trading Brain)

> Cập nhật 2026-06. Sản phẩm = trợ lý quyết định (HUD), đã deploy online. Hành trình:
> `KE-HOACH.md`; giải thích chi tiết: `notebooklm/ver2/`.

## 1. Vấn đề
Trade swing crypto 1-3 ngày discretionary (Hyperliquid) dễ cảm tính, FOMO, khó biết
bản thân giỏi ở bối cảnh nào. Cần công cụ: (a) trình bày bối cảnh + rủi ro trung thực
để ra quyết định tốt hơn, (b) nhật ký khám phá **edge cá nhân**.

## 2. Người dùng
Một người: chính chủ (dev React/Node/PostgreSQL/Railway, tư duy poker, swing 1-3 ngày,
trade BTC/ETH/SOL/HYPE trên Hyperliquid).

## 3. Mục tiêu sản phẩm
- HUD đọc nhanh mỗi ngày: **bias, risk vào lệnh, checklist, funding, RSI, trend** mỗi coin.
- Cảnh báo thời điểm xấu (quá mua/bán, quá căng, đám đông đông) để tránh FOMO.
- Journal: ghi lệnh + context → sau 200-300 lệnh trả lời "tôi thắng/cháy ở bối cảnh nào".
- **Online, dùng chung mọi thiết bị** (1 URL, 1 PostgreSQL).
- Trợ lý hỏi-đáp (Gemini) giải thích bối cảnh.

## 4. Phạm vi
**Có:** web app FastAPI 4 layer (bias-aware); data giá+funding qua CCXT (tự dò sàn);
journal PostgreSQL (+ghi tay); chat Gemini; bộ script nghiên cứu để kiểm chứng tín hiệu mới.

**KHÔNG (non-goals):** không auto-trade; không bịa "xác suất thắng %"; không hứa thắng
buy-and-hold (đã chứng minh rất khó); không đưa tín hiệu chưa kiểm chứng vào dùng.

## 5. Tiêu chí thành công
| Mức | Tiêu chí |
|---|---|
| Đạt (xong) | HUD online chạy; bias/risk/checklist trung thực; journal Postgres ghi/đóng/ghi-tay/thống kê; mở mọi thiết bị |
| Hữu ích | Sau vài tháng, journal đủ lệnh để lộ edge cá nhân |
| Lý tưởng | Cải thiện kỷ luật & winrate nhờ tránh bối cảnh xấu journal chỉ ra |

## 6. Ràng buộc / sự thật nền
- Tín hiệu công khai (EMA/RSI/funding) edge yếu → HUD là *bối cảnh*, không phải lệnh.
- Funding lấy được lịch sử dài + free; OI/liquidation phải trả phí hoặc tự thu thập.
- Binance hay bị chặn 451 → app tự dò Bybit/Binance/OKX.

## 7. Trạng thái
**Đã deploy online (Railway + PostgreSQL).** 4 layer bias-aware, Gemini chat, ghi tay,
mobile — đều hoạt động. Bước tiếp: xem `TASKS.md` (HYPE/Hyperliquid, OI/liquidation, ...).
