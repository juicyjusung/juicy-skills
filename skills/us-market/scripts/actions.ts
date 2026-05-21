#!/usr/bin/env bun
import { AlpacaClient, num, parseFlags, validateSymbol } from "./_client.ts";

const sym = process.argv[2]?.toUpperCase() ?? "";
if (!sym) {
  console.error("usage: bun actions.ts <SYMBOL> [--types=split,dividend] [--start=ISO] [--end=ISO]");
  process.exit(1);
}

const TYPE_MAP: Record<string, string[]> = {
  split: ["forward_split", "reverse_split"],
  dividend: ["cash_dividend", "stock_dividend"],
};

try {
  validateSymbol(sym);
  const flags = parseFlags(process.argv.slice(3));
  const typesRaw = flags.get("types");
  let alpacaTypes: string[] | undefined;
  if (typesRaw) {
    const requested = typesRaw.split(",").map((t) => t.trim()).filter(Boolean);
    alpacaTypes = [];
    for (const t of requested) {
      const mapped = TYPE_MAP[t];
      if (mapped) alpacaTypes.push(...mapped);
      else alpacaTypes.push(t);
    }
  }

  const client = new AlpacaClient();
  const res: any = await client.getCorporateActions({
    symbol: sym,
    types: alpacaTypes,
    start: flags.get("start"),
    end: flags.get("end"),
  });

  const ca = res.corporate_actions ?? {};
  const fSplits = Array.isArray(ca.forward_splits) ? ca.forward_splits : [];
  const rSplits = Array.isArray(ca.reverse_splits) ? ca.reverse_splits : [];
  const cashDivs = Array.isArray(ca.cash_dividends) ? ca.cash_dividends : [];
  const stockDivs = Array.isArray(ca.stock_dividends) ? ca.stock_dividends : [];

  const splits = [
    ...fSplits.map((s: any) => ({
      ex_date: s.ex_date ?? null,
      ratio: s.new_rate && s.old_rate ? `${s.new_rate}:${s.old_rate}` : null,
      payable_date: s.payable_date ?? null,
      type: "forward_split",
    })),
    ...rSplits.map((s: any) => ({
      ex_date: s.ex_date ?? null,
      ratio: s.new_rate && s.old_rate ? `${s.new_rate}:${s.old_rate}` : null,
      payable_date: s.payable_date ?? null,
      type: "reverse_split",
    })),
  ];

  const dividends = [
    ...cashDivs.map((d: any) => ({
      ex_date: d.ex_date ?? null,
      cash_amount: num(d.rate),
      record_date: d.record_date ?? null,
      pay_date: d.payable_date ?? null,
      type: "cash_dividend",
    })),
    ...stockDivs.map((d: any) => ({
      ex_date: d.ex_date ?? null,
      cash_amount: null,
      record_date: d.record_date ?? null,
      pay_date: d.payable_date ?? null,
      type: "stock_dividend",
    })),
  ];

  const out = { symbol: sym, splits, dividends };
  console.log(JSON.stringify(out, null, 2));
} catch (e) {
  console.error(e instanceof Error ? e.message : String(e));
  process.exit(1);
}
