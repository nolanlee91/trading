# Cập nhật từ ver2 → ver3

Tóm tắt những thay đổi của hệ thống so với bộ tài liệu ver2. (Thay đổi v1→v2 nằm ở
`../ver2/05-cap-nhat-v1-v2.md`.)

## Thay đổi lớn

1. **Nguồn dữ liệu chính chuyển sang Hyperliquid (đúng sàn người dùng trade).**
   - Trước (v2): tự dò sàn **Bybit → Binance → OKX** (proxy), funding 8h.
   - Nay (v3): **Hyperliquid là nguồn chính** cho cả giá lẫn funding; proxy chỉ còn là
     **fallback** khi Hyperliquid không vào được.
   - Funding Hyperliquid trả **mỗi giờ (1h)**, không phải 8h. Hệ thống tính đúng %/năm
     theo chu kỳ từng sàn (`rate × 24/chu_kỳ_giờ × 365`).
   - **Sửa logic quy năm funding:** trước cứng `×3×365` (giả định 8h) → nay theo chu kỳ
     thật của sàn. Với Hyperliquid (1h) nếu để công thức cũ sẽ sai ~8 lần.

2. **Thêm coin HYPE → 4 coin (BTC/ETH/SOL/HYPE).**
   - HYPE chỉ có trên Hyperliquid; dữ liệu từ ~cuối 2024 (lịch sử ngắn hơn 3 coin kia).
   - Nhãn hiển thị/lưu giữ dạng quen (BTC/USDT…) để không phá lệnh đã ghi; số liệu sau
     lưng lấy từ Hyperliquid.

3. **Thêm 3 chỉ số ngữ cảnh trên HUD.**
   - **Volume 1D (×TB):** khối lượng ngày so trung bình 20 ngày (cờ khi ≥ ×2).
   - **Biên 30 ngày:** vị trí giá so đỉnh/đáy 30 ngày (cờ khi sát đỉnh/đáy).
   - **Corr BTC:** tương quan lợi suất ngày 30 phiên với BTC (BTC=1.0; coin đi riêng có
     corr thấp).
   - Chi tiết cách đọc: `02-chi-so-va-y-nghia.md` mục 4.

4. **Bối cảnh được LƯU XUỐNG database (không chỉ hiển thị).**
   - Mỗi lệnh ghi nhật ký nay kèm thêm 4 trường ngữ cảnh mới (volume, cách đỉnh, cách
     đáy, corr BTC). Thống kê edge thêm nhóm **theo volume**.
   - Lệnh cũ (trước v3) để trống các trường này → rơi nhóm "?" (bình thường).

5. **Snapshot bối cảnh hằng ngày (N-4).**
   - Hệ thống tự chụp bối cảnh cả 4 coin **mỗi ngày, kể cả ngày không vào lệnh**, lưu
     bảng `daily_snapshots` (1 dòng/coin/ngày, không nhân đôi).
   - Mục đích: sau này so "ngày đánh vs ngày bỏ qua" để tránh thiên lệch.
   - Xem qua API: `GET /api/snapshots?days=30`.

## KHÔNG đổi (vẫn đúng từ v1/v2)
- Triết lý: HUD hỗ trợ quyết định, không phải bot; không bịa xác suất.
- Bias theo trend 4H; Risk Score & Checklist xoay theo bias (long/short/đứng ngoài).
- Journal trên PostgreSQL (dùng chung mọi thiết bị), có ghi lệnh nhập tay; chạy local
  không có `DATABASE_URL` thì dùng SQLite.
- Trợ lý Gemini, tối ưu mobile.
- Verdict nghiên cứu: tín hiệu cơ học đơn lẻ không thắng buy-and-hold; edge yếu; giá
  trị thật ở journal tìm edge cá nhân. (Xem `04-do-dang-tin.md`.)

## Lưu ý khi đổi nguồn
- Giá & funding hiển thị có thể **lệch nhẹ** so với bản v2 (do đổi từ Binance/Bybit
  sang Hyperliquid) — đúng chủ ý, không phải lỗi.
- Các lệnh/snapshot ghi **trước thời điểm đổi nguồn** mang context theo sàn cũ; khi soi
  edge nhớ mốc chuyển nguồn.
