#!/usr/bin/env bun
import { AlpacaClient, num, parseFlags, toNyIso, validateSymbol, type Feed } from "./_client.ts";

const sym = process.argv[2]?.toUpperCase() ?? "";
if (!sym) {
  console.error("usage: bun quote.ts <SYMBOL> [--type=quote|trade|snapshot] [--feed=iex|sip|delayed_sip]");
  process.exit(1);
}

try {
  validateSymbol(sym);
  const flags = parseFlags(process.argv.slice(3));
  const type = (flags.get("type") ?? "snapshot") as "quote" | "trade" | "snapshot";
  if (!["quote", "trade", "snapshot"].includes(type)) {
    throw new Error(`bad --type: ${type}`);
  }
  const client = new AlpacaClient({ feed: flags.get("feed") as Feed | undefined });

  const base = {
    symbol: sym,
    feed: client.feed,
    delayed: client.feed === "delayed_sip",
    as_of: new Date().toISOString().replace("Z", "+00:00"),
  };

  let out: Record<string, unknown>;
  if (type === "quote") {
    const r: any = await client.getLatestQuote(sym);
    const q = r.quote ?? {};
    out = {
      ...base,
      latest_quote: {
        bid: num(q.bp),
        bid_size: num(q.bs),
        ask: num(q.ap),
        ask_size: num(q.as),
        ts: toNyIso(q.t),
      },
    };
  } else if (type === "trade") {
    const r: any = await client.getLatestTrade(sym);
    const t = r.trade ?? {};
    out = {
      ...base,
      latest_trade: {
        price: num(t.p),
        size: num(t.s),
        ts: toNyIso(t.t),
      },
    };
  } else {
    const s: any = await client.getSnapshot(sym);
    const lq = s.latestQuote ?? {};
    const lt = s.latestTrade ?? {};
    const db = s.dailyBar ?? {};
    const pdb = s.prevDailyBar ?? {};
    const close = num(db.c);
    const prevClose = num(pdb.c);
    const change = close != null && prevClose != null ? close - prevClose : null;
    const changePct = change != null && prevClose ? (change / prevClose) * 100 : null;
    out = {
      ...base,
      latest_quote: {
        bid: num(lq.bp),
        bid_size: num(lq.bs),
        ask: num(lq.ap),
        ask_size: num(lq.as),
        ts: toNyIso(lq.t),
      },
      latest_trade: {
        price: num(lt.p),
        size: num(lt.s),
        ts: toNyIso(lt.t),
      },
      daily_bar: {
        o: num(db.o), h: num(db.h), l: num(db.l), c: num(db.c), v: num(db.v),
        ts: toNyIso(db.t),
      },
      prev_daily_bar: {
        o: num(pdb.o), h: num(pdb.h), l: num(pdb.l), c: num(pdb.c), v: num(pdb.v),
        ts: toNyIso(pdb.t),
      },
      change,
      change_pct: changePct,
    };
  }
  console.log(JSON.stringify(out, null, 2));
} catch (e) {
  console.error(e instanceof Error ? e.message : String(e));
  process.exit(1);
}
