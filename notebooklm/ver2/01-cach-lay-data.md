# Hệ thống lấy dữ liệu như thế nào (ver2)

## Nguồn: CCXT + tự dò sàn

Dùng thư viện **CCXT** lấy dữ liệu công khai. Vì **Binance hay bị chặn lỗi 451** ở một
số mạng (công ty/cloud), app **tự dò sàn vào được theo thứ tự Bybit → Binance → OKX**,
dùng sàn nào kết nối được. Dashboard hiển thị tên nguồn đang dùng (vd "nguồn: bybit").
Có thể ép 1 sàn bằng biến môi trường `DATA_EXCHANGE`.

Dữ liệu giá & funding là **công khai** — không cần API key, không cần đăng nhập.

## Các loại dữ liệu

| Loại | Free? | Lịch sử dài? | Thực tế |
|---|---|---|---|
| Giá (OHLCV) | ✅ | ✅ | Dùng ngay (nến 4H/1D cho HUD; 1H/15m cho nghiên cứu) |
| Funding rate | ✅ | ✅ | Dùng ngay (8h/lần trên Binance/Bybit) |
| Open Interest | ⚠️ | ❌ (~30 ngày free) | Muốn lịch sử dài phải trả phí hoặc tự thu thập |
| Liquidation | ❌ | ❌ | Hầu hết trả phí |

→ Hệ thống dựa trên **giá + funding** (hai nguồn vừa free vừa có lịch sử sâu).

**Funding nghĩa là gì:** phí định kỳ giữa long và short trên hợp đồng vĩnh viễn.
Funding **dương** = long trả short (đám đông nghiêng long). Funding **âm** = short trả
long (đám đông nghiêng short → bối cảnh dễ squeeze lên).

## Độ tươi & cache
- App online **tự kéo dữ liệu thật mỗi 5 phút**.
- Nút "⟳ Refresh data" để kéo ngay (hiện trạng thái "đang làm mới ~30-60s").
- Dữ liệu cache dạng Parquet để không spam API.

## Chống "nhìn trước tương lai" (trong nghiên cứu)
- Tín hiệu chỉ tính **sau khi nến đóng**; lệnh khớp ở **giá mở cửa nến kế tiếp**.
- Ngưỡng percentile funding tính bằng **cửa sổ chỉ-dùng-quá-khứ** (expanding).

## Lưu ý lỗi đã sửa (ver2)
Code tải dữ liệu cũ dừng phân trang sớm với sàn giới hạn ~200 nến/lần (Bybit/OKX) →
từng hiển thị **giá cũ sai** (vd ETH $4225 thay vì ~$1989). Đã sửa: phân trang tới
hiện tại. Bài học: luôn kiểm chứng số trước khi tin.
