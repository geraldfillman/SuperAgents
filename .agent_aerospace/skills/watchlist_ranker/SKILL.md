# Watchlist Ranker

Purpose: turn company scorecards into a ranked watchlist with transparent component scores.

Inputs:

- company scorecards from the processed data or live rebuild
- optional ticker filter
- budget candidate threshold carried through from scorecard generation

Outputs:

- ranked watchlist JSON with composite score and component breakdowns
- plain-language reasons and risks for each ranked company

Priority signals:

- contract award activity
- procurement signals
- execution evidence such as TRL, milestones, and test events
- explicit budget exposure before candidate budget exposure
- financial and insider risk modifiers

Notes:

- rankings are deterministic and explainable; they are not model-generated opinions
- explicit budget overrides should be preferred over thematic candidates whenever available
