"""연구자 제안값(docs/proposals/*.json) → data/policies.json, data/income_tables.json 이관.

SPEC §3-6 스키마의 키를 전부 갖추도록 정규화하고(없는 키는 null), 스키마 밖 키와
id 없는 메타 항목은 버린다. 값은 바꾸지 않는다. 표준 라이브러리만.
"""
import json, sys, pathlib

ROOT = pathlib.Path(__file__).resolve().parent.parent
PROP = ROOT / "docs" / "proposals"
DATA = ROOT / "data"

INCOME_KEYS = ["basis", "pct", "pct_dual", "pct_adjust_by_household", "amount", "note"]
CRIT_KEYS = ["marriage_within_months", "pre_marriage_allowed", "pre_marriage_within_months",
             "no_home_required", "income", "total_asset_limit", "net_asset_limit",
             "car_value_limit", "savings_months_min", "savings_count_min", "age_max", "region"]
BENEFIT_KEYS = ["summary", "limit_amount", "rate_note"]
PENDING_KEYS = ["summary", "source_url", "effective"]
TOP_KEYS = ["id", "name", "provider", "category", "confidence", "criteria", "benefit",
            "pending_change", "source_url", "content_id", "source_hash", "last_notified_hash",
            "verified_at", "note"]
CONF = {"official", "secondary", "unverified"}
CAT = {"supply", "loan", "subsidy"}
BASIS = {"urban_worker_pct", "median_pct", "annual_krw"}


def pick(src, keys, defaults=None):
    defaults = defaults or {}
    return {k: src.get(k, defaults.get(k)) for k in keys}


def normalize_policy(p, warn):
    out = pick(p, TOP_KEYS)
    crit = pick(p.get("criteria") or {}, CRIT_KEYS, {"pre_marriage_allowed": False, "no_home_required": True})
    inc = pick((p.get("criteria") or {}).get("income") or {}, INCOME_KEYS)
    crit["income"] = inc
    out["criteria"] = crit
    out["benefit"] = pick(p.get("benefit") or {}, BENEFIT_KEYS, {"summary": ""})
    pc = p.get("pending_change")
    out["pending_change"] = pick(pc, PENDING_KEYS, {"effective": "unknown"}) if pc else None
    # 구 필드명 content_selector → content_id ("#id" 단일 형식만 승계, D14)
    sel = p.get("content_selector")
    if out["content_id"] is None and isinstance(sel, str) and sel.startswith("#") and " " not in sel:
        out["content_id"] = sel
    if out["source_hash"] is None:
        out["source_hash"] = ""
    if out["confidence"] not in CONF:
        warn.append(f"{out['id']}: confidence={out['confidence']!r} → unverified 로 강등")
        out["confidence"] = "unverified"
    if out["category"] not in CAT:
        warn.append(f"{out['id']}: category={out['category']!r}")
    if inc["basis"] not in BASIS:
        warn.append(f"{out['id']}: income.basis={inc['basis']!r}")
    dropped = set(p) - set(TOP_KEYS)
    if dropped:
        warn.append(f"{out['id']}: 스키마 밖 키 제거 {sorted(dropped)}")
    return out


def main():
    warn = []
    raw = json.loads((PROP / "policies.json").read_text(encoding="utf-8"))
    items = raw.get("policies", raw) if isinstance(raw, dict) else raw
    pols = [normalize_policy(p, warn) for p in items if isinstance(p, dict) and p.get("id")]
    ids = [p["id"] for p in pols]
    assert len(ids) == len(set(ids)), "정책 id 중복"

    it = json.loads((PROP / "income_tables.json").read_text(encoding="utf-8"))
    tables = {}
    for name in ("urban_worker", "median_income"):
        t = it.get(name) or {}
        bh = {}
        for hh, row in (t.get("by_household") or {}).items():
            bh[str(hh)] = {str(k): int(v) for k, v in row.items() if v is not None}
        tables[name] = {
            "year_label": t.get("year_label", ""),
            "source_url": t.get("source_url", ""),
            "verified_at": t.get("verified_at", ""),
            "confidence": t.get("confidence", "unverified"),
            "by_household": bh,
        }
    tables["updated_at"] = it.get("updated_at") or it.get("_meta", {}).get("updated_at", "")

    DATA.mkdir(exist_ok=True)
    (DATA / "policies.json").write_text(json.dumps(pols, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    (DATA / "income_tables.json").write_text(json.dumps(tables, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(f"policies: {len(pols)} → data/policies.json  ids={ids}")
    print(f"income_tables: urban_worker households={sorted(tables['urban_worker']['by_household'])} "
          f"median households={sorted(tables['median_income']['by_household'])}")
    for w in warn:
        print("WARN", w)
    return 0


if __name__ == "__main__":
    sys.exit(main())
