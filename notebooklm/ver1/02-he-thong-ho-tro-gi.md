# Hệ thống hỗ trợ gì — chi tiết 4 layer

Hệ thống là một HUD (heads-up display) gồm 4 lớp. Lớp 1-3 đọc thị trường; lớp 4 (quan trọng nhất) đọc chính người dùng.

## Layer 1 — Context (bối cảnh thị trường)

Với mỗi coin (BTC/ETH/SOL), hiển thị:

- **Trend 4H và 1D**: dựa trên xếp tầng EMA (đường trung bình động).
  - `bullish` (tăng): EMA20 > EMA50 > EMA200.
  - `bearish` (giảm): EMA20 < EMA50 < EMA200.
  - `mixed` (lẫn lộn): còn lại — thường là đi ngang/không rõ xu hướng.
- **Funding percentile**: funding hiện tại đứng ở vị trí bao nhiêu % so với 1 năm gần nhất → đám đông đang lệch long hay short, và lệch mạnh tới đâu.
- **RSI (14, khung 4H)**: chỉ báo động lượng. >70 quá mua, <30 quá bán.
- **Khoảng cách giá so EMA20**, tính bằng số lần ATR (độ biến động): giá đang "căng" (xa EMA, dễ hồi) hay gần vùng vào đẹp.
- **Return 7 ngày** và **ATR%** (độ biến động, để ước lượng cỡ lệnh).

Mục đích: thấy nhanh khung lớn đang nghiêng chiều nào, đám đông ở đâu, giá có căng không.

## Bias — đánh THEO trend lớn

Trước khi chấm Risk và Checklist, hệ thống xác định **bias** theo trend 4H:
- 4H bullish → **bias LONG** (chỉ xét mua thuận trend).
- 4H bearish → **bias SHORT** (chỉ xét bán thuận trend).
- 4H mixed → **ĐỨNG NGOÀI** (không có lợi thế rõ).

Nguyên tắc rút ra từ nghiên cứu: *đừng đánh ngược trend lớn*. Vì vậy Risk Score và
Checklist đều **xoay theo bias**, không cứng cho long.

## Layer 2 — Risk Score (điểm rủi ro vào lệnh THEO BIAS)

Chấm điểm rủi ro nếu vào lệnh **đúng theo bias** ngay lúc này:

**Khi bias LONG** (uptrend): funding ≥95pct (+2, đám đông long), RSI ≥75 (+2, quá mua),
giá ≥2 ATR TRÊN EMA20 (+3, căng lên dễ hồi), 1D bearish ngược bias (+2).

**Khi bias SHORT** (downtrend): funding ≤5pct (+2, đám đông short → dễ squeeze lên),
RSI ≤25 (+2, quá bán → dễ nảy), giá ≤-2 ATR DƯỚI EMA20 (+3, căng xuống dễ hồi lên),
1D bullish ngược bias (+2).

**Khi ĐỨNG NGOÀI:** mặc định điểm cao (không có bias).

Tổng → **0-2 Bình thường · 3-5 Cẩn thận · 6+ Rủi ro cao**, kèm lý do. Đây là cảnh báo
"đừng vào lệnh sai thời điểm" được định lượng (cả FOMO mua đỉnh lẫn đuổi bán đáy).

## Layer 3 — Checklist (theo BIAS)

Hiện các điều kiện thuận lợi để vào lệnh **thuận trend** dưới dạng ✓/✗, rồi đếm X/5.

**Bias LONG:** 4H bullish · 1D không bearish · giá gần/dưới EMA20 (pullback để mua) ·
RSI không quá nóng (<70) · funding không đông long (<85pct).

**Bias SHORT:** 4H bearish · 1D không bullish · giá gần/trên EMA20 (hồi lên kháng cự để
bán) · RSI không quá bán (>30) · funding không đông short (>15pct).

Lưu ý điều kiện vào lệnh đúng: trong downtrend, điểm bán đẹp là **khi giá hồi LÊN kháng
cự** (EMA20), không phải đuổi bán khi giá đã căng xuống. Checklist phản ánh đúng điều này.

## Layer 4 — Journal (nhật ký) — phần có giá trị thật nhất

Đây là thứ tạo ra **edge cá nhân**, khác với việc đi tìm alpha chung (đã bị các quỹ khai thác cạn).

Cách hoạt động:
1. Khi người dùng vào một lệnh thật, bấm "Ghi lệnh". Hệ thống **tự động chụp lại bối cảnh tại thời điểm đó**: giá, funding percentile, trend 4H/1D, RSI, khoảng cách EMA — kèm lý do người dùng tự ghi.
2. Khi đóng lệnh, nhập giá thoát → hệ thống tính **PnL %**.
3. Sau khi tích lũy đủ lệnh (lý tưởng 200-300), phần thống kê chỉ ra:
   - Người dùng **thắng nhiều nhất** ở bối cảnh nào (vd: funding 25-50 percentile, trend 4H bullish, RSI 50-65).
   - Người dùng **cháy nhiều nhất** ở bối cảnh nào (vd: funding >90, RSI >75 — tức FOMO).

Thống kê được nhóm theo: funding percentile bucket, trend 4H, RSI bucket — mỗi nhóm hiện số lệnh, tỉ lệ thắng, PnL trung bình.

Triết lý: tìm "khi nào CHÍNH BẠN giao dịch tốt" dễ và hữu ích hơn nhiều so với tìm một công thức thắng cả thị trường.

## Điều hệ thống cố tình KHÔNG làm

- Không tự đặt lệnh.
- Không hiển thị "tín hiệu mua/bán" kiểu cứng nhắc.
- Không bịa ra phần trăm xác suất thắng.
- Khi không có kèo rõ (vd downtrend), nó nói thẳng "đứng ngoài/chờ" thay vì vẽ ra cơ hội ảo.
