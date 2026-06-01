# Hệ thống lấy dữ liệu như thế nào

## Nguồn dữ liệu: CCXT + Binance

Hệ thống dùng thư viện **CCXT** (chuẩn ngành) để lấy dữ liệu công khai từ sàn **Binance** qua internet. Toàn bộ chạy trên máy người dùng (hoặc server Railway), không qua máy chủ trung gian nào khác.

Quan trọng: dữ liệu giá và funding là **công khai** — không cần tài khoản, không cần API key, không cần đăng nhập. (Chỉ khi muốn *đặt lệnh thật* mới cần API key — mà hệ thống này KHÔNG đặt lệnh.)

## Các loại dữ liệu

### 1. Giá (OHLCV) — dễ, miễn phí, lịch sử sâu
- OHLCV = Open/High/Low/Close/Volume, dạng **nến** (candle), không phải theo giây.
- Các khung dùng: 1D và 4H (cho dashboard), thêm 1H/15m (cho nghiên cứu).
- Lấy được từ 2023 đến hiện tại.
- Coin: BTC, ETH, SOL (từ Binance). HYPE phải lấy riêng từ Hyperliquid (Binance không có).

### 2. Funding rate — dễ, miễn phí, lịch sử sâu
- Funding là khoản phí định kỳ giữa người long và short trên hợp đồng vĩnh viễn (perpetual). Binance trả funding **mỗi 8 giờ**; Hyperliquid **mỗi 1 giờ**.
- Funding âm = phe short đông, phải trả tiền cho phe long (bối cảnh dễ bị squeeze lên).
- Funding dương = phe long đông.
- Lấy qua hàm `fetch_funding_rate_history` của CCXT, từ 2023 đến nay.

### 3. Open Interest (OI) — KHÓ, gần như không có lịch sử miễn phí
- OI = tổng số hợp đồng đang mở.
- Binance public chỉ cho OI **hiện tại** và lịch sử **~30 ngày**. Muốn 2-3 năm phải **trả phí** (Coinglass, Amberdata) hoặc **tự thu thập từ bây giờ trở đi**.

### 4. Liquidation (thanh lý) — KHÓ NHẤT
- Dữ liệu thanh lý lịch sử chuẩn gần như đều **trả phí** (Coinglass, Hyblock, Amberdata).

### Bảng tóm tắt
| Loại | Free? | Lịch sử dài? | Thực tế |
|---|---|---|---|
| Giá (OHLCV) | ✅ | ✅ | Dùng ngay |
| Funding | ✅ | ✅ | Dùng ngay |
| Open Interest | ⚠️ | ❌ (~30 ngày) | Trả phí hoặc tự thu thập |
| Liquidation | ❌ | ❌ | Hầu hết trả phí |

→ Vì vậy hệ thống hiện tại chỉ dựa trên **giá + funding** (hai nguồn duy nhất vừa miễn phí vừa có lịch sử sâu).

## Lưu trữ (cache)

Dữ liệu tải về được lưu dạng file **Parquet** trên đĩa (thư mục `data_cache/`). Lần sau đọc từ cache cho nhanh, không gọi lại API liên tục.

## Độ tươi của dữ liệu (data freshness)

- Bản web (deploy Railway) **tự kéo dữ liệu thật từ Binance mỗi 5 phút** (scheduler chạy trong tiến trình).
- Trang web cũng tự làm mới hiển thị mỗi 5 phút.
- Có nút "⟳ Refresh data" để kéo ngay tức thì.
- Dữ liệu tươi tới nến gần nhất (trễ vài phút).

## Chống "nhìn trước tương lai" (look-ahead) trong nghiên cứu

Khi backtest, hệ thống tuân thủ kỷ luật nghiêm:
- Tín hiệu chỉ tính **sau khi nến đóng**.
- Lệnh chỉ khớp ở **giá mở cửa của nến kế tiếp** (không dùng giá đóng của nến tín hiệu).
- Ngưỡng percentile của funding tính bằng **cửa sổ chỉ-dùng-quá-khứ** (expanding), không dùng toàn bộ lịch sử (tránh "biết trước").

Đây là điều phân biệt nghiên cứu nghiêm túc với backtest ảo: nếu dùng dữ liệu tương lai, con số đẹp giả tạo và sẽ sập khi giao dịch thật.
