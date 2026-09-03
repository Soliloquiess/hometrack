# -*- coding: utf-8 -*-
"""hometrack QA - SPEC v1.2 3-1 / 3-2 를 검수자가 별도로 구현한 독립 판정 오라클.

site/index.html 의 JS 구현을 참고하지 않고 명세 문장만 보고 썼다.
비교는 판정 등급(ok/cond/no)과 불변식(배지·강등)만 한다 - 사유 문구는 별도 항목으로 본다.
"""
import json, datetime, os

# QA_ROOT 로 검수 대상 스냅샷(예: 커밋 8ac4a07 추출본)을 지정할 수 있다.
ROOT = os.environ.get('QA_ROOT') or os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DAYS_PER_MONTH = 365.25 / 12


def load_data():
    j = lambda p: json.load(open(os.path.join(ROOT, p), encoding='utf-8'))
    return {
        'meta': j('data/meta.json'),
        'notices': j('data/notices.json'),
        'policies': j('data/policies.json'),
        'income_tables': j('data/income_tables.json'),
        'trades': j('data/trades.json'),
        'diff': j('data/snapshot_diff.json'),
        'diff_history': j('data/diff_history.json'),
        'config': j('config.json'),
    }


# ------------------------------------------------------------------ 3-1 예산
RANK = {'all': 3, 'part': 2, 'over': 1}


def deposit_axis(n, avail):
    """D10 - deposit_min 이 null 이면 상한이 있어도 판정하지 않는다."""
    if n.get('deposit_min') is None:
        return 'none'
    if n.get('deposit_max') is None:
        return 'over' if n['deposit_min'] > avail else 'part'
    if n['deposit_min'] > avail:
        return 'over'
    if n['deposit_max'] <= avail:
        return 'all'
    return 'part'


def rent_axis(n, cap):
    """D9 - 거래유형 선택과 무관하게 항상 적용. 상한 미입력이면 판정 없음."""
    if cap is None:
        return 'none'
    rmin, rmax = n.get('rent_min'), n.get('rent_max')
    if rmin is None and rmax is None:
        return 'none'
    if rmin is None:
        rmin = rmax
    if rmax is None:
        rmax = rmin
    if rmin > cap:
        return 'over'
    if rmax <= cap:
        return 'all'
    return 'part'


def budget_of(n, cond):
    if cond.get('deposit') is None and cond.get('loan') is None:
        return 'none'
    avail = (cond.get('deposit') or 0) + (cond.get('loan') or 0)
    d = deposit_axis(n, avail)
    r = rent_axis(n, cond.get('rentCap'))
    if d == 'none' and r == 'none':
        return 'unknown'
    graded = [x for x in (d, r) if x != 'none']
    return min(graded, key=lambda k: RANK[k])


def ratio_within(agg, avail, sample_min):
    """D6 - deposit_hist 만으로 계산. 마지막 개방 버킷의 비례분은 0."""
    if not agg or not agg.get('count') or agg['count'] < sample_min:
        return None
    if avail is None:
        return None
    hist = agg.get('deposit_hist') or []
    if not hist:
        return None
    total = 0.0
    within = 0.0
    for b in hist:
        c = b.get('count') or 0
        total += c
        hi, lo = b.get('hi'), b['lo']
        if hi is not None and hi <= avail:
            within += c
        elif lo <= avail and (hi is None or avail < hi):
            if hi is not None:
                within += c * (avail - lo) / (hi - lo)
    if total < sample_min:
        return None
    return max(0.0, min(1.0, within / total))


# ------------------------------------------------------------------ 3-2 자격
def applied_pct(inc, cond):
    dual_ok = bool(cond.get('dual')) and inc.get('pct_dual') is not None
    base = inc.get('pct_dual') if dual_ok else inc.get('pct')
    if base is None:
        return None
    adj = 0
    tbl = inc.get('pct_adjust_by_household') or {}
    h = cond.get('household')
    if h is not None and tbl.get(str(h)) is not None:
        adj = tbl[str(h)] or 0
    return {'base': base, 'adjust': adj, 'pct': base + adj}


def income_limit(inc, cond, tables):
    tbl = tables['urban_worker'] if inc['basis'] == 'urban_worker_pct' else tables['median_income']
    a = applied_pct(inc, cond)
    if a is None:
        return (None, None, False)
    if cond.get('household') is None:
        return (None, a, False)
    row = tbl['by_household'].get(str(cond['household']))
    if row is None:
        return (None, a, False)
    direct = row.get(str(a['pct']))
    if direct is not None:
        return (direct, a, False)
    hundred = row.get('100')
    if hundred is None:
        return (None, a, False)
    return (hundred * a['pct'] / 100.0, a, True)


def judge_income(p, cond, tables):
    inc = (p.get('criteria') or {}).get('income')
    if not inc or not inc.get('basis'):
        return []
    if cond.get('income') is None:
        return [{'k': 'cond', 'why': 'income-missing'}]
    if inc['basis'] == 'annual_krw':
        if inc.get('amount') is None:
            return [{'k': 'cond', 'why': 'income-limit-missing'}]
        if cond['income'] > inc['amount']:
            return [{'k': 'no', 'incomeOver': True, 'approx': False, 'why': 'income-over-annual'}]
        return []
    if cond.get('household') is None:
        return [{'k': 'cond', 'why': 'household-missing'}]
    if cond.get('dual') is None and inc.get('pct_dual') is not None:
        return [{'k': 'cond', 'why': 'dual-missing'}]
    limit, _a, approx = income_limit(inc, cond, tables)
    if limit is None:
        return [{'k': 'cond', 'why': 'limit-unavailable'}]
    mine = cond['income'] * 10000.0 / 12.0
    if mine > limit:
        return [{'k': 'no', 'incomeOver': True, 'approx': approx, 'why': 'income-over-pct'}]
    return []


def judge_assets(p, cond):
    c = p.get('criteria') or {}
    out, missing = [], []
    for key, inp, nm in (('total_asset_limit', 'totalAsset', 'total'),
                         ('net_asset_limit', 'netAsset', 'net'),
                         ('car_value_limit', 'carValue', 'car')):
        lim = c.get(key)
        if lim is None:
            continue
        v = cond.get(inp)
        if v is None:
            missing.append(nm)
            continue
        if v > lim:
            out.append({'k': 'no', 'why': 'asset-over-' + nm})
    if missing:
        out.append({'k': 'cond', 'why': 'asset-missing-' + '.'.join(missing)})
    return out


def judge_savings(p, cond):
    c = p.get('criteria') or {}
    if c.get('savings_months_min') is None and c.get('savings_count_min') is None:
        return []
    if cond.get('savingsMonths') is None and cond.get('savingsCount') is None:
        return [{'k': 'cond', 'why': 'savings-missing'}]
    out = []
    if (c.get('savings_months_min') is not None and cond.get('savingsMonths') is not None
            and cond['savingsMonths'] < c['savings_months_min']):
        out.append({'k': 'no', 'why': 'savings-months-short'})
    if (c.get('savings_count_min') is not None and cond.get('savingsCount') is not None
            and cond['savingsCount'] < c['savings_count_min']):
        out.append({'k': 'no', 'why': 'savings-count-short'})
    return out


def judge_nohome(p, cond):
    if not (p.get('criteria') or {}).get('no_home_required'):
        return []
    if cond.get('noHome') == 'no':
        return [{'k': 'no', 'why': 'has-home'}]
    if cond.get('noHome') != 'yes':
        return [{'k': 'cond', 'why': 'nohome-missing'}]
    return []


def judge_age(p, cond):
    if (p.get('criteria') or {}).get('age_max') is None:
        return []
    return [{'k': 'cond', 'why': 'age-no-input'}]


def judge_region(p, cond):
    r = (p.get('criteria') or {}).get('region')
    if r is None or r == '전국' or '부산' in str(r):
        return []
    return [{'k': 'cond', 'why': 'region-mismatch'}]


def parse_date(s):
    s = str(s or '').strip()
    if not s:
        return None
    try:
        return datetime.date(int(s[0:4]), int(s[5:7]), int(s[8:10]))
    except Exception:
        return None


def months_delta(s, now_date):
    d = parse_date(s)
    if d is None:
        return None
    return (d - now_date).days / DAYS_PER_MONTH


def judge_marriage(p, cond, now_date):
    c = p.get('criteria') or {}
    needs = (c.get('marriage_within_months') is not None
             or c.get('pre_marriage_allowed') is False
             or c.get('pre_marriage_within_months') is not None)
    if not cond.get('marry'):
        return [{'k': 'cond', 'why': 'marry-missing'}] if needs else []
    m = months_delta(cond['marry'], now_date)
    if m is None:
        return [{'k': 'cond', 'why': 'marry-unparsable'}]
    if m > 0:
        if c.get('pre_marriage_allowed') is False:
            return [{'k': 'cond', 'why': 'pre-not-allowed'}]
        if c.get('pre_marriage_within_months') is not None and m > c['pre_marriage_within_months']:
            return [{'k': 'cond', 'why': 'pre-window-over'}]
        return []
    if c.get('marriage_within_months') is None:
        return []
    if -m <= c['marriage_within_months']:
        return []
    return [{'k': 'no', 'why': 'marriage-years-over'}]


def judge_policy(p, cond, tables, now_date):
    conf = p.get('confidence') or 'unverified'
    pend = bool(p.get('pending_change'))
    issues = (judge_marriage(p, cond, now_date) + judge_income(p, cond, tables)
              + judge_assets(p, cond) + judge_savings(p, cond)
              + judge_nohome(p, cond) + judge_age(p, cond) + judge_region(p, cond))
    hard, gates, badges = [], [], set()
    for r in issues:
        if r['k'] != 'no':
            continue
        if r.get('approx'):
            badges.add('approx')
            gates.append('approx')
            continue
        if conf != 'official':
            gates.append('nonofficial')
            continue
        if pend and r.get('incomeOver'):
            badges.add('pending')
            gates.append('pending')
            continue
        hard.append(r)
    if hard:
        return {'k': 'no', 'reasons': sorted(r['why'] for r in hard), 'badges': sorted(badges)}
    conds = [r['why'] for r in issues if r['k'] == 'cond']
    if conf != 'official' and not gates and not conds:
        conds = ['nonofficial-note']
    if gates or conds:
        return {'k': 'cond', 'reasons': sorted(set(gates + conds)), 'badges': sorted(badges)}
    return {'k': 'ok', 'reasons': [], 'badges': sorted(badges)}


# ------------------------------------------------------------------ 공고 자격
def norm(s):
    return ''.join(str(s or '').split())


EXCL_INPUTS = {
    'noHome': lambda cond: cond.get('noHome') == 'no',
    'householder': lambda cond: cond.get('householder') == 'no',
}


def exclusion_hit(n, cond, rules):
    for e in (n.get('exclusions') or []):
        ne = norm(e)
        for r in rules:
            if (r.get('match') or 'contains') != 'contains':
                continue
            if norm(r.get('keyword')) not in ne:
                continue
            test = EXCL_INPUTS.get(r.get('input'))
            if test and test(cond):
                return e
    return None


def judge_notice(n, cond, policies, rules, tables, now_date):
    if exclusion_hit(n, cond, rules):
        return {'k': 'no', 'why': 'exclusion'}
    lpid = n.get('linked_policy_id')
    if not lpid:
        return {'k': 'cond', 'why': 'no-link'}
    p = next((x for x in policies if x.get('id') == lpid), None)
    if p is None:
        return {'k': 'cond', 'why': 'dangling'}
    pv = judge_policy(p, cond, tables, now_date)
    if pv['k'] == 'ok':
        return {'k': 'ok', 'why': 'inherit-ok', 'policy': p['name']}
    if pv['k'] == 'no':
        return {'k': 'cond', 'why': 'inherit-no-downgraded', 'policy': p['name']}
    return {'k': 'cond', 'why': 'inherit-cond', 'policy': p['name']}


if __name__ == '__main__':
    D = load_data()
    print('policies', len(D['policies']), 'notices', len(D['notices']))
