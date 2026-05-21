# stock-research

Objective, fact-only stock research on a single public company (KOSPI/KOSDAQ or NYSE/NASDAQ). Produces `stocks/{ticker}/research.md` with cited facts, timestamps, and evidence gaps — **no buy/sell opinions, no valuation judgments**.

```bash
npx skills add juicyjusung/juicy-skills/stock-research
```

**Triggers on:** "리서치 작성", "기업분석", "stock research", "fundamental analysis", "ticker 분석" — with any ticker (`005930`, `247540`, `TSLA`, `AAPL`, `BRK.B`).

**Output:** structured markdown report grounded in 1st-party sources (DART for KR, SEC EDGAR for US) cross-checked with 2nd-party (FMP, pykrx).

## Companion skills

This skill calls `kr-market` and `us-market` for live quotes/multiples. Install both if you want full coverage — env vars below cover all three.

## Environment variables

Create `.env` in the project root (`stocks/` parent) or skill directory:

```bash
# === Required for KR research ===
# OpenDART (KR disclosures + financials)
# Get key: https://opendart.fss.or.kr (free, instant)
OPEN_DART_API_KEY=

# Kiwoom (live KR quotes, used via kr-market)
# Get keys: https://openapi.kiwoom.com (production domain)
KIWOOM_APP_KEY=
KIWOOM_SECRET_KEY=

# === Required for US research ===
# Financial Modeling Prep (US fundamentals, 250 free calls/day)
# Get key: https://site.financialmodelingprep.com
FMP_API_KEY=

# Alpaca (live US quotes, used via us-market)
# Get keys: https://alpaca.markets
APCA_API_KEY_ID=
APCA_API_SECRET_KEY=

# === Optional — macro context ===
# FRED (US macro: rates, CPI, etc.)
# Get key: https://fred.stlouisfed.org
FRED_API_KEY=

# BOK ECOS (KR macro: 한국은행 통계)
# Get key: https://ecos.bok.or.kr
BOK_ECOS_API_KEY=

# === Optional — SEC EDGAR identity ===
# Required by SEC's fair-use policy. Default is a placeholder; set to your contact.
EDGAR_IDENTITY="your-name your-email@example.com"

# === Optional — web research fallback ===
# Tavily (used when structured APIs miss data)
TAVILY_API_KEY=
```

### Minimum to run

- KR ticker: `OPEN_DART_API_KEY` + `KIWOOM_APP_KEY` + `KIWOOM_SECRET_KEY`
- US ticker: `FMP_API_KEY` + `APCA_API_KEY_ID` + `APCA_API_SECRET_KEY`

EDGAR works without an API key but expects a contact identity per SEC fair-use policy.

## Runtime

Python via `uv`. Scripts auto-install deps on first run:

```bash
uv run scripts/fetch_dart.py 005930 --section all
uv run scripts/fetch_edgar.py AAPL --section all
uv run scripts/fetch_fmp.py AAPL --section all
uv run scripts/fetch_pykrx.py 005930 --section all
```

## Usage

```
/stock-research 005930          # full KR research
/stock-research AAPL            # full US research
/stock-research AAPL --update   # incremental refresh (financials, events, consensus)
/stock-research AAPL --section=financials
```

Output lands in `stocks/{ticker}/research.md`. Evidence cache in `stocks/{ticker}/_evidence/`.

See `SKILL.md` for the full workflow, objectivity rules, and section spec.
