from fastapi import FastAPI, HTTPException, Header
from fastapi.responses import HTMLResponse
from datetime import datetime, timezone, date
import sqlite3, uuid, json, threading, os, math, secrets, base64
from functools import wraps
from zoneinfo import ZoneInfo
from fastapi.responses import JSONResponse
from market_data import TwelveDataAdapter, MarketDataError
from strategy import signal_from_bars, backtest, CONFIG

app = FastAPI(title="Trading Control Room - Paper Operations")
DB = os.getenv("TCR_DB", "control_room.db")
POLL_SECONDS = int(os.getenv("TCR_POLL_SECONDS", "300"))
CONTROL_TOKEN = os.getenv("TCR_CONTROL_TOKEN", "")

RULES = {
    "starting_balance": 5000.0,
    "max_position": 500.0,
    "max_planned_loss": 25.0,
    "daily_loss_stop": 75.0,
    "drawdown_freeze": 250.0,
    "symbol": "SPY",
    "interval": "4h",
}

def utcnow():
    return datetime.now(timezone.utc).isoformat()

_local = threading.local()
_cycle_lock = threading.RLock()

class TransactionConnection:
    def __init__(self, con): self.con = con
    def __getattr__(self, name): return getattr(self.con, name)
    def commit(self): pass
    def close(self): pass

def atomic(fn):
    @wraps(fn)
    def wrapped(*args, **kwargs):
        with _cycle_lock:
            if getattr(_local, "con", None): return fn(*args, **kwargs)
            con = sqlite3.connect(DB, timeout=30)
            con.row_factory = sqlite3.Row
            con.execute("BEGIN IMMEDIATE")
            _local.con = con
            try:
                result = fn(*args, **kwargs)
                con.commit()
                return result
            except BaseException:
                con.rollback()
                raise
            finally:
                _local.con = None
                con.close()
    return wrapped

def db():
    if getattr(_local, "con", None): return TransactionConnection(_local.con)
    con = sqlite3.connect(DB, timeout=30)
    con.row_factory = sqlite3.Row
    return con

def init_db():
    con = db()
    con.executescript("""
    CREATE TABLE IF NOT EXISTS messages(
      id TEXT PRIMARY KEY, ts TEXT, sender TEXT, recipient TEXT,
      type TEXT, status TEXT, reason TEXT, data TEXT, trade_id TEXT
    );
    CREATE TABLE IF NOT EXISTS state(key TEXT PRIMARY KEY, value TEXT);
    CREATE TABLE IF NOT EXISTS candles(
      symbol TEXT, interval TEXT, bar_time TEXT,
      open REAL, high REAL, low REAL, close REAL, volume REAL,
      PRIMARY KEY(symbol, interval, bar_time)
    );
    CREATE TABLE IF NOT EXISTS positions(
      id TEXT PRIMARY KEY, symbol TEXT, status TEXT,
      entry_time TEXT, entry_price REAL, qty REAL, stop REAL,
      position_value REAL, planned_loss REAL,
      exit_time TEXT, exit_price REAL, realized_pnl REAL, exit_reason TEXT
    );
    CREATE TABLE IF NOT EXISTS daily_pnl(
      trade_date TEXT PRIMARY KEY, realized_pnl REAL NOT NULL DEFAULT 0
    );
    CREATE TABLE IF NOT EXISTS reviews(
      id TEXT PRIMARY KEY, ts TEXT, kind TEXT, payload TEXT
    );
    """)
    defaults = {
      "cash": RULES["starting_balance"],
      "equity": RULES["starting_balance"],
      "peak_equity": RULES["starting_balance"],
      "frozen": False,
      "freeze_reason": "",
      "last_cycle": "",
      "last_price": "0",
    }
    for k,v in defaults.items():
        con.execute("INSERT OR IGNORE INTO state(key,value) VALUES (?,?)",(k,str(v).lower() if isinstance(v,bool) else str(v)))
    con.commit(); con.close()

def state_raw():
    con=db()
    d={r["key"]:r["value"] for r in con.execute("SELECT * FROM state")}
    con.close()
    return d

def get_state():
    d=state_raw()
    return {
      "cash": float(d.get("cash",RULES["starting_balance"])),
      "equity": float(d.get("equity",RULES["starting_balance"])),
      "peak_equity": float(d.get("peak_equity",RULES["starting_balance"])),
      "frozen": d.get("frozen","false")=="true",
      "freeze_reason": d.get("freeze_reason",""),
      "last_cycle": d.get("last_cycle",""),
      "last_price": float(d.get("last_price","0") or 0),
    }

def set_state(k,v):
    con=db()
    value=str(v).lower() if isinstance(v,bool) else str(v)
    con.execute("INSERT OR REPLACE INTO state(key,value) VALUES (?,?)",(k,value))
    con.commit(); con.close()

def emit(sender, recipient, typ, status, reason, data=None, trade_id=None):
    msg={"id":str(uuid.uuid4()),"ts":utcnow(),"sender":sender,"recipient":recipient,
         "type":typ,"status":status,"reason":reason,"data":data or {},"trade_id":trade_id}
    con=db()
    con.execute("INSERT INTO messages VALUES (?,?,?,?,?,?,?,?,?)",
      (msg["id"],msg["ts"],sender,recipient,typ,status,reason,json.dumps(msg["data"]),trade_id))
    con.commit(); con.close()
    return msg

def save_candles(bars):
    con=db(); inserted=0
    for b in bars:
        cur=con.execute("""INSERT OR IGNORE INTO candles
          (symbol,interval,bar_time,open,high,low,close,volume)
          VALUES (?,?,?,?,?,?,?,?)""",
          ("SPY","4h",b["datetime"],b["open"],b["high"],b["low"],b["close"],b["volume"]))
        inserted += cur.rowcount
    con.commit(); con.close()
    return inserted

def latest_saved_bar():
    con=db()
    r=con.execute("SELECT * FROM candles WHERE symbol='SPY' AND interval='4h' ORDER BY bar_time DESC LIMIT 1").fetchone()
    con.close()
    return dict(r) if r else None

def open_position():
    con=db()
    r=con.execute("SELECT * FROM positions WHERE status='OPEN' ORDER BY entry_time DESC LIMIT 1").fetchone()
    con.close()
    return dict(r) if r else None

def today_realized():
    d=datetime.now(ZoneInfo("America/New_York")).date().isoformat()
    con=db()
    r=con.execute("SELECT realized_pnl FROM daily_pnl WHERE trade_date=?",(d,)).fetchone()
    con.close()
    return float(r["realized_pnl"]) if r else 0.0

def add_daily_pnl(amount):
    d=datetime.now(ZoneInfo("America/New_York")).date().isoformat()
    con=db()
    con.execute("""INSERT INTO daily_pnl(trade_date,realized_pnl) VALUES (?,?)
      ON CONFLICT(trade_date) DO UPDATE SET realized_pnl=realized_pnl+excluded.realized_pnl""",(d,amount))
    con.commit(); con.close()

@atomic
def update_equity(mark):
    s=get_state(); pos=open_position()
    equity=s["cash"] + (pos["qty"]*mark if pos else 0.0)
    peak=max(s["peak_equity"],equity)
    set_state("last_price",mark); set_state("equity",equity); set_state("peak_equity",peak)
    if peak-equity >= RULES["drawdown_freeze"] and not s["frozen"]:
        freeze_system(f"Drawdown circuit breaker reached: ${peak-equity:.2f}.")
    return equity, peak

@atomic
def freeze_system(reason):
    set_state("frozen",True); set_state("freeze_reason",reason)
    emit("Supervisor","ALL","FREEZE","FROZEN",reason)

def risk_check(candidate):
    if not all(isinstance(candidate.get(k), (int, float)) and math.isfinite(candidate[k]) and candidate[k] > 0 for k in ("quantity", "position_value", "planned_loss", "stop", "entry_reference")):
        return False, "Invalid candidate values."
    if candidate["stop"] >= candidate["entry_reference"]: return False, "Invalid protective stop."
    s=get_state()
    if s["peak_equity"]-s["equity"] >= RULES["drawdown_freeze"]: return False, "Drawdown circuit breaker reached."
    if s["frozen"]: return False, "System is frozen."
    if open_position(): return False, "An open position already exists."
    if today_realized() <= -RULES["daily_loss_stop"]: return False, "Daily loss circuit breaker reached."
    if candidate.get("position_value",0) > RULES["max_position"]+1e-6: return False, "Maximum position exceeded."
    if candidate.get("planned_loss",0) > RULES["max_planned_loss"]+1e-6: return False, "Maximum planned loss exceeded."
    if candidate.get("quantity",0) <= 0: return False, "Invalid quantity."
    return True, "All deterministic risk checks passed."

@atomic
def paper_enter(candidate, bar):
    trade_id=str(uuid.uuid4())
    entry=float(bar["close"])*(1+CONFIG.slippage_bps/10000)
    qty=min(float(candidate["quantity"]), RULES["max_position"]/entry, RULES["max_planned_loss"]/max(entry-float(candidate["stop"]), 1e-9))
    value=entry*qty
    s=get_state()
    if value > s["cash"]: qty=s["cash"]/entry; value=entry*qty
    if qty <= 0: return None
    planned=qty*max(0,entry-float(candidate["stop"]))
    con=db()
    con.execute("""INSERT INTO positions
      (id,symbol,status,entry_time,entry_price,qty,stop,position_value,planned_loss)
      VALUES (?,?,?,?,?,?,?,?,?)""",
      (trade_id,"SPY","OPEN",bar["datetime"],entry,qty,candidate["stop"],value,planned))
    con.commit(); con.close()
    set_state("cash",s["cash"]-value)
    emit("Paper Trader","Logger","PAPER_ENTRY","OPEN",
         f"Opened simulated SPY long: {qty:.4f} shares at ${entry:.2f}.",
         {"qty":qty,"entry":entry,"stop":candidate["stop"],"value":value,"planned_loss":planned},trade_id)
    return trade_id

@atomic
def paper_exit(pos, raw_price, bar_time, reason):
    exit_price=float(raw_price)*(1-CONFIG.slippage_bps/10000)
    proceeds=pos["qty"]*exit_price
    pnl=proceeds-pos["position_value"]
    con=db()
    con.execute("""UPDATE positions SET status='CLOSED',exit_time=?,exit_price=?,
      realized_pnl=?,exit_reason=? WHERE id=?""",(bar_time,exit_price,pnl,reason,pos["id"]))
    con.commit(); con.close()
    s=get_state(); set_state("cash",s["cash"]+proceeds)
    add_daily_pnl(pnl)
    emit("Paper Trader","Logger","PAPER_EXIT","CLOSED",
         f"Closed simulated SPY position. Realized P/L ${pnl:.2f}.",
         {"exit":exit_price,"pnl":pnl,"reason":reason},pos["id"])
    if today_realized() <= -RULES["daily_loss_stop"]:
        freeze_system(f"Daily realized loss reached ${-today_realized():.2f}.")
    return pnl

def process_exit(bars):
    pos=open_position()
    if not pos: return None
    bar=bars[-1]
    closes=[float(x["close"]) for x in bars]
    exit_ma=sum(closes[-20:])/20 if len(closes)>=20 else None
    if float(bar["low"]) <= pos["stop"]:
        return paper_exit(pos,min(pos["stop"],float(bar["open"])),bar["datetime"],"PROTECTIVE_STOP")
    if exit_ma is not None and float(bar["close"]) < exit_ma:
        return paper_exit(pos,bar["close"],bar["datetime"],"CLOSE_BELOW_20_SMA")
    return None

def reviewer_snapshot():
    con=db()
    rows=[dict(r) for r in con.execute("SELECT * FROM positions WHERE status='CLOSED' ORDER BY exit_time")]
    con.close()
    wins=[r for r in rows if (r["realized_pnl"] or 0)>0]
    pnl=sum((r["realized_pnl"] or 0) for r in rows)
    report={"closed_trades":len(rows),"wins":len(wins),
            "win_rate_pct":(len(wins)/len(rows)*100 if rows else 0),
            "realized_pnl":pnl,"daily_realized_pnl":today_realized(),
            "state":get_state()}
    rid=str(uuid.uuid4())
    con=db(); con.execute("INSERT INTO reviews VALUES (?,?,?,?)",(rid,utcnow(),"OPERATIONS",json.dumps(report)))
    con.commit(); con.close()
    emit("Performance Reviewer","Supervisor","PERFORMANCE_REVIEW","REVIEW",
         "Operational performance snapshot completed.",report)
    return report

_scheduler_stop=threading.Event()
_scheduler_thread=None

def autonomous_cycle(force=False):
    set_state("last_cycle",utcnow())
    try:
        bars=TwelveDataAdapter().latest_completed_bars("SPY","4h",100)
        if not bars: return {"status":"NO_DATA"}
        processed=state_raw().get("last_processed_bar", "")
        pending=[i for i,b in enumerate(bars) if b["datetime"] > processed]
        if not processed: pending=[len(bars)-1]
        if processed and processed < bars[0]["datetime"]:
            freeze_system("Recovery data gap: operator review required.")
        result={"status":"NO_NEW_BAR"}
        for i in pending:
            result=process_bars(bars[:i+1], allow_entry=(i==len(bars)-1))
        return result
    except Exception as e:
        emit("Supervisor","Logger","SYSTEM_ERROR","NO_ACTION",f"{type(e).__name__}: {e}",{})
        return {"status":"ERROR","reason":str(e)}

@atomic
def process_bars(bars, allow_entry=True):
        save_candles(bars)
        processed=state_raw().get("last_processed_bar", "")
        if processed and bars[-1]["datetime"] <= processed:
            return {"status":"NO_NEW_BAR","bar_time":bars[-1]["datetime"]}
        update_equity(float(bars[-1]["close"]))
        set_state("last_processed_bar", bars[-1]["datetime"])
        set_state("last_success", utcnow())
        emit("Market Data","Analyst","NEW_BAR","RECEIVED","New completed SPY 4-hour candle received.",{"bar":bars[-1]})

        # Existing position gets exit priority.
        if open_position():
            pnl=process_exit(bars)
            if pnl is None:
                emit("Analyst","Paper Trader","HOLD","NO_ACTION","Open paper position remains within exit rules.",{})
            reviewer_snapshot()
            update_equity(float(bars[-1]["close"]))
            return {"status":"POSITION_REVIEWED","exit_pnl":pnl}

        opened=datetime.fromisoformat(bars[-1]["datetime"]).replace(tzinfo=ZoneInfo("America/New_York"))
        if not allow_entry or (datetime.now(timezone.utc)-opened.astimezone(timezone.utc)).total_seconds() > 86400:
            emit("Supervisor","Analyst","ENTRY_SKIPPED","NO_ACTION","Historical or stale candle; exits only.")
            return {"status":"ENTRY_SKIPPED"}
        sig=signal_from_bars(bars)
        emit("Analyst","Risk & Compliance",sig["signal"],
             "PENDING" if sig["signal"]=="CANDIDATE" else "NO_ACTION",sig["reason"],sig)
        if sig["signal"]!="CANDIDATE":
            return sig

        approved,reason=risk_check(sig)
        emit("Risk & Compliance","Paper Trader","APPROVED" if approved else "REJECTED",
             "APPROVED" if approved else "BLOCKED",reason,sig)
        if approved:
            tid=paper_enter(sig,bars[-1])
            update_equity(float(bars[-1]["close"]))
            return {"status":"PAPER_ENTRY","trade_id":tid}
        return {"status":"REJECTED","reason":reason}
def scheduler_loop():
    while not _scheduler_stop.is_set():
        autonomous_cycle()
        _scheduler_stop.wait(POLL_SECONDS)

def start_scheduler():
    global _scheduler_thread
    if _scheduler_thread and _scheduler_thread.is_alive(): return
    _scheduler_stop.clear()
    _scheduler_thread=threading.Thread(target=scheduler_loop,daemon=True)
    _scheduler_thread.start()

def require_control(x_control_token: str | None):
    if not CONTROL_TOKEN or not secrets.compare_digest(x_control_token or "", CONTROL_TOKEN):
        raise HTTPException(401,"Invalid control token.")

@app.on_event("startup")
def startup():
    if not CONTROL_TOKEN or not os.getenv("TCR_DASHBOARD_PASSWORD"):
        raise RuntimeError("Control token and dashboard password are required.")
    os.makedirs(os.path.dirname(os.path.abspath(DB)), exist_ok=True)
    init_db()
    if os.getenv("TWELVE_DATA_API_KEY"):
        start_scheduler()
        emit("Supervisor","ALL","STARTUP","ACTIVE","Paper operations scheduler started.",{"poll_seconds":POLL_SECONDS})
    else:
        emit("Supervisor","ALL","STARTUP","WAITING","TWELVE_DATA_API_KEY is not configured.",{})

@app.get("/status")
def status():
    pos=open_position()
    s=get_state()
    unrealized=(pos["qty"]*(s["last_price"]-pos["entry_price"])) if pos and s["last_price"] else 0.0
    return {"last_success":state_raw().get("last_success", ""), "last_processed_bar":state_raw().get("last_processed_bar", ""), "rules":RULES,"state":s,"daily_realized_pnl":today_realized(),
            "open_position":pos,"unrealized_pnl":unrealized,
            "scheduler_running":bool(_scheduler_thread and _scheduler_thread.is_alive())}

@app.get("/messages")
def messages(limit:int=200):
    con=db(); rows=con.execute("SELECT * FROM messages ORDER BY ts DESC LIMIT ?",(min(max(limit,1),1000),)).fetchall(); con.close()
    return [dict(r)|{"data":json.loads(r["data"])} for r in rows]

@app.get("/positions")
def positions():
    con=db(); rows=con.execute("SELECT * FROM positions ORDER BY entry_time DESC").fetchall(); con.close()
    return [dict(r) for r in rows]

@app.get("/candles")
def candles(limit:int=100):
    con=db(); rows=con.execute("SELECT * FROM candles ORDER BY bar_time DESC LIMIT ?",(min(max(limit,1),1000),)).fetchall(); con.close()
    return [dict(r) for r in rows]

@app.get("/review")
def review():
    return reviewer_snapshot()

@app.post("/cycle")
def cycle(x_control_token: str | None = Header(default=None)):
    require_control(x_control_token)
    return autonomous_cycle()

@app.post("/freeze")
def freeze(x_control_token: str | None = Header(default=None)):
    require_control(x_control_token); freeze_system("Manual supervisor freeze."); return {"ok":True}

@app.post("/resume")
def resume(x_control_token: str | None = Header(default=None)):
    require_control(x_control_token)
    s=get_state()
    if today_realized() <= -RULES["daily_loss_stop"] or s["peak_equity"]-s["equity"] >= RULES["drawdown_freeze"]:
        raise HTTPException(409,"Risk circuit breaker remains active.")
    set_state("frozen",False); set_state("freeze_reason","")
    emit("Supervisor","ALL","RESUME","ACTIVE","Manual supervisor resume.",{})
    return {"ok":True}

@app.post("/backtest")
def run_backtest(outputsize:int=500):
    try:
        bars=TwelveDataAdapter().latest_completed_bars("SPY","4h",min(max(outputsize,100),5000))
        report=backtest(bars)
        if "error" not in report:
            emit("Performance Reviewer","Supervisor","BACKTEST_REPORT","REVIEW",
                 "Historical backtest completed; this does not establish future performance.",
                 {k:v for k,v in report.items() if k not in ("trade_log","equity_curve")})
        return report
    except MarketDataError as e:
        return {"error":str(e)}

@app.get("/",response_class=HTMLResponse)
def home():
    return HTMLResponse(r"""
<!doctype html><html><head><meta charset="utf-8"><title>Trading Control Room</title>
<style>
body{font-family:system-ui;background:#0d1117;color:#e6edf3;margin:0;padding:22px}
h1{margin:0 0 8px}.muted{color:#8b949e}.grid{display:grid;grid-template-columns:repeat(3,1fr);gap:12px}
.card{background:#161b22;border:1px solid #30363d;border-radius:14px;padding:15px;margin-bottom:12px}
.good{color:#3fb950}.bad{color:#f85149}.warn{color:#d29922}.msg{padding:10px;border-top:1px solid #30363d}
button{padding:9px 12px;margin-right:8px;border-radius:8px;border:0}table{width:100%;border-collapse:collapse}
td,th{padding:7px;text-align:left;border-bottom:1px solid #30363d}
</style></head><body>
<h1>Trading Control Room <span class="muted">Paper Operations</span></h1>
<div id="summary" class="card"></div>
<div class="grid">
<div class="card"><b>Supervisor</b><p>Health, freezes, recovery</p></div>
<div class="card"><b>Analyst</b><p>Fixed SPY 4h strategy</p></div>
<div class="card"><b>Risk & Compliance</b><p>Hard-coded limits</p></div>
<div class="card"><b>Paper Trader</b><p>Entries, exits, P/L</p></div>
<div class="card"><b>Logger</b><p>Persistent audit trail</p></div>
<div class="card"><b>Performance Reviewer</b><p>Results and learning</p></div>
</div>
<div class="card"><button onclick="cycle()">Run cycle now</button><button onclick="freeze()">Freeze</button><button onclick="resume()">Resume</button><button onclick="review()">Reviewer snapshot</button><span id="action"></span></div>
<div class="card"><h2>Positions</h2><div id="positions"></div></div>
<div class="card"><h2>Live communication / audit feed</h2><div id="feed"></div></div>
<script>
const esc=x=>String(x??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
let token=localStorage.getItem('tcr_token')||'';
async function post(path){let r=await fetch(path,{method:'POST',headers:{'X-Control-Token':token}});if(r.status==401){token=prompt('Control token')||'';localStorage.setItem('tcr_token',token);return post(path)}return r.json()}
async function refresh(){
 let s=await (await fetch('/status')).json(), st=s.state, p=s.open_position;
 summary.innerHTML=`System: <b class="${st.frozen?'bad':'good'}">${st.frozen?'FROZEN':'ACTIVE'}</b> · Scheduler: <b class="${s.scheduler_running?'good':'warn'}">${s.scheduler_running?'RUNNING':'WAITING'}</b> · Equity <b>$${st.equity.toFixed(2)}</b> · Cash $${st.cash.toFixed(2)} · Daily realized P/L <b>$${s.daily_realized_pnl.toFixed(2)}</b> · Unrealized <b>$${s.unrealized_pnl.toFixed(2)}</b>${st.freeze_reason?' · '+esc(st.freeze_reason):''}`;
 let ps=await (await fetch('/positions')).json();
 positions.innerHTML=ps.length?`<table><tr><th>Status</th><th>Entry</th><th>Qty</th><th>Exit</th><th>P/L</th><th>Reason</th></tr>${ps.map(x=>`<tr><td>${esc(x.status)}</td><td>${x.entry_price?.toFixed(2)||''}</td><td>${x.qty?.toFixed(4)||''}</td><td>${x.exit_price?.toFixed(2)||''}</td><td>${x.realized_pnl?.toFixed(2)||''}</td><td>${x.exit_reason||''}</td></tr>`).join('')}</table>`:'No positions yet.';
 let m=await (await fetch('/messages?limit=100')).json();
 feed.innerHTML=m.map(x=>`<div class="msg"><b>${esc(x.sender)} → ${esc(x.recipient)}</b> · ${esc(x.type)} · ${esc(x.status)}<br>${esc(x.reason)}<br><span class="muted">${esc(x.ts)}</span></div>`).join('');
}
async function cycle(){action.textContent=JSON.stringify(await post('/cycle'));refresh()}
async function freeze(){action.textContent=JSON.stringify(await post('/freeze'));refresh()}
async function resume(){action.textContent=JSON.stringify(await post('/resume'));refresh()}
async function review(){let r=await(await fetch('/review')).json();action.textContent=`Reviewer: ${r.closed_trades} closed trades, P/L $${r.realized_pnl.toFixed(2)}, win rate ${r.win_rate_pct.toFixed(1)}%`;refresh()}
refresh();setInterval(refresh,5000);
</script></body></html>""")


@app.middleware("http")
async def dashboard_auth(request, call_next):
    if request.url.path != "/healthz":
        expected_user = os.getenv("TCR_DASHBOARD_USER", "operator")
        expected_password = os.getenv("TCR_DASHBOARD_PASSWORD", "")
        try:
            scheme, encoded = request.headers.get("authorization", "").split(" ", 1)
            user, password = base64.b64decode(encoded, validate=True).decode().split(":", 1)
            valid = scheme.lower() == "basic" and secrets.compare_digest(user, expected_user) and bool(expected_password) and secrets.compare_digest(password, expected_password)
        except Exception:
            valid = False
        if not valid:
            return JSONResponse({"detail":"Authentication required"}, status_code=401, headers={"WWW-Authenticate":'Basic realm="Paper Control Room"'})
    response = await call_next(request)
    response.headers["Cache-Control"] = "no-store"
    response.headers["X-Content-Type-Options"] = "nosniff"
    return response

@app.get("/healthz")
def health():
    try:
        con=db(); con.execute("SELECT 1 FROM state LIMIT 1").fetchone(); con.close()
        if not (_scheduler_thread and _scheduler_thread.is_alive()):
            return JSONResponse({"status":"scheduler_unavailable"},status_code=503)
        last=state_raw().get("last_cycle", "")
        if not last or (datetime.now(timezone.utc)-datetime.fromisoformat(last)).total_seconds() > max(POLL_SECONDS*2,60):
            return JSONResponse({"status":"scheduler_stalled"},status_code=503)
        return {"status":"ok","mode":"paper"}
    except Exception:
        return JSONResponse({"status":"unhealthy"},status_code=503)

@app.on_event("shutdown")
def shutdown():
    _scheduler_stop.set()
    if _scheduler_thread: _scheduler_thread.join(timeout=20)
