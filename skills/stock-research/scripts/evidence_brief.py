#!/usr/bin/env python3
"""Create a compact evidence brief for stock research drafting.

The brief is the preferred file to read before writing research.md. It points
to canonical financials, source URLs, and large raw files without loading those
raw files into the model context wholesale.
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
from pathlib import Path
from typing import Any


PREFERRED_METRICS = [
    ("revenue", "Revenue"),
    ("operating_income", "Operating income"),
    ("net_income", "Net income"),
    ("cfo", "CFO"),
    ("capex", "CAPEX"),
    ("fcf", "FCF"),
    ("total_assets", "Total assets"),
    ("total_liabilities", "Total liabilities"),
    ("total_equity", "Total equity"),
    ("eps_basic", "EPS"),
]

MARKET_FIELDS = [
    ("price", "Price"),
    ("high_52w", "52w high"),
    ("low_52w", "52w low"),
    ("market_cap_krw", "Market cap KRW"),
    ("shares_outstanding", "Shares"),
    ("PER", "PER"),
    ("PBR", "PBR"),
    ("EPS", "EPS"),
    ("BPS", "BPS"),
    ("DIV", "Dividend yield"),
]


def load_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None


def format_bytes(value: int | float | None) -> str:
    if value is None:
        return "n/a"
    size = float(value)
    for unit in ("B", "KB", "MB", "GB"):
        if size < 1024 or unit == "GB":
            return f"{size:.0f}{unit}" if unit == "B" else f"{size:.1f}{unit}"
        size /= 1024
    return f"{size:.1f}GB"


def format_value(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, float):
        if abs(value) >= 1_000_000:
            return f"{value:,.0f}"
        return f"{value:,.2f}".rstrip("0").rstrip(".")
    if isinstance(value, int):
        return f"{value:,}"
    return str(value)


def md_escape(value: Any) -> str:
    return str(value).replace("|", "\\|").replace("\n", " ")


def build_inventory(evidence_dir: Path, manifest: dict[str, Any] | None, max_inline_bytes: int) -> list[dict[str, Any]]:
    if manifest and isinstance(manifest.get("entries"), list):
        normalized: list[dict[str, Any]] = []
        for raw in manifest["entries"]:
            if not isinstance(raw, dict):
                continue
            entry = dict(raw)
            size = int(entry.get("bytes") or 0)
            large_file = bool(entry.get("large_file")) or size > max_inline_bytes
            entry["large_file"] = large_file
            entry["load_policy"] = entry.get("load_policy") or ("do_not_load_whole_file" if large_file else "safe_to_load_inline")
            normalized.append(entry)
        return normalized

    entries: list[dict[str, Any]] = []
    for path in sorted(evidence_dir.rglob("*")):
        if not path.is_file() or path.name == "manifest.json":
            continue
        if path.suffix.lower() not in {".json", ".md", ".txt", ".csv"}:
            continue
        size = path.stat().st_size
        entries.append(
            {
                "path": str(path.relative_to(evidence_dir)),
                "bytes": size,
                "source": "unknown",
                "fetched_at": None,
                "urls": [],
                "large_file": size > max_inline_bytes,
                "load_policy": "do_not_load_whole_file" if size > max_inline_bytes else "safe_to_load_inline",
            }
        )
    return entries


def metric_table(canonical: dict[str, Any] | None) -> list[str]:
    if not canonical:
        return ["- canonical_financials.json not found."]
    years = [str(y) for y in canonical.get("years", [])][-5:]
    if not years:
        return ["- No canonical financial years found."]

    metrics = canonical.get("metrics", {})
    lines = ["| Metric | " + " | ".join(years) + " | Source files |", "|---|" + "|".join(["---"] * len(years)) + "|---|"]
    for key, label in PREFERRED_METRICS:
        by_year = metrics.get(key)
        if not isinstance(by_year, dict):
            continue
        values: list[str] = []
        sources: set[str] = set()
        for year in years:
            point = by_year.get(year, {})
            values.append(format_value(point.get("value")) if isinstance(point, dict) else "")
            if isinstance(point, dict) and point.get("source_file"):
                sources.add(str(point["source_file"]))
        lines.append(f"| {label} | " + " | ".join(md_escape(v) for v in values) + f" | {md_escape(', '.join(sorted(sources)))} |")
    return lines if len(lines) > 2 else ["- Canonical financials exist, but no preferred metrics were populated."]


def market_lines(canonical: dict[str, Any] | None) -> list[str]:
    if not canonical:
        return []
    snapshot = canonical.get("market_snapshot", {})
    if not isinstance(snapshot, dict) or not snapshot:
        return ["- No market snapshot found in canonical_financials.json."]
    lines = ["| Field | Value | As of | Source file |", "|---|---:|---|---|"]
    for key, label in MARKET_FIELDS:
        point = snapshot.get(key)
        if not isinstance(point, dict):
            continue
        lines.append(
            f"| {label} | {md_escape(format_value(point.get('value')))} | "
            f"{md_escape(point.get('as_of', ''))} | {md_escape(point.get('source_file', ''))} |"
        )
    return lines


def collect_errors(evidence_dir: Path, entries: list[dict[str, Any]], max_inline_bytes: int) -> list[str]:
    errors: list[str] = []
    for entry in entries:
        if int(entry.get("bytes") or 0) > max_inline_bytes:
            continue
        rel = entry.get("path")
        if not rel or not str(rel).endswith(".json"):
            continue
        payload = load_json(evidence_dir / str(rel))
        if isinstance(payload, dict):
            err = payload.get("error") or payload.get("_error")
            if err:
                errors.append(f"- `{rel}`: {err}")
    return errors


def build_brief(evidence_dir: Path, ticker: str, max_items: int, max_inline_bytes: int) -> str:
    manifest_path = evidence_dir / "manifest.json"
    canonical_path = evidence_dir / "canonical_financials.json"
    manifest = load_json(manifest_path) if manifest_path.exists() else None
    canonical = load_json(canonical_path) if canonical_path.exists() else None
    entries = build_inventory(evidence_dir, manifest if isinstance(manifest, dict) else None, max_inline_bytes)
    large = [e for e in entries if e.get("large_file") or int(e.get("bytes") or 0) > max_inline_bytes]
    urls: list[str] = []
    for entry in entries:
        for url in entry.get("urls") or []:
            if isinstance(url, str) and url not in urls:
                urls.append(url)

    lines: list[str] = [
        f"# Evidence Brief — {ticker}",
        "",
        f"- generated_at: {dt.datetime.now(dt.UTC).isoformat()}",
        f"- evidence_dir: `{evidence_dir}`",
        f"- file_count: {len(entries)}",
        f"- max_inline_bytes: {format_bytes(max_inline_bytes)}",
        "",
        "## Read First",
        "",
        "- Use this brief, `canonical_financials.json`, and `manifest.json` before opening raw files.",
        "- Do not load files marked `do_not_load_whole_file` wholesale; inspect them by targeted search or parser extraction only.",
        "",
        "## File Inventory",
        "",
        "| Path | Size | Source | Fetched at | Load policy |",
        "|---|---:|---|---|---|",
    ]
    for entry in entries[:max_items]:
        lines.append(
            f"| `{md_escape(entry.get('path', ''))}` | {format_bytes(entry.get('bytes'))} | "
            f"{md_escape(entry.get('source', ''))} | {md_escape(entry.get('fetched_at') or '')} | "
            f"{md_escape(entry.get('load_policy') or '')} |"
        )
    if len(entries) > max_items:
        lines.append(f"| ... | ... | ... | ... | {len(entries) - max_items} more files omitted |")

    lines.extend(["", "## Do Not Load Wholesale", ""])
    if large:
        for entry in large:
            lines.append(f"- `{entry.get('path')}` ({format_bytes(entry.get('bytes'))}): use targeted extraction/search.")
    else:
        lines.append("- None.")

    lines.extend(["", "## Canonical Financials", ""])
    lines.extend(metric_table(canonical if isinstance(canonical, dict) else None))
    lines.extend(["", "## Market Snapshot", ""])
    lines.extend(market_lines(canonical if isinstance(canonical, dict) else None))

    errors = collect_errors(evidence_dir, entries, max_inline_bytes)
    lines.extend(["", "## Evidence Errors", ""])
    lines.extend(errors or ["- None found in small JSON evidence files."])

    lines.extend(["", "## Source URLs", ""])
    if urls:
        for url in urls[:30]:
            lines.append(f"- {url}")
        if len(urls) > 30:
            lines.append(f"- ... {len(urls) - 30} more URLs in manifest.json")
    else:
        lines.append("- No URLs collected in manifest.")

    lines.append("")
    return "\n".join(lines)


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("evidence_dir", type=Path)
    p.add_argument("--ticker", required=True)
    p.add_argument("--out", type=Path)
    p.add_argument("--max-items", type=int, default=40)
    p.add_argument("--max-inline-bytes", type=int, default=100_000)
    args = p.parse_args()

    brief = build_brief(args.evidence_dir, args.ticker, args.max_items, args.max_inline_bytes)
    out = args.out or (args.evidence_dir / "evidence_brief.md")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(brief, encoding="utf-8")
    print(f"wrote {out}")


if __name__ == "__main__":
    main()
