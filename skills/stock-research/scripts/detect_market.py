#!/usr/bin/env python3
"""티커 → 시장 판별.

KR: 6자리 숫자 (KOSPI/KOSDAQ)
US: 1~5자리 알파벳, 선택적 . 클래스 접미사 (e.g., BRK.B)
UNKNOWN: 그 외

Usage:
    python detect_market.py 005930  # KR
    python detect_market.py TSLA    # US
    python detect_market.py BRK.B   # US
"""
import re
import sys


def detect(ticker: str) -> str:
    t = ticker.strip().upper()
    if re.fullmatch(r"\d{6}", t):
        return "KR"
    if re.fullmatch(r"[A-Z]{1,5}(\.[A-Z])?", t):
        return "US"
    return "UNKNOWN"


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("usage: detect_market.py <ticker>", file=sys.stderr)
        sys.exit(2)
    print(detect(sys.argv[1]))
