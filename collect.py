#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""hometrack 수집기 — 공공 API → data/*.json  (SPEC v1.2 §3-5 · §3-6)

표준 라이브러리만 사용한다. pip 의존성을 만들지 않는다.

사용법
    python collect.py              # 실수집. 환경변수 DATA_GO_KR_KEY 필요
    python collect.py --fixture    # data/fixtures/ 의 응답 샘플로 오프라인 수집 (D23)

원칙 (CLAUDE.md §4 · SPEC §0)
    - API 키는 환경변수로만 읽고, 로그·JSON·예외 문자열에 남기지 않는다 (D7 → mask_secret)
    - 수집기 단위 try/except. 실패하면 직전 데이터를 유지하고 meta.collectors[] 에 사유를 남긴다
    - LH 공고문 본문·자유서식에서 금액·면적을 정규식으로 긁지 않는다
    - 예산·자격 판정 로직은 여기에 두지 않는다 (화면 JS 담당). 여기서는 집계와 병합만 한다
"""

from __future__ import annotations

import argparse
import fnmatch
import hashlib
import json
import os
import re
import statistics
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from datetime import date, datetime, timedelta, timezone
from html.parser import HTMLParser
from pathlib import Path
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError


def _kst():
    """KST 시간대.

    zoneinfo 를 먼저 쓰되, Windows 처럼 시스템 tz 데이터베이스가 없는 환경에서는
    (`tzdata` 는 pip 패키지라 쓸 수 없다) 고정 오프셋으로 폴백한다.
    한국은 서머타임이 없어 UTC+9 고정값이 zoneinfo 와 동일한 결과를 준다.
    """
    try:
        return ZoneInfo("Asia/Seoul")
    except (ZoneInfoNotFoundError, KeyError, OSError):
        return timezone(timedelta(hours=9), "KST")


KST = _kst()
ROOT = Path(__file__).resolve().parent
DATA_DIR = ROOT / "data"
FIXTURE_DIR = DATA_DIR / "fixtures"
CONFIG_PATH = ROOT / "config.json"

ENV_KEY = "DATA_GO_KR_KEY"
USER_AGENT = "hometrack/1.0 (+https://github.com/) python-urllib"
HTTP_TIMEOUT = 20

HOUSING_TYPES = ("apt", "villa", "officetel")


# ---------------------------------------------------------------------------
# 0. 키 마스킹 (D7) — 저장·출력의 유일한 통로
# ---------------------------------------------------------------------------

_SERVICE_KEY_RE = re.compile(r"(?i)(service_?key)=[^&\s\"'\]}>]*")
_QUERY_RE = re.compile(r"(https?://[^\s\"'<>]+?)\?[^\s\"'<>]*")


def mask_secret(text):
    """serviceKey·요청 쿼리스트링을 마스킹한다.

    - 발급키 원문(환경변수 값)이 문자열에 있으면 지운다 (URL 인코딩된 형태 포함)
    - `serviceKey=...` 패턴을 `serviceKey=***` 로 치환한다
    - http(s) URL 의 쿼리스트링 전체를 `?***` 로 잘라낸다 (요청 URL 원문 출력 금지)
    """
    if text is None:
        return None
    s = text if isinstance(text, str) else str(text)
    key = os.environ.get(ENV_KEY) or ""
    if len(key) >= 8:
        s = s.replace(key, "***")
        s = s.replace(urllib.parse.quote(key, safe=""), "***")
        s = s.replace(urllib.parse.quote_plus(key), "***")
    s = _SERVICE_KEY_RE.sub(r"\1=***", s)
    s = _QUERY_RE.sub(r"\1?***", s)
    return s


def _init_stdio():
    """Windows 콘솔 기본 코드페이지(cp949)에서 한글·기호가 깨지지 않게 UTF-8 로 맞춘다."""
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, ValueError, OSError):
            pass


def log(msg):
    """모든 표준출력은 이 함수를 지난다."""
    print(mask_secret(msg), flush=True)


def describe_error(exc):
    """예외를 그대로 str() 하지 않는다 — urllib 예외는 요청 URL 을 노출한다 (D7)."""
    cls = type(exc).__name__
    if isinstance(exc, urllib.error.HTTPError):
        return mask_secret("%s %s %s" % (cls, exc.code, getattr(exc, "reason", "")))
    if isinstance(exc, urllib.error.URLError):
        return mask_secret("%s %s" % (cls, getattr(exc, "reason", "")))
    return mask_secret("%s: %s" % (cls, exc))


# ---------------------------------------------------------------------------
# 1. 유틸
# ---------------------------------------------------------------------------

def now_iso():
    return datetime.now(KST).isoformat(timespec="seconds")


def today_str():
    return datetime.now(KST).date().isoformat()


def read_json(path, default=None):
    try:
        with open(path, "r", encoding="utf-8") as fh:
            return json.load(fh)
    except FileNotFoundError:
        return default
    except (json.JSONDecodeError, OSError) as exc:
        log("경고: %s 를 읽지 못했다 — %s" % (path.name, describe_error(exc)))
        return default


def write_json(path, payload, newline="\n", indent=2):
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    with open(tmp, "w", encoding="utf-8", newline=newline) as fh:
        json.dump(payload, fh, ensure_ascii=False, indent=indent, sort_keys=False)
        fh.write("\n")
    tmp.replace(path)


_INDENT_RE = re.compile(r"^( +)\S", re.MULTILINE)


def detect_format(path, default_indent=2):
    """사람이 관리하는 파일을 다시 쓸 때 줄바꿈·들여쓰기를 바꾸지 않기 위해 확인한다.

    collect.py 가 policies.json 의 source_hash 두 필드만 고치는데 파일 전체가
    재포맷되면, 사람이 diff 로 실제 변경을 확인할 수 없다.
    """
    try:
        raw = path.read_bytes()
    except OSError:
        return "\n", default_indent
    # LF 전용 파일에 None 을 돌려주면 open(newline=None) 이 Windows 에서 \n → \r\n 으로
    # 번역해 파일 전체가 CRLF 로 재기록된다 (DEF-9). 감지한 줄바꿈을 그대로 돌려준다.
    newline = "\r\n" if b"\r\n" in raw else "\n"
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError:
        return newline, default_indent
    matched = _INDENT_RE.search(text.replace("\r\n", "\n"))
    indent = len(matched.group(1)) if matched else default_indent
    return newline, indent


def to_int(value, default=None):
    """'15,000' · ' 84.9 ' · 15000 → int. 실패하면 default."""
    if value is None:
        return default
    if isinstance(value, bool):
        return default
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        return int(round(value))
    s = str(value).replace(",", "").replace(" ", "").strip()
    if not s:
        return default
    try:
        return int(round(float(s)))
    except ValueError:
        return default


def to_float(value, default=None):
    if value is None:
        return default
    s = str(value).replace(",", "").replace(" ", "").strip()
    if not s:
        return default
    try:
        return float(s)
    except ValueError:
        return default


def month_str(d):
    return "%04d%02d" % (d.year, d.month)


def shift_month(d, delta):
    total = d.year * 12 + (d.month - 1) + delta
    return date(total // 12, total % 12 + 1, 1)


def recent_months(today, count):
    """당월을 마지막으로 하는 최근 count 개월의 YYYYMM 오름차순 배열."""
    base = date(today.year, today.month, 1)
    return [month_str(shift_month(base, -i)) for i in range(count - 1, -1, -1)]


def percentile(sorted_values, pct):
    """선형 보간 분위수. sorted_values 는 오름차순 정렬된 수치 배열."""
    if not sorted_values:
        return None
    if len(sorted_values) == 1:
        return float(sorted_values[0])
    pos = (len(sorted_values) - 1) * pct
    low = int(pos)
    high = min(low + 1, len(sorted_values) - 1)
    frac = pos - low
    return sorted_values[low] * (1 - frac) + sorted_values[high] * frac


def sha1_hex(text):
    return hashlib.sha1(text.encode("utf-8")).hexdigest()


# ---------------------------------------------------------------------------
# 2. 수집기 기록 (meta.collectors[])
# ---------------------------------------------------------------------------

class CollectorRun:
    """수집기 하나의 실행 기록. status·error·duration 을 스키마대로 남긴다 (§3-6, D8)."""

    def __init__(self, key, name, source, kind, note=None, list_url=None):
        self.key = key
        self.record = {
            "key": key,
            "name": name,
            "source": source,
            "kind": kind,
            "status": "ok",
            "last_success": None,
            "item_count": 0,
            "error": None,
            "duration_ms": 0,
            "note": note,
            "list_url": list_url,
            "registered_at": None,
            "detail_registered_at": None,
        }
        self._t0 = time.monotonic()

    # -- 상태 --------------------------------------------------------------
    def skip(self, reason):
        self.record["status"] = "skip"
        self.record["error"] = mask_secret(reason)

    def fail(self, exc_or_reason):
        self.record["status"] = "fail"
        if isinstance(exc_or_reason, BaseException):
            self.record["error"] = describe_error(exc_or_reason)
        else:
            self.record["error"] = mask_secret(exc_or_reason)

    def add_note(self, text):
        existing = self.record.get("note")
        self.record["note"] = ("%s · %s" % (existing, text)) if existing else text

    def finish(self, prev_by_key):
        self.record["duration_ms"] = int((time.monotonic() - self._t0) * 1000)
        if self.record["status"] == "ok":
            self.record["last_success"] = now_iso()
        else:
            prev = prev_by_key.get(self.key) or {}
            self.record["last_success"] = prev.get("last_success")
        return self.record

    @property
    def ok(self):
        return self.record["status"] == "ok"


# ---------------------------------------------------------------------------
# 3. HTTP / fixture 전송 계층
# ---------------------------------------------------------------------------

# --fixture-scenario — 오류 봉투 재현 경로를 코드로 고정한다 (DEF-1 · DEF-2).
# 값 = {fixture 파일명 glob: 대체할 fixture 파일명}
FIXTURE_SCENARIOS = {
    "normal": {},
    "trades_error": {"trades_*.xml": "error_trades_auth.xml"},
    "trades_no_result_code": {"trades_*.xml": "error_trades_no_result_code.xml"},
    "trades_count_mismatch": {"trades_*.xml": "error_trades_count_mismatch.xml"},
    "lh_error": {"lh_notice_list.json": "error_lh_auth.json"},
    "lh_empty": {"lh_notice_list.json": "error_lh_empty.json"},
    "lh_zero": {"lh_notice_list.json": "error_lh_zero.json"},
}


class Transport:
    """실네트워크와 fixture 를 같은 인터페이스로 감춘다.

    fixture 모드는 파싱·병합·diff 경로를 실제와 같게 태우는 것이 목적이므로
    응답 본문만 파일에서 읽고 그 뒤 처리는 실수집과 동일하다 (D23).
    """

    def __init__(self, fixture, scenario="normal"):
        self.fixture = fixture
        self.scenario = scenario
        self.overrides = FIXTURE_SCENARIOS.get(scenario, {})
        self.calls = 0

    def _override(self, fixture_name):
        for pattern, replacement in self.overrides.items():
            if fnmatch.fnmatch(fixture_name, pattern):
                return replacement
        return None

    def get(self, url, params, fixture_name=None, fixture_empty=None):
        self.calls += 1
        if self.fixture:
            if fixture_name is None:
                raise RuntimeError("fixture 모드인데 fixture 파일명이 지정되지 않았다")
            override = self._override(fixture_name)
            if override:
                override_path = FIXTURE_DIR / override
                if not override_path.exists():
                    raise FileNotFoundError("시나리오 fixture 없음: %s" % override)
                return override_path.read_bytes()
            path = FIXTURE_DIR / fixture_name
            if path.exists():
                return path.read_bytes()
            if fixture_empty is not None:
                return fixture_empty
            raise FileNotFoundError("fixture 없음: %s" % fixture_name)
        query = urllib.parse.urlencode(params, doseq=True)
        request = urllib.request.Request(
            url + "?" + query, headers={"User-Agent": USER_AGENT}
        )
        with urllib.request.urlopen(request, timeout=HTTP_TIMEOUT) as resp:
            return resp.read()


def decode_body(raw):
    for encoding in ("utf-8", "cp949", "euc-kr"):
        try:
            return raw.decode(encoding)
        except UnicodeDecodeError:
            continue
    return raw.decode("utf-8", errors="replace")


# ---------------------------------------------------------------------------
# 4. 실거래 3종 (국토교통부 전월세) — §3-3 · §3-5 · D15
# ---------------------------------------------------------------------------

# 응답 필드명은 DATA_SOURCES §A-4 기준이며 ⚠️영문/국문 표기 중 어느 쪽이 오는지
# 원문 스키마와 대조하지 못했다. 두 계열을 모두 별칭으로 받는다.
TRADE_ALIASES = {
    "deposit": ("deposit", "보증금액", "보증금", "전세금액"),
    "rent": ("monthlyRent", "월세금액", "월세"),
    "area": ("excluUseAr", "전용면적"),
    "dong": ("umdNm", "법정동"),
    "year": ("dealYear", "계약년도", "년"),
    "month": ("dealMonth", "계약월", "월"),
    "day": ("dealDay", "계약일", "일"),
    "sgg": ("sggCd", "지역코드"),
    "build_year": ("buildYear", "건축년도"),
    "floor": ("floor", "층"),
}

EMPTY_TRADE_XML = (
    b"<response><header><resultCode>00</resultCode>"
    b"<resultMsg>NORMAL SERVICE</resultMsg></header>"
    b"<body><items/><numOfRows>0</numOfRows><pageNo>1</pageNo>"
    b"<totalCount>0</totalCount></body></response>"
)


def _field(item, logical):
    for name in TRADE_ALIASES[logical]:
        if name in item and item[name] not in (None, ""):
            return item[name]
    return None


def parse_trade_xml(raw, housing_type, lawd_cd, deal_ymd):
    """실거래 XML 응답 → (계약 배열, total_count, item 노드 수).

    **HTTP 200 은 성공이 아니다** (DEF-2). data.go.kr 계열은 인증 실패·트래픽 초과·
    파라미터 오류를 HTTP 200 + 표준 오류 봉투(`OpenAPI_ServiceResponse`/`cmmMsgHeader`/
    `returnAuthMsg`/`errMsg`)로 돌려준다. 그 봉투에는 `resultCode` 가 없어서
    "정상 + 0건" 으로 넘기면 집계가 빈 배열로 덮여 직전 데이터가 사라진다.
    따라서 오류 봉투와 `resultCode` 부재를 모두 실패로 본다.
    """
    text = decode_body(raw)
    try:
        root = ET.fromstring(text)
    except ET.ParseError as exc:
        raise RuntimeError("실거래 응답이 XML 이 아니다 — %s" % mask_secret(str(exc)))

    if root.tag == "OpenAPI_ServiceResponse" or root.find(".//cmmMsgHeader") is not None:
        detail = ""
        for tag in ("returnAuthMsg", "errMsg", "returnReasonCode"):
            detail = (root.findtext(".//" + tag) or "").strip()
            if detail:
                break
        raise RuntimeError(
            "실거래 API 오류 봉투(%s) — %s" % (root.tag, mask_secret(detail or "사유 미표기"))
        )

    result_code = (root.findtext(".//resultCode") or "").strip()
    result_msg = (root.findtext(".//resultMsg") or "").strip()
    if not result_code:
        raise RuntimeError("실거래 응답에 resultCode 가 없다 — 정상 응답으로 보지 않는다")
    if result_code not in ("00", "0", "000"):
        raise RuntimeError("실거래 API 오류 resultCode=%s %s" % (result_code, mask_secret(result_msg)))
    total_text = root.findtext(".//totalCount")
    total_count = to_int(total_text, 0) or 0

    contracts = []
    node_count = 0
    for node in root.iter("item"):
        node_count += 1
        item = {}
        for child in node:
            item[child.tag] = (child.text or "").strip()
        deposit = to_int(_field(item, "deposit"))
        if deposit is None:
            continue
        rent = to_int(_field(item, "rent"), 0) or 0
        year = to_int(_field(item, "year"))
        month = to_int(_field(item, "month"))
        ym = "%04d%02d" % (year, month) if year and month else deal_ymd
        contracts.append(
            {
                "ym": ym,
                "housing_type": housing_type,
                "lawd_cd": (str(_field(item, "sgg") or lawd_cd)).strip()[:5],
                "dong": (str(_field(item, "dong") or "")).strip(),
                "deposit": deposit,
                "rent": rent,
                "area": to_float(_field(item, "area")),
            }
        )
    return contracts, total_count, node_count


def classify_deal_type(deposit, rent, banjeonse_ratio):
    """§3-3. 월세 0 → 전세 / 보증금 >= 월세 × ratio → 반전세 / 그 외 월세."""
    if not rent:
        return "jeonse"
    if deposit >= rent * banjeonse_ratio:
        return "banjeonse"
    return "wolse"


def fixture_trade_targets():
    """fixture 파일명에서 (housing_type, lawd_cd, ym) 목록을 만든다.

    fixture 모드의 대상 구간을 오늘 날짜에서 계산하지 않는 이유: 날짜가 흐르면
    같은 fixture 로 다른 결과가 나와 '2회 연속 동일' 검수가 무의미해진다.
    """
    pattern = re.compile(r"^trades_(apt|villa|officetel)_(\d{5})_(\d{6})\.xml$")
    targets = []
    if not FIXTURE_DIR.exists():
        return targets
    for path in sorted(FIXTURE_DIR.glob("trades_*.xml")):
        matched = pattern.match(path.name)
        if matched:
            targets.append((matched.group(1), matched.group(2), matched.group(3)))
    return targets


def collect_trades(cfg, run, transport, service_key, cache):
    """실거래 3종 수집. 반환 = (계약 배열, 재수집 구간, 집계 대상 구간)."""
    trades_cfg = cfg.get("trades", {})
    endpoints = trades_cfg.get("endpoints", {})
    num_of_rows = int(trades_cfg.get("num_of_rows", 1000))
    max_pages = int(trades_cfg.get("max_pages", 200))
    today = datetime.now(KST).date()

    if transport.fixture:
        num_of_rows = int(trades_cfg.get("fixture_num_of_rows", num_of_rows))
        targets = fixture_trade_targets()
        window = sorted({ym for _, _, ym in targets})
        if not targets:
            run.skip("data/fixtures/ 에 trades_*.xml 이 없다")
            return [], [], window
    else:
        window = recent_months(today, int(cfg.get("trade_months", 12)))
        targets = [
            (housing_type, lawd, ym)
            for housing_type in HOUSING_TYPES
            for lawd in cfg.get("sigungu_codes", [])
            for ym in window
        ]

    refetch_count = int(trades_cfg.get("refetch_months", 2))
    refetch_window = set(window[-refetch_count:]) if refetch_count > 0 else set()
    cached_months = cache.get("months") or {}

    collected = {}
    refetched = set()
    for housing_type, lawd, ym in targets:
        cache_key = "%s:%s:%s" % (housing_type, lawd, ym)
        needs_fetch = (
            transport.fixture
            or ym in refetch_window
            or cache_key not in cached_months
        )
        if not needs_fetch:
            collected[cache_key] = cached_months[cache_key]
            continue

        endpoint = endpoints.get(housing_type)
        if not endpoint:
            raise RuntimeError("config.trades.endpoints.%s 가 비어 있다" % housing_type)

        items = []
        node_total = 0
        declared_total = None
        page = 1
        while page <= max_pages:
            fixture_name = "trades_%s_%s_%s%s.xml" % (
                housing_type, lawd, ym, "" if page == 1 else "_p%d" % page
            )
            raw = transport.get(
                endpoint,
                {
                    "serviceKey": service_key,
                    "LAWD_CD": lawd,
                    "DEAL_YMD": ym,
                    "numOfRows": num_of_rows,
                    "pageNo": page,
                },
                fixture_name=fixture_name,
                fixture_empty=EMPTY_TRADE_XML,
            )
            batch, total_count, node_count = parse_trade_xml(raw, housing_type, lawd, ym)
            if declared_total is None:
                declared_total = total_count
            items.extend(batch)
            node_total += node_count
            if not node_count or page * num_of_rows >= total_count:
                break
            page += 1
        else:
            run.add_note("페이지 상한 %d 도달 (%s)" % (max_pages, cache_key))

        # totalCount 와 실제로 파싱한 item 수가 다르면 응답 구조가 바뀐 것이다 (DEF-2).
        # 조용히 적은 건수로 집계하면 중위값·히스토그램이 통째로 틀어진다.
        if declared_total is not None and node_total != declared_total and page <= max_pages:
            raise RuntimeError(
                "실거래 %s: totalCount %d 인데 파싱 %d건 — 응답 구조 불일치"
                % (cache_key, declared_total, node_total)
            )
        dropped = node_total - len(items)
        if dropped > 0:
            run.add_note("보증금 없는 계약 %d건 제외 (%s)" % (dropped, cache_key))

        collected[cache_key] = items
        refetched.add(ym)

    contracts = [c for items in collected.values() for c in items]
    # 전 구간 합계 0건은 성공이 아니다 (DEF-2). 캐시·집계를 갱신하지 않고 실패로 떨어뜨려
    # 직전 trades.json 을 그대로 유지한다.
    if not contracts:
        raise RuntimeError("실거래 전 구간 합계 0건 — 정상 응답으로 보지 않는다 (직전 집계 유지)")

    cache["months"] = collected
    cache["fetched_at"] = now_iso()
    return contracts, sorted(refetched), window


def build_dong_index(cfg):
    """법정동명 → 역 id 배열. 복수 역 중복 매핑 허용 (§3-4)."""
    index = {}
    for station in cfg.get("stations", []):
        for dong in station.get("dongs", []):
            index.setdefault(dong, []).append(station["id"])
    return index


def deposit_histogram(values, bucket):
    """만원 단위 보증금 히스토그램. 마지막 버킷은 hi: null 개방 (D6).

    count 합 == 전체 건수를 보장한다 (버킷 경계로 계약이 새지 않게 clamp).
    """
    if not values:
        return []
    lo0 = (min(values) // bucket) * bucket
    top = max(values)
    edges = []
    lo = lo0
    while lo <= top:
        edges.append(lo)
        lo += bucket
    if not edges:
        edges = [lo0]
    hist = [{"lo": lo, "hi": lo + bucket, "count": 0} for lo in edges]
    hist[-1]["hi"] = None
    last = len(hist) - 1
    for value in values:
        idx = int((value - lo0) // bucket)
        if idx < 0:
            idx = 0
        elif idx > last:
            idx = last
        hist[idx]["count"] += 1
    return hist


def aggregate_trades(contracts, cfg, window):
    """집계 키 = station_id + housing_type + deal_type (§3-3). 유형을 섞지 않는다."""
    dong_index = build_dong_index(cfg)
    banjeonse_ratio = to_float(cfg.get("banjeonse_ratio", 240), 240.0)
    conversion_rate = to_float(cfg.get("conversion_rate", 6.0), 6.0)
    bucket = int(cfg.get("deposit_hist_bucket", 500))
    window_set = set(window)

    groups = {}
    excluded = 0
    latest_ym = None
    for contract in contracts:
        if contract["ym"] not in window_set:
            continue
        if latest_ym is None or contract["ym"] > latest_ym:
            latest_ym = contract["ym"]
        station_ids = dong_index.get(contract["dong"])
        if not station_ids:
            excluded += 1
            continue
        deal_type = classify_deal_type(contract["deposit"], contract["rent"], banjeonse_ratio)
        for station_id in station_ids:
            groups.setdefault((station_id, contract["housing_type"], deal_type), []).append(contract)

    updated_at = now_iso()
    aggregates = []
    for (station_id, housing_type, deal_type) in sorted(groups):
        rows = groups[(station_id, housing_type, deal_type)]
        deposits = sorted(row["deposit"] for row in rows)
        rents = sorted(row["rent"] for row in rows if row["rent"])
        # 계약별 전세환산액의 중위 — 중위값들을 환산한 값이 아니다 (D17)
        equivalents = sorted(
            row["deposit"] + row["rent"] * 12 * 100.0 / conversion_rate for row in rows
        )
        monthly = []
        for ym in window:
            month_rows = [row for row in rows if row["ym"] == ym]
            if not month_rows:
                continue
            monthly.append(
                {
                    "ym": ym,
                    "count": len(month_rows),
                    "deposit_median": int(round(statistics.median(row["deposit"] for row in month_rows))),
                }
            )
        aggregates.append(
            {
                "station_id": station_id,
                "housing_type": housing_type,
                "deal_type": deal_type,
                "months": len(window),
                "count": len(rows),
                "deposit_median": int(round(statistics.median(deposits))),
                "deposit_p25": int(round(percentile(deposits, 0.25))),
                "deposit_p75": int(round(percentile(deposits, 0.75))),
                "deposit_hist": deposit_histogram(deposits, bucket),
                "rent_median": int(round(statistics.median(rents))) if rents else None,
                "jeonse_equiv_median": int(round(statistics.median(equivalents))),
                "monthly": monthly,
                "updated_at": updated_at,
            }
        )
    return aggregates, excluded, latest_ym


# ---------------------------------------------------------------------------
# 5. LH 분양임대공고문 조회 (15058530) — D1
# ---------------------------------------------------------------------------

EMPTY_LH_JSON = b'[{"resHeader":[{"SS_CODE":"Y","ALL_CNT":"0"}]},{"dsList":[]}]'

_LH_DETAIL_KEYS = (
    ("PAN_ID", ("panid", "pan_id")),
    ("CCR_CNNT_SYS_DS_CD", ("ccrcnntsysdscd", "ccr_cnnt_sys_ds_cd")),
    ("UPP_AIS_TP_CD", ("uppaistpcd", "upp_ais_tp_cd")),
    ("AIS_TP_CD", ("aistpcd", "ais_tp_cd")),
    ("SPL_INF_TP_CD", ("splinftpcd", "spl_inf_tp_cd")),
)


def parse_lh_detail_url(url):
    """DTL_URL 에서 상세 API 파라미터를 뽑는다. PAN_ID 는 응답 필드가 아니다 (§E-1-2).

    두 형태를 모두 처리한다.
      A) ...&gv_param=CCR_CNNT_SYS_DS_CD:02,PAN_ID:0000059133,LCC:Y   (콜론·콤마)
      B) ...selectWrtancInfo.do?panId=2015122300018495&ccrCnntSysDsCd=03&uppAisTpCd=06
    """
    found = {}
    if not url:
        return found
    try:
        query = urllib.parse.urlsplit(url).query
    except ValueError:
        return found
    flat = {}
    for key, values in urllib.parse.parse_qs(query, keep_blank_values=False).items():
        if values:
            flat[key.lower()] = values[0]

    for canonical, aliases in _LH_DETAIL_KEYS:
        for alias in aliases:
            if alias in flat:
                found[canonical] = flat[alias].strip()
                break

    gv_param = flat.get("gv_param")
    if gv_param:
        for token in gv_param.split(","):
            name, sep, value = token.partition(":")
            if not sep:
                continue
            name = name.strip().upper()
            value = value.strip()
            if name and value:
                found.setdefault(name, value)
    return {k: v for k, v in found.items() if v}


def lh_extract_items(payload):
    """응답 봉투 형태가 실호출로 확정되지 않았다 (§E-8).

    구조를 가정하지 않고 `PAN_NM` 을 가진 dict 를 전부 모은다. ALL_CNT 도 함께 찾는다.
    """
    items = []
    all_count = 0

    def walk(node):
        nonlocal all_count
        if isinstance(node, dict):
            if "ALL_CNT" in node:
                value = to_int(node.get("ALL_CNT"), 0) or 0
                all_count = max(all_count, value)
            if "PAN_NM" in node:
                items.append(node)
                return
            for value in node.values():
                walk(value)
        elif isinstance(node, list):
            for value in node:
                walk(value)

    walk(payload)
    return items, all_count


_LH_MSG_KEYS = ("MSG", "SS_MSG", "ERR_MSG", "RS_MSG", "RESULT_MSG", "returnAuthMsg", "errMsg")


def lh_envelope_status(payload):
    """응답 봉투에서 (SS_CODE 목록, 사유 문자열) 을 뽑는다 (DEF-1).

    LH 계열은 인증 실패·파라미터 오류를 HTTP 200 + `SS_CODE:"N"` 으로 돌려준다.
    이 검사가 없으면 '공고 0건 수집 성공'이 되어 직전 공고 전건이 소멸로 뒤집힌다.
    """
    codes = []
    messages = []

    def walk(node):
        if isinstance(node, dict):
            if "SS_CODE" in node:
                codes.append(str(node.get("SS_CODE") or "").strip())
                for key in _LH_MSG_KEYS:
                    value = node.get(key)
                    if value:
                        messages.append(str(value).strip())
            for value in node.values():
                walk(value)
        elif isinstance(node, list):
            for value in node:
                walk(value)

    walk(payload)
    return codes, mask_secret(" · ".join(messages)[:200])


def check_lh_envelope(payload):
    """봉투가 정상이 아니면 예외. **200 OK 는 성공이 아니다** (DEF-1)."""
    codes, message = lh_envelope_status(payload)
    if not codes:
        raise RuntimeError("LH 응답에 SS_CODE 가 없다 — 정상 응답으로 보지 않는다")
    bad = [code for code in codes if code != "Y"]
    if bad:
        raise RuntimeError("LH 응답 오류 SS_CODE=%s %s" % (bad[0], message))


def promote_https(url):
    """원문 링크를 https 로 승격 시도한다 (DEF-14 · SPEC §3-6 `source_url: string|null`).

    문자열 치환만 한다 — 실제로 https 로 서비스되는지 요청을 보내 확인하지는 않는다.
    승격 후에도 https 가 아니면 링크를 싣지 않는다(null).
    """
    text = (url or "").strip()
    if not text:
        return None
    if text.startswith("https://"):
        return text
    if text.startswith("http://"):
        return "https://" + text[len("http://"):]
    return None


_GU_PATTERN_CACHE = {}


def _gu_pattern(gu_name):
    """구·군명을 낱말 경계에서만 매칭하는 정규식 (DEF-7).

    앞 = 문자열 시작 · 공백/구분기호 · `부산` / 뒤 = 한글 음절이 이어지지 않는다.
    어간 부분일치(`수영`·`사상`·`기장`)와 다른 시도 구명(`강남구` → `남구`)의
    오탐을 막는다. 잘못된 sigungu_code 는 복합 식별키 재료라 id 까지 오염시킨다.
    """
    pattern = _GU_PATTERN_CACHE.get(gu_name)
    if pattern is None:
        pattern = re.compile(
            r"(?:^|(?<=[\s()\[\]{},./·:;|~+\-])|(?<=부산))%s(?![가-힣])" % re.escape(gu_name)
        )
        _GU_PATTERN_CACHE[gu_name] = pattern
    return pattern


def match_busan_gu(cfg, *texts):
    """제목 등에서 부산 구·군명을 찾는다. 없으면 (None, None).

    목록 응답의 지역 축은 시도 단위(CNP_CD_NM = '부산광역시'|'전국')뿐이라
    구·군은 제목에서만 얻는다 (§E-1-5). 실패는 정상이며 null 을 허용한다 (§3-4).
    """
    table = cfg.get("busan_sigungu_codes", {})
    # 긴 이름 우선 — '강서구' 가 '서구' 로 잘리지 않게 한다
    names = sorted(
        (n for n in table if n.endswith("구") or n.endswith("군")), key=len, reverse=True
    )
    for text in texts:
        if not text:
            continue
        for gu_name in names:
            if _gu_pattern(gu_name).search(text):
                return gu_name, table[gu_name]
    return None, None


def region_accepted(cfg, region_name):
    allow = cfg.get("lh", {}).get("accept_region_names", [])
    if not allow:
        return True
    text = region_name or ""
    return any(token and token in text for token in allow)


def lh_to_notice(cfg, item, collected_at, today):
    title = (item.get("PAN_NM") or "").strip()
    detail_url = (item.get("DTL_URL") or "").strip()
    # M26 + DEF-14: http 는 https 로 승격 시도하고, 그래도 https 가 아니면 싣지 않는다
    source_url = promote_https(detail_url)
    supply_type = (item.get("AIS_TP_CD_NM") or item.get("UPP_AIS_TP_NM") or "").strip() or None
    gu_name, gu_code = match_busan_gu(cfg, title)
    detail_params = parse_lh_detail_url(detail_url)
    notice = {
        "id": None,
        "id_basis": None,
        "source": "LH",
        "entry_kind": "auto",
        "detail_level": "meta_only",
        "source_url": source_url,
        "title": title,
        "supply_type": supply_type,
        "sigungu_code": gu_code,
        "sigungu_name": gu_name,
        "dong_name": None,
        "station_ids": [],
        # 목록 응답에 금액·면적·접수기간 필드가 없다 (§E-1-5). 수동 등록으로만 채운다.
        "deposit_min": None,
        "deposit_max": None,
        "rent_min": None,
        "rent_max": None,
        "area_min": None,
        "area_max": None,
        "target_groups": [],
        "exclusions": [],
        "linked_policy_id": None,
        "apply_start": None,
        "apply_end": None,
        "notice_status": (item.get("PAN_SS") or "").strip() or None,
        "announced_at": None,
        "first_seen": today,
        "disappeared": False,
        "collected_at": collected_at,
    }
    notice["_notice_no"] = detail_params.get("PAN_ID")
    notice["_detail_params"] = detail_params
    # 복합키 재료 (DEF-4). 승격 전 DTL_URL 원문을 쓴다 — 승격 규칙이 바뀌면 id 가 흔들린다.
    notice["_detail_url"] = detail_url
    return notice


def collect_lh(cfg, run, transport, service_key):
    lh_cfg = cfg.get("lh", {})
    endpoint = lh_cfg.get("list_endpoint")
    if not endpoint:
        raise RuntimeError("config.lh.list_endpoint 가 비어 있다")

    today = datetime.now(KST).date()
    # 게시일 창 = 오늘 − trade_months 개월 ~ 오늘, 마감일 창 = 오늘 ~ 오늘 + lookahead_days.
    # PAN_NT_ST_DT·CLSG_DT 는 필수 요청 필터라 '전체 조회'가 없다 (§E-1-1).
    start_from = shift_month(date(today.year, today.month, 1), -int(cfg.get("trade_months", 12)))
    closing_to = today + timedelta(days=int(lh_cfg.get("lookahead_days", 365)))
    dot = lambda d: d.strftime("%Y.%m.%d")

    page_size = int(lh_cfg.get("PG_SZ", 100))
    max_pages = int(lh_cfg.get("max_pages", 50))
    regions = lh_cfg.get("region_queries") or [{}]
    upp_codes = lh_cfg.get("UPP_AIS_TP_CD") or [None]
    statuses = lh_cfg.get("PAN_SS") or [None]

    raw_items = []
    for region in regions:
        for upp in upp_codes:
            for status in statuses:
                page = 1
                while page <= max_pages:
                    params = {
                        "serviceKey": service_key,
                        "PG_SZ": page_size,
                        "PAGE": page,
                        "PAN_NT_ST_DT": dot(start_from),
                        "CLSG_DT": dot(closing_to),
                    }
                    if upp:
                        params["UPP_AIS_TP_CD"] = upp
                    if status:
                        params["PAN_SS"] = status
                    params.update({k: v for k, v in region.items() if v})
                    raw = transport.get(
                        endpoint,
                        params,
                        fixture_name="lh_notice_list.json",
                        fixture_empty=EMPTY_LH_JSON,
                    )
                    payload = json.loads(decode_body(raw))
                    # 200 OK 는 성공이 아니다 — 봉투를 먼저 본다 (DEF-1)
                    check_lh_envelope(payload)
                    batch, all_count = lh_extract_items(payload)
                    if all_count > 0 and not batch:
                        raise RuntimeError(
                            "LH ALL_CNT=%d 인데 파싱 0건 — 응답 봉투 구조가 바뀌었다" % all_count
                        )
                    raw_items.extend(batch)
                    if not batch or page * page_size >= all_count:
                        break
                    page += 1
                else:
                    run.add_note("페이지 상한 %d 도달" % max_pages)

    collected_at = now_iso()
    today_iso = today.isoformat()
    notices = []
    seen_signature = set()
    dropped_signatures = set()
    for item in raw_items:
        signature = (
            (item.get("PAN_NM") or "").strip(),
            (item.get("DTL_URL") or "").strip(),
            (item.get("AIS_TP_CD_NM") or "").strip(),
        )
        # 지역·유형·상태를 나눠 여러 번 조회하므로 중복이 정상이다.
        # 중복 제거를 지역 필터보다 먼저 해야 제외 건수가 조회 횟수만큼 부풀지 않는다 (DEF-8).
        if signature in seen_signature or signature in dropped_signatures:
            continue
        if not region_accepted(cfg, item.get("CNP_CD_NM")):
            dropped_signatures.add(signature)
            continue
        seen_signature.add(signature)
        notices.append(lh_to_notice(cfg, item, collected_at, today_iso))

    dropped_region = len(dropped_signatures)
    if dropped_region:
        run.add_note("부산·전국 외 지역 %d건 제외" % dropped_region)
    if not cfg.get("lh_detail_confirmed", False):
        run.add_note("상세 API(15057999) 미확인 — 금액·면적은 수동 등록")
    return notices


def collect_lh_detail(cfg, notice, transport, service_key):
    """상세 API 호출 골격. config.lh_detail_confirmed 가 true 일 때만 쓴다.

    🔴 응답에 임대보증금·월임대료·전용면적 필드가 있는지 실호출로 확인되지 않았다
    (DATA_SOURCES §E-1-4). 확인 전에는 호출하지 않고 detail_level: meta_only 를 유지한다.
    확인 후 SPEC §3-5 에 자동 승격 규칙이 추가되면 이 함수에서 금액·면적을 채운다.
    """
    if not cfg.get("lh_detail_confirmed", False):
        return None
    params = dict(notice.get("_detail_params") or {})
    required = ("PAN_ID", "CCR_CNNT_SYS_DS_CD", "UPP_AIS_TP_CD", "SPL_INF_TP_CD")
    if any(key not in params for key in required):
        return None
    params["serviceKey"] = service_key
    raw = transport.get(
        cfg["lh"]["detail_endpoint"],
        params,
        fixture_name="lh_notice_detail.json",
        fixture_empty=b"{}",
    )
    return json.loads(decode_body(raw))


# ---------------------------------------------------------------------------
# 6. 마이홈포털 공공주택 모집공고 (15108420) — 스키마 미확인
# ---------------------------------------------------------------------------

MYHOME_TITLE_KEYS = ("PAN_NM", "title", "ntcTitle", "rcritNtcNm", "bbsTtl", "공고명")
MYHOME_URL_KEYS = ("DTL_URL", "url", "detailUrl", "ntcUrl", "원문URL")
EMPTY_MYHOME_JSON = (
    b'{"response":{"header":{"resultCode":"00","resultMsg":"NORMAL SERVICE"},'
    b'"body":{"pageNo":1,"numOfRows":0,"totalCount":0,"items":[]}}}'
)


def myhome_extract_items(payload):
    """스키마 미확인이므로 제목처럼 보이는 키를 가진 dict 만 모은다. 파싱은 최소."""
    items = []

    def walk(node):
        if isinstance(node, dict):
            if any(key in node for key in MYHOME_TITLE_KEYS):
                items.append(node)
                return
            for value in node.values():
                walk(value)
        elif isinstance(node, list):
            for value in node:
                walk(value)

    walk(payload)
    return items


def first_value(item, keys):
    for key in keys:
        value = item.get(key)
        if value not in (None, ""):
            return str(value).strip()
    return None


def collect_myhome(cfg, run, transport, service_key):
    """호출 골격 + 원문 저장. 응답 스키마가 확정되기 전까지 파싱은 최소로 둔다."""
    myhome_cfg = cfg.get("myhome", {})
    endpoint = myhome_cfg.get("list_endpoint")
    if not endpoint and not transport.fixture:
        run.skip("마이홈 엔드포인트 미확인 (15108420 활용신청 후 확정)")
        return []

    max_calls = int(myhome_cfg.get("max_calls_per_run", 20))
    page_size = int(myhome_cfg.get("PG_SZ", 100))
    raw_pages = []
    page = 1
    while page <= max_calls:
        params = {"serviceKey": service_key, "pageNo": page, "numOfRows": page_size}
        params.update(myhome_cfg.get("params") or {})
        raw = transport.get(
            endpoint or "https://apis.data.go.kr/", params,
            fixture_name="myhome_notice_list.json",
            fixture_empty=EMPTY_MYHOME_JSON,
        )
        text = mask_secret(decode_body(raw))
        try:
            payload = json.loads(text)
        except json.JSONDecodeError:
            payload = {"_unparsed_text": text[:20000]}
        raw_pages.append(payload)
        batch = myhome_extract_items(payload)
        if len(batch) < page_size:
            break
        page += 1

    # 스키마 확정용 원문 저장 (키 마스킹 후)
    write_json(
        DATA_DIR / "raw_myhome_last.json",
        {
            "saved_at": now_iso(),
            "source": "국토교통부_마이홈포털 공공주택 모집공고 조회 서비스 (15108420)",
            "note": "응답 스키마 미확인. 스키마 확정용 원문 보관 파일이며 화면·판정에 쓰지 않는다. 인증키 마스킹 적용.",
            "fixture": transport.fixture,
            "pages": raw_pages,
        },
    )

    collected_at = now_iso()
    today_iso = today_str()
    notices = []
    for item in [row for page_payload in raw_pages for row in myhome_extract_items(page_payload)]:
        title = first_value(item, MYHOME_TITLE_KEYS)
        if not title:
            continue
        url = first_value(item, MYHOME_URL_KEYS)
        gu_name, gu_code = match_busan_gu(cfg, title)
        notices.append(
            {
                "id": None,
                "id_basis": None,
                "source": "MYHOME",
                "entry_kind": "auto",
                "detail_level": "meta_only",
                "source_url": promote_https(url),  # DEF-14
                "title": title,
                "supply_type": None,
                "sigungu_code": gu_code,
                "sigungu_name": gu_name,
                "dong_name": None,
                "station_ids": [],
                "deposit_min": None,
                "deposit_max": None,
                "rent_min": None,
                "rent_max": None,
                "area_min": None,
                "area_max": None,
                "target_groups": [],
                "exclusions": [],
                "linked_policy_id": None,
                "apply_start": None,
                "apply_end": None,
                "notice_status": None,
                "announced_at": None,
                "first_seen": today_iso,
                "disappeared": False,
                "collected_at": collected_at,
                "_notice_no": None,
                "_detail_url": url or "",
            }
        )
    run.add_note("응답 스키마 미확인 — 제목·링크만 최소 파싱, 원문은 data/raw_myhome_last.json")
    return notices


# ---------------------------------------------------------------------------
# 7. 공고 병합 · 식별키 · 신규/마감 판정 (§3-5, D8 · D12)
# ---------------------------------------------------------------------------

NOTICE_FIELDS = (
    "id", "id_basis", "source", "entry_kind", "detail_level", "source_url", "title",
    "supply_type", "sigungu_code", "sigungu_name", "dong_name", "station_ids",
    "deposit_min", "deposit_max", "rent_min", "rent_max", "area_min", "area_max",
    "target_groups", "exclusions", "linked_policy_id", "apply_start", "apply_end",
    "notice_status", "announced_at", "first_seen", "disappeared", "collected_at",
)


def normalize_title(text):
    return re.sub(r"\s+", "", text or "")


def composite_id(notice, level=0):
    """폴백 식별키. **배정 순서에 의존하지 않는 단일 산식**이다 (DEF-4 · §3-5).

    재료 = source | supply_type | apply_end | apply_start | sigungu_code
           | 정규화한 제목 | DTL_URL 원문(있으면)

    단계적 충돌 확장(level 0→1→2)을 없앤 이유: 확장은 배정 순서에 의존해서, 같은 구·같은
    공급유형 공고가 하나 늘면 정렬상 뒤로 밀린 기존 공고의 키가 바뀌고 같은 공고가
    '신규'와 '마감(추정)'으로 동시에 떴다. `level` 인자는 호출 호환을 위해 남겨 두며
    산식에 영향을 주지 않는다.
    """
    parts = [
        notice.get("source") or "",
        notice.get("supply_type") or "",
        notice.get("apply_end") or "",
        notice.get("apply_start") or "",
        notice.get("sigungu_code") or "",
        normalize_title(notice.get("title")),
        (notice.get("_detail_url") or "").strip(),
    ]
    return "%s:c%s" % (notice.get("source") or "?", sha1_hex("|".join(parts))[:12])


def _id_sort_key(notice):
    """식별키 배정 순서를 내용으로 고정한다.

    산식 자체는 순서에 의존하지 않지만, 재료가 완전히 같은 중복 공고에 붙는 `#N` 접미는
    순회 순서를 따르므로 내용 기준으로 정렬해 실행 간 흔들림을 막는다.
    """
    return (
        str(notice.get("_notice_no") or ""),
        notice.get("source") or "",
        notice.get("supply_type") or "",
        notice.get("apply_end") or "",
        notice.get("sigungu_code") or "",
        notice.get("apply_start") or "",
        normalize_title(notice.get("title")),
    )


def assign_notice_ids(notices):
    """1순위 `{source}:{공고번호}`, 폴백 복합키 해시 (DEF-4).

    재료가 완전히 같은 중복만 `#N` 접미로 갈라 놓는다 — 산식을 단계적으로 바꾸지 않는다.
    """
    used = set()
    for notice in sorted(notices, key=_id_sort_key):
        notice_no = notice.get("_notice_no")
        if notice_no:
            candidate = "%s:%s" % (notice["source"], str(notice_no).strip())
            basis = "notice_no"
        else:
            candidate = composite_id(notice)
            basis = "composite"
        base = candidate
        dup = 0
        while candidate in used:
            dup += 1
            candidate = "%s#%d" % (base, dup)
        used.add(candidate)
        notice["id"] = candidate
        notice["id_basis"] = basis
    return notices


def apply_policy_map(cfg, notice):
    """공급유형 → 정책 id 자동 부여 (§3-2). 표에 없으면 null 을 유지한다."""
    if notice.get("linked_policy_id"):
        return
    mapping = cfg.get("supply_type_policy_map") or {}
    haystacks = [notice.get("supply_type") or "", notice.get("title") or ""]
    for supply_type, policy_id in mapping.items():
        if any(supply_type and supply_type in text for text in haystacks):
            notice["linked_policy_id"] = policy_id
            return


def load_manual_notices(path, today_iso):
    """notices_manual.json — 사람이 채우는 파일. 없으면 빈 배열로 만들어 둔다."""
    if not path.exists():
        write_json(path, [])
        return [], True
    raw = read_json(path, None)
    if raw is None:
        return [], False
    if not isinstance(raw, list):
        log("경고: notices_manual.json 이 배열이 아니다 — 무시한다")
        return [], False
    entries = []
    for row in raw:
        if not isinstance(row, dict):
            continue
        entry = dict(row)
        entry["entry_kind"] = "manual"
        entry.setdefault("detail_level", "detailed")
        entry.setdefault("disappeared", False)
        entry.setdefault("first_seen", today_iso)
        entry.setdefault("collected_at", now_iso())
        entries.append(entry)
    return entries, True


def normalize_notice(notice):
    """SPEC §3-6 필드만 남기고 내부 필드(_ 접두)는 떨어낸다."""
    out = {}
    for field in NOTICE_FIELDS:
        value = notice.get(field)
        if field in ("station_ids", "target_groups", "exclusions"):
            value = list(value) if isinstance(value, (list, tuple)) else []
        elif field == "disappeared":
            value = bool(value)
        out[field] = value
    return out


def merge_notices(cfg, auto_notices, manual_notices, prev_notices, authoritative, today_iso):
    """자동 + 수동 병합 → 소멸 판정 → first_seen 승계.

    수집기가 실패·건너뜀이면 그 출처는 authoritative 가 아니므로 직전 데이터를
    그대로 유지하고 '소멸' 로 판정하지 않는다 (원칙 7).
    """
    merged = {}
    for notice in auto_notices:
        apply_policy_map(cfg, notice)
        merged[notice["id"]] = notice

    for entry in manual_notices:
        if not entry.get("id"):
            entry["_notice_no"] = entry.get("notice_no")
            assign_notice_ids([entry])
        apply_policy_map(cfg, entry)
        base = merged.get(entry["id"])
        if base:
            combined = dict(base)
            combined.update({k: v for k, v in entry.items() if v not in (None, [], "")})
            combined["entry_kind"] = "manual"
            combined["detail_level"] = "detailed"
            merged[entry["id"]] = combined
        else:
            entry.setdefault("id_basis", "composite")
            merged[entry["id"]] = entry

    prev_by_id = {n.get("id"): n for n in prev_notices if isinstance(n, dict) and n.get("id")}
    retain_days = int(cfg.get("notice_retain_days", 60))
    cutoff = (datetime.now(KST).date() - timedelta(days=retain_days)).isoformat()

    for notice_id, prev in prev_by_id.items():
        if notice_id in merged:
            continue
        entry_kind = prev.get("entry_kind") or "auto"
        source = prev.get("source")
        is_authoritative = (
            authoritative.get("manual", False)
            if entry_kind == "manual"
            else authoritative.get(source, False)
        )
        carried = dict(prev)
        if is_authoritative:
            carried["disappeared"] = True
        if carried.get("disappeared") and (carried.get("collected_at") or "") < cutoff:
            continue  # 오래된 소멸 공고는 잘라낸다
        merged[notice_id] = carried

    # first_seen 승계 (D8) — 없으면 오늘
    for notice_id, notice in merged.items():
        prev = prev_by_id.get(notice_id)
        if prev and prev.get("first_seen"):
            notice["first_seen"] = prev["first_seen"]
        elif not notice.get("first_seen"):
            notice["first_seen"] = today_iso

    ordered = sorted(merged.values(), key=lambda n: (n.get("source") or "", n.get("id") or ""))
    return [normalize_notice(n) for n in ordered], prev_by_id


def dday(apply_end, base_day):
    if not apply_end:
        return None
    try:
        end = date.fromisoformat(str(apply_end)[:10])
    except ValueError:
        return None
    return (end - base_day).days


def build_diff(cfg, notices, prev_by_id, prev_diff, collector_records, today):
    """snapshot_diff.json 을 만든다 (§3-6, D12)."""
    today_iso = today.isoformat()
    is_first_run = prev_diff is None and not prev_by_id

    new_notices = []
    if not is_first_run:
        new_notices = [
            n["id"] for n in notices
            if n["id"] not in prev_by_id and not n.get("disappeared")
        ]

    # D12 의 세 번째 마감 경로 — LH PAN_SS 가 접수마감 (DEF-5). 판정 문자열은 config 에 둔다.
    closed_statuses = set((cfg.get("lh") or {}).get("closed_statuses") or ["접수마감"])

    def is_status_closed(notice):
        status = (notice.get("notice_status") or "").strip()
        return bool(status) and status in closed_statuses

    closed_notices = []
    for notice in notices:
        if notice.get("disappeared"):
            closed_notices.append({"id": notice["id"], "reason": "disappeared"})
            continue
        if is_status_closed(notice):
            closed_notices.append({"id": notice["id"], "reason": "notice_status"})
            continue
        days = dday(notice.get("apply_end"), today)
        if days is not None and days < 0:
            closed_notices.append({"id": notice["id"], "reason": "apply_end"})

    # 이번 수집에서 새로 D-30 / D-7 안으로 들어온 것만 (D12)
    prev_day = None
    if prev_diff and prev_diff.get("date"):
        try:
            prev_day = date.fromisoformat(str(prev_diff["date"])[:10])
        except ValueError:
            prev_day = None
    thresholds = cfg.get("closing_soon_thresholds") or [30, 7]
    closing_soon = {}
    if not is_first_run:
        for notice in notices:
            if notice.get("disappeared") or is_status_closed(notice):
                continue  # 이미 마감으로 판정된 공고는 임박에 넣지 않는다 (D12)
            days = dday(notice.get("apply_end"), today)
            if days is None or days < 0:
                continue  # apply_end 가 null 이면 D-day 를 계산하지 않는다
            prev_days = dday(notice.get("apply_end"), prev_day) if prev_day else None
            was_known = notice["id"] in prev_by_id
            for threshold in thresholds:
                if days > threshold:
                    continue
                already_inside = (
                    was_known and prev_days is not None and 0 <= prev_days <= threshold
                )
                if already_inside:
                    continue
                current = closing_soon.get(notice["id"])
                if current is None or days < current:
                    closing_soon[notice["id"]] = days

    failures = []
    for record in collector_records:
        if record["status"] == "fail" or (record["status"] == "skip" and record["kind"] != "none"):
            failures.append(
                {
                    "key": record["key"],
                    "name": record["name"],
                    # SPEC §3-6 필수 — 화면이 '실패'와 '건너뜀' 문구를 구분할 유일한 근거 (DEF-3)
                    "status": record["status"],
                    "error": record["error"],
                    "last_success": record["last_success"],
                }
            )

    return {
        "date": today_iso,
        "is_first_run": is_first_run,
        "new_notices": sorted(new_notices),
        "closing_soon": [
            {"id": nid, "dday": closing_soon[nid]} for nid in sorted(closing_soon)
        ],
        "closed_notices": sorted(closed_notices, key=lambda row: row["id"]),
        "changed_policies": [],
        "collector_failures": failures,
    }


# ---------------------------------------------------------------------------
# 8. 정책 변경 감지 (§3-5, D14)
# ---------------------------------------------------------------------------

class IdTextExtractor(HTMLParser):
    """`id` 속성이 일치하는 첫 요소의 텍스트만 모은다. 선택자 문법은 지원하지 않는다."""

    def __init__(self, target_id):
        super().__init__(convert_charrefs=True)
        self.target_id = target_id
        self.depth = 0
        self.capturing = False
        self.done = False
        self.chunks = []

    def handle_starttag(self, tag, attrs):
        if self.done:
            return
        if self.capturing:
            self.depth += 1
            return
        for name, value in attrs:
            if name.lower() == "id" and value == self.target_id:
                self.capturing = True
                self.depth = 1
                return

    def handle_endtag(self, tag):
        if self.capturing and not self.done:
            self.depth -= 1
            if self.depth <= 0:
                self.capturing = False
                self.done = True

    def handle_data(self, data):
        if self.capturing and not self.done:
            self.chunks.append(data)

    @property
    def text(self):
        return "".join(self.chunks)


_TAG_RE = re.compile(r"(?is)<(script|style)[^>]*>.*?</\1>")
_ANY_TAG_RE = re.compile(r"(?s)<[^>]+>")
_DATE_RE = re.compile(r"\d{2,4}\s*[-./년]\s*\d{1,2}\s*[-./월]\s*\d{1,2}\s*일?")


def normalize_for_hash(text):
    """공백·숫자·날짜 패턴을 제거한다 — 방문자 수·갱신일 배너로 매일 변경되지 않게."""
    stripped = _DATE_RE.sub("", text)
    stripped = re.sub(r"\d", "", stripped)
    return re.sub(r"\s+", "", stripped)


def policy_content_hash(html_text, content_id):
    """(hash, basis). content_id 는 '#id' 하나만 받는다 (D14)."""
    if content_id:
        target = content_id[1:] if content_id.startswith("#") else content_id
        parser = IdTextExtractor(target)
        parser.feed(html_text)
        parser.close()
        text = parser.text
        if text.strip():
            return sha1_hex(re.sub(r"\s+", " ", text).strip()), "content_id"
    body = _ANY_TAG_RE.sub(" ", _TAG_RE.sub(" ", html_text))
    return sha1_hex(normalize_for_hash(body)), "normalized_text"


def collect_policies(cfg, run, transport):
    """policies.json 의 source_url 을 가져와 본문 해시를 비교한다.

    반환 = (changed_policies, policy_verified_latest, 정책 수)
    가져오기 실패는 해시를 갱신하지 않고 수집기를 fail 로 남긴다 (원칙 4).
    """
    path = DATA_DIR / "policies.json"
    policies = read_json(path, None)
    if policies is None:
        run.skip("data/policies.json 없음 — 정책 데이터 이관 전")
        return [], None, 0
    if not isinstance(policies, list):
        run.fail("data/policies.json 이 배열이 아니다")
        return [], None, 0

    # 배열 첫 요소가 id 없는 _meta 성 객체일 수 있다 — id 없는 항목은 건너뛴다
    rows = [p for p in policies if isinstance(p, dict) and p.get("id")]
    verified = sorted(p["verified_at"] for p in rows if p.get("verified_at"))
    latest_verified = verified[-1] if verified else None

    if transport.fixture:
        run.skip("fixture 모드 — 정책 페이지 fetch 생략")
        return [], latest_verified, len(rows)

    changed = []
    failures = []
    dirty = False
    for policy in rows:
        url = policy.get("source_url")
        if not url or not url.startswith("https://"):
            failures.append("%s: source_url 없음/https 아님" % policy["id"])
            continue
        try:
            request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
            with urllib.request.urlopen(request, timeout=HTTP_TIMEOUT) as resp:
                html_text = decode_body(resp.read())
        except Exception as exc:  # noqa: BLE001 — 정책별로 실패를 격리한다
            failures.append("%s: %s" % (policy["id"], describe_error(exc)))
            continue
        new_hash, _basis = policy_content_hash(html_text, policy.get("content_id"))
        prev_hash = policy.get("source_hash")
        if new_hash != prev_hash:
            policy["source_hash"] = new_hash
            dirty = True
        if prev_hash and prev_hash != new_hash and policy.get("last_notified_hash") != new_hash:
            changed.append({"id": policy["id"], "prev_hash": prev_hash, "new_hash": new_hash})
            policy["last_notified_hash"] = new_hash

    # policies.json 은 사람이 관리하는 파일이다. source_hash·last_notified_hash 가
    # 실제로 바뀐 경우에만 다시 쓰고, 줄바꿈 방식도 원본을 따라간다 (불필요한 diff 방지).
    if dirty:
        newline, indent = detect_format(path)
        write_json(path, policies, newline=newline, indent=indent)
    if failures:
        run.fail("정책 %d건 가져오기 실패: %s" % (len(failures), "; ".join(failures[:3])))
    return changed, latest_verified, len(rows)


# ---------------------------------------------------------------------------
# 9. 메인
# ---------------------------------------------------------------------------

# SPEC §3-6 meta.config 키. build.py 가 config.json 에서 다시 복사하지만
# data/meta.json 자체도 §3-6 과 같은 모양이어야 혼동이 없다.
META_CONFIG_KEYS = (
    "base_station", "conversion_rate", "trade_months", "trend_months",
    "sample_min", "banjeonse_ratio", "deposit_hist_bucket", "notice_retain_days",
    "sigungu_codes", "exclusion_rules",
)


def meta_config(cfg):
    out = {key: cfg.get(key) for key in META_CONFIG_KEYS}
    out["stations"] = [
        {
            "id": station.get("id"),
            "name": station.get("name"),
            "gu": station.get("gu"),
            "dongs": list(station.get("dongs") or []),
        }
        for station in cfg.get("stations", [])
    ]
    return out


def main(argv=None):
    parser = argparse.ArgumentParser(description="hometrack 수집기")
    parser.add_argument(
        "--fixture",
        action="store_true",
        help="data/fixtures/ 의 응답 샘플로 오프라인 수집 (HTTP 호출 없음)",
    )
    parser.add_argument(
        "--fixture-scenario",
        default="normal",
        choices=sorted(FIXTURE_SCENARIOS),
        help="fixture 모드에서 특정 응답을 오류 봉투로 바꿔 실패 경로를 재현한다 (DEF-1·DEF-2)",
    )
    args = parser.parse_args(argv)
    if args.fixture_scenario != "normal" and not args.fixture:
        parser.error("--fixture-scenario 는 --fixture 와 함께 쓴다")
    _init_stdio()

    cfg = read_json(CONFIG_PATH, None)
    if cfg is None:
        log("오류: config.json 을 읽을 수 없다")
        return 2

    DATA_DIR.mkdir(parents=True, exist_ok=True)
    transport = Transport(args.fixture, args.fixture_scenario)
    service_key = os.environ.get(ENV_KEY) or ""
    has_key = bool(service_key)
    today = datetime.now(KST).date()
    today_iso = today.isoformat()

    prev_meta = read_json(DATA_DIR / "meta.json", {}) or {}
    prev_collectors = {
        row.get("key"): row
        for row in (prev_meta.get("collectors") or [])
        if isinstance(row, dict)
    }
    prev_notices = read_json(DATA_DIR / "notices_prev.json", None)
    prev_notices_list = prev_notices if isinstance(prev_notices, list) else []
    prev_diff = read_json(DATA_DIR / "snapshot_diff.json", None)

    mode = "fixture" if args.fixture else ("live" if has_key else "no-key")
    if args.fixture and args.fixture_scenario != "normal":
        mode += "/" + args.fixture_scenario
    log("hometrack collect 시작 — mode=%s, KST %s" % (mode, now_iso()))

    runs = []

    # -- 실거래 3종 --------------------------------------------------------
    trades_run = CollectorRun(
        key="trades",
        name="국토교통부 실거래가 (전월세 3종)",
        source="국토교통부 실거래가 공개 API — 아파트·연립다세대·오피스텔 전월세",
        kind="auto",
        note="과거 계약 통계, 매물 아님 · 신고 지연 최대 30일",
        list_url="https://rt.molit.go.kr/",
    )
    runs.append(trades_run)
    trades_payload = None
    excluded_trade_count = prev_meta.get("excluded_trade_count", 0) or 0
    if not has_key and not args.fixture:
        trades_run.skip("%s 없음" % ENV_KEY)
    else:
        cache_path = DATA_DIR / "trades_cache.json"
        cache = read_json(cache_path, {}) or {}
        try:
            contracts, refetched, window = collect_trades(
                cfg, trades_run, transport, service_key, cache
            )
            if trades_run.ok:
                aggregates, excluded, latest_ym = aggregate_trades(contracts, cfg, window)
                trades_payload = {
                    "aggregates": aggregates,
                    "latest_contract_ym": latest_ym,
                    "refetched_months": refetched,
                    "fetched_at": now_iso(),
                }
                excluded_trade_count = excluded
                trades_run.record["item_count"] = len(contracts)
                if args.fixture:
                    # fixture 모드는 매번 fixture 를 다시 읽으므로 캐시가 필요 없고,
                    # 실수집 캐시를 fixture 데이터로 덮어써서도 안 된다.
                    trades_run.add_note("fixture")
                else:
                    write_json(cache_path, cache)
        except Exception as exc:  # noqa: BLE001 — 수집기 단위 격리
            trades_run.fail(exc)
            log("실거래 수집 실패: %s" % trades_run.record["error"])

    # -- LH 공고 -----------------------------------------------------------
    lh_run = CollectorRun(
        key="lh",
        name="LH 분양임대공고문 (부산)",
        source="한국토지주택공사_분양임대공고문 조회 서비스 (15058530)",
        kind="semi",
        list_url=cfg.get("lh", {}).get("list_url"),
    )
    runs.append(lh_run)
    lh_notices = []
    if not has_key and not args.fixture:
        lh_run.skip("%s 없음" % ENV_KEY)
    else:
        try:
            lh_notices = collect_lh(cfg, lh_run, transport, service_key)
            lh_run.record["item_count"] = len(lh_notices)
            if args.fixture:
                lh_run.add_note("fixture")
        except Exception as exc:  # noqa: BLE001
            lh_run.fail(exc)
            lh_notices = []
            log("LH 수집 실패: %s" % lh_run.record["error"])

    # -- 마이홈 ------------------------------------------------------------
    myhome_run = CollectorRun(
        key="myhome",
        name="마이홈포털 공공주택 모집공고",
        source="국토교통부_마이홈포털 공공주택 모집공고 조회 서비스 (15108420)",
        kind="semi",
        list_url=cfg.get("myhome", {}).get("list_url"),
    )
    runs.append(myhome_run)
    myhome_notices = []
    if not has_key and not args.fixture:
        myhome_run.skip("%s 없음" % ENV_KEY)
    else:
        try:
            myhome_notices = collect_myhome(cfg, myhome_run, transport, service_key)
            myhome_run.record["item_count"] = len(myhome_notices)
            if args.fixture:
                myhome_run.add_note("fixture")
        except Exception as exc:  # noqa: BLE001
            myhome_run.fail(exc)
            myhome_notices = []
            log("마이홈 수집 실패: %s" % myhome_run.record["error"])

    # -- 수동 등록 (BMC 등) ------------------------------------------------
    manual_path = DATA_DIR / "notices_manual.json"
    manual_notices, manual_ok = load_manual_notices(manual_path, today_iso)
    bmc_run = CollectorRun(
        key="bmc",
        name="부산도시공사 임대주택 공고",
        source="부산도시공사 청약센터 (수동 등록 — data/notices_manual.json)",
        kind="manual",
        note="금액·면적·배제조건은 공고문 원문을 보고 사람이 등록한다",
        list_url="https://apply.bmc.busan.kr/",
    )
    runs.append(bmc_run)
    if not manual_ok:
        bmc_run.skip("notices_manual.json 을 읽지 못했다")
    else:
        bmc_entries = [n for n in manual_notices if (n.get("source") == "BMC")]
        bmc_run.record["item_count"] = len(bmc_entries)
        registered = sorted(n["registered_at"] for n in bmc_entries if n.get("registered_at"))
        detail_registered = sorted(
            n["detail_registered_at"] for n in bmc_entries if n.get("detail_registered_at")
        )
        bmc_run.record["registered_at"] = registered[-1] if registered else None
        bmc_run.record["detail_registered_at"] = (
            detail_registered[-1] if detail_registered else None
        )

    # -- 정책 변경 감지 ----------------------------------------------------
    policy_run = CollectorRun(
        key="policy",
        name="신혼부부 정책 기준",
        source="data/policies.json (출처 페이지 변경 감지)",
        kind="semi",
        note="수치는 사람이 확인해 등록한다 · 변경 감지만 자동",
    )
    runs.append(policy_run)
    changed_policies, policy_verified_latest, policy_count = collect_policies(
        cfg, policy_run, transport
    )
    policy_run.record["item_count"] = policy_count
    if policy_verified_latest is None:
        policy_verified_latest = prev_meta.get("policy_verified_latest")

    # -- 민간 매물 (수집하지 않는 줄) --------------------------------------
    private_run = CollectorRun(
        key="private",
        name="민간 매물 (네이버부동산·직방·다방)",
        source="수집하지 않음",
        kind="none",
        note="수집 안 함 — 검색 링크만 제공",
    )
    private_run.skip("민간 부동산 플랫폼은 크롤링하지 않는다 (원칙 3)")
    runs.append(private_run)

    # -- 0건 수집은 성공이 아니다 (DEF-1) ----------------------------------
    # 직전에 공고가 있었는데 이번 결과가 0건이면 그 출처를 authoritative 에서 강등해
    # disappeared 를 찍지 않는다. 오탐 소멸은 notices_prev.json 이 덮이면서 새 기준선이 되고
    # notice_retain_days 후 잘려 나가 되돌릴 수 없다.
    prev_active_by_source = {}
    for row in prev_notices_list:
        if not isinstance(row, dict) or row.get("disappeared"):
            continue
        if (row.get("entry_kind") or "auto") == "manual":
            continue
        source_name = row.get("source")
        if source_name:
            prev_active_by_source[source_name] = prev_active_by_source.get(source_name, 0) + 1

    def authoritative_for(run, source_name, collected_notices):
        if not run.ok:
            return False
        prev_count = prev_active_by_source.get(source_name, 0)
        if not collected_notices and prev_count > 0:
            run.add_note("0건 수집 — 마감 판정 보류")
            log("경고: %s 0건 수집 — 마감 판정을 보류하고 직전 %d건을 유지한다"
                % (source_name, prev_count))
            return False
        return True

    authoritative = {
        "LH": authoritative_for(lh_run, "LH", lh_notices),
        "MYHOME": authoritative_for(myhome_run, "MYHOME", myhome_notices),
        "manual": manual_ok,
    }

    collector_records = [run.finish(prev_collectors) for run in runs]

    # -- 공고 병합 ---------------------------------------------------------
    auto_notices = assign_notice_ids(lh_notices + myhome_notices)
    notices, prev_by_id = merge_notices(
        cfg, auto_notices, manual_notices, prev_notices_list, authoritative, today_iso
    )

    diff = build_diff(cfg, notices, prev_by_id, prev_diff, collector_records, today)
    diff["changed_policies"] = changed_policies

    history = read_json(DATA_DIR / "diff_history.json", []) or []
    if not isinstance(history, list):
        history = []
    history = [row for row in history if isinstance(row, dict) and row.get("date") != diff["date"]]
    history.append(diff)
    keep_days = int(cfg.get("diff_history_days", 14))
    history = sorted(history, key=lambda row: row.get("date") or "")[-keep_days:]

    meta = {
        "generated_at": now_iso(),
        "config": meta_config(cfg),
        "collectors": collector_records,
        "policy_verified_latest": policy_verified_latest,
        "excluded_trade_count": excluded_trade_count,
    }

    write_json(DATA_DIR / "notices.json", notices)
    if trades_payload is not None:
        write_json(DATA_DIR / "trades.json", trades_payload)
    elif not (DATA_DIR / "trades.json").exists():
        # 첫 실행에서 실거래가 실패해도 build.py 가 읽을 형태는 있어야 한다
        write_json(
            DATA_DIR / "trades.json",
            {"aggregates": [], "latest_contract_ym": None, "refetched_months": [], "fetched_at": None},
        )
    write_json(DATA_DIR / "snapshot_diff.json", diff)
    write_json(DATA_DIR / "diff_history.json", history)
    write_json(DATA_DIR / "meta.json", meta)
    write_json(DATA_DIR / "notices_prev.json", notices)

    if trades_payload is not None:
        trades_line = "실거래 집계 %d조합" % len(trades_payload.get("aggregates") or [])
    else:
        # 실패해도 trades.json 은 직전 집계를 그대로 들고 있다 — "0조합" 이라고 찍으면
        # 로그를 읽는 사람이 데이터가 사라진 줄 안다 (DEF-10)
        kept = read_json(DATA_DIR / "trades.json", None) or {}
        trades_line = "실거래 직전 데이터 유지(%d조합)" % len(kept.get("aggregates") or [])
    log(
        "완료 — 공고 %d건 / %s / 신규 %d건 / 마감 %d건 / 미매핑 계약 %d건"
        % (
            len(notices),
            trades_line,
            len(diff["new_notices"]),
            len(diff["closed_notices"]),
            excluded_trade_count,
        )
    )
    for record in collector_records:
        log(
            "  [%s] %-4s %s%s"
            % (
                record["key"],
                record["status"],
                record["name"],
                (" — %s" % record["error"]) if record["error"] else "",
            )
        )
    return 0


if __name__ == "__main__":
    sys.exit(main())
