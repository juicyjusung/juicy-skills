#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = [
#   "pykrx>=1.0.45",
#   "pandas",
# ]
# ///
"""pykrx 기반 한국 시세·재무비율 수집 (무인증).

사용:
    uv run --env-file .env $SKILL_DIR/scripts/fetch_pykrx.py 005930 --section market --out _evidence/market.json
    uv run --env-file .env $SKILL_DIR/scripts/fetch_pykrx.py 005930 --section ratios --out _evidence/ratios.json
    uv run --env-file .env $SKILL_DIR/scripts/fetch_pykrx.py 005930 --section valuation --out _evidence/val.json
    uv run --env-file .env $SKILL_DIR/scripts/fetch_pykrx.py 005930 --section all --out-dir _evidence/pykrx

섹션:
    market      시장(KOSPI/KOSDAQ), 시총, 유통주식수, 외국인 보유율
    ratios      PER/PBR/배당수익률 (KRX 발표)
    valuation   현재가, 52주 고저, ratios + 시총
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import sys
from pathlib import Path
from typing import Any


def _import_krx():
    try:
        from pykrx import stock  # type: ignore
        return stock
    except ImportError:
        print("ERROR: pykrx not installed. Run with `uv run --env-file .env $SKILL_DIR/scripts/fetch_pykrx.py ...`", file=sys.stderr)
        sys.exit(1)


def _today() -> str:
    return dt.date.today().strftime("%Y%m%d")


def _last_trading_day(stock, today: str, ticker: str) -> str:
    """Walk back up to 30 days until ticker has OHLCV data.

    Wider window covers system clock ahead of KRX data window (e.g. weekend +
    long holiday + future-dated test env).
    """
    base = dt.datetime.strptime(today, "%Y%m%d").date()
    for delta in range(0, 30):
        candidate = (base - dt.timedelta(days=delta)).strftime("%Y%m%d")
        try:
            df = stock.get_market_ohlcv(candidate, candidate, ticker)
            if not df.empty:
                return candidate
        except Exception:
            continue
    raise RuntimeError(f"no trading day with data for {ticker} within 30d of {today}")


def _market_segment(stock, today: str, ticker: str) -> str | None:
    for market in ("KOSPI", "KOSDAQ", "KONEX"):
        try:
            if ticker in stock.get_market_ticker_list(today, market=market):
                return market
        except Exception:
            continue
    return None


def _cap_row(stock, today: str, ticker: str):
    try:
        cap_df = stock.get_market_cap(today, today, ticker)
        if not cap_df.empty:
            return cap_df.iloc[-1]
    except Exception:
        pass
    try:
        cap_df = stock.get_market_cap_by_ticker(today)
        if ticker in cap_df.index:
            return cap_df.loc[ticker]
    except Exception:
        pass
    return None


def _fundamental_row(stock, today: str, ticker: str):
    try:
        df = stock.get_market_fundamental(today, today, ticker)
        if not df.empty:
            return df.iloc[-1]
    except Exception:
        pass
    try:
        df = stock.get_market_fundamental_by_ticker(today)
        if ticker in df.index:
            return df.loc[ticker]
    except Exception:
        pass
    return None


def _context(ticker: str):
    stock = _import_krx()
    today = _last_trading_day(stock, _today(), ticker)
    return stock, today


def _market(ticker: str, stock, today: str) -> dict[str, Any]:
    try:
        market_name = stock.get_market_ticker_name(ticker)
        row = _cap_row(stock, today, ticker)
        cap = int(row["시가총액"]) if row is not None else None
        shares = int(row["상장주식수"]) if row is not None else None
        segment = _market_segment(stock, today, ticker)
    except Exception as exc:  # noqa: BLE001
        return {"error": f"market fetch failed: {exc}"}
    return {
        "ticker": ticker,
        "name": market_name,
        "market": segment,
        "as_of": today,
        "market_cap_krw": cap,
        "shares_outstanding": shares,
        "_fetched_at": dt.datetime.now().isoformat(),
    }


def market(ticker: str) -> dict[str, Any]:
    stock, today = _context(ticker)
    return _market(ticker, stock, today)


def _ratios(ticker: str, stock, today: str) -> dict[str, Any]:
    try:
        row = _fundamental_row(stock, today, ticker)
        if row is None:
            return {"error": "no fundamental data"}
        out = {
            "ticker": ticker,
            "as_of": today,
            "BPS": float(row.get("BPS", 0)),
            "PER": float(row.get("PER", 0)),
            "PBR": float(row.get("PBR", 0)),
            "EPS": float(row.get("EPS", 0)),
            "DIV": float(row.get("DIV", 0)),
            "DPS": float(row.get("DPS", 0)),
            "_fetched_at": dt.datetime.now().isoformat(),
        }
        return out
    except Exception as exc:  # noqa: BLE001
        return {"error": f"ratios fetch failed: {exc}"}


def ratios(ticker: str) -> dict[str, Any]:
    stock, today = _context(ticker)
    return _ratios(ticker, stock, today)


def _valuation(
    ticker: str,
    stock,
    today: str,
    market_payload: dict[str, Any] | None = None,
    ratios_payload: dict[str, Any] | None = None,
) -> dict[str, Any]:
    base = dt.datetime.strptime(today, "%Y%m%d").date()
    start_52w = (base - dt.timedelta(days=365)).strftime("%Y%m%d")
    out: dict[str, Any] = {"ticker": ticker, "as_of": today}
    try:
        ohlcv = stock.get_market_ohlcv(start_52w, today, ticker)
        if not ohlcv.empty:
            out["price"] = float(ohlcv.iloc[-1]["종가"])
            out["high_52w"] = float(ohlcv["고가"].max())
            out["low_52w"] = float(ohlcv["저가"].min())
        m = market_payload if market_payload is not None else _market(ticker, stock, today)
        out["market_cap_krw"] = m.get("market_cap_krw")
        out["shares_outstanding"] = m.get("shares_outstanding")
        r = ratios_payload if ratios_payload is not None else _ratios(ticker, stock, today)
        for k in ("PER", "PBR", "EPS", "BPS", "DIV", "DPS"):
            if k in r:
                out[k] = r[k]
    except Exception as exc:  # noqa: BLE001
        return {"error": f"valuation fetch failed: {exc}"}
    out["_fetched_at"] = dt.datetime.now().isoformat()
    return out


def valuation(ticker: str) -> dict[str, Any]:
    stock, today = _context(ticker)
    return _valuation(ticker, stock, today)


SECTIONS = {
    "market": market,
    "ratios": ratios,
    "valuation": valuation,
}


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("ticker")
    p.add_argument("--section", required=True, choices=sorted(SECTIONS) + ["all"])
    p.add_argument("--out", type=Path)
    p.add_argument("--out-dir", type=Path,
                   help="--section all 시 3개 JSON 저장 폴더 ({ticker}_{section}.json)")
    args = p.parse_args()
    if args.section == "all":
        if not args.out_dir:
            p.error("--section all 은 --out-dir 필요")
        args.out_dir.mkdir(parents=True, exist_ok=True)
        had_error = False
        stock, today = _context(args.ticker)
        market_data = _market(args.ticker, stock, today)
        ratios_data = _ratios(args.ticker, stock, today)
        valuation_data = _valuation(args.ticker, stock, today, market_payload=market_data, ratios_payload=ratios_data)
        for sec, data in (
            ("market", market_data),
            ("ratios", ratios_data),
            ("valuation", valuation_data),
        ):
            out = args.out_dir / f"{args.ticker}_{sec}.json"
            out.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
            print(f"wrote {out}")
            had_error = had_error or "error" in data
        if had_error:
            sys.exit(1)
        return
    if not args.out:
        p.error("--out required for single section")
    data = SECTIONS[args.section](args.ticker)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    if "error" in data:
        print(f"WARN: {data['error']}", file=sys.stderr)
        sys.exit(1)
    print(f"wrote {args.out}")


if __name__ == "__main__":
    main()
