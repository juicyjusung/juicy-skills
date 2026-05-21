# 객관성 규칙

Research Layer 의 정체성. 위반 시 산출물 폐기·재작성.

## 1. 금칙어 (lint 차단 대상)

본문에 다음 단어 등장 시 `$SKILL_DIR/scripts/lint_research.py` 가 실패 처리. Evaluation Layer 로 미루기.

### 가치 판단
- 저평가 / 고평가 / 적정가 / 적정가치
- 매수 / 매도 / 추천 / 보유 / 비중확대 / 비중축소

### 정성 형용
- 유망 / 매력적 / 우량 / 부실 / 견조 / 양호
- 호재 / 악재 / 기대 / 우려 / 부담 / 모멘텀
- 성장 가능성 / 잠재력 / 전망 밝음

### 예측·주관
- ~할 것으로 보인다 / ~할 전망 / ~이 예상된다
- 향후 / 앞으로 / 중장기적으로

**예외**: 인용 안 직접 등장은 허용 — "회사 가이던스: '2026년 매출 X조 전망'" 처럼 따옴표 안.

## 2. 허용 표현

### 2.1 수치 + 출처 + 시점
```
2025년 매출 300조원 [DART 사업보고서, 2026-03-15]
2026년 5월 20일 종가 75,000원 [KRX]
```

### 2.2 비교 사실
```
peer 평균 PER 12.5 대비 PER 8.2
영업이익률 9.3% (산업 평균 6.8%)
```

### 2.3 추세 진술 (의견 없이 숫자만)
```
영업이익률 3년 연속 하락: 10.2% → 7.8% → 5.3%
FCF 2년 연속 음전: -1.2조 → -0.8조
```

### 2.4 회사·기관 공식 입장 인용
```
회사 가이던스 (2026-Q1 컨퍼런스콜): "2026 CAPEX 50조원 집행 계획"
S&P 신용등급: AA- (2026-04-10, S&P Global)
```
인용은 따옴표 + 출처 명시. 본인 의견과 구분.

## 3. 인용·시점 규칙

### 3.1 모든 수치는 다음 중 하나로 표기
- 인라인: `300조원 [DART 사업보고서, 2026-03-15]`
- Footnote: `300조원[^1]` + 본문 끝 `[^1]: DART 사업보고서, 2026-03-15`
- 표 캡션: `*출처: FnGuide, 2026-05-20*`

### 3.2 frontmatter 필수 필드
```yaml
as_of: 2026-05-21              # 작성 기준일
price_as_of: 2026-05-20        # 가격 기준일
financials_as_of: 2025-12-31   # 최신 결산일
evidence_manifest: _evidence/manifest.json
canonical_financials: _evidence/canonical_financials.json
evidence_brief: _evidence/evidence_brief.md
sources:
  - https://dart.fss.or.kr/...
  - https://...
```

### 3.3 가격·시총 등 시점 의존 지표
같은 `as_of` 기준으로 통일. 혼용 금지.

## 4. Evidence Gap 표기

자료 못 찾은 항목은 **빈칸 X**. 명시:
```
- 시장점유율 2025년: N/A (출처 미확보 — 2024년까지만 IDC 발표)
- 경쟁사 영업이익률: N/A (사업부별 segment 분리 안 됨)
```

추측·외삽 절대 금지. Evaluation Layer 가 gap 보고 가중치 조정.

## 5. 출처 신뢰도 등급

| 등급 | 한국 | 미국 |
|---|---|---|
| 1차 (best) | DART 사업·분기보고서 (XBRL) | SEC EDGAR 10-K/10-Q (XBRL) |
| 2차 | FnGuide, 회사 IR | FMP, Bloomberg, Morningstar |
| 3차 | 네이버 금융, 증권사 리포트 | Yahoo, Seeking Alpha |

분석에는 항상 1차 우선. 2·3차는 cross-check 보조. 1·2차 수치 불일치 시 1차 우선 + 차이 노트.

## 6. 회계기준 차이 주의

비율 비교 시 다음 항목은 주석 필수:
- IFRS 16 리스 (영업이익·EBITDA 영향)
- 재고 평가: LIFO (미국 일부) vs FIFO (한국·미국 다수)
- R&D 자산화 vs 비용화
- 비반복 항목 (자산매각, 손상차손, 환산손익)

**Normalized 수치** 별도 표시 권장:
```
2025 영업이익 12.3조원 (보고)
  - 손상차손 2.1조원 제외 시 normalized 14.4조원
```

## 7. peer 비교 규칙

- peer 3~5개 명시 + 선정 기준 명시
- 선정 기준 예: 시총 ±50%, 동일 GICS sub-industry, 동일 회계기준
- 최소 2개 peer 는 멀티플/수익성 수치값을 채움
- 잘못 고른 peer 의 멀티플 비교는 무의미 — 수치가 전부 N/A이면 peer fetch를 추가하거나 비교 불가 사유를 Evidence Gap에 명시

## 8. lint 자가 점검 명령

```bash
python3 $SKILL_DIR/scripts/lint_research.py stocks/{ticker}/research.md
```

종료 코드:
- 0: 통과
- 1: 금칙어 발견 (위치 출력)
- 2: 인용 누락 (수치 있는데 출처 표기 없음)
- 3: frontmatter 필수 필드 누락
