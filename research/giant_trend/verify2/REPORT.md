Ambiguities / choices (verify2):
- Start: buy target at start-day close; returns from next day. Last day: liquidate (0.3% cost), tax that year.
- Decision-day state: filings with decision idx <= t; live if t - decision idx <= 200. Rebalance on every decision day of any giant.
- "Finite price" for selection = raw adj[t] finite (not ffilled); membership from packed member array.
- Annual tax paid at last trading day of year by scaling all positions/basis/cash pro rata (not counted as sale); buy costs capitalised into basis; sale gain uses net proceeds. Dividend income itself not taxed. Deduction 0.25 absolute.
- Delisting rule only when last price >5 days before panel end; 250d return uses ffilled price at last-250.
- Sharpe: pre-tax net daily ret minus rf/252 (rate_known_pct ffilled to panel dates). CAGR years=(days)/365.25. MaxDD on pre-tax net curve (after-tax also in json).
- EW rebalances first trading day of each calendar quarter (from 1999-07-01) plus initial purchase at start; H2 EW also starts equal weight at 2007-01-01.
- Empty target => cash earning max(rf-2%,0)*0.846.
