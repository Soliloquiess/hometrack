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

## 실행
```bash
python collect.py --fixture   # 키 없이 오프라인 수집. data/fixtures/ 의 응답 샘플로 data/*.json 생성
python collect.py             # 실수집. 환경변수 DATA_GO_KR_KEY 필요 (없으면 각 수집기를 skip 하고 직전 데이터 유지)
python build.py               # data/*.json + config.json → site/index.html (단일 파일 · 외부 요청 0건)
python build.py --no-smoke    # 같은 빌드에서 Node 런타임 스모크만 건너뛴다
```
**사이트 열기**: `site/index.html` 을 **더블클릭**한다. 서버가 필요 없다(원하면 `python -m http.server -d site 8000`).

`build.py` 는 `mockup/index.html` 을 빌드 시점에 읽어 변환하므로 목업 복제본을 손으로 관리하지 않는다.
변환 마커를 못 찾거나 스키마·URL·외부요청·시크릿 검증을 어기면 **빌드가 실패하고 `site/` 를 쓰지 않는다**
(종료 코드 1 = 검증 위반 / 2 = 빌드 중단 / 3 = 런타임 스모크 실패). `site/` 는 빌드로만 만든다 — 손으로 고치지 않는다.
Node 가 있으면 빌드 끝에서 `tools/smoke_site.js` 가 산출 HTML 의 `renderAll()` + 5탭을 DOM 스텁 위에서 돌려
throw·`NaN`/`undefined`/`Infinity` 노출 0건을 확인한다. Node 가 없으면 "스모크 생략"을 출력하고 빌드는 성공한다.

Python 3.12 표준 라이브러리만 쓴다(설치할 것 없음). 키는 로컬에서는 환경변수(`export DATA_GO_KR_KEY=...`),
GitHub Actions 에서는 저장소 Secrets `DATA_GO_KR_KEY` 로만 넣는다 — 코드·JSON·커밋에 남기지 않는다.

## 다른 PC에서 이어서 작업하기
1. `git clone https://github.com/Soliloquiess/hometrack.git`
2. 폴더에서 Claude Code 실행. `CLAUDE.md`와 `.claude/`(전용 에이전트 5개, 핸드오프 스킬)를 자동으로 읽는다.
3. "hometrack 개발 시작"이라고 하면 `CLAUDE.md` §9 다음 할 일부터 이어진다.
4. 세션 끝에 `/hometrack-handoff` → 커밋 → `git push`.

상태: 기획·디자인 완료, 개발 미착수 (2026-09-03)
