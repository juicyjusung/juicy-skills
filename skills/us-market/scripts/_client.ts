import { readFileSync, existsSync } from "node:fs";
import { dirname, join } from "node:path";

const DATA_BASE = "https://data.alpaca.markets";
const SYMBOL_RX = /^[A-Z][A-Z0-9.\-]{0,9}$/;
const KR_TICKER_RX = /^\d{6}$/;

export type Feed = "iex" | "sip" | "delayed_sip";
const VALID_FEEDS: Feed[] = ["iex", "sip", "delayed_sip"];

export interface ClientOpts {
  feed?: Feed;
}

function findProjectRoot(): string {
  let dir = process.cwd();
  for (let i = 0; i < 8; i++) {
    if (existsSync(join(dir, ".env"))) return dir;
    const parent = dirname(dir);
    if (parent === dir) break;
    dir = parent;
  }
  return process.cwd();
}

function parseEnvFile(path: string): Record<string, string> {
  const out: Record<string, string> = {};
  if (!existsSync(path)) return out;
  const raw = readFileSync(path, "utf8");
  for (const line of raw.split(/\r?\n/)) {
    const trimmed = line.trim();
    if (!trimmed || trimmed.startsWith("#")) continue;
    const m = line.match(/^\s*([A-Z0-9_]+)\s*=\s*(.*?)\s*$/);
    if (!m) continue;
    const [, k, vRaw] = m;
    // Strip inline `# comment` only when value is not single/double-quoted.
    let v = vRaw;
    if (!/^["']/.test(v)) {
      const hashIdx = v.indexOf("#");
      if (hashIdx >= 0) v = v.slice(0, hashIdx).trim();
    }
    out[k] = v.replace(/^["']|["']$/g, "");
  }
  return out;
}

// Skill-local .env wins over project-root .env. Existing process.env wins over both.
function loadEnv(): void {
  const skillEnv = parseEnvFile(join(import.meta.dirname ?? "", "..", ".env"));
  const rootEnv = parseEnvFile(join(findProjectRoot(), ".env"));
  for (const k of Object.keys(rootEnv)) {
    if (!process.env[k]) process.env[k] = rootEnv[k];
  }
  for (const k of Object.keys(skillEnv)) {
    if (!process.env[k]) process.env[k] = skillEnv[k];
  }
}

function resolveFeed(override?: string): Feed {
  const cli = (override ?? "").trim();
  if (cli) {
    if (!VALID_FEEDS.includes(cli as Feed)) {
      throw new Error(`bad --feed: ${cli}. one of ${VALID_FEEDS.join("|")}`);
    }
    return cli as Feed;
  }
  const envRaw = (process.env.ALPACA_FEED ?? "").trim();
  if (envRaw) {
    const norm = envRaw === "sip-delayed" ? "delayed_sip" : envRaw;
    if (!VALID_FEEDS.includes(norm as Feed)) {
      throw new Error(`bad ALPACA_FEED: ${envRaw}. one of ${VALID_FEEDS.join("|")}`);
    }
    return norm as Feed;
  }
  return "delayed_sip";
}

export function validateSymbol(sym: string): void {
  if (KR_TICKER_RX.test(sym)) {
    throw new Error(`'${sym}' looks like a 6-digit Korean ticker. Use the kr-market skill for KOSPI/KOSDAQ.`);
  }
  if (!SYMBOL_RX.test(sym)) {
    throw new Error(`invalid US symbol '${sym}'. expected uppercase ticker like AAPL, BRK.B`);
  }
}

export function num(v: unknown): number | null {
  if (v == null) return null;
  if (typeof v === "number") return Number.isFinite(v) ? v : null;
  const s = String(v).trim();
  if (s === "" || s === "-") return null;
  const n = Number(s);
  return Number.isFinite(n) ? n : null;
}

export function toNyIso(ts: unknown): string | null {
  if (ts == null) return null;
  const d = ts instanceof Date ? ts : new Date(String(ts));
  if (Number.isNaN(d.getTime())) return null;
  // Build YYYY-MM-DDTHH:mm:ss with America/New_York offset.
  const fmt = new Intl.DateTimeFormat("en-US", {
    timeZone: "America/New_York",
    year: "numeric", month: "2-digit", day: "2-digit",
    hour: "2-digit", minute: "2-digit", second: "2-digit",
    hour12: false,
    timeZoneName: "shortOffset",
  });
  const parts = fmt.formatToParts(d);
  const get = (t: string) => parts.find((p) => p.type === t)?.value ?? "";
  const yyyy = get("year"), mm = get("month"), dd = get("day");
  const hh = get("hour") === "24" ? "00" : get("hour");
  const mi = get("minute"), ss = get("second");
  const tzn = get("timeZoneName"); // "GMT-4" or "GMT-5"
  const offMatch = tzn.match(/GMT([+-])(\d{1,2})(?::?(\d{2}))?/);
  const sign = offMatch?.[1] ?? "+";
  const offH = (offMatch?.[2] ?? "0").padStart(2, "0");
  const offM = offMatch?.[3] ?? "00";
  return `${yyyy}-${mm}-${dd}T${hh}:${mi}:${ss}${sign}${offH}:${offM}`;
}

async function sleep(ms: number): Promise<void> {
  return new Promise((r) => setTimeout(r, ms));
}

async function fetchWithRetry(url: string, init: RequestInit): Promise<Response> {
  const delays = [0, 1000, 2000, 4000];
  let lastErr: unknown;
  for (const d of delays) {
    if (d > 0) await sleep(d);
    try {
      const res = await fetch(url, init);
      if (res.status === 429 || res.status >= 500) {
        lastErr = new Error(`http ${res.status} ${res.statusText}`);
        continue;
      }
      return res;
    } catch (e) {
      lastErr = e;
    }
  }
  throw lastErr instanceof Error ? lastErr : new Error("fetch failed");
}

export interface BarsOpts {
  interval: string;
  count?: number;
  start?: string;
  end?: string;
  pageToken?: string;
}

export interface TradesOpts {
  count?: number;
  start?: string;
  end?: string;
  pageToken?: string;
}

export interface NewsOpts {
  symbols?: string[];
  count?: number;
  start?: string;
  end?: string;
  pageToken?: string;
}

export interface ActionsOpts {
  symbol: string;
  types?: string[];
  start?: string;
  end?: string;
}

export class AlpacaClient {
  feed: Feed;
  private keyId: string;
  private secret: string;

  constructor(opts: ClientOpts = {}) {
    loadEnv();
    const keyId = process.env.APCA_API_KEY_ID;
    const secret = process.env.APCA_API_SECRET_KEY;
    if (!keyId || !secret) {
      throw new Error("Missing APCA_API_KEY_ID/APCA_API_SECRET_KEY. Add to .env or environment.");
    }
    this.keyId = keyId;
    this.secret = secret;
    this.feed = resolveFeed(opts.feed);
  }

  private headers(): Record<string, string> {
    return {
      "APCA-API-KEY-ID": this.keyId,
      "APCA-API-SECRET-KEY": this.secret,
      accept: "application/json",
    };
  }

  async rawGet<T = any>(path: string, query: Record<string, string | number | undefined> = {}): Promise<T> {
    const url = new URL(path, DATA_BASE);
    for (const [k, v] of Object.entries(query)) {
      if (v == null || v === "") continue;
      url.searchParams.set(k, String(v));
    }
    const res = await fetchWithRetry(url.toString(), { method: "GET", headers: this.headers() });
    const txt = await res.text();
    if (!res.ok) {
      throw new Error(`alpaca ${res.status} ${res.statusText}: ${txt.slice(0, 300)}`);
    }
    try {
      return JSON.parse(txt) as T;
    } catch {
      throw new Error(`non-JSON response: ${txt.slice(0, 200)}`);
    }
  }

  // ---- SDK-backed (with raw-fetch fallback to honor feed param) ----

  async getLatestQuote(symbol: string): Promise<any> {
    return this.rawGet<{ quote: any; symbol: string }>(
      `/v2/stocks/${encodeURIComponent(symbol)}/quotes/latest`,
      { feed: this.feed },
    );
  }

  async getLatestTrade(symbol: string): Promise<any> {
    return this.rawGet<{ trade: any; symbol: string }>(
      `/v2/stocks/${encodeURIComponent(symbol)}/trades/latest`,
      { feed: this.feed },
    );
  }

  async getSnapshot(symbol: string): Promise<any> {
    return this.rawGet<any>(`/v2/stocks/${encodeURIComponent(symbol)}/snapshot`, { feed: this.feed });
  }

  // Alpaca historical bars/trades endpoints reject `feed=delayed_sip` directly.
  // Free-plan users access delayed SIP data by sending `feed=sip`, but Alpaca
  // rejects any query touching the most recent 15 minutes (403 "subscription does
  // not permit querying recent SIP data"). We clamp `end` to ~16 minutes ago when
  // the caller didn't specify one, and the feed is delayed_sip.
  private feedForHistorical(): string {
    return this.feed === "delayed_sip" ? "sip" : this.feed;
  }

  private defaultEnd(userEnd: string | undefined): string | undefined {
    if (userEnd) return userEnd;
    if (this.feed !== "delayed_sip") return undefined;
    const t = new Date(Date.now() - 16 * 60 * 1000);
    return t.toISOString();
  }

  // Daily/weekly intervals default to ~90 days back; intraday to ~7 days back.
  // Without `start`, Alpaca returns nothing — these defaults give a useful window.
  private defaultStart(userStart: string | undefined, interval?: string): string | undefined {
    if (userStart) return userStart;
    const isIntraday = !!interval && /Min$|Hour$/.test(interval);
    const daysBack = isIntraday ? 7 : 90;
    return new Date(Date.now() - daysBack * 24 * 60 * 60 * 1000).toISOString();
  }

  async getBars(symbol: string, opts: BarsOpts): Promise<{ bars: any[]; next_page_token: string | null }> {
    const collected: any[] = [];
    let pageToken: string | undefined = opts.pageToken;
    const target = opts.count ?? 100;
    do {
      const limit = Math.min(1000, Math.max(1, target - collected.length));
      const page = await this.rawGet<{ bars: any[]; next_page_token: string | null }>(
        `/v2/stocks/${encodeURIComponent(symbol)}/bars`,
        {
          timeframe: opts.interval,
          start: this.defaultStart(opts.start, opts.interval),
          end: this.defaultEnd(opts.end),
          limit,
          adjustment: "raw",
          feed: this.feedForHistorical(),
          sort: "desc",
          page_token: pageToken,
        },
      );
      if (Array.isArray(page.bars)) collected.push(...page.bars);
      pageToken = page.next_page_token ?? undefined;
      if (collected.length >= target) break;
    } while (pageToken);
    return { bars: collected.slice(0, target), next_page_token: pageToken ?? null };
  }

  async getTrades(symbol: string, opts: TradesOpts): Promise<{ trades: any[]; next_page_token: string | null }> {
    const collected: any[] = [];
    let pageToken: string | undefined = opts.pageToken;
    const target = opts.count ?? 100;
    do {
      const limit = Math.min(10000, Math.max(1, target - collected.length));
      const page = await this.rawGet<{ trades: any[]; next_page_token: string | null }>(
        `/v2/stocks/${encodeURIComponent(symbol)}/trades`,
        {
          start: this.defaultStart(opts.start, "1Min"),
          end: this.defaultEnd(opts.end),
          limit,
          feed: this.feedForHistorical(),
          sort: "desc",
          page_token: pageToken,
        },
      );
      if (Array.isArray(page.trades)) collected.push(...page.trades);
      pageToken = page.next_page_token ?? undefined;
      if (collected.length >= target) break;
    } while (pageToken);
    return { trades: collected.slice(0, target), next_page_token: pageToken ?? null };
  }

  // ---- raw-fetch only (v1beta1 / v1) ----

  async getScreener(by: "most-actives" | "gainers" | "losers", top = 10): Promise<any> {
    const map = {
      "most-actives": "/v1beta1/screener/stocks/most-actives",
      gainers: "/v1beta1/screener/stocks/movers",
      losers: "/v1beta1/screener/stocks/movers",
    } as const;
    const path = map[by];
    const query: Record<string, string | number> = { top };
    return this.rawGet<any>(path, query);
  }

  async getNews(opts: NewsOpts): Promise<{ news: any[]; next_page_token: string | null }> {
    const collected: any[] = [];
    let pageToken: string | undefined = opts.pageToken;
    const target = opts.count ?? 25;
    do {
      const limit = Math.min(50, Math.max(1, target - collected.length));
      const page = await this.rawGet<{ news: any[]; next_page_token: string | null }>(
        "/v1beta1/news",
        {
          symbols: opts.symbols?.join(","),
          start: opts.start,
          end: opts.end,
          limit,
          sort: "desc",
          page_token: pageToken,
        },
      );
      if (Array.isArray(page.news)) collected.push(...page.news);
      pageToken = page.next_page_token ?? undefined;
      if (collected.length >= target) break;
    } while (pageToken);
    return { news: collected.slice(0, target), next_page_token: pageToken ?? null };
  }

  async getCorporateActions(opts: ActionsOpts): Promise<any> {
    const types = (opts.types && opts.types.length > 0) ? opts.types.join(",") : "forward_split,reverse_split,cash_dividend,stock_dividend";
    return this.rawGet<any>("/v1/corporate-actions", {
      symbols: opts.symbol,
      types,
      start: opts.start,
      end: opts.end,
    });
  }
}

export function parseFlags(argv: string[]): Map<string, string> {
  const flags = new Map<string, string>();
  for (const a of argv) {
    const m = a.match(/^--([a-z][a-z0-9-]*)=(.*)$/);
    if (m) flags.set(m[1], m[2]);
  }
  return flags;
}
