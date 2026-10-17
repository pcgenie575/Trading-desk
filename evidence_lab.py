"""Evidence collection only: no strategy activation or operational ledger access."""
import hashlib,json,threading,subprocess,sys,tempfile
from pathlib import Path
from fastapi import Header,HTTPException
from fastapi.responses import HTMLResponse
from profit_evidence import from_database
VERSION='evidence-lab-v1'
OBSERVED={'REJECTED','FILL_REJECTED','CONTRACT_REJECTED','DATA_ENTRY_BLOCKED','ENTRY_SKIPPED','ORDER_EXPIRED','EXIT_QUEUED','FREEZE'}

def digest(x):return hashlib.sha256(json.dumps(x,sort_keys=True).encode()).hexdigest()

def initialise(c):
    c.executescript('''
    CREATE TABLE IF NOT EXISTS execution_evidence(trade_id TEXT,side TEXT,recorded_at TEXT,payload TEXT,PRIMARY KEY(trade_id,side));
    CREATE TABLE IF NOT EXISTS shadow_observations(id TEXT PRIMARY KEY,recorded_at TEXT,symbol TEXT,bar_time TEXT,event TEXT,payload TEXT);
    CREATE TABLE IF NOT EXISTS paired_collection(id TEXT PRIMARY KEY,registered_at TEXT,protocol TEXT);
    CREATE TABLE IF NOT EXISTS paired_observations(plan_id TEXT,symbol TEXT,bar_time TEXT,recorded_at TEXT,payload TEXT,PRIMARY KEY(plan_id,symbol,bar_time));
    CREATE TABLE IF NOT EXISTS engine_replays(id TEXT PRIMARY KEY,registered_at TEXT,status TEXT,protocol TEXT,payload TEXT,dataset TEXT);
    ''')

def record_fill(c,trade_id,side,ts,fill):
    c.execute('INSERT INTO execution_evidence VALUES (?,?,?,?)',(trade_id,side,ts,json.dumps(fill)))

def record_shadow(c,msg,bar_time):
    if msg['type'] not in OBSERVED:return
    d=msg['data'];symbol=d.get('symbol','UNKNOWN')
    # Deduplicate repeated freeze polling; retain distinct proposals and quality incidents.
    key=digest({'symbol':symbol,'bar_time':bar_time,'event':msg['type'],'reason':msg['reason'],'proposal':d.get('proposal_id'),'quality':d.get('context_hash')})
    p={'reason':msg['reason'],'audit_message_id':msg['id'],'observed_at':msg['ts'],'context':d,
       'classification':'EXIT_INTENT' if msg['type']=='EXIT_QUEUED' else 'DATA_OR_OPERATION_BLOCK' if msg['type'] in ('FREEZE','DATA_ENTRY_BLOCKED') else 'UNEXECUTED_DECISION',
       'hypothetical':True,'counterfactual_pnl':None,'limitation':'No assumed fill or missed profit. Later price movement is observational, not causal evidence.'}
    c.execute('INSERT OR IGNORE INTO shadow_observations VALUES (?,?,?,?,?,?)',(key,msg['ts'],symbol,bar_time,msg['type'],json.dumps(p)))

def engine_fingerprint():
    names=['app.py','strategy.py','execution.py','risk_policy.py','exposure.py','decision_contracts.py','data_quality.py','feed_snapshots.py','universe.py','engine_replay.py']
    return {n:hashlib.sha256(Path(__file__).with_name(n).read_bytes()).hexdigest() for n in names}

def paired_protocol(s):
    from learning_cycle import TEST_PROTOCOL
    return {'version':VERSION,'existing_fixed_experiment':TEST_PROTOCOL,'baseline':'Frozen Trend Breakout v1; operational ledger stays separate.',
      'engine':engine_fingerprint(),'rules':s['RULES'],'candidate_orders_allowed':False,
      'gate':'Existing controlled-learning development and forward gates remain mandatory. Collection alone cannot qualify or activate a candidate.',
      'collection':'First validated SPY candle observed after registration whose open is after registration; immutable originals, no historical backfill.'}

def collect(c,s,symbol,bars,observed):
    if symbol!='SPY' or not bars:return
    from data_quality import stamp
    from datetime import datetime
    row=c.execute('SELECT * FROM paired_collection WHERE id=?',(VERSION,)).fetchone()
    if not row:return
    if json.loads(row['protocol'])['engine']!=engine_fingerprint():return
    registered=datetime.fromisoformat(row['registered_at']);b=bars[-1]
    if stamp(b['datetime']).astimezone(registered.tzinfo)<registered:return
    c.execute('INSERT OR IGNORE INTO paired_observations VALUES (?,?,?,?,?)',(VERSION,symbol,b['datetime'],observed,json.dumps(b)))

def readiness(c):
    from etf_diagnostics import diagnose
    from etf_protocol import PROTOCOL
    results=[]
    for r in c.execute("SELECT id,status,protocol,payload,dataset FROM edge_lab_runs WHERE kind='ETF' ORDER BY ts DESC LIMIT 5"):
        p=json.loads(r['payload']);result=p.get('result') or {};data=json.loads(r['dataset'])
        checks=result.get('input_checks',{})
        results.append({'id':r['id'],'status':r['status'],'diagnostics':diagnose(data,checks,PROTOCOL),
          'performance_available':bool(result.get('normal')),'original_result_preserved':True})
    return {'experiments':results,'verified_source_facts':[{'symbol':'IAU','event':'10-for-1 split','effective_date':'2010-06-24','new_per_old':10,
      'source':'https://www.sec.gov/Archives/edgar/data/1278680/000119312510137666/dex991.htm',
      'use':'Independent comparison fact only. Provider event dates must match; this does not clear an existing check.'}],
      'decision':'DATA_BLOCKED' if any(r['status']=='DATA_BLOCKED' for r in results) else 'REVIEW_SAVED_GATES',
      'repair_policy':'New verified data requires a separately versioned input record. Never overwrite old experiments, shorten the period or relax tolerances.',
      'paid_data_allowed':False,'automatic_retry':False}

def install(app,s):
    from funding_study import install as install_funding_study
    install_funding_study(app,s)
    from schedule_study import install as install_schedule_study
    install_schedule_study(app,s)
    from volatility_study import install as install_volatility_study
    install_volatility_study(app,s)
    from issuer_evidence import install as install_issuer_evidence
    install_issuer_evidence(app,s)
    from price_source_review import install as install_price_sources
    install_price_sources(app,s)
    from gsg_forensics import install as install_gsg_forensics
    install_gsg_forensics(app,s)
    from input_revision import install as install_input_revision
    install_input_revision(app,s)
    worker_lock=threading.Lock()
    def setup():
        c=s['db']();initialise(c)
        c.execute('INSERT OR IGNORE INTO paired_collection VALUES (?,?,?)',(VERSION,s['utcnow'](),json.dumps(paired_protocol(s))))
        # A stopped process cannot leave a successful-looking replay in progress.
        c.execute("UPDATE engine_replays SET status='INTERRUPTED' WHERE status='RUNNING'")
        c.commit();c.close()
    @app.on_event('startup')
    def startup():setup()
    def overview():
        c=s['db']();plan=c.execute('SELECT * FROM paired_collection WHERE id=?',(VERSION,)).fetchone()
        frames=c.execute('SELECT COUNT(*) FROM paired_observations WHERE plan_id=?',(VERSION,)).fetchone()[0]
        shadows=[dict(r) for r in c.execute('SELECT * FROM shadow_observations ORDER BY recorded_at DESC LIMIT 100')]
        total=c.execute('SELECT COUNT(*) FROM shadow_observations').fetchone()[0]
        repairs=readiness(c);replays=[dict(r) for r in c.execute('SELECT id,registered_at,status,protocol,payload FROM engine_replays ORDER BY registered_at DESC LIMIT 10')]
        for r in replays:r['protocol']=json.loads(r['protocol']);r['payload']=json.loads(r['payload'])
        for r in shadows:
            r['payload']=json.loads(r['payload']);t=r['bar_time']
            # These bounds start strictly after both the decision and next eligible open.
            from data_quality import stamp,NY
            from datetime import datetime
            after=datetime.fromisoformat(r['recorded_at'])
            anchor=max(t or '',after.astimezone(NY).strftime('%Y-%m-%d %H:%M:%S'))
            bars=[dict(b) for b in c.execute("SELECT bar_time,open,high,low,close FROM candles WHERE symbol=? AND interval='4h' AND bar_time>? ORDER BY bar_time LIMIT 60",(r['symbol'],anchor))]
            bars=[b for b in bars if stamp(b['bar_time']).astimezone(after.tzinfo)>after]
            r['follow_up']={'future_bars':len(bars),'reference':bars[0]['open'] if bars else None,
              'observed_high':max(b['high'] for b in bars) if bars else None,'observed_low':min(b['low'] for b in bars) if bars else None,
              'counterfactual_pnl':None,'note':'Price path only; fills, stops, costs and exposure were not simulated. Revised provider history may differ from original observations.'}
        c.close()
        learning=s['LEARNING_CYCLE']['overview']()
        job=next((j for j in learning['automatic_tests'] if j['id']=='controlled-learning-v1'),None)
        protocol=json.loads(plan['protocol']) if plan else None
        same=bool(protocol) and protocol['engine']==engine_fingerprint()
        return {'version':VERSION,'profit':from_database(s),'shadow':{'total':total,'rows':shadows,'historical_backfill':False},
          'data_readiness':repairs,'paired':{'registered_at':plan['registered_at'] if plan else None,'protocol':protocol,'future_bars':frames,
             'engine_unchanged':same,'status':'PROTOCOL_CHANGED' if plan and not same else job['status'] if job else 'WAITING_DEVELOPMENT_GATE',
             'required_observation_trades':learning['policy']['min_observation_trades'],'candidate_orders_allowed':False,
             'existing_experiment':job,'automatic_activation':False},'replays':replays}
    @app.get('/evidence')
    def page():return HTMLResponse(Path(__file__).with_name('evidence.html').read_text(encoding='utf8'))
    @app.get('/evidence-lab')
    def state():return overview()
    @app.get('/profit-evidence')
    def profit():return from_database(s)
    @app.post('/evidence-lab/replay')
    def replay(x_control_token:str|None=Header(default=None)):
        s['require_control'](x_control_token)
        if not worker_lock.acquire(False):raise HTTPException(409,'An isolated replay is already running.')
        try:
            with s['_cycle_lock']:
                c=s['db']();rows=list(reversed(c.execute('SELECT symbol,ts,payload FROM quality_reports ORDER BY ts DESC LIMIT 500').fetchall()))
                events=[{'symbol':r['symbol'],'observed_at':r['ts'],'bars':json.loads(r['payload'])['input_bars']} for r in rows if '/' not in r['symbol']]
                if not events:c.close();raise HTTPException(422,'No saved US observations to replay.')
                protocol={'version':'recorded-engine-replay-v1','engine':engine_fingerprint(),'dataset_hash':digest(events),
                  'scope':'Recorded provider batches through actual four-hour quality, queue, contract, cost, risk and ledger functions in a separate process/database.',
                  'limitations':['Not the daily development test. Deduplicated reports omit repeated polls.','Historical manual revisions/resumes are not replayed; quarantines remain freezes.','No scheduler outages, actual broker liquidity, taxes, AUD performance or independent historical source certification.','Descriptive diagnostic, never a promotion screen.']}
                rid=digest(protocol);old=c.execute('SELECT id,status FROM engine_replays WHERE id=?',(rid,)).fetchone()
                if old:c.close();worker_lock.release();return dict(old)
                c.execute('INSERT INTO engine_replays VALUES (?,?,?,?,?,?)',(rid,s['utcnow'](),'RUNNING',json.dumps(protocol),'{}',json.dumps(events)));c.commit();c.close()
            def work():
                result={};status='FAILED'
                try:
                    with tempfile.TemporaryDirectory() as td:
                        source=Path(td)/'input.json';source.write_text(json.dumps(events))
                        run=subprocess.run([sys.executable,str(Path(__file__).with_name('engine_replay.py')),str(source)],capture_output=True,text=True,timeout=120)
                        if run.returncode:result={'error':'Isolated replay failed; no live database was opened.'}
                        else:result=json.loads(run.stdout);status='COMPLETE'
                except subprocess.TimeoutExpired:result={'error':'Replay exceeded the fixed 120-second resource limit.'}
                except Exception as ex:result={'error':type(ex).__name__}
                finally:
                    c=s['db']();c.execute('UPDATE engine_replays SET status=?,payload=? WHERE id=?',(status,json.dumps(result),rid));c.commit();c.close();worker_lock.release()
            threading.Thread(target=work,daemon=True,name='isolated-paper-replay').start()
            return {'id':rid,'status':'RUNNING'}
        except Exception:
            if worker_lock.locked():worker_lock.release()
            raise
    return {'setup':setup,'overview':overview}
