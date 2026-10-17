"""Preserve as-observed inputs across the provider's documented source rollover.

Unknown, large or premature changes remain raw for existing quarantine checks.
No trusted candle or paper trade is rewritten by this module.
"""
from datetime import datetime,timedelta,time,timezone
from zoneinfo import ZoneInfo
import math
from data_quality import slots,stamp
NY=ZoneInfo('America/New_York')
SOURCE='https://support.twelvedata.com/en/articles/9935903-us-equities-market-data'
MAX_ROLLOVER_CHANGE=.001

def phase(bar_time,observed_at):
    if stamp(bar_time).date()==datetime.fromisoformat(observed_at).astimezone(NY).date():return 'LIMITED_INTRADAY'
    return 'HISTORICAL'

def historical_available(bar_time):
    day=stamp(bar_time).date()
    for _ in range(10):
        day+=timedelta(days=1);session=slots(day)
        if session is None:return None
        if session:return datetime.combine(day,time(0),NY).astimezone(timezone.utc)
    return None

def preserve_observed(symbol,bars,saved,origins,now=None):
    now=now or datetime.now(timezone.utc);result=[];events=[]
    for bar in bars:
        b=dict(bar);old=saved.get(b.get('datetime'));origin=origins.get(b.get('datetime'))
        if '/' not in symbol and old and origin and origin.get('source_phase')=='LIMITED_INTRADAY':
            try:
                ready=historical_available(b['datetime']);observed=datetime.fromisoformat(origin['first_seen'])
                valid=all(math.isfinite(b[k]) and b[k]>0 for k in ('open','high','low','close'))
                valid=valid and b['low']<=min(b['open'],b['close'])<=max(b['open'],b['close'])<=b['high']
                valid=valid and math.isfinite(b.get('volume',0)) and b.get('volume',0)>=0
                consistent=phase(b['datetime'],origin['first_seen'])=='LIMITED_INTRADAY'
                delta=max(abs(b[k]/old[k]-1) for k in ('open','high','low','close'))
                if ready and observed<ready<=now and valid and consistent and delta<=MAX_ROLLOVER_CHANGE:
                    if any(b[k]!=old[k] for k in ('open','high','low','close','volume')):
                        events.append({'bar_time':b['datetime'],'first_seen':origin['first_seen'],'max_relative_ohlc_difference':delta,
                          'action':'Retained original as-observed OHLCV; provider revision not accepted.',
                          'basis':'Feed phase inferred from documented publication schedule; no per-bar vendor source identifier.'})
                    for k in ('open','high','low','close','volume'):b[k]=old[k]
            except (KeyError,TypeError,ValueError,ZeroDivisionError,OverflowError):pass
        result.append(b)
    return result,events
