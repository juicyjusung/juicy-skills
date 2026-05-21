# Output Format

Write the answer in Korean. Keep it compact and practical.

## Template

```text
단타 계획: {ticker} {name}
기준: {data_time} KST / 리스크 모드: {risk_mode}

1. 결론
- 상태: {보유 관리 | 조건부 진입 가능 | 신규 진입 보류 | 방어 우선 | 데이터 부족}
- 단타 적합도: {score}/100
- 핵심 판단: {one sentence}
- 근거 강도: {강함 | 보통 | 약함}

2. 가격 계획
- 기준가: {reference_price}원
- 현재가: {current_price}원
- 손절가: {stop_price_or_hold}
- 1차 익절가: {target1_or_hold}
- 2차 익절가: {target2_or_hold}
- 손익비: {rr1}R / {rr2}R

3. 셋업 판정
- VWAP 지지형: {강함 | 보통 | 약함 | 해당 없음}
- 눌림목: {강함 | 보통 | 약함 | 해당 없음}
- 돌파형: {강함 | 보통 | 약함 | 해당 없음}
- 스캘핑: {강함 | 보통 | 약함 | 해당 없음}

4. 무효화 조건
- {price or condition}
- {price or condition}

5. 경고
- {warning}
- {warning}
```

## Style

- Use conditional language: `이탈 시`, `회복 실패 시`, `유지될 때`.
- State stale or missing data before any price plan.
- If a gate fails, show a defensive plan if useful, but do not frame it as a
  valid new entry.
- Avoid definitive phrases such as `무조건`, `확실`, `매수`, `매도`, or `보장`.
- Include the data 기준 시각 whenever the source provides it; otherwise say
  `조회 시점 기준`.
