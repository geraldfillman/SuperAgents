# Insider Tracker

Purpose: monitor insider buying and selling around contract and milestone events.

Focus:

- open-market purchases before milestone-rich windows
- repeated executive sales before slippage disclosures
- trade clustering around financing events

This concept can be reused from the biotech project with domain-specific alert thresholds.

Workflow:

- resolve ticker to CIK through the SEC mapping
- fetch recent Form 4 entries from SEC submissions
- download ownership XML from the SEC archive
- parse normalized insider-trade records into `data/processed/insider_trades`
