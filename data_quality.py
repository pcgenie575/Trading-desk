"""Bounded, explicit US core-session calendar and conservative entry gates."""
from datetime import datetime,date,time,timedelta,timezone
from zoneinfo import ZoneInfo
import hashlib,json,math
VERSION='session-quality-v1'
PRICE_REL_TOL=1e-6
PRICE_ABS_TOL=1e-5
NY=ZoneInfo('America/New_York')
SOURCE='https://www.nyse.com/trade/hours-calendars'
HOLIDAYS={2026:'01-01 01-19 02-16 04-03 05-25 06-19 07-03 09-07 11-26 12-25',2027:'01-01 01-18 02-15 03-26 05-31 06-18 07-05 09-06 11-25 12-24',2028:'01-17 02-21 04-14 05-29 06-19 07-04 09-04 11-23 12-25'}
EARLY={2026:'11-27 12-24',2027:'11-26',2028:'07-03 11-24'}
def stamp(value):
    d=datetime.fromisoformat(value)
    return d.replace(tzinfo=NY) if d.tzinfo is None else d.astimezone(NY)
def slots(day):
    if day.year not in HOLIDAYS:return None
    if day.weekday()>4 or day.strftime('%m-%d') in HOLIDAYS[day.year].split():return []
    return [datetime.combine(day,t,NY) for t in ([time(9,30)] if day.strftime('%m-%d') in EARLY[day.year].split() else [time(9,30),time(13,30)])]
def expected(start,end):
    result=[];day=start.astimezone(NY).date()
    if (end.date()-day).days>370:raise ValueError('Calendar interval too large')
    while day<=end.astimezone(NY).date():
        available=slots(day)
        if available is None:raise ValueError('Calendar year unavailable')
        result.extend(d for d in available if start<=d<=end);day+=timedelta(days=1)
    return result
def assess(symbol,bars,now=None,saved=None):
    now=now or datetime.now(timezone.utc);issues=[];warnings=[];seen=set();valid=[];quarantine=False
    def issue(code,detail,hard=False):
        nonlocal quarantine
        issues.append({'code':code,'detail':detail});quarantine=quarantine or hard
    if not bars:issue('NO_DATA','No candles supplied',True)
    for b in bars:
        try:
            t=stamp(b['datetime']);nums=[float(b[k]) for k in ('open','high','low','close')];o,h,l,c=nums
            volume=float(b.get('volume') or 0)
            if not math.isfinite(volume) or volume<0:raise ValueError('Volume')
            if not all(math.isfinite(x) and 0<x<=1e9 for x in nums) or not l<=min(o,c)<=max(o,c)<=h:raise ValueError('OHLC')
            if t in seen:issue('DUPLICATE_TIMESTAMP',t.isoformat(),True)
            if valid and t<=valid[-1][0]:issue('UNORDERED_TIMESTAMP',t.isoformat(),True)
            if t.astimezone(timezone.utc)+timedelta(hours=4,minutes=15)>now:issue('INCOMPLETE_CANDLE',t.isoformat(),True)
            if '/' not in symbol:
                session=slots(t.date())
                if session is None:issue('CALENDAR_UNAVAILABLE',str(t.year))
                elif t not in session:issue('OUTSIDE_EXPECTED_SESSION',t.isoformat(),True)
            if valid and abs(o/valid[-1][1]['close']-1)>.30:issue('PRICE_DISCONTINUITY','Opening gap exceeds 30%; could be real news, bad data or a corporate action. Requires investigation.',True)
            prior=(saved or {}).get(b['datetime'])
            if prior and any(not math.isclose(float(prior[k]),float(b[k]),rel_tol=PRICE_REL_TOL,abs_tol=PRICE_ABS_TOL) for k in ('open','high','low','close')):issue('HISTORICAL_REVISION',b['datetime'],True)
            seen.add(t);valid.append((t,dict(b,open=o,high=h,low=l,close=c)))
        except (ValueError,TypeError,KeyError,OverflowError):issue('INVALID_CANDLE','Timestamp or OHLC validation failed',True)
    if valid and '/' not in symbol:
        try:
            # Gate entries using latest 60 bars, not an unbounded historical scan.
            recent=valid[-60:];required=expected(recent[0][0],recent[-1][0]);missing=[d.isoformat() for d in required if d not in seen]
            if missing:issue('MISSING_SESSION_BARS',', '.join(missing[:8])+f' ({len(missing)} total)')
            elapsed=expected(valid[-1][0],now.astimezone(NY));overdue=[d for d in elapsed if d>valid[-1][0] and d.astimezone(timezone.utc)+timedelta(hours=4,minutes=15)<=now]
            if overdue:issue('STALE_SESSION_DATA',f'{len(overdue)} expected completed candles after latest received')
            elif (now-valid[-1][0].astimezone(timezone.utc)).total_seconds()>86400:warnings.append('Clock-old candle with no later expected completed session; closed market alone is not a feed failure. Existing entry age rule still applies.')
        except ValueError as e:issue('CALENDAR_UNAVAILABLE',str(e))
    report={'version':VERSION,'symbol':symbol,'entry_allowed':not issues and '/' not in symbol,'quarantined':quarantine,'issues':issues,'warnings':warnings,'last_bar':bars[-1].get('datetime') if bars else None,'calendar_source':SOURCE,'calendar_years':[2026,2027,2028],'assumptions':'Regular-session 4h openings 09:30/13:30 New York; early close omits 13:30; eligibility remains opening+4h15. Unscheduled closures and corporate actions are not supplied.'}
    if '/' in symbol:report['warnings'].append('Crypto remains observation only; US session-calendar checks do not apply.')
    report['context_hash']=hashlib.sha256(json.dumps({'report':report,'bars':bars},sort_keys=True).encode()).hexdigest();return report
