# Risk Policy

Use this policy after collecting live data. Hard gates override scores and
trading-style preferences.

## Risk Modes

| mode | max basic stop width | minimum first target | posture |
|---|---:|---:|---|
| `conservative` | about 1.0% | 1.8R | Hold unless the setup is clean. |
| `balanced` | about 1.5-2.0% | 1.5R | Combine chart invalidation with R. |
| `aggressive` | about 2.5% | 1.3R | Allow some high-volatility momentum. |

Use the tighter value when bars are thin, orderbook gaps are wide, or the move is
already extended. These are defaults, not promises.

## Hard Gates

Return `데이터 부족` when any required source fails: quote, intraday bars,
orderbook, or recent ticks.

Return `보류` for a new-entry request when:

- Intraday bars are fewer than 20 usable candles.
- Tick data is fewer than 5 executions.
- Bid/ask spread is wider than 3 ticks.
- The required stop width exceeds the selected risk mode.
- The first target is below the selected mode's minimum R.
- Price is chasing an overheated gap without support confirmation.
- Current price is already below VWAP and below the recent intraday low zone.

Return `방어 우선` for a holding-management request when:

- Current price is already below the chosen invalidation line.
- Current price is meaningfully below the user's average price and rebound
  evidence is weak.
- Orderbook liquidity is too thin for a clean stop.

## Stop Rules

Prefer the highest valid stop below the reference price that is backed by
structure:

1. Recent intraday swing low.
2. VWAP failure line, if price is trading above VWAP.
3. Breakout line retest failure, if the setup is breakout.
4. Fixed-percent stop from the risk mode.
5. One extra tick lower when spread or orderbook gaps are elevated.

Do not move a stop farther away only to make the plan look tradable.

## Target Rules

Set first target from the greater of the minimum R target and the nearest clean
resistance zone. If the nearest resistance is below the required R target, mark
the plan as poor risk-reward instead of inventing a higher target.

Use second target around 2R or the next clear intraday resistance. For fast
momentum names, prefer partial profit at first target and trail the remainder.

## Position Sizing

Calculate position size only when the user provides account capital or maximum
loss amount. Never fetch account data.

Formula:

```text
quantity = floor(max_loss_krw / abs(entry_price - stop_price))
```

State that slippage and fees can make realized loss larger than the formula.
