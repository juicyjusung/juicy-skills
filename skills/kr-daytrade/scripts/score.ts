#!/usr/bin/env bun
import { readFileSync } from "node:fs";
import { roundToTick, tickSize, type RoundMode } from "./tick-size.ts";

type RiskMode = "conservative" | "balanced" | "aggressive";
type TradeStyle = "auto" | "scalp" | "daytrade" | "breakout" | "pullback";
type Strength = "strong" | "medium" | "weak";

interface Candle {
  date?: string | number | null;
  open?: number | null;
  high?: number | null;
  low?: number | null;
  close?: number | null;
  volume?: number | null;
}

interface Level {
  price?: number | null;
  qty?: number | null;
}

interface Gate {
  code: string;
  severity: "block" | "warn";
  message: string;
}

interface PricePlan {
  reference: number;
  current: number;
  stop: number | null;
  target1: number | null;
  target2: number | null;
  risk_per_share: number | null;
  rr1: number | null;
  rr2: number | null;
}

const RISK: Record<RiskMode, { maxStopPct: number; minRr1: number }> = {
  conservative: { maxStopPct: 0.01, minRr1: 1.8 },
  balanced: { maxStopPct: 0.018, minRr1: 1.5 },
  aggressive: { maxStopPct: 0.025, minRr1: 1.3 },
};

function parseFlags(args: string[]): Map<string, string> {
  const flags = new Map<string, string>();
  for (const arg of args) {
    const match = arg.match(/^--([a-z-]+)(?:=(.+))?$/);
    if (match) flags.set(match[1], match[2] ?? "true");
  }
  return flags;
}

function usage(): never {
  console.error(
    [
      "usage: bun score.ts --ticker=005930 --quote=quote.json --bars=bars.json --orderbook=orderbook.json --ticks=ticks.json",
      "       [--avg-price=72300] [--risk=balanced|conservative|aggressive] [--style=auto|scalp|daytrade|breakout|pullback]",
    ].join("\n"),
  );
  process.exit(1);
}

function readJson(path: string | undefined): unknown | null {
  if (!path) return null;
  return JSON.parse(readFileSync(path, "utf8"));
}

function num(value: unknown): number | null {
  if (typeof value === "number" && Number.isFinite(value)) return value;
  if (typeof value === "string") {
    const parsed = Number(value.replace(/[, +]/g, ""));
    return Number.isFinite(parsed) ? parsed : null;
  }
  return null;
}

function asArray(value: unknown): Array<Record<string, unknown>> {
  return Array.isArray(value) ? (value as Array<Record<string, unknown>>) : [];
}

function normalizeBars(raw: unknown): Candle[] {
  const rows = asArray((raw as Record<string, unknown> | null)?.candles);
  const candles = rows
    .map((row) => ({
      date: (row.date as string | number | null | undefined) ?? null,
      open: num(row.open),
      high: num(row.high),
      low: num(row.low),
      close: num(row.close),
      volume: num(row.volume),
    }))
    .filter((c) => c.high != null && c.low != null && c.close != null);

  const first = sortableDate(candles[0]?.date);
  const last = sortableDate(candles[candles.length - 1]?.date);
  if (first != null && last != null && first > last) candles.reverse();
  return candles;
}

function sortableDate(value: string | number | null | undefined): number | null {
  if (value == null) return null;
  const parsed = Number(String(value).replace(/\D/g, ""));
  return Number.isFinite(parsed) ? parsed : null;
}

function avg(values: number[]): number | null {
  const usable = values.filter((v) => Number.isFinite(v));
  if (!usable.length) return null;
  return usable.reduce((sum, value) => sum + value, 0) / usable.length;
}

function min(values: Array<number | null | undefined>): number | null {
  const usable = values.filter((v): v is number => typeof v === "number" && Number.isFinite(v));
  return usable.length ? Math.min(...usable) : null;
}

function max(values: Array<number | null | undefined>): number | null {
  const usable = values.filter((v): v is number => typeof v === "number" && Number.isFinite(v));
  return usable.length ? Math.max(...usable) : null;
}

function calcVwap(candles: Candle[]): number | null {
  let pv = 0;
  let volume = 0;
  for (const c of candles) {
    if (c.high == null || c.low == null || c.close == null || c.volume == null || c.volume <= 0) continue;
    const typical = (c.high + c.low + c.close) / 3;
    pv += typical * c.volume;
    volume += c.volume;
  }
  return volume > 0 ? pv / volume : null;
}

function bestLevels(raw: unknown): { bestAsk: Level | null; bestBid: Level | null; totalAsk: number | null; totalBid: number | null } {
  const obj = (raw ?? {}) as Record<string, unknown>;
  const asks = asArray(obj.asks);
  const bids = asArray(obj.bids);
  return {
    bestAsk: (asks.find((a) => num(a.price) != null) as Level | undefined) ?? null,
    bestBid: (bids.find((b) => num(b.price) != null) as Level | undefined) ?? null,
    totalAsk: num(obj.total_ask_qty) ?? sumQty(asks),
    totalBid: num(obj.total_bid_qty) ?? sumQty(bids),
  };
}

function sumQty(levels: Array<Record<string, unknown>>): number | null {
  const total = levels.reduce((sum, level) => sum + (num(level.qty) ?? 0), 0);
  return total > 0 ? total : null;
}

function tickStrength(raw: unknown): number | null {
  const ticks = asArray((raw as Record<string, unknown> | null)?.ticks);
  const strengths = ticks.map((tick) => num(tick.strength)).filter((v): v is number => v != null);
  return avg(strengths);
}

function classifyStrength(score: number, gates: Gate[]): Strength {
  if (gates.some((gate) => gate.severity === "block")) return "weak";
  if (score >= 70) return "strong";
  if (score >= 50) return "medium";
  return "weak";
}

function roundMaybe(price: number | null, mode: RoundMode): number | null {
  return price == null || price <= 0 ? null : roundToTick(price, mode);
}

function pct(a: number, b: number): number {
  return b === 0 ? 0 : (a - b) / b;
}

const flags = parseFlags(process.argv.slice(2));
const ticker = flags.get("ticker");
if (!ticker) usage();

const riskMode = (flags.get("risk") ?? "balanced") as RiskMode;
if (!Object.keys(RISK).includes(riskMode)) throw new Error(`bad --risk: ${riskMode}`);
const style = (flags.get("style") ?? "auto") as TradeStyle;
if (!["auto", "scalp", "daytrade", "breakout", "pullback"].includes(style)) throw new Error(`bad --style: ${style}`);

const avgPrice = num(flags.get("avg-price"));
const mode = avgPrice != null ? "holding_management" : "new_entry";
const quote = (readJson(flags.get("quote")) ?? {}) as Record<string, unknown>;
const barsRaw = readJson(flags.get("bars"));
const orderbookRaw = readJson(flags.get("orderbook"));
const ticksRaw = readJson(flags.get("ticks"));

const current = num(quote.current_price);
const quoteTime = (quote.timestamp ?? quote.as_of ?? null) as string | null;
const candles = normalizeBars(barsRaw);
const recent = candles.slice(-12);
const prior = candles.slice(-32, -1);
const latest = candles[candles.length - 1];
const vwap = calcVwap(candles);
const recentLow = min(recent.map((c) => c.low));
const recentHigh = max(recent.map((c) => c.high));
const priorHigh = max(prior.map((c) => c.high));
const avgVolume = avg(prior.map((c) => c.volume ?? 0).filter((v) => v > 0));
const levels = bestLevels(orderbookRaw);
const bestAsk = num(levels.bestAsk?.price);
const bestBid = num(levels.bestBid?.price);
const bidAskRatio = levels.totalAsk && levels.totalBid ? levels.totalBid / levels.totalAsk : null;
const strength = tickStrength(ticksRaw);
const tickCount = asArray((ticksRaw as Record<string, unknown> | null)?.ticks).length;
const spreadTicks =
  current != null && bestAsk != null && bestBid != null ? (bestAsk - bestBid) / tickSize(current) : null;

const gates: Gate[] = [];
if (current == null) gates.push({ code: "missing_quote", severity: "block", message: "현재가 데이터가 없습니다." });
if (candles.length < 20) gates.push({ code: "insufficient_bars", severity: "block", message: "분봉 데이터가 20개 미만입니다." });
if (tickCount < 5) gates.push({ code: "insufficient_ticks", severity: "block", message: "최근 체결 데이터가 부족합니다." });
if (bestAsk == null || bestBid == null) gates.push({ code: "missing_orderbook", severity: "block", message: "호가 데이터가 없습니다." });
if (spreadTicks != null && spreadTicks > 3) {
  gates.push({ code: "wide_spread", severity: "block", message: `호가 공백이 ${spreadTicks.toFixed(1)}틱으로 넓습니다.` });
}

let score = 50;
const setup: Array<{ name: string; strength: Strength; reason: string }> = [];
const warnings: string[] = [];

if (current != null && vwap != null) {
  if (current > vwap) score += 12;
  else score -= 15;
}
if (avgVolume != null && latest?.volume != null) {
  const volumeRatio = latest.volume / avgVolume;
  if (volumeRatio >= 1.5) score += 14;
  else if (volumeRatio < 0.7) score -= 8;
}
if (strength != null) {
  if (strength >= 150) score += 10;
  else if (strength < 100) score -= 10;
}
if (bidAskRatio != null) {
  if (bidAskRatio >= 1.2) score += 8;
  else if (bidAskRatio <= 0.8) score -= 8;
}
if (spreadTicks != null && spreadTicks <= 1) score += 4;

const gapPct =
  num(quote.open) != null && num(quote.prev_close) != null
    ? pct(num(quote.open) as number, num(quote.prev_close) as number) * 100
    : null;
if (gapPct != null && gapPct >= 3 && current != null && vwap != null && current > vwap) {
  setup.push({ name: "gap", strength: "medium", reason: `시가 갭 ${gapPct.toFixed(1)}% 이후 VWAP 위` });
}
if (current != null && vwap != null && recentLow != null && current > vwap && recentLow >= vwap * 0.995) {
  setup.push({ name: "vwap_support", strength: "strong", reason: "현재가가 VWAP 위이고 최근 저점이 VWAP 부근을 지지" });
}
if (current != null && vwap != null && recentHigh != null && current > vwap && current < recentHigh * 0.995) {
  setup.push({ name: "pullback", strength: "medium", reason: "최근 고점 아래 눌림 구간이지만 VWAP 위" });
}
if (current != null && priorHigh != null && latest?.volume != null && avgVolume != null && current > priorHigh && latest.volume > avgVolume * 1.2) {
  setup.push({ name: "breakout", strength: "strong", reason: "직전 고점 돌파와 거래량 증가" });
}
if (strength != null && strength >= 150 && bidAskRatio != null && bidAskRatio >= 1.2 && spreadTicks != null && spreadTicks <= 2) {
  setup.push({ name: "scalping", strength: "medium", reason: "체결강도와 매수잔량이 우호적이고 스프레드가 좁음" });
}

const ref = current != null ? (avgPrice ?? current) : avgPrice;
let prices: PricePlan = {
  reference: ref ?? 0,
  current: current ?? 0,
  stop: null,
  target1: null,
  target2: null,
  risk_per_share: null,
  rr1: null,
  rr2: null,
};

if (current != null && ref != null && ref > 0) {
  const risk = RISK[riskMode];
  const fixedStop = ref * (1 - risk.maxStopPct);
  const structuralStops = [recentLow, vwap != null && current > vwap ? vwap * 0.997 : null, fixedStop]
    .filter((price): price is number => price != null && price > 0 && price < ref)
    .map((price) => roundToTick(price, "floor"))
    .sort((a, b) => b - a);
  const stop = structuralStops[0] ?? null;
  const riskPerShare = stop == null ? null : ref - stop;
  const stopPct = riskPerShare == null ? null : riskPerShare / ref;
  if (stopPct != null && stopPct > risk.maxStopPct) {
    gates.push({
      code: "excessive_stop_width",
      severity: mode === "new_entry" ? "block" : "warn",
      message: `손절폭 ${(stopPct * 100).toFixed(2)}%가 ${riskMode} 기준보다 큽니다.`,
    });
  }
  if (stop != null && current <= stop) {
    gates.push({ code: "below_invalidation", severity: "block", message: "현재가가 이미 무효화선 이하입니다." });
  }

  const targetByR = riskPerShare == null ? null : ref + riskPerShare * risk.minRr1;
  const resistance = [num(quote.high), recentHigh, priorHigh]
    .filter((price): price is number => price != null && price > ref)
    .sort((a, b) => a - b)[0];
  const target1Raw = resistance != null && targetByR != null && resistance < targetByR ? resistance : targetByR;
  const target2Raw = riskPerShare == null ? null : Math.max(ref + riskPerShare * 2, resistance ?? 0);
  const target1 = roundMaybe(target1Raw, "ceil");
  const target2 = roundMaybe(target2Raw, "ceil");
  const rr1 = target1 != null && riskPerShare != null && riskPerShare > 0 ? (target1 - ref) / riskPerShare : null;
  const rr2 = target2 != null && riskPerShare != null && riskPerShare > 0 ? (target2 - ref) / riskPerShare : null;
  if (rr1 != null && rr1 < risk.minRr1) {
    gates.push({
      code: "insufficient_rr",
      severity: mode === "new_entry" ? "block" : "warn",
      message: `1차 손익비 ${rr1.toFixed(2)}R가 ${riskMode} 기준 ${risk.minRr1}R보다 낮습니다.`,
    });
  }
  prices = {
    reference: roundToTick(ref, "nearest"),
    current: roundToTick(current, "nearest"),
    stop,
    target1,
    target2,
    risk_per_share: riskPerShare == null ? null : Math.round(riskPerShare),
    rr1: rr1 == null ? null : Number(rr1.toFixed(2)),
    rr2: rr2 == null ? null : Number(rr2.toFixed(2)),
  };
}

if (spreadTicks != null && spreadTicks > 1) warnings.push(`호가 공백이 ${spreadTicks.toFixed(1)}틱입니다.`);
if (strength != null && strength < 100) warnings.push("체결강도가 100 미만이라 매수 지속성이 약합니다.");
if (gapPct != null && gapPct >= 3 && !setup.some((s) => s.name === "vwap_support")) {
  warnings.push("갭상승 후 지지 확인이 약해 추격 진입 근거가 약합니다.");
}
if (!setup.length) warnings.push("명확한 VWAP, 눌림목, 돌파 셋업이 확인되지 않았습니다.");

const hasBlock = gates.some((gate) => gate.severity === "block");
score = Math.max(0, Math.min(100, Math.round(score)));
if (gates.some((gate) => ["missing_quote", "insufficient_bars", "insufficient_ticks", "missing_orderbook"].includes(gate.code))) {
  score = 0;
} else if (hasBlock) {
  score = Math.min(score, 49);
}

let status: string;
if (gates.some((gate) => ["missing_quote", "insufficient_bars", "insufficient_ticks", "missing_orderbook"].includes(gate.code))) {
  status = "data_insufficient";
} else if (mode === "holding_management" && hasBlock) {
  status = "defense_priority";
} else if (mode === "new_entry" && hasBlock) {
  status = "entry_hold";
} else if (mode === "holding_management") {
  status = "conditional_hold_plan";
} else {
  status = "conditional_entry_possible";
}

console.log(
  JSON.stringify(
    {
      ticker,
      mode,
      risk_mode: riskMode,
      trade_style: style,
      status,
      score,
      evidence_strength: classifyStrength(score, gates),
      as_of: quoteTime ?? new Date().toISOString(),
      indicators: {
        vwap: vwap == null ? null : Math.round(vwap),
        recent_low: recentLow == null ? null : roundToTick(recentLow, "floor"),
        recent_high: recentHigh == null ? null : roundToTick(recentHigh, "ceil"),
        prior_high: priorHigh == null ? null : roundToTick(priorHigh, "ceil"),
        avg_tick_strength: strength == null ? null : Number(strength.toFixed(1)),
        bid_ask_qty_ratio: bidAskRatio == null ? null : Number(bidAskRatio.toFixed(2)),
        spread_ticks: spreadTicks == null ? null : Number(spreadTicks.toFixed(1)),
      },
      setup,
      gates,
      prices,
      warnings,
    },
    null,
    2,
  ),
);
