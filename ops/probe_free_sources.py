from pathlib import Path
from datetime import datetime,timezone
from urllib.request import Request,urlopen
from urllib.error import HTTPError
import json,hashlib
p=Path('data/free-source-probe-v1');p.mkdir(exist_ok=True)
start=int(datetime(2006,1,1,tzinfo=timezone.utc).timestamp());end=int(datetime(2016,1,1,tzinfo=timezone.utc).timestamp())
requests=[{'id':provider+'-'+symbol,'provider':provider,'symbol':symbol,'url':('https://query1.finance.yahoo.com/v8/finance/chart/'+symbol+'?period1='+str(start)+'&period2='+str(end)+'&interval=1d&events=div%2Csplits' if provider=='Yahoo' else 'https://stooq.com/q/d/l/?s='+symbol.lower()+'.us&i=d&d1=20060101&d2=20151231')} for provider in ('Yahoo','Stooq') for symbol in ('GSG','IEF')]
plan={'version':'free-source-probe-v1','registered_at':datetime.now(timezone.utc).isoformat(),'purpose':'Read-only source availability and overlap investigation; no backtest, validation prices, data replacement or strategy activation.','max_requests':4,'retry_allowed':False,'requests':requests,'raw_fill_semantics':'Unverified until independently established. Returned OHLC alone does not certify raw tradeable prices.','comparison_tolerance':'Fixed 0.02 USD absolute for each OHLC field in overlapping saved sessions; exact dates; no fitting of scale factors or tolerances.'}
if (p/'plan.json').exists():raise SystemExit('Plan already exists: inspect retained attempts; do not rerun.')
(p/'plan.json').write_text(json.dumps(plan,indent=2),encoding='utf8');attempts=[]
for item in requests:
 a=dict(item,attempted_at=datetime.now(timezone.utc).isoformat())
 try:
  with urlopen(Request(item['url'],headers={'User-Agent':'TradingDeskSourceReview/1.0'}),timeout=30) as r:
   body=r.read(6000001);a.update(http_status=r.status,content_type=r.headers.get('Content-Type'),final_url=r.url)
  if len(body)>6000000:raise ValueError('Response exceeds fixed source size limit.')
  filename=item['id']+'.response';(p/filename).write_bytes(body);a.update(filename=filename,bytes=len(body),sha256=hashlib.sha256(body).hexdigest(),status='RECEIVED')
 except HTTPError as e:a.update(status='UNAVAILABLE',http_status=e.code,error_type='HTTPError')
 except Exception as e:a.update(status='UNAVAILABLE',error_type=type(e).__name__)
 attempts.append(a);(p/'attempts.json').write_text(json.dumps(attempts,indent=2),encoding='utf8')
 print(json.dumps({k:a[k] for k in ('id','status','http_status','bytes','content_type','error_type') if k in a}),flush=True)
