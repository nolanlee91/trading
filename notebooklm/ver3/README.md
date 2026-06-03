# Bộ tài liệu NotebookLM — ver3 (BẢN HIỆN HÀNH)

Đây là bộ nguồn **mới nhất** để nạp vào NotebookLM. Mỗi file tự-chứa, đọc độc lập.

## Nạp vào NotebookLM
1. Mở NotebookLM → tạo (hoặc cập nhật) notebook.
2. Upload các file `.md` trong thư mục **ver3** này làm sources.
3. Nếu trước đó đã nạp ver1/ver2: **xóa source cũ, thay bằng ver3** (tránh mâu thuẫn).

## Danh sách file
- `00-tong-quan.md` — hệ thống là gì, triết lý, 4 layer, những điểm mới ver3.
- `01-cach-lay-data.md` — **Hyperliquid là nguồn chính** (sàn user trade), funding 1h,
  4 coin gồm HYPE, fallback proxy, độ tươi.
- `02-chi-so-va-y-nghia.md` — **ý nghĩa CHI TIẾT từng chỉ số**: Bias, Risk, Checklist,
  + 3 chỉ số ngữ cảnh mới (volume, biên 30N, corr BTC).
- `03-cach-su-dung.md` — dùng online, journal PostgreSQL, snapshot hằng ngày, ghi tay,
  chat Gemini.
- `04-do-dang-tin.md` — độ đáng tin từng tín hiệu, verdict nghiên cứu.
- `05-cap-nhat-v2-v3.md` — những thay đổi so với ver2.

## Câu hỏi mẫu để test trong NotebookLM
- "Hệ thống lấy dữ liệu từ sàn nào? Vì sao là Hyperliquid?"
- "Funding Hyperliquid tính %/năm thế nào, khác sàn 8h ra sao?"
- "Corr BTC nghĩa là gì, đọc thế nào?"
- "Biên 30 ngày và volume bất thường dùng để làm gì?"
- "Snapshot hằng ngày để làm gì?"
- "Bias được xác định dựa vào đâu? Risk vào lệnh 5 nghĩa là gì?"
- "Vì sao đây là trợ lý quyết định chứ không phải bot?"

> Bản cũ nằm ở `../ver1/` và `../ver2/` (chỉ để tham khảo lịch sử — đừng nạp lẫn với ver3).
