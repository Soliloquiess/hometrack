# hometrack 수집·데이터 계층 검수 보고 (2026-09-03)

검수자: `ht-qa` (독립 재현 · 코드 수정 금지 · 쓰기 범위 `docs/qa/` 만)
대상: `config.json` · `collect.py` · `data/*.json` · `data/fixtures/*` · `.github/workflows/daily.yml` · `tools/ingest_proposals.py` · `docs/proposals/*`
기준: `docs/SPEC.md` v1.2 §3-3·§3-4·§3-5·§3-6·§4(Q1~Q56)·§6(D1~D24) · `CLAUDE.md` §4
범위: **수집·데이터 계층만.** 화면은 별도 검수(`REPORT_site_20260903.md`) — 화면 전용 항목은 `범위 밖(화면 검수)` 표기만.
환경: Windows 10 · Python 3.12 · Git Bash · 네트워크 사용 가능(실호출 403 수신 확인)
검수 대상 커밋: `8ac4a07`

> 이 보고서 본문은 검수 에이전트가 텍스트로 반환한 것을 팀 리더가 그대로 저장한 것이다(에이전트의 파일 쓰기가 하네스에 의해 차단됨). 재현 스크립트 `oracle_collect_trades.py`·`oracle_collect_edge.py` 는 검수자가 직접 작성했다.

## 판정: 조건부 GO
fixture 경로의 집계·분류·식별키·마스킹은 독립 오라클과 **불일치 0건**으로 재현됐으나, 상류 API가 **HTTP 200으로 오류·빈 응답을 돌려주는 경우**를 실패로 보지 않아 `status:"ok"` 상태에서 ① 직전 공고 전건이 `disappeared`로 뒤집히고 ② `trades.json`이 빈 집계로 덮이는 **치명 결함 2건**이 재현됐다 — 원칙 4·7 위반.
**GO 조건**: DEF-1·DEF-2·DEF-3·DEF-4 수정 후 재검수.

## 재현 산출물
| 파일 | 내용 |
|---|---|
| `docs/qa/oracle_collect_trades.py` | **독립 오라클.** `collect.py`를 import하지 않고 fixture XML을 따로 파싱해 분류·중위·p25/p75·히스토그램·월별·환산액 계산 후 `data/trades.json`과 전 필드 대조 |
| `docs/qa/oracle_collect_edge.py` | 경계·불변식 단위 오라클. `collect.py` 함수 직접 호출(분류 경계·창 경계·히스토그램·마스킹·오류응답·식별키·마감판정·meta 스키마) |

```
$ python docs/qa/oracle_collect_trades.py
[1] fixture 구간 8개 · 계약 19건 (totalCount 합 19)
[2] 미매핑 계약 1건 · 집계 조합 31개 · 구간 ['202608', '202609']
[3] 표본 5건 미만 조합 28/31 개
[4] 경계 계약 보증금=24000 월세=100 (경계 24000) -> banjeonse
[4] 경계 계약 보증금=23999 월세=100 (경계 24000) -> wolse
조합 31개 대조 완료 — 불일치 0건        # EXIT=0

$ python docs/qa/oracle_collect_edge.py
결과 — NG 10건                          # EXIT=1  (DEF-1~DEF-7·DEF-9·DEF-13·DEF-15 대응)
```

## SPEC §4 항목별 결과 (Q1~Q56)

| Q# | 결과 | 증거 |
|---|---|---|
| Q1 | 범위 밖(화면 검수) | 참고: 사본에서 `build.py` → `site/index.html` 200,474 bytes, 경고 0건, `node smoke_site.js` throw 0 |
| Q2 | 범위 밖(화면 검수) | 참고: `build.py` [5/5] "외부 요청 토큰 9종 전부 0건" |
| Q3~Q6 | 범위 밖(화면 검수) | — |
| Q7 | **부분 통과**(데이터 측) | `grep -rniE "income\|budget\|salary\|소득\|예산\|혼인예정" data/*.json` → 0건 |
| Q8, Q9 | 범위 밖(화면 검수) | — |
| Q10, Q11 | 범위 밖(화면 검수) | 데이터 근거: LH 자동수집분 `deposit_min` 전건 `null`(5건) → D10 "금액 미표기" 경로만 발생 |
| Q12 | 범위 밖(화면 검수) | 데이터 측: `confidence` official 7 / secondary 1(`p_busan_lucky7`) |
| Q13~Q17 | 범위 밖(화면 검수) | — |
| Q18 | **부분 통과**(데이터 측) | `kind` = trades:`auto` / lh:`semi` / myhome:`semi` / bmc:`manual` / policy:`semi` / private:`none`. 스키마 미확인 출처가 `auto`로 표시되지 않음 |
| Q19 | 범위 밖(화면 검수) | 데이터 근거: `collectors[key=trades].note = "과거 계약 통계, 매물 아님 · 신고 지연 최대 30일"` (`collect.py:1497`) |
| Q20 | **부분 통과**(데이터 측) | `sample_min=5`가 `meta.config`로 전달. 31조합 중 28조합이 5건 미만 |
| Q21 | **통과** | 오라클: 집계 키에 `housing_type` 포함, 한 행 내 유형 혼합 0건 |
| Q22 | **통과**(데이터 측)·DEF-3 동반 | RUN 3(LH fixture 파손) → `lh:fail`, 나머지 ok, 공고 5건 유지, `disappeared` 0건, `last_success` 직전값 유지, `collector_failures`에 lh 기록. RUN 4(실거래 파손) → `trades:fail`, `trades.json` 직전 31조합 + 직전 `fetched_at` 유지 |
| Q23 | **통과** | RUN 1(data 삭제 후) → `is_first_run=true`, `new_notices=[]` |
| Q24 | **조건부 통과** | RUN 1→2 동일 fixture: `new_notices=[]`, `closed_notices=[]`, id 집합 동일(5/5). 단 DEF-4 |
| Q25, Q26 | 범위 밖(화면 검수) | — |
| Q27 | **부분 통과**(데이터 측) | `by_household["2"]["110"]=6,452,897`·`["130"]=7,626,151` 존재. `p_happy_house`: `pct 100`/`pct_dual 120`/`pct_adjust {"1":20,"2":10}` |
| Q28 | **부분 통과**(데이터 측) | `pct_adjust_by_household`에 `"3"` 이상 키 없음 → 가산 0 → `["3"]["100"]=8,168,429` |
| Q29~Q35 | 범위 밖(화면 검수) | 데이터 근거: `marriage_within_months=84`(6정책), `pre_marriage_allowed=false`(`p_newborn_jeonse`), `pending_change` 4건, `year_label` 2종 |
| Q36 | **부분 통과**(데이터 측) | `deposit_hist` 31조합 전건. 버킷 폭 500 · `lo` 오름차순 · 마지막 `hi:null` · count 합 == count 전건 일치 · 값 단위 재귀속 검증 통과. CDF 보간 계수(1.6/0.02/0.98) 0건 |
| Q37~Q41 | 범위 밖(화면 검수) | — |
| Q42 | **통과** | ①`git grep -nE "serviceKey=[A-Za-z0-9%+/=]{16,}\|DATA_GO_KR_KEY\s*=\s*['\"]"` → 0건 ②RUN 7 `DATA_GO_KR_KEY=abc` 실모드 실호출(403 수신) → stdout·`meta.json`·`data/*.json` 어디에도 `abc`·`serviceKey=` 0건 ③RUN 8 46자 키 → 동일 0건 ④단위: `mask_secret`이 URL 쿼리 전체를 `?***`로 절단, `HTTPError`는 `"HTTPError 401 Unauthorized"`로 URL·키 미포함 |
| Q43 | 범위 밖(화면 검수) | 데이터 측: `collectors[].key` 6종이 스키마 enum과 정확히 일치 |
| Q44 | **부분 통과**(데이터 측) | `private`: `kind:"none"`, `note:"수집 안 함 — 검색 링크만 제공"`, `status:"skip"`, `collector_failures`에서 제외(`collect.py:1246`) |
| Q45 | **통과** | RUN 1→2: `first_seen` 5건 전부 동일(`2026-09-03`), 변한 필드는 `collected_at` 뿐 |
| Q46 | **부분 통과**(데이터 측) | `dday(None,today) is None`, `closing_soon`에서 `days is None` 조기 continue(`collect.py:1229`). 5건 전부 `apply_end:null`이고 `closing_soon=[]` |
| Q47 | **실패** | DEF-1(오탐 `disappeared`) + DEF-5(`reason:"notice_status"` 미구현) |
| Q48 | 범위 밖(화면 검수) | — |
| Q49 | **통과**(데이터 측) | `grep -rc stops_from_base data/*.json site/index.html` → 0건. `meta.config.stations` 13역 1호선 순서 유지 |
| Q50 | 범위 밖 + **DEF-6** | `exclusion_rules` 6항목이 `meta.config`로 전달되나 `input:"housingBenefit"` 축이 산출물에 없어 영구 무시 |
| Q51 | **부분 통과**(데이터 측) | `supply_type_policy_map` 6개 매핑의 정책 id 전부 존재 — dangling 0건. 검증 코드 `build.py:240-243` 존재 |
| Q52 | **통과** | `snapshot_diff.json`에 `history` 키 없음, `diff_history.json` 별도 배열·각 항목 7키 전부(누락 `[]`). `refetched_months`는 `data/trades.json` 에만 |
| Q53 | **부분 통과**(데이터 측) | `diff.is_first_run`이 `snapshot_diff.json`·`diff_history[]` 양쪽에 실림 |
| Q54 | **통과** | RUN 11(정책 1건 `source_url`을 미존재 도메인으로) → `policy:fail`, `kind`는 `semi` 유지, 실패 정책 `source_hash` 센티넬 그대로 미갱신, `changed_policies=[]`. `content_id`는 `#id` 단일 처리 + 미발견 시 정규화 폴백, 선택자 엔진 없음(`collect.py:1330-1341`) |
| Q55 | **통과**(fixture)·실키 육안 필요 | `num_of_rows=1000`, 페이징 조건 `page*numOfRows >= totalCount`(`collect.py:496`). fixture(`fixture_num_of_rows=3`): `trades_apt_26410_202609`(totalCount 5) → p1 3건 + p2 2건 = 5건 = totalCount. 오라클이 8구간 전부 확인 |
| Q56 | **통과** | RUN 6(키 없이 실모드): 예외 0, `trades·lh·myhome` 전부 `skip` + `error:"DATA_GO_KR_KEY 없음"`, `notices.json`·`trades.json` md5 불변. `--fixture` → `build.py` 페이지 생성 성공(경고 0건, 스모크 통과) |

**집계**: 통과 12 · 부분 통과 12 · 조건부 통과 1 · 실패 1 · 범위 밖(화면 검수) 30

## 결함 표

| # | 심각도 | 파일:줄 | 문제 | 재현 | 권고 |
|---|---|---|---|---|---|
| DEF-1 | **치명** | `collect.py:667-689`(`lh_extract_items`)·`1159-1166`(`merge_notices`)·`1206-1208` | LH 목록 API가 HTTP 200 + 오류/빈 봉투(`SS_CODE:"N"`, `dsList:[]`)를 돌려주면 예외가 없어 `status:"ok"`, `item_count:0`. 그러면 `authoritative["LH"]=True`이므로 직전 공고 전건이 `disappeared:true` + `closed_notices`로 뒤집힌다. 원칙 4·7 위반 | RUN 9: fixture를 `[{"resHeader":[{"SS_CODE":"N",...}]},{"dsList":[]}]`로 교체 → `공고 5건 / 마감 5건`, `lh: ok, item=0, error=None`, `disappeared=True 5건`, `closed_notices` 5건 전부 `reason:"disappeared"`, `collector_failures`에 lh 없음 | ①`resHeader.SS_CODE != "Y"`면 `RuntimeError`(마스킹 후) ②`ALL_CNT>0`인데 `items==0`이면 실패 ③직전에 공고가 있었는데 이번이 0건이면 `authoritative=False`로 강등해 `disappeared`를 찍지 않는다 |
| DEF-2 | **치명** | `collect.py:370-375`(`parse_trade_xml`)·`1630-1631` | 실거래 API가 data.go.kr 표준 오류 봉투(`<OpenAPI_ServiceResponse><cmmMsgHeader><returnAuthMsg>…`)를 HTTP 200으로 돌려주면 `resultCode`가 없어 `result_code==""` → 검사 건너뜀, `totalCount` 0. 결과: `trades:ok`인데 계약 0건 → `trades.json`이 `aggregates:[]`로 덮이고 `latest_contract_ym:null`, `excluded_trade_count` 0 리셋. 필드명 별칭(영문/국문 미확인, `collect.py:341-352`)이 실응답과 다를 때도 같은 경로로 조용히 0건 | RUN 10: 전 `trades_*.xml`을 인증오류 봉투로 교체 → `trades: ok, item=0`, `aggregates: 0`(직전 31→0). `oracle_collect_edge.py` F절 NG | ①`resultCode`가 없으면 정상으로 보지 말고 `returnAuthMsg`/`errMsg`/`cmmMsgHeader` 존재를 오류로 판정 ②전 구간 합계 0건이면 `fail`로 떨어뜨려 직전 데이터 유지 ③구간별 `totalCount` 합과 파싱 건수 불일치 시 실패 |
| DEF-3 | **높음** | `collect.py:1244-1254` · `data/snapshot_diff.json` | `collector_failures[]`에 SPEC §3-6 필수 필드 `status:"fail"\|"skip"`이 없다(`key·name·error·last_success` 4개뿐). `build.py:274-292` 검증기도 확인하지 않아 통과 | `oracle_collect_edge.py` I절 NG | `failures.append`에 `"status": record["status"]` 추가. `build.py` 검증기에 enum 확인 추가 |
| DEF-4 | **높음** | `collect.py:1012-1026`(`composite_id`)·`1049-1069`(`assign_notice_ids`) | 복합키 충돌 확장(level 0→1→2)이 배정 순서에 의존. 같은 `source+supply_type+apply_end+sigungu_code` 공고가 있으면 정렬상 첫 건은 level-0, 나머지는 level-2 키. 정렬상 앞서는 공고가 새로 들어오면 기존 공고 id가 밀려 전부 바뀐다 → 같은 공고가 "신규"와 "마감(추정)"으로 동시에 뜬다 | `oracle_collect_edge.py` G절: 연제구 매입임대 2건 → 3번째 추가 시 기존 2건 id 전부 변경 | 충돌 여부와 무관하게 키 산식 고정: `PAN_ID` 없으면 처음부터 level-2(제목 포함) 복합키, 또는 `DTL_URL` 원문을 키 재료에. 순서 의존 확장 제거 |
| DEF-5 | 중간 | `collect.py:1206-1212` | `closed_notices[].reason`에 `notice_status`가 생성되지 않는다. D12·§3-6의 3번째 경로(LH `PAN_SS`가 `접수마감`)를 `build_diff`가 보지 않는다. `config.lh.PAN_SS=["공고중","접수중"]`이라 접수마감 공고는 목록에서 빠지고 전부 `disappeared` 문구 | `oracle_collect_edge.py` I절: `notice_status:"접수마감"` → `closed_notices=[]` NG | `build_diff`에 `notice_status in ("접수마감",…)` → `reason:"notice_status"` 분기. 판정 문자열은 `config`로 |
| DEF-6 | 중간 | `config.json:133` · `site/index.html:929` | `{"keyword":"주거급여수급","input":"housingBenefit"}`가 가리키는 입력 축이 산출물에 데이터 블록 1곳에만 있고 판정 함수·입력 컨트롤이 없다 → 규칙이 영구히 매칭되지 않는다 | `grep -no "housingBenefit" site/index.html` → `929` 단독. 대비: `noHome`은 1160·1368·1468·1715줄 | 입력 축 추가 또는 규칙 제거. 최소한 `build.py`가 `exclusion_rules[].input`이 화면 축 목록에 없으면 경고 |
| DEF-7 | 중간 | `collect.py:705-711`(`match_busan_gu`) | 구·군명 어간 부분일치가 제목에서 잘못된 `sigungu_code`를 뽑는다(`사상`·`수영`·`기장` 같은 일반어). 잘못된 `sigungu_code`는 복합 식별키 재료이므로 id까지 오염 | H절: `"부산 수영장 인근 행복주택 모집"`→`('수영구','26500')`, `"사상 최대 규모 통합공공임대 모집"`→`('사상구','26530')` | 어간 폴백을 `구`/`군` 포함 형태·구분자 경계로 제한하거나 제거. 못 찾으면 `null`이 정상(§3-4) |
| DEF-8 | 낮음 | `collect.py:787,825,837-838` | `dropped_region`을 중복 제거 전에 세어 8회 조회로 같은 공고를 8번 센다 | `data/meta.json`: `"부산·전국 외 지역 8건 제외"` — 실제 1건 | 중복 제거 후 카운트 |
| DEF-9 | 낮음 | `collect.py:161`(`detect_format`)·`142`(`write_json`) | LF 전용 파일에 `newline=None`을 돌려주는데 Windows에서 `\n`→`\r\n` 변환 → `policies.json`이 CRLF로 재기록 | RUN 6 후: `policies.json` 16,999→17,666 bytes | LF 파일에는 `newline="\n"` |
| DEF-10 | 낮음 | `collect.py:1644-1652` | 실거래 실패 시 종료 로그가 `"실거래 집계 0조합"`이지만 `trades.json`은 직전 31조합 유지 → 로그 오독 | RUN 4 | 실패 시 `"직전 데이터 유지(N조합)"` 문구 |
| DEF-11 | 낮음 | `.github/workflows/daily.yml:50-57` | 키 유출 검사가 `servicekey` 문자열만 본다. 발급키 원문 자체는 검사하지 않음. `mask_secret`은 `len(key)>=8`일 때만 원문 치환 | E절: 키 `abc` → 미마스킹(설계상 한계) | `grep -qrF -- "$DATA_GO_KR_KEY" data/ site/` 추가(출력 없이 종료코드만) |
| DEF-12 | 낮음 | `.github/workflows/daily.yml:18-21` | `permissions`가 워크플로 전역이라 `deploy` 잡이 불필요한 `contents: write` 상속 | 파일 확인 | 잡별 분리 |
| DEF-13 | 낮음 | `config.json:49-52` | `gyodae.gu`가 `"동래구"`인데 1호선 교대역 소재지는 연제구 거제동 | B절 NG | `gu`는 역 소재 구로 통일(연제구). 사용자 매핑 검토 시 함께 |
| DEF-14 | 낮음 | `collect.py:727` · `data/notices.json` 3번째 | `DTL_URL`이 `http://`면 `source_url`을 `null`로(M26 의도). SPEC §3-6은 `source_url: string`(non-null) → 스키마 불일치 + 원문 링크 없는 카드 | `"source_url": null` | 스키마를 `string\|null`로 정정 + "원문 링크 없음" 문구, 또는 `http→https` 승격 시도 |
| DEF-15 | 정보 | `collect.py:1398-1401` | `data/meta.json`의 `config`에 `notice_retain_days`·`exclusion_rules`가 없다. 결함 아님 — SPEC이 `build.py` 복사로 규정하고 `build.py:83-95`가 채운다 | J절 | 그대로 두거나 혼동 방지용으로 `collect.py`도 복사 |
| DEF-16 | 낮음 | `data/income_tables.json` `urban_worker.by_household["6"]` | 6인 가구 행에 `130` 키가 없다(1~5·7~8인과 비대칭) → 6인 130% 정책은 `근사값` 폴백 | `'130' in u['6']` → False | 원문 재확인 또는 원문 부재를 note 로 |

**추가 관찰(결함 아님)**
- `data/notices.json` 5건 전부 `station_ids: []` — LH 목록 응답에 법정동이 없어 자동수집분은 역 매핑 불가(정상). Q49의 "N정거장"이 자동수집 공고에서는 계산되지 않는다.
- `policies.json` 8건 전부 `content_id: null` → D14의 `#id` 경로가 실데이터에서 쓰이지 않고 전건 정규화 텍스트 폴백.
- `criteria.region`이 `null`인 정책 3건 — SPEC §3-6은 `null` 처리를 정의하지 않음(화면 검수 대상).
- `data/trades_cache.json`은 `.gitignore`에 없어 Actions가 커밋(의도된 설계 — 러너가 매회 새 체크아웃). 화면에는 안 실림.
- `tools/ingest_proposals.py` 재실행 결과가 커밋된 `data/policies.json`·`income_tables.json`과 완전 일치. 단 재실행은 `source_hash`·`last_notified_hash`를 초기화하므로 실수집 후에는 다시 돌리면 안 된다.
- 단일 계약 조합은 `deposit_hist`가 `[{lo, hi:null, count:1}]` 한 버킷뿐 — D6 선형 비례분의 상한이 없어 화면이 처리해야 한다.

## 지시서 항목별 확인 결과 (요약)
1. 독립 오라클 — 31조합 × 전 필드 불일치 0건. `excluded_trade_count=1`(안락동)·`latest_contract_ym=202609` 일치.
2. 경계 — 반전세 `24000 >= 100×240` 포함, `23999` 제외. 월세 0 → 전세. 복수 매핑 11개 법정동 허용, 미매핑 제외+카운트. 12개월 창 `202510~202609`, 재수집 창 당월·전월, 연말 경계 정상.
3. 실패 주입 — LH·실거래 각각 해당 수집기만 `fail`, 직전 데이터·`last_success` 유지, 오탐 0. 원복 후 신규 0.
4. 키 없음/가짜 키 — 예외 0, skip, md5 불변. 가짜 키(403 수신) → 키·`serviceKey=` 노출 0. 주의: 키 없이 실모드로 돌리면 `policy` 수집기는 실제 HTTP 요청을 보내고 `source_hash`를 갱신한다(DEF-9 동반).
5. 시크릿 grep 0건. 워크플로 `set +x`·env 주입 양호(DEF-11·12). `oracle_collect_edge.py:110`에 46자 가짜 키 리터럴 있음(실키 아님).
6. `config.json` — 13역 순서·시군구 코드 정확, 정책 id dangling 0. 법정동 초안은 인접 생활권 범위. `gu` 1건 오류(DEF-13).
7. `policies.json`·`income_tables.json` — 스키마 키 전수 일치, 필수 수치 일치(2인 100% 5,866,270 · 130% 7,626,151 · 기준중위 2인 4,199,292). `confidence` 표본 4건 §E 출처와 어긋남 0.
8. `daily.yml` — cron·명령·조건부 커밋·Pages 배포 정상. `timeout-minutes` 미설정.

## 저장소 상태·프로세스 메모
- 저장소 내 실행은 `collect.py --fixture` 2회만, 이후 `git checkout -- data/` 원복. 파괴적 실험은 전부 스크래치 사본.
- 병행 세션의 커밋 `8ac4a07`이 검수 중 만든 `oracle_collect_*.py` 2종을 함께 스테이징했다(데이터 오염 없음, HEAD 기준 재실행 결론 동일). **병행 작업 시 `git add -A` 대신 경로 지정 스테이징**이 필요하다.
- `CLAUDE.md` §9가 `개발 미착수`로 남아 있음 — 핸드오프 갱신 필요.

## 육안·실키 확인 필요
1. 실키 1회 실호출 — `trades.endpoints` 3종 경로, 실거래 응답 필드 국문/영문, `lh.CNP_CD="26"`·생략 조회, LH 봉투 구조·`PAN_SS` 값 집합, Q55 `totalCount` 손 대조
2. 마이홈 API 스키마(15108420) — 활용신청 후. 현재 `list_endpoint: null` → 영구 skip
3. 역↔법정동 매핑 사용자 검토 1회 — `gyodae.gu`, 부산대역 `온천동`·`부곡동`, 범어사역 `청룡동`
4. 6인 가구 130% 값(DEF-16)
5. Actions 로그 실물(Q42)
6. 화면 항목 30개 — 별도 화면 검수

## 다음 단계 함정 3개
1. **"200 OK는 성공이 아니다."** data.go.kr 계열은 인증 실패·트래픽 초과·파라미터 오류를 HTTP 200 + 오류 봉투로 돌려준다. DEF-1·DEF-2 수정 전에는 실모드로 돌리지 말 것.
2. **`disappeared`는 되돌릴 수 없다.** `notices_prev.json`이 매 실행 덮여 쓰이므로 오탐이 새 기준선이 되고 `notice_retain_days` 후 잘려 나간다.
3. **복합키는 조용히 흔들린다.** DEF-4는 같은 구·같은 공급유형 공고가 2건 이상인 실데이터에서만 터진다.

---

## 재검수 (커밋 `525fa70`, 2026-09-03) — 판정: **GO**

DEF-1~DEF-16 **16건 전부 수정 확인.** 오라클 NG 0건(`oracle_collect_edge.py` OK 71 / NG 0 · `oracle_collect_trades.py` 31조합 불일치 0), `--fixture-scenario` 6종 전부 규격대로(해당 수집기 `fail` 또는 `lh_zero` 는 `ok`+마감 판정 보류, 직전 데이터 유지, `disappeared` 0, `closed` 0, `collector_failures[].status` 존재), 복합 식별키 입력 순열 24개 전수 불변. 치명·높음 잔존 0.

- 초판 오라클 F절 3항의 판정식은 검수자 측 오류였다(`lh_extract_items` 는 순수 추출기, 봉투 검사는 `check_lh_envelope()` 가 `collect_lh` 페이지 루프에서 선행 호출). 오라클을 그 함수 기준으로 고치고 케이스를 5종으로 넓혔다.
- DEF-1 방어 3중(봉투 `SS_CODE` / `ALL_CNT>0`·파싱 0건 / 직전 공고 있는데 0건 → `authoritative` 강등), DEF-2 방어 4중(봉투 감지 / `resultCode` 부재 / `totalCount`≠파싱 수 / 전 구간 0건).
- DEF-5 e2e: `notice_status:"접수마감"` 공고 → `closed_notices[].reason:"notice_status"`. DEF-6 음성 통제: 규칙 재삽입 시 `build.py` 경고 1건. DEF-7 오탐 전멸(`수영장`·`사상 최대`·`기장님`·`서울 강남구` → null) + 참긍정 유지. DEF-9 재기록 후 CRLF 0. DEF-11 발급키 원문 grep(`-q`). DEF-12 잡별 권한 + `timeout-minutes`.
- 회귀: 시크릿 grep 0 · 46자 가짜 키 실모드(403) 키 노출 0 · 빌드 경고 0 · 스모크 throw 0 · 2회 연속 fixture 신규 0.

**잔존(결함 아님)**: ① 재료 완전 동일 레코드의 `#N` 재배정(원리적 한계) ② `PAN_ID` 없는 공고의 복합키는 제목 변경에 흔들림(SPEC §3-5 폴백 성질 — 실주행 며칠간 `new_notices` 육안 확인 권장) ③ `lh_zero`(0건 수집 보류)가 탭5 새 소식에 실리지 않음 — 원칙 7 취지상 SPEC 개정 검토 사안 ④ 실키 실호출 확인 6건 — DEF-2 가드가 이제 불확실성을 `fail` 로 드러내므로 첫 실주행에서 즉시 감지됨 ⑤ 마이홈 스키마·매핑 사용자 검토·6인 130% 원문·Actions 로그 실물.
