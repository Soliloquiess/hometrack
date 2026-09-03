/* hometrack QA - 상태별로 renderAll() 을 돌려 산출 HTML 을 긁고
   NaN/undefined/Infinity 누출 · 필수 문구 · 견고성(throw 0) 을 검사한다. */
const fs = require('fs');
const path = require('path');
const H = require(path.join(__dirname, 'oracle_site_harness.js'));
const NOW_ISO = process.env.QA_NOW || '2026-09-03T15:20:21+09:00';

const CONDS = {
  '빈 조건(첫 방문)': {},
  '기본 2인 미입력': { household: 2 },
  '정상 입력': { deposit: 15000, loan: 6000, rentCap: 30, income: 5000, dual: false, household: 2,
                 netAsset: 20000, totalAsset: 25000, carValue: 2000, savingsMonths: 24, savingsCount: 24,
                 marry: '2023-09-03', noHome: 'yes' },
  '맞벌이 2인': { deposit: 15000, loan: 6000, rentCap: 30, income: 6000, dual: true, household: 2, marry: '2023-09-03', noHome: 'yes' },
  '3인 가구': { deposit: 15000, loan: 6000, income: 5000, dual: false, household: 3, marry: '2023-09-03', noHome: 'yes' },
  '9인 가구': { deposit: 15000, loan: 6000, income: 5000, dual: true, household: 9, marry: '2023-09-03', noHome: 'yes' },
  '기혼 11년': { deposit: 15000, loan: 6000, income: 3000, dual: false, household: 2, marry: '2015-09-03', noHome: 'yes' },
  '미래 혼인': { deposit: 15000, loan: 6000, income: 3000, dual: false, household: 2, marry: '2027-09-03', noHome: 'yes' },
  '유주택 + 자산초과': { deposit: 15000, loan: 6000, income: 999999, dual: true, household: 2, marry: '2015-09-03',
                        noHome: 'no', netAsset: 999999, totalAsset: 999999, carValue: 999999, savingsMonths: 0, savingsCount: 0 },
  '극단 0': { deposit: 0, loan: 0, rentCap: 0, income: 0, dual: false, household: 1, marry: '2026-09-03',
              noHome: 'yes', netAsset: 0, totalAsset: 0, carValue: 0, savingsMonths: 0, savingsCount: 0 },
  '극단 999999': { deposit: 999999, loan: 999999, rentCap: 999999, income: 999999, dual: true, household: 8,
                   marry: '2026-09-03', noHome: 'no', netAsset: 999999, totalAsset: 999999, carValue: 999999 },
  '음수 문자열': { deposit: '-100', loan: '-1', rentCap: '-5', income: '-9', household: '-2', marry: '-', noHome: 'x' },
  '문자열 쓰레기': { deposit: 'abc', loan: 'abc', rentCap: 'abc', income: 'abc', household: 'abc', marry: 'abc' },
  '기준역 노포': { deposit: 15000, loan: 6000, income: 5000, household: 2, dual: false, marry: '2023-09-03', noHome: 'yes', base: 'nopo' },
  '기준역 시청': { deposit: 15000, loan: 6000, income: 5000, household: 2, dual: false, marry: '2023-09-03', noHome: 'yes', base: 'sicheong' }
};

/* 견고성 - 데이터를 망가뜨려도 throw 0 이어야 한다 */
const MUTATIONS = {
  '무변형': 'void 0',
  'confidence 오타': 'DATA.policies.forEach(function(p){ p.confidence = "Official"; });',
  'confidence null': 'DATA.policies.forEach(function(p){ p.confidence = null; });',
  'verified_at null': 'DATA.policies.forEach(function(p){ p.verified_at = null; });',
  'verified_at 쓰레기': 'DATA.policies.forEach(function(p){ p.verified_at = "어제"; });',
  'rent_median null (스키마 내)': 'DATA.trades.aggregates.forEach(function(a){ a.rent_median = null; });',
  'deposit_median null (스키마 밖)': 'DATA.trades.aggregates.forEach(function(a){ a.deposit_median = null; });',
  'jeonse_equiv null (스키마 밖)': 'DATA.trades.aggregates.forEach(function(a){ a.jeonse_equiv_median = null; });',
  'monthly 비움': 'DATA.trades.aggregates.forEach(function(a){ a.monthly = []; });',
  'count 0': 'DATA.trades.aggregates.forEach(function(a){ a.count = 0; });',
  'deposit_hist 제거': 'DATA.trades.aggregates.forEach(function(a){ a.deposit_hist = null; });',
  'apply_end null 전부': 'DATA.notices.forEach(function(n){ n.apply_end = null; n.apply_start = null; });',
  'deposit_* null 전부': 'DATA.notices.forEach(function(n){ n.deposit_min=null;n.deposit_max=null;n.rent_min=null;n.rent_max=null; });',
  'collectors 순서 뒤섞기': 'DATA.meta.collectors.reverse();',
  'collectors name 변경': 'DATA.meta.collectors.forEach(function(c){ c.name = "XX-" + c.key; });',
  'collectors kind 오타': 'DATA.meta.collectors.forEach(function(c){ c.kind = "AUTO"; });',
  'collector 실패': 'DATA.meta.collectors.forEach(function(c){ if(c.key==="lh"){ c.status="fail"; c.error="QA 강제 실패"; } });',
  'linked dangling': 'DATA.notices.forEach(function(n){ if(n.linked_policy_id) n.linked_policy_id = "p_nope"; });',
  'linked null': 'DATA.notices.forEach(function(n){ n.linked_policy_id = null; });',
  'stations 비움': 'DATA.notices.forEach(function(n){ n.station_ids = []; });',
  'is_first_run': 'DATA.diff.is_first_run = true;',
  'diff 비움': 'DATA.diff.new_notices=[];DATA.diff.closing_soon=[];DATA.diff.closed_notices=[];DATA.diff.changed_policies=[];DATA.diff.collector_failures=[];',
  'diff_history 비움': 'DATA.diff_history = [];',
  'trades 집계 비움': 'DATA.trades.aggregates = [];',
  'notices 비움': 'DATA.notices = [];',
  'policies 비움': 'DATA.policies = [];',
  'income_tables 비움': 'DATA.income_tables.urban_worker.by_household = {}; DATA.income_tables.median_income.by_household = {};',
  'generated_at null': 'DATA.meta.generated_at = null;',
  'pending_change 붙이기': 'DATA.policies.forEach(function(p){ p.pending_change = { summary:"QA", source_url:"javascript:alert(1)", effective:"unknown" }; });',
  'source_url javascript:': 'DATA.notices.forEach(function(n){ n.source_url = "javascript:alert(1)"; }); DATA.policies.forEach(function(p){ p.policy_url = p.source_url = "javascript:alert(1)"; });',
  'exclusion_rules 비움': 'EXCLUSION_RULES.length = 0;',
  'exclusions 추가': 'DATA.notices.forEach(function(n){ n.exclusions = ["유주택자 제외","해외 체류자 제외"]; });'
};

const BAD = ['NaN', 'undefined', 'Infinity', '[object Object]'];
const results = [];

function scanHtml(ctx){
  const parts = [];
  for (const [id, el] of Object.entries(ctx.__els)) {
    if (el.innerHTML) parts.push({ id, html: el.innerHTML });
    if (el.textContent) parts.push({ id, html: String(el.textContent) });
  }
  return parts;
}

for (const [mname, mut] of Object.entries(MUTATIONS)) {
  for (const [cname, cond] of Object.entries(CONDS)) {
    const ctx = H.load({ now: NOW_ISO });
    const rec = { mutation: mname, cond: cname, errors: [], leaks: [] };
    if (ctx.__errors.length) rec.errors.push('init: ' + ctx.__errors[0].message.split('\n')[0]);
    try {
      ctx.__run(mut);
      ctx.__run('COND = blankCond();');
      ctx.__run('(function(o){ for(var k in o) COND[k]=o[k]; })(' + JSON.stringify(cond) + ');');
      ctx.__run('renderFresh(); renderAll();');
      ['input', 'homes', 'policy', 'stations', 'news'].forEach(t => {
        try { ctx.__run('showTab(' + JSON.stringify(t) + '); renderPrintHead(' + JSON.stringify(t) + ');'); }
        catch (e) { rec.errors.push('showTab ' + t + ': ' + String(e && e.message)); }
      });
    } catch (e) {
      rec.errors.push('render: ' + String(e && e.message));
    }
    for (const part of scanHtml(ctx)) {
      for (const bad of BAD) {
        if (part.html.indexOf(bad) >= 0) {
          const i = part.html.indexOf(bad);
          rec.leaks.push({ el: part.id, bad, ctx: part.html.slice(Math.max(0, i - 90), i + 60) });
        }
      }
    }
    results.push(rec);
  }
}

const withErr = results.filter(r => r.errors.length);
const withLeak = results.filter(r => r.leaks.length);
console.log('총 시나리오:', results.length, '| throw:', withErr.length, '| 누출:', withLeak.length);
withErr.slice(0, 30).forEach(r => console.log('  THROW [' + r.mutation + ' / ' + r.cond + '] ' + r.errors.join(' ; ')));
const leakKeys = new Map();
withLeak.forEach(r => r.leaks.forEach(l => {
  const k = r.mutation + '|' + l.bad + '|' + l.el;
  if (!leakKeys.has(k)) leakKeys.set(k, { cond: r.cond, ...l });
}));
[...leakKeys.entries()].slice(0, 60).forEach(([k, v]) =>
  console.log('  LEAK ' + k + ' (' + v.cond + ')  …' + v.ctx.replace(/\s+/g, ' ') + '…'));
fs.writeFileSync(process.argv[2] || path.join(__dirname, '_render_out.json'), JSON.stringify(results, null, 1));
