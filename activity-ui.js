/* Display-only NYSE regular-session calendar. Never controls trading. */
(function(root){
const holidays={2026:['01-01','01-19','02-16','04-03','05-25','06-19','07-03','09-07','11-26','12-25'],2027:['01-01','01-18','02-15','03-26','05-31','06-18','07-05','09-06','11-25','12-24'],2028:['01-17','02-21','04-14','05-29','06-19','07-04','09-04','11-23','12-25']};
const early=new Set(['2026-11-27','2026-12-24','2027-11-26','2028-07-03','2028-11-24']);
const parts=(date,zone)=>Object.fromEntries(new Intl.DateTimeFormat('en-CA',{timeZone:zone,year:'numeric',month:'2-digit',day:'2-digit',hour:'2-digit',minute:'2-digit',second:'2-digit',hourCycle:'h23'}).formatToParts(date).filter(p=>p.type!=='literal').map(p=>[p.type,p.value]));
function wallUtc(day,hour,minute=0){const target=Date.parse(day+'T'+String(hour).padStart(2,'0')+':'+String(minute).padStart(2,'0')+':00Z');let value=target;for(let i=0;i<3;i++){const p=parts(new Date(value),'America/New_York');const shown=Date.parse(`${p.year}-${p.month}-${p.day}T${p.hour}:${p.minute}:${p.second}Z`);value+=target-shown;}return new Date(value);}
function session(day){const year=+day.slice(0,4);if(!holidays[year])return null;const weekday=new Date(day+'T12:00:00Z').getUTCDay();return weekday!==0&&weekday!==6&&!holidays[year].includes(day.slice(5));}
function calendar(now){const p=parts(now,'America/New_York'),day=`${p.year}-${p.month}-${p.day}`;if(session(day)===null)return {known:false,open:false,next:null};const close=early.has(day)?13:16;
 const open=session(day)&&now>=wallUtc(day,9,30)&&now<wallUtc(day,close);let next=null;
 for(let i=0;i<15;i++){const d=new Date(day+'T12:00:00Z');d.setUTCDate(d.getUTCDate()+i);const key=d.toISOString().slice(0,10);if(session(key)===null)break;const candidate=wallUtc(key,9,30);if(session(key)&&candidate>now){next=candidate;break;}}
 return {known:true,open:!!open,next,earlyClose:early.has(day)};
}
const stamp=x=>{if(!x)return null;const value=new Date(x);return Number.isFinite(+value)?value:null;};
const perth=d=>d?new Intl.DateTimeFormat('en-AU',{timeZone:'Australia/Perth',weekday:'short',day:'numeric',month:'short',hour:'numeric',minute:'2-digit'}).format(d)+' Perth':'Unavailable';
function assess(status,messages=[],now=new Date()){
 // The dashboard supplies the status response's HTTP Date. Device clocks can
 // be wrong; use one clock for both the session and checkpoint comparisons.
 const responseTime=stamp(status._server_time);if(responseTime)now=responseTime;
 const market=calendar(now),state=status.state||{},cycle=stamp(state.last_cycle),age=cycle?(now-cycle)/60000:null;
 const stocks=(status.coverage?.instruments||[]).filter(x=>x.paper_enabled&&x.asset==='US share/ETF');
 const active=new Set((status.open_positions||[]).map(x=>x.symbol));const problems=stocks.filter(x=>['FEED_ERROR','DATA_QUARANTINED','NO_COMPLETED_DATA'].includes(x.status));
 const fetched=stocks.map(x=>stamp(x.last_success)).filter(Boolean).sort((a,b)=>b-a)[0];
 const latestBar=stocks.map(x=>x.last_bar).filter(Boolean).sort().at(-1);
 const symbolSet=new Set(stocks.map(x=>x.symbol));const stockEvent=messages.find(x=>symbolSet.has(x.data?.symbol));
 let title=market.known?(market.open?'Market open · waiting for a completed candle':'Market closed · waiting for the next session'):'Market calendar needs an update';let tone='calm';
 let reason='The active strategy uses completed four-hour candles. Dashboard refreshes do not create new prices or trades. Crypto is observation-only.';
 const relevant=messages.find(x=>x.type==='NEW_BAR'&&symbolSet.has(x.data?.symbol));
 if(market.open&&relevant&&stamp(relevant.ts)&&now-stamp(relevant.ts)<300000)title='New stock candle received · decisions recorded';
 if(!market.known){tone='warn';reason='The display calendar covers 2026–2028 only. Trading continues under the existing rules; no opening time is guessed.';}
 if(market.open&&stocks.some(x=>active.has(x.symbol)&&(!stamp(x.last_success)||now-stamp(x.last_success)>2700000))){title='Market open · position data needs attention';tone='warn';}
 if(problems.length){title='Data needs attention';tone='warn';reason='Feed issues: '+problems.map(x=>x.symbol+' ('+x.status.replaceAll('_',' ').toLowerCase()+')').join(', ')+'. Inspect coverage before relying on displayed prices.';}
 if(!status.scheduler_running||age===null||age>15){title='Scheduler needs attention';tone='warn';reason=!status.scheduler_running?'The scheduler is not running.':'No recent scheduler checkpoint is available. Displayed values may be old.';}
 if(Object.hasOwn(status,'_server_time')&&!responseTime){title='Server clock unavailable';tone='warn';reason='The status response has no usable server timestamp. Session and freshness checks cannot be verified.';}
 if(state.frozen){title='Paper desk paused · risk control active';tone='warn';reason=state.freeze_reason||'A risk freeze blocks entries. Review the evidence; this banner does not unfreeze the desk.';}
 const clockUnknown=Object.hasOwn(status,'_server_time')&&!responseTime;
 return {title,tone,reason,market:clockUnknown?'Server time unavailable':market.known?(market.open?'Regular session open':'Regular session closed'):'Calendar unavailable',next:!clockUnknown&&market.next?perth(market.next):'Unavailable',cycle:perth(cycle),feed:perth(fetched),bar:latestBar?latestBar+' New York · candle start':'No stock candle recorded',event:perth(stamp(stockEvent?.ts))};
}
function render(status,messages,now){const r=assess(status,messages,now),box=document.getElementById('desk-activity');if(!box)return;box.dataset.tone=r.tone;for(const [id,key] of [['activity-title','title'],['activity-reason','reason'],['activity-market','market'],['activity-next','next'],['activity-cycle','cycle'],['activity-feed','feed'],['activity-bar','bar'],['activity-event','event']])document.getElementById(id).textContent=r[key];}
function unavailable(){const box=document.getElementById('desk-activity');if(!box)return;box.dataset.tone='warn';document.getElementById('activity-title').textContent='Dashboard connection needs attention';document.getElementById('activity-reason').textContent='Could not refresh desk status. Any displayed timestamps and values are from the last successful dashboard refresh.';}
root.DeskActivity={assess,calendar,wallUtc,render,unavailable};if(typeof module!=='undefined')module.exports=root.DeskActivity;
})(typeof window!=='undefined'?window:globalThis);
