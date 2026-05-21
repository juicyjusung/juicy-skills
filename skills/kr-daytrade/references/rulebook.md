# Rulebook

Treat these rules as structured heuristics, not guarantees. Hard gates in
`risk-policy.md` take priority.

## Contents

- Core Rules
- Context Rules
- Warning Rules
- Low-Confidence Rules

## Core Rules

```text
id: core-vwap-support
category: core
setup: vwap
confidence: strong
weight: high
applies_when: Current price is above intraday VWAP and pullbacks hold near VWAP.
calculation: Compare current price, recent lows, and intraday VWAP.
output_hint: VWAP 위 지지가 유지되면 눌림 계획은 유효하나 VWAP 이탈 후 회복 실패는 무효화.
```

```text
id: core-volume-confirmation
category: core
setup: breakout | pullback | scalping
confidence: strong
weight: high
applies_when: Recent volume is meaningfully above the prior intraday average.
calculation: Last candle volume versus prior 20-candle average.
output_hint: 거래량 동반 여부를 셋업 강도의 핵심 근거로 표시.
```

```text
id: core-risk-reward
category: core
setup: risk
confidence: strong
weight: high
applies_when: A stop and first target can be estimated.
calculation: rr1 = abs(target1 - reference) / abs(reference - stop).
output_hint: 1차 손익비가 리스크 모드 기준에 못 미치면 신규 진입 보류.
```

```text
id: core-recent-low-stop
category: core
setup: risk
confidence: strong
weight: high
applies_when: Recent intraday bars show a clear swing low.
calculation: Use the lowest low from recent candles, adjusted to tick size.
output_hint: 직전 저점 이탈은 단타 무효화선으로 우선 고려.
```

## Context Rules

```text
id: context-pullback
category: context
setup: pullback
confidence: medium
weight: medium
applies_when: Price pulls back after a first impulse but remains above VWAP or prior support.
calculation: Current price below recent high, above VWAP, with recent low above the prior swing low.
output_hint: 눌림목은 지지 확인 후에만 조건부로 표현.
```

```text
id: context-breakout
category: context
setup: breakout
confidence: medium
weight: medium
applies_when: Price clears a prior intraday high or box top with increased volume.
calculation: Current price above previous 20-candle high and last volume above average.
output_hint: 돌파선 재이탈을 가장 가까운 무효화 조건으로 표시.
```

```text
id: context-gap
category: context
setup: gap
confidence: medium
weight: medium
applies_when: Open is more than 3% above prior close.
calculation: gap_pct = (open - prev_close) / prev_close * 100.
output_hint: 갭상승 후 지지 확인 전 추격은 보류 또는 약한 근거로 처리.
```

```text
id: context-scalping
category: context
setup: scalping
confidence: medium
weight: medium
applies_when: Execution strength is high, volume expands, and spread is tight.
calculation: Tick strength near or above 150, bid depth supportive, spread within 1-2 ticks.
output_hint: 스캘핑 근거는 짧은 유효기간을 명시.
```

## Warning Rules

```text
id: warning-orderbook-gap
category: warning
setup: risk
confidence: strong
weight: high
applies_when: Best ask and best bid are separated by several ticks or depth is thin.
calculation: spread_ticks = (best_ask - best_bid) / tick_size(current_price).
output_hint: 호가 공백이 크면 손절 체결 가능성을 낮게 보고 지정가 우선 경고.
```

```text
id: warning-fake-liquidity
category: warning
setup: scalping
confidence: weak
weight: low
applies_when: Large displayed depth changes quickly or does not translate into executions.
calculation: Requires repeated orderbook snapshots; single snapshot is weak evidence.
output_hint: 단일 호가창만으로 허매수, 허매도를 단정하지 말 것.
```

```text
id: warning-late-session
category: warning
setup: risk
confidence: medium
weight: medium
applies_when: Near close, volatility rises, or liquidity fades.
calculation: Use Korea market time and source timestamp when available.
output_hint: 장 막판에는 신규 진입보다 방어와 청산 계획을 우선.
```

## Low-Confidence Rules

```text
id: lowconf-tick-strength-alone
category: low-confidence
setup: scalping
confidence: weak
weight: low
applies_when: Execution strength is the only bullish evidence.
calculation: Tick strength without volume, VWAP, and orderbook confirmation.
output_hint: 체결강도 단독 근거는 약함으로 표시.
```
