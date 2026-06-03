# Hệ thống lấy dữ liệu như thế nào (ver3)

## Nguồn chính: Hyperliquid (đúng sàn người dùng trade thật)

Dùng thư viện **CCXT** lấy dữ liệu công khai. Từ ver3, **nguồn chính là Hyperliquid** —
lấy cả **giá (OHLCV)** lẫn **funding** trực tiếp từ sàn người dùng giao dịch thật. Lý
do: bối cảnh để ra quyết định và để ghi vào nhật ký phải đúng sàn mình đánh, không
phải số "xấp xỉ" từ sàn khác.

- Trên Hyperliquid, các coin dùng cặp USDC vĩnh viễn (perp), ví dụ `BTC/USDC:USDC`,
  `HYPE/USDC:USDC`. App tự dựng đúng ký hiệu này.
- **Funding Hyperliquid trả MỖI GIỜ (1h)** — khác các sàn perp khác trả mỗi 8h. Điều
  này được tính đúng khi quy đổi ra %/năm (xem mục "Funding" bên dưới).

### Fallback khi Hyperliquid không vào được
Nếu mạng chặn Hyperliquid, app **tự fallback theo thứ tự Bybit → Binance → OKX** (các
sàn này funding 8h). Dashboard hiển thị tên nguồn đang dùng (vd "nguồn: hyperliquid").
Có thể ép 1 sàn bằng biến môi trường `DATA_EXCHANGE` (vd `DATA_EXCHANGE=hyperliquid`).

Lưu ý: coin **HYPE chỉ có trên Hyperliquid** — nếu phải fallback sang sàn proxy, HYPE
có thể không hiển thị.

Dữ liệu giá & funding là **công khai** — không cần API key, không cần đăng nhập.

## Các coin theo dõi
**BTC, ETH, SOL, HYPE** (4 coin). Nhãn hiển thị/lưu nhật ký giữ dạng quen thuộc
(`BTC/USDT`, `ETH/USDT`, `SOL/USDT`, `HYPE/USDC`) để không phá các lệnh đã ghi trước
đó, nhưng **số liệu phía sau lấy từ Hyperliquid**.

> Lưu ý lịch sử: HYPE là coin mới, dữ liệu chỉ có từ khoảng **cuối 2024** trở đi — đủ
> để tính EMA/RSI/biên 30 ngày, nhưng các thống kê dài hạn (percentile 1 năm) sẽ ngắn
> hơn BTC/ETH/SOL.

## Các loại dữ liệu

| Loại | Free? | Lịch sử dài? | Thực tế |
|---|---|---|---|
| Giá (OHLCV) | ✅ | ✅ | Dùng ngay (nến 4H/1D cho HUD; 1H/15m cho nghiên cứu) |
| Funding rate | ✅ | ✅ | Dùng ngay (Hyperliquid **1h/lần**; sàn proxy 8h/lần) |
| Open Interest | ⚠️ | ❌ (~30 ngày free) | Muốn lịch sử dài phải trả phí hoặc tự thu thập |
| Liquidation | ❌ | ❌ | Hầu hết trả phí |

→ Hệ thống dựa trên **giá + funding** (hai nguồn vừa free vừa có lịch sử sâu). OI /
liquidation vẫn đang chờ nguồn (trả phí hoặc tự thu thập forward).

**Funding nghĩa là gì:** phí định kỳ giữa long và short trên hợp đồng vĩnh viễn.
Funding **dương** = long trả short (đám đông nghiêng long). Funding **âm** = short trả
long (đám đông nghiêng short → bối cảnh dễ squeeze lên).

**Quy đổi funding ra %/năm:** `rate_mỗi_kỳ × số_kỳ_mỗi_ngày × 365`. Số kỳ mỗi ngày =
`24 / chu_kỳ_giờ`. Hyperliquid (1h) → ×24×365; sàn proxy (8h) → ×3×365. Nhờ vậy số
%/năm đúng dù funding Hyperliquid mỗi kỳ nhỏ hơn ~8 lần.

## Độ tươi & cache
- App online **tự kéo dữ liệu thật mỗi 5 phút**.
- Nút "⟳ Refresh data" để kéo ngay (hiện trạng thái "đang làm mới ~30-60s").
- Dữ liệu cache dạng Parquet để không spam API.

## Chống "nhìn trước tương lai" (trong nghiên cứu)
- Tín hiệu chỉ tính **sau khi nến đóng**; lệnh khớp ở **giá mở cửa nến kế tiếp**.
- Ngưỡng percentile funding tính bằng **cửa sổ chỉ-dùng-quá-khứ** (expanding).

## Lưu ý lỗi đã sửa (còn đúng từ ver2)
Code tải dữ liệu cũ dừng phân trang sớm với sàn giới hạn nến/lần → từng hiển thị **giá
cũ sai**. Đã sửa: phân trang tới hiện tại (áp dụng cho mọi sàn, kể cả Hyperliquid trả
500 bản ghi/trang). Bài học: luôn kiểm chứng số trước khi tin.
