#!/usr/bin/env bun
import { callApi, parseNumber } from "./_client.ts";

type RankBy = "volume" | "change" | "value";

const flags = new Map<string, string>();
for (const a of process.argv.slice(2)) {
  const m = a.match(/^--([a-z-]+)=(.+)$/);
  if (m) flags.set(m[1], m[2]);
}

const by = (flags.get("by") ?? "volume") as RankBy;
const market = flags.get("market") ?? "000"; // 000=전체, 001=KOSPI, 101=KOSDAQ
const stex = flags.get("stex") ?? "1"; // 1=KRX
const sortTp = flags.get("sort") ?? "1"; // 1=거래량(많은순) 등 (TR별 의미 다름)
const count = Number(flags.get("count") ?? "30");

if (!["volume", "change", "value"].includes(by)) {
  console.error(`bad --by: ${by}`);
  process.exit(1);
}

function spec(b: RankBy): {
  apiId: string;
  path: string;
  body: Record<string, unknown>;
} {
  switch (b) {
    case "volume":
      // ka10030 당일거래량상위
      return {
        apiId: "ka10030",
        path: "/api/dostk/rkinfo",
        body: {
          mrkt_tp: market,
          sort_tp: sortTp,
          mang_stk_incls: "0",
          crd_tp: "0",
          trde_qty_tp: "0",
          pric_tp: "0",
          trde_prica_tp: "0",
          mrkt_open_tp: "0",
          stex_tp: stex,
        },
      };
    case "change":
      // ka10027 전일대비등락률상위
      return {
        apiId: "ka10027",
        path: "/api/dostk/rkinfo",
        body: {
          mrkt_tp: market,
          sort_tp: sortTp, // 1=상승률,2=상승폭,3=하락률,4=하락폭 (가이드 확인)
          trde_qty_cnd: "0000",
          stk_cnd: "0",
          crd_cnd: "0",
          updown_incls: "1",
          pric_cnd: "0",
          trde_prica_cnd: "0",
          stex_tp: stex,
        },
      };
    case "value":
      // ka10032 거래대금상위
      return {
        apiId: "ka10032",
        path: "/api/dostk/rkinfo",
        body: {
          mrkt_tp: market,
          mang_stk_incls: "0",
          stex_tp: stex,
        },
      };
  }
}

const { apiId, path, body } = spec(by);

try {
  const res = await callApi({
    apiId,
    path,
    body,
  });
  const d = res.data as Record<string, unknown>;
  const rowsKey = Object.keys(d).find((k) => Array.isArray(d[k]));
  const rows = rowsKey ? ((d[rowsKey] as Array<Record<string, unknown>>) ?? []) : [];
  const items = rows.slice(0, count).map((r, idx) => ({
    rank: parseNumber(r.rank ?? r.rnk) ?? idx + 1,
    ticker: r.stk_cd ?? null,
    name: r.stk_nm ?? null,
    price: parseNumber(r.cur_prc),
    change: parseNumber(r.pred_pre),
    change_pct: parseNumber(r.flu_rt),
    volume: parseNumber(r.trde_qty),
    trade_value: parseNumber(r.trde_amt ?? r.trde_prica),
  }));
  console.log(
    JSON.stringify(
      {
        by,
        tr: apiId,
        market,
        count: items.length,
        items,
        cont_yn: res.headers.contYn ?? null,
        next_key: res.headers.nextKey ?? null,
        _rows_key: rowsKey,
      },
      null,
      2,
    ),
  );
} catch (e) {
  console.error(e instanceof Error ? e.message : String(e));
  process.exit(1);
}
