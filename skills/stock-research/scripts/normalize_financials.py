#!/usr/bin/env python3
"""Normalize fetched evidence into a compact financial metric JSON.

Usage:
    python3 normalize_financials.py stocks/005930/_evidence --ticker 005930 --out stocks/005930/_evidence/canonical_financials.json

This is intentionally heuristic. It does not replace source files; it creates
a small, citation-friendly index of the line items a research.md usually needs.
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import re
from pathlib import Path
from typing import Any


KR_ACCOUNT_MAP: list[tuple[str, re.Pattern[str]]] = [
    ("revenue", re.compile(r"매출|영업수익|수익\(매출액\)")),
    ("gross_profit", re.compile(r"매출총이익")),
    ("operating_income", re.compile(r"영업이익")),
    ("net_income", re.compile(r"당기순이익|분기순이익|반기순이익")),
    ("total_assets", re.compile(r"자산총계")),
    ("total_liabilities", re.compile(r"부채총계")),
    ("total_equity", re.compile(r"자본총계")),
    ("current_assets", re.compile(r"유동자산")),
    ("current_liabilities", re.compile(r"유동부채")),
    ("cash", re.compile(r"현금및현금성자산")),
    ("receivables", re.compile(r"매출채권")),
    ("inventory", re.compile(r"재고자산")),
    ("payables", re.compile(r"매입채무")),
    ("cfo", re.compile(r"영업활동.*현금흐름")),
    ("cfi", re.compile(r"투자활동.*현금흐름")),
    ("cff", re.compile(r"재무활동.*현금흐름")),
    ("capex", re.compile(r"유형자산.*취득|무형자산.*취득")),
    ("eps_basic", re.compile(r"기본주당.*이익|기본주당순이익")),
]

FMP_FIELD_MAP = {
    "revenue": ("revenue", "Revenue"),
    "gross_profit": ("grossProfit", "Gross Profit"),
    "operating_income": ("operatingIncome", "Operating Income"),
    "net_income": ("netIncome", "Net Income"),
    "eps_basic": ("eps", "EPS"),
    "total_assets": ("totalAssets", "Total Assets"),
    "total_liabilities": ("totalLiabilities", "Total Liabilities"),
    "total_equity": ("totalStockholdersEquity", "Total Equity"),
    "current_assets": ("totalCurrentAssets", "Current Assets"),
    "current_liabilities": ("totalCurrentLiabilities", "Current Liabilities"),
    "cash": ("cashAndCashEquivalents", "Cash And Cash Equivalents"),
    "inventory": ("inventory", "Inventory"),
    "receivables": ("netReceivables", "Receivables"),
    "payables": ("accountPayables", "Payables"),
    "cfo": ("netCashProvidedByOperatingActivities", "CFO"),
    "capex": ("capitalExpenditure", "CAPEX"),
    "fcf": ("freeCashFlow", "Free Cash Flow"),
}


def parse_amount(value: Any) -> float | None:
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return float(value)
    text = str(value).strip().replace(",", "")
    if not text or text in {"-", "—"}:
        return None
    negative = text.startswith("(") and text.endswith(")")
    text = text.strip("()")
    try:
        out = float(text)
    except ValueError:
        return None
    return -out if negative else out


def load_json_files(root: Path) -> list[tuple[Path, Any]]:
    files: list[tuple[Path, Any]] = []
    for path in sorted(root.rglob("*.json")):
        if path.name in {"manifest.json", "canonical_financials.json"}:
            continue
        try:
            files.append((path, json.loads(path.read_text(encoding="utf-8"))))
        except (OSError, json.JSONDecodeError):
            continue
    return files


def add_metric(metrics: dict[str, dict[str, dict[str, Any]]], metric: str, year: str, value: Any, source_file: Path, source_label: str) -> None:
    amount = parse_amount(value)
    if amount is None:
        return
    metrics.setdefault(metric, {})[year] = {
        "value": amount,
        "source_file": str(source_file),
        "source": source_label,
    }


def normalize_dart(path: Path, payload: dict[str, Any], metrics: dict[str, dict[str, dict[str, Any]]]) -> None:
    if "series" in payload:
        for account, years in payload.get("series", {}).items():
            metric = next((name for name, pattern in KR_ACCOUNT_MAP if pattern.search(account)), None)
            if not metric or not isinstance(years, dict):
                continue
            for year, value in years.items():
                add_metric(metrics, metric, str(year), value, path, "DART XBRL")
        return

    statements = payload.get("statements_by_year", {})
    if not isinstance(statements, dict):
        return
    for year, statement in statements.items():
        accounts = statement.get("accounts", []) if isinstance(statement, dict) else []
        for account in accounts:
            if not isinstance(account, dict):
                continue
            account_name = str(account.get("account_nm", ""))
            metric = next((name for name, pattern in KR_ACCOUNT_MAP if pattern.search(account_name)), None)
            if not metric:
                continue
            value = account.get("thstrm_amount") or account.get("frmtrm_amount")
            add_metric(metrics, metric, str(year), value, path, "DART XBRL")


def normalize_fmp(path: Path, payload: Any, metrics: dict[str, dict[str, dict[str, Any]]]) -> None:
    if isinstance(payload, list):
        collections = [payload]
    elif isinstance(payload, dict):
        collections = [
            payload.get("income_statement", []),
            payload.get("balance_sheet_statement", []),
            payload.get("cash_flow_statement", []),
            payload.get("ratios", []),
        ]
    else:
        return
    for rows in collections:
        if not isinstance(rows, list):
            continue
        for row in rows:
            if not isinstance(row, dict):
                continue
            year = str(row.get("calendarYear") or str(row.get("date", ""))[:4])
            if not re.fullmatch(r"20\d{2}", year):
                continue
            for metric, (field, label) in FMP_FIELD_MAP.items():
                if field in row:
                    add_metric(metrics, metric, year, row[field], path, f"FMP {label}")


def normalize_pykrx(path: Path, payload: dict[str, Any], metrics: dict[str, dict[str, dict[str, Any]]]) -> dict[str, Any]:
    snapshot: dict[str, Any] = {}
    as_of = str(payload.get("as_of", ""))
    for field in ("price", "high_52w", "low_52w", "market_cap_krw", "shares_outstanding", "PER", "PBR", "EPS", "BPS", "DIV", "DPS"):
        if field in payload and payload[field] is not None:
            snapshot[field] = {"value": payload[field], "as_of": as_of, "source_file": str(path), "source": "KRX/pykrx"}
    return snapshot


def build(root: Path, ticker: str) -> dict[str, Any]:
    metrics: dict[str, dict[str, dict[str, Any]]] = {}
    market_snapshot: dict[str, Any] = {}
    for path, payload in load_json_files(root):
        lowered = " ".join(part.lower() for part in path.parts)
        if isinstance(payload, dict) and ("dart" in lowered or "statements_by_year" in payload or "series" in payload):
            normalize_dart(path, payload, metrics)
        if "fmp" in lowered or (isinstance(payload, dict) and ("income_statement" in payload or "balance_sheet_statement" in payload)):
            normalize_fmp(path, payload, metrics)
        if isinstance(payload, dict) and ("pykrx" in lowered or any(k in payload for k in ("market_cap_krw", "PER", "PBR", "price"))):
            market_snapshot.update(normalize_pykrx(path, payload, metrics))

    years = sorted({year for by_year in metrics.values() for year in by_year})
    return {
        "ticker": ticker,
        "generated_at": dt.datetime.now(dt.UTC).isoformat(),
        "years": years,
        "metrics": metrics,
        "market_snapshot": market_snapshot,
        "notes": [
            "Amounts are raw source units unless the source file states otherwise.",
            "Use source_file/source in each metric when citing research.md.",
        ],
    }


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("evidence_dir", type=Path)
    p.add_argument("--ticker", required=True)
    p.add_argument("--out", type=Path)
    args = p.parse_args()

    out = args.out or (args.evidence_dir / "canonical_financials.json")
    result = build(args.evidence_dir, args.ticker)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"wrote {out} ({len(result['metrics'])} metrics, {len(result['years'])} years)")


if __name__ == "__main__":
    main()
