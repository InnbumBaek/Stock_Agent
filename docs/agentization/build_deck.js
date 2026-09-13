const pptxgen = require("pptxgenjs");

const NAVY_D = "0D1B33", NAVY = "1E2761", NAVY_M = "2C3E6B";
const ICE = "CADCFC", GOLD = "C8A24A", GOLD_L = "E8D9AE";
const WHITE = "FFFFFF", PAPER = "F4F6FB", CARD = "FFFFFF";
const INK = "18202F", MUTED = "6B7688", LINE = "DCE3EF";
const RED = "9E2B25", RED_L = "F7E9E8", GREEN = "1F6B4E";

const F = "Malgun Gothic";
const FM = "Courier New";
const W = 13.333, H = 7.5, M = 0.62, CW = W - M * 2;

const pres = new pptxgen();
pres.layout = "LAYOUT_WIDE";
pres.author = "Stock Agent";
pres.title = "Stock Agent 에이전트화 방안";

const sh = () => ({ type: "outer", color: "9AA7BD", blur: 10, offset: 2, angle: 90, opacity: 0.22 });

function base(dark) {
  const s = pres.addSlide();
  s.background = { color: dark ? NAVY_D : PAPER };
  return s;
}

function header(s, kicker, title, sub) {
  s.addText(kicker, {
    x: M, y: 0.42, w: CW, h: 0.26, isTextBox: true, margin: 0,
    fontFace: F, fontSize: 11, bold: true, color: GOLD, charSpacing: 2,
  });
  s.addText(title, {
    x: M, y: 0.72, w: CW, h: 0.62, isTextBox: true, margin: 0,
    fontFace: F, fontSize: 29, bold: true, color: NAVY, valign: "top",
  });
  if (sub) {
    s.addText(sub, {
      x: M, y: 1.36, w: CW, h: 0.3, isTextBox: true, margin: 0,
      fontFace: F, fontSize: 13, color: MUTED,
    });
  }
}

function card(s, o) {
  s.addShape(pres.ShapeType.roundRect, {
    x: o.x, y: o.y, w: o.w, h: o.h, rectRadius: o.r === undefined ? 0.08 : o.r,
    fill: { color: o.fill || CARD },
    line: o.line === null ? { type: "none" } : { color: o.line || LINE, width: 1 },
    shadow: o.noShadow ? undefined : sh(),
  });
}

function numDot(s, x, y, n, d, fill, txt) {
  s.addShape(pres.ShapeType.ellipse, {
    x, y, w: d, h: d, fill: { color: fill || NAVY },
    line: { type: "none" },
  });
  s.addText(txt !== undefined ? txt : String(n), {
    x, y, w: d, h: d, isTextBox: true, margin: 0,
    fontFace: F, fontSize: d >= 0.5 ? 15 : 12, bold: true,
    color: WHITE, align: "center", valign: "middle",
  });
}

function footer(s, t) {
  s.addText(t, {
    x: M, y: H - 0.44, w: CW, h: 0.24, isTextBox: true, margin: 0,
    fontFace: F, fontSize: 9, color: MUTED,
  });
}

/* ══════════ 1. TITLE ══════════ */
{
  const s = base(true);
  s.addShape(pres.ShapeType.ellipse, {
    x: 9.5, y: -1.6, w: 6.2, h: 6.2, fill: { color: NAVY, transparency: 45 }, line: { type: "none" },
  });
  s.addShape(pres.ShapeType.ellipse, {
    x: 11.0, y: 3.4, w: 3.4, h: 3.4, fill: { color: GOLD, transparency: 88 }, line: { type: "none" },
  });

  s.addText("내부 검토용 · 대외비 · 투자권유 자료 아님", {
    x: M, y: 0.62, w: 8, h: 0.28, isTextBox: true, margin: 0,
    fontFace: F, fontSize: 11, bold: true, color: GOLD, charSpacing: 1.5,
  });

  s.addText("Stock Agent 에이전트화 방안", {
    x: M, y: 2.05, w: 10.6, h: 0.95, isTextBox: true, margin: 0,
    fontFace: F, fontSize: 44, bold: true, color: WHITE,
  });
  s.addText("단일 파일 측정 도구를  ·  대형 증권사형 멀티 에이전트 데스크로", {
    x: M, y: 3.05, w: 10.6, h: 0.42, isTextBox: true, margin: 0,
    fontFace: F, fontSize: 18, color: ICE,
  });
  s.addText("ki_monitor.py 8,684줄은 다시 쓰지 않는다. 감싸서 조직을 얹는다.", {
    x: M, y: 3.52, w: 10.6, h: 0.34, isTextBox: true, margin: 0,
    fontFace: F, fontSize: 13, italic: true, color: "8FA3C8",
  });

  const chips = [["8", "데스크 에이전트"], ["0", "원장 쓰기 권한"], ["6", "발행 게이트"], ["9주", "전환 기간"]];
  chips.forEach((c, i) => {
    const x = M + i * 2.62;
    s.addText(c[0], {
      x, y: 4.72, w: 2.4, h: 0.62, isTextBox: true, margin: 0,
      fontFace: F, fontSize: 34, bold: true, color: GOLD,
    });
    s.addText(c[1], {
      x, y: 5.36, w: 2.4, h: 0.28, isTextBox: true, margin: 0,
      fontFace: F, fontSize: 11.5, color: ICE,
    });
  });

  s.addText("2026-09-13  ·  대상 저장소 InnbumBaek/Stock_Agent  ·  최종 결정은 투자심의위원회에서 사람이 한다", {
    x: M, y: 6.55, w: 11.5, h: 0.3, isTextBox: true, margin: 0,
    fontFace: F, fontSize: 10.5, color: "7E8DAB",
  });
  s.addNotes("이 방안은 기존 측정 파이프라인을 유지한 채 그 위에 조직을 얹는 제안입니다. 핵심은 측정층과 판단층의 분리입니다.");
}

/* ══════════ 2. EXEC SUMMARY ══════════ */
{
  const s = base(false);
  header(s, "EXECUTIVE SUMMARY", "요약 — 무엇을 바꾸고, 무엇을 지키는가");

  const rows = [
    ["바꾼다", "사람 한 명이 읽던 §1~§18을 여덟 개 데스크가 나눠 읽는다", "리포트는 이미 나온다. 문제는 85개 종목의 §5를 읽을 사람이 없다는 것이다.", NAVY],
    ["지킨다", "원장(ki.sqlite)은 여전히 측정한 사실만 담는다", "에이전트에게는 쓰기 도구를 아예 주지 않는다. 규칙이 아니라 구조로 막는다.", GREEN],
    ["새로 만든다", "'해석' 등급과 준법감시 게이트", "에이전트 산출은 1차 자료가 아니다. 다섯 번째 등급을 만들어 섞이지 않게 한다.", GOLD],
  ];
  rows.forEach((r, i) => {
    const y = 1.82 + i * 1.30;
    card(s, { x: M, y, w: 7.85, h: 1.13 });
    s.addShape(pres.ShapeType.roundRect, {
      x: M + 0.26, y: y + 0.24, w: 1.16, h: 0.34, rectRadius: 0.17,
      fill: { color: r[3] }, line: { type: "none" },
    });
    s.addText(r[0], {
      x: M + 0.26, y: y + 0.24, w: 1.16, h: 0.34, isTextBox: true, margin: 0,
      fontFace: F, fontSize: 11, bold: true, color: WHITE, align: "center", valign: "middle",
    });
    s.addText(r[1], {
      x: M + 1.58, y: y + 0.19, w: 6.05, h: 0.34, isTextBox: true, margin: 0,
      fontFace: F, fontSize: 14.5, bold: true, color: INK, valign: "middle",
    });
    s.addText(r[2], {
      x: M + 1.58, y: y + 0.58, w: 6.05, h: 0.42, isTextBox: true, margin: 0,
      fontFace: F, fontSize: 11.5, color: MUTED,
    });
  });

  const stats = [["8", "데스크 에이전트", "리서치3·집행1·통제3·간사1"], ["1", "원장 쓰기 주체", "data-ops 단독"],
                 ["6", "발행 전 게이트", "두 데스크가 거부권 보유"], ["5", "출처 등급", "1차·참고·방법론·사내·해석"]];
  stats.forEach((t, i) => {
    const x = 8.72 + (i % 2) * 2.02, y = 1.82 + Math.floor(i / 2) * 1.94;
    card(s, { x, y, w: 1.88, h: 1.78, fill: NAVY, line: null });
    s.addText(t[0], {
      x: x + 0.16, y: y + 0.22, w: 1.56, h: 0.62, isTextBox: true, margin: 0,
      fontFace: F, fontSize: 34, bold: true, color: GOLD,
    });
    s.addText(t[1], {
      x: x + 0.16, y: y + 0.86, w: 1.56, h: 0.3, isTextBox: true, margin: 0,
      fontFace: F, fontSize: 11.5, bold: true, color: WHITE,
    });
    s.addText(t[2], {
      x: x + 0.16, y: y + 1.16, w: 1.56, h: 0.5, isTextBox: true, margin: 0,
      fontFace: F, fontSize: 9.5, color: ICE,
    });
  });

  card(s, { x: M, y: 5.76, w: 7.85, h: 0.86, fill: "EDF1F9", line: "C6D2E8" });
  s.addText([
    { text: "자동화하는 것은 '읽기'이지 '결정'이 아니다.  ", options: { bold: true, color: NAVY } },
    { text: "에이전트가 늘어도 점수·등급·매매 시그널은 만들지 않는다. 회의에 올라가는 것은 쟁점이지 결론이 아니다.", options: { color: INK } },
  ], { x: M + 0.26, y: 5.9, w: 7.35, h: 0.6, isTextBox: true, margin: 0, fontFace: F, fontSize: 11.5 });

  footer(s, "근거 — CLAUDE.md '절대 깨지 말아야 할 것' 1~5 · stock-monitor/README.md 설계 원칙 1~4");
}

/* ══════════ 3. AS-IS ══════════ */
{
  const s = base(false);
  header(s, "AS-IS 진단", "지금 가진 것 — 측정 파이프라인은 이미 완성돼 있다",
         "새로 만들 것은 측정이 아니라, 측정 결과를 읽고 정렬하는 층이다.");

  const flow = [
    ["공식 API 5종", "KRX · DART · ECOS\nKIS · FRED", NAVY],
    ["ki.sqlite 원장", "사실만 담는다\n7개 테이블", NAVY_M],
    ["측정 함수", "처분소요일 · 집행\n시뮬 · 분위 · 매물대", NAVY_M],
    ["HTML 리포트", "§1~§8 · 외부 리소스 0\n절마다 출처 등급", NAVY_M],
    ["오프라인 회의", "사람이 결정한다", GOLD],
  ];
  const bw = 2.14, gap = 0.34;
  flow.forEach((f, i) => {
    const x = M + i * (bw + gap);
    card(s, { x, y: 2.0, w: bw, h: 1.62, fill: f[2], line: null });
    s.addText(f[0], {
      x: x + 0.14, y: 2.2, w: bw - 0.28, h: 0.34, isTextBox: true, margin: 0,
      fontFace: F, fontSize: 13, bold: true, color: WHITE, align: "center",
    });
    s.addText(f[1], {
      x: x + 0.12, y: 2.6, w: bw - 0.24, h: 0.86, isTextBox: true, margin: 0,
      fontFace: F, fontSize: 10, color: i === 4 ? "3A2E12" : ICE, align: "center",
    });
    if (i < 4) {
      s.addText("▶", {
        x: x + bw, y: 2.62, w: gap, h: 0.38, isTextBox: true, margin: 0,
        fontFace: F, fontSize: 13, bold: true, color: GOLD, align: "center", valign: "middle",
      });
    }
  });

  const st = [["8,684", "줄 · 단일 파일", "ki_monitor.py 하나가 수집·계산·리포트를 전부 한다"],
              ["5", "1차 출처 공식 API", "크롤링 없음 · 유료 벤더 없음 · 뉴스 본문 없음"],
              ["12", "편 채택 논문", "팩터마다 논문 키를 달고 나간다 (.papers.json)"],
              ["4", "개 핵심 질문", "q1 진척 · q2 처분여건 · q3 실행 · q4 시점"]];
  st.forEach((t, i) => {
    const x = M + i * (2.98 + 0.13);
    card(s, { x, y: 4.02, w: 2.98, h: 1.72 });
    s.addText(t[0], {
      x: x + 0.2, y: 4.22, w: 2.6, h: 0.62, isTextBox: true, margin: 0,
      fontFace: F, fontSize: 32, bold: true, color: NAVY,
    });
    s.addText(t[1], {
      x: x + 0.2, y: 4.86, w: 2.6, h: 0.28, isTextBox: true, margin: 0,
      fontFace: F, fontSize: 11.5, bold: true, color: GOLD,
    });
    s.addText(t[2], {
      x: x + 0.2, y: 5.16, w: 2.6, h: 0.5, isTextBox: true, margin: 0,
      fontFace: F, fontSize: 10, color: MUTED,
    });
  });

  card(s, { x: M, y: 5.94, w: CW, h: 0.68, fill: "EDF1F9", line: "C6D2E8" });
  s.addText([
    { text: "결론 — ", options: { bold: true, color: NAVY } },
    { text: "데이터·계산·검증(자체 검증 세트 128개)은 손댈 것이 없다. 부족한 것은 ", options: { color: INK } },
    { text: "산출물을 읽어 회의 쟁점으로 바꾸는 사람의 시간", options: { bold: true, color: RED } },
    { text: " 하나뿐이다.", options: { color: INK } },
  ], { x: M + 0.26, y: 6.06, w: CW - 0.5, h: 0.44, isTextBox: true, margin: 0, fontFace: F, fontSize: 12, valign: "middle" });

  footer(s, "출처 — 저장소 실측 (ki_monitor.py · .papers.json · CATALOG 31개 항목 · SECTIONS 18개 절)");
}

/* ══════════ 4. WHY ══════════ */
{
  const s = base(false);
  header(s, "WHY", "왜 에이전트화인가 — 병목은 계산이 아니라 독해다");

  const cols = [
    { t: "지금의 병목", c: RED, bg: "FBF0EF", ln: "E9CFCC", items: [
      ["읽는 사람이 한 명", "리포트는 매일 08:50에 나오지만, §1~§18을 끝까지 읽는 사람은 사실상 한 명이다."],
      ["85개 종목 × §5", "종목별 상세는 사람이 통독할 분량이 아니다. 결국 몇 종목만 보고 회의에 들어간다."],
      ["이어 붙이기가 수작업", "DART 공시 원문 · 채택 논문 · 매크로 일정을 종목에 연결하는 일은 전부 손이다."],
    ]},
    { t: "에이전트화 이후", c: GREEN, bg: "EEF5F1", ln: "CBDFD5", items: [
      ["데스크가 나눠 동시에 읽는다", "기업분석·계량·매크로·집행이 각자 자기 절만 맡아 병렬로 읽는다."],
      ["종목마다 초안이 붙는다", "측정값 옆에 '이 숫자가 무엇을 뜻할 수 있는가'가 등급 '해석'으로 함께 온다."],
      ["회의에는 쟁점만 올라온다", "간사 에이전트가 데스크 간 불일치와 결측만 추려 한 장으로 정렬한다."],
    ]},
  ];
  cols.forEach((col, ci) => {
    const x = M + ci * (6.02 + 0.26);
    card(s, { x, y: 1.72, w: 6.02, h: 4.24, fill: col.bg, line: col.ln });
    s.addText(col.t, {
      x: x + 0.3, y: 1.94, w: 5.4, h: 0.36, isTextBox: true, margin: 0,
      fontFace: F, fontSize: 17, bold: true, color: col.c,
    });
    col.items.forEach((it, i) => {
      const y = 2.48 + i * 1.14;
      numDot(s, x + 0.3, y + 0.02, i + 1, 0.38, col.c);
      s.addText(it[0], {
        x: x + 0.82, y, w: 4.95, h: 0.32, isTextBox: true, margin: 0,
        fontFace: F, fontSize: 13.5, bold: true, color: INK,
      });
      s.addText(it[1], {
        x: x + 0.82, y: y + 0.34, w: 4.95, h: 0.66, isTextBox: true, margin: 0,
        fontFace: F, fontSize: 11, color: MUTED,
      });
    });
  });

  card(s, { x: M, y: 6.1, w: CW, h: 0.66, fill: NAVY, line: null });
  s.addText([
    { text: "자동화 대상은 '독해와 정렬'이다. ", options: { bold: true, color: GOLD } },
    { text: "판단은 지금과 똑같이 회의에서 사람이 한다 — 이 경계가 흔들리면 에이전트화는 실패다.", options: { color: WHITE } },
  ], { x: M + 0.3, y: 6.22, w: CW - 0.6, h: 0.44, isTextBox: true, margin: 0, fontFace: F, fontSize: 12.5, valign: "middle" });
}

/* ══════════ 5. NON-NEGOTIABLE ══════════ */
{
  const s = base(false);
  header(s, "NON-NEGOTIABLE", "에이전트가 들어와도 깨지 않는 다섯 가지",
         "아래는 CLAUDE.md 에 이미 적혀 있는 규칙이다. 에이전트화는 이것을 완화하는 일이 아니라, 코드가 아닌 곳에서도 지키게 만드는 일이다.");

  const rules = [
    ["재기만 하고 판단하지 않는다", "점수·등급·매매 시그널을 만들지 않는다.", "에이전트 적용 — 산출물 판정 어휘 게이트 (게이트 ①)"],
    ["원장에는 측정한 사실만 쓴다", "추정·가정·장중 스냅샷(persist=False)을 넣지 않는다.", "에이전트 적용 — MCP 에 쓰기 도구 미노출 (구조적 차단)"],
    ["없는 값을 만들지 않는다", "못 구한 값은 None 과 사유. 0 으로 채우지 않는다.", "에이전트 적용 — 봉투 스키마의 null 허용 · 신선도 게이트 (④)"],
    ["재료에는 등급이 있다", "1차 · 참고 · 방법론 · 사내를 같은 표에 섞지 않는다.", "에이전트 적용 — 다섯 번째 등급 '해석' 신설 (게이트 ②)"],
    ["키와 대외비는 저장소 밖에 둔다", ".gitignore 는 약하다. git add -f 한 번이면 뚫린다.", "에이전트 적용 — 출력 scrub() 강제 · 유출 게이트 (⑤)"],
  ];
  rules.forEach((r, i) => {
    const y = 2.24 + i * 0.87;
    card(s, { x: M, y, w: CW, h: 0.75 });
    numDot(s, M + 0.24, y + 0.17, i + 1, 0.41, NAVY);
    s.addText(r[0], {
      x: M + 0.82, y: y + 0.09, w: 3.5, h: 0.3, isTextBox: true, margin: 0,
      fontFace: F, fontSize: 13.5, bold: true, color: NAVY, valign: "middle",
    });
    s.addText(r[1], {
      x: M + 0.82, y: y + 0.4, w: 4.6, h: 0.28, isTextBox: true, margin: 0,
      fontFace: F, fontSize: 10.5, color: MUTED, valign: "middle",
    });
    s.addShape(pres.ShapeType.roundRect, {
      x: M + 5.68, y: y + 0.16, w: 6.2, h: 0.44, rectRadius: 0.08,
      fill: { color: "EDF1F9" }, line: { type: "none" },
    });
    s.addText(r[2], {
      x: M + 5.82, y: y + 0.16, w: 5.95, h: 0.44, isTextBox: true, margin: 0,
      fontFace: F, fontSize: 11, bold: true, color: NAVY_M, valign: "middle",
    });
  });

  footer(s, "인용 — CLAUDE.md §1~§5 · selftest 128개가 ①·⑤의 코드 측면을 이미 검사한다");
}

/* ══════════ 6. CHINESE WALL ══════════ */
{
  const s = base(false);
  header(s, "CORE DESIGN", "정보교류차단 — 측정층과 판단층을 벽으로 나눈다",
         "증권사가 고유계정과 리서치를 벽으로 나누듯, 원장과 에이전트를 나눈다.");

  card(s, { x: M, y: 1.92, w: 5.1, h: 3.34, fill: NAVY, line: null });
  s.addText("측정층  MEASUREMENT", {
    x: M + 0.28, y: 2.12, w: 4.5, h: 0.3, isTextBox: true, margin: 0,
    fontFace: F, fontSize: 11.5, bold: true, color: GOLD, charSpacing: 1,
  });
  s.addText("ki.sqlite 원장", {
    x: M + 0.28, y: 2.44, w: 4.5, h: 0.42, isTextBox: true, margin: 0,
    fontFace: F, fontSize: 22, bold: true, color: WHITE,
  });
  [["공식 API 5종에서 받은 값만 들어간다", ""],
   ["쓰기 주체는 data-ops 단독", ""],
   ["KIS 장중 스냅샷은 persist=False", ""],
   ["오염되면 되돌릴 수 없다", ""]].forEach((t, i) => {
    s.addText("· " + t[0], {
      x: M + 0.28, y: 3.06 + i * 0.42, w: 4.5, h: 0.34, isTextBox: true, margin: 0,
      fontFace: F, fontSize: 12, color: ICE,
    });
  });
  s.addText("ingest · catchup · fundamentals", {
    x: M + 0.28, y: 4.82, w: 4.5, h: 0.28, isTextBox: true, margin: 0,
    fontFace: F, fontSize: 10, italic: true, color: "8FA3C8",
  });

  card(s, { x: 5.98, y: 1.92, w: 1.42, h: 3.34, fill: "1A1508", line: GOLD, r: 0.1 });
  s.addText("읽 기 전 용", {
    x: 5.98, y: 2.28, w: 1.42, h: 1.5, isTextBox: true, margin: 0,
    fontFace: F, fontSize: 16, bold: true, color: GOLD, align: "center",
  });
  s.addText("MCP\nki-ledger", {
    x: 5.98, y: 3.52, w: 1.42, h: 0.7, isTextBox: true, margin: 0,
    fontFace: F, fontSize: 12, bold: true, color: WHITE, align: "center",
  });
  s.addText("쓰기 도구\n없음", {
    x: 5.98, y: 4.3, w: 1.42, h: 0.6, isTextBox: true, margin: 0,
    fontFace: F, fontSize: 10.5, color: GOLD_L, align: "center",
  });

  card(s, { x: 7.98, y: 1.92, w: 4.75, h: 3.34, fill: CARD });
  s.addText("판단층  INTERPRETATION", {
    x: 8.26, y: 2.12, w: 4.2, h: 0.3, isTextBox: true, margin: 0,
    fontFace: F, fontSize: 11.5, bold: true, color: GOLD, charSpacing: 1,
  });
  s.addText("여덟 개 데스크", {
    x: 8.26, y: 2.44, w: 4.2, h: 0.42, isTextBox: true, margin: 0,
    fontFace: F, fontSize: 22, bold: true, color: NAVY,
  });
  const desks = ["기업분석", "계량분석", "매크로", "집행", "리스크", "준법감시", "데이터운영", "IC 간사"];
  desks.forEach((d, i) => {
    const x = 8.26 + (i % 2) * 2.14, y = 3.06 + Math.floor(i / 2) * 0.44;
    s.addShape(pres.ShapeType.roundRect, {
      x, y, w: 2.0, h: 0.36, rectRadius: 0.06,
      fill: { color: "EDF1F9" }, line: { type: "none" },
    });
    s.addText(d, {
      x: x + 0.1, y, w: 1.85, h: 0.36, isTextBox: true, margin: 0,
      fontFace: F, fontSize: 11, bold: true, color: NAVY_M, valign: "middle",
    });
  });
  s.addText("산출물 등급 = '해석' — 절대 1차가 되지 않는다", {
    x: 8.26, y: 4.86, w: 4.2, h: 0.28, isTextBox: true, margin: 0,
    fontFace: F, fontSize: 10.5, italic: true, color: RED,
  });

  const notes = [
    ["벽은 규칙이 아니라 구조다", "'쓰지 마라'라고 프롬프트에 적는 대신, 쓸 수 있는 도구를 만들지 않는다."],
    ["역류를 막는다", "에이전트의 해석이 다음 측정의 입력이 되면 오염이 순환한다. 봉투는 한 방향으로만 흐른다."],
    ["감사 가능하게 남긴다", "모든 데스크 산출물은 봉투째 저장된다. 나중에 '왜 그렇게 읽었는가'를 되짚을 수 있다."],
  ];
  notes.forEach((n, i) => {
    const x = M + i * 4.11;
    card(s, { x, y: 5.46, w: 3.94, h: 1.14, fill: "EDF1F9", line: "C6D2E8" });
    s.addText(n[0], {
      x: x + 0.22, y: 5.62, w: 3.5, h: 0.3, isTextBox: true, margin: 0,
      fontFace: F, fontSize: 12.5, bold: true, color: NAVY,
    });
    s.addText(n[1], {
      x: x + 0.22, y: 5.94, w: 3.55, h: 0.56, isTextBox: true, margin: 0,
      fontFace: F, fontSize: 10, color: MUTED,
    });
  });
}

/* ══════════ 7. ORG CHART ══════════ */
{
  const s = base(false);
  header(s, "TARGET ORG", "대형 증권사 조직을 그대로 옮긴다",
         "새 개념을 발명하지 않는다. 이미 검증된 분업과 견제 구조를 에이전트에 대응시킨다.");

  card(s, { x: 4.1, y: 1.70, w: 5.13, h: 0.54, fill: GOLD, line: null });
  s.addText("투자심의위원회 (IC)  ·  사람이 결정한다", {
    x: 4.1, y: 1.70, w: 5.13, h: 0.54, isTextBox: true, margin: 0,
    fontFace: F, fontSize: 14, bold: true, color: "2E2408", align: "center", valign: "middle",
  });
  s.addShape(pres.ShapeType.line, {
    x: 6.665, y: 2.24, w: 0, h: 0.20, line: { color: "9AA7BD", width: 1.5 },
  });
  card(s, { x: 4.66, y: 2.44, w: 4.01, h: 0.50, fill: NAVY, line: null });
  s.addText("ic-chair  ·  간사 — 통합·정렬 (판단하지 않는다)", {
    x: 4.66, y: 2.44, w: 4.01, h: 0.50, isTextBox: true, margin: 0,
    fontFace: F, fontSize: 11.5, bold: true, color: WHITE, align: "center", valign: "middle",
  });
  s.addShape(pres.ShapeType.line, {
    x: 6.665, y: 2.94, w: 0, h: 0.18, line: { color: "9AA7BD", width: 1.5 },
  });
  s.addShape(pres.ShapeType.line, {
    x: 1.86, y: 3.12, w: 9.61, h: 0, line: { color: "9AA7BD", width: 1.5 },
  });

  const units = [
    { t: "리서치본부", sub: "Research", c: NAVY, a: ["equity-analyst\n기업분석역", "quant-researcher\n계량분석역", "macro-strategist\n매크로전략역"] },
    { t: "트레이딩·집행", sub: "Execution", c: NAVY_M, a: ["execution-trader\n집행역"] },
    { t: "리스크관리본부", sub: "Risk", c: "5B4B8A", a: ["risk-officer\n리스크심사역"], veto: true },
    { t: "준법감시", sub: "Compliance", c: RED, a: ["compliance-officer\n준법감시역"], veto: true },
    { t: "데이터·IT", sub: "Operations", c: GREEN, a: ["data-ops\n원장운영역"], write: true },
  ];
  const uw = 2.29, ug = 0.185;
  units.forEach((u, i) => {
    const x = M + i * (uw + ug);
    s.addShape(pres.ShapeType.line, {
      x: x + uw / 2, y: 3.12, w: 0, h: 0.18, line: { color: "9AA7BD", width: 1.5 },
    });
    card(s, { x, y: 3.30, w: uw, h: 0.58, fill: u.c, line: null });
    s.addText(u.t, {
      x: x + 0.06, y: 3.36, w: uw - 0.12, h: 0.28, isTextBox: true, margin: 0,
      fontFace: F, fontSize: 12.5, bold: true, color: WHITE, align: "center",
    });
    s.addText(u.sub, {
      x: x + 0.06, y: 3.62, w: uw - 0.12, h: 0.22, isTextBox: true, margin: 0,
      fontFace: F, fontSize: 9, color: ICE, align: "center", charSpacing: 1,
    });
    u.a.forEach((a, j) => {
      const y = 4.02 + j * 0.68;
      card(s, { x, y, w: uw, h: 0.60, fill: CARD, line: u.veto ? GOLD : LINE });
      s.addText(a, {
        x: x + 0.06, y, w: uw - 0.12, h: 0.60, isTextBox: true, margin: 0,
        fontFace: F, fontSize: 10.5, bold: true, color: INK, align: "center", valign: "middle",
      });
    });
    const badgeY = 4.02 + u.a.length * 0.68 + 0.04;
    if (u.veto) {
      s.addText("거부권", {
        x: x + 0.06, y: badgeY, w: uw - 0.12, h: 0.26, isTextBox: true, margin: 0,
        fontFace: F, fontSize: 9.5, bold: true, color: GOLD, align: "center",
      });
    }
    if (u.write) {
      s.addText("원장 쓰기 단독", {
        x: x + 0.06, y: badgeY, w: uw - 0.12, h: 0.26, isTextBox: true, margin: 0,
        fontFace: F, fontSize: 9.5, bold: true, color: GREEN, align: "center",
      });
    }
  });

  card(s, { x: M, y: 6.42, w: CW, h: 0.62, fill: "EDF1F9", line: "C6D2E8" });
  s.addText([
    { text: "견제 구조 —  ", options: { bold: true, color: NAVY } },
    { text: "리서치가 만든 해석은 리스크와 준법감시 ", options: { color: INK } },
    { text: "두 곳을 모두 통과", options: { bold: true, color: RED } },
    { text: "해야 IC 에 올라간다(4-eyes). 원장을 고칠 수 있는 곳은 데이터·IT 하나뿐이고, 그곳은 해석을 쓰지 않는다.", options: { color: INK } },
  ], { x: M + 0.28, y: 6.42, w: CW - 0.56, h: 0.62, isTextBox: true, margin: 0, fontFace: F, fontSize: 11, valign: "middle" });
}

/* ══════════ 8 & 9. AGENT CATALOG ══════════ */
function catalogSlide(kicker, title, sub, rows, note) {
  const s = base(false);
  header(s, kicker, title, sub);
  const head = ["에이전트 · 직책", "무엇을 읽는가 (입력)", "무엇을 내는가 (산출)", "근거 · 제약"];
  const body = [head.map(h => ({
    text: h, options: { bold: true, color: WHITE, fill: { color: NAVY }, fontSize: 11.5, valign: "middle" },
  }))];
  rows.forEach(r => {
    body.push([
      { text: r[0], options: { bold: true, color: NAVY, fontSize: 11, valign: "middle" } },
      { text: r[1], options: { color: INK, fontSize: 10, valign: "middle" } },
      { text: r[2], options: { color: INK, fontSize: 10, valign: "middle" } },
      { text: r[3], options: { color: MUTED, fontSize: 9.5, italic: true, valign: "middle" } },
    ]);
  });
  s.addTable(body, {
    x: M, y: 1.84, w: CW, colW: [2.5, 3.35, 3.35, 2.89],
    border: { type: "solid", color: LINE, pt: 1 },
    fill: { color: CARD }, fontFace: F, rowH: 0.8, margin: 0.09,
    autoPage: false,
  });
  card(s, { x: M, y: 6.06, w: CW, h: 0.76, fill: "EDF1F9", line: "C6D2E8" });
  s.addText(note, {
    x: M + 0.28, y: 6.06, w: CW - 0.56, h: 0.76, isTextBox: true, margin: 0,
    fontFace: F, fontSize: 11, color: INK, valign: "middle",
  });
  return s;
}

catalogSlide("AGENT CATALOG  1/2", "데스크 정의 — 리서치본부 · 트레이딩",
  "각 데스크는 리포트의 특정 절과 네 개 질문 중 하나에 묶인다. 담당 범위 밖은 읽지 않는다.",
  [
    ["equity-analyst\n기업분석역",
     "ledger.facts · ledger.disclosure\nDART 공시 원문 링크",
     "§5 종목별 코멘트 초안\n공시 이벤트의 사실관계 정리",
     "공시 원문만 인용. 제목 요약 금지 —\n발행조건·전환가·리픽싱은 원문에 있다"],
    ["quant-researcher\n계량분석역",
     "ledger.factors · ledger.candles\n.papers.json 채택본 12편",
     "§6 팩터 해설 + limits\n논문 채택 심사 (하루 1편)",
     "채택본에 없는 논문 인용 금지.\n논문이 주장하지 않는 것을 함께 낸다"],
    ["macro-strategist\n매크로전략역",
     "ledger.macro (ECOS 100대)\nledger.calendar · FRED",
     "§4·§7 국면 서술 (수준 아닌 분위)\n금통위·만기·락업 일정 정렬",
     "락업은 '추정' 등급 고정 —\n의무보유확약으로 서술하면 게이트 탈락"],
    ["execution-trader\n집행역",
     "ledger.facts (거래량·거래대금)\n§3 집행 시뮬레이션 결과",
     "매도 규칙 4종 비교 해설\n참여율·충격 가정의 민감도",
     "주문 API 호출 불가 (OrderNotAllowed).\n평균과 중앙값을 반드시 함께 낸다"],
  ],
  "리서치 세 데스크는 서로의 산출물을 보지 않는다. 같은 결론으로 수렴하면 교차검증의 의미가 사라지기 때문이다. 불일치는 지우지 않고 IC 간사가 쟁점으로 올린다.");

catalogSlide("AGENT CATALOG  2/2", "데스크 정의 — 통제 · 운영 · 의결",
  "이쪽은 새로운 해석을 만들지 않는다. 만들어진 해석을 검사하고, 원장을 유지하고, 회의에 올린다.",
  [
    ["risk-officer\n리스크심사역  (거부권)",
     "리서치·집행 데스크의 봉투 전량\nledger.facts 원본",
     "숫자 재검산 (교차검산 · 항등식)\n집중도 · 상관 · 가정 스트레스",
     "인용된 값이 원장 값과 다르면 즉시 반려.\n숫자를 고쳐 주지 않는다 — 돌려보낸다"],
    ["compliance-officer\n준법감시역  (거부권)",
     "발행 직전의 모든 산출물\nSECTION_SOURCES · CATALOG",
     "여섯 게이트 판정 · 발행 승인/반려\n대외비·자격증명 유출 검사",
     "판정 어휘·등급 혼입·미인용 논문·\n신선도 초과 중 하나라도 걸리면 발행 중단"],
    ["data-ops\n원장운영역  (쓰기 단독)",
     "KRX·DART·ECOS·KIS·FRED\ndiagnose · catalog · .api_fields.json",
     "ingest · catchup · fundamentals\nstale_days · 결측 · 필드매핑 감시",
     "해석을 만들지 않는다. 이 데스크만\nki.sqlite 에 쓸 수 있고, 사실만 쓴다"],
    ["ic-chair\n투자심의위원회 간사",
     "게이트를 통과한 봉투 전량",
     "회의자료 한 장으로 조립\n데스크 간 불일치·결측을 쟁점화",
     "종합 의견·권고를 쓰지 않는다.\n쟁점을 정렬할 뿐, 결정은 사람이 한다"],
  ],
  "거부권은 실제로 발행을 멈추는 권한이다. 두 통제 데스크 중 하나라도 반려하면 그날 회의자료에서 해당 절이 통째로 빠지고, 그 자리에는 '반려됨 — 사유'가 남는다. 조용히 통과시키는 것이 가장 위험하다.");

/* ══════════ 10. RBAC ══════════ */
{
  const s = base(false);
  header(s, "PERMISSIONS", "권한 매트릭스 — 누가 무엇을 할 수 있는가",
         "권한은 프롬프트가 아니라 도구 노출과 훅으로 강제한다. 아래는 실제로 부여할 도구 목록이다.");

  const cols = ["원장 읽기", "원장 쓰기", "외부 API 호출", "KIS 주문", "회의자료 발행", "거부권"];
  const M_ = {
    "equity-analyst": ["●", "✕", "△ DART 원문", "✕", "✕", "✕"],
    "quant-researcher": ["●", "✕", "△ 논문 4곳", "✕", "✕", "✕"],
    "macro-strategist": ["●", "✕", "△ ECOS·FRED", "✕", "✕", "✕"],
    "execution-trader": ["●", "✕", "✕", "✕", "✕", "✕"],
    "risk-officer": ["●", "✕", "✕", "✕", "✕", "●"],
    "compliance-officer": ["●", "✕", "✕", "✕", "●", "●"],
    "data-ops": ["●", "●", "● 5종 전부", "✕", "✕", "✕"],
    "ic-chair": ["●", "✕", "✕", "✕", "△ 초안만", "✕"],
  };
  const head = [{ text: "에이전트", options: { bold: true, color: WHITE, fill: { color: NAVY }, fontSize: 11, align: "left" } }]
    .concat(cols.map(c => ({ text: c, options: { bold: true, color: WHITE, fill: { color: NAVY }, fontSize: 10.5, align: "center" } })));
  const body = [head];
  Object.keys(M_).forEach(k => {
    const row = [{ text: k, options: { bold: true, color: NAVY, fontSize: 10.5, align: "left", valign: "middle" } }];
    M_[k].forEach(v => {
      const yes = v.indexOf("●") === 0, no = v === "✕";
      row.push({ text: v, options: {
        fontSize: no ? 11 : 10, bold: yes, align: "center", valign: "middle",
        color: no ? "B9C2D2" : (yes ? GREEN : GOLD),
        fill: { color: no ? "FAFBFD" : (yes ? "EAF4EF" : "FBF6EA") },
      }});
    });
    body.push(row);
  });
  s.addTable(body, {
    x: M, y: 1.86, w: CW, colW: [2.62, 1.28, 1.28, 1.85, 1.28, 1.62, 1.16],
    border: { type: "solid", color: LINE, pt: 1 },
    fill: { color: CARD }, fontFace: F, rowH: 0.39, margin: 0.07, autoPage: false,
  });

  const boxes = [
    ["KIS 주문 열은 전부 ✕", "같은 서버에 주문 API 가 있지만 화이트리스트에 없다. 코드가 OrderNotAllowed 로 막고 selftest 가 매번 검사한다. 에이전트에게도 이 도구는 만들지 않는다.", RED],
    ["원장 쓰기는 한 칸뿐", "data-ops 만 ●. 나머지 일곱은 MCP 읽기 도구만 받는다. '쓰지 말라'는 지시가 아니라 쓸 수단이 없는 상태다.", GREEN],
    ["△ 는 화이트리스트 호출", "해당 데스크가 부를 수 있는 엔드포인트를 명시 열거한다. 목록 밖 호출은 PreToolUse 훅이 차단한다.", GOLD],
  ];
  boxes.forEach((b, i) => {
    const x = M + i * 4.11;
    card(s, { x, y: 5.74, w: 3.94, h: 1.2 });
    s.addShape(pres.ShapeType.ellipse, { x: x + 0.22, y: 5.925, w: 0.16, h: 0.16, fill: { color: b[2] }, line: { type: "none" } });
    s.addText(b[0], {
      x: x + 0.48, y: 5.86, w: 3.3, h: 0.3, isTextBox: true, margin: 0,
      fontFace: F, fontSize: 12, bold: true, color: NAVY,
    });
    s.addText(b[1], {
      x: x + 0.22, y: 6.2, w: 3.56, h: 0.66, isTextBox: true, margin: 0,
      fontFace: F, fontSize: 9.5, color: MUTED,
    });
  });
}

/* ══════════ 11. ENVELOPE ══════════ */
{
  const s = base(false);
  header(s, "PROTOCOL", "데스크 사이를 오가는 것은 숫자가 아니라 '봉투'다",
         "숫자만 넘기면 받는 쪽에서 가정과 한계가 사라진다. 이 도구가 이미 facts 로 지키는 규칙을 에이전트 간 통신에 그대로 적용한다.");

  card(s, { x: M, y: 1.94, w: 6.7, h: 4.06, fill: "12203C", line: null });
  const code = [
    '{',
    '  "claim":        "처분 소요일수 12.4 영업일",',
    '  "value":        12.4,',
    '  "unit":         "business_days",',
    '  "asof":         "2026-09-11",',
    '  "stale_days":   2,',
    '  "source_grade": "해석",',
    '  "sources":      ["KRX/일별매매정보"],',
    '  "method": {',
    '    "paper":   "amihud2002",',
    '    "assumes": { "participation": 0.15 }',
    '  },',
    '  "limits": [',
    '    "논문 표본은 미국 상장주 — 코스닥",',
    '    "소형주 외삽의 근거가 아니다",',
    '    "평균 기준. 중앙값 기준은 18.1일"',
    '  ],',
    '  "desk":       "execution-trader",',
    '  "reviewed_by": ["risk", "compliance"]',
    '}',
  ].join("\n");
  s.addText(code, {
    x: M + 0.26, y: 2.08, w: 6.2, h: 3.8, isTextBox: true, margin: 0,
    fontFace: FM, fontSize: 9.5, color: "C9E2FF", lineSpacing: 12.4,
  });

  const fields = [
    ["source_grade", "1차 · 참고 · 방법론 · 사내 · 해석", "다섯 번째 등급 '해석'을 신설한다. 에이전트가 쓴 문장은 무엇을 근거로 삼았든 '해석'이며, 승격 경로가 없다."],
    ["asof · stale_days", "기준일과 며칠 묵었는가", "몇 주 묵은 종가가 현재가 행세를 하는 것이 가장 조용한 실패다. 봉투에 없으면 게이트에서 반려된다."],
    ["method.paper", "채택본 12편 중 어느 것인가", "팩터는 논문 키를 달고 나간다. 채택본에 없는 키는 게이트 ③ 이 잡는다."],
    ["limits", "그 논문이 주장하지 않는 것", "가장 흔한 사고는 논문이 말한 적 없는 것을 말했다고 읽는 것이다. 비어 있으면 발행되지 않는다."],
  ];
  fields.forEach((f, i) => {
    const y = 1.94 + i * 1.04;
    card(s, { x: 7.52, y, w: 5.2, h: 0.94 });
    s.addText(f[0], {
      x: 7.74, y: y + 0.11, w: 2.3, h: 0.26, isTextBox: true, margin: 0,
      fontFace: FM, fontSize: 11, bold: true, color: NAVY,
    });
    s.addText(f[1], {
      x: 9.95, y: y + 0.12, w: 2.6, h: 0.24, isTextBox: true, margin: 0,
      fontFace: F, fontSize: 9.5, color: GOLD, align: "right",
    });
    s.addText(f[2], {
      x: 7.74, y: y + 0.4, w: 4.8, h: 0.48, isTextBox: true, margin: 0,
      fontFace: F, fontSize: 9.5, color: MUTED,
    });
  });

  card(s, { x: M, y: 6.12, w: CW, h: 0.68, fill: NAVY, line: null });
  s.addText([
    { text: "봉투는 한 방향으로만 흐른다. ", options: { bold: true, color: GOLD } },
    { text: "측정층 → 판단층 → 통제 → IC. 역류(해석이 원장으로 되돌아가는 것)는 스키마에도 도구에도 경로가 없다.", options: { color: WHITE } },
  ], { x: M + 0.3, y: 6.24, w: CW - 0.6, h: 0.44, isTextBox: true, margin: 0, fontFace: F, fontSize: 12, valign: "middle" });
}

/* ══════════ 12. TECH STACK ══════════ */
{
  const s = base(false);
  header(s, "TECH STACK", "구현 — 8,684줄을 다시 쓰지 않고 감싼다",
         "ki_monitor.py 는 한 줄도 고치지 않는다. 이미 있는 JSON 출력 명령(facts · candles · factors · calendar · macro)이 그대로 인터페이스가 된다.");

  const layers = [
    ["의결", "ic-chair 오케스트레이터", "Claude Agent SDK · 서브에이전트 팬아웃/팬인", NAVY, "게이트 통과분만 조립"],
    ["데스크", ".claude/agents/*.md  8개", "에이전트별 시스템 프롬프트 · 허용 도구 목록 · 담당 절", NAVY_M, "도구 목록이 곧 권한"],
    ["지식", ".claude/skills/  4종", "source-grading · envelope-schema · paper-adoption · compliance-gate", "5B4B8A", "규칙을 프롬프트에 흩지 않는다"],
    ["도구", "MCP 서버  ki-ledger (stdio · Python)", "ki_monitor.py 의 읽기 명령만 감싼 7개 도구. 쓰기 도구 없음", GREEN, "벽이 세워지는 지점"],
    ["통제", "Hooks  PreToolUse / PostToolUse", "화이트리스트 밖 호출 차단 · 모든 출력에 scrub() 강제 · 봉투 스키마 검증", RED, "코드가 지키는 마지막 선"],
    ["실행", "ki_monitor.py  ·  SCHEDULE.cmd", "변경 없음. 07:30 · 08:50 · 16:10 자동 실행도 그대로", "6B7688", "손대지 않는다"],
  ];
  layers.forEach((l, i) => {
    const y = 2.06 + i * 0.735;
    card(s, { x: M, y, w: CW, h: 0.64 });
    s.addShape(pres.ShapeType.roundRect, {
      x: M + 0.14, y: y + 0.12, w: 0.86, h: 0.4, rectRadius: 0.07,
      fill: { color: l[3] }, line: { type: "none" },
    });
    s.addText(l[0], {
      x: M + 0.14, y: y + 0.12, w: 0.86, h: 0.4, isTextBox: true, margin: 0,
      fontFace: F, fontSize: 11, bold: true, color: WHITE, align: "center", valign: "middle",
    });
    s.addText(l[1], {
      x: M + 1.14, y: y + 0.06, w: 3.9, h: 0.52, isTextBox: true, margin: 0,
      fontFace: F, fontSize: 12.5, bold: true, color: INK, valign: "middle",
    });
    s.addText(l[2], {
      x: M + 5.12, y: y + 0.06, w: 4.55, h: 0.52, isTextBox: true, margin: 0,
      fontFace: F, fontSize: 10, color: MUTED, valign: "middle",
    });
    s.addText(l[4], {
      x: M + 9.75, y: y + 0.06, w: 2.3, h: 0.52, isTextBox: true, margin: 0,
      fontFace: F, fontSize: 10, bold: true, color: l[3], align: "right", valign: "middle",
    });
  });

  card(s, { x: M, y: 6.5, w: CW, h: 0.52, fill: "EDF1F9", line: "C6D2E8" });
  s.addText("추가되는 파이썬 코드는 MCP 서버 한 개(약 200줄)와 게이트 검사기 한 개뿐이다. 나머지는 마크다운 설정 파일이다.", {
    x: M + 0.28, y: 6.5, w: CW - 0.56, h: 0.52, isTextBox: true, margin: 0,
    fontFace: F, fontSize: 11, color: INK, valign: "middle",
  });
}

/* ══════════ 13. MCP SERVER ══════════ */
{
  const s = base(false);
  header(s, "MCP DESIGN", "ki-ledger — 벽이 실제로 세워지는 곳",
         "노출하는 도구가 곧 권한이다. 아래 일곱 개 외에는 존재하지 않으므로, 에이전트는 원장을 고칠 방법 자체가 없다.");

  const rows = [
    ["ledger.facts", "facts --codes", "종목별 관측 사실 전량 (계산 없음)", "○"],
    ["ledger.candles", "candles --code --days", "수정주가 일봉 · 빈 봉은 버린다", "○"],
    ["ledger.factors", "factors --codes --win", "팩터 값 + 논문 키 + limits", "○"],
    ["ledger.calendar", "calendar --days", "일정 + 등급(공표·규칙·추정)", "○"],
    ["ledger.macro", "macro --limit", "ECOS 100대 통계 · 통계명·단위·시점 보존", "○"],
    ["ledger.disclosure", "facts --with-disclosures", "DART 공시 목록 + 접수번호 원문 링크", "○"],
    ["ledger.quality", "(신규) 얇은 래퍼", "stale_days · 결측 항목 · 필드매핑 검증 상태", "○"],
  ];
  const head = ["MCP 도구", "대응 CLI (이미 존재)", "반환", "읽기\n전용"].map(h => ({
    text: h, options: { bold: true, color: WHITE, fill: { color: NAVY }, fontSize: 11, valign: "middle", align: h.indexOf("읽기") === 0 ? "center" : "left" },
  }));
  const body = [head];
  rows.forEach(r => body.push([
    { text: r[0], options: { fontFace: FM, bold: true, color: NAVY, fontSize: 10.5, valign: "middle" } },
    { text: r[1], options: { fontFace: FM, color: MUTED, fontSize: 10, valign: "middle" } },
    { text: r[2], options: { color: INK, fontSize: 10.5, valign: "middle" } },
    { text: r[3], options: { bold: true, color: GREEN, fontSize: 13, align: "center", valign: "middle" } },
  ]));
  s.addTable(body, {
    x: M, y: 1.96, w: 7.62, colW: [1.92, 2.28, 2.62, 0.8],
    border: { type: "solid", color: LINE, pt: 1 },
    fill: { color: CARD }, fontFace: F, rowH: 0.475, margin: 0.08, autoPage: false,
  });

  card(s, { x: 8.42, y: 1.96, w: 4.3, h: 1.86, fill: RED_L, line: "E9CFCC" });
  s.addText("노출하지 않는 것", {
    x: 8.66, y: 2.14, w: 3.8, h: 0.3, isTextBox: true, margin: 0,
    fontFace: F, fontSize: 13, bold: true, color: RED,
  });
  ["ingest · catchup · fundamentals", "macro-us · import-keys · migrate-keys", "watch · live · eod (알림 발송)", "KIS 주문 계열 전부"].forEach((t, i) => {
    s.addText("✕  " + t, {
      x: 8.66, y: 2.5 + i * 0.31, w: 3.85, h: 0.28, isTextBox: true, margin: 0,
      fontFace: F, fontSize: 10.5, color: INK,
    });
  });

  card(s, { x: 8.42, y: 3.98, w: 4.3, h: 1.44, fill: CARD });
  s.addText("data-ops 는 예외다", {
    x: 8.66, y: 4.14, w: 3.8, h: 0.3, isTextBox: true, margin: 0,
    fontFace: F, fontSize: 13, bold: true, color: GREEN,
  });
  s.addText("원장운영역만 MCP 가 아니라 Bash 로 ki_monitor.py 를 직접 부른다. 대신 이 데스크에는 해석을 쓰는 권한이 없고, 산출물은 '적재 결과'와 '품질 경고'뿐이다.", {
    x: 8.66, y: 4.48, w: 3.85, h: 0.84, isTextBox: true, margin: 0,
    fontFace: F, fontSize: 10, color: MUTED,
  });

  card(s, { x: 8.42, y: 5.58, w: 4.3, h: 1.2, fill: NAVY, line: null });
  s.addText("네트워크를 쓰지 않는다", {
    x: 8.66, y: 5.74, w: 3.8, h: 0.28, isTextBox: true, margin: 0,
    fontFace: F, fontSize: 12.5, bold: true, color: GOLD,
  });
  s.addText("일곱 도구 전부 원장만 읽는다. 오래됐으면 stale_days 로 알릴 뿐, 몰래 새로 받아오지 않는다 — facts 가 이미 지키는 규칙이다.", {
    x: 8.66, y: 6.06, w: 3.85, h: 0.62, isTextBox: true, margin: 0,
    fontFace: F, fontSize: 10, color: ICE,
  });

  footer(s, "기존 규약 유지 — stdout 은 JSON 만, 진단 메시지는 전부 stderr");
}

/* ══════════ 14. DAILY TIMELINE ══════════ */
{
  const s = base(false);
  header(s, "OPERATIONS", "하루 운영 — 기존 자동 실행 시각을 그대로 쓴다",
         "SCHEDULE.cmd 의 07:30 · 08:50 · 16:10 은 바꾸지 않는다. 그 사이에 데스크 시간을 끼워 넣는다.");

  const stops = [
    ["07:30", "논문 수확 · 채택 심사", "quant-researcher", "네 곳(arXiv·S2·OpenAlex·Crossref)에서 후보를 쌓고, Crossref 재대조를 통과한 것만 하루 최대 1편 채택", NAVY],
    ["08:50", "아침 리포트 + 데스크 초안", "리서치 3 · 집행 1", "리포트 생성 직후 네 데스크가 병렬로 자기 절을 읽고 봉투를 낸다. 서로의 산출은 보지 않는다", NAVY_M],
    ["09:00\n~15:30", "장중 감시 (읽기만)", "data-ops", "KIS 스냅샷은 persist=False — 화면에만 뜨고 원장에는 쓰지 않는다. 데스크는 장중에 돌지 않는다", "5B4B8A"],
    ["16:10", "종가 적재 · 품질 점검", "data-ops 단독", "그날의 유일한 원장 쓰기. catchup 으로 밀린 영업일을 채우고 stale_days 를 갱신한다", GREEN],
    ["17:00", "게이트 → IC 자료 조립", "통제 2 · 간사 1", "여섯 게이트를 돌리고, 통과한 봉투만 한 장으로 조립한다. 반려분은 '반려됨 — 사유'로 남는다", GOLD],
  ];
  const bw = 2.36, bg2 = 0.12;
  stops.forEach((st, i) => {
    const x = M + i * (bw + bg2);
    card(s, { x, y: 2.1, w: bw, h: 0.74, fill: st[4], line: null });
    s.addText(st[0], {
      x, y: 2.1, w: bw, h: 0.74, isTextBox: true, margin: 0,
      fontFace: F, fontSize: st[0].indexOf("\n") >= 0 ? 15 : 21, bold: true,
      color: i === 4 ? "2E2408" : WHITE, align: "center", valign: "middle",
    });
    card(s, { x, y: 2.98, w: bw, h: 3.06 });
    s.addText(st[1], {
      x: x + 0.16, y: 3.16, w: bw - 0.32, h: 0.56, isTextBox: true, margin: 0,
      fontFace: F, fontSize: 13, bold: true, color: NAVY,
    });
    s.addShape(pres.ShapeType.roundRect, {
      x: x + 0.16, y: 3.78, w: bw - 0.32, h: 0.3, rectRadius: 0.06,
      fill: { color: "EDF1F9" }, line: { type: "none" },
    });
    s.addText(st[2], {
      x: x + 0.24, y: 3.78, w: bw - 0.48, h: 0.3, isTextBox: true, margin: 0,
      fontFace: F, fontSize: 9.5, bold: true, color: NAVY_M, valign: "middle",
    });
    s.addText(st[3], {
      x: x + 0.16, y: 4.2, w: bw - 0.32, h: 1.66, isTextBox: true, margin: 0,
      fontFace: F, fontSize: 10, color: MUTED,
    });
  });

  card(s, { x: M, y: 6.2, w: CW, h: 0.62, fill: "EDF1F9", line: "C6D2E8" });
  s.addText([
    { text: "장중에 데스크를 돌리지 않는 이유 — ", options: { bold: true, color: NAVY } },
    { text: "일봉 장부 위에 세운 해석을 장중 값과 섞으면, 무엇을 근거로 읽었는지가 시각마다 달라진다. 하루 한 번, 같은 기준일 위에서만 읽는다.", options: { color: INK } },
  ], { x: M + 0.28, y: 6.2, w: CW - 0.56, h: 0.62, isTextBox: true, margin: 0, fontFace: F, fontSize: 11, valign: "middle" });
}

/* ══════════ 15. GATES ══════════ */
{
  const s = base(false);
  header(s, "GOVERNANCE", "발행 전 여섯 개의 게이트를 통과해야 한다",
         "기존 자체 검증 128개는 그대로 둔다. 게이트는 코드가 아니라 '에이전트가 쓴 문장'을 검사하는 층으로 그 위에 얹는다.");

  const gates = [
    ["판정 어휘", "산출물에 점수·등급·목표주가·매수/매도 어휘가 있는가", "발견 시 해당 문장 삭제 후 반려", RED],
    ["출처 등급", "모든 주장에 grade 가 있는가 · '해석'이 '1차'로 승격되지 않았는가", "등급 없는 주장은 발행 차단", GOLD],
    ["논문 실재", "인용 키가 .papers.json 채택본에 있는가 · limits 가 비어 있지 않은가", "미채택 논문 인용 시 즉시 반려", NAVY],
    ["신선도", "asof · stale_days 가 붙어 있는가 · 임계일(기본 3영업일)을 넘지 않았는가", "초과 시 값 대신 '데이터 없음'", NAVY_M],
    ["유출 검사", "키·URL·포트폴리오사 실명이 산출물에 남았는가 (scrub())", "한 건이라도 걸리면 전체 발행 중단", "5B4B8A"],
    ["4-eyes", "리스크와 준법감시 양쪽이 승인했는가", "한 곳이라도 반려하면 해당 절 제외", GREEN],
  ];
  gates.forEach((g, i) => {
    const x = M + (i % 3) * 4.11, y = 2.16 + Math.floor(i / 3) * 2.06;
    card(s, { x, y, w: 3.94, h: 1.88 });
    numDot(s, x + 0.24, y + 0.24, i + 1, 0.44, g[3]);
    s.addText("게이트 " + (i + 1), {
      x: x + 0.8, y: y + 0.22, w: 2.9, h: 0.24, isTextBox: true, margin: 0,
      fontFace: F, fontSize: 9.5, bold: true, color: g[3], charSpacing: 1,
    });
    s.addText(g[0], {
      x: x + 0.8, y: y + 0.44, w: 2.9, h: 0.3, isTextBox: true, margin: 0,
      fontFace: F, fontSize: 15, bold: true, color: NAVY,
    });
    s.addText(g[1], {
      x: x + 0.24, y: y + 0.86, w: 3.48, h: 0.6, isTextBox: true, margin: 0,
      fontFace: F, fontSize: 10, color: INK,
    });
    s.addShape(pres.ShapeType.roundRect, {
      x: x + 0.24, y: y + 1.44, w: 3.48, h: 0.32, rectRadius: 0.06,
      fill: { color: "F1F4FA" }, line: { type: "none" },
    });
    s.addText("실패 시 —  " + g[2], {
      x: x + 0.36, y: y + 1.44, w: 3.28, h: 0.32, isTextBox: true, margin: 0,
      fontFace: F, fontSize: 9.5, bold: true, color: MUTED, valign: "middle",
    });
  });

  card(s, { x: M, y: 6.36, w: CW, h: 0.56, fill: NAVY, line: null });
  s.addText([
    { text: "게이트는 통계가 아니라 차단기다. ", options: { bold: true, color: GOLD } },
    { text: "'대체로 지켜졌다'는 판정이 없다. 통과 아니면 반려이고, 반려된 절은 회의자료에서 빈칸이 아니라 '반려됨 — 사유'로 보인다.", options: { color: WHITE } },
  ], { x: M + 0.3, y: 6.36, w: CW - 0.6, h: 0.56, isTextBox: true, margin: 0, fontFace: F, fontSize: 11.5, valign: "middle" });
}

/* ══════════ 16. RISKS ══════════ */
{
  const s = base(false);
  header(s, "RISK REGISTER", "리스크와 완화 — 가장 급한 것은 에이전트가 아니다",
         "P0 는 이번 방안과 무관하게 오늘 처리해야 한다. 압축 파일 안에서 실제로 발견된 사항이다.");

  const risks = [
    ["P0", "자격증명 평문 노출", "env.txt 에 KRX·DART·ECOS·FRED·KIS 6종 키가 평문으로 있다. 파일명이 .env 가 아니어서 .gitignore 어떤 규칙에도 안 걸린다.", "즉시 폐기·재발급 → 저장소 밖(%USERPROFILE%\\Stock-Agent-keys\\.env)으로 이전 → .gitignore 에 env.txt 추가", RED],
    ["높음", "환각 — 없는 값 생성", "원장에 없는 값을 그럴듯하게 채우는 것이 LLM 의 기본 실패 양식이다. 0 으로 채우는 것보다 나쁘다.", "봉투 스키마가 null 을 허용하고 근거 필드를 필수로 한다 + 게이트 ④ 신선도", NAVY],
    ["높음", "등급 혼입 — 해석이 사실로", "에이전트 문장이 §5 표에서 측정값과 같은 무게로 읽히면, 이 도구가 막으려던 실패가 재현된다.", "'해석' 등급 신설 + 게이트 ② + 리포트에서 별도 블록으로 분리 렌더", GOLD],
    ["치명·비가역", "원장 오염", "추정치가 ki.sqlite 에 한 번 들어가면 다음 측정이 오염되고 되돌릴 수 없다.", "MCP 에 쓰기 도구 미노출 + data-ops 단독 권한 + PreToolUse 훅 차단", "5B4B8A"],
    ["중", "유사투자자문 규제", "권고·목표가를 생성하는 순간 산출물의 성격이 바뀐다.", "권고 미생성 원칙 유지 + 배포통제 배너(STAGE) + 내부 검토용 고지 유지", NAVY_M],
    ["중", "비용 · 지연", "종목 85개 × 데스크 4개를 매일 돌리면 호출량이 선형으로 는다.", "데스크별 모델 등급 분리 · 변동 종목만 증분 처리 · 17:00 배치 일괄 실행", GREEN],
  ];
  const head = ["등급", "리스크", "무엇이 문제인가", "완화"].map((h, i) => ({
    text: h, options: { bold: true, color: WHITE, fill: { color: NAVY }, fontSize: 11, valign: "middle", align: i === 0 ? "center" : "left" },
  }));
  const body = [head];
  risks.forEach(r => body.push([
    { text: r[0], options: { bold: true, color: WHITE, fill: { color: r[4] }, fontSize: 10, align: "center", valign: "middle" } },
    { text: r[1], options: { bold: true, color: r[0] === "P0" ? RED : NAVY, fontSize: 11, valign: "middle" } },
    { text: r[2], options: { color: INK, fontSize: 9, valign: "middle" } },
    { text: r[3], options: { color: MUTED, fontSize: 9, valign: "middle" } },
  ]));
  s.addTable(body, {
    x: M, y: 1.9, w: CW, colW: [1.02, 2.32, 4.6, 4.15],
    border: { type: "solid", color: LINE, pt: 1 },
    fill: { color: CARD }, fontFace: F, rowH: 0.6, margin: 0.07, autoPage: false,
  });

  card(s, { x: M, y: 6.24, w: CW, h: 0.7, fill: RED_L, line: "E9CFCC" });
  s.addText([
    { text: "P0 조치 전에는 어떤 단계도 시작하지 않는다. ", options: { bold: true, color: RED } },
    { text: "키가 유출된 상태에서 저장소를 공개 이력에 올리면 재발급 외에 되돌릴 방법이 없다 — CLAUDE.md 가 이미 경고하고 있는 그대로다.", options: { color: INK } },
  ], { x: M + 0.28, y: 6.24, w: CW - 0.56, h: 0.7, isTextBox: true, margin: 0, fontFace: F, fontSize: 11, valign: "middle" });
}

/* ══════════ 17. ROADMAP ══════════ */
{
  const s = base(false);
  header(s, "ROADMAP", "9주 전환 계획 — 병행 운영으로 끝낸다",
         "마지막 두 주는 사람이 만든 회의자료와 에이전트 산출을 나란히 놓고 대조한다. 대조 없이 전환하지 않는다.");

  const ph = [
    ["Phase 0", "W1", "위생", ["env.txt 키 6종 폐기·재발급", "저장소 밖으로 키 이전", ".gitignore 에 env.txt 추가", "docs/audit.py 로 유출 재검사"], RED],
    ["Phase 1", "W1–2", "원장 게이트웨이", ["ki-ledger MCP 서버 (읽기 7종)", "봉투 스키마 확정 · 검증기", "'해석' 등급 신설", "PreToolUse 훅 화이트리스트"], NAVY],
    ["Phase 2", "W3–4", "리서치 데스크", ["equity · quant · macro · execution", "담당 절 매핑 (§3~§7)", "산출은 초안까지 — 발행 안 함", "사람이 초안 품질 육안 대조"], NAVY_M],
    ["Phase 3", "W5–6", "통제 데스크", ["risk · compliance 구현", "게이트 ①~⑥ 코드화", "거부권 · 반려 사유 기록", "4-eyes 강제"], "5B4B8A"],
    ["Phase 4", "W7–9", "IC 통합 · 병행", ["ic-chair 조립 · 쟁점 정렬", "2주 병행 운영 (사람 vs 에이전트)", "불일치 원인 전수 분석", "KPI 계측 후 전환 결정"], GREEN],
  ];
  const pw = 2.36, pg = 0.12;
  ph.forEach((p, i) => {
    const x = M + i * (pw + pg);
    s.addShape(pres.ShapeType.roundRect, {
      x, y: 2.16, w: pw, h: 0.42, rectRadius: 0.07,
      fill: { color: p[4] }, line: { type: "none" },
    });
    s.addText(p[0] + "   ·   " + p[1], {
      x, y: 2.16, w: pw, h: 0.42, isTextBox: true, margin: 0,
      fontFace: F, fontSize: 11, bold: true, color: WHITE, align: "center", valign: "middle",
    });
    card(s, { x, y: 2.7, w: pw, h: 3.34 });
    s.addText(p[2], {
      x: x + 0.16, y: 2.86, w: pw - 0.32, h: 0.6, isTextBox: true, margin: 0,
      fontFace: F, fontSize: 15, bold: true, color: NAVY,
    });
    p[3].forEach((t, j) => {
      s.addShape(pres.ShapeType.ellipse, {
        x: x + 0.19, y: 3.725 + j * 0.62, w: 0.11, h: 0.11,
        fill: { color: p[4] }, line: { type: "none" },
      });
      s.addText(t, {
        x: x + 0.4, y: 3.5 + j * 0.62, w: pw - 0.56, h: 0.56, isTextBox: true, margin: 0,
        fontFace: F, fontSize: 10, color: INK,
      });
    });
  });

  const outs = [["Phase 1 종료", "에이전트가 원장을 읽을 수는 있고 쓸 수는 없는 상태"],
                ["Phase 3 종료", "게이트가 실제로 발행을 멈출 수 있는 상태"],
                ["Phase 4 종료", "병행 2주 결과로 전환 여부를 사람이 결정"]];
  outs.forEach((o, i) => {
    const x = M + i * 4.11;
    card(s, { x, y: 6.16, w: 3.94, h: 0.68, fill: "EDF1F9", line: "C6D2E8" });
    s.addText(o[0], {
      x: x + 0.2, y: 6.24, w: 3.6, h: 0.26, isTextBox: true, margin: 0,
      fontFace: F, fontSize: 10.5, bold: true, color: GOLD,
    });
    s.addText(o[1], {
      x: x + 0.2, y: 6.5, w: 3.6, h: 0.26, isTextBox: true, margin: 0,
      fontFace: F, fontSize: 9.5, color: INK,
    });
  });
}

/* ══════════ 18. WEEK 1 + KPI ══════════ */
{
  const s = base(true);
  s.addShape(pres.ShapeType.ellipse, {
    x: 10.4, y: -1.8, w: 5.6, h: 5.6, fill: { color: NAVY, transparency: 50 }, line: { type: "none" },
  });

  s.addText("NEXT STEP", {
    x: M, y: 0.5, w: CW, h: 0.26, isTextBox: true, margin: 0,
    fontFace: F, fontSize: 11, bold: true, color: GOLD, charSpacing: 2,
  });
  s.addText("이번 주에 할 것과, 무엇으로 성공을 판정할 것인가", {
    x: M, y: 0.8, w: CW, h: 0.56, isTextBox: true, margin: 0,
    fontFace: F, fontSize: 29, bold: true, color: WHITE,
  });

  const todo = [
    ["키 6종 폐기·재발급", "KRX · DART · ECOS · FRED · KIS(앱키+시크릿). env.txt 는 삭제한다", "P0 · 오늘"],
    ["저장소 위생 재검사", ".gitignore 에 env.txt 추가 후 docs/audit.py 전수 실행", "P0 · 오늘"],
    ["봉투 스키마 1장 확정", "필수 필드 · '해석' 등급 정의 · null 규칙. 코드보다 먼저 합의한다", "W1"],
    ["ki-ledger MCP 골격", "facts · candles · factors 세 개만 먼저. 쓰기 도구는 만들지 않는다", "W1"],
    ["데스크 1개 시범", "quant-researcher 하나만 붙여 §6 초안을 뽑고 사람이 육안 대조", "W2"],
  ];
  todo.forEach((t, i) => {
    const y = 1.66 + i * 0.94;
    s.addShape(pres.ShapeType.roundRect, {
      x: M, y, w: 7.6, h: 0.82, rectRadius: 0.08,
      fill: { color: "16274A" }, line: { color: "2C3E6B", width: 1 },
    });
    numDot(s, M + 0.22, y + 0.2, i + 1, 0.42, i < 2 ? RED : GOLD);
    s.addText(t[0], {
      x: M + 0.82, y: y + 0.12, w: 5.1, h: 0.3, isTextBox: true, margin: 0,
      fontFace: F, fontSize: 13.5, bold: true, color: WHITE,
    });
    s.addText(t[1], {
      x: M + 0.82, y: y + 0.43, w: 5.5, h: 0.3, isTextBox: true, margin: 0,
      fontFace: F, fontSize: 10, color: "9FB3D6",
    });
    s.addText(t[2], {
      x: M + 6.3, y: y + 0.12, w: 1.14, h: 0.3, isTextBox: true, margin: 0,
      fontFace: F, fontSize: 10.5, bold: true, color: i < 2 ? "E88A84" : GOLD, align: "right",
    });
  });

  s.addText("성공 판정 지표", {
    x: 8.6, y: 1.66, w: 4.1, h: 0.3, isTextBox: true, margin: 0,
    fontFace: F, fontSize: 14, bold: true, color: GOLD,
  });
  const kpi = [["0건", "출처 등급 없는 주장", "게이트 ② 반려 건수 = 0 이어야 한다"],
               ["0건", "원장 오염", "ki.sqlite 에 에이전트 기원 레코드 0"],
               ["0건", "미채택 논문 인용", "게이트 ③ · selftest 가 함께 검사"],
               ["4h → 30m", "회의자료 준비 시간", "병행 2주 실측으로 판정"]];
  kpi.forEach((k, i) => {
    const y = 2.1 + i * 1.16;
    s.addText(k[0], {
      x: 8.6, y, w: 4.1, h: 0.44, isTextBox: true, margin: 0,
      fontFace: F, fontSize: 26, bold: true, color: WHITE,
    });
    s.addText(k[1], {
      x: 8.6, y: y + 0.46, w: 4.1, h: 0.26, isTextBox: true, margin: 0,
      fontFace: F, fontSize: 11.5, bold: true, color: ICE,
    });
    s.addText(k[2], {
      x: 8.6, y: y + 0.72, w: 4.1, h: 0.26, isTextBox: true, margin: 0,
      fontFace: F, fontSize: 9.5, color: "8FA3C8",
    });
  });

  s.addText("내부 검토용 · 대외비  ·  투자권유 · 투자자문 자료가 아니며, 최종 판단과 책임은 이용자에게 있습니다.", {
    x: M, y: 6.82, w: CW, h: 0.28, isTextBox: true, margin: 0,
    fontFace: F, fontSize: 9.5, color: "7E8DAB",
  });
  s.addNotes("Phase 0 는 이 방안의 승인 여부와 무관하게 오늘 처리해야 합니다.");
}

/* ══════════ 19. APPENDIX ══════════ */
{
  const s = base(false);
  header(s, "APPENDIX", "저장소에 추가되는 것 — 파일 배치",
         "기존 파일은 하나도 옮기지 않는다. 아래는 전부 새로 생기는 경로다.");

  card(s, { x: M, y: 1.94, w: 6.7, h: 4.62, fill: "12203C", line: null });
  const tree = [
    'Stock_Agent/',
    '├─ stock-monitor/          변경 없음 (ki_monitor.py 8,684줄)',
    '├─ docs/                   변경 없음',
    '│',
    '├─ agents/                 ← 새로 생김',
    '│   ├─ ki_ledger_mcp.py       MCP 서버 · 읽기 7종 (~200줄)',
    '│   ├─ envelope.py            봉투 스키마 · 검증기',
    '│   └─ gates.py               게이트 ①~⑥ 검사기',
    '│',
    '└─ .claude/',
    '    ├─ agents/                데스크 8개 정의',
    '    │   ├─ equity-analyst.md',
    '    │   ├─ quant-researcher.md',
    '    │   ├─ macro-strategist.md',
    '    │   ├─ execution-trader.md',
    '    │   ├─ risk-officer.md',
    '    │   ├─ compliance-officer.md',
    '    │   ├─ data-ops.md',
    '    │   └─ ic-chair.md',
    '    ├─ skills/                규칙 4종',
    '    │   ├─ source-grading/     등급 판정 기준',
    '    │   ├─ envelope-schema/    봉투 작성법',
    '    │   ├─ paper-adoption/     논문 채택 심사',
    '    │   └─ compliance-gate/    게이트 판정 기준',
    '    └─ settings.json          훅 · MCP 등록',
  ].join("\n");
  s.addText(tree, {
    x: M + 0.26, y: 2.06, w: 6.2, h: 4.38, isTextBox: true, margin: 0,
    fontFace: FM, fontSize: 8.5, color: "C9E2FF", lineSpacing: 11.2,
  });

  const notes = [
    ["ki_monitor.py 는 열지 않는다", "CRLF 파일이라 편집 도구가 줄바꿈을 바꾸면 파일 전체가 diff 에 잡힌다. 감싸기만 하고 손대지 않는 이유이기도 하다.", NAVY],
    [".claude/settings.json 은 팀 공용", "훅과 MCP 등록은 커밋한다. settings.local.json 만 개인 설정으로 제외한다 — 기존 .gitignore 규칙 그대로다.", NAVY_M],
    ["게이트는 selftest 와 나란히 돈다", "python agents/gates.py --selftest 를 기존 128개 옆에 붙인다. 검증은 한 곳에서 돌아야 실제로 돌아간다.", GREEN],
    ["대외비 규칙은 확장한다", "데스크 산출 봉투도 포트폴리오사 실명을 담는다. out/ 과 같은 등급으로 .gitignore 에 넣는다.", RED],
  ];
  notes.forEach((n, i) => {
    const y = 1.94 + i * 1.18;
    card(s, { x: 7.52, y, w: 5.2, h: 1.06 });
    s.addShape(pres.ShapeType.ellipse, { x: 7.74, y: y + 0.19, w: 0.15, h: 0.15, fill: { color: n[2] }, line: { type: "none" } });
    s.addText(n[0], {
      x: 7.98, y: y + 0.12, w: 4.6, h: 0.3, isTextBox: true, margin: 0,
      fontFace: F, fontSize: 12.5, bold: true, color: NAVY,
    });
    s.addText(n[1], {
      x: 7.74, y: y + 0.44, w: 4.82, h: 0.52, isTextBox: true, margin: 0,
      fontFace: F, fontSize: 9.5, color: MUTED,
    });
  });

  footer(s, "새로 쓰는 파이썬 코드 약 400줄 · 나머지는 마크다운 정의 파일 · 기존 코드 변경 0줄");
}

pres.writeFile({ fileName: process.argv[2] || "deck.pptx" })
  .then(f => console.log("WROTE " + f))
  .catch(e => { console.error(e); process.exit(1); });
