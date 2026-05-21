#!/usr/bin/env bun
import { AlpacaClient, num, parseFlags, toNyIso, type Feed } from "./_client.ts";

const VALID_BY = ["most-actives", "gainers", "losers"] as const;
type By = (typeof VALID_BY)[number];

try {
  const flags = parseFlags(process.argv.slice(2));
  const by = flags.get("by") as By | undefined;
  if (!by || !VALID_BY.includes(by)) {
    console.error(`usage: bun screener.ts --by=most-actives|gainers|losers [--top=10] [--feed=...]`);
    process.exit(1);
  }
  const top = Number(flags.get("top") ?? "10");
  if (!Number.isFinite(top) || top <= 0 || top > 50) {
    throw new Error(`bad --top: ${flags.get("top")} (1-50)`);
  }

  const client = new AlpacaClient({ feed: flags.get("feed") as Feed | undefined });
  const raw: any = await client.getScreener(by, top);

  // most-actives: { most_actives: [...], last_updated }
  // movers:       { gainers: [...], losers: [...], last_updated, market_type }
  let pool: any[] = [];
  if (by === "most-actives") {
    pool = raw.most_actives ?? [];
  } else if (by === "gainers") {
    pool = raw.gainers ?? [];
  } else {
    pool = raw.losers ?? [];
  }

  const items = pool.slice(0, top).map((r: any) => ({
    symbol: r.symbol ?? null,
    volume: num(r.volume),
    trade_count: num(r.trade_count),
    price: num(r.price),
    change: num(r.change),
    change_pct: num(r.percent_change ?? r.change_percent),
  }));

  const out = {
    by,
    as_of: toNyIso(raw.last_updated) ?? new Date().toISOString().replace("Z", "+00:00"),
    items,
  };
  console.log(JSON.stringify(out, null, 2));
} catch (e) {
  console.error(e instanceof Error ? e.message : String(e));
  process.exit(1);
}
