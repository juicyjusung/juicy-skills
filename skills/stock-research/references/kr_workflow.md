# 한국 종목 워크플로우

티커: 6자리 숫자 (예: `005930` 삼성전자, `035720` 카카오, `247540` 에코프로비엠)

## 0. 사전 체크

```bash
# DART key 확인 (.env 자동 로드)
uv run --env-file .env python3 -c "import os; assert os.environ.get('OPEN_DART_API_KEY'), 'DART key missing'; print('ok')"
```

key 없으면 사용자에게 안내 + Tavily 우선 검색/추출로 진행 (제한적). firecrawl/WebSearch 는 fallback.

모든 fetch script 는 `SKILL_DIR=.claude/skills/stock-research` 지정 후 `uv run --env-file .env $SKILL_DIR/scripts/fetch_*.py ...` 형식으로 호출. PEP 723 inline deps 가 첫 실행 시 자동 설치됨.

## 1. 회사 식별 (Identity)

### 1.1 DART corp 검색 → 회사 기본 정보
```bash
uv run --env-file .env $SKILL_DIR/scripts/fetch_dart.py 005930 --section identity --out _evidence/dart_identity.json
```
출력: 회사명·CIK·corp_code·결산월·업종코드(KSIC)·시총

### 1.2 KRX 시장 정보
```bash
uv run --env-file .env $SKILL_DIR/scripts/fetch_pykrx.py 005930 --section market --out _evidence/krx_market.json
```
출력: 시장(KOSPI/KOSDAQ), 시총, 유통주식수, 외국인 보유율

## 2. 사업 (Business)

### 2.1 DART 사업보고서 (Form 11014, 가장 최근 연차)
```bash
uv run --env-file .env $SKILL_DIR/scripts/fetch_dart.py 005930 --section business --out _evidence/dart_business.json
```
- 사업부별 매출 비중·영업이익
- 지역별 매출
- 주요 제품·고객·공급사 (집중도)
- 자회사·관계사 (단순화된 지배구조)

### 2.2 보완: 회사 IR 페이지
Tavily 로 `{회사명} IR 분기 발표자료 site:samsung.com` 등 검색 후, 필요한 URL 만 `tavily-extract` 로 추출. PDF/동적 페이지 추출이 막히면 firecrawl fallback.
세그먼트 economics 가 DART 보다 상세한 경우 多.

## 3. Operating KPI

`references/industry_kpi.md` 의 매트릭스 보고 업종별 KPI 결정.
- DART 사업보고서 본문 정량 분석 표
- 회사 분기 IR 발표자료 (PDF) — Tavily 로 URL 을 먼저 찾고, PDF 파싱이 필요할 때 firecrawl-parse fallback

## 4. 재무 (3~5년)

### 4.1 DART XBRL 재무제표
```bash
uv run --env-file .env $SKILL_DIR/scripts/fetch_dart.py 005930 --section financials --years 5 --summary --out _evidence/dart_fin.json
```
포함:
- 손익: 매출, 영업이익, 순이익, EBITDA
- 수익성: ROE, ROA, ROIC, EPS
- 건전성: 부채비율, 유동비율, 이자보상배율
- CF: CFO, CAPEX, FCF
- 주주환원: 배당, 자사주
- 운전자본: DSO, DIO, DPO, CCC

### 4.2 cross-check: pykrx 재무비율
```bash
uv run --env-file .env $SKILL_DIR/scripts/fetch_pykrx.py 005930 --section ratios --out _evidence/krx_ratios.json
```
DART 와 불일치 시 DART (1차) 우선, 차이 footnote 처리.

### 4.3 canonical 재무 파일
```bash
python3 $SKILL_DIR/scripts/normalize_financials.py _evidence --ticker 005930 --out _evidence/canonical_financials.json
python3 $SKILL_DIR/scripts/evidence_manifest.py _evidence --ticker 005930 --out _evidence/manifest.json
python3 $SKILL_DIR/scripts/evidence_brief.py _evidence --ticker 005930 --out _evidence/evidence_brief.md
```
research.md 재무 표는 이 파일의 `metrics` 를 우선 참고하고, 각 값의 `source_file/source` 를 인용에 연결.
작성 단계에서는 `evidence_brief.md` 를 먼저 읽고, 100KB 초과 raw 파일은 전체 로드하지 않는다.

## 5. 시장·밸류에이션 현황

```bash
uv run --env-file .env $SKILL_DIR/scripts/fetch_pykrx.py 005930 --section valuation --out _evidence/krx_val.json
```
- 현재가, 52주 고저
- PER, PBR, PSR, 배당수익률 (KRX 발표 기준)
- EV/EBITDA 는 DART 재무 + 시총으로 계산

### Peer 비교
- 동일 KSIC 4자리 + 시총 ±50% 후보 추출
- 최대 5개. 비교 표 작성
- 선정 기준 명시 ("KSIC 26110 반도체 제조, 시총 10조원 이상")

## 6. 산업·경쟁

- 시장 규모: 업계 협회 (예: 한국반도체산업협회), 정부 백서, IDC/Gartner
- 점유율: 회사 IR + 업계 자료 cross-check
- Tavily search: `{산업명} 시장규모 2025 한국` / `market share Korea 2025`
- 특정 협회·정부·시장조사 URL 이 잡히면 `tavily-extract` 로 본문만 추출

## 7. 매크로 노출

- 수출 비중 → DART 사업보고서 지역별 매출
- 환율 민감도: 회사 reported sensitivity (있는 경우)
- 한국은행 ECOS: 원/달러 환율, 금리 시계열
```bash
# 환율 (한국은행 ECOS — 원/달러)
uv run --env-file .env --with requests python3 -c "import os, requests; k=os.environ['BOK_ECOS_API_KEY']; r=requests.get(f'https://ecos.bok.or.kr/api/StatisticSearch/{k}/json/kr/1/10/731Y001/D/20260101/20260520/0000001').json(); print(r['StatisticSearch']['row'][:3])"
# FRED DEXKOUS 도 같은 환율, 보조
```

## 8. 최근 이벤트 (6~12개월)

### 8.1 DART 공시 목록
```bash
uv run --env-file .env $SKILL_DIR/scripts/fetch_dart.py 005930 --section disclosures --days 365 --out _evidence/dart_disc.json
```
- 정정공시
- 주요사항보고서 (M&A, 자사주, 증자)
- 분기·반기·사업보고서 (실적)

`fetch_dart.py --section all` 경로는 raw disclosures 와 함께 `{ticker}_disclosures_summary.json` 를 생성한다. 최근 이벤트 작성 시 summary 를 먼저 사용하고, 필요한 공시 URL 만 부분 확인한다.

### 8.2 뉴스 (Tavily 우선)
한국 뉴스 공식 API 부재 → Tavily 로 검색 후 원문 확인:
- tavily-search `"삼성전자" 실적 OR 공시 -광고 site:hankyung.com OR site:mk.co.kr`
- 필요한 기사/공식 보도자료 URL 만 tavily-extract
- Tavily 가 동적 페이지·PDF 에서 실패할 때만 firecrawl fallback
- 최근 6개월 필터

## 9. 컨센서스·가이던스

- FnGuide (스크래핑 또는 한경 컨센서스 페이지)
- 회사 공식 가이던스 (분기 컨퍼런스콜, IR 보도자료)
- 최근 4~8분기 surprise 이력 → 회사 IR + 증권사 리포트
- 출처별 차이 명시

## 10. 지배구조

DART 사업보고서:
- 최대주주 및 특수관계인 (지분율)
- 이사회 구성 (사외이사 비율)
- 임원 보수 (이사회 의결액)

한국 특수 항목:
- 일감몰아주기 대상 여부
- 지주사 전환 진행
- 합병비율 (계열사 합병 시)

## 11. 자본배분 트랙레코드

5년 시계열로 DART 에서 추출:
- CAPEX / 매출 %
- R&D / 매출 %
- M&A 이력 (인수가, 인수일, 통합 후 매출 기여)
- 배당 총액·DPS
- 자사주 매입·소각 누적

ROIC 5년 추이로 자본배분 효율 사실 진술 (수치만).

## 12. 갱신

- 분기 실적 발표 후: `--update --section=재무,KPI,이벤트,컨센서스`
- 사업보고서 발표 후 (3월): 전체 재작성
- 60일 경과: 시장·밸류에이션만 갱신

## 13. MCP 우선 경로 (설치된 경우)

Korean Stock MCP (DART+KRX) 설치되어 있으면 단순 조회는 MCP 직접 호출:
- `mcp__korean_stock__get_corp_info`
- `mcp__korean_stock__get_disclosures`
- `mcp__korean_stock__get_quote`

복잡한 XBRL 파싱·5년 시계열은 여전히 Python script 권장 (raw JSON 덤프 + 요약만 컨텍스트로).
