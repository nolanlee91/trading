# Cách sử dụng hệ thống (ver3)

## A. Mở app online
Mở URL công khai (Railway) trên điện thoại/laptop bất kỳ. Lần đầu hiện "đang tải..."
~30-60s rồi hiện **4 card BTC/ETH/SOL/HYPE**. Cùng một URL → mọi thiết bị dùng chung 1
database. Dòng trên cùng hiện nguồn dữ liệu đang dùng (vd "nguồn: hyperliquid").

## B. Đọc dashboard mỗi ngày
Mỗi card hiển thị (ý nghĩa chi tiết xem `02-chi-so-va-y-nghia.md`):
- **Bias** (LONG / SHORT / ĐỨNG NGOÀI) theo trend 4H.
- **Risk vào lệnh** (badge: Bình thường / Cẩn thận / Rủi ro cao).
- Trend 4H/1D, funding percentile, RSI, khoảng cách EMA, ATR, return 7 ngày.
- **Volume 1D (×TB), Biên 30N (cách đỉnh/đáy), Corr BTC** — ngữ cảnh bổ sung.
- **Checklist** 5 điều kiện theo bias (✓/✗, "X/5 thuận lợi").
- Các **cờ cảnh báo** (flags): funding cực đoan, giá căng quá ATR, volume bất thường,
  sát đỉnh/đáy 30 ngày.

Cách đọc thực dụng:
- Bias SHORT + checklist cao + Risk thấp → bối cảnh thuận để bán theo trend (tự quyết).
- Risk "Rủi ro cao" → tránh hoặc giảm cỡ.
- ĐỨNG NGOÀI → trend chưa rõ, kiên nhẫn thường tốt hơn.
- Sát đỉnh/đáy 30N hoặc volume bất thường → đọc thêm cờ trước khi vào.

## C. Journal (quan trọng nhất — lưu trên PostgreSQL, dùng chung mọi thiết bị)

**Ghi lệnh khi đang vào (chuẩn nhất):**
1. Chọn coin, long/short, gõ lý do → bấm "＋ Ghi lệnh".
2. Hệ thống tự chụp **toàn bộ bối cảnh tại đúng thời điểm vào** — trend, funding, RSI,
   khoảng cách EMA, **và (mới từ ver3) volume, vị trí biên 30N, corr BTC** — lưu kèm
   lệnh xuống database.

**Đóng lệnh:** bấm "Đóng" ở lệnh đó → nhập giá thoát → tự tính PnL%.

**Ghi lệnh đã đóng / quá khứ (nhập tay):** form "Ghi lệnh đã đóng" — nhập coin, side,
giá vào, giá ra → lưu thẳng vào database. Dùng cho lệnh ngoài app hoặc lệnh cũ.

**Xem edge cá nhân:** phần thống kê tự tổng hợp tỉ lệ thắng & PnL trung bình theo nhóm
**funding / trend / RSI / volume**. Cần đủ lệnh mới tin (app cảnh báo khi còn ít lệnh).

> Lưu ý dữ liệu: các trường ngữ cảnh mới (volume, biên 30N, corr) **chỉ có với lệnh ghi
> từ ver3 trở đi**. Lệnh cũ để trống các trường này (nhóm "?") — bình thường, không
> phải lỗi.

Kỷ luật: ghi MỌI lệnh, kể cả lệnh xấu/FOMO — chính lệnh thua mới lộ bối cảnh nên tránh.

## D. Snapshot bối cảnh hằng ngày (mới ở ver3)
Mỗi ngày hệ thống **tự chụp một "ảnh" bối cảnh của cả 4 coin** (trend, funding, RSI,
volume, biên 30N, corr, bias, risk) lưu vào bảng riêng — **kể cả ngày bạn KHÔNG vào
lệnh**. Mục đích: sau này so sánh "hôm mình đánh" khác "hôm mình bỏ qua" ở điểm nào
(tránh chỉ nhìn các ngày có lệnh → thiên lệch).
- Ghi **1 lần/coin/ngày** (gọi lại nhiều lần trong ngày không bị nhân đôi).
- Xem qua API: `GET /api/snapshots?days=30` (trả các snapshot 30 ngày gần nhất).

## E. Trợ lý hỏi-đáp (Gemini)
Ô "Hỏi trợ lý": gõ câu hỏi (vd "ETH thế nào? tôi đang short từ 2080") → Gemini trả lời
dựa trên dữ liệu thật của HUD. Cần cấu hình `GEMINI_API_KEY`. Lưu ý: Gemini chỉ *giải
thích bối cảnh*, không làm tín hiệu chính xác hơn (edge vẫn yếu).

## F. Tự làm mới
Tự kéo dữ liệu mỗi 5 phút; nút "⟳ Refresh data" để kéo ngay.

## G. Công cụ nghiên cứu (nâng cao, chạy local)
Bộ script kiểm chứng ý tưởng mới trước khi đưa vào HUD: `compare.py`, `run_funding.py`,
`study_funding.py`, `study_decay.py` (tách kỳ kiểm tra edge còn sống/đã suy thoái).
Luôn kiểm chứng (trừ phí, chống nhìn trước) trước khi thêm tín hiệu mới.
