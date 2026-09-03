#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""독립 오라클 — data/fixtures/trades_*.xml 을 QA 가 따로 파싱해 집계하고
data/trades.json 과 대조한다.

collect.py 를 import 하지 않는다. 규칙은 docs/SPEC.md v1.2 §3-3 · §3-4 · §3-6 에서
직접 읽어 구현했다. 작성자 코드의 결과를 정답으로 삼지 않는다.

사용법
    python docs/qa/oracle_collect_trades.py
종료코드
    0 = 불일치 0건, 1 = 불일치 있음
"""

from __future__ import annotations

import json
import re
import statistics
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
FIX = ROOT / "data" / "fixtures"
CFG = json.loads((ROOT / "config.json").read_text(encoding="utf-8"))
TRADES = json.loads((ROOT / "data" / "trades.json").read_text(encoding="utf-8"))
META = json.loads((ROOT / "data" / "meta.json").read_text(encoding="utf-8"))

BUCKET = int(CFG["deposit_hist_bucket"])
RATIO = float(CFG["banjeonse_ratio"])
RATE = float(CFG["conversion_rate"])

problems: list[str] = []


def note(msg: str) -> None:
    problems.append(msg)
    print("불일치: " + msg)


# ---------------------------------------------------------------- 1. fixture 파싱
FNAME = re.compile(r"^trades_(apt|villa|officetel)_(\d{5})_(\d{6})(?:_p(\d+))?\.xml$")


def num(text):
    return int(round(float(str(text).replace(",", "").strip())))


def parse_all():
    """fixture 전체를 파일명 순으로 파싱. 페이지 파일(_pN)도 같은 구간에 합친다."""
    by_slot = {}
    totals = {}
    for path in sorted(FIX.glob("trades_*.xml")):
        m = FNAME.match(path.name)
        if not m:
            print("건너뜀(이름 규칙 밖): %s" % path.name)
            continue
        htype, lawd, ym, _page = m.group(1), m.group(2), m.group(3), m.group(4)
        root = ET.fromstring(path.read_text(encoding="utf-8"))
        code = (root.findtext(".//resultCode") or "").strip()
        if code not in ("00", "0", "000"):
            note("%s resultCode=%s" % (path.name, code))
        total = num(root.findtext(".//totalCount") or 0)
        slot = (htype, lawd, ym)
        totals.setdefault(slot, total)
        if totals[slot] != total:
            note("%s totalCount 가 페이지마다 다르다" % path.name)
        rows = by_slot.setdefault(slot, [])
        for item in root.iter("item"):
            f = {c.tag: (c.text or "").strip() for c in item}
            deposit = num(f["보증금액"])
            rent = num(f["월세금액"])
            rows.append(
                {
                    "ym": "%04d%02d" % (num(f["계약년도"]), num(f["계약월"])),
                    "housing_type": htype,
                    "dong": f["법정동"].strip(),
                    "deposit": deposit,
                    "rent": rent,
                }
            )
    return by_slot, totals


by_slot, totals = parse_all()

# Q55 — 구간별 계약 건수 == 응답 totalCount
for slot, rows in sorted(by_slot.items()):
    if len(rows) != totals[slot]:
        note("Q55 %s: fixture 계약 %d건 != totalCount %d" % (slot, len(rows), totals[slot]))
print("[1] fixture 구간 %d개 · 계약 %d건 (totalCount 합 %d)"
      % (len(by_slot), sum(len(r) for r in by_slot.values()), sum(totals.values())))

contracts = [row for rows in by_slot.values() for row in rows]

# ---------------------------------------------------------------- 2. 분류·매핑
def deal_type(deposit, rent):
    """SPEC §3-3 — 월세 0 → 전세 / 보증금 >= 월세 x 240 → 반전세 / 그 외 월세."""
    if rent == 0:
        return "jeonse"
    if deposit >= rent * RATIO:
        return "banjeonse"
    return "wolse"


dong_map = {}
for st in CFG["stations"]:
    for dong in st["dongs"]:
        dong_map.setdefault(dong, []).append(st["id"])

window = sorted({c["ym"] for c in contracts})
groups = {}
excluded = 0
for c in contracts:
    stations = dong_map.get(c["dong"])
    if not stations:
        excluded += 1
        continue
    dt = deal_type(c["deposit"], c["rent"])
    for sid in stations:
        groups.setdefault((sid, c["housing_type"], dt), []).append(c)

print("[2] 미매핑 계약 %d건 · 집계 조합 %d개 · 구간 %s" % (excluded, len(groups), window))
if META.get("excluded_trade_count") != excluded:
    note("meta.excluded_trade_count=%r != 오라클 %d" % (META.get("excluded_trade_count"), excluded))

# ---------------------------------------------------------------- 3. 통계
def pct_linear(values, p):
    """선형 보간 분위수 (numpy 기본 'linear' 과 동일 정의)."""
    if not values:
        return None
    if len(values) == 1:
        return float(values[0])
    pos = (len(values) - 1) * p
    lo = int(pos)
    hi = min(lo + 1, len(values) - 1)
    frac = pos - lo
    return values[lo] * (1 - frac) + values[hi] * frac


def pct_nearest(values, p):
    """최근접 순위(nearest-rank) 분위수 — 대안 정의. 어느 쪽이 쓰였는지 판별용."""
    if not values:
        return None
    import math
    k = max(1, math.ceil(p * len(values)))
    return float(values[k - 1])


def hist(values):
    """SPEC D6 — 폭 BUCKET, lo 오름차순, 마지막 버킷 hi=null 개방."""
    if not values:
        return []
    lo0 = (min(values) // BUCKET) * BUCKET
    top = max(values)
    edges = []
    lo = lo0
    while lo <= top:
        edges.append(lo)
        lo += BUCKET
    out = [{"lo": e, "hi": e + BUCKET, "count": 0} for e in edges]
    out[-1]["hi"] = None
    for v in values:
        idx = min(int((v - lo0) // BUCKET), len(out) - 1)
        out[max(idx, 0)]["count"] += 1
    return out


expected = {}
for key, rows in groups.items():
    dep = sorted(r["deposit"] for r in rows)
    rents = sorted(r["rent"] for r in rows if r["rent"])
    # D17 — 계약별 전세환산액의 중위 (중위값을 환산한 값이 아니다)
    equiv = sorted(r["deposit"] + r["rent"] * 12 * 100.0 / RATE for r in rows)
    monthly = []
    for ym in window:
        mr = [r for r in rows if r["ym"] == ym]
        if mr:
            monthly.append({
                "ym": ym,
                "count": len(mr),
                "deposit_median": int(round(statistics.median(r["deposit"] for r in mr))),
            })
    expected[key] = {
        "count": len(rows),
        "deposit_median": int(round(statistics.median(dep))),
        "deposit_p25_linear": int(round(pct_linear(dep, 0.25))),
        "deposit_p75_linear": int(round(pct_linear(dep, 0.75))),
        "deposit_p25_nearest": int(round(pct_nearest(dep, 0.25))),
        "deposit_p75_nearest": int(round(pct_nearest(dep, 0.75))),
        "deposit_hist": hist(dep),
        "rent_median": int(round(statistics.median(rents))) if rents else None,
        "jeonse_equiv_median": int(round(statistics.median(equiv))),
        "monthly": monthly,
        "deposits": dep,
    }

# ---------------------------------------------------------------- 4. 대조
actual = {}
for a in TRADES.get("aggregates") or []:
    k = (a["station_id"], a["housing_type"], a["deal_type"])
    if k in actual:
        note("trades.json 에 중복 집계 키 %s" % (k,))
    actual[k] = a

for k in sorted(set(expected) | set(actual)):
    if k not in actual:
        note("trades.json 에 조합 %s 가 없다 (오라클 count=%d)" % (k, expected[k]["count"]))
        continue
    if k not in expected:
        note("trades.json 에 오라클에 없는 조합 %s (count=%d)" % (k, actual[k]["count"]))
        continue
    e, a = expected[k], actual[k]
    for field in ("count", "deposit_median", "jeonse_equiv_median", "rent_median"):
        if a.get(field) != e[field]:
            note("%s.%s: 실제 %r != 오라클 %r" % (k, field, a.get(field), e[field]))
    if a.get("deposit_p25") not in (e["deposit_p25_linear"], e["deposit_p25_nearest"]):
        note("%s.deposit_p25: 실제 %r != 선형 %r / 최근접 %r"
             % (k, a.get("deposit_p25"), e["deposit_p25_linear"], e["deposit_p25_nearest"]))
    if a.get("deposit_p75") not in (e["deposit_p75_linear"], e["deposit_p75_nearest"]):
        note("%s.deposit_p75: 실제 %r != 선형 %r / 최근접 %r"
             % (k, a.get("deposit_p75"), e["deposit_p75_linear"], e["deposit_p75_nearest"]))
    if a.get("deposit_hist") != e["deposit_hist"]:
        note("%s.deposit_hist: 실제 %r != 오라클 %r" % (k, a.get("deposit_hist"), e["deposit_hist"]))
    if a.get("monthly") != e["monthly"]:
        note("%s.monthly: 실제 %r != 오라클 %r" % (k, a.get("monthly"), e["monthly"]))
    # SPEC §3-6 — deposit_hist 의 count 합 == count
    hsum = sum(b.get("count", 0) for b in (a.get("deposit_hist") or []))
    if hsum != a.get("count"):
        note("%s: deposit_hist count 합 %d != count %d" % (k, hsum, a.get("count")))
    h = a.get("deposit_hist") or []
    if h:
        if h[-1].get("hi") is not None:
            note("%s: 마지막 버킷 hi 가 null 이 아니다 (%r)" % (k, h[-1].get("hi")))
        los = [b["lo"] for b in h]
        if los != sorted(los):
            note("%s: deposit_hist lo 가 오름차순이 아니다" % (k,))
        for b in h[:-1]:
            if b.get("hi") != b["lo"] + BUCKET:
                note("%s: 버킷 폭이 %d 이 아니다 (%r)" % (k, BUCKET, b))
        # 히스토그램이 실제 보증금 분포와 맞는지 값 단위로 재검증
        for v in e["deposits"]:
            hits = [b for b in h
                    if b["lo"] <= v and (b["hi"] is None or v < b["hi"])]
            if len(hits) != 1:
                note("%s: 보증금 %d 이 버킷 %d개에 걸린다" % (k, v, len(hits)))

# 유형 미혼합 (Q21) — 한 집계 행의 계약이 모두 같은 housing_type 인지
for k, rows in groups.items():
    kinds = {r["housing_type"] for r in rows}
    if len(kinds) != 1 or kinds != {k[1]}:
        note("Q21 %s: housing_type 혼합 %r" % (k, kinds))

# latest_contract_ym
exp_latest = max(c["ym"] for c in contracts) if contracts else None
if TRADES.get("latest_contract_ym") != exp_latest:
    note("latest_contract_ym: 실제 %r != 오라클 %r" % (TRADES.get("latest_contract_ym"), exp_latest))

# months 필드 = 집계 창 길이
for k, a in sorted(actual.items()):
    if a.get("months") != len(window):
        note("%s.months: 실제 %r != 창 길이 %d" % (k, a.get("months"), len(window)))

# 표본 부족 (Q20) — sample_min 미만 조합 목록만 출력(판정은 화면 검수 몫)
low = [(k, a["count"]) for k, a in sorted(actual.items()) if a["count"] < int(CFG["sample_min"])]
print("[3] 표본 %d건 미만 조합 %d/%d 개: %s"
      % (int(CFG["sample_min"]), len(low), len(actual), low[:8]))

# 반전세 경계 (§3-3) — 경계값 계약이 실제로 어느 분류로 갔는지 표시
for c in contracts:
    if c["rent"]:
        boundary = c["rent"] * RATIO
        if abs(c["deposit"] - boundary) <= 1:
            print("[4] 경계 계약 보증금=%d 월세=%d (경계 %g) → %s"
                  % (c["deposit"], c["rent"], boundary, deal_type(c["deposit"], c["rent"])))

print()
print("조합 %d개 대조 완료 — 불일치 %d건" % (len(expected), len(problems)))
sys.exit(1 if problems else 0)
