# Kế hoạch chi tiết — Trading Brain

> **CẬP NHẬT 2026-06 — kế hoạch này ĐÃ thực hiện xong và dẫn tới pivot.**
> Toàn bộ Phase A→D đã chạy thật. Kết quả: mọi chiến lược cơ học đơn lẻ KHÔNG có
> edge bền thắng buy-and-hold (trend hòa/beta, short & regime tệ hơn, phân kỳ 15m
> cháy, funding-squeeze yếu). → Dự án **pivot sang Trader Decision Assistant (HUD)**.
> Trạng thái hiện tại + sản phẩm: xem `README.md`, `PRD.md`, `TASKS.md`.
> Đánh giá độ đáng tin từng tín hiệu: xem `notebooklm/04-do-dang-tin.md`.
> Phần dưới là kế hoạch GỐC (giữ lại làm bối cảnh phương pháp luận).

---

> File này để anh đọc và hiểu **em định làm gì, theo thứ tự nào, và vì sao**.
> Chưa code thêm gì cho tới khi anh duyệt hướng đi.

---

## 0. Mình đang ở đâu (đã xong)

Phase 1 harness đã chạy thật trên dữ liệu Binance 2023→nay:

| | BTC | ETH | SOL |
|---|---|---|---|
| Số lệnh | 511 | 483 | 467 |
| Win rate | 32.5% | 32.3% | 31.3% |
| Expectancy | −0.18R | −0.14R | −0.13R |
| Net return | −62% | −51% | −48% |
| vs Buy & Hold | thua | thua | thua |

**Kết luận:** setup "trend-continuation pullback" phiên bản thô **âm kỳ vọng**.
Đây là kết quả tốt — nó giết ảo tưởng *trước khi* mình tốn công xây UI/AI.

**Vì sao thua (giả thuyết, cần kiểm chứng):**
1. TP=2R, SL=1R → cần win rate > 33.3% mới hòa. Thực tế ~32% → dưới ngưỡng.
2. 511 lệnh = **overtrading**. Entry fire quá dễ → phí ăn mòn (BTC trả 3440$/10k vốn).
3. Long-only trong bull thị trường → về bản chất khó thắng mua-và-giữ.

Ba cái này là **3 nghi phạm**. Bước tiếp theo là điều tra chúng, không phải đoán.

---

## 1. Nguyên tắc xuyên suốt (để không tự lừa mình)

Đây là phần quan trọng nhất của cả dự án:

- **Không vặn tham số trên toàn bộ data rồi tin.** Mỗi lần mình thử 1 biến thể và
  giữ cái thắng = đang overfit. Càng thử nhiều, con số đẹp càng vô nghĩa.
- **Mọi thay đổi phải kiểm bằng walk-forward** (train quá khứ → test tương lai chưa thấy).
- **Đếm số biến thể đã thử.** Thử 20 setup rồi 1 cái "thắng" có thể chỉ là may.
- **Báo cáo trung thực:** luôn kèm số lệnh, phí, funding, so buy-and-hold, drawdown.
- **Edge phải sống out-of-sample**, không phải in-sample.

> Slogan: *"In-sample ai cũng thắng. Out-of-sample mới là thật."*

---

## 2. Lộ trình tổng (5 bước)

```
[A] Chẩn đoán baseline   ← LÀM TRƯỚC, rẻ, củng cố niềm tin số liệu
        ↓
[B] Cải thiện setup      ← siết entry / đổi logic, vẫn 1 cấu hình
        ↓
[C] Walk-forward         ← kiểm tra edge có sống out-of-sample không
        ↓
[D] Quyết: edge hay bỏ   ← cổng quyết định. Không edge → quay lại B hoặc đổi tiền đề
        ↓
[E] Mở rộng              ← scanner → AI giải thích → dashboard → on-chain
```

Mình **không** nhảy cóc. Mỗi bước có tiêu chí pass/fail rõ ràng.

---

## 3. Chi tiết từng bước

### [A] Chẩn đoán baseline (1 buổi) — *em đề xuất làm cái này trước*

Mục tiêu: hiểu **vì sao** thua, chưa sửa gì.

Em sẽ thêm vào `report.py` (không đụng logic strategy):

1. **PnL tách theo năm** (2023 / 2024 / 2025) → setup thua đều hay chỉ thua 1 regime?
2. **Phân bố R-multiple** → thua vì nhiều lệnh −1R nhỏ, hay vài lệnh thua to?
3. **PnL theo độ dài giữ lệnh** → lệnh giữ lâu có tệ hơn không?
4. **Equity curve xuất PNG** → nhìn hình dạng thua (đều đặn hay sốc).
5. **Re-confirm không look-ahead**: in vài lệnh mẫu (signal time vs entry time)
   để mắt thường xác nhận entry luôn ở nến SAU.

**Output:** một bảng + 1 ảnh equity curve mỗi coin.
**Tiêu chí:** không có tiêu chí pass/fail — đây là bước *hiểu*, không phải *sửa*.

---

### [B] Cải thiện setup (vài buổi)

Chỉ làm sau khi [A] cho biết thua ở đâu. Các hướng (chọn 1–2, không làm hết):

**B1. Siết entry, giảm overtrading**
- pullback chặt hơn (giảm `pullback_tol`)
- yêu cầu 3 EMA giãn đủ rộng (trend mạnh thật, không phải sideway)
- thêm filter volume > Volume MA
- chỉ vào khi 4H trend *vừa* chuyển bullish (bắt sóng sớm, không đu đỉnh)
- *Kỳ vọng:* < 150 lệnh, chất lượng cao hơn

**B2. Đổi quản lý lệnh**
- TP/SL khác (vd 1.5R, hoặc trailing theo ATR thay vì TP cố định)
- break-even stop sau khi đạt 1R
- *Lưu ý:* đây dễ overfit nhất → bắt buộc qua [C]

**B3. Đổi/ghép logic**
- thêm điều kiện cấu trúc (HH/HL) thay vì chỉ EMA
- lọc theo giờ trong ngày (crypto có giờ thanh khoản tốt/xấu)

**Tiêu chí pass [B]:** expectancy > 0 *và* đủ lệnh (≥100) trên TOÀN data.
Nhưng pass [B] **chưa đủ** — phải qua [C].

---

### [C] Walk-forward (Phase 2 cũ) — cổng chống tự lừa

Cách làm:
```
Cửa sổ trượt:
  Train 6 tháng  →  chọn tham số tốt nhất
  Test  3 tháng  →  áp tham số đó lên đoạn CHƯA THẤY, ghi kết quả
  Dịch tới 3 tháng, lặp lại
Cộng dồn tất cả đoạn Test = "kết quả out-of-sample"
```

**Tiêu chí pass [C]:**
- Out-of-sample expectancy > 0
- Ổn định qua nhiều cửa sổ (không phải 1 cửa sổ ăn may)
- Beat buy-and-hold *hoặc* drawdown thấp hơn hẳn (tùy mục tiêu ở [D])

Nếu in-sample đẹp mà out-of-sample sập → đó là overfit, **loại**.

---

### [D] Cổng quyết định

Đặt thẳng câu hỏi:
- Mình muốn **beat hold** hay muốn **equity mượt / ít drawdown**? (2 mục tiêu khác nhau)
- Edge đến từ **timing** (lúc nào vào) hay **sizing** (đặt bao nhiêu)?
- Có chấp nhận thêm **chiều short** / **regime filter** (chỉ trade khi đúng pha) không?

→ Nếu có ≥1 setup sống out-of-sample: sang [E].
→ Nếu không: quay lại [B] với ý tưởng khác, hoặc đổi tiền đề. **Không** ép xây tiếp.

---

### [E] Mở rộng (chỉ khi đã có edge thật)

Đúng thứ tự spec anh đã chốt:
1. **Scanner** — quét BTC/ETH/SOL realtime, output dựa trên expectancy đã chứng minh
   (KHÔNG dùng "AI confidence 82%").
2. **AI Analyst** — Claude chỉ *giải thích* setup + *cảnh báo rủi ro* + tóm tắt
   confluence. Không bịa xác suất thắng.
3. **Dashboard** (React) — chỉ làm sau cùng.
4. **HYPE / Hyperliquid** — bật trong config, test riêng (nguồn data + regime khác).
5. **On-chain** — funding history thật, OI, liquidation (Coinglass/Hyperliquid).

---

## 4. Việc kỹ thuật còn nợ (sẽ vá khi cần)

- [ ] Funding hiện là hằng số approximation → cắm `fetchFundingRateHistory` thật ở [E].
- [ ] Chưa test HYPE (cần verify ccxt hỗ trợ Hyperliquid OHLCV + funding hourly).
- [ ] Chưa có cơ chế chống "thử quá nhiều biến thể" — sẽ log số lần thử ở [C].
- [ ] Sizing hiện cố định 1% rủi ro/lệnh — có thể là biến nghiên cứu ở [D].

---

## 5. Em đề xuất

Bắt đầu bằng **[A] Chẩn đoán** — rẻ, không rủi ro overfit, và cho mình biết
3 nghi phạm ở mục 0 cái nào là thủ phạm chính. Sau khi nhìn equity curve + PnL
theo năm, mình mới quyết [B] đi hướng nào.

Anh đọc xong, bảo em "làm [A]" là em chạy. Hoặc anh muốn đổi thứ tự cũng được.
