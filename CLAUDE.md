# hometrack — 부산 신혼집 대시보드 (개인 프로젝트)

레인 B: `collect.py` → `data/*.json` → `build.py` → `site/index.html` (의존성 0 단일 HTML).
명세 `docs/SPEC.md`, 출처·정책 조사 `docs/DATA_SOURCES.md`.

## Design
UI·HTML을 쓰거나 고칠 때는 **먼저 루트 `DESIGN.md` 를 읽고** Strict Rule로 적용한다.
기존 코드 관습이 DESIGN.md보다 우선한다. 규칙을 어겼으면 이유를 한 줄로 보고한다.

## 원칙
- 산출물 `site/` 를 손으로 편집하지 않는다. 생성기·템플릿·`assets_src/` 를 고친다.
- 개인 조건(예산·소득·혼인예정일)은 localStorage에만. 저장소·JSON·URL에 넣지 않는다.
- 민간 부동산 플랫폼은 크롤링하지 않는다. 검색 딥링크만 생성한다.
