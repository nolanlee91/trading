# Các chỉ số trên HUD và ý nghĩa chi tiết (ver3)

File này giải thích CHÍNH XÁC từng con số hiển thị trên dashboard nghĩa là gì, dựa
trên đúng quy tắc trong code (`app.py`). Đọc để hiểu "Risk 5", "Bias", "checklist 4/5",
và các chỉ số ngữ cảnh nghĩa là gì.

---

## 1. BIAS — đánh theo chiều nào

**Bias xác định CHÍNH dựa vào trend khung 4H** (xếp tầng EMA20/50/200 trên nến 4 giờ):

| Trend 4H | Điều kiện EMA | Bias |
|---|---|---|
| bullish | EMA20 > EMA50 > EMA200 | **LONG** (chỉ xét mua thuận trend) |
| bearish | EMA20 < EMA50 < EMA200 | **SHORT** (chỉ xét bán thuận trend) |
| mixed | EMA dính chùm/đan xen | **ĐỨNG NGOÀI** (không có lợi thế rõ) |

Nguyên tắc nền: *đừng đánh ngược trend lớn*. Vì vậy mọi chỉ số khác (Risk, Checklist)
đều xoay theo Bias này. Trend 1D (ngày) KHÔNG quyết định bias, mà dùng để **xác nhận**:
nếu 1D ngược chiều bias thì bị cộng điểm rủi ro (xem mục 2).

→ Trả lời ngắn: **Bias chính dựa vào trend EMA khung 4H.**

---

## 2. RISK SCORE — "Risk vào lệnh N" nghĩa là gì

Là **điểm rủi ro nếu VÀO LỆNH THEO BIAS ngay lúc này**. Thang 0-9, càng cao càng nên
khoan/giảm cỡ. Tính bằng cách cộng điểm các yếu tố BẤT LỢI cho hướng đang xét:

**Khi Bias = LONG** (uptrend), cộng điểm nếu:
- Funding ≥ 95 percentile → **+2** (đám đông long quá đông, dễ bị xả)
- RSI ≥ 75 → **+2** (quá mua)
- Giá ≥ 2 ATR TRÊN EMA20 → **+3** (căng lên, dễ hồi xuống)
- Trend 1D bearish (ngược bias) → **+2**

**Khi Bias = SHORT** (downtrend), cộng điểm nếu:
- Funding ≤ 5 percentile → **+2** (đám đông short quá đông → dễ squeeze LÊN)
- RSI ≤ 25 → **+2** (quá bán → dễ nảy lên)
- Giá ≤ -2 ATR DƯỚI EMA20 → **+3** (căng xuống, dễ hồi lên)
- Trend 1D bullish (ngược bias) → **+2**

**Khi ĐỨNG NGOÀI:** mặc định **6** (không có bias → rủi ro cao).

**Phân loại (band):**
| Điểm | Nhãn | Ý nghĩa |
|---|---|---|
| 0-2 | Bình thường | Không có yếu tố bất lợi rõ → thời điểm vào tương đối ổn |
| 3-5 | Cẩn thận | Có vài yếu tố bất lợi → giảm cỡ lệnh / chờ điểm tốt hơn |
| 6+ | Rủi ro cao | Nhiều yếu tố bất lợi hoặc không có bias → nên tránh |

**Ví dụ "Risk vào lệnh 5":** nằm trong nhóm **Cẩn thận** — khoảng 2 yếu tố bất lợi cộng
lại (vd giá đang căng +2ATR (+3) và 1D ngược bias (+2) = 5). HUD kèm phần "lý do" liệt
kê đúng yếu tố nào cộng điểm. Risk 5 KHÔNG có nghĩa "cấm vào" — nghĩa là "vào lúc này
hơi rủi ro, cân nhắc giảm size hoặc chờ".

Lưu ý: Risk Score là rủi ro về **THỜI ĐIỂM vào lệnh**, không phải dự báo thắng/thua.

---

## 3. CHECKLIST — 5 điều kiện thuận lợi (theo Bias)

Hiển thị dạng ✓/✗ và đếm "X/5 thuận lợi". Bộ checklist ĐỔI theo bias:

### Bias LONG — 5 điều kiện
1. **4H bullish** — trend khung 4H đang tăng.
2. **1D không bearish** — khung ngày không ngược chiều.
3. **Giá gần/dưới EMA20 (pullback để mua)** — giá hồi về vùng EMA20 (dist < 0.5 ATR).
4. **RSI không quá nóng (< 70)** — còn dư địa, không mua đỉnh.
5. **Funding không đông long (< 85 percentile)** — đám đông chưa dồn hết về long.

### Bias SHORT — 5 điều kiện (đối xứng)
1. **4H bearish** — trend khung 4H đang giảm.
2. **1D không bullish** — khung ngày không ngược chiều.
3. **Giá gần/trên EMA20 (hồi lên kháng cự để bán)** — giá bật lên vùng EMA20
   (dist > -0.5 ATR), bán khi giá *hồi lên*, KHÔNG đuổi bán khi đã căng xuống.
4. **RSI không quá bán (> 30)** — chưa quá bán (tránh bán vùng dễ nảy).
5. **Funding không đông short (> 15 percentile)** — đám đông chưa dồn hết về short.

**Đọc tally:** "4/5 thuận lợi" = 4 điều kiện đúng, 1 sai. Điều kiện sai cho biết *đang
thiếu gì*.

---

## 4. Các chỉ số ngữ cảnh

| Chỉ số | Ý nghĩa | Cách đọc |
|---|---|---|
| **Trend 4H / 1D** | Xu hướng 2 khung (EMA stacking) | bullish=xanh, bearish=đỏ, mixed=vàng |
| **Giá vs EMA20** | Khoảng cách giá tới EMA20, đo bằng **ATR** | +1.5 ATR = căng lên; -1.5 = căng xuống; gần 0 = sát EMA |
| **RSI (4H)** | Động lượng (0-100) | >70 quá mua, <30 quá bán, 45-65 trung tính |
| **Funding** | Phí perp + quy năm | dương = long trả short; âm = short trả long |
| **Funding percentile** | Funding hiện tại đứng đâu so với 1 năm | >90 đám đông long cực đông; <10 đám đông short cực đông; ~50 trung bình |
| **Funding velocity** | Funding đang tăng hay giảm (so ~3 ngày gần nhất với 3 ngày trước) | đổi nhanh = đám đông đang ùa vào 1 chiều |
| **ATR%** | Độ biến động (ATR / giá) | để ước lượng cỡ lệnh & đặt SL |
| **Return 7 ngày** | % thay đổi giá 7 ngày | momentum trung hạn |

### Ba chỉ số ngữ cảnh MỚI ở ver3

**Volume 1D (×TB):** khối lượng ngày hiện tại so với **trung bình 20 ngày**.
- `×1.0` = bằng trung bình. `×0.4` = chợ ế (ít quan tâm). `×2.5` = sôi động bất thường.
- Volume cao bất thường (≥ ×2) → có sự kiện/biến động mạnh, cẩn thận với cú phá giá giả
  hoặc biến động lớn. App bật cờ "Volume 1D bất thường" khi ≥ ×2.

**Biên 30 ngày (cách đỉnh / cách đáy):** giá hiện tại đứng đâu trong **biên cao–thấp
30 ngày gần nhất**.
- *cách đỉnh* = % so với ĐỈNH 30N (số âm = đang ở dưới đỉnh; vd −5% là gần đỉnh).
- *cách đáy* = % so với ĐÁY 30N (số dương = đang ở trên đáy; vd +1% là sát đáy).
- Sát đỉnh → coi chừng kháng cự (long dễ bị chặn). Sát đáy → coi chừng hỗ trợ / đảo
  chiều (short muộn dễ bị nảy). App bật cờ khi sát đỉnh (≥ −2%) hoặc sát đáy (≤ +2%).

**Tương quan BTC (corr):** mức độ giá coin **đi cùng nhịp BTC** (tương quan lợi suất
ngày, 30 phiên gần nhất).
- BTC với chính nó = **1.0**. ETH/SOL thường **~0.85–0.9** (đi rất sát BTC).
- Số **thấp** (vd HYPE ~0.5) = coin đi *riêng*, ít phụ thuộc BTC → cơ hội/rủi ro riêng
  của coin đó, không thể "đọc BTC để đoán".
- Ý nghĩa thực dụng: nếu đang ôm nhiều lệnh corr cao với BTC, thực chất đang **đặt cùng
  một cược vào BTC** (rủi ro tập trung). Coin corr thấp giúp đa dạng hơn.

### ATR là gì
ATR (Average True Range) = biên dao động trung bình mỗi nến. Dùng để: đo "căng" (giá
cách EMA bao nhiêu ATR), đặt mục tiêu/SL theo bội số ATR (vd SL = 1.5×ATR), thay vì
số tiền cố định — vì ATR tự co giãn theo độ biến động.

---

## 5. Tinh thần đọc HUD
- Bias cho biết **chiều nên theo**; Checklist cho biết **đã đủ điều kiện chưa**; Risk
  cho biết **thời điểm có rủi ro không**; các chỉ số ngữ cảnh (volume, biên 30N, corr)
  cho biết **bức tranh xung quanh**.
- Tất cả là **ngữ cảnh hỗ trợ**, tín hiệu edge yếu (xem `04-do-dang-tin.md`). Quyết
  định và quản trị rủi ro là của người dùng.
