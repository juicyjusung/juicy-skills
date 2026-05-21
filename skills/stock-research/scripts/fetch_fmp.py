#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = [
#   "requests",
#   "python-dotenv",
# ]
# ///
"""Financial Modeling Prep (FMP) 미국 재무·밸류에이션 데이터 수집.

환경변수: FMP_API_KEY (필수)

사용:
    uv run --env-file .env $SKILL_DIR/scripts/fetch_fmp.py AAPL --section profile --out _evidence/fmp_profile.json
    uv run --env-file .env $SKILL_DIR/scripts/fetch_fmp.py AAPL --section financials --out _evidence/fmp_financials.json
    uv run --env-file .env $SKILL_DIR/scripts/fetch_fmp.py AAPL --section ratios --out _evidence/fmp_ratios.json
    uv run --env-file .env $SKILL_DIR/scripts/fetch_fmp.py AAPL --section valuation --out _evidence/fmp_val.json
    uv run --env-file .env $SKILL_DIR/scripts/fetch_fmp.py AAPL --section peers --out _evidence/fmp_peers.json
    uv run --env-file .env $SKILL_DIR/scripts/fetch_fmp.py AAPL --section peer-valuations --symbols MSFT,GOOGL,META --out _evidence/fmp_peer_vals.json
    uv run --env-file .env $SKILL_DIR/scripts/fetch_fmp.py AAPL --section estimates --out _evidence/fmp_est.json

무료 티어 한도: 250/일. Endpoint: /stable/ (2024년 이후 신규 키 호환).
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import sys
from pathlib import Path
from typing import Any

import requests

try:
    from dotenv import load_dotenv

    load_dotenv()
except ImportError:
    pass

BASE = "https://financialmodelingprep.com/stable"


def _key() -> str:
    k = os.environ.get("FMP_API_KEY")
    if not k:
        print("ERROR: FMP_API_KEY not set", file=sys.stderr)
        sys.exit(1)
    return k


def _get(path: str, params: dict[str, Any] | None = None) -> Any:
    params = dict(params or {})
    params["apikey"] = _key()
    url = f"{BASE}{path}"
    r = requests.get(url, params=params, timeout=30)
    r.raise_for_status()
    return r.json()


def profile(ticker: str) -> dict[str, Any]:
    data = _get("/profile", {"symbol": ticker})
    if not data:
        return {"error": "no profile"}
    return {"ticker": ticker, "profile": data[0], "_fetched_at": dt.datetime.now().isoformat()}


def ratios(ticker: str, years: int = 5) -> dict[str, Any]:
    data = _get("/ratios", {"symbol": ticker, "limit": years})
    return {"ticker": ticker, "ratios": data, "_fetched_at": dt.datetime.now().isoformat()}


def financials(ticker: str, years: int = 5) -> dict[str, Any]:
    """Income/balance/cashflow statements from FMP stable endpoints."""
    income = _get("/income-statement", {"symbol": ticker, "limit": years, "period": "annual"})
    balance = _get("/balance-sheet-statement", {"symbol": ticker, "limit": years, "period": "annual"})
    cashflow = _get("/cash-flow-statement", {"symbol": ticker, "limit": years, "period": "annual"})
    return {
        "ticker": ticker,
        "income_statement": income if isinstance(income, list) else [],
        "balance_sheet_statement": balance if isinstance(balance, list) else [],
        "cash_flow_statement": cashflow if isinstance(cashflow, list) else [],
        "_fetched_at": dt.datetime.now().isoformat(),
    }


def valuation(ticker: str) -> dict[str, Any]:
    quote = _get("/quote", {"symbol": ticker})
    km = _get("/key-metrics-ttm", {"symbol": ticker})
    return {
        "ticker": ticker,
        "quote": quote[0] if isinstance(quote, list) and quote else quote,
        "key_metrics_ttm": km[0] if isinstance(km, list) and km else km,
        "_fetched_at": dt.datetime.now().isoformat(),
    }


def peers(ticker: str) -> dict[str, Any]:
    data = _get("/stock-peers", {"symbol": ticker})
    return {"ticker": ticker, "peers": data, "_fetched_at": dt.datetime.now().isoformat()}


def _parse_symbols(raw: str | None) -> list[str]:
    if not raw:
        return []
    return [part.strip().upper() for chunk in raw.split(",") for part in chunk.split() if part.strip()]


def _symbols_from_peers_payload(payload: dict[str, Any]) -> list[str]:
    data = payload.get("peers")
    symbols: list[str] = []
    rows = data if isinstance(data, list) else [data]
    for row in rows:
        if isinstance(row, str):
            symbols.append(row)
        elif isinstance(row, dict):
            for key in ("peersList", "peers", "symbols", "peerSymbols"):
                value = row.get(key)
                if isinstance(value, list):
                    symbols.extend(str(item) for item in value)
                elif isinstance(value, str):
                    symbols.extend(_parse_symbols(value))
    return [sym.upper() for sym in symbols if sym]


def peer_valuations(ticker: str, symbols: list[str] | None = None, peer_limit: int = 5) -> dict[str, Any]:
    """Fetch multiple peer valuation payloads inside one Python process.

    This does not reduce FMP API request count; it removes repeated uv/Python
    cold starts and keeps peer evidence in one compact file.
    """
    selected = list(symbols or [])
    peer_source: dict[str, Any] | None = None
    if not selected:
        try:
            peer_source = peers(ticker)
            selected = _symbols_from_peers_payload(peer_source)
        except requests.HTTPError as exc:
            return {"ticker": ticker, "error": f"peer discovery failed: HTTP {exc.response.status_code}: {exc.response.text[:120]}"}
    selected = [sym for sym in selected if sym and sym.upper() != ticker.upper()]
    deduped = list(dict.fromkeys(sym.upper() for sym in selected))[:peer_limit]
    valuations: dict[str, Any] = {}
    for symbol in deduped:
        try:
            valuations[symbol] = valuation(symbol)
        except requests.HTTPError as exc:
            valuations[symbol] = {"ticker": symbol, "error": f"HTTP {exc.response.status_code}: {exc.response.text[:120]}"}
        except Exception as exc:  # noqa: BLE001
            valuations[symbol] = {"ticker": symbol, "error": str(exc)}
    return {
        "ticker": ticker,
        "symbols": deduped,
        "peer_source": peer_source,
        "valuations": valuations,
        "_note": "One process, one output file. API request count is still quote+key-metrics per peer.",
        "_fetched_at": dt.datetime.now().isoformat(),
    }


def estimates(ticker: str) -> dict[str, Any]:
    est = _get("/analyst-estimates", {"symbol": ticker})
    sur = _get("/earnings-surprises", {"symbol": ticker})
    return {
        "ticker": ticker,
        "analyst_estimates": est[:8] if isinstance(est, list) else [],
        "earnings_surprises": sur[:8] if isinstance(sur, list) else [],
        "_fetched_at": dt.datetime.now().isoformat(),
    }


SECTIONS = {
    "profile": lambda t, a: profile(t),
    "financials": lambda t, a: financials(t, years=a.years),
    "ratios": lambda t, a: ratios(t, years=a.years),
    "valuation": lambda t, a: valuation(t),
    "peers": lambda t, a: peers(t),
    "peer-valuations": lambda t, a: peer_valuations(t, symbols=_parse_symbols(a.symbols), peer_limit=a.peer_limit),
    "estimates": lambda t, a: estimates(t),
}


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("ticker")
    p.add_argument("--section", choices=sorted(SECTIONS) + ["all"],
                   help="단일 / 'all' = 6 section 한 번에")
    p.add_argument("--out", type=Path,
                   help="단일 섹션 출력. --section all 시 무시")
    p.add_argument("--out-dir", type=Path,
                   help="--section all 시 JSON 저장 폴더 ({ticker}_{section}.json)")
    p.add_argument("--years", type=int, default=5)
    p.add_argument("--symbols",
                   help="--section peer-valuations 에서 사용할 peer 티커 목록. 예: MSFT,GOOGL,META")
    p.add_argument("--peer-limit", type=int, default=5,
                   help="peer-valuations 최대 peer 수")
    args = p.parse_args()
    if not args.section:
        p.error("--section required")

    if args.section == "all":
        if not args.out_dir:
            p.error("--section all 은 --out-dir 필요")
        args.out_dir.mkdir(parents=True, exist_ok=True)
        for sec in ("profile", "financials", "ratios", "valuation", "peers", "estimates"):
            try:
                data = SECTIONS[sec](args.ticker, args)
            except requests.HTTPError as exc:
                data = {"error": f"HTTP {exc.response.status_code}: {exc.response.text[:120]}"}
            out = args.out_dir / f"{args.ticker}_{sec}.json"
            out.write_text(json.dumps(data, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
            print(f"wrote {out}")
        return

    try:
        data = SECTIONS[args.section](args.ticker, args)
    except requests.HTTPError as exc:
        print(f"HTTPError: {exc} ({exc.response.text[:200]})", file=sys.stderr)
        sys.exit(1)
    if not args.out:
        p.error("--out required for single section")
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(data, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
    if "error" in data:
        print(f"WARN: {data['error']}", file=sys.stderr)
        sys.exit(1)
    print(f"wrote {args.out}")


if __name__ == "__main__":
    main()
