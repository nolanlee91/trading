# Độ đáng tin của hệ thống — đánh giá trung thực (ver2)

Phần này không đổi về bản chất so với ver1: mọi kết luận từ backtest thật 2023→nay, có
trừ phí + slippage + funding, tuân thủ chống nhìn-trước.

## Tóm tắt một câu
Hệ thống **đáng tin như công cụ trình bày bối cảnh + ghi nhật ký**, KHÔNG đáng tin như
"máy in tiền". Giá trị thật nằm ở kỷ luật và ở edge cá nhân (journal), không phải ở một
tín hiệu thị trường thần kỳ.

## Verdict các tín hiệu đã kiểm chứng
- **Trend-following (EMA pullback):** gần hòa vốn, KHÔNG thắng buy-and-hold; lợi nhuận
  chủ yếu là **beta** (ăn theo sóng) chứ không phải **alpha** (kỹ năng); suy thoái sau 2023.
- **Short / lọc regime:** làm tệ hơn → đã tắt.
- **Phân kỳ RSI 15m (scalp):** **cháy −100%** vì phí; bài học: scalp khung nhỏ chết vì phí.
- **Funding-squeeze (long khi funding cực âm):** edge **yếu & không nhất quán** khi đo
  đúng (expanding percentile, tách kỳ, so với drift). Không thắng buy-and-hold.

## Khái niệm cần hiểu
- **Drift:** xu hướng nền của thị trường (giữ đại cũng lời/lỗ theo thị trường).
- **Beta vs Alpha:** Beta = lời do ăn theo thị trường (ai cũng có); Alpha = lời vượt
  trên thị trường (kỹ năng). Nhiều "chiến lược lời" thực ra chỉ là beta trá hình.
- **Decay:** edge mất dần khi nhiều người khai thác (tín hiệu công khai dễ bị arbitrage).
- **Overfit:** vặn tham số cho khớp quá khứ → đẹp giả tạo, sập khi giao dịch thật.

## Nên tin tới đâu
| Thành phần | Độ tin | Dùng để |
|---|---|---|
| Bias / Trend 4H-1D | Trung bình | Xác định chiều nên theo |
| Funding percentile | Yếu | Biết đám đông lệch đâu |
| Risk Score | Trung bình | Tránh vào lệnh thời điểm tệ |
| Checklist | Trung bình | Ép kỷ luật, nhìn đủ yếu tố |
| Tín hiệu vào lệnh tự động | KHÔNG có | (hệ thống không làm việc này) |
| Journal / edge cá nhân | Cao (sau đủ lệnh) | Khám phá điểm mạnh/yếu bản thân |

## Vì sao vẫn đáng làm dù tín hiệu yếu
1. **Kỷ luật:** buộc nhìn đủ yếu tố (bias, risk, checklist) thay vì FOMO.
2. **Cảnh báo rủi ro:** Risk Score giúp tránh vào lệnh thời điểm tệ.
3. **Trung thực:** nói "đứng ngoài" khi không có kèo, không vẽ cơ hội ảo.
4. **Journal:** nguồn edge khả thi nhất — tìm "khi nào CHÍNH BẠN thắng". Cần đủ dữ liệu.

## Cảnh báo cuối
Đây là công cụ HỖ TRỢ QUYẾT ĐỊNH, không phải lời khuyên đầu tư, không đảm bảo lợi
nhuận. Người dùng tự chịu trách nhiệm quản trị rủi ro (cỡ lệnh, cắt lỗ, đòn bẩy).
