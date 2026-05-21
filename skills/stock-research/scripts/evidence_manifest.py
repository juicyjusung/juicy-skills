#!/usr/bin/env python3
"""Build an evidence manifest for stock research raw data.

Usage:
    python3 evidence_manifest.py stocks/005930/_evidence --ticker 005930 --out stocks/005930/_evidence/manifest.json

The manifest gives the research writer and reviewer a compact index of the
raw files used: path, sha256, fetched_at, detected source, URL hints, and a
load policy so large raw evidence is not pulled into the model context whole.
"""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
from pathlib import Path
from typing import Any


SOURCE_HINTS = {
    "dart": "DART",
    "edgar": "SEC EDGAR",
    "fmp": "Financial Modeling Prep",
    "pykrx": "KRX/pykrx",
    "fred": "FRED",
    "ecos": "BOK ECOS",
}


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def load_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None


def walk_values(value: Any):
    if isinstance(value, dict):
        for v in value.values():
            yield from walk_values(v)
    elif isinstance(value, list):
        for v in value:
            yield from walk_values(v)
    else:
        yield value


def detect_source(path: Path, payload: Any) -> str:
    haystack = " ".join(str(part).lower() for part in path.parts)
    if isinstance(payload, dict):
        haystack += " " + " ".join(str(k).lower() for k in payload.keys())
    for token, source in SOURCE_HINTS.items():
        if token in haystack:
            return source
    return "web/manual"


def collect_urls(payload: Any) -> list[str]:
    urls: list[str] = []
    for value in walk_values(payload):
        if isinstance(value, str) and value.startswith(("http://", "https://")):
            urls.append(value)
    return sorted(set(urls))


def fetched_at(payload: Any) -> str | None:
    if isinstance(payload, dict):
        value = payload.get("_fetched_at") or payload.get("fetched_at") or payload.get("as_of")
        return str(value) if value else None
    return None


def build_manifest(evidence_dir: Path, ticker: str, max_inline_bytes: int = 100_000) -> dict[str, Any]:
    entries: list[dict[str, Any]] = []
    for path in sorted(evidence_dir.rglob("*")):
        if not path.is_file() or path.name == "manifest.json":
            continue
        if path.suffix.lower() not in {".json", ".md", ".txt", ".csv"}:
            continue
        size = path.stat().st_size
        large_file = size > max_inline_bytes
        payload = load_json(path) if path.suffix.lower() == ".json" else None
        entries.append(
            {
                "path": str(path.relative_to(evidence_dir)),
                "sha256": sha256(path),
                "bytes": size,
                "source": detect_source(path, payload),
                "fetched_at": fetched_at(payload),
                "urls": collect_urls(payload)[:20] if payload is not None else [],
                "large_file": large_file,
                "load_policy": "do_not_load_whole_file" if large_file else "safe_to_load_inline",
            }
        )
    return {
        "ticker": ticker,
        "evidence_dir": str(evidence_dir),
        "generated_at": dt.datetime.now(dt.UTC).isoformat(),
        "max_inline_bytes": max_inline_bytes,
        "file_count": len(entries),
        "entries": entries,
    }


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("evidence_dir", type=Path)
    p.add_argument("--ticker", required=True)
    p.add_argument("--out", type=Path)
    p.add_argument("--max-inline-bytes", type=int, default=100_000,
                   help="Files larger than this get load_policy=do_not_load_whole_file")
    args = p.parse_args()

    manifest = build_manifest(args.evidence_dir, args.ticker, max_inline_bytes=args.max_inline_bytes)
    out = args.out or (args.evidence_dir / "manifest.json")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"wrote {out} ({manifest['file_count']} files)")


if __name__ == "__main__":
    main()
