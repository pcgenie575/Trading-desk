from fastapi import FastAPI, HTTPException, Header
from fastapi.responses import HTMLResponse, Response
from datetime import datetime, timezone, date, timedelta
import sqlite3, uuid, json, threading, os, math, secrets, base64
from functools import wraps
from dataclasses import asdict
from analyst_tools import analyse, VERSION as ANALYST_VERSION, PARAMETERS as ANALYST_PARAMETERS
from execution import COSTS, fill, sized_entry
from exposure import check as exposure_check, LIMITS as EXPOSURE_LIMITS
from research_engine import compare, validate_bars, fingerprint, PROTOCOL
from urllib.parse import urlparse
from typing import Literal
from pydantic import BaseModel, Field
from universe import INSTRUMENTS, DAILY_CREDITS, SCAN_CREDITS, OPEN_REFRESH_SECONDS, SCAN_REFRESH_SECONDS, MAX_OPEN, MAX_EXPOSURE, MAX_PORTFOLIO_PLANNED_LOSS
from zoneinfo import ZoneInfo
from fastapi.responses import JSONResponse
from market_data import TwelveDataAdapter, MarketDataError
from strategy import signal_from_bars, backtest, CONFIG
from agent_curriculum import curriculum, candidate_integrity, analyst_guidance, evidence_review, VERSION as CURRICULUM_VERSION
from agent_curriculum import BOOKS, AGENTS

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
    CREATE TABLE IF NOT EXISTS trade_context(
      trade_id TEXT PRIMARY KEY, payload TEXT NOT NULL
    );
    CREATE TABLE IF NOT EXISTS trade_reviews(
      trade_id TEXT PRIMARY KEY, updated_at TEXT NOT NULL,
      review_status TEXT NOT NULL, followed_rules TEXT NOT NULL, notes TEXT NOT NULL,
      rule_break TEXT NOT NULL DEFAULT 'none'
    );
    CREATE TABLE IF NOT EXISTS analyst_reports(symbol TEXT,bar_time TEXT,version TEXT,context_hash TEXT,created_at TEXT,payload TEXT,PRIMARY KEY(symbol,bar_time,version,context_hash));
    CREATE TABLE IF NOT EXISTS pending_orders(symbol TEXT PRIMARY KEY,side TEXT,signal_time TEXT,payload TEXT);
    CREATE TABLE IF NOT EXISTS research_runs(id TEXT PRIMARY KEY,ts TEXT,symbol TEXT,dataset_hash TEXT,protocol TEXT,test_start TEXT,test_end TEXT,status TEXT,payload TEXT,dataset TEXT);
    CREATE TABLE IF NOT EXISTS forward_plans(id TEXT PRIMARY KEY,symbol TEXT,registered_at TEXT,protocol TEXT,status TEXT,run_id TEXT);
    CREATE TABLE IF NOT EXISTS weekly_reports(week TEXT PRIMARY KEY,ts TEXT,payload TEXT);
    CREATE TABLE IF NOT EXISTS equity_history(ts TEXT PRIMARY KEY,equity REAL,peak REAL);
    CREATE TABLE IF NOT EXISTS knowledge_entries(
      id TEXT PRIMARY KEY, version INTEGER NOT NULL, updated_at TEXT NOT NULL,
      title TEXT NOT NULL, kind TEXT NOT NULL, status TEXT NOT NULL,
      content TEXT NOT NULL, evidence TEXT NOT NULL, source_url TEXT NOT NULL,
      agents TEXT NOT NULL, builtin INTEGER NOT NULL DEFAULT 0
    );
    CREATE TABLE IF NOT EXISTS knowledge_history(
      entry_id TEXT NOT NULL, version INTEGER NOT NULL, ts TEXT NOT NULL,
      payload TEXT NOT NULL, PRIMARY KEY(entry_id,version)
    );
    """)
    for name in ('entry_fee','exit_fee','estimated_costs'):
        if name not in {r['name'] for r in con.execute('PRAGMA table_info(positions)')}:
            con.execute('ALTER TABLE positions ADD COLUMN '+name+' REAL NOT NULL DEFAULT 0')
    if 'rule_break' not in {r['name'] for r in con.execute('PRAGMA table_info(trade_reviews)')}:
        con.execute("ALTER TABLE trade_reviews ADD COLUMN rule_break TEXT NOT NULL DEFAULT 'none'")
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
    for book in BOOKS:
        entry_id='book:'+book['id'];ts=utcnow()
        cur=con.execute('INSERT OR IGNORE INTO knowledge_entries VALUES (?,?,?,?,?,?,?,?,?,?,?)',
            (entry_id,1,ts,book['title'],'lesson','approved',book['lesson'],
             'Public author/publisher description; original coded curriculum '+CURRICULUM_VERSION+'. Full book not ingested.',book['source'],json.dumps(book['roles']),1))
        if cur.rowcount:
            row=dict(con.execute('SELECT * FROM knowledge_entries WHERE id=?',(entry_id,)).fetchone())
            con.execute('INSERT INTO knowledge_history VALUES (?,?,?,?)',(entry_id,1,ts,json.dumps(row)))
    con.commit(); con.close()

def knowledge_for_agent(agent,full=False):
    if agent not in AGENTS:return []
    con=db();rows=con.execute("SELECT * FROM knowledge_entries WHERE status='approved' AND kind='lesson' ORDER BY id").fetchall();con.close()
    result=[]
    for row in rows:
        if agent not in json.loads(row['agents']):continue
        item={'id':row['id'],'version':row['version'],'title':row['title'],
              'application':'coded curriculum' if row['builtin'] else 'reference guidance'}
        if full:item.update(content=row['content'],evidence=row['evidence'],source_url=row['source_url'])
        result.append(item)
    return result

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
         "type":typ,"status":status,"reason":reason,"data":{"symbol":current_symbol(),"knowledge_refs":knowledge_for_agent(sender),**(data or {})},"trade_id":trade_id}
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
    con=db();con.execute('INSERT OR REPLACE INTO equity_history VALUES (?,?,?)',(utcnow(),equity,peak));con.commit();con.close()
    return equity, peak

@atomic
def freeze_system(reason):
    set_state("frozen",True); set_state("freeze_reason",reason)
    emit("Supervisor","ALL","FREEZE","FROZEN",reason)

def risk_check(candidate):
    consistent,reason=candidate_integrity(candidate)
    if not consistent:return False,'Book-informed sizing check: '+reason
    if not all(isinstance(candidate.get(k), (int, float)) and math.isfinite(candidate[k]) and candidate[k] > 0 for k in ("quantity", "position_value", "planned_loss", "stop", "entry_reference")):
        return False, "Invalid candidate values."
    if candidate["stop"] >= candidate["entry_reference"]: return False, "Invalid protective stop."
    risk_value=candidate.get('cash_cost',candidate['position_value']);risk_loss=candidate.get('cost_adjusted_risk',candidate['planned_loss'])
    s=get_state()
    if s["peak_equity"]-s["equity"] >= RULES["drawdown_freeze"]: return False, "Drawdown circuit breaker reached."
    if s["frozen"]: return False, "System is frozen."
    if open_position(): return False, "An open position already exists for this symbol."
    active=open_positions()
    if len(active)>=MAX_OPEN: return False, "Maximum open positions reached."
    if sum(p["position_value"] for p in active)+risk_value > MAX_EXPOSURE+1e-6: return False, "Portfolio exposure limit reached."
    if sum(p["planned_loss"] for p in active)+risk_loss > MAX_PORTFOLIO_PLANNED_LOSS+1e-6: return False, "Portfolio planned-loss limit reached."
    if risk_value>s["cash"]: return False, "Insufficient paper cash."
    if not INSTRUMENTS.get(current_symbol(),{}).get("paper_enabled"): return False, "Instrument is observation only."
    if today_realized() <= -RULES["daily_loss_stop"]: return False, "Daily loss circuit breaker reached."
    if risk_value > RULES["max_position"]+1e-6: return False, "Maximum position exceeded."
    if risk_loss > RULES["max_planned_loss"]+1e-6: return False, "Maximum planned loss exceeded."
    if candidate.get("quantity",0) <= 0: return False, "Invalid quantity."
    series={}
    con=db();cutoff=(datetime.now(ZoneInfo('America/New_York')).replace(tzinfo=None)-timedelta(days=10)).isoformat(sep=' ')
    for symbol in {current_symbol(),*(p['symbol'] for p in active)}:
        rows=con.execute("SELECT bar_time,close FROM candles WHERE symbol=? AND interval='4h' ORDER BY bar_time DESC LIMIT 100",(symbol,)).fetchall()
        series[symbol]={r['bar_time']:r['close'] for r in rows} if rows and rows[0]['bar_time']>=cutoff else {}
    con.close()
    allowed,details=exposure_check(current_symbol(),risk_value,active,series)
    if not allowed:return False,details
    return True, "All deterministic risk and concentration checks passed."

@atomic
def paper_enter(candidate, bar):
    trade_id=str(uuid.uuid4())
    raw=float(bar.get('fill_open',bar['close']))
    f=sized_entry(raw,float(candidate['stop']),get_state()['cash'],max_qty=float(candidate['quantity']))
    if not f:
        emit('Risk & Compliance','Paper Trader','FILL_REJECTED','BLOCKED','Gap or costs invalidate the planned entry.')
        return None
    entry=f['price'];qty=f['qty'];value=f['cash'];planned=f['planned_loss'];s=get_state()
    checked=dict(candidate,entry_reference=entry,quantity=qty,position_value=entry*qty,planned_loss=qty*(entry-candidate['stop']),cash_cost=value,cost_adjusted_risk=planned)
    approved,reason=risk_check(checked)
    if not approved:emit('Risk & Compliance','Paper Trader','FILL_REJECTED','BLOCKED',reason);return None
    con=db()
    con.execute("""INSERT INTO positions
      (id,symbol,status,entry_time,entry_price,qty,stop,position_value,planned_loss,entry_fee,estimated_costs)
      VALUES (?,?,?,?,?,?,?,?,?,?,?)""",
      (trade_id,current_symbol(),"OPEN",bar["datetime"],entry,qty,candidate["stop"],value,planned,f["fee"],f["total_cost"]))
    context={"strategy":"Trend Breakout v1","mode":"paper","captured_at":utcnow(),
             "candidate":candidate,"strategy_config":asdict(CONFIG),"risk_rules":dict(RULES),
             "instrument":dict(INSTRUMENTS[current_symbol()])}
    context['execution']={'model':asdict(COSTS),'entry':f,'signal_time':candidate.get('signal_time'),'fill_basis':'Next eligible candle open; reconstructed after delayed candle arrival' if 'fill_open' in bar else 'Direct test/helper fill'}
    context['curriculum_version']=CURRICULUM_VERSION
    context['knowledge']={agent:knowledge_for_agent(agent,full=True) for agent in ('Analyst','Risk & Compliance','Paper Trader')}
    con.execute("INSERT INTO trade_context VALUES (?,?)",(trade_id,json.dumps(context)))
    con.commit(); con.close()
    set_state("cash",s["cash"]-value)
    emit("Paper Trader","Logger","PAPER_ENTRY","OPEN",
         f"Opened simulated {current_symbol()} long: {qty:.4f} shares at ${entry:.2f}.",
         {"qty":qty,"entry":entry,"stop":candidate["stop"],"value":value,"planned_loss":planned},trade_id)
    return trade_id

@atomic
def paper_exit(pos, raw_price, bar_time, reason):
    f=fill(float(raw_price),pos['qty'],'sell');exit_price=f['price'];proceeds=f['cash']
    pnl=proceeds-pos["position_value"]
    con=db()
    con.execute("""UPDATE positions SET status='CLOSED',exit_time=?,exit_price=?,
      realized_pnl=?,exit_reason=?,exit_fee=?,estimated_costs=estimated_costs+? WHERE id=?""",(bar_time,exit_price,pnl,reason,f["fee"],f["total_cost"],pos["id"]))
    con.commit(); con.close()
    s=get_state(); set_state("cash",s["cash"]+proceeds)
    add_daily_pnl(pnl)
    emit("Paper Trader","Logger","PAPER_EXIT","CLOSED",
         f"Closed simulated {pos['symbol']} position. Realized P/L ${pnl:.2f}.",
         {"exit":exit_price,"pnl":pnl,"reason":reason,"costs":f},pos["id"])
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
        con=db();con.execute('INSERT OR REPLACE INTO pending_orders VALUES (?,?,?,?)',(current_symbol(),'sell',bar['datetime'],json.dumps({'trade_id':pos['id'],'reason':'CLOSE_BELOW_20_SMA','queued_at':utcnow()})));con.commit();con.close()
        emit('Analyst','Paper Trader','EXIT_QUEUED','PENDING','MA exit waits for a later eligible candle open.')
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
            "state":get_state(),"learning_review":evidence_review(rows),"knowledge":knowledge_for_agent('Performance Reviewer',full=True)}
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
        con=db();active.update(r['symbol'] for r in con.execute('SELECT symbol FROM pending_orders'));con.close()
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
        maybe_weekly_report()
        maybe_forward_research()
        return results.get('SPY',{'status':'SCAN_CYCLE','results':results})

@atomic
def process_bars(bars, allow_entry=True):
        save_candles(bars)
        processed=state_raw().get(checkpoint_key(), "")
        if processed and bars[-1]["datetime"] <= processed:
            return {"status":"NO_NEW_BAR","bar_time":bars[-1]["datetime"]}
        update_equity(float(bars[-1]["open"]))
        set_state(checkpoint_key(), bars[-1]["datetime"])
        set_state("last_success", utcnow())
        emit("Market Data","Analyst","NEW_BAR","RECEIVED",f"New completed {current_symbol()} 4-hour candle received.",{"bar":bars[-1]})
        analysis=build_analysis(current_symbol(),bars)
        save_analysis(analysis)
        emit("Analyst","Logger","TREND_ANALYSIS","CONTEXT",analysis["summary"],analysis)

        con=db();order=con.execute('SELECT * FROM pending_orders WHERE symbol=?',(current_symbol(),)).fetchone();con.close()
        order_payload=json.loads(order['payload']) if order else {}
        opened_utc=datetime.fromisoformat(bars[-1]['datetime']).replace(tzinfo=ZoneInfo('America/New_York')).astimezone(timezone.utc)
        eligible=order and opened_utc>=datetime.fromisoformat(order_payload.get('queued_at',datetime.fromisoformat(order['signal_time']).replace(tzinfo=ZoneInfo('America/New_York')).astimezone(timezone.utc).isoformat())) and datetime.fromisoformat(bars[-1]['datetime'])>=datetime.fromisoformat(order['signal_time'])+timedelta(hours=4,minutes=15)
        if eligible:
            con=db();con.execute('DELETE FROM pending_orders WHERE symbol=?',(current_symbol(),));con.commit();con.close()
            payload=json.loads(order['payload']);bar=bars[-1]
            if order['side']=='sell':
                pos=open_position()
                if pos and pos['id']==payload['trade_id']:paper_exit(pos,min(float(bar['open']),pos['stop']),bar['datetime'],payload['reason']) if float(bar['open'])<pos['stop'] else paper_exit(pos,float(bar['open']),bar['datetime'],payload['reason'])
            else:
                stale=datetime.fromisoformat(bar['datetime'])-datetime.fromisoformat(order['signal_time'])>timedelta(days=7)
                if not stale and INSTRUMENTS[current_symbol()]['paper_enabled']:
                    tid=paper_enter(payload,dict(bar,fill_open=float(bar['open'])))
                    if tid:
                        process_exit(bars);update_equity(float(bar['close']));return {'status':'PAPER_ENTRY','trade_id':tid}
                else:emit('Supervisor','Paper Trader','ORDER_EXPIRED','NO_ACTION','Pending entry expired.')
            update_equity(float(bar['close']))
            return {'status':'ORDER_PROCESSED'}
        update_equity(float(bars[-1]["close"]))
        if order and order['side']=='buy':return {'status':'ORDER_WAIT','reason':'Next candle open must be after the recorded decision time.'}
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
        sig['learning']=analyst_guidance(sig)
        sig['analysis']=analysis
        emit("Analyst","Risk & Compliance",sig["signal"],
             "PENDING" if sig["signal"]=="CANDIDATE" else "NO_ACTION",sig["reason"],sig)
        if sig["signal"]!="CANDIDATE":
            return sig

        approved,reason=risk_check(sig)
        emit("Risk & Compliance","Paper Trader","APPROVED" if approved else "REJECTED",
             "APPROVED" if approved else "BLOCKED",reason,sig)
        if approved:
            sig['signal_time']=bars[-1]['datetime'];sig['queued_at']=utcnow()
            con=db();con.execute('INSERT OR REPLACE INTO pending_orders VALUES (?,?,?,?)',(current_symbol(),'buy',bars[-1]['datetime'],json.dumps(sig)));con.commit();con.close()
            emit('Paper Trader','Logger','ENTRY_QUEUED','PENDING','Signal waits for a later eligible candle open; costs and risk are rechecked at fill.',sig)
            return {'status':'ENTRY_QUEUED'}
        return {"status":"REJECTED","reason":reason}
def scheduler_loop():
    while not _scheduler_stop.is_set():
        try:autonomous_cycle()
        except Exception as e:
            try:freeze_system('Unexpected scheduler failure: '+type(e).__name__+'; operator review required.')
            except Exception:pass
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
    # Interrupted experiments remain retained and cannot masquerade as completed trials.
    con=db();con.execute("UPDATE research_runs SET status='INTERRUPTED' WHERE status='RUNNING'");con.commit();con.close()
    seed_analyst_reports()
    register_forward_plan()
    maybe_weekly_report()
    training=curriculum()
    if not training['self_check']['passed']:raise RuntimeError('Curriculum self-check failed.')
    emit('Supervisor','ALL','CURRICULUM_LOADED','ACTIVE','Book-informed rule curriculum loaded.',
         {'version':training['version'],'fingerprint':training['fingerprint'],'checks':training['self_check']})
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
    unrealized=sum(p["qty"]*(float(raw.get("mark:"+p["symbol"],raw.get("last_price",p["entry_price"]) if p["symbol"]=="SPY" else p["entry_price"])))-p["position_value"] for p in open_positions())
    return {"last_success":state_raw().get("last_success", ""), "last_processed_bar":state_raw().get(checkpoint_key(), ""), "rules":RULES,"state":s,"daily_realized_pnl":today_realized(),
            "open_position":pos,"open_positions":open_positions(),"coverage":coverage(),"training":curriculum(),"unrealized_pnl":unrealized,
            "execution_costs":asdict(COSTS),"exposure_limits":EXPOSURE_LIMITS,"pending_orders":pending_orders(),"scheduler_running":bool(_scheduler_thread and _scheduler_thread.is_alive())}

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

@app.get('/training')
def training_status():
    return dict(curriculum(),evidence=evidence_review(positions()))

AgentName=Literal['Market Data','Analyst','Risk & Compliance','Paper Trader','Logger','Supervisor','Performance Reviewer']

class KnowledgeInput(BaseModel):
    expected_version: int=Field(default=0,ge=0)
    title: str=Field(min_length=3,max_length=160)
    kind: Literal['lesson','hypothesis','experiment']='lesson'
    status: Literal['draft','in_review','approved','rejected','archived']='draft'
    content: str=Field(min_length=1,max_length=6000)
    evidence: str=Field(default='',max_length=4000)
    source_url: str=Field(default='',max_length=800)
    agents: list[AgentName]=Field(default_factory=list,max_length=7)

@app.get('/knowledge')
def knowledge():
    con=db();rows=con.execute('SELECT * FROM knowledge_entries ORDER BY updated_at DESC,id').fetchall();con.close()
    return {'entries':[dict(r,agents=json.loads(r['agents'])) for r in rows],'agents':list(AGENTS),
            'policy':'Approved custom lessons are reference context, not executable trading rules. Experiments are operator-entered records.'}

@app.get('/knowledge/{entry_id}/history')
def knowledge_history(entry_id: str):
    con=db();rows=con.execute('SELECT payload FROM knowledge_history WHERE entry_id=? ORDER BY version DESC',(entry_id,)).fetchall();con.close()
    return [dict(json.loads(r['payload']),agents=json.loads(json.loads(r['payload'])['agents'])) for r in rows]

def validate_knowledge(payload):
    if not payload.title.strip() or not payload.content.strip():raise HTTPException(422,'Title and content cannot be blank.')
    if payload.status=='approved' and (not payload.evidence.strip() or not payload.agents):
        raise HTTPException(422,'Approval requires evidence and at least one assigned agent.')
    if payload.source_url:
        parsed=urlparse(payload.source_url)
        if parsed.scheme not in ('http','https') or not parsed.netloc or parsed.username or parsed.password:
            raise HTTPException(422,'Source must be an HTTP(S) URL without embedded credentials.')

def write_knowledge(entry_id,payload,old=None):
    validate_knowledge(payload);con=db()
    if old:
        if old['builtin']:raise HTTPException(409,'The installed book curriculum is read-only. Create a related lesson instead.')
        if payload.expected_version!=old['version']:raise HTTPException(409,'This record changed. Reload it before saving.')
        version=old['version']+1
    else:
        if payload.expected_version!=0:raise HTTPException(409,'New records start at version zero.')
        if con.execute('SELECT COUNT(*) FROM knowledge_entries').fetchone()[0]>=250:raise HTTPException(409,'Knowledge base limit reached (250 records).')
        version=1
    ts=utcnow()
    con.execute('INSERT OR REPLACE INTO knowledge_entries VALUES (?,?,?,?,?,?,?,?,?,?,?)',
        (entry_id,version,ts,payload.title.strip(),payload.kind,payload.status,payload.content.strip(),payload.evidence.strip(),payload.source_url.strip(),json.dumps(sorted(set(payload.agents))),0))
    row=dict(con.execute('SELECT * FROM knowledge_entries WHERE id=?',(entry_id,)).fetchone())
    con.execute('INSERT INTO knowledge_history VALUES (?,?,?,?)',(entry_id,version,ts,json.dumps(row)))
    con.commit();con.close()
    emit('Research Lab','Supervisor','KNOWLEDGE_SAVED','RECORDED','Knowledge record saved.',{'entry_id':entry_id,'version':version,'kind':payload.kind,'review_status':payload.status})
    return dict(row,agents=json.loads(row['agents']))

@app.post('/knowledge')
@atomic
def create_knowledge(payload: KnowledgeInput, x_control_token: str | None=Header(default=None)):
    require_control(x_control_token)
    return write_knowledge(str(uuid.uuid4()),payload)

@app.put('/knowledge/{entry_id}')
@atomic
def update_knowledge(entry_id: str,payload: KnowledgeInput,x_control_token: str | None=Header(default=None)):
    require_control(x_control_token);con=db()
    old=con.execute('SELECT * FROM knowledge_entries WHERE id=?',(entry_id,)).fetchone();con.close()
    if not old:raise HTTPException(404,'Knowledge record not found.')
    return write_knowledge(entry_id,payload,old)

@app.get("/messages")
def messages(limit:int=200):
    con=db(); rows=con.execute("SELECT * FROM messages ORDER BY ts DESC LIMIT ?",(min(max(limit,1),1000),)).fetchall(); con.close()
    return [dict(r)|{"data":json.loads(r["data"])} for r in rows]

@app.get("/positions")
def positions():
    con=db(); rows=con.execute("SELECT * FROM positions ORDER BY entry_time DESC").fetchall(); con.close()
    return [dict(r) for r in rows]

@app.get('/journal')
def journal():
    con=db()
    rows=con.execute('''SELECT p.*,c.payload AS context_payload,r.updated_at AS review_updated_at,
      r.review_status,r.followed_rules,r.notes,r.rule_break FROM positions p
      LEFT JOIN trade_context c ON c.trade_id=p.id
      LEFT JOIN trade_reviews r ON r.trade_id=p.id ORDER BY p.entry_time DESC,p.id''').fetchall()
    con.close()
    trades=[]
    for row in rows:
        item=dict(row);payload=item.pop('context_payload')
        item['context']=json.loads(payload) if payload else None
        trades.append(item)
    return {'mode':'paper','trades':trades,'strategy':{'name':'Trend Breakout v1','config':asdict(CONFIG)},
            'export_version':1}

class TradeReviewInput(BaseModel):
    review_status: Literal['draft','reviewed']='draft'
    followed_rules: Literal['unknown','yes','partial','no']='unknown'
    notes: str=Field(default='',max_length=4000)
    rule_break: Literal['none','moved_stop','oversized','revenge_trade','fomo','other']='none'

@app.put('/journal/{trade_id}/review')
@atomic
def save_trade_review(trade_id: str, review: TradeReviewInput, x_control_token: str | None=Header(default=None)):
    require_control(x_control_token)
    con=db()
    if not con.execute('SELECT id FROM positions WHERE id=?',(trade_id,)).fetchone():
        con.close();raise HTTPException(404,'Paper trade not found.')
    con.execute('INSERT OR REPLACE INTO trade_reviews(trade_id,updated_at,review_status,followed_rules,notes,rule_break) VALUES (?,?,?,?,?,?)',
                (trade_id,utcnow(),review.review_status,review.followed_rules,review.notes,review.rule_break))
    con.commit();con.close()
    emit('Journal','Supervisor','TRADE_REVIEW_SAVED','RECORDED','Operator saved a paper-trade review.',
         {'review_status':review.review_status,'followed_rules':review.followed_rules},trade_id)
    return {'ok':True}

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

@app.post('/backtest')
def run_backtest(outputsize:int=500,x_control_token: str | None=Header(default=None)):
    require_control(x_control_token)
    return run_research(ResearchInput(symbol='SPY',use_cached=True),x_control_token)

@app.get("/",response_class=HTMLResponse)
def home():
    from pathlib import Path
    return HTMLResponse(Path(__file__).with_name('dashboard.html').read_text(encoding='utf-8'))

@app.get('/journal-ui.js')
def journal_ui():
    from pathlib import Path
    return Response(Path(__file__).with_name('journal-ui.js').read_text(encoding='utf-8'),media_type='application/javascript')

@app.get('/research',response_class=HTMLResponse)
def research_page():
    from pathlib import Path
    return HTMLResponse(Path(__file__).with_name('research.html').read_text(encoding='utf-8'))


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


def pending_orders():
    con=db();rows=[dict(r) for r in con.execute('SELECT symbol,side,signal_time FROM pending_orders')];con.close();return rows

class ResearchBar(BaseModel):
    datetime: str
    open: float
    high: float
    low: float
    close: float
    volume: float=0

class ResearchInput(BaseModel):
    symbol: str=Field(default='SPY',max_length=12)
    use_cached: bool=True
    bars: list[ResearchBar]=Field(default_factory=list,max_length=5000)
    source: str=Field(default='Saved free-provider candles',min_length=3,max_length=400)

@app.get('/experiments')
def experiments(limit:int=10,offset:int=0):
    limit=min(max(limit,1),20);offset=max(offset,0)
    con=db();total=con.execute('SELECT COUNT(*) FROM research_runs').fetchone()[0]
    rows=[dict(r) for r in con.execute('SELECT id,ts,symbol,dataset_hash,protocol,test_start,test_end,status,payload FROM research_runs ORDER BY ts DESC LIMIT ? OFFSET ?',(limit,offset))];con.close()
    for r in rows:
        r['payload']=json.loads(r['payload']);r['protocol']=json.loads(r['protocol'])
        for variant in r['payload'].get('variants',[]):
            for period in ('development','later_period'):
                variant[period].pop('equity_curve',None);variant[period].pop('trade_log',None)
        for baseline in ('benchmark_500','benchmark_full_capital'):
            if baseline in r['payload']:r['payload'][baseline].pop('equity_curve',None)
    return {'runs':rows,'total':total,'offset':offset,'limit':limit,'protocol':PROTOCOL,'no_automatic_activation':True,'forward_plans':forward_plans()}

@app.get('/experiments/{run_id}')
def experiment_result(run_id: str):
    con=db();row=con.execute('SELECT id,ts,symbol,dataset_hash,protocol,test_start,test_end,status,payload FROM research_runs WHERE id=?',(run_id,)).fetchone();con.close()
    if not row:raise HTTPException(404,'Experiment not found.')
    return dict(row,protocol=json.loads(row['protocol']),payload=json.loads(row['payload']))

@app.post('/experiments')
def run_research(payload: ResearchInput,x_control_token: str | None=Header(default=None)):
    require_control(x_control_token)
    if payload.symbol not in INSTRUMENTS or not INSTRUMENTS[payload.symbol]['paper_enabled']:raise HTTPException(422,'Choose a paper-enabled US instrument.')
    with _cycle_lock:
        con=db()
        if payload.use_cached:
            rows=con.execute("SELECT bar_time AS datetime,open,high,low,close,volume FROM candles WHERE symbol=? AND interval='4h' ORDER BY bar_time",(payload.symbol,)).fetchall();bars=[dict(r) for r in rows][-5000:]
        else:bars=[r.model_dump() for r in payload.bars]
        try:validate_bars(bars)
        except (ValueError,KeyError,TypeError) as e:con.close();raise HTTPException(422,str(e))
        if datetime.fromisoformat(bars[-1]['datetime']).replace(tzinfo=ZoneInfo('America/New_York')).astimezone(timezone.utc)+timedelta(hours=4,minutes=15)>datetime.now(timezone.utc):con.close();raise HTTPException(422,'Research requires completed candles.')
        digest=fingerprint(payload.symbol,bars);proto=json.dumps(PROTOCOL,sort_keys=True)
        existing=con.execute('SELECT id,payload,status FROM research_runs WHERE dataset_hash=? AND protocol=?',(digest,proto)).fetchone()
        if existing:con.close();return {'id':existing['id'],'status':existing['status'],'reused_existing_run':True,'result':json.loads(existing['payload'])}
        if con.execute('SELECT COUNT(*) FROM research_runs').fetchone()[0]>=100:con.close();raise HTTPException(409,'Research history limit reached (100 batches). Export before extending storage.')
        split=int(len(bars)*.7);start=bars[split]['datetime'];end=bars[-1]['datetime']
        prior=con.execute('SELECT test_start,test_end FROM research_runs WHERE symbol=?',(payload.symbol,)).fetchall()
        reuse=any(not(end<r['test_start'] or start>r['test_end']) for r in prior)
        rid=str(uuid.uuid4());meta={'source':payload.source,'bars':len(bars),'split_index':split,'test_period_reused':reuse,'later_period_label':'Previously tested period' if reuse else 'First recorded test of this period in this lab','dataset_sha256':digest,'predeclared_at':utcnow(),'variants_attempted':8,'edge_validated':False}
        con.execute('INSERT INTO research_runs VALUES (?,?,?,?,?,?,?,?,?,?)',(rid,utcnow(),payload.symbol,digest,proto,start,end,'RUNNING',json.dumps(meta),json.dumps(bars)));con.commit();con.close()
    # Run outside scheduler lock; protocol and dataset already frozen and durably registered.
    try:
        result=dict(meta,**compare(bars,split));state='COMPLETE'
    except Exception as e:result=dict(meta,error=type(e).__name__);state='FAILED'
    with _cycle_lock:
        con=db();con.execute('UPDATE research_runs SET status=?,payload=? WHERE id=?',(state,json.dumps(result),rid));con.commit();con.close()
        emit('Performance Reviewer','Research Lab','EXPERIMENT_RECORDED',state,'Fixed comparison batch retained; no strategy activation.',{'id':rid,'variants':8,'test_period_reused':reuse})
    return {'id':rid,'status':state,'result':result}

@app.get('/experiments/{run_id}/dataset')
def experiment_dataset(run_id: str):
    con=db();row=con.execute('SELECT symbol,dataset,protocol FROM research_runs WHERE id=?',(run_id,)).fetchone();con.close()
    if not row:raise HTTPException(404,'Experiment not found.')
    return {'symbol':row['symbol'],'bars':json.loads(row['dataset']),'protocol':json.loads(row['protocol'])}

@atomic
def maybe_weekly_report():
    now=datetime.now(ZoneInfo('America/New_York'));monday=now.date()-timedelta(days=now.weekday());start=monday-timedelta(days=7);week=start.isoformat()
    con=db()
    if con.execute('SELECT 1 FROM weekly_reports WHERE week=?',(week,)).fetchone():con.close();return
    rows=[dict(r) for r in con.execute("SELECT p.*,r.followed_rules,r.review_status FROM positions p LEFT JOIN trade_reviews r ON p.id=r.trade_id WHERE p.status='CLOSED' AND p.exit_time>=? AND p.exit_time<?",(week,monday.isoformat()))]
    total=con.execute("SELECT COUNT(*) FROM positions WHERE status='CLOSED'").fetchone()[0]
    failures=con.execute("SELECT COUNT(*) FROM messages WHERE sender='Market Data' AND type='SYSTEM_ERROR' AND ts>=? AND ts<?",(datetime.combine(start,datetime.min.time(),ZoneInfo('America/New_York')).astimezone(timezone.utc).isoformat(),datetime.combine(monday,datetime.min.time(),ZoneInfo('America/New_York')).astimezone(timezone.utc).isoformat())).fetchone()[0]
    equity=[dict(r) for r in con.execute('SELECT * FROM equity_history WHERE ts>=? AND ts<? ORDER BY ts',(datetime.combine(start,datetime.min.time(),ZoneInfo('America/New_York')).astimezone(timezone.utc).isoformat(),datetime.combine(monday,datetime.min.time(),ZoneInfo('America/New_York')).astimezone(timezone.utc).isoformat()))]
    pnl=sum(r['realized_pnl'] or 0 for r in rows);eligible=[r for r in rows if r['planned_loss']>0];reviewed=[r for r in rows if r['review_status']=='reviewed' and r['followed_rules'] in ('yes','partial','no')]
    frozen=get_state()['frozen'];decision='pause' if frozen else 'investigate' if failures or (len(rows)>=30 and pnl<0) else 'continue collecting'
    reasons=[]
    if frozen:reasons.append(get_state()['freeze_reason'])
    if failures:reasons.append(str(failures)+' provider failures during this week; check coverage before interpreting results.')
    if total<30:reasons.append('Fewer than 30 closed trades overall; this collection milestone does not establish profitability.')
    if not rows:reasons.append('No closed trades in this week; expectancy and adherence are unavailable.')
    if len(rows)>=30 and pnl<0:reasons.append('Negative weekly expectancy after recorded costs; inspect setups and execution.')
    if not reasons:reasons.append('Continue monitoring; a positive week alone does not validate an edge.')
    report={'week_start':week,'week_end':(monday-timedelta(days=1)).isoformat(),'timezone':'America/New_York','decision':decision,'reasons':reasons,'closed_trades':len(rows),'overall_closed_trades':total,'net_pnl':pnl,'expectancy_dollars':pnl/len(rows) if rows else None,'expectancy_r':sum((r['realized_pnl'] or 0)/r['planned_loss'] for r in eligible)/len(eligible) if eligible else None,'estimated_costs':sum(r['estimated_costs'] for r in rows),'legacy_trades_without_cost_model':sum(r['entry_fee']==0 for r in rows),'drawdown':max((r['peak']-r['equity'] for r in equity),default=None),'equity_observations':len(equity),'rule_adherence_pct':sum(r['followed_rules']=='yes' for r in reviewed)/len(reviewed)*100 if reviewed else None,'reviewed_trades':len(reviewed),'data_failures':failures,'edge_validated':False,'automatic_strategy_changes':False}
    con.execute('INSERT INTO weekly_reports VALUES (?,?,?)',(week,utcnow(),json.dumps(report)));con.commit();con.close()
    emit('Performance Reviewer','Supervisor','WEEKLY_DECISION','REVIEW','Weekly decision: '+decision,report)
    return report

@app.get('/weekly-reports')
def weekly_reports():
    con=db();rows=[dict(r) for r in con.execute('SELECT * FROM weekly_reports ORDER BY week DESC LIMIT 52')];con.close()
    return [dict(r,payload=json.loads(r['payload'])) for r in rows]


def register_forward_plan():
    con=db();proto=json.dumps(PROTOCOL,sort_keys=True)
    con.execute("UPDATE forward_plans SET status='INTERRUPTED' WHERE status='RUNNING'")
    con.execute('INSERT OR IGNORE INTO forward_plans VALUES (?,?,?,?,?,?)',('forward-SPY-'+PROTOCOL['version'],'SPY',utcnow(),proto,'COLLECTING',None));con.commit();con.close()

@app.get('/forward-plans')
def forward_plans():
    con=db();rows=[dict(r) for r in con.execute('SELECT * FROM forward_plans ORDER BY registered_at DESC')]
    for r in rows:
        bars=con.execute("SELECT bar_time FROM candles WHERE symbol=? AND interval='4h' ORDER BY bar_time",(r['symbol'],)).fetchall()
        r['future_completed_bars']=sum(datetime.fromisoformat(b['bar_time']).replace(tzinfo=ZoneInfo('America/New_York')).astimezone(timezone.utc)>=datetime.fromisoformat(r['registered_at']) for b in bars)
        r['required_future_bars']=120;r['protocol']=json.loads(r['protocol'])
    con.close();return rows

def maybe_forward_research():
    con=db();plans=con.execute("SELECT * FROM forward_plans WHERE status='COLLECTING'").fetchall()
    for plan in plans:
        if plan['protocol']!=json.dumps(PROTOCOL,sort_keys=True):
            con.execute("UPDATE forward_plans SET status='REVIEW_REQUIRED' WHERE id=?",(plan['id'],));continue
        bars=[dict(r) for r in con.execute("SELECT bar_time AS datetime,open,high,low,close,volume FROM candles WHERE symbol=? AND interval='4h' ORDER BY bar_time",(plan['symbol'],))]
        future=[i for i,b in enumerate(bars) if datetime.fromisoformat(b['datetime']).replace(tzinfo=ZoneInfo('America/New_York')).astimezone(timezone.utc)>=datetime.fromisoformat(plan['registered_at'])]
        if len(future)<120 or future[0]<60:continue
        selected=bars[future[0]-60:future[119]+1];digest=fingerprint(plan['symbol'],selected);rid=str(uuid.uuid4())
        meta={'source':'Future saved free candles, protocol frozen before their opening timestamps','bars':len(selected),'split_index':60,'split_policy':'60 prior warm-up bars; first 120 future completed bars form the test','test_period_reused':False,'later_period_label':'Reserved forward period','dataset_sha256':digest,'predeclared_at':plan['registered_at'],'variants_attempted':8,'edge_validated':False}
        con.execute('INSERT INTO research_runs VALUES (?,?,?,?,?,?,?,?,?,?)',(rid,utcnow(),plan['symbol'],digest,plan['protocol'],selected[60]['datetime'],selected[-1]['datetime'],'RUNNING',json.dumps(meta),json.dumps(selected)))
        con.execute("UPDATE forward_plans SET status='RUNNING',run_id=? WHERE id=?",(rid,plan['id']));con.commit()
        # Protocol, dataset and attempted trial are durable before calculation.
        try:result=dict(meta,**compare(selected,60));state='COMPLETE'
        except Exception as e:result=dict(meta,error=type(e).__name__);state='FAILED'
        con.execute('UPDATE research_runs SET status=?,payload=? WHERE id=?',(state,json.dumps(result),rid))
        con.execute('UPDATE forward_plans SET status=?,run_id=? WHERE id=?',(state,rid,plan['id']))
        con.commit()
        emit('Performance Reviewer','Research Lab','FORWARD_EXPERIMENT',state,'Reserved future-period comparisons retained; no activation.',{'id':rid,'plan_id':plan['id']})
    con.commit();con.close()


def build_analysis(symbol,bars=None,knowledge=None):
    con=db()
    if bars is None:bars=list(reversed([dict(r) for r in con.execute("SELECT bar_time AS datetime,open,high,low,close,volume FROM candles WHERE symbol=? AND interval='4h' ORDER BY bar_time DESC LIMIT 100",(symbol,))]))
    market=list(reversed([dict(r) for r in con.execute("SELECT bar_time AS datetime,open,high,low,close,volume FROM candles WHERE symbol='SPY' AND interval='4h' ORDER BY bar_time DESC LIMIT 600")]))
    con.close()
    try:return analyse(symbol,bars,market,knowledge=knowledge if knowledge is not None else knowledge_for_agent('Analyst',True))
    except (ValueError,KeyError,TypeError,OverflowError):return {'version':ANALYST_VERSION,'symbol':symbol,'status':'INVALID_DATA','summary':'Analysis unavailable: saved candle validation failed.','knowledge':knowledge_for_agent('Analyst',True)}

@atomic
def save_analysis(report):
    if not report.get('bar_time') or not report.get('context_hash'):return
    con=db();con.execute('INSERT OR IGNORE INTO analyst_reports VALUES (?,?,?,?,?,?)',(report['symbol'],report['bar_time'],report['version'],report['context_hash'],utcnow(),json.dumps(report)));con.commit();con.close()

def seed_analyst_reports():
    for symbol in INSTRUMENTS:save_analysis(build_analysis(symbol))

@app.get('/analyst-analysis')
def analyst_analysis():
    knowledge=knowledge_for_agent('Analyst',True);con=db()
    closed=[dict(r) for r in con.execute("SELECT id,status,exit_time,planned_loss,realized_pnl FROM positions WHERE status='CLOSED' ORDER BY exit_time DESC LIMIT 100")]
    total=con.execute("SELECT COUNT(*) FROM positions WHERE status='CLOSED'").fetchone()[0];con.close()
    return {'version':ANALYST_VERSION,'parameters':ANALYST_PARAMETERS,'reports':[build_analysis(symbol,knowledge=knowledge) for symbol in INSTRUMENTS if INSTRUMENTS[symbol]['paper_enabled']],
            'knowledge':knowledge,'memory':dict(evidence_review(closed),total_closed_trades=total,sample_scope='Most recent up to 100 closed paper trades; current ledger may include legacy entry costs.'),
            'policy':'Descriptive tools and versioned reference context. Active Trend Breakout v1, risk limits and reserved research protocol are unchanged. No model fine-tuning or automatic lesson execution.','extra_provider_requests':0}

@app.get('/analyst-analysis/{symbol}/history')
def analyst_analysis_history(symbol: str,limit:int=20):
    if symbol not in INSTRUMENTS:raise HTTPException(404,'Unknown instrument.')
    con=db();rows=con.execute('SELECT payload FROM analyst_reports WHERE symbol=? ORDER BY created_at DESC LIMIT ?',(symbol,min(max(limit,1),50))).fetchall();con.close();return [json.loads(r['payload']) for r in rows]

@app.get('/analyst',response_class=HTMLResponse)
def analyst_page():
    from pathlib import Path
    return HTMLResponse(Path(__file__).with_name('analyst.html').read_text(encoding='utf-8'))
