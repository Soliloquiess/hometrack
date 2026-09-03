/* hometrack QA — site/index.html 의 JS 를 DOM 스텁 위에서 실행하는 독립 하네스.
   작성자의 tools/smoke_site.js 를 쓰지 않는다. 검수자가 별도로 만든 것.
   사용: const H = require('./oracle_site_harness.js'); const ctx = H.load({now:'2026-09-03T15:20:21+09:00'}); */
const fs = require('fs'), path = require('path'), vm = require('vm');

/* QA_ROOT 로 검수 대상 스냅샷(예: 커밋 8ac4a07 추출본)을 지정할 수 있다. */
const ROOT = process.env.QA_ROOT ? path.resolve(process.env.QA_ROOT) : path.resolve(__dirname, '..', '..');

function makeEl(id, tag){
  const el = {
    _id: id, tagName: (tag||'div').toUpperCase(),
    innerHTML: '', textContent: '', value: '', checked: false,
    hidden: false, title: '', style: {}, _attrs: {}, _listeners: {},
    children: [], options: [], selectedIndex: -1, disabled: false, files: [],
    classList: {
      _s: new Set(),
      add(c){ this._s.add(c); }, remove(c){ this._s.delete(c); },
      toggle(c, on){ if(on === undefined) { this._s.has(c) ? this._s.delete(c) : this._s.add(c); }
                     else if(on) this._s.add(c); else this._s.delete(c); return this._s.has(c); },
      contains(c){ return this._s.has(c); }
    },
    setAttribute(k, v){ this._attrs[k] = String(v); },
    getAttribute(k){ return Object.prototype.hasOwnProperty.call(this._attrs, k) ? this._attrs[k] : null; },
    removeAttribute(k){ delete this._attrs[k]; },
    addEventListener(t, f){ (this._listeners[t] = this._listeners[t] || []).push(f); },
    removeEventListener(){},
    querySelectorAll(){ return []; },
    querySelector(){ return null; },
    appendChild(c){ this.children.push(c); return c; },
    closest(){ return null; },
    matches(){ return false; },
    scrollIntoView(){},
    focus(){},
    dispatchEvent(){ return true; }
  };
  return el;
}

function load(opts){
  opts = opts || {};
  const html = fs.readFileSync(path.join(ROOT, 'site', 'index.html'), 'utf8');
  const lines = html.split('\n');
  // 마지막 <script> 블록(본문 JS) 만 뽑는다. head 인라인 테마 스크립트는 제외.
  const starts = [], ends = [];
  lines.forEach((l, i) => { if(/<script>/.test(l)) starts.push(i); if(/<\/script>/.test(l)) ends.push(i); });
  const s = starts[starts.length-1], e = ends[ends.length-1];
  const code = lines.slice(s+1, e).join('\n');

  const store = Object.create(null);
  const els = Object.create(null);
  const errors = [];
  const sandbox = {
    console,
    Math, JSON, Date, Number, String, Boolean, Array, Object, RegExp, isNaN, parseInt, parseFloat,
    Infinity, NaN, undefined,
    localStorage: {
      getItem(k){ if(opts.blockStorage) throw new Error('blocked'); return k in store ? store[k] : null; },
      setItem(k, v){ if(opts.blockStorage) throw new Error('blocked'); store[k] = String(v); },
      removeItem(k){ if(opts.blockStorage) throw new Error('blocked'); delete store[k]; }
    },
    location: { hash: opts.hash || '' },
    document: {
      documentElement: makeEl('html', 'html'),
      body: makeEl('body', 'body'),
      title: '',
      getElementById(id){ return els[id] || (els[id] = makeEl(id)); },
      querySelectorAll(){ return []; },
      querySelector(){ return null; },
      createElement(t){ return makeEl('_new', t); },
      addEventListener(){}
    }
  };
  sandbox.window = sandbox;
  sandbox.globalThis = sandbox;
  sandbox.self = sandbox;
  sandbox.window.addEventListener = function(){};
  sandbox.window.matchMedia = function(){ return { matches:false, addListener(){}, addEventListener(){} }; };
  if(opts.seedCond) store['hmt.cond'] = JSON.stringify(opts.seedCond);

  const ctx = vm.createContext(sandbox);
  try{
    vm.runInContext(code, ctx, { filename: 'site-index-inline.js' });
  }catch(err){
    errors.push({ phase:'init', message: String(err && err.stack || err) });
  }
  ctx.__els = els;
  ctx.__errors = errors;
  ctx.__store = store;
  if(opts.now) { try{ vm.runInContext('NOW = new Date(' + JSON.stringify(opts.now) + ');', ctx); }catch(e){} }
  ctx.__run = (src) => vm.runInContext(src, ctx);
  return ctx;
}
module.exports = { load, makeEl, ROOT };
