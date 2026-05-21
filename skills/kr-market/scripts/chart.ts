#!/usr/bin/env bun
import { callApi, parseNumber } from "./_client.ts";

interface Args {
  ticker: string;
  interval: "day" | "week" | "month" | "min";
  count: number;
  minUnit: string;
  baseDt: string;
}

function parseArgs(): Args {
  const ticker = process.argv[2];
  if (!ticker || !/^\d{6}$/.test(ticker)) {
    console.error("usage: bun chart.ts <6-digit-ticker> [--interval=day|week|month|min] [--count=N] [--min-unit=1|3|5|10|15|30|60] [--base-dt=YYYYMMDD]");
    process.exit(1);
  }
  const flags = new Map<string, string>();
  for (const a of process.argv.slice(3)) {
    const m = a.match(/^--([a-z-]+)=(.+)$/);
    if (m) flags.set(m[1], m[2]);
  }
  const interval = (flags.get("interval") ?? "day") as Args["interval"];
  if (!["day", "week", "month", "min"].includes(interval)) {
    console.error(`bad --interval: ${interval}`);
    process.exit(1);
  }
  const count = Number(flags.get("count") ?? "60");
  const minUnit = flags.get("min-unit") ?? "1";
  const today = new Date();
  const yyyymmdd = `${today.getFullYear()}${String(today.getMonth() + 1).padStart(2, "0")}${String(today.getDate()).padStart(2, "0")}`;
  const baseDt = flags.get("base-dt") ?? yyyymmdd;
  return { ticker, interval, count, minUnit, baseDt };
}

function trCodeFor(interval: Args["interval"]): { apiId: string; path: string } {
  // ka10081 일봉, ka10082 주봉, ka10083 월봉, ka10080 분봉 (Kiwoom 차트 TR)
  switch (interval) {
    case "day":
      return { apiId: "ka10081", path: "/api/dostk/chart" };
    case "week":
      return { apiId: "ka10082", path: "/api/dostk/chart" };
    case "month":
      return { apiId: "ka10083", path: "/api/dostk/chart" };
    case "min":
      return { apiId: "ka10080", path: "/api/dostk/chart" };
  }
}

function bodyFor(args: Args): Record<string, unknown> {
  if (args.interval === "min") {
    return {
      stk_cd: args.ticker,
      tic_scope: args.minUnit,
      upd_stkpc_tp: "1",
    };
  }
  return {
    stk_cd: args.ticker,
    base_dt: args.baseDt,
    upd_stkpc_tp: "1",
  };
}

const args = parseArgs();
const { apiId, path } = trCodeFor(args.interval);

try {
  const res = await callApi({
    apiId,
    path,
    body: bodyFor(args),
  });
  const d = res.data as Record<string, unknown>;
  const candidateKeys = [
    "stk_dt_pole_chart_qry",
    "stk_min_pole_chart_qry",
    "stk_week_pole_chart_qry",
    "stk_mont_pole_chart_qry",
  ];
  let rows: Array<Record<string, unknown>> = [];
  for (const k of candidateKeys) {
    if (Array.isArray(d[k])) {
      rows = d[k] as Array<Record<string, unknown>>;
      break;
    }
  }
  const candles = rows.slice(0, args.count).map((r) => ({
    date: r.dt ?? r.cntr_tm ?? null,
    open: parseNumber(r.open_pric),
    high: parseNumber(r.high_pric),
    low: parseNumber(r.low_pric),
    close: parseNumber(r.cur_prc),
    volume: parseNumber(r.trde_qty),
  }));
  const out = {
    ticker: args.ticker,
    interval: args.interval,
    count: candles.length,
    candles,
    cont_yn: res.headers.contYn ?? null,
    next_key: res.headers.nextKey ?? null,
  };
  console.log(JSON.stringify(out, null, 2));
} catch (e) {
  console.error(e instanceof Error ? e.message : String(e));
  process.exit(1);
}
