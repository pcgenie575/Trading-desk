import unittest,sys,math,json
from pathlib import Path
from datetime import date,timedelta
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from daily_research import features,context,simulate_daily,VARIANTS,NEIGHBOURS,PROTOCOL,validate_daily,run_daily,SYMBOLS
from cost_diagnostics import diagnose,matched_reprice,SCENARIOS,metrics
from research_engine import simulate
from execution import COSTS,fill
import test_operations as base
room=base.room

def daily_bars(count=350):
    bars=[];day=date(2014,1,1)
    while len(bars)<count:
        if day.weekday()<5:
            i=len(bars);p=100+i*.12+math.sin(i/15)*2
            bars.append(dict(datetime=day.isoformat(),open=p-.1,high=p+.05,low=p-.2,close=p,volume=1000))
        day+=timedelta(days=1)
    return bars

class EdgeMath(unittest.TestCase):
    def test_daily_adapter_includes_end_day_and_rejects_wrong_identity(self):
        from market_data import TwelveDataAdapter,MarketDataError
        from urllib.parse import urlparse,parse_qs
        from io import BytesIO
        bar={'datetime':'2026-10-09','open':'100','high':'101','low':'99','close':'100','volume':'10'}
        payload={'meta':{'symbol':'SPY','currency':'USD','interval':'1day','exchange':'NYSE Arca'},'values':[bar]}
        requests=[]
        def response(req,**kwargs):requests.append(parse_qs(urlparse(req.full_url).query));return BytesIO(json.dumps(payload).encode())
        with patch('market_data.urlopen',side_effect=response):
            r=TwelveDataAdapter('synthetic-key').historical_daily('SPY','2026-10-09','2026-10-09')
            self.assertEqual(r['bars'][0]['datetime'],'2026-10-09');self.assertEqual(requests[0]['end_date'],['2026-10-09 23:59:59']);self.assertEqual(requests[0]['adjust'],['splits'])
            payload['meta']['symbol']='AAPL'
            with self.assertRaises(MarketDataError):TwelveDataAdapter('synthetic-key').historical_daily('SPY','2026-10-09','2026-10-09')

    def test_fixed_path_repricing_and_roundtrip(self):
        from test_research import ResearchOperations
        bars=ResearchOperations().dataset();r=simulate(bars,126,'breakout','full')
        fixed=matched_reprice(r['trade_log'],bars,COSTS)
        self.assertAlmostEqual(fixed['net_pnl'],r['net_pnl'],places=7)
        result=diagnose('SPY',bars,126)
        self.assertEqual(len(result['variants']),8);self.assertTrue(result['period_reused'])
        self.assertAlmostEqual(result['example_round_trip']['cost'],6.2)
        self.assertGreaterEqual(matched_reprice(r['trade_log'],bars,SCENARIOS['fx_0bps'])['net_pnl'],fixed['net_pnl'])
        self.assertEqual(PROTOCOL['promotion']['min_trades'],100)

    def test_features_and_rs_never_use_future(self):
        bars=daily_bars();dataset={s:[dict(b) for b in bars] for s in SYMBOLS};before=context(dataset)
        for b in dataset['TSLA'][300:]:
            for k in ('open','high','low','close'):b[k]*=3
        after=context(dataset);day=bars[299]['datetime']
        self.assertEqual(before[0]['TSLA'][day],after[0]['TSLA'][day]);self.assertEqual(before[1][day],after[1][day])
        self.assertEqual(features(bars[:300])[day],features(bars)[day])

    def test_every_declared_candidate_and_neighbour_executes_real_math(self):
        bars=daily_bars();dataset={s:[dict(b) for b in bars] for s in SYMBOLS};ctx=context(dataset)
        for variant in VARIANTS+NEIGHBOURS:
            r=simulate_daily('AAPL' if variant.get('relative_strength') else 'SPY',bars,variant,bars[0]['datetime'],bars[-1]['datetime'],COSTS,ctx)
            self.assertGreater(r['trades'],0,variant['id']);self.assertAlmostEqual(r['net_pnl'],sum(t['pnl'] for t in r['trade_log']))

    def test_daily_next_session_open_gap_and_conservation(self):
        bars=daily_bars();ctx=context({'SPY':bars})
        r=simulate_daily('SPY',bars,VARIANTS[0],bars[0]['datetime'],bars[-1]['datetime'],COSTS,ctx)
        self.assertTrue(r['trades']);self.assertAlmostEqual(r['net_pnl'],sum(t['pnl'] for t in r['trade_log']))
        entry_index=next(i for i,b in enumerate(bars) if b['datetime']==r['trade_log'][0]['entry_time'])
        gapbars=[dict(b) for b in bars];gapday=gapbars[entry_index+1];price=gapday['open']*.8
        gapday.update(open=price,high=price+1,low=price-1,close=price)
        gapresult=simulate_daily('SPY',gapbars,VARIANTS[0],bars[0]['datetime'],bars[-1]['datetime'],COSTS,context({'SPY':gapbars}))
        self.assertEqual(gapresult['trade_log'][0]['reason'],'PROTECTIVE_STOP');self.assertLess(gapresult['trade_log'][0]['pnl'],-25)
        # Entire predeclared development result unaffected by later changed prices.
        cutoff=bars[280]['datetime'];a=simulate_daily('SPY',bars,VARIANTS[0],bars[0]['datetime'],cutoff,COSTS,ctx)
        changed=[dict(b) for b in bars]
        for b in changed[281:]:
            for k in ('open','high','low','close'):b[k]*=3
        b=simulate_daily('SPY',changed,VARIANTS[0],bars[0]['datetime'],cutoff,COSTS,context({'SPY':changed}))
        self.assertEqual(a,b)
        # Remove a known next SPY session: its intended next-open fill must be skipped.
        target=r['trade_log'][0]['entry_time'];missing=[b for b in bars if b['datetime']!=target]
        ctx2=context({'SPY':bars,'AAPL':missing})
        result=simulate_daily('AAPL',missing,VARIANTS[0],bars[0]['datetime'],bars[-1]['datetime'],COSTS,ctx2)
        self.assertGreater(result['skipped_missing_next_sessions'],0)

    def test_promotion_concentration_and_invalid_history(self):
        m=metrics([{'pnl':100,'r':4},{'pnl':80,'r':3.2},{'pnl':-5,'r':-.2}])
        self.assertEqual(m['positive_profit_top_two_share'],1);self.assertLess(m['pnl_excluding_best_two'],0)
        bars=daily_bars();bad=[dict(b) for b in bars];bad[1]['datetime']=bad[0]['datetime']
        with self.assertRaises(ValueError):validate_daily(bad)
        with self.assertRaises(ValueError):run_daily({'SPY':bars})
        with self.assertRaises(ValueError):run_daily({s:bars for s in SYMBOLS})

    def test_selection_opens_only_one_validation_and_failed_development_stops(self):
        bars=[];day=date(2006,1,2)
        while day<=date(2026,10,9):
            if day.weekday()<5:bars.append(dict(datetime=day.isoformat(),open=100,high=101,low=99,close=100,volume=100))
            day+=timedelta(days=1)
        data={s:bars for s in SYMBOLS};calls=[]
        def summary(dataset,variant,symbols,start,end,cost,ctx):
            calls.append((variant['id'],start))
            trade={'pnl':10,'r':.4,'costs':1}
            return dict(metrics([trade]*120),sum_individual_drawdowns=10,symbol_results={s:{'trade_log':[dict(trade,symbol=s)]} for s in symbols})
        def fakecontext(dataset):return ({'SPY':{b['datetime']:{} for b in bars}}, {}, {})
        with patch('daily_research.context',side_effect=fakecontext),patch('daily_research.summarize',side_effect=summary),patch('daily_research.passive',return_value={'max_drawdown':20,'net_pnl':100}):
            result=run_daily(data)
        self.assertEqual(result['selected_candidate'],'daily_100_20_50')
        self.assertEqual([v for v,start in calls if start=='2016-01-01'],['daily_100_20_50']*2)
        self.assertTrue(result['numeric_screen_passed']);self.assertFalse(result['forward_paper_eligible'])
        calls.clear()
        def negative(*args):
            r=summary(*args);r['expectancy_r']=-.1;return r
        with patch('daily_research.context',side_effect=fakecontext),patch('daily_research.summarize',side_effect=negative):result=run_daily(data)
        self.assertIsNone(result['historical_validation']);self.assertFalse(any(start=='2016-01-01' for _,start in calls))

class EdgeAPI(base.Operations):
    def test_register_daily_once_auth_and_no_ledger_change(self):
        from fastapi.testclient import TestClient
        # Freeze the data worker so this endpoint test never calls a real provider.
        with patch('edge_lab_api.threading.Thread'):
            with TestClient(room.app) as client:
                self.assertEqual(client.get('/edge-lab').status_code,401);client.auth=('operator','test-password')
                self.assertEqual(client.post('/edge-lab/daily').status_code,401)
                headers={'X-Control-Token':'test-control-token'}
                first=client.post('/edge-lab/daily',headers=headers).json();again=client.post('/edge-lab/daily',headers=headers).json()
                self.assertEqual(first['id'],again['id']);self.assertTrue(first['payload']['selection_locked_before_data'])
                self.assertEqual(client.get('/edge-lab').json()['runs'][0]['protocol']['version'],'daily-edge-v1')
                room.init_db();self.assertEqual(client.get('/edge-lab/'+first['id']).status_code,200)
                self.assertEqual(client.post('/edge-lab/'+first['id']+'/retry-data',headers=headers).status_code,409)
                self.assertEqual(room.positions(),[]);self.assertEqual(room.get_state()['cash'],5000)
                self.assertEqual(room.PROTOCOL['version'],'swing-research-v2')

for name in list(base.Operations.__dict__):
    if name.startswith('test_'):setattr(EdgeAPI,name,None)
if __name__=='__main__':unittest.main()


