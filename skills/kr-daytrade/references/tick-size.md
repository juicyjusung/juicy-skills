# Tick Size

Use this KRX stock tick-size table for regular Korean stocks. The source is KRX
Global Market Guide, "Tick Size":
https://global.krx.co.kr/contents/GLB/06/0602/0602010201/GLB0602010201T3.jsp

| stock price | tick |
|---:|---:|
| below 2,000 KRW | 1 KRW |
| 2,000 to below 5,000 | 5 KRW |
| 5,000 to below 20,000 | 10 KRW |
| 20,000 to below 50,000 | 50 KRW |
| 50,000 to below 200,000 | 100 KRW |
| 200,000 to below 500,000 | 500 KRW |
| 500,000 or higher | 1,000 KRW |

## Rounding

- Stops: round down to the nearest valid tick for long-position risk plans.
- Targets: round up to the nearest valid tick.
- Reference prices: round to the nearest valid tick.
- If the instrument is not a regular stock, flag that tick-size rules may need
  separate confirmation.

Use `scripts/tick-size.ts` for deterministic calculation.
