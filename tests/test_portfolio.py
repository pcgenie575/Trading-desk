import unittest,sys,copy
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from test_edge_lab import daily_bars
from excursions import initial,observe,report
from portfolio_research import simulate,PROTOCOL
from risk_policy import assess
from execution import COSTS,sized_entry

class PortfolioEvidence(unittest.TestCase):
    def data(self):
        bars=daily_bars(160)
        # Identical simultaneous breakouts must not become four independent positions.
        for i,b in enumerate(bars):
            p=100+i;b.update(open=p,high=p+.1,low=p-.1,close=p,volume=1000)
        return {s:copy.deepcopy(bars) for s in PROTOCOL['symbols']}

    def test_shared_cash_correlation_and_future_prices(self):
        data=self.data();a=simulate(data)
        self.assertTrue(any('CONCENTRATION_COMBINED' in d['failed_checks'] for d in a['risk_decisions']))
        self.assertLessEqual(max(p['open_positions'] for p in a['equity_curve']),3)
        self.assertLessEqual(max(p['gross_book_cost'] for p in a['equity_curve']),750+1e-6)
        self.assertTrue(a['trade_log']);self.assertIn('excursions',a['trade_log'][0])
        for bars in data.values():bars.append(dict(datetime='2016-01-04',open=1,high=1,low=1,close=1,volume=1))
        self.assertEqual(a,simulate(data))

    def test_gap_loss_freezes_entries_but_exits_are_recorded(self):
        data=self.data()
        for bars in data.values():
            for b in bars[110:]:b.update(open=60,high=61,low=59,close=60)
        r=simulate(data)
        self.assertTrue(r['freeze']);self.assertTrue(any(t['loss_exceeded_plan'] for t in r['trade_log']))
        self.assertEqual(r['trade_log'][0]['reason'],'OPENING_GAP_STOP')
        after=[p for p in r['equity_curve'] if p['day']>=r['freeze']['day']]
        self.assertTrue(all(p['frozen'] and p['open_positions']==0 for p in after))

    def test_excursions_do_not_include_post_exit_high(self):
        s=initial(100,2,25);s=observe(s,dict(datetime='a',open=99,low=90,high=150),95)
        r=report(s);self.assertEqual(r['mfe_pct'],0);self.assertEqual(r['mae_pct'],5)
        self.assertTrue(r['exit_order_uncertain']);self.assertEqual(s,observe(s,dict(datetime='a',open=50,low=1,high=200)))
        gap=report(observe(initial(100,2,25),dict(datetime='b',open=80,low=1,high=200),95))
        self.assertEqual(gap['mae_pct'],20);self.assertFalse(gap['exit_order_uncertain'])

    def test_fill_gate_rejects_changed_daily_loss_and_cash(self):
        f=sized_entry(100,95);c=dict(quantity=f['qty'],entry_reference=f['price'],stop=95,position_value=f['qty']*f['price'],planned_loss=f['qty']*(f['price']-95),cash_cost=f['cash'],cost_adjusted_risk=f['planned_loss'])
        state=dict(cash=5000,equity=5000,peak_equity=5000,frozen=False)
        self.assertTrue(assess(c,'SPY',state,[],0,{},dict(max_position=500,max_planned_loss=25,daily_loss_stop=75,drawdown_freeze=250))['approved'])
        self.assertFalse(assess(c,'SPY',dict(state,cash=1),[],-80,{},dict(max_position=500,max_planned_loss=25,daily_loss_stop=75,drawdown_freeze=250))['approved'])
