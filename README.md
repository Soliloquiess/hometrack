# hometrack

부산 1호선 시청 이북 13역(기준역 구서) 생활권에서 **예비신혼부부가 지원 가능한 공공 임대 공고**, **실제 전월세 거래 통계**, **신혼부부 주거 지원 정책**을 한 화면에 모아 매일 자동 갱신하는 개인용 정적 사이트.

- 의존성 0 단일 HTML. 외부 요청 없음. 개인 조건(예산·소득)은 브라우저에만 저장.
- 민간 부동산 플랫폼은 수집하지 않고 검색 링크만 제공.
- 자격 판정은 참고용이며 공식 판정이 아님. 출처가 확인되지 않은 정책은 "불가"를 표시하지 않음.

| 문서 | 내용 |
|---|---|
| [`CLAUDE.md`](CLAUDE.md) | 원칙·워크플로·**현재 상태와 다음 할 일** |
| [`docs/SPEC.md`](docs/SPEC.md) | 화면·판정 규칙·데이터 스키마 명세 |
| [`DESIGN.md`](DESIGN.md) | 디자인 규칙 |
| [`docs/DATA_SOURCES.md`](docs/DATA_SOURCES.md) | 공공 API·정책 출처 조사 |
| [`mockup/index.html`](mockup/index.html) | 디자인 목업(샘플 데이터, 더블클릭으로 열림) |

## 다른 PC에서 이어서 작업하기
1. `git clone https://github.com/Soliloquiess/hometrack.git`
2. 폴더에서 Claude Code 실행. `CLAUDE.md`와 `.claude/`(전용 에이전트 5개, 핸드오프 스킬)를 자동으로 읽는다.
3. "hometrack 개발 시작"이라고 하면 `CLAUDE.md` §9 다음 할 일부터 이어진다.
4. 세션 끝에 `/hometrack-handoff` → 커밋 → `git push`.

상태: 기획·디자인 완료, 개발 미착수 (2026-09-03)
