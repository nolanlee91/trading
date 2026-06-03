# Hướng dẫn sử dụng Trader Decision Assistant (chi tiết)

> Tài liệu này bám đúng quy tắc trong code (`app.py`). Mọi ngưỡng số đều là ngưỡng
> thật hệ thống đang dùng. Đọc một lần để hiểu app "nghĩ" gì, rồi dùng phần cuối
> (Quy trình + Kịch bản) làm cẩm nang hằng ngày.

**Nguyên tắc nền — đọc trước khi tin bất cứ con số nào:**
Đây là **HUD hỗ trợ quyết định**, KHÔNG phải bot, KHÔNG phải tín hiệu mua/bán. Mọi tín
hiệu thị trường trong app đều **edge yếu** (đã kiểm chứng — xem `notebooklm/ver3/04`).
Giá trị thật của app nằm ở: (1) ép kỷ luật nhìn đủ yếu tố, (2) cảnh báo thời điểm tệ,
(3) **nhật ký để tìm edge CÁ NHÂN của bạn**. App không bao giờ nói "nên mua/bán" —
nó chỉ bày bối cảnh, bạn tự quyết.

---

# PHẦN 1 — Ý NGHĨA TỪNG CHỈ SỐ

## 1.1. Nền tảng: dữ liệu lấy từ đâu
- Nguồn chính **Hyperliquid** (đúng sàn bạn trade thật) — cả giá lẫn funding. Fallback
  Bybit→Binance→OKX nếu Hyperliquid không vào được.
- 4 coin: **BTC, ETH, SOL, HYPE** (HYPE chỉ có trên Hyperliquid).
- Nến dùng để phân tích: **4H** (khung chính ra bias) và **1D** (khung xác nhận).
- Tự kéo lại mỗi 5 phút. Tín hiệu tính trên nến đã/đang chạy; quyết định là của bạn.

## 1.2. Trend 4H và Trend 1D (xương sống)
Tính bằng **xếp tầng 3 đường EMA** (trung bình động hàm mũ) 20/50/200 trên từng khung:

| Trạng thái | Điều kiện | Hiển thị UI |
|---|---|---|
| **bullish** (tăng) | EMA20 > EMA50 > EMA200 | mũi tên ▲ xanh (`up`) |
| **bearish** (giảm) | EMA20 < EMA50 < EMA200 | mũi tên ▼ đỏ (`down`) |
| **mixed** (đan xen) | còn lại (EMA dính chùm) | ▬ vàng (`flat`) |

- **4H quyết định BIAS** (chiều được phép đánh).
- **1D dùng để XÁC NHẬN**: nếu 1D ngược chiều bias → cộng điểm rủi ro (mục 1.4).
- Ý tưởng: chỉ đánh thuận trend lớn, không bắt dao rơi/đu đỉnh ngược xu hướng.

## 1.3. BIAS — chiều được phép đánh
Suy ra trực tiếp từ trend 4H:
- 4H bullish → **BIAS = LONG** (chỉ xét mua).
- 4H bearish → **BIAS = SHORT** (chỉ xét bán).
- 4H mixed → **BIAS = NEUTRAL = ĐỨNG NGOÀI** (không có lợi thế rõ).

Toàn bộ Checklist và Risk Score **xoay theo bias này**. NEUTRAL nghĩa là "thị trường
chưa cho kèo rõ" — mặc định nên đứng ngoài.

## 1.4. RISK SCORE — điểm rủi ro của THỜI ĐIỂM vào lệnh (0–9)
KHÔNG phải dự báo thắng/thua. Là "vào lệnh **theo bias** ngay bây giờ có rủi ro về thời
điểm không". Cộng điểm các yếu tố BẤT LỢI:

**Khi BIAS = LONG**, cộng nếu:
- Funding percentile **≥ 95** → **+2** (đám đông long quá đông, dễ bị xả)
- RSI **≥ 75** → **+2** (quá mua)
- Giá **≥ 2 ATR TRÊN** EMA20 → **+3** (căng lên, dễ hồi xuống)
- Trend 1D **bearish** (ngược bias) → **+2**

**Khi BIAS = SHORT**, cộng nếu:
- Funding percentile **≤ 5** → **+2** (đám đông short quá đông → dễ squeeze LÊN)
- RSI **≤ 25** → **+2** (quá bán → dễ nảy lên)
- Giá **≤ −2 ATR DƯỚI** EMA20 → **+3** (căng xuống, dễ hồi lên)
- Trend 1D **bullish** (ngược bias) → **+2**

**Khi NEUTRAL:** mặc định **6** (không có bias → rủi ro cao theo định nghĩa).

**Phân loại (band) + màu UI:**
| Điểm | Band | Màu | Nghĩa |
|---|---|---|---|
| 0–2 | Bình thường (`low`) | xanh | Không có yếu tố bất lợi rõ → thời điểm tương đối ổn |
| 3–5 | Cẩn thận (`medium`) | vàng | Có vài yếu tố bất lợi → giảm cỡ / chờ điểm đẹp hơn |
| 6–9 | Rủi ro cao (`high`) | đỏ | Nhiều yếu tố bất lợi hoặc không có bias → nên tránh |

App kèm danh sách **"lý do"** (risk_why) liệt kê đúng yếu tố nào đang cộng điểm. Risk
cao KHÔNG có nghĩa "cấm vào" — nghĩa là "nếu vào, biết mình đang vào lúc căng".

## 1.5. CHECKLIST — 5 điều kiện CHẤT LƯỢNG để vào lệnh thuận trend
Hiển thị ✓/✗ và đếm "X/5 thuận lợi". Bộ điều kiện ĐỔI theo bias.

**BIAS LONG — 5 điều kiện:**
1. **4H bullish** — trend khung 4H đang tăng.
2. **1D không bearish** — khung ngày không ngược chiều.
3. **Giá gần/dưới EMA20** (`dist_atr < 0.5`) — mua khi giá *hồi về* (pullback), không đu đỉnh.
4. **RSI không quá nóng** (`< 70`) — còn dư địa.
5. **Funding không đông long** (`percentile < 85`) — đám đông chưa dồn hết một bên.

**BIAS SHORT — 5 điều kiện (đối xứng):**
1. **4H bearish** — trend 4H đang giảm.
2. **1D không bullish** — khung ngày không ngược chiều.
3. **Giá gần/trên EMA20** (`dist_atr > -0.5`) — bán khi giá *hồi lên kháng cự*, KHÔNG đuổi bán khi đã căng xuống.
4. **RSI không quá bán** (`> 30`) — tránh bán vùng dễ nảy.
5. **Funding không đông short** (`percentile > 15`) — tránh short khi quá nhiều người đã short (rủi ro squeeze).

**Đọc tally:** "4/5" = 4 đúng, 1 sai. **Điều kiện SAI quan trọng hơn con số** — nó cho
biết đang thiếu gì. Ví dụ short 4/5 mà thiếu điều kiện 3 → hướng đúng nhưng *giá đang
căng xuống, chưa phải điểm short đẹp* → nên chờ hồi lên EMA20.

## 1.6. Các chỉ số NGỮ CẢNH (không cộng điểm, để hiểu bức tranh)

**Giá vs EMA20 (`dist_atr`)** — khoảng cách giá tới EMA20 đo bằng **số lần ATR**:
- `+1.5 ATR` = căng lên trên; `−1.5 ATR` = căng xuống dưới; gần `0` = sát EMA20 (vùng pullback đẹp).
- Đây là biến dùng cho điều kiện checklist #3 và risk (±2 ATR).

**RSI (14, khung 4H)** — động lượng 0–100: `>70` quá mua, `<30` quá bán, `~45–65` trung tính.

**ATR% (`atr_pct`)** — độ biến động = ATR / giá. Dùng để **ước lượng cỡ lệnh & đặt cắt
lỗ** theo bội số ATR (vd SL = 1.5×ATR), thay vì số tiền cứng — vì ATR tự co giãn theo
biến động. Coin ATR% cao (vd HYPE) = biên dao động lớn → cần SL rộng hơn / size nhỏ hơn.

**Funding** — phí định kỳ giữa long và short trên hợp đồng vĩnh viễn:
- **Dương** = long trả short (đám đông nghiêng long). **Âm** = short trả long (đám đông nghiêng short).
- Hyperliquid trả **mỗi giờ (1h)**; sàn proxy 8h. App hiển thị funding/kỳ + **quy năm**
  (`%/năm = rate × 24/chu_kỳ_giờ × 365`).

**Funding percentile** — funding hiện tại đứng đâu so với **365 ngày** qua (cửa sổ chỉ
dùng quá khứ): `>90` đám đông long cực đông; `<10` đám đông short cực đông; `~50` trung
bình. **Đây là biến dùng trong risk & checklist**, quan trọng hơn con số funding tuyệt đối.

**Funding velocity** — funding đang tăng hay giảm (so trung bình ~3 ngày gần nhất với 3
ngày trước). UI hiện dạng số (đổi annualized giữa 2 cửa sổ). Đổi nhanh = đám đông đang
ùa vào một chiều.

**Volume 1D (`vol_ratio`)** — khối lượng ngày so **trung bình 20 ngày**: `×1.0` = bằng
TB; `×0.4` = chợ ế; `≥×2` = sôi động bất thường (app bật cờ).

**Biên 30 ngày (`to_high` / `to_low`)** — giá đứng đâu trong biên cao–thấp 30 ngày:
- `to_high` = % so ĐỈNH 30N (âm = dưới đỉnh; vd −3% là sát đỉnh).
- `to_low` = % so ĐÁY 30N (dương = trên đáy; vd +1% là sát đáy).
- Sát đỉnh → coi chừng kháng cự; sát đáy → coi chừng hỗ trợ/đảo chiều.

**Corr BTC (`corr_btc`)** — mức coin đi cùng nhịp BTC (tương quan lợi suất ngày 30 phiên):
- BTC = `1.0`. ETH/SOL thường `~0.85–0.9`. HYPE thấp hơn (`~0.5`) = đi riêng.
- Ý nghĩa: ôm nhiều lệnh corr cao = thực ra **đặt cùng một cược vào BTC** (rủi ro tập trung).

**Return 7 ngày (`ret7`)** — % thay đổi giá 7 ngày, momentum trung hạn.

## 1.7. FLAGS — cờ cảnh báo tự bật
App tự gắn cờ khi gặp bối cảnh đáng chú ý:
- Funding percentile **≤ 10** → "Funding cực ÂM (đông short) — bối cảnh squeeze LÊN".
- Funding percentile **≥ 90** → "Funding cực DƯƠNG (đông long) — rủi ro flush XUỐNG".
- `dist_atr ≥ 1.5` → "Giá căng trên EMA20 — chờ hồi hơn đuổi".
- `dist_atr ≤ −1.5` → "Giá dưới EMA20 — quá bán ngắn hạn".
- `vol_ratio ≥ 2` → "Volume 1D bất thường".
- `to_high ≥ −2` → "Sát ĐỈNH 30 ngày — coi chừng kháng cự".
- ngược lại `to_low ≤ 2` → "Sát ĐÁY 30 ngày — coi chừng hỗ trợ/đảo chiều".

---

# PHẦN 2 — CÁCH KẾT HỢP CÁC CHỈ SỐ

Thứ tự đọc một coin (từ thô đến tinh). Đừng nhìn lẻ từng chỉ số — đọc theo tầng:

### Bước 1 — BIAS trả lời "được đánh chiều nào?"
- LONG/SHORT → có chiều để xét. NEUTRAL → **mặc định đứng ngoài**, đọc tiếp chỉ để theo dõi.

### Bước 2 — CHECKLIST trả lời "đã đủ điều kiện CHẤT LƯỢNG chưa?"
- 4–5/5 → bối cảnh thuận. 0–2/5 → hướng có thể đúng nhưng **điểm vào chưa đẹp**.
- Luôn xem **điều kiện nào sai** để biết thiếu gì (thường là #3 — giá chưa pullback/hồi về EMA20).

### Bước 3 — RISK SCORE trả lời "THỜI ĐIỂM có căng không?"
- Bình thường → thời điểm ổn. Cẩn thận → giảm size/chờ. Rủi ro cao → tránh.
- Đọc danh sách "lý do" để biết căng vì cái gì (funding/RSI/giá căng/1D ngược).

### Bước 4 — FLAGS + NGỮ CẢNH tinh chỉnh
- Sát đỉnh/đáy 30N, volume bất thường, funding cực đoan → các "ổ gà" cần để ý.
- ATR% → quyết định **cỡ lệnh & SL** (biến động cao thì nhỏ size, SL rộng).
- Corr BTC → kiểm tra mình có đang gom rủi ro về một hướng BTC không.

### Bước 5 — RA QUYẾT ĐỊNH (của bạn) → GHI JOURNAL
- Vào hay không, size bao nhiêu, SL/TP ở đâu — bạn quyết. Rồi **ghi lệnh** để app lưu bối cảnh.

### Quy tắc kết hợp thực dụng
- **"Kèo đẹp" điển hình:** Bias rõ (LONG/SHORT) **+** Checklist 4–5/5 **+** Risk Bình thường
  **+** không cờ cực đoan **+** giá gần EMA20 (pullback). Đây là lúc bối cảnh ủng hộ nhất.
- **"Đúng hướng nhưng chờ":** Bias rõ + Checklist cao **nhưng** điều kiện #3 sai (giá căng)
  → chờ giá hồi về EMA20 thay vì đuổi.
- **"Tránh":** NEUTRAL, hoặc Risk cao, hoặc nhiều cờ cực đoan (funding ≥90 + sát đỉnh +
  volume bất thường) → đứng ngoài, dù "cảm giác" muốn vào.
- **Mâu thuẫn khung:** 4H bullish nhưng 1D bearish → bias long nhưng bị +2 risk; ưu tiên
  size nhỏ hoặc bỏ qua, vì hai khung không đồng thuận.
- **Funding là CROWDING, không phải HƯỚNG:** funding cao = nhiều đòn bẩy một bên → rủi ro
  đảo chiều, KHÔNG phải "tín hiệu bán". Dùng để tránh vào lúc đám đông đã chật.

> Nhắc lại: các tín hiệu này **edge yếu**. Kết hợp chúng giúp **lọc bỏ kèo tệ** tốt hơn là
> giúp "tìm kèo thắng". Edge thật đến từ Journal (Phần 3.B) sau khi đủ lệnh.

---

# PHẦN 3 — CÁCH SỬ DỤNG APP

Giao diện có **4 màn**, chuyển bằng thanh điều hướng dưới đáy: **Market · Journal ·
Snapshots · Assistant**. App tự kéo data mỗi 5 phút; nút **Refresh** để kéo ngay.

> Nếu thấy nhãn **"mock data"** ở góc trạng thái → backend chưa kết nối được, app đang
> hiện dữ liệu GIẢ để demo giao diện. Đừng ra quyết định trên mock; bấm Refresh hoặc
> kiểm tra server.

## A. Màn MARKET (chính)
- **Ma trận trên cùng:** mỗi coin một dòng gọn — ticker, giá, BIAS, thanh Risk (9 vạch)
  + điểm risk. Để liếc nhanh "4 coin đang thế nào".
- **Card chi tiết từng coin:** giá + return 7D, BIAS, cặp trend 4H/1D (mũi tên), các ô
  chỉ số (Funding pctl, RSI, Vol ratio, Dist EMA20, Funding vel, To 30D High/Low),
  thanh Risk + band + danh sách lý do, **checklist 5 dòng** (✓/✗), khối số liệu thô
  (Price, Funding/kỳ, Funding ann, Funding pctl, ATR%, BTC corr, Risk score), và **flags**.
- Dùng đúng quy trình Phần 2 trên từng card.

## B. Màn JOURNAL (quan trọng nhất cho edge cá nhân)
Đây là nơi tạo ra giá trị dài hạn của app. **Ghi MỌI lệnh**, kể cả lệnh xấu/FOMO — chính
lệnh thua mới lộ bối cảnh nên tránh.

**B1. Ghi lệnh đang mở (chuẩn nhất):**
1. Chọn coin, chọn Long/Short, gõ **lý do/luận điểm vào**.
2. Bấm ghi → app **tự chụp toàn bộ bối cảnh tại đúng thời điểm vào** (trend, funding
   pctl, RSI, dist EMA, volume, biên 30N, corr BTC) và lưu kèm lệnh.
   → Vì context tự chụp, hãy ghi **ngay khi vào lệnh thật**, đừng ghi muộn.

**B2. Đóng lệnh:** ở lệnh đang mở, bấm **Close trade** → nhập **giá thoát** → app tự tính
PnL% (đúng công thức long/short).

**B3. Ghi lệnh đã đóng / quá khứ (nhập tay):** form "lệnh đã đóng" — nhập coin, side, giá
vào, giá ra → lưu thẳng. Dùng cho lệnh ngoài app hoặc lệnh cũ. (Context lúc nhập là context
*hiện tại*, nên kém chính xác hơn B1 — ưu tiên B1 cho lệnh mới.)

**B4. Xem EDGE cá nhân (khối thống kê):**
- Tổng quan: tổng lệnh, **win rate**, **PnL trung bình**, số lệnh mở/đóng.
- **Best/Worst theo từng nhóm:** Funding / Trend regime / RSI / Volume — cho biết bạn
  thắng đậm nhất và thua nặng nhất ở bối cảnh nào.
- ⚠️ **Cần đủ lệnh mới tin** (mẫu nhỏ là nhiễu, không phải edge). Vài chục lệnh trở lên
  mới bắt đầu có ý nghĩa. Đây là điểm khác biệt cốt lõi: tìm "khi nào CHÍNH BẠN thắng",
  không phải tìm tín hiệu thần kỳ.

> Lưu ý dữ liệu: các trường ngữ cảnh mới (volume/biên 30N/corr) chỉ có với lệnh ghi từ
> bản mới trở đi; lệnh cũ để trống (nhóm "?") — bình thường.

## C. Màn SNAPSHOTS (ảnh chụp bối cảnh hằng ngày)
- App tự chụp bối cảnh cả 4 coin **mỗi ngày, kể cả ngày bạn KHÔNG vào lệnh** (1 ảnh/ngày).
- Dòng thời gian hiện mỗi ngày: regime (bull/bear/mixed), tóm tắt số long/short, và bias
  + risk từng coin.
- **Mục đích:** so "hôm mình đánh" với "hôm mình bỏ qua" — tránh chỉ nhìn ngày-có-lệnh
  (thiên lệch). Có bộ lọc số ngày (7/30...).

## D. Màn ASSISTANT (trợ lý Gemini)
- Hỏi tự nhiên (vd "bối cảnh SOL thế nào?", "vì sao BTC risk thấp?") → Gemini trả lời
  **dựa trên dữ liệu thật của HUD**, có ràng buộc trung thực.
- Có sẵn vài câu gợi ý bấm nhanh.
- **Giới hạn:** Gemini chỉ *giải thích bối cảnh*, KHÔNG đưa lệnh mua/bán, KHÔNG bịa xác
  suất. Nó không làm tín hiệu chính xác hơn — edge vẫn yếu.

---

# PHẦN 4 — QUY TRÌNH HẰNG NGÀY (cẩm nang nhanh)

1. **Mở Market**, liếc ma trận 4 coin: coin nào có Bias rõ + Risk thấp?
2. Với coin quan tâm, đọc card theo 5 bước Phần 2: Bias → Checklist → Risk → Flags/ngữ
   cảnh → quyết định.
3. Nếu **không có kèo đẹp** (NEUTRAL / Risk cao / checklist thấp / cờ cực đoan) → **đứng
   ngoài**. Kiên nhẫn thường là quyết định đúng.
4. Nếu vào lệnh thật → **ghi Journal ngay** (để app chụp context chuẩn). Đặt SL theo ATR.
5. Khi đóng lệnh → bấm Close, nhập giá thoát.
6. Định kỳ (mỗi vài tuần) mở **Journal → thống kê** xem best/worst bucket: bối cảnh nào
   mình nên đánh nhiều hơn, bối cảnh nào nên tránh. Đó là edge cá nhân đang lớn dần.

---

# PHẦN 5 — NHỮNG ĐIỀU PHẢI NHỚ (kỷ luật)

- **App không bảo bạn mua/bán.** Nó bày bối cảnh; bạn chịu trách nhiệm size, SL, đòn bẩy.
- **Tín hiệu thị trường = edge yếu.** Dùng để *lọc kèo tệ*, không phải *bảo đảm kèo thắng*.
- **Funding/percentile = crowding, không phải hướng.**
- **Risk Score = rủi ro thời điểm, không phải dự báo thắng/thua.**
- **Mẫu nhỏ là nhiễu.** Đừng kết luận edge cá nhân khi mới vài lệnh.
- **Ghi mọi lệnh trung thực**, nhất là lệnh xấu — đó là dữ liệu quý nhất.
- **Đứng ngoài là một quyết định hợp lệ** và thường là quyết định tốt.

> Tài liệu liên quan: `notebooklm/ver3/` (bản cho NotebookLM), `TASKS.md` (tiến độ),
> `ARCHITECTURE.md` / `PRD.md` (thiết kế hệ thống).
