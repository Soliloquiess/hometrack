# DESIGN.md — hometrack (부산 신혼집 대시보드) 디자인 규칙

> 레인 **B**: `collect.py` → `data/*.json` → `build.py` → 의존성 0 단일 `site/index.html`.
> 산출 HTML을 손으로 고치지 않는다. **`build.py`·템플릿·`assets_src/` CSS를 고친다.**
> 글로벌 규칙 `~/.claude/design/DESIGN.standalone.md` 가 있으면 참고하되, **없어도 이 파일만으로 동작한다**(CLAUDE.md §0 "전역 설정 없이 동작"). 토큰은 아래 값이 정본이다.

## 0. 절대 원칙
1. **자기완결** — CSS·JS·데이터 인라인. 외부 CDN·웹폰트·이미지·지도 타일 링크 금지(GitHub Pages에 올려도 외부 요청 0건 유지).
2. **인쇄 가능** — `@media print` 필수. 추천 목록·정책 표는 PDF로 뽑아 둘이 같이 본다.
3. **개인 조건은 브라우저에만** — 예산·소득·혼인예정일은 `localStorage`. 빌드 산출물·저장소·URL 파라미터에 절대 넣지 않는다.
4. **출처·수집 시각·자동/수동 표시** — 모든 데이터 블록에 붙인다. 낡은 화면을 최신으로 오인하는 사고 방지.

## 1. 토큰 — svntrack `base.css` 상속 (새 팔레트 금지)
같은 사용자의 도구들(svntrack·flowtrack·adptrack)과 한 세트로 보이게 **이름·값 그대로** 쓴다.

```css
:root{
  --bg:#f4f6f9; --bg-2:#ffffff; --bg-3:#eef1f6; --bg-sunk:#e7ebf2;
  --fg:#16202c; --fg-2:#45536a; --fg-3:#7b8798;
  --line:#d6dce6; --line-2:#c2cad8;
  --accent:#1e5fbf; --accent-bg:#e5eefc;
  --hi:#b7381f; --hi-bg:#fde8e3;      /* 불가 · 마감 임박 · 수집 실패 */
  --mid:#9a5b00; --mid-bg:#fdf0d8;    /* 조건부 · 주의 */
  --low:#4c6b2f; --low-bg:#e9f3dd;    /* 해당 · 예산 내 */
  --add-bg:#e3f5e6; --add-fg:#12602a; /* 새 소식: 신규 */
  --del-bg:#fde9e9; --del-fg:#97231f; /* 새 소식: 마감·삭제 */
  --shadow:0 1px 2px rgba(20,30,50,.07),0 1px 8px rgba(20,30,50,.05);
  --radius:7px;
  --sans:"Malgun Gothic","맑은 고딕","Apple SD Gothic Neo","Noto Sans KR",system-ui,-apple-system,"Segoe UI",Roboto,sans-serif;
  --mono:"D2Coding","Consolas","Menlo","DejaVu Sans Mono","Courier New",monospace;
}
@media (prefers-color-scheme:dark){ :root:not([data-theme="light"]){
  --bg:#12151b; --bg-2:#1a1f27; --bg-3:#222833; --bg-sunk:#0e1116;
  --fg:#dfe5ee; --fg-2:#a8b3c4; --fg-3:#77839a; --line:#2d3543; --line-2:#3d4757;
  --accent:#6fa8ff; --accent-bg:#17263d;
  --hi:#ff8f78; --hi-bg:#3a1c17; --mid:#ffc266; --mid-bg:#382a12; --low:#9fd07a; --low-bg:#1f2b16;
  --add-bg:#14301d; --add-fg:#86d99b; --del-bg:#351a1a; --del-fg:#f0908c;
  --shadow:0 1px 2px rgba(0,0,0,.4);
}}
:root[data-theme="dark"]{ /* 위 다크 블록과 동일 값을 반복 (토글 우선) */ }
```

### 1-1. 인쇄 팔레트 `--print-*` (정본)

`@media print` 는 **라이트 고정 + 대비 강화** 팔레트를 쓴다. 그 값을 인쇄 블록 안에 리터럴로 적으면
DESIGN.md 에 없는 4번째 팔레트가 조용히 생긴다(검수 M14). 그래서 **인쇄 값도 여기서 토큰으로 정의**하고,
`@media print` 는 `--bg: var(--print-bg)` 처럼 **대입만** 한다. 인쇄 블록의 색 리터럴은 **0건**이어야 한다.

```css
:root{
  --print-bg:#ffffff; --print-bg-2:#ffffff; --print-bg-3:#f1f3f6; --print-bg-sunk:#e4e7ec;
  --print-fg:#000000; --print-fg-2:#2b3340; --print-fg-3:#4a5260;
  --print-line:#b4bbc6; --print-line-2:#8f97a4;
  --print-accent:#1a4f9e; --print-accent-bg:#e9f0fb;
  --print-hi:#8f2a15; --print-hi-bg:#fbe6e1;
  --print-mid:#7a4700; --print-mid-bg:#fbf0d6;
  --print-low:#3b551f; --print-low-bg:#eaf3de;
  --print-add-bg:#e6f4e8; --print-add-fg:#14562a;
  --print-del-bg:#fbe8e8; --print-del-fg:#86201c;
}
@media print{ :root, :root[data-theme="dark"], :root:not([data-theme="light"]){
  --bg:var(--print-bg); --bg-2:var(--print-bg-2); --bg-3:var(--print-bg-3); --bg-sunk:var(--print-bg-sunk);
  --fg:var(--print-fg); --fg-2:var(--print-fg-2); --fg-3:var(--print-fg-3);
  --line:var(--print-line); --line-2:var(--print-line-2);
  --accent:var(--print-accent); --accent-bg:var(--print-accent-bg);
  --hi:var(--print-hi); --hi-bg:var(--print-hi-bg);
  --mid:var(--print-mid); --mid-bg:var(--print-mid-bg);
  --low:var(--print-low); --low-bg:var(--print-low-bg);
  --add-bg:var(--print-add-bg); --add-fg:var(--print-add-fg);
  --del-bg:var(--print-del-bg); --del-fg:var(--print-del-fg);
  --shadow:none;
}}
```

**인쇄 대비 전략은 하나로 통일한다 — "배경 강제 + 테두리 이중화"**(검수 M15).
`print-color-adjust:exact` 로 배경을 살리고, **배경이 빠지는 프린터를 대비해 같은 요소에 1px 테두리를 함께 건다.**
대상: `.verdict` `.dday` `.conf` `.fitchip` `.tag-*` `.chip` `.pbar` `.policy-stale` `.policy-changed` `.news-item` `.stat`.
배경만으로 구분되던 것(`.tag-*` · `.policy-stale` · `.policy-changed`)에 테두리 폴백이 없으면 흑백 인쇄에서 구분이 사라진다.

글로벌 템플릿 역할명 ↔ 이 프로젝트 토큰 대응: `--bg-sub`→`--bg-3` · `--fg-muted`→`--fg-3` · `--border`→`--line` · `--accent-soft`→`--accent-bg` · `--ok`→`--low` · `--warn`→`--mid` · `--danger`→`--hi` · `--info`→`--accent` · `--font`→`--sans`.

기본 테마 **라이트**. 다크는 `prefers-color-scheme` 자동 + 상단바 토글(`data-theme`), svntrack과 동일 방식.

## 2. 셸 — svntrack 앱 셸 상속
- 상단바 `.topbar` sticky 46px: 브랜드(`home<span>track</span>`) · 탭 5개(`.nav-link`) · 우측에 **수집 시각 + 테마 토글**.
- 본문 `.wrap` max-width 1100px. 카드 = `--bg-2` + `--line` 1px + `--radius` + `--shadow`.
- 타이포: body 14px/1.55, h1 20px, h2 14px `--fg-2`. 숫자 칸 `tabular-nums` 우측 정렬.

## 3. 이 프로젝트 고유 규칙
- **3단 판정 뱃지**는 색+텍스트 병기: `해당`(`--low`) · `조건부`(`--mid`) · `불가`(`--hi`). 사유 텍스트를 뱃지 옆에 항상 붙인다.
- **D-day**: 7일 이내 `--hi`, 30일 이내 `--mid`, 그 외 `--fg-2`. 마감 지난 공고는 목록에서 접되 삭제하지 않는다(새 소식에서 참조).
- **실거래 vs 매물 구분**: 실거래 블록에는 "과거 계약 통계, 매물 아님" 캡션을 고정 표기.
- **외부 링크는 예외 없이** `target="_blank" rel="noopener noreferrer" referrerpolicy="no-referrer"` 를 건다(검수 P23).
  대상 = 매물 딥링크 3개 · 공고 원문 · 정책 근거 출처 · 신선도 바의 원문 목록 · 새 소식의 출처 열기.
  `noopener` 만으로는 Referer 로 Pages 주소가 새고, `noreferrer` 만으로는 구형 브라우저에서 `window.opener` 가 남는다. **셋을 한 세트로 쓴다.**
  `href` 는 `https?://` 만 통과시키는 화이트리스트를 지나게 하고, 통과하지 못하면 링크를 만들지 않고 텍스트로만 적는다(수동 등록 파일의 `javascript:` 차단).
- **예산 밖 항목은 기본 접힘.** 화면에는 "예산 밖 N건 접힘" 한 줄만 보이고, 카드는 hidden 컨테이너에 두어 인쇄·펼침 시 드러난다. 펼쳐진 카드에는 "예산 밖" 라벨이 반드시 붙는다(인쇄물에서 예산 내와 구분).
- **빈 상태 문구 3종**을 구분: 데이터 없음 / 조건 미입력(입력 탭 유도) / 수집 실패(실패 시각·출처 표시).
- 차트는 인라인 SVG만(역별 중위값 막대, 3개월 추세 라인). 지도 타일 금지 → 역 순서를 1호선 노선도식 가로 띠로 표현.
- `@media print`: 상단바·입력 폼·토글 숨김, 접힌 공고 펼침, 링크 URL 병기.
- 375px: 탭은 가로 스크롤, 카드 세로 스택, 표는 컨테이너 안에서 가로 스크롤.

## 4. 산출 전 셀프 체크
- [ ] 외부 요청 0건 (DevTools Network) — Pages에 올려도 동일
- [ ] 개인 조건이 HTML·JSON·URL 어디에도 없음
- [ ] 모든 데이터 블록에 출처·수집 시각·자동/수동 표시
- [ ] 예산 밖 항목 미노출, 3단 뱃지에 사유 텍스트
- [ ] 인쇄 미리보기 / 375px / 다크 정상
- [ ] 색 리터럴 하드코딩 0건, 표 세로선 0건
