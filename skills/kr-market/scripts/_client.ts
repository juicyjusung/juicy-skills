import { readFileSync, writeFileSync, existsSync, chmodSync, mkdirSync } from "node:fs";
import { dirname, join, resolve } from "node:path";

const BASE_URL = "https://api.kiwoom.com";
const TOKEN_PATH = resolveTokenPath();
const REFRESH_MARGIN_MS = 5 * 60 * 1000;

interface TokenCache {
  token: string;
  token_type: string;
  expires_dt: string;
  expires_at_ms: number;
}

interface TokenResponse {
  token: string;
  token_type: string;
  expires_dt: string;
  return_code: number;
  return_msg: string;
}

export interface RequestOptions {
  apiId: string;
  body: Record<string, unknown>;
  contYn?: "Y" | "N";
  nextKey?: string;
  path: string;
}

export interface ApiResponse<T = Record<string, unknown>> {
  data: T;
  headers: {
    contYn?: string;
    nextKey?: string;
    apiId?: string;
  };
  returnCode: number;
  returnMsg: string;
}

function resolveTokenPath(): string {
  const override = process.env.KIWOOM_TOKEN_PATH;
  if (override) return resolve(override);
  const cwd = process.cwd();
  return join(cwd, "stocks", ".kiwoom-token.json");
}

function projectRoot(): string {
  let dir = process.cwd();
  for (let i = 0; i < 6; i++) {
    if (existsSync(join(dir, ".env"))) return dir;
    const parent = dirname(dir);
    if (parent === dir) break;
    dir = parent;
  }
  return process.cwd();
}

function loadEnv(): void {
  if (process.env.KIWOOM_APP_KEY && process.env.KIWOOM_SECRET_KEY) return;
  const envPath = join(projectRoot(), ".env");
  if (!existsSync(envPath)) return;
  const raw = readFileSync(envPath, "utf8");
  for (const line of raw.split(/\r?\n/)) {
    const m = line.match(/^\s*([A-Z0-9_]+)\s*=\s*(.*?)\s*$/);
    if (!m) continue;
    const [, k, vRaw] = m;
    const v = vRaw.replace(/^["']|["']$/g, "");
    if (!process.env[k]) process.env[k] = v;
  }
}

function parseExpiresDt(s: string): number {
  // Format observed: "YYYYMMDDHHMMSS" or "YYYYMMDDTHHMMSS"
  const cleaned = s.replace(/[^0-9]/g, "");
  if (cleaned.length < 14) return Date.now() + 60 * 60 * 1000;
  const y = +cleaned.slice(0, 4);
  const mo = +cleaned.slice(4, 6) - 1;
  const d = +cleaned.slice(6, 8);
  const h = +cleaned.slice(8, 10);
  const mi = +cleaned.slice(10, 12);
  const se = +cleaned.slice(12, 14);
  return new Date(y, mo, d, h, mi, se).getTime();
}

function readCache(): TokenCache | null {
  if (!existsSync(TOKEN_PATH)) return null;
  try {
    const c = JSON.parse(readFileSync(TOKEN_PATH, "utf8")) as TokenCache;
    if (!c.token || !c.expires_at_ms) return null;
    return c;
  } catch {
    return null;
  }
}

function writeCache(c: TokenCache): void {
  mkdirSync(dirname(TOKEN_PATH), { recursive: true });
  writeFileSync(TOKEN_PATH, JSON.stringify(c, null, 2));
  try {
    chmodSync(TOKEN_PATH, 0o600);
  } catch {}
}

async function issueToken(): Promise<TokenCache> {
  loadEnv();
  const appkey = process.env.KIWOOM_APP_KEY;
  const secretkey = process.env.KIWOOM_SECRET_KEY;
  if (!appkey || !secretkey) {
    throw new Error("KIWOOM_APP_KEY/KIWOOM_SECRET_KEY missing in .env");
  }
  const res = await fetch(`${BASE_URL}/oauth2/token`, {
    method: "POST",
    headers: { "Content-Type": "application/json;charset=UTF-8" },
    body: JSON.stringify({ grant_type: "client_credentials", appkey, secretkey }),
  });
  const txt = await res.text();
  let json: TokenResponse;
  try {
    json = JSON.parse(txt) as TokenResponse;
  } catch {
    throw new Error(`token endpoint non-JSON response (status=${res.status}): ${txt.slice(0, 200)}`);
  }
  if (json.return_code !== 0 || !json.token) {
    throw new Error(`token issue failed: ${json.return_code} ${json.return_msg}`);
  }
  const cache: TokenCache = {
    token: json.token,
    token_type: json.token_type,
    expires_dt: json.expires_dt,
    expires_at_ms: parseExpiresDt(json.expires_dt),
  };
  writeCache(cache);
  return cache;
}

export async function getToken(force = false): Promise<string> {
  if (!force) {
    const c = readCache();
    if (c && c.expires_at_ms - REFRESH_MARGIN_MS > Date.now()) return c.token;
  }
  const fresh = await issueToken();
  return fresh.token;
}

export async function revokeToken(): Promise<void> {
  loadEnv();
  const cache = readCache();
  if (!cache) return;
  const appkey = process.env.KIWOOM_APP_KEY;
  const secretkey = process.env.KIWOOM_SECRET_KEY;
  if (!appkey || !secretkey) return;
  await fetch(`${BASE_URL}/oauth2/revoke`, {
    method: "POST",
    headers: { "Content-Type": "application/json;charset=UTF-8" },
    body: JSON.stringify({ appkey, secretkey, token: cache.token }),
  });
}

export async function callApi<T = Record<string, unknown>>(
  opts: RequestOptions,
): Promise<ApiResponse<T>> {
  const token = await getToken();
  const headers: Record<string, string> = {
    "Content-Type": "application/json;charset=UTF-8",
    authorization: `Bearer ${token}`,
    "api-id": opts.apiId,
  };
  if (opts.contYn) headers["cont-yn"] = opts.contYn;
  if (opts.nextKey) headers["next-key"] = opts.nextKey;

  const url = `${BASE_URL}${opts.path}`;
  const res = await fetchWithRetry(url, {
    method: "POST",
    headers,
    body: JSON.stringify(opts.body),
  });
  const txt = await res.text();
  let data: Record<string, unknown>;
  try {
    data = JSON.parse(txt);
  } catch {
    throw new Error(`non-JSON response (status=${res.status}): ${txt.slice(0, 200)}`);
  }
  const returnCode = typeof data.return_code === "number" ? data.return_code : -1;
  const returnMsg = String(data.return_msg ?? "");
  if (returnCode !== 0) {
    throw new Error(`api ${opts.apiId} failed: ${returnCode} ${returnMsg}`);
  }
  return {
    data: data as T,
    headers: {
      contYn: res.headers.get("cont-yn") ?? undefined,
      nextKey: res.headers.get("next-key") ?? undefined,
      apiId: res.headers.get("api-id") ?? undefined,
    },
    returnCode,
    returnMsg,
  };
}

async function fetchWithRetry(url: string, init: RequestInit): Promise<Response> {
  const delays = [0, 1000, 2000, 4000];
  let lastErr: unknown;
  for (const d of delays) {
    if (d > 0) await sleep(d);
    try {
      const res = await fetch(url, init);
      if (res.status === 429 || res.status >= 500) {
        lastErr = new Error(`http ${res.status}`);
        continue;
      }
      return res;
    } catch (e) {
      lastErr = e;
    }
  }
  throw lastErr instanceof Error ? lastErr : new Error("fetch failed");
}

function sleep(ms: number): Promise<void> {
  return new Promise((r) => setTimeout(r, ms));
}

export function parseNumber(v: unknown): number | null {
  if (v == null) return null;
  const s = String(v).trim().replace(/^[+\-]+/, (m) => (m.includes("-") ? "-" : ""));
  if (s === "" || s === "-") return null;
  const n = Number(s);
  return Number.isFinite(n) ? n : null;
}
