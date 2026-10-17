# ETF evidence decision and remaining acceptance requirements

Reviewed 17 October 2026. This is a source-review memo, not a new dataset, approved corporate-action record, strategy experiment or investment recommendation.

## Decision

Keep the five-asset draft PARTIAL_DRAFT. IWM, IEF and EFA are assembled for review; IAU and GSG remain mandatory and blocked. No partial-universe simulation, strategy change or promotion is authorised by this memo.

The remaining work is evidence acquisition and input-method approval. Repeating parameter tests cannot resolve these source problems. Do not keep requesting the same failed endpoints or consume paid data credits.

## IAU: historical statements now mapped across 2006–2015

Four primary issuer filings contain audited three-year cash-flow statements whose combined periods cover every requested year:

| Filing | Statement periods | Cash proceeds from gold sales / sponsor fees paid, in USD thousands |
|---|---|---|
| [FY2008, F-6](https://www.sec.gov/Archives/edgar/data/1278680/000119312509040518/d10k.htm) | 2006–2008 | 2006: 2,750 / 2,750; 2007: 4,094 / 4,094; 2008: 6,856 / 6,856 |
| [FY2010, F-6](https://www.sec.gov/Archives/edgar/data/1278680/000119312511047433/d10k.htm) | 2008–2010 | 2008: 6,856 / 6,856; 2009: 8,680 / 8,680; 2010: 11,051 / 11,051 |
| [FY2012, F-6](https://www.sec.gov/Archives/edgar/data/1278680/000119312513084326/d454111d10k.htm) | 2010–2012 | 2010: 11,051 / 11,051; 2011: 17,758 / 17,758; 2012: 24,815 / 24,815 |
| [FY2015, F-6](https://www.sec.gov/Archives/edgar/data/1278680/000143774916026346/iau20151231_10k.htm) | 2013–2015 | 2013: 22,834 / 22,834; 2014: 16,698 / 16,698; 2015: 15,432 / 15,432 |

Amounts are manually transcribed from the primary filing tables; sponsor-fee outflows are shown as positive magnitudes here. Repeated overlap years agree. These statements report no net operating cash generation.

**Interpretation:** this supports the expectation of no routine cash distributions. It does not constitute a complete dated corporate-action history or an explicit issuer certification that no exceptional distributions occurred. Zero net cash alone cannot prove the absence of offsetting cash flows. Amounts are rounded in thousands, not an event-level register.

Item 1 of the FY2008 and FY2015 filings also explains that unexpected cash or property may be distributed, for example following a claim settlement. Therefore a general “no dividend” classification, or absence of a dividend worksheet, is insufficient for our present coverage gate.

The separately retained 2010 split evidence remains valid; it does not resolve cash-distribution coverage. No zero-event record has been inserted into the draft.

### Evidence that would resolve the IAU question

Obtain a complete issuer/trustee corporate-action history covering 1 January 2006 through 31 December 2015, including explicit confirmation of no cash/property distributions if none occurred. If events occurred, require ex-date, amount and currency per share, payable date and the share basis around the 2010 split. Preserve original files, publication context and hashes.

Alternatively, a separately documented methodology review could assess whether audited financial statements plus a complete review of relevant filings/amendments suffice. Such a decision would require a new explicit evidence standard and retained review, rather than silently changing the current parser's coverage flag. This memo supplies neither that approval nor an automatic acceptance path.

## GSG: daily prices and start-date feasibility

### Follow-up: exchange notice identifies 21 July as trading start

The [NYSE Information Memo 06-52](https://www.nyse.com/publicdocs/nyse/regulation/nyse/NYSE_Rules.pdf), dated 21 July 2006, identifies GSG and schedules its NYSE trading start for that day. This is primary exchange evidence supporting the retained candidate's first date, rather than merely another price publisher with the same gap. The web-indexed notice was reviewed; the combined PDF exceeded the web reader's size limit.

Keep the dates distinct: the [issuer's FY2007 filing, Item 5](https://www.sec.gov/Archives/edgar/data/1346616/000119312508055731/d10k.htm) refers to a 19 July 2006 IPO, and its registration statement became effective that day. Fund inception is 10 July. Neither date alone establishes an earlier exchange-traded OHLC bar. The exchange notice is more directly relevant to the intended first trading session; the differing issuer wording is retained rather than discarded.

**Methodology decision:** treat the original requirement for GSG trading data by 20 July as incompatible with the exchange's scheduled start, pending any contrary authoritative transaction record. Do not label the 21 July candidate incomplete solely because it lacks a 20 July bar. This does not approve its daily OHLC or change the original failed coverage check. A future input protocol must explicitly account for the trading start and retain the original DATA_BLOCKED result. No later start or replacement protocol has been activated.

The retained second-publisher candidate begins 21 July 2006; the original protocol requires coverage by 20 July. It also disagrees materially with the saved provider's early OHLC values. Quarterly issuer extrema matching candidate daily closes does not establish valid daily opens, highs and lows.

Evidence required: an authoritative first trading-session date and reliable daily trade OHLC for the original period, with definitions for splits, adjustments and market session. If the fixed cutoff precedes the first tradable session, mark the original protocol infeasible. A later start would need a separately declared protocol revision; never invent a prelisting candle or silently move the cutoff.

## Next decision

Keep autonomous paper observation running under its existing controls. Pause new ETF performance experiments until the inputs and method have been reviewed. Useful next evidence is an issuer/trustee response for IAU and source clarification for GSG. Any external support message requires the user's authorisation before sending. No purchase or account action is required for this memo.

No new price requests, research reruns, runtime code edits, ledger changes or risk changes were made for this review. Original source captures remain unchanged. Web-rendered filing review is not a full original-byte filing archive or amendment review.

See [Input Revision](INPUT_REVISION.md), [Issuer Evidence](ISSUER_EVIDENCE.md), and [GSG Data Integrity](GSG_DATA_INTEGRITY.md).
