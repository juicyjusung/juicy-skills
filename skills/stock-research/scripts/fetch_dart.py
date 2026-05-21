#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = [
#   "dart-fss>=0.4.10",
#   "requests",
#   "python-dotenv",
# ]
# ///
"""DART (한국 공시) 데이터 수집.

설계 결정 (2026-05 운영 경험):
- corp_code 룩업: dart-fss `get_corp_list().find_by_stock_code(ticker)` 만 신뢰 가능.
- 공시 목록·재무제표 본 데이터: dart-fss wrapper (`extract_fs`, `search_filings`) 가 빈 결과·corp_code 미지정 시 3개월 제한으로 자주 실패.
  → OpenDART REST 엔드포인트 직접 호출 (`requests`) 로 우회. 안정적.

환경변수: OPEN_DART_API_KEY (필수)

사용:
    uv run --env-file .env $SKILL_DIR/scripts/fetch_dart.py 005930 --section identity --out _evidence/identity.json
    uv run --env-file .env $SKILL_DIR/scripts/fetch_dart.py 005930 --section disclosures --days 365 --out _evidence/disc.json
    uv run --env-file .env $SKILL_DIR/scripts/fetch_dart.py 005930 --section financials --years 5 --out _evidence/fin.json
    uv run --env-file .env $SKILL_DIR/scripts/fetch_dart.py 005930 --section business --out _evidence/biz.json
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import re
import sys
from pathlib import Path
from typing import Any

import requests

try:
    from dotenv import load_dotenv

    load_dotenv()
except ImportError:
    pass


OPENDART_BASE = "https://opendart.fss.or.kr/api"

# DART 정기보고서 reprt_code
REPRT_CODES: dict[str, str] = {
    "11011": "사업보고서(연차)",
    "11012": "반기보고서",
    "11013": "1분기보고서",
    "11014": "3분기보고서",
}


def _require_key() -> str:
    key = os.environ.get("OPEN_DART_API_KEY")
    if not key:
        print("ERROR: OPEN_DART_API_KEY not set", file=sys.stderr)
        sys.exit(1)
    return key


def _import_dart_fss():
    try:
        import dart_fss as ds  # type: ignore
        return ds
    except ImportError:
        print(
            "ERROR: dart-fss not installed. Run with `uv run --env-file .env $SKILL_DIR/scripts/fetch_dart.py ...`",
            file=sys.stderr,
        )
        sys.exit(1)


def _resolve_corp_code(ticker: str) -> dict[str, Any]:
    """ticker (6자리 종목코드) → DART corp_code 메타.

    dart-fss 의 CORPCODE.xml 캐시를 사용 (첫 호출 시 다운로드).
    """
    ds = _import_dart_fss()
    ds.set_api_key(api_key=_require_key())
    corp_list = ds.get_corp_list()
    matches = corp_list.find_by_stock_code(ticker)
    if not matches:
        return {"error": f"ticker {ticker} not found in DART corp list"}
    c = matches if not isinstance(matches, list) else matches[0]
    return {
        "ticker": ticker,
        "corp_code": getattr(c, "corp_code", None),
        "corp_name": getattr(c, "corp_name", None),
        "stock_name": getattr(c, "stock_name", None),
        "modify_date": str(getattr(c, "modify_date", "")),
    }


def _meta_or_resolve(ticker: str, meta: dict[str, Any] | None = None) -> dict[str, Any]:
    return meta if meta is not None else _resolve_corp_code(ticker)


def _api_get(path: str, params: dict[str, Any]) -> dict[str, Any]:
    params = dict(params)
    params["crtfc_key"] = _require_key()
    r = requests.get(f"{OPENDART_BASE}/{path}", params=params, timeout=30)
    r.raise_for_status()
    return r.json()


# -----------------------------------------------------------------------------
# Sections
# -----------------------------------------------------------------------------


def identity(ticker: str, meta: dict[str, Any] | None = None) -> dict[str, Any]:
    meta = _meta_or_resolve(ticker, meta)
    if "error" in meta:
        return meta
    # 추가 회사정보 (업종·결산월·시총·시장구분)
    try:
        info = _api_get("company.json", {"corp_code": meta["corp_code"]})
    except requests.HTTPError as exc:
        info = {"_error": str(exc)}
    return {
        **meta,
        "company_info": info,
        "_fetched_at": dt.datetime.now().isoformat(),
    }


def _list_chunk(corp_code: str, bgn: str, end: str, pblntf_detail_ty: str | None) -> list[dict]:
    """list.json 1회 호출 (페이지네이션 포함). DART 는 한 호출 최대 100건, 3개월 범위."""
    page_no = 1
    rows: list[dict] = []
    while True:
        params: dict[str, Any] = {
            "corp_code": corp_code,
            "bgn_de": bgn,
            "end_de": end,
            "page_no": page_no,
            "page_count": 100,
            "last_reprt_at": "Y",
        }
        if pblntf_detail_ty:
            params["pblntf_detail_ty"] = pblntf_detail_ty
        j = _api_get("list.json", params)
        status = j.get("status")
        if status == "013":  # 데이터 없음
            break
        if status != "000":
            return [{"_api_error": f"{status} {j.get('message')}"}]
        rows.extend(j.get("list", []))
        if page_no >= int(j.get("total_page", 1)):
            break
        page_no += 1
    return rows


def _list_range(corp_code: str, days: int, pblntf_detail_ty: str | None = None) -> list[dict]:
    """DART list.json 의 3개월 제한 우회: 90일 단위 청크."""
    end = dt.date.today()
    start = end - dt.timedelta(days=days)
    all_rows: list[dict] = []
    cur = start
    while cur <= end:
        nxt = min(cur + dt.timedelta(days=90), end)
        rows = _list_chunk(corp_code, cur.strftime("%Y%m%d"), nxt.strftime("%Y%m%d"), pblntf_detail_ty)
        all_rows.extend(rows)
        cur = nxt + dt.timedelta(days=1)
    # 중복 제거 (rcept_no)
    seen: set[str] = set()
    deduped: list[dict] = []
    for r in all_rows:
        rcp = str(r.get("rcept_no", ""))
        if rcp and rcp not in seen:
            seen.add(rcp)
            deduped.append(r)
    return deduped


def disclosures(ticker: str, days: int = 365, meta: dict[str, Any] | None = None) -> dict[str, Any]:
    meta = _meta_or_resolve(ticker, meta)
    if "error" in meta:
        return meta
    rows = _list_range(meta["corp_code"], days)
    return {
        "ticker": ticker,
        "corp_code": meta["corp_code"],
        "corp_name": meta["corp_name"],
        "since_days": days,
        "count": len(rows),
        "items": rows,
        "_fetched_at": dt.datetime.now().isoformat(),
    }


MAJOR_DISCLOSURE_RE = re.compile(
    "사업보고서|반기보고서|분기보고서|주요사항보고서|"
    "자기주식|배당|현금ㆍ현물배당|합병|분할|증자|감자|"
    "단일판매|공급계약|타법인|소송|벌금|영업정지|조회공시|"
    "최대주주|임원ㆍ주요주주|영업실적|잠정실적"
)


def summarize_disclosures(payload: dict[str, Any], limit: int = 50, major_only: bool = False) -> dict[str, Any]:
    """Return a compact, citation-friendly disclosure index."""
    items = payload.get("items", [])
    if not isinstance(items, list):
        items = []
    selected: list[dict[str, Any]] = []
    for row in items:
        if not isinstance(row, dict):
            continue
        report_nm = str(row.get("report_nm", ""))
        if major_only and not MAJOR_DISCLOSURE_RE.search(report_nm):
            continue
        rcp = row.get("rcept_no")
        selected.append(
            {
                "rcept_dt": row.get("rcept_dt"),
                "report_nm": report_nm,
                "rcept_no": rcp,
                "url": f"https://dart.fss.or.kr/dsaf001/main.do?rcpNo={rcp}" if rcp else None,
            }
        )
    selected.sort(key=lambda row: str(row.get("rcept_dt") or ""), reverse=True)
    return {
        "ticker": payload.get("ticker"),
        "corp_code": payload.get("corp_code"),
        "corp_name": payload.get("corp_name"),
        "since_days": payload.get("since_days"),
        "count_raw": len(items),
        "count_selected": len(selected),
        "limit": limit,
        "major_only": major_only,
        "items": selected[:limit],
        "_note": "공시 전체 원문 목록은 disclosures raw JSON 에 있고, research 작성 시에는 이 summary 우선 사용.",
        "_fetched_at": payload.get("_fetched_at"),
    }


def _fnltt_acnt_all(corp_code: str, year: int, reprt_code: str = "11011", fs_div: str = "CFS") -> dict[str, Any]:
    """fnlttSinglAcntAll.json — 한 (corp, 연도, 보고서) 의 전체 계정 dump."""
    j = _api_get(
        "fnlttSinglAcntAll.json",
        {
            "corp_code": corp_code,
            "bsns_year": str(year),
            "reprt_code": reprt_code,
            "fs_div": fs_div,
        },
    )
    return j


def financials(
    ticker: str,
    years: int = 5,
    fs_div: str = "CFS",
    reprt_code: str = "11011",
    meta: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """N년 사업보고서 재무제표 (연결 CFS 기본).

    DART OpenAPI `fnlttSinglAcntAll` 직접 호출. dart-fss `extract_fs` wrapper 가
    빈 결과 반환하는 문제 우회.
    """
    meta = _meta_or_resolve(ticker, meta)
    if "error" in meta:
        return meta
    cur_year = dt.date.today().year
    # 사업보고서(11011)는 보통 다음 해 3월 공시된다. 현재연도 대신
    # 최근 완료 회계연도까지의 years개를 기본 조회해 6개년 출력 혼선을 막는다.
    end_year = cur_year - 1
    start_year = end_year - years + 1
    statements: dict[str, Any] = {}
    for year in range(start_year, end_year + 1):
        try:
            j = _fnltt_acnt_all(meta["corp_code"], year, reprt_code, fs_div)
        except requests.HTTPError as exc:
            statements[str(year)] = {"_error": str(exc)}
            continue
        status = j.get("status")
        if status == "013":
            statements[str(year)] = {"_status": "013 (no data)"}
            continue
        if status != "000":
            statements[str(year)] = {"_status": f"{status} {j.get('message')}"}
            continue
        statements[str(year)] = {
            "fs_div": fs_div,
            "reprt_code": reprt_code,
            "accounts": j.get("list", []),
        }
    return {
        "ticker": ticker,
        "corp_code": meta["corp_code"],
        "corp_name": meta["corp_name"],
        "fs_div": fs_div,
        "reprt_code": reprt_code,
        "years": f"{start_year}~{end_year}",
        "statements_by_year": statements,
        "_fetched_at": dt.datetime.now().isoformat(),
    }


def business(ticker: str, meta: dict[str, Any] | None = None) -> dict[str, Any]:
    """최근 사업보고서 (pblntf_detail_ty=A001) 메타 + URL.

    본문 segment/지역/고객 텍스트는 호출 측이 URL 을 WebFetch/firecrawl 로 추출.
    """
    meta = _meta_or_resolve(ticker, meta)
    if "error" in meta:
        return meta
    rows = _list_range(meta["corp_code"], days=400, pblntf_detail_ty="A001")
    items = []
    for r in rows:
        rcp = r.get("rcept_no")
        items.append(
            {
                "rcept_no": rcp,
                "rcept_dt": r.get("rcept_dt"),
                "report_nm": r.get("report_nm"),
                "url": f"https://dart.fss.or.kr/dsaf001/main.do?rcpNo={rcp}" if rcp else None,
            }
        )
    return {
        "ticker": ticker,
        "corp_code": meta["corp_code"],
        "corp_name": meta["corp_name"],
        "annual_reports": items,
        "_note": "사업·segment·지역 매출은 URL 의 사업보고서를 WebFetch 로 추출하세요.",
        "_fetched_at": dt.datetime.now().isoformat(),
    }


SECTIONS = {
    "identity": lambda t, a: identity(t),
    "disclosures": lambda t, a: disclosures(t, days=a.days),
    "financials": lambda t, a: financials(t, years=a.years, fs_div=a.fs_div, reprt_code=a.reprt_code),
    "business": lambda t, a: business(t),
}


# 핵심 손익·CF·BS account_nm 정규식 — summary 모드용
SUMMARY_ACCOUNT_RE = (
    "매출|영업수익|수익\\(매출액\\)|"
    "매출원가|매출총이익|"
    "판매비와관리비|영업이익|영업이익\\(손실\\)|"
    "법인세비용차감전순이익|당기순이익|당기순이익\\(손실\\)|"
    "EBITDA|감가상각|상각|"
    "자산총계|부채총계|자본총계|"
    "유동자산|비유동자산|유동부채|비유동부채|"
    "매출채권|재고자산|매입채무|"
    "이익잉여금|"
    "영업활동.*현금흐름|"
    "투자활동.*현금흐름|"
    "재무활동.*현금흐름|"
    "유형자산.*취득|무형자산.*취득|"
    "현금및현금성자산|"
    "배당|자기주식|"
    "기본주당.*이익|희석주당.*이익|기본주당순이익"
)


def _summarize_financials(fin: dict[str, Any]) -> dict[str, Any]:
    """5년 시계열을 핵심 account 만 추린 평탄화 dict 로 반환.

    {"매출액": {"2021": x, "2022": y, ...}, ...}
    """
    import re as _re
    pattern = _re.compile(f"({SUMMARY_ACCOUNT_RE})")
    series: dict[str, dict[str, str]] = {}
    for year, payload in fin.get("statements_by_year", {}).items():
        accounts = payload.get("accounts", []) if isinstance(payload, dict) else []
        for acc in accounts:
            name = acc.get("account_nm", "")
            if pattern.match(name):
                series.setdefault(name, {})[year] = acc.get("thstrm_amount")
    return {
        "ticker": fin.get("ticker"),
        "corp_code": fin.get("corp_code"),
        "corp_name": fin.get("corp_name"),
        "fs_div": fin.get("fs_div"),
        "years": fin.get("years"),
        "series": series,
        "_note": "핵심 account 만 추림. 전체는 --section financials (no --summary) 로 fetch.",
        "_fetched_at": fin.get("_fetched_at"),
    }


def main() -> None:
    p = argparse.ArgumentParser(description="DART data fetcher (OpenAPI direct)")
    p.add_argument("ticker")
    p.add_argument("--section", choices=sorted(SECTIONS) + ["all"],
                   help="단일 섹션 / 'all' = identity+financials+disclosures+business 한 번에")
    p.add_argument("--out", type=Path,
                   help="단일 섹션 출력 파일. --section all 시 무시 (--out-dir 사용)")
    p.add_argument("--out-dir", type=Path,
                   help="--section all 시 4개 JSON 저장할 폴더. {ticker}_{section}.json 으로 생성")
    p.add_argument("--days", type=int, default=365)
    p.add_argument("--years", type=int, default=5)
    p.add_argument("--fs-div", choices=["CFS", "OFS"], default="CFS", dest="fs_div",
                   help="CFS=연결, OFS=별도 (financials)")
    p.add_argument("--reprt-code", choices=list(REPRT_CODES), default="11011", dest="reprt_code",
                   help="11011=사업, 11012=반기, 11013=1Q, 11014=3Q (financials)")
    p.add_argument("--summary", action="store_true",
                   help="financials: 200+ accounts 대신 핵심 30개만 평탄화. 토큰 -50%%+")
    p.add_argument("--disclosure-limit", type=int, default=50,
                   help="--section all 에서 함께 쓰는 disclosures summary 최대 건수")
    p.add_argument("--major-only", action="store_true",
                   help="disclosures summary 를 주요/정기/자본거래성 공시로 필터링")
    args = p.parse_args()

    if not args.section:
        p.error("--section required")

    if args.section == "all":
        if not args.out_dir:
            p.error("--section all 은 --out-dir 필요")
        args.out_dir.mkdir(parents=True, exist_ok=True)
        results: dict[str, dict[str, Any]] = {}
        meta = _resolve_corp_code(args.ticker)
        for sec in ("identity", "financials", "disclosures", "business"):
            if "error" in meta:
                data = meta
            elif sec == "identity":
                data = identity(args.ticker, meta=meta)
            elif sec == "financials":
                data = financials(args.ticker, years=args.years, fs_div=args.fs_div, reprt_code=args.reprt_code, meta=meta)
            elif sec == "disclosures":
                data = disclosures(args.ticker, days=args.days, meta=meta)
            else:
                data = business(args.ticker, meta=meta)
            if sec == "financials" and args.summary and "statements_by_year" in data:
                data = _summarize_financials(data)
            out = args.out_dir / f"{args.ticker}_{sec}.json"
            out.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
            results[sec] = {"path": str(out), "error": data.get("error")}
            print(f"wrote {out}")
            if sec == "disclosures" and "items" in data:
                summary = summarize_disclosures(data, limit=args.disclosure_limit, major_only=args.major_only)
                summary_out = args.out_dir / f"{args.ticker}_disclosures_summary.json"
                summary_out.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
                print(f"wrote {summary_out}")
        if any(r["error"] for r in results.values()):
            sys.exit(1)
        return

    fn = SECTIONS[args.section]
    data = fn(args.ticker, args)
    if args.section == "financials" and args.summary and "statements_by_year" in data:
        data = _summarize_financials(data)
    if not args.out:
        p.error("--out required for single section")
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    if "error" in data:
        print(f"WARN: {data['error']}", file=sys.stderr)
        sys.exit(1)
    print(f"wrote {args.out}")


if __name__ == "__main__":
    main()
