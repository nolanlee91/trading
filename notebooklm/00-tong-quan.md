# Tổng quan hệ thống — Trader Decision Assistant

## Hệ thống này là gì

Một **trợ lý quyết định giao dịch crypto** (Trader Decision Assistant) — giống **HUD trong poker**, KHÔNG phải bot tự động vào lệnh. Nó đọc dữ liệu thị trường, trình bày *bối cảnh* và *cảnh báo rủi ro*, rồi để **người dùng tự quyết định** vào/ra lệnh.

Tên thư mục dự án: `trading-brain`. Ngôn ngữ: Python. Triển khai: web app (FastAPI) deploy lên Railway, mở được từ điện thoại.

## Triết lý cốt lõi

1. **Không auto-trade.** Hệ thống không tự đặt lệnh. Người dùng đánh Hyperliquid theo phong cách discretionary (tự quyết), hệ thống chỉ hỗ trợ.
2. **Không bịa xác suất.** Không hiển thị kiểu "LONG, confidence 82%". Mọi con số đều là dữ liệu thật hoặc quy tắc heuristic ghi rõ.
3. **Kiểm chứng trước khi tin.** Mọi ý tưởng giao dịch đều được backtest trung thực (trừ phí, chống nhìn trước) trước khi dùng.
4. **Tìm edge cá nhân, không tìm alpha thần kỳ.** Alpha chung của thị trường crypto đã bị hàng nghìn quỹ khai thác cạn. Edge dễ tìm hơn là *edge cá nhân*: chính người dùng thắng/thua nhiều nhất ở bối cảnh nào.

## Vì sao lại là "trợ lý" chứ không phải "bot"

Hệ thống ra đời sau một quá trình nghiên cứu trung thực, trong đó **mọi chiến lược cơ học đơn lẻ được thử đều KHÔNG có lợi thế bền vững thắng được chiến lược mua-và-giữ (buy-and-hold)**:
- Trend-following (mua theo xu hướng): hòa vốn, lợi nhuận chủ yếu là "ăn theo sóng thị trường" chứ không phải kỹ năng.
- Phân kỳ RSI khung 15 phút (scalp): cháy tài khoản vì phí giao dịch.
- Tín hiệu funding (vị thế đám đông): có chút lợi thế nhưng yếu và không ổn định.

Kết luận thực dụng: thay vì cố tìm "chiến lược thần kỳ", hệ thống chuyển thành **công cụ hỗ trợ con người ra quyết định tốt hơn** + **nhật ký để khám phá edge cá nhân**.

## Bốn thành phần (4 layer)

1. **Context** — trend khung 4H & 1D, funding percentile, RSI, khoảng cách giá so EMA, độ biến động (ATR).
2. **Risk Score** — chấm điểm rủi ro nếu vào lệnh long ngay lúc này (thang 0-9).
3. **Checklist** — danh sách điều kiện thuận lợi, hiện ✓/✗ và đếm "X/5 thuận lợi".
4. **Journal** — ghi lại từng lệnh thật của người dùng kèm bối cảnh lúc vào, rồi tính PnL. Sau 200-300 lệnh, hệ thống chỉ ra người dùng thắng/cháy ở bối cảnh nào = **edge cá nhân**.

## Các tài liệu khác trong bộ này

- `01-cach-lay-data.md` — Hệ thống lấy dữ liệu ở đâu, miễn phí hay trả phí, tươi tới mức nào.
- `02-he-thong-ho-tro-gi.md` — Chi tiết 4 layer hỗ trợ gì.
- `03-cach-su-dung.md` — Cách chạy và sử dụng, đặc biệt là nhật ký.
- `04-do-dang-tin.md` — Độ đáng tin: cái gì đã kiểm chứng, cái gì yếu, tin tới đâu.
