# Financial Monitor

Purpose: estimate runway and financing risk for aerospace and defense issuers.

Track:

- cash balance
- quarterly burn
- equity raises
- debt financing
- going concern language

This concept is intentionally portable from the biotech project, but implementation should only be copied after the SEC cache contract is fixed.

Workflow:

- fetch SEC `companyfacts` for a ticker or CIK
- use watchlist batch mode with `--only-missing` for broad coverage refreshes
- estimate liquidity and operating burn from primary XBRL concepts
- search cached filing text for explicit going-concern language
- write normalized `financials` records to `data/processed/financials`
