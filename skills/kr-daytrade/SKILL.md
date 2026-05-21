---
name: kr-daytrade
description: >-
  Build conditional Korean stock day-trading risk plans using live KOSPI/KOSDAQ
  data from the kr-market skill. Use when the user gives a Korean 6-digit ticker
  or Korean stock name and asks for 단타 계획, 손절가, 익절가, 분할익절, 평단가
  관리, 눌림목, 돌파, VWAP, 호가, 체결강도, 스캘핑, or whether a Korean stock
  is suitable for an intraday trade. Supports holding-management mode when an
  average price is provided and new-entry evaluation mode when it is not. Do not
  use for order execution, account or balance lookup, automated trading, US
  stocks, options, futures, crypto, long-term research, or definitive buy or sell
  recommendations.
---

# KR Daytrade

Create a conditional day-trading plan for Korean stocks. Treat the output as a
risk plan, not an instruction to trade.

## Workflow

1. Identify the stock. Prefer a 6-digit Korean ticker. If the user provides only
   a name and the ticker is not obvious, ask for the 6-digit code.
2. Classify the mode:
   - Use holding-management mode when the user provides `avg_price` or says they
     already hold the stock.
   - Use new-entry evaluation mode when no average price is provided.
3. Default missing options:
   - `risk_mode`: `balanced`
   - `trade_style`: `auto`
   - `timeframe`: 1-minute bars, then 3-minute bars if 1-minute data is noisy.
4. Trigger `kr-market` and collect required live data:
   - `quote.ts` for current price, change, volume, high, low, open, prior close.
   - `chart.ts --interval=min --count=80 --min-unit=1` for intraday bars.
   - `orderbook.ts` for 10-level bid/ask prices and quantities.
   - `ticks.ts --count=30` for recent execution data and strength.
5. Run `scripts/score.ts` with the collected JSON files when available. Use the
   JSON output as a first pass, then apply judgment from the references.
6. Apply the decision order: hard gates, weighted setup assessment, then price
   plan. Do not force stop or target prices when the required data or risk
   structure is poor.
7. Reply in Korean using `references/output-format.md`. Include the data time,
   risk mode, conclusion, price plan, setup judgment, invalidation conditions,
   warnings, and evidence strength.

## Data Collection

Use the existing `kr-market` skill for all live Korean market data. Do not guess
real-time prices from model memory or web snippets.

Example local flow after collecting each JSON response:

```bash
bun skills/kr-daytrade/scripts/score.ts \
  --ticker 005930 \
  --avg-price 72300 \
  --risk balanced \
  --quote quote.json \
  --bars bars.json \
  --orderbook orderbook.json \
  --ticks ticks.json
```

If optional flow, sector, or rank data is available, use it only as supporting
evidence. Never make it a prerequisite for stop or target calculation.

## Decision Rules

Read `references/risk-policy.md` for risk modes, hard gates, and position-risk
handling. Hard gates override weighted scores.

Read `references/rulebook.md` when judging VWAP support, pullback, breakout,
gap, scalping, orderbook risk, or weak evidence. Treat low-confidence rules as
context only.

Read `references/tick-size.md` or use `scripts/tick-size.ts` for Korean stock
tick-size rounding. Round stops down, targets up, and neutral reference prices
to the nearest tick.

## Price Planning

For holding-management mode, show:

- Current price versus average price.
- Chart invalidation stop, fixed-percent stop candidate, VWAP or recent-low
  stop, and the chosen stop.
- First and second profit-taking levels.
- Split-taking plan and defensive warning if the current price is already below
  the invalidation line.

For new-entry evaluation mode, show:

- Whether the setup is tradable now, conditional, or on hold.
- Candidate entry area, invalidation line, stop, first target, second target,
  and R multiples.
- A clear hold conclusion when the first target does not meet the selected risk
  mode's minimum R.

## Safety

Never call order, account, balance, position, credit, or automated-trading APIs.
Never present the plan as guaranteed or as a definitive instruction to buy or
sell. Use conditional phrasing such as `이탈 시`, `회복 실패 시`, `손익비가
유지될 때`, and `데이터 기준`.

If data is stale, missing, or inconsistent, stop and say which data is missing.
If the user asks for account-based position sizing, calculate it only from
numbers the user directly provides.

## Resources

- `references/output-format.md`: Korean response template.
- `references/risk-policy.md`: risk modes, hard gates, and warnings.
- `references/rulebook.md`: setup and warning rules.
- `references/tick-size.md`: KRX tick-size table and rounding policy.
- `scripts/score.ts`: deterministic first-pass scoring and price candidates.
- `scripts/tick-size.ts`: tick-size calculation and rounding helper.
