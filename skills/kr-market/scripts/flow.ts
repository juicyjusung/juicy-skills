#!/usr/bin/env bun
import { callApi, parseNumber } from "./_client.ts";

type FlowType = "trader" | "foreign" | "inst";

const ticker = process.argv[2];
const flags = new Map<string, string>();
for (const a of process.argv.slice(3)) {
  const m = a.match(/^--([a-z-]+)=(.+)$/);
  if (m) flags.set(m[1], m[2]);
}
const type = (flags.get("type") ?? "trader") as FlowType;
const count = Number(flags.get("count") ?? "30");

if (!ticker || !/^\d{6}$/.test(ticker)) {
  console.error(
    "usage: bun flow.ts <6-digit-ticker> [--type=trader|foreign|inst] [--count=N]",
  );
  process.exit(1);
}
if (!["trader", "foreign", "inst"].includes(type)) {
  console.error(`bad --type: ${type}`);
  process.exit(1);
}

function spec(t: FlowType): { apiId: string; path: string } {
  switch (t) {
    case "trader":
      return { apiId: "ka10040", path: "/api/dostk/rkinfo" };
    case "foreign":
      return { apiId: "ka10008", path: "/api/dostk/frgnistt" };
    case "inst":
      return { apiId: "ka10009", path: "/api/dostk/frgnistt" };
  }
}

const { apiId, path } = spec(type);

try {
  const res = await callApi({
    apiId,
    path,
    body: { stk_cd: ticker },
  });
  const d = res.data as Record<string, unknown>;
  const rowsKey = Object.keys(d).find((k) => Array.isArray(d[k]));
  const rows = rowsKey ? ((d[rowsKey] as Array<Record<string, unknown>>) ?? []) : [];

  let items: Array<Record<string, unknown>>;
  if (type === "trader") {
    // ka10040 returns flat object with sel_trde_ori_<N> / buy_trde_ori_<N> for N=1..5
    items = [];
    for (let n = 1; n <= 5; n++) {
      const sellName = d[`sel_trde_ori_${n}`];
      const buyName = d[`buy_trde_ori_${n}`];
      if (!sellName && !buyName) continue;
      items.push({
        rank: n,
        sell_broker: sellName ?? null,
        sell_broker_code: d[`sel_trde_ori_cd_${n}`] ?? null,
        sell_qty: parseNumber(d[`sel_trde_ori_qty_${n}`]),
        sell_change: parseNumber(d[`sel_trde_ori_irds_${n}`]),
        buy_broker: buyName ?? null,
        buy_broker_code: d[`buy_trde_ori_cd_${n}`] ?? null,
        buy_qty: parseNumber(d[`buy_trde_ori_qty_${n}`]),
        buy_change: parseNumber(d[`buy_trde_ori_irds_${n}`]),
      });
    }
  } else {
    items = rows.slice(0, count).map((r) => ({
      date: r.dt ?? null,
      close: parseNumber(r.close_pric ?? r.cur_prc),
      change: parseNumber(r.pred_pre),
      change_pct: parseNumber(r.flu_rt ?? r.pred_pre_rt),
      volume: parseNumber(r.trde_qty),
      net_change: parseNumber(r.chg_qty),
      holding_qty: parseNumber(r.poss_stkcnt),
      holding_pct: parseNumber(r.wght ?? r.limit_exh_rt),
      acquirable_qty: parseNumber(r.gain_pos_stkcnt),
      limit_qty: parseNumber(r.frgnr_limit),
    }));
  }

  console.log(
    JSON.stringify(
      {
        ticker,
        type,
        tr: apiId,
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
