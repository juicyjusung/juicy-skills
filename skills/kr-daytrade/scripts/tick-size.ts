#!/usr/bin/env bun

export type RoundMode = "nearest" | "floor" | "ceil";

export function tickSize(price: number): number {
  assertPositivePrice(price);
  if (price < 2_000) return 1;
  if (price < 5_000) return 5;
  if (price < 20_000) return 10;
  if (price < 50_000) return 50;
  if (price < 200_000) return 100;
  if (price < 500_000) return 500;
  return 1_000;
}

export function roundToTick(price: number, mode: RoundMode = "nearest"): number {
  assertPositivePrice(price);
  const unit = tickSize(price);
  const scaled = price / unit;
  if (mode === "floor") return Math.floor(scaled) * unit;
  if (mode === "ceil") return Math.ceil(scaled) * unit;
  return Math.round(scaled) * unit;
}

function assertPositivePrice(price: number): void {
  if (!Number.isFinite(price) || price <= 0) {
    throw new Error(`price must be a positive number: ${price}`);
  }
}

function usage(): never {
  console.error("usage: bun tick-size.ts <price> [--mode=nearest|floor|ceil]");
  process.exit(1);
}

function parseMode(raw: string | undefined): RoundMode {
  const mode = raw ?? "nearest";
  if (mode === "nearest" || mode === "floor" || mode === "ceil") return mode;
  throw new Error(`bad --mode: ${mode}`);
}

if (import.meta.main) {
  try {
    const rawPrice = process.argv[2];
    if (!rawPrice) usage();
    const price = Number(rawPrice.replace(/,/g, ""));
    const flags = new Map<string, string>();
    for (const arg of process.argv.slice(3)) {
      const match = arg.match(/^--([a-z-]+)=(.+)$/);
      if (match) flags.set(match[1], match[2]);
    }
    const mode = parseMode(flags.get("mode"));
    console.log(
      JSON.stringify(
        {
          price,
          tick_size: tickSize(price),
          mode,
          rounded: roundToTick(price, mode),
        },
        null,
        2,
      ),
    );
  } catch (error) {
    console.error(error instanceof Error ? error.message : String(error));
    process.exit(1);
  }
}
