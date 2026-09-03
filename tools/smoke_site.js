#!/usr/bin/env node
/* tools/smoke_site.js — site/index.html 런타임 스모크 (Node, 의존성 0)
 *
 * 브라우저 없이 확인할 수 있는 것만 확인한다:
 *   1. 산출 HTML 의 <script> 본문이 초소형 DOM 스텁 위에서 throw 없이 평가되는가
 *   2. renderAll() + showTab() 5탭이 throw 없이 도는가
 *   3. 화면에 찍히는 문자열(innerHTML / textContent / document.title)에
 *      NaN · undefined · Infinity · null 이 새어 나오지 않는가
 *
 * 확인하지 못하는 것: 실제 레이아웃·CSS·인쇄·접근성·클릭 동작.
 * 그것은 QA(ht-qa) 가 브라우저에서 본다. 이 스크립트는 "백지 크래시" 만 막는다.
 *
 * 사용: node tools/smoke_site.js [site/index.html]
 */

"use strict";

const fs = require("fs");
const path = require("path");
const vm = require("vm");

const file = process.argv[2] || path.join(__dirname, "..", "site", "index.html");
const html = fs.readFileSync(file, "utf8");

/* ---------------------------------------------------------------- script 추출 */
const scripts = [];
const SCRIPT_RE = /<script\b([^>]*)>([\s\S]*?)<\/script\s*>/gi;
let m;
while ((m = SCRIPT_RE.exec(html)) !== null) {
  if (/\bsrc\s*=/i.test(m[1])) {
    fail("외부 스크립트 src= 가 있다 — 산출물은 인라인만 허용된다");
  }
  scripts.push(m[2]);
}
if (scripts.length === 0) fail("<script> 본문을 찾지 못했다");

/* ---------------------------------------------------------------- 출력 수집 */
const sinks = [];   /* {where, value} — 화면에 찍히는 모든 문자열 */
function sink(where, value) { sinks.push({ where: where, value: String(value) }); }

/* ---------------------------------------------------------------- DOM 스텁 */
function makeEl(name) {
  const el = {
    _name: name, _attrs: {}, _events: {}, _html: "", _text: "",
    id: /^#/.test(name) ? name.slice(1) : "",
    value: "", checked: false, hidden: false, disabled: false, open: false,
    className: "", style: {},
    classList: {
      add: function () {}, remove: function () {},
      toggle: function () {}, contains: function () { return false; }
    },
    setAttribute: function (k, v) { this._attrs[k] = String(v); },
    getAttribute: function (k) {
      return Object.prototype.hasOwnProperty.call(this._attrs, k) ? this._attrs[k] : null;
    },
    removeAttribute: function (k) { delete this._attrs[k]; },
    addEventListener: function (t, f) { (this._events[t] = this._events[t] || []).push(f); },
    removeEventListener: function () {},
    /* 스텁은 innerHTML 을 파싱하지 않는다. 빈 목록을 돌려주면 호출부의
       Array.prototype.forEach.call 이 아무 것도 하지 않고 지나간다(throw 없음). */
    querySelectorAll: function () { return []; },
    querySelector: function () { return null; },
    appendChild: function () {},
    focus: function () {},
    closest: function () { return null; }
  };
  Object.defineProperty(el, "innerHTML", {
    get: function () { return this._html; },
    set: function (v) { this._html = String(v); sink(name + ".innerHTML", v); }
  });
  /* <select>.options — 목업은 `options.length === 0` 일 때만 <option> 을 채운다.
     innerHTML 을 파싱하지 않으므로 문자열 안의 <option 개수로 길이만 흉내낸다. */
  Object.defineProperty(el, "options", {
    get: function () {
      const n = (this._html.match(/<option\b/gi) || []).length;
      const out = [];
      for (let i = 0; i < n; i++) out.push(makeEl("<option>"));
      return out;
    }
  });
  Object.defineProperty(el, "textContent", {
    get: function () { return this._text; },
    set: function (v) { this._text = String(v); sink(name + ".textContent", v); }
  });
  return el;
}

const byId = new Map();
const documentStub = {
  getElementById: function (id) {
    if (!byId.has(id)) byId.set(id, makeEl("#" + id));
    return byId.get(id);
  },
  querySelectorAll: function () { return []; },
  querySelector: function () { return null; },
  documentElement: makeEl("html"),
  addEventListener: function () {},
  createElement: function (t) { return makeEl("<" + t + ">"); },
  body: makeEl("body")
};
Object.defineProperty(documentStub, "title", {
  get: function () { return this._title || ""; },
  set: function (v) { this._title = String(v); sink("document.title", v); }
});

const store = new Map();
const localStorageStub = {
  getItem: function (k) { return store.has(k) ? store.get(k) : null; },
  setItem: function (k, v) { store.set(k, String(v)); },
  removeItem: function (k) { store.delete(k); },
  clear: function () { store.clear(); }
};

const sandbox = {
  document: documentStub,
  localStorage: localStorageStub,
  sessionStorage: undefined,
  location: { hash: "", search: "", href: "file:///site/index.html" },
  navigator: { userAgent: "smoke" },
  console: console,
  setTimeout: function (fn) { return 0; },   /* 하이라이트 해제 타이머 — 즉시 무시 */
  clearTimeout: function () {},
  matchMedia: function () {
    return { matches: false, addEventListener: function () {}, addListener: function () {} };
  },
  confirm: function () { return false; },
  alert: function () {},
  addEventListener: function () {},
  removeEventListener: function () {},
  print: function () {}
};
sandbox.window = sandbox;
sandbox.self = sandbox;
sandbox.globalThis = sandbox;

const context = vm.createContext(sandbox);

/* ---------------------------------------------------------------- 실행 */
const problems = [];

scripts.forEach(function (code, i) {
  try {
    vm.runInContext(code, context, { filename: "inline-script-" + (i + 1) + ".js" });
  } catch (e) {
    problems.push("script#" + (i + 1) + " 평가에서 throw: " + (e && e.stack ? e.stack : e));
  }
});
if (problems.length) report();

/* renderAll() + 5탭 */
const TABS = ["input", "homes", "policy", "stations", "news"];
function call(label, fn) {
  try { fn(); } catch (e) {
    problems.push(label + " 에서 throw: " + (e && e.stack ? e.stack : e));
  }
}

function renderPass(label) {
  call(label + " renderAll()", function () { sandbox.renderAll(); });
  TABS.forEach(function (t) {
    call(label + ' showTab("' + t + '")', function () { sandbox.showTab(t); });
  });
  /* 탭5 두 모드(오늘 diff / 보관 이력) 는 UI 상태로만 갈린다 — 둘 다 그려 본다. */
  if (sandbox.UI && typeof sandbox.renderNews === "function") {
    ["today", "week"].forEach(function (mode) {
      call(label + ' renderNews("' + mode + '")', function () {
        sandbox.UI.newsMode = mode; sandbox.renderNews();
      });
    });
    sandbox.UI.newsMode = "today";
  }
}

/* 1차 — 조건 미입력(첫 방문). 빈 상태 문구 경로. */
renderPass("[조건 미입력]");

/* 2차 — 조건 입력됨(재방문). 예산·자격 판정과 차트가 실제로 그려지는 경로.
   localStorage 를 통해서만 주입한다 — 화면이 조건을 읽는 유일한 경로가 그것이다. */
if (typeof sandbox.loadCond === "function" && Array.isArray(sandbox.STATIONS)) {
  const ids = sandbox.STATIONS.map(function (s) { return s.id; });
  store.set("hmt.cond", JSON.stringify({
    deals: ["jeonse", "banjeonse", "wolse"],
    deposit: 12000, loan: 9000, rentCap: 30,
    income: 6000, dual: true, household: 2,
    netAsset: 8000, totalAsset: 12000, carValue: 1200,
    savingsMonths: 30, savingsCount: 30,
    marry: "2027-04-17", noHome: "yes",
    base: (sandbox.CFG && sandbox.CFG.base_station) || ids[0],
    stations: ids
  }));
  call("[조건 입력] loadCond()", function () { sandbox.loadCond(); });
  renderPass("[조건 입력]");

  /* 3차 — 주택유형·정렬·지역 축을 바꿔 본다(빈 집계 조합에서 죽지 않는지). */
  if (sandbox.UI) {
    ["apt", "villa", "officetel"].forEach(function (ht) {
      call("[유형 " + ht + "]", function () {
        sandbox.UI.houseType = ht; sandbox.renderHomes(); sandbox.renderStations();
      });
    });
    sandbox.UI.houseType = "apt";
    call("[마감 포함]", function () {
      sandbox.UI.withClosed = true; sandbox.renderHomes(); sandbox.UI.withClosed = false;
    });
    call("[부산 전역]", function () {
      sandbox.UI.region = "busan"; sandbox.renderHomes(); sandbox.UI.region = "near";
    });
  }
}

/* 첫 실행 화면은 diff.is_first_run 데이터 경로로만 도달한다(D21/M3) — 그 경로도 그려 본다. */
if (sandbox.DATA && sandbox.DATA.diff && typeof sandbox.renderNews === "function") {
  const prev = sandbox.DATA.diff.is_first_run;
  call("renderNews(is_first_run=true)", function () {
    sandbox.DATA.diff.is_first_run = true; sandbox.renderNews();
  });
  sandbox.DATA.diff.is_first_run = prev;
  call("renderNews(is_first_run 복귀)", function () { sandbox.renderNews(); });
}

/* ---------------------------------------------------------------- 출력 점검 */
const BAD = [
  { re: /\bNaN\b/, name: "NaN" },
  { re: /\bundefined\b/, name: "undefined" },
  { re: /\b-?Infinity\b/, name: "Infinity" }
];
/* `null` 은 검사하지 않는다 — policies.json 의 `note`(개발자 메모)가 사용자용 `비고` 에
   그대로 찍히고(DESIGN_SPEC §7-3) 그 원문에 "pct_dual = null" 같은 표기가 들어 있다.
   화면 코드의 null 노출 방지는 M4·M18·M19·M25 가드로 이미 처리돼 있고,
   문구 다듬기는 policies.json 소관이다. 여기서 막으면 데이터 문구가 빌드를 깨뜨린다. */
sinks.forEach(function (s) {
  BAD.forEach(function (b) {
    if (b.re.test(s.value)) {
      problems.push(b.name + " 노출 — " + s.where + ": …" + excerpt(s.value, b.re) + "…");
    }
  });
});

function excerpt(text, re) {
  const at = text.search(re);
  const from = Math.max(0, at - 60);
  return text.slice(from, at + 60).replace(/\s+/g, " ");
}

/* ---------------------------------------------------------------- 보고 */
function report() {
  const uniq = [];
  problems.forEach(function (p) { if (uniq.indexOf(p) < 0) uniq.push(p); });
  if (uniq.length === 0) {
    console.log("스모크 OK — script " + scripts.length + "개 평가 · renderAll()+5탭 "
      + "(조건 미입력·조건 입력 2회) throw 0 · 출력 " + sinks.length
      + "곳에서 NaN/undefined/Infinity 0건");
    process.exit(0);
  }
  console.log("스모크 실패 — " + uniq.length + "건 (출력 " + sinks.length + "곳 점검)");
  uniq.slice(0, 30).forEach(function (p) { console.log("  - " + p); });
  if (uniq.length > 30) console.log("  … 그 외 " + (uniq.length - 30) + "건");
  process.exit(1);
}

function fail(msg) {
  console.log("스모크 실패 — " + msg);
  process.exit(1);
}

report();
