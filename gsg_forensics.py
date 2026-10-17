"""Fixed saved-input investigation; source review only, no strategy calculations."""
import json,hashlib,copy,math
from pathlib import Path
from html import escape
from urllib.parse import urlparse
from input_integrity import audit_bars
from price_source_review import parse_yahoo,digest,VERSION as PARENT,PRICE_TOLERANCE

VERSION='gsg-ohlc-forensics-v1'

def facts():return json.loads(Path(__file__).with_name('gsg-quarterly-facts.json').read_text(encoding='utf8'))

def fingerprint():
    return {n:hashlib.sha256(Path(__file__).with_name(n).read_bytes()).hexdigest() for n in ('gsg_forensics.py','input_integrity.py','price_source_review.py','daily_research.py')}

def quarterly(bars,reference):
    rows=[]
    for fact in reference['rows']:
        year=fact['year'];q=fact['quarter'];selected=[b for b in bars if int(b['datetime'][:4])==year and (int(b['datetime'][5:7])-1)//3+1==q]
        row=copy.deepcopy(fact);row.update(sessions=len(selected),intraday_extrema=None,closing_extrema=None,intraday_matches=None,closing_matches=None)
        if selected:
            row['intraday_extrema']={'high':max(b['high'] for b in selected),'low':min(b['low'] for b in selected)}
            row['closing_extrema']={'high':max(b['close'] for b in selected),'low':min(b['close'] for b in selected)}
            for key,metric in (('intraday_matches','intraday_extrema'),('closing_matches','closing_extrema')):
                row[key]=all(abs(row[metric][k]-fact['reported_'+k])<=PRICE_TOLERANCE+1e-10 for k in ('high','low'))
        rows.append(row)
    observed=[r for r in rows if r['sessions']]
    return {'quarters_with_observations':len(observed),'missing_quarters':len(rows)-len(observed),'intraday_extrema_matches':sum(r['intraday_matches'] is True for r in rows),'closing_extrema_matches':sum(r['closing_matches'] is True for r in rows),'tolerance_usd':PRICE_TOLERANCE,'rows':rows,'source_certified':False,'note':'Quarterly aggregate agreement does not establish every daily close, any opening/intraday price, first trading date or historical data availability. Closing-extrema comparison is exploratory; the issuer table label is retained verbatim in the fact metadata.'}

def analyse(original,parent,reference):
    if parent['summary']['source_dataset_hash']!=digest(original):raise ValueError('Original ETF data differs from the retained source review.')
    received=next(x for x in parent['summary']['results'] if x['id']=='Yahoo-GSG')
    text=parent['responses']['Yahoo-GSG']
    if hashlib.sha256(text.encode()).hexdigest()!=received['sha256']:raise ValueError('Parent GSG response hash mismatch.')
    expected={(2006,3),(2006,4)}|{(y,q) for y in range(2007,2011) for q in range(1,5)}
    rows=reference['rows']
    if len(rows)!=18 or {(r['year'],r['quarter']) for r in rows}!=expected:raise ValueError('Exactly the fixed 18 issuer quarters are required.')
    for r in rows:
        u=urlparse(r['source'])
        if u.scheme!='https' or u.netloc!='www.sec.gov' or not u.path.startswith('/Archives/edgar/data/'):raise ValueError('Primary SEC source required.')
        if any(isinstance(r[k],bool) or not isinstance(r[k],(int,float)) or not math.isfinite(r[k]) for k in ('reported_high','reported_low')) or not 0<r['reported_low']<=r['reported_high']:raise ValueError('Invalid transcribed range.')
    candidate=parse_yahoo(json.loads(text),'GSG')['bars'];saved=original['pages']['GSG:none']['bars']
    all_saved={k.split(':')[0]:audit_bars(v['bars']) for k,v in original['pages'].items() if k.endswith(':none')}
    return {'version':VERSION,'decision':'INVESTIGATE_SOURCE_INTEGRITY','saved_gsg':audit_bars(saved),'candidate_gsg':audit_bars(candidate),'other_saved_etf_integrity':all_saved,'quarterly':{'saved':quarterly(saved,reference),'candidate':quarterly(candidate,reference)},'issuer_fact_record':copy.deepcopy(reference),'source_dataset_hash':digest(original),'parent_response_hash':received['sha256'],'additional_price_requests':0,'performance_calculation_allowed':False,'original_inputs_replaced':False,'activation_allowed':False,'limitations':['The flat-run warning is a source-review diagnostic chosen after observing the anomaly, not a validated test of feed accuracy. A flat bar can be legitimate.','No claim is made that the provider fabricated prices or that this series is NAV. The cause has not been independently established.','Both issuer-range interpretations are retained; a matching close range is not certification of raw opening/high/low fills.','GSG still misses the original warm-up cutoff and has unresolved daily discrepancies. All original gates remain closed.','Full issuer filing archives and amendment review are incomplete. Numerical facts were transcribed from accessible primary filing tables.','No strategy, backtest, holdout evaluation, broker connection or source substitution is performed.']}

def render(report):
    body='<p>State: '+escape(report['status'])+'. Source investigation only; original strategy, datasets and limits remain unchanged.</p>'
    if report.get('installed_source_matches') is False or report.get('installed_facts_match') is False:
        body+='<p role="alert">Installed calculation source or issuer facts differ from this retained record. Review the recorded protocol before using these historical diagnostics.</p>'
    if report['status']=='RECORDED':
        p=report['summary'];s=p['saved_gsg'];c=p['candidate_gsg'];rows=[]
        for year in sorted(s['by_year']):
            a=s['by_year'][year];b=c['by_year'].get(year,{})
            rows.append('<tr><td>'+escape(year)+'</td><td>'+str(a['flat_ohlc_sessions'])+' / '+str(a['sessions'])+'</td><td>'+str(b.get('flat_ohlc_sessions','Unknown'))+' / '+str(b.get('sessions','Unknown'))+'</td></tr>')
        body+='<section><h2>Repeated flat daily bars</h2><p>A flat bar reports the same open, high, low and close. Five consecutive observed flat bars trigger a review flag in this diagnostic. A flag is not proof of the cause, and the absence of a flag is not source certification.</p><div class="scroll"><table><thead><tr><th>Year</th><th>Saved GSG flat / total</th><th>Candidate GSG flat / total</th></tr></thead><tbody>'+''.join(rows)+'</tbody></table></div><p>Longest saved run: '+str(s['longest_flat_run_sessions'])+' observed sessions. Sources remain quarantined.</p></section>'
        comparisons=[]
        for name,q in p['quarterly'].items():comparisons.append('<tr><td>'+escape(name)+'</td><td>'+str(q['quarters_with_observations'])+'</td><td>'+str(q['intraday_extrema_matches'])+'</td><td>'+str(q['closing_extrema_matches'])+'</td></tr>')
        body+='<section><h2>Independent issuer range comparison</h2><p>Issuer tables describe quarterly high and low sale prices. Both intraday and closing-extrema comparisons are shown. Closing-extrema matching is an exploratory observation; it does not verify every daily price or any opening fill.</p><div class="scroll"><table><thead><tr><th>Series</th><th>Observed quarters</th><th>Intraday matches</th><th>Closing matches</th></tr></thead><tbody>'+''.join(comparisons)+'</tbody></table></div></section><section><h2>Evidence and limits</h2><details><summary>Quality flags, issuer links and complete range comparisons</summary><pre>'+escape(json.dumps(p,indent=2))+'</pre></details></section>'
    return '<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Data integrity · Trading Desk</title><style>:root{color-scheme:dark}*{box-sizing:border-box}body{margin:0;background:#09131e;color:#eaf2fb;font:15px system-ui}main{max-width:1100px;margin:auto;padding:28px}nav{display:flex;gap:22px;flex-wrap:wrap}a{color:#71e2c0}p{line-height:1.7;color:#a4b4c9}section{padding:24px;background:#142231;border:1px solid #294054;border-radius:16px;margin:20px 0}table{width:100%;border-collapse:collapse;min-width:570px}td,th{padding:14px;border-bottom:1px solid #294054;text-align:left}.scroll{overflow:auto}pre{white-space:pre-wrap;overflow-wrap:anywhere;font-size:12px}summary{cursor:pointer}:focus-visible{outline:2px solid #71e2c0}@media(max-width:700px){main{padding:16px}section{padding:18px}}</style><main><nav><a href="/">Trading desk</a><a href="/etf-research">ETF research</a><a href="/price-sources">Price source review</a><a href="/gsg-forensics">Integrity JSON</a></nav><h1>Can we trust the price bars?</h1>'+body+'</main></html>'

def install(app,s):
    from fastapi import Header,HTTPException
    from fastapi.responses import HTMLResponse
    def overview():
        c=s['db']();r=c.execute('SELECT * FROM price_source_reviews WHERE id=?',(VERSION,)).fetchone();c.close()
        if not r:return {'id':VERSION,'status':'NOT_RECORDED','activation_allowed':False}
        protocol=json.loads(r['protocol']);payload=json.loads(r['payload']);summary=payload['summary'];valid=digest(summary)==protocol['summary_hash']
        return {'id':VERSION,'recorded_at':r['recorded_at'],'status':'RECORDED' if valid else 'EVIDENCE_BLOCKED','protocol':protocol,'summary':summary if valid else {'error':'Stored summary integrity failed.'},'retained_integrity':valid,'installed_source_matches':protocol['source_fingerprint']==fingerprint(),'installed_facts_match':protocol['issuer_fact_hash']==digest(facts()),'activation_allowed':False}
    @app.get('/gsg-forensics')
    def state():return overview()
    @app.get('/data-integrity')
    def page():return HTMLResponse(render(overview()))
    @app.post('/gsg-forensics/record')
    def record(x_control_token:str|None=Header(default=None)):
        s['require_control'](x_control_token)
        with s['_cycle_lock']:
            c=s['db']();old=c.execute('SELECT id FROM price_source_reviews WHERE id=?',(VERSION,)).fetchone()
            parent=c.execute('SELECT protocol,payload FROM price_source_reviews WHERE id=?',(PARENT,)).fetchone();c.close()
            if old:return overview()
            if not parent:raise HTTPException(422,'Completed retained source review required.')
            pp=json.loads(parent['protocol']);payload=json.loads(parent['payload'])
            c=s['db']();original=c.execute('SELECT id,dataset FROM edge_lab_runs WHERE id=?',(pp['original_etf_id'],)).fetchone();c.close()
            if not original:raise HTTPException(422,'Original ETF input record unavailable.')
            try:
                if digest(payload['summary'])!=pp['summary_hash']:raise ValueError('Parent summary hash mismatch.')
                reference=facts();summary=analyse(json.loads(original['dataset']),payload,reference)
            except (ValueError,KeyError,TypeError,IndexError):raise HTTPException(422,'Source integrity or issuer reference verification failed; no fallback.')
            protocol={'version':VERSION,'original_etf_id':original['id'],'parent_review_id':PARENT,'parent_payload_hash':digest(payload),'source_dataset_hash':summary['source_dataset_hash'],'issuer_fact_hash':digest(reference),'source_fingerprint':fingerprint(),'summary_hash':digest(summary)}
            c=s['db']();c.execute('INSERT INTO price_source_reviews VALUES (?,?,?,?)',(VERSION,s['utcnow'](),json.dumps(protocol),json.dumps({'summary':summary})));c.commit();c.close()
        return overview()
    return {'overview':overview}
