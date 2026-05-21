#!/usr/bin/env bun
import { callApi, parseNumber } from "./_client.ts";

const flags = new Map<string, string>();
for (const a of process.argv.slice(2)) {
  const m = a.match(/^--([a-z-]+)=(.+)$/);
  if (m) flags.set(m[1], m[2]);
}
// inds_cd: 001=종합(KOSPI), 101=종합(KOSDAQ), etc. Default 종합지수.
const indsCd = flags.get("inds-cd") ?? "001";
const count = Number(flags.get("count") ?? "100");

try {
  const res = await callApi({
    apiId: "ka20003",
    path: "/api/dostk/sect",
    body: { inds_cd: indsCd },
  });
  const d = res.data as Record<string, unknown>;
  const rowsKey = Object.keys(d).find((k) => Array.isArray(d[k]));
  const rows = rowsKey ? ((d[rowsKey] as Array<Record<string, unknown>>) ?? []) : [];
  const items = rows.slice(0, count).map((r) => ({
    code: r.inds_cd ?? r.stk_cd ?? null,
    name: r.inds_nm ?? r.stk_nm ?? null,
    current: parseNumber(r.cur_prc),
    change: parseNumber(r.pred_pre),
    change_pct: parseNumber(r.flu_rt),
    volume: parseNumber(r.trde_qty),
    trade_value: parseNumber(r.trde_prica),
  }));
  console.log(
    JSON.stringify(
      {
        inds_cd: indsCd,
        count: items.length,
        items,
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
