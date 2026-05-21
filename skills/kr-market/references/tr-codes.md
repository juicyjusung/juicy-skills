# Kiwoom TR 코드 / 엔드포인트 참조

| 용도 | TR (api-id) | endpoint path | 주요 요청 필드 | 비고 |
|------|------|------|------|------|
| OAuth 토큰 발급 | — | `/oauth2/token` | `grant_type`, `appkey`, `secretkey` | 응답 `expires_dt`(문자열), `token` |
| OAuth 토큰 폐기 | — | `/oauth2/revoke` | `appkey`, `secretkey`, `token` | |
| 주식기본정보 (현재가/등락/거래량) | `ka10001` | `/api/dostk/stkinfo` | `stk_cd` | quote.ts 사용 |
| 주식호가 (10단계) | `ka10004` | `/api/dostk/mrkcond` | `stk_cd` | orderbook.ts 사용 |
| 주식 일봉차트 | `ka10081` | `/api/dostk/chart` | `stk_cd`, `base_dt`, `upd_stkpc_tp` | |
| 주식 주봉차트 | `ka10082` | `/api/dostk/chart` | `stk_cd`, `base_dt`, `upd_stkpc_tp` | |
| 주식 월봉차트 | `ka10083` | `/api/dostk/chart` | `stk_cd`, `base_dt`, `upd_stkpc_tp` | |
| 주식 분봉차트 | `ka10080` | `/api/dostk/chart` | `stk_cd`, `tic_scope`(1/3/5/10/15/30/60), `upd_stkpc_tp` | |
| 시간별 체결 (틱) | `ka10003` | `/api/dostk/stkinfo` | `stk_cd` | ticks.ts. 응답 배열 `cntr_infr` |
| 당일 주요거래원 (5단계) | `ka10040` | `/api/dostk/rkinfo` | `stk_cd` | flow.ts --type=trader. **flat object** (배열 아님), `sel_trde_ori_<N>` / `buy_trde_ori_<N>` (N=1..5) |
| 외국인 매매동향 | `ka10008` | `/api/dostk/frgnistt` | `stk_cd` | flow.ts --type=foreign. 응답 배열 `stk_frgnr` |
| 기관 매매동향 | `ka10009` | `/api/dostk/frgnistt` | `stk_cd` | flow.ts --type=inst. 응답 배열 (장 마감 후 빈 응답 가능) |
| 전업종지수 | `ka20003` | `/api/dostk/sect` | `inds_cd`(001=KOSPI종합, 101=KOSDAQ종합) | sector.ts |
| 당일 거래량 상위 | `ka10030` | `/api/dostk/rkinfo` | `mrkt_tp`, `sort_tp`, `mang_stk_incls`, `crd_tp`, `trde_qty_tp`, `pric_tp`, `trde_prica_tp`, `mrkt_open_tp`, `stex_tp` | rank.ts --by=volume. 배열 `tdy_trde_qty_upper` |
| 전일대비 등락률 상위 | `ka10027` | `/api/dostk/rkinfo` | `mrkt_tp`, `sort_tp`, `trde_qty_cnd`, `stk_cnd`, `crd_cnd`, `updown_incls`, `pric_cnd`, `trde_prica_cnd`, `stex_tp` | rank.ts --by=change. 배열 `pred_pre_flu_rt_upper` |
| 거래대금 상위 | `ka10032` | `/api/dostk/rkinfo` | `mrkt_tp`, `mang_stk_incls`, `stex_tp` | rank.ts --by=value. 배열 `trde_prica_upper` |

## 공통 헤더

요청:
- `Content-Type: application/json;charset=UTF-8` (필수)
- `authorization: Bearer <token>` (필수)
- `api-id: <TR 코드>` (필수)
- `cont-yn: Y` (연속조회 시)
- `next-key: <prev response next-key>` (연속조회 시)

응답 헤더:
- `cont-yn`: `Y` 면 다음 페이지 존재
- `next-key`: 다음 호출에 전달

## 응답 공통 필드

- `return_code`: 0=정상, 그 외 에러
- `return_msg`: 메시지

## 종목코드 표기

- 6자리 그대로 (예: `005930`)
- 일부 TR/거래소 구분 필요 시 접두사 사용 (예: `KRX:005930`, `NXT:039490_NX`). 본 스킬 운영 기본은 6자리만.

## 숫자 파싱 주의

- 가격/등락 필드가 `+0700`, `-150`, `0000123` 같이 부호·0패딩 문자열로 옴
- `parseNumber()` 헬퍼 사용 (부호 처리 + 변환)

## 새 TR 추가 절차

1. 공식 가이드 https://openapi.kiwoom.com/m/guide/apiguide?jobTpCode=XX 에서 TR 코드/path/필드 확인
2. 이 표에 한 행 추가
3. `scripts/` 에 새 파일 작성 (기존 `quote.ts` 패턴 참고)
4. SKILL.md 워크플로우 분기 추가

## 검증된 응답 필드 (2026-05-21 실제 호출 기준)

### ka10001 (주식기본정보) 주요 필드
- `stk_nm`(종목명), `cur_prc`(현재가, ±부호), `pred_pre`(전일대비), `flu_rt`(등락률)
- `trde_qty`(거래량), `open_pric`/`high_pric`/`low_pric`(시고저, ±부호)
- `base_pric`(전일종가), `mac`(시가총액 백만원), `per`/`pbr`/`eps`/`bps`/`roe`
- `250hgst`/`250lwst`(250일 고/저)

### ka10004 (호가 10단계) 필드 패턴 — **확정**
- 1단계 (best): `sel_fpr_bid` / `sel_fpr_req` / `buy_fpr_bid` / `buy_fpr_req`
- 2~10단계: `sel_<N>th_pre_bid` / `sel_<N>th_pre_req` / `buy_<N>th_pre_bid` / `buy_<N>th_pre_req`
- 합계: `tot_sel_req` / `tot_buy_req`
- 시간외: `ovt_sel_req` / `ovt_buy_req`
- 기준시각: `bid_req_base_tm` (HHMMSS)

### ka10081 (일봉) 응답 배열 키
- 응답 root 의 `stk_dt_pole_chart_qry` 배열 (확정)
- 각 row 필드: `dt`(YYYYMMDD), `open_pric`, `high_pric`, `low_pric`, `cur_prc`(종가), `trde_qty`

### ka10080 (분봉) 응답 배열 키
- `stk_min_pole_chart_qry` 배열
- row 필드: `cntr_tm`(YYYYMMDDHHMMSS), `open_pric`, `high_pric`, `low_pric`, `cur_prc`, `trde_qty`

### ka10003 (체결정보 틱) 응답 필드
- 배열 `cntr_infr` 의 row: `tm`(HHMMSS), `cur_prc`(±), `pred_pre`(±), `pre_rt`(±), `cntr_trde_qty`(±, 체결 수량/방향), `sign`(1=상한,2=상승,3=보합,4=하한,5=하락), `acc_trde_qty`(누적 거래량), `acc_trde_prica`(누적 거래대금), `pri_sel_bid_unit`/`pri_buy_bid_unit`(최우선 매도/매수호가), `cntr_str`(체결강도)

### ka10040 (당일주요거래원) — 배열 아닌 flat
- N=1..5 각 단계마다 8개 필드:
  - `sel_trde_ori_<N>`(매도사명), `sel_trde_ori_cd_<N>`, `sel_trde_ori_qty_<N>`, `sel_trde_ori_irds_<N>`(증감)
  - `buy_trde_ori_<N>`, `buy_trde_ori_cd_<N>`, `buy_trde_ori_qty_<N>`, `buy_trde_ori_irds_<N>`

### ka10008 (외국인 매매동향) 응답 필드
- 배열 `stk_frgnr` 의 row: `dt`(YYYYMMDD), `close_pric`(±), `pred_pre`(±), `trde_qty`, `chg_qty`(순매매 보유 증감), `poss_stkcnt`(보유 주식수), `wght`(보유 비중 %), `gain_pos_stkcnt`(취득가능), `frgnr_limit`(한도), `frgnr_limit_irds`, `limit_exh_rt`

### ka20003 (전업종지수) 응답 필드
- 배열 row: `inds_cd`, `inds_nm`, `cur_prc`, `pred_pre`, `flu_rt`, `trde_qty`, `trde_prica`

### ka10030 / ka10027 / ka10032 (순위) 공통 row 필드
- `stk_cd`, `stk_nm`, `cur_prc`(±), `pred_pre_sig`, `pred_pre`(±), `flu_rt`(±), `trde_qty`, `trde_amt`(거래대금, 단위 백만원?)
- ka10027: `flu_rt` 기준 정렬
- ka10032: `trde_prica` (거래대금 정렬) 필드 사용 — 응답 배열 키도 다름

### 연속조회
- 응답 헤더 `cont-yn=Y` 면 `next-key` 받아 다음 호출에 같은 헤더 전달

### 시장코드 (`mrkt_tp`)
- `000`: 전체, `001`: KOSPI, `101`: KOSDAQ

### 거래소 (`stex_tp`)
- `1`: KRX, `2`: NXT, `3`: SOR

### `inds_cd` (업종 코드) 주요값
- `001`: KOSPI 종합, `101`: KOSDAQ 종합
- KOSPI 세부: `002` 대형주, `003` 중형주, `004` 소형주, `005` 음식료, `006` 섬유의복, `007` 종이목재, `008` 화학, `009` 의약품, `010` 비금속, `011` 철강금속, `012` 기계, `013` 전기전자, `014` 의료정밀, `015` 운수장비, `016` 유통, `017` 전기가스, `018` 건설, `019` 운수창고, `020` 통신, `021` 금융, `022` 은행, `024` 증권, `025` 보험, `026` 서비스, `027` 제조
