"""Read-only quality comparisons for isolated, unapproved historical sources."""
import copy,math
import json,hashlib
from pathlib import Path
from html import escape
from datetime import datetime,timezone
from zoneinfo import ZoneInfo
from daily_research import validate_daily

START='2006-01-01';END='2015-12-31';PRICE_TOLERANCE=.02;EVENT_TOLERANCE=.0001
VERSION='free-source-probe-v1'
IDS=('Yahoo-GSG','Yahoo-IEF','Stooq-GSG','Stooq-IEF')

def digest(x):return hashlib.sha256(json.dumps(x,sort_keys=True,separators=(',',':')).encode()).hexdigest()

def source_url(provider,symbol):
    if provider=='Yahoo':return 'https://query1.finance.yahoo.com/v8/finance/chart/'+symbol+'?period1=1136073600&period2=1451606400&interval=1d&events=div%2Csplits'
    if provider=='Stooq':return 'https://stooq.com/q/d/l/?s='+symbol.lower()+'.us&i=d&d1=20060101&d2=20151231'
    raise ValueError('Unsupported source.')

def parse_yahoo(payload,symbol):
    chart=payload['chart']
    if chart.get('error') or len(chart.get('result') or [])!=1:raise ValueError('A single successful chart result is required.')
    r=chart['result'][0];m=r['meta']
    if m.get('symbol')!=symbol or m.get('currency')!='USD' or m.get('instrumentType')!='ETF' or m.get('exchangeTimezoneName')!='America/New_York' or m.get('dataGranularity')!='1d':raise ValueError('Daily USD ETF identity mismatch.')
    times=r['timestamp'];q=r['indicators']['quote'][0];adjusted=r['indicators']['adjclose'][0]['adjclose']
    if not times or any(len(q[k])!=len(times) for k in ('open','high','low','close','volume')) or len(adjusted)!=len(times):raise ValueError('Incomplete parallel arrays.')
    def day(t):return datetime.fromtimestamp(t,timezone.utc).astimezone(ZoneInfo('America/New_York')).date().isoformat()
    bars=[];adj={}
    for i,t in enumerate(times):
        values=[q[k][i] for k in ('open','high','low','close','volume')]+[adjusted[i]]
        if any(isinstance(v,bool) or not isinstance(v,(int,float)) or not math.isfinite(v) for v in values):raise ValueError('Null or invalid historical value; no silent row dropping.')
        d=day(t);bars.append(dict(datetime=d,**{k:float(q[k][i]) for k in ('open','high','low','close','volume')}));adj[d]=float(adjusted[i])
        if adj[d]<=0:raise ValueError('Invalid adjusted close.')
    validate_daily(bars,START,END)
    events=[]
    for event in r.get('events',{}).get('dividends',{}).values():
        amount=event['amount'];d=day(event['date'])
        if not START<=d<=END or isinstance(amount,bool) or not isinstance(amount,(int,float)) or not math.isfinite(amount) or amount<0:raise ValueError('Invalid dividend event.')
        events.append({'ex_date':d,'amount':float(amount)})
    splits=copy.deepcopy(r.get('events',{}).get('splits',{}))
    return {'bars':bars,'adjusted_close':adj,'dividends':events,'splits':splits,'meta':{k:m.get(k) for k in ('symbol','currency','exchangeName','fullExchangeName','instrumentType','exchangeTimezoneName','dataGranularity','firstTradeDate')},'fill_basis_verified':False}

def compare_prices(candidate,saved):
    a={b['datetime']:b for b in candidate};b={x['datetime']:x for x in saved};days=sorted(a.keys()&b.keys())
    by_field={};mismatch_dates=set()
    for k in ('open','high','low','close'):
        changes=[(d,abs(a[d][k]-b[d][k])) for d in days]
        bad=[(d,v) for d,v in changes if v>PRICE_TOLERANCE+1e-10];mismatch_dates.update(d for d,_ in bad)
        by_field[k]={'compared_sessions':len(days),'mismatches':len(bad),'max_absolute_difference':max((v for _,v in changes),default=None)}
    years={y:sum(d.startswith(y) for d in mismatch_dates) for y in sorted({d[:4] for d in mismatch_dates})}
    return {'tolerance_usd':PRICE_TOLERANCE,'overlap_sessions':len(days),'mismatched_sessions':len(mismatch_dates),'mismatches_by_year':years,'first_mismatch_dates':sorted(mismatch_dates)[:5],'fields':by_field,'candidate_only_sessions':len(a.keys()-b.keys()),'saved_only_sessions':len(b.keys()-a.keys()),'all_overlapping_ohlc_within_tolerance':bool(days) and not mismatch_dates,'note':'Agreement is a diagnostic, not proof of independence, raw adjustment semantics or full accuracy.'}

def compare_events(candidate,issuer):
    def amounts(events):
        result={}
        for e in events:
            if START<=e['ex_date']<=END:result[e['ex_date']]=result.get(e['ex_date'],0)+e['amount']
        return result
    a=amounts(candidate);b=amounts([e for e in issuer.get('events',[]) if e.get('type')=='distribution'])
    common=a.keys()&b.keys();bad=sorted(d for d in common if abs(a[d]-b[d])>EVENT_TOLERANCE)
    rounded=sum(abs(a[d]*1000-round(a[d]*1000))<1e-7 and abs(a[d]-b[d])<=.0005000001 for d in bad)
    return {'issuer_coverage_verified':issuer.get('coverage_verified') is True,'candidate_events':len(a),'issuer_events':len(b),'matched_dates':len(common),'amount_discrepancies':len(bad),'amount_discrepancy_dates':bad[:8],'discrepancies_compatible_with_three_decimal_rounding':rounded,'unexplained_amount_discrepancies':len(bad)-rounded,'missing_candidate_dates':sorted(b.keys()-a.keys()),'extra_candidate_dates':sorted(a.keys()-b.keys()),'tolerance_usd':EVENT_TOLERANCE,'reconciled':issuer.get('coverage_verified') is True and bool(b) and not bad and a.keys()==b.keys(),'note':'Rounding compatibility is descriptive only; the strict event tolerance is unchanged. Ex-date amounts do not verify payment dates, raw prices or historical availability.'}

def diagnose_adjustments(parsed,saved,issuer):
    """Check independently returned adj-close jumps on issuer ex-dates only."""
    raw={b['datetime']:b for b in parsed['bars']};adj=parsed['adjusted_close'];dates=sorted(raw)
    previous={d:p for p,d in zip(dates,dates[1:])};events={}
    for e in issuer.get('events',[]):
        if e.get('type')=='distribution' and START<=e['ex_date']<=END:events[e['ex_date']]=events.get(e['ex_date'],0)+e['amount']
    checked=[];missing=[];bad=[]
    for d,amount in events.items():
        prior=previous.get(d)
        if not prior:missing.append(d);continue
        expected=1-amount/raw[prior]['close'];observed=(raw[d]['close']/adj[d])/(raw[prior]['close']/adj[prior])
        checked.append(d)
        if expected<=0 or not math.isclose(observed,expected,rel_tol=8e-4,abs_tol=8e-4):bad.append(d)
    return {'issuer_dates_checked':len(checked),'mismatches':len(bad),'first_mismatch_dates':sorted(bad)[:8],'missing_event_dates':sorted(missing),'same_original_factor_tolerance':.0008,'note':'This diagnostic uses separately retained Yahoo adjusted closes. It does not repair the original Twelve Data series.'}

def profile(parsed,saved,reference,issuer,symbol):
    bars=parsed['bars'];first=bars[0]['datetime'];last=bars[-1]['datetime'];dates={b['datetime'] for b in bars}
    expected={d for d in reference if first<=d<=END}
    return {'symbol':symbol,'source_metadata':parsed['meta'],'observations':len(bars),'first':first,'last':last,'reference_proxy':'Saved SPY session dates; not a certified historical exchange calendar.','missing_reference_sessions':sorted(expected-dates),'extra_reference_sessions':sorted(dates-expected),'registered_start_requirement_met':first<=('2006-07-20' if symbol=='GSG' else '2006-01-10'),'registered_end_requirement_met':last==END,'ohlc_comparison':compare_prices(bars,saved),'distribution_comparison':compare_events(parsed['dividends'],issuer),'adjusted_close_diagnostic':diagnose_adjustments(parsed,saved,issuer),'reported_splits':len(parsed['splits']),'fill_basis_verified':False,'production_eligible':False,'original_inputs_replaced':False,'performance_calculation_allowed':False,'decision':'QUARANTINED_SOURCE_CANDIDATE'}

def build_review(plan,attempts,responses,original):
    if plan['version']!=VERSION or plan['max_requests']!=4 or plan['retry_allowed'] is not False:raise ValueError('Fixed four-request sourcing plan required.')
    if len(attempts)!=4 or {a['id'] for a in attempts}!=set(IDS) or len(plan['requests'])!=4:raise ValueError('All original attempts must be retained once.')
    planned={a['id']:a for a in plan['requests']}
    if set(planned)!=set(IDS):raise ValueError('Unexpected source request.')
    results=[]
    for a in attempts:
        item=planned[a['id']]
        if any(a[k]!=item[k] for k in ('provider','symbol','url')) or a['id']!=a['provider']+'-'+a['symbol']:raise ValueError('Attempt identity differs from registered request.')
        if a['url']!=source_url(a['provider'],a['symbol']):raise ValueError('Unexpected publisher URL or requested period.')
        r={k:v for k,v in a.items() if k!='filename'}
        if a['status']=='RECEIVED':
            body=responses[a['id']]
            if len(body)>6000000 or len(body)!=a['bytes'] or hashlib.sha256(body).hexdigest()!=a['sha256']:raise ValueError('Retained response hash or size differs.')
            if a['provider']=='Yahoo':
                try:
                    parsed=parse_yahoo(json.loads(body),a['symbol'])
                    r['profile']=profile(parsed,original['pages'][a['symbol']+':none']['bars'],original['reference'],original['distributions'][a['symbol']],a['symbol']);r['status']='PROFILED_NOT_APPROVED'
                except (ValueError,KeyError,TypeError,IndexError) as ex:r.update(status='INVALID_DATA',error_type=type(ex).__name__,reason=str(ex)[:200])
            else:
                html=b'<html' in body.lower() or b'<!doctype html' in body.lower()
                r.update(status='NOT_PRICE_DATA' if html else 'UNREVIEWED_FORMAT',reason='The retained response is HTML rather than historical CSV. No access restriction or challenge bypass attempted.' if html else 'This fixed source probe has no approved parser for the retained format.')
        results.append(r)
    return {'version':VERSION,'plan':copy.deepcopy(plan),'source_dataset_hash':digest(original),'results':results,'public_source_requests':4,'twelve_data_requests':0,'original_inputs_replaced':False,'performance_calculation_allowed':False,'activation_allowed':False,'decision':'INVESTIGATE_SOURCES','limitations':['This is source verification on previously inspected development dates, not a new strategy trial or validation.','Plan saved locally before four public requests. Server recording occurs after collection; no claim of server preregistration before data.','Publisher agreement does not establish independent underlying sources or certified raw-price semantics.','Yahoo dividend rounding is descriptive; strict amount and original factor tolerances remain unchanged.','Returned source metadata is current and is not a historical instrument master. No current quote is used in a historical calculation.','The GSG distribution worksheet remains unverified in the original dataset; the separate issuer supplement does not silently change it.']}

def render(report):
    body='<p>State: '+escape(report['status'])+'. Original research and trading controls remain unchanged.</p>'
    if report['status']=='RECORDED':
        rows=[]
        for r in report['summary']['results']:
            p=r.get('profile');details=r.get('reason',r['status'])
            if p:
                details=f"{p['observations']} sessions; {p['first']} to {p['last']}. {p['ohlc_comparison']['mismatched_sessions']} overlapping OHLC mismatches. Registered start requirement: {'met' if p['registered_start_requirement_met'] else 'not met'}."
            rows.append('<tr><td>'+escape(r['id'])+'</td><td>'+escape(r['status'])+'</td><td>'+escape(details)+'</td></tr>')
        body+='<section><h2>Four bounded source checks</h2><div class="scroll"><table><thead><tr><th>Source</th><th>Decision</th><th>Evidence</th></tr></thead><tbody>'+''.join(rows)+'</tbody></table></div></section>'
        body+='<section><h2>What these checks establish</h2><p>The OHLC comparison measures agreement with saved prices. The adjusted-close diagnostic checks issuer ex-dates at the existing factor tolerance. Dividend rounding remains separately reported; these checks do not certify a replacement feed.</p><p>No source is approved for fills, no dataset is replaced, and no backtest is run. Read the coverage and discrepancy counts in the full summary before considering a separately registered input revision.</p></section><section><h2>Full quality summary</h2><pre>'+escape(json.dumps(report['summary'],indent=2))+'</pre></section>'
    return '<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Price source review · Trading Desk</title><style>:root{color-scheme:dark}*{box-sizing:border-box}body{background:#09131e;color:#eaf2fb;font:15px system-ui;margin:0}main{max-width:1150px;padding:28px;margin:auto}nav{display:flex;gap:22px;flex-wrap:wrap}a{color:#71e2c0}p{color:#a4b4c9;line-height:1.7}section{background:#142231;border:1px solid #294054;padding:24px;margin:20px 0;border-radius:16px}table{border-collapse:collapse;width:100%;min-width:700px}td,th{text-align:left;border-bottom:1px solid #294054;padding:14px}.scroll{overflow:auto}pre{white-space:pre-wrap;overflow-wrap:anywhere;font-size:12px}:focus-visible{outline:2px solid #71e2c0}@media(max-width:700px){main{padding:16px}section{padding:18px}}</style><main><nav><a href="/">Trading desk</a><a href="/etf-research">ETF research</a><a href="/issuer-sources">Issuer audit</a><a href="/price-source-review">Quality JSON</a></nav><h1>Free price sources, checked.</h1>'+body+'</main></html>'

def install(app,s):
    from fastapi import HTTPException,Header
    from fastapi.responses import HTMLResponse
    @app.on_event('startup')
    def init():
        c=s['db']();c.execute('CREATE TABLE IF NOT EXISTS price_source_reviews(id TEXT PRIMARY KEY,recorded_at TEXT,protocol TEXT,payload TEXT)');c.commit();c.close()
    def overview():
        c=s['db']();row=c.execute('SELECT * FROM price_source_reviews WHERE id=?',(VERSION,)).fetchone();c.close()
        if not row:return {'id':VERSION,'status':'NOT_RECORDED','activation_allowed':False}
        p=json.loads(row['payload']);result={'id':VERSION,'status':'RECORDED','recorded_at':row['recorded_at'],'protocol':json.loads(row['protocol']),'summary':p['summary'],'activation_allowed':False,'retained_responses_private':True}
        try:
            for a in p['summary']['results']:
                if a.get('sha256') and hashlib.sha256(p['responses'][a['id']].encode()).hexdigest()!=a['sha256']:raise ValueError('Source hash mismatch.')
            if digest(p['summary'])!=result['protocol']['summary_hash']:raise ValueError('Summary hash mismatch.')
            result['retained_integrity']=True
        except (ValueError,KeyError,TypeError):result.update(status='EVIDENCE_BLOCKED',summary={'error':'Retained source review failed integrity checks.'},retained_integrity=False)
        return result
    @app.get('/price-source-review')
    def state():return overview()
    @app.get('/price-sources')
    def page():return HTMLResponse(render(overview()))
    @app.post('/price-source-review/record')
    def record(x_control_token:str|None=Header(default=None)):
        s['require_control'](x_control_token)
        with s['_cycle_lock']:
            c=s['db']();old=c.execute('SELECT id FROM price_source_reviews WHERE id=?',(VERSION,)).fetchone()
            source=c.execute("SELECT id,dataset FROM edge_lab_runs WHERE kind='ETF' ORDER BY ts DESC LIMIT 1").fetchone();c.close()
            if old:return overview()
            if not source:raise HTTPException(422,'Original ETF dataset required.')
            folder=Path(s['DB']).resolve().parent/'free-source-probe-v1'
            try:
                plan=json.loads((folder/'plan.json').read_text(encoding='utf8'));attempts=json.loads((folder/'attempts.json').read_text(encoding='utf8'))
                responses={k:(folder/(k+'.response')).read_bytes() for k in IDS if any(a['id']==k and a['status']=='RECEIVED' for a in attempts)}
                summary=build_review(plan,attempts,responses,json.loads(source['dataset']))
            except (OSError,ValueError,KeyError,TypeError):raise HTTPException(422,'Complete, matching retained source attempts required; no automatic fetch.')
            protocol={'version':VERSION,'original_etf_id':source['id'],'source_dataset_hash':summary['source_dataset_hash'],'plan_hash':digest(plan),'summary_hash':digest(summary),'source_fingerprint':hashlib.sha256(Path(__file__).read_bytes()).hexdigest()}
            payload={'summary':summary,'responses':{k:v.decode('utf8') for k,v in responses.items()}}
            c=s['db']();c.execute('INSERT INTO price_source_reviews VALUES (?,?,?,?)',(VERSION,s['utcnow'](),json.dumps(protocol),json.dumps(payload)));c.commit();c.close()
        return overview()
    return {'overview':overview}
