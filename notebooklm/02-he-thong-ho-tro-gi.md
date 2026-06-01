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

## Layer 2 — Risk Score (điểm rủi ro)

Chấm điểm rủi ro **nếu vào lệnh long ngay lúc này**, theo quy tắc cộng điểm:

| Điều kiện | Điểm |
|---|---|
| Funding ≥ 95 percentile (đám đông long cực đông) | +2 |
| RSI ≥ 75 (quá mua) | +2 |
| Giá ≥ 2 ATR trên EMA20 (quá căng) | +3 |
| Trend 4H lẫn lộn (mixed) | +2 |
| Trend 4H giảm (bearish) | +2 |

Tổng điểm → phân loại:
- **0-2: Bình thường**
- **3-5: Cẩn thận**
- **6+: Rủi ro cao**

Kèm theo lý do vì sao điểm cao (vd "RSI >75", "giá >2 ATR trên EMA20"). Đây là cảnh báo "đừng FOMO" được định lượng.

## Layer 3 — Checklist (danh sách kiểm tra)

Thay vì phán "LONG", hệ thống hiện các điều kiện thuận lợi cho lệnh long dưới dạng ✓/✗:

- ✓/✗ 4H bullish
- ✓/✗ 1D không bearish
- ✓/✗ Giá gần/dưới EMA20 (đang pullback, không đu đỉnh)
- ✓/✗ RSI không quá nóng (<70)
- ✓/✗ Funding không đông long (<85 percentile)

Rồi đếm: ví dụ "**3/5 thuận lợi**". Người dùng tự cân nhắc có đủ điều kiện theo kế hoạch của mình không. Giống checklist trước khi cất cánh — buộc nhìn đủ yếu tố thay vì cảm tính.

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
