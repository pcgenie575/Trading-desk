"""Additive, read-only issuer source audit; never overrides an ETF input gate."""
import copy,json,hashlib,math,re
from datetime import date,timedelta
from pathlib import Path
from urllib.parse import urlparse
from html import escape

VERSION='issuer-evidence-v1'

def catalog():
    return json.loads(Path(__file__).with_name('issuer-evidence-catalog.json').read_text(encoding='utf8'))

def digest(value):
    return hashlib.sha256(json.dumps(value,sort_keys=True,separators=(',',':')).encode()).hexdigest()

def verify(spec,captures):
    """Validate retained excerpt integrity and narrowly scoped source statements."""
    if spec['version']!=VERSION:raise ValueError('Unsupported source audit version.')
    for key,meta in spec['captures'].items():
        text=captures[key]
        if hashlib.sha256(text.encode()).hexdigest()!=meta['sha256']:raise ValueError('Source capture hash mismatch.')
    periods=copy.deepcopy(spec['gsg_no_distribution_periods'])
    expected=date(2006,7,10)
    for row in sorted(periods,key=lambda r:r['start']):
        u=urlparse(row['source'])
        if u.scheme!='https' or u.netloc!='www.sec.gov' or not re.match(r'^/Archives/edgar/data/(1332174|1346616)/\d+/[^/]+\.htm$',u.path):raise ValueError('Unsupported primary source.')
        if date.fromisoformat(row['start'])!=expected:raise ValueError('Distribution coverage has a gap or overlap.')
        end=date.fromisoformat(row['end'])
        if end<expected:raise ValueError('Invalid source coverage period.')
        expected=end+timedelta(days=1)
        text=' '.join(captures[row['capture']].split())
        block=next((b for b in text.split('--------------------------------------------------------------------------------') if row['source'] in b),None)
        if not block or 'The Trust made no distributions to Shareholders during the fiscal year' not in block:raise ValueError('Explicit no-distribution statement missing.')
        # Only the issuer sentence, not an unrelated year elsewhere in the filing.
        sentence=block.split('The Trust made no distributions to Shareholders during the fiscal year',1)[1].split('. The Trust',1)[0]
        if row['start'][:4] not in sentence or row['end'][:4] not in sentence:raise ValueError('Source statement does not cover its claimed years.')
    if expected!=date(2016,1,1):raise ValueError('Incomplete registered development coverage.')
    split=spec['iau_split'];text=' '.join(captures[split['capture']].split())
    if split['source']!='https://www.sec.gov/Archives/edgar/data/1278680/000119312510137666/dex991.htm' or split['effective_date']!='2010-06-24' or split['new_per_old']!=10:raise ValueError('Unsupported split claim.')
    if not all(x in text for x in (split['source'],'IAU/TSX: IGT','10 for 1 split','NYSEArca on June 24, 2010')):raise ValueError('Split announcement support missing.')
    return {'gsg_distribution_statement_coverage':'SUPPORTED_BY_FILINGS','coverage_start':'2006-07-10','coverage_end':'2015-12-31','iau_split_independently_supported':True,'capture_integrity':'MATCHED_EXCERPT_HASHES','original_filing_archive':'UNAVAILABLE_HTTP_403','original_gate_overridden':False,'performance_calculation_allowed':False,'activation_allowed':False}

def overlay(verified,source):
    r=copy.deepcopy(verified);r['original_job_id']=source.get('id');r['original_status']=source.get('status','NOT_AVAILABLE')
    payload=source.get('payload',{});checks=payload.get('input_checks',{})
    splits=checks.get('IAU',{}).get('inferred_splits',[])
    r['iau_provider_split_matches']=any(x.get('effective_date')=='2010-06-24' and isinstance(x.get('new_per_old'),(float,int)) and math.isfinite(x['new_per_old']) and math.isclose(x['new_per_old'],10,rel_tol=1e-4) for x in splits) if checks.get('IAU') else None
    r['original_issues']={s:copy.deepcopy(c.get('issues',[])) for s,c in checks.items()}
    r['original_input_hash']=payload.get('input_hash')
    r['note']='Supplemental issuer facts are separate from the immutable original input check. The original worksheet and price failures remain authoritative.'
    return r

def render(report):
    spec=report.get('catalog',{});result=report.get('result',{})
    rows=''.join('<tr><td>'+escape(p['start']+' to '+p['end'])+'</td><td>No shareholder distributions reported</td><td><a href="'+escape(p['source'],quote=True)+'" rel="noopener" target="_blank">Issuer filing · Item 5</a></td></tr>' for p in spec.get('gsg_no_distribution_periods',[]))
    limitations=''.join('<li>'+escape(x)+'</li>' for x in spec.get('limitations',[]))
    body='<p>Evidence state: <strong>'+escape(report['status'])+'</strong>. Research remains blocked; this page cannot activate or rerun it.</p>'
    if report['status']=='RECORDED':
        split=spec['iau_split'];body+='<section><h2>GSG distribution evidence</h2><p>Five explicit historical issuer statements cover July 2006 through December 2015. This supports no shareholder distributions for those periods; it does not supply the missing price history.</p><div class="scroll"><table><thead><tr><th>Period</th><th>Issuer statement</th><th>Primary source</th></tr></thead><tbody>'+rows+'</tbody></table></div></section>'
        body+='<section><h2>IAU split evidence</h2><p>The issuer announced a 10-for-1 split, effective for NYSE Arca pricing on 24 June 2010. Saved provider split matches: '+escape(str(result.get('iau_provider_split_matches')))+'. Historical distribution coverage remains unknown.</p><a href="'+escape(split['source'],quote=True)+'">Issuer split announcement</a></section>'
        body+='<section><h2>Original blockers remain visible</h2><pre>'+escape(json.dumps(result.get('original_issues',{}),indent=2))+'</pre></section><section><h2>Evidence limits</h2><ul>'+limitations+'</ul><p>Captured excerpt hashes, not hashes of original SEC filing bytes, are checked before recording. Captures are retained in the database and included in SQLite backups.</p></section>'
    return '<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Issuer source audit · Trading Desk</title><style>:root{color-scheme:dark}*{box-sizing:border-box}body{margin:0;background:#09131e;color:#eaf2fb;font:15px system-ui}main{max-width:1100px;margin:auto;padding:28px}nav{display:flex;gap:24px;flex-wrap:wrap}a{color:#71e2c0}p,li{line-height:1.7;color:#a4b4c9}section{background:#142231;border:1px solid #294054;border-radius:16px;padding:24px;margin:20px 0}h1{font-size:34px}h2{font-size:21px}table{width:100%;border-collapse:collapse}th,td{padding:14px;border-bottom:1px solid #294054;text-align:left}.scroll{overflow:auto}pre{white-space:pre-wrap;overflow-wrap:anywhere}:focus-visible{outline:2px solid #71e2c0}@media(max-width:700px){main{padding:16px}section{padding:18px}h1{font-size:28px}}</style><main><nav><a href="/">Trading desk</a><a href="/etf-research">ETF research</a><a href="/issuer-audit">Evidence JSON</a></nav><h1>Issuer evidence, with its limits.</h1>'+body+'</main></html>'

def install(app,s):
    from fastapi import Header,HTTPException
    from fastapi.responses import HTMLResponse,PlainTextResponse
    @app.on_event('startup')
    def init():
        c=s['db']();c.execute('CREATE TABLE IF NOT EXISTS issuer_evidence(id TEXT PRIMARY KEY,recorded_at TEXT,catalog TEXT,payload TEXT)');c.commit();c.close()
    def overview():
        c=s['db']();row=c.execute('SELECT * FROM issuer_evidence WHERE id=?',(VERSION,)).fetchone()
        original=c.execute("SELECT id,status,payload FROM edge_lab_runs WHERE kind='ETF' ORDER BY ts DESC LIMIT 1").fetchone();c.close()
        if not row:return {'id':VERSION,'status':'NOT_RECORDED','activation_allowed':False}
        spec=json.loads(row['catalog']);p=json.loads(row['payload']);source=dict(original) if original else {}
        if source:source['payload']=json.loads(source['payload'])
        r={'id':VERSION,'status':'RECORDED','recorded_at':row['recorded_at'],'catalog':spec,'catalog_hash':digest(spec),'installed_catalog_matches':spec==catalog(),'result':overlay(p['verified'],source),'activation_allowed':False}
        try:verify(spec,p['captures']);r['stored_capture_integrity']=True
        except (ValueError,KeyError,TypeError):
            r['stored_capture_integrity']=False;r['status']='EVIDENCE_BLOCKED'
            r['result']={'error':'Retained excerpts failed verification.','performance_calculation_allowed':False,'activation_allowed':False}
        if not r['installed_catalog_matches']:r['status']='CATALOG_CHANGED'
        return r
    @app.get('/issuer-audit')
    def state():return overview()
    @app.get('/issuer-sources')
    def page():return HTMLResponse(render(overview()))
    @app.get('/issuer-audit/source/{capture_id}')
    def source(capture_id:str):
        c=s['db']();row=c.execute('SELECT catalog,payload FROM issuer_evidence WHERE id=?',(VERSION,)).fetchone();c.close()
        if not row:raise HTTPException(404,'No recorded capture.')
        spec=json.loads(row['catalog']);p=json.loads(row['payload'])
        if capture_id not in spec['captures']:raise HTTPException(404,'Unknown capture.')
        try:verify(spec,p['captures'])
        except (ValueError,KeyError,TypeError):raise HTTPException(409,'Stored evidence integrity failed.')
        return PlainTextResponse(p['captures'][capture_id])
    @app.post('/issuer-audit/record')
    def record(x_control_token:str|None=Header(default=None)):
        s['require_control'](x_control_token)
        with s['_cycle_lock']:
            c=s['db']();old=c.execute('SELECT id FROM issuer_evidence WHERE id=?',(VERSION,)).fetchone();c.close()
            if old:return overview()
            spec=catalog();folder=Path(s['DB']).resolve().parent/'issuer-audit-captures'
            try:
                captures={k:(folder/m['filename']).read_text(encoding='utf8') for k,m in spec['captures'].items()}
                result=verify(spec,captures)
            except (OSError,ValueError,KeyError,TypeError):raise HTTPException(422,'Complete hash-matched source excerpts required; no automatic fetch.')
            c=s['db']();c.execute('INSERT INTO issuer_evidence VALUES (?,?,?,?)',(VERSION,s['utcnow'](),json.dumps(spec),json.dumps({'verified':result,'captures':captures})));c.commit();c.close()
        return overview()
    return {'overview':overview}
