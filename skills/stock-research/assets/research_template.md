---
ticker: {TICKER}
name: {COMPANY_NAME}
exchange: {EXCHANGE}              # KOSPI / KOSDAQ / NYSE / NASDAQ
currency: {CURRENCY}              # KRW / USD
fiscal_year_end: {MONTH}          # 12 (December), 6 (June) 등
accounting_standard: {STANDARD}   # K-IFRS / US GAAP / IFRS
gics_sector: {SECTOR}
gics_sub_industry: {SUB_INDUSTRY}
as_of: {YYYY-MM-DD}               # 작성 기준일
price_as_of: {YYYY-MM-DD}         # 가격 시점
financials_as_of: {YYYY-MM-DD}    # 최신 결산일
evidence_manifest: _evidence/manifest.json
canonical_financials: _evidence/canonical_financials.json
evidence_brief: _evidence/evidence_brief.md
sources:
  - {PRIMARY_URL_1}
  - {PRIMARY_OR_SECONDARY_URL_2}
---

# {COMPANY_NAME} ({TICKER}) Research

> 본 문서는 객관 사실만 정리. 의견·판단·추천 포함되지 않음.
> 모든 수치는 출처·시점 명시. 자료 미확보 항목은 `N/A` 표기.

## 1. 회사 식별

- **회사명**: {name}
- **티커**: {ticker} ({exchange})
- **통화**: {currency}
- **결산월**: {fiscal_year_end}월
- **회계기준**: {accounting_standard}
- **산업**: GICS {sector} / {sub_industry}
- **시가총액**: {시총} [출처:날짜]
- **유통주식수**: {주식수} [출처:날짜]

## 2. 사업

### 2.1 사업부별 매출·이익
| 사업부 | 매출 비중 (%) | 영업이익률 (%) |
|---|---|---|
| ... | ... | ... |
*출처: {source}, {date}*

### 2.2 지역별 매출
| 지역 | 비중 (%) |
|---|---|
| ... | ... |

### 2.3 주요 제품·서비스
- ...

### 2.4 고객·공급사 집중도
- 상위 N개 고객 매출 비중: X% [출처]
- 주요 공급사: ...

### 2.5 자회사·관계사 (요약)
- ...

## 3. Operating KPI

> 산업별 핵심 운영지표. `references/industry_kpi.md` 참조.

| KPI | YYYY-1 | YYYY | 출처 |
|---|---|---|---|
| ... | ... | ... | ... |

## 4. 재무 (최근 3~5년)

### 4.1 손익
| 항목 | YYYY-4 | YYYY-3 | YYYY-2 | YYYY-1 | YYYY |
|---|---|---|---|---|---|
| 매출 |  |  |  |  |  |
| YoY 성장률 (%) |  |  |  |  |  |
| 영업이익 |  |  |  |  |  |
| 영업이익률 (%) |  |  |  |  |  |
| 순이익 |  |  |  |  |  |
| EBITDA |  |  |  |  |  |
| EBITDA 마진 (%) |  |  |  |  |  |
| EPS (희석) |  |  |  |  |  |

### 4.2 수익성
| 항목 | YYYY-4 | YYYY-3 | YYYY-2 | YYYY-1 | YYYY |
|---|---|---|---|---|---|
| ROE (%) |  |  |  |  |  |
| ROA (%) |  |  |  |  |  |
| ROIC (%) |  |  |  |  |  |

### 4.3 재무건전성
| 항목 | YYYY-4 | YYYY-3 | YYYY-2 | YYYY-1 | YYYY |
|---|---|---|---|---|---|
| 부채비율 (%) |  |  |  |  |  |
| 유동비율 |  |  |  |  |  |
| 이자보상배율 |  |  |  |  |  |
| 순차입금 / EBITDA |  |  |  |  |  |

### 4.4 현금흐름
| 항목 | YYYY-4 | YYYY-3 | YYYY-2 | YYYY-1 | YYYY |
|---|---|---|---|---|---|
| 영업현금흐름 (CFO) |  |  |  |  |  |
| CAPEX |  |  |  |  |  |
| FCF |  |  |  |  |  |
| FCF 마진 (%) |  |  |  |  |  |

### 4.5 주주환원
| 항목 | YYYY-4 | YYYY-3 | YYYY-2 | YYYY-1 | YYYY |
|---|---|---|---|---|---|
| 배당총액 |  |  |  |  |  |
| DPS |  |  |  |  |  |
| 배당성향 (%) |  |  |  |  |  |
| 배당수익률 (%) |  |  |  |  |  |
| 자사주 매입 |  |  |  |  |  |
| 자사주 소각 |  |  |  |  |  |

### 4.6 운전자본·CCC
| 항목 | YYYY-4 | YYYY-3 | YYYY-2 | YYYY-1 | YYYY |
|---|---|---|---|---|---|
| DSO (일) |  |  |  |  |  |
| DIO (일) |  |  |  |  |  |
| DPO (일) |  |  |  |  |  |
| CCC (일) |  |  |  |  |  |

*전체 4장 출처: {source}, {date}*

## 5. 시장·밸류에이션 현황

### 5.1 가격·시총
- 현재가: {가격} ({as_of})
- 52주 고저: {high} / {low}
- 시총: {시총}

### 5.2 멀티플
| 지표 | 자사 | Peer 평균 |
|---|---|---|
| PER (TTM) |  |  |
| PER (Fwd) |  |  |
| PBR |  |  |
| PSR |  |  |
| PEG |  |  |
| EV / EBITDA |  |  |
| EV / Sales |  |  |
| 배당수익률 (%) |  |  |

### 5.3 Peer 비교
| 회사 | 시총 | PER | PBR | EV/EBITDA | ROE |
|---|---|---|---|---|---|
| {self} |  |  |  |  |  |
| {peer1} |  |  |  |  |  |
| {peer2} |  |  |  |  |  |
| {peer3} |  |  |  |  |  |

*Peer 선정 기준: {기준 명시 — GICS xxx, 시총 ±50% 등}. 최소 2개 peer는 멀티플/수익성 수치를 채울 것. 전부 N/A이면 peer fetch를 추가하거나 비교 불가 사유를 Evidence Gap에 명시하고 사용자에게 보고.*

## 6. 산업·경쟁

### 6.1 시장 규모
- TAM: {규모} (출처, 연도)
- 성장률: {CAGR}

### 6.2 점유율
| 회사 | 점유율 (%) | 기준 |
|---|---|---|
| {self} |  |  |
| {comp1} |  |  |

### 6.3 산업 사이클 단계
{성장기 / 성숙기 / 쇠퇴기 — 사실 근거: 매출 성장률, 신규 진입 등}

### 6.4 경쟁사 핵심 차이 (객관 사실만)
- {Comp A}: {제품·시장·기술 차이 — 사실 진술}

## 7. 매크로 노출

- 수출 비중: X% → 환율 민감
- 부채구조: 변동금리 비중 X% → 금리 민감
- 원자재: {원자재} 사용량 X톤/연
- 규제 대상: {규제명}

## 8. 최근 이벤트 (6~12개월)

| 날짜 | 이벤트 | 출처 |
|---|---|---|
| YYYY-MM-DD | 실적 발표 (컨센서스 대비 +/-X%) | DART/EDGAR |
| YYYY-MM-DD | M&A·자사주·증자 | ... |
| YYYY-MM-DD | 경영진 변동 | ... |
| YYYY-MM-DD | 규제·소송 | ... |

## 9. 컨센서스·가이던스

### 9.1 컨센서스
| 지표 | 2026E | 2027E | 출처 (날짜) |
|---|---|---|---|
| 매출 |  |  |  |
| 영업이익 |  |  |  |
| EPS |  |  |  |

### 9.2 회사 가이던스
- {분기·연간 가이던스 인용 — 따옴표 안에 회사 발언}

### 9.3 Surprise 이력 (최근 4~8분기)
| 분기 | 컨센서스 EPS | 실제 EPS | Surprise (%) |
|---|---|---|---|
| ... | ... | ... | ... |

### 9.4 컨센서스 조정 추세
- 최근 90일 EPS 컨센서스 변동: +/-X%

## 10. 지배구조

### 10.1 주요 주주
| 주주 | 지분율 (%) | 비고 |
|---|---|---|
| 최대주주 |  |  |
| 특수관계인 |  |  |
| 외국인 |  |  |
| 기관 |  |  |

### 10.2 이사회
- 사내이사 N명 / 사외이사 N명
- 위원회: 감사·보상·지명

### 10.3 경영진 보수
- CEO 총보수: X (구성: 고정 X / 변동 X / 주식보상 X)
- 출처: {DEF-14A 또는 사업보고서}

### 10.4 한국 한정 (해당 시)
- 일감몰아주기 대상: Y/N
- 지주사 전환: ...
- 합병·분할 진행: ...

## 11. 자본배분 트랙레코드

| 연도 | CAPEX | CAPEX/매출 | R&D | R&D/매출 | M&A | 배당 | 자사주 |
|---|---|---|---|---|---|---|---|
| YYYY-4 |  |  |  |  |  |  |  |
| YYYY-3 |  |  |  |  |  |  |  |
| YYYY-2 |  |  |  |  |  |  |  |
| YYYY-1 |  |  |  |  |  |  |  |
| YYYY |  |  |  |  |  |  |  |

### 11.1 ROIC 추이
| 연도 | YYYY-4 | YYYY-3 | YYYY-2 | YYYY-1 | YYYY |
|---|---|---|---|---|---|
| ROIC (%) |  |  |  |  |  |

### 11.2 주요 M&A
| 날짜 | 대상 | 인수가 | 통합 후 매출 기여 |
|---|---|---|---|
| ... | ... | ... | ... |

---

## Evidence Gap

자료 못 찾은 항목 명시:
- {항목}: N/A ({사유})
- {수치가 비어 있는 peer 항목}: N/A ({추가 fetch 실패/권한 제한/공시 미제공 등 구체 사유})

## 참고 자료

[1] {출처명} ({URL}, {접근일})
[2] ...

## Evidence Manifest

- manifest: `_evidence/manifest.json`
- canonical financials: `_evidence/canonical_financials.json`
- evidence brief: `_evidence/evidence_brief.md`

## 변경 이력
참조: `CHANGELOG.md`
