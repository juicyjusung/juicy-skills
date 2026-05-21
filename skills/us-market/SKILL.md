---
name: us-market
description: >-
  Use this skill for any US stock market data lookup — NYSE/NASDAQ tickers like
  AAPL, TSLA, MSFT, NVDA, SPY, AMD, INTC, BRK.B, or company names (Tesla, Nvidia,
  엔비디아, 애플). Triggers whenever a user wants live or historical info about a
  US-listed stock: current price, quote, snapshot, bid/ask, last trade, previous
  close, OHLC bars, daily/weekly/monthly/intraday candles, charts, trend, volume,
  ticks, trades, dividends, dividend history, ex-date, splits, corporate actions,
  news headlines, market movers, gainers/losers, most-active. Comparing two US
  tickers' performance counts. Korean phrasing fully supported ("지금 얼마",
  "현재가", "일봉", "배당", "거래량", "어제 종가"). Mixed-language and conversational
  requests count — if the user is researching, eyeballing, citing, or asking about
  a US-listed equity, use this skill. Do NOT use for: order placement,
  account/positions, options, crypto, Korean 6-digit tickers (route to kr-market),
  pure technical-analysis math with no data fetch, or conceptual explanations that
  don't need real quotes.
---

# US Market Skill

목적: 미국 주식 (NYSE/NASDAQ) 시세·차트·체결·순위·뉴스·기업액션 조회. TypeScript CLI 묶음. 데이터 도메인 전용 (`data.alpaca.markets`).

현재 backend: **Alpaca Market Data API v2 / v1beta1 / v1**. provider 교체 시 `scripts/_client.ts` (HTTP/인증/feed) + `references/endpoints.md` (endpoint 매핑) + 각 스크립트 필드 매핑만 교체. 외부 인터페이스 (CLI args, 출력 JSON 스키마) 는 provider-agnostic 유지.

## 트리거

- US 티커 (1-5자 영문 또는 BRK.B 형식) + 시세/현재가/스냅샷/차트/봉/체결/뉴스/배당/분할 키워드
- "Alpaca" 명시 호출
- 사용자가 영문 티커만 던지며 "지금 얼마", "현재가", "오늘 종가" 등 물을 때
- 미국 시장 전체 순위 ("미국 가장 활발한 종목", "오늘 상승률 1위 (미국)")

비대상:
- 주문 (매수/매도), 계좌, 포지션 → 이 스킬에서 거절
- 크립토, 옵션 → 이 스킬에서 거절
- 6자리 한국 티커 (예: 005930) → `kr-market` 스킬로 라우팅

## 사전 조건

`.env` (스킬 디렉토리 또는 프로젝트 루트):
```
APCA_API_KEY_ID=...
APCA_API_SECRET_KEY=...
ALPACA_FEED=delayed_sip   # 선택. iex|sip|delayed_sip. 기본 delayed_sip
```

런타임: `bun`. 외부 패키지 불필요 — 내장 `fetch` + `.env` 직접 파싱.

## 베이스 URL

- Data: `https://data.alpaca.markets`
- **trading host 사용 안 함**. `/v2/orders`, `/v2/account`, `/v2/positions` 등은 본 스킬 범위 외.

## 워크플로우

```
0. SKILL_DIR=.agents/skills/alpaca-market
1. 사용자 의도 분류:
   - 스냅샷/현재가/quote/trade  → scripts/quote.ts <SYMBOL> [--type=snapshot|quote|trade]
   - 차트/OHLC/봉              → scripts/bars.ts <SYMBOL> [--interval=1Min|5Min|15Min|30Min|1Hour|1Day|1Week|1Month] [--count=N]
   - 체결/tick                  → scripts/trades.ts <SYMBOL> [--count=N]
   - 순위/movers                → scripts/screener.ts --by=most-actives|gainers|losers [--top=10]
   - 뉴스                       → scripts/news.ts [--symbols=AAPL,TSLA] [--count=N]
   - 분할/배당/corp action      → scripts/actions.ts <SYMBOL> [--types=split,dividend]
2. bun $SKILL_DIR/scripts/<script>.ts <args>
3. 출력은 단일 JSON. 사용자에게는 핵심 요약 (price, change_pct, volume 등) + delayed=true 인 경우 "15분 지연 데이터" 명시.
4. 페이지네이션 필요 시 응답 next_page_token 을 다음 호출 `--page-token=...` 으로 전달.
```

## 출력 규약

- 모든 스크립트 stdout 은 단일 JSON 객체
- 에러는 stderr + exit code 1
- 가격 단위: USD. SDK/API 가 string 으로 줄 수도 있으므로 `num()` 으로 일괄 변환
- 시각: ISO8601 (`America/New_York` offset 포함)
- 누락 필드는 명시적 `null`. 키 자체는 유지 → consumer 안정성

## Feed 선택

우선순위: CLI `--feed` > env `ALPACA_FEED` > default `delayed_sip`.

- `delayed_sip` (default): SIP 통합, 15분 지연. **무료 플랜 권장값**. IEX 보다 거래량·NBBO 정확.
- `iex`: IEX 단일 거래소 데이터. 무료. 실시간이지만 거래량 일부만 잡힘.
- `sip`: SIP 실시간 통합. **Algo Trader Plus 이상 유료 플랜 필요**. 미가입시 Alpaca 가 403 반환.

## 안전장치

- 거래(trading) endpoint (`/v2/orders`, `/v2/account`, `/v2/positions`, `/v2/portfolio` 등) 호출 금지. `_client.ts` 는 data host 만 사용.
- 사용자가 매수/매도 요청 시 거절하고 별도 트레이딩 스킬 필요함을 안내.
- 6자리 한국 티커 입력 시 `validateSymbol()` 이 거절하고 kr-market 으로 라우팅 힌트.
- 키 로깅 금지. stderr 에도 secret 출력 안 함.
- `.env` 파일 권한 0600 권장 (사용자 책임 — `.env` 가 프로젝트 루트일 수도 있어 자동 chmod 안 함).

## Endpoint 참조

상세 endpoint·필드 매핑은 `references/endpoints.md` 참조. 새 endpoint 추가 시 그 파일에 먼저 등록 후 스크립트 작성.

## Evidence Gap

- `delayed_sip` feed 파라미터 일부 endpoint 미지원 가능성. raw fetch + `feed=delayed_sip` 직접 전달 시 정상 응답 확인됨 (v2/stocks/*/snapshot, /bars, /trades).
- Free tier rate limit: 200 req/min (문서값). 429 / 5xx 시 1s→2s→4s 지수 백오프, 최대 3회 재시도.
- `/v1beta1/screener/stocks/movers` 가 `gainers`·`losers` 한 호출에 같이 줌. 스크립트에서 `--by` 따라 분기.
- Corporate actions endpoint path 는 `/v1/corporate-actions`. Alpaca 가 과거 `/v2/corporate-actions` 표기한 적 있어 변경 가능성 주시.
