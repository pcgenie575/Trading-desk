"""Reconcile recorded cashflows; never estimate missing historical execution costs."""
import json,math
COMPONENTS=('spread','slippage','commission','fx')

def valid_fill(value):
    return isinstance(value,dict) and all(isinstance(value.get(k),(int,float)) and math.isfinite(value[k]) and value[k]>=0 for k in (*COMPONENTS,'fee','total_cost','price','qty','cash')) and math.isclose(sum(value[k] for k in COMPONENTS),value['total_cost'],abs_tol=1e-6)

def reconcile(positions,contexts,executions,marks,state,starting_balance):
    rows=[];known={k:0. for k in COMPONENTS};closed_net=0.;open_net=0.;missing_marks=[]
    for p in positions:
        evidence={side:executions.get((p['id'],side)) for side in ('buy','sell')}
        if not evidence['buy']:evidence['buy']=contexts.get(p['id'],{}).get('execution',{}).get('entry')
        sides=['buy','sell'] if p['status']=='CLOSED' else ['buy']
        complete=all(valid_fill(evidence[x]) for x in sides)
        parts={k:sum(evidence[x][k] for x in sides if valid_fill(evidence[x])) for k in COMPONENTS}
        for k in COMPONENTS:known[k]+=parts[k]
        residuals={}
        if valid_fill(evidence['buy']):residuals['entry_cash']=p['position_value']-evidence['buy']['cash']
        if p['status']=='CLOSED':
            net=p['realized_pnl'];closed_net+=net
            if valid_fill(evidence['sell']):residuals['exit_cash']=p['realized_pnl']-(evidence['sell']['cash']-p['position_value'])
        else:
            mark=marks.get(p['symbol'])
            if mark is None:net=None;missing_marks.append(p['symbol'])
            else:net=p['qty']*mark-p['position_value'];open_net+=net
        cost=sum(parts.values())
        rows.append({'trade_id':p['id'],'symbol':p['symbol'],'status':p['status'],'recorded_net_pnl':net,
          'known_cost_components':parts,'known_cost_total':cost,'cost_coverage':'COMPLETE_RECORDED_MODEL' if complete else 'INCOMPLETE_LEGACY',
          'missing_sides':[x for x in sides if not valid_fill(evidence[x])],
          'gross_before_recorded_costs':net+cost if complete and net is not None else None,
          'cashflow_residuals':residuals,'cashflows_reconcile':all(abs(x)<1e-6 for x in residuals.values()),
          'note':'Open P/L includes entry costs only; future liquidation costs and AUD FX returns are not included.' if p['status']=='OPEN' else 'Net is the unchanged ledger result; unknown costs are not zero.'})
    expected_cash=starting_balance+closed_net-sum(p['position_value'] for p in positions if p['status']=='OPEN')
    expected_equity=expected_cash+sum(p['qty']*marks[p['symbol']] for p in positions if p['status']=='OPEN' and p['symbol'] in marks)
    return {'version':'profit-evidence-v1','currency':'USD','closed_trades':sum(p['status']=='CLOSED' for p in positions),
      'realized_net':closed_net,'open_mark_net':None if missing_marks else open_net,
      'known_execution_costs':known,'incomplete_cost_trades':sum(r['cost_coverage']=='INCOMPLETE_LEGACY' for r in rows),
      'gross_expectancy_available':bool(rows) and all(r['cost_coverage']=='COMPLETE_RECORDED_MODEL' for r in rows),
      'cash_residual':state['cash']-expected_cash,'equity_residual':None if missing_marks else state['equity']-expected_equity,
      'missing_marks':missing_marks,'trades':rows,'edge_validated':False,
      'limitations':['Estimated fill costs are not verified broker charges.','Legacy omissions remain unknown, not reconstructed from current tariffs.','No taxes, AUD returns, deposits or withdrawals are modelled.','Spread/slippage already affect fill prices: do not subtract them from ledger net twice.']}

def from_database(s):
    c=s['db']();positions=[dict(r) for r in c.execute('SELECT * FROM positions')]
    contexts={r['trade_id']:json.loads(r['payload']) for r in c.execute('SELECT * FROM trade_context')}
    fills={(r['trade_id'],r['side']):json.loads(r['payload']) for r in c.execute('SELECT * FROM execution_evidence')}
    # Original PAPER_EXIT audit payloads can supply evidence without rewriting legacy rows.
    for r in c.execute("SELECT trade_id,data FROM messages WHERE type='PAPER_EXIT' ORDER BY ts"):
        f=json.loads(r['data']).get('costs')
        if valid_fill(f):fills.setdefault((r['trade_id'],'sell'),f)
    c.close();raw=s['state_raw']();marks={}
    for p in positions:
        value=raw.get('mark:'+p['symbol'])
        if value is not None:
            value=float(value)
            if math.isfinite(value) and value>0:marks[p['symbol']]=value
    report=reconcile(positions,contexts,fills,marks,s['get_state'](),s['RULES']['starting_balance'])
    report['mark_freshness']=[{'symbol':p['symbol'],'last_success':raw.get('feed_success:'+p['symbol']),
      'last_bar':raw.get(s['checkpoint_key'](p['symbol'])),'coverage':raw.get('coverage:'+p['symbol'],'UNKNOWN'),
      'quarantined':json.loads(raw.get('quality:'+p['symbol'],'{}')).get('quarantined',False)} for p in positions if p['status']=='OPEN']
    return report
