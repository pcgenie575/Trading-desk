"""Versioned action-based input draft. Partial bundles cannot reach a simulator."""
import copy,json,hashlib,math
from pathlib import Path
from html import escape
from daily_research import validate_daily
from corporate_actions import parse_distributions,reconcile
from input_integrity import audit_bars
from price_source_review import parse_yahoo,compare_prices,diagnose_adjustments,digest,VERSION as SOURCE_VERSION

VERSION='etf-action-inputs-v2-draft'
SYMBOLS=('IWM','IEF','EFA','IAU','GSG')
PROTOCOL={'version':VERSION,'symbols':list(SYMBOLS),'warmup_start':'2006-01-01','development_start':'2007-01-03','development_end':'2015-12-31','purpose':'Assemble an input-review draft using unchanged raw prices and original issuer action records. No strategy calculation or source promotion.',
 'method':'IWM/EFA retain original reconciliation evidence. IEF replaces the derived-price dependency only in this new draft: use original explicitly unadjusted prices and full issuer dividend/payment records, corroborated against the retained second-source OHLC and adjusted-close factors.',
 'ief_checks':'Exact saved session coverage; $0.02 OHLC overlap tolerance; original 0.0008 factor tolerance on issuer dates and independently normalised adjusted-close levels. Last retained close is the common anchor, not a fitted scale or price replacement.',
 'lookahead':'Back-adjusted closes are diagnostic only. Future signals must use raw bars and actions effective by the decision date through the existing point-in-time signal_features method. No fully back-adjusted prices become opening fills or signal inputs.',
 'blocked_assets':'IAU lacks complete historical cash-distribution evidence. GSG fails original early coverage and daily OHLC integrity/verification. Preserve both in the manifest; do not omit them from the five-asset requirement.',
 'approval':'ASSEMBLED_FOR_REVIEW is not source certification, simulator readiness or permission to activate. All five components and a separately recorded methodology review are mandatory before any future simulation.',
 'strategy_changed':False,'performance_calculation_allowed':False,'activation_allowed':False}

def fingerprint():
    return {n:hashlib.sha256(Path(__file__).with_name(n).read_bytes()).hexdigest() for n in ('input_revision.py','corporate_actions.py','input_integrity.py','price_source_review.py','daily_research.py')}

def back_adjusted_close(raw,events):
    """Diagnostic history in final-day units; never used for as-of signals/fills."""
    dates=[b['datetime'] for b in raw];by={b['datetime']:b['close'] for b in raw};previous={d:p for p,d in zip(dates,dates[1:])};amounts={}
    for e in events:
        if e['type']!='distribution':raise ValueError('This fixed IEF draft supports dividend-only diagnostic adjustments.')
        if e['ex_date'] in by:amounts[e['ex_date']]=amounts.get(e['ex_date'],0)+e['amount']
    factor=1.;result={}
    for d in reversed(dates):
        result[d]=by[d]*factor
        if d in amounts:
            if d not in previous:raise ValueError('Prior session missing for a distribution.')
            adjustment=1-amounts[d]/by[previous[d]]
            if adjustment<=0:raise ValueError('Invalid dividend adjustment.')
            factor*=adjustment
    return result

def normalised_levels(derived,independent):
    if set(derived)!=set(independent):raise ValueError('Exact adjusted-close dates required.')
    last=max(derived);a=derived[last];b=independent[last]
    if a<=0 or b<=0:raise ValueError('Positive final anchor required.')
    diffs={d:abs(derived[d]/a-independent[d]/b) for d in derived}
    bad=[d for d in derived if not math.isclose(derived[d]/a,independent[d]/b,rel_tol=8e-4,abs_tol=8e-4)]
    return {'sessions':len(diffs),'anchor_date':last,'normalisation':'Each series divided by its own final retained close. No fitted parameters. Derived levels are diagnostic only.','tolerance':.0008,'max_absolute_normalised_difference':max(diffs.values()),'mismatches':len(bad),'first_mismatch_dates':sorted(bad)[:5],'matched':not bad}

def require_complete(manifest):
    if set(manifest['components'])!=set(SYMBOLS) or any(manifest['components'][s]['status']!='ASSEMBLED_FOR_REVIEW' for s in SYMBOLS):raise ValueError('Incomplete five-asset draft: simulation is forbidden.')
    raise ValueError('Draft methodology has no recorded approval or simulation capability.')

def build(original,parent,issuer_originals):
    if parent['summary']['source_dataset_hash']!=digest(original):raise ValueError('Original dataset differs from the source-review parent.')
    if any(s+':'+m not in original['pages'] for s in SYMBOLS for m in ('none','splits','all')) or any(s not in original['distributions'] for s in SYMBOLS):raise ValueError('Original five-asset evidence must remain present.')
    source=next(x for x in parent['summary']['results'] if x['id']=='Yahoo-IEF');text=parent['responses']['Yahoo-IEF']
    if hashlib.sha256(text.encode()).hexdigest()!=source['sha256']:raise ValueError('Independent response hash mismatch.')
    alternative=parse_yahoo(json.loads(text),'IEF')
    components={};assets={};reference=original['reference'];origin=digest(original)
    for symbol in SYMBOLS:
        if symbol in ('IAU','GSG'):
            issues=['DISTRIBUTION_COVERAGE_UNVERIFIED'] if symbol=='IAU' else ['EARLY_HISTORY_UNVERIFIED','DAILY_OHLC_INTEGRITY_UNRESOLVED']
            components[symbol]={'status':'BLOCKED','issues':issues,'materialised':False};continue
        page=original['pages'][symbol+':none'];raw=page['bars'];dist=original['distributions'][symbol];content=issuer_originals[symbol]
        if hashlib.sha256(content).hexdigest()!=dist['source_hash']:raise ValueError('Original issuer file hash mismatch.')
        parsed=parse_distributions(symbol,content)
        if parsed['events']!=dist['events'] or not parsed['coverage_verified']:raise ValueError('Original issuer events differ on reparse.')
        m=page['meta']
        if page.get('adjustment_requested')!='none' or m.get('symbol')!=symbol or m.get('currency')!='USD' or m.get('interval')!='1day':raise ValueError('Explicit unchanged raw-price identity required.')
        validate_daily(raw,'2006-01-01','2015-12-31');dates=[b['datetime'] for b in raw]
        if raw[0]['datetime']>'2006-01-10' or raw[-1]['datetime']!='2015-12-31' or dates!=[d for d in reference if raw[0]['datetime']<=d<='2015-12-31']:raise ValueError('Registered raw coverage required without a shortened fallback.')
        quality=audit_bars(raw)
        if quality['requires_source_review']:raise ValueError('Extended flat OHLC run in a proposed component.')
        events=[copy.deepcopy(e) for e in parsed['events'] if '2006-01-01'<=e['ex_date']<='2015-12-31']
        for e in events:
            if e['currency']!='USD' or not math.isfinite(e['amount']) or e['amount']<0 or e['pay_date']<e['ex_date']:raise ValueError('Invalid original issuer action.')
        evidence={'raw_hash':digest(raw),'events_hash':digest(events),'issuer_source_hash':parsed['source_hash'],'issuer_source':parsed['source'],'bars':len(raw),'distribution_events':len(events),'flat_run_review':quality['requires_source_review']}
        if symbol in ('IWM','EFA'):
            check=reconcile(raw,original['pages'][symbol+':splits']['bars'],original['pages'][symbol+':all']['bars'],parsed,reference,'2006-01-01','2015-12-31')
            if not check['passed']:raise ValueError('A previously reconciled component no longer passes its original check.')
            evidence['original_reconciliation']=check
        else:
            split=original['pages']['IEF:splits']['bars']
            if dates!=[b['datetime'] for b in split] or any(not math.isclose(b[k],p[k],rel_tol=3e-5,abs_tol=3e-5) for b,p in zip(raw,split) for k in ('open','high','low','close')) or alternative['splits']:raise ValueError('Unexpected split in fixed dividend-only IEF method.')
            prices=compare_prices(alternative['bars'],raw);factors=diagnose_adjustments(alternative,raw,parsed)
            derived=back_adjusted_close(raw,events);levels=normalised_levels(derived,alternative['adjusted_close'])
            if not prices['all_overlapping_ohlc_within_tolerance'] or prices['candidate_only_sessions'] or prices['saved_only_sessions'] or factors['issuer_dates_checked']!=len({e['ex_date'] for e in events}) or factors['mismatches'] or factors['missing_event_dates'] or not levels['matched']:raise ValueError('Independent IEF diagnostic checks failed; no tolerance change.')
            evidence.update(independent_ohlc=prices,independent_issuer_factor_check=factors,normalised_level_check=levels,diagnostic_derived_close_hash=digest(derived),excluded_original_provider_adjusted_hash=digest(original['pages']['IEF:all']))
        assets[symbol]={'raw':copy.deepcopy(raw),'events':events,'raw_fills_only':True,'signal_method':'Original corporate_actions.signal_features: effective-date actions only. Full back-adjusted diagnostic levels are excluded.'}
        components[symbol]={'status':'ASSEMBLED_FOR_REVIEW','issues':[],'materialised':True,'evidence':evidence,'source_certified':False}
    manifest={'version':VERSION,'status':'PARTIAL_DRAFT','source_dataset_hash':origin,'components':components,'assembled_components':len(assets),'required_components':5,'ready_for_simulation':False,'methodology_approved':False,'performance_calculation_allowed':False,'activation_allowed':False,'original_dataset_replaced':False,'additional_price_requests':0,'limitations':['Issuer worksheets are retrospective gross cash records; investor withholding, tax and historical availability are not certified.','Original SPY sessions are a proxy, not a certified historical calendar.','Cross-source agreement and deterministic reconciliation do not prove independent underlying data or every raw-price detail.','This draft uses a new input methodology for IEF. It does not clear or amend the original provider-adjustment failures.','Unknown IAU distributions and unresolved GSG prices remain blocking. No assets, dates or thresholds are omitted to obtain a pass.']}
    bundle={'version':VERSION,'reference':copy.deepcopy(reference),'assets':assets,'manifest_hash':digest(manifest),'ready_for_simulation':False}
    return manifest,bundle

def render(report):
    body='<p>State: '+escape(report['status'])+'. No prices are replaced and no strategy test runs from this draft.</p>'
    if report.get('installed_source_matches') is False:body+='<p role="alert">Installed source differs from this retained draft. Review the recorded method before using it.</p>'
    if 'manifest' in report:
        m=report['manifest'];rows=''.join('<tr><td>'+escape(s)+'</td><td>'+escape(c['status'])+'</td><td>'+escape(', '.join(c['issues']) or 'Evidence assembled; methodology review still required')+'</td></tr>' for s,c in m['components'].items())
        body+='<section><h2>'+str(m['assembled_components'])+' of 5 components assembled for review</h2><p>IWM and EFA retain their original reconciliation evidence. IEF uses unchanged raw prices and issuer actions with independent adjustment checks. IAU and GSG remain in the five-asset manifest as blockers.</p><div class="scroll"><table><thead><tr><th>Asset</th><th>Draft state</th><th>Review requirement</th></tr></thead><tbody>'+rows+'</tbody></table></div><p><strong>Not ready for simulation.</strong> This page cannot approve a source, omit an asset, relax a gate or activate trading.</p></section><section><h2>Method and evidence</h2><details><summary>Component provenance, checks and limitations</summary><pre>'+escape(json.dumps(m,indent=2))+'</pre></details><p><a href="/input-revision/bundle">Private draft JSON export</a></p></section>'
    return '<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Input revision · Trading Desk</title><style>:root{color-scheme:dark}*{box-sizing:border-box}body{margin:0;background:#09131e;color:#eaf2fb;font:15px system-ui}main{max-width:1100px;margin:auto;padding:28px}nav{display:flex;gap:22px;flex-wrap:wrap}a{color:#71e2c0}p{line-height:1.7;color:#a4b4c9}section{background:#142231;border:1px solid #294054;border-radius:16px;padding:24px;margin:20px 0}table{border-collapse:collapse;width:100%;min-width:650px}td,th{padding:14px;border-bottom:1px solid #294054;text-align:left}.scroll{overflow:auto}pre{white-space:pre-wrap;overflow-wrap:anywhere;font-size:12px}summary{cursor:pointer}:focus-visible{outline:2px solid #71e2c0}@media(max-width:700px){main{padding:16px}section{padding:18px}}</style><main><nav><a href="/">Trading desk</a><a href="/etf-research">ETF research</a><a href="/data-integrity">Data integrity</a><a href="/input-revision">Manifest JSON</a></nav><h1>A separate input draft.</h1>'+body+'</main></html>'

def install(app,s):
    from fastapi import HTTPException,Header
    from fastapi.responses import HTMLResponse
    @app.on_event('startup')
    def init():
        c=s['db']();c.execute('CREATE TABLE IF NOT EXISTS input_revisions(id TEXT PRIMARY KEY,created_at TEXT,status TEXT,protocol TEXT,manifest TEXT,bundle TEXT)');c.commit();c.close()
    def retained(full=False):
        c=s['db']();r=c.execute('SELECT * FROM input_revisions WHERE id=?',(VERSION,)).fetchone();c.close()
        if not r:return {'id':VERSION,'status':'NOT_BUILT','activation_allowed':False}
        p=json.loads(r['protocol']);m=json.loads(r['manifest']);stored=json.loads(r['bundle']);valid=digest(m)==p['manifest_hash'] and digest(stored)==p['stored_bundle_hash']
        if not valid:
            if full:raise HTTPException(409,'Draft integrity failed.')
            return {'id':VERSION,'status':'EVIDENCE_BLOCKED','activation_allowed':False}
        result={'id':VERSION,'created_at':r['created_at'],'status':r['status'],'protocol':p,'manifest':m,'retained_integrity':True,'installed_source_matches':p['source_fingerprint']==fingerprint(),'activation_allowed':False}
        if full:result['bundle']=stored['draft']
        return result
    @app.get('/input-revision')
    def state():return retained()
    @app.get('/input-revision/bundle')
    def export():return retained(True)
    @app.get('/input-draft')
    def page():return HTMLResponse(render(retained()))
    @app.post('/input-revision/build')
    def record(x_control_token:str|None=Header(default=None)):
        s['require_control'](x_control_token)
        with s['_cycle_lock']:
            c=s['db']();old=c.execute('SELECT id FROM input_revisions WHERE id=?',(VERSION,)).fetchone();parent=c.execute('SELECT protocol,payload FROM price_source_reviews WHERE id=?',(SOURCE_VERSION,)).fetchone();c.close()
            if old:return retained()
            if not parent:raise HTTPException(422,'Retained source review required.')
            pp=json.loads(parent['protocol']);payload=json.loads(parent['payload'])
            c=s['db']();source=c.execute('SELECT id,dataset FROM edge_lab_runs WHERE id=?',(pp['original_etf_id'],)).fetchone();c.close()
            if not source:raise HTTPException(422,'Original ETF input required.')
            try:
                if digest(payload['summary'])!=pp['summary_hash']:raise ValueError('Parent summary mismatch.')
                folder=Path(s['DB']).resolve().parent/'etf-issuer-sources';originals={t:(folder/(source['id']+'-'+t+'.xml')).read_bytes() for t in ('IWM','IEF','EFA')}
                manifest,bundle=build(json.loads(source['dataset']),payload,originals)
            except (OSError,ValueError,KeyError,TypeError,IndexError):raise HTTPException(422,'Original source integrity or action reconciliation failed; no fallback or source fetch.')
            stored={'draft':bundle,'issuer_originals':{k:v.decode('utf8') for k,v in originals.items()}}
            protocol={'method':PROTOCOL,'original_etf_id':source['id'],'parent_source_review':SOURCE_VERSION,'parent_payload_hash':digest(payload),'source_fingerprint':fingerprint(),'manifest_hash':digest(manifest),'stored_bundle_hash':digest(stored)}
            c=s['db']();c.execute('INSERT INTO input_revisions VALUES (?,?,?,?,?,?)',(VERSION,s['utcnow'](),'PARTIAL_DRAFT',json.dumps(protocol),json.dumps(manifest),json.dumps(stored)));c.commit();c.close()
        return retained()
    return {'overview':retained}
