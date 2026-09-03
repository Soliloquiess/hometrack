/* hometrack QA - SPEC §4 Q# 중 "문구·구조" 항목을 렌더 결과에서 직접 확인한다. */
const path = require('path');
const fs = require('fs');
const H = require(path.join(__dirname, 'oracle_site_harness.js'));
const NOW = '2026-09-03T15:20:21+09:00';

const BASE = { deposit: 15000, loan: 6000, rentCap: 30, income: 5000, dual: false, household: 2,
               marry: '2023-09-03', noHome: 'yes' };

function run(cond, mut, tab){
  const c = H.load({ now: NOW });
  if (mut) c.__run(mut);
  c.__run('COND = blankCond();');
  c.__run('(function(o){for(var k in o)COND[k]=o[k];})(' + JSON.stringify(cond || {}) + ');');
  c.__run('renderFresh(); renderAll();');
  if (tab) c.__run('showTab(' + JSON.stringify(tab) + ');');
  const html = {};
  for (const [id, el] of Object.entries(c.__els)) html[id] = (el.innerHTML || '') + ' ' + (el.textContent || '');
  html.__all = Object.values(html).join('\n');
  return { c, html };
}

const out = [];
function chk(q, label, ok, evid){
  out.push({ q, label, ok: !!ok, evid: String(evid == null ? '' : evid).replace(/\s+/g, ' ').slice(0, 240) });
}
function findIn(s, needle){
  const i = s.indexOf(needle);
  return i < 0 ? null : s.slice(Math.max(0, i - 70), i + 110);
}

/* ---------- Q18 신선도 바 : 출처별 6줄 + kind 그대로 ---------- */
{
  const { c, html } = run(BASE);
  const f = html.fresh;
  const keys = JSON.parse(c.__run('JSON.stringify(freshCollectors().map(function(x){return x.key;}))'));
  const kinds = JSON.parse(c.__run('JSON.stringify(DATA.meta.collectors.map(function(x){return [x.key,x.kind];}))'));
  const rows = (f.match(/class="row/g) || []).length;
  chk('Q18', '신선도 바 줄 수 = collectors 수', rows === kinds.length, 'rows=' + rows + ' collectors=' + kinds.length);
  chk('Q18', '줄 순서 = SPEC §2 표 순서 (myhome,lh,bmc,trades,policy,private)',
      keys.join(',') === 'myhome,lh,bmc,trades,policy,private', keys.join(','));
  const kindTxt = { auto: '자동', semi: '반자동', manual: '수동', none: '—' };
  let ok = true, ev = [];
  kinds.forEach(([k, kind]) => { const t = kindTxt[kind]; if (f.indexOf(t) < 0) { ok = false; } ev.push(k + '=' + kind + '/' + t); });
  chk('Q18', 'kind 값을 화면 문구로 그대로 표시(승격 없음)', ok, ev.join(' '));
  chk('Q18/Q44', '민간 줄 = 수집 안 함 — 검색 링크만 제공', f.indexOf('수집 안 함 — 검색 링크만 제공') >= 0,
      findIn(f, '수집 안 함'));
  chk('Q18/D1', 'LH 줄에 "금액·면적은 수동" 취지가 적혀 있다',
      /금액[^<]{0,20}면적[^<]{0,20}수동|수동[^<]{0,20}금액/.test(f), findIn(f, '면적'));
  chk('Q19', '시세 줄에 신고 지연 30일 주석', f.indexOf('신고 지연') >= 0 && f.indexOf('30일') >= 0, findIn(f, '신고 지연'));
}

/* ---------- Q43 라벨을 바꿔도 key 분기가 유지된다 ---------- */
{
  const { html } = run(BASE, 'DATA.meta.collectors.forEach(function(c){ c.name = "라벨변경-" + c.key; });');
  const f = html.fresh;
  chk('Q43', 'collectors[].name 을 바꿔도 민간 줄 문구 유지', f.indexOf('수집 안 함 — 검색 링크만 제공') >= 0, findIn(f, '수집 안 함'));
  chk('Q43', 'collectors[].name 을 바꿔도 LH 2줄(상세 등록) 유지', /상세 등록/.test(f), findIn(f, '상세 등록'));
}

/* ---------- Q22 수집 실패 ---------- */
{
  const { html } = run(BASE, 'DATA.meta.collectors.forEach(function(c){ if(c.key==="lh"){c.status="fail";c.error="QA 강제 실패";} });' +
    ' DATA.diff.collector_failures=[{key:"lh",name:"LH",error:"QA 강제 실패",last_success:"2026-09-02T07:00:00+09:00"}];');
  chk('Q22', '실패 줄이 fail 클래스(--hi)로 바뀐다', /class="row fail"|row fail/.test(html.fresh), findIn(html.fresh, 'row fail'));
  chk('Q22', '실패 사유가 신선도 바에 적힌다', html.fresh.indexOf('QA 강제 실패') >= 0, findIn(html.fresh, 'QA 강제 실패'));
  chk('Q22', '직전 성공 시각이 함께 표시된다', /직전 성공|마지막 성공/.test(html.fresh), findIn(html.fresh, '성공'));
  chk('Q22', '탭5 새 소식에 수집 실패 섹션', html['news-main'].indexOf('수집 실패') >= 0, findIn(html['news-main'], '수집 실패'));
  chk('Q22', '탭2 에 실패 배너 + 직전 수집분 안내', /banner err|수집이 실패/.test(html['homes-main']), findIn(html['homes-main'], '실패'));
}

/* ---------- Q23 / Q53 첫 실행 ---------- */
{
  const { html } = run(BASE, 'DATA.diff.is_first_run = true;');
  chk('Q23', 'is_first_run 시 첫 수집 안내', /첫 수집/.test(html['news-main']), findIn(html['news-main'], '첫 수집'));
  const src = fs.readFileSync(path.join(H.ROOT, 'site', 'index.html'), 'utf8');
  const firstRunRefs = (src.match(/is_first_run/g) || []).length;
  chk('Q53', '첫 실행 경로가 diff.is_first_run 데이터로만 (버튼·목업 플래그 0)',
      !/data-mock|mockFirstRun|forceFirstRun|btn-firstrun/.test(src), 'is_first_run 참조 ' + firstRunRefs + '회, 목업 플래그 0');
}

/* ---------- Q25 조건 미입력 빈 상태 ---------- */
{
  const { html } = run({});
  ['homes-main', 'policy-main', 'st-table', 'news-main'].forEach(id => {
    chk('Q25', id + ' 에 NaN/undefined 없음', !/NaN|undefined|Infinity/.test(html[id]), (html[id] || '').slice(0, 0));
  });
  chk('Q25', '탭2 조건 미입력 안내', /조건 입력|예산을 먼저/.test(html['homes-main']), findIn(html['homes-main'], '조건'));
  chk('Q25', '탭3 조건 미입력 배너', /조건을 입력하면/.test(html['policy-main']), findIn(html['policy-main'], '조건을 입력'));
  chk('Q25', '탭4 비율열이 — 로 표시(0% 아님)', !/>0%</.test(html['st-table']), findIn(html['st-table'], '—'));
  chk('Q25', '탭 배지에 0 노출 없음', String(html['nb-homes'] || '').trim() === '',
      JSON.stringify(html['nb-homes']));
}

/* ---------- Q27 / Q28 / Q34 적용비율 ---------- */
function pctOf(cond){
  const { c } = run(cond);
  return JSON.parse(c.__run('JSON.stringify((function(){var p=policyById("p_happy_house");' +
    'var L=incomeLimitOf(p.criteria.income); return {pct:L.ap.pct,base:L.ap.base,adj:L.ap.adjust,limit:L.limit,approx:!!L.approx};})())'));
}
{
  const a = pctOf(Object.assign({}, BASE, { household: 2, dual: false }));
  const b = pctOf(Object.assign({}, BASE, { household: 2, dual: true }));
  const cc = pctOf(Object.assign({}, BASE, { household: 3, dual: false }));
  const d = pctOf(Object.assign({}, BASE, { household: 3, dual: true }));
  const tbl = JSON.parse(fs.readFileSync(path.join(H.ROOT, 'data', 'income_tables.json'), 'utf8'));
  chk('Q27', '2인 행복주택 적용비율 110 · 기준액 = by_household["2"]["110"]',
      a.pct === 110 && !a.approx && a.limit === tbl.urban_worker.by_household['2']['110'],
      JSON.stringify(a) + ' 표값=' + tbl.urban_worker.by_household['2']['110']);
  chk('Q27', '2인 맞벌이 130 · 기준액 = by_household["2"]["130"]',
      b.pct === 130 && !b.approx && b.limit === tbl.urban_worker.by_household['2']['130'],
      JSON.stringify(b) + ' 표값=' + tbl.urban_worker.by_household['2']['130']);
  chk('Q28', '3인 가산 0 → 100 / 맞벌이 120',
      cc.pct === 100 && d.pct === 120 && !cc.approx && !d.approx,
      JSON.stringify(cc) + ' / ' + JSON.stringify(d));
  const { html } = run(Object.assign({}, BASE, { household: 2, dual: true }), null, 'policy');
  chk('Q34', '정책 카드에 가산 반영 적용비율 표기(130%(120%+10%p 가산))',
      /130%\(120%\+10%p 가산\)/.test(html['policy-main']), findIn(html['policy-main'], '%p 가산'));
  chk('Q34', '정책 카드에 year_label 노출', html['policy-main'].indexOf(tbl.urban_worker.year_label) >= 0,
      findIn(html['policy-main'], tbl.urban_worker.year_label));
}

/* ---------- Q35 소득 라벨 ---------- */
{
  const src = fs.readFileSync(path.join(H.ROOT, 'site', 'index.html'), 'utf8');
  chk('Q35', '탭1 소득 라벨 = 부부 합산 전년도 세전 연소득 (+만원)',
      /부부 합산 전년도 세전 연소득/.test(src), findIn(src, '부부 합산 전년도 세전 연소득'));
}

/* ---------- Q37 버킷 캡션 ---------- */
{
  const { html } = run(BASE, null, 'homes');
  const all = html.__all;
  const n = (all.match(/500만원 버킷 기준/g) || []).length;
  chk('Q37', '예산 내 비율 표시 지점에 "500만원 버킷 기준" 캡션', n >= 2, '출현 ' + n + '회');
  chk('Q19', '탭2 시세 블록에 "과거 계약" + "매물이 아닙니다" + 신고 지연',
      /과거 계약/.test(all) && /매물이 아닙니다|매물 아님/.test(all) && /신고 지연/.test(all),
      findIn(all, '과거 계약'));
  const srcAll = fs.readFileSync(path.join(H.ROOT, 'site', 'index.html'), 'utf8');
  const tab4 = srcAll.slice(srcAll.indexOf('id="tab-stations"'), srcAll.indexOf('id="tab-news"'));
  chk('Q19', '탭4(정적 마크업)에도 "과거 계약 · 매물 아님 · 신고 지연" 캡션',
      /과거 계약/.test(tab4) && /매물이 아닙니다/.test(tab4) && /신고 지연/.test(tab4), findIn(tab4, '과거 계약'));
  const capCount = (srcAll.match(/신고 지연/g) || []).length;
  chk('Q19', '시세 표시 지점 캡션 4곳(신선도바·탭2·탭4·수집기 note)', capCount >= 4, '신고 지연 ' + capCount + '회');
}

/* ---------- Q38~Q41 예산 2축 (합성 공고) ---------- */
{
  const c = H.load({ now: NOW });
  c.__run('__N = { deposit_min:1000, deposit_max:2000, rent_min:28, rent_max:35 };');
  const set = (o) => { c.__run('COND = blankCond(); (function(x){for(var k in x)COND[k]=x[k];})(' + JSON.stringify(o) + ');'); };
  set({ deals: ['jeonse'], deposit: 15000, loan: 6000, rentCap: 30 });
  let b = JSON.parse(c.__run('JSON.stringify(budgetOf(__N))'));
  chk('Q38', '전세만 선택 + 월세상한 30 · 공고 28~35 → 일부 평형 가능', b.k === 'part' && b.txt === '일부 평형 가능',
      JSON.stringify(b));
  set({ deals: ['jeonse'], deposit: 15000, loan: 6000, rentCap: null });
  b = JSON.parse(c.__run('JSON.stringify(budgetOf(__N))'));
  chk('Q39', '월세 상한 미입력 → 보증금만 판정 + 사유에 "월임대료 상한 미입력"',
      b.k === 'all' && /월임대료 상한 미입력/.test(b.why), JSON.stringify(b));
  c.__run('__N2 = { deposit_min:null, deposit_max:20000, rent_min:null, rent_max:null };');
  set({ deposit: 15000, loan: 6000, rentCap: 30 });
  b = JSON.parse(c.__run('JSON.stringify(budgetOf(__N2))'));
  chk('Q40', 'deposit_min null · max 있음 → 금액 미표기(unknown)', b.k === 'unknown', JSON.stringify(b));
  c.__run('__N3 = { deposit_min:15000, deposit_max:null, rent_min:null, rent_max:null };');
  b = JSON.parse(c.__run('JSON.stringify(budgetOf(__N3))'));
  chk('Q41', 'deposit_min 있음 · max null → 하한 판정 + 사유에 "상한 미표기"',
      b.k === 'part' && /상한 미표기/.test(b.why), JSON.stringify(b));
  c.__run('__N4 = { deposit_min:900000, deposit_max:990000, rent_min:null, rent_max:null };');
  b = JSON.parse(c.__run('JSON.stringify(budgetOf(__N4))'));
  chk('Q10', '예산 밖 공고 → over', b.k === 'over', JSON.stringify(b));
}

/* ---------- Q10 / Q11 목록 구성 ---------- */
{
  const c = H.load({ now: NOW });
  c.__run('DATA.notices = DATA.notices.concat([' +
    '{id:"S1",source:"LH",entry_kind:"manual",detail_level:"detailed",source_url:"https://e.invalid/1",title:"예산 밖 공고",supply_type:"행복주택",sigungu_code:"26410",sigungu_name:"금정구",dong_name:null,station_ids:["guseo"],deposit_min:900000,deposit_max:990000,rent_min:null,rent_max:null,area_min:null,area_max:null,target_groups:[],exclusions:[],linked_policy_id:"p_happy_house",apply_start:null,apply_end:"2026-10-01",notice_status:"접수중",announced_at:null,first_seen:"2026-09-03",disappeared:false,collected_at:"2026-09-03T15:20:21+09:00"},' +
    '{id:"S2",source:"LH",entry_kind:"manual",detail_level:"detailed",source_url:"https://e.invalid/2",title:"예산 내 공고",supply_type:"행복주택",sigungu_code:"26410",sigungu_name:"금정구",dong_name:null,station_ids:["guseo"],deposit_min:1000,deposit_max:2000,rent_min:null,rent_max:null,area_min:null,area_max:null,target_groups:[],exclusions:[],linked_policy_id:"p_happy_house",apply_start:null,apply_end:"2026-10-01",notice_status:"접수중",announced_at:null,first_seen:"2026-09-03",disappeared:false,collected_at:"2026-09-03T15:20:21+09:00"}]);');
  c.__run('COND = blankCond(); (function(x){for(var k in x)COND[k]=x[k];})(' + JSON.stringify(Object.assign({}, BASE, { })) + ');');
  c.__run('UI.region = "all";');
  const res = JSON.parse(c.__run('JSON.stringify((function(){var r=computeHomes();' +
    'return {fit:r.fit.map(function(x){return x.n.id;}),unknown:r.unknown.map(function(x){return x.n.id;}),over:r.over.map(function(x){return x.n.id;})};})())'));
  chk('Q10', '예산 밖 공고가 over 묶음에만 들어간다', res.over.indexOf('S1') >= 0 && res.fit.indexOf('S1') < 0 && res.unknown.indexOf('S1') < 0, JSON.stringify(res));
  chk('Q11', '금액 null 공고가 over(예산 밖)로 가지 않는다', res.over.length === 1 && res.over[0] === 'S1', JSON.stringify(res));
  const near = JSON.parse(c.__run('JSON.stringify((function(){UI.region="near";var r=computeHomes();return[r.fit.length,r.unknown.length,r.over.length,r.outRegion];})())'));
  const busan = JSON.parse(c.__run('JSON.stringify((function(){UI.region="busan";var r=computeHomes();return[r.fit.length,r.unknown.length,r.over.length,r.outRegion];})())'));
  chk('Q11/§2-2-3', '지역 필터 "부산 전역" 이 실제로 목록을 넓힌다',
      JSON.stringify(near) !== JSON.stringify(busan),
      'near=' + JSON.stringify(near) + ' busan=' + JSON.stringify(busan) + ' (inRegion 이 UI.region 을 읽지 않음)');
  c.__run('renderHomes();');
  const homes = c.__els['homes-main'].innerHTML;
  chk('Q10', '예산 밖은 접힌 한 줄(fold)로만 노출', /예산 밖 \d+건/.test(homes) && /foldbody/.test(homes), findIn(homes, '예산 밖'));
  chk('Q11', '금액 미표기 섹션이 접히지 않고 별도 노출', /금액 미표기/.test(homes), findIn(homes, '금액 미표기'));
}

/* ---------- Q46 / Q47 / Q48 마감 ---------- */
{
  const c = H.load({ now: NOW });
  const mk = (o) => JSON.stringify(Object.assign({ apply_start: null, apply_end: null, notice_status: '공고중', disappeared: false }, o));
  const dd = (o) => JSON.parse(c.__run('JSON.stringify(ddayOf(' + mk(o) + '))'));
  const cl = (o) => JSON.parse(c.__run('JSON.stringify(closedOf(' + mk(o) + '))'));
  chk('Q46', 'apply_end null → D-day 계산 안 함 · dday-off', dd({}).d === null && dd({}).cls === 'dday-off', JSON.stringify(dd({})));
  chk('Q46', 'apply_end null → closed 아님', cl({}).closed === false, JSON.stringify(cl({})));
  chk('Q47', 'apply_end 경과 → 접수 종료 문구', cl({ apply_end: '2026-08-01' }).reason === 'apply_end', JSON.stringify(cl({ apply_end: '2026-08-01' })));
  chk('Q47', 'disappeared → "출처 목록에서 사라짐(마감 추정)" 문구 구분',
      cl({ disappeared: true, apply_end: '2026-12-31' }).txt === '출처 목록에서 사라짐(마감 추정)',
      JSON.stringify(cl({ disappeared: true, apply_end: '2026-12-31' })));
  chk('Q47', 'notice_status 접수마감(기간 미표기) 문구 구분',
      cl({ notice_status: '접수마감' }).reason === 'notice_status', JSON.stringify(cl({ notice_status: '접수마감' })));
  const d7 = dd({ apply_end: '2026-09-06', apply_start: '2026-08-01' });
  const d20 = dd({ apply_end: '2026-09-23', apply_start: '2026-08-01' });
  const d60 = dd({ apply_end: '2026-11-02', apply_start: '2026-08-01' });
  chk('Q46/D-day', 'D-3 → dday-hi · D-20 → dday-mid · D-60 → 무색',
      d7.cls === 'dday-hi' && d20.cls === 'dday-mid' && d60.cls === '',
      JSON.stringify([d7, d20, d60]));
  const { html } = run(BASE, null, 'homes');
  chk('Q48', '탭2 마감 임박 캡션이 "현재 D-30 전체" 를 밝힌다',
      /현재 D-30|지금 D-30|오늘 기준/.test(html['homes-main']), findIn(html['homes-main'], 'D-30'));
  chk('Q48', '탭5 마감 임박 캡션이 "새로 들어온 것" 을 밝힌다',
      /새로/.test(html['news-main']), findIn(html['news-main'], '새로'));
  chk('Q45', '탭2 신규 블록이 first_seen 최근 7일 기준임을 밝힌다',
      /7일/.test(html['homes-main']), findIn(html['homes-main'], '7일'));
}

/* ---------- Q49 기준역 즉시 재계산 ---------- */
{
  const c = H.load({ now: NOW });
  const stops = (base) => {
    c.__run('COND = blankCond(); COND.base = ' + JSON.stringify(base) + ';');
    return JSON.parse(c.__run('JSON.stringify(STATIONS.map(function(s){return stopsFromBase(s.id);}))'));
  };
  const g = stops('guseo'), n = stops('nopo');
  chk('Q49', '기준역 변경 시 정거장 수가 다시 계산된다', JSON.stringify(g) !== JSON.stringify(n),
      'guseo=' + g.join(',') + ' / nopo=' + n.join(','));
  chk('Q49', 'guseo 기준 = |index-8|', JSON.stringify(g) === JSON.stringify([8, 7, 6, 5, 4, 3, 2, 1, 0, 1, 2, 3, 4]), g.join(','));
  const files = fs.readdirSync(path.join(H.ROOT, 'data')).filter(f => f.endsWith('.json'));
  const hits = files.filter(f => fs.readFileSync(path.join(H.ROOT, 'data', f), 'utf8').indexOf('stops_from_base') >= 0);
  chk('Q49', 'data/*.json 에 stops_from_base 0건', hits.length === 0, hits.join(',') || '0건 (' + files.length + '파일 검사)');
}

/* ---------- Q50 배제 조건 ---------- */
{
  const src = fs.readFileSync(path.join(H.ROOT, 'site', 'index.html'), 'utf8');
  const js = src.split('\n').slice(938).join('\n');
  const kw = JSON.parse(fs.readFileSync(path.join(H.ROOT, 'config.json'), 'utf8')).exclusion_rules.map(r => r.keyword);
  const exclFn = js.slice(js.indexOf('var EXCL_INPUT'), js.indexOf('function judgeNotice'));
  const hard = kw.filter(k => exclFn.indexOf(k) >= 0);
  chk('Q50', '공고 배제 판정 코드(EXCL_INPUT~noticeExclusionHit)에 키워드 하드코딩 0건',
      hard.length === 0, hard.join(',') || '검사 키워드: ' + kw.join(','));
  const kwElsewhere = kw.filter(k => js.indexOf(k) >= 0);
  chk('Q50', '참고: JS 전체의 키워드 문자열 출현(정책 사유 문구 포함)',
      true, kwElsewhere.map(k => k + '(' + (js.split(k).length - 1) + ')').join(' ') || '0건');
  const c = H.load({ now: NOW });
  const mkN = (excl) => JSON.stringify({ id: 'X', exclusions: excl, linked_policy_id: 'p_happy_house', target_groups: [] });
  const j = (excl, noHome) => {
    c.__run('COND = blankCond(); COND.noHome = ' + JSON.stringify(noHome) + ';');
    return JSON.parse(c.__run('JSON.stringify(judgeNotice(' + mkN(excl) + '))'));
  };
  chk('Q50', '매핑된 exclusions + 유주택 입력 → 불가', j(['유주택자 제외'], 'no').k === 'no', JSON.stringify(j(['유주택자 제외'], 'no')));
  chk('Q50', '매핑된 exclusions + 무주택 입력 → 불가 아님', j(['유주택자 제외'], 'yes').k !== 'no', JSON.stringify(j(['유주택자 제외'], 'yes')));
  chk('Q50', '표에 없는 exclusions 는 판정에 쓰이지 않는다', j(['해외 체류자 제외'], 'no').k !== 'no', JSON.stringify(j(['해외 체류자 제외'], 'no')));
  chk('Q50', '입력 축이 없는 규칙(householder)은 불가를 내지 않는다', j(['세대주가 아닌 자 제외'], 'no').k !== 'no',
      JSON.stringify(j(['세대주가 아닌 자 제외'], 'no')));
}

/* ---------- Q51 dangling ---------- */
{
  const c = H.load({ now: NOW });
  c.__run('COND = blankCond();');
  const v = JSON.parse(c.__run('JSON.stringify(judgeNotice({id:"X",exclusions:[],target_groups:[],linked_policy_id:"p_typo"}))'));
  const v2 = JSON.parse(c.__run('JSON.stringify(judgeNotice({id:"Y",exclusions:[],target_groups:[],linked_policy_id:null}))'));
  chk('Q51', 'dangling → "연결 정책(p_typo)을 찾을 수 없음 — 설정 오류"',
      v.k === 'cond' && v.why === '연결 정책(p_typo)을 찾을 수 없음 — 설정 오류', JSON.stringify(v));
  chk('Q15/Q51', 'null 문구와 dangling 문구가 다르다', v.why !== v2.why, JSON.stringify(v2));
}

/* ---------- Q20 / Q21 표본·주택유형 ---------- */
{
  const c = H.load({ now: NOW });
  c.__run('COND = blankCond(); (function(x){for(var k in x)COND[k]=x[k];})(' + JSON.stringify(BASE) + ');');
  c.__run('UI.houseType = "apt"; renderStations();');
  const t = c.__els['st-table'].innerHTML;
  chk('Q20', '표본 5건 미만 역에 "표본 N건" 표기 + dim 클래스', /표본 \d+건/.test(t) && /class="dim"|dim/.test(t), findIn(t, '표본 '));
  const rows = JSON.parse(c.__run('JSON.stringify(STATIONS.map(function(s){var a=aggOf(s.id,"apt","jeonse");return a?[s.id,a.count,a.housing_type]:[s.id,0,null];}))'));
  chk('Q21', '아파트 선택 시 집계 housing_type 이 전부 apt', rows.every(r => r[2] === null || r[2] === 'apt'), JSON.stringify(rows).slice(0, 200));
  c.__run('UI.houseType = "officetel"; renderStations();');
  const t2 = c.__els['st-table'].innerHTML;
  chk('Q21', '유형을 바꾸면 표 값이 달라진다(섞이지 않는다)', t !== t2, 'apt len=' + t.length + ' officetel len=' + t2.length);
}

/* ---------- Q9 localStorage 차단 ---------- */
{
  const c = H.load({ now: NOW, blockStorage: true });
  chk('Q9', 'localStorage 차단 환경에서 init throw 0', c.__errors.length === 0, JSON.stringify(c.__errors).slice(0, 200));
  c.__run('COND = blankCond(); COND.deposit = 1000; saveCond(); renderAll();');
  chk('Q9', '차단 안내 문구가 뜬다', /저장이 차단|차단되어/.test(c.__els['store-banner'].innerHTML),
      c.__els['store-banner'].innerHTML.replace(/\s+/g, ' ').slice(0, 200));
}

/* ---------- Q8 딥링크 ---------- */
{
  const { html } = run(BASE, null, 'homes');
  const all = html.__all;
  const links = all.match(/<a[^>]*href="https?:[^"]*"[^>]*>/g) || [];
  const bad = links.filter(a => !/rel="noopener noreferrer"/.test(a) || !/referrerpolicy="no-referrer"/.test(a));
  chk('Q8', '외부 <a> 전부 noopener noreferrer + referrerpolicy', bad.length === 0,
      '외부링크 ' + links.length + '개 · 위반 ' + bad.length + (bad[0] ? ' 예: ' + bad[0] : ''));
  const urls = (all.match(/href="(https?:[^"]*)"/g) || []).map(s => s.slice(6, -1));
  const leaky = urls.filter(u => /(\d{4,})/.test(u.split('?')[1] || '') && !/panId|cntntsId|newsId|mi=|list_no|bid|aisTpCd|uppAisTpCd|PAN_ID|gv_|ccrCnntSysDsCd|page=/.test(u));
  chk('Q8', '딥링크 URL 에 금액·소득 숫자 파라미터 0건', leaky.length === 0, leaky.join(' | ') || urls.length + '개 검사');
  const dl = html['homes-main'];
  chk('Q8', '민간 딥링크에 역명·거래유형만', /new\.land\.naver\.com|zigbang|dabangapp/.test(dl) &&
      !/deposit|income|budget|price/.test(dl), findIn(dl, 'zigbang'));
}

/* ---------- Q7 개인 조건이 산출물·데이터에 없음 ---------- */
{
  const src = fs.readFileSync(path.join(H.ROOT, 'site', 'index.html'), 'utf8');
  const keys = ['hmt.cond'];
  const files = fs.readdirSync(path.join(H.ROOT, 'data')).filter(f => f.endsWith('.json'));
  /* 재검수 정정(2026-09-03) — 이전 판은 `"noHome"` 같은 **축 이름**을 찾았고,
     `meta.config.exclusion_rules[].input: "noHome"` 에 걸려 오탐이 났다.
     그 값은 D19 가 코드 하드코딩을 막기 위해 config 로 뺀 **규칙표의 축 식별자**이고
     사용자의 답(`"yes"`/`"no"`)이 아니다. Q7 이 막는 것은 **개인 조건의 값**이므로
     검사를 "키:값 쌍" 으로 좁힌다. */
  const condPatterns = [
    /"deposit"\s*:\s*-?\d/, /"loan"\s*:\s*-?\d/, /"rentCap"\s*:\s*-?\d/,
    /"income"\s*:\s*-?\d/, /"netAsset"\s*:\s*-?\d/, /"totalAsset"\s*:\s*-?\d/,
    /"carValue"\s*:\s*-?\d/, /"savingsMonths"\s*:\s*-?\d/, /"savingsCount"\s*:\s*-?\d/,
    /"marry"\s*:\s*"\d{4}-/, /"noHome"\s*:\s*"(yes|no)"/, /"dual"\s*:\s*(true|false)/,
    /"household"\s*:\s*\d/, /hmt\.cond/, /"savedAt"\s*:/
  ];
  const hits = [];
  files.forEach(f => {
    const t = fs.readFileSync(path.join(H.ROOT, 'data', f), 'utf8');
    condPatterns.forEach(re => { const m = t.match(re); if (m) hits.push(f + ':' + m[0]); });
  });
  chk('Q7', 'data/*.json 에 개인 조건 값 0건 (축 이름은 D19 규칙표라 제외)',
      hits.length === 0, hits.join(', ') || files.length + '파일 × ' + condPatterns.length + '패턴 검사');
  /* 축 이름이 어디에 왜 있는지는 별도로 기록해 둔다 - 다음 검수자가 다시 오탐하지 않게. */
  const axisHits = [];
  files.forEach(f => {
    const t = fs.readFileSync(path.join(H.ROOT, 'data', f), 'utf8');
    const m = t.match(/"input"\s*:\s*"[A-Za-z]+"/g);
    if (m) axisHits.push(f + ':' + [...new Set(m)].join('/'));
  });
  chk('Q7', '참고: 축 이름(exclusion_rules[].input)의 출현 위치', true,
      axisHits.join(' ') || '0건');
  const sinks = (src.match(/localStorage\.(setItem|getItem|removeItem)\([^)]*/g) || []);
  const badSink = sinks.filter(s => !/hmt\.(cond|theme)|STORE_KEY/.test(s));
  chk('Q7', '저장 sink 는 hmt.cond / hmt.theme 뿐', badSink.length === 0, sinks.join(' | '));
}

/* ---------- 결과 ---------- */
const fail = out.filter(o => !o.ok);
out.forEach(o => console.log((o.ok ? 'PASS ' : 'FAIL ') + o.q.padEnd(10) + ' ' + o.label + (o.evid ? '  <<' + o.evid + '>>' : '')));
console.log('\n합계 ' + out.length + '항목 · 통과 ' + (out.length - fail.length) + ' · 실패 ' + fail.length);
fs.writeFileSync(process.argv[2] || path.join(__dirname, '_assert_out.json'), JSON.stringify(out, null, 1));
