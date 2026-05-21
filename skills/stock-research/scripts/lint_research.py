#!/usr/bin/env python3
"""research.md 객관성 lint.

체크:
- 금칙어 (가치판단·정성형용·예측주관)
- 인용 누락 (수치 옆 [출처:날짜] 또는 footnote 없음)
- frontmatter 필수 필드와 sources URL
- N/A 사유 누락
- 가격·시총·멀티플의 저신뢰 출처 단독 사용

Exit codes:
    0: 통과
    1: 금칙어 발견
    2: 인용 누락
    3: frontmatter 누락
    4: 파일 못 읽음
    5: evidence/source quality 실패

Usage:
    python lint_research.py stocks/005930/research.md
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

FORBIDDEN = [
    # 가치 판단
    "저평가", "고평가", "적정가", "적정가치",
    "매수", "매도", "추천", "비중확대", "비중축소",
    # 정성 형용
    "유망", "매력적", "우량", "부실", "견조", "양호",
    "호재", "악재", "기대", "우려", "모멘텀",
    "성장 가능성", "잠재력", "전망 밝",
    # 예측·주관
    "할 것으로 보인다", "할 전망", "이 예상된다",
    "향후", "앞으로", "중장기적",
]

# 따옴표 안 인용은 허용. 따옴표 밖 사용만 차단.
QUOTE_RE = re.compile(r'"[^"\n]*"|"[^"\n]*"|\'[^\'\n]*\'')

REQUIRED_FRONTMATTER = ["ticker", "name", "as_of", "price_as_of", "financials_as_of", "sources"]
MIN_SOURCE_URLS = 2

# 수치 옆 인용: [...YYYY-MM-DD...] 또는 footnote [^n] 또는 "*출처:..." 표 캡션
CITATION_HINT = re.compile(r"\[[^\]]*\d{4}-\d{2}-\d{2}[^\]]*\]|\[\^[\w-]+\]|\*출처[:：]")
# 수치 패턴: 단위 포함 (조원, 억원, 만, %, 배, USD, KRW, m, b)
NUMBER_WITH_UNIT = re.compile(
    r"\b\d[\d,\.]*\s*(조원|억원|백만원|만원|%|배|원|USD|KRW|\$|m|b|bn|M|B|Bn)\b"
)
URL_RE = re.compile(r"https?://[^\s)>\]]+")
LOW_TRUST_SOURCE_RE = re.compile(r"블로그|blog|카페|forum|community|reddit", re.IGNORECASE)
MARKET_DATA_RE = re.compile(
    r"현재가|종가|시가총액|52주|PER|PBR|PSR|PEG|EV/|EV\s*/|멀티플|market cap|valuation",
    re.IGNORECASE,
)
TRUSTED_MARKET_SOURCE_RE = re.compile(
    r"KRX|pykrx|FnGuide|Company Guide|DART|SEC|EDGAR|FMP|Financial Modeling Prep|"
    r"Nasdaq|NYSE|Yahoo|Reuters|Bloomberg|회사 IR|IR|10-K|10-Q|사업보고서",
    re.IGNORECASE,
)
PLACEHOLDER_RE = re.compile(r"\bTODO\b|\bTBD\b|채워넣|작성 예정", re.IGNORECASE)


def strip_quotes(line: str) -> str:
    return QUOTE_RE.sub("", line)


def parse_frontmatter(text: str) -> dict[str, object] | None:
    if not text.startswith("---"):
        return None
    end = text.find("\n---", 3)
    if end == -1:
        return None
    block = text[3:end].strip()
    out: dict[str, object] = {}
    current_key: str | None = None
    for line in block.splitlines():
        raw = line.rstrip()
        line = raw.split("#", 1)[0].rstrip()
        if not line.strip():
            continue
        if line.startswith("  -") and current_key:
            values = out.setdefault(current_key, [])
            if isinstance(values, list):
                values.append(line.split("-", 1)[1].strip().strip('"\''))
            continue
        if ":" in line and not line.startswith("  "):
            k, _, v = line.partition(":")
            current_key = k.strip()
            value = v.strip().strip('"\'')
            if value:
                out[current_key] = value
            else:
                out[current_key] = []
    return out


def source_urls(fm: dict[str, object]) -> list[str]:
    raw = fm.get("sources", [])
    if isinstance(raw, list):
        return [s for s in raw if URL_RE.search(s)]
    if isinstance(raw, str):
        return URL_RE.findall(raw)
    return []


def has_table_caption(lines: list[str], idx: int) -> bool:
    """Return true if a markdown table row has a nearby source caption.

    Search from the current row to the first blank line after the table. Also
    look one line above because some tables use a lead-in source sentence.
    """
    start = max(0, idx - 1)
    end = idx
    while end < len(lines) and lines[end].strip():
        end += 1
    region = "\n".join(lines[start:end])
    return bool(CITATION_HINT.search(region))


def has_na_reason(lines: list[str], idx: int) -> bool:
    line = lines[idx]
    reason_re = re.compile(r"N/A\s*(\(|—|-|:)|출처 미확보|미파싱|미수집|미공시|미확인|미완료|권한 제한|자료 부재|별도 fetch|동상")
    if reason_re.search(line):
        return True
    if "N/A` 표기" in line or "`N/A` 표기" in line:
        return True
    if line.lstrip().startswith("|"):
        start = idx
        while start > 0 and lines[start - 1].strip():
            start -= 1
        end = idx
        while end < len(lines) and lines[end].strip():
            end += 1
        region = "\n".join(lines[start:end])
        return bool(re.search(r"출처 미확보|미파싱|미수집|미공시|미확인|미완료|권한 제한|자료 부재|별도 fetch|동상|Evidence Gap", region))
    return False


def lint(path: Path) -> int:
    try:
        text = path.read_text(encoding="utf-8")
    except OSError as exc:
        print(f"ERROR: cannot read {path}: {exc}", file=sys.stderr)
        return 4

    # 1) frontmatter
    fm = parse_frontmatter(text)
    if fm is None:
        print("FAIL: frontmatter (---...---) missing")
        return 3
    missing = [k for k in REQUIRED_FRONTMATTER if not fm.get(k)]
    if missing:
        print(f"FAIL: frontmatter missing fields: {', '.join(missing)}")
        return 3
    urls = source_urls(fm)
    if len(urls) < MIN_SOURCE_URLS:
        print(f"FAIL: frontmatter sources needs at least {MIN_SOURCE_URLS} URL(s); found {len(urls)}")
        return 3

    body_start = text.find("\n---", 3)
    body = text[body_start + 4 :] if body_start != -1 else text
    body_lines = body.splitlines()

    # 1.5) placeholder / unresolved scaffold
    placeholders = [(i, line.strip()[:120]) for i, line in enumerate(body_lines, start=1) if PLACEHOLDER_RE.search(line)]
    if placeholders:
        print("FAIL: unresolved placeholders found")
        for line_no, snippet in placeholders[:20]:
            print(f"  L{line_no}: {snippet}")
        return 5

    # 2) 금칙어
    violations: list[tuple[int, str, str]] = []
    for i, raw_line in enumerate(body_lines, start=1):
        stripped = strip_quotes(raw_line)
        for word in FORBIDDEN:
            if word in stripped:
                violations.append((i, word, raw_line.strip()[:120]))
    if violations:
        print("FAIL: forbidden words found (move to Evaluation Layer)")
        for line_no, word, snippet in violations:
            print(f"  L{line_no}: '{word}' in: {snippet}")
        return 1

    # 3) 인용 누락 — 숫자+단위 있는 줄에 인용 hint 없음 검출
    missing_cite: list[tuple[int, str]] = []
    in_code = False
    for i, raw_line in enumerate(body_lines, start=1):
        s = raw_line.rstrip()
        if s.startswith("```"):
            in_code = not in_code
            continue
        if in_code:
            continue
        if s.startswith("|") and "---" in s:
            continue  # 표 구분선
        if NUMBER_WITH_UNIT.search(s) and not CITATION_HINT.search(s):
            # 표 안의 셀이면 캡션이 표 아래 한 줄에 있는지 관용 처리
            missing_cite.append((i, s.strip()[:120]))
    if missing_cite:
        rows_in_table = [m for m in missing_cite if m[1].startswith("|")]
        non_table = [m for m in missing_cite if not m[1].startswith("|")]
        table_violations: list[tuple[int, str]] = []
        for line_no, snippet in rows_in_table:
            if not has_table_caption(body_lines, line_no - 1):
                table_violations.append((line_no, snippet))
        real = non_table + table_violations
        if real:
            print("FAIL: numbers without citation ([source:YYYY-MM-DD] or footnote)")
            for line_no, snippet in real[:20]:
                print(f"  L{line_no}: {snippet}")
            if len(real) > 20:
                print(f"  ... and {len(real) - 20} more")
            return 2

    # 4) N/A must explain why the evidence is missing.
    bad_na: list[tuple[int, str]] = []
    for idx, line in enumerate(body_lines):
        if "N/A" not in line:
            continue
        if not has_na_reason(body_lines, idx):
            bad_na.append((idx + 1, line.strip()[:120]))
    if bad_na:
        print("FAIL: N/A without explicit reason")
        for line_no, snippet in bad_na[:20]:
            print(f"  L{line_no}: {snippet}")
        return 5

    # 5) Market data should not rely only on low-trust sources.
    low_trust_market: list[tuple[int, str]] = []
    for i, line in enumerate(body_lines, start=1):
        if MARKET_DATA_RE.search(line) and LOW_TRUST_SOURCE_RE.search(line) and not TRUSTED_MARKET_SOURCE_RE.search(line):
            low_trust_market.append((i, line.strip()[:120]))
    if low_trust_market:
        print("FAIL: market/valuation data uses low-trust source without primary/secondary corroboration")
        for line_no, snippet in low_trust_market[:20]:
            print(f"  L{line_no}: {snippet}")
        return 5

    print("OK")
    return 0


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("usage: lint_research.py <path>", file=sys.stderr)
        sys.exit(4)
    sys.exit(lint(Path(sys.argv[1])))
