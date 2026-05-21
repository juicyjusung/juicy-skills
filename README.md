# juicy-skills

A personal collection of agent skills for [Claude Code](https://claude.ai/claude-code), installable via [skills.sh](https://skills.sh/docs).

## Skills

| Skill | Description | Install |
|-------|-------------|---------|
| [persuade](#persuade) | Persuasive writing — proposals, emails, Slack, pushbacks | `npx skills add juicyjusung/juicy-skills/persuade` |
| [kr-market](#kr-market) | Live Korean (KOSPI/KOSDAQ) stock data — quotes, orderbook, charts, flow | `npx skills add juicyjusung/juicy-skills/kr-market` |
| [us-market](#us-market) | Live US (NYSE/NASDAQ) stock data — quotes, bars, trades, news, actions | `npx skills add juicyjusung/juicy-skills/us-market` |
| [stock-research](#stock-research) | Objective, cited stock research report for one ticker (KR or US) | `npx skills add juicyjusung/juicy-skills/stock-research` |

## persuade

Turn ideas into persuasive text through conversation. Clarify the claim, build evidence, check logic, produce a polished draft.

```bash
npx skills add juicyjusung/juicy-skills/persuade
```

**Triggers on:** proposing, persuading, convincing, arguing, justifying, making a case, pushing back — or Korean equivalents (제안서, 설득, 주장, 어필, 반박, 어떻게 얘기하면 좋을까).

**How it works:**

- **Fast Track** — clear claim + some evidence → draft immediately, minimal questions
- **Deep Track** — vague direction → iterative questions to establish claim → build evidence → draft

All drafts use a 3-layer sandwich structure: Claim → Evidence + Examples → Counter-argument → Restatement.

**Supports:** any language (auto-detected), any medium (Slack, email, proposal, report), web research via tavily when evidence is thin.

## kr-market

Live KOSPI/KOSDAQ market data — quotes, 10-level orderbook, OHLC bars, ticks, foreign/institutional flow, sector indices, rankings.

```bash
npx skills add juicyjusung/juicy-skills/kr-market
```

**Triggers on:** 6-digit Korean tickers (`005930`, `247540`), Korean company names (삼성전자, 카카오), Korean market terms (현재가, 호가, 일봉, 외국인 순매수, KOSPI/KOSDAQ).

**Backend:** Kiwoom OpenAPI REST (production domain). Provider-agnostic CLI/JSON interface.

**Required env:** `KIWOOM_APP_KEY`, `KIWOOM_SECRET_KEY` — see `skills/kr-market/README.md`.

## us-market

Live US (NYSE/NASDAQ) market data — quotes, OHLC bars, trades, news, corporate actions (dividends/splits), screener (gainers/losers/most-active).

```bash
npx skills add juicyjusung/juicy-skills/us-market
```

**Triggers on:** US tickers (`AAPL`, `TSLA`, `BRK.B`), company names (Tesla, Nvidia), quote/chart/dividend/split queries. Korean phrasing supported (지금 얼마, 현재가, 일봉, 배당).

**Backend:** Alpaca Market Data API. Free tier defaults to 15-min delayed SIP; override with `--feed=iex` or `ALPACA_FEED=iex`.

**Required env:** `APCA_API_KEY_ID`, `APCA_API_SECRET_KEY` — see `skills/us-market/README.md`.

## stock-research

Produces `stocks/{ticker}/research.md` — objective, fact-only research report for one public company (KR or US). Every number cited with source + timestamp. **No buy/sell opinions, no valuation judgments.**

```bash
npx skills add juicyjusung/juicy-skills/stock-research
```

**Triggers on:** "리서치 작성", "기업분석", "stock research", "fundamental analysis", "ticker 분석" with any KR/US ticker.

**Sources:** DART (KR disclosures) + SEC EDGAR (US filings) as 1st-party; FMP, pykrx as cross-check; calls `kr-market` / `us-market` for live quotes.

**Required env (minimum):**
- KR: `OPEN_DART_API_KEY` + `KIWOOM_APP_KEY` + `KIWOOM_SECRET_KEY`
- US: `FMP_API_KEY` + `APCA_API_KEY_ID` + `APCA_API_SECRET_KEY`

Optional: `FRED_API_KEY`, `BOK_ECOS_API_KEY`, `EDGAR_IDENTITY`, `TAVILY_API_KEY` — see `skills/stock-research/README.md`.

## License

MIT
