# -*- coding: utf-8 -*-
"""hometrack QA - oracle_site_grid.js 가 덤프한 site/index.html 판정 결과를
oracle_site_judge.py(독립 구현)와 전수 대조하고 SPEC 불변식을 검사한다.

python docs/qa/oracle_site_compare.py <grid.json>
"""
import json, sys, os, datetime, collections

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import oracle_site_judge as O

NOW_DATE = datetime.date(2026, 9, 3)


def main(path):
    D = O.load_data()
    tables = D['income_tables']
    policies = D['policies']
    pol_by_id = {p['id']: p for p in policies}
    rules = D['config']['exclusion_rules']
    sample_min = D['config']['sample_min']

    mismatch = collections.Counter()
    examples = {}
    inv = collections.Counter()
    inv_ex = {}
    counts = collections.Counter()
    synth = {}
    seen_verdicts = collections.Counter()
    badge_seen = collections.Counter()

    def note(bucket, key, payload):
        bucket[key] += 1
        store = examples if bucket is mismatch else inv_ex
        store.setdefault(key, payload)

    with open(path, encoding='utf-8') as f:
        header = json.loads(f.readline())
        synth = {n['id']: n for n in header['meta']['synth']}
        for line in f:
            rec = json.loads(line)
            if rec.get('t') == 'p':
                cond = rec['cond']
                for got in rec['pol']:
                    p = pol_by_id[got['id']]
                    exp = O.judge_policy(p, cond, tables, NOW_DATE)
                    counts['policy_evals'] += 1
                    seen_verdicts[(got['id'], got['k'])] += 1
                    for b in got['badges']:
                        badge_seen[b] += 1
                    if exp['k'] != got['k']:
                        note(mismatch, ('policy_k', got['id'], exp['k'], got['k']),
                             {'cond': cond, 'expected': exp, 'got': got})
                    # 불변식 Q12 - 비official 정책에서 불가 0
                    if got['k'] == 'no' and p.get('confidence') != 'official':
                        note(inv, ('Q12_nonofficial_no', got['id']), {'cond': cond, 'got': got})
                    # 불변식 Q16 - 근사값 기반 사유가 "불가"로 남지 않는다 (기준 단위, D11)
                    #   SPEC §3-2 결합 2단: "official 이고 근사값이 아닌 불가 사유"만 불가.
                    #   따라서 카드 자체는 다른(하드) 사유로 불가일 수 있다 - 그건 정상.
                    if got['k'] == 'no':
                        ii = O.judge_income(p, cond, tables)
                        if any(r['k'] == 'no' and r.get('approx') for r in ii):
                            note(inv, ('Q16_approx_reason_no', got['id']), {'cond': cond, 'got': got})
                        # 불변식 Q31 - pending_change + 소득초과 사유가 불가로 남지 않는다
                        if p.get('pending_change') and any(
                                r['k'] == 'no' and r.get('incomeOver') and not r.get('approx') for r in ii):
                            note(inv, ('Q31_pending_income_reason_no', got['id']), {'cond': cond, 'got': got})
                    # 불변식 Q32 - 유주택(하드 불가)이 다른 사유에 삼켜지지 않는다
                    if cond.get('noHome') == 'no' and (p.get('criteria') or {}).get('no_home_required') \
                            and p.get('confidence') == 'official':
                        if got['k'] != 'no' or '유주택' not in (got['why'] or ''):
                            note(inv, ('Q32_hasHome_swallowed', got['id'], got['k']),
                                 {'cond': cond, 'got': got})
                    # 불변식 Q17 - 사유 없는 배지 0
                    if not (got.get('why') or '').strip():
                        note(inv, ('Q17_empty_why', got['id'], got['k']), {'cond': cond, 'got': got})
                    # 불변식 Q33 - 강등되면 사유에 '참고:' 가 남는다
                    if got['k'] == 'cond' and got['badges'] and '참고:' not in (got['why'] or ''):
                        note(inv, ('Q33_no_note', got['id'], tuple(got['badges'])),
                             {'cond': cond, 'got': got})
                    # NaN/undefined/Infinity 누출
                    w = got.get('why') or ''
                    for bad in ('NaN', 'undefined', 'Infinity', 'null%', '[object'):
                        if bad in w:
                            note(inv, ('leak_' + bad, got['id']), {'cond': cond, 'got': got})
            elif rec.get('t') == 'n':
                cond = rec['cond']
                allnotices = {n['id']: n for n in D['notices']}
                allnotices.update(synth)
                for got in rec['notices']:
                    n = allnotices[got['id']]
                    exp = O.judge_notice(n, cond, policies, rules, tables, NOW_DATE)
                    counts['notice_evals'] += 1
                    if exp['k'] != got['k']:
                        note(mismatch, ('notice_k', got['id'], exp['k'], got['k']),
                             {'cond': cond, 'expected': exp, 'got': got})
                    expb = O.budget_of(n, cond)
                    if expb != got['budget']:
                        note(mismatch, ('notice_budget', got['id'], expb, got['budget']),
                             {'cond': cond, 'expected': expb, 'got': got})
                    # Q13 - 승계된 불가 0
                    if got['k'] == 'no':
                        hit = O.exclusion_hit(n, cond, rules)
                        if not hit:
                            note(inv, ('Q13_inherited_no', got['id']), {'cond': cond, 'got': got})
                    # Q15 - linked null → 조건부
                    if not n.get('linked_policy_id') and got['k'] != 'cond':
                        hit = O.exclusion_hit(n, cond, rules)
                        if not hit:
                            note(inv, ('Q15_null_link', got['id'], got['k']), {'cond': cond, 'got': got})
                    # Q14 - 승계 사유에 정책명
                    if n.get('linked_policy_id') in pol_by_id and got['k'] in ('ok', 'cond'):
                        nm = pol_by_id[n['linked_policy_id']]['name']
                        if not O.exclusion_hit(n, cond, rules) and nm not in (got['why'] or ''):
                            note(inv, ('Q14_no_policy_name', got['id'], got['k']),
                                 {'cond': cond, 'got': got})
                    # Q46 - apply_end null → dday 계산 안 함 + --hi 아님
                    if n.get('apply_end') is None:
                        if got['dday'] is not None or got['ddayCls'] != 'dday-off':
                            note(inv, ('Q46_null_dday', got['id']), {'cond': cond, 'got': got})
                    # Q11/Q40 - deposit_min null → unknown/none (예산 밖 아님)
                    if n.get('deposit_min') is None and got['budget'] == 'over':
                        rm = n.get('rent_min')
                        rx = n.get('rent_max')
                        if rm is None and rx is None:
                            note(inv, ('Q11_null_over', got['id']), {'cond': cond, 'got': got})
                    if not (got.get('why') or '').strip():
                        note(inv, ('Q17_notice_empty_why', got['id'], got['k']), {'cond': cond, 'got': got})
                    w = (got.get('why') or '') + '|' + (got.get('budgetWhy') or '')
                    for bad in ('NaN', 'undefined', 'Infinity', '[object'):
                        if bad in w:
                            note(inv, ('leak_notice_' + bad, got['id']), {'cond': cond, 'got': got})
            elif rec.get('t') == 'r':
                av = rec['avail']
                aggs = {(a['station_id'], a['housing_type'], a['deal_type']): a
                        for a in D['trades']['aggregates']}
                for got in rec['aggs']:
                    a = aggs[(got['station_id'], got['housing_type'], got['deal_type'])]
                    exp = O.ratio_within(a, av, sample_min)
                    counts['ratio_evals'] += 1
                    if exp is None or got['r'] is None:
                        if (exp is None) != (got['r'] is None):
                            note(mismatch, ('ratio_none', got['station_id'], got['housing_type'],
                                            got['deal_type'], av), {'expected': exp, 'got': got})
                    elif abs(exp - got['r']) > 1e-9:
                        note(mismatch, ('ratio_val', got['station_id'], got['housing_type'],
                                        got['deal_type'], av), {'expected': exp, 'got': got})

    print('== 평가 건수 ==')
    for k, v in sorted(counts.items()):
        print('  %-16s %d' % (k, v))
    print('== 판정 분포 (정책 x 등급) ==')
    for (pid, k), v in sorted(seen_verdicts.items()):
        print('  %-24s %-5s %d' % (pid, k, v))
    print('== 배지 발생 ==', dict(badge_seen))
    print('== 오라클 불일치 %d 종 ==' % len(mismatch))
    for k, v in sorted(mismatch.items(), key=lambda x: -x[1]):
        print('  %s x%d' % (k, v))
        print('    ex:', json.dumps(examples[k], ensure_ascii=False)[:600])
    print('== 불변식 위반 %d 종 ==' % len(inv))
    for k, v in sorted(inv.items(), key=lambda x: -x[1]):
        print('  %s x%d' % (k, v))
        print('    ex:', json.dumps(inv_ex[k], ensure_ascii=False)[:700])
    print('RESULT:', 'PASS' if not mismatch and not inv else 'FAIL')


if __name__ == '__main__':
    main(sys.argv[1])
