#!/usr/bin/env bun
import { callApi, parseNumber } from "./_client.ts";

const ticker = process.argv[2];
if (!ticker || !/^\d{6}$/.test(ticker)) {
  console.error("usage: bun quote.ts <6-digit-ticker>");
  process.exit(1);
}

try {
  const res = await callApi({
    apiId: "ka10001",
    path: "/api/dostk/stkinfo",
    body: { stk_cd: ticker },
  });
  const d = res.data as Record<string, unknown>;
  const out = {
    ticker,
    name: d.stk_nm ?? null,
    current_price: parseNumber(d.cur_prc),
    change: parseNumber(d.pred_pre),
    change_pct: parseNumber(d.flu_rt),
    volume: parseNumber(d.trde_qty),
    open: parseNumber(d.open_pric),
    high: parseNumber(d.high_pric),
    low: parseNumber(d.low_pric),
    prev_close: parseNumber(d.base_pric),
    market_cap: parseNumber(d.mac),
    raw: d,
  };
  console.log(JSON.stringify(out, null, 2));
} catch (e) {
  console.error(e instanceof Error ? e.message : String(e));
  process.exit(1);
}
