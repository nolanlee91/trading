# Tài liệu NotebookLM — phiên bản

Thư mục này chứa các bộ tài liệu (sources) cho NotebookLM, chia theo phiên bản.

| Thư mục | Trạng thái | Dùng để |
|---|---|---|
| **`ver3/`** | ✅ **HIỆN HÀNH — nạp bộ này** | Bản mới nhất: Hyperliquid là nguồn chính (funding 1h), thêm HYPE (4 coin), ngữ cảnh mới (volume/biên 30N/corr BTC), persist context vào journal + snapshot hằng ngày |
| `ver2/` | 📦 Lưu trữ (cũ) | Bias-aware, online PostgreSQL, Gemini, tự dò sàn proxy — đã bị ver3 thay |
| `ver1/` | 📦 Lưu trữ (cũ) | Bản đầu, chỉ để tham khảo lịch sử |

## Cần làm gì
- Nạp/cập nhật NotebookLM bằng các file trong **`ver3/`**.
- Nếu đã nạp ver1/ver2 trước đó → xóa source cũ, thay bằng ver3 (tránh mâu thuẫn).
- Xem `ver3/README.md` để biết danh sách file + câu hỏi mẫu.
- Xem `ver3/05-cap-nhat-v2-v3.md` để biết những gì đã thay đổi.
