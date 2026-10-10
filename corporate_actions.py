"""Point-in-time signal prices and verified cash-distribution accounting inputs."""
import math,re,hashlib,xml.etree.ElementTree as ET
from datetime import datetime,date
from daily_research import validate_daily

ISSUERS={'IWM':('239710','iShares Russell 2000 ETF'),'IEF':('239456','iShares 7-10 Year Treasury Bond ETF'),
         'EFA':('239623','iShares MSCI EAFE ETF'),'IAU':('239561','iShares Gold Trust'),'GSG':('239757','iShares S&P GSCI Commodity-Indexed Trust')}
def issuer_url(symbol):
    return 'https://www.blackrock.com/varnish-api/blk-one01-product-data/product-data/api/v1/get-fund-document?appSubType=ISHARES&appType=PRODUCT_PAGE&component=fundDownload&locale=en_US&portfolioId='+ISSUERS[symbol][0]+'&targetSite=us-ishares&userType=individual'

def parse_distributions(symbol,content):
    if symbol not in ISSUERS or len(content)>8000000:raise ValueError('Unsupported issuer export.')
    text=content.decode('utf8')
    if '<!DOCTYPE' in text.upper() or '<!ENTITY' in text.upper():raise ValueError('Unsafe XML declaration.')
    # Issuer SpreadsheetML contains literal ampersands; retain original bytes/hash.
    text=re.sub(r'&(?!#\d+;|#x[0-9a-fA-F]+;|[a-zA-Z]+;)','&amp;',text)
    ns={'s':'urn:schemas-microsoft-com:office:spreadsheet'};root=ET.fromstring(text)
    sheets=[s for s in root.findall('s:Worksheet',ns) if s.attrib.get('{'+ns['s']+'}Name')=='Distributions']
    if len(sheets)!=1:raise ValueError('A complete distributions worksheet is required; missing is not zero.')
    rows=[[c.text or '' for c in r.findall('.//s:Data',ns)] for r in sheets[0].findall('.//s:Row',ns)]
    if not rows or rows[0][:4]!=['Record Date','Ex-Date','Payable Date','Total Distribution']:raise ValueError('Issuer distribution schema changed.')
    events=[];seen=set()
    for row in rows[1:]:
        if not row or not any(x.strip() for x in row):continue
        if len(row)!=8:raise ValueError('Malformed distribution row.')
        ex=datetime.strptime(row[1],'%b %d, %Y').date().isoformat();pay=datetime.strptime(row[2],'%b %d, %Y').date().isoformat();amount=float(row[3])
        if not math.isfinite(amount) or amount<0 or pay<ex:raise ValueError('Invalid distribution amount or payment date.')
        key=(ex,pay)
        if key in seen:raise ValueError('Duplicate distribution event.')
        seen.add(key)
        if amount:events.append({'type':'distribution','ex_date':ex,'pay_date':pay,'amount':amount,'currency':'USD'})
    return {'symbol':symbol,'source':issuer_url(symbol),'source_hash':hashlib.sha256(content).hexdigest(),'coverage_verified':True,
            'source_rows':len(rows)-1,'events':sorted(events,key=lambda e:e['ex_date']),
            'basis':'Full issuer distributions worksheet; gross USD before investor withholding/tax. Original export retained privately.'}

def reconcile(raw,split,all_adjusted,distribution,reference,start,end):
    """Require matched dates/OHLC factors and reconcile all adjustment jumps.
    A split inferred from two price modes remains labelled provider-inferred.
    """
    for bars in (raw,split,all_adjusted):validate_daily(bars,start,end)
    maps=[{b['datetime']:b for b in bars} for bars in (raw,split,all_adjusted)]
    dates=set(maps[0]);issues=[];splits=[]
    if distribution.get('coverage_verified') is False:issues.append('DISTRIBUTION_SOURCE_UNVERIFIED')
    if any(set(m)!=dates for m in maps[1:]):issues.append('ADJUSTMENT_DATE_MISMATCH')
    expected={d for d in reference if raw[0]['datetime']<=d<=end}
    if dates!=expected:issues.append('MISSING_OR_EXTRA_REFERENCE_SESSIONS')
    if raw[-1]['datetime']!=end:issues.append('END_SESSION_MISSING')
    if raw[0]['datetime']>'2006-07-20':issues.append('WARMUP_HISTORY_TOO_SHORT')
    div={}
    for e in distribution['events']:
        if start<=e['ex_date']<=end:div[e['ex_date']]=div.get(e['ex_date'],0)+e['amount']
    factors={};previous=None;prior_raw=None
    for day in sorted(dates):
        if any(day not in m for m in maps[1:]):continue
        r,s,a=(m[day] for m in maps)
        f=r['close']/s['close'];g=s['close']/a['close']
        if any(not math.isclose(r[k]/s[k],f,rel_tol=3e-5,abs_tol=3e-5) or not math.isclose(s[k]/a[k],g,rel_tol=3e-5,abs_tol=3e-5) for k in ('open','high','low','close')):
            issues.append('NON_UNIFORM_ADJUSTMENT:'+day)
        if previous:
            ratio=previous[0]/f
            if not math.isclose(ratio,1,rel_tol=1e-4):
                if not .01<=ratio<=100:issues.append('INVALID_SPLIT_FACTOR:'+day)
                else:splits.append({'type':'split','effective_date':day,'new_per_old':ratio,'basis':'Inferred from matched raw/split provider prices; not independently issuer-verified.'})
            # Compare dividend adjustment discontinuity with the issuer cash amount.
            expected_jump=1-div.get(day,0)/(prior_raw/ratio)
            actual_jump=g/previous[1]
            if expected_jump<=0 or not math.isclose(actual_jump,expected_jump,rel_tol=8e-4,abs_tol=8e-4):issues.append('DISTRIBUTION_RECONCILIATION:'+day)
        factors[day]=f;previous=(f,g);prior_raw=r['close']
    # No inferred split is silently elevated to issuer-verified evidence.
    if splits:issues.append('SPLIT_EVENT_REQUIRES_INDEPENDENT_VERIFICATION')
    return {'passed':not issues,'issues':sorted(set(issues)),'bars':len(raw),'first':raw[0]['datetime'],'last':raw[-1]['datetime'],
            'missing_reference_sessions':len(expected-dates),'distribution_events':sum(start<=e['ex_date']<=end for e in distribution['events']),
            'inferred_splits':splits,'adjustment_factor_tolerance':.0008,'reference':'Saved SPY daily session proxy, not an independently certified historical exchange calendar.'}

def signal_features(raw,events):
    """Rebase only past prices using events effective on the current day.
    Future distributions and splits never alter earlier feature snapshots.
    """
    splits={e['effective_date']:e['new_per_old'] for e in events if e['type']=='split'};div={}
    for e in events:
        if e['type']=='distribution':div[e['ex_date']]=div.get(e['ex_date'],0)+e['amount']
    window=[];out={}
    for b in raw:
        day=b['datetime'];ratio=splits.get(day,1)
        if ratio!=1:
            window=[dict(p,**{k:p[k]/ratio for k in ('open','high','low','close')}) for p in window]
        if day in div and window:
            factor=1-div[day]/window[-1]['close']
            if factor<=0:raise ValueError('Distribution exceeds prior close.')
            window=[dict(p,**{k:p[k]*factor for k in ('open','high','low','close')}) for p in window]
        prior_high=max(p['high'] for p in window[-20:]) if len(window)>=20 else None
        window.append(dict(b));window=window[-101:];closes=[p['close'] for p in window]
        out[day]={'trend':sum(closes[-100:])/100 if len(closes)>=100 else None,
                  'exit_ma':sum(closes[-50:])/50 if len(closes)>=50 else None,'prior_high':prior_high,
                  'series':{p['datetime']:p['close'] for p in window[-100:]}}
    return out

def split_position(position,ratio):
    """Keep economic cost, original R denominator and excursion dollars invariant."""
    p=dict(position,qty=position['qty']*ratio,stop=position['stop']/ratio)
    if 'excursion' in p:
        x=dict(p['excursion']);x['quantity']*=ratio
        for k in ('entry_reference','lowest_observed','highest_observed'):x[k]/=ratio
        p['excursion']=x
    return p
