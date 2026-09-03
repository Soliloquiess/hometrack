#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""검수용 경계·불변식 단위 오라클 — collect.py 의 함수를 직접 호출해
SPEC v1.2 §3-3 · §3-4 · §3-5 · §3-6 의 판정·마스킹·식별키 규칙을 재현한다.

네트워크를 쓰지 않는다. data/ 를 쓰지 않는다(읽기만).

사용법
    python docs/qa/oracle_collect_edge.py
출력
    [OK] / [NG] 로 항목별 결과. NG 가 하나라도 있으면 종료코드 1.
"""

from __future__ import annotations

import json
import os
import sys
import urllib.error
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

import collect  # noqa: E402

FAIL = []


def check(name, ok, detail=""):
    print("[%s] %s%s" % ("OK" if ok else "NG", name, ("  — " + detail) if detail else ""))
    if not ok:
        FAIL.append(name)


CFG = json.loads((ROOT / "config.json").read_text(encoding="utf-8"))
RATIO = float(CFG["banjeonse_ratio"])

print("=" * 72)
print("A. 분류 경계 (§3-3)")
print("=" * 72)
c = collect.classify_deal_type
check("월세 0 → 전세", c(30000, 0, RATIO) == "jeonse")
check("월세 0 · 보증금 0 → 전세", c(0, 0, RATIO) == "jeonse",
      "보증금 0 전세가 만들어질 수 있다(하한 신고 제외 규칙 없음)")
check("보증금 == 월세x240 → 반전세(경계 포함)", c(24000, 100, RATIO) == "banjeonse")
check("보증금 == 월세x240 - 1 → 월세", c(23999, 100, RATIO) == "wolse")
check("보증금 == 월세x240 + 1 → 반전세", c(24001, 100, RATIO) == "banjeonse")
check("보증금 0 · 월세 있음 → 월세", c(0, 50, RATIO) == "wolse")

print()
print("=" * 72)
print("B. 역 매핑 (§3-4)")
print("=" * 72)
idx = collect.build_dong_index(CFG)
multi = {d: v for d, v in idx.items() if len(v) > 1}
check("복수 역 중복 매핑 허용", bool(multi), "%d개 법정동이 2개 이상 역에 매핑" % len(multi))
check("미매핑 법정동은 인덱스에 없다", idx.get("안락동") is None)
dup_in_station = [s["id"] for s in CFG["stations"] if len(s["dongs"]) != len(set(s["dongs"]))]
check("한 역 안에서 법정동 중복 없음", not dup_in_station, str(dup_in_station))
# 같은 역에 같은 dong 이 두 번 들어가면 그 역의 count 가 2배가 된다
check("역 id 중복 없음", len({s["id"] for s in CFG["stations"]}) == len(CFG["stations"]))
order = [s["name"] for s in CFG["stations"]]
expect_order = ["시청", "연산", "교대", "동래", "명륜", "온천장", "부산대",
                "장전", "구서", "두실", "남산", "범어사", "노포"]
check("1호선 13역 순서", order == expect_order, " → ".join(order))
check("기준역 base_station 이 stations 에 있다",
      CFG["base_station"] in {s["id"] for s in CFG["stations"]})
gu_of = {s["id"]: s["gu"] for s in CFG["stations"]}
check("교대역 gu 표기", gu_of["gyodae"] == "연제구",
      "config 값=%s (1호선 교대역 소재지는 연제구 거제동)" % gu_of["gyodae"])

print()
print("=" * 72)
print("C. 12개월 창 · 재수집 경계 (§3-5, D15)")
print("=" * 72)
today = date(2026, 9, 3)
w = collect.recent_months(today, 12)
check("창 길이 12", len(w) == 12, str(w))
check("창 마지막 = 당월", w[-1] == "202609")
check("창 처음 = 11개월 전", w[0] == "202510")
refetch = set(w[-int(CFG["trades"]["refetch_months"]):])
check("재수집 구간 = 당월·전월", refetch == {"202609", "202608"}, str(sorted(refetch)))
check("연말 경계(1월 → 전월 12월)",
      collect.recent_months(date(2026, 1, 15), 2) == ["202512", "202601"])
check("집계 창 밖 계약은 버려진다",
      collect.aggregate_trades(
          [{"ym": "202001", "housing_type": "apt", "dong": "구서동", "deposit": 1, "rent": 0}],
          CFG, w)[0] == [])

print()
print("=" * 72)
print("D. 히스토그램 불변식 (D6)")
print("=" * 72)
for vals in ([100], [0], [499, 500, 501], [1, 100000], list(range(0, 5000, 37))):
    h = collect.deposit_histogram(vals, int(CFG["deposit_hist_bucket"]))
    s = sum(b["count"] for b in h)
    ok = s == len(vals) and h[-1]["hi"] is None and [b["lo"] for b in h] == sorted(b["lo"] for b in h)
    check("hist n=%d 합=%d 마지막hi=%r" % (len(vals), s, h[-1]["hi"]), ok)
h1 = collect.deposit_histogram([1200], 500)
check("단일 계약 → 버킷 1개이고 hi=null(상한 없는 열린 버킷)",
      len(h1) == 1 and h1[0]["hi"] is None,
      "예산 내 비율의 선형 비례분을 계산할 상한이 없다 → 화면 처리 필요: %r" % h1)

print()
print("=" * 72)
print("E. 키 마스킹 (D7, Q42)")
print("=" * 72)
REAL = "Zm9vYmFyMTIzNDU2Nzg5MEFCQ0RFRkdISUpLTE1OT1A9PQ"   # 46자 가짜 '실키'
SHORT = "abc"
url = "https://apis.data.go.kr/1613000/x/y?serviceKey=%s&LAWD_CD=26410" % REAL

os.environ[collect.ENV_KEY] = REAL
m = collect.mask_secret(url)
check("실키 URL 마스킹 — 키 문자열 없음", REAL not in m, m)
check("실키 URL 마스킹 — serviceKey= 없음", "serviceKey=" not in m, m)
m2 = collect.mask_secret("인증키 오류: " + REAL)
check("쿼리 밖 키 원문도 마스킹", REAL not in m2, m2)
m3 = collect.mask_secret("키(URL 인코딩): " + REAL.replace("=", "%3D"))
check("URL 인코딩된 키도 마스킹", "%3D" not in m3 or REAL[:20] not in m3, m3)
he = urllib.error.HTTPError(url, 401, "Unauthorized", None, None)
d = collect.describe_error(he)
check("HTTPError 문자열에 URL·키 없음",
      REAL not in d and "serviceKey" not in d and "apis.data.go.kr" not in d, d)
ue = urllib.error.URLError(OSError("connect fail to %s" % url))
d2 = collect.describe_error(ue)
check("URLError 문자열에 키 없음", REAL not in d2, d2)

os.environ[collect.ENV_KEY] = SHORT
m4 = collect.mask_secret("https://x/y?serviceKey=%s&a=1" % SHORT)
check("짧은 가짜 키도 serviceKey= 가 사라진다", "serviceKey=" not in m4 and SHORT not in m4, m4)
m5 = collect.mask_secret("resultMsg: SERVICE KEY IS NOT REGISTERED (%s)" % SHORT)
check("8자 미만 키는 쿼리 밖에서 마스킹되지 않는다(설계상 한계)",
      SHORT in m5, "mask_secret 은 len(key)>=8 일 때만 원문 치환: %r" % m5)
os.environ.pop(collect.ENV_KEY, None)

print()
print("=" * 72)
print("F. API 오류 응답 처리 (원칙 4·7)")
print("=" * 72)
AUTH_ERR = b"""<OpenAPI_ServiceResponse><cmmMsgHeader>
<errMsg>SERVICE ERROR</errMsg>
<returnAuthMsg>SERVICE_KEY_IS_NOT_REGISTERED_ERROR</returnAuthMsg>
<returnReasonCode>30</returnReasonCode></cmmMsgHeader></OpenAPI_ServiceResponse>"""
try:
    rows, total, _n = collect.parse_trade_xml(AUTH_ERR, "apt", "26410", "202609")
    check("실거래 인증오류 응답이 예외로 걸러진다", False,
          "예외 없이 계약 %d건·totalCount %d 으로 '정상'이 된다 → aggregates 가 빈 배열로 덮여 직전 데이터가 사라진다"
          % (len(rows), total))
except Exception as exc:  # noqa: BLE001
    check("실거래 인증오류 응답이 예외로 걸러진다", True, type(exc).__name__)

LIMIT_ERR = b"""<response><header><resultCode>22</resultCode>
<resultMsg>LIMITED_NUMBER_OF_SERVICE_REQUESTS_EXCEEDS_ERROR</resultMsg></header></response>"""
try:
    collect.parse_trade_xml(LIMIT_ERR, "apt", "26410", "202609")
    check("resultCode 비정상은 예외", False)
except Exception:
    check("resultCode 비정상은 예외", True)

# 재검수(2026-09-03): 원 판정식은 `lh_extract_items` 가 오류 봉투에서 비어 있지 않은 items 를
# 돌려주기를 요구했다. 그 함수는 "PAN_NM 을 가진 dict 를 모으는" 순수 추출기라 어떤 구현으로도
# 만족할 수 없는 잘못된 판정식이었다(검수자 오류). 봉투 검사가 `check_lh_envelope()` 로 분리됐으니
# 판정을 그 함수로 옮기고, 대신 케이스를 넓혀 더 강하게 본다.
LH_ENVELOPES = [
    ("SS_CODE=N 인증오류",
     [{"resHeader": [{"SS_CODE": "N", "MSG": "인증키 오류", "ALL_CNT": "0"}]}, {"dsList": []}]),
    ("SS_CODE=E 파라미터오류",
     [{"resHeader": [{"SS_CODE": "E", "ERR_MSG": "필수 파라미터 누락"}]}]),
    ("SS_CODE 자체가 없는 봉투", [{"dsList": []}]),
    ("빈 리스트 응답", []),
    ("빈 dict 응답", {}),
]
for _label, _payload in LH_ENVELOPES:
    try:
        collect.check_lh_envelope(_payload)
        check("LH 오류 봉투가 예외로 걸러진다 - %s" % _label, False,
              "예외 없음 -> '공고 0건 수집 성공' 이 되어 직전 공고가 disappeared 로 뒤집힌다")
    except Exception as _exc:  # noqa: BLE001
        check("LH 오류 봉투가 예외로 걸러진다 - %s" % _label, True,
              "%s: %s" % (type(_exc).__name__, _exc))

OK_ENVELOPE = [{"resHeader": [{"SS_CODE": "Y", "ALL_CNT": "1"}]},
               {"dsList": [{"PAN_NM": "테스트", "CNP_CD_NM": "부산광역시"}]}]
try:
    collect.check_lh_envelope(OK_ENVELOPE)
    check("정상 봉투(SS_CODE=Y)는 통과한다", True)
except Exception as _exc:  # noqa: BLE001
    check("정상 봉투(SS_CODE=Y)는 통과한다", False, repr(_exc))

_skew = [{"resHeader": [{"SS_CODE": "Y", "ALL_CNT": "37"}]}, {"dsListRenamed": [{"TITLE": "x"}]}]
_items_skew, _cnt_skew = collect.lh_extract_items(_skew)
check("ALL_CNT>0 · 파싱 0건 조건이 성립(collect_lh 가 실패로 올려야 한다)",
      _cnt_skew > 0 and not _items_skew, "ALL_CNT=%d items=%d" % (_cnt_skew, len(_items_skew)))
_src = (collect.ROOT / "collect.py").read_text(encoding="utf-8")
check("봉투 검사가 collect_lh 페이지 루프에서 호출된다",
      "check_lh_envelope(payload)" in _src)
check("ALL_CNT>0 · 파싱 0건 가드가 collect_lh 에 있다",
      "all_count > 0 and not batch" in _src)
check("실거래 전 구간 0건 가드가 있다",
      "실거래 전 구간 합계 0건" in _src)
check("0건 수집 시 마감 판정 보류 가드가 있다",
      "0건 수집 — 마감 판정 보류" in _src)


print()
print("=" * 72)
print("G. 식별키 안정성 (§3-5, Q24 · Q45)")
print("=" * 72)


def mk(title, supply, gu):
    return {"source": "LH", "supply_type": supply, "sigungu_code": gu,
            "apply_end": None, "apply_start": None, "title": title, "_notice_no": None}


base = [mk("부산연제구 매입임대 A차 모집", "매입임대", "26470"),
        mk("부산연제구 매입임대 B차 모집", "매입임대", "26470")]
ids1 = {n["title"]: n["id"] for n in collect.assign_notice_ids([dict(x) for x in base])}
added = base + [mk("가나다 부산연제구 매입임대 신규 모집", "매입임대", "26470")]
ids2 = {n["title"]: n["id"] for n in collect.assign_notice_ids([dict(x) for x in added])}
moved = [t for t in ids1 if ids1[t] != ids2[t]]
check("공고 1건 추가 시 기존 공고 id 가 유지된다", not moved,
      "id 가 바뀐 기존 공고 %d건: %s → 다음 수집에서 '신규 공고' 오탐 + 기존 id 소멸(마감 오탐)"
      % (len(moved), [(t, ids1[t], ids2[t]) for t in moved]))

only_title = [mk("공고 X", None, None), mk("공고 Y", None, None), mk("공고 Z", None, None)]
res = collect.assign_notice_ids([dict(x) for x in only_title])
lvl0 = [n["title"] for n in res if n["id"] == collect.composite_id(n, 0)]
check("복합키 구성요소가 모두 null 인 공고가 제목 기반 키로 떨어지지 않는다",
      len(lvl0) == len(only_title),
      "level0 유지 %d/%d — 나머지는 정규화 제목이 키에 들어간다(§3-5 폴백 level2)"
      % (len(lvl0), len(only_title)))

same = [mk("동일 제목 공고", "행복주택", "26410"), mk("동일 제목 공고", "행복주택", "26410")]
res2 = collect.assign_notice_ids([dict(x) for x in same])
check("완전 동중복도 서로 다른 id 를 받는다",
      len({n["id"] for n in res2}) == 2, str([n["id"] for n in res2]))

print()
print("=" * 72)
print("G2. 식별키 순서 불변성 — 순열 전수 (DEF-4 재검수)")
print("=" * 72)
import itertools


def _mk2(title, supply, gu, url=None, no=None):
    return {"source": "LH", "supply_type": supply, "sigungu_code": gu,
            "apply_end": None, "apply_start": None, "title": title,
            "_notice_no": no, "_detail_url": url}


def _ids(rows):
    out = collect.assign_notice_ids([dict(r) for r in rows])
    return {(r["title"], r.get("_detail_url") or "", str(r.get("_notice_no") or "")): r["id"]
            for r in out}


# (1) 같은 재료(source+supply_type+sigungu_code)를 공유하는 공고 4건 — 제목·URL 만 다르다
pool = [
    _mk2("부산연제구 매입임대 A차 모집", "매입임대", "26470"),
    _mk2("부산연제구 매입임대 B차 모집", "매입임대", "26470"),
    _mk2("가나다 부산연제구 매입임대 신규", "매입임대", "26470"),
    _mk2("ㄱㄴㄷ 부산연제구 매입임대 추가", "매입임대", "26470"),
]
base = _ids(pool)
bad = []
for perm in itertools.permutations(pool):
    got = _ids(list(perm))
    if got != base:
        bad.append([r["title"] for r in perm])
check("입력 순서 24개 순열 전부에서 id 동일 (재료 겹치는 4건)", not bad,
      "불일치 순열 %d개" % len(bad))

# (2) 부분집합 -> 전체집합 확장: 기존 id 가 보존되는가
grow = []
for k in range(1, len(pool) + 1):
    ids_k = _ids(pool[:k])
    for key, val in _ids(pool[:k - 1]).items() if k > 1 else []:
        if ids_k.get(key) != val:
            grow.append((k, key[0], val, ids_k.get(key)))
check("공고를 1건씩 늘려도 기존 공고 id 가 바뀌지 않는다", not grow, str(grow))

# (3) 공고 1건 삭제 시 남은 공고 id 보존
drop = []
for skip in range(len(pool)):
    remain = [r for n, r in enumerate(pool) if n != skip]
    got = _ids(remain)
    for key, val in got.items():
        if base.get(key) != val:
            drop.append((skip, key[0], base.get(key), val))
check("공고 1건이 사라져도 남은 공고 id 가 바뀌지 않는다", not drop, str(drop))

# (4) 재료가 완전히 같은 3건 — #N 접미만 남는다(구분 불가 레코드의 한계)
triple = [_mk2("같은 제목", "행복주택", "26410") for _ in range(3)]
tids = sorted(r["id"] for r in collect.assign_notice_ids([dict(r) for r in triple]))
check("재료 완전 동일 3건은 #N 으로만 갈린다", len(set(tids)) == 3, str(tids))
t2 = sorted(r["id"] for r in collect.assign_notice_ids([dict(r) for r in triple[:2]]))
check("재료 완전 동일 레코드는 1건 줄면 #N 이 재배정된다(원리적 한계 — 결함으로 보지 않음)",
      t2 == tids[:2], "3건 %s -> 2건 %s" % (tids, t2))

# (5) PAN_ID 가 있으면 제목·URL 이 바뀌어도 id 불변
a = _mk2("원래 제목", "행복주택", "26410", url="https://x/1", no="0000059133")
b = _mk2("한 글자 고친 제목", "행복주택", "26410", url="https://x/2", no="0000059133")
ia = collect.assign_notice_ids([dict(a)])[0]["id"]
ib = collect.assign_notice_ids([dict(b)])[0]["id"]
check("PAN_ID 가 있으면 제목·URL 변경에도 id 불변", ia == ib, "%s vs %s" % (ia, ib))

# (6) 제목이 한 글자 바뀌면 복합키는 바뀐다 (§3-5 폴백의 알려진 성질)
c1 = collect.assign_notice_ids([dict(_mk2("제목 A", "매입임대", "26470"))])[0]["id"]
c2 = collect.assign_notice_ids([dict(_mk2("제목 B", "매입임대", "26470"))])[0]["id"]
check("복합키는 제목 변경 시 바뀐다(폴백의 알려진 성질 — 실데이터 감시 필요)", c1 != c2,
      "%s vs %s" % (c1, c2))

print()
print("=" * 72)
print("H. 지역 추출 (§3-4 · LH)")
print("=" * 72)
mb = lambda t: collect.match_busan_gu(CFG, t)
check("'부산금정구' → 금정구/26410", mb("2026년 부산금정구 행복주택 모집") == ("금정구", "26410"))
check("'부산 동래구' → 동래구/26260", mb("부산 동래구 국민임대") == ("동래구", "26260"))
check("구 이름 없는 전국 공고 → (None, None)", mb("2026년 통합공공임대주택 입주자 모집공고") == (None, None))
fp = mb("부산 수영장 인근 행복주택 모집")
check("'수영장' 이 수영구로 오인되지 않는다", fp == (None, None),
      "결과 %r — 구명 어간 부분일치가 오탐을 만든다" % (fp,))
fp2 = mb("사상 최대 규모 통합공공임대 모집")
check("'사상 최대' 가 사상구로 오인되지 않는다", fp2 == (None, None), "결과 %r" % (fp2,))
check("금정구 코드", CFG["busan_sigungu_codes"]["금정구"] == "26410")
check("동래구 코드", CFG["busan_sigungu_codes"]["동래구"] == "26260")
check("연제구 코드", CFG["busan_sigungu_codes"]["연제구"] == "26470")
check("시세 수집 시군구 3개 = 연제·동래·금정",
      set(CFG["sigungu_codes"]) == {"26470", "26260", "26410"})

print()
print("=" * 72)
print("I. 마감·임박 판정 (D12)")
print("=" * 72)
t = date(2026, 9, 3)
check("apply_end null → D-day 계산 안 함", collect.dday(None, t) is None)
check("apply_end == today → D-0", collect.dday("2026-09-03", t) == 0)
check("apply_end 어제 → 음수", collect.dday("2026-09-02", t) == -1)
check("잘못된 날짜 문자열 → None", collect.dday("미정", t) is None)

records = [
    {"key": "lh", "name": "LH", "kind": "semi", "status": "fail", "error": "e", "last_success": None},
    {"key": "policy", "name": "정책", "kind": "semi", "status": "skip", "error": "e", "last_success": None},
    {"key": "private", "name": "민간", "kind": "none", "status": "skip", "error": "e", "last_success": None},
    {"key": "trades", "name": "실거래", "kind": "auto", "status": "ok", "error": None, "last_success": "x"},
]
d = collect.build_diff(CFG, [], {}, {"date": "2026-09-02"}, records, t)
keys = [f["key"] for f in d["collector_failures"]]
check("collector_failures 에 fail·skip 포함, kind=none 제외", keys == ["lh", "policy"], str(keys))
has_status = all("status" in f for f in d["collector_failures"])
check("collector_failures[].status 필드가 있다 (§3-6)", has_status,
      "실제 키 %s — SPEC §3-6 은 status: 'fail'|'skip' 을 요구한다. 화면이 fail/skip 문구를 구분할 근거가 없다"
      % sorted(d["collector_failures"][0]))

ns = {"id": "LH:x", "apply_end": None, "disappeared": False, "notice_status": "접수마감"}
d2 = collect.build_diff(CFG, [ns], {"LH:x": dict(ns)}, {"date": "2026-09-02"}, [], t)
reasons = [r["reason"] for r in d2["closed_notices"]]
check("PAN_SS='접수마감' 공고가 reason='notice_status' 로 마감 처리된다",
      reasons == ["notice_status"],
      "실제 closed_notices=%r — build_diff 는 notice_status 를 보지 않는다(collect.py:1205-1213). "
      "§3-6 의 reason enum 중 notice_status 가 절대 생성되지 않는다" % d2["closed_notices"])

first = collect.build_diff(CFG, [], {}, None, [], t)
check("첫 실행 is_first_run=True 이고 신규 0건",
      first["is_first_run"] is True and first["new_notices"] == [])

print()
print("=" * 72)
print("J. meta 스키마 (§3-6)")
print("=" * 72)
mc = collect.meta_config(CFG)
need = ["base_station", "conversion_rate", "trade_months", "trend_months", "sample_min",
        "banjeonse_ratio", "deposit_hist_bucket", "notice_retain_days", "exclusion_rules",
        "sigungu_codes", "stations"]
missing = [k for k in need if k not in mc]
check("meta.config 에 §3-6 키 전부", not missing,
      "누락 %s (build.py 가 config.json 에서 다시 채우므로 화면은 성립하지만 data/meta.json 자체는 §3-6 과 다르다)"
      % missing)
check("meta.config.stations 가 1호선 순서를 유지",
      [s["name"] for s in mc["stations"]] == expect_order)
check("meta 에 refetched_months 없음 (D21)", "refetched_months" not in collect.META_CONFIG_KEYS)

print()
print("=" * 72)
print("결과 — NG %d건: %s" % (len(FAIL), FAIL))
sys.exit(1 if FAIL else 0)
