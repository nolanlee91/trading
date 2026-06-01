# Độ đáng tin của hệ thống — đánh giá trung thực

Đây là phần quan trọng nhất để không tự lừa mình. Mọi kết luận dưới đây đều từ backtest thật trên dữ liệu 2023→2026, có trừ phí + slippage + funding, và tuân thủ chống nhìn-trước.

## Tóm tắt một câu

Hệ thống **đáng tin như một công cụ trình bày bối cảnh và ghi nhật ký**, KHÔNG đáng tin như một "máy in tiền" tự sinh lời. Giá trị thật nằm ở kỷ luật và ở edge cá nhân (journal), không phải ở một tín hiệu thị trường thần kỳ.

## Các tín hiệu đã kiểm chứng và verdict

### 1. Trend-following (mua theo xu hướng + pullback EMA)
- Kết quả: gần hòa vốn sau phí. BTC nhỉnh dương (+5% với cấu hình tốt nhất), ETH/SOL quanh hòa.
- **Không thắng được buy-and-hold** (mua-và-giữ). Ví dụ hold BTC +344% trong khi chiến lược chỉ +5%.
- Phần lớn lợi nhuận là **beta** (ăn theo sóng tăng chung), không phải **alpha** (kỹ năng). Khi tách riêng, ở giai đoạn 2023-2024 chiến lược thậm chí THUA việc giữ ngẫu nhiên.
- **Suy thoái (decay)**: mạnh 2023, yếu dần 2025-2026.
- Độ tin để dùng làm tín hiệu vào lệnh: **thấp**. Chỉ dùng làm *bối cảnh xu hướng*.

### 2. Short (bán khống) và lọc regime
- Thêm chiều short làm kết quả **tệ hơn** (short trong thị trường tăng = bơi ngược dòng + bị squeeze).
- Lọc regime bằng độ giãn EMA: **không hiệu quả**, có khi tệ hơn.
- Độ tin: **thấp**, đã tắt.

### 3. Phân kỳ RSI khung 15 phút (scalp)
- Kết quả: **cháy tài khoản (-100%)** trên cả 3 coin.
- Lý do: khung càng nhỏ, phí giao dịch càng nuốt hết lợi nhuận; phân kỳ đảo chiều thuần là "bắt dao rơi".
- Bài học: **scalp khung nhỏ chết vì phí**, không phải vì thiếu tín hiệu.
- Độ tin: **rất thấp**, không dùng.

### 4. Funding-squeeze (long khi funding cực âm) — tín hiệu chính của HUD
- Nghiên cứu mô tả ban đầu trông hứa hẹn (funding âm sâu → giá thường tăng sau 48-72h, có dose-response rõ).
- Nhưng khi kiểm chứng ĐÚNG cách (expanding percentile chống nhìn trước, tách kỳ, so với drift thị trường): edge **yếu và không nhất quán**.
  - Không coin nào vượt drift ở CẢ hai giai đoạn (2023-24 và 2025-26).
  - Mỗi coin chỉ nhỉnh ở một giai đoạn, và là giai đoạn khác nhau → dấu hiệu nhiễu.
- **Không thắng buy-and-hold.** Lợi nhuận đẹp 2023-2024 phần lớn lại là beta.
- Độ tin: **yếu**. Chỉ nên coi là *một input ngữ cảnh* (đám đông đang lệch đâu), không phải tín hiệu vào lệnh độc lập.

### Funding velocity (tốc độ funding đổi)
- Không hơn funding level rõ ràng; coin-dependent (cứu coin này, hại coin kia) → mong manh.

## Khái niệm quan trọng để hiểu độ tin

- **Drift**: xu hướng tăng/giảm nền của thị trường. Crypto 2023-2024 cứ giữ đại cũng lời → đó là drift, không phải kỹ năng.
- **Beta vs Alpha**: Beta = lời do ăn theo thị trường (ai cũng có). Alpha = lời vượt trên thị trường (kỹ năng thật). Nhiều "chiến lược lời" thực ra chỉ là beta trá hình.
- **Decay**: edge mất dần khi nhiều người khai thác. Tín hiệu công khai (RSI, EMA, funding) dễ bị arbitrage cạn.
- **Overfit**: vặn tham số cho khớp quá khứ → số đẹp giả tạo, sập khi giao dịch thật.

## Vì sao vẫn đáng làm dù tín hiệu yếu

1. **Kỷ luật**: hệ thống buộc nhìn đủ yếu tố (trend, funding, rủi ro, checklist) thay vì cảm tính/FOMO. Bản thân điều này giảm lỗi.
2. **Cảnh báo rủi ro**: Risk Score giúp tránh vào lệnh ở thời điểm tệ (quá mua, quá căng, đám đông đông).
3. **Trung thực**: hệ thống nói "đứng ngoài" khi không có kèo, không vẽ cơ hội ảo.
4. **Journal — edge cá nhân**: đây mới là nguồn edge khả thi nhất. Tìm "khi nào CHÍNH BẠN thắng" dễ hơn tìm alpha chung. Nhưng cần đủ dữ liệu (200-300 lệnh) mới đáng tin.

## Nên tin tới đâu — bảng nhanh

| Thành phần | Độ tin | Dùng để |
|---|---|---|
| Trend 4H/1D | Trung bình | Bối cảnh xu hướng |
| Funding percentile | Yếu | Biết đám đông lệch đâu |
| Risk Score | Trung bình | Tránh vào lệnh thời điểm tệ |
| Checklist | Trung bình | Ép kỷ luật, nhìn đủ yếu tố |
| Tín hiệu vào lệnh tự động | KHÔNG có | (hệ thống không làm việc này) |
| Journal / edge cá nhân | Cao (sau đủ lệnh) | Khám phá điểm mạnh/yếu của bản thân |

## Cảnh báo cuối

Đây là công cụ HỖ TRỢ QUYẾT ĐỊNH, không phải lời khuyên đầu tư và không đảm bảo lợi nhuận. Người dùng tự chịu trách nhiệm quản trị rủi ro (cỡ lệnh, cắt lỗ). Dữ liệu funding/giá lấy từ Binance; thị trường thật ở Hyperliquid có thể khác đôi chút.
