"""
app.py — Trader Decision Assistant (HUD), không phải bot.

4 layer:
  L1 Context   : trend 4H/1D, funding percentile, RSI, distance EMA, ATR.
  L2 Risk Score: cộng điểm rủi ro khi VÀO LONG ngay bây giờ (0-2 bình thường,
                 3-5 cẩn thận, 6+ rủi ro cao).
  L3 Checklist : các điều kiện thuận lợi cho long, hiện ✓/✗ + tally X/5.
  L4 Journal   : ghi lệnh thật + context lúc vào + PnL -> sau 200-300 lệnh tìm
                 EDGE CÁ NHÂN (anh thắng/cháy ở bối cảnh nào). SQLite, bền.

Chạy local:  uvicorn app:app --reload
Railway:     uvicorn app:app --host 0.0.0.0 --port $PORT  (xem Procfile)
             Gắn Volume + đặt DB_PATH=/data/journal.db để journal không mất khi redeploy.
"""

from __future__ import annotations

import datetime as dt
import json
import os
import sqlite3
import threading
import urllib.error
import urllib.request

import ccxt
from apscheduler.schedulers.background import BackgroundScheduler
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse

from data import fetch_ohlcv
from data_funding import fetch_funding
from indicators import atr, ema, rsi

PAIRS = [("BTC/USDT", "BTC/USDT:USDT"), ("ETH/USDT", "ETH/USDT:USDT"),
         ("SOL/USDT", "SOL/USDT:USDT")]
CACHE = "./data_cache"
LOOKBACK_DAYS = 450
FUNDING_PCT_DAYS = 365
DB_PATH = os.environ.get("DB_PATH", "journal.db")
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")          # đặt biến môi trường, KHÔNG hardcode
GEMINI_MODEL = os.environ.get("GEMINI_MODEL", "gemini-2.0-flash")

# Binance hay bị chặn 451 ở một số mạng (công ty/cloud). Tự dò sàn vào được.
# Ép 1 sàn cụ thể bằng env DATA_EXCHANGE; mặc định thử Bybit → Binance → OKX.
DATA_EXCHANGES = ([os.environ["DATA_EXCHANGE"]] if os.environ.get("DATA_EXCHANGE")
                  else ["bybit", "binance", "okx"])
_RESOLVED_EX = None

SNAPSHOT: dict = {"asof": None, "status": "đang tải lần đầu...", "coins": []}
_LOCK = threading.Lock()


# ─────────────────────────── Layer 1-3: phân tích ───────────────────────────
def _trend(c, e20, e50, e200) -> str:
    if e20 > e50 > e200:
        return "bullish"
    if e20 < e50 < e200:
        return "bearish"
    return "mixed"


def _since(days: int) -> str:
    d = dt.datetime.now(dt.timezone.utc) - dt.timedelta(days=days)
    return d.strftime("%Y-%m-%dT%H:%M:%SZ")


def data_exchange() -> str:
    """Dò 1 lần sàn nào vào được (tránh 451 Binance), cache lại kết quả."""
    global _RESOLVED_EX
    if _RESOLVED_EX:
        return _RESOLVED_EX
    for name in DATA_EXCHANGES:
        try:
            getattr(ccxt, name)({"enableRateLimit": True}).fetch_ohlcv("BTC/USDT", "4h", limit=1)
            _RESOLVED_EX = name
            return name
        except Exception:
            continue
    _RESOLVED_EX = DATA_EXCHANGES[0]   # fallback: vẫn trả 1 tên để báo lỗi rõ ràng
    return _RESOLVED_EX


def analyze_coin(spot: str, perp: str, force: bool) -> dict:
    ex = data_exchange()
    fb = dict(symbol=spot, exchange=ex, market="spot",
              since=_since(LOOKBACK_DAYS), until=None, cache_dir=CACHE, force=force)
    h4 = fetch_ohlcv(timeframe="4h", **fb)
    d1 = fetch_ohlcv(timeframe="1d", **fb)
    fund = fetch_funding(perp, ex, _since(FUNDING_PCT_DAYS + 30), None, CACHE, force=force)

    e20 = ema(h4["close"], 20); e50 = ema(h4["close"], 50); e200 = ema(h4["close"], 200)
    r = rsi(h4["close"], 14); a = atr(h4["high"], h4["low"], h4["close"], 14)
    px = float(h4["close"].iloc[-1]); atr_v = float(a.iloc[-1]); r_now = float(r.iloc[-1])
    dist_atr = (px - float(e20.iloc[-1])) / atr_v if atr_v else 0.0
    t4 = _trend(px, e20.iloc[-1], e50.iloc[-1], e200.iloc[-1])

    de20 = ema(d1["close"], 20); de50 = ema(d1["close"], 50); de200 = ema(d1["close"], 200)
    t1d = _trend(d1["close"].iloc[-1], de20.iloc[-1], de50.iloc[-1], de200.iloc[-1])
    ret7 = float(d1["close"].iloc[-1] / d1["close"].iloc[-8] - 1)

    f_win = fund[fund["time"] >= fund["time"].max() - dt.timedelta(days=FUNDING_PCT_DAYS)]
    f_now = float(fund["funding"].iloc[-1])
    f_pctl = float((f_win["funding"] < f_now).mean() * 100)
    ann = f_now * 3 * 365 * 100
    vel = "tăng" if fund["funding"].iloc[-9:].mean() > fund["funding"].iloc[-18:-9].mean() else "giảm"

    # ── L2: Risk score (rủi ro khi vào LONG ngay) ──
    risk, why = 0, []
    if f_pctl >= 95: risk += 2; why.append("funding >95pct")
    if r_now >= 75: risk += 2; why.append("RSI >75")
    if dist_atr >= 2: risk += 3; why.append("giá >2 ATR trên EMA20")
    if t4 == "mixed": risk += 2; why.append("trend 4H không rõ")
    if t4 == "bearish": risk += 2; why.append("trend 4H bearish")
    band = "Bình thường" if risk <= 2 else ("Cẩn thận" if risk <= 5 else "Rủi ro cao")

    # ── L3: Checklist (điều kiện thuận lợi cho LONG) ──
    checklist = [
        {"label": "4H bullish", "ok": t4 == "bullish"},
        {"label": "1D không bearish", "ok": t1d != "bearish"},
        {"label": "Giá gần/dưới EMA20 (pullback)", "ok": dist_atr < 0.5},
        {"label": "RSI không quá nóng (<70)", "ok": r_now < 70},
        {"label": "Funding không đông long (<85pct)", "ok": f_pctl < 85},
    ]
    n_ok = sum(1 for c in checklist if c["ok"])

    flags = []
    if f_pctl <= 10:
        flags.append("Funding cực ÂM (đông short) — bối cảnh squeeze LÊN (edge yếu)")
    elif f_pctl >= 90:
        flags.append("Funding cực DƯƠNG (đông long) — rủi ro flush XUỐNG")
    if dist_atr >= 1.5:
        flags.append(f"Giá căng +{dist_atr:.1f} ATR trên EMA20 — chờ hồi hơn đuổi")
    elif dist_atr <= -1.5:
        flags.append(f"Giá {dist_atr:.1f} ATR dưới EMA20 — quá bán ngắn hạn")

    return {"symbol": spot, "price": px, "trend_4h": t4, "trend_1d": t1d,
            "dist_atr": round(dist_atr, 2), "rsi": round(r_now, 0),
            "ret7": round(ret7 * 100, 1), "funding": round(f_now * 100, 4),
            "funding_ann": round(ann, 0), "funding_pctl": round(f_pctl, 0),
            "funding_vel": vel, "atr_pct": round(atr_v / px * 100, 1),
            "risk_score": risk, "risk_band": band, "risk_why": why,
            "checklist": checklist, "checklist_ok": n_ok, "checklist_n": len(checklist),
            "flags": flags}


def refresh(force: bool = True) -> None:
    coins = []
    for spot, perp in PAIRS:
        try:
            coins.append(analyze_coin(spot, perp, force))
        except Exception as e:
            coins.append({"symbol": spot, "error": str(e)})
    with _LOCK:
        SNAPSHOT["coins"] = coins
        SNAPSHOT["asof"] = dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
        SNAPSHOT["status"] = "ok"
        SNAPSHOT["source"] = _RESOLVED_EX or "?"


def _ctx_for(symbol: str) -> dict:
    with _LOCK:
        for c in SNAPSHOT["coins"]:
            if c.get("symbol") == symbol:
                return c
    return {}


# ─────────────────────────── Trợ lý hỏi-đáp (Gemini) ───────────────────────────
GEMINI_SYS = """Bạn là trợ lý PHÂN TÍCH BỐI CẢNH giao dịch crypto cho một trader swing
discretionary, KHÔNG phải cố vấn đầu tư. Quy tắc bắt buộc:
- CHỈ dùng dữ liệu JSON được cung cấp. KHÔNG bịa số.
- Các tín hiệu (trend, funding, RSI) có EDGE YẾU đã được kiểm chứng — TUYỆT ĐỐI không
  dự báo giá tự tin, không nói chắc chắn lên/xuống.
- Trả lời như NGỮ CẢNH hỗ trợ quyết định: nêu yếu tố ủng hộ và rủi ro cho cả 2 chiều.
- Luôn nhắc người dùng tự quyết định và quản trị rủi ro/đòn bẩy.
- Ngắn gọn, tiếng Việt, cụ thể bằng số. Nếu hỏi về vị thế (vd short từ giá X), tính
  trạng thái lãi/lỗ và mức giá quan trọng (EMA20 = kháng cự/hỗ trợ) từ dữ liệu."""


def ask_gemini(question: str) -> str:
    if not GEMINI_API_KEY:
        return ("Chưa cấu hình GEMINI_API_KEY. Lấy key free tại Google AI Studio, rồi đặt "
                "biến môi trường GEMINI_API_KEY (local: $env:GEMINI_API_KEY='...'; Railway: "
                "thêm ở mục Variables) và khởi động lại.")
    with _LOCK:
        ctx = json.dumps(SNAPSHOT, ensure_ascii=False)
    body = {
        "systemInstruction": {"parts": [{"text": GEMINI_SYS}]},
        "contents": [{"parts": [{"text":
            f"Dữ liệu thị trường hiện tại (JSON):\n{ctx}\n\nCâu hỏi của trader: {question}"}]}],
        "generationConfig": {"temperature": 0.4},
    }
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{GEMINI_MODEL}:generateContent"
    req = urllib.request.Request(
        url, data=json.dumps(body).encode("utf-8"), method="POST",
        headers={"Content-Type": "application/json", "x-goog-api-key": GEMINI_API_KEY})
    try:
        with urllib.request.urlopen(req, timeout=40) as r:
            data = json.loads(r.read())
        return data["candidates"][0]["content"]["parts"][0]["text"]
    except urllib.error.HTTPError as e:
        return f"Lỗi Gemini API ({e.code}): {e.read().decode('utf-8', 'ignore')[:300]}"
    except Exception as e:
        return f"Lỗi gọi Gemini: {e}"


# ─────────────────────────── Layer 4: Journal (SQLite) ───────────────────────────
def db() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    with db() as conn:
        conn.execute("""CREATE TABLE IF NOT EXISTS trades(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ts_open TEXT, symbol TEXT, side TEXT, reason TEXT,
            ctx_price REAL, ctx_funding_pctl REAL, ctx_trend4h TEXT,
            ctx_trend1d TEXT, ctx_rsi REAL, ctx_dist_atr REAL,
            ts_close TEXT, exit_price REAL, pnl_pct REAL, status TEXT)""")


def _rsi_bucket(v):
    if v is None: return "?"
    return "<35" if v < 35 else "35-50" if v < 50 else "50-65" if v < 65 else "65-75" if v < 75 else ">75"


def _fpctl_bucket(v):
    if v is None: return "?"
    return "<25" if v < 25 else "25-50" if v < 50 else "50-75" if v < 75 else "75-90" if v < 90 else ">90"


# ─────────────────────────── FastAPI ───────────────────────────
app = FastAPI(title="Trader Decision Assistant")


@app.on_event("startup")
def _startup() -> None:
    init_db()
    threading.Thread(target=refresh, daemon=True).start()
    sched = BackgroundScheduler(timezone="UTC")
    sched.add_job(refresh, "interval", minutes=5, max_instances=1, coalesce=True)
    sched.start()


@app.get("/api/dashboard")
def api_dashboard(refresh_now: bool = False) -> JSONResponse:
    if refresh_now:
        refresh()
    with _LOCK:
        return JSONResponse(SNAPSHOT)


@app.post("/api/journal/open")
async def journal_open(req: Request) -> JSONResponse:
    b = await req.json()
    ctx = _ctx_for(b["symbol"])
    now = dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%d %H:%M")
    with db() as conn:
        cur = conn.execute(
            """INSERT INTO trades(ts_open,symbol,side,reason,ctx_price,ctx_funding_pctl,
               ctx_trend4h,ctx_trend1d,ctx_rsi,ctx_dist_atr,status)
               VALUES(?,?,?,?,?,?,?,?,?,?,'open')""",
            (now, b["symbol"], b.get("side", "long"), b.get("reason", ""),
             ctx.get("price"), ctx.get("funding_pctl"), ctx.get("trend_4h"),
             ctx.get("trend_1d"), ctx.get("rsi"), ctx.get("dist_atr")))
        return JSONResponse({"id": cur.lastrowid})


@app.post("/api/journal/close")
async def journal_close(req: Request) -> JSONResponse:
    b = await req.json()
    now = dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%d %H:%M")
    with db() as conn:
        row = conn.execute("SELECT * FROM trades WHERE id=?", (b["id"],)).fetchone()
        if not row:
            return JSONResponse({"error": "not found"}, status_code=404)
        entry, exitp = row["ctx_price"], float(b["exit_price"])
        pnl = (exitp / entry - 1) if row["side"] == "long" else (entry / exitp - 1)
        conn.execute("UPDATE trades SET ts_close=?,exit_price=?,pnl_pct=?,status='closed' WHERE id=?",
                     (now, exitp, round(pnl * 100, 2), b["id"]))
    return JSONResponse({"ok": True, "pnl_pct": round(pnl * 100, 2)})


@app.get("/api/journal")
def journal_list() -> JSONResponse:
    with db() as conn:
        rows = [dict(r) for r in conn.execute("SELECT * FROM trades ORDER BY id DESC").fetchall()]
    return JSONResponse(rows)


@app.get("/api/journal/stats")
def journal_stats() -> JSONResponse:
    with db() as conn:
        rows = [dict(r) for r in conn.execute(
            "SELECT * FROM trades WHERE status='closed'").fetchall()]
    n = len(rows)
    if n == 0:
        return JSONResponse({"n": 0})

    def agg(keyfn):
        groups = {}
        for r in rows:
            k = keyfn(r)
            groups.setdefault(k, []).append(r["pnl_pct"])
        return {k: {"n": len(v), "win": round(sum(1 for x in v if x > 0) / len(v) * 100, 0),
                    "avg": round(sum(v) / len(v), 2)} for k, v in sorted(groups.items())}

    wins = sum(1 for r in rows if r["pnl_pct"] > 0)
    return JSONResponse({
        "n": n, "win": round(wins / n * 100, 1),
        "avg_pnl": round(sum(r["pnl_pct"] for r in rows) / n, 2),
        "by_funding": agg(lambda r: _fpctl_bucket(r["ctx_funding_pctl"])),
        "by_trend4h": agg(lambda r: r["ctx_trend4h"] or "?"),
        "by_rsi": agg(lambda r: _rsi_bucket(r["ctx_rsi"])),
    })


@app.post("/api/ask")
async def api_ask(req: Request) -> JSONResponse:
    b = await req.json()
    return JSONResponse({"answer": ask_gemini(b.get("question", ""))})


@app.get("/", response_class=HTMLResponse)
def index() -> str:
    return PAGE


PAGE = """<!doctype html><html lang="vi"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Trader Decision Assistant</title><style>
*{box-sizing:border-box}body{margin:0;background:#0e1117;color:#e6e6e6;
font-family:system-ui,Segoe UI,Roboto,sans-serif;padding:16px;max-width:780px;margin:auto}
h1{font-size:18px;margin:4px 0}h2{font-size:15px;margin:18px 0 6px;color:#9aa4b2}
.sub{color:#8b95a5;font-size:12px;margin-bottom:12px}
.card{background:#161b22;border:1px solid #232a33;border-radius:12px;padding:14px;margin:10px 0}
.row{display:flex;justify-content:space-between;align-items:center}
.sym{font-weight:700;font-size:16px}.px{font-variant-numeric:tabular-nums;color:#cbd5e1}
.grid{display:grid;grid-template-columns:1fr 1fr;gap:6px 14px;margin:8px 0;font-size:13px}
.k{color:#8b95a5}.bull{color:#3fb950}.bear{color:#f85149}.mixed{color:#d29922}
.badge{display:inline-block;padding:3px 9px;border-radius:20px;font-size:12px;font-weight:700}
.b-ok{background:#13361f;color:#3fb950}.b-warn{background:#3a3214;color:#d29922}.b-bad{background:#3d1719;color:#f85149}
.chk{font-size:13px;margin:2px 0}.y{color:#3fb950}.n{color:#f85149}
.flag{font-size:12px;color:#e3b341;margin:3px 0}
.warn{background:#1d2530;border-radius:8px;padding:8px;font-size:11px;color:#8b95a5;margin-bottom:12px}
button{background:#21262d;color:#e6e6e6;border:1px solid #30363d;border-radius:8px;padding:6px 12px;cursor:pointer}
input,select,textarea{background:#0e1117;color:#e6e6e6;border:1px solid #30363d;border-radius:6px;padding:6px;font-size:13px}
table{width:100%;border-collapse:collapse;font-size:12px}td,th{border-bottom:1px solid #232a33;padding:5px;text-align:left}
.form{display:flex;flex-wrap:wrap;gap:6px;align-items:center}
.small{font-size:11px;color:#8b95a5}
</style></head><body>
<h1>🎯 Trader Decision Assistant</h1>
<div class="sub" id="asof">đang tải...</div>
<div class="warn">⚠️ HUD hỗ trợ quyết định, KHÔNG phải lệnh mua/bán. Tín hiệu thị trường có edge yếu.
Giá trị thật nằm ở JOURNAL: ghi lệnh của chính anh để tìm EDGE CÁ NHÂN.</div>
<div id="app"></div>

<h2>💬 Hỏi trợ lý (Gemini) — bám dữ liệu thật</h2>
<div class="card">
 <div class="form">
  <input id="q" placeholder="vd: ETH đang thế nào? tôi đang short x5 từ 2080" style="flex:1;min-width:220px">
  <button onclick="ask()">Hỏi</button>
 </div>
 <div id="ans" class="read" style="white-space:pre-wrap"></div>
 <div class="small">Trả lời chỉ dựa trên dữ liệu hiện tại; tín hiệu edge yếu, KHÔNG phải lệnh.</div>
</div>

<h2>📓 Journal — ghi lệnh</h2>
<div class="card"><div class="form">
 <select id="j-sym"><option>BTC/USDT</option><option>ETH/USDT</option><option>SOL/USDT</option></select>
 <select id="j-side"><option>long</option><option>short</option></select>
 <input id="j-reason" placeholder="Lý do vào (vd: pullback EMA20, funding âm)" style="flex:1;min-width:180px">
 <button onclick="openTrade()">＋ Ghi lệnh (chụp context hiện tại)</button>
</div><div class="small">Khi ghi, hệ thống tự lưu trend/funding/RSI/EMA tại thời điểm này.</div></div>

<h2>📈 Lệnh & PnL</h2>
<div class="card" id="trades">chưa có lệnh.</div>

<h2>🧠 Edge cá nhân (cần đủ lệnh mới đáng tin)</h2>
<div class="card" id="stats">chưa có dữ liệu.</div>

<button onclick="loadAll(true)">⟳ Refresh data</button>
<script>
const cls=t=>t==='bullish'?'bull':t==='bearish'?'bear':'mixed';
const bandCls=b=>b==='Bình thường'?'b-ok':b==='Cẩn thận'?'b-warn':'b-bad';
function card(c){
 if(c.error)return `<div class="card"><span class="sym">${c.symbol}</span> — lỗi: ${c.error}</div>`;
 const chk=c.checklist.map(x=>`<div class="chk"><span class="${x.ok?'y':'n'}">${x.ok?'✓':'✗'}</span> ${x.label}</div>`).join('');
 const flags=(c.flags||[]).map(f=>`<div class="flag">• ${f}</div>`).join('');
 return `<div class="card">
  <div class="row"><span class="sym">${c.symbol}</span>
   <span><span class="badge ${bandCls(c.risk_band)}">Risk ${c.risk_score} · ${c.risk_band}</span>
   &nbsp;<span class="px">$${c.price.toLocaleString()}</span></span></div>
  <div class="grid">
   <div><span class="k">Trend 4H/1D:</span> <span class="${cls(c.trend_4h)}">${c.trend_4h}</span> / <span class="${cls(c.trend_1d)}">${c.trend_1d}</span></div>
   <div><span class="k">Giá vs EMA20:</span> ${c.dist_atr>0?'+':''}${c.dist_atr} ATR</div>
   <div><span class="k">RSI / 7d:</span> ${c.rsi} / ${c.ret7>0?'+':''}${c.ret7}%</div>
   <div><span class="k">Funding:</span> ${c.funding_pctl}pct (${c.funding_vel})</div>
  </div>
  <div class="small">Checklist long: ${c.checklist_ok}/${c.checklist_n} thuận lợi</div>
  ${chk}${flags}</div>`;
}
async function loadDash(force){
 const r=await fetch('/api/dashboard'+(force?'?refresh_now=true':''));const d=await r.json();
 document.getElementById('asof').textContent=d.status==='ok'?('Cập nhật: '+d.asof+' · nguồn '+(d.source||'?')):d.status;
 document.getElementById('app').innerHTML=(d.coins||[]).map(card).join('');
}
async function loadTrades(){
 const rows=await (await fetch('/api/journal')).json();
 if(!rows.length){document.getElementById('trades').textContent='chưa có lệnh.';return;}
 let h='<table><tr><th>#</th><th>coin</th><th>side</th><th>vào</th><th>ctx</th><th>PnL</th><th></th></tr>';
 for(const t of rows){
  const ctx=`${t.ctx_trend4h||'?'} · f${t.ctx_funding_pctl??'?'} · RSI${t.ctx_rsi??'?'}`;
  const pnl=t.status==='closed'?`<span class="${t.pnl_pct>0?'y':'n'}">${t.pnl_pct>0?'+':''}${t.pnl_pct}%</span>`:'<i>mở</i>';
  const act=t.status==='open'?`<button onclick="closeTrade(${t.id})">Đóng</button>`:'';
  h+=`<tr><td>${t.id}</td><td>${t.symbol}</td><td>${t.side}</td><td>${t.ts_open}<br><span class="small">$${t.ctx_price?.toLocaleString()||'?'}</span></td><td class="small">${ctx}</td><td>${pnl}</td><td>${act}</td></tr>`;
 }
 document.getElementById('trades').innerHTML=h+'</table>';
}
async function loadStats(){
 const s=await (await fetch('/api/journal/stats')).json();
 if(!s.n){document.getElementById('stats').textContent='chưa có lệnh đã đóng.';return;}
 const tbl=(o)=>'<table><tr><th>nhóm</th><th>n</th><th>win%</th><th>avg PnL</th></tr>'+
  Object.entries(o).map(([k,v])=>`<tr><td>${k}</td><td>${v.n}</td><td>${v.win}%</td><td class="${v.avg>0?'y':'n'}">${v.avg>0?'+':''}${v.avg}%</td></tr>`).join('')+'</table>';
 let h=`<div class="small">Tổng ${s.n} lệnh đã đóng · win ${s.win}% · avg ${s.avg_pnl}%`;
 h+= s.n<30?' — ⚠️ <30 lệnh, chưa đủ tin.':'';
 h+='</div><h3 style="font-size:13px;margin:10px 0 4px">Theo funding percentile</h3>'+tbl(s.by_funding);
 h+='<h3 style="font-size:13px;margin:10px 0 4px">Theo trend 4H</h3>'+tbl(s.by_trend4h);
 h+='<h3 style="font-size:13px;margin:10px 0 4px">Theo RSI</h3>'+tbl(s.by_rsi);
 document.getElementById('stats').innerHTML=h;
}
async function openTrade(){
 const body={symbol:j_sym.value,side:j_side.value,reason:j_reason.value};
 await fetch('/api/journal/open',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)});
 j_reason.value='';loadTrades();loadStats();
}
async function closeTrade(id){
 const px=prompt('Giá thoát?');if(!px)return;
 await fetch('/api/journal/close',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({id,exit_price:parseFloat(px)})});
 loadTrades();loadStats();
}
async function ask(){
 const q=document.getElementById('q').value;if(!q)return;
 document.getElementById('ans').textContent='đang hỏi Gemini...';
 try{const r=await fetch('/api/ask',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({question:q})});
  const d=await r.json();document.getElementById('ans').textContent=d.answer;}
 catch(e){document.getElementById('ans').textContent='Lỗi: '+e;}
}
function loadAll(force){loadDash(force);loadTrades();loadStats();}
loadAll(false);setInterval(()=>loadDash(false),300000);
</script></body></html>"""
