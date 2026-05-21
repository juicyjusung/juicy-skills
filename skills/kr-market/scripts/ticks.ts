#!/usr/bin/env bun
import { callApi, parseNumber } from "./_client.ts";

const ticker = process.argv[2];
const flags = new Map<string, string>();
for (const a of process.argv.slice(3)) {
  const m = a.match(/^--([a-z-]+)=(.+)$/);
  if (m) flags.set(m[1], m[2]);
}
const count = Number(flags.get("count") ?? "30");

if (!ticker || !/^\d{6}$/.test(ticker)) {
  console.error("usage: bun ticks.ts <6-digit-ticker> [--count=N]");
  process.exit(1);
}

try {
  const res = await callApi({
    apiId: "ka10003",
    path: "/api/dostk/stkinfo",
    body: { stk_cd: ticker },
  });
  const d = res.data as Record<string, unknown>;
  const rowsKey = Object.keys(d).find((k) => Array.isArray(d[k])) ?? "cntr_infr";
  const rows = (d[rowsKey] as Array<Record<string, unknown>>) ?? [];
  // sign: 1=상한,2=상승,3=보합,4=하한,5=하락 (가이드)
  const signMap: Record<string, string> = {
    "1": "upper_limit",
    "2": "up",
    "3": "flat",
    "4": "lower_limit",
    "5": "down",
  };
  const ticks = rows.slice(0, count).map((r) => ({
    time: r.tm ?? null,
    price: parseNumber(r.cur_prc),
    change: parseNumber(r.pred_pre),
    change_pct: parseNumber(r.pre_rt),
    qty: parseNumber(r.cntr_trde_qty),
    acc_volume: parseNumber(r.acc_trde_qty),
    acc_trade_value: parseNumber(r.acc_trde_prica),
    best_ask: parseNumber(r.pri_sel_bid_unit),
    best_bid: parseNumber(r.pri_buy_bid_unit),
    sign: signMap[String(r.sign ?? "")] ?? r.sign ?? null,
    strength: parseNumber(r.cntr_str),
  }));
  console.log(
    JSON.stringify(
      {
        ticker,
        count: ticks.length,
        ticks,
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
