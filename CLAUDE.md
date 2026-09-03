# hometrack — 부산 신혼집·정책 개인 대시보드

> 이 파일은 Claude Code 가 이 폴더에서 자동으로 읽는 **프로젝트 전용 지침**이다.
> 다른 PC 에서 `git clone` 또는 `git pull` 후 이 폴더에서 Claude Code 를 열면 그대로 이어서 작업할 수 있다.
> 회사 업무·다른 프로젝트와 무관한 개인 프로젝트다. 전역 설정이 없어도 이 파일 + `DESIGN.md` + `docs/SPEC.md` 만으로 동작해야 한다.

## 1. 한 줄 요약
부산 1호선 **시청 이북 13역**(시청·연산 / 교대·동래·명륜·온천장 / 부산대·장전·구서·두실·남산·범어사·노포, 기준역 **구서**)에서
예비신혼부부가 지원 가능한 **공공 임대 공고 + 실거래 시세 + 신혼부부 정책**을 한 화면에 모아 **매일 자동 갱신**하는 정적 사이트.

## 2. 문서 지도 (작업 전 반드시 읽는 순서)
| 순서 | 파일 | 내용 |
|---|---|---|
| 1 | `CLAUDE.md` (이 파일) | 원칙·워크플로·현재 상태 |
| 2 | `docs/SPEC.md` | 화면 5개·판정 규칙·JSON 스키마·검수 기준 Q1~Q56. **모든 개발의 기준 문서** |
| 3 | `DESIGN.md` | 디자인 토큰·셸·고유 규칙. UI 를 만들거나 고칠 때 Strict Rule |
| 4 | `docs/DESIGN_SPEC.md` + `mockup/index.html` | 화면 설계서와 동작하는 목업(샘플 데이터). 개발은 이 목업의 구조·클래스명을 승계 |
| 5 | `docs/DATA_SOURCES.md` | 공공 API·정책 출처 조사(출처 URL·확인일 병기). 정책 수치의 근거 |
| 6 | `docs/REVIEW_docs_20260903.md` | 기획 검수 보고(24건). 왜 이런 규칙이 생겼는지의 이유 |

## 3. 구조 (레인 B: 생성기 → 단일 HTML)
```
collect.py   공공 API 수집 → data/*.json         (매일, GitHub Actions)
build.py     data/*.json + policies → site/index.html (의존성 0 단일 파일)
mockup/      디자인 목업 (참고용, 개발 후에도 삭제하지 않음)
docs/        명세·설계·조사·검수·QA 증적
.github/workflows/daily.yml   매일 07:00 KST 수집 → 커밋 → GitHub Pages
```
- Python 3 **표준 라이브러리만** 사용. pip 의존성을 만들지 않는다.
- `site/` 는 생성 산출물이다. **손으로 편집하지 않는다.** `build.py`·템플릿을 고친다.
- API 키는 **GitHub Actions Secrets** 에만 둔다. 코드·JSON·커밋에 절대 넣지 않는다. 로컬 실행은 환경변수(`.env` 는 gitignore).

## 4. 절대 원칙 (SPEC §0 요약 — 어기면 안 됨)
1. **외부 요청 0건.** 산출 HTML 은 CDN·웹폰트·이미지·지도 타일을 불러오지 않는다.
2. **개인 조건(예산·소득·혼인예정일 등)은 브라우저 localStorage 에만.** 저장소·JSON·URL 파라미터·딥링크에 넣지 않는다.
3. **민간 부동산 플랫폼(네이버부동산·직방·다방)은 크롤링하지 않는다.** 역·거래유형만 실은 검색 딥링크만 생성한다(`rel="noopener noreferrer" referrerpolicy="no-referrer"`).
4. **"불가" 판정은 함부로 내지 않는다.** `confidence` 가 official 이 아닌 정책, 소득표 근사값(폴백)에 근거한 판정, 연결 정책에서 승계한 판정은 전부 **조건부**로 강등한다. 공고가 불가를 낼 근거는 원문 `exclusions` 하나뿐이다. (잘못된 불가는 신청 포기로 끝나 되돌릴 수 없다.)
5. **정책 자격 수치를 코드에 하드코딩하지 않는다.** `data/policies.json`·`data/income_tables.json` 으로 관리하고 출처·확인일·신뢰도를 함께 적는다.
6. **모든 데이터 블록에 출처·수집 시각·자동/반자동/수동 태그를 표시**하고, 태그는 수집기가 보고한 값을 화면에서 임의 승격하지 않는다.
7. **수집 실패를 조용히 넘기지 않는다.** 수집기 단위 try/except → 직전 데이터 유지 + 화면에 실패 표시 + "새 소식"에 기록.
8. **실거래는 매물이 아니다.** 시세 블록에 "과거 계약 통계, 신고 지연 최대 30일" 캡션을 고정한다.
9. LH 공고 API 는 게시판 메타(제목·등록일·자유서식)만 준다. **자유서식 본문에서 금액·면적을 정규식으로 긁지 않는다.** 상세는 `notices_manual.json` 수동 등록.

## 5. 워크플로와 에이전트 팀 (이 프로젝트 전용, `.claude/agents/`)
단계: **기획 → 디자인 → 개발 → QA**. 작성과 검수는 **항상 분리된 에이전트**가 한다. 같은 에이전트가 자기 결과를 승인하지 않는다.

| 에이전트 | 역할 | 쓰기 범위 |
|---|---|---|
| `ht-planner` | SPEC 개정, 미결 정리 | `docs/SPEC.md` |
| `ht-researcher` | 공공 API·정책 수치 조사(웹) | `docs/DATA_SOURCES.md`, `data/policies.json`·`income_tables.json` 값 제안 |
| `ht-designer` | 화면 설계·목업·빌드 템플릿 CSS | `docs/DESIGN_SPEC.md`, `mockup/`, `build.py` 의 템플릿/CSS 부분 |
| `ht-developer` | `collect.py`·`build.py`·워크플로 구현, 빌드 실행 | 코드 전반. `site/` 는 빌드로만 |
| `ht-qa` | SPEC §4 Q1~Q56 검수, 재현·증적 | `docs/qa/` 만 |

메인 세션은 팀 리더로서 분석·분배·조율만 한다. 순서: (필요 시) 조사 → 구현 → **QA(실패 시 구현으로 재순환)** → 상태 갱신 → 사용자 보고.
2개 이상 독립 작업은 병렬. 사소한 단일 수정·질의응답은 직접 처리해도 된다.

## 6. 자주 쓰는 명령
```bash
python collect.py                 # 수집 (환경변수 DATA_GO_KR_KEY 필요)
python build.py                   # site/index.html 생성
python -m http.server -d site 8000   # 로컬 확인 http://localhost:8000
git pull --rebase && git push     # 세션 시작·종료
```
Windows Claude Code 의 `!` 프롬프트는 Git Bash 이므로 경로는 `/c/...` 형식으로 쓴다. 저장소 위치는 PC 마다 다르다(회사 PC `/c/DEVTool/hometrack`, 집 PC `/c/Users/cyh12/hometrack`). 명령은 저장소 루트에서 실행한다.

## 7. Design
UI·HTML을 쓰거나 고칠 때는 **먼저 루트 `DESIGN.md` 를 읽고** Strict Rule로 적용한다.
기존 코드 관습이 DESIGN.md보다 우선한다. 규칙을 어겼으면 이유를 한 줄로 보고한다.
토큰은 svntrack 계열을 상속한 값이며 새 팔레트를 만들지 않는다.

## 8. 세션 시작·종료 규칙
- **시작**: `git pull` → 이 파일 §9 "현재 상태" 확인 → 사용자가 "hometrack 개발 시작"이라 하면 §9 다음 할 일부터.
- **종료**: `/hometrack-handoff` 실행 → §9 를 갱신하고 커밋 → 사용자가 push. 회사 PC 의 전역 메모리에 의존하지 않는다.

---

## 9. 현재 상태 (핸드오프 — `/hometrack-handoff` 가 갱신한다)

**최종 갱신**: 2026-09-03 · **단계**: 개발 v1 완료 · QA 2계층 GO(수집) / 조건부 GO→재검수 중(화면) · **실키 미발급 → 실데이터 미검증**

### 완료 (전부 커밋·푸시됨, `python collect.py --fixture && python build.py` 로 재현)
- **재검수** `docs/REVIEW_predev_20260903.md` — 기획 P1~P23 · 목업 M1~M30 · 하네스 H1~H6. 핵심: LH API 오선정(15058449 게시판 → **15058530 분양임대공고문**), 행복주택 **2인가구 +10%p 가산** 스키마 누락, 2026-06-09 소득기준 완화 발표 미반영, 기혼 7년 판정식·예산 내 비율 데이터 부재, 목업 크래시 2곳
- **SPEC v1.2** — 결정 D1~D24(§6), §4 검수 항목 **Q1~Q56** 번호 부여. 이후 소폭 패치: LH 응답에 접수기간·PAN_ID 없음(부산+전국 조회), `closed reason notice_status`, `collector_failures.status fail|skip|hold`, `notice_retain_days`, `source_url string|null`, `age_max/region` 조건부 규칙
- **DATA_SOURCES §E** — LH API 3종(15058530 목록·15057999 상세·15056765 공급정보) 확정, 2026 기준중위소득 1~6인(2인 4,199,292), 도시근로자 `year_label` "2026년도 적용기준(2025년 실적)"(2인 100% 5,866,270 · 130% 7,626,151), 가산 3유형 원문, 임대차 신고 하한(보증금 6천만 초과 또는 월세 30만 초과), 버팀목·§B-2 정정. 2026-06 완화는 **미시행**(`pending_change`, `effective: unknown`)
- **데이터** `data/policies.json` 8건(official 7 · secondary 1) · `data/income_tables.json` — `tools/ingest_proposals.py` 로 `docs/proposals/*.json` 이관(실수집 후 재실행 금지: `source_hash` 초기화)
- **수집** `config.json`(13역 1호선 순서·법정동 초안·설정·`exclusion_rules`·`supply_type_policy_map`) · `collect.py`(수집기 6종, `--fixture`, `--fixture-scenario` 6종, 키 마스킹, 200 OK 오류 봉투를 실패로, 0건 수집 시 마감 판정 보류 `hold`, 복합키 고정 산식) · `data/fixtures/` · `.github/workflows/daily.yml`(잡별 최소 권한, 키 유출 검사)
- **디자인** 목업 v1.2.2 + `DESIGN.md`(`--print-*` 토큰) + `DESIGN_SPEC.md` v1.2.2
- **빌드** `build.py`(목업을 빌드 시점에 변환 · 스키마/URL/외부요청/시크릿 검증 · 스모크) · `tools/smoke_site.js` · `site/index.html`
- **QA** `docs/qa/REPORT_collect_20260903.md` — 1차 조건부 GO(결함 16) → 수정 → 재검수 **GO** / `docs/qa/REPORT_site_20260903.md` — 1차 조건부 GO(결함 8) → 수정 → 재검수 1~8 해소 + 신규 #9·#10(hold 줄 건수) → 수정 → **hold 줄 재확인 진행 중**. 오라클(`docs/qa/oracle_*`)·Chrome 증적(`site_*`, `site2_*`) 커밋

### 사용자 결정·행동 대기 (전부 사용자만 가능)
1. 🔴 **공공데이터포털 활용신청(자동승인)** — 실거래 전월세 3종(15126474 아파트 · 15126473 연립다세대 · 15126475 오피스텔), **LH 15058530(+15057999·15056765)**, 마이홈 15108420. 발급 키 → 저장소 Settings → Secrets → `DATA_GO_KR_KEY`. **키가 들어오기 전까지 실데이터는 한 번도 검증되지 않았다.** 첫 실주행은 `config.json` 의 `⚠️미확인` 상수(실거래 엔드포인트 경로·응답 필드 국문/영문·LH `CNP_CD=26`·봉투 구조)를 한 번에 확정한다 — 틀리면 `fail` 로 드러나게 만들어 두었다(조용한 0건 아님)
2. 🔴 **저장소 Settings → Pages → Source = GitHub Actions** (`daily.yml` 이 `deploy-pages` 사용)
3. 🔴 **역↔법정동 매핑 검토 1회** — `config.json` `stations[].dongs`(수기 초안). 특히 교대(연제구 거제동)·부산대(온천동·부곡동)·범어사(청룡동). LH 자동수집분은 응답에 법정동이 없어 `station_ids` 가 비므로 **"13역 인근" 필터에서는 가려지고 "부산 전역" 으로 봐야 한다**(수동 등록으로 역을 붙일 수 있음)
4. (선택) 마이홈 API 스키마 확정 후 `config.myhome.list_endpoint` 채우기 — 현재 null → 영구 `skip`

### 다음 할 일
1. QA B 의 hold 줄 재확인 결과 반영(보고서 재검수 절 R10) → 화면 계층 **GO** 확정
2. 키 발급 후: `DATA_GO_KR_KEY=… python collect.py` 1회 → `data/raw_myhome_last.json`·LH 응답 덤프로 스키마 확정 → `config.json` `_note` 미확인 상수 정리 → LH 상세 API(15057999·15056765)에 금액·면적이 있으면 SPEC §3-5 "자동 승격 규칙" 추가 + `lh_detail_confirmed: true`
3. 첫 실주행 며칠간 탭5 `new_notices` 육안 확인(복합키 폴백 공고의 제목 변경 오탐 감시) — QA A 잔존 ②
4. 잔여 조사: 럭키7하우스 2026 회차 원문 / 6인 가구 130% 원문 / 통합공공임대 맞벌이 % / 2026-06 완화 시행 여부 재확인(시행되면 `pending_change` → 값 갱신) / 민간 딥링크 실제 쿼리 문법(현재 플레이스홀더)
5. Actions 첫 실행 로그에서 키 패턴 0건 육안 확인(Q42)

### 운영 메모
- 병행 에이전트 작업 시 **`git add -A` 금지** — 경로 지정 스테이징(검수자 산출물 혼입 사고 1회 있었음)
- `.claude/agents/ht-*.md` 는 저장소 루트를 cwd 로 Claude Code 를 열어야 `subagent_type` 으로 직접 호출된다. 다른 cwd 에서는 general-purpose/executor 에 "이 파일을 읽고 그 역할로" 지시
- 이 PC(집)는 GitHub 푸시 자격증명 있음. 회사 PC 경로 `/c/DEVTool/hometrack`, 집 PC `/c/Users/cyh12/hometrack`
