# hometrack 개발 착수 전 재검수 보고 (기획·디자인·하네스)

- **검수일**: 2026-09-03
- **검수 대상**: `docs/SPEC.md` v1.1 · `docs/DATA_SOURCES.md` · `docs/DESIGN_SPEC.md` v1.1 · `DESIGN.md` · `mockup/index.html` · `CLAUDE.md` · `.claude/agents/*` · `.claude/skills/hometrack-handoff`
- **검수 방식**: 문서 전량 독해 + 목업 JS 추출 실행(Node, 판정 함수 극단값 그리드 81,648 조합) + 조사 문서의 핵심 사실 4건 웹 재확인(출처·확인일 병기)
- **성격**: 기획·디자인 검수 2차. 개발은 미착수 상태 유지. 파일 수정 없음(이 보고서만 추가)

---

## 판정: **조건부 GO — SPEC v1.2 개정 후 착수**

판정 불변식 4개(비official 불가 금지 / 근사값 불가 금지 / 공고 불가 승계 금지 / `linked_policy_id` null → 조건부)는 목업에서 **전수 검증 위반 0건**으로 지켜졌다. 문서 규율과 원칙은 그대로 유지할 가치가 있다.

그러나 개발에 들어가면 그대로 굳어질 결함이 세 층에 있다.

1. **조사 결론 자체가 뒤집힐 것 2건** — LH 공고 출처를 잘못된 API로 결론냈고, 2026-06 소득기준 완화 발표가 반영되지 않았다.
2. **판정 규칙의 공백 3건** — 2인 가구 소득 가산(+10%p)이 스키마에 없어 **기본 사용자(2인)에게 잘못된 "불가"가 난다.** 기혼 7년 판정식이 없다. "예산 내 비율"을 만들 데이터가 스키마에 없다.
3. **목업을 지시대로 승계하면 백지가 되는 크래시 2곳** 포함 목업 결함 30건.

아래 §1(치명·높음)을 SPEC v1.2 + 목업 수정으로 반영한 뒤 착수하면 된다. 대부분 문서·목업 수정이며, 사용자 결정이 필요한 것은 §5의 3건이다.

---

## 1. 결함 표 — 기획·조사 (SPEC / DATA_SOURCES / DESIGN_SPEC)

| # | 심각도 | 위치 | 문제 | 근거 | 권고 |
|---|---|---|---|---|---|
| P1 | **치명** | DATA_SOURCES §A-1·§D-2, SPEC §3-5 "LH 메타데이터 전용", CLAUDE.md §4-9 | **LH 출처로 조사한 API가 잘못됐다.** 조사한 15058449는 "청약센터 **공지사항**(게시판)" API다. LH에는 별도로 **"분양임대공고문 조회 서비스"(15058530, `apis.data.go.kr/B552555/lhLeaseNoticeInfo1/lhLeaseNoticeInfo1`)** 가 있고, 요청에 `CNP_CD`(지역코드)·`UPP_AIS_TP_CD`(06=임대주택)·`PAN_SS`(공고중/접수중/접수마감)·`PAN_NT_ST_DT`·`CLSG_DT`(마감일), 응답에 `AIS_TP_CD_NM`(행복주택 등 세부유형)·`PAN_NM`·`CNP_CD_NM`(지역명)·`PAN_SS`·`DTL_URL`(공고 상세 URL)이 있다. 자동승인, 개발계정 10,000건/일. 짝 API "분양임대공고별 상세정보 조회"(15057999, `lhLeaseNoticeDtlInfo1/getLeaseNoticeDtlInfo1`, `PAN_ID` 필수)는 주택형/필지별 공급정보를 준다 — **임대보증금·월임대료·전용면적 필드 포함 여부는 페이지 표에 없어 실호출로 확인해야 한다** | data.go.kr 15058530 · 15057999 페이지 (확인 2026-09-03) | **DATA_SOURCES 재조사 + SPEC §3-5 개정.** LH는 "제목만 감지, 전국 게시판 노이즈"가 아니라 **부산 필터 + 유형 + 마감일 + 상세 URL이 있는 정형 공고**로 바뀐다. 상세 API에 금액이 있으면 LH 카드가 `detailed`로 자동 채워질 수 있어 탭2의 성격이 달라진다. 활용신청은 자동승인이므로 사용자가 **오늘 신청 → 연구자가 실호출로 스키마 확정** 가능. 15058449(공지사항)는 후보에서 제외 |
| P2 | **치명** | SPEC §3-6 `policies.criteria.income {pct, pct_dual}`, §3-2 소득 판정식 | **가구원수별 가산이 스키마에 없다.** 행복주택 공식 원문: "계층별 소득기준에 **1인 가구 20%p, 2인 가구 10%p 각각 가산**". 즉 2인 신혼은 110%(맞벌이 130%), 3인 이상은 100%(120%). 스키마는 `pct`/`pct_dual` 2개뿐이라 둘 중 하나만 표현된다. 목업 샘플 `p001`은 100/120 → **2인 가구(이 도구의 기본값) 예비신혼부부가 110%가 아닌 100%에서 걸려 잘못된 "불가"를 받는다.** 원칙 9가 막으려는 바로 그 사고이며 `confidence: official`이라 어떤 게이트에도 걸리지 않는다. 국민임대·통합공공임대도 같은 가산 체계 | myhome.go.kr 행복주택 입주자격 원문 (확인 2026-09-03); `mockup/index.html:1023` p001 `pct:100, pct_dual:120` | **SPEC §3-6 개정**: `income.pct_adjust_by_household: {"1": 20, "2": 10}` (또는 `pct_by_household` 표) 신설. §3-2 판정식에 "적용비율 = 기본비율 + 가구원수 가산" 추가. §4 검수 항목에 "2인 가구 기본 입력에서 행복주택 기준액이 110%/130% 값으로 표시됨" 추가 |
| P3 | **높음** | DATA_SOURCES §B-1·§B-2, SPEC §7 | **2026-06-09 정부 "결혼 친화 제도 개선" 발표가 미반영.** 행복주택 맞벌이 신혼 소득기준 월 763만→**939만원**(≈2인 160%), 통합공공임대 맞벌이 신혼 우선공급 462만→630만원·일반 798만→924만원, 미혼 입주 후 결혼 시 1회 재계약 허용, 버팀목 가산금리 0.3→0.15%p. 기사는 "실제 적용 시점과 세부 요건은 후속 절차를 거쳐 확정"이라 **시행 여부는 미확정** | 서울신문 2026-06-10, 하우징포스트 2026-06-10 (확인 2026-09-03) | **DATA_SOURCES 추가 조사**: 공공주택특별법 시행규칙 개정·시행 여부 확인. 시행 전이면 `policies.json`에 `note`로 남기고 화면 정책 카드에 "완화 예정 — 확정 시 갱신" 한 줄. 시행됐으면 값 갱신. 어느 쪽이든 **현재 조사값(120%/130%)을 official로 굳혀 불가를 내면 위험** |
| P4 | **높음** | DATA_SOURCES 전체, SPEC §3-6 `income_tables.median_income` | **기준중위소득 표가 조사되지 않았다.** 통합공공임대(`basis: median_pct`)는 기준중위소득 기준인데 DATA_SOURCES에 값이 한 줄도 없다. 개발 착수 시 통합공공임대는 전부 `조건부 — 기준액 미확보`. 2026년 값은 보건복지부 고시로 공표돼 있다(2인 4,480,645원 · 3인 5,718,091원 · 4인 6,929,885원, 6.51% 인상) — 확보가 쉬운 official 자료 | 보건복지부 보도자료 "2026년도 기준 중위소득 6.51% 인상" (확인 2026-09-03) | **DATA_SOURCES §D-4 추가 + `income_tables.median_income` 채움.** CLAUDE.md §9 잔여 조사 목록에도 누락됨 → 추가 |
| P5 | **높음** | SPEC §3-2, §3-6 `criteria.marriage_within_months`, 탭1 입력 | **기혼자 판정식이 없다.** `marriage_within_months`(혼인 7년)는 스키마에만 있고 판정식·입력 수단이 없다. 탭1은 "혼인 예정일" 단일 필드. 목업 실측: 혼인일 2015-01-01(11년 기혼) → 행복주택 **"해당"**. 이 도구는 결혼 후에도 계속 쓰이므로 반드시 만난다 | `mockup/index.html:1294-1305` (`marriage_within_months` 읽는 코드 0건) | **SPEC §3-2 개정**: 혼인(예정)일이 과거면 혼인기간 = 오늘 − 혼인일, `≤ marriage_within_months`면 충족, 초과면 official일 때 불가. 탭1 라벨을 "혼인(예정)일"로 하고 과거 날짜를 기혼으로 해석 |
| P6 | **높음** | SPEC §3-1 "예산 내 비율", §3-6 `trades.aggregates` | **"예산 내 비율 = 예산 내 계약 건수 / 전체 건수"를 계산할 데이터가 스키마에 없다.** 집계는 `count`+분위수 3개뿐이고, 예산은 브라우저에만 있어 `collect.py`가 미리 셀 수도 없다(원칙 5). 목업은 p25/p50/p75 조각선형 CDF 근사(계수 1.6/0.02/0.98 하드코딩)로 대체했고 그 근사값이 "내 예산 이내 61%"로 확정값처럼 표시된다 | `mockup/index.html:1191-1210` | **SPEC §3-6 개정 (착수 전 결정)**: `aggregates[].deposit_hist: [{lo, hi, count}]` 보증금 히스토그램 버킷(예: 500만원 단위)을 실어 브라우저에서 정확 계산. 또는 "근사값"임을 화면에 명시. 결정 없이 개발하면 근사가 그대로 굳는다 |
| P7 | **높음** | SPEC §3-5 자동화, CLAUDE.md §3 | **공개 저장소의 Actions 로그는 공개다.** `urllib` 예외 문자열·`meta.collectors[].error`·디버그 print에 요청 URL이 들어가면 `serviceKey`가 **로그와 커밋된 JSON에 남는다.** SPEC은 "키를 저장소에 넣지 않는다"만 말하고 이 경로를 막지 않았다 | SPEC §3-5, `.gitignore` | **SPEC §3-5 규칙 추가**: 에러 문자열은 `serviceKey=` 이후를 마스킹한 뒤 저장·출력. 요청 URL을 로그에 찍지 않음. §4에 "`data/*.json`·Actions 로그에 키 패턴 0건" 항목 |
| P8 | **높음** | SPEC §3-5 LH 수집 규칙 | (P1이 유지될 경우) LH 공지사항 API는 **전국 게시판**("의정부 예비자 추첨 결과…")이라 부산 필터가 없어 새 소식이 매일 전국 공지로 넘친다. SPEC 자신이 경계한 경보 피로 | DATA_SOURCES §D-2 샘플 | P1로 API를 바꾸면 `CNP_CD` 필터로 해소. 남길 경우 제목·부서 "부산" 키워드 필터 규칙을 명문화 |
| P9 | 중간 | SPEC §2-1 "신규 = 최근 7일", §3-6 `notices` | `first_seen` 필드가 SPEC 스키마에 없다. DESIGN_SPEC §7-2가 "목업 확장 필드"로 자백했고 SPEC은 미반영. `diff.new_notices`는 하루치라 7일 창을 만들 수 없다 | DESIGN_SPEC §7-2 | **SPEC §3-6 개정**: `notices[].first_seen: string(YYYY-MM-DD)` 신설, `notices_prev.json`에서 승계·보존 규칙 명시 |
| P10 | 중간 | SPEC §3-6 `meta.collectors[]` | 출처별로 다른 표시(LH 2줄, 실패 배너)를 요구하면서 **줄을 식별할 안정키가 없다.** 목업은 한국어 `name` 문자열로 분기한다(`c.name === "공고 · LH"`). `collect.py`가 이름을 바꾸면 SPEC §2 요구가 소리 없이 사라진다 | `mockup/index.html:1397,1404,1408,1871,2378` | **SPEC §3-6 개정**: `collectors[].key: "myhome"\|"lh"\|"bmc"\|"trades"\|"policy"\|"private"` 신설. 목업이 쓰는 `note`/`list_url`/`registered_at`/`detail_registered_at`도 정식화. `kind` enum에 `"none"` 추가(민간 매물 줄) |
| P11 | 중간 | SPEC §3-1 월세 공고 AND 조건 | "월세 공고는 `rent_min <= 월세상한` AND"의 적용 조건이 **공고 성질인지 사용자 거래유형 선택인지** 불명. 공공임대 공고는 전부 월임대료가 있으므로 목업 해석(사용자가 월세를 골라야 적용, 기본은 전세만)에서는 **기본 상태에서 월세 축이 통째로 꺼진다.** `rent_max` 2단 표기도 미정의 | `mockup/index.html:1181-1185` 실측: 월임대료 28~35만원 공고가 상한 30에서 "전 평형 가능" | **SPEC 개정**: 공고 판정은 거래유형 선택과 무관하게 보증금·월임대료 두 축 항상 적용. 월세 상한 미입력이면 보증금만 판정 + 사유에 "월임대료 상한 미입력" |
| P12 | 중간 | SPEC §3-1 표 4행 | "`deposit_min`·`deposit_max`가 null"이 **둘 다인지 하나라도인지** 불명. 목업은 한쪽만 null이면 다른 값을 대입 → `min=null, max=6200, 가용 5000`이 **"예산 밖"으로 접혀 사라진다.** 하한을 모르는데 탈락 처리 | `mockup/index.html:1176-1179` | **SPEC 개정**: `deposit_min`이 null이면 무조건 "금액 미표기". 하한이 있고 상한만 null이면 하한으로만 판정 + "상한 미표기" 사유 |
| P13 | 중간 | SPEC §3-2 원칙 9 | 불가 사유가 **여러 개 동시 성립할 때 우선순위**와 근사값 강등의 **단위(기준별인지 정책 전체인지)** 미정의. 목업은 첫 `no`만 채택 + 정책 전체 강등 → 유주택(하드 불가)이 근사값 소득 사유에 삼켜져 사유 텍스트에 안 나온다 | `mockup/index.html:1310-1319` | **SPEC 개정**: 근사값 강등은 기준 단위. 근사값 아닌 official 불가 사유가 하나라도 있으면 불가, 사유는 그 기준. 사유가 복수면 전부 나열 |
| P14 | 중간 | SPEC §3-5 diff, §3-6 `snapshot_diff` | `closed_notices` 정의 불명 — `apply_end` 경과인지, 직전분에 있다가 사라진 공고인지. `meta_only`(접수기간 null) 공고는 어느 쪽으로도 "마감"이 안 된다. 탭2 마감 임박은 D-30 재계산, 탭5는 `diff.closing_soon` → 두 화면 건수가 어긋날 수 있고 `closing_soon[].dday`는 미사용 | `mockup/index.html:1786 vs 2326` | **SPEC 개정**: `closed` = `apply_end < today` **또는** 출처 목록에서 소멸(`disappeared: true` 별도 표기). 마감 임박 정본은 한쪽으로 |
| P15 | 중간 | DATA_SOURCES §D-3 | welfarenote 표(2인 5,477,003 / 3인 7,626,973)를 "신뢰도 낮음"으로 기각했으나, 그 값은 **2025년도 적용(2024년 실적) 표로 정합**하고 D-3의 값(2인 5,866,270 / 3인 8,168,429)은 jpdc가 "**2026년** 원" 표로 게시한 값이다. 즉 두 표는 연도가 다를 뿐 둘 다 맞을 가능성이 크다. `year_label`을 "2025년도 적용기준(2024년 실적)"(SPEC 예시)으로 붙이면 **틀린 라벨**이 된다 | jpdc.co.kr 소득기준 표 "전년도 도시근로자 월 평균 소득기준(2026년, 원)" (확인 2026-09-03) | `income_tables.urban_worker.year_label`을 **"2026년도 적용기준(2025년 실적)"** 으로 확정하되 원문 한 곳에서 병기 문구를 직접 확인. D-3의 "미채택" 기록에 이 재해석을 덧붙임 |
| P16 | 중간 | SPEC §3-6 `policies.content_selector`, §3-5 변경 감지 | `content_selector`(CSS 선택자)를 표준 라이브러리만으로 구현해야 한다. `html.parser`는 선택자 엔진이 없다. busan.go.kr류는 UA 차단·JS 렌더 가능성도 있다 | CLAUDE.md §3 "표준 라이브러리만" | 선택자를 `#id` 단일 형식으로 제한하거나 `content_selector` → `content_id`로 축소. 실패 시 `semi` 유지 + 실패 표시(원칙 4) |
| P17 | 중간 | SPEC §3-5 실거래 호출 수 | "회당 18회 호출"은 페이징 미고려. 실거래 API는 `numOfRows`/`pageNo` 기본 10건이라 구·월 단위로 수백 건이면 다중 페이지. 첫 실행은 12개월 전체(108회+페이지) | DATA_SOURCES §A-4 | `numOfRows=1000` 명시, 첫 실행 백필 규칙 추가. 한도(10,000/일) 내이므로 위험은 낮음 |
| P18 | 낮음 | SPEC §3-2 소득 판정식 | 공급형 정책의 공식 기준은 "**전년도** 세대 월평균 **세전** 소득"인데 입력 라벨은 "부부 합산 연소득". 어느 연도·세전 여부가 불명 | myhome.go.kr 원문 "전년도 도시근로자…" | 탭1 라벨·도움말에 "전년도 세전 연소득(부부 합산)" 명시 |
| P19 | 낮음 | SPEC §3-6 `trades.aggregates.jeonse_equiv_median` | 계약별 환산액의 중위인지, 중위값들을 환산한 것인지 미정의 | — | "계약별 환산액의 중위" 로 명시 |
| P20 | 낮음 | SPEC 탭1 "첫 방문 시 기본 탭" | 재방문(해시 없음 + 저장된 조건 있음) 시 기본 탭 미정의 | — | 조건 저장돼 있으면 탭2 |
| P21 | 낮음 | SPEC §4 · CLAUDE.md §2·§9 · ht-qa | §4 항목은 **26개**인데 CLAUDE.md·ht-qa는 "22항목", §9는 "20번 2회 연속 수집"(실제 24번) | SPEC.md:660-685 | 항목 번호를 §4에 부여하고 참조를 번호로 통일 |
| P22 | 낮음 | DESIGN_SPEC §0 "미해결 1건" vs §7-2 "해소됨" / DESIGN_SPEC:913 | 같은 문서 안에서 상충. 913행의 `조건부 — 대상 미표기(공고문 확인 필요)` 문구는 목업 실제 출력(`연결된 정책 없음. 자격 대조 정보 없음`)과 다름 | 목업 실측 | DESIGN_SPEC 두 곳 정리 |
| P23 | 낮음 | DESIGN.md §3 "매물 딥링크 … `rel="noopener"`" / §0 글로벌 규칙 참조 | SPEC·CLAUDE.md는 `noopener noreferrer` + `referrerpolicy`인데 상위 문서(Strict Rule) DESIGN.md가 약한 형태. `~/.claude/design/DESIGN.standalone.md` 참조는 이 PC에 없는 파일(CLAUDE.md "전역 설정 없이 동작" 원칙과 충돌) | — | DESIGN.md §3 문구 강화, 글로벌 참조 삭제 또는 "없어도 무관" 명시 |

## 2. 결함 표 — 목업 (`mockup/index.html`, 개발이 승계할 대상)

검증: 판정 함수(`judgePolicy`/`judgeNotice`/`budgetOf`/`incomeLimitOf`/`ddayOf`)를 Node로 추출 실행. **불변식 4종 81,648 조합 위반 0건.** 아래는 그 외 결함.

| # | 심각도 | 위치 | 문제 | 권고 |
|---|---|---|---|---|
| M1 | **치명** | :1329, :1334, :2050 | `CONF[conf].txt` 폴백 없음. `confidence`가 enum 밖(예: `"Official"`)이면 `TypeError` → `renderAll()`(2431) 첫 호출에서 죽어 `showTab()` 미실행 → **상단바만 남은 백지.** `policies.json`은 수동 파일이라 현실적 | `CONF[conf] \|\| CONF.unverified`(1374 `confHtml`처럼) + build.py enum 검증 실패 시 빌드 중단 |
| M2 | **높음** | :761 + :1572 | `$("btn-sample").addEventListener` null 가드 없음. CLAUDE.md §9 "data-mock-only 3곳 제거"를 그대로 하면 `bindInputs()`(2426)에서 throw → **백지** | 버튼·핸들러(1572-1581)를 한 쌍으로 제거 |
| M3 | **높음** | :2300, :876 | `is_first_run`을 읽는 코드가 없다. 첫 실행 화면은 목업 전용 버튼으로만 도달 → 버튼 제거 시 SPEC §4 첫 실행 항목 무조건 실패 | 2300을 `DATA.diff.is_first_run`으로 배선 |
| M4 | **높음** | :1068 | `wonRange` 하한이 raw 숫자: `"15,000 ~ 2억 4,000만원"`. 화면에 지금 보인다 | 양쪽 `won()` |
| M5 | **높음** | :1176-1179 | P12 (min null → 예산 밖으로 감춤) | P12 |
| M6 | **높음** | :1397, :1404, :1408, :1871, :2378 | P10 (한국어 표시명 분기) | P10 |
| M7 | **높음** | :2237, :1709, :1801, :1896 | `stops_from_base`가 **구서 기준으로 데이터에 구워짐**, 기준역은 탭1에서 변경 가능. 실측 `base=sicheong`: 시청 행이 기준역인데 "8정거장" | 13역 순서 인덱스 차로 런타임 계산 |
| M8 | **높음** | :1191-1210 | P6 (예산 내 비율 근사) | P6 |
| M9 | **높음** | :1294-1305 | P5 (기혼 판정 없음) | P5 |
| M10 | 중간 | :1310-1319 | P13 (첫 `no`만 채택) | P13 |
| M11 | 중간 | :1181-1185 | P11 (월세 축 게이트) | P11 |
| M12 | 중간 | :1090 | `monthsUntil`이 일자 무시(`12-31 → 3개월`) → `pre_marriage_within_months: 3`이 최대 1개월 관대 | 일수 기준 |
| M13 | 중간 | :1046 | `parseDT`가 날짜만(UTC)과 날짜+시각(로컬)을 같이 처리 → KST에서 `future(today) === true`, 음수 오프셋 브라우저에서 D-day 하루 밀림 | 날짜만이면 `T00:00:00` 부착 |
| M14 | 중간 | :590-596 | `@media print` 안에 DESIGN.md에 없는 **hex 리터럴 21개**(4번째 팔레트) | DESIGN.md에 `--print-*` 편입 또는 토큰 사용 |
| M15 | 중간 | :620, :632 | `print-color-adjust: exact`로 배경 강제 — SPEC §1 "배경색 대신 테두리"의 반대. `.tag-*`·`.policy-stale/-changed`는 테두리 폴백 없음 | 전략 하나로 통일 + 테두리 폴백 |
| M16 | 중간 | :28, :58, :83 | `--fg-3`가 DESIGN.md와 다름(라이트 `#6b7789` vs `#7b8798`, 다크 `#8b97ab` vs `#77839a`). 나머지 24개 토큰 일치 | 정본 한쪽으로 |
| M17 | 중간 | :1549, :1585 | 상한 초과 입력 시 `renderAll()`이 입력 중 필드를 비움(`"1000000"` 7번째 키에서 사라짐) | 에러 상태에서 DOM value 유지 |
| M18 | 중간 | :2038, :2076 | `verified_at` 비정상이면 `"최종 확인 (NaN일 전)"` + 90일 경고 무음 | `isNaN` 가드 + 빌드 검증 |
| M19 | 중간 | :2230 | `rent_median` null → 탭4 `"3,000 / null"` 노출 | `num()` 경유 |
| M20 | 중간 | :1347 | `exclusions` 키워드 `"유주택"` 하드코딩, 대조 축 `noHome` 하나. SPEC "키워드 목록은 config.json" 위반 | 키워드↔입력축 매핑표를 config로 |
| M21 | 중간 | :1618 | `appliedPct = dual ? 120 : 100` UI 하드코딩 → 국민임대(70/90) 사용자에게 잘못된 기준액 안내. 원칙 8 위반 | 정책별 비율에서 유도 |
| M22 | 중간 | :1896 vs :1988 | 시세 근거 블록이 사이드 역 필터를 무시 | `UI.stationFilter \|\| COND.stations` |
| M23 | 중간 | :1355 | `linked_policy_id` dangling 참조가 null과 같은 문구 → 매핑 오타가 정상으로 위장 | 별도 사유 + 빌드 시 참조 검증 |
| M24 | 낮음 | :2329 | `dd.d == null`이 `null <= 7` true → 접수기간 미표기 공고가 `--hi` | null 가드 |
| M25 | 낮음 | :1390 | 실패 분기 `KIND[c.kind]` 폴백 없음 → `"실패 · undefined"` | 폴백 |
| M26 | 낮음 | :1764, :2077, :1418, :1833 | `href`에 스킴 검증 없음(`javascript:` 가능). `notices_manual.json`은 수동 입력 | build.py `https?://` 화이트리스트 |
| M27 | 낮음 | :645-650 | ARIA tabs 패턴 없음(키보드 전환 자체는 `<a href>`+`:focus-visible`로 충족) | 선택. `aria-controls`만 추가 |
| M28 | 낮음 | :1782, :1851 | 상단 고정 섹션·facet 건수가 유형/해당만 필터를 무시 | 의도면 SPEC에 한 줄 |
| M29 | 낮음 | :1995 | "마감 포함" 필터가 fold 개폐 외 효과 없음 | 라벨을 "마감된 공고 펼치기"로 |
| M30 | 낮음 | :890 vs `trades` | `refetched_months`가 `meta`와 `trades` 양쪽에 중복 | 한쪽 |

**스키마 불일치 (`var DATA` vs SPEC §3-6)** — `snapshot_diff.json` ↔ `DATA.diff` 이름 불일치 · `diff_history.json`(별도 파일, 14일 배열) ↔ `DATA.diff.history`(중첩 + `is_first_run`·`closing_soon` 누락) · `DATA.stations[]`는 SPEC상 `config.json` 소관(필드명 목업이 발명) · 목업 전용 필드: `notices[].first_seen`, `meta.policy_verified_latest`, `collectors[].note/list_url/registered_at/detail_registered_at`, `policies[].source_changed`(SPEC은 해시 비교로만 판단 → 근거 2중화), `kind: "none"` · 미사용: `closing_soon[].dday`, `criteria.marriage_within_months/age_max/region`, `diff.is_first_run`. **일치 확인**: `notices` 26필드, `aggregates` 12+3, `policies` 13+12+5+3, `income_tables`, `meta.config` 7키, 단위 처리(:1232 `income × 10000 ÷ 12`).

**통과 확인**: 외부 요청 0건(12개 `http` 문자열 전부 데이터·딥링크·인쇄 셀렉터) · 딥링크 역명+거래유형만(:1831), 외부 `<a>` 전부 `noopener noreferrer`+`referrerpolicy` · localStorage 5곳 try/catch + 차단 안내 · 테마 3블록 + head 인라인 · 표 세로선 0 · 375px 컨테이너 스크롤 · 인쇄 숨김/펼침/URL 병기 · `data-mock-only` 3곳 · 빈 상태 3종 · `housing_type` 미혼합 · D-day 7/30 · `sample_min` config 경유 · 승계 사유 정책명 포함 · `pct_dual` null 폴백 · XSS `esc()` 전수.

## 3. 하네스 (`CLAUDE.md` · `.claude/`)

| # | 심각도 | 위치 | 문제 | 권고 |
|---|---|---|---|---|
| H1 | 중간 | CLAUDE.md §9, `docs/qa/` | §9는 "QA 최종 GO, 잔여 결함 0 (12,960 조합 전수 + 독립 오라클)"이라 쓰지만 **`docs/qa/`에는 png 2 · pdf 2만 있고 QA 보고서(`REPORT_*.md`)와 오라클 스크립트가 없다.** ht-qa 지시서가 요구하는 산출물이 저장소에 없어 주장을 재현할 수 없다. 이 검수의 목업 실행에서 결함 30건이 나왔다 | QA 보고서·오라클을 `docs/qa/`에 커밋. 재현 불가한 "GO"는 §9에서 "QA 보고서 미커밋"으로 정직하게 표기 |
| H2 | 중간 | CLAUDE.md §9 다음 할 일 4 | "`data-mock-only` 3곳 제거"를 그대로 수행하면 M2·M3 크래시. 지시 자체가 함정 | "버튼·핸들러·`is_first_run` 배선을 함께" 로 문구 수정 |
| H3 | 낮음 | CLAUDE.md §6, `hometrack-handoff` SKILL 4단계 | 경로 `/c/DEVTool/hometrack` 하드코딩. 이 PC는 `C:/Users/cyh12/hometrack` | "저장소 루트에서" 로 경로 비의존화 |
| H4 | 낮음 | `.claude/agents/ht-developer.md` `model: sonnet` | `build.py`는 190KB 목업의 판정 불변식을 템플릿화하는 작업. 본 검수에서 목업의 미묘한 결함(단위·날짜·문자열 분기)이 다수 나온 점을 보면 상향 권장 | `model: opus` 또는 build.py 작업만 opus 지정 |
| H5 | 낮음 | `.claude/agents/ht-researcher.md` | WebFetch만으로는 data.go.kr 첨부(xlsx) 열람·API 실호출 불가 → P1·마이홈 스키마가 계속 미확인으로 남는 구조. 활용신청은 자동승인 | 사용자가 키 발급 → 연구자에게 실호출 권한(환경변수) 부여 절차를 CLAUDE.md §8에 추가 |
| H6 | 낮음 | `.gitignore` | `.env`, `*.key`는 있으나 로컬 실행 시 생길 `data/*.local.json`·`*.log` 패턴 없음 | 추가 |

## 4. 잘 되어 있어 유지할 것

- SPEC §0 원칙 10개, 특히 원칙 9(불가 금지 게이트)와 §3-2 "불가 비승계" — 목업에서 **전수 검증 위반 0건**으로 실제 구현됐다.
- `income_tables` 가구원수×비율 2차원 구조와 "표에서 직접 조회, 곱셈 금지" 규칙 — 정확하다. P2의 가산만 얹으면 된다.
- 목업의 방어 코드: localStorage 5곳 try/catch, `esc()` 전수, 빈 상태 3종, `sample_min` config 경유, 외부 링크 속성 전수 적용.
- DATA_SOURCES의 "미확인 항목 총괄 목록" 습관. P1·P4는 그 목록의 확장이지 방식의 문제가 아니다.
- 프로젝트 전용 에이전트 5개 + 쓰기 범위 분리 + 작성/검수 분리 원칙.

## 5. 사용자 결정·행동 (기존 3건 + 신규 2건)

| # | 항목 | 왜 사용자만 할 수 있나 |
|---|---|---|
| U1 (기존) | 공공데이터포털 활용신청 — **LH 분양임대공고문 15058530 + 상세 15057999 추가**, 마이홈 15108420, 실거래 3종 | 계정 소유자. 전부 자동승인이라 오늘 가능. 키가 있어야 P1·마이홈 스키마가 확정된다 |
| U2 (기존) | 역↔법정동 매핑 검토 | 생활권 감각 |
| U3 (기존) | 저장소 공개 유지 여부 | 이미 공개 상태. P7(로그 키 유출 방지)을 조건으로 유지 권고 |
| U4 (신규) | **P6 예산 내 비율 방식** — 히스토그램 버킷(정확) vs 근사 표시 | 스키마·수집 로직이 갈린다. 권고: 히스토그램 |
| U5 (신규) | **P3 2026-06 소득기준 완화** — 시행 확인 전까지 화면에 "완화 예정" 표기 여부 | 판정 결과가 달라지는 정책 방향. 권고: 표기 |

## 6. 착수 전 반영 순서 (권고)

1. **조사 재확인 (ht-researcher, U1 이후)**: P1 LH 분양임대공고문·상세 API 실호출로 응답 스키마 확정 → P3 시행 여부 → P4 기준중위소득 표 → P15 `year_label` 확정. DATA_SOURCES §D-4~D-7로 추가.
2. **SPEC v1.2 (ht-planner)**: P2 가구원수 가산 스키마 · P5 기혼 판정식 · P6 히스토그램 스키마 · P7 키 마스킹 · P9 `first_seen` · P10 `collectors[].key` · P11~P14 판정 규칙 명확화 · P1 결과에 따라 §3-5 LH 절 재작성 · §4 항목 번호 부여 + 신규 항목(2인 110% 표시 / 기혼 7년 초과 불가 / 키 패턴 0건 / dangling 참조 / min-null 미표기).
3. **목업 v1.2 (ht-designer)**: M1~M4·M7·M12·M13·M16~M19·M21~M24 수정 + SPEC v1.2 반영(P2·P5·P6·P10~P13). `docs/DESIGN_SPEC.md` 7-2 정리.
4. **QA 증적 커밋 (ht-qa)**: 목업 재검수 보고서 + 오라클 스크립트를 `docs/qa/`에. §9 갱신.
5. 그 다음 CLAUDE.md §9 "다음 할 일" 1번(`config.json`)부터 개발 착수.

---

### 참고 — 이번 검수에서 웹으로 재확인한 출처 (확인일 2026-09-03)

- [한국토지주택공사_분양임대공고문 조회 서비스 (15058530)](https://www.data.go.kr/data/15058530/openapi.do) — 요청 `CNP_CD`/`UPP_AIS_TP_CD`/`PAN_SS`/`PAN_NT_ST_DT`/`CLSG_DT`, 응답 `AIS_TP_CD_NM`/`PAN_NM`/`CNP_CD_NM`/`PAN_SS`/`DTL_URL`, 자동승인
- [한국토지주택공사_분양임대공고별 상세정보 조회 서비스 (15057999)](https://www.data.go.kr/data/15057999/openapi.do) — `PAN_ID`·`SPL_INF_TP_CD`·`UPP_AIS_TP_CD` 필수. 금액 필드는 페이지 표에 없음 → 실호출 확인 필요
- [마이홈포털 행복주택 입주자격 안내](https://www.myhome.go.kr/hws/portal/cont/selectHappyHouseView.do) — "1인 가구 20%p, 2인 가구 10%p 각각 가산", 자산 3억 4,500만 / 자동차 4,542만 (2026년도 적용기준)
- [공공임대주택 포털 소득기준 표](https://www.jpdc.co.kr/housing/public-housing/happy-housing/income.htm?_layout=playout&_view=print) — "전년도 도시근로자 월 평균 소득기준(2026년, 원)" 2인 100% 5,866,270
- [보건복지부 2026년도 기준 중위소득 6.51% 인상](https://www.mohw.go.kr/board.es?mid=a10503000000&bid=0027&act=view&list_no=1487098) — 2인 4,480,645 / 3인 5,718,091 / 4인 6,929,885
- [서울신문 2026-06-10 신혼부부 행복주택 소득 기준 1인 가구 2배로](https://www.seoul.co.kr/news/economy/2026/06/10/20260610008002) · [하우징포스트 2026-06-10](https://housing-post.com/View.aspx?No=4106487) — 763만→939만, 통합공공임대 462→630 / 798→924, 시행 시점 미확정
