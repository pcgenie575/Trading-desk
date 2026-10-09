from fastapi import FastAPI, HTTPException, Header
from fastapi.responses import HTMLResponse
from datetime import datetime, timezone, date
import sqlite3, uuid, json, threading, os, math, secrets, base64
from functools import wraps
from universe import INSTRUMENTS, DAILY_CREDITS, SCAN_CREDITS, OPEN_REFRESH_SECONDS, SCAN_REFRESH_SECONDS, MAX_OPEN, MAX_EXPOSURE, MAX_PORTFOLIO_PLANNED_LOSS
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
    "symbol": "US multi-symbol",
    "max_open_positions": MAX_OPEN,
    "max_portfolio_exposure": MAX_EXPOSURE,
    "max_portfolio_planned_loss": MAX_PORTFOLIO_PLANNED_LOSS,
    "interval": "4h",
}

def current_symbol():
    return getattr(_local, "symbol", "SPY")

def checkpoint_key(symbol=None):
    symbol=symbol or current_symbol()
    return "last_processed_bar" if symbol=="SPY" else "last_processed_bar:"+symbol

def open_positions():
    con=db(); rows=[dict(r) for r in con.execute("SELECT * FROM positions WHERE status='OPEN'")]; con.close(); return rows

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
         "type":typ,"status":status,"reason":reason,"data":{"symbol":current_symbol(),**(data or {})},"trade_id":trade_id}
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
          (current_symbol(),"4h",b["datetime"],b["open"],b["high"],b["low"],b["close"],b["volume"]))
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
    r=con.execute("SELECT * FROM positions WHERE status='OPEN' AND symbol=? ORDER BY entry_time DESC LIMIT 1",(current_symbol(),)).fetchone()
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
    s=get_state()
    set_state("mark:"+current_symbol(),mark)
    raw=state_raw()
    equity=s["cash"] + sum(p["qty"]*float(raw.get("mark:"+p["symbol"],raw.get("last_price",p["entry_price"]) if p["symbol"]=="SPY" else p["entry_price"])) for p in open_positions())
    peak=max(s["peak_equity"],equity)
    if current_symbol()=="SPY": set_state("last_price",mark)
    set_state("equity",equity); set_state("peak_equity",peak)
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
    if open_position(): return False, "An open position already exists for this symbol."
    active=open_positions()
    if len(active)>=MAX_OPEN: return False, "Maximum open positions reached."
    if sum(p["position_value"] for p in active)+candidate["position_value"] > MAX_EXPOSURE+1e-6: return False, "Portfolio exposure limit reached."
    if sum(p["planned_loss"] for p in active)+candidate["planned_loss"] > MAX_PORTFOLIO_PLANNED_LOSS+1e-6: return False, "Portfolio planned-loss limit reached."
    if candidate["position_value"]>s["cash"]: return False, "Insufficient paper cash."
    if not INSTRUMENTS.get(current_symbol(),{}).get("paper_enabled"): return False, "Instrument is observation only."
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
      (trade_id,current_symbol(),"OPEN",bar["datetime"],entry,qty,candidate["stop"],value,planned))
    con.commit(); con.close()
    set_state("cash",s["cash"]-value)
    emit("Paper Trader","Logger","PAPER_ENTRY","OPEN",
         f"Opened simulated {current_symbol()} long: {qty:.4f} shares at ${entry:.2f}.",
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
         f"Closed simulated {pos['symbol']} position. Realized P/L ${pnl:.2f}.",
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

@atomic
def reserve_credit(is_open=False):
    day=datetime.now(timezone.utc).date().isoformat()
    raw=state_raw(); key='credits:'+day; used=int(raw.get(key,0))
    if used >= (DAILY_CREDITS if is_open else SCAN_CREDITS): return False
    minute=datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M')
    minute_key='credit_minute'; count=int(raw.get('credit_minute_count',0)) if raw.get(minute_key)==minute else 0
    if count>=6: return False
    set_state(key,used+1);set_state(minute_key,minute);set_state('credit_minute_count',count+1)
    return True

def autonomous_cycle(force=False):
    with _cycle_lock:
        set_state('last_cycle',utcnow())
        active={p['symbol'] for p in open_positions()}
        symbols=list(INSTRUMENTS); raw=state_raw(); cursor=int(raw.get('scan_cursor',0))%len(symbols)
        scanner=symbols[cursor];set_state('scan_cursor',(cursor+1)%len(symbols))
        selected=list(sorted(active))
        if scanner not in active:selected.append(scanner)
        results={}
        for symbol in selected:
            _local.symbol=symbol
            try:
                last=state_raw().get('fetch:'+symbol,'')
                interval=OPEN_REFRESH_SECONDS if symbol in active else SCAN_REFRESH_SECONDS
                if last and (datetime.now(timezone.utc)-datetime.fromisoformat(last)).total_seconds()<interval:continue
                if not reserve_credit(symbol in active):
                    set_state('coverage:'+symbol,'BUDGET_WAIT');continue
                set_state('fetch:'+symbol,utcnow())
                bars=TwelveDataAdapter().latest_completed_bars(symbol,'4h',100)
                if not bars:
                    set_state('coverage:'+symbol,'NO_COMPLETED_DATA');continue
                set_state('coverage:'+symbol,'DATA_RECEIVED')
                set_state('feed_success:'+symbol,utcnow())
                processed=state_raw().get(checkpoint_key(),'')
                pending=[i for i,b in enumerate(bars) if b['datetime']>processed]
                if not processed:pending=[len(bars)-1]
                if processed and processed<bars[0]['datetime']:
                    freeze_system('Recovery data gap for '+symbol+': operator review required.')
                result={'status':'NO_NEW_BAR'}
                for i in pending:
                    result=process_bars(bars[:i+1],allow_entry=(i==len(bars)-1 and INSTRUMENTS[symbol]['paper_enabled']))
                results[symbol]=result
            except Exception as e:
                set_state('coverage:'+symbol,'FEED_ERROR')
                reason=f'{type(e).__name__}: {e}'
                set_state('feed_error:'+symbol,reason)
                emit('Market Data','Logger','SYSTEM_ERROR','NO_ACTION',reason)
                results[symbol]={'status':'ERROR'}
            finally:_local.symbol='SPY'
        return results.get('SPY',{'status':'SCAN_CYCLE','results':results})

@atomic
def process_bars(bars, allow_entry=True):
        save_candles(bars)
        processed=state_raw().get(checkpoint_key(), "")
        if processed and bars[-1]["datetime"] <= processed:
            return {"status":"NO_NEW_BAR","bar_time":bars[-1]["datetime"]}
        update_equity(float(bars[-1]["close"]))
        set_state(checkpoint_key(), bars[-1]["datetime"])
        set_state("last_success", utcnow())
        emit("Market Data","Analyst","NEW_BAR","RECEIVED",f"New completed {current_symbol()} 4-hour candle received.",{"bar":bars[-1]})

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
            emit("Supervisor","Analyst","ENTRY_SKIPPED","NO_ACTION","Historical, stale or observation-only candle; no entry.")
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
    raw=state_raw()
    unrealized=sum(p["qty"]*(float(raw.get("mark:"+p["symbol"],raw.get("last_price",p["entry_price"]) if p["symbol"]=="SPY" else p["entry_price"]))-p["entry_price"]) for p in open_positions())
    return {"last_success":state_raw().get("last_success", ""), "last_processed_bar":state_raw().get(checkpoint_key(), ""), "rules":RULES,"state":s,"daily_realized_pnl":today_realized(),
            "open_position":pos,"open_positions":open_positions(),"coverage":coverage(),"unrealized_pnl":unrealized,
            "scheduler_running":bool(_scheduler_thread and _scheduler_thread.is_alive())}

@app.get('/coverage')
def coverage():
    raw=state_raw();day=datetime.now(timezone.utc).date().isoformat()
    return {'scope':'Free-data watchlist; not all Webull instruments','credits_used_today':int(raw.get('credits:'+day,0)),
      'daily_request_cap':DAILY_CREDITS,'scanner_cap':SCAN_CREDITS,'open_refresh_seconds':OPEN_REFRESH_SECONDS,
      'instruments':[dict(i,status=raw.get('coverage:'+symbol,'WAITING'),last_fetch=raw.get('fetch:'+symbol,''),
        last_success=raw.get('feed_success:'+symbol,''),last_bar=raw.get(checkpoint_key(symbol),''),
        error=raw.get('feed_error:'+symbol,'') if raw.get('coverage:'+symbol)=='FEED_ERROR' else '') for symbol,i in INSTRUMENTS.items()],
      'awaiting_data':['Australian shares/ETFs','Hong Kong shares/ETFs','China Connect','US options','Warrants'],
      'disabled_features':['Margin','Short selling'],'crypto_note':'Observation only; crypto execution fee/spread model is not validated.'}

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
def run_backtest(outputsize:int=500, x_control_token: str | None = Header(default=None)):
    require_control(x_control_token)
    if not reserve_credit():
        raise HTTPException(429,"Free data request budget is exhausted; try later.")
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
    from pathlib import Path
    return HTMLResponse(Path(__file__).with_name('dashboard.html').read_text(encoding='utf-8'))


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
