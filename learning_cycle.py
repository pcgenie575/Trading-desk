"""Weekly evidence review and approval queue. Never mutates trading policy."""
import hashlib,json,threading
from dataclasses import replace,asdict
from datetime import datetime,timedelta
from zoneinfo import ZoneInfo
from pathlib import Path
from fastapi import Header,HTTPException
from fastapi.responses import HTMLResponse
from pydantic import BaseModel,Field

VERSION='controlled-learning-v1'
from research_engine import simulate,validate_bars,fingerprint,PROTOCOL as RESEARCH_PROTOCOL
from execution import COSTS
STRESS=replace(COSTS,half_spread_bps=COSTS.half_spread_bps*2,slippage_bps=COSTS.slippage_bps*2,fee_per_order=COSTS.fee_per_order*2,fx_bps=COSTS.fx_bps*2)
TEST_PROTOCOL={'version':VERSION,'symbol':'SPY','entry':'breakout','candidate_exit':'trailing','baseline_exit':'full',
 'rules':RESEARCH_PROTOCOL,'costs':asdict(COSTS),'stress':asdict(STRESS),'development_fraction':.7,
 'future_bars':1000,'selection':'One fixed exit hypothesis, one attempt; no tuning or replacements after failure.',
 'limitation':'Single-instrument simulation; approval for changing the multi-position desk additionally requires portfolio validation. No automatic activation.'}
POLICY={'version':VERSION,'review_timezone':'America/New_York','min_observation_trades':30,
 'promotion':{'min_trades':100,'min_stress_expectancy_r':.15,'min_profit_factor':1.3,'max_two_winner_share':.35},
 'automatic_strategy_changes':False,'extra_provider_requests':0,
 'scope':'Deterministic reviews and draft lessons. Research uses separately registered fixed experiments; never parameter search after a win or loss.'}

def screen(metrics):
    if not metrics:return {'passed':False,'failures':['No completed cost-stress evidence.']}
    trades=metrics.get('trade_log',[]);profit=sum(max(0,t.get('pnl',0)) for t in trades)
    loss=-sum(min(0,t.get('pnl',0)) for t in trades)
    top=sum(sorted((max(0,t.get('pnl',0)) for t in trades),reverse=True)[:2])
    failures=[]
    if metrics.get('max_drawdown',0)>250:failures.append('Drawdown exceeds the fixed account guardrail.')
    if len(trades)<100:failures.append('Fewer than 100 closed trades.')
    if metrics.get('expectancy_r') is None or metrics['expectancy_r']<.15:failures.append('Stress expectancy below +0.15R.')
    if loss<=0 or profit/loss<1.3:failures.append('Profit factor insufficient or unestimable.')
    if not profit or top/profit>.35:failures.append('Results depend too heavily on two winners.')
    if sum(t.get('pnl',0) for t in trades)-top<=0:failures.append('Profit disappears without the two largest winners.')
    return {'passed':not failures,'failures':failures}

def review(rows,report):
    closed=[r for r in rows if r.get('status')=='CLOSED']
    eligible=[r for r in closed if r.get('planned_loss',0)>0 and r.get('realized_pnl') is not None]
    pnl=sum(r.get('realized_pnl') or 0 for r in closed)
    sufficient=len(closed)>=POLICY['min_observation_trades']
    return {'closed_trades':len(closed),'eligible_r_trades':len(eligible),'net_realized_pnl':pnl,
      'mean_r':sum(r['realized_pnl']/r['planned_loss'] for r in eligible)/len(eligible) if eligible else None,
      'decision':'INVESTIGATE' if report.get('data_failures') or report.get('decision')=='pause' else 'REVIEW_RESEARCH' if sufficient else 'COLLECT_MORE',
      'lesson':'Treat data revisions as a reliability issue, not a trading outcome.' if report.get('data_failures') or report.get('decision')=='pause' else 'Do not infer an edge from open gains or a small closed-trade sample.' if not sufficient else 'Compare net R, costs, drawdown and concentration before proposing a change.',
      'hypothesis': 'Review the existing fixed ETF diversification and exit experiments; do not invent new settings from this sample.' if sufficient else None,
      'limitations':['Observational review, not causation or model training.','Legacy cost/context omissions remain unknown.','No position, risk limit or entry freeze is changed.']}

def install(app,s):
    busy=threading.Lock()
    def init():
        c=s['db']();c.executescript('CREATE TABLE IF NOT EXISTS learning_cycles(week TEXT PRIMARY KEY,ts TEXT,payload TEXT); CREATE TABLE IF NOT EXISTS learning_approvals(id TEXT PRIMARY KEY,ts TEXT,cycle_week TEXT,evidence_hash TEXT,decision TEXT,note TEXT); CREATE TABLE IF NOT EXISTS learning_tests(id TEXT PRIMARY KEY,registered_at TEXT,status TEXT,protocol TEXT,dataset TEXT,payload TEXT);');c.commit();c.close()
    def test_tick():
        # Isolated cached-data work outside the trading lock. No provider or ledger writes.
        c=s['db']()
        try:
            job=c.execute('SELECT * FROM learning_tests WHERE id=?',(VERSION,)).fetchone()
            if s['get_state']()['frozen']:c.close();return
            if not job:
                if c.execute("SELECT COUNT(*) FROM positions WHERE status='CLOSED'").fetchone()[0]<30:c.close();return
                bars=[dict(r) for r in c.execute("SELECT bar_time AS datetime,open,high,low,close,volume FROM candles WHERE symbol='SPY' AND interval='4h' ORDER BY bar_time")][-5000:]
                if len(bars)<180:c.close();return
                try:
                    validate_bars(bars)
                    quality=s['assess_quality']('SPY',bars)
                    if not quality.get('entry_allowed'):c.close();return
                except (ValueError,KeyError,TypeError):c.close();return
                proto=dict(TEST_PROTOCOL,dataset_hash=fingerprint('SPY',bars),quality=quality)
                c.execute('INSERT INTO learning_tests VALUES (?,?,?,?,?,?)',(VERSION,s['utcnow'](),'DEVELOPMENT_RUNNING',json.dumps(proto),json.dumps(bars),'{}'));c.commit()
                job=c.execute('SELECT * FROM learning_tests WHERE id=?',(VERSION,)).fetchone()
            job=dict(job);p=json.loads(job['payload'])
            proto=json.loads(job['protocol']);expected=json.loads(json.dumps(TEST_PROTOCOL))
            if any(proto.get(k)!=v for k,v in expected.items()):
                c.execute('UPDATE learning_tests SET status=? WHERE id=?',('PROTOCOL_BLOCKED',VERSION));c.commit();c.close();return
            if job['status']=='DEVELOPMENT_RUNNING':
                bars=json.loads(job['dataset']);split=int(len(bars)*.7)
                if fingerprint('SPY',bars)!=proto.get('dataset_hash'):
                    c.execute('UPDATE learning_tests SET status=? WHERE id=?',('DATA_BLOCKED',VERSION));c.commit();c.close();return
                candidate=simulate(bars[:split],50,'breakout','trailing',STRESS)
                baseline=simulate(bars[:split],50,'breakout','full',STRESS)
                gate=screen(candidate);improved=candidate['expectancy_r'] is not None and baseline['expectancy_r'] is not None and candidate['expectancy_r']>baseline['expectancy_r'] and candidate['max_drawdown']<=baseline['max_drawdown']
                p={'development_stress':candidate,'baseline_stress':baseline,'development_normal':simulate(bars[:split],50,'breakout','trailing'), 'screen':gate,'improved_over_baseline':improved,'later_period_scored':False,'historical_data_reused':True}
                status='FORWARD_COLLECTING' if gate['passed'] and improved else 'REJECTED'
                if status=='FORWARD_COLLECTING':p['forward_registered_at']=s['utcnow']()
                c.execute('UPDATE learning_tests SET status=?,payload=? WHERE id=?',(status,json.dumps(p),VERSION));c.commit()
            elif job['status']=='FORWARD_COLLECTING':
                bars=[dict(r) for r in c.execute("SELECT bar_time AS datetime,open,high,low,close,volume FROM candles WHERE symbol='SPY' AND interval='4h' ORDER BY bar_time")]
                registered=datetime.fromisoformat(p['forward_registered_at'])
                future=[i for i,b in enumerate(bars) if datetime.fromisoformat(b['datetime']).replace(tzinfo=ZoneInfo('America/New_York')).astimezone(ZoneInfo('UTC'))>=registered]
                if len(future)>=1000 and future[0]>=50:
                    selected=bars[future[0]-50:future[999]+1];validate_bars(selected)
                    if s['assess_quality']('SPY',selected).get('entry_allowed'):
                        candidate=simulate(selected,50,'breakout','trailing',STRESS);baseline=simulate(selected,50,'breakout','full',STRESS)
                        p.update(forward_stress=candidate,forward_baseline_stress=baseline,forward_normal=simulate(selected,50,'breakout','trailing'),forward_dataset_hash=fingerprint('SPY',selected))
                        gate=screen(candidate);p['forward_screen']=gate
                        improved=baseline['expectancy_r'] is not None and candidate['expectancy_r'] is not None and candidate['expectancy_r']>baseline['expectancy_r'] and candidate['max_drawdown']<=baseline['max_drawdown']
                        status='PORTFOLIO_REVIEW_REQUIRED' if gate['passed'] and improved else 'REJECTED'
                    retained={'development':json.loads(job['dataset']),'forward':selected}
                    c.execute('UPDATE learning_tests SET status=?,payload=?,dataset=? WHERE id=?',(status,json.dumps(p),json.dumps(retained),VERSION));c.commit()
            c.close()
        except Exception:
            c.execute('UPDATE learning_tests SET status=? WHERE id=?',('FAILED',VERSION));c.commit();raise
        finally:c.close()
    def tick():
        if not busy.acquire(False):return
        try:
            init();s['maybe_weekly_report']()
            c=s['db']();reports=[dict(r) for r in c.execute('SELECT * FROM weekly_reports ORDER BY week')]
            # One immutable review per completed week; restart never duplicates a lesson.
            for record in reports:
                week=record['week']
                if c.execute('SELECT 1 FROM learning_cycles WHERE week=?',(week,)).fetchone():continue
                end=(datetime.fromisoformat(week)+timedelta(days=7)).date().isoformat()
                rows=[dict(r) for r in c.execute("SELECT * FROM positions WHERE status='CLOSED' AND exit_time<?",(end,))]
                result=review(rows,json.loads(record['payload']));result.update(week=week,policy=POLICY,evidence_report=record['payload'],created_at=s['utcnow']())
                result['evidence_hash']=hashlib.sha256(json.dumps(result,sort_keys=True).encode()).hexdigest()
                c.execute('INSERT INTO learning_cycles VALUES (?,?,?)',(week,s['utcnow'](),json.dumps(result)))
                entry='auto-learning-'+week;ts=s['utcnow']()
                if c.execute('SELECT COUNT(*) FROM knowledge_entries').fetchone()[0]<250:
                    c.execute('INSERT OR IGNORE INTO knowledge_entries VALUES (?,?,?,?,?,?,?,?,?,?,?)',(entry,1,ts,'Weekly experience review '+week,'lesson','in_review',result['lesson'],json.dumps({'cycle':week,'evidence_hash':result['evidence_hash'],'closed_trades':len(rows)}),'',json.dumps(['Analyst','Performance Reviewer','Supervisor']),0))
                    row=c.execute('SELECT * FROM knowledge_entries WHERE id=?',(entry,)).fetchone()
                    c.execute('INSERT OR IGNORE INTO knowledge_history VALUES (?,?,?,?)',(entry,1,ts,json.dumps(dict(row))))
                c.commit();s['emit']('Performance Reviewer','Research Lab','LEARNING_REVIEW','REVIEW','Weekly experience review and draft lesson recorded.',{'week':week,'decision':result['decision']})
            c.close()
            test_tick()
        finally:busy.release()
    def overview():
        init();c=s['db']();cycles=[json.loads(r['payload']) for r in c.execute('SELECT payload FROM learning_cycles ORDER BY week DESC LIMIT 52')]
        approvals=[dict(r) for r in c.execute('SELECT * FROM learning_approvals ORDER BY ts DESC LIMIT 100')]
        experiments=[dict(r) for r in c.execute("SELECT id,kind,status,payload FROM edge_lab_runs WHERE kind='ETF' ORDER BY ts DESC LIMIT 10")]
        forwards=[dict(r) for r in c.execute('SELECT id,symbol,registered_at,status,run_id FROM forward_plans ORDER BY registered_at DESC')]
        tests=[dict(r) for r in c.execute('SELECT id,registered_at,status,protocol,payload FROM learning_tests')];c.close()
        for t in tests:
            t['protocol']=json.loads(t['protocol']);t['payload']=json.loads(t['payload'])
        research=[]
        for r in experiments:
            p=json.loads(r['payload']);result=p.get('result') or {};gate=screen(result.get('stress'))
            # Preserve the registered engine's stronger basket/drawdown gate too.
            eligible=gate['passed'] and result.get('forward_paper_eligible') is True
            research.append({'id':r['id'],'status':r['status'],'screen':gate,'forward_eligible':eligible,'automatic_activation':False})
        return {'policy':POLICY,'cycles':cycles,'research':research,'forward_tests':forwards,'automatic_tests':tests,'approvals':approvals,
          'activation_status':'Operator software change required after qualifying research and forward evidence; this service cannot modify the active strategy.'}
    @app.get('/learning')
    def page():return HTMLResponse(Path(__file__).with_name('learning.html').read_text(encoding='utf8'))
    @app.get('/learning-cycle')
    def state():return overview()
    class Approval(BaseModel):
        week:str
        evidence_hash:str
        note:str=Field(min_length=3,max_length=1000)
    @app.post('/learning-cycle/approve-lesson')
    def approve(payload:Approval,x_control_token:str|None=Header(default=None)):
        s['require_control'](x_control_token);init()
        with s['_cycle_lock']:
            c=s['db']();row=c.execute('SELECT payload FROM learning_cycles WHERE week=?',(payload.week,)).fetchone();c.close()
            if not row or json.loads(row['payload'])['evidence_hash']!=payload.evidence_hash:raise HTTPException(409,'Reload the exact recorded evidence before approval.')
            c=s['db']();old=c.execute('SELECT * FROM knowledge_entries WHERE id=?',('auto-learning-'+payload.week,)).fetchone();c.close()
            if not old:raise HTTPException(409,'No draft lesson is available.')
            if old['status']=='approved':return {'status':'ALREADY_APPROVED','strategy_changed':False}
            if old['version']!=1 or old['content']!=json.loads(row['payload'])['lesson']:raise HTTPException(409,'The lesson was edited; review its current version in the knowledge base instead.')
            k=s['KnowledgeInput'](expected_version=old['version'],title=old['title'],kind='lesson',status='approved',content=old['content'],evidence=old['evidence']+'\nOperator review: '+payload.note,agents=json.loads(old['agents']))
            s['write_knowledge'](old['id'],k,dict(old))
            c=s['db']();c.execute('INSERT INTO learning_approvals VALUES (?,?,?,?,?,?)',(old['id'],s['utcnow'](),payload.week,payload.evidence_hash,'LESSON_APPROVED',payload.note));c.commit();c.close()
            return {'status':'LESSON_APPROVED','strategy_changed':False}
    return {'tick':tick,'overview':overview}
