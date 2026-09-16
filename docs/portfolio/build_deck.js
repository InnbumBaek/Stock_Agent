const pptxgen = require("pptxgenjs");
const fs = require("fs"), path = require("path");

const PX = process.env.PX_DIR || path.join(__dirname, "sprites");
const cache = {};
function img(name) {
  if (!cache[name]) cache[name] = "image/png;base64," + fs.readFileSync(path.join(PX, name + ".png")).toString("base64");
  return cache[name];
}

/* ── 팔레트 ───────────────────────────────────────────────────────
   크롬(UI)은 네온, 차트 계열색은 검증 통과한 별도 세트를 쓴다.      */
const BG = "0D1018", PANEL = "171E30", PANEL2 = "1F2740", PANEL3 = "111726";
const INK = "E8ECF5", MUT = "93A2C0", DIM = "5E6B87";
const EDGE = "2E3A5C";
const GRN = "3DFA7E", CYN = "35D6ED", AMB = "FFB627", MAG = "FF4D6D",
      PUR = "9D7BFF", GLD = "FFD34E", ORG = "FF7847", BLU = "4FC3F7";
// 검증 통과 (dark surface · 6검사 PASS)
const C1 = "26A455", C2 = "2596B0", C3 = "C98416", C4 = "C93B54";

const F = "Malgun Gothic", FM = "Courier New";
const W = 13.333, H = 7.5, M = 0.6, CW = W - M * 2;

const pres = new pptxgen();
pres.layout = "LAYOUT_WIDE";
pres.title = "Stock Agent v2 — 살아있는 리서치 데스크";

function slide() { const s = pres.addSlide(); s.background = { color: BG }; return s; }

/* 하드 오프셋 그림자를 가진 픽셀 패널 (둥근 모서리 없음) */
function panel(s, o) {
  const off = o.off === undefined ? 0.055 : o.off;
  if (off > 0) s.addShape(pres.ShapeType.rect, {
    x: o.x + off, y: o.y + off, w: o.w, h: o.h,
    fill: { color: o.shadow || "070A12" }, line: { type: "none" },
  });
  s.addShape(pres.ShapeType.rect, {
    x: o.x, y: o.y, w: o.w, h: o.h,
    fill: { color: o.fill || PANEL },
    line: o.line === null ? { type: "none" } : { color: o.line || EDGE, width: 1.25 },
  });
}
function txt(s, t, o) { s.addText(t, Object.assign({ isTextBox: true, margin: 0, fontFace: F }, o)); }
function mono(s, t, o) { s.addText(t, Object.assign({ isTextBox: true, margin: 0, fontFace: FM }, o)); }

function header(s, kicker, title, sub) {
  mono(s, "▚ " + kicker, { x: M, y: 0.40, w: CW, h: 0.26, fontSize: 11, bold: true, color: AMB, charSpacing: 1.5 });
  txt(s, title, { x: M, y: 0.68, w: CW, h: 0.60, fontSize: 28, bold: true, color: INK, valign: "top" });
  if (sub) txt(s, sub, { x: M, y: 1.30, w: CW, h: 0.30, fontSize: 12.5, color: MUT });
}
function foot(s, t) { mono(s, t, { x: M, y: H - 0.42, w: CW, h: 0.24, fontSize: 9, color: DIM }); }

/* 픽셀 바닥 타일 한 줄 */
function floorRow(s, x, y, w, tile, c1, c2) {
  const n = Math.floor(w / tile);
  for (let i = 0; i < n; i++) s.addShape(pres.ShapeType.rect, {
    x: x + i * tile, y, w: tile, h: tile,
    fill: { color: i % 2 ? c2 : c1 }, line: { type: "none" },
  });
}
/* 픽셀 진행 막대 */
function pxBar(s, x, y, w, h, frac, on, off) {
  const cells = 20, cw = w / cells, lit = Math.round(cells * frac);
  for (let i = 0; i < cells; i++) s.addShape(pres.ShapeType.rect, {
    x: x + i * cw + 0.012, y, w: cw - 0.024, h,
    fill: { color: i < lit ? on : (off || "232B44") }, line: { type: "none" },
  });
}


const ICE_ = "CADCFC";


/* ═══ 1. 표지 ═══ */
function sCover() {
  const s = slide();
  for (let i = 0; i < 42; i++) s.addShape(pres.ShapeType.rect, {
    x: 0, y: i * 0.18, w: W, h: 0.03, fill: { color: "121826" }, line: { type: "none" } });

  mono(s, "PORTFOLIO  ·  코스닥벤처 · 메자닌 운용", {
    x: M, y: 0.52, w: 10, h: 0.26, fontSize: 11, bold: true, color: AMB, charSpacing: 1 });

  txt(s, "메자닌 포트폴리오 회수 판단 시스템", {
    x: M, y: 1.20, w: 11.6, h: 0.9, fontSize: 42, bold: true, color: INK });
  mono(s, "리픽싱 · 희석 · 락업 · 처분여건을 매일 재는 도구", {
    x: M, y: 2.10, w: 11.6, h: 0.42, fontSize: 19, bold: true, color: GRN });
  txt(s, "한국거래소·금융감독원 공식 API 로 숫자를 받아 원장에 쌓고, 그 원장으로 회수 판단 리포트를 만든다.\n판단은 넣지 않는다 — 재기만 하고, 그 측정값이 무엇을 셌는지와 어떤 가정 위에 서 있는지를 함께 낸다.", {
    x: M, y: 2.64, w: 11.6, h: 0.7, fontSize: 13, color: MUT, lineSpacing: 20 });

  const chips = [["8,684", "줄 · 단일 파일", "수집 · 계산 · 리포트"],
                 ["128", "자체 검증", "교차검산 · 항등식 · 방향성"],
                 ["5", "1차 출처 API", "크롤링 · 벤더 데이터 없음"],
                 ["0", "판정 어휘", "점수 · 등급 · 목표주가 없음"]];
  chips.forEach((c, i) => {
    const x = M + i * 3.06;
    panel(s, { x, y: 3.78, w: 2.86, h: 1.18, fill: PANEL, line: EDGE });
    mono(s, c[0], { x: x + 0.18, y: 3.92, w: 2.5, h: 0.44, fontSize: 25, bold: true, color: GLD });
    txt(s, c[1], { x: x + 0.18, y: 4.38, w: 2.5, h: 0.24, fontSize: 11, bold: true, color: INK });
    txt(s, c[2], { x: x + 0.18, y: 4.62, w: 2.52, h: 0.24, fontSize: 9.5, color: MUT });
  });

  const sprites = ["ag_equity", "ag_quant", "ag_exec", "ag_risk", "ag_compliance", "ag_dataops"];
  sprites.forEach((sp, i) => s.addImage({ data: img(sp), x: M + i * 0.62, y: 5.34, w: 0.5, h: 0.5 }));
  mono(s, "확장 설계 — 데스크 에이전트 · 논문 재현 관문 (PART 5)", {
    x: M + 4.0, y: 5.46, w: 6.0, h: 0.26, fontSize: 10, color: DIM });

  panel(s, { x: M, y: 6.14, w: CW, h: 0.62, fill: PANEL3, line: EDGE });
  txt(s, [
    { text: "만든 이유 — ", options: { bold: true, color: GLD } },
    { text: "메자닌은 리픽싱·희석·락업·유동성이 서로 얽혀 있어서, 한 종목의 회수 시점을 눈으로 판단하기 어렵다. 그 네 가지를 매일 같은 기준으로 재려고 만들었다.", options: { color: INK } },
  ], { x: M + 0.26, y: 6.14, w: CW - 0.52, h: 0.62, fontSize: 11, valign: "middle", fontFace: F, isTextBox: true, margin: 0 });
  mono(s, "2026-09  ·  github.com/InnbumBaek/Stock_Agent  ·  내부 검토용 · 투자권유 자료 아님", {
    x: M, y: 6.96, w: 11.6, h: 0.26, fontSize: 9, color: DIM });
}

/* ═══ 2. 한 장 요약 ═══ */
function sOnePager() {
  const s = slide();
  header(s, "ONE PAGER", "무엇을 만들었고, 무엇이 다른가",
         "시세 대시보드는 많다. 이 도구가 다루는 것은 시세가 아니라 메자닌 포지션의 회수 조건이다.");

  const rows = [
    ["메자닌 구조를 계산한다", "리픽싱 시나리오 · 완전희석 지분 · 전환 잠재주식수를 코드로 계산한다. 공시 제목이 아니라 발행조건으로 본다.", GRN],
    ["희석과 권리락을 구분한다", "CB 전환은 주식수만 늘고 권리락이 아니다. 수정주가를 조정하면 과거 수익률이 조용히 틀어진다 — 구분해서 처리한다.", CYN],
    ["팔 수 있는지를 잰다", "처분 소요일수를 평균과 중앙값으로 나란히 낸다. 거래대금이 상위 며칠에 몰리는 코스닥 소형주는 평균값이 낙관적이다.", AMB],
    ["모른다는 것을 표시한다", "락업은 '추정'이고 확약이 아니다. 못 구한 값은 None 과 사유를 낸다. 0 으로 채우지 않는다.", PUR],
  ];
  rows.forEach((r, i) => {
    const y = 1.82 + i * 1.06;
    panel(s, { x: M, y, w: 7.9, h: 0.94, fill: PANEL, line: EDGE });
    s.addShape(pres.ShapeType.rect, { x: M + 0.18, y: y + 0.18, w: 0.16, h: 0.58, fill: { color: r[2] }, line: { type: "none" } });
    txt(s, r[0], { x: M + 0.52, y: y + 0.14, w: 7.1, h: 0.3, fontSize: 14, bold: true, color: r[2] });
    txt(s, r[1], { x: M + 0.52, y: y + 0.46, w: 7.2, h: 0.42, fontSize: 10.5, color: MUT });
  });

  panel(s, { x: 8.72, y: 1.82, w: 4.01, h: 4.26, fill: PANEL, line: GLD });
  mono(s, "면접에서 보실 것", { x: 8.94, y: 1.98, w: 3.6, h: 0.26, fontSize: 11, bold: true, color: GLD });
  const ev = [
    ["refix_scenario()", "리픽싱 최저한도까지의 희석 가속"],
    ["fully_diluted_ownership()", "CB · BW · 옵션풀 반영 지분"],
    ["adjust_audit()", "희석 ≠ 권리락 판별"],
    ["exit_days (mean · median)", "처분 소요일수 두 기준"],
    ["LOCKUP_MONTHS = 6", "벤처금융 보호예수 · 추정 표기"],
    ["selftest 128", "교차검산 · 항등식 · 방향성"],
  ];
  ev.forEach((e, i) => {
    const y = 2.34 + i * 0.6;
    s.addShape(pres.ShapeType.rect, { x: 8.94, y, w: 3.58, h: 0.52, fill: { color: i % 2 ? PANEL3 : PANEL2 }, line: { type: "none" } });
    mono(s, e[0], { x: 9.06, y: y + 0.04, w: 3.4, h: 0.24, fontSize: 9, bold: true, color: CYN });
    txt(s, e[1], { x: 9.06, y: y + 0.26, w: 3.4, h: 0.24, fontSize: 9, color: MUT });
  });

  panel(s, { x: M, y: 6.20, w: CW, h: 0.62, fill: "16281C", line: "2A5A3A" });
  txt(s, [
    { text: "설계 원칙 하나로 줄이면 — ", options: { bold: true, color: GRN } },
    { text: "재기만 하고 판단하지 않는다. 점수·등급·목표주가를 만들지 않는다. 회의에서 근거 없는 결론이 근거 있는 숫자처럼 읽히는 것이 이 시스템이 막으려는 실패다.", options: { color: INK } },
  ], { x: M + 0.26, y: 6.20, w: CW - 0.52, h: 0.62, fontSize: 11, valign: "middle", fontFace: F, isTextBox: true, margin: 0 });
}

/* ═══ 3. 운용역의 네 질문 ═══ */
function sQuestions() {
  const s = slide();
  header(s, "PART 1 · THE FOUR QUESTIONS", "운용역이 매일 답해야 하는 네 가지",
         "리포트 구조와 팩터 인용이 전부 이 네 질문에 묶여 있다. 질문에 답하지 않는 지표는 넣지 않는다.");

  const qs = [
    ["q1", "얼마나 왔는가", "회수계획 대비 진척", ["회수 목표 · 기한 대비 현재", "목표회수단가 갭", "총수익률 · 배당 반영"], CYN],
    ["q2", "팔 수 있는가", "처분 여건 · 거래비용", ["처분 소요일수 (평균 · 중앙값)", "유효 스프레드 · 비유동성", "락업 잔여 · 물량 압력"], GRN],
    ["q3", "어떻게 팔 것인가", "실행", ["매도 규칙 4종 비교", "가격 충격 가정과 민감도", "매물대 분포"], AMB],
    ["q4", "지금이 그 때인가", "시점 · 국면", ["지수·금리 분위", "금통위 · 파생 만기 일정", "공시 이벤트 · CAR"], MAG],
  ];
  qs.forEach((q, i) => {
    const x = M + i * 3.06;
    panel(s, { x, y: 1.88, w: 2.86, h: 0.5, fill: q[4], line: null });
    mono(s, q[0], { x: x + 0.14, y: 1.88, w: 0.6, h: 0.5, fontSize: 14, bold: true, color: "0D1018", valign: "middle" });
    txt(s, q[1], { x: x + 0.74, y: 1.88, w: 2.0, h: 0.5, fontSize: 13.5, bold: true, color: "0D1018", valign: "middle" });
    panel(s, { x, y: 2.46, w: 2.86, h: 3.3, fill: PANEL, line: EDGE });
    txt(s, q[2], { x: x + 0.18, y: 2.62, w: 2.5, h: 0.3, fontSize: 11, bold: true, color: q[4] });
    q[3].forEach((t, j) => {
      s.addShape(pres.ShapeType.rect, { x: x + 0.2, y: 3.14 + j * 0.62, w: 0.08, h: 0.08, fill: { color: q[4] }, line: { type: "none" } });
      txt(s, t, { x: x + 0.38, y: 3.06 + j * 0.62, w: 2.32, h: 0.56, fontSize: 10, color: INK });
    });
    mono(s, "논문 인용 → " + q[0], { x: x + 0.18, y: 5.3, w: 2.5, h: 0.24, fontSize: 8.5, color: DIM });
  });

  panel(s, { x: M, y: 5.96, w: CW, h: 0.88, fill: PANEL3, line: EDGE });
  txt(s, [
    { text: "이 네 질문이 코드 안에 있다. ", options: { bold: true, color: GLD } },
    { text: "`.papers.json` 의 모든 채택 논문은 q1~q4 중 하나에 태그돼 있고, 네 질문 중 하나를 바꾸지 않는 논문은 채택하지 않는다.\n", options: { color: INK } },
    { text: "지표를 늘리는 것이 목적이 아니라, 회수 시점을 판단하는 데 쓰이지 않는 지표를 들이지 않는 것이 목적이다.", options: { color: MUT } },
  ], { x: M + 0.26, y: 5.96, w: CW - 0.52, h: 0.88, fontSize: 11, valign: "middle", lineSpacing: 18, fontFace: F, isTextBox: true, margin: 0 });
}

/* ═══ 4. 메자닌은 왜 어려운가 ═══ */
function sWhyHard() {
  const s = slide();
  header(s, "PART 2 · WHY MEZZANINE IS HARD", "네 가지가 서로를 움직인다",
         "하나만 보면 답이 나오는 것 같지만, 실제로는 주가가 내리면 전환가가 내리고, 전환가가 내리면 희석이 커지고, 희석이 커지면 팔기가 어려워진다.");

  const nodes = [
    ["주가 하락", "시장", 1.0, 2.3, MAG],
    ["전환가 하락", "리픽싱 조항", 4.2, 2.3, AMB],
    ["잠재주식 증가", "희석", 7.4, 2.3, PUR],
    ["처분 난도 상승", "유동성", 10.6, 2.3, CYN],
  ];
  nodes.forEach((n, i) => {
    panel(s, { x: n[2], y: n[3], w: 2.3, h: 1.1, fill: PANEL, line: n[4] });
    txt(s, n[0], { x: n[2] + 0.14, y: n[3] + 0.2, w: 2.02, h: 0.34, fontSize: 14, bold: true, color: n[4], align: "center" });
    mono(s, n[1], { x: n[2] + 0.14, y: n[3] + 0.6, w: 2.02, h: 0.24, fontSize: 9.5, color: MUT, align: "center" });
    if (i < 3) s.addImage({ data: img("ar_am"), x: n[2] + 2.42, y: n[3] + 0.44, w: 0.38, h: 0.24 });
  });
  mono(s, "▲  되먹임 — 희석이 커지면 오버행으로 주가가 더 눌린다", {
    x: M, y: 3.58, w: CW, h: 0.28, fontSize: 10.5, bold: true, color: MAG, align: "center" });

  const items = [
    ["리픽싱 최저한도", "최초 전환가액의 70%", "그 밑으로는 주주총회 특별결의가 있어야 한다. 정관만으로는 안 된다(2021 개정).", AMB],
    ["상향조정 의무", "사모 발행 시", "주가 하락으로 내린 뒤 다시 오르면 상향조정해야 한다. 범위는 최초 전환가액의 70~100%.", GRN],
    ["락업은 확약이 아니다", "상장일 + 6개월 (추정)", "실제 의무보유 기간·대상은 증권신고서를 봐야 한다. 이 도구는 '추정' 등급으로 표시한다.", CYN],
    ["평균은 낙관적이다", "처분 소요일수", "거래대금이 상위 며칠에 몰리는 종목은 평균 거래량 기준이 실제보다 짧게 나온다.", PUR],
  ];
  items.forEach((it, i) => {
    const x = M + (i % 2) * 6.18, y = 4.06 + Math.floor(i / 2) * 1.32;
    panel(s, { x, y, w: 5.92, h: 1.2, fill: PANEL, line: EDGE });
    txt(s, it[0], { x: x + 0.2, y: y + 0.14, w: 3.4, h: 0.28, fontSize: 12.5, bold: true, color: it[3] });
    mono(s, it[1], { x: x + 3.6, y: y + 0.16, w: 2.14, h: 0.24, fontSize: 9.5, color: GLD, align: "right" });
    txt(s, it[2], { x: x + 0.2, y: y + 0.48, w: 5.54, h: 0.62, fontSize: 10, color: MUT });
  });
  foot(s, "// 제도 근거는 금융위원회 「증권의 발행 및 공시 등에 관한 규정」 개정 보도자료 · 시행 시점과 최신 개정은 원문 재확인 필요");
}


/* ═══ 5. ★ 리픽싱 ═══ */
function sRefix() {
  const s = slide();
  header(s, "PART 2 · ★ REFIXING", "리픽싱 — 주가가 더 내리면 희석이 얼마나 가속되는가",
         "전환가액은 고정이 아니다. 주가가 내리면 따라 내리고, 그만큼 잠재주식수가 늘어난다. 최저한도에 닿기 전까지는 계속 늘어난다.");

  panel(s, { x: M, y: 1.88, w: 6.5, h: 2.44, fill: "0A1020", line: EDGE });
  mono(s, "ki_monitor.py", { x: M + 0.24, y: 2.0, w: 3.0, h: 0.22, fontSize: 9, color: DIM });
  mono(s, [
    'def refix_scenario(cb_amount, price, floor_price,',
    '                   drops=(0.9, 0.8, 0.7)) -> list[dict]:',
    '    """주가가 더 내리면 희석이 얼마나 가속되는가."""',
    '    out = []',
    '    for d in drops:',
    '        px = price * d',
    '        cv = max(px, floor_price)          # 최저조정한도',
    '        out.append({"price": round(px, 1),',
    '                    "conv_price": round(cv, 1),',
    '                    "potential_shares":',
    '                        round(cb_amount / cv) if cv else None})',
    '    return out',
  ].join("\n"), { x: M + 0.24, y: 2.26, w: 6.06, h: 1.94, fontSize: 9.2, color: "A9C8F0", lineSpacing: 12.4, valign: "top" });

  panel(s, { x: 7.32, y: 1.88, w: 5.41, h: 2.44, fill: PANEL, line: AMB });
  mono(s, "산출 예 · CB 10억 · 현재가 10,000 · 하한 7,000", {
    x: 7.54, y: 2.0, w: 5.0, h: 0.24, fontSize: 9.5, bold: true, color: AMB });
  const rows = [["기준", "10,000", "10,000", "100,000", DIM],
                ["-10%", "9,000", "9,000", "111,111", INK],
                ["-20%", "8,000", "8,000", "125,000", INK],
                ["-30%", "7,000", "7,000", "142,857", MAG]];
  mono(s, "주가", { x: 7.54, y: 2.34, w: 1.0, h: 0.22, fontSize: 8.5, color: DIM });
  mono(s, "전환가", { x: 9.0, y: 2.34, w: 1.1, h: 0.22, fontSize: 8.5, color: DIM });
  mono(s, "잠재주식수", { x: 10.8, y: 2.34, w: 1.7, h: 0.22, fontSize: 8.5, color: DIM, align: "right" });
  rows.forEach((r, i) => {
    const y = 2.60 + i * 0.36;
    s.addShape(pres.ShapeType.rect, { x: 7.54, y, w: 4.96, h: 0.34, fill: { color: i % 2 ? PANEL3 : PANEL2 }, line: { type: "none" } });
    mono(s, r[0], { x: 7.64, y, w: 1.0, h: 0.34, fontSize: 9.5, bold: true, color: r[4], valign: "middle" });
    mono(s, r[1], { x: 8.5, y, w: 1.1, h: 0.34, fontSize: 9.5, color: MUT, align: "right", valign: "middle" });
    mono(s, r[2], { x: 9.6, y, w: 1.1, h: 0.34, fontSize: 9.5, color: r[4], align: "right", valign: "middle" });
    mono(s, r[3], { x: 10.8, y, w: 1.6, h: 0.34, fontSize: 9.5, bold: true, color: r[4], align: "right", valign: "middle" });
  });
  mono(s, "-30% 에서 하한에 닿는다 — 그 아래로는 더 늘지 않는다", {
    x: 7.54, y: 4.04, w: 5.0, h: 0.24, fontSize: 9, italic: true, color: GRN });

  const rule = [
    ["최저조정한도", "최초 전환가액의 70%", "그 밑으로 내리려면 발행 시마다 주주총회 특별결의가 필요하다. 정관에 근거를 두는 방식은 2021년 개정으로 막혔다.", AMB],
    ["상향조정 의무", "사모 발행 · 70~100%", "하락으로 조정한 뒤 주가가 오르면 다시 올려야 한다. 범위는 최초 전환가액을 넘지 못한다.", GRN],
    ["콜옵션 공시", "행사자 공시 의무화", "발행사·최대주주가 되사는 콜옵션의 행사자와 조건이 공시 대상이 됐다. 지분 변동 감시에 쓴다.", CYN],
  ];
  rule.forEach((r, i) => {
    const x = M + i * 4.11;
    panel(s, { x, y: 4.5, w: 3.94, h: 1.5, fill: PANEL, line: EDGE });
    txt(s, r[0], { x: x + 0.2, y: 4.64, w: 3.5, h: 0.28, fontSize: 12.5, bold: true, color: r[3] });
    mono(s, r[1], { x: x + 0.2, y: 4.94, w: 3.5, h: 0.24, fontSize: 9.5, color: GLD });
    txt(s, r[2], { x: x + 0.2, y: 5.22, w: 3.56, h: 0.68, fontSize: 9.5, color: MUT });
  });

  panel(s, { x: M, y: 6.16, w: CW, h: 0.66, fill: "2A1520", line: "5C2A3A" });
  txt(s, [
    { text: "한계를 함께 낸다 — ", options: { bold: true, color: MAG } },
    { text: "floor_price 는 우리가 넣는 값이다. 실제 조항(조정 주기·한도·예외)은 증권신고서와 주요사항보고서 원문을 봐야 한다. 공시 제목만으로는 알 수 없고, 이 도구는 원문 링크를 달아 둔다.", options: { color: INK } },
  ], { x: M + 0.26, y: 6.16, w: CW - 0.52, h: 0.66, fontSize: 10.5, valign: "middle", fontFace: F, isTextBox: true, margin: 0 });
}

/* ═══ 6. ★ 완전희석 ═══ */
function sDilution() {
  const s = slide();
  header(s, "PART 2 · ★ DILUTION", "보통주만 보면 지분율이 과대평가된다",
         "메자닌 포지션은 전환 전까지 주식이 아니다. 그런데 우리 지분율은 전환 후 기준으로 봐야 협상도 회수도 말이 된다.");

  panel(s, { x: M, y: 1.90, w: 6.5, h: 2.1, fill: "0A1020", line: EDGE });
  mono(s, [
    'def fully_diluted_ownership(our_shares, common,',
    '        cb_potential=0.0, bw_potential=0.0,',
    '        option_pool=0.0) -> dict:',
    '    """보통주만 보면 지분율이 과대평가됩니다."""',
    '    fd = common + cb_potential + bw_potential + option_pool',
    '    if fd <= 0:',
    '        return {"ownership_fd": None}     # 0 으로 채우지 않는다',
    '    return {"ownership_common": our_shares / common,',
    '            "ownership_fd":     our_shares / fd,',
    '            "fully_diluted_shares": fd}',
  ].join("\n"), { x: M + 0.24, y: 2.04, w: 6.06, h: 1.86, fontSize: 9.2, color: "A9C8F0", lineSpacing: 12.4, valign: "top" });

  panel(s, { x: 7.32, y: 1.90, w: 5.41, h: 2.1, fill: PANEL, line: PUR });
  mono(s, "무엇이 분모에 들어가는가", { x: 7.54, y: 2.04, w: 5.0, h: 0.26, fontSize: 11, bold: true, color: PUR });
  [["common", "보통주 발행주식총수", "dart.ds002.stock_total"],
   ["cb_potential", "전환사채 전환 시 주식", "ds005.cb_amount ÷ 전환가액"],
   ["bw_potential", "신주인수권 행사 시 주식", "행사가액 · 행사비율"],
   ["option_pool", "미행사 스톡옵션", "사업보고서 주식매수선택권"]].forEach((t, i) => {
    const y = 2.40 + i * 0.38;
    mono(s, t[0], { x: 7.54, y, w: 1.5, h: 0.3, fontSize: 9, bold: true, color: CYN, valign: "middle" });
    txt(s, t[1], { x: 9.1, y, w: 1.9, h: 0.3, fontSize: 9.5, color: INK, valign: "middle" });
    mono(s, t[2], { x: 11.0, y, w: 1.5, h: 0.3, fontSize: 7.5, color: DIM, align: "right", valign: "middle" });
  });

  const tests = [
    ["완전희석 < 보통주 지분", "fully_diluted_ownership(100, 1000, 200) 의 ownership_fd 가 ownership_common 보다 작은가", GRN],
    ["리픽싱이 희석을 키운다", "refix_scenario(...) 의 마지막 시나리오 잠재주식수가 첫 시나리오보다 큰가", GRN],
    ["0 분모는 None", "분모가 0 이면 계산을 거부하고 None 을 낸다 — 0 으로 채우지 않는다", AMB],
  ];
  mono(s, "이 두 함수를 검사하는 selftest", { x: M, y: 4.22, w: 6.0, h: 0.28, fontSize: 11, bold: true, color: GLD });
  tests.forEach((t, i) => {
    const y = 4.58 + i * 0.68;
    panel(s, { x: M, y, w: CW, h: 0.6, fill: PANEL, line: EDGE });
    s.addImage({ data: img("ic_ok"), x: M + 0.2, y: y + 0.21, w: 0.18, h: 0.18 });
    txt(s, t[0], { x: M + 0.5, y, w: 3.4, h: 0.6, fontSize: 12, bold: true, color: t[2], valign: "middle" });
    txt(s, t[1], { x: M + 4.0, y, w: 8.0, h: 0.6, fontSize: 10, color: MUT, valign: "middle" });
  });

  panel(s, { x: M, y: 6.62, w: CW, h: 0.5, fill: PANEL3, line: EDGE });
  txt(s, "예외가 안 난다고 맞는 게 아니다 — 금융 데이터 코드는 조용히 틀린다. 컬럼이 뒤바뀌어도, 단위가 천원이어도 계산은 돌아간다. 그래서 방향성 테스트를 둔다.", {
    x: M + 0.26, y: 6.62, w: CW - 0.52, h: 0.5, fontSize: 10.5, color: INK, valign: "middle" });
}

/* ═══ 7. ★★ 희석 ≠ 권리락 (킬러) ═══ */
function sNotExRight() {
  const s = slide();
  header(s, "PART 2 · ★★ THE SUBTLE ONE", "희석은 권리락이 아니다 — 수정주가를 조정하면 안 된다",
         "메자닌 포트폴리오는 CB 전환이 상시 일어난다. 주식수 증가를 자동으로 권리락으로 처리하는 순간, 과거 수익률이 조용히 틀어진다.");

  const cases = [
    { t: "무상증자 · 액면분할", c: GRN, ic: "ic_ok", v: "조정한다",
      rows: [["주식수", "×2"], ["주가", "÷2 (권리락)"], ["시가총액", "불변"], ["수정주가", "과거를 ÷2"]],
      why: "주가 실측이 주식수 비율을 뒷받침한다. 같은 날 주가가 정확히 절반이 됐다면 권리락이다." },
    { t: "CB 전환 · 유상증자 · 옵션행사", c: MAG, ic: "ic_no", v: "조정하지 않는다",
      rows: [["주식수", "+2.5%"], ["주가", "시장이 정한다"], ["시가총액", "증가"], ["수정주가", "그대로 둔다"]],
      why: "주식수만 늘고 권리락은 없다. 여기서 조정하면 전환 이전 구간 수익률이 통째로 왜곡된다." },
  ];
  cases.forEach((c, i) => {
    const x = M + i * 6.18;
    panel(s, { x, y: 1.88, w: 5.92, h: 3.2, fill: PANEL, line: c.c });
    s.addImage({ data: img(c.ic), x: x + 0.22, y: 2.06, w: 0.22, h: 0.22 });
    txt(s, c.t, { x: x + 0.56, y: 2.0, w: 3.5, h: 0.32, fontSize: 13.5, bold: true, color: INK });
    s.addShape(pres.ShapeType.rect, { x: x + 4.1, y: 2.0, w: 1.6, h: 0.32, fill: { color: c.c }, line: { type: "none" } });
    mono(s, c.v, { x: x + 4.1, y: 2.0, w: 1.6, h: 0.32, fontSize: 9.5, bold: true, color: "0D1018", align: "center", valign: "middle" });
    c.rows.forEach((r, j) => {
      const y = 2.52 + j * 0.42;
      s.addShape(pres.ShapeType.rect, { x: x + 0.22, y, w: 5.48, h: 0.36, fill: { color: j % 2 ? PANEL3 : PANEL2 }, line: { type: "none" } });
      mono(s, r[0], { x: x + 0.36, y, w: 1.6, h: 0.36, fontSize: 10, color: MUT, valign: "middle" });
      mono(s, r[1], { x: x + 2.0, y, w: 3.5, h: 0.36, fontSize: 10, bold: true, color: c.c, valign: "middle" });
    });
    txt(s, c.why, { x: x + 0.22, y: 4.34, w: 5.5, h: 0.6, fontSize: 10, color: MUT });
  });

  panel(s, { x: M, y: 5.24, w: 7.9, h: 1.58, fill: "0A1020", line: EDGE });
  mono(s, "selftest — 이 구분을 매번 검사한다", { x: M + 0.24, y: 5.36, w: 5.0, h: 0.24, fontSize: 9.5, bold: true, color: GLD });
  mono(s, [
    'd.loc[200:, "shares"] *= 1.025              # 주식수만 +2.5%',
    'd.loc[200, ["open","high","low","close"]] *= 0.90   # 시장 하락',
    'r = adjust_audit(d)',
    '_assert(r["n_actions"] == 0)                # 조정하지 않는다',
    '_assert(len(r["unresolved"]) == 1)          # 대신 "확인 필요" 로 표시',
  ].join("\n"), { x: M + 0.24, y: 5.64, w: 7.46, h: 1.06, fontSize: 8.6, color: "A9C8F0", lineSpacing: 11.6, valign: "top" });

  panel(s, { x: 8.72, y: 5.24, w: 4.01, h: 1.58, fill: "16281C", line: "2A5A3A" });
  txt(s, "지우지 않고 남긴다", { x: 8.94, y: 5.38, w: 3.6, h: 0.28, fontSize: 12.5, bold: true, color: GRN });
  txt(s, "판별이 안 되면 조정하지도, 없애지도 않고 '확인 필요' 로 남긴다. 사람이 DART 원문을 보고 판단한다.\n조용히 처리하는 것이 가장 위험하다.", {
    x: 8.94, y: 5.70, w: 3.62, h: 1.0, fontSize: 9.5, color: INK, lineSpacing: 14 });
}

/* ═══ 8. 락업 ═══ */
function sLockup() {
  const s = slide();
  header(s, "PART 2 · LOCKUP", "락업은 '추정'이다 — 확약으로 서술하지 않는다",
         "일정에도 등급이 있다. 확정된 일정과 관행상 그럴 것을 같은 무게로 읽으면, 추정이 확약처럼 읽힌다.");

  const grades = [
    ["공표", "기관이 미리 공표한 확정 일정", "금통위(연 8회) · FOMC(연 8회)", ".calendar.json 에 출처·확인일과 함께 적는다. 공개 API 가 없어 사람이 확인한다.", GRN],
    ["규칙", "제도로 정해진 규칙에서 계산", "지수선물·옵션 만기 (매월 둘째 목요일)", "외부 호출 없이 계산한다. 휴장일이면 앞당겨질 수 있다는 사실을 함께 적는다.", CYN],
    ["추정", "원장의 상장일에서 관행으로 계산", "락업 만료 (상장 + 6개월) · 상장 3년", "의무보유확약이 아니다. 실제 기간·대상은 증권신고서를 봐야 한다.", MAG],
  ];
  grades.forEach((g, i) => {
    const y = 1.90 + i * 1.34;
    panel(s, { x: M, y, w: CW, h: 1.2, fill: PANEL, line: g[4] });
    s.addShape(pres.ShapeType.rect, { x: M + 0.2, y: y + 0.22, w: 0.94, h: 0.42, fill: { color: g[4] }, line: { type: "none" } });
    mono(s, g[0], { x: M + 0.2, y: y + 0.22, w: 0.94, h: 0.42, fontSize: 11, bold: true, color: "0D1018", align: "center", valign: "middle" });
    txt(s, g[1], { x: M + 1.3, y: y + 0.18, w: 4.0, h: 0.28, fontSize: 12.5, bold: true, color: INK });
    mono(s, g[2], { x: M + 1.3, y: y + 0.5, w: 4.6, h: 0.26, fontSize: 9.5, color: g[4] });
    txt(s, g[3], { x: M + 6.2, y: y + 0.22, w: 5.7, h: 0.72, fontSize: 10.5, color: MUT, valign: "middle" });
  });

  panel(s, { x: M, y: 5.98, w: 7.9, h: 0.84, fill: "0A1020", line: EDGE });
  mono(s, 'LOCKUP_MONTHS = 6   # 벤처금융 보호예수는 통상 1~6개월. 보수적으로 6개월을 씁니다', {
    x: M + 0.24, y: 5.98, w: 7.46, h: 0.84, fontSize: 9.2, color: "A9C8F0", valign: "middle" });
  panel(s, { x: 8.72, y: 5.98, w: 4.01, h: 0.84, fill: PANEL3, line: EDGE });
  txt(s, "보수적으로 잡는다 — 짧게 잡으면 팔 수 있다고 착각하게 된다.", {
    x: 8.94, y: 5.98, w: 3.62, h: 0.84, fontSize: 10, color: INK, valign: "middle" });
}


/* ═══ 9. 팔 수 있는가 ═══ */
function sLiquidity() {
  const s = slide();
  header(s, "PART 3 · CAN WE SELL", "처분 소요일수 — 평균과 중앙값을 나란히 낸다",
         "코스닥 소형주는 거래대금이 상위 며칠에 몰린다. 평균 거래량으로 나누면 실제보다 짧게 나오고, 그 낙관이 회수 계획에 그대로 들어간다.");

  panel(s, { x: M, y: 1.90, w: 6.1, h: 2.5, fill: PANEL, line: EDGE });
  txt(s, "같은 종목, 두 기준", { x: M + 0.24, y: 2.04, w: 5.0, h: 0.3, fontSize: 13.5, bold: true, color: INK });
  const cmp = [["목표 물량", "1,200,000 주", DIM],
               ["평균 거래량 기준", "12.4 영업일", GRN],
               ["중앙값 기준", "18.1 영업일", MAG],
               ["차이", "+5.7 일 (46%)", AMB]];
  cmp.forEach((c, i) => {
    const y = 2.46 + i * 0.44;
    s.addShape(pres.ShapeType.rect, { x: M + 0.24, y, w: 5.62, h: 0.38, fill: { color: i % 2 ? PANEL3 : PANEL2 }, line: { type: "none" } });
    txt(s, c[0], { x: M + 0.38, y, w: 3.0, h: 0.38, fontSize: 11, color: MUT, valign: "middle" });
    mono(s, c[1], { x: M + 3.3, y, w: 2.4, h: 0.38, fontSize: 12, bold: true, color: c[2], align: "right", valign: "middle" });
  });
  mono(s, "숫자는 예시입니다 (실제 값은 대외비)", { x: M + 0.24, y: 4.14, w: 5.6, h: 0.22, fontSize: 8.5, color: DIM });

  const facts = [
    ["가정을 드러낸다", "참여율(일 거래량의 몇 %까지 낼 것인가)을 표에 적고 민감도를 함께 낸다. 숫자만 내면 가정이 숨는다.", CYN],
    ["유효 스프레드", "Roll(1984) 추정치. 호가가 없어도 종가 계열만으로 거래비용을 잰다.", PUR],
    ["비유동성", "Amihud(2002) — 거래대금당 가격 충격. 코스닥 소형주에서 특히 크다.", AMB],
    ["매물대", "가격대별 거래대금 분포. 어느 구간에 물량이 쌓여 있는지 본다.", GRN],
  ];
  facts.forEach((f, i) => {
    const y = 1.90 + i * 0.64;
    panel(s, { x: 6.86, y, w: 5.87, h: 0.56, fill: PANEL, line: EDGE });
    s.addShape(pres.ShapeType.rect, { x: 7.06, y: y + 0.12, w: 0.12, h: 0.32, fill: { color: f[2] }, line: { type: "none" } });
    txt(s, f[0], { x: 7.3, y, w: 1.9, h: 0.56, fontSize: 11.5, bold: true, color: f[2], valign: "middle" });
    txt(s, f[1], { x: 9.2, y, w: 3.4, h: 0.56, fontSize: 9, color: MUT, valign: "middle" });
  });

  panel(s, { x: 6.86, y: 4.5, w: 5.87, h: 1.5, fill: PANEL3, line: EDGE });
  txt(s, "락업이 남아 있으면 소요일수는 의미가 없다", { x: 7.06, y: 4.64, w: 5.4, h: 0.28, fontSize: 12, bold: true, color: GLD });
  txt(s, "처분 여건은 '팔 수 있는 상태인가'와 '판다면 며칠 걸리는가'가 곱해진 값이다. 락업 잔여일이 소요일수보다 길면, 소요일수는 아직 답이 아니라 준비다.", {
    x: 7.06, y: 4.96, w: 5.44, h: 0.9, fontSize: 10, color: INK });

  panel(s, { x: M, y: 4.5, w: 6.1, h: 1.5, fill: "2A1520", line: "5C2A3A" });
  txt(s, "왜 중앙값을 함께 내는가", { x: M + 0.24, y: 4.64, w: 5.6, h: 0.28, fontSize: 12, bold: true, color: MAG });
  txt(s, "실적 발표·테마 뉴스가 있던 며칠이 평균을 끌어올린다. 그날 팔 수 있었을지는 별개 문제다. 중앙값은 '평범한 날'에 낼 수 있는 물량을 본다.", {
    x: M + 0.24, y: 4.96, w: 5.64, h: 0.9, fontSize: 10, color: INK });

  panel(s, { x: M, y: 6.16, w: CW, h: 0.62, fill: PANEL3, line: EDGE });
  txt(s, [
    { text: "출처 등급 — ", options: { bold: true, color: GLD } },
    { text: "[1차] KRX 일별매매정보 거래량·거래대금 · [방법론] 처분 소요일 = 목표 물량 ÷ 기간 거래량, 가정은 표에 명시 · [사내] exit_plan.csv 의 목표 물량", options: { color: MUT } },
  ], { x: M + 0.26, y: 6.16, w: CW - 0.52, h: 0.62, fontSize: 10, valign: "middle", fontFace: F, isTextBox: true, margin: 0 });
}

/* ═══ 10. 어떻게 팔 것인가 ═══ */
function sExecution() {
  const s = slide();
  header(s, "PART 3 · HOW TO SELL", "매도 규칙 네 가지를 과거 구간마다 재현한다",
         "어떤 규칙이 좋은지 주장하지 않는다. 같은 구간에서 네 규칙이 각각 어떤 실현단가를 냈는지만 낸다. 고르는 것은 사람이다.");

  const rules = [
    ["즉시", "IMMEDIATE", "첫날 전량", "기준선. 충격이 가장 크고 시점 위험이 없다.", MAG],
    ["균등", "TWAP", "기간 균등 분할", "가장 단순하다. 유동성이 낮은 날에도 같은 물량을 낸다.", CYN],
    ["유동성비례", "VWAP", "그날 거래량에 비례", "거래가 많은 날 더 낸다. 시장을 따라간다.", GRN],
    ["유동성상위일", "TOP-N", "상위 거래일에만", "가장 좋아 보이지만 사후적 선택이다 — 그 사실을 함께 적는다.", AMB],
  ];
  rules.forEach((r, i) => {
    const x = M + i * 3.06;
    panel(s, { x, y: 1.90, w: 2.86, h: 0.48, fill: r[4], line: null });
    txt(s, r[0], { x: x + 0.14, y: 1.90, w: 1.4, h: 0.48, fontSize: 13, bold: true, color: "0D1018", valign: "middle" });
    mono(s, r[1], { x: x + 1.5, y: 1.90, w: 1.24, h: 0.48, fontSize: 8.5, color: "0D1018", align: "right", valign: "middle" });
    panel(s, { x, y: 2.46, w: 2.86, h: 1.72, fill: PANEL, line: EDGE });
    mono(s, r[2], { x: x + 0.18, y: 2.62, w: 2.5, h: 0.26, fontSize: 10, bold: true, color: r[4] });
    txt(s, r[3], { x: x + 0.18, y: 2.96, w: 2.52, h: 1.06, fontSize: 10, color: MUT });
  });

  const notes = [
    ["가격 충격은 가정이다", "제곱근 모형을 쓴다. 모형이 맞다는 뜻이 아니라, 어떤 모형을 썼는지 밝힌다는 뜻이다. Almgren-Chriss(2000) 를 인용한다.", AMB],
    ["과거 구간마다 반복한다", "한 구간의 결과는 그 구간의 운이다. 여러 구간에서 같은 규칙을 돌려 분포를 본다.", CYN],
    ["사후적 선택을 표시한다", "'유동성 상위일' 은 그날이 상위일인 줄 미리 알 수 없다. 실행 가능한 규칙이 아니라 상한선으로 읽어야 한다.", MAG],
  ];
  notes.forEach((n, i) => {
    const x = M + i * 4.11;
    panel(s, { x, y: 4.36, w: 3.94, h: 1.66, fill: PANEL, line: EDGE });
    s.addShape(pres.ShapeType.rect, { x: x + 0.2, y: 4.54, w: 0.14, h: 0.14, fill: { color: n[2] }, line: { type: "none" } });
    txt(s, n[0], { x: x + 0.46, y: 4.46, w: 3.3, h: 0.3, fontSize: 12, bold: true, color: n[2] });
    txt(s, n[1], { x: x + 0.2, y: 4.84, w: 3.56, h: 1.0, fontSize: 9.5, color: MUT });
  });

  panel(s, { x: M, y: 6.18, w: CW, h: 0.64, fill: "16281C", line: "2A5A3A" });
  txt(s, [
    { text: "이 절이 내지 않는 것 — ", options: { bold: true, color: GRN } },
    { text: "\"VWAP 으로 파십시오\" 같은 권고. 네 규칙의 실현단가와 그 가정만 낸다. 권고를 만드는 순간 산출물의 성격이 바뀌고, 이 도구는 그 선을 넘지 않는다.", options: { color: INK } },
  ], { x: M + 0.26, y: 6.18, w: CW - 0.52, h: 0.64, fontSize: 10.5, valign: "middle", fontFace: F, isTextBox: true, margin: 0 });
}

/* ═══ 11. 코스닥벤처펀드 편입요건 ═══ */
function sFundRule() {
  const s = slide();
  header(s, "PART 3 · FUND CONSTRAINT", "코스닥벤처펀드 편입요건 — 다음에 붙일 것",
         "회수는 수익률 문제이기 전에 요건 문제다. 팔면 비율이 깨지는 상황을 회수 판단 전에 알아야 한다.");

  const req = [
    ["벤처기업 신주", "15% 이상", "펀드 자산 기준. 신주여야 하므로 구주 매입으로는 못 채운다.", GRN],
    ["벤처 + 코스닥 중소·중견", "35% 이상", "벤처기업, 또는 벤처 해제 후 7년 이내 코스닥 중소·중견기업.", CYN],
    ["합계", "50% 이상", "위 둘을 합쳐 자산의 절반 이상을 유지해야 한다.", AMB],
    ["코스닥 공모주 우선배정", "30% 이상", "2026-01-01 이후 25% → 30% 로 상향됐다.", PUR],
  ];
  req.forEach((r, i) => {
    const y = 1.90 + i * 0.88;
    panel(s, { x: M, y, w: 7.0, h: 0.78, fill: PANEL, line: EDGE });
    txt(s, r[0], { x: M + 0.22, y: y + 0.06, w: 4.8, h: 0.28, fontSize: 12, bold: true, color: INK });
    txt(s, r[2], { x: M + 0.22, y: y + 0.38, w: 4.85, h: 0.32, fontSize: 9.5, color: MUT });
    s.addShape(pres.ShapeType.rect, { x: M + 5.3, y: y + 0.19, w: 1.3, h: 0.4, fill: { color: r[3] }, line: { type: "none" } });
    mono(s, r[1], { x: M + 5.3, y: y + 0.19, w: 1.3, h: 0.4, fontSize: 10.5, bold: true, color: "0D1018", align: "center", valign: "middle" });
  });

  panel(s, { x: 7.82, y: 1.90, w: 4.91, h: 2.4, fill: PANEL, line: GLD });
  txt(s, "무엇을 계산할 것인가", { x: 8.04, y: 2.04, w: 4.5, h: 0.28, fontSize: 12.5, bold: true, color: GLD });
  ["현재 편입비율 (신주 · 합계)", "이 종목을 전량 처분하면 비율이 얼마가 되는가",
   "요건 미달까지 남은 여유 금액", "전환 시 신주 인정 여부 (구주 전환은 신주가 아니다)"].forEach((t, i) => {
    s.addImage({ data: img("ar_am"), x: 8.04, y: 2.48 + i * 0.44, w: 0.24, h: 0.15 });
    txt(s, t, { x: 8.36, y: 2.4 + i * 0.44, w: 4.2, h: 0.4, fontSize: 10, color: INK });
  });

  panel(s, { x: 7.82, y: 4.48, w: 4.91, h: 1.54, fill: "2A1520", line: "5C2A3A" });
  txt(s, "아직 구현하지 않았다", { x: 8.04, y: 4.62, w: 4.5, h: 0.28, fontSize: 12.5, bold: true, color: MAG });
  txt(s, "펀드 단위 데이터(수탁고·편입 원장)가 이 도구에 없기 때문이다. 종목 단위 측정은 되지만 펀드 단위 제약은 사내 데이터가 붙어야 한다. 있는 척하지 않고 '다음에 붙일 것' 으로 적어 둔다.", {
    x: 8.04, y: 4.94, w: 4.52, h: 1.0, fontSize: 9.5, color: INK });

  panel(s, { x: M, y: 5.50, w: 7.0, h: 0.52, fill: PANEL3, line: EDGE });
  txt(s, "세제 혜택도 바뀐다 — 2026 과세연도부터 소득공제 한도가 축소됐다(경과규정 있음). 판매 논리가 아니라 환매 압력의 변수로 본다.", {
    x: M + 0.22, y: 5.50, w: 6.6, h: 0.52, fontSize: 9.5, color: INK, valign: "middle" });

  panel(s, { x: M, y: 6.18, w: CW, h: 0.64, fill: PANEL3, line: EDGE });
  txt(s, [
    { text: "[참고] ", options: { bold: true, color: AMB } },
    { text: "위 수치는 금융위원회·금융투자협회 공개자료 기준이며 제도는 자주 바뀐다. 실제 운용에 쓰기 전에 현행 규정 원문으로 재확인해야 한다 — 이 도구의 원칙대로, 확인한 날짜와 함께 적는다.", options: { color: INK } },
  ], { x: M + 0.26, y: 6.18, w: CW - 0.52, h: 0.64, fontSize: 10, valign: "middle", fontFace: F, isTextBox: true, margin: 0 });
}

/* ═══ 12. 데이터 ═══ */
function sData() {
  const s = slide();
  header(s, "PART 4 · DATA", "전부 1차 출처다 — 크롤링도, 벤더 데이터도 없다",
         "2차 가공물(증권사 리포트·언론 기사)을 근거로 쓰지 않는다. 출처가 곧 신뢰도이고, 신뢰도는 절마다 표시된다.");

  const src = [
    ["KRX Open API", "한국거래소", "종목 일별시세 · 지수 · 국고채 · 선물", "헤더 AUTH_KEY", GRN],
    ["DART Open API", "금융감독원", "공시목록 · 기업개황 · 주요계정 · 대량보유 · CB발행", "쿼리 crtfc_key", CYN],
    ["ECOS Open API", "한국은행", "100대 통계지표 (기준금리 · 환율 · 물가)", "인증키", PUR],
    ["KIS Open API", "한국투자증권", "국내주식 현재가 · 호가 (시세 2종만)", "앱키/시크릿", AMB],
    ["FRED", "세인트루이스 연준", "미국 국채 2년·10년 · 스프레드 · 달러지수", "무료 키", BLU],
  ];
  src.forEach((r, i) => {
    const y = 1.90 + i * 0.66;
    panel(s, { x: M, y, w: 7.9, h: 0.58, fill: PANEL, line: EDGE });
    s.addShape(pres.ShapeType.rect, { x: M + 0.18, y: y + 0.12, w: 0.12, h: 0.34, fill: { color: r[4] }, line: { type: "none" } });
    mono(s, r[0], { x: M + 0.44, y, w: 1.9, h: 0.58, fontSize: 10, bold: true, color: r[4], valign: "middle" });
    txt(s, r[1], { x: M + 2.34, y, w: 1.4, h: 0.58, fontSize: 9.5, color: MUT, valign: "middle" });
    txt(s, r[2], { x: M + 3.74, y, w: 3.0, h: 0.58, fontSize: 9.5, color: INK, valign: "middle" });
    mono(s, r[3], { x: M + 6.7, y, w: 1.1, h: 0.58, fontSize: 8, color: DIM, align: "right", valign: "middle" });
  });

  const notes = [
    ["\"API 가 된다\" ≠ \"내 필드가 맞다\"", "호출이 200 이어도 필드명을 하나 잘못 적으면 그 값은 조용히 None 이 되고 리포트엔 '데이터 없음' 이 찍힌다. 틀렸다는 신호가 어디에도 안 뜬다.", MAG],
    ["그래서 필드를 얼려 뒀다", "각 기관 공식 예제·표준 클라이언트에서 응답 필드를 뽑아 .api_fields.json 에 고정하고, selftest 가 매번 '내 매핑이 그 안에 있는가' 를 검사한다. 네트워크 없이 돈다.", GRN],
    ["주문 API 는 막았다", "KIS 는 같은 서버에 주문이 있다. 시세 조회 2종만 화이트리스트에 두고, 그 밖은 OrderNotAllowed 로 막는다. selftest 가 검사한다.", CYN],
  ];
  notes.forEach((n, i) => {
    const y = 1.90 + i * 1.44;
    panel(s, { x: 8.72, y, w: 4.01, h: 1.32, fill: PANEL, line: EDGE });
    txt(s, n[0], { x: 8.94, y: y + 0.14, w: 3.6, h: 0.44, fontSize: 11, bold: true, color: n[2] });
    txt(s, n[1], { x: 8.94, y: y + 0.6, w: 3.62, h: 0.64, fontSize: 9, color: MUT });
  });

  panel(s, { x: M, y: 5.32, w: 7.9, h: 1.5, fill: PANEL3, line: EDGE });
  txt(s, "제3자 저작 계열은 기본값에서 뺐다", { x: M + 0.24, y: 5.46, w: 7.4, h: 0.28, fontSize: 12, bold: true, color: GLD });
  txt(s, "VIX(Cboe) · 나스닥종합(Nasdaq) · 미국 하이일드 스프레드(ICE) 는 FRED 로 받을 수는 있으나 저작권이 제3자에게 있다. --include-restricted 로만 켜지고, 켜면 리포트에 저작권 주체가 함께 찍힌다. 이미 적재된 것은 --purge-restricted 로 지운다.", {
    x: M + 0.24, y: 5.78, w: 7.44, h: 0.92, fontSize: 10, color: INK });
}


/* ═══ 13. 검증 ═══ */
function sVerify() {
  const s = slide();
  header(s, "PART 4 · VERIFICATION", "예외가 안 난다고 맞는 게 아니다",
         "금융 데이터 코드는 조용히 틀린다. 컬럼이 뒤바뀌어도, 단위가 천원이어도 계산은 끝까지 돌아간다. 그래서 값이 상식적인지를 따로 검사한다.");

  const kinds = [
    ["교차검산", "같은 값을 두 경로로 구해 맞춰 본다", "거래대금 ÷ 거래량 이 고가·저가 범위 안에 들어오는가", GRN],
    ["항등식", "정의상 반드시 성립해야 하는 식", "종가 × 상장주식수 = 시가총액", CYN],
    ["방향성", "부호·대소 관계가 맞는가", "완전희석 지분 < 보통주 지분 · 리픽싱이 희석을 키운다", AMB],
    ["결측 처리", "모를 때 모른다고 하는가", "F-Score 항목 하나가 비면 0 이 아니라 None 을 낸다", PUR],
    ["주입 방어", "리포트에 들어가는 문자열", "_esc() 를 거치지 않은 <script> 가 HTML 에 들어가지 않는가", MAG],
    ["유출 방어", "예외 문구에 키가 남는가", "DART 는 인증키를 쿼리로 보낸다 — 모든 예외를 scrub() 에 통과시킨다", ORG],
  ];
  kinds.forEach((k, i) => {
    const x = M + (i % 3) * 4.11, y = 1.88 + Math.floor(i / 3) * 1.68;
    panel(s, { x, y, w: 3.94, h: 1.5, fill: PANEL, line: EDGE });
    s.addShape(pres.ShapeType.rect, { x: x + 0.2, y: y + 0.18, w: 0.12, h: 0.32, fill: { color: k[3] }, line: { type: "none" } });
    txt(s, k[0], { x: x + 0.44, y: y + 0.14, w: 3.3, h: 0.3, fontSize: 13, bold: true, color: k[3] });
    txt(s, k[1], { x: x + 0.2, y: y + 0.48, w: 3.56, h: 0.28, fontSize: 9.5, color: MUT });
    s.addShape(pres.ShapeType.rect, { x: x + 0.2, y: y + 0.8, w: 3.56, h: 0.56, fill: { color: PANEL2 }, line: { type: "none" } });
    txt(s, k[2], { x: x + 0.32, y: y + 0.8, w: 3.34, h: 0.56, fontSize: 9, color: INK, valign: "middle" });
  });

  panel(s, { x: M, y: 5.28, w: 5.9, h: 1.54, fill: "0A1020", line: EDGE });
  mono(s, [
    '$ python ki_monitor.py selftest',
    '',
    '  128 passed, 0 failed  (총 128)',
    '',
    '$ python docs/audit.py',
    '  전부 통과 (2건 경고)',
  ].join("\n"), { x: M + 0.24, y: 5.42, w: 5.5, h: 1.3, fontSize: 10, color: GRN, lineSpacing: 13, valign: "top" });

  panel(s, { x: 6.72, y: 5.28, w: 6.01, h: 1.54, fill: PANEL, line: EDGE });
  txt(s, "테스트가 못 보는 것은 감사 스크립트가 본다", { x: 6.94, y: 5.42, w: 5.6, h: 0.28, fontSize: 12, bold: true, color: GLD });
  txt(s, "줄바꿈이 뒤집혔는지(CRLF/LF), 배치 파일의 괄호·라벨이 성립하는지, 저장소에 키나 실명이 새지 않았는지, 문서에 적힌 테스트 개수가 실제와 맞는지 — docs/audit.py 가 검사한다. 키·네트워크 없이 돈다.", {
    x: 6.94, y: 5.74, w: 5.62, h: 0.96, fontSize: 9.5, color: MUT });
}

/* ═══ 14. 모르는 것을 모른다고 ═══ */
function sUnknown() {
  const s = slide();
  header(s, "PART 4 · KNOWING WHAT WE DON'T KNOW", "없는 값을 만들지 않는다",
         "0 으로 채우면 계산은 끝까지 돌아가고, 받는 쪽은 '측정 못 함' 과 '0 으로 측정됨' 을 구분할 수 없게 된다.");

  const cases = [
    ["못 구한 값", "None + 사유", "0 으로 채우지 않는다. F-Score 항목 하나가 비면 점수를 내지 않는다.", GRN],
    ["표본 부족", "계산 거부", "동종 비교군 표본이 적으면 그 사실을 적고 비교를 하지 않는다.", CYN],
    ["판별 불가", "'확인 필요' 로 표시", "권리락인지 희석인지 판별이 안 되면 조정하지도, 지우지도 않는다.", AMB],
    ["묵은 값", "기준일 + 경과일수", "원장은 일별 종가라 며칠 묵을 수 있다. 몇 주 된 종가가 현재가 행세를 하는 것이 가장 조용한 실패다.", PUR],
    ["추정한 값", "등급 '추정' 고정", "락업은 관행으로 계산한 것이지 확약이 아니다. 값에 등급이 붙어 리포트에 함께 실린다.", MAG],
  ];
  cases.forEach((c, i) => {
    const y = 1.90 + i * 0.86;
    panel(s, { x: M, y, w: CW, h: 0.74, fill: PANEL, line: EDGE });
    txt(s, c[0], { x: M + 0.24, y, w: 2.0, h: 0.74, fontSize: 12.5, bold: true, color: INK, valign: "middle" });
    s.addShape(pres.ShapeType.rect, { x: M + 2.36, y: y + 0.17, w: 2.0, h: 0.4, fill: { color: c[3] }, line: { type: "none" } });
    mono(s, c[1], { x: M + 2.36, y: y + 0.17, w: 2.0, h: 0.4, fontSize: 10, bold: true, color: "0D1018", align: "center", valign: "middle" });
    txt(s, c[2], { x: M + 4.6, y, w: 7.3, h: 0.74, fontSize: 10.5, color: MUT, valign: "middle" });
  });

  panel(s, { x: M, y: 6.30, w: CW, h: 0.54, fill: "16281C", line: "2A5A3A" });
  txt(s, [
    { text: "모른다는 것을 아는 게 낫다. ", options: { bold: true, color: GRN } },
    { text: "회수 회의에서 가장 비싼 실수는 틀린 숫자가 아니라, 틀린 줄 모르고 쓴 숫자다.", options: { color: INK } },
  ], { x: M + 0.26, y: 6.30, w: CW - 0.52, h: 0.54, fontSize: 11, valign: "middle", fontFace: F, isTextBox: true, margin: 0 });
}

/* ═══ 15. 출처 등급 ═══ */
function sGrade() {
  const s = slide();
  header(s, "PART 4 · SOURCE GRADING", "재료에는 등급이 있다 — 같은 표에 섞지 않는다",
         "회의에서 가장 먼저 나오는 질문은 \"그 숫자 어디서 났나요\" 다. 절마다 하단에 출처와 등급을 적어 둔다.");

  const grades = [
    ["1차", "근거로 삼아도 된다", "KRX · DART · 한국은행 ECOS · KIS", GRN],
    ["참고", "\"이런 이야기가 돈다\" 까지만", "뉴스 헤드라인 · 심리지표 (본문은 쓰지 않는다)", AMB],
    ["방법론", "계산 규칙의 출처이지 시세 출처가 아니다", "논문 — .papers.json 채택본만 인용 가능", CYN],
    ["사내", "우리가 넣은 값", "exit_plan.csv · positions.csv · watchlist.csv", PUR],
  ];
  grades.forEach((g, i) => {
    const x = M + i * 3.06;
    panel(s, { x, y: 1.90, w: 2.86, h: 0.5, fill: g[3], line: null });
    mono(s, g[0], { x, y: 1.90, w: 2.86, h: 0.5, fontSize: 14, bold: true, color: "0D1018", align: "center", valign: "middle" });
    panel(s, { x, y: 2.48, w: 2.86, h: 1.76, fill: PANEL, line: EDGE });
    txt(s, g[1], { x: x + 0.18, y: 2.64, w: 2.5, h: 0.6, fontSize: 11, bold: true, color: INK });
    txt(s, g[2], { x: x + 0.18, y: 3.3, w: 2.52, h: 0.8, fontSize: 9.5, color: MUT });
  });

  panel(s, { x: M, y: 4.44, w: 7.9, h: 1.4, fill: "0A1020", line: EDGE });
  mono(s, "SECTION_SOURCES — 절마다 하단에 찍힌다", { x: M + 0.24, y: 4.56, w: 5.0, h: 0.24, fontSize: 9.5, bold: true, color: GLD });
  mono(s, [
    '"s2": [("1차",   "KRX Open API 일별매매정보 — 거래량·거래대금·상장주식수"),',
    '       ("1차",   "DART Open API — 최대주주·지분 공시"),',
    '       ("방법론", "처분 소요일 = 목표 물량 ÷ 기간 평균 거래량 (가정은 표에 명시)")],',
  ].join("\n"), { x: M + 0.24, y: 4.84, w: 7.46, h: 0.9, fontSize: 8.4, color: "A9C8F0", lineSpacing: 12, valign: "top" });

  panel(s, { x: 8.72, y: 4.44, w: 4.01, h: 1.4, fill: PANEL, line: MAG });
  txt(s, "논문은 시세 출처가 아니다", { x: 8.94, y: 4.58, w: 3.6, h: 0.28, fontSize: 12, bold: true, color: MAG });
  txt(s, "팩터는 논문 키를 달고 나가고, selftest 가 \"모든 팩터가 실재하는 논문을 인용하는가\" 를 검사한다. 그리고 그 논문이 주장하지 않는 것(limits)을 값과 함께 낸다.", {
    x: 8.94, y: 4.90, w: 3.62, h: 0.86, fontSize: 9.5, color: MUT });

  panel(s, { x: M, y: 6.02, w: CW, h: 0.8, fill: PANEL3, line: EDGE });
  txt(s, [
    { text: "가장 흔한 사고는 ", options: { color: INK } },
    { text: "논문이 말한 적 없는 것을 말했다고 읽는 것", options: { bold: true, color: MAG } },
    { text: " 이다.\n", options: { color: INK } },
    { text: "예: Amihud(2002) 의 표본은 미국 상장주다. 코스닥 소형주에 그대로 외삽할 근거가 아니며, 그 문장이 값 옆에 붙어 나간다.", options: { color: MUT } },
  ], { x: M + 0.26, y: 6.02, w: CW - 0.52, h: 0.8, fontSize: 10.5, valign: "middle", lineSpacing: 17, fontFace: F, isTextBox: true, margin: 0 });
}

/* ═══ 17. 에이전트 조직 (압축) ═══ */
function sAgents() {
  const s = slide();
  header(s, "PART 5 · SCALING", "다음 단계 — 데스크 에이전트로 읽기를 나눈다",
         "측정은 이미 된다. 병목은 85개 종목의 상세를 읽을 사람이 한 명이라는 것이다. 읽기를 나누되, 판단은 나누지 않는다.");

  const desks = [
    ["ag_equity", "기업분석", "공시 원문 · 재무", BLU],
    ["ag_quant", "계량", "팩터 · 논문 재현", PUR],
    ["ag_macro", "매크로", "국면 · 일정", CYN],
    ["ag_exec", "집행", "처분여건 · 시뮬", AMB],
    ["ag_risk", "리스크", "숫자 재검산", MAG],
    ["ag_compliance", "준법감시", "발행 게이트", ORG],
    ["ag_dataops", "데이터", "원장 쓰기 단독", GRN],
    ["ag_chair", "간사", "쟁점 정렬", GLD],
  ];
  desks.forEach((d, i) => {
    const x = M + (i % 4) * 3.06, y = 1.88 + Math.floor(i / 4) * 1.32;
    panel(s, { x, y, w: 2.86, h: 1.2, fill: PANEL, line: EDGE });
    s.addImage({ data: img(d[0]), x: x + 0.18, y: y + 0.3, w: 0.6, h: 0.6 });
    txt(s, d[1], { x: x + 0.88, y: y + 0.26, w: 1.8, h: 0.3, fontSize: 12.5, bold: true, color: d[3] });
    txt(s, d[2], { x: x + 0.88, y: y + 0.58, w: 1.86, h: 0.44, fontSize: 9.5, color: MUT });
  });

  const keys = [
    ["벽은 구조다", "원장(ki.sqlite)을 쓸 수 있는 도구를 에이전트에게 만들어 주지 않는다. MCP 서버에 읽기 도구만 노출한다 — \"쓰지 마라\" 는 지시가 아니라 쓸 수단이 없는 상태다.", GRN],
    ["산출은 등급 '해석'", "에이전트가 쓴 문장은 무엇을 근거로 삼았든 1차 자료가 되지 않는다. 다섯 번째 등급을 만들어 측정값과 섞이지 않게 한다.", MAG],
    ["이벤트로 소집한다", "공시 1건 = 인스턴스 1개. 봉투를 내면 소멸한다. 무상태라 같은 입력이면 같은 결과가 나오고, 그래서 되짚을 수 있다.", CYN],
  ];
  keys.forEach((k, i) => {
    const x = M + i * 4.11;
    panel(s, { x, y: 4.6, w: 3.94, h: 1.6, fill: PANEL3, line: EDGE });
    txt(s, k[0], { x: x + 0.2, y: 4.74, w: 3.5, h: 0.3, fontSize: 12, bold: true, color: k[2] });
    txt(s, k[1], { x: x + 0.2, y: 5.06, w: 3.56, h: 1.0, fontSize: 9.5, color: MUT });
  });

  panel(s, { x: M, y: 6.34, w: CW, h: 0.54, fill: PANEL3, line: EDGE });
  txt(s, [
    { text: "자동화 대상은 '독해와 정렬' 이다. ", options: { bold: true, color: GLD } },
    { text: "판단은 지금과 똑같이 회의에서 사람이 한다 — 이 경계가 흔들리면 실패다.", options: { color: INK } },
  ], { x: M + 0.26, y: 6.34, w: CW - 0.52, h: 0.54, fontSize: 11, valign: "middle", fontFace: F, isTextBox: true, margin: 0 });
}

/* ═══ 18. 앞으로 ═══ */
function sNextUp() {
  const s = slide();
  header(s, "PART 5 · WHAT'S NEXT", "다음에 채울 것 — 있는 척하지 않는다",
         "지금 없는 것을 정확히 적어 두는 편이, 있는 것처럼 보이게 만드는 것보다 낫다.");

  const todo = [
    ["메자닌 지표 보강", "패리티(주가÷전환가) · 전환프리미엄 · put 행사 가능일과 행사 시 IRR · 리픽싱 여력(현 전환가 → 하한까지)", "W1–3", GRN],
    ["발행조건 구조화", "지금은 cb_amount · cb_conv_price 두 값뿐이다. 주요사항보고서 원문에서 조정주기 · 하한 · put/call 조항을 구조화한다", "W3–6", CYN],
    ["펀드 단위 제약", "코스닥벤처펀드 편입비율 모니터링. 사내 편입 원장이 붙어야 가능하다", "사내 데이터 필요", AMB],
    ["논문 재현 관문", "채택본 12편이 코스닥에서 실제로 성립하는지 소급 재현한다. 통과한 것만 인용 자격을 준다", "W4–8", PUR],
    ["데스크 에이전트", "읽기를 나눈다. 원장 쓰기 권한은 주지 않는다", "W8–", MAG],
  ];
  todo.forEach((t, i) => {
    const y = 1.90 + i * 0.94;
    panel(s, { x: M, y, w: CW, h: 0.82, fill: PANEL, line: EDGE });
    s.addShape(pres.ShapeType.rect, { x: M + 0.2, y: y + 0.19, w: 0.44, h: 0.44, fill: { color: t[3] }, line: { type: "none" } });
    mono(s, String(i + 1), { x: M + 0.2, y: y + 0.19, w: 0.44, h: 0.44, fontSize: 14, bold: true, color: "0D1018", align: "center", valign: "middle" });
    txt(s, t[0], { x: M + 0.8, y: y + 0.11, w: 3.2, h: 0.3, fontSize: 12.5, bold: true, color: INK });
    txt(s, t[1], { x: M + 0.8, y: y + 0.42, w: 8.6, h: 0.32, fontSize: 9.5, color: MUT });
    mono(s, t[2], { x: M + 9.6, y: y + 0.11, w: 2.3, h: 0.3, fontSize: 10, bold: true, color: t[3], align: "right" });
  });

  panel(s, { x: M, y: 6.62, w: CW, h: 0.5, fill: PANEL3, line: EDGE });
  txt(s, "가장 먼저 알아야 할 숫자 — 채택본 12편 중 몇 편이 코스닥에서 실제로 성립하는가. 지금은 아무도 모른다.", {
    x: M + 0.26, y: 6.62, w: CW - 0.52, h: 0.5, fontSize: 11, bold: true, color: GLD, valign: "middle" });
}

/* ═══ 19. 마무리 ═══ */
function sClose() {
  const s = slide();
  for (let i = 0; i < 42; i++) s.addShape(pres.ShapeType.rect, {
    x: 0, y: i * 0.18, w: W, h: 0.03, fill: { color: "121826" }, line: { type: "none" } });

  mono(s, "▚ SUMMARY", { x: M, y: 0.46, w: CW, h: 0.26, fontSize: 11, bold: true, color: AMB, charSpacing: 1.5 });
  txt(s, "이 프로젝트로 보여드리고 싶은 것", {
    x: M, y: 0.76, w: CW, h: 0.56, fontSize: 28, bold: true, color: INK });

  const points = [
    ["메자닌 구조를 계산으로 옮길 수 있다", "리픽싱 · 완전희석 · 전환 잠재주식수를 조항에서 코드로 옮겼고, 그 계산이 맞는지 방향성 테스트로 검사한다.", GRN],
    ["실무에서만 보이는 함정을 안다", "CB 전환을 권리락으로 처리하면 과거 수익률이 조용히 틀어진다. 이 구분을 코드와 테스트로 남겼다.", CYN],
    ["데이터의 신뢰도를 관리한다", "1차 출처만 쓰고, 응답 필드를 얼려 두고, 절마다 출처와 등급을 찍는다. 못 구한 값은 None 으로 낸다.", AMB],
    ["측정과 판단을 분리한다", "점수 · 등급 · 목표주가를 만들지 않는다. 회의에 올리는 것은 측정값과 그 가정 · 한계다.", PUR],
    ["혼자서 끝까지 만든다", "수집 · 계산 · 검증 · 리포트 · 자동 실행까지 8,684줄 단일 파일로 돌아가고, 자체 검증 128개가 매번 통과한다.", MAG],
  ];
  points.forEach((p, i) => {
    const y = 1.60 + i * 0.98;
    panel(s, { x: M, y, w: 8.3, h: 0.86, fill: "16274A", line: "2C3E6B" });
    s.addShape(pres.ShapeType.rect, { x: M + 0.2, y: y + 0.2, w: 0.14, h: 0.46, fill: { color: p[2] }, line: { type: "none" } });
    txt(s, p[0], { x: M + 0.52, y: y + 0.12, w: 7.5, h: 0.3, fontSize: 13, bold: true, color: INK });
    txt(s, p[1], { x: M + 0.52, y: y + 0.44, w: 7.6, h: 0.36, fontSize: 9.5, color: "9FB3D6" });
  });

  mono(s, "저장소", { x: 9.2, y: 1.60, w: 3.5, h: 0.26, fontSize: 11, bold: true, color: AMB, charSpacing: 1 });
  mono(s, "github.com/InnbumBaek/\nStock_Agent", { x: 9.2, y: 1.90, w: 3.5, h: 0.5, fontSize: 10.5, color: CYN, lineSpacing: 14 });

  const st = [["8,684", "줄 · 단일 파일"], ["128", "자체 검증 · 전부 통과"], ["5", "1차 출처 API"], ["12", "인용 논문 (재현 예정)"]];
  st.forEach((t, i) => {
    const y = 2.68 + i * 0.86;
    mono(s, t[0], { x: 9.2, y, w: 3.5, h: 0.4, fontSize: 24, bold: true, color: GLD });
    txt(s, t[1], { x: 9.2, y: y + 0.4, w: 3.5, h: 0.24, fontSize: 10, color: ICE_ });
  });

  panel(s, { x: M, y: 6.56, w: 8.3, h: 0.5, fill: "16281C", line: "2A5A3A" });
  txt(s, "이 도구가 하지 않는 일 — 매매 시그널, 목표주가, 투자 권고. 그 선을 지키는 것이 설계의 핵심입니다.", {
    x: M + 0.24, y: 6.56, w: 7.9, h: 0.5, fontSize: 10.5, bold: true, color: GRN, valign: "middle" });
  mono(s, "내부 검토용 · 대외비 · 투자권유 · 투자자문 자료가 아닙니다", {
    x: 9.2, y: 6.56, w: 3.5, h: 0.5, fontSize: 8.5, color: DIM, valign: "middle" });
}

function sReplication() {
  const s = slide();
  header(s, "PART 5 · ★ REPLICATION GATE", "재현 관문 — 인용하기 전에 우리 데이터로 계산해 본다",
         "이 데스크가 다루는 것은 코스닥 소형주다. 논문 표본이 미국 대형주라면, 그 결론은 가설이지 근거가 아니다.");

  const steps = [
    ["논문에서 검정 가능한 주장 하나를 뽑는다", "\"거래량이 낮을수록 이후 수익률이 높다\" 처럼 방향이 있는 한 문장으로 환원한다. 환원되지 않으면 재현 대상이 아니다."],
    ["원장에서 그 팩터를 계산한다", "ki.sqlite 일봉으로 팩터를 만든다. 새 데이터를 받지 않는다 — 이미 KRX 공식 API 로 받아 둔 것만 쓴다."],
    ["코스닥 전종목에 적용해 방향을 본다", "분위 포트폴리오 스프레드의 부호가 논문과 같은가. 표본이 부족하면 계산을 거부한다(기존 원칙 그대로)."],
    ["세 가지 중 하나로 판정한다", "재현됨 / 방향 반대 / 판정 불가. 재현되지 않아도 지우지 않고 결과를 남긴다."],
    ["재현된 것만 채택본으로 넘긴다", "판정 결과와 표본 구간이 논문 항목에 함께 저장돼, 리포트에 인용될 때 같이 따라 나간다."],
  ];
  steps.forEach((st, i) => {
    const y = 1.84 + i * 0.86;
    panel(s, { x: M, y, w: 6.5, h: 0.76, fill: PANEL, line: EDGE });
    s.addShape(pres.ShapeType.rect, { x: M + 0.14, y: y + 0.16, w: 0.44, h: 0.44, fill: { color: GRN }, line: { type: "none" } });
    mono(s, String(i + 1), { x: M + 0.14, y: y + 0.16, w: 0.44, h: 0.44, fontSize: 14, bold: true, color: "0D1018", align: "center", valign: "middle" });
    txt(s, st[0], { x: M + 0.72, y: y + 0.08, w: 5.6, h: 0.28, fontSize: 12.5, bold: true, color: INK });
    txt(s, st[1], { x: M + 0.72, y: y + 0.36, w: 5.6, h: 0.36, fontSize: 9.5, color: MUT });
  });

  panel(s, { x: 7.44, y: 1.84, w: 5.29, h: 4.3, fill: PANEL, line: EDGE });
  mono(s, "판정 예시  ·  win=60 · KOSDAQ 전종목", { x: 7.64, y: 1.98, w: 4.9, h: 0.26, fontSize: 10, bold: true, color: AMB });
  const ex = [
    ["amihud2002", "비유동성 ↑ → 수익 ↑", "재현됨", GRN, "ic_ok"],
    ["dnr1998", "회전율 ↓ → 수익 ↑", "재현됨", GRN, "ic_ok"],
    ["jt1993", "6개월 모멘텀 지속", "방향 반대", MAG, "ic_no"],
    ["ahxz2006", "특이변동성 ↑ → 수익 ↓", "판정 불가", DIM, "ic_no"],
    ["roll1984", "스프레드 추정", "재현됨", GRN, "ic_ok"],
  ];
  ex.forEach((e, i) => {
    const y = 2.34 + i * 0.52;
    s.addShape(pres.ShapeType.rect, { x: 7.64, y, w: 4.9, h: 0.44, fill: { color: i % 2 ? PANEL3 : PANEL2 }, line: { type: "none" } });
    mono(s, e[0], { x: 7.76, y, w: 1.4, h: 0.44, fontSize: 9.5, bold: true, color: INK, valign: "middle" });
    txt(s, e[1], { x: 9.20, y, w: 2.0, h: 0.44, fontSize: 9.5, color: MUT, valign: "middle" });
    s.addImage({ data: img(e[4]), x: 11.24, y: y + 0.14, w: 0.17, h: 0.17 });
    mono(s, e[2], { x: 11.48, y, w: 1.0, h: 0.44, fontSize: 9.5, bold: true, color: e[3], valign: "middle" });
  });
  txt(s, "jt1993 모멘텀은 코스닥에서 방향이 뒤집힌다 — 널리 알려진 사실이다.\n인용은 하되 \"우리 표본에서는 반대\"가 값에 붙어 나간다.", {
    x: 7.64, y: 5.10, w: 4.9, h: 0.5, fontSize: 9.5, italic: true, color: AMB, lineSpacing: 13 });
  txt(s, "판정은 매번 표본 구간과 함께 기록된다. 같은 논문이라도 구간이 바뀌면 판정이 바뀔 수 있고, 그 변화 자체가 신호다.", {
    x: 7.64, y: 5.68, w: 4.9, h: 0.5, fontSize: 9.5, color: MUT, lineSpacing: 13 });

  panel(s, { x: M, y: 6.18, w: CW, h: 0.66, fill: "2A1520", line: "5C2A3A" });
  txt(s, [
    { text: "재현 실패는 실패가 아니다.  ", options: { bold: true, color: MAG } },
    { text: "\"이 논문은 코스닥에서 성립하지 않는다\"는 것도 측정 결과다. 지우지 않고 남겨 두면, 다음 사람이 같은 논문을 다시 주워 오는 일을 막는다.", options: { color: INK } },
  ], { x: M + 0.26, y: 6.18, w: CW - 0.52, h: 0.66, fontSize: 11.5, valign: "middle", fontFace: F, isTextBox: true, margin: 0 });
}


/* ═══ 슬라이드 순서 (19장) ═══ */
sCover();      sOnePager();   sQuestions();
sWhyHard();    sRefix();      sDilution();   sNotExRight();  sLockup();
sLiquidity();  sExecution();  sFundRule();
sData();       sVerify();     sUnknown();    sGrade();
sReplication(); sAgents();    sNextUp();     sClose();

pres.writeFile({ fileName: process.argv[2] || "pf.pptx" })
  .then(f => console.log("WROTE " + f))
  .catch(e => { console.error(e); process.exit(1); });
