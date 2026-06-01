# PRD — Trader Decision Assistant (Trading Brain)

> Bản cập nhật 2026-06. Sản phẩm đã pivot từ "research lab tìm chiến lược tự động"
> sang "trợ lý quyết định (HUD)". Chi tiết hành trình: `KE-HOACH.md`, `notebooklm/`.

## 1. Vấn đề

Trade swing crypto 1-3 ngày discretionary (trên Hyperliquid) dễ cảm tính, FOMO, và
khó biết bản thân thật sự giỏi ở bối cảnh nào. Cần công cụ: (a) trình bày bối cảnh +
rủi ro một cách trung thực để ra quyết định tốt hơn, (b) ghi nhật ný để khám phá
**edge cá nhân**.

## 2. Người dùng

Một người: chính chủ (dev React/Node/PostgreSQL/Railway, tư duy poker, swing 1-3 ngày,
trade BTC/ETH/SOL/HYPE trên Hyperliquid).

## 3. Mục tiêu sản phẩm

- HUD đọc nhanh mỗi ngày: trend, funding percentile, rủi ro, checklist cho mỗi coin.
- Cảnh báo thời điểm xấu (quá mua, quá căng, đám đông đông) để tránh FOMO.
- Journal: ghi lệnh + context tự động → sau 200-300 lệnh trả lời "tôi thắng/cháy ở
  bối cảnh nào".
- Mở được từ điện thoại (deploy Railway).

## 4. Phạm vi

**Có:**
- Web app (FastAPI) 4 layer: Context, Risk Score, Checklist, Journal.
- Data giá + funding qua CCXT/Binance, tự refresh 5 phút.
- Bộ script nghiên cứu để kiểm chứng tín hiệu mới trước khi đưa vào HUD.

**KHÔNG (non-goals):**
- KHÔNG auto-trade / tự vào lệnh. Người bấm lệnh.
- KHÔNG bịa "xác suất thắng %".
- KHÔNG hứa thắng buy-and-hold (đã chứng minh là rất khó với tín hiệu công khai).
- KHÔNG đưa tín hiệu chưa kiểm chứng (trừ phí, chống nhìn trước) vào dùng.

## 5. Tiêu chí thành công

| Mức | Tiêu chí |
|---|---|
| Đạt (đã xong) | HUD chạy, hiển thị bối cảnh + risk + checklist trung thực; journal ghi/đóng/thống kê được; deploy được Railway |
| Hữu ích | Sau vài tháng dùng, journal đủ lệnh để lộ edge cá nhân (bối cảnh thắng/cháy) |
| Lý tưởng | Người dùng cải thiện kỷ luật & winrate nhờ tránh các bối cảnh xấu journal chỉ ra |

## 6. Ràng buộc / sự thật nền

- Tín hiệu thị trường công khai (EMA/RSI/funding) edge yếu → HUD chỉ là *bối cảnh*,
  không phải lệnh. Xem `notebooklm/04-do-dang-tin.md`.
- Funding lấy được lịch sử dài + free; OI/liquidation phải trả phí hoặc tự thu thập.
- Journal dùng SQLite; trên Railway cần Volume + `DB_PATH` để bền qua redeploy.

## 7. Trạng thái

Đã build & test xong web app 4 layer (`app.py`). Chưa deploy (chủ tự deploy Railway).
Bước tiếp khả dĩ: thêm HYPE/Hyperliquid, đổi SQLite→Postgres, thêm OI/liquidation khi có.
