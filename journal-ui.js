let journalTrade=null,journalDirty=false;
const ruleLabels={none:'No tagged break',moved_stop:'Moved stop',oversized:'Oversized',revenge_trade:'Revenge trade',fomo:'FOMO',other:'Other'};
function dateNumber(value){const m=/^(\d{4})-(\d{2})-(\d{2})/.exec(value||'');return m?Date.UTC(+m[1],+m[2]-1,+m[3]):null}
function holdingDays(p){const a=dateNumber(p.entry_time),b=dateNumber(p.exit_time);return a===null||b===null?null:Math.max(0,(b-a)/86400000)}
function currentTradingMonth(){const parts=new Intl.DateTimeFormat('en-US',{timeZone:'America/New_York',year:'numeric',month:'2-digit'}).formatToParts(new Date());return parts.find(p=>p.type==='year').value+'-'+parts.find(p=>p.type==='month').value}
function groupedResults(rows,key){
 const groups={};rows.filter(p=>p.status==='CLOSED').forEach(p=>{const k=key(p);if(k===null)return;const g=groups[k]||(groups[k]={key:k,count:0,net:0,rTotal:0,rCount:0});g.count++;g.net+=p.realized_pnl||0;if(p.planned_loss>0){g.rTotal+=(p.realized_pnl||0)/p.planned_loss;g.rCount++}});
 return Object.values(groups).map(g=>({...g,average:g.net/g.count,expectancyR:g.rCount?g.rTotal/g.rCount:null})).sort((a,b)=>b.net-a.net);
}
function journalRows(){
 const symbol=document.getElementById('journal-symbol').value||'ALL',month=document.getElementById('journal-month').value||'';
 return (snapshot.journal?.trades||[]).filter(p=>(symbol==='ALL'||p.symbol===symbol)&&(!month||(p.exit_time||p.entry_time).startsWith(month)));
}
function tradeAnalytics(rows){
 const closed=rows.filter(p=>p.status==='CLOSED').sort((a,b)=>(a.exit_time||'').localeCompare(b.exit_time||'')||a.id.localeCompare(b.id));
 const wins=closed.filter(p=>p.realized_pnl>0),profit=wins.reduce((n,p)=>n+p.realized_pnl,0),loss=-closed.filter(p=>p.realized_pnl<0).reduce((n,p)=>n+p.realized_pnl,0);
 let total=0,peak=0,drawdown=0;const curve=[0];
 closed.forEach(p=>{total+=p.realized_pnl||0;peak=Math.max(peak,total);drawdown=Math.max(drawdown,peak-total);curve.push(total)});
 const rTrades=closed.filter(p=>p.planned_loss>0),assessed=closed.filter(p=>p.review_status==='reviewed'&&['yes','partial','no'].includes(p.followed_rules));
 return {closed:closed.length,net:total,winRate:closed.length?wins.length/closed.length*100:null,average:closed.length?total/closed.length:null,profitFactor:loss?profit/loss:null,noLosses:closed.length>0&&loss===0,drawdown,curve,
 expectancyR:rTrades.length?rTrades.reduce((n,p)=>n+(p.realized_pnl||0)/p.planned_loss,0)/rTrades.length:null,rCount:rTrades.length,
 averageWin:wins.length?profit/wins.length:null,averageLoss:closed.length-wins.length-closed.filter(p=>p.realized_pnl===0).length?loss/closed.filter(p=>p.realized_pnl<0).length:null,
 adherence:assessed.length?assessed.filter(p=>p.followed_rules==='yes').length/assessed.length*100:null,assessed:assessed.length};
}
function journalChart(a){
 if(!a.closed)return '<div class="empty-state">The performance curve starts after your first closed paper trade.</div>';
 const low=Math.min(...a.curve),high=Math.max(...a.curve),range=high-low||1;
 const points=a.curve.map((v,i)=>[20+i/(a.curve.length-1)*660,140-(v-low)/range*105]);
 let peak=0;const peaks=a.curve.map((v,i)=>{peak=Math.max(peak,v);return [points[i][0],140-(peak-low)/range*105]});const zero=140-(0-low)/range*105;
 return '<svg class="journal-chart" viewBox="0 0 700 170" role="img" aria-label="Cumulative closed-trade profit and loss and high-water mark, '+esc(money(a.net))+'"><path d="M20 '+zero+'H680" stroke="#57718c" stroke-dasharray="3 5"/><polyline points="'+peaks.map(p=>p.join(',')).join(' ')+'" fill="none" stroke="#b39cff" stroke-width="1.5" stroke-dasharray="4 4"/><polyline points="'+points.map(p=>p.join(',')).join(' ')+'" fill="none" stroke="'+(a.net>=0?'#71e2c0':'#ff9fa7')+'" stroke-width="2.5"/><text x="20" y="165" fill="#9badc3" font-size="10">Start · cumulative P/L</text><text x="680" y="165" fill="#9badc3" font-size="10" text-anchor="end">'+a.closed+' closed trades</text><text x="20" y="20" fill="#b39cff" font-size="10">'+esc(money(high))+' high-water mark</text></svg>';
}
function resultTable(groups){
 if(!groups.length)return '<div class="empty-state">Results appear after trades close.</div>';
 const scale=Math.max(...groups.map(g=>Math.abs(g.net)),1);
 return '<div class="tablewrap"><table><thead><tr><th>Group</th><th>Trades</th><th>Net P/L</th><th>Expectancy</th></tr></thead><tbody>'+groups.map(g=>'<tr><td>'+esc(g.key)+'<span class="result-bar" style="width:'+Math.max(2,Math.abs(g.net)/scale*100)+'%;background:'+(g.net>=0?'#71e2c0':'#ff9fa7')+'"></span></td><td>'+g.count+'</td><td class="'+(g.net<0?'negative':'positive')+'">'+money(g.net)+'</td><td>'+(g.expectancyR===null?'—':g.expectancyR.toFixed(2)+'R')+'</td></tr>').join('')+'</tbody></table></div>';
}
function renderSwingPanels(rows){
 const month=currentTradingMonth(),monthly=tradeAnalytics(snapshot.journal.trades.filter(p=>p.exit_time?.startsWith(month))),s=snapshot.status;
 const dailyHeadroom=Math.max(0,s.rules.daily_loss_stop+s.daily_realized_pnl),drawdown=Math.max(0,s.state.peak_equity-s.state.equity),ddHeadroom=Math.max(0,s.rules.drawdown_freeze-drawdown);
 document.getElementById('swing-summary').innerHTML='<div><span class="eyebrow">SWING DESK · '+esc(month)+' · PAPER</span><h2>Net closed P/L this month</h2><strong class="swing-pnl '+(monthly.net<0?'negative':'positive')+'">'+(monthly.closed?money(monthly.net):'—')+'</strong><p class="muted">'+monthly.closed+' completed trades · '+(monthly.closed?'Recorded outcomes after simulated slippage':'Building the first closed-trade sample')+'</p></div><div class="swing-headroom"><span>Daily loss headroom<b>'+money(dailyHeadroom)+'</b></span><span>Drawdown headroom<b>'+money(ddHeadroom)+'</b></span><span>Peak-to-equity drawdown<b>'+money(drawdown)+'</b></span><span>Open paper positions<b>'+(s.open_positions||[]).length+' / '+s.rules.max_open_positions+'</b></span><small>Daily headroom uses realized P/L. Drawdown uses recorded marks; both are subject to the desk’s circuit breakers.</small></div>';
 const setups=groupedResults(rows,p=>p.context?.strategy||'Earlier trade · setup not captured');
 document.getElementById('setup-results').innerHTML=resultTable(setups);
 document.getElementById('instrument-results').innerHTML=resultTable(groupedResults(rows,p=>p.symbol));
 const eligible=setups.filter(g=>g.count>=5),closed=rows.filter(p=>p.status==='CLOSED');
 document.getElementById('setup-verdict').textContent=closed.length>=20&&eligible.length>=2?'Highest recorded setup net: '+eligible[0].key+' ('+money(eligible[0].net)+', n='+eligible[0].count+'). Lowest: '+eligible.at(-1).key+' ('+money(eligible.at(-1).net)+', n='+eligible.at(-1).count+'). These are historical observations.':'Building the sample: '+closed.length+' closed trades. Setup comparisons need at least two recorded setups, five trades per setup and 20 closed trades overall. The current autonomous engine uses one fixed setup.';
 const bands=['Same day','1–3 days','4–10 days','11+ days'];const cells={};
 closed.forEach(p=>{const days=holdingDays(p),entry=dateNumber(p.entry_time);if(days===null||entry===null)return;const day=new Date(entry).getUTCDay();if(day<1||day>5)return;const band=days===0?0:days<=3?1:days<=10?2:3;const key=band+':'+day;const c=cells[key]||(cells[key]={n:0,pnl:0});c.n++;c.pnl+=p.realized_pnl||0});
 const max=Math.max(1,...Object.values(cells).map(c=>Math.abs(c.pnl/c.n)));
 document.getElementById('swing-heatmap').innerHTML='<div class="tablewrap"><table class="heatmap"><thead><tr><th>Holding period</th>'+['Mon','Tue','Wed','Thu','Fri'].map(d=>'<th>'+d+'</th>').join('')+'</tr></thead><tbody>'+bands.map((band,i)=>'<tr><th>'+band+'</th>'+[1,2,3,4,5].map(day=>{const c=cells[i+':'+day];if(!c)return '<td class="heat-empty">—<small>n=0</small></td>';const avg=c.pnl/c.n;return '<td style="background:rgba('+(avg<0?'239,104,123':'66,196,153')+','+(0.08+Math.abs(avg)/max*.25)+')">'+money(avg)+'<small>n='+c.n+'</small></td>'}).join('')+'</tr>').join('')+'</tbody></table></div>';
 const tagged=closed.filter(p=>p.review_status==='reviewed'&&p.rule_break&&p.rule_break!=='none');
 document.getElementById('discipline-results').innerHTML=resultTable(groupedResults(tagged,p=>ruleLabels[p.rule_break]||'Other'));
 const weeks=groupedResults(rows,p=>{const date=dateNumber(p.exit_time);if(date===null)return null;const day=new Date(date).getUTCDay();return new Date(date-((day+6)%7)*86400000).toISOString().slice(0,10)+' week'}).sort((a,b)=>b.key.localeCompare(a.key));
 document.getElementById('weekly-results').innerHTML=resultTable(weeks.slice(0,8));
}
function renderJournalWorkspace(){
 if(!snapshot.journal)return;
 const select=document.getElementById('journal-symbol'),previous=select.value||'ALL';
 select.innerHTML='<option value="ALL">All instruments</option>'+[...new Set(snapshot.journal.trades.map(p=>p.symbol))].sort().map(s=>'<option value="'+esc(s)+'">'+esc(s)+'</option>').join('');select.value=previous;
 const rows=journalRows(),a=tradeAnalytics(rows);
 if(!journalDirty&&!rows.some(p=>p.id===journalTrade))journalTrade=null;
 document.getElementById('journal-period').textContent='Period: '+(document.getElementById('journal-month').value||'All history')+' · Instrument: '+(select.value||'ALL')+' · Paper account · Trade dates in New York';
 const measures=[['Net closed P/L',a.closed?money(a.net):'—'],['Win rate',a.winRate===null?'—':a.winRate.toFixed(1)+'%'],['Expectancy in R',a.expectancyR===null?'—':a.expectancyR.toFixed(2)+'R'],['Profit factor',a.profitFactor===null?(a.noLosses?'No losses':'—'):a.profitFactor.toFixed(2)],['Closed-trade drawdown',a.closed?money(a.drawdown):'—'],['Completed trades',a.closed],['Avg win / avg loss',(a.averageWin===null?'—':money(a.averageWin))+' / '+(a.averageLoss===null?'—':money(a.averageLoss))],['Rule adherence',a.adherence===null?'Not assessed':a.adherence.toFixed(1)+'% · n='+a.assessed]];
 document.getElementById('journal-analytics').innerHTML=measures.map(([k,v])=>'<div class="journal-stat"><span class="muted">'+k+'</span><strong>'+v+'</strong></div>').join('');
 document.getElementById('journal-curve').innerHTML=journalChart(a);
 renderSwingPanels(rows);
 document.getElementById('journal-list').innerHTML=rows.length?rows.map(p=>'<button class="trade-row" data-trade="'+esc(p.id)+'" aria-pressed="'+(journalTrade===p.id)+'"><span><b>'+esc(p.symbol)+'</b><small>'+esc(p.entry_time)+' · '+esc(p.context?.strategy||'Earlier trade · plan not captured')+'</small></span><span class="data-state">'+esc(p.status)+'</span><span>'+(p.status==='CLOSED'?money(p.realized_pnl):'Open')+'</span><span class="muted">'+esc(p.review_status||'Not reviewed')+'</span></button>').join(''):'<div class="empty-state">No paper trades match these filters.</div>';
 if(!journalDirty)renderJournalTrade();
 const cfg=snapshot.journal.strategy.config;
 document.getElementById('playbook').innerHTML='<span class="eyebrow">ACTIVE STRATEGY</span><h3>'+esc(snapshot.journal.strategy.name)+'</h3><ol><li><b>Plan:</b> completed close above the '+cfg.trend_ma+'-bar average and the previous '+cfg.breakout_lookback+'-bar high.</li><li><b>Risk:</b> protective stop '+(cfg.stop_pct*100).toFixed(0)+'% below reference, subject to the desk’s position and portfolio limits.</li><li><b>Exit:</b> protective stop or close below the '+cfg.exit_ma+'-bar average. Stop gaps use the lower opening price.</li><li><b>Review:</b> compare the saved candidate, execution, exit and your observations.</li></ol><p class="muted">Paper long positions · '+cfg.slippage_bps+' bps simulated slippage per side · no commission charged in the current engine. This playbook describes the active rules; new trade records capture their configuration at entry.</p>';
}
function renderJournalTrade(){
 const p=snapshot.journal.trades.find(p=>p.id===journalTrade),area=document.getElementById('journal-detail');
 if(!p){area.innerHTML='<div class="empty-state">Select a trade to compare its plan, execution and review.</div>';return}
 area.innerHTML='<span class="eyebrow">PAPER TRADE RECORD</span><h3>'+esc(p.symbol)+' · '+esc(p.status)+'</h3><div class="review-facts"><div><small>Entry execution</small><b>'+money(p.entry_price)+'</b></div><div><small>Quantity</small><b>'+p.qty.toFixed(6)+'</b></div><div><small>Protective stop</small><b>'+money(p.stop)+'</b></div><div><small>Planned loss at entry</small><b>'+money(p.planned_loss)+'</b></div></div><p class="muted">'+(p.exit_time?'Exit '+esc(p.exit_time)+' · '+money(p.exit_price)+' · '+esc(p.exit_reason)+'<br>Realized '+money(p.realized_pnl)+' · '+(p.planned_loss>0?(p.realized_pnl/p.planned_loss).toFixed(2)+'R':'R unavailable')+' · '+holdingDays(p)+' calendar days held':'Position remains open. No closed-trade result yet.')+'</p><details><summary>Original plan and strategy configuration</summary>'+(p.context?'<pre>'+esc(JSON.stringify(p.context,null,2))+'</pre>':'<p class="muted">This position predates plan capture. Its execution and protective stop are retained; an original candidate/configuration snapshot is unavailable.</p>')+'</details><form id="trade-review-form"><label>Review status<select name="review_status"><option value="draft">Draft</option><option value="reviewed">Reviewed</option></select></label><label>Did the trade follow its rules?<select name="followed_rules"><option value="unknown">Not assessed</option><option value="yes">Yes</option><option value="partial">Partly</option><option value="no">No</option></select></label><label>Rule-break tag<select name="rule_break">'+Object.entries(ruleLabels).map(([k,v])=>'<option value="'+k+'">'+v+'</option>').join('')+'</select></label><label>Observations and next adjustment<textarea name="notes" maxlength="4000" rows="5" placeholder="What was the setup? What happened? What should we review?"></textarea></label><button class="control" type="submit">Save review</button><span id="review-save-state" role="status"></span><p class="muted">Saved on your server. Last saved: '+esc(stamp(p.review_updated_at))+'</p></form>';
 const form=document.getElementById('trade-review-form');form.elements.review_status.value=p.review_status||'draft';form.elements.followed_rules.value=p.followed_rules||'unknown';form.elements.rule_break.value=p.rule_break||'none';form.elements.notes.value=p.notes||'';
 form.addEventListener('input',()=>{journalDirty=true});form.addEventListener('submit',saveJournalReview);
}
async function saveJournalReview(e){
 e.preventDefault();const form=e.target,button=form.querySelector('button'),label=document.getElementById('review-save-state');
 const token=prompt('Enter your control token to save this review');if(!token)return;
 button.disabled=true;
 try{const response=await fetch('/journal/'+encodeURIComponent(journalTrade)+'/review',{method:'PUT',headers:{'Content-Type':'application/json','X-Control-Token':token},body:JSON.stringify({review_status:form.elements.review_status.value,followed_rules:form.elements.followed_rules.value,rule_break:form.elements.rule_break.value,notes:form.elements.notes.value})});if(!response.ok)throw Error('Review could not be saved ('+response.status+').');journalDirty=false;await refresh();document.getElementById('review-save-state').textContent='Saved.'}catch(err){label.textContent=err.message+' Your text remains here.'}finally{button.disabled=false}
}
function calculateRiskScenario(values,rules,cash){
 const {entry,stop,target,cost,risk}=values;
 if(![entry,stop,target,cost,risk,cash].every(Number.isFinite)||entry<=0||stop<=0||stop>=entry||target<=entry||cost<0||risk<=cost||cash<=0)throw Error('Use positive prices, a stop below entry, a target above entry, and risk greater than estimated costs.');
 const budget=Math.min(risk,rules.max_planned_loss),qty=Math.min((budget-cost)/(entry-stop),rules.max_position/entry,cash/entry);
 if(qty<=0)throw Error('Estimated costs consume the desk’s risk allowance.');
 const loss=qty*(entry-stop)+cost,reward=qty*(target-entry)-cost;
 return {qty,loss,reward,ratio:reward/loss,value:qty*entry,budget};
}
document.getElementById('risk-scenario').addEventListener('submit',e=>{
 e.preventDefault();const form=e.target;try{
 const input=Object.fromEntries(['entry','stop','target','cost','risk'].map(k=>[k,Number(form.elements[k].value)]));
 if(form.elements.risk_mode.value==='percent')input.risk=snapshot.status.state.equity*input.risk/100;
 const result=calculateRiskScenario(input,snapshot.status.rules,snapshot.status.state.cash);
 document.getElementById('risk-result').innerHTML='<b>'+result.qty.toFixed(6)+' shares / units</b><p>Position '+money(result.value)+' · Estimated loss '+money(result.loss)+'<br>Target result '+money(result.reward)+' · Reward/risk '+result.ratio.toFixed(2)+'R</p><p class="muted">Capped by the desk’s per-position cash and risk limits. Scenario only; this does not create an order or alter the strategy. Portfolio approval still applies.</p>';
 }catch(err){document.getElementById('risk-result').textContent=err.message}
});
document.getElementById('journal-list').addEventListener('click',e=>{const row=e.target.closest('[data-trade]');if(!row)return;if(journalDirty&&!confirm('Discard unsaved review edits?'))return;journalDirty=false;journalTrade=row.dataset.trade;renderJournalWorkspace()});
['journal-symbol','journal-month'].forEach(id=>document.getElementById(id).addEventListener('change',renderJournalWorkspace));
document.getElementById('journal-export').addEventListener('click',()=>{
 const payload={export_version:1,mode:'paper',exported_at:new Date().toISOString(),trades:snapshot.journal.trades,strategy:snapshot.journal.strategy};
 const url=URL.createObjectURL(new Blob([JSON.stringify(payload,null,2)],{type:'application/json'})),a=document.createElement('a');a.href=url;a.download='trading-desk-paper-journal-'+new Date().toISOString().slice(0,10)+'.json';a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);
});
document.getElementById('journal-print').addEventListener('click',()=>window.print());
document.getElementById('journal-month').value=currentTradingMonth();
