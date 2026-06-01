# Cách sử dụng hệ thống

## A. Chạy bản web (cách dùng chính)

Hệ thống là một web app (FastAPI). Chạy local:
```
cd trading-brain
.venv\Scripts\activate
uvicorn app:app --reload
```
Mở trình duyệt: `http://localhost:8011` (hoặc cổng uvicorn báo).

Lần đầu mở hiện "đang tải..." khoảng 30-60 giây (đang kéo dữ liệu), sau đó hiển thị 3 card BTC/ETH/SOL.

## B. Đọc dashboard mỗi ngày

Mỗi card coin cho thấy:
- Trend 4H/1D (xanh = tăng, đỏ = giảm, vàng = lẫn lộn).
- Badge **Risk Score** (Bình thường / Cẩn thận / Rủi ro cao).
- Funding percentile, RSI, khoảng cách EMA, return 7 ngày.
- **Checklist** ✓/✗ với điểm "X/5 thuận lợi".
- Cờ cảnh báo (nếu có).

Cách đọc thực dụng:
- Risk "Rủi ro cao" + checklist thấp → đừng vào, hoặc giảm cỡ lệnh.
- Trend bullish + giá gần EMA20 + checklist cao → bối cảnh thuận cho long (vẫn tự quyết).
- Trend bearish → hệ thống khuyên đứng ngoài; long ngược trend rủi ro cao.

## C. Dùng Journal (quan trọng nhất)

Đây là nơi tạo giá trị dài hạn.

**Ghi một lệnh:**
1. Chọn coin, chọn long/short.
2. Gõ lý do vào lệnh (vd "pullback EMA20, funding âm").
3. Bấm "＋ Ghi lệnh". Hệ thống tự lưu toàn bộ bối cảnh thị trường tại thời điểm đó.

**Đóng một lệnh:**
1. Trong bảng "Lệnh & PnL", bấm "Đóng" ở lệnh tương ứng.
2. Nhập giá thoát. Hệ thống tính PnL %.

**Xem edge cá nhân:**
- Phần "Edge cá nhân" tự tổng hợp: tỉ lệ thắng và PnL trung bình theo từng nhóm bối cảnh (funding, trend, RSI).
- Lưu ý: cần đủ lệnh mới đáng tin. Dưới 30 lệnh, hệ thống cảnh báo "chưa đủ tin".

**Kỷ luật khuyến nghị:** ghi MỌI lệnh, kể cả lệnh xấu/FOMO. Chính những lệnh thua mới lộ ra bối cảnh nên tránh.

## D. Tự làm mới dữ liệu

- Bản deploy tự kéo dữ liệu mỗi 5 phút.
- Trang tự làm mới hiển thị mỗi 5 phút.
- Nút "⟳ Refresh data" để kéo ngay.

## E. Deploy lên Railway (để mở từ điện thoại)

Tóm tắt (chi tiết trong file DEPLOY.md của dự án):
1. `git init && git add -A && git commit -m "..."`
2. `railway login` → `railway init` → `railway up`
3. `railway domain` để tạo URL public.

**Lưu ý quan trọng về Journal:** nhật ký lưu bằng SQLite. Filesystem Railway là tạm → mỗi lần redeploy sẽ mất nhật ký. Để giữ: thêm biến môi trường `DB_PATH=/data/journal.db` và gắn một Volume mount tại `/data`. (Hoặc chuyển sang PostgreSQL ở giai đoạn sau.)

## F. Công cụ nghiên cứu kèm theo (nâng cao)

Ngoài web app, dự án còn các script để kiểm chứng ý tưởng mới trước khi tin:
- `compare.py` — so sánh các biến thể chiến lược trend.
- `run_funding.py`, `study_funding.py`, `study_decay.py` — nghiên cứu tín hiệu funding.
- `study_decay.py` đặc biệt: tách dữ liệu 2 nửa thời gian để kiểm tra một edge còn sống hay đã suy thoái.

Các script này dùng khi muốn thêm tín hiệu mới vào HUD — luôn kiểm chứng (trừ phí, chống nhìn trước) trước khi đưa vào dùng.
