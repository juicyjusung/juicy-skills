# us-market

Live US (NYSE/NASDAQ) stock market data — quotes, OHLC bars, trades, news, corporate actions, screener.

```bash
npx skills add juicyjusung/juicy-skills/us-market
```

**Triggers on:** US tickers (`AAPL`, `TSLA`, `BRK.B`), company names (Tesla, Nvidia, 엔비디아), quote/chart/dividend/split/news queries. Korean phrasing fully supported (지금 얼마, 현재가, 일봉, 배당).

**Does NOT cover:** Korean 6-digit tickers (→ `kr-market`), order placement, account/positions, options, crypto.

## Backend

**Alpaca Market Data API** (v2 / v1beta1 / v1). Data domain only (`data.alpaca.markets`). Provider-agnostic CLI/JSON interface.

## Environment variables

Create `.env` in the skill directory or project root:

```bash
# Required — Alpaca API credentials
APCA_API_KEY_ID=your_key_id
APCA_API_SECRET_KEY=your_secret

# Optional — market data feed. Default: delayed_sip
# iex          : free real-time IEX-only
# sip          : paid full SIP
# delayed_sip  : free 15-min delayed full SIP
ALPACA_FEED=delayed_sip
```

### How to get keys

1. Sign up at https://alpaca.markets (free)
2. Create paper or live account
3. Generate API keys at https://app.alpaca.markets/paper/dashboard/overview (or live)
4. Paste into `.env`

> Free tier defaults to `delayed_sip`. Override with `--feed=iex` per call or set `ALPACA_FEED=iex`.

## Runtime

- TypeScript via `bun`
- First run: `cd ~/.claude/skills/us-market && bun install`

## CLI surface

```bash
bun scripts/quote.ts AAPL                # latest quote + snapshot
bun scripts/bars.ts AAPL --tf=1Day       # OHLC bars
bun scripts/trades.ts AAPL               # recent trades
bun scripts/news.ts AAPL                 # headlines
bun scripts/actions.ts AAPL              # dividends, splits
bun scripts/screener.ts --type=gainers   # market movers
```

See `SKILL.md` for full argument reference and feed override rules.
