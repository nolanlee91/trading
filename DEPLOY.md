# Deploy Swing Dashboard lên Railway

Web service 1-process: FastAPI vừa serve trang HTML vừa serve API, scheduler trong
process tự refresh data mỗi sáng 6:00 UTC. Mở từ điện thoại được.

## File liên quan
- `app.py` — web service (FastAPI + APScheduler).
- `Procfile` — lệnh chạy: `uvicorn app:app --host 0.0.0.0 --port $PORT`.
- `.python-version` — pin Python 3.12 cho Nixpacks.
- `requirements.txt` — deps (Railway tự `pip install`).
- `.gitignore` — bỏ .venv, data_cache, reports khỏi repo.

## Cách 1 — Railway CLI (nhanh)
```bash
cd trading-brain
git init && git add -A && git commit -m "swing dashboard"
railway login
railway init            # tạo project mới
railway up              # build + deploy
railway domain          # tạo URL public để mở trên điện thoại
```

## Cách 2 — GitHub
1. Push thư mục `trading-brain/` lên một repo GitHub.
2. Railway → New Project → Deploy from GitHub repo → chọn repo.
3. Railway tự nhận Python (qua requirements.txt) + Procfile.
4. Settings → Networking → Generate Domain để có URL.

## Kiểm tra sau deploy
- Mở `https://<domain>/` → thấy 3 card BTC/ETH/SOL.
- Lần đầu hiện "đang tải..." ~30-60s (đang kéo data), sau đó có số.
- `https://<domain>/api/dashboard` → JSON.
- Bấm "⟳ Refresh data" để kéo mới ngay; trang tự làm mới mỗi 5 phút.

## Trợ lý hỏi-đáp (Gemini)
- Cần biến môi trường `GEMINI_API_KEY` (lấy free tại Google AI Studio).
- Local (PowerShell): `$env:GEMINI_API_KEY='AIza...'` rồi chạy uvicorn trong cùng cửa sổ.
  Giữ lâu dài: `setx GEMINI_API_KEY "AIza..."` (mở terminal mới mới có hiệu lực).
- Railway: Variables → thêm `GEMINI_API_KEY`. Đổi model (tùy chọn): `GEMINI_MODEL`
  (mặc định `gemini-2.5-flash`).
- **Lỗi 429 "quota / check billing":** key đang ở **free-tier**. Model (2.0/2.5) KHÔNG
  quyết định free hay trả phí — **billing trên project của key mới quyết định**. Khắc phục:
  dùng đúng key thuộc project ĐÃ bật billing (cùng key với các app trả phí khác), hoặc
  bật billing cho project của key hiện tại tại Google AI Studio / Cloud Console. Nếu chỉ
  dính giới hạn theo phút thì đợi ~1 phút.
- KHÔNG commit key vào git. Prompt đã ràng buộc: Gemini chỉ dùng dữ liệu thật, không
  bịa dự báo, luôn nhắc quản trị rủi ro.

## Lưu ý
- Filesystem Railway là tạm: mỗi lần redeploy sẽ kéo lại data từ đầu (vài chục giây). OK.
- Scheduler kéo data thật mỗi 5 phút. Đổi nhịp ở `app.py` (`sched.add_job ... minutes=`).
- Giá/funding lấy từ sàn public (không cần API key). Binance hay bị chặn 451 ở mạng
  công ty/cloud → app **tự dò** Bybit → Binance → OKX, dùng sàn nào vào được. Ép 1 sàn
  bằng env `DATA_EXCHANGE=bybit`. (Symbol dùng định dạng chung của CCXT nên đổi sàn không
  cần sửa gì khác.)
- Muốn lưu lịch sử snapshot (để soi lại): thêm PostgreSQL của Railway sau (Phase tiếp).
## Journal — chọn 1 trong 2 nơi lưu

App tự nhận: **có `DATABASE_URL` → dùng PostgreSQL; không có → SQLite** (local).

**Cách 1 (KHUYÊN — dùng chung mọi thiết bị, 1 database): PostgreSQL**
1. Railway → project → **New → Database → Add PostgreSQL**.
2. Vào **service app** → Variables → thêm reference: `DATABASE_URL` = `${{Postgres.DATABASE_URL}}`
   (chọn từ gợi ý của Railway, trỏ tới Postgres vừa tạo).
3. Redeploy. App tự tạo bảng `trades` trong Postgres. Mở URL từ điện thoại/laptop nào
   cũng chung 1 journal, bền vĩnh viễn, không mất khi redeploy.

**Cách 2 (đơn giản, 1 instance): SQLite + Volume**
- Variables thêm `DB_PATH=/data/journal.db`; Settings → Volumes → mount `/data`.
- Đủ cho 1 mình dùng; nhưng Postgres bền & chuẩn hơn cho nhiều thiết bị.

> Lệnh đã ghi ở máy local nằm trong SQLite local, KHÔNG tự sang Postgres. Sau khi
> deploy Postgres, ghi lại trên app online (1 lệnh) hoặc nhờ chèn tay.
