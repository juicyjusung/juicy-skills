# Alpaca Endpoint Catalog

Base: `https://data.alpaca.markets`. All GET. Headers: `APCA-API-KEY-ID`, `APCA-API-SECRET-KEY`, `accept: application/json`.

`feed` query param applies to v2 stocks endpoints. Values: `iex` | `sip` | `delayed_sip`.

## v2 — Stock Market Data

| Purpose | Method | Path | Key Query Params | Used By |
|---|---|---|---|---|
| Latest quote | GET | `/v2/stocks/{symbol}/quotes/latest` | `feed` | `quote.ts --type=quote` |
| Latest trade | GET | `/v2/stocks/{symbol}/trades/latest` | `feed` | `quote.ts --type=trade` |
| Snapshot | GET | `/v2/stocks/{symbol}/snapshot` | `feed` | `quote.ts --type=snapshot` |
| Bars | GET | `/v2/stocks/{symbol}/bars` | `timeframe`, `start`, `end`, `limit`, `adjustment`, `feed`, `page_token` | `bars.ts` |
| Trades | GET | `/v2/stocks/{symbol}/trades` | `start`, `end`, `limit`, `feed`, `page_token` | `trades.ts` |

`timeframe` values accepted: `1Min`, `5Min`, `15Min`, `30Min`, `1Hour`, `1Day`, `1Week`, `1Month`.

### Free-plan quirks for bars / trades

These were discovered during smoke testing — keep in mind when modifying the endpoint code:

1. **`feed=delayed_sip` is rejected on `/v2/stocks/*/bars` and `/v2/stocks/*/trades`.** Snapshot/latest endpoints accept it, historical do not. `_client.ts#feedForHistorical()` rewrites `delayed_sip` → `sip` for these calls. Alpaca then auto-delays the response 15 minutes when the account lacks real-time SIP entitlement.
2. **Free SIP forbids querying recent data.** Any query whose window touches the last 15 minutes returns `403 "subscription does not permit querying recent SIP data"`. `_client.ts#defaultEnd()` clamps `end` to `now - 16min` when the caller did not specify one and the feed is `delayed_sip`.
3. **No `start` → empty `bars` array.** Without an explicit `start`, Alpaca returns nothing rather than the most recent N bars. `_client.ts#defaultStart()` defaults to 7 days back for intraday intervals and 90 days back for daily / weekly / monthly.
4. **`sort=desc` is required to get newest-first bars.** Alpaca's default is ascending. We always pass `sort=desc` so `--count=N` returns the *last* N bars.

### Snapshot response shape

```jsonc
{
  "symbol": "AAPL",
  "latestQuote": { "bp": 184.21, "bs": 3, "ap": 184.23, "as": 5, "t": "...", "x": "V", "c": ["R"], "z": "C" },
  "latestTrade": { "p": 184.22, "s": 100, "t": "...", "x": "V", "c": ["@"], "z": "C", "i": 12345 },
  "minuteBar":   { "o":..., "h":..., "l":..., "c":..., "v":..., "t":"...", "n":..., "vw":... },
  "dailyBar":    { ... },
  "prevDailyBar":{ ... }
}
```

### Bar fields

- `t` — bar start ISO timestamp
- `o`/`h`/`l`/`c` — OHLC
- `v` — volume
- `n` — trade count
- `vw` — VWAP

### Trade fields

- `t` — ISO timestamp
- `p` — price
- `s` — size
- `x` — exchange code (single char)
- `i` — trade ID
- `c` — conditions (array of single-char codes)
- `z` — tape (A/B/C)

## v1beta1 — Screener

`feed` NOT accepted here.

| Purpose | Method | Path | Key Query Params | Used By |
|---|---|---|---|---|
| Most actives | GET | `/v1beta1/screener/stocks/most-actives` | `top` | `screener.ts --by=most-actives` |
| Movers (gainers + losers) | GET | `/v1beta1/screener/stocks/movers` | `top` | `screener.ts --by=gainers|losers` |

Response shape (movers):

```jsonc
{
  "gainers": [ { "symbol": "...", "percent_change": 12.3, "change": 2.1, "price": 19.5 } ],
  "losers":  [ ... ],
  "market_type": "stocks",
  "last_updated": "2026-05-21T..."
}
```

Response shape (most-actives):

```jsonc
{
  "most_actives": [ { "symbol": "...", "volume": 123, "trade_count": 456 } ],
  "last_updated": "..."
}
```

Note: `price` / `change` may be missing for `most-actives` items — we surface as `null`.

## v1beta1 — News

| Purpose | Method | Path | Key Query Params | Used By |
|---|---|---|---|---|
| News feed | GET | `/v1beta1/news` | `symbols`, `start`, `end`, `limit`, `sort`, `page_token` | `news.ts` |

Response shape:

```jsonc
{
  "news": [
    { "id": 12345, "headline": "...", "summary": "...", "url": "...",
      "symbols": ["AAPL"], "source": "...", "author": "...",
      "created_at": "2026-05-21T...", "updated_at": "2026-05-21T..." }
  ],
  "next_page_token": null
}
```

Notes:
- `limit` max 50 per page; we page until `--count` is satisfied.
- `sort=desc` returns newest first.

## v1 — Corporate Actions

| Purpose | Method | Path | Key Query Params | Used By |
|---|---|---|---|---|
| Splits / dividends | GET | `/v1/corporate-actions` | `symbols`, `types`, `start`, `end` | `actions.ts` |

`types` is a comma-separated list. Accepted values include:
- `forward_split`, `reverse_split`
- `cash_dividend`, `stock_dividend`
- (others Alpaca documents — `name_change`, `worthless_removal`, etc. — not surfaced by default)

Response shape:

```jsonc
{
  "corporate_actions": {
    "forward_splits":  [ { "symbol": "AAPL", "ex_date": "...", "new_rate": 4, "old_rate": 1, "payable_date": "..." } ],
    "reverse_splits":  [ ... ],
    "cash_dividends":  [ { "symbol": "AAPL", "ex_date": "...", "rate": 0.24, "record_date": "...", "payable_date": "..." } ],
    "stock_dividends": [ ... ]
  },
  "next_page_token": null
}
```

Normalization rules used by `actions.ts`:
- `splits` array merges forward + reverse, each item carries a `type` field.
- `dividends` array merges cash + stock, `type` field discriminates.
- Split ratio formatted as `"new:old"` (e.g. `"4:1"` for a 4-for-1 forward split).

## Endpoints intentionally NOT used

- `/v2/orders`, `/v2/account`, `/v2/positions`, `/v2/portfolio` — trading host. Out of scope. Refuse.
- `/v2/stocks/quotes` (multi-symbol historical quotes) — not yet needed; add to a new script if requested.
- WebSocket streaming (`wss://stream.data.alpaca.markets/...`) — REST-only skill.
- `/v1beta3/crypto/*`, `/v1beta1/options/*` — out of scope.

## Provider Swap Checklist

When swapping providers:
1. Replace HTTP/auth in `_client.ts` (base URL, headers, retry policy).
2. Update method bodies in `_client.ts` to call new endpoints.
3. Update field mappings in each `scripts/*.ts` (the only Alpaca-specific code outside `_client.ts` is the inline mapping from Alpaca's snake_case / abbreviated keys to our normalized output).
4. Update this file.
5. CLI args and stdout JSON schema **must not change** — that's the consumer contract.
