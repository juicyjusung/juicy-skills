---
name: kr-market
description: >-
  Fetch live Korean (KOSPI/KOSDAQ) stock market data. This is the ONLY way to
  get real-time KR market data — model has no built-in access, so trigger
  this skill (don't guess, don't WebFetch). MUST trigger whenever the user
  asks about a Korean stock or the Korean market — including from inside
  other skills (e.g. stock-research filling 종목 리서치 for a KOSPI/KOSDAQ
  name) or mid-conversation lookups. Trigger signals: (1) 6-digit Korean
  ticker like 005930, 035720, 247540, 005380; (2) Korean company name
  (삼성전자, 현대차, 카카오, 네이버, 셀트리온, 에코프로비엠, SK하이닉스,
  LG에너지솔루션 등); (3) Korean market terms — 현재가, 시세, 호가,
  orderbook, 일봉/분봉/주봉, 차트, 체결, 거래원, 외국인·기관 수급,
  업종지수, KOSPI/KOSDAQ 지수, 거래량/등락률/거래대금 상위, 시총, PER, 등락률;
  (4) Korean-language live-price phrasing — "지금 얼마", "오늘 종가",
  "현재가", "호가창", "일봉 데이터", "외국인 순매수", "코스피 상승률
  상위", "국내 시세". Examples: "005930 지금 얼마야", "삼성전자 거래량",
  "에코프로비엠 일봉 csv", "코스닥 거래대금 상위", "KOSPI 지수
  알려줘", "현대차 호가창", "stocks/247540/research.md 채워줘 — 현재가/시총/PER".
  Do NOT trigger for: US/NYSE/NASDAQ tickers (AAPL, TSLA, NVDA, MSFT, BRK.B —
  use us-market instead), S&P/Dow/Nasdaq indices, Japan/HK/EU/China markets
  (도요타, 닛케이, 항셍, 상해), crypto (비트코인, 이더리움, 업비트), order
  placement (매수/매도/주문), account balance/holdings (잔고/보유종목/평가금액),
  mock trading (모의투자). Provider-agnostic interface — currently Kiwoom
  REST (.env: KIWOOM_APP_KEY/KIWOOM_SECRET_KEY), provider may swap. Production
  domain only.
---

# KR Market Skill

목적: 국내 종목(KOSPI/KOSDAQ, 6자리) 시세·호가·차트·수급·순위 조회. TypeScript CLI 묶음. 운영 도메인 전용.

현재 backend: **Kiwoom OpenAPI REST**. 추후 다른 증권사 API 교체 가능. 교체 시 `scripts/_client.ts`(HTTP/인증) + `references/tr-codes.md`(TR 매핑) + 각 스크립트의 필드 매핑만 갈아끼움. 외부 인터페이스(CLI args, 출력 JSON 스키마)는 provider-agnostic 유지.

## 트리거

- 6자리 한국 티커 + 시세/현재가/호가/차트/일봉/분봉/종목정보 등 키워드
- "키움 API", "Kiwoom" 명시 호출
- 사용자가 종목코드만 던지며 "지금 얼마", "지금 가격", "오늘 종가" 등 물을 때

비대상: 주문(매수/매도), 계좌 잔고, 모의투자, 해외 종목 → 이 스킬에서 처리 금지.

## 사전 조건

`.env` 에 다음 키 존재 (운영 발급):
```
KIWOOM_APP_KEY=...
KIWOOM_SECRET_KEY=...
```

런타임: `bun` (Node 호환). 외부 패키지 불필요 — 내장 `fetch` + `dotenv` 형식의 `.env` 직접 파싱.

## 베이스 URL

- REST: `https://api.kiwoom.com`
- 토큰 캐시: `stocks/.kiwoom-token.json` (gitignore 대상, 0600 권한)

## 워크플로우

```
0. SKILL_DIR=.claude/skills/kr-market
1. 사용자 의도 분류:
   - 현재가/종목정보      → scripts/quote.ts <티커>
   - 호가                 → scripts/orderbook.ts <티커>
   - 일/주/월/분봉 차트   → scripts/chart.ts <티커> [--interval=day|week|month|min] [--count=N] [--min-unit=1|3|5|10|15|30|60]
   - 시간별 체결          → scripts/ticks.ts <티커> [--count=N]
   - 거래원/외국인/기관   → scripts/flow.ts <티커> --type=trader|foreign|inst [--count=N]
   - 업종지수             → scripts/sector.ts [--inds-cd=001|101|...] [--count=N]
   - 순위 스크리너        → scripts/rank.ts --by=volume|change|value [--market=000|001|101] [--count=N]
2. bun $SKILL_DIR/scripts/<script>.ts <args>
3. 출력은 JSON. 사용자에게는 핵심만 요약 (가격, 등락, 거래량 등).
4. 연속조회 필요 시 응답 cont-yn=Y + next-key 를 다음 호출에 전달.
```

## 출력 규약

- 모든 스크립트 stdout 은 단일 JSON 객체
- 에러는 stderr + exit code 1
- 가격 단위: 원(KRW). 부호 포함 문자열은 숫자로 변환 후 표시
- 시각: ISO8601 (Asia/Seoul)

## TR 참조

상세 TR 코드·필드는 `references/tr-codes.md` 참조. 새 TR 추가 시 그 파일에 먼저 등록하고 스크립트 작성.

## 토큰 관리

- `scripts/_client.ts` 의 `getToken()` 이 디스크 캐시 확인 → 만료 5분 전 자동 재발급
- 재발급 실패 시 stderr 에 `return_msg` 출력 후 exit 1
- 강제 갱신: `bun scripts/token.ts --refresh`

## 호출 규칙 (실수 방지)

1. 모든 REST 호출은 **POST**, `Content-Type: application/json;charset=UTF-8`
2. 헤더 필수: `authorization: Bearer <token>`, `api-id: <TR>`
3. 종목코드는 6자리 그대로 전송 (예: "005930"). 일부 TR 은 `KRX:005930` 접두사 필요 — `references/tr-codes.md` 의 필드 표 참조
4. 응답 숫자가 문자열·부호·0패딩으로 올 수 있음. 파싱 시 `parseFloat(x.replace(/^[+\- ]+/,''))` 형태 사용

## 안전장치

- 주문/계좌/체결/신용 관련 엔드포인트(`/api/dostk/ordr`, `/api/dostk/acnt`, `/api/dostk/crdordr` 등)는 이 스킬에서 호출 금지. 사용자가 요청해도 거절하고 별도 스킬 필요함을 알릴 것.
- 토큰 파일 권한 0600 유지. 로그·README 등에 키/토큰 노출 금지.

## Evidence Gap

- Rate limit, refresh token TTL, 동시조회 한도 문서화 안 됨. 429/실패 시 지수 백오프 (1s → 2s → 4s, 최대 3회).
- 일부 TR endpoint path 가 공식 가이드와 커뮤니티 문서간 표기 차이 있음. 의심 시 공식 가이드 https://openapi.kiwoom.com/m/guide/apiguide 확인.
