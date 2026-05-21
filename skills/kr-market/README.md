# kr-market

Live Korean (KOSPI/KOSDAQ) stock market data — quotes, orderbook, charts, ticks, sector indices, flow (foreign/institutional), rankings.

```bash
npx skills add juicyjusung/juicy-skills/kr-market
```

**Triggers on:** 6-digit Korean tickers (`005930`, `247540`), Korean company names (삼성전자, 카카오, 네이버), Korean market terms (현재가, 호가, 일봉, 외국인 순매수, KOSPI/KOSDAQ).

**Does NOT cover:** US tickers (→ `us-market`), order placement, account balance, crypto, mock trading.

## Backend

Currently **Kiwoom OpenAPI REST**. Provider-agnostic CLI/JSON interface — provider can swap by replacing `scripts/_client.ts` + `references/tr-codes.md`.

## Environment variables

Create `.env` in the skill directory or project root:

```bash
# Required — Kiwoom OpenAPI REST credentials
KIWOOM_APP_KEY=your_app_key
KIWOOM_SECRET_KEY=your_secret_key
```

### How to get keys

1. Sign up at https://openapi.kiwoom.com
2. Apply for REST API access (운영 / production domain)
3. Issue App Key + Secret Key from the developer console
4. Paste into `.env`

> Production domain only — mock trading (`mockapi`) is not supported.

## Runtime

- TypeScript via `bun` (`package.json` ships with deps)
- First run: `cd ~/.claude/skills/kr-market && bun install`

## CLI surface

```bash
bun scripts/quote.ts 005930              # current price
bun scripts/orderbook.ts 005930          # 10-level bid/ask
bun scripts/chart.ts 005930 --tf=D       # daily candles
bun scripts/ticks.ts 005930              # recent trades
bun scripts/flow.ts 005930               # foreign/institutional net buy
bun scripts/rank.ts --type=volume        # market-wide rankings
bun scripts/sector.ts                    # sector indices
```

See `SKILL.md` for full argument reference.
