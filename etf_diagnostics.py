"""Read-only explanations of saved ETF input failures; never clears a gate."""
import math


def diagnose(dataset, checks, protocol):
    rows = []
    for symbol in protocol['symbols']:
        check = checks.get(symbol, {})
        pages = dataset.get('pages', {})
        maps = [{b['datetime']: b for b in pages.get(symbol + ':' + mode, {}).get('bars', [])}
                for mode in ('none', 'splits', 'all')]
        source = dataset.get('distributions', {}).get(symbol, {})
        cash = {}
        for event in source.get('events', []):
            if event.get('type') == 'distribution':
                cash[event['ex_date']] = cash.get(event['ex_date'], 0) + event['amount']
        years = {}; examples = []; invalid = 0
        dates = sorted(maps[0])
        for previous, day in zip(dates, dates[1:]):
            if not protocol['warmup_start'] <= day <= protocol['development_end']:
                continue
            if not all(previous in m and day in m for m in maps):
                continue
            try:
                r0, s0, a0 = [m[previous]['close'] for m in maps]
                r1, s1, a1 = [m[day]['close'] for m in maps]
                if not all(math.isfinite(x) and x > 0 for x in (r0,s0,a0,r1,s1,a1)):
                    raise ValueError('Invalid prices')
                split_ratio = (r0 / s0) / (r1 / s1)
                implied = (1 - (s1/a1)/(s0/a0)) * (r0/split_ratio)
                amount = cash.get(day, 0)
                expected = 1 - amount / (r0/split_ratio)
                matches = expected > 0 and math.isclose((s1/a1)/(s0/a0), expected, rel_tol=8e-4, abs_tol=8e-4)
            except (TypeError, ValueError, ZeroDivisionError):
                invalid += 1; continue
            if amount > 0:
                y = years.setdefault(day[:4], {'issuer_events':0, 'mismatches':0, 'apparently_unadjusted':0})
                y['issuer_events'] += 1
                if not matches:
                    y['mismatches'] += 1
                    if abs(implied) < amount * .1:
                        y['apparently_unadjusted'] += 1
                    if len(examples) < 3:
                        examples.append({'date':day, 'issuer_cash_per_share':amount, 'provider_implied_cash_per_share':implied})
        issues = check.get('issues', [])
        actions = []
        if any(i.startswith('DISTRIBUTION_RECONCILIATION:') for i in issues):
            actions.append('Resolve issuer/provider adjustment discrepancies using independently verified history; do not relax the tolerance.')
        if 'DISTRIBUTION_SOURCE_UNVERIFIED' in issues:
            actions.append('Obtain complete dated distribution evidence. A missing worksheet is not evidence of zero distributions.')
        if 'SPLIT_EVENT_REQUIRES_INDEPENDENT_VERIFICATION' in issues:
            actions.append('Match every inferred split to an issuer announcement, including its effective date and ratio.')
        if 'WARMUP_HISTORY_TOO_SHORT' in issues:
            actions.append('Obtain the missing early history from a verified free source; do not shorten the registered period.')
        if issues and not actions:
            actions.append('Investigate the recorded input issues before any performance calculation.')
        if not check:
            actions.append('Wait for complete input checks; partial collection is not a pass.')
        rows.append({'symbol':symbol, 'gate_passed':check.get('passed') is True,
                     'distribution_coverage_verified':source.get('coverage_verified') is True,
                     'distribution_adjustments_by_year':years, 'mismatch_examples':examples,
                     'invalid_price_pairs':invalid, 'next_actions':actions})
    return {'version':'etf-input-diagnostics-v1', 'read_only':True, 'extra_provider_requests':0,
            'activation_allowed':False, 'rows':rows,
            'note':'Derived from saved inputs. Implied cash is an adjustment-factor diagnostic, not earned income. Existing gates, protocols and results remain authoritative.'}
