# 검수 보고 — `site/index.html` 화면·판정 계층 (SPEC v1.2 §4 Q1~Q56)

| 항목 | 값 |
|---|---|
| 검수 대상 | `site/index.html` — 커밋 `8ac4a07` (`8ac4a078948d46046b171276044f034a49660fb7`), sha256 앞 16자 `9f2785c356ceae8e` |
| 실행 시각 | **2026-09-03 15:25 ~ 16:02 (KST)** — D-day·"최근 7일"·경과일은 실행일 의존이므로 오라클에도 같은 기준(`NOW = 2026-09-03T15:20:21+09:00`)을 주입해 대조했다 |
| 실행 환경 | Windows 10 Pro 19045 · Python 3.12.5 · Node v24.14.0 · Chrome 152.0.7977.65 (`--headless=new`) |
| 검수 범위 | **화면·판정 계층.** 수집 계층(`collect.py`·`data/` 생성)은 `docs/qa/REPORT_collect_20260903.md` 담당 — 해당 항목은 "범위 밖(수집 검수)" |
| 쓰기 범위 | `docs/qa/` 만. 소스·명세·목업·데이터 무수정, 커밋 없음 |

> **검수 중 대상 파일이 변한 것에 대한 처리.** 병행 수집 계층 레인이 `collect.py` 수정(DEF-1~16) 후 `collect.py`·`build.py` 를 재실행해
> 검수 중 `site/index.html` 이 15:57·15:58 에 두 번 갱신되고, 검수 종료 시점에는 커밋까지 됐다
> (현재 `HEAD` = `5f8f824`, 그 안의 `site/index.html` DATA `generated_at` = `2026-09-03T15:58:54+09:00`).
> 검수 대상 커밋 `8ac4a07` 대비 차이는 **`var DATA` 리터럴 6줄(929·930·931·932·934·935)뿐이고 CSS·JS·마크업 2,780줄은 바이트 동일**임을
> 검수 시작·종료 두 시점에 줄 단위로 확인했다. 따라서 이 보고의 코드 좌표(`site/index.html:줄번호`)는 `8ac4a07` 과 현재 `HEAD` 양쪽에 그대로 유효하다.
> 그 위에서 판정 오라클·문구 단정·견고성 3종은 **커밋 `8ac4a07` 추출본**(`git show 8ac4a07:…`)을 대상으로 다시 돌려 결과가 동일함을 확인했고,
> 브라우저 증적(png·pdf)은 15:43~15:57 사이의 작업본으로 찍혀 **DATA 값(수집 시각·공고 id)만 커밋본과 다르다.** 결함 재현에는 영향이 없다.

---

## 1. 판정

# 조건부 GO

**한 줄 이유** — 자격·예산 판정은 독립 오라클 전수 재현에서 불일치 **0건**(정책 453,600 · 공고 1,240 · 비율 279 평가)이고 잘못된 "불가"를 내는 경로가 없다. 다만 탭2 **지역 필터 "부산 전역"이 코드상 연결돼 있지 않아**(`inRegion()` 이 `UI.region` 을 읽지 않음) 현재 데이터의 공고 5건 중 4건이 어떤 조작으로도 추천 목록에 도달하지 못한다 — 결함 #1 을 고치고 재검수해야 GO.

**조건부 해제 조건**: 결함 #1(높음) 수정 + #2·#3(중간) 수정 후 해당 항목 재검수(Q6·Q10·Q11·§2 신선도 표).

---

## 2. 무엇을 어떻게 확인했는가 (작성자 스크립트 미사용)

`tools/smoke_site.js` 는 쓰지 않았다. 검수자가 별도로 만든 6종:

| 파일 | 역할 | 규모 |
|---|---|---|
| `docs/qa/oracle_site_harness.js` | `site/index.html` 의 인라인 JS 를 DOM 스텁 위에서 실행(`vm` 컨텍스트). `QA_ROOT` 로 검수 대상 스냅샷 지정 | — |
| `docs/qa/oracle_site_judge.py` | **SPEC §3-1·§3-2 문장만 보고 별도로 구현한 판정 함수**. 화면 JS 를 참조하지 않았다 | 예산 2축·비율·소득·자산·청약·무주택·연령·지역·혼인·결합 4단 |
| `docs/qa/oracle_site_grid.js` | 조건 그리드로 화면 JS 를 전수 실행해 결과 덤프 | 조건 **56,700** × 정책 8 = **453,600** 판정 / 공고 31종(실 5 + 합성 26) × 조건·예산 40셋 = **1,240** / 비율 **279** |
| `docs/qa/oracle_site_compare.py` | 두 구현을 등급(ok/cond/no)·예산등급·비율값으로 대조 + SPEC 불변식 검사 | |
| `docs/qa/oracle_site_render.js` | 데이터 변형 30종 × 조건 16종 = **480 시나리오** 렌더 → throw·`NaN`/`undefined`/`Infinity` 누출 스캔 | |
| `docs/qa/oracle_site_assert.js` | Q# 중 문구·구조 항목 **73건** 단정 | |

**그리드 축** — 소득 `[null,0,3000,5000,7000,7500,8500,13000,99999,999999]` × 가구원수 `[null,1..9]` × 맞벌이 `[null,true,false]` × 무주택 `["","yes","no"]` × 혼인일 `["", 2015-09-03(11년 전), 2023-09-03, 2026-09-03(오늘), 2026-11-03(2개월 후), 2027-09-03(1년 후), "not-a-date"]` × 자산 3셋(미입력/0/999999) × 청약 3셋(미입력/24/0). 예산은 8셋(미입력·0·정상·상한 0·999999 등)을 직교로 돌렸다.

**핵심 수치**

```
== 평가 건수 ==   policy_evals 453600 · notice_evals 1240 · ratio_evals 279
== 배지 발생 ==   {'pending': 55377, 'approx': 11907}
== 오라클 불일치 == 0 종
== 견고성 ==      480 시나리오 · throw 0
== 문구·구조 단정 == 73항목 · 통과 72 · 실패 1 (결함 #1)
```

**불변식 전수 결과**

| 불변식 | 결과 |
|---|---|
| 비official(`p_busan_lucky7`, secondary) 정책의 "불가" | **0 / 56,700** (극단값 전부 포함) |
| 근사값(`approx`) 기준에서 비롯한 "불가" 사유 | **0** — 11,907건 전부 `조건부 — 기준액 근사값…` 로 강등 |
| `pending_change` 정책의 소득초과 "불가" | **0** — 55,377건 전부 `조건부 — 기준 완화 예정(확정 시 갱신)` |
| 공고에 승계된 "불가" | **0 / 1,240** — 공고 불가는 `exclusions` 매칭 경로 하나뿐 |
| 사유 없는 배지(빈 `why`) | **0** (정책·공고 양쪽) |
| `apply_end == null` 공고의 D-day 계산·`--hi` 누출 | **0** (`{d:null, cls:"dday-off"}`) |
| 기혼 7년 초과 official 정책 "불가" **발생** | 발생 확인 — `혼인 기간 7년 초과 (혼인 후 11년 0개월 경과)`, 7정책 동시 |
| 2인 가구 기본 입력 행복주택 기준액 | `by_household["2"]["110"]` = **6,452,897원** (맞벌이 `["2"]["130"]` = **7,626,151원**) |
| 3인 가구 (가산 키 없음 → 0) | `["3"]["100"]` = 8,168,429 / 맞벌이 `["3"]["120"]` = 9,802,115 |

---

## 3. SPEC §4 항목별 결과 (Q1~Q56)

| Q# | 결과 | 증거 |
|---|---|---|
| Q1 | 통과 | 단일 파일 `file:///…/site/index.html` 로 렌더. 5탭 전부 `window.onerror`/`unhandledrejection` **0건**(Chrome 계측) |
| Q2 | 통과 | `performance.getEntriesByType("resource")` = **0건 × 5탭**. 정적 전수: `<script src>`·`<link href>`·`<img>`·`<iframe>`·`@import`·`url(`·`fetch(`·`XMLHttpRequest`·`sendBeacon`·`WebSocket`·`new Worker`·`EventSource` **전부 0건**. `href=`/`src=` 속성 13개 전부 `#해시`(탭) 또는 런타임 `esc(u)`. https 문자열 23종 전부 분류 — 딥링크 3(역명+거래유형만)/정책 근거 9/공고 원문 6/출처 목록 4/발표 출처 1, **위반 0** |
| Q3 | 통과 | `showTab()` 이 `#tab-*` 5개를 `hidden` 토글, `hashchange` 리스너 + `<a href="#…">` → 새로고침·뒤로가기 유지 (`:1591-1612`) |
| Q4 | 통과 | 테마 **3블록** — `:root` 45토큰 전량 / `@media (prefers-color-scheme:dark){:root:not([data-theme="light"])}` 22토큰 / `:root[data-theme="dark"]` 22토큰, **두 다크 블록 값 동일**하고 22토큰 모두 `:root` 에 정의됨. **토큰 정의행 밖 색 리터럴 0건**. `<head>` 최상단 인라인 스크립트가 `hmt.theme` 로 `data-theme` 선반영(`:11-12`). `body{background:var(--bg)}`(`:127`). 대비 16쌍 계산 — `--fg`/`--fg-2`/판정 6색 전부 AA(4.5) 이상 |
| Q5 | 통과 | 375·414·768·1100·1200px × 5탭 = 25조합 계측 — `documentElement.scrollWidth == clientWidth` **전부 일치(가로 스크롤 0)**. 뷰포트 밖 요소는 전부 `nav.nav`(탭)/`div.line1`(노선 띠)/`div.tablescroll`(표) 내부이며 `overflow:hidden` 클리핑 **0건**. 육안: `site_375_{homes,stations,policy,input}.png` |
| **Q6** | **실패** | 숨김·펼침·URL 병기는 통과 — 인쇄 계측: `.topbar` `none` · `.side` `none` · `#tab-input` `none` · `.print-head` `block` · `.foldbody[hidden]` **display block(높이 295/337px = 펼쳐짐)** · `details.datanote` 8개 전부 닫힘(강제 펼침 제외) · `.fold` 테두리 top 0/bottom 1px · `a[href^=http]::after` URL 병기. **그러나 A4 본문폭(703px)에서 시세 카드가 종이 밖으로 잘리고(문서폭 1557px) 탭4 표가 26~41px 초과** → 결함 #3·#4 |
| Q7 | 통과 | `data/*.json` 10파일에 개인 조건 필드(`"deposit":`·`"loan":`·`"rentCap"`·`"netAsset"`·`"totalAsset"`·`"carValue"`·`"savingsMonths"`·`"savingsCount"`·`"marry"`·`"noHome"`·`hmt.cond`) **0건**. 저장 sink 는 `hmt.cond`(`STORE_KEY`)·`hmt.theme` **2개뿐**, 전부 `try/catch`. 쿠키·sessionStorage·IndexedDB 사용 0 |
| Q8 | 통과 | 렌더된 외부 `<a href="https…">` **20개 전부** `rel="noopener noreferrer"` + `referrerpolicy="no-referrer"` + `target="_blank"`(`extLink()` 단일 경로 `:972-977`). `safeUrl()` 화이트리스트 — 미통과 시 링크 대신 `링크 형식 오류` 칩. 딥링크 URL 에 금액·소득 파라미터 **0건**(예: `zigbang.com/search?q=구서역%20전세`) |
| Q9 | 통과 | `localStorage` 전 메서드 throw 환경 → **init throw 0**, 렌더 정상, `store-banner` 에 `이 브라우저에서 저장이 차단되어 새로고침 시 초기화됩니다` |
| Q10 | 통과 | 합성 공고(보증금 45,000~60,000 / 가용 18,000) → `computeHomes()` `over` 묶음에만, `fit`·`unknown` 에 없음. 화면은 `예산 밖 N건` 접힌 한 줄 + `.foldbody[hidden]`. 증적 `site_inject_homes.png` |
| Q11 | 통과 | `deposit_min == null` · `deposit_max = 20000` → `budgetOf().k = "unknown"`(`금액 미표기`), `over` 아님. 화면에 `금액 미표기 · 예산 판정을 할 수 없는 공고입니다. 탈락이 아닙니다.` 별도 섹션(접힘 아님) |
| Q12 | 통과 | 56,700조합 × `p_busan_lucky7`(secondary) → **불가 0건**. 극단값(소득 999,999만원·유주택·자산 999,999·혼인 11년 초과·청약 0)에서도 `조건부 — 수치 미검증(2차 자료 기준). 공고문 확인 필요 / 참고: …` |
| Q13 | 통과 | 공고 판정 1,240건 중 `exclusions` 매칭 없는 "불가" **0건**. 연결 정책 불가 공고는 전부 `조건부 — 연결 정책 자격 미충족 (…). 공고 기준은 다를 수 있으니 공고문 확인` |
| Q14 | 통과 | 승계 판정(ok/cond) 전수에서 사유에 연결 정책명 포함 — 위반 0. 예: `해당 — 자격 기준 충족 (연결 정책: 행복주택 (신혼부부·예비신혼부부))` |
| Q15 | 통과 | `linked_policy_id: null` → `조건부 — 연결된 정책 없음. 자격 대조 정보 없음`(target_groups 있으면 `… 대상 표기는 있으나 기준 대조 불가`). 해당·불가 **0건** |
| Q16 | 통과(문구 이견) | 근사값 기준에서 비롯한 "불가" **0건 / 근사값 11,907건**. 단 D11 "근사값 강등은 **기준 단위**" 규칙상 근사값 배지가 붙은 카드가 **다른 하드 사유**(유주택·자산 초과)로 불가가 될 수 있다 — Q16 문장을 카드 단위로 읽으면 실패로도 읽힌다. **SPEC §3-2 결합 2단·D11·DESIGN_SPEC §2-2-2 예시 기준**으로 통과 처리, 문장 어긋남은 §6. 부작용은 결함 #5 |
| Q17 | 통과 | 정책 453,600 + 공고 1,240 판정 전수에서 `why` 빈 문자열 **0건** |
| Q18 | 통과 | 신선도 바 **6줄**이 `myhome,lh,bmc,trades,policy,private` 순서 고정(`FRESH_ORDER`; `collectors[]` 를 `reverse()` 해도 순서 유지 확인). 태그는 `kind` 원값(`auto→자동`·`semi→반자동`·`manual→수동`·`none→—`), 승격 0. LH 2줄 병기(`감지 N분 전 · 공고 5건` + `상세 등록 —`) + `금액·면적은 수동 등록` 명기. **단 정책 줄 본문 문구가 SPEC §2 표와 다름 → 결함 #2** |
| Q19 | 통과 | "과거 계약 / 매물 아님 / 신고 지연 최대 30일" 캡션 **4곳** — 신선도 바(`:1576`)·탭2 시세 근거(`:2133`)·탭4 막대 차트(`:889` 정적)·`collectors[].note`(`:929`) |
| Q20 | 통과 | 탭4 표에 `표본 1건`·`표본 2건` 칩 + `.dim`(`--mid`), 탭2 요약은 `표본 부족 (1건) 참고값 …` 로 중위값 단정 안 함. 표본 0 은 `해당 기간 신고된 계약 없음`. `ratioWithin()` 은 `count < 5` → `null`(비율 미표기) |
| Q21 | 통과 | `aggOf(sid, htype, dtype)` 3키 조회. 아파트 선택 시 반환 집계 `housing_type` 전부 `apt`, 유형 전환 시 표 내용 변화 확인. 캡션 `주택유형을 섞은 중위값은 만들지 않습니다` |
| Q22 | 통과 | `collectors[key=lh].status="fail"` 강제 → 그 줄만 `class="row fail"`(`--hi`), `직전 성공 2026-09-03 15:20 (방금) · 5건` + 실패 사유 병기, 탭5 `⑤ 수집 실패` 1건, 탭2 `banner err`: `공고 수집이 실패했습니다 — LH …: QA 강제 실패. 아래는 2026-09-03 15:20 수집분입니다.` |
| Q23 | 통과 | `diff.is_first_run = true` → 탭5 `첫 수집입니다 / 비교할 직전 수집분이 없어 변경분을 만들 수 없습니다. 다음 수집부터 표시합니다.` throw 0 |
| Q24 | 범위 밖(수집 검수) | 2회 연속 수집 신규 0건 = `collect.py` 식별키. `REPORT_collect_20260903.md` 참조 |
| Q25 | 통과 | 조건 미입력 렌더에서 `homes-main`·`policy-main`·`st-table`·`news-main` 에 `NaN`/`undefined`/`Infinity` **0건**. 탭 배지 `nb-homes`·`nb-policy` = 빈 문자열(0 미노출). 탭2 `조건을 먼저 입력하세요`, 탭3 `banner warn`, 탭4 비율열 `—` |
| Q26 | 통과 | 조작 요소 전부 네이티브 포커서블 — `<button type=button>`(seg·facet·fold·rowbtn·line1-st)·`<input type=checkbox/radio/number/date>`·`<a href>`. `div`/`span` + onclick **0건**. `:focus-visible{outline:2px solid var(--accent)}`(`:145`). 탭 5개에 `aria-controls="tab-*"`(D22), 활성 탭 `aria-current="page"`, fold·row 에 `aria-expanded` |
| Q27 | 통과 | 가구원수 2·비맞벌이 → 적용비율 **110%**(100+10), 기준액 **6,452,897원** = `urban_worker.by_household["2"]["110"]` 정확 일치, `approx=false`. 맞벌이 → **130%**(120+10), **7,626,151원** = `["2"]["130"]`. `100%`/`120%` 아님 확인 |
| Q28 | 통과 | 가구원수 3 → `pct_adjust_by_household` 에 `"3"` 없음 → 가산 0 → **100%** / 맞벌이 **120%**, 둘 다 표 직접 조회(`approx=false`). 1인은 가산 20 → 120/140(140 은 표에 없어 근사값 → 강등 정상) |
| Q29 | 통과 | 혼인일 `2015-09-03`(11년 전) → `marriage_within_months:84` official 정책 **7건 불가**, 사유 `혼인 기간 7년 초과 (혼인 후 11년 0개월 경과)`. 게이트 면제 확인(비official 럭키7만 조건부 강등) |
| Q30 | 통과 | 혼인일 `2027-01-15`(미래) → `pre_marriage_allowed:false` 인 `p_newborn_jeonse` = `조건부 — 예비신혼 불인정 정책 — 혼인신고 후 신청 가능`. 8정책 **불가 0건**. `pre_marriage_within_months:3` 초과분은 `혼인 예정일까지 4.4개월 남음 …`(일수 기준 환산 `DAYS_PER_MONTH=30.4375` 확인) |
| Q31 | 통과 | `pending_change` 4정책 × 소득 초과 → **불가 0건**, `조건부 — 기준 완화 예정(확정 시 갱신) / 참고: 월평균 소득 16,666,667원이 기준 6,452,897원 초과 … — 완화가 예고된 기준이라 불가로 판정하지 않음` + `완화 예정` 배지(`tag-mid`). 전수 55,377건 |
| Q32 | 통과 | 유주택 + 자산 3종 초과 + 소득 초과 + 청약 부족 동시 → `p_national_rental` 사유에 **6개 전부** 나열: `월평균 소득 … 초과 / 총자산 … / 자동차 가액 … / 청약통장 가입 0개월 < 기준 6개월 / 납입 0회 < 기준 6회 / 유주택 — 무주택 요건 미충족`. **유주택 삼켜짐 없음** — official·`no_home_required` 정책 전수에서 유주택 입력 시 사유에 `유주택` 포함, 위반 0 |
| Q33 | 부분 통과 | **조건부** 판정에서는 강등 원인이 `참고:` 로 전부 남는다(전수 확인). **불가** 판정에서는 게이트 강등된 기준의 원인 문구가 사라지는데 배지는 남는다 → 결함 #5 |
| Q34 | 통과 | 정책 카드 소득 행: `도시근로자 월평균소득 100%(맞벌이 120%) 이하 · 2인 · **130%(120%+10%p 가산)** 적용액 7,626,151원` + `<span class="yl">2026년도 적용기준(2025년 실적)</span>` — 가산 반영 적용비율 + `year_label` 동시 노출 |
| Q35 | 통과 | `<span class="lab">부부 합산 전년도 세전 연소득 <span class="unit">만원</span></span>`(`:740`). `…연소득(만원)` 괄호형이 아니라 `unit` 스팬 분리형 — 요구 정보(연도·세전·부부합산·만원) 전부 있어 통과, 표기 차이는 §6 |
| Q36 | 통과 | `ratioWithin()` 손계산 대조 — `guseo/apt/jeonse`(count 5, `deposit_hist` 15버킷): 가용액 21,000 → 화면 `0.8`, 손계산 `(1+1+1+1)/5 = 80%` 일치 / 16,200 → 화면 `0.48`, 손계산 `(1+1+1×(200/500))/5 = 48%` 일치 / 18,000 → 브라우저 표시 `내 예산 이내 60%`, 손계산 `3/5` 일치. 개방 버킷(`hi:null`)은 999,999 에서도 세지 않음(0.8 유지). **분위수 CDF 보간 계수(`1.6`/`0.02`/`0.98`)·`quantile`·`percentile`·`deposit_p25/p75` 참조 JS 코드부 0건** |
| Q37 | 통과 | `500만원 버킷 기준` 캡션 렌더 **8회**. 값은 `CFG.deposit_hist_bucket` 에서 유도(`bucketCaption()`), 하드코딩 아님 |
| Q38 | 통과 | 거래유형 **전세만**(`deals:["jeonse"]`) · 월세 상한 30 · 공고 `rent 28~35` → `{k:"part", txt:"일부 평형 가능", why:"보증금 전 평형(1,000만원 ~ 2,000만원) / 월임대료 일부 평형(28 ~ 35만원, 상한 30만원)"}`. 브라우저 확증: `site_inject_homes.png` 의 `QA · 일부 평형 (월임대료 28~35, 상한 30) — Q38` 카드 |
| Q39 | 통과 | 월세 상한 `null` → `{k:"all", why:"보증금 전 평형(…) / 월임대료 상한 미입력"}` — 보증금 축만 반영 |
| Q40 | 통과 | `deposit_min:null, deposit_max:20000` → `{k:"unknown", why:"임대보증금 하한 미표기 / 월임대료 미표기"}`. 예산 밖으로 접히지 않음 |
| Q41 | 통과 | `deposit_min:15000, deposit_max:null`(가용 18,000) → `{k:"part", why:"보증금 하한 1억 5,000만원은 예산 내 · 상한 미표기 / 월임대료 미표기"}`. 하한 초과 시 `보증금 하한 …이 가용액 초과 (상한 미표기)` |
| Q42 | 통과(로그 실측은 범위 밖) | `site/index.html`·`data/*.json` 10파일에 `serviceKey`/`servicekey` **0건**. 32자 이상 hex/base64 후보 = URL 경로 문자열뿐. `collect.py:72-88 mask_secret()` 이 `serviceKey=…`→`***`, http(s) 쿼리스트링 전체→`?***`, 키 원문·URL-encode 3형태 치환하고 `err_text()`·`log()`·`record["error"]` 가 전부 경유. `.github/workflows/daily.yml:53` 에 `grep -rniE 'servicekey' data/ site/` 게이트 존재 |
| Q43 | 통과 | `collectors[].name` 을 전부 `라벨변경-{key}` 로 바꿔도 민간 줄 문구·LH 2줄(`상세 등록`)·실패 배너 유지. 화면 분기는 `collectorByKey(k)`·`FRESH_ORDER`·`c.key === "lh"` 등 **key 전용**, 한국어 name 분기 0 |
| Q44 | 통과 | `kind:"none"` 민간 줄 = `class="row off"` 회색 + `수집 안 함 — 검색 링크만 제공`. (같은 문구가 정책 줄에도 나오는 것은 결함 #2 이며 민간 줄 자체는 규격대로) |
| Q45 | 부분(화면 통과) | 화면: 탭2 `신규 · 최근 7일` 이 `notices[].first_seen` 을 `daysBetween(fs, NOW) <= 7 && >= 0` 로 필터(`:2004-2008`), 캡션 `notices[].first_seen 기준`. 합성 공고 `first_seen 2026-09-01` 포함·마감분 제외 확인. **`first_seen` 승계(2회 연속 수집 불변)는 범위 밖(수집 검수)** |
| Q46 | 통과 | `apply_end:null` → `ddayOf() = {d:null, cls:"dday-off", txt:"접수기간 미표기"}`, `closedOf().closed = false`. 공고 판정 1,240건 전수에서 `apply_end==null` 인데 `d != null` 또는 `cls != "dday-off"` 인 사례 **0건**. 마감 임박 블록에도 미포함 |
| Q47 | 통과 | 3경로 문구 구분 — `apply_end < today` → `접수 종료 (08/01)`(reason `apply_end`) / `disappeared:true` → `출처 목록에서 사라짐(마감 추정)`(reason `disappeared`) / `notice_status=="접수마감"` + 기간 미표기 → `공고상태 접수마감 (접수기간 미표기)`(reason `notice_status`). `disappeared` 가 `apply_end` 보다 먼저 평가됨 |
| Q48 | 통과 | 탭2 `마감 임박 · D-30 이내` + `오늘 기준으로 다시 센 전체 — 새 소식 탭은 "새로 들어온 것"만 셉니다`. 탭5 `② 마감 임박은 이번 수집에서 새로 D-30/D-7 안으로 들어온 공고입니다(diff.closing_soon). 추천 주거 탭의 고정 섹션은 오늘 기준 D-30 전체…`. 양쪽 캡션이 세는 대상을 명시 |
| Q49 | 통과 | `stopsFromBase()` 가 `meta.config.stations[]` 인덱스 차로 계산 — 기준역 `guseo` → `8,7,6,5,4,3,2,1,0,1,2,3,4`(= 절댓값 i−8), `nopo` → `12,…,0`. 기준역 변경 시 즉시 다른 값. `data/*.json` 10파일에 `stops_from_base` **0건**(`build.py:238-239` 도 error 로 차단). `meta.config.stations` 순서 = `config.json` 순서 그대로 |
| Q50 | 통과 | 배제 판정은 `EXCLUSION_RULES`(=`CFG.exclusion_rules`) 경유. 판정 코드부(`EXCL_INPUT`~`noticeExclusionHit`)에 config 키워드 하드코딩 **0건**. 동작: `유주택자 제외` + 무주택 `no` → **불가**, 무주택 `yes` → 불가 아님, 표에 없는 `해외 체류자 제외` → 표시만, 입력 축 없는 `세대주가아닌`(householder) → 불가 안 냄. 카드에 `배제 조건은 config.exclusion_rules 에 매칭된 항목만 판정에 씁니다. 나머지는 표시만 합니다.` 명기 |
| Q51 | 통과 | 화면: `조건부 — 연결 정책(p_typo)을 찾을 수 없음 — 설정 오류`, `null` 문구(`연결된 정책 없음. 자격 대조 정보 없음`)와 **다름**. 빌드: `build.py:261-266` 이 dangling 을 `report.warn` 으로 남기고 `Report.error` 가 아니므로 빌드 성공(코드 확인. `build.py` 실행은 `site/` 를 덮어써 하지 않았다) |
| Q52 | 통과 | 화면 데이터 7키 = `meta, notices, trades, income_tables, policies, diff, diff_history`. `DATA.diff` ≡ `data/snapshot_diff.json`, `DATA.diff_history` ≡ `data/diff_history.json`(배열 1항목)이고 히스토리 항목 키가 `snapshot_diff` 와 동일(`date, is_first_run, new_notices, closing_soon, closed_notices, changed_policies, collector_failures`). `diff.history` 중첩 없음. `refetched_months` = `trades` 에만(`diff`·`meta` 에 없음) |
| Q53 | 통과 | 첫 실행 화면은 `DATA.diff.is_first_run` 단일 경로(`renderNews()`). `data-mock`·`mockFirstRun`·`forceFirstRun`·`btn-firstrun` **0건**, `data-mock-only` **0건** |
| Q54 | 범위 밖(수집 검수) | `content_id` 단일 `#id` 수용·실패 시 해시 미갱신 = `collect.py` |
| Q55 | 범위 밖(수집 검수) | `numOfRows=1000` + `pageNo` 순회·`totalCount` 대조 = `collect.py` |
| Q56 | 범위 밖(수집 검수) | 키 없는 환경 `status:"skip"`·`--fixture` = `collect.py`. 화면 측 정황만 확인 — 현 산출물이 fixture 기반 빌드(`collectors[].note` 에 `· fixture`, `policy` 수집기 `error:"fixture 모드 — 정책 페이지 fetch 생략"`)이며 그 상태로 Q1~Q26 검수가 실제로 가능했다 |

**집계** — 통과 47 · 부분/문구이견 4(Q16·Q33·Q35·Q45) · 실패 1(Q6) · 범위 밖 4(Q24·Q54·Q55·Q56)

---

## 4. 결함

| # | 심각도 | 파일:줄 | 문제 | 재현 | 권고 |
|---|---|---|---|---|---|
| 1 | **높음** | `site/index.html:1859-1866` (`inRegion`) | 탭2 **지역 필터가 동작하지 않는다.** `inRegion(n)` 이 `UI.region` 을 전혀 읽지 않아 `13역 인근`↔`부산 전역` 버튼(`:2238-2240`)·`부산 전역으로 보기` 버튼(`:2213-2214`)을 눌러도 목록이 그대로다. 필터 라벨(`:2160`)·힌트(`:2151-2152` "부산 전역으로 바꾸면 N건이 더 있습니다")·노트(`:2193-2194`)만 바뀐다. 현 데이터에서 공고 5건 중 **4건**(`station_ids: []` + `sigungu_code` 있음)이 `outRegion` 으로 잡혀 **어떤 조작으로도 추천 주거 탭에 표시되지 않는다.** 화면이 "더 있다"고 알려주면서 보여줄 방법이 없다 | `node docs/qa/oracle_site_assert.js` → `FAIL Q11/§2-2-3  near=[fit,unknown,over,outRegion]=[1,1,1,4] busan=[1,1,1,4]`. 브라우저: `docs/qa/site_inject_homes.png` — `UI.region="busan"` 상태인데 `신규 · 최근 7일` 이 9건(합성 8 + 실 1)이고 LH 실공고 4건이 없다 | `inRegion(n)` 첫 줄에 `if(UI.region === "busan") return true;` 추가(또는 `meta.config.sigungu_codes`/`busan_sigungu_codes` 로 부산 여부 판정). SPEC §2 탭2 2-3 "지역 필터 기본값은 13역 인근이되 그 결과가 0건이면 부산 전역 건수를 안내" |
| 2 | 중간 | `site/index.html:1531-1534` (`renderFresh` 의 `status === "skip"` 분기) | skip 인 **모든** 수집기에 `수집 안 함 — 검색 링크만 제공` 을 찍는다. 이 문구는 SPEC §2 표·Q44 에서 `kind:"none"` 민간 매물 줄 전용이다. 현 데이터에서 **정책 줄(`key:"policy"`, `kind:"semi"`, `status:"skip"`)이 "수집 안 함 — 검색 링크만 제공"으로 표시**되어 사실과 다르고, SPEC §2 가 정한 정상 표시 `정리 YYYY-MM-DD · 페이지 점검 N시간 전`(=`meta.policy_verified_latest` 2026-09-03)이 화면에서 사라진다. skip 사유(`error: "fixture 모드 — 정책 페이지 fetch 생략"`)도 표시되지 않는다(원칙 7 "조용히 넘기지 않는다"). D23 의 키 없는 환경에서는 myhome·lh·trades 줄까지 같은 문구가 된다 | 신선도 바 렌더 5번째 줄: `신혼부부 정책 기준 │ 수집 안 함 — 검색 링크만 제공 │ 수치는 사람이 확인해 등록한다 · 변경 감지만 자동 │ [반자동]`. 검증: 정책 줄에 `정리 ` 문구 없음(`/정리 /.test(fresh) === false`), `fixture 모드` 문자열 화면 출현 `false`. 증적 `docs/qa/site_light_1200_homes.png` 5번째 줄 | skip 분기 조건을 `c.kind === "none"`(또는 `c.key === "private"`)로 좁히고, 그 밖의 skip 은 `--mid` 로 `직전 성공 {fmtDT} · {건수} · 이번 실행 건너뜀({error})` 형태로 별도 처리. 정책 줄은 `key === "policy"` 분기가 살아나야 한다 |
| 3 | 중간 | `site/index.html:373-376`(`.tradewrap`/`.trade-sum`) + `:654`(인쇄 `overflow:visible`) | **인쇄에서 시세 근거 카드가 종이 밖으로 잘린다.** `.tradewrap{display:flex; overflow-x:auto}` 에 `flex-wrap` 이 없고 `.trade-sum{flex:0 0 250px}` 이라, 인쇄 블록이 `overflow:visible!important` 로 스크롤만 없애면 카드가 그대로 옆으로 뻗는다. A4 본문폭(210mm−24mm ≈ 703px) 계측에서 탭2 문서 폭이 **1557px**(선택 역 6개 기준, 관심 역 13개 전체면 더 커진다) | A4 폭 계측: `homes  A4본문폭=688px docScrollW=1557 → 종이 밖 요소 60개 (DIV.trade-sum right=783 w=250 …)`. 증적 `docs/qa/site_inject_print_homes.png`(4번째 카드부터 잘림), `docs/qa/site_print_homes_full.pdf` | `@media print` 에 `.tradewrap{display:block!important}`(카드 세로 스택) 또는 `.tradewrap{flex-wrap:wrap!important}` + `.trade-sum{flex:0 0 48%!important}` 추가 |
| 4 | 낮음 | `site/index.html:425-431`(`.etable`) + `:654` | 인쇄에서 **탭4 비교표가 A4 본문폭을 26~41px 초과**해 마지막 열이 잘린다. `.tablescroll` 이 인쇄에서 `overflow:visible` 이라 스크롤로 볼 수도 없다 | A4 폭 계측: `stations A4본문폭=688px docScrollW=746, TABLE.etable right=746 w=729`. 증적 `docs/qa/site_print_stations.pdf`, `docs/qa/site_printemul_stations.png` | `@media print` 에 `.etable{font-size:9.5pt} .etable th,.etable td{padding:4px 6px}` 로 폭을 줄이거나 탭4 인쇄만 `@page{size:A4 landscape}` |
| 5 | 낮음 | `site/index.html:1444-1454`(`judgePolicy` 의 `if(hard.length)` 분기) + `:2344-2346`(`gateBadges`) | 판정이 **불가**로 확정되면 게이트로 강등된 기준의 원인 문구(`gates`/`notes`)가 사유에서 통째로 버려진다. 그런데 `근사값 강등`·`완화 예정` 배지는 그대로 붙어 **사유 없는 배지**가 된다. D11 "강등의 원인 문구는 지우지 않고 사유 뒤에 `참고:` 로 남긴다"·Q33 과 어긋난다 | 가구원수 1 · 맞벌이 O · 연소득 7,000만원 · 총자산·자동차 999,999만원 → `p_happy_house` = **불가**, `badges:["approx"]`, `why = "총자산이 기준 초과 (99억 9,999만원 > 3억 4,500만원) / 자동차 가액이 기준 초과 (…)"` — 140% 근사값 기준 소득 초과 사실이 카드에서 사라졌는데 `근사값 강등` 칩은 표시된다. 전수: `Q16_approx_reason_no` 8,307건 + `Q31_pending_income_reason_no` 33,561건 = **41,868건** | `hard.length` 분기에서도 `notes` 를 `… / 참고: …` 로 이어 붙인다. 최소한 hard 불가일 때는 `gateBadges` 를 떼거나 `참고` 툴팁을 남긴다 |
| 6 | 낮음 | `site/index.html:1531-1534` | 민간 매물 줄에서 `v` 와 `why` 가 같은 문장을 두 번 찍는다 — skip 분기가 `v` 를 상수로, `why` 를 `c.note` 로 쓰는데 `private` 수집기의 `note` 가 마침 같은 문장이다 | 신선도 바 6번째 줄: `민간 매물 (네이버부동산·직방·다방) │ 수집 안 함 — 검색 링크만 제공 │ 수집 안 함 — 검색 링크만 제공 │ [—]`. 증적 `docs/qa/site_light_1200_homes.png` | private 줄의 `why` 는 `c.error`(`민간 부동산 플랫폼은 크롤링하지 않는다 (원칙 3)`) 또는 기존 폴백 문구를 쓴다. 결함 #2 와 함께 고칠 수 있다 |
| 7 | 낮음 | `site/index.html:1164-1175`(`loadCond`) + `:1186`(`availAmount`) | `localStorage["hmt.cond"]` 값을 타입 검증 없이 `COND` 로 복사한다(`for(var k in o) COND[k] = o[k]`). 숫자 필드에 문자열이 들어오면 `availAmount()` 가 문자열 연결(`"-100" + "-1" = "-100-1"`)이 되어 탭4 막대 SVG 에 `width="NaN"` 이 찍힌다(DESIGN_SPEC §4 "어느 상태에서도 `NaN`·`undefined`·`Infinity` 금지"). UI 입력 경로는 `Number(raw)` + `numError()` 로 막혀 있어 **손상·조작된 저장값에서만** 발생한다 | `node docs/qa/oracle_site_render.js` → `총 시나리오 480 · throw 0 · 누출 63`. 누출은 전부 `chart-bar` 이고 조건은 `음수 문자열`(30) · `문자열 쓰레기`(30) · `deposit_median null`(3). 예: `<rect x="62" y="6" width="NaN" height="14" …>` | `loadCond()` 에서 `NUMFIELDS` 대응 키는 `Number.isFinite(v) ? v : null` 로 정규화. 실브라우저 정상 경로(실데이터·합성데이터 × 5탭)에서는 누출 0건이므로 우선순위는 낮다 |
| 8 | 낮음 | `site/index.html:2433-2441`(`barChart`) | 집계의 `deposit_median` 이 전부 없으면 `maxV = 0` → `plot * 0 / 0 = NaN` → 막대 폭 `NaN`. 스키마상 `deposit_median: int`(non-null)이라 정상 데이터에서는 나지 않지만 가드가 없다. `count > 0` 필터만 있어 `count>0` + `median null` 조합을 막지 못한다 | `oracle_site_render.js` 변형 `deposit_median null (스키마 밖)` × 조건 `빈 조건`·`기본 2인 미입력`·`극단 0` → `width="NaN"` 3건 | `rows` 필터에 `r.a.deposit_median != null` 추가 + `var maxV = Math.max(1, …)` |

---

## 5. 육안 확인 필요

Chrome 152 헤드리스로 계측·촬영이 가능해 남은 항목은 적다.

1. **실제 프린터 흑백 출력** — `print-color-adjust:exact` + 1px 테두리 이중화가 CSS·계측으로는 확인되지만(테두리 규칙 8종 존재, PDF 5종 생성), 배경을 빼는 실제 드라이버에서 `.tag`·`.policy-stale`·`.policy-changed`·`.exclrow` 구분이 유지되는지는 종이로 봐야 한다.
2. **A4 실제 페이지 나눔** — `break-inside:avoid` 가 걸린 `.notice`/`.policy`/`.trade-sum`/`.news-sec` 가 실제로 쪼개지지 않는지. 생성한 PDF(`site_print_policy.pdf` 8쪽 등)를 사람이 넘겨 봐야 한다(이 환경에 PDF 렌더러 `pdftoppm` 없음).
3. **실기기 375px 터치 스크롤** — 탭 바(`nav` 336/404px)·노선 띠(`line1` 314/644px)·표(`tablescroll` 314/684px)가 가로 스크롤 컨테이너임은 계측으로 확인했으나, 모바일에서 세로 스크롤과 충돌하지 않는지는 실기기 확인 몫.
4. **다크 모드 시스템 자동 전환** — `data-theme` 주입 사본으로 다크 팔레트를 확인했고 두 다크 블록 값이 동일함을 코드로 확인했으나, `prefers-color-scheme` 실제 전환 시 번쩍임 유무는 실기기 확인 몫(`<head>` 인라인 스크립트 존재는 확인).
5. **GitHub Pages 배포본의 외부 요청 0건** — 로컬 `file://` 에서 리소스 요청 0건을 확인했다. Pages(https)에서도 같아야 하지만 배포 후 1회 확인 권장.

---

## 6. 지시서·SPEC 어긋남 (SPEC 기준으로 판정했고 어긋남만 보고)

1. **Q16 문장 vs D11.** Q16 은 "`근사값` 배지가 붙은 **판정**에서 불가 0건" 이라 쓰여 카드 단위로 읽힌다. 그런데 §3-2 결합 2단은 "official 이고 **근사값이 아닌** 불가 사유가 하나라도 있으면 불가", D11·DESIGN_SPEC §2-2-2 는 "근사값 강등은 **기준 단위**"이며 그 예시가 `불가 — 소득 … / 총자산 … / 유주택` 이다. 즉 근사값 배지가 붙은 카드가 다른 하드 사유로 불가가 되는 것은 **정상**이다. Q16 은 "근사값 **사유**에서 비롯한 불가 0건" 으로 문장을 조여야 검수 자동화가 오탐하지 않는다. Q31 도 같다.
2. **Q35 문자열.** SPEC 은 라벨을 `부부 합산 전년도 세전 연소득(만원)` 으로 못박았고 구현은 `부부 합산 전년도 세전 연소득` + `<span class="unit">만원</span>` 이다. 요구 정보는 전부 있어 통과로 봤다.
3. **`ht-qa.md` 지시서의 불변식 목록.** "금액 null·meta_only 공고 예산 판정 제외"라고 적혀 있으나 SPEC 은 `meta_only` 를 판정에서 빼는 게 아니라 **금액이 null 이면 `금액 미표기`** 로 처리한다(D10). 구현은 SPEC 대로다.
4. **정책 `note` 산문 안의 "null" 단어.** `data/policies.json` 의 `criteria.income.note`·`note` 에 `pct_dual = null(→ pct 로 판정, 조건부)`·`청약통장 요건은 원문에서 확인하지 못해 null` 처럼 **"null" 이라는 단어가 데이터 원문으로** 들어 있고 정책 카드가 그 산문을 그대로 노출한다(`:2358`, `esc()` 경유). 연구자가 쓴 근거 문장이므로 누출 검사 대상에서 **의도적으로 제외**했다. 누출 검사는 `NaN`·`undefined`·`Infinity`·`[object Object]` 4패턴으로만 했고 정상 경로 결과는 0건이다.

**참고(결함 아님)**

- `--fg-3` 대비: 라이트 `on --bg-2` **3.65**, `on --bg-3` **3.22** / 다크 4.33·3.87 — WCAG AA(4.5) 미달, AA-large(3.0) 충족. 11.5~12px 캡션·보조문에 쓰인다. `DESIGN.md` §1 이 토큰 값을 정본으로 고정하고 "새 팔레트 금지"라 화면 계층에서 고칠 수 없다. 인쇄 팔레트는 7.08~7.87 로 문제 없다.
- 탭1 `f-household` 의 HTML `max="10"`(`:743`) ↔ JS `NUMLIMIT["f-household"].max = 20`(`:1685`) 불일치. `type=number` 의 `max` 는 힌트일 뿐이라 11~20 을 타이핑하면 통과한다. 판정은 그래도 정상(11인 이상은 표에 행이 없어 `기준액 미확보` 조건부).
- `income_tables.median_income.by_household["2"]` 에 `"110"` 칸이 없어(고시가 100/120/150 만 공표) **통합공공임대는 2인 가구에서 항상 근사값**이 되고, 그 결과 소득 초과로 불가가 나지 않는다. SPEC §3-2 폴백 규칙대로 동작한 것이지만 D2 가 노린 "기본 입력에서 공급형 정책이 정상 판정" 상태는 아니다 — 데이터(연구자) 몫.
- `site/index.html:8` 의 `<head>` 인라인 스크립트 **주석 안에 리터럴 `</body>` 가 있다.** HTML 파싱상 무해하다(`</script` 만 스크립트를 닫는다). 그러나 `</body>` 를 **첫 번째 매치로 치환**하는 도구는 이 스크립트를 깨뜨린다 — 이번 검수의 인쇄 에뮬레이션 사본이 실제로 한 번 깨졌다.

---

## 7. 다음 단계 함정 3개

1. **결함 #1 을 고치면 탭2 에 "역 매핑 없음" 공고가 4건 쏟아진다.** 현 `notices[].station_ids` 는 5건 전부 빈 배열이어서 카드의 `기준역까지` 가 전부 `역 매핑 없음` 이 되고, 좌측 `역` facet 은 13개 역 모두 0 을 표시하는데 `공급유형` facet 은 5 를 표시하는 불일치가 눈에 보이게 된다. 필터 수정과 **공고↔역 매핑(수집 계층)** 을 같은 회차에 맞춰야 사용자가 "필터가 또 이상하다"고 느끼지 않는다.
2. **`site/index.html` 을 두 검수자가 동시에 보고 있다.** 이번 검수 중에도 병행 수집 검수자의 `collect.py`+`build.py` 재실행으로 대상 파일이 두 번 갱신됐다. 다음 회차에는 검수 시작 시 `git show <commit>:site/index.html` 로 스냅샷을 떠서 고정하고(`QA_ROOT` 환경변수로 이 저장소의 오라클 3종이 이미 지원한다) 그 위에서 판정하라. 작업본 위에서 돌리면 결함 재현 좌표가 흔들린다.
3. **`build.py` 를 QA 가 돌리면 검수 대상이 사라진다.** `build.py` 는 `site/index.html` 을 덮어쓴다. Q51(dangling 경고 + 빌드 성공)·Q56(fixture 경로) 을 실측하려면 산출 경로 인자(`--out`)가 필요하다. 이번엔 `build.py:261-266`·`Report.error/warn` 코드 확인으로 대체했고 **실행하지 않았다.**

---

## 8. 증적 파일

| 파일 | 내용 |
|---|---|
| `site_light_1200_{homes,policy,stations,news}.png` | 라이트 · 데스크톱 1200px 4탭 |
| `site_dark_1200_homes.png` · `site_dark_375_policy.png` | 다크(`data-theme="dark"` 주입 사본) 데스크톱·모바일 |
| `site_375_{homes,stations,policy,input}.png` | **정확한 375px 렌더**(iframe 375px 랩퍼 — `--window-size=375` 는 헤드리스에서 504px 로 렌더돼 크롭이 된다) |
| `site_inject_homes.png` | 합성 공고 9건 주입 — 예산 2축·배제조건·dangling·마감 3경로가 한 화면에 |
| `site_printemul_{input,homes,policy,stations}.png` | `@media print` → `@media all` 치환 사본으로 인쇄 레이아웃을 화면에서 확인 |
| `site_inject_print_homes.png` | 인쇄 레이아웃 + 합성 데이터 — 결함 #3(시세 카드 잘림) 증적 |
| `site_print_{homes,policy,stations,input}.pdf` · `site_print_homes_full.pdf` | `--print-to-pdf` 실 PDF 5종 |
| `oracle_site_{harness,grid,render,assert}.js` · `oracle_site_{judge,compare}.py` | 재현 스크립트(부록 참조) |

---

## 9. `git status --short`

```
?? docs/qa/REPORT_site_20260903.md
?? docs/qa/oracle_site_assert.js
?? docs/qa/oracle_site_compare.py
?? docs/qa/oracle_site_grid.js
?? docs/qa/oracle_site_harness.js
?? docs/qa/oracle_site_judge.py
?? docs/qa/oracle_site_render.js
?? docs/qa/site_375_homes.png
?? docs/qa/site_375_input.png
?? docs/qa/site_375_policy.png
?? docs/qa/site_375_stations.png
?? docs/qa/site_dark_1200_homes.png
?? docs/qa/site_dark_375_policy.png
?? docs/qa/site_inject_homes.png
?? docs/qa/site_inject_print_homes.png
?? docs/qa/site_light_1200_homes.png
?? docs/qa/site_light_1200_news.png
?? docs/qa/site_light_1200_policy.png
?? docs/qa/site_light_1200_stations.png
?? docs/qa/site_print_homes.pdf
?? docs/qa/site_print_homes_full.pdf
?? docs/qa/site_print_input.pdf
?? docs/qa/site_print_policy.pdf
?? docs/qa/site_print_stations.pdf
?? docs/qa/site_printemul_homes.png
?? docs/qa/site_printemul_input.png
?? docs/qa/site_printemul_policy.png
?? docs/qa/site_printemul_stations.png
```

**`docs/qa/` 외 변경 0건.** 기존 `docs/qa/01~04`(v1.1 목업 증적)과 병행 검수자의 `REPORT_collect_20260903.md`·`oracle_collect_*.py` 는 건드리지 않았다. 커밋하지 않았다.
`data/`·`site/index.html` 이 커밋 `8ac4a07` 과 다른 것은 **병행 수집 검수자의 `collect.py`/`build.py` 재실행 결과**이며 이 검수자의 쓰기가 아니다(위 목록에 없다).

---

### 부록 — 재현 명령

```bash
# 검수 대상 스냅샷 고정
mkdir -p /tmp/c/site /tmp/c/data
git show 8ac4a07:site/index.html > /tmp/c/site/index.html
git show 8ac4a07:config.json     > /tmp/c/config.json
for f in meta notices policies income_tables trades snapshot_diff diff_history; do
  git show 8ac4a07:data/$f.json > /tmp/c/data/$f.json; done
export QA_ROOT=/tmp/c

# 1) 판정 전수 재현 (화면 JS 대 독립 오라클)
node   docs/qa/oracle_site_grid.js    /tmp/grid.json
python docs/qa/oracle_site_compare.py /tmp/grid.json      # -> 오라클 불일치 0 종

# 2) 견고성 (데이터 변형 30 x 조건 16)
node docs/qa/oracle_site_render.js /tmp/render.json       # -> throw 0

# 3) 문구 구조 단정 73항목
node docs/qa/oracle_site_assert.js /tmp/assert.json       # -> 통과 72 / 실패 1 (결함 #1)
```

---
---

# 재검수 (2026-09-03 16:40 ~ 17:00 KST)

| 항목 | 값 |
|---|---|
| 재검수 대상 | `site/index.html` — 커밋 `3316a3f` (`design: 화면 QA 결함 1~8 수정 … + 재빌드`), sha256 앞 16자 `61498245b6932841` |
| 함께 반영된 명세 | `5e3f819` (SPEC — `collector_failures[].status` 에 `hold` 추가) · `324c6f9` (collect/build 의 hold 기록) · DESIGN_SPEC **v1.2.2** |
| 1차 대비 코드 변경 | `site/index.html` **+110 / −14 줄** (DATA 리터럴 제외). CSS 인쇄 블록 · `normCond()` 신설 · `judgePolicy` 불가 분기 · `renderFresh` skip/hold 분기 · `inRegion` · `barChart` 가드 · `FAILURE_STATUS` 표 · `.news-item.is-off` |
| 재검수 기준 시각 | 오라클·계측에 `NOW = 2026-09-03T16:37:12+09:00` 주입 |
| 쓰기 범위 | `docs/qa/` 만. 소스·명세·목업 무수정. `collect.py`/`build.py` 는 지시대로 fixture 시나리오 확인에만 실행하고 **`git checkout -- data site` 로 원복**(원복 후 `site/index.html` sha256 = `61498245b6932841`, 재검수 시작 시점과 동일) |

## R1. 판정

# 조건부 GO

**한 줄 이유** — 1차 결함 **#1~#8 전건이 해소**됐고(전수 재현·A4 계측·손상값 주입으로 각각 확인) 판정 오라클은 여전히 불일치 0이지만, 이번에 새로 들어온 `hold` 렌더가 신선도 바에 **`직전 0건 유지`** 라고 사실과 다르게 적어(실제 5건 유지, 같은 줄의 사유는 `직전 5건 유지`) 한 줄 안에서 자기모순을 만든다 — 새 결함 #9 를 고치면 GO.

**조건부 해제 조건**: 새 결함 #9(중간) 수정 + #10(낮음) 정리 후 신선도 바 hold 줄만 재확인. 1차 결함 #1~#8 관련 항목은 재검수 불필요.

## R2. 1차 결함 #1~#8 해소 확인

| # | 1차 심각도 | 결과 | 재현·증거 |
|---|---|---|---|
| 1 | 높음 | **해소** | `inRegion()` 에 `if(UI.region === "busan") return true;` 추가(`:1946-1951`). 계측 — `near`: `{unknown:1, outRegion:4, 도달:1}` → `busan`: `{unknown:5, outRegion:0, **도달 5/5**}`, `inRegion()` 이 5건 전부 `true`. 오라클 `Q11/§2-2-3` 단정 **통과**(1차 유일 실패 항목). 브라우저: `site2_fresh_hold_1200.png` — `부산 전역` 활성에서 `신규 · 최근 7일 13건`(실 5 + 합성 8), LH 실공고 4건이 모두 카드로 나온다 |
| 2 | 중간 | **해소** | skip 분기를 `c.status === "skip" && c.key === "private"` 로 좁히고(`:1594`) 그 외 skip 은 별도 문구로 분기(`:1604-1612`). 정책 줄 = `정리 2026-09-03 · 이번 실행 건너뜀` + 사유 `fixture 모드 — 정책 페이지 fetch 생략`. SPEC §2 가 요구한 `meta.policy_verified_latest` 가 화면에 복귀하고 skip 사유도 표시된다(원칙 7). `수집 안 함 — 검색 링크만 제공` 문구 출현 **1회**(민간 줄 전용) |
| 3 | 중간 | **해소** | 인쇄 블록에 `.tradewrap{flex-wrap:wrap!important}` + `.trade-sum{flex:0 0 calc(50% - 3px)!important; max-width:calc(50% - 3px)!important}` 추가(`:663-664`). A4 본문폭 **703px** 계측(합성 공고 14건 · 시세 카드 6개) — 탭2 `docScrollW=703 == pageW=703`, **종이 밖 요소 0개**(1차 1557px / 60개). 육안 `site2_printemul_homes.png` 에서 시세 카드가 2열로 접혀 들어간다 |
| 4 | 낮음 | **해소** | 인쇄 블록에 `.etable{font-size:9pt}` · `th,td{padding:3px 4px; word-break:break-all}` · `th{font-size:8.5pt; white-space:normal}` 추가(`:667-669`). 703px 계측 — 탭4 `docScrollW=703`, 종이 밖 **0개**(1차 746px / 134개). 육안 `site2_printemul_stations.png` 에서 마지막 열 `진행 공고` 까지 보인다. `landscape` 로 도망가지 않아 다른 탭 용지 방향이 유지된다 |
| 5 | 낮음 | **해소** | 불가 분기에서도 `notes` 를 `참고:` 로 이어 붙인다(`:1496-1501`). 1차 보고서 재현 케이스(가구원수 1 · 맞벌이 O · 연소득 7,000만원 · 총자산·자동차 999,999만원) → `p_happy_house` = `불가 [approx] 총자산이 기준 초과(…) / 자동차 가액이 기준 초과(…) / **참고: 월평균 소득 5,833,333원이 기준 5,338,708원 초과 (1인 · 140%(120%+20%p 가산) · 근사값) — 기준액이 근사값이라 불가로 판정하지 않음**`. 오라클 `Q33_no_note` 를 **불가 판정까지 확장**해 전수 검사 — 배지가 붙었는데 `참고:` 가 없는 카드 **0 / 453,600** |
| 6 | 낮음 | **해소** | private 줄 `.why` 가 `c.error` 우선(`:1600`). `.v` = `수집 안 함 — 검색 링크만 제공`, `.why` = `민간 부동산 플랫폼은 크롤링하지 않는다 (원칙 3)` — 중복 없음 |
| 7 | 낮음 | **해소** | `normCond()` 신설(`:1187-1206`). 손상된 `hmt.cond` 4종을 `loadCond()` 경로로 주입 — 문자열 숫자·NaN·객체/배열 뒤섞기·스키마 밖 키 전부 미입력으로 정규화, `availAmount()` 는 항상 `number`, **누출 0**. 스키마 밖 키(`evil`, `__proto__x`)가 `COND` 에 남지 않아 프로토타입 오염·XSS 표면도 함께 줄었다. 견고성 스위트 **누출 63 → 0 / 480 시나리오**, throw 0 |
| 8 | 낮음 | **해소** | `rows` 필터에 `Number.isFinite(r.a.deposit_median)` 추가 + `maxV` 가 유한·양수가 아니면 `표시할 값 없음 — …` 문구(`:2524-2534`). `deposit_median = null` 주입 시 `width="NaN"` **0건** |

**전수 재현 결과 (커밋 `3316a3f`)**

```
== 평가 건수 ==   policy_evals 453600 · notice_evals 1240 · ratio_evals 279
== 배지 발생 ==   {'pending': 55377, 'approx': 11907}
== 오라클 불일치 == 0 종
== 불변식 위반 == 0 종            RESULT: PASS      (1차: 불변식 7종 41,868건 — R4 참조)
== 견고성 ==      480 시나리오 · throw 0 · 누출 0    (1차: 누출 63)
== 문구·구조 단정 == 74항목 · 통과 74 · 실패 0        (1차: 73항목 · 실패 1)
```

**회귀 확인** — 화면 계층 계측을 합성 데이터(공고 14건·시세 카드 6개·예산 입력) 위에서 다시 돌렸다.
`375 · 414 · 768 · 1100 · 1200px × 5탭 = 25조합` 전부 `scrollWidth == clientWidth`(body 가로 스크롤 0), 스크롤 컨테이너 밖 넘침 0, 텍스트 클리핑 0.
콘솔 에러 **0**, `performance.getEntriesByType("resource")` = **0건**(전 조합), 본문 텍스트 `NaN`/`undefined`/`Infinity`/`[object` **0건**.
즉 Q1·Q2·Q5·Q25 는 인쇄 CSS·`normCond` 변경에도 회귀가 없다.

> 1차 라운드 계측 스크립트에 있던 오탐 하나를 함께 고쳤다 — 조상 사슬을 훑을 때 첫 `overflow:hidden` 조상에서 멈추던 탓에
> `.pbar{overflow:hidden}`(막대 채움 클립) 안쪽 `<i>` 가 상위 `.tradewrap`(가로 스크롤)을 못 보고 7건 오탐이 났다.
> 사슬 전체를 훑고 텍스트 클리핑은 요소 자신의 `scrollWidth` 로 따로 보게 바꾼 뒤 0건이 됐다.

## R3. `hold` 렌더 확인 (SPEC `5e3f819`)

**(a) 테스트 데이터 주입** — `diff.collector_failures` 에 `fail`(myhome) · `hold`(lh) · `skip`(policy) 한 건씩.

신선도 바 — 3색·3문구 구분 확인 (`site2_fresh_hold_1200.png`)

| status | 줄 클래스 | 태그 | 본문 |
|---|---|---|---|
| `fail` | `row fail` (`--hi`) | `실패 · 반자동` (`tag-high`) | `직전 성공 2026-09-02 07:01 (34시간 전) · 0건` + 사유 |
| `hold` | `row warn` (`--mid`) | `보류 · 반자동` (`tag-mid`) | `0건 수집 — 마감 판정 보류 · 직전 5건 유지` + 사유 |
| `skip` | `row off` (`--fg-3`) | `반자동` (kind 원값, 승격 없음) | `정리 2026-09-03 · 이번 실행 건너뜀` + 사유 |
| `skip`(private) | `row off` | `—` | `수집 안 함 — 검색 링크만 제공` (전용 문구 유지) |

탭5 ⑤ — 3종 구분 확인 (`site2_news_hold_1200.png`)

```
⑤ 수집 실패  3건
  ⏸  LH 분양임대공고문 (부산) — 0건 수집 — 마감 판정 보류      (.news-item.is-warn / --mid)
     사유: LH 목록이 0건을 돌려줬습니다 … · 마지막 성공 2026-09-03 16:37
  —  신혼부부 정책 기준 — 이번 실행 건너뜀                      (.news-item.is-off  / --fg-3)
     사유: fixture 모드 — 정책 페이지 fetch 생략 · 마지막 성공 2026-09-03 14:29
  ✕  마이홈포털 공공주택 모집공고 — 수집 실패                    (.news-item.is-fail / --hi)
     사유: HTTP 500 — 마이홈 API 응답 오류 · 마지막 성공 2026-09-02 07:01
```

- 분기는 `FAILURE_STATUS` 표(`:1155-1162`) 경유이고 `status` 가 없는 옛 데이터는 `fail` 로 폴백한다 — enum 밖 값에서 `undefined` 가 새지 않는다.
- 상단바 수집 상태는 `2026-09-03 16:37 · 수집 실패 1` — `hold`·`skip` 은 실패 카운트에 넣지 않는다. `collectors[].status === "fail"` 만 세므로 정확하다.
- `hold` 의 정본은 `diff.collector_failures` 이고 `collectors[].status` 는 `ok` 로 남는다(SPEC `5e3f819`). `holdOf(key)`(`:1580-1584`)가 그것을 읽고, `collectors[].status === "hold"` 로 직접 오는 경우도 함께 받는다 — 양쪽 경로 확인.
- 인쇄에서도 hold 줄이 `보류 · 반자동` 태그와 테두리를 유지한다(`site2_printemul_homes.png`).

**(b) 실데이터 경로** — `python collect.py --fixture --fixture-scenario lh_zero && python build.py`

```
경고: LH 0건 수집 — 마감 판정을 보류하고 직전 5건을 유지한다
완료 — 공고 5건 / 실거래 집계 31조합 / 신규 0건 / 마감 0건
snapshot_diff.collector_failures[0] = {"key":"lh","status":"hold",
   "error":"0건 수집 — 마감 판정 보류 · 직전 5건 유지","last_success":"2026-09-03T16:48:08+09:00"}
notices.json = 5건 (전부 LH) · closed_notices = 0
build.py … 경고 0건 · 런타임 스모크 통과
```

빌드 산출물에서 신선도 바 LH 줄 = `row warn` + `보류 · 반자동`, 탭5 ⑤ = `⏸ … — 0건 수집 — 마감 판정 보류`.
**즉 hold 는 실데이터 경로에서도 화면에 뜬다.** 다만 그 줄의 건수 표기가 틀렸다 → 새 결함 #9.

**원복** — `python collect.py --fixture && python build.py` 후 남은 차이는 타임스탬프 8종과 `meta.collectors[].duration_ms`(측정 잡음)뿐임을 타임스탬프 정규화 대조로 확인하고, 지시대로 `git checkout -- data site` 실행. 원복 후 `site/index.html` sha256 앞 16자 = `61498245b6932841` (재검수 시작 시점과 동일), `git status` 에 `data/`·`site/` 변경 **0건**.

## R4. 디자이너가 남긴 두 판단에 대한 결론

**(a) `Q16_approx_reason_no` · `Q31_pending_income_reason_no` 41,868건 — 주장 타당. 오라클을 조였다.**

디자이너 주장이 맞다. SPEC §3-2 결합 2단은 "official 이고 **근사값이 아닌** 불가 사유가 하나라도 있으면 불가"이고, D11·DESIGN_SPEC §2-2-2 는 근사값 강등을 **기준 단위**로 규정하며 그 실측 예시가 바로 `불가 — 소득 … / 총자산 … / 유주택` 이다. 1차 보고서 §6-1 도 같은 결론을 냈지만 **오라클 코드는 조이지 않고 남겨 뒀다** — 그게 이번에 41,868건을 그대로 다시 세게 만들었다. 검수자 잘못이다.

`docs/qa/oracle_site_compare.py` 를 고쳤다(검사 축을 "카드 판정"에서 **"불가 사유 목록의 구성"**으로 이동):

```python
# 화면 사유의 `참고:` 앞부분(= 하드 불가 사유)의 항목 수가
# 독립 오라클이 계산한 하드 사유 수와 같아야 한다.
hard_part = why.split(' / 참고: ')[0]
n_shown = len([s for s in hard_part.split(' / ') if s.strip()])
n_exp   = len(exp.get('reasons') or [])
if n_shown != n_exp: -> Q16Q31_hard_reason_count 위반
```

이 형태가 1차 판보다 **더 엄격하다** — 게이트 대상 사유가 하드로 새면 개수가 늘고, 하드 사유가 삼켜지면(Q32) 개수가 줄어 양쪽을 다 잡는다. 453,600 판정에서 **위반 0**. 아울러 `Q33_no_note` 를 `cond` 뿐 아니라 **`no` 판정까지 확장**해 결함 #5 의 재발을 상시 감시하게 했다.

> **SPEC 쪽 권고(화면 계층 몫 아님)**: §4 Q16·Q31 의 문장은 여전히 "배지가 붙은 **판정**에서 불가 0건" 으로 읽혀 다음 검수자가 같은 오탐을 반복할 소지가 있다. "근사값·완화예정 **사유**가 불가 사유 목록에 남지 않음" 으로 조이는 편이 안전하다(1차 보고 §6-1 과 동일 권고).

**(b) Q7 이 `exclusion_rules[].input:"noHome"` 에 걸린 것 — 주장 타당. 오탐이다. 오라클을 조였다.**

`data/meta.json` 의 `"input": "noHome"` 은 D19 가 **키워드 하드코딩을 막기 위해 `config.json` 으로 뺀 규칙표의 축 식별자**이고 사용자의 답(`"yes"`/`"no"`)이 아니다. Q7 이 막는 것은 개인 조건의 **값**이므로 축 이름은 대상이 아니다. (1차 라운드에서 통과했던 이유는 그때 `collect.py` 가 `meta.json` 에 `exclusion_rules` 를 쓰지 않아 `build.py` 가 `config.json` 에서 복사해 넣었기 때문이고, DEF 수정으로 `collect.py` 가 직접 쓰게 되면서 드러났다.)

`docs/qa/oracle_site_assert.js` 의 Q7 검사를 **키:값 쌍 15패턴**으로 바꿨다 — `"deposit"\s*:\s*-?\d` · `"noHome"\s*:\s*"(yes|no)"` · `"marry"\s*:\s*"\d{4}-` · `"dual"\s*:\s*(true|false)` · `hmt\.cond` · `"savedAt"\s*:` 등. 결과 **10파일 × 15패턴 = 0건**. 아울러 축 이름의 출현 위치를 별도 항목으로 **기록**해 다음 검수자가 다시 오탐하지 않게 남겼다(`meta.json:"input": "noHome"/"input": "householder"`).

## R5. 새 결함

| # | 심각도 | 파일:줄 | 문제 | 재현 | 권고 |
|---|---|---|---|---|---|
| 9 | 중간 | `site/index.html:1616-1622` (`renderFresh` 의 `hold` 분기) | 신선도 바 hold 줄이 `직전 **0건** 유지` 라고 **사실과 다르게** 적는다. `num(c.item_count)` 를 쓰는데 `collectors[].item_count` 는 **이번 회차 수집 건수(0)** 이고 "직전 유지 건수"가 아니다. 실제로는 `notices.json` 이 5건을 유지했고, **같은 줄의 `.why`(= collect.py 가 준 `error`)는 `직전 5건 유지` 라고 적어 한 줄 안에서 자기모순**이다. 탭2 목록·탭 배지도 5건을 보여줘 3중으로 어긋난다. hold 는 "출처가 0건을 돌려줬지만 직전 데이터를 지키고 있다"를 알리려고 만든 상태인데, 화면은 그 반대(직전분도 0건)로 읽힌다 — 원칙 3·6 이 막으려는 오인이다 | `python collect.py --fixture --fixture-scenario lh_zero && python build.py` → 신선도 바 2번째 줄: `LH 분양임대공고문 (부산) │ 0건 수집 — 마감 판정 보류 · 직전 0건 유지 │ 0건 수집 — 마감 판정 보류 · 직전 5건 유지 │ [보류 · 반자동]`. 같은 화면의 `신규 · 최근 7일` = 5건, 탭 배지 `추천 주거 5`. 증적 `docs/qa/site2_hold_itemcount_bug.png`, `docs/qa/site2_real_hold_lhzero.png` | `item_count` 대신 **유지된 실제 건수**를 센다 — 예: `DATA.notices.filter(function(n){ return n.source === "LH"; }).length`. 출처↔`source` 매핑을 화면에 새로 만들지 않으려면 건수 문구를 아예 빼고(`0건 수집 — 마감 판정 보류`) 건수는 `.why`(collect.py 의 `error`)에만 맡기는 편이 안전하다. `collect.py` 가 유지 건수를 별도 필드(`retained_count`)로 주는 것이 가장 깔끔하다 — 그건 수집 계층 몫 |
| 10 | 낮음 | `site/index.html:1616-1622` | hold 줄의 `.v` 와 `.why` 가 같은 문장으로 시작해 사실상 두 번 읽힌다 — `.v` = `0건 수집 — 마감 판정 보류 · 직전 0건 유지`, `.why` = `0건 수집 — 마감 판정 보류 · 직전 5건 유지`. 1차 결함 #6(민간 줄 `.v`/`.why` 중복)과 **같은 계열이 hold 분기에서 재발**했다. `.why` 폴백(`hold.error || c.note || "출처가 0건을 돌려줬습니다 …"`)이 `hold.error` 를 먼저 보는데 그 값이 `.v` 와 겹치는 문장이다 | 위와 같은 재현. `docs/qa/site2_hold_itemcount_bug.png` 2번째 줄 | `.v` 는 상태·건수만(`0건 수집 — 마감 판정 보류`), `.why` 는 **왜 보류하는지**만(`출처가 0건을 돌려줬습니다. 목록이 실제로 비었는지 출처 장애인지 알 수 없어 마감 판정을 하지 않습니다.`) 쓰게 역할을 나눈다. `hold.error` 가 상태 문구를 반복하면 폴백 문구를 쓰는 편이 낫다 |

## R6. 육안 확인 필요 (1차와 동일, 갱신분만)

1. **실제 프린터 흑백 출력** — 인쇄 대비 이중화(배경 강제 + 1px 테두리)는 CSS·계측으로 확인했고 이번에 `hold` 줄(`--mid` 배경 + 테두리)이 추가됐다. 배경을 빼는 드라이버에서 `fail`/`hold`/`skip` 3색이 종이에서 구분되는지는 사람이 봐야 한다 — **hold 가 새로 생겼으므로 1차보다 확인 가치가 커졌다.**
2. **A4 실제 페이지 나눔** — `site2_print_{homes,stations,news,input}.pdf` 4종을 넘겨 `.trade-sum` 2열 접힘이 페이지 경계에서 쪼개지지 않는지. 폭은 계측으로 확인했으나 높이·나눔은 PDF 렌더러(`pdftoppm`)가 이 환경에 없어 자동 확인하지 못했다.
3. **실기기 375px 터치 스크롤** — 1차와 동일.
4. **`prefers-color-scheme` 실제 전환 시 번쩍임** — 1차와 동일. 다크 증적 `site2_dark_homes_1200.png`.
5. **GitHub Pages 배포본 외부 요청 0건** — 1차와 동일(로컬 `file://` 에서 0건 확인).

## R7. 다음 단계 함정 3개 (갱신)

1. **결함 #9 를 "직전 건수"로 고칠 때 출처↔`notices[].source` 매핑을 화면에 새로 만들지 마라.** `collectors[].key`(`lh`)와 `notices[].source`(`LH`)는 다른 축이고, 화면이 그 대응표를 갖는 순간 D8("화면 분기는 `key` 로만")이 무너진다. `collect.py` 가 `retained_count` 를 주는 쪽이 정답이다.
2. **`13역 인근` 기본값은 여전히 대부분을 가린다.** 결함 #1 은 "부산 전역으로 전부 볼 수 있다"까지 고쳐졌지만 `notices[].station_ids` 는 실데이터에서 아직 전부 빈 배열이어서 기본 상태에서는 5건 중 1건만 보인다. 공고↔역 매핑(수집 계층)이 들어오기 전까지 **기본 지역 필터를 `부산 전역` 으로 둘지**는 사용자 결정 사항이다 — 화면이 임의로 바꾸면 SPEC §2 탭2 2-3("기본값은 13역 인근")을 어긴다.
3. **`hold` 는 SPEC 상 "⑤ 수집 실패" 섹션에 들어간다.** `5e3f819` 가 그렇게 정했고 구현도 그렇지만, 섹션 제목이 3종(실패·건너뜀·보류)을 포괄하지 못해 `보류 3건` 이 `수집 실패 3건` 으로 세어진다. 화면 결함이 아니라 **SPEC 문구 문제**이므로 다음 SPEC 개정에서 제목을 `⑤ 수집 상태 알림` 류로 넓히는 것을 검토하라. 화면이 먼저 제목을 바꾸면 명세와 어긋난다.

## R8. 재검수 증적

| 파일 | 내용 |
|---|---|
| `site2_fresh_hold_1200.png` | 신선도 바 fail/hold/skip 3색·3문구 + `부산 전역` 에서 실공고 4건 복귀 |
| `site2_news_hold_1200.png` | 탭5 ⑤ 3종(`⏸`/`—`/`✕`) 구분 |
| `site2_homes_1200.png` · `site2_stations_1200.png` | 합성 공고 14건 · 예산 2축 · 시세 6카드 (라이트 1200px) |
| `site2_dark_homes_1200.png` | 다크(`data-theme="dark"` 주입 사본) |
| `site2_375_{homes,stations,news}.png` | 정확한 375px 렌더(iframe 375px 랩퍼) |
| `site2_printemul_{homes,stations,input}.png` | **A4 본문폭 703px** 인쇄 레이아웃 — 결함 #3·#4 해소 증적 |
| `site2_print_{homes,stations,news,input}.pdf` | `--print-to-pdf` 실 PDF 4종 |
| `site2_real_hold_lhzero.png` | `--fixture-scenario lh_zero` 실데이터 경로의 탭5 hold |
| `site2_hold_itemcount_bug.png` | **새 결함 #9·#10** — `직전 0건 유지` vs `직전 5건 유지` vs 목록 5건 |

오라클 6종은 1차와 같은 파일이며 이번에 `oracle_site_compare.py`(Q16/Q31/Q33 검사) · `oracle_site_assert.js`(Q7 검사) 두 개를 R4 결론대로 고쳤다. `QA_ROOT` 로 임의 커밋 스냅샷을 대상으로 돌릴 수 있다.

## R9. `git status --short` (재검수 종료 시점)

```
 M docs/qa/oracle_site_assert.js
 M docs/qa/oracle_site_compare.py
?? docs/qa/site2_375_homes.png
?? docs/qa/site2_375_news.png
?? docs/qa/site2_375_stations.png
?? docs/qa/site2_dark_homes_1200.png
?? docs/qa/site2_fresh_hold_1200.png
?? docs/qa/site2_hold_itemcount_bug.png
?? docs/qa/site2_homes_1200.png
?? docs/qa/site2_news_hold_1200.png
?? docs/qa/site2_print_homes.pdf
?? docs/qa/site2_print_input.pdf
?? docs/qa/site2_print_news.pdf
?? docs/qa/site2_print_stations.pdf
?? docs/qa/site2_printemul_homes.png
?? docs/qa/site2_printemul_input.png
?? docs/qa/site2_printemul_stations.png
?? docs/qa/site2_real_hold_lhzero.png
?? docs/qa/site2_stations_1200.png
```

**`docs/qa/` 외 변경 0건.** `collect.py`/`build.py` 를 fixture 시나리오 확인에 실행했으나 `git checkout -- data site` 로 원복해 `data/`·`site/` 는 `HEAD`(`3316a3f`)와 동일하다(`site/index.html` sha256 앞 16자 `61498245b6932841`). 소스·명세·목업은 손대지 않았고 커밋하지 않았다.
