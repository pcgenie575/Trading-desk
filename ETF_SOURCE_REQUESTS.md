# ETF source questions — ready to send

Prepared 17 October 2026. Status: **DRAFT, NOT SENT**. These requests seek free source clarification; they do not authorise a purchase, paid data subscription or use of personal credentials.

## IAU — request to issuer

Use the [official iShares contact form](https://www.ishares.com/us/about-us/contact-us), selecting the appropriate investor type. No recipient email address is assumed.

Subject: IAU historical cash/property distributions, 2006–2015

Hello iShares team,

I am checking historical data for the US-listed iShares Gold Trust (IAU) for paper-trading research.

Could you provide an authoritative record of all cash or property distributions with ex-dates from 1 January 2006 through 31 December 2015? If none occurred, could you explicitly confirm that the entire period had no such distributions?

If there were events, please include the ex-date, amount and currency per share, record date and payable date, and explain the share basis around the 10-for-1 split effective for NYSE Arca pricing on 24 June 2010. Please distinguish shareholder distributions from gold sold to pay trust expenses and from in-kind basket redemptions.

The historical statements show gold-sale proceeds offsetting sponsor fees, but I would like to avoid treating a missing distribution worksheet or a current distribution-frequency label as a complete historical register.

A free public document or written product-data clarification would be sufficient. Please do not enrol me in a paid service.

Thank you.

## GSG — request for source clarification

This can be included as a separate issuer enquiry. The issuer may refer daily market-price questions to the exchange or a data publisher; no publisher support message has been sent.

Subject: GSG early daily market-price history and field definitions

Hello iShares team,

I am verifying US-listed GSG daily historical market prices for July 2006 through December 2015 for paper-trading research.

NYSE Information Memo 06-52, dated 21 July 2006, schedules the start of NYSE trading for that day. Historical issuer filings refer to a 19 July 2006 IPO, while fund inception is 10 July. Could you confirm the first regular exchange-trading session and distinguish these dates?

Do you provide, or identify a free authoritative source for, daily traded open/high/low/close prices from the first session onward? Please clarify the session/timezone, whether values are market trades rather than NAV, and whether historical values are adjusted for splits or other actions.

Two retained data sources disagree materially on early daily ranges. One reports identical open/high/low/close on all 253 retained 2008 sessions. Quarterly sale-price extrema in filings are useful checks, but cannot validate each day's intraday range. I am therefore looking for field definitions and trustworthy daily records rather than permission to infer missing prices.

A free public source or clarification is welcome; please do not enrol me in a paid service.

Thank you.

## How a reply will be handled

1. Retain the original response and attachments privately, including dates, source identity and file hashes. Do not publish personal contact details or a private support conversation.
2. Confirm that the reply names the correct US-listed instrument, covers the entire requested period and distinguishes cash/property distributions from redemptions or trust expenses.
3. Preserve any event details at original precision. An ambiguous “does not pay dividends” response does not resolve historical coverage.
4. Record source clarification separately from the original dataset and failed experiment. Check price semantics before assembling any additional component.
5. Document any new evidence standard or first-session protocol revision before testing. A support reply does not activate a strategy or clear unrelated quality failures.

## Current decision

The five-asset input draft remains partial. IAU distribution coverage and GSG daily OHLC reliability remain blocked. The NYSE notice supports a 21 July trading start, so a requirement for a traded bar by 20 July needs an explicit protocol correction; it must not be filled with an invented price.

The official product page and download link were checked again. They did not expose a complete historical distribution register through the available web reader. No repeated API download or paid endpoint was used. Broad searches and generic “no dividend” labels are not substitutes for the missing evidence.

See [evidence decision](ETF_EVIDENCE_DECISION.md) and [input revision](INPUT_REVISION.md).
