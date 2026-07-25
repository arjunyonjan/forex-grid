# 24H Synthetic Simulation Plan

## Goal
Run 24 hours of 1-second ticks through the straddle grid instantly to estimate monthly performance.

## Data Source
**Synthetic** — Geometric Brownian Motion (GBM) calibrated to XAU/USD.
- No API key, zero cost, instant generation
- Parameters: 15% annual vol, $0.60 spread, zero drift
- Generates 86,400 ticks with realistic bid/ask prices

## Endpoint
`GET /simulate?hours=24`
- Generates GBM ticks for specified duration
- Resets live broker state → feeds all ticks at max speed → restores state
- Returns JSON: `{start_balance, end_balance, total_trades, wins, losses, max_dd, monthly_equiv}`

## Frontend
- "24H" button in header bar
- Spinner while running
- Results card: 2×4 grid (Start, End, Trades, Wins, Win%, DD, Monthly%)
- Results auto-dismiss on next SSE tick or manual close

## Files to Edit
| File | Change |
|------|--------|
| `broker.py` | Add `simulate(hours, start_price)` using GBM |
| `main.py` | Add `/simulate` GET endpoint |
| `js/app.js` | Add button + results card display |

## Not Changed
- Components (price-bar, stats-panel, etc.)
- Tests (9/9 should still pass)
