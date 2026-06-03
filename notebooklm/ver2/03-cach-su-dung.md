# Cách sử dụng hệ thống (ver2)

## A. Mở app online
Mở URL công khai (Railway) trên điện thoại/laptop bất kỳ. Lần đầu hiện "đang tải..."
~30-60s rồi hiện 3 card BTC/ETH/SOL. Cùng một URL → mọi thiết bị dùng chung 1 database.

## B. Đọc dashboard mỗi ngày
Mỗi card hiển thị (ý nghĩa chi tiết xem `02-chi-so-va-y-nghia.md`):
- **Bias** (LONG / SHORT / ĐỨNG NGOÀI) theo trend 4H.
- **Risk vào lệnh** (badge: Bình thường / Cẩn thận / Rủi ro cao).
- Trend 4H/1D, funding percentile, RSI, khoảng cách EMA, ATR, return 7 ngày.
- **Checklist** 5 điều kiện theo bias (✓/✗, "X/5 thuận lợi").

Cách đọc thực dụng:
- Bias SHORT + checklist cao + Risk thấp → bối cảnh thuận để bán theo trend (tự quyết).
- Risk "Rủi ro cao" → tránh hoặc giảm cỡ.
- ĐỨNG NGOÀI → trend chưa rõ, kiên nhẫn thường tốt hơn.

## C. Journal (quan trọng nhất — lưu trên PostgreSQL, dùng chung mọi thiết bị)

**Ghi lệnh khi đang vào (chuẩn nhất):**
1. Chọn coin, long/short, gõ lý do → bấm "＋ Ghi lệnh".
2. Hệ thống tự chụp trend/funding/RSI/EMA **tại đúng thời điểm vào**.

**Đóng lệnh:** bấm "Đóng" ở lệnh đó → nhập giá thoát → tự tính PnL%.

**Ghi lệnh đã đóng / quá khứ (nhập tay):** form "Ghi lệnh đã đóng" — nhập coin, side,
giá vào, giá ra → lưu thẳng vào database. Dùng cho lệnh ngoài app hoặc lệnh cũ.

**Xem edge cá nhân:** phần thống kê tự tổng hợp tỉ lệ thắng & PnL trung bình theo nhóm
funding / trend / RSI. Cần đủ lệnh mới tin (app cảnh báo "<30 lệnh, chưa đủ tin").

Kỷ luật: ghi MỌI lệnh, kể cả lệnh xấu/FOMO — chính lệnh thua mới lộ bối cảnh nên tránh.

## D. Trợ lý hỏi-đáp (Gemini)
Ô "Hỏi trợ lý": gõ câu hỏi (vd "ETH thế nào? tôi đang short từ 2080") → Gemini trả lời
dựa trên dữ liệu thật của HUD. Cần cấu hình `GEMINI_API_KEY`. Lưu ý: Gemini chỉ *giải
thích bối cảnh*, không làm tín hiệu chính xác hơn (edge vẫn yếu).

## E. Tự làm mới
Tự kéo dữ liệu mỗi 5 phút; nút "⟳ Refresh data" để kéo ngay.

## F. Công cụ nghiên cứu (nâng cao, chạy local)
Bộ script kiểm chứng ý tưởng mới trước khi đưa vào HUD: `compare.py`, `run_funding.py`,
`study_funding.py`, `study_decay.py` (tách kỳ kiểm tra edge còn sống/đã suy thoái).
Luôn kiểm chứng (trừ phí, chống nhìn trước) trước khi thêm tín hiệu mới.
