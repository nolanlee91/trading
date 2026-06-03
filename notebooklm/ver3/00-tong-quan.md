# Tổng quan hệ thống — Trader Decision Assistant (ver3)

## Hệ thống này là gì

Một **trợ lý quyết định giao dịch crypto** (Trader Decision Assistant) — giống **HUD
trong poker**, KHÔNG phải bot tự động vào lệnh. Nó đọc dữ liệu thị trường, trình bày
*bối cảnh* + *cảnh báo rủi ro*, rồi để **người dùng tự quyết định**.

Hiện đã **chạy online** (web app deploy trên Railway), mở từ điện thoại/laptop/máy khác
đều được, dùng chung một database.

## Triết lý cốt lõi
1. **Không auto-trade.** Hệ thống không đặt lệnh; người dùng (đánh Hyperliquid
   discretionary) tự quyết.
2. **Không bịa xác suất.** Không hiển thị "confidence 82%". Mọi số là dữ liệu thật
   hoặc quy tắc heuristic ghi rõ.
3. **Kiểm chứng trước khi tin.** Mọi ý tưởng đều backtest trung thực (trừ phí, chống
   nhìn trước) trước khi dùng.
4. **Tìm edge cá nhân, không tìm alpha thần kỳ.** Alpha chung đã bị nghìn quỹ khai
   thác cạn; dễ hơn là tìm *chính người dùng* thắng/cháy ở bối cảnh nào (qua Journal).

## Mới ở ver3 (so với ver2)
- **Dữ liệu lấy thẳng từ Hyperliquid** — đúng sàn người dùng trade thật — cho cả giá
  lẫn funding (funding Hyperliquid trả **mỗi giờ**, không phải 8h như sàn perp khác).
  Khi Hyperliquid không vào được mới fallback proxy (Bybit/Binance/OKX).
- **Thêm coin HYPE** (chỉ có trên Hyperliquid) bên cạnh BTC/ETH/SOL → **4 coin**.
- **Ngữ cảnh giàu hơn:** volume bất thường, vị trí giá trong biên 30 ngày, tương quan
  với BTC.
- **Bối cảnh được LƯU XUỐNG database**, không chỉ hiện trên màn hình: mỗi lệnh ghi kèm
  các chỉ số ngữ cảnh; ngoài ra hệ thống còn **chụp bối cảnh thị trường mỗi ngày**
  (kể cả ngày không vào lệnh) để sau này so "ngày đánh vs ngày bỏ qua".

## Bốn thành phần (4 layer)
1. **Context** — trend 4H/1D, funding percentile, RSI, khoảng cách EMA, ATR, **+ volume
   1D so trung bình, vị trí trong biên 30 ngày, tương quan BTC**.
2. **Risk Score** — điểm rủi ro khi vào lệnh THEO BIAS (0-9). Xem `02-chi-so-va-y-nghia.md`.
3. **Checklist** — 5 điều kiện thuận lợi theo bias (✓/✗, tally X/5).
4. **Journal** — ghi lệnh thật + context lúc vào + PnL → sau 200-300 lệnh tìm edge
   cá nhân. Lưu trên PostgreSQL (dùng chung mọi thiết bị). **+ snapshot bối cảnh hằng ngày.**

Kèm: **trợ lý hỏi-đáp Gemini** (giải thích bối cảnh bằng ngôn ngữ tự nhiên, bám dữ
liệu thật).

## Vì sao là "trợ lý" chứ không phải "bot"
Quá trình nghiên cứu cho thấy **mọi chiến lược cơ học đơn lẻ đều không có edge bền
thắng buy-and-hold**: trend-following (hòa, chủ yếu beta), short/regime (tệ hơn), phân
kỳ 15m (cháy vì phí), funding-squeeze (yếu). → Giá trị thật chuyển sang **hỗ trợ con
người ra quyết định tốt hơn + nhật ký tìm edge cá nhân**. Chi tiết: `04-do-dang-tin.md`.

## Các tài liệu trong bộ ver3
- `00-tong-quan.md` — file này.
- `01-cach-lay-data.md` — lấy dữ liệu ở đâu (Hyperliquid chính), độ tươi.
- `02-chi-so-va-y-nghia.md` — **ý nghĩa CHI TIẾT từng chỉ số** (Bias, Risk, Checklist,
  + 3 chỉ số ngữ cảnh mới).
- `03-cach-su-dung.md` — cách dùng (online, journal, snapshot, chat, nhập tay).
- `04-do-dang-tin.md` — độ đáng tin của từng tín hiệu.
- `05-cap-nhat-v2-v3.md` — những thay đổi so với ver2.
