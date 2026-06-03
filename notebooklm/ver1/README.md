# Bộ tài liệu cho NotebookLM — Trader Decision Assistant

5 file trong thư mục này là **nguồn (sources)** để nạp vào NotebookLM, giúp hỏi đáp về hệ thống. Mỗi file tự-chứa, có thể đọc độc lập.

## Cách dùng
1. Mở NotebookLM → tạo notebook mới.
2. Upload cả 5 file `.md` trong thư mục này làm sources.
3. Hỏi tự nhiên, ví dụ:
   - "Hệ thống lấy dữ liệu funding ở đâu, có miễn phí không?"
   - "Tín hiệu funding đáng tin tới mức nào?"
   - "Journal hoạt động thế nào và vì sao nó quan trọng?"
   - "Vì sao đây là trợ lý quyết định chứ không phải bot?"

## Danh sách file
- `00-tong-quan.md` — Hệ thống là gì, triết lý, 4 layer, vì sao là trợ lý không phải bot.
- `01-cach-lay-data.md` — Nguồn dữ liệu (CCXT/Binance), free vs trả phí, độ tươi, chống nhìn trước.
- `02-he-thong-ho-tro-gi.md` — Chi tiết 4 layer: Context, Risk Score, Checklist, Journal.
- `03-cach-su-dung.md` — Cách chạy, đọc dashboard, dùng journal, deploy Railway.
- `04-do-dang-tin.md` — Đánh giá trung thực độ đáng tin của từng tín hiệu, các verdict nghiên cứu.

## Lưu ý
Các tài liệu phản ánh kết quả nghiên cứu tới 2026-06. Đặc biệt đọc kỹ `04-do-dang-tin.md`: hệ thống đáng tin như công cụ hỗ trợ + nhật ký, KHÔNG phải máy sinh lời tự động.
