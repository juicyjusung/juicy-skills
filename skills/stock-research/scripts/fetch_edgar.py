#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = [
#   "edgartools>=3.0",
#   "pandas",
# ]
# ///
"""SEC EDGAR (미국 공시) 데이터 수집 (무인증).

사용:
    uv run --env-file .env $SKILL_DIR/scripts/fetch_edgar.py AAPL --section identity --out _evidence/identity.json
    uv run --env-file .env $SKILL_DIR/scripts/fetch_edgar.py AAPL --section disclosures --days 365 --out _evidence/disc.json
    uv run --env-file .env $SKILL_DIR/scripts/fetch_edgar.py AAPL --section financials --years 5 --out _evidence/fin.json
    uv run --env-file .env $SKILL_DIR/scripts/fetch_edgar.py AAPL --section business --out _evidence/biz.json

EDGAR_IDENTITY 환경변수 권장 (SEC 정책):
    export EDGAR_IDENTITY="Your Name your.email@example.com"
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import sys
from pathlib import Path
from typing import Any


def _ensure_identity() -> None:
    if "EDGAR_IDENTITY" not in os.environ:
        os.environ["EDGAR_IDENTITY"] = "stock-research-skill no-reply@example.com"


def _import_edgar():
    try:
        from edgar import Company, set_identity  # type: ignore
        _ensure_identity()
        set_identity(os.environ["EDGAR_IDENTITY"])
        return Company
    except ImportError:
        print("ERROR: edgartools not installed. Run with `uv run --env-file .env $SKILL_DIR/scripts/fetch_edgar.py ...`", file=sys.stderr)
        sys.exit(1)


def identity(ticker: str) -> dict[str, Any]:
    Company = _import_edgar()
    try:
        c = Company(ticker)
    except Exception as exc:  # noqa: BLE001
        return {"error": f"company lookup failed: {exc}"}
    return {
        "ticker": ticker,
        "cik": getattr(c, "cik", None),
        "name": getattr(c, "name", None),
        "sic": getattr(c, "sic", None),
        "sic_description": getattr(c, "sic_description", None),
        "fiscal_year_end": str(getattr(c, "fiscal_year_end", "")),
        "exchanges": getattr(c, "exchanges", None),
        "_fetched_at": dt.datetime.now().isoformat(),
    }


def disclosures(ticker: str, days: int = 365) -> dict[str, Any]:
    Company = _import_edgar()
    try:
        c = Company(ticker)
        filings = c.get_filings(form=["8-K", "10-Q", "10-K", "DEF 14A", "SC 13D", "SC 13G"])
    except Exception as exc:  # noqa: BLE001
        return {"error": f"filings fetch failed: {exc}"}
    cutoff = dt.date.today() - dt.timedelta(days=days)
    rows = []
    try:
        for f in filings:
            fdate = getattr(f, "filing_date", None)
            if fdate is None:
                continue
            if isinstance(fdate, str):
                try:
                    fdate_d = dt.date.fromisoformat(fdate)
                except ValueError:
                    continue
            else:
                fdate_d = fdate
            if fdate_d < cutoff:
                continue
            rows.append(
                {
                    "form": getattr(f, "form", None),
                    "filing_date": str(fdate_d),
                    "accession": getattr(f, "accession_no", None),
                    "primary_document": getattr(f, "primary_document", None),
                }
            )
    except Exception as exc:  # noqa: BLE001
        return {"error": f"iterate filings failed: {exc}"}
    return {
        "ticker": ticker,
        "since": str(cutoff),
        "count": len(rows),
        "items": rows,
        "_fetched_at": dt.datetime.now().isoformat(),
    }


def financials(ticker: str, years: int = 5) -> dict[str, Any]:
    Company = _import_edgar()
    try:
        c = Company(ticker)
        fins = c.financials  # edgartools Financials object
    except Exception as exc:  # noqa: BLE001
        return {"error": f"financials fetch failed: {exc}"}

    def df_to_json(label: str) -> Any:
        try:
            df = getattr(fins, label, None)
            if df is None:
                return None
            if hasattr(df, "to_dataframe"):
                df = df.to_dataframe()
            return json.loads(df.to_json(orient="split", date_format="iso"))
        except Exception as exc:  # noqa: BLE001
            return {"error": str(exc)}

    return {
        "ticker": ticker,
        "income_statement": df_to_json("income_statement"),
        "balance_sheet": df_to_json("balance_sheet"),
        "cash_flow_statement": df_to_json("cash_flow_statement"),
        "_fetched_at": dt.datetime.now().isoformat(),
    }


def business(ticker: str) -> dict[str, Any]:
    """최근 10-K 의 메타데이터 (URL/accession). 본문 segment·지역은 WebFetch 권장."""
    Company = _import_edgar()
    try:
        c = Company(ticker)
        tenks = list(c.get_filings(form="10-K").latest(3))
    except Exception as exc:  # noqa: BLE001
        return {"error": f"10-K fetch failed: {exc}"}
    items = []
    for f in tenks:
        items.append(
            {
                "form": getattr(f, "form", None),
                "filing_date": str(getattr(f, "filing_date", "")),
                "accession": getattr(f, "accession_no", None),
                "url": getattr(f, "filing_url", None),
                "primary_document_url": getattr(f, "document_url", None) or getattr(f, "primary_doc_url", None),
            }
        )
    return {
        "ticker": ticker,
        "ten_k_filings": items,
        "_note": "Item 1 (Business) / Item 1A (Risk) / Note Segment 본문은 url 을 WebFetch/firecrawl 로 추출.",
        "_fetched_at": dt.datetime.now().isoformat(),
    }


SECTIONS = {
    "identity": lambda t, a: identity(t),
    "disclosures": lambda t, a: disclosures(t, days=a.days),
    "financials": lambda t, a: financials(t, years=a.years),
    "business": lambda t, a: business(t),
}


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("ticker")
    p.add_argument("--section", choices=sorted(SECTIONS) + ["all"],
                   help="단일 / 'all' = 4 section 한 번에")
    p.add_argument("--out", type=Path,
                   help="단일 섹션 출력")
    p.add_argument("--out-dir", type=Path,
                   help="--section all 시 4 JSON 폴더 ({ticker}_{section}.json)")
    p.add_argument("--days", type=int, default=365)
    p.add_argument("--years", type=int, default=5)
    args = p.parse_args()
    if not args.section:
        p.error("--section required")

    if args.section == "all":
        if not args.out_dir:
            p.error("--section all 은 --out-dir 필요")
        args.out_dir.mkdir(parents=True, exist_ok=True)
        for sec in ("identity", "financials", "disclosures", "business"):
            data = SECTIONS[sec](args.ticker, args)
            out = args.out_dir / f"{args.ticker}_{sec}.json"
            out.write_text(json.dumps(data, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
            print(f"wrote {out}")
        return

    data = SECTIONS[args.section](args.ticker, args)
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
