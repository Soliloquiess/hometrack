/* hometrack QA - site/index.html 의 판정 JS 를 전수 그리드로 돌려 결과를 덤프한다.
   작성자의 tools/smoke_site.js 는 쓰지 않는다. 검수자가 별도로 만든 드라이버.
   출력: 1행 = { cond, policies:[{id,k,badges,why}], notices:[{id,k,why}] } */
const fs = require('fs');
const path = require('path');
const H = require(path.join(__dirname, 'oracle_site_harness.js'));

const NOW_ISO = process.env.QA_NOW || '2026-09-03T15:20:21+09:00';
const OUT = process.argv[2] || path.join(__dirname, '_grid_out.json');

/* ---- 조건 그리드 (극단값 포함) ---------------------------------------- */
const INCOMES = [null, 0, 3000, 5000, 7000, 7500, 8500, 13000, 99999, 999999];
const HOUSEHOLDS = [null, 1, 2, 3, 4, 5, 6, 7, 8, 9];
const DUALS = [null, true, false];
const NOHOMES = ['', 'yes', 'no'];
const MARRYS = ['', '2015-09-03', '2023-09-03', '2026-09-03', '2026-11-03', '2027-09-03', 'not-a-date'];
const ASSETSETS = [
  { netAsset: null, totalAsset: null, carValue: null },
  { netAsset: 0, totalAsset: 0, carValue: 0 },
  { netAsset: 999999, totalAsset: 999999, carValue: 999999 }
];
const SAVINGSETS = [
  { savingsMonths: null, savingsCount: null },
  { savingsMonths: 24, savingsCount: 24 },
  { savingsMonths: 0, savingsCount: 0 }
];

function buildGrid(){
  const rows = [];
  INCOMES.forEach(income => HOUSEHOLDS.forEach(household => DUALS.forEach(dual =>
    NOHOMES.forEach(noHome => MARRYS.forEach(marry =>
      ASSETSETS.forEach((A, ai) => SAVINGSETS.forEach((S, si) => {
        rows.push(Object.assign({ income, household, dual, noHome, marry, _a: ai, _s: si }, A, S));
      }))
    ))
  )));
  return rows;
}

/* ---- 합성 공고 (실데이터는 금액·배제조건이 전부 null 이라 경로가 안 열린다) ---- */
const SYNTH = [
  { id: 'SYN:dep-null-max', deposit_min: null, deposit_max: 20000, rent_min: null, rent_max: null, linked_policy_id: 'p_happy_house' },
  { id: 'SYN:dep-min-nomax', deposit_min: 15000, deposit_max: null, rent_min: null, rent_max: null, linked_policy_id: 'p_happy_house' },
  { id: 'SYN:dep-all', deposit_min: 5000, deposit_max: 10000, rent_min: null, rent_max: null, linked_policy_id: 'p_happy_house' },
  { id: 'SYN:dep-part', deposit_min: 5000, deposit_max: 90000, rent_min: null, rent_max: null, linked_policy_id: 'p_happy_house' },
  { id: 'SYN:dep-over', deposit_min: 900000, deposit_max: 990000, rent_min: null, rent_max: null, linked_policy_id: 'p_happy_house' },
  { id: 'SYN:Q38-rent-part', deposit_min: 1000, deposit_max: 2000, rent_min: 28, rent_max: 35, linked_policy_id: 'p_happy_house' },
  { id: 'SYN:rent-all', deposit_min: 1000, deposit_max: 2000, rent_min: 10, rent_max: 20, linked_policy_id: 'p_happy_house' },
  { id: 'SYN:rent-over', deposit_min: 1000, deposit_max: 2000, rent_min: 200, rent_max: 300, linked_policy_id: 'p_happy_house' },
  { id: 'SYN:rent-only-max', deposit_min: null, deposit_max: null, rent_min: null, rent_max: 40, linked_policy_id: 'p_happy_house' },
  { id: 'SYN:excl-nohome', deposit_min: 1000, deposit_max: 2000, rent_min: null, rent_max: null, linked_policy_id: 'p_happy_house', exclusions: ['유주택자 제외'] },
  { id: 'SYN:excl-unmapped', deposit_min: 1000, deposit_max: 2000, rent_min: null, rent_max: null, linked_policy_id: 'p_happy_house', exclusions: ['해외 체류자 제외'] },
  { id: 'SYN:excl-householder', deposit_min: 1000, deposit_max: 2000, rent_min: null, rent_max: null, linked_policy_id: 'p_happy_house', exclusions: ['세대주가 아닌 자 제외'] },
  { id: 'SYN:dangling', deposit_min: 1000, deposit_max: 2000, linked_policy_id: 'p_does_not_exist' },
  { id: 'SYN:link-null-tg', deposit_min: 1000, deposit_max: 2000, linked_policy_id: null, target_groups: ['신혼부부'] },
  { id: 'SYN:link-null-notg', deposit_min: 1000, deposit_max: 2000, linked_policy_id: null, target_groups: [] },
  { id: 'SYN:link-lucky7', deposit_min: 1000, deposit_max: 2000, linked_policy_id: 'p_busan_lucky7' },
  { id: 'SYN:link-newborn', deposit_min: 1000, deposit_max: 2000, linked_policy_id: 'p_newborn_jeonse' },
  { id: 'SYN:link-integrated', deposit_min: 1000, deposit_max: 2000, linked_policy_id: 'p_integrated_public' },
  { id: 'SYN:link-national', deposit_min: 1000, deposit_max: 2000, linked_policy_id: 'p_national_rental' },
  { id: 'SYN:apply-end-null', deposit_min: 1000, deposit_max: 2000, apply_end: null, notice_status: '공고중', linked_policy_id: 'p_happy_house' },
  { id: 'SYN:apply-end-d3', deposit_min: 1000, deposit_max: 2000, apply_start: '2026-08-20', apply_end: '2026-09-06', notice_status: '접수중', linked_policy_id: 'p_happy_house' },
  { id: 'SYN:apply-end-d20', deposit_min: 1000, deposit_max: 2000, apply_start: '2026-08-20', apply_end: '2026-09-23', notice_status: '접수중', linked_policy_id: 'p_happy_house' },
  { id: 'SYN:apply-end-d60', deposit_min: 1000, deposit_max: 2000, apply_start: '2026-08-20', apply_end: '2026-11-02', notice_status: '접수중', linked_policy_id: 'p_happy_house' },
  { id: 'SYN:apply-end-past', deposit_min: 1000, deposit_max: 2000, apply_start: '2026-07-01', apply_end: '2026-08-01', notice_status: '접수마감', linked_policy_id: 'p_happy_house' },
  { id: 'SYN:disappeared', deposit_min: 1000, deposit_max: 2000, apply_end: '2026-12-31', disappeared: true, linked_policy_id: 'p_happy_house' },
  { id: 'SYN:status-closed-noend', deposit_min: 1000, deposit_max: 2000, apply_end: null, notice_status: '접수마감', linked_policy_id: 'p_happy_house' }
];

function fillNotice(o){
  const base = {
    id: o.id, id_basis: 'composite', source: 'LH', entry_kind: 'manual', detail_level: 'detailed',
    source_url: 'https://example.invalid/x', title: 'QA 합성 공고 ' + o.id, supply_type: '행복주택',
    sigungu_code: '26410', sigungu_name: '금정구', dong_name: null, station_ids: ['guseo'],
    deposit_min: null, deposit_max: null, rent_min: null, rent_max: null, area_min: null, area_max: null,
    target_groups: [], exclusions: [], linked_policy_id: null,
    apply_start: null, apply_end: null, notice_status: '공고중', announced_at: null,
    first_seen: '2026-09-03', disappeared: false, collected_at: '2026-09-03T15:20:21+09:00'
  };
  return Object.assign(base, o);
}

const ctx = H.load({ now: NOW_ISO });
if (ctx.__errors.length) {
  console.error('HARNESS INIT ERRORS', ctx.__errors);
  process.exit(2);
}
ctx.__run('__SYNTH = ' + JSON.stringify(SYNTH.map(fillNotice)) + ';');
ctx.__run('__ALLNOTICES = DATA.notices.concat(__SYNTH);');

const grid = buildGrid();
const out = fs.createWriteStream(OUT, { encoding: 'utf8' });
out.write(JSON.stringify({ meta: { now: NOW_ISO, rows: grid.length,
  policies: JSON.parse(ctx.__run('JSON.stringify(DATA.policies.map(function(p){return p.id;}))')),
  notices: JSON.parse(ctx.__run('JSON.stringify(__ALLNOTICES.map(function(n){return n.id;}))')),
  synth: SYNTH.map(fillNotice) } }) + '\n');

/* 예산 축은 조건 그리드와 직교이므로 따로 돈다 */
const BUDGETS = [
  { deposit: null, loan: null, rentCap: null },
  { deposit: 0, loan: 0, rentCap: null },
  { deposit: 10000, loan: 5000, rentCap: null },
  { deposit: 10000, loan: 5000, rentCap: 30 },
  { deposit: 15000, loan: 0, rentCap: 30 },
  { deposit: 1000, loan: 0, rentCap: 0 },
  { deposit: null, loan: 20000, rentCap: 999999 },
  { deposit: 999999, loan: 999999, rentCap: 999999 }
];

ctx.__run(`
__evalPolicies = function(){
  return DATA.policies.map(function(p){
    var v = judgePolicy(p);
    return { id:p.id, conf:p.confidence, k:v.k, badges:Object.keys(v.badges||{}).sort(), why:v.why };
  });
};
__evalNotices = function(){
  return __ALLNOTICES.map(function(n){
    var v = judgeNotice(n);
    var b = budgetOf(n);
    var dd = ddayOf(n), cl = closedOf(n);
    return { id:n.id, k:v.k, why:v.why, conf:v.conf||null, dangling:!!v.dangling,
             budget:b.k, budgetWhy:b.why||null, dday:dd.d, ddayCls:dd.cls, ddayTxt:dd.txt,
             closed:cl.closed, closedReason:cl.reason, stops:noticeStops(n) };
  });
};
__setCond = function(o){ for(var k in o) COND[k]=o[k]; };
`);

let n = 0;
for (const g of grid) {
  ctx.__run('COND = blankCond();');
  ctx.__run('__setCond(' + JSON.stringify(g) + ');');
  const pol = JSON.parse(ctx.__run('JSON.stringify(__evalPolicies())'));
  out.write(JSON.stringify({ t: 'p', cond: g, pol }) + '\n');
  n++;
}
/* 공고: 조건 그리드를 다 돌리면 폭발하므로 대표 조건 × 예산 전량 */
const NOTICE_CONDS = [
  { income: null, household: 2, dual: null, noHome: '', marry: '', netAsset: null, totalAsset: null, carValue: null, savingsMonths: null, savingsCount: null },
  { income: 5000, household: 2, dual: false, noHome: 'yes', marry: '2023-09-03', netAsset: 0, totalAsset: 0, carValue: 0, savingsMonths: 24, savingsCount: 24 },
  { income: 999999, household: 2, dual: true, noHome: 'no', marry: '2015-09-03', netAsset: 999999, totalAsset: 999999, carValue: 999999, savingsMonths: 0, savingsCount: 0 },
  { income: 7000, household: 5, dual: true, noHome: 'no', marry: '2027-09-03', netAsset: null, totalAsset: 999999, carValue: null, savingsMonths: null, savingsCount: null },
  { income: 0, household: 9, dual: false, noHome: 'yes', marry: '2026-11-03', netAsset: 0, totalAsset: 0, carValue: 0, savingsMonths: 24, savingsCount: 24 }
];
for (const c of NOTICE_CONDS) {
  for (const b of BUDGETS) {
    ctx.__run('COND = blankCond();');
    ctx.__run('__setCond(' + JSON.stringify(Object.assign({}, c, b)) + ');');
    const notices = JSON.parse(ctx.__run('JSON.stringify(__evalNotices())'));
    out.write(JSON.stringify({ t: 'n', cond: Object.assign({}, c, b), notices }) + '\n');
  }
}
/* 예산 내 비율 - 전 집계 × 가용액 */
const AVAILS = [null, 0, 5000, 12000, 15000, 19500, 21000, 50000, 999999];
ctx.__run('__evalRatio = function(av){ return DATA.trades.aggregates.map(function(a){' +
          ' return { station_id:a.station_id, housing_type:a.housing_type, deal_type:a.deal_type,' +
          ' count:a.count, r:ratioWithin(a, av) }; }); };');
for (const av of AVAILS) {
  const r = JSON.parse(ctx.__run('JSON.stringify(__evalRatio(' + JSON.stringify(av) + '))'));
  out.write(JSON.stringify({ t: 'r', avail: av, aggs: r }) + '\n');
}
out.end();
console.error('grid rows written: policies=' + n + ' noticeSets=' + (NOTICE_CONDS.length * BUDGETS.length) + ' ratioSets=' + AVAILS.length);
