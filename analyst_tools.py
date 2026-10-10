"""Deterministic Analyst tools. Descriptive context only; active entry rules stay fixed."""
from datetime import datetime,timezone,timedelta
from zoneinfo import ZoneInfo
import math,hashlib,json
from strategy import signal_from_bars
VERSION='analyst-tools-v1'
PARAMETERS={'sma_fast':20,'sma_slow':50,'slope_bars':5,'atr_bars':14,'rsi_bars':14,'relative_strength_intervals':20,'structure_window':5,'same_session_volume_samples':10,'volume_ratio_reference':1.2,'extension_atr_reference':2.0}
SOURCES={'atr':'https://www.fidelity.com/learning-center/trading-investing/technical-analysis/technical-indicator-guide/atr','rsi':'https://www.fidelity.com/learning-center/trading-investing/technical-analysis/technical-indicator-guide/RSI'}

def stamp(s):
    d=datetime.fromisoformat(s)
    return d.replace(tzinfo=ZoneInfo('America/New_York')) if d.tzinfo is None else d.astimezone(ZoneInfo('America/New_York'))

def clean(bars,cutoff,now):
    out=[];last=None
    for bar in bars:
        t=stamp(bar['datetime'])
        if last is not None and t<=last:raise ValueError('Analysis candles must be unique and chronological.')
        last=t
        if not all(type(bar.get(k)) in (int,float) and math.isfinite(bar[k]) and 0<bar[k]<=1e9 for k in ('open','high','low','close')):raise ValueError('Invalid analysis prices.')
        if not bar['low']<=min(bar['open'],bar['close'])<=max(bar['open'],bar['close'])<=bar['high']:raise ValueError('Invalid analysis OHLC range.')
        if t<=cutoff and t.astimezone(timezone.utc)+timedelta(hours=4,minutes=15)<=now:out.append(bar)
    return out

def mean(values,n):return sum(values[-n:])/n if len(values)>=n else None

def rsi(closes,n=14):
    if len(closes)<=n:return None
    changes=[b-a for a,b in zip(closes,closes[1:])]
    gain=sum(max(v,0) for v in changes[:n])/n;loss=sum(max(-v,0) for v in changes[:n])/n
    for v in changes[n:]:gain=(gain*(n-1)+max(v,0))/n;loss=(loss*(n-1)+max(-v,0))/n
    if not gain and not loss:return 50.0
    if not loss:return 100.0
    return 100-100/(1+gain/loss)

def atr(bars,n=14):
    if len(bars)<=n:return None
    ranges=[max(b['high']-b['low'],abs(b['high']-a['close']),abs(b['low']-a['close'])) for a,b in zip(bars,bars[1:])]
    result=sum(ranges[:n])/n
    for value in ranges[n:]:result=(result*(n-1)+value)/n
    return result

def trend(bars):
    c=[b['close'] for b in bars];m20=mean(c,20);m50=mean(c,50);prior=mean(c[:-5],50);slope=(m50/prior-1)*100 if m50 and prior else None
    regime='UNAVAILABLE'
    if m20 and m50 and slope is not None:
        regime='UPTREND' if c[-1]>m20>m50 and slope>0 else 'DOWNTREND' if c[-1]<m20<m50 and slope<0 else 'MIXED'
    return {'sma20':m20,'sma50':m50,'sma50_slope_5_bars_pct':slope,'regime':regime}

def analyse(symbol,bars,benchmark=None,now=None,knowledge=None):
    now=now or datetime.now(timezone.utc);knowledge=knowledge or []
    if not bars:return {'version':VERSION,'symbol':symbol,'status':'NO_DATA','summary':'No saved candles yet.','knowledge':knowledge,'active_policy':'Trend Breakout v1; diagnostic tools do not alter entries.'}
    cutoff=stamp(bars[-1]['datetime']);bars=clean(bars,cutoff,now)
    if not bars:return {'version':VERSION,'symbol':symbol,'status':'NO_COMPLETED_DATA','summary':'No eligible completed candles.','knowledge':knowledge}
    cutoff=stamp(bars[-1]['datetime']);c=[b['close'] for b in bars];close=c[-1];tr=trend(bars);a=atr(bars);momentum=rsi(c)
    bench=clean(benchmark or [],cutoff,now);bt=trend(bench) if bench else {'regime':'UNAVAILABLE'}
    own={stamp(b['datetime']):b['close'] for b in bars};market={stamp(b['datetime']):b['close'] for b in bench};aligned=sorted(set(own)&set(market));relative=None;relative_window=None
    if symbol!='SPY' and len(aligned)>=21:
        start,end=aligned[-21],aligned[-1]
        # Require benchmark to include the exact observation candle, not a stale older endpoint.
        if end==cutoff:
            own_return=(own[end]/own[start]-1)*100;spy_return=(market[end]/market[start]-1)*100
            relative={'symbol_return_pct':own_return,'spy_return_pct':spy_return,'excess_percentage_points':own_return-spy_return,'aligned_intervals':20}
            relative_window={'start':start.isoformat(),'end':end.isoformat()}
    time_key=cutoff.time();volumes=[float(b.get('volume') or 0) for b in bars[:-1] if stamp(b['datetime']).time()==time_key][-10:]
    v=float(bars[-1].get('volume') or 0);volume_ratio=v/(sum(volumes)/len(volumes)) if math.isfinite(v) and v>0 and len(volumes)>=10 and all(math.isfinite(x) and x>0 for x in volumes) else None
    structure=None
    if len(bars)>=10:
        previous,recent=bars[-10:-5],bars[-5:];structure={'higher_window_high':max(b['high'] for b in recent)>max(b['high'] for b in previous),'higher_window_low':min(b['low'] for b in recent)>min(b['low'] for b in previous),'note':'Five-bar window comparison, not confirmed swing pivots.'}
    signal=signal_from_bars(bars);age=(now-cutoff.astimezone(timezone.utc)).total_seconds()/3600
    flags=[]
    if age>24:flags.append('Candle opening is over 24 hours old; no fresh active entry analysis.')
    if bt.get('regime')=='UNAVAILABLE':flags.append('Market trend context is unavailable.')
    elif not bench or stamp(bench[-1]['datetime'])!=cutoff:flags.append('Latest SPY candle is not aligned; market context may lag.')
    if symbol!='SPY' and relative is None:flags.append('Relative strength unavailable: need 21 aligned timestamps ending at this candle.')
    if volume_ratio is None:flags.append('Volume context unavailable: need ten positive prior samples from the same candle opening time.')
    extension=(close-tr['sma20'])/a if a and tr['sma20'] else None
    if extension is not None and extension>2:flags.append('Price is over two ATR above its 20-bar average; descriptive extension flag, not an entry ban.')
    if momentum is not None and momentum>=70:flags.append('RSI is at least 70; momentum is elevated, not a forecast of a reversal.')
    if a and close*.05<a:flags.append('The current fixed stop distance is narrower than one ATR; gap risk still applies.')
    checks=[{'label':'Price above 20-bar average','value':close>tr['sma20'] if tr['sma20'] else None}, {'label':'Price above 50-bar average','value':close>tr['sma50'] if tr['sma50'] else None},{'label':'50-bar average rising over five bars','value':tr['sma50_slope_5_bars_pct']>0 if tr['sma50_slope_5_bars_pct'] is not None else None},{'label':'Higher five-bar highs and lows','value':all((structure['higher_window_high'],structure['higher_window_low'])) if structure else None},{'label':'Outperforming SPY over aligned intervals','value':relative['excess_percentage_points']>0 if relative else None},{'label':'Same-session volume at least 1.2× baseline','value':volume_ratio>=1.2 if volume_ratio is not None else None}]
    known=[x for x in checks if x['value'] is not None]
    result={'version':VERSION,'parameters':PARAMETERS,'sources':SOURCES,'symbol':symbol,'status':'STALE' if age>24 else 'AVAILABLE','bar_time':bars[-1]['datetime'],'generated_at':now.isoformat(),'bar_count':len(bars),'close':close,'trend':tr,'market':dict(bt,symbol='SPY',bar_time=bench[-1]['datetime'] if bench else None),'atr14':a,'atr_pct':a/close*100 if a is not None else None,'stop_distance_atr':close*.05/a if a else None,'rsi14':momentum,'extension_atr':extension,'structure':structure,'relative_strength':relative,'relative_window':relative_window,'volume_ratio':volume_ratio,'volume_samples':len(volumes),'checks':checks,'supported_conditions':sum(x['value'] is True for x in known),'available_conditions':len(known),'active_signal':signal['signal'],'active_reason':signal['reason'],'summary':tr['regime'].replace('_',' ').title()+'; '+signal['signal'].replace('_',' ').lower()+ ' under the fixed breakout policy.','flags':flags,'knowledge':knowledge,'active_policy':'Trend Breakout v1 remains active. Indicators and condition counts are descriptive context, not a win probability or new entry filter.','limitations':['No news, earnings, fundamentals or whole-market scan.','Four-hour indicators are not daily/weekly trend confirmation.','RSI compares gains/losses of this instrument; relative strength compares its return with SPY.','SPY is a US equity proxy, not the whole market; volume can be incomplete.','Wilder RSI/ATR are seeded from saved history; values can differ from longer-history charts.','Clock-age flags may reflect closed sessions/weekends; inspect feed coverage separately.']}
    result['series']=[{'time':b['datetime'],'close':b['close'],'sma20':mean(c[:i+1],20),'sma50':mean(c[:i+1],50)} for i,b in enumerate(bars) if i>=max(0,len(bars)-60)]
    result['context_hash']=hashlib.sha256(json.dumps({'version':VERSION,'bar':result['bar_time'],'data':bars,'market':result['market'],'knowledge':knowledge},sort_keys=True).encode()).hexdigest()[:20]
    return result
