#!/usr/bin/env bun
import { AlpacaClient, parseFlags, toNyIso } from "./_client.ts";

try {
  const flags = parseFlags(process.argv.slice(2));
  const symbolsRaw = flags.get("symbols");
  const symbols = symbolsRaw ? symbolsRaw.split(",").map((s) => s.trim().toUpperCase()).filter(Boolean) : undefined;
  const count = Number(flags.get("count") ?? "25");
  if (!Number.isFinite(count) || count <= 0) throw new Error(`bad --count: ${flags.get("count")}`);

  const client = new AlpacaClient();
  const { news, next_page_token } = await client.getNews({
    symbols,
    count,
    start: flags.get("start"),
    end: flags.get("end"),
    pageToken: flags.get("page-token"),
  });

  const items = news.map((n: any) => ({
    id: n.id ?? null,
    headline: n.headline ?? null,
    summary: n.summary ?? null,
    url: n.url ?? null,
    symbols: Array.isArray(n.symbols) ? n.symbols : null,
    source: n.source ?? null,
    author: n.author ?? null,
    created_at: toNyIso(n.created_at),
    updated_at: toNyIso(n.updated_at),
  }));

  const out = { items, next_page_token };
  console.log(JSON.stringify(out, null, 2));
} catch (e) {
  console.error(e instanceof Error ? e.message : String(e));
  process.exit(1);
}
