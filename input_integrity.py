"""Descriptive source-integrity tools. Flags never certify a feed or alter trading."""
from daily_research import validate_daily

FLAT_RUN_REVIEW_SESSIONS=5

def audit_bars(bars):
    if not bars:raise ValueError('Retained bars required.')
    validate_daily(bars,start=bars[0]['datetime'],end=bars[-1]['datetime'])
    runs=[];current=[];years={}
    for b in bars:
        flat=max(b[k] for k in ('open','high','low','close'))-min(b[k] for k in ('open','high','low','close'))<=1e-8
        y=years.setdefault(b['datetime'][:4],{'sessions':0,'flat_ohlc_sessions':0,'flat_sessions_with_positive_volume':0})
        y['sessions']+=1
        if flat:
            y['flat_ohlc_sessions']+=1;y['flat_sessions_with_positive_volume']+=int(b.get('volume',0)>0);current.append(b['datetime'])
        elif current:runs.append(current);current=[]
    if current:runs.append(current)
    suspicious=[{'first':r[0],'last':r[-1],'sessions':len(r)} for r in runs if len(r)>=FLAT_RUN_REVIEW_SESSIONS]
    return {'sessions':len(bars),'flat_ohlc_sessions':sum(y['flat_ohlc_sessions'] for y in years.values()),'longest_flat_run_sessions':max((len(r) for r in runs),default=0),'review_threshold_sessions':FLAT_RUN_REVIEW_SESSIONS,'suspicious_runs':suspicious,'by_year':years,'requires_source_review':bool(suspicious),'source_certified':False,'activation_allowed':False,'interpretation':'Five consecutive observed flat OHLC bars trigger investigation, not an automatic finding of bad data. Illiquidity or a halt can produce legitimate flat bars; nonzero ranges in another source need reconciliation. This diagnostic threshold was chosen after observing the GSG anomaly and is not a validated statistical test.'}
