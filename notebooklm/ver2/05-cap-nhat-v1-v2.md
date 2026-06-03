# Cập nhật từ ver1 → ver2

Tóm tắt những thay đổi của hệ thống so với bộ tài liệu ver1, để biết bản nào mới.

## Thay đổi lớn

1. **Checklist & Risk Score giờ theo BIAS (long/short/đứng ngoài).**
   - Trước (v1): checklist & risk cứng cho LONG, kể cả khi downtrend → sai logic.
   - Nay (v2): xác định bias theo trend 4H (bullish→long, bearish→short, mixed→đứng
     ngoài); checklist và risk xoay theo bias. Chi tiết: `02-chi-so-va-y-nghia.md`.

2. **Đã deploy online (Railway), dùng chung nhiều thiết bị.**
   - App chạy tại một URL công khai, mở trên điện thoại/laptop/máy khác đều được.
   - Tự refresh dữ liệu mỗi 5 phút.

3. **Journal chuyển sang PostgreSQL (dùng chung 1 database).**
   - Trước (v1): SQLite local (mỗi máy 1 file riêng).
   - Nay (v2): có `DATABASE_URL` → dùng PostgreSQL trên Railway → mọi thiết bị chung
     một journal, bền qua redeploy. (Chạy local không có DATABASE_URL thì vẫn SQLite.)
   - Thêm chức năng **"Ghi lệnh đã đóng" nhập tay** (entry/exit thật) cho lệnh quá khứ.

4. **Tự dò sàn lấy dữ liệu (tránh lỗi 451 Binance).**
   - Binance hay bị chặn 451 ở mạng công ty/cloud. App tự thử **Bybit → Binance → OKX**,
     dùng sàn nào vào được. Dashboard hiện tên nguồn đang dùng.

5. **Trợ lý hỏi-đáp bằng Gemini.**
   - Thêm ô chat: hỏi tự nhiên, Gemini trả lời dựa trên dữ liệu thật của HUD, có ràng
     buộc trung thực (không bịa dự báo, nhắc edge yếu & quản trị rủi ro). Cần
     `GEMINI_API_KEY`.

6. **Tối ưu giao diện cho mobile.**
   - Lưới 1 cột trên màn nhỏ, bảng cuộn ngang, input/nút cỡ chạm tay.

## Sửa lỗi quan trọng
- **Bug phân trang dữ liệu:** code cũ dừng tải sớm với sàn giới hạn ~200 nến/lần
  (Bybit/OKX) → từng hiển thị GIÁ CŨ sai (vd ETH $4225 thay vì ~$1989). Đã sửa: phân
  trang tới hiện tại.
- **Nút ghi lệnh trên web:** trước truy cập sai biến (id gạch ngang) nên không chạy;
  đã sửa dùng getElementById.

## KHÔNG đổi (vẫn đúng từ v1)
- Triết lý: HUD hỗ trợ quyết định, không phải bot; không bịa xác suất.
- Verdict nghiên cứu: tín hiệu cơ học đơn lẻ không thắng buy-and-hold; edge yếu;
  giá trị thật ở journal tìm edge cá nhân. (Xem `04-do-dang-tin.md`.)
- Nguồn dữ liệu chính: giá + funding (free, lịch sử dài); OI/liquidation vẫn khó/trả phí.
