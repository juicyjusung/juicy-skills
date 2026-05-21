#!/usr/bin/env bun
import { AlpacaClient, num, parseFlags, toNyIso, validateSymbol, type Feed } from "./_client.ts";

const VALID_INTERVALS = ["1Min", "5Min", "15Min", "30Min", "1Hour", "1Day", "1Week", "1Month"];

const sym = process.argv[2]?.toUpperCase() ?? "";
if (!sym) {
  console.error("usage: bun bars.ts <SYMBOL> [--interval=1Min|5Min|15Min|30Min|1Hour|1Day|1Week|1Month] [--count=N] [--start=ISO] [--end=ISO] [--feed=...] [--page-token=...]");
  process.exit(1);
}

try {
  validateSymbol(sym);
  const flags = parseFlags(process.argv.slice(3));
  const interval = flags.get("interval") ?? "1Day";
  if (!VALID_INTERVALS.includes(interval)) {
    throw new Error(`bad --interval: ${interval}. one of ${VALID_INTERVALS.join("|")}`);
  }
  const count = Number(flags.get("count") ?? "100");
  if (!Number.isFinite(count) || count <= 0) throw new Error(`bad --count: ${flags.get("count")}`);

  const client = new AlpacaClient({ feed: flags.get("feed") as Feed | undefined });
  const { bars, next_page_token } = await client.getBars(sym, {
    interval,
    count,
    start: flags.get("start"),
    end: flags.get("end"),
    pageToken: flags.get("page-token"),
  });

  const out = {
    symbol: sym,
    interval,
    feed: client.feed,
    bars: bars.map((b: any) => ({
      t: toNyIso(b.t),
      o: num(b.o),
      h: num(b.h),
      l: num(b.l),
      c: num(b.c),
      v: num(b.v),
      n: num(b.n),
      vw: num(b.vw),
    })),
    next_page_token,
  };
  console.log(JSON.stringify(out, null, 2));
} catch (e) {
  console.error(e instanceof Error ? e.message : String(e));
  process.exit(1);
}
