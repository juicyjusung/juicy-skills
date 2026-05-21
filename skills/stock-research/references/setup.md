# Setup 가이드 — Stock Research

처음 실행 전 1회 셋업. 전체 무료 가능.

## 1. API Key 발급 (5분, 전부 무료)

### 1.1 OPEN DART (한국 공시)
- URL: https://opendart.fss.or.kr/uss/umt/cmm/EgovMberInsertView.do
- 가입 → API 키 신청 → 즉시 발급
- 한도: 1,000회/분, 20,000회/일
- 환경변수: `OPEN_DART_API_KEY`

### 1.2 Financial Modeling Prep (미국 재무)
- URL: https://site.financialmodelingprep.com/developer/docs
- 무료 티어 250회/일
- 환경변수: `FMP_API_KEY`
- **주의**: 2024년 이후 신규 가입자는 `/api/v3/` legacy endpoint 차단됨. 본 스킬의 `fetch_fmp.py` 는 `/stable/` 신규 endpoint 사용.

### 1.3 FRED (미국 거시)
- URL: https://fred.stlouisfed.org/docs/api/api_key.html
- 즉시 발급, 무제한
- 환경변수: `FRED_API_KEY`

### 1.4 한국은행 ECOS (한국 거시)
- URL: https://ecos.bok.or.kr/api/
- 신청 후 1영업일 내 발급
- 환경변수: `BOK_ECOS_API_KEY`

### 환경변수 설정 (zsh)
```bash
# ~/.zshrc 또는 ~/.zprofile 에 추가
export OPEN_DART_API_KEY="..."
export FMP_API_KEY="..."
export FRED_API_KEY="..."
export BOK_ECOS_API_KEY="..."
```

또는 프로젝트 루트 `.env` 파일:
```
OPEN_DART_API_KEY=...
FMP_API_KEY=...
FRED_API_KEY=...
BOK_ECOS_API_KEY=...
```

## 2. Python 실행 환경 — uv

본 스킬은 **uv** 사용 전제. `pip install` 불필요. 각 fetch script 는 PEP 723 inline metadata 로 의존성 선언 → `uv run` 이 캐시된 venv 에 자동 설치·실행.

### 2.1 uv 설치 (한 번만)
```bash
# macOS
brew install uv
# 또는
curl -LsSf https://astral.sh/uv/install.sh | sh
```

확인:
```bash
uv --version   # uv 0.4+ 권장
```

### 2.2 스크립트 실행 방법

세 가지 모두 동일:
```bash
# 1) uv run (권장)
SKILL_DIR=.claude/skills/stock-research
uv run --env-file .env $SKILL_DIR/scripts/fetch_dart.py 005930 --section identity --out _evidence/identity.json

# 2) 직접 실행 (스크립트 shebang 사용)
chmod +x $SKILL_DIR/scripts/fetch_*.py
$SKILL_DIR/scripts/fetch_dart.py 005930 --section identity --out _evidence/identity.json

# 3) .env 자동 로드 + 실행
uv run --env-file .env $SKILL_DIR/scripts/fetch_dart.py 005930 --section identity --out _evidence/identity.json
```

첫 실행 시 uv 가 의존성 다운로드 후 캐싱 (~10초). 이후 즉시 실행 (~1초).

### 2.3 각 script 가 끌어쓰는 패키지

| Script | 의존 (PEP 723 명시) | 용도 |
|---|---|---|
| `fetch_dart.py` | `dart-fss`, `requests`, `python-dotenv` | DART 공시·재무 |
| `fetch_pykrx.py` | `pykrx`, `pandas` | KRX 시세·비율 |
| `fetch_edgar.py` | `edgartools`, `pandas` | SEC EDGAR XBRL |
| `fetch_fmp.py` | `requests`, `python-dotenv` | FMP 미국 재무 |
| `normalize_financials.py` | (stdlib only) | 원자료 → canonical 재무 metric |
| `evidence_manifest.py` | (stdlib only) | 원자료 file hash/source/fetched_at index |
| `evidence_brief.py` | (stdlib only) | manifest/canonical 기반 작성용 compact brief |
| `lint_research.py` | (stdlib only) | 객관성 lint |
| `detect_market.py` | (stdlib only) | KR/US 판별 |

stdlib-only 스크립트(`detect_market.py`, `normalize_financials.py`, `evidence_manifest.py`, `evidence_brief.py`, `lint_research.py`)는 `python3 $SKILL_DIR/scripts/...` 로도 직접 실행 가능.

## 3. MCP 서버 설치 (선택, Claude 컨텍스트 절약)

### 3.1 Korean Stock MCP (DART+KRX 통합)
```bash
claude mcp add korean-stock npx korean-stock-mcp
# 또는 GitHub clone 후 로컬 경로
```
참조: https://fastmcp.me/MCP/Details/1279/korean-stock-market-dart-krx

### 3.2 Yahoo Finance MCP (미국)
```bash
claude mcp add yahoo-finance npx @alex2yang/yahoo-finance-mcp
```
참조: https://github.com/Alex2Yang97/yahoo-finance-mcp

### 3.3 (선택) Alpha Vantage MCP
```bash
claude mcp add alpha-vantage npx @alphavantage/mcp
# ALPHAVANTAGE_API_KEY 필요
```

MCP 설치 확인:
```bash
claude mcp list
```

## 4. 검증 (sanity check)

uv 와 4개 API key 셋업 끝났는지 한 줄씩 확인:

```bash
# 한국 시세 (pykrx, 무인증)
uv run --with pykrx python3 -c "from pykrx import stock; print(stock.get_market_ohlcv('20260101','20260121','005930').head())"

# 미국 공시 (edgartools, 무인증)
uv run --with edgartools python3 -c "from edgar import Company; print(Company('AAPL').name)"

# DART (API key 필요)
uv run --env-file .env --with dart-fss python3 -c "import os, dart_fss as ds; ds.set_api_key(api_key=os.environ['OPEN_DART_API_KEY']); print(ds.get_corp_list().find_by_corp_name('삼성전자')[0])"

# FMP (API key 필요, /stable/ endpoint)
uv run --env-file .env --with requests python3 -c "import os, requests; r = requests.get('https://financialmodelingprep.com/stable/profile', params={'symbol':'AAPL','apikey':os.environ['FMP_API_KEY']}).json(); print(r[0]['symbol'], r[0]['marketCap'])"

# FRED (API key 필요)
uv run --env-file .env --with requests python3 -c "import os, requests; r = requests.get('https://api.stlouisfed.org/fred/series', params={'series_id':'GDP','api_key':os.environ['FRED_API_KEY'],'file_type':'json'}).json(); print(r['seriess'][0]['title'])"

# 한국은행 ECOS (API key 필요)
uv run --env-file .env --with requests python3 -c "import os, requests; k=os.environ['BOK_ECOS_API_KEY']; r=requests.get(f'https://ecos.bok.or.kr/api/StatisticTableList/{k}/json/kr/1/1').json(); print('rows', len(r.get('StatisticTableList',{}).get('row',[])))"
```

모두 출력 정상이면 준비 완료.

## 5. 트러블슈팅

| 증상 | 원인 | 해결 |
|---|---|---|
| `KeyError: 'OPEN_DART_API_KEY'` | env 미설정 | `uv run --env-file .env ...` 사용 또는 shell export |
| `dart-fss` SSL 에러 | 인증서 누수 | `uv run --with certifi --upgrade ...` 또는 macOS `Install Certificates.command` 실행 |
| `pykrx` 가격 None | 휴장일·상장폐지·미래일자 | 영업일 확인, `_last_trading_day` 가 30일 walk-back |
| `pykrx` "KRX 로그인 실패" + 시총·재무비율 0건 | 일부 pykrx 엔드포인트(`get_market_cap`, `get_market_fundamental`)가 최근 KRX 로그인 필요 | `KRX_ID`/`KRX_PW` 환경변수 설정, 또는 `FinanceDataReader` fallback. `get_market_ohlcv` 는 무인증 정상 |
| `edgartools` 회사 못 찾음 | 티커 변경·delisting | CIK 직접 사용 |
| MCP `command not found` | npm/npx 미설치 | `brew install node` |
| `uv: command not found` | uv 미설치 | `brew install uv` 또는 `curl -LsSf https://astral.sh/uv/install.sh \| sh` |
| FMP `Legacy Endpoint` 403 | 신규 키에 v3 사용 | `fetch_fmp.py` 가 `/stable/` 사용. 직접 호출 시 base 갱신 |

## 6. 미설치 환경에서 진행

API key 일부만 있어도 스킬 동작 가능:
- DART key 없음 → 한국 종목 fetch 시 사용자에게 안내 + `_evidence_gap` 표기 후 시세·뉴스로만 작성
- FMP key 없음 → yfinance/EDGAR fallback
- FRED key 없음 → 매크로 섹션 skip

스킬은 가능한 부분만 채우고 빠진 부분 명시 — **추측 금지**.
