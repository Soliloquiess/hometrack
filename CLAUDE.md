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
| 2 | `docs/SPEC.md` | 화면 5개·판정 규칙·JSON 스키마·검수 기준 22항목. **모든 개발의 기준 문서** |
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
| `ht-qa` | SPEC §4 22항목 검수, 재현·증적 | `docs/qa/` 만 |

메인 세션은 팀 리더로서 분석·분배·조율만 한다. 순서: (필요 시) 조사 → 구현 → **QA(실패 시 구현으로 재순환)** → 상태 갱신 → 사용자 보고.
2개 이상 독립 작업은 병렬. 사소한 단일 수정·질의응답은 직접 처리해도 된다.

## 6. 자주 쓰는 명령
```bash
python collect.py                 # 수집 (환경변수 DATA_GO_KR_KEY 필요)
python build.py                   # site/index.html 생성
python -m http.server -d site 8000   # 로컬 확인 http://localhost:8000
git pull --rebase && git push     # 세션 시작·종료
```
Windows Claude Code 의 `!` 프롬프트는 Git Bash 이므로 경로는 `/c/DEVTool/hometrack` 형식으로 쓴다.

## 7. Design
UI·HTML을 쓰거나 고칠 때는 **먼저 루트 `DESIGN.md` 를 읽고** Strict Rule로 적용한다.
기존 코드 관습이 DESIGN.md보다 우선한다. 규칙을 어겼으면 이유를 한 줄로 보고한다.
토큰은 svntrack 계열을 상속한 값이며 새 팔레트를 만들지 않는다.

## 8. 세션 시작·종료 규칙
- **시작**: `git pull` → 이 파일 §9 "현재 상태" 확인 → 사용자가 "hometrack 개발 시작"이라 하면 §9 다음 할 일부터.
- **종료**: `/hometrack-handoff` 실행 → §9 를 갱신하고 커밋 → 사용자가 push. 회사 PC 의 전역 메모리에 의존하지 않는다.

---

## 9. 현재 상태 (핸드오프 — `/hometrack-handoff` 가 갱신한다)

**최종 갱신**: 2026-09-03 · **단계**: 기획·디자인 완료, **개발 미착수**

### 완료
- SPEC v1.1(757줄) — 기획 검수 24건 반영, 디자이너 발견 스키마 공백(`linked_policy_id`) 정식 반영
- DATA_SOURCES — 실거래 API 3종 확인(시군구 연제 26470·동래 26260·금정 26410), 2인 가구 도시근로자 월평균소득 100~140% 확보(100%=5,866,270원, 2025 실적 기준)
- 디자인 — DESIGN_SPEC + 동작 목업(191KB). QA 최종 **GO**, 잔여 결함 0 (12,960 조합 전수 + 독립 오라클 재현)
- GitHub 공개 저장소 개설, 첫 푸시 완료

### 사용자 결정·행동 대기
1. **공공데이터포털 활용신청** — 마이홈 공공주택 모집공고(15108420), 국토부 실거래가 전월세 3종(아파트·연립다세대·오피스텔). 발급 키 → 저장소 Settings → Secrets → `DATA_GO_KR_KEY`
2. **마이홈 API 응답 스키마 확정** — 활용신청 후에만 가능. 금액·면적·대상 필드 유무에 따라 탭2 카드 구성 확정
3. **역↔법정동 매핑 검토** — 개발자가 13역 초안(`config.json`)을 만들면 생활권 감각으로 1회 검토

### 다음 할 일 (개발 단계 착수 순서)
1. `config.json` — 13역·기준역·시군구 코드·설정값(trade_months 12 / trend_months 3 / conversion_rate 6.0 / sample_min 5) + 역↔법정동 매핑 초안
2. `collect.py` — 실거래 3종 수집기 먼저(키만 있으면 바로 검증 가능) → 마이홈 → LH 메타 감지 → 스냅샷 diff(`notices_prev.json`)
3. `data/policies.json`·`income_tables.json` — DATA_SOURCES 값 이관, `confidence`·`year_label` 포함
4. `build.py` — 목업 `mockup/index.html` 의 구조·클래스·`const DATA` 스키마를 승계해 템플릿화. `data-mock-only` 3곳 제거
5. `.github/workflows/daily.yml` — cron `0 22 * * *`(UTC = 07:00 KST) → collect → build → commit → Pages. 저장소 Settings → Pages → Source = GitHub Actions
6. `ht-qa` 로 SPEC §4 22항목 검수(20번 "2회 연속 수집 신규 0건" 포함)

### 잔여 조사(미확인)
임대차 신고 금액 하한 / 럭키7하우스 2026 소득기준 / 1·3~6인 가구 130~140% 원문 / 민간 플랫폼 딥링크 실제 쿼리 문법(목업은 플레이스홀더)
