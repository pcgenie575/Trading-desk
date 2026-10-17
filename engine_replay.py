"""Run recorded feed batches in an isolated process, database and virtual clock.

No scheduler, HTTP server, learning worker or provider is started.
"""
import json,os,sys,tempfile,secrets
from pathlib import Path
from datetime import datetime,timezone

def run(events):
    if not events or len(events)>500:raise ValueError('Replay requires 1–500 recorded batches.')
    for e in events:
        if len(e['bars'])>100:raise ValueError('Batch exceeds the original provider window.')
        if datetime.fromisoformat(e['observed_at']).tzinfo is None:raise ValueError('Observation must have an explicit timezone.')
    with tempfile.TemporaryDirectory() as td:
        # Set before import; never inherit the operational database or credentials.
        os.environ['TCR_DB']=str(Path(td)/'isolated.db')
        os.environ['TCR_CONTROL_TOKEN']=secrets.token_hex(32)
        for name in ('TWELVE_DATA_API_KEY','TCR_DASHBOARD_PASSWORD'):os.environ.pop(name,None)
        import app as room
        if any(e['symbol'] not in room.INSTRUMENTS or '/' in e['symbol'] for e in events):raise ValueError('US paper universe required.')
        from data_quality import assess
        class Clock(datetime):
            current=datetime.now(timezone.utc)
            @classmethod
            def now(cls,tz=None):return cls.current.astimezone(tz) if tz else cls.current.replace(tzinfo=None)
        room.DB=os.environ['TCR_DB'];room.datetime=Clock
        room.utcnow=lambda:Clock.current.isoformat()
        room.assess_quality=lambda symbol,bars,**kw:assess(symbol,bars,now=Clock.current,**kw)
        def forbidden(*a,**kw):raise RuntimeError('Provider access is forbidden in replay.')
        room.TwelveDataAdapter.latest_completed_bars=forbidden
        room.init_db();statuses={}
        for e in sorted(events,key=lambda e:(e['observed_at'],e['symbol'])):
            Clock.current=datetime.fromisoformat(e['observed_at']).astimezone(timezone.utc)
            room._local.symbol=e['symbol']
            result=room.process_received_bars(e['bars']);key=result.get('status',result.get('signal','UNKNOWN'));statuses[key]=statuses.get(key,0)+1
        positions=room.positions();closed=[p for p in positions if p['status']=='CLOSED']
        c=room.db();decisions=[dict(r) for r in c.execute('SELECT phase,decision,payload FROM risk_decisions')]
        decisions=[dict(phase=r['phase'],decision=r['decision'],checks=json.loads(r['payload']).get('checks',[])) for r in decisions]
        marks={p['symbol']:float(room.state_raw().get('mark:'+p['symbol'],p['entry_price'])) for p in positions if p['status']=='OPEN'}
        from profit_evidence import from_database
        evidence=from_database(room.__dict__);c.close()
        return {'version':'recorded-engine-replay-v1','isolated':True,'provider_requests':0,'batches':len(events),'statuses':statuses,
          'account':room.get_state(),'positions':positions,'risk_decisions':decisions,'profit':evidence,
          'closed_trades':len(closed),'edge_validated':False,'activation_allowed':False,
          'limitations':['Recorded observations are not an independent out-of-sample dataset.','Deduplicated quality reports omit unchanged polls and manual recovery actions.','Simulation does not recreate unrecorded market events or outages.']}

if __name__=='__main__':
    result=run(json.loads(Path(sys.argv[1]).read_text()))
    print(json.dumps(result,allow_nan=False))
