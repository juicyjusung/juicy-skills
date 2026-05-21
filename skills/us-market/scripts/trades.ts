#!/usr/bin/env bun
import { AlpacaClient, num, parseFlags, toNyIso, validateSymbol, type Feed } from "./_client.ts";

const sym = process.argv[2]?.toUpperCase() ?? "";
if (!sym) {
  console.error("usage: bun trades.ts <SYMBOL> [--count=N] [--start=ISO] [--end=ISO] [--feed=...] [--page-token=...]");
  process.exit(1);
}

try {
  validateSymbol(sym);
  const flags = parseFlags(process.argv.slice(3));
  const count = Number(flags.get("count") ?? "100");
  if (!Number.isFinite(count) || count <= 0) throw new Error(`bad --count: ${flags.get("count")}`);

  const client = new AlpacaClient({ feed: flags.get("feed") as Feed | undefined });
  const { trades, next_page_token } = await client.getTrades(sym, {
    count,
    start: flags.get("start"),
    end: flags.get("end"),
    pageToken: flags.get("page-token"),
  });

  const out = {
    symbol: sym,
    feed: client.feed,
    trades: trades.map((t: any) => ({
      t: toNyIso(t.t),
      p: num(t.p),
      s: num(t.s),
      x: t.x ?? null,
      i: num(t.i),
      c: Array.isArray(t.c) ? t.c : null,
      z: t.z ?? null,
    })),
    next_page_token,
  };
  console.log(JSON.stringify(out, null, 2));
} catch (e) {
  console.error(e instanceof Error ? e.message : String(e));
  process.exit(1);
}
