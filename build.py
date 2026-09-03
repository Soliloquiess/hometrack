#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""build.py — data/*.json + config.json → site/index.html (의존성 0 단일 파일)

레인 B 의 두 번째 단계다. `collect.py` 가 남긴 `data/*.json` 과 `config.json` 을
화면 데이터 7키로 조립하고, **목업 `mockup/index.html` 을 빌드 시점에 읽어** 변환한다.

목업 복제본을 손으로 관리하지 않는다(그러면 디자이너 수정이 반영되지 않는다).
변환은 마커 기반이며, 마커를 하나라도 못 찾으면 **빌드를 중단**한다 —
목업을 조용히 그대로 내보내는 것이 이 스크립트가 낼 수 있는 최악의 결과다.

Python 3 표준 라이브러리만 쓴다. Node 는 런타임 스모크(선택)에만 쓴다.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parent
DATA_DIR = ROOT / "data"
MOCKUP = ROOT / "mockup" / "index.html"
SITE_DIR = ROOT / "site"
OUT = SITE_DIR / "index.html"
CONFIG = ROOT / "config.json"
SMOKE = ROOT / "tools" / "smoke_site.js"


class BuildError(Exception):
    """빌드를 계속하면 안 되는 상황. 종료 코드 != 0."""


def _init_stdio() -> None:
    """Windows cp949 콘솔에서 '—' 같은 문자로 죽지 않도록 stdout/stderr 를 UTF-8 로."""
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, ValueError):
            pass


_init_stdio()


def log(msg: str) -> None:
    print(msg, flush=True)


class Report:
    """검증 결과 수집기. error 가 하나라도 있으면 빌드가 실패한다."""

    def __init__(self) -> None:
        self.errors: list[str] = []
        self.warnings: list[str] = []

    def error(self, msg: str) -> None:
        self.errors.append(msg)

    def warn(self, msg: str) -> None:
        self.warnings.append(msg)

    def dump(self) -> None:
        for w in self.warnings:
            log("  [경고] " + w)
        for e in self.errors:
            log("  [실패] " + e)


# ===========================================================================
# 1. 데이터 조립
# ===========================================================================

def read_json(path: Path, default=None, required: bool = False):
    try:
        with open(path, "r", encoding="utf-8") as fh:
            return json.load(fh)
    except FileNotFoundError:
        if required:
            raise BuildError("필수 파일이 없다: %s" % path)
        log("  · %s 없음 — 기본값 사용" % path.name)
        return default
    except (json.JSONDecodeError, OSError) as exc:
        raise BuildError("%s 를 읽지 못했다 — %s" % (path.name, exc)) from exc


# SPEC §3-6 meta.config 키 목록 + D19 exclusion_rules.
# 🔴 stations 는 1호선 순서 배열이다. 정렬하지 않는다(DESIGN_SPEC §7-5 함정 3) —
#    화면의 "N정거장"이 이 배열의 인덱스 차이기 때문에 정렬하면 전부 틀린다.
META_CONFIG_KEYS = [
    "base_station",
    "conversion_rate",
    "trade_months",
    "trend_months",
    "sample_min",
    "banjeonse_ratio",
    "deposit_hist_bucket",
    "notice_retain_days",
    "sigungu_codes",
    "exclusion_rules",
    "stations",
]

# 화면 데이터 7키 (DESIGN_SPEC §7-1). 이 목록과 정확히 일치해야 한다.
SCREEN_KEYS = ["meta", "notices", "trades", "income_tables", "policies", "diff", "diff_history"]

# 화면에 싣지 않는 파일 — 수집 원본·캐시·픽스처.
NOT_SHIPPED = ["raw_myhome_last.json", "trades_cache.json"]


def assemble_data(report: Report) -> dict:
    """data/*.json + config.json → 화면 데이터 7키."""
    config = read_json(CONFIG, required=True)
    meta = read_json(DATA_DIR / "meta.json", required=True)
    if not isinstance(meta, dict):
        raise BuildError("meta.json 이 객체가 아니다")

    # meta.config — collect.py 가 쓴 값을 바탕으로 config.json 정본을 덮어쓴다.
    merged = dict(meta.get("config") or {})
    cfg_out = {}
    for key in META_CONFIG_KEYS:
        if key in config:
            cfg_out[key] = config[key]
        elif key in merged:
            cfg_out[key] = merged[key]
            report.warn("meta.config.%s 가 config.json 에 없어 meta.json 값을 그대로 썼다" % key)
        else:
            report.warn("meta.config.%s 가 어디에도 없다 — 화면 기본값에 의존한다" % key)
    # collect.py 가 추가로 남긴 키는 버리지 않는다(주석 키 `_...` 는 제외).
    for key, value in merged.items():
        if key not in cfg_out and not key.startswith("_"):
            cfg_out[key] = value
    meta["config"] = cfg_out

    stations = cfg_out.get("stations") or []
    if not stations:
        report.error("meta.config.stations 가 비었다 — 역 목록 없이는 화면이 성립하지 않는다")
    else:
        log("  · stations %d개 (1호선 순서 유지): %s" % (
            len(stations), " → ".join(str(s.get("id")) for s in stations)))
    if not cfg_out.get("exclusion_rules"):
        report.warn("meta.config.exclusion_rules 가 비었다 — 공고 '불가' 판정 근거표가 없다(D19)")

    data = {
        "meta": meta,
        "notices": read_json(DATA_DIR / "notices.json", default=[], required=True),
        "trades": read_json(DATA_DIR / "trades.json", default={}, required=True),
        "income_tables": read_json(DATA_DIR / "income_tables.json", default={}, required=True),
        "policies": read_json(DATA_DIR / "policies.json", default=[], required=True),
        # D21 — snapshot_diff.json 전체가 `diff`, diff_history.json 배열이 `diff_history`.
        #       diff.history 로 중첩하지 않는다(중첩하면 히스토리에서 is_first_run 이 사라진다).
        "diff": read_json(DATA_DIR / "snapshot_diff.json", default={}, required=True),
        "diff_history": read_json(DATA_DIR / "diff_history.json", default=[], required=True),
    }
    if list(data.keys()) != SCREEN_KEYS:
        raise BuildError("화면 데이터 키가 7개와 다르다: %s" % list(data.keys()))
    if "history" in (data["diff"] or {}):
        report.error("diff.history 중첩이 있다 — diff_history 최상위 키로 분리해야 한다(D21)")
    if "refetched_months" in data["meta"]:
        report.error("meta.refetched_months 가 있다 — trades 에만 둔다(D21)")
    for name in NOT_SHIPPED:
        if (DATA_DIR / name).exists():
            log("  · %s 는 화면에 싣지 않는다(확인)" % name)
    return data


# ===========================================================================
# 2. 스키마 · URL 검증
# ===========================================================================

ENUM_CONFIDENCE = {"official", "secondary", "unverified"}
ENUM_CATEGORY = {"supply", "loan", "subsidy"}
ENUM_INCOME_BASIS = {"urban_worker_pct", "median_pct", "annual_krw"}
ENUM_COLLECTOR_KIND = {"auto", "semi", "manual", "none"}
ENUM_COLLECTOR_STATUS = {"ok", "fail", "skip"}
ENUM_NOTICE_DETAIL = {"meta_only", "detailed"}
ENUM_NOTICE_SOURCE = {"MYHOME", "LH", "BMC"}
ENUM_NOTICE_ENTRY = {"auto", "manual"}
ENUM_ID_BASIS = {"notice_no", "composite"}
ENUM_CLOSED_REASON = {"apply_end", "disappeared", "notice_status"}
ENUM_HOUSING_TYPE = {"apt", "villa", "officetel"}
ENUM_DEAL_TYPE = {"jeonse", "banjeonse", "wolse"}


def _enum(report: Report, where: str, value, allowed: set, required: bool = True) -> None:
    if value is None and not required:
        return
    if value not in allowed:
        report.error("%s = %r — 허용값 %s" % (where, value, sorted(allowed)))


def validate_schema(data: dict, report: Report) -> None:
    meta = data["meta"]

    # --- meta.collectors ---
    collectors = meta.get("collectors")
    if not isinstance(collectors, list) or not collectors:
        report.error("meta.collectors 가 비었다 — 신선도 바가 아무 줄도 못 낸다")
        collectors = []
    seen_keys = set()
    for i, c in enumerate(collectors):
        where = "meta.collectors[%d]" % i
        key = c.get("key")
        if not key:
            report.error("%s.key 가 없다 — 화면 분기는 key 로만 한다(D8)" % where)
        elif key in seen_keys:
            report.error("%s.key=%r 가 중복이다" % (where, key))
        else:
            seen_keys.add(key)
        _enum(report, where + ".kind", c.get("kind"), ENUM_COLLECTOR_KIND)
        _enum(report, where + ".status", c.get("status"), ENUM_COLLECTOR_STATUS)

    # --- notices ---
    notices = data["notices"]
    if not isinstance(notices, list):
        raise BuildError("notices.json 이 배열이 아니다")
    policy_ids = {p.get("id") for p in data["policies"] if isinstance(p, dict)}
    notice_ids = set()
    dangling = []
    for i, n in enumerate(notices):
        where = "notices[%d](%s)" % (i, n.get("id"))
        nid = n.get("id")
        if not nid:
            report.error("%s.id 가 없다" % where)
        elif nid in notice_ids:
            report.error("%s.id 가 중복이다" % where)
        else:
            notice_ids.add(nid)
        _enum(report, where + ".source", n.get("source"), ENUM_NOTICE_SOURCE)
        _enum(report, where + ".entry_kind", n.get("entry_kind"), ENUM_NOTICE_ENTRY)
        _enum(report, where + ".detail_level", n.get("detail_level"), ENUM_NOTICE_DETAIL)
        _enum(report, where + ".id_basis", n.get("id_basis"), ENUM_ID_BASIS, required=False)
        if "stops_from_base" in n:
            report.error("%s.stops_from_base 가 있다 — 데이터에 두지 않는다(D18)" % where)
        lp = n.get("linked_policy_id")
        # D20 — dangling 은 경고만. 빌드는 계속한다(화면이 '설정 오류' 문구로 구분해 낸다).
        if lp and lp not in policy_ids:
            dangling.append("%s → linked_policy_id=%r" % (where, lp))
    for d in dangling:
        report.warn("dangling 참조(D20 — 빌드 계속, 화면은 '설정 오류'로 표시): " + d)

    # --- policies ---
    policies = data["policies"]
    if not isinstance(policies, list):
        raise BuildError("policies.json 이 배열이 아니다")
    for i, p in enumerate(policies):
        where = "policies[%d](%s)" % (i, p.get("id"))
        if not p.get("id"):
            report.error("%s.id 가 없다" % where)
        _enum(report, where + ".confidence", p.get("confidence"), ENUM_CONFIDENCE)
        _enum(report, where + ".category", p.get("category"), ENUM_CATEGORY)
        income = (p.get("criteria") or {}).get("income")
        if isinstance(income, dict):
            _enum(report, where + ".criteria.income.basis", income.get("basis"), ENUM_INCOME_BASIS)
        if not p.get("verified_at"):
            report.error("%s.verified_at 이 없다 — 최종 확인일 없는 정책은 싣지 않는다" % where)

    # --- income_tables ---
    it = data["income_tables"]
    if isinstance(it, dict):
        for tname in ("urban_worker", "median_income"):
            tbl = it.get(tname)
            if not isinstance(tbl, dict):
                report.warn("income_tables.%s 가 없다 — 해당 basis 정책이 '기준액 미확보'로 남는다" % tname)
                continue
            _enum(report, "income_tables.%s.confidence" % tname, tbl.get("confidence"),
                  ENUM_CONFIDENCE, required=False)
            if not tbl.get("year_label"):
                report.warn("income_tables.%s.year_label 이 없다 — 카드에서 적용년도가 안 보인다(D13)" % tname)
            if not tbl.get("by_household"):
                report.warn("income_tables.%s.by_household 가 비었다" % tname)

    # --- trades ---
    trades = data["trades"]
    if isinstance(trades, dict):
        for i, a in enumerate(trades.get("aggregates") or []):
            where = "trades.aggregates[%d]" % i
            _enum(report, where + ".housing_type", a.get("housing_type"), ENUM_HOUSING_TYPE)
            _enum(report, where + ".deal_type", a.get("deal_type"), ENUM_DEAL_TYPE)

    # --- diff / diff_history ---
    diffs = [("diff", data["diff"])]
    for i, h in enumerate(data["diff_history"] or []):
        diffs.append(("diff_history[%d]" % i, h))
    for where, d in diffs:
        if not isinstance(d, dict):
            report.error("%s 가 객체가 아니다" % where)
            continue
        missing = [k for k in ("date", "is_first_run", "new_notices", "closing_soon",
                               "closed_notices", "changed_policies", "collector_failures")
                   if k not in d]
        if missing:
            report.error("%s 에 7키 중 %s 가 없다(D21)" % (where, missing))
        for c in d.get("closed_notices") or []:
            if isinstance(c, dict):
                _enum(report, where + ".closed_notices[].reason", c.get("reason"),
                      ENUM_CLOSED_REASON, required=False)
        for c in d.get("collector_failures") or []:
            if isinstance(c, dict) and not c.get("key"):
                report.error("%s.collector_failures[] 에 key 가 없다(D8)" % where)


URL_KEYS = ("source_url", "list_url", "DTL_URL")
HTTP_RE = re.compile(r"^https?://", re.I)


def sanitize_urls(node, report: Report, path: str = "") -> int:
    """source_url / list_url / DTL_URL 은 https?:// 만 허용. 아니면 null + 경고."""
    replaced = 0
    if isinstance(node, dict):
        for key in list(node.keys()):
            value = node[key]
            here = "%s.%s" % (path, key) if path else key
            if key in URL_KEYS and value is not None:
                if not isinstance(value, str) or not HTTP_RE.match(value.strip()):
                    report.warn("URL 스킴 위반 → null 로 치환: %s = %r" % (here, value))
                    node[key] = None
                    replaced += 1
                continue
            replaced += sanitize_urls(value, report, here)
    elif isinstance(node, list):
        for i, value in enumerate(node):
            replaced += sanitize_urls(value, report, "%s[%d]" % (path, i))
    return replaced


# ===========================================================================
# 3. 목업 → 사이트 변환
# ===========================================================================

def js_json(data: dict) -> str:
    """화면 데이터를 `<script>` 안에 안전하게 실을 수 있는 JS 리터럴로 만든다.

    - `<` 를 전부 `\\u003c` 로 escape → `</script>` 조기 종료·`<!--` 주석 개시 차단
    - U+2028/U+2029 는 JS 에서 줄바꿈으로 해석되므로 escape
    """
    def one(value) -> str:
        text = json.dumps(value, ensure_ascii=False, separators=(",", ":"))
        return (text.replace("<", "\\u003c")
                    .replace(chr(0x2028), "\\u2028")
                    .replace(chr(0x2029), "\\u2029"))

    lines = ["var DATA = {"]
    for i, key in enumerate(SCREEN_KEYS):
        comma = "," if i < len(SCREEN_KEYS) - 1 else ""
        lines.append(' %s: %s%s' % (json.dumps(key), one(data[key]), comma))
    lines.append("};")
    return "\n".join(lines)


DATA_BLOCK_RE = re.compile(r"^var DATA = \{.*?^[ \t]*\};[ \t]*$", re.S | re.M)
MOCK_JS_BLOCK_RE = re.compile(
    r"[ \t]*/\* ── 목업 전용 블록 시작.*?목업 전용 블록 끝[^\n]*\*/[ \t]*\n", re.S)
NOW_RE = re.compile(
    r"/\* 목업은 generated_at .*?var NOW = parseDT\(DATA\.meta\.generated_at\);", re.S)
SAMPLE_COMMENT_RE = re.compile(
    r"   \[0\] 샘플 데이터 —[^\n]*\n[^\n]*목업 확장 필드\(§7-2 참조\)\.\n")

NOW_PATCH = """/* build.py 교체 지점 — D-day·"최근 7일"·경과일은 **페이지를 여는 시각** 기준으로
   매일 다시 계산한다(DESIGN_SPEC §7-5 함정 2). 목업은 샘플 날짜가 고정이라
   generated_at 을 "지금"으로 삼았지만 실 빌드가 그러면 D-day 가 수집 시각에 고정된다.
   신선도 바의 "N시간 전"은 relTime() 이 NOW 와 collectors[].last_success 의 차로 내므로
   generated_at·last_success **실측값** 기준이 유지되고(SPEC §2),
   인쇄 헤더·수집 상태 줄은 DATA.meta.generated_at 을 그대로 찍는다. */
var NOW = new Date();"""


def _tag_span(html: str, open_start: int, tag: str):
    """open_start 의 `<tag` 부터 짝이 맞는 `</tag>` 까지의 (시작, 끝) 을 돌려준다."""
    open_re = re.compile(r"<" + re.escape(tag) + r"\b", re.I)
    close_re = re.compile(r"</" + re.escape(tag) + r"\s*>", re.I)
    depth = 0
    i = open_start
    while True:
        mo = open_re.search(html, i)
        mc = close_re.search(html, i)
        if mc is None:
            return None
        if mo is not None and mo.start() < mc.start():
            depth += 1
            i = mo.end()
        else:
            depth -= 1
            i = mc.end()
            if depth == 0:
                return open_start, i


def strip_mock_only(html: str) -> tuple[str, int]:
    """`data-mock-only` 가 달린 요소를 여는 태그부터 닫는 태그까지 통째로 지운다."""
    removed = 0
    while True:
        at = html.find("data-mock-only")
        if at < 0:
            break
        lt = html.rfind("<", 0, at)
        if lt < 0:
            raise BuildError("data-mock-only 의 여는 태그를 찾지 못했다 (offset %d)" % at)
        m = re.match(r"<([A-Za-z][\w-]*)", html[lt:])
        if not m:
            raise BuildError("data-mock-only 의 태그명을 읽지 못했다 (offset %d)" % lt)
        tag = m.group(1)
        span = _tag_span(html, lt, tag)
        if span is None:
            raise BuildError("data-mock-only <%s> 의 닫는 태그를 찾지 못했다" % tag)
        a, b = span
        # 줄 전체를 차지하던 요소면 남은 빈 줄까지 함께 지운다.
        line_start = html.rfind("\n", 0, a) + 1
        if html[line_start:a].strip() == "":
            a = line_start
        tail = re.match(r"[ \t]*\n", html[b:])
        if tail:
            b += tail.end()
        html = html[:a] + html[b:]
        removed += 1
        if removed > 20:
            raise BuildError("data-mock-only 제거가 20회를 넘었다 — 마커 해석이 잘못됐다")
    return html, removed


def render_template(data: dict, report: Report) -> str:
    """목업을 읽어 실 사이트 HTML 로 변환한다. 마커 미발견은 전부 BuildError."""
    html = MOCKUP.read_text(encoding="utf-8")
    src_len = len(html)

    def sub_once(pattern, repl, what: str, text: str) -> str:
        if isinstance(pattern, str):
            hits = text.count(pattern)
            if hits != 1:
                raise BuildError("%s 마커가 %d번 발견됐다(1번이어야 한다): %r" % (what, hits, pattern))
            return text.replace(pattern, repl, 1)
        found = pattern.findall(text)
        if len(found) != 1:
            raise BuildError("%s 마커가 %d번 발견됐다(1번이어야 한다): %s"
                             % (what, len(found), pattern.pattern[:60]))
        return pattern.sub(lambda _m: repl, text, count=1)

    # (a) var DATA 블록 교체
    html = sub_once(DATA_BLOCK_RE, js_json(data), "var DATA 블록", html)

    # (b) 목업 전용 요소 3곳 + bindInputs() 목업 전용 블록
    html, removed = strip_mock_only(html)
    if removed != 3:
        raise BuildError("data-mock-only 요소를 3곳 지워야 하는데 %d곳을 지웠다 "
                         "— 목업이 바뀌었다면 DESIGN_SPEC §7-1 을 다시 확인하라" % removed)
    html = sub_once(MOCK_JS_BLOCK_RE, "", "bindInputs() 목업 전용 블록", html)
    if "btn-sample" in html or "btn-firstrun" in html:
        raise BuildError("목업 전용 버튼 id 가 산출물에 남았다 (btn-sample / btn-firstrun)")

    # (c) NOW — 실시각으로. 신선도 바·인쇄 헤더는 generated_at 실측값을 계속 쓴다.
    html = sub_once(NOW_RE, NOW_PATCH, "var NOW", html)
    if "parseDT(DATA.meta.generated_at)" in html:
        raise BuildError("NOW 교체 후에도 parseDT(DATA.meta.generated_at) 가 남았다")
    gen_uses = html.count("DATA.meta.generated_at")
    if gen_uses < 3:
        raise BuildError("generated_at 을 직접 쓰는 지점이 %d곳뿐이다 — 신선도 바·인쇄 헤더가 "
                         "실측값을 잃었을 수 있다(DESIGN_SPEC §7-5 함정 1)" % gen_uses)
    if "relTime(c.last_success)" not in html:
        raise BuildError("신선도 바의 relTime(c.last_success) 이 사라졌다 — "
                         "'N시간 전'이 실측값 기준이 아니게 된다(SPEC §2)")
    log("  · generated_at 직접 사용 %d곳 유지 (인쇄 헤더·수집 상태·새 소식 기준선)" % gen_uses)

    # (d) 목업 표기 제거
    html = sub_once("<title>hometrack — 부산 신혼집 대시보드 (디자인 목업)</title>",
                    "<title>hometrack — 부산 신혼집 대시보드</title>", "<title>", html)
    html = sub_once('document.title = TAB_TITLE[name] + " · hometrack (목업)";',
                    'document.title = TAB_TITLE[name] + " · hometrack";',
                    "document.title", html)
    html = sub_once("   hometrack — 디자인 목업 (단일 정적 HTML, 외부 리소스 0건)",
                    "   hometrack — 빌드 산출 (단일 정적 HTML, 외부 리소스 0건)",
                    "CSS 머리 주석", html)
    html = sub_once(SAMPLE_COMMENT_RE,
                    "   [0] 화면 데이터 — build.py 가 data/*.json + config.json 에서\n"
                    "       7키(SPEC §3-6 · DESIGN_SPEC §7-1)로 조립해 삽입한다. 손으로 고치지 않는다.\n",
                    "[0] 데이터 주석", html)

    log("  · 목업 %s자 → 산출 %s자" % (format(src_len, ","), format(len(html), ",")))
    return html


# ===========================================================================
# 4. 산출물 검증
# ===========================================================================

# 외부 요청을 만들 수 있는 토큰. 딥링크 href 와 인쇄 CSS 의 attr(href) 는 제외한다
# (목업과 같은 기준 — 목업 기준선도 이 9개가 전부 0건이다).
FORBIDDEN_TOKENS = [
    "src=", "<link", "<img", "@import", "url(",
    "fetch(", "XMLHttpRequest", "sendBeacon", "WebSocket",
]

# 개인 조건(COND / hmt.cond)이 새어 나갈 수 있는 sink. localStorage 만 허용.
COND_SINKS = [
    "document.cookie", "URLSearchParams", "location.search", "location.href",
    "postMessage", "sessionStorage", "fetch(", "XMLHttpRequest", "sendBeacon",
    "WebSocket", "history.pushState", "history.replaceState",
]

# 대소문자 무시 — daily.yml 의 `grep -rniE 'servicekey'` 와 같은 기준으로 본다(D7 · Q42).
SECRET_PATTERNS = ["servicekey", "data_go_kr_key"]


def verify_output(html: str, report: Report) -> None:
    # --- 외부 요청 0건 ---
    for token in FORBIDDEN_TOKENS:
        hits = html.count(token)
        if hits:
            lines = [str(i + 1) for i, line in enumerate(html.splitlines()) if token in line][:5]
            report.error("외부 요청 토큰 %r %d건 (줄 %s) — 산출 HTML 은 0건이어야 한다"
                         % (token, hits, ", ".join(lines)))
    log("  · 외부 요청 토큰 %d종 전부 0건 (attr(href) %d · href= %d 는 허용 규칙)"
        % (len(FORBIDDEN_TOKENS), html.count("attr(href)"), html.count("href=")))

    # --- 시크릿 0건 ---
    lowered = html.lower()
    for pat in SECRET_PATTERNS:
        hits = lowered.count(pat)
        if hits:
            report.error("시크릿 패턴 %r %d건" % (pat, hits))
    env_key = os.environ.get("DATA_GO_KR_KEY")
    if env_key and len(env_key) >= 8 and env_key in html:
        report.error("환경변수 DATA_GO_KR_KEY 값이 산출물에 들어 있다")
    log("  · 시크릿 패턴 %d종 전부 0건" % len(SECRET_PATTERNS))

    # --- 개인 조건 sink ---
    bad_sink = []
    for i, line in enumerate(html.splitlines(), 1):
        if "COND" not in line and "STORE_KEY" not in line and "hmt.cond" not in line:
            continue
        for sink in COND_SINKS:
            if sink in line:
                bad_sink.append("%d: %s … %s" % (i, sink, line.strip()[:80]))
    for b in bad_sink:
        report.error("개인 조건이 localStorage 외 sink 에 닿는다 — " + b)
    store_lines = [(i, line) for i, line in enumerate(html.splitlines(), 1)
                   if "STORE_KEY" in line]
    for i, line in store_lines:
        if any(op in line for op in ("setItem", "getItem", "removeItem")) \
                and "localStorage" not in line:
            report.error("STORE_KEY 저장/조회가 localStorage 가 아니다 — 줄 %d" % i)
    log("  · 개인 조건 sink: localStorage 전용 확인 (STORE_KEY 등장 %d줄, 위반 %d건)"
        % (len(store_lines), len(bad_sink)))

    # --- 구조 ---
    mock = html.count("data-mock-only")
    if mock:
        report.error("data-mock-only 가 %d건 남았다" % mock)
    var_data = len(re.findall(r"(?<![\w$])var\s+DATA\s*=", html))
    if var_data != 1:
        report.error("var DATA 선언이 %d개다(1개여야 한다)" % var_data)
    log("  · data-mock-only 0건 · var DATA 선언 %d개" % var_data)

    # --- JSON 삽입 안전성 ---
    body = html[html.find("var DATA = {"):]
    end = body.find("\n};")
    block = body[:end if end > 0 else len(body)]
    for token, name in (("</", "</ (조기 script 종료)"), (chr(0x2028), "U+2028"), (chr(0x2029), "U+2029")):
        if token in block:
            report.error("DATA 블록에 %s 가 이스케이프되지 않고 남았다" % name)
    log("  · DATA 블록 escape 확인: </ 0건 · U+2028/2029 0건 (< → \\u003c)")


# ===========================================================================
# 5. 런타임 스모크 (Node — 선택)
# ===========================================================================

def run_smoke() -> bool | None:
    """Node 가 있으면 tools/smoke_site.js 를 돌린다. 없으면 None."""
    node = shutil.which("node")
    if not node:
        log("스모크 생략 — Node 를 찾지 못했다(`node --version`). "
            "빌드 필수 의존이 아니므로 산출물은 정상이다. 브라우저 확인은 QA 몫으로 남는다.")
        return None
    if not SMOKE.exists():
        log("스모크 생략 — %s 가 없다" % SMOKE)
        return None
    log("런타임 스모크: node %s" % SMOKE.name)
    proc = subprocess.run([node, str(SMOKE), str(OUT)], capture_output=True, text=True,
                          encoding="utf-8", errors="replace")
    for line in (proc.stdout or "").splitlines():
        log("  " + line)
    for line in (proc.stderr or "").splitlines():
        log("  ! " + line)
    return proc.returncode == 0


# ===========================================================================
# main
# ===========================================================================

def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="data/*.json + config.json → site/index.html")
    parser.add_argument("--no-smoke", action="store_true", help="Node 런타임 스모크를 건너뛴다")
    args = parser.parse_args(argv)

    report = Report()
    try:
        log("[1/5] 데이터 조립")
        data = assemble_data(report)

        log("[2/5] 스키마 검증")
        validate_schema(data, report)

        log("[3/5] URL 스킴 검증")
        replaced = sanitize_urls(data, report)
        log("  · source_url/list_url/DTL_URL — null 치환 %d건" % replaced)

        log("[4/5] 목업 → 사이트 변환")
        html = render_template(data, report)

        log("[5/5] 산출물 검증")
        verify_output(html, report)
    except BuildError as exc:
        log("")
        log("빌드 중단: %s" % exc)
        report.dump()
        return 2

    report.dump()
    if report.errors:
        log("")
        log("빌드 실패 — 검증 위반 %d건 (경고 %d건). site/index.html 을 쓰지 않았다."
            % (len(report.errors), len(report.warnings)))
        return 1

    SITE_DIR.mkdir(parents=True, exist_ok=True)
    # LF 로 쓴다 — Windows 에서 CRLF 로 나가면 git 이 경고하고 diff 가 전 줄로 부푼다.
    with open(OUT, "w", encoding="utf-8", newline="\n") as fh:
        fh.write(html)
    size = OUT.stat().st_size
    log("")
    log("생성: %s — %s bytes (%.1f KB) · 경고 %d건"
        % (OUT, format(size, ","), size / 1024.0, len(report.warnings)))

    if args.no_smoke:
        log("스모크 생략 — --no-smoke")
        return 0
    ok = run_smoke()
    if ok is False:
        log("")
        log("런타임 스모크 실패 — 산출물은 남겨 두었다(원인 확인용).")
        return 3
    if ok:
        log("런타임 스모크 통과")
    return 0


if __name__ == "__main__":
    sys.exit(main())
