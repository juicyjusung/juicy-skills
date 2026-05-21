#!/usr/bin/env bun
import { callApi, parseNumber } from "./_client.ts";

const ticker = process.argv[2];
if (!ticker || !/^\d{6}$/.test(ticker)) {
  console.error("usage: bun orderbook.ts <6-digit-ticker>");
  process.exit(1);
}

try {
  const res = await callApi({
    apiId: "ka10004",
    path: "/api/dostk/mrkcond",
    body: { stk_cd: ticker },
  });
  const d = res.data as Record<string, unknown>;

  // Kiwoom ka10004 호가:
  //   Level 1 (best): sel_fpr_bid / sel_fpr_req / buy_fpr_bid / buy_fpr_req
  //   Level 2-10:     sel_<N>th_pre_bid / sel_<N>th_pre_req / buy_<N>th_pre_bid / buy_<N>th_pre_req
  const asks: Array<{ level: number; price: number | null; qty: number | null }> = [];
  const bids: Array<{ level: number; price: number | null; qty: number | null }> = [];
  for (let i = 1; i <= 10; i++) {
    const askPriceKey = i === 1 ? "sel_fpr_bid" : `sel_${i}th_pre_bid`;
    const askQtyKey = i === 1 ? "sel_fpr_req" : `sel_${i}th_pre_req`;
    const bidPriceKey = i === 1 ? "buy_fpr_bid" : `buy_${i}th_pre_bid`;
    const bidQtyKey = i === 1 ? "buy_fpr_req" : `buy_${i}th_pre_req`;
    asks.push({
      level: i,
      price: parseNumber(d[askPriceKey]),
      qty: parseNumber(d[askQtyKey]),
    });
    bids.push({
      level: i,
      price: parseNumber(d[bidPriceKey]),
      qty: parseNumber(d[bidQtyKey]),
    });
  }
  const out = {
    ticker,
    timestamp: d.bid_req_base_tm ?? null,
    asks: asks.filter((a) => a.price !== null || a.qty !== null),
    bids: bids.filter((b) => b.price !== null || b.qty !== null),
    total_ask_qty: parseNumber(d.tot_sel_req),
    total_bid_qty: parseNumber(d.tot_buy_req),
    raw: d,
  };
  console.log(JSON.stringify(out, null, 2));
} catch (e) {
  console.error(e instanceof Error ? e.message : String(e));
  process.exit(1);
}
