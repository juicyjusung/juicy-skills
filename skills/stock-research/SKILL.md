---
name: stock-research
description: >-
  Use this skill for objective, fact-only stock research on a single public
  company or ticker, including Korean KOSPI/KOSDAQ names and US NYSE/NASDAQ
  names. Trigger whenever the user asks for stock research, fundamental
  analysis, equity due diligence, ticker/company investigation, 종목 리서치,
  기업분석, 리서치 작성, 종목코드 분석, or similar work, even if they do not say
  "research". Produce `stocks/{ticker}/research.md` with cited facts,
  timestamps, evidence gaps, and no buy/sell opinions or valuation judgments.
  Use for tickers such as `005930`, `247540`, `TSLA`, `AAPL`, `BRK.B`.
---

# Stock Research Skill

목적: 티커 하나 받아서 **객관 사실만** 정리한 `stocks/{ticker}/research.md` 작성. 의견·판단·추천 금지. Evaluation Layer 입력용.

## 트리거

- `/stock-research <ticker>` 명시 호출
- 사용자가 종목 코드(6자리 숫자=한국, 알파벳=미국) + "리서치", "분석", "research", "조사" 등 언급
- `--update` 플래그: 재무·이벤트·컨센서스만 증분 갱신
- `--section=<name>` 플래그: 특정 섹션만 작성

## 핵심 원칙 — 반드시 지킬 것

1. **객관 사실만**. 금칙어(저평가/매수/유망 등) 등장 시 자체 중단·재작성. `references/objectivity.md` 참조.
2. **모든 수치에 출처+시점 필수**. `[출처:YYYY-MM-DD]` 형식.
3. **자료 못 찾은 항목은 `N/A (출처 미확보)`** — 추측 금지.
4. **1차 자료 우선**: 한국 DART · 미국 SEC EDGAR. 2·3차는 cross-check용.
5. **frontmatter `as_of` 필수**.

## 워크플로우 (요약)

```
0. `SKILL_DIR=.claude/skills/stock-research` 를 기준 경로로 둔다.
1. 티커 → `$SKILL_DIR/scripts/detect_market.py` 로 KR/US 판별
2. 시장별 fetch 1회 호출로 묶음 (--section all):
   - KR: fetch_dart.py {ticker} --section all --summary --out-dir _evidence/dart
         + fetch_pykrx.py {ticker} --section all --out-dir _evidence/pykrx
   - US: fetch_edgar.py {ticker} --section all --out-dir _evidence/edgar
         + fetch_fmp.py {ticker} --section all --out-dir _evidence/fmp
   둘 다 BG 병렬 실행 (`&` + `wait`). 절차 3 의 코드블록 참조.
3. 산업 KPI 결정 (references/industry_kpi.md) — 해당 산업만 읽기
4. normalize_financials.py → evidence_manifest.py → evidence_brief.py 순서로 compact evidence 생성
5. Tavily 로 보충 검색·추출 (사업부 본문, 시장점유율, 뉴스 — fetch 가 못 채운 부분만). firecrawl/WebSearch 는 fallback
6. evidence_brief.md + canonical_financials.json 우선 읽고, raw 대용량 파일은 targeted search 로만 확인
7. assets/research_template.md 구조로 research.md 작성 — 첫 작성에 인용 명시 (lint 재시도 줄임)
8. lint_research.py — exit 0 까지
```

세부는 각 reference 참조. SKILL.md 짧게 유지.

## 병렬 fetch 패턴 (필수 — 시간 절감 핵심)

5~10개 fetch script 직렬 실행 시 10분 소요. 병렬 처리로 1~2분 단축 가능. **한 번의 Bash 호출**에 묶기:

### 한국 종목 (예: 005930)
```bash
cd /Users/user/projects/juicyjusung/stock
SKILL_DIR=.claude/skills/stock-research
OUT=.claude/skills/stock-research-workspace/.../with_skill/_evidence
mkdir -p $OUT
(
  uv run --env-file .env $SKILL_DIR/scripts/fetch_dart.py 005930 --section all --summary --out-dir $OUT/dart &
  uv run --env-file .env $SKILL_DIR/scripts/fetch_pykrx.py 005930 --section all --out-dir $OUT/pykrx &
  wait
)
python3 $SKILL_DIR/scripts/normalize_financials.py $OUT --ticker 005930 --out $OUT/canonical_financials.json
python3 $SKILL_DIR/scripts/evidence_manifest.py $OUT --ticker 005930 --out $OUT/manifest.json
python3 $SKILL_DIR/scripts/evidence_brief.py $OUT --ticker 005930 --out $OUT/evidence_brief.md
```

### 미국 종목 (예: TSLA)
```bash
OUT=.claude/skills/stock-research-workspace/.../with_skill/_evidence
SKILL_DIR=.claude/skills/stock-research
mkdir -p $OUT
(
  uv run --env-file .env $SKILL_DIR/scripts/fetch_edgar.py TSLA --section all --out-dir $OUT/edgar &
  uv run --env-file .env $SKILL_DIR/scripts/fetch_fmp.py TSLA --section all --out-dir $OUT/fmp &
  wait
)
python3 $SKILL_DIR/scripts/normalize_financials.py $OUT --ticker TSLA --out $OUT/canonical_financials.json
python3 $SKILL_DIR/scripts/evidence_manifest.py $OUT --ticker TSLA --out $OUT/manifest.json
python3 $SKILL_DIR/scripts/evidence_brief.py $OUT --ticker TSLA --out $OUT/evidence_brief.md
```

### Peer 추가 (선택)
peer 멀티플 비교 시 `peers` JSON 의 ticker 를 고른 뒤 한 프로세스에서 valuation 묶음 fetch:
```bash
uv run --env-file .env $SKILL_DIR/scripts/fetch_fmp.py TSLA --section peer-valuations --symbols F,GM,RIVN,TM --out $OUT/fmp_peer_valuations.json
python3 $SKILL_DIR/scripts/evidence_manifest.py $OUT --ticker TSLA --out $OUT/manifest.json
python3 $SKILL_DIR/scripts/evidence_brief.py $OUT --ticker TSLA --out $OUT/evidence_brief.md
```

원칙: 다른 API (DART vs KRX, EDGAR vs FMP) 는 병렬. 같은 API 안의 peer 조회는 `peer-valuations` 로 묶어 uv/Python 콜드스타트를 줄인다. FMP 무료 250/일 한도는 그대로 적용된다.

## --all 과 --summary 옵션

- `--section all`: 한 process 에서 4~6 섹션 동시 처리 → uv 콜드스타트 ×N → ×1, dart-fss CORPCODE 로드 ×N → ×1. **3~5배 빠름**.
- `--summary` (fetch_dart financials 전용): 200+ accounts → 핵심 30개 (매출/영업이익/CFO/CAPEX 등) 평탄화 dict. 컨텍스트 -50%+, 5년 시계열 한눈에.
- `fetch_dart.py --section all`: corp_code 를 1회만 resolve 하고, 공시 raw 와 `{ticker}_disclosures_summary.json` 를 함께 생성한다.
- `fetch_pykrx.py --section all`: 영업일·시총·fundamental 조회를 재사용해 market/ratios/valuation 중복 호출을 피한다.
- `fetch_fmp.py --section peer-valuations`: 여러 peer valuation 을 한 프로세스·한 파일로 저장한다.
- `evidence_brief.py`: manifest + canonical 요약. 작성 단계는 이 파일을 먼저 읽고, 100KB 초과 raw 는 통째로 열지 않는다.

## 도구 사용 우선순위 (하이브리드 패턴)

토큰·정확도 최적화를 위해 다음 순서로 시도:

1. **MCP 직접 호출** — Korean Stock MCP (DART+KRX), Yahoo Finance MCP 가 설치되어 있으면 단순 조회는 여기로. 컨텍스트 가장 깨끗.
2. **Python script (`$SKILL_DIR/scripts/fetch_*.py`)** — 복잡한 파싱(XBRL, 사업부 segment, 멀티페이지 공시). 결과는 `_evidence/raw_{ticker}_{date}.json` 로 저장하고 요약만 읽음.
3. **Tavily (`tvly search`, `tavily-search`, `tavily-extract`, `tavily-research`)** — 뉴스·증권사 리포트·IR 페이지·시장점유율처럼 정형 API 없는 자료는 Tavily 우선. 먼저 search 로 URL 을 찾고, 필요한 페이지만 extract 한다.
4. **firecrawl** — Tavily extract 가 JS 렌더링, PDF 파싱, 로그인/클릭/페이지네이션 등으로 부족할 때 fallback.
5. **일반 WebSearch** — Tavily/firecrawl 이 부적합하거나 빠른 보조 확인이 필요할 때만 사용.
6. **회사 IR 페이지 직접 fetch** — 분기 발표자료 PDF 등.

원칙: raw 데이터는 파일로 저장하고 markdown 본문에는 요약·인용만. `manifest.json` 의 `load_policy=do_not_load_whole_file` 파일은 targeted search/추출로만 확인한다. Claude 컨텍스트 보호.

## 웹 검색 원칙

- 정형 API(DART/EDGAR/FMP/KRX) 가 못 채운 자료는 Tavily 를 먼저 사용한다.
- Discovery/search: `tvly search` 또는 `tavily-search`.
- 특정 URL 본문 추출: `tavily-extract`.
- 여러 출처를 종합해야 하는 산업·시장 리서치: `tavily-research`.
- Tavily 결과 URL 중 원문 출처가 확인되는 페이지만 evidence 에 남긴다. 블로그·커뮤니티 단독 출처는 사용하지 않는다.
- firecrawl 은 Tavily 가 동적 페이지, PDF, 상호작용, 인증 흐름 때문에 실패할 때만 fallback 으로 사용한다.

## 정확도 우선 작성 예산

- 단어 수 예산은 최종 문서 가독성을 위한 soft budget 이다. 자료 수집·검증을 단어 수 때문에 생략하지 않는다.
- 기본 산출물은 3,500~5,500단어. 대형주, 다사업부, 최근 이벤트가 많은 종목은 6,000~8,000단어까지 허용한다. 단순 update 는 1,000~2,500단어.
- 작성 전 읽는 파일 우선순위: `_evidence/evidence_brief.md` → `_evidence/canonical_financials.json` → `_evidence/manifest.json`.
- 100KB 초과 raw JSON/MD 는 전체 읽기 금지. 단, 핵심 수치·이벤트·N/A 항목 확인에는 `rg`, parser, targeted extraction 으로 원자료를 부분 확인한다.
- 정확도 gate:
  - 재무 핵심 수치는 DART/EDGAR/FMP canonical 과 원자료 `source_file` 을 대조한다.
  - 가격·시총·멀티플은 KRX/FMP/거래소/회사 공시 등 신뢰 출처를 우선한다.
  - 사업부·KPI·가이던스는 회사 공시/IR/10-K/사업보고서 우선, 부족하면 Tavily 로 2차 출처 보강.
  - 산업·뉴스·시장점유율은 Tavily 로 원문 URL 을 찾고, 필요한 페이지만 extract 한다.
  - 2차 출처 단독 수치는 Evidence Gap 또는 보조 출처로 명시한다.
- 최종 문서는 중복 설명을 줄이고 표·출처 캡션을 우선한다. 정확도 검증 결과를 줄이지 말고 표현만 압축한다.

## 산출 위치

```
stocks/
└── {ticker}/
	    ├── research.md          # 본 산출물
	    ├── CHANGELOG.md         # 갱신 이력
	    └── _evidence/           # raw 자료 (선택)
	        ├── manifest.json    # evidence file hash/source/fetched_at index
	        ├── canonical_financials.json
	        ├── evidence_brief.md
	        ├── dart_2026-05-21.json
        ├── edgar_10k_2025.json
        └── ...
```

프로젝트 루트 `stocks/` 폴더 없으면 생성.

## 갱신 정책

| 트리거 | 갱신 범위 |
|---|---|
| `--update` (분기 실적 발표 후) | 재무·KPI·이벤트·컨센서스 |
| `--section=<name>` | 해당 섹션만 |
| 60일 경과 (price/valuation 한정) | 시장·밸류에이션 |
| 전체 재작성 | 연차 보고서 발표 후 |

`as_of` 필드 항상 최신화. 변경 사항은 `CHANGELOG.md` 에 한 줄로 기록.

## 참조 문서 (progressive disclosure — 다 읽지 말 것)

상황 따라 최소만 읽기. 토큰·시간 절약.

| 시점 | 읽을 파일 |
|---|---|
| 항상 (필수) | `references/objectivity.md` — 금칙어·인용·gap 규칙. |
| 첫 실행 / 셋업 막힐 때 | `references/setup.md` — API key·uv·MCP. |
| KR 티커 (6자리) | `references/kr_workflow.md` — DART/pykrx 절차. |
| US 티커 (알파벳) | `references/us_workflow.md` — EDGAR/FMP 절차. |
| 산업 KPI 결정 시 | `references/industry_kpi.md` — 해당 산업 1개 섹션만. |
| 작성 시 | `assets/research_template.md` — 출력 골격. |

원칙: KR 종목인데 us_workflow 읽지 말 것. 산업이 반도체로 확정되면 industry_kpi.md 의 반도체 절만 보면 됨.

## 스크립트

호출 방식: `SKILL_DIR=.claude/skills/stock-research` 지정 후 모든 fetch script 는 `uv run --env-file .env $SKILL_DIR/scripts/fetch_*.py ...` (PEP 723 inline deps 자동 설치). stdlib-only 스크립트는 `python3 $SKILL_DIR/scripts/...` 도 가능.

- `$SKILL_DIR/scripts/detect_market.py <ticker>` (stdlib) → `KR` / `US` / `UNKNOWN`
- `$SKILL_DIR/scripts/fetch_dart.py <ticker> --section ... --out ...` (dart-fss) → DART 공시·재무 JSON
- `$SKILL_DIR/scripts/fetch_pykrx.py <ticker> --section ... --out ...` (pykrx) → 시세·재무비율 JSON
- `$SKILL_DIR/scripts/fetch_edgar.py <ticker> --section ... --out ...` (edgartools) → 10-K/10-Q JSON
- `$SKILL_DIR/scripts/fetch_fmp.py <ticker> --section ... --out ...` (requests, `/stable/` endpoint) → FMP JSON
- `$SKILL_DIR/scripts/normalize_financials.py <evidence_dir> --ticker ... --out ...` (stdlib) → 핵심 재무 canonical JSON
- `$SKILL_DIR/scripts/evidence_manifest.py <evidence_dir> --ticker ... --out ...` (stdlib) → evidence index
- `$SKILL_DIR/scripts/evidence_brief.py <evidence_dir> --ticker ... --out ...` (stdlib) → 작성용 compact evidence brief
- `$SKILL_DIR/scripts/lint_research.py <path>` (stdlib) → 금칙어·인용·frontmatter 검사 (exit 0=통과)

모든 fetch script `--out _evidence/...` 옵션으로 raw JSON 덤프. 본문에는 요약만 인용.

uv 미설치 시: `brew install uv` 또는 `curl -LsSf https://astral.sh/uv/install.sh | sh`

## 환경 변수

`$SKILL_DIR/scripts/` 가 읽는 키 — 사용자가 `~/.zshrc` 또는 `.env` 에 설정:

```
OPEN_DART_API_KEY=xxx        # https://opendart.fss.or.kr
FMP_API_KEY=xxx              # https://site.financialmodelingprep.com
FRED_API_KEY=xxx             # https://fred.stlouisfed.org
BOK_ECOS_API_KEY=xxx         # https://ecos.bok.or.kr
```

미설정 시 해당 소스 skip — 다른 소스로 보충하고 `_evidence_gap` 표기.

## 산출물 검증 체크리스트

research.md 작성 후 self-check:

- [ ] frontmatter `as_of`, `price_as_of`, `financials_as_of` 채워짐
- [ ] frontmatter `sources` URL 2개 이상 + `_evidence/manifest.json` + `_evidence/evidence_brief.md` 생성
- [ ] 모든 수치 옆 `[출처:날짜]` 또는 footnote
- [ ] 금칙어 0건 (`lint_research.py` 통과)
- [ ] peer 3~5개 명시 + 선정 기준 명시 + 최소 2개 peer 수치값
- [ ] 재무 3~5년 추이 테이블
- [ ] Evidence gap 명시 (N/A 항목 사유)
- [ ] 가격·시총·멀티플은 거래소/FMP/SEC/DART/회사 IR 등 1·2차 자료 우선, 블로그 단독 금지

체크 실패 시 사용자에게 보고 후 보강 또는 명시적 skip.

## 첫 작성 시 인용 명시 (lint 재시도 회피)

각 수치 라인을 쓸 때 **그 자리에서 즉시** `[출처명, YYYY-MM-DD]` 붙일 것. 표 셀에 적기 어려우면 표 바로 아래 `*출처: {src}, {date}*` 캡션 한 줄. 다 쓰고 나서 인용 채우기보다, 쓰는 순간 출처를 옆에 두는 게 훨씬 빠름 (lint 재시도 2~3회 → 0회).

## 참고 산출물

`examples/` 폴더에 잘 작성된 research.md 1개 (있다면). 구조·인용 스타일·gap 표기 방식 참고용. 새로 작성 시 형식만 모방, 내용은 새로 fetch.
