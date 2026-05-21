# 미국 종목 워크플로우

티커: 알파벳 (예: `TSLA`, `AAPL`, `NVDA`, `BRK.B`)

## 0. 사전 체크

```bash
# EDGAR 무인증 ping
uv run --with edgartools python3 -c "from edgar import Company; print(Company('AAPL').name)"

# FMP key 확인 (있으면)
uv run --env-file .env python3 -c "import os; assert os.environ.get('FMP_API_KEY'); print('ok')"
```

모든 fetch script 는 `SKILL_DIR=.claude/skills/stock-research` 지정 후 `uv run --env-file .env $SKILL_DIR/scripts/fetch_*.py ...` 형식. PEP 723 inline deps 자동 설치.

## 1. 회사 식별 (Identity)

```bash
uv run --env-file .env $SKILL_DIR/scripts/fetch_edgar.py AAPL --section identity --out _evidence/edgar_identity.json
```
출력: 회사명, CIK, exchange, GICS sector/sub-industry, fiscal_year_end, 시총

## 2. 사업 (Business)

### 2.1 SEC 10-K (Form 10-K, Item 1 Business)
```bash
uv run --env-file .env $SKILL_DIR/scripts/fetch_edgar.py AAPL --section business --out _evidence/edgar_business.json
```
- Operating segments (Note 14 or Segment Reporting)
- 지역별 매출 (Geographic Information)
- 주요 고객 (10% 이상 매출 차지 고객 공시 의무)
- 자회사 (Exhibit 21)

### 2.2 보완: 회사 IR 페이지, earnings deck
Tavily 로 회사 IR/earnings deck URL 을 먼저 찾고, HTML 은 `tavily-extract` 로 추출. PDF 파싱이 필요하거나 Tavily 추출이 막히면 firecrawl-parse fallback.

## 3. Operating KPI

`references/industry_kpi.md` 매트릭스 참조. 미국은 segment 정보 풍부 → IR 발표자료에 잘 정리됨.

## 4. 재무 (3~5년)

### 4.1 EDGAR XBRL 재무제표
```bash
uv run --env-file .env $SKILL_DIR/scripts/fetch_edgar.py AAPL --section financials --years 5 --out _evidence/edgar_fin.json
```
edgartools 가 표준화된 income/balance/cashflow 제공.

### 4.2 보완·cross-check: FMP
```bash
uv run --env-file .env $SKILL_DIR/scripts/fetch_fmp.py AAPL --section ratios --out _evidence/fmp_ratios.json
uv run --env-file .env $SKILL_DIR/scripts/fetch_fmp.py AAPL --section financials --out _evidence/fmp_financials.json
```
FMP 가 미리 계산해주는 비율:
- ROE, ROA, ROIC, ROCE
- 부채비율, current ratio, quick ratio, interest coverage
- DSO, DIO, DPO, CCC
- FCF, FCF margin

불일치 시 EDGAR (1차) 우선.

### 4.3 canonical 재무 파일
```bash
python3 $SKILL_DIR/scripts/normalize_financials.py _evidence --ticker AAPL --out _evidence/canonical_financials.json
python3 $SKILL_DIR/scripts/evidence_manifest.py _evidence --ticker AAPL --out _evidence/manifest.json
python3 $SKILL_DIR/scripts/evidence_brief.py _evidence --ticker AAPL --out _evidence/evidence_brief.md
```
research.md 재무 표는 이 파일의 `metrics` 를 우선 참고하고, 각 값의 `source_file/source` 를 인용에 연결.
작성 단계에서는 `evidence_brief.md` 를 먼저 읽고, 100KB 초과 raw 파일은 전체 로드하지 않는다.

## 5. 시장·밸류에이션 현황

```bash
uv run --env-file .env $SKILL_DIR/scripts/fetch_fmp.py AAPL --section valuation --out _evidence/fmp_val.json
```
- 현재가, 52주 고저, 시총
- PER (trailing/forward), PBR, PSR, PEG
- EV, EV/EBITDA, EV/Sales

### Peer 비교
- 동일 GICS sub-industry (8자리) + 시총 ±50%
- FMP: `uv run --env-file .env $SKILL_DIR/scripts/fetch_fmp.py AAPL --section peers --out _evidence/fmp_peers.json` 로 peer 후보 자동 추출 (`/stable/stock-peers`)
- 선택한 peer valuation 은 한 프로세스에서 묶음 fetch:
```bash
uv run --env-file .env $SKILL_DIR/scripts/fetch_fmp.py AAPL --section peer-valuations --symbols MSFT,GOOGL,META --out _evidence/fmp_peer_valuations.json
```
- 최대 5개, 선정 기준 명시

## 6. 산업·경쟁

- 시장 규모: Statista, IDC, Gartner, McKinsey, IBISWorld
- 점유율: 회사 10-K + 시장조사기관
- Tavily search: `"market size" "{industry}" 2025 USD`
- 특정 시장조사·협회·회사 IR URL 이 잡히면 `tavily-extract` 로 필요한 본문만 추출

## 7. 매크로 노출

- 수출/달러 비중: 10-K Geographic
- 금리 민감도: 부채구조 (Note Long-term Debt + Hedging disclosures)
- 원자재: 10-K Risk Factors + Note Commodity
- FRED API:
```bash
# 10Y Treasury (DGS10), DXY, WTI (DCOILWTICO), Copper (PCOPPUSDM)
uv run --env-file .env --with requests python3 -c "import os, requests; k=os.environ['FRED_API_KEY']; r=requests.get('https://api.stlouisfed.org/fred/series/observations', params={'series_id':'DGS10','api_key':k,'file_type':'json','sort_order':'desc','limit':5}).json(); print(r['observations'][:3])"
```

## 8. 최근 이벤트 (6~12개월)

### 8.1 SEC 8-K (수시공시)
```bash
uv run --env-file .env $SKILL_DIR/scripts/fetch_edgar.py AAPL --section disclosures --days 365 --out _evidence/edgar_8k.json
```
8-K Item 별로 분류:
- Item 2.02 Earnings
- Item 1.01/2.01 M&A
- Item 5.02 Executive changes
- Item 8.01 Other (자사주, 배당 등)

### 8.2 DEF-14A (위임장) — 경영진 보수, 이사회
### 8.3 Form 13D/13G — 5% 이상 주주 변동
### 8.4 Form 4 — 내부자 거래

### 8.5 어닝콜 트랜스크립트
- Seeking Alpha (스크래핑 또는 비공식 API)
- API Ninjas Earnings Call Transcript (무료 한도)
- Benzinga (유료, 있는 경우)

### 8.6 뉴스
- tavily-search `Tesla earnings OR product OR lawsuit site:reuters.com OR site:bloomberg.com` 6개월
- 필요한 Reuters/Bloomberg/회사 IR press releases URL 만 `tavily-extract`
- Tavily 가 동적 페이지·PDF 에서 실패할 때만 firecrawl fallback

## 9. 컨센서스·가이던스

- FMP: `uv run --env-file .env $SKILL_DIR/scripts/fetch_fmp.py AAPL --section estimates --out _evidence/fmp_est.json` — `/stable/analyst-estimates` + `/stable/earnings-surprises` 통합
- 회사 가이던스: earnings call transcript 의 forward-looking
- 출처: FMP, Refinitiv (있으면), Finnhub fallback

## 10. 지배구조

DEF-14A 에서:
- 임원·이사 보수 (Summary Compensation Table)
- 스톡옵션·RSU grants
- 이사회 구성, 사외이사 비율, 위원회
- Say-on-Pay 결과

Form 13D/13G 에서:
- 5% 이상 주주
- Institutional ownership (13F 집계, Whalewisdom 등)

## 11. 자본배분 트랙레코드

10-K 5년 시계열:
- CAPEX / Revenue %
- R&D / Revenue %
- M&A 이력 (Cash flow from investing — Acquisitions, net)
- Dividends paid (CF financing)
- Treasury stock purchases (CF financing)
- Cash & marketable securities 잔액 추이

ROIC 5년 추이.

## 12. 갱신

- 분기 10-Q 발표 후: `--update --section=재무,KPI,이벤트,컨센서스`
- 연차 10-K 발표 후: 전체 재작성
- 60일 경과: 시장·밸류에이션만

## 13. MCP 우선 경로 (설치된 경우)

Yahoo Finance MCP 설치되어 있으면 단순 조회 MCP 직접:
- `mcp__yahoo_finance__get_financials`
- `mcp__yahoo_finance__get_quote`
- `mcp__yahoo_finance__get_news`

Alpha Vantage MCP 있으면 기술지표·환율 추가 활용. 복잡한 SEC 파싱은 edgartools.

## 14. ADR·non-US 주의

- ADR (예: BABA): 미국 거래소 상장이지만 본사 외국. 회계는 본국 기준 (BABA = IFRS).
- 통화 단위 확인 (USD 표시이지만 본사 보고는 다른 통화일 수 있음).
- 추가 1차 자료: 본국 거래소 공시 (예: BABA → HKEX).
