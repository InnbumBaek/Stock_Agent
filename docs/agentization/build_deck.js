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


function sTitle() {
  const s = slide();
  // 스캔라인
  for (let i = 0; i < 42; i++) s.addShape(pres.ShapeType.rect, {
    x: 0, y: i * 0.18, w: W, h: 0.03, fill: { color: "121826" }, line: { type: "none" },
  });

  mono(s, "STOCK_AGENT  ·  에이전트화 계획안  ·  INTERNAL  ·  NOT INVESTMENT ADVICE", {
    x: M, y: 0.52, w: 10, h: 0.26, fontSize: 11, bold: true, color: AMB, charSpacing: 1,
  });

  txt(s, "살아있는 리서치 데스크", {
    x: M, y: 1.28, w: 11.4, h: 0.86, fontSize: 46, bold: true, color: INK,
  });
  mono(s, "논문이 흐르고, 에이전트가 소집된다", {
    x: M, y: 2.16, w: 11.4, h: 0.42, fontSize: 20, bold: true, color: GRN,
  });
  txt(s, "대형 증권사 조직을 그대로 옮기되, 논문은 매주 새로 들어와 재현 검사를 통과한 것만 살아남고\n에이전트는 이벤트가 뜰 때만 소집됐다가 봉투를 내고 사라진다.", {
    x: M, y: 2.68, w: 11.4, h: 0.66, fontSize: 13, color: MUT, lineSpacing: 20,
  });

  // 에이전트 8기 + 바닥
  const sprites = ["ag_equity", "ag_quant", "ag_macro", "ag_exec", "ag_risk", "ag_compliance", "ag_dataops", "ag_chair"];
  const labels = ["기업분석", "계량", "매크로", "집행", "리스크", "준법", "데이터", "간사"];
  const sw = 0.82, gap = 0.62;
  const totalW = sprites.length * sw + (sprites.length - 1) * (gap - sw);
  sprites.forEach((sp, i) => {
    const x = M + i * gap;
    s.addImage({ data: img(sp), x, y: 4.02, w: sw, h: sw });
    mono(s, labels[i], { x: x - 0.12, y: 5.04, w: sw + 0.24, h: 0.22, fontSize: 8.5, color: DIM, align: "center" });
  });
  floorRow(s, M - 0.02, 4.84, 5.16, 0.129, "1B2338", "141B2C");

  const chips = [["N", "살아있는 논문", "고정 12편이 아니다"], ["주 1회", "논문 사이클", "일회성 배치가 아니다"],
                 ["7", "발행 게이트", "재현 관문 신설"], ["0", "원장 쓰기 권한", "에이전트는 못 쓴다"]];
  chips.forEach((c, i) => {
    const x = M + i * 3.06;
    panel(s, { x, y: 5.42, w: 2.86, h: 1.06, fill: PANEL, line: EDGE });
    mono(s, c[0], { x: x + 0.16, y: 5.54, w: 2.5, h: 0.34, fontSize: 21, bold: true, color: GLD });
    txt(s, c[1], { x: x + 0.16, y: 5.90, w: 2.5, h: 0.24, fontSize: 11, bold: true, color: INK });
    txt(s, c[2], { x: x + 0.16, y: 6.14, w: 2.5, h: 0.22, fontSize: 9.5, color: MUT });
  });
  mono(s, "2026-09-13  ·  InnbumBaek/Stock_Agent  ·  최종 결정은 사람이 한다", {
    x: M, y: 6.72, w: 11.5, h: 0.26, fontSize: 9.5, color: DIM,
  });
}

function sProblem() {
  const s = slide();
  header(s, "PART 2 · PROBLEM", "12편은 목록이 아니라 스냅샷이다",
         ".papers.json 의 verified 는 2026-09-05 다. 그날 이후로 이 데스크의 방법론은 멈춰 있다.");

  panel(s, { x: M, y: 1.86, w: 6.0, h: 4.56, fill: PANEL, line: EDGE });
  mono(s, "adopted = 12   ·   frozen @ 2026-09-05", {
    x: M + 0.24, y: 2.04, w: 5.5, h: 0.26, fontSize: 11, bold: true, color: MAG,
  });
  const papers = ["roll1984", "j1990", "ritter1991", "jt1993", "dnr1998", "ac2000",
                  "fh2001", "amihud2002", "gh2004", "athl2005", "ahxz2006", "cs2012"];
  papers.forEach((p, i) => {
    const x = M + 0.26 + (i % 4) * 1.42, y = 2.52 + Math.floor(i / 4) * 1.02;
    s.addImage({ data: img("ob_paper"), x, y, w: 0.34, h: 0.34, transparency: 45 });
    mono(s, p, { x: x + 0.40, y: y + 0.05, w: 1.0, h: 0.24, fontSize: 8.5, color: DIM });
    mono(s, String(parseInt(p.replace(/\D/g, "").slice(-4))), {
      x: x + 0.40, y: y + 0.26, w: 1.0, h: 0.2, fontSize: 8, color: "3F4A63" });
  });
  mono(s, "최신 채택본이 2012년이다 — 14년치 계량금융이 비어 있다", {
    x: M + 0.26, y: 5.36, w: 5.5, h: 0.3, fontSize: 10.5, bold: true, color: AMB,
  });
  txt(s, "그 사이 시장미시구조·집행비용 연구가 가장 많이 쌓인 구간이다. 훑지 않아서 없는 것이지, 없어서 없는 것이 아니다.", {
    x: M + 0.26, y: 5.68, w: 5.5, h: 0.5, fontSize: 10, color: MUT });

  const probs = [
    ["손으로 고른 목록은 고른 날짜에서 멈춘다", "누가 언제 다시 훑을지가 정해져 있지 않으면, 갱신은 사실상 일어나지 않는다.", MAG],
    ["인용은 검증이 아니다", "논문이 미국 대형주에서 보인 효과가 코스닥 소형주에서 성립하는지는 아무도 확인하지 않았다.", ORG],
    ["틀린 채로 계속 쓰인다", "채택본에 은퇴 개념이 없다. 뒤집힌 결과도 목록에 남아 계속 인용된다.", AMB],
  ];
  probs.forEach((p, i) => {
    const y = 1.86 + i * 1.13;
    panel(s, { x: 6.86, y, w: 5.87, h: 1.02, fill: PANEL, line: EDGE });
    s.addImage({ data: img("ic_no"), x: 7.06, y: y + 0.15, w: 0.22, h: 0.22 });
    txt(s, p[0], { x: 7.40, y: y + 0.12, w: 5.15, h: 0.28, fontSize: 12.5, bold: true, color: p[2] });
    txt(s, p[1], { x: 7.40, y: y + 0.42, w: 5.15, h: 0.5, fontSize: 10, color: MUT });
  });
  panel(s, { x: 6.86, y: 5.28, w: 5.87, h: 1.14, fill: "16281C", line: "2A5A3A" });
  s.addImage({ data: img("ic_spark"), x: 7.06, y: 5.46, w: 0.24, h: 0.24 });
  txt(s, "그래서 편수를 세지 않는다", { x: 7.40, y: 5.42, w: 5.15, h: 0.3, fontSize: 13, bold: true, color: GRN });
  txt(s, "\"몇 편 있는가\"가 아니라 \"몇 편이 아직 살아있는가\"를 센다. 채택은 상태이지 영구 자격이 아니다.", {
    x: 7.40, y: 5.74, w: 5.15, h: 0.56, fontSize: 10.5, color: INK });
  foot(s, "// 근거: stock-monitor/.papers.json — schema ki.papers/1 · verified 2026-09-05 · adopted 12");
}

function sPipeline() {
  const s = slide();
  header(s, "PART 2 · PAPER PIPELINE", "주 1회 — 새 논문을 들여와 통과 테스트를 돌린다",
         "일회성 배치가 아니라 매주 도는 사이클이다. 수확은 이미 있고(fetch_papers.py), 새로 넣는 것은 세 번째 — 재현 관문이다.");

  const stages = [
    ["01", "수확", "HARVEST", "arXiv q-fin 8분류\nSemantic Scholar\nOpenAlex · Crossref", "주 ~400건", CYN],
    ["02", "심사", "SCREEN", "초록으로 네 질문 중\n하나를 바꾸는가 판정\n프리프린트 등급 표시", "주 ~40건", BLU],
    ["03", "재현", "REPLICATE", "우리 원장 일봉에서\n그 팩터를 실제로 계산\n방향·유의성 대조", "주 ~6건", GRN],
    ["04", "채택", "ADOPT", "Crossref 발행정보 재대조\nlimits 작성 필수\n통과분만 채택", "주 ~2건", AMB],
    ["05", "감가", "DECAY", "반감기마다 재현 재검\n누적 실패 시 은퇴\n인용 절에 경고", "상시", MAG],
  ];
  const sw = 2.36, sg = 0.13;
  stages.forEach((st, i) => {
    const x = M + i * (sw + sg);
    panel(s, { x, y: 1.86, w: sw, h: 0.52, fill: st[5], line: null });
    mono(s, st[0] + "  " + st[2], { x: x + 0.12, y: 1.86, w: sw - 0.24, h: 0.52, fontSize: 10.5, bold: true, color: "0D1018", valign: "middle" });
    panel(s, { x, y: 2.46, w: sw, h: 2.72, fill: PANEL, line: EDGE });
    txt(s, st[1], { x: x + 0.16, y: 2.62, w: sw - 0.32, h: 0.36, fontSize: 19, bold: true, color: st[5] });
    txt(s, st[3], { x: x + 0.16, y: 3.06, w: sw - 0.32, h: 1.1, fontSize: 10.5, color: INK, lineSpacing: 16 });
    panel(s, { x: x + 0.16, y: 4.42, w: sw - 0.32, h: 0.36, fill: PANEL2, line: null, off: 0 });
    mono(s, st[4], { x: x + 0.16, y: 4.42, w: sw - 0.32, h: 0.36, fontSize: 10, bold: true, color: MUT, align: "center", valign: "middle" });
    if (i < 4) s.addImage({ data: img("ar_am"), x: x + sw - 0.06, y: 3.52, w: 0.3, h: 0.19 });
  });

  // 깔때기
  panel(s, { x: M, y: 5.38, w: CW, h: 1.02, fill: PANEL3, line: EDGE });
  txt(s, "매주 같은 깔때기를 돌린다", { x: M + 0.24, y: 5.5, w: 4.0, h: 0.28, fontSize: 12.5, bold: true, color: GLD });
  txt(s, "주 400건을 훑어 2건이 남는다. 같은 사이클에 반감기가 도래한 기존 채택본도 함께 태워 재검한다(주 최대 3편). 12편을 한꺼번에 검사하는 단계는 없다.", {
    x: M + 0.24, y: 5.80, w: 7.4, h: 0.46, fontSize: 10.5, color: MUT });
  const fr = [["400", CYN], ["40", BLU], ["6", GRN], ["2", AMB]];
  fr.forEach((f, i) => {
    const x = 8.5 + i * 1.08;
    mono(s, f[0], { x, y: 5.52, w: 0.9, h: 0.42, fontSize: 22, bold: true, color: f[1], align: "center" });
    if (i < 3) mono(s, "▸", { x: x + 0.72, y: 5.58, w: 0.34, h: 0.3, fontSize: 13, color: DIM, align: "center" });
    mono(s, ["수확", "심사", "재현", "채택"][i], { x, y: 5.98, w: 0.9, h: 0.24, fontSize: 9, color: DIM, align: "center" });
  });
  foot(s, "// 주 1회 · 월요일 07:30 배치 · 수확 4곳은 이미 구현돼 있다 (docs/fetch_papers.py) · 03 재현과 05 감가가 신설분");
}

function sReplication() {
  const s = slide();
  header(s, "PART 2 · ★ REPLICATION GATE", "재현 관문 — 인용하기 전에 우리 데이터로 계산해 본다",
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
  panel(s, { x: 7.64, y: 4.90, w: 4.9, h: 1.24, fill: "132318", line: GRN });
  mono(s, "통과 임계  |t| \u2265 3.0", { x: 7.80, y: 4.97, w: 3.0, h: 0.24, fontSize: 11, bold: true, color: GRN, valign: "top" });
  txt(s, "2.0 은 검정을 한 번 할 때의 값이다. 주 1회 사이클이면 연 150회쯤 되고, 그때 2.0 은 효과 없는 팩터를 해마다 7~8개 통과시킨다 — '논문 근거 있음' 딱지를 달고서.", {
    x: 7.80, y: 5.22, w: 4.58, h: 0.46, fontSize: 8.6, color: INK, lineSpacing: 10.4, valign: "top" });
  txt(s, "표준오차는 Newey-West 로 잰다. 월간 스프레드는 자기상관이 있어 보통 표준오차를 쓰면 t 가 과장된다.", {
    x: 7.80, y: 5.66, w: 4.58, h: 0.32, fontSize: 8.6, color: MUT, lineSpacing: 10.4, valign: "top" });
  mono(s, "Harvey\u00b7Liu\u00b7Zhu (2016) RFS 29(1) 5-68   \u00b7   Newey\u00b7West (1987) ECTA 55(3)", {
    x: 7.80, y: 5.94, w: 4.58, h: 0.18, fontSize: 7.2, color: DIM, valign: "top" });

  panel(s, { x: M, y: 6.18, w: CW, h: 0.66, fill: "2A1520", line: "5C2A3A" });
  txt(s, [
    { text: "재현 실패는 실패가 아니다.  ", options: { bold: true, color: MAG } },
    { text: "\"이 논문은 코스닥에서 성립하지 않는다\"는 것도 측정 결과다. 지우지 않고 남겨 두면, 다음 사람이 같은 논문을 다시 주워 오는 일을 막는다. 통과하지 못한 논문은 '미검증'으로 남아 표시를 달고 인용된다 — 관문은 정지 버튼이 아니다.", options: { color: INK } },
  ], { x: M + 0.26, y: 6.18, w: CW - 0.52, h: 0.66, fontSize: 11.5, valign: "middle", fontFace: F, isTextBox: true, margin: 0 });
}

function sDecay() {
  const s = slide();
  header(s, "PART 2 · DECAY & RETIRE", "채택은 상태이지 영구 자격이 아니다",
         "채택본에도 반감기를 둔다. 반감기가 지나면 재현을 다시 돌리고, 결과에 따라 유지·경고·은퇴로 나뉜다.");

  const rules = [
    ["반감기 180일", "채택 후 180영업일이 지나면 재검 대상이 된다. 주간 사이클에 신규 후보와 함께 태운다 — 주 최대 3편, recheck_due 오래된 순.", CYN],
    ["1회 실패 → 경고", "재현이 깨지면 은퇴시키지 않고 '경고'로 표시한다. 그 팩터를 쓰는 리포트 절 하단에 그대로 찍힌다.", AMB],
    ["연속 2회 실패 → 은퇴", "다음 반감기에도 깨지면 은퇴한다. 인용이 끊기고, 그 팩터를 쓰던 계산은 '방법론 없음'으로 빠진다.", MAG],
    ["이관분은 4주에 나눠 소화", "기존 12편은 원 채택일 기준이라 전부 도래 상태다. 주 3편 상한이 자연히 분산시킨다 — 몰아서 돌리지 않는다.", DIM],
  ];
  rules.forEach((r, i) => {
    const y = 1.84 + i * 0.94;
    panel(s, { x: M, y, w: 5.5, h: 0.84, fill: PANEL, line: EDGE });
    s.addShape(pres.ShapeType.rect, { x: M + 0.16, y: y + 0.18, w: 0.16, h: 0.48, fill: { color: r[2] }, line: { type: "none" } });
    txt(s, r[0], { x: M + 0.48, y: y + 0.12, w: 4.8, h: 0.28, fontSize: 13, bold: true, color: r[2] });
    txt(s, r[1], { x: M + 0.48, y: y + 0.42, w: 4.85, h: 0.38, fontSize: 10, color: MUT });
  });

  panel(s, { x: 6.4, y: 1.84, w: 6.33, h: 3.76, fill: PANEL, line: EDGE });
  txt(s, "살아있는 채택본 — 12개월 시뮬레이션", { x: 6.64, y: 1.98, w: 5.8, h: 0.28, fontSize: 13, bold: true, color: INK });
  txt(s, "주 2편 채택 · 반감기 180일 · 재현 실패율 18% 가정", { x: 6.64, y: 2.26, w: 5.8, h: 0.22, fontSize: 9.5, color: DIM });
  const months = ["1월","2월","3월","4월","5월","6월","7월","8월","9월","10월","11월","12월"];
  s.addChart(pres.ChartType.bar, [
    { name: "유지", labels: months, values: [12,18,25,32,38,43,47,50,54,57,60,63] },
    { name: "신규 채택", labels: months, values: [8,8,8,8,8,8,8,8,8,8,8,8] },
    { name: "은퇴", labels: months, values: [0,0,1,1,2,3,4,4,5,5,5,6] },
  ], {
    x: 6.62, y: 2.56, w: 5.9, h: 2.9,
    barGrouping: "stacked", chartColors: [C1, C2, C4],
    showLegend: true, legendPos: "b", legendColor: MUT, legendFontSize: 9, legendFontFace: F,
    showValue: false,
    catAxisLabelColor: MUT, catAxisLabelFontSize: 8.5, catAxisLabelFontFace: F, catAxisLineShow: false,
    valAxisLabelColor: MUT, valAxisLabelFontSize: 8.5, valAxisLabelFontFace: F, valAxisLineShow: false,
    valGridLine: { color: "2A3350", size: 1 }, catGridLine: { style: "none" },
    valAxisMaxVal: 80, plotArea: { fill: { color: PANEL } }, chartArea: { fill: { color: PANEL } },
    dataBorder: { pt: 1.5, color: PANEL },
  });
  panel(s, { x: 6.4, y: 5.76, w: 6.33, h: 1.06, fill: PANEL3, line: EDGE });
  txt(s, "주 2편씩 들어오고 반감기마다 재검된다. 1년 뒤 63편은 결과일 뿐 목표가 아니다 — 편수가 아니라 통과 여부가 자격이다.", {
    x: 6.64, y: 5.76, w: 5.85, h: 1.06, fontSize: 10.5, color: INK, valign: "middle" });
  foot(s, "// 시뮬레이션 가정값이며 실측이 아니다. 실제 채택률은 Phase 2 병행 운영에서 측정한다.");
}

function sLedger() {
  const s = slide();
  header(s, "PART 2 · PAPER LEDGER", "논문 원장 — 채택도 은퇴도 이력으로 남는다",
         ".papers.json 을 목록에서 append-only 원장으로 바꾼다. 상태가 바뀐 이유가 항상 남아 있어야 한다.");

  panel(s, { x: M, y: 1.86, w: 7.0, h: 4.32, fill: "0A1020", line: EDGE });
  mono(s, [
    '{',
    '  "schema": "ki.papers/2",',
    '  "papers": {',
    '    "amihud2002": {',
    '      "title":   "Illiquidity and stock returns",',
    '      "doi":     "10.1016/S1386-4181(01)00024-6",',
    '      "grade":   "저널 게재",',
    '      "question": "q2",',
    '',
    '      "state":   "adopted",   // unverified|adopted|warned|retired',
    '      "state_at":    "2026-02-11",',
    '      "half_life_d": 180,',
    '      "recheck_due": "2026-11-05",',
    '',
    '      "replication": [             // append-only',
    '        { "at": "2026-02-11", "verdict": "재현됨",',
    '          "universe": "KOSDAQ", "n": 1418,',
    '          "window":   "2023-01-02..2026-02-07",',
    '          "claim":    "비유동성 상위분위 초과수익 > 0",',
    '          "observed": { "spread_mean_bp": 41, "t": 3.42 } }',
    '      ],',
    '',
    '      "limits": [',
    '        "표본은 미국 상장주 — 코스닥 외삽 근거 아님",',
    '        "거래정지 구간 제외 · 생존편의 보정 안 함"',
    '      ]',
    '    }',
    '  }',
    '}',
  ].join("\n"), { x: M + 0.24, y: 2.0, w: 6.55, h: 4.06, fontSize: 8.0, color: "A9C8F0", lineSpacing: 10.4, valign: "top" });

  const notes = [
    ["state 가 자격이다", "adopted 는 재현 통과. unverified 는 아직 재검 순번이 안 온 것 — 인용은 되지만 '미검증' 이 붙는다. warned 는 경고, retired 는 인용 차단.", GRN],
    ["replication 은 배열이다", "덮어쓰지 않고 쌓는다. 언제 재현했고 그때 무엇을 봤는지가 전부 남아, 판정이 바뀐 이유를 되짚을 수 있다.", CYN],
    ["observed 는 측정값이다", "논문이 뭐라 했는지가 아니라 우리 원장에서 무엇이 나왔는지다. 이 값이 없으면 채택되지 않는다.", AMB],
    ["limits 는 여전히 필수다", "논문이 주장하지 않는 것을 함께 낸다. 비어 있으면 게이트가 막는다 — 기존 규칙 그대로.", PUR],
  ];
  notes.forEach((n, i) => {
    const y = 1.86 + i * 1.1;
    panel(s, { x: 7.86, y, w: 4.87, h: 0.98, fill: PANEL, line: EDGE });
    s.addShape(pres.ShapeType.rect, { x: 8.06, y: y + 0.19, w: 0.14, h: 0.14, fill: { color: n[2] }, line: { type: "none" } });
    txt(s, n[0], { x: 8.32, y: y + 0.11, w: 4.3, h: 0.28, fontSize: 12, bold: true, color: n[2] });
    txt(s, n[1], { x: 8.06, y: y + 0.40, w: 4.56, h: 0.5, fontSize: 9.5, color: MUT });
  });
  foot(s, "// selftest 확장: 모든 팩터가 state=adopted 인 논문을 인용하는가 · replication 이 비어 있는 채택본이 없는가");
}

function sStandingSpawn() {
  const s = slide();
  header(s, "PART 3 · DYNAMIC AGENTS", "상설은 셋뿐이다. 나머지 여섯은 불릴 때만 온다.",
         "조직도를 고정하지 않는다. 아홉 데스크를 매일 전부 돌리는 대신, 그 질문의 답이 달라졌을 때만 띄운다.");

  panel(s, { x: M, y: 1.82, w: 4.4, h: 4.3, fill: PANEL, line: GRN });
  mono(s, "STANDING  ·  상설 3", { x: M + 0.24, y: 1.98, w: 3.9, h: 0.26, fontSize: 11, bold: true, color: GRN });
  txt(s, "항상 떠 있다. 하루의 리듬을 만든다.", { x: M + 0.24, y: 2.26, w: 3.9, h: 0.24, fontSize: 10, color: MUT });
  const standing = [
    ["ag_dataops", "data-ops", "원장 적재 · 품질 — 그날의 유일한 쓰기", "쓰기 단독", GRN],
    ["ag_compliance", "compliance-officer", "일곱 게이트 판정 · 발행 승인", "거부권", ORG],
    ["ag_chair", "ic-chair", "봉투 수집 · 쟁점 정렬 · 조립", "조립만", GLD],
  ];
  standing.forEach((a, i) => {
    const y = 2.70 + i * 0.86;
    panel(s, { x: M + 0.22, y, w: 3.96, h: 0.74, fill: PANEL2, line: EDGE, off: 0 });
    s.addImage({ data: img(a[0]), x: M + 0.32, y: y + 0.09, w: 0.44, h: 0.44 });
    mono(s, a[1], { x: M + 0.84, y: y + 0.06, w: 2.3, h: 0.22, fontSize: 9, bold: true, color: INK });
    txt(s, a[2], { x: M + 0.84, y: y + 0.28, w: 2.4, h: 0.26, fontSize: 8.5, color: MUT });
    mono(s, a[3], { x: M + 3.22, y, w: 0.88, h: 0.62, fontSize: 7.5, bold: true, color: a[4], align: "right", valign: "middle" });
  });

  panel(s, { x: 5.32, y: 1.82, w: 7.41, h: 4.3, fill: PANEL, line: AMB });
  mono(s, "SPAWNED  ·  이벤트 소집 6 역할 × N 인스턴스", { x: 5.56, y: 1.98, w: 6.9, h: 0.26, fontSize: 11, bold: true, color: AMB });
  txt(s, "트리거가 뜰 때만 인스턴스가 생기고, 봉투를 내면 사라진다. 상태를 들고 있지 않으므로 같은 입력이면 같은 결과가 나온다.", {
    x: 5.56, y: 2.26, w: 6.9, h: 0.24, fontSize: 10, color: MUT });
  const spawned = [
    ["q1-progress", "진척 변동", CYN], ["q2-disposal", "처분여건 변동", GRN],
    ["q3-execution", "q2 봉투 갱신", AMB], ["q4-timing", "공시 · 일정", MAG],
    ["quant-method", "주간 재현", PUR], ["risk-officer", "봉투 묶음", MAG],
  ];
  spawned.forEach((a, i) => {
    const x = 5.56 + (i % 3) * 2.36, y = 2.60 + Math.floor(i / 3) * 0.7;
    panel(s, { x, y, w: 2.22, h: 0.62, fill: PANEL2, line: EDGE, off: 0 });
    s.addShape(pres.ShapeType.rect, { x: x + 0.1, y: y + 0.14, w: 0.1, h: 0.34, fill: { color: a[2] }, line: { type: "none" } });
    mono(s, a[0], { x: x + 0.28, y: y + 0.06, w: 1.52, h: 0.22, fontSize: 7.4, bold: true, color: INK });
    txt(s, a[1], { x: x + 0.28, y: y + 0.28, w: 1.52, h: 0.24, fontSize: 8, color: MUT });
    mono(s, "×N", { x: x + 1.8, y, w: 0.36, h: 0.62, fontSize: 9, bold: true, color: a[2], align: "right", valign: "middle" });
  });

  panel(s, { x: M, y: 6.28, w: CW, h: 0.6, fill: PANEL3, line: EDGE });
  txt(s, [
    { text: "왜 소집인가 —  ", options: { bold: true, color: AMB } },
    { text: "85종목 × 종목단위 3데스크를 매일 돌리면 255회다. 어제와 달라진 것이 없는 종목을 다시 읽는 것은 같은 답을 다시 사는 일이다. 질문의 답이 달라진 곳에만 예산을 쓴다.", options: { color: INK } },
  ], { x: M + 0.26, y: 6.28, w: CW - 0.52, h: 0.6, fontSize: 11, valign: "middle", fontFace: F, isTextBox: true, margin: 0 });
}

function sLifecycle() {
  const s = slide();
  header(s, "PART 3 · LIFECYCLE", "소집 → 작업 → 봉투 → 소멸",
         "에이전트는 세션을 갖지 않는다. 기억을 들고 있지 않으므로, 어제의 오해가 오늘로 넘어오지 않는다.");

  const life = [
    ["SPAWN", "소집", "트리거가 입력을 확정해서 넘긴다.\n종목코드 · 공시 접수번호 · 기준일.\n그 밖의 것은 볼 수 없다.", CYN, 1.0],
    ["WORK", "작업", "허용된 MCP 읽기 도구만 부른다.\n예산(토큰·호출수)이 정해져 있고,\n넘으면 그대로 중단된다.", BLU, 0.75],
    ["ENVELOPE", "봉투", "측정값 + 등급 + 가정 + 한계.\n스키마를 못 맞추면 산출이 아니라\n실패로 기록된다.", GRN, 0.5],
    ["DISSOLVE", "소멸", "인스턴스가 사라진다.\n남는 것은 봉투와 실행 로그뿐 —\n둘 다 재생 가능하다.", DIM, 0.15],
  ];
  life.forEach((l, i) => {
    const x = M + i * 3.12;
    panel(s, { x, y: 1.88, w: 2.86, h: 3.5, fill: PANEL, line: EDGE });
    s.addImage({ data: img("ag_equity"), x: x + 1.03, y: 2.08, w: 0.8, h: 0.8, transparency: Math.round((1 - l[4]) * 100) });
    mono(s, l[0], { x: x + 0.16, y: 3.02, w: 2.54, h: 0.26, fontSize: 10.5, bold: true, color: l[3], align: "center", charSpacing: 1 });
    txt(s, l[1], { x: x + 0.16, y: 3.30, w: 2.54, h: 0.36, fontSize: 18, bold: true, color: INK, align: "center" });
    txt(s, l[2], { x: x + 0.18, y: 3.80, w: 2.5, h: 1.1, fontSize: 10, color: MUT, align: "center", lineSpacing: 15 });
    pxBar(s, x + 0.3, 5.02, 2.26, 0.12, l[4], l[3]);
    if (i < 3) s.addImage({ data: img("ar_cy"), x: x + 2.9, y: 2.34, w: 0.3, h: 0.19 });
  });

  const props = [
    ["무상태 (stateless)", "같은 입력 → 같은 봉투. 어제 무엇을 봤는지 기억하지 않는다.", GRN],
    ["예산 제한", "인스턴스마다 호출·토큰 상한. 초과하면 '미완'으로 끝나지 조용히 넘어가지 않는다.", AMB],
    ["격리", "다른 인스턴스의 산출을 보지 않는다. 수렴하면 교차검증의 의미가 사라진다.", CYN],
    ["재생 가능", "실행 로그로 같은 인스턴스를 다시 띄워 결과를 대조할 수 있다.", PUR],
  ];
  props.forEach((p, i) => {
    const x = M + i * 3.12;
    panel(s, { x, y: 5.56, w: 2.86, h: 1.28, fill: PANEL3, line: EDGE });
    txt(s, p[0], { x: x + 0.18, y: 5.7, w: 2.5, h: 0.26, fontSize: 11.5, bold: true, color: p[2] });
    txt(s, p[1], { x: x + 0.18, y: 5.98, w: 2.52, h: 0.74, fontSize: 9.5, color: MUT });
  });
}

function sTriggers() {
  const s = slide();
  header(s, "PART 3 · TRIGGERS", "무엇이 누구를 부르는가",
         "트리거는 원장의 변화에서 나온다. 사람이 부르는 것이 아니라 데이터가 부른다.");

  const rows = [
    ["DART 신규 공시 · 희석/지분", "q2-disposal", "접수번호 1건", "공시당 1", "자본구조·희석 재계산 (T1)"],
    ["DART 신규 공시 · 실적", "q1-progress", "접수번호 1건", "공시당 1", "회수계획 대비 진척 갱신 (T1)"],
    ["DART 신규 공시 · 그 밖", "q4-timing", "접수번호 1건", "공시당 1", "이벤트로 시점 판단에 반영 (T1)"],
    ["종가 ±8% 이상 변동", "q2-disposal · risk-officer", "종목코드 · 기준일", "종목당 1", "처분여건 재계산 · 숫자 재검산"],
    ["락업 만료 D-30 진입", "q3-execution · q4-timing", "종목코드 · 해제일", "종목당 1", "물량 압력 · 시점 (등급 '추정')"],
    ["ECOS·캘린더 갱신", "q4-timing", "지표 키 목록", "일 1", "국면 서술"],
    ["재현 재검 기한 도래", "quant-method", "논문 키", "주 3편", "재현 판정 → 장부 append (T3)"],
    ["봉투 묶음 완성 · 게이트", "risk-officer · compliance-officer", "그날 봉투 전량", "일 1", "재검산 → 게이트 ①~⑦ → 발행"],
  ];
  const head = ["트리거 (원장의 변화)", "소집되는 데스크", "넘겨받는 입력", "상한", "산출"].map((h, i) => ({
    text: h, options: { bold: true, color: AMB, fill: { color: PANEL2 }, fontSize: 10.5, valign: "middle", fontFace: FM },
  }));
  const body = [head];
  rows.forEach((r, i) => body.push([
    { text: r[0], options: { color: INK, fontSize: 10, bold: true, valign: "middle", fill: { color: i % 2 ? PANEL3 : PANEL } } },
    { text: r[1], options: { color: CYN, fontSize: 9.5, valign: "middle", fontFace: FM, fill: { color: i % 2 ? PANEL3 : PANEL } } },
    { text: r[2], options: { color: MUT, fontSize: 9.5, valign: "middle", fill: { color: i % 2 ? PANEL3 : PANEL } } },
    { text: r[3], options: { color: GRN, fontSize: 9.5, bold: true, align: "center", valign: "middle", fill: { color: i % 2 ? PANEL3 : PANEL } } },
    { text: r[4], options: { color: MUT, fontSize: 9.5, valign: "middle", fill: { color: i % 2 ? PANEL3 : PANEL } } },
  ]));
  s.addTable(body, {
    x: M, y: 1.84, w: CW, colW: [2.66, 2.72, 1.94, 1.05, 3.76],
    border: { type: "solid", color: EDGE, pt: 1 },
    fontFace: F, rowH: 0.45, margin: 0.08, autoPage: false,
  });

  panel(s, { x: M, y: 6.14, w: CW, h: 0.62, fill: PANEL3, line: EDGE });
  txt(s, [
    { text: "트리거가 없으면 아무도 소집되지 않는다. ", options: { bold: true, color: GRN } },
    { text: "조용한 날은 조용한 것이 정상이다 — 할 말이 없는데 데스크를 돌려 말을 만들게 하는 것이 이 구조가 막으려는 실패다. 상설 셋(data-ops · compliance-officer · ic-chair)은 그래도 매일 돈다.", options: { color: INK } },
  ], { x: M + 0.26, y: 6.14, w: CW - 0.52, h: 0.62, fontSize: 11, valign: "middle", fontFace: F, isTextBox: true, margin: 0 });
}

function sLoad() {
  const s = slide();
  header(s, "PART 3 · LOAD", "전수 실행 대비 실제 부하",
         "20영업일 시뮬레이션. 전수 방식은 종목수에 고정으로 묶이고, 이벤트 방식은 그날 일어난 일의 수만큼만 돈다.");

  panel(s, { x: M, y: 1.84, w: 8.3, h: 4.3, fill: PANEL, line: EDGE });
  txt(s, "일별 에이전트 인스턴스 수", { x: M + 0.26, y: 1.98, w: 5.0, h: 0.3, fontSize: 14, bold: true, color: INK });
  txt(s, "가정 — 감시 85종목 · 종목단위 데스크 3 (q1·q2·q3) · 공시 발생률 6% · ±8% 변동 발생률 4%", {
    x: M + 0.26, y: 2.28, w: 7.6, h: 0.22, fontSize: 9.5, color: DIM });
  const days = Array.from({ length: 20 }, (_, i) => "D" + (i + 1));
  s.addChart(pres.ChartType.line, [
    { name: "전수 실행 (85×3)", labels: days, values: Array(20).fill(255) },
    { name: "이벤트 소집", labels: days, values: [28,38,32,44,26,36,64,30,42,34,52,29,40,47,31,37,34,70,42,32] },
  ], {
    x: M + 0.2, y: 2.6, w: 7.9, h: 3.3,
    chartColors: [C4, C1], lineDataSymbol: "none", lineSize: 3,
    showLegend: true, legendPos: "b", legendColor: MUT, legendFontSize: 10, legendFontFace: F,
    catAxisLabelColor: DIM, catAxisLabelFontSize: 8, catAxisLabelFontFace: FM, catAxisLineShow: false,
    valAxisLabelColor: MUT, valAxisLabelFontSize: 9, valAxisLabelFontFace: FM, valAxisLineShow: false,
    valGridLine: { color: "2A3350", size: 1 }, catGridLine: { style: "none" },
    valAxisMinVal: 0, valAxisMaxVal: 300,
    plotArea: { fill: { color: PANEL } }, chartArea: { fill: { color: PANEL } },
  });

  const st = [["5,100", "전수 · 20일 누계", "인스턴스", C4], ["788", "이벤트 · 20일 누계", "인스턴스", C1],
              ["-85%", "부하 감소", "같은 커버리지", GRN], ["70", "최대 피크일", "D18 · 공시 집중", AMB]];
  st.forEach((t, i) => {
    const y = 1.84 + i * 1.11;
    panel(s, { x: 9.12, y, w: 3.61, h: 0.99, fill: PANEL, line: EDGE });
    mono(s, t[0], { x: 9.34, y: y + 0.12, w: 3.2, h: 0.4, fontSize: 24, bold: true, color: t[3] });
    txt(s, t[1], { x: 9.34, y: y + 0.54, w: 3.2, h: 0.22, fontSize: 10.5, bold: true, color: INK });
    txt(s, t[2], { x: 9.34, y: y + 0.74, w: 3.2, h: 0.2, fontSize: 9, color: MUT });
  });

  panel(s, { x: M, y: 6.3, w: CW, h: 0.58, fill: PANEL3, line: EDGE });
  txt(s, [
    { text: "핵심은 절감이 아니라 피크다. ", options: { bold: true, color: AMB } },
    { text: "전수 방식은 조용한 날에도 255를 쓰느라, 정작 공시가 몰린 날(D18)에 더 깊이 볼 여력이 없다. 이벤트 방식은 그날 예산을 그날 일에 쓴다.", options: { color: INK } },
  ], { x: M + 0.26, y: 6.3, w: CW - 0.52, h: 0.58, fontSize: 11, valign: "middle", fontFace: F, isTextBox: true, margin: 0 });
  foot(s, "// 발생률은 여전히 가정값이다. 역산기는 들어갔고(run_day.py --stage convene) 실측에는 원장이 필요하다 — 이 수치는 아직 실측이 아니다.");
}

function sEscalation() {
  const s = slide();
  header(s, "PART 3 · ESCALATION", "쉬운 일에 비싼 모델을 쓰지 않는다",
         "모든 인스턴스가 같은 급일 필요는 없다. 아래에서 시작해, 걸리는 것만 위로 올린다.");

  const tiers = [
    ["T1", "경량", "정형 추출 · 분류", "공시 제목에서 종류 판별, 값 파싱, 스키마 채우기처럼 답이 하나로 정해지는 일.", "전체의 ~70%", CYN, 0.28],
    ["T2", "표준", "해석 · 서술", "측정값을 읽고 §5·§6 초안을 쓰는 일. 대부분의 데스크 산출이 여기서 나온다.", "전체의 ~25%", GRN, 0.62],
    ["T3", "상위", "이견 · 이상치 · 재현 설계", "데스크 간 판정이 갈리거나, 재현 관문 설계처럼 틀리면 비싼 일.", "전체의 ~5%", AMB, 1.0],
  ];
  tiers.forEach((t, i) => {
    const y = 1.86 + i * 1.42;
    panel(s, { x: M, y, w: 8.2, h: 1.3, fill: PANEL, line: EDGE });
    s.addShape(pres.ShapeType.rect, { x: M + 0.18, y: y + 0.2, w: 0.9, h: 0.9, fill: { color: t[5] }, line: { type: "none" } });
    mono(s, t[0], { x: M + 0.18, y: y + 0.2, w: 0.9, h: 0.9, fontSize: 22, bold: true, color: "0D1018", align: "center", valign: "middle" });
    txt(s, t[1] + "  ·  " + t[2], { x: M + 1.26, y: y + 0.18, w: 5.0, h: 0.3, fontSize: 14, bold: true, color: t[5] });
    txt(s, t[3], { x: M + 1.26, y: y + 0.52, w: 6.7, h: 0.44, fontSize: 10.5, color: MUT });
    pxBar(s, M + 1.26, y + 1.0, 5.2, 0.14, t[6], t[5]);
    mono(s, t[4], { x: M + 6.6, y: y + 0.94, w: 1.4, h: 0.24, fontSize: 9.5, bold: true, color: MUT, align: "right" });
  });

  panel(s, { x: 9.02, y: 1.86, w: 3.71, h: 2.72, fill: PANEL, line: AMB });
  mono(s, "승격 조건  ·  ● 집행 중", { x: 9.24, y: 2.0, w: 3.3, h: 0.26, fontSize: 11, bold: true, color: AMB });
  [["두 데스크의 판정이 갈릴 때", 1],
   ["게이트에 두 번 연속 반려될 때", 1],
   ["예산 초과로 미완일 때", 1],
   ["리스크 검산 불일치 — 위 '갈림'이 덮는다", 0],
   ["재현이 '판정 불가' — 사이클이 따로 돈다", 0]].forEach((t, i) => {
    const y = 2.34 + i * 0.42;
    s.addShape(pres.ShapeType.rect, { x: 9.24, y: y + 0.09, w: 0.14, h: 0.14,
      fill: { color: t[1] ? GRN : PANEL2 }, line: t[1] ? { type: "none" } : { color: DIM, pt: 1 } });
    txt(s, t[0], { x: 9.56, y, w: 3.0, h: 0.3, fontSize: 9.5, color: t[1] ? INK : DIM });
  });

  panel(s, { x: 9.02, y: 4.76, w: 3.71, h: 2.08, fill: PANEL3, line: EDGE });
  mono(s, "승격은 기록된다", { x: 9.24, y: 4.9, w: 3.3, h: 0.26, fontSize: 11, bold: true, color: GRN });
  txt(s, "첫 반려는 같은 급에서 다시 한다 — 금지어 하나에 T3 을 띄우지 않는다. 두 번 연속이면 그때 올라가고, 어느 인스턴스가 왜 올라갔는지가 봉투에 남는다. 승격이 잦은 지점이 이 시스템이 약한 곳이다.", {
    x: 9.24, y: 5.2, w: 3.3, h: 1.0, fontSize: 10, color: MUT });
  mono(s, "escalated_from: \"T2\"\nescalated_because: \"desks_disagree\"", {
    x: 9.24, y: 6.2, w: 3.3, h: 0.5, fontSize: 8.5, color: CYN, lineSpacing: 12 });
}

function sWall() {
  const s = slide();
  header(s, "PART 4 · THE WALL", "동적으로 바뀌어도 벽은 그대로다",
         "에이전트가 매번 새로 생기더라도, 원장에 쓸 수 있는 도구를 받는 인스턴스는 없다.");

  panel(s, { x: M, y: 1.9, w: 4.5, h: 3.5, fill: PANEL, line: GRN });
  mono(s, "MEASUREMENT  ·  측정층", { x: M + 0.24, y: 2.06, w: 4.0, h: 0.26, fontSize: 10.5, bold: true, color: GRN });
  s.addImage({ data: img("ob_db"), x: M + 0.24, y: 2.44, w: 0.86, h: 0.86 });
  txt(s, "ki.sqlite", { x: M + 1.24, y: 2.5, w: 3.0, h: 0.4, fontSize: 22, bold: true, color: INK });
  mono(s, "7 tables · 사실만", { x: M + 1.24, y: 2.94, w: 3.0, h: 0.24, fontSize: 9.5, color: MUT });
  ["공식 API 5종의 값만 들어간다", "쓰기 주체는 data-ops 단독", "KIS 장중 스냅샷은 persist=False", "오염되면 되돌릴 수 없다"].forEach((t, i) => {
    mono(s, "▸ ", { x: M + 0.26, y: 3.5 + i * 0.42, w: 0.24, h: 0.26, fontSize: 10, color: GRN });
    txt(s, t, { x: M + 0.52, y: 3.48 + i * 0.42, w: 3.8, h: 0.3, fontSize: 11, color: INK });
  });

  for (let i = 0; i < 6; i++) s.addImage({ data: img("ob_wall"), x: 5.34, y: 1.9 + i * 0.585, w: 0.6, h: 0.6 });
  s.addShape(pres.ShapeType.rect, { x: 5.16, y: 3.22, w: 0.96, h: 0.66, fill: { color: "0D1018" }, line: { color: AMB, width: 1.25 } });
  mono(s, "READ\nONLY", { x: 5.16, y: 3.22, w: 0.96, h: 0.66, fontSize: 10, bold: true, color: AMB, align: "center", valign: "middle", lineSpacing: 12 });

  panel(s, { x: 6.34, y: 1.9, w: 6.39, h: 3.5, fill: PANEL, line: AMB });
  mono(s, "INTERPRETATION  ·  판단층 (동적)", { x: 6.58, y: 2.06, w: 5.9, h: 0.26, fontSize: 10.5, bold: true, color: AMB });
  const tools = [["facts", GRN], ["price_series", GRN], ["price_series", GRN], ["calendar", GRN],
                 ["macro", GRN], ["disclosures", GRN], ["staleness", GRN], ["papers", CYN]];
  tools.forEach((t, i) => {
    const x = 6.58 + (i % 2) * 3.0, y = 2.44 + Math.floor(i / 2) * 0.42;
    s.addShape(pres.ShapeType.rect, { x, y, w: 2.82, h: 0.34, fill: { color: PANEL2 }, line: { type: "none" } });
    s.addImage({ data: img("ic_ok"), x: x + 0.1, y: y + 0.1, w: 0.14, h: 0.14 });
    mono(s, t[0], { x: x + 0.32, y, w: 2.4, h: 0.34, fontSize: 9.5, bold: true, color: t[1], valign: "middle" });
  });
  mono(s, "ingest · catchup · fundamentals · KIS 주문  →  도구가 존재하지 않는다", {
    x: 6.58, y: 4.32, w: 5.9, h: 0.26, fontSize: 9.5, bold: true, color: MAG });
  txt(s, "새 도구 papers 가 추가된다 — 논문 원장을 읽기만 한다. 채택·은퇴를 쓰는 것은 재현 파이프라인(배치)이지 에이전트가 아니다.", {
    x: 6.58, y: 4.64, w: 5.9, h: 0.6, fontSize: 10, color: MUT });

  const w3 = [["벽은 구조다", "\"쓰지 마라\"라고 적는 대신, 쓸 수 있는 도구를 만들지 않는다."],
              ["역류가 없다", "해석이 원장으로 되돌아가는 경로가 스키마에도 도구에도 없다."],
              ["인스턴스가 늘어도 같다", "1개든 400개든 전부 같은 읽기 도구 집합만 받는다."]];
  w3.forEach((n, i) => {
    const x = M + i * 4.11;
    panel(s, { x, y: 5.62, w: 3.94, h: 1.18, fill: PANEL3, line: EDGE });
    txt(s, n[0], { x: x + 0.2, y: 5.76, w: 3.5, h: 0.28, fontSize: 12, bold: true, color: GRN });
    txt(s, n[1], { x: x + 0.2, y: 6.06, w: 3.56, h: 0.62, fontSize: 10, color: MUT });
  });
}

function sEnvelope() {
  const s = slide();
  header(s, "PART 4 · ENVELOPE v2", "봉투에 재현 결과가 함께 실린다",
         "논문 키만 다는 것으로는 부족하다. 그 논문이 우리 표본에서 어떻게 나왔는지가 같이 가야 한다.");

  panel(s, { x: M, y: 1.84, w: 6.7, h: 4.62, fill: "0A1020", line: EDGE });
  mono(s, [
    '{',
    '  "claim":        "처분 소요일수 12.4 영업일",',
    '  "measure":      "disposal_days",   "subject": "000660",',
    '  "value":        12.4,',
    '  "unit":         "business_days",',
    '  "asof":         "2026-09-11",  "stale_days": 2,',
    '',
    '  "source_grade": "해석",',
    '  "sources":      ["KRX/일별매매정보"],',
    '',
    '  "method": {',
    '    "paper":       "amihud2002",',
    '    "paper_state": "adopted",',
    '    "replication": {                    // ← v2 신설',
    '      "verdict":  "재현됨",',
    '      "at":       "2026-02-11",',
    '      "universe": "KOSDAQ", "n": 1418,',
    '      "observed": { "spread_mean_bp": 41, "t": 3.42 }   // 임계 3.0',
    '    },',
    '    "assumes": { "participation": 0.15 }',
    '  },',
    '',
    '  "read": [{"key": "000660.close", "value": 88.0,',
    '            "asof": "2026-09-11", "kind": "raw"}],   // \u2190 v2',
    '',
    '  "limits": ["논문 표본은 미국 상장주 — 코스닥 외삽 근거 아님"],',
    '',
    '  "desk": "q3-execution",',
    '  "instance": "q3-execution-20260911-000660-a91f",  // ← v2 신설',
    '  "tier": "T2",  "attempt": 1,  "escalated_from": null,',
    '  "spent": {"tool_calls": 11, "completed": true},   // \u2190 v2',
    '  "reviewed_by": ["risk", "compliance"]',
    '}',
  ].join("\n"), { x: M + 0.24, y: 1.96, w: 6.25, h: 4.42, fontSize: 7.4, color: "A9C8F0", lineSpacing: 9.2, valign: "top" });

  const f = [
    ["read · kind", "무엇을 읽고 냈는가 · 원본인가 파생인가", "정정이 오면 원장의 같은 칸이 덮어써진다. 파생값을 원본 칸과 대조하면 거짓 '바뀜'이 나온다.", GRN],
    ["paper_state", "그 논문이 어느 상태인가", "retired · 방향 반대는 반려. unverified 는 통과하되 '미검증' 표시가 함께 나간다.", CYN],
    ["measure", "무엇을 잰 값인가", "데스크가 달라도 같은 것을 쟀으면 같은 이름이다. 이것이 없으면 대조 자체가 안 되고, '갈린 곳 없음'이 '안 봤다'가 된다.", PUR],
    ["spent · attempt", "호출을 몇 번 썼고 끝냈는가", "토큰은 담지 않는다 — 에이전트가 신뢰성 있게 세지 못한다. 미완이면 사유를 요구한다.", AMB],
  ];
  f.forEach((x2, i) => {
    const y = 1.88 + i * 1.08;
    panel(s, { x: 7.52, y, w: 5.21, h: 0.96, fill: PANEL, line: EDGE });
    mono(s, x2[0], { x: 7.74, y: y + 0.1, w: 2.6, h: 0.24, fontSize: 10, bold: true, color: x2[3] });
    txt(s, x2[1], { x: 10.2, y: y + 0.11, w: 2.36, h: 0.22, fontSize: 8.8, color: MUT, align: "right" });
    txt(s, x2[2], { x: 7.74, y: y + 0.38, w: 4.8, h: 0.5, fontSize: 9.5, color: INK });
  });
  panel(s, { x: 7.52, y: 6.22, w: 5.21, h: 0.6, fill: PANEL3, line: EDGE });
  txt(s, "등급 '해석' 은 그대로다 — 재현까지 통과해도 에이전트 문장은 1차 자료가 되지 않는다.", {
    x: 7.74, y: 6.22, w: 4.8, h: 0.6, fontSize: 10, bold: true, color: AMB, valign: "middle" });
}

function sGates() {
  const s = slide();
  header(s, "PART 4 · GATES ×7", "발행 전 일곱 관문 — 하나라도 걸리면 멈춘다",
         "여섯 개는 지난 방안 그대로이고, ③ 재현 관문이 새로 들어간다.");

  const gates = [
    ["판정 어휘", "점수·등급·목표주가·매수/매도 어휘가 있는가", "문장 삭제 후 반려", MAG, false],
    ["출처 등급", "모든 주장에 grade 가 있는가 · '해석'이 승격되지 않았는가", "등급 없는 주장 차단", AMB, false],
    ["재현", "인용 논문의 state 가 무엇인가 (4상태)", "retired · 방향 반대 → 반려", GRN, true],
    ["논문 실재", "장부에 실재하는 논문인가 · limits 가 비어 있지 않은가", "지어낸 인용 차단", CYN, false],
    ["신선도", "asof·stale_days 가 임계(3영업일)를 넘지 않는가", "값 대신 '데이터 없음'", BLU, false],
    ["유출 검사", "키·URL·포트폴리오사 실명이 남았는가 (scrub())", "전체 발행 중단", ORG, false],
    ["4-eyes", "리스크와 준법감시 양쪽이 승인했는가", "해당 절 제외", PUR, false],
  ];
  gates.forEach((g, i) => {
    const col = i % 4, row = Math.floor(i / 4);
    const x = M + col * 3.06, y = 1.86 + row * 2.24;
    panel(s, { x, y, w: 2.86, h: 2.06, fill: g[4] ? "132318" : PANEL, line: g[4] ? GRN : EDGE });
    s.addImage({ data: img("ob_gate"), x: x + 0.18, y: y + 0.18, w: 0.5, h: 0.5 });
    mono(s, "GATE " + (i + 1), { x: x + 0.78, y: y + 0.2, w: 1.9, h: 0.22, fontSize: 9, bold: true, color: g[3], charSpacing: 1 });
    txt(s, g[0], { x: x + 0.78, y: y + 0.4, w: 1.94, h: 0.3, fontSize: 14, bold: true, color: INK });
    txt(s, g[1], { x: x + 0.18, y: y + 0.8, w: 2.5, h: 0.72, fontSize: 9.5, color: MUT });
    s.addShape(pres.ShapeType.rect, { x: x + 0.18, y: y + 1.58, w: 2.5, h: 0.32, fill: { color: PANEL2 }, line: { type: "none" } });
    mono(s, "✕ " + g[2], { x: x + 0.28, y: y + 1.58, w: 2.3, h: 0.32, fontSize: 8.8, bold: true, color: MUT, valign: "middle" });
    if (g[4]) { s.addImage({ data: img("ic_spark"), x: x + 2.44, y: y + 0.16, w: 0.22, h: 0.22 }); }
  });
  panel(s, { x: M + 3.06 * 3, y: 4.10, w: 2.86, h: 2.06, fill: PANEL3, line: EDGE });
  txt(s, "통과 아니면 반려다", { x: M + 3.06 * 3 + 0.18, y: 4.26, w: 2.5, h: 0.3, fontSize: 13, bold: true, color: GLD });
  txt(s, "\"대체로 지켜졌다\"는 판정이 없다. 반려된 절은 회의자료에서 빈칸이 아니라 '반려됨 — 사유' 로 보인다. 조용히 통과시키는 것이 가장 위험하다.", {
    x: M + 3.06 * 3 + 0.18, y: 4.6, w: 2.52, h: 1.4, fontSize: 10, color: MUT });
  foot(s, "// 기존 selftest 128개는 그대로 둔다. 게이트는 코드가 아니라 '에이전트가 쓴 문장'을 검사하는 층으로 그 위에 얹는다.");
}

function sScorecard() {
  const s = slide();
  header(s, "PART 4 · SCORECARD & REPLAY", "데스크를 계측한다 — 다만 자동으로 고치지는 않는다",
         "무엇이 얼마나 반려됐고 무엇이 재현에 실패했는지를 매주 본다. 프롬프트를 고치는 것은 사람이다.");

  panel(s, { x: M, y: 1.86, w: 6.3, h: 3.0, fill: PANEL, line: EDGE });
  txt(s, "주간 데스크 스코어카드  (예시 값)", { x: M + 0.24, y: 2.0, w: 4.6, h: 0.3, fontSize: 14, bold: true, color: INK });
  const sc = [
    ["q1-progress", 0.94, 0.06, GRN],
    ["q2-disposal", 0.81, 0.19, AMB],
    ["q3-execution", 0.90, 0.10, GRN],
    ["q4-timing", 0.88, 0.12, GRN],
    ["quant-method", 0.97, 0.03, GRN],
  ];
  mono(s, "데스크", { x: M + 0.24, y: 2.36, w: 2.2, h: 0.22, fontSize: 9, color: DIM });
  mono(s, "게이트 통과율", { x: M + 2.5, y: 2.36, w: 2.6, h: 0.22, fontSize: 9, color: DIM });
  mono(s, "반려", { x: M + 5.3, y: 2.36, w: 0.8, h: 0.22, fontSize: 9, color: DIM, align: "right" });
  sc.forEach((r, i) => {
    const y = 2.62 + i * 0.38;
    mono(s, r[0], { x: M + 0.24, y, w: 2.2, h: 0.3, fontSize: 9.5, color: INK, valign: "middle" });
    pxBar(s, M + 2.5, y + 0.09, 2.6, 0.14, r[1], r[3]);
    mono(s, Math.round(r[2] * 100) + "%", { x: M + 5.3, y, w: 0.8, h: 0.3, fontSize: 9.5, bold: true, color: r[3], align: "right", valign: "middle" });
  });
  txt(s, "위 숫자는 모양이다. 실제 값은 발행 기록에서 나온다 — 아직 원장에 물려 돌린 적이 없어 실측이 아니다. 반려가 몰리는 곳은 프롬프트가 아니라 스킬 문서를 고쳐야 한다는 신호다.", {
    x: M + 0.24, y: 4.50, w: 5.85, h: 0.3, fontSize: 9, italic: true, color: AMB });

  const metrics = [["게이트 통과율", "n/N", "반려가 몰리는 관문도 함께", GRN],
                   ["승격 분포", "T1→T2→T3", "집행 사유 셋의 분포만", AMB],
                   ["예산 미완", "건수 · 호출", "토큰은 세지 않는다", CYN],
                   ["표시 포화도", "0~1", "1.0 이면 그 표시는 배경", MAG]];
  metrics.forEach((m, i) => {
    const x = 7.1 + (i % 2) * 2.86, y = 1.86 + Math.floor(i / 2) * 1.54;
    panel(s, { x, y, w: 2.72, h: 1.42, fill: PANEL, line: EDGE });
    mono(s, m[1], { x: x + 0.18, y: y + 0.16, w: 2.36, h: 0.42, fontSize: 23, bold: true, color: m[3] });
    txt(s, m[0], { x: x + 0.18, y: y + 0.62, w: 2.36, h: 0.24, fontSize: 10.5, bold: true, color: INK });
    txt(s, m[2], { x: x + 0.18, y: y + 0.88, w: 2.4, h: 0.42, fontSize: 9, color: MUT });
  });

  panel(s, { x: M, y: 5.02, w: CW, h: 1.8, fill: PANEL3, line: EDGE });
  txt(s, "리플레이 — 왜 그렇게 읽었는가를 되짚는다", { x: M + 0.26, y: 5.16, w: 6.0, h: 0.3, fontSize: 14, bold: true, color: GLD });
  const rp = [
    ["봉투가 읽은 것을 적는다", "원장은 정정이 오면 같은 칸을 덮어쓴다. 봉투의 read 와 대조해야 '틀렸다'와 '바뀌었다'가 갈린다."],
    ["instance ID 로 특정된다", "어느 인스턴스가 어떤 입력으로 만든 문장인지 좁혀진다. 무상태라 같은 입력이면 같은 봉투가 나와야 한다."],
    ["논문 원장은 append-only", "그날의 재현 판정이 남아 있어, 지금 기준이 아니라 그때 기준으로 되짚을 수 있다."],
  ];
  rp.forEach((r, i) => {
    const x = M + 0.26 + i * 4.03;
    s.addImage({ data: img("ic_ok"), x, y: 5.58, w: 0.18, h: 0.18 });
    txt(s, r[0], { x: x + 0.26, y: 5.52, w: 3.6, h: 0.28, fontSize: 11.5, bold: true, color: INK });
    txt(s, r[1], { x: x + 0.26, y: 5.82, w: 3.62, h: 0.8, fontSize: 9.5, color: MUT });
  });
}

function sDay() {
  const s = slide();
  header(s, "PART 5 · A DAY", "하루 — 기존 자동 실행 시각은 그대로 쓴다",
         "SCHEDULE.cmd 의 07:30 · 08:50 · 16:10 을 바꾸지 않는다. 그 사이에 소집·게이트·조립을 끼워 넣는다.");

  const stops = [
    ["07:30", "수확 · 재현 배치", ["arXiv·S2·OpenAlex·Crossref 훑기", "재검 기한 도래분 재현 실행", "채택 최대 1편 · 은퇴 판정"], "배치 (에이전트 아님)", CYN],
    ["08:50", "리포트 + 소집", ["리포트 생성 (기존 그대로)", "트리거 스캔 → 인스턴스 생성", "데스크 병렬 작업 · 봉투 제출"], "spawn ~50", GRN],
    ["09:00\n~15:30", "장중 (읽기만)", ["KIS 스냅샷은 화면에만", "원장에 쓰지 않는다", "데스크는 돌지 않는다"], "standing only", PUR],
    ["16:10", "종가 적재", ["그날의 유일한 원장 쓰기", "catchup 으로 영업일 채움", "stale_days 갱신"], "data-ops 단독", AMB],
    ["17:00", "게이트 → 조립", ["risk 검산 → compliance 판정", "통과분만 ic-chair 로", "반려분은 사유와 함께 남는다"], "발행", GLD],
  ];
  const bw = 2.36, bg = 0.12;
  stops.forEach((st, i) => {
    const x = M + i * (bw + bg);
    panel(s, { x, y: 1.9, w: bw, h: 0.62, fill: st[4], line: null });
    mono(s, st[0], { x, y: 1.9, w: bw, h: 0.62, fontSize: st[0].indexOf("\n") >= 0 ? 13 : 19, bold: true, color: "0D1018", align: "center", valign: "middle" });
    panel(s, { x, y: 2.62, w: bw, h: 3.16, fill: PANEL, line: EDGE });
    txt(s, st[1], { x: x + 0.16, y: 2.78, w: bw - 0.32, h: 0.56, fontSize: 13, bold: true, color: INK });
    st[2].forEach((t, j) => {
      s.addShape(pres.ShapeType.rect, { x: x + 0.18, y: 3.5 + j * 0.62, w: 0.08, h: 0.08, fill: { color: st[4] }, line: { type: "none" } });
      txt(s, t, { x: x + 0.36, y: 3.42 + j * 0.62, w: bw - 0.54, h: 0.56, fontSize: 9.5, color: MUT });
    });
    s.addShape(pres.ShapeType.rect, { x: x + 0.16, y: 5.3, w: bw - 0.32, h: 0.32, fill: { color: PANEL2 }, line: { type: "none" } });
    mono(s, st[3], { x: x + 0.16, y: 5.3, w: bw - 0.32, h: 0.32, fontSize: 8.8, bold: true, color: st[4], align: "center", valign: "middle" });
  });

  panel(s, { x: M, y: 5.96, w: CW, h: 0.86, fill: PANEL3, line: EDGE });
  txt(s, [
    { text: "장중에 데스크를 돌리지 않는 이유 — ", options: { bold: true, color: AMB } },
    { text: "일봉 장부 위에 세운 해석을 장중 값과 섞으면 무엇을 근거로 읽었는지가 시각마다 달라진다. 하루 한 번, 같은 기준일 위에서만 읽는다.\n", options: { color: INK } },
    { text: "재현을 07:30 배치로 두는 이유 — ", options: { bold: true, color: CYN } },
    { text: "재현은 판단이 아니라 계산이다. 에이전트가 아니라 결정적 코드가 돌려야 매번 같은 답이 나온다.", options: { color: INK } },
  ], { x: M + 0.26, y: 5.96, w: CW - 0.52, h: 0.86, fontSize: 10.5, valign: "middle", lineSpacing: 17, fontFace: F, isTextBox: true, margin: 0 });
}

function sRoadmap() {
  const s = slide();
  header(s, "PART 5 · ROADMAP", "다섯 단계 중 넷이 코드로 들어갔다",
         "논문 파이프라인이 먼저였다. 재현되지 않은 방법론 위에 에이전트를 아무리 많이 띄워도 의미가 없기 때문이다.");

  const ph = [
    ["P1", "들어감", "논문 원장", ["ki.papers/2 스키마 전환", "state · replication · 반감기", "기존 12편 이관 (미검증으로)", "papers MCP 도구"], CYN, 1],
    ["P2", "들어감", "재현 관문", ["분위 러너 · 이벤트 러너", "임계 |t| ≥ 3.0 확정", "판정 → 장부 append", "게이트 ③ 코드화"], GRN, 1],
    ["P3", "들어감", "사이클 상시화", ["월 07:40 주간 배치 등록", "재검 도래분 합류 · 주 3편", "감가 · 경고 · 은퇴 자동화", "채택률 실측은 원장 필요"], AMB, 0.85],
    ["P4", "들어감", "동적 소집", ["트리거 스캐너", "작업지시서 발급 · 회수 대조", "T1~T3 에스컬레이션", "봉투 v2 · instance · read"], PUR, 1],
    ["P5", "일부", "병행 운영", ["스코어카드 · 리플레이", "사람 산출과 2주 대조", "불일치 원인 전수 분석", "전환 여부는 사람이 결정"], MAG, 0.4],
  ];
  const pw = 2.36, pg = 0.12;
  ph.forEach((p, i) => {
    const x = M + i * (pw + pg);
    panel(s, { x, y: 1.88, w: pw, h: 0.46, fill: p[4], line: null });
    mono(s, p[0] + "  ·  " + p[1], { x, y: 1.88, w: pw, h: 0.46, fontSize: 10.5, bold: true, color: "0D1018", align: "center", valign: "middle" });
    panel(s, { x, y: 2.44, w: pw, h: 3.3, fill: PANEL, line: p[5] >= 1 ? p[4] : EDGE });
    txt(s, p[2], { x: x + 0.16, y: 2.6, w: pw - 0.32, h: 0.6, fontSize: 15, bold: true, color: p[4] });
    pxBar(s, x + 0.16, 3.06, pw - 0.32, 0.1, p[5], p[4]);
    p[3].forEach((t, j) => {
      s.addShape(pres.ShapeType.rect, { x: x + 0.18, y: 3.32 + j * 0.62, w: 0.08, h: 0.08, fill: { color: p[4] }, line: { type: "none" } });
      txt(s, t, { x: x + 0.36, y: 3.24 + j * 0.62, w: pw - 0.54, h: 0.56, fontSize: 9.5, color: INK });
    });
  });

  const outs = [["코드로 끝난 것", "스키마 · 러너 · 관문 · 트리거 · 사이클 · 되짚기 — 자체 검사 339개", GRN],
                ["원장이 있어야 되는 것", "12편 중 5편의 실제 재현 · 채택률 · 트리거 발생률 실측", AMB],
                ["사람이 정할 것", "병행 2주 결과로 전환 여부 — 이 덱이 아니라 회의에서", MAG]];
  outs.forEach((o, i) => {
    const x = M + i * 4.11;
    panel(s, { x, y: 5.94, w: 3.94, h: 0.76, fill: PANEL3, line: EDGE });
    mono(s, o[0], { x: x + 0.2, y: 6.04, w: 3.5, h: 0.24, fontSize: 10, bold: true, color: o[2] });
    txt(s, o[1], { x: x + 0.2, y: 6.28, w: 3.56, h: 0.36, fontSize: 10, color: INK });
  });
}

function sNext() {
  const s = slide();
  for (let i = 0; i < 42; i++) s.addShape(pres.ShapeType.rect, {
    x: 0, y: i * 0.18, w: W, h: 0.03, fill: { color: "121826" }, line: { type: "none" },
  });
  mono(s, "▚ PART 5 · NEXT STEP", { x: M, y: 0.46, w: CW, h: 0.26, fontSize: 11, bold: true, color: AMB, charSpacing: 1.5 });
  txt(s, "코드로 끝난 것과, 원장이 있어야 되는 것", {
    x: M, y: 0.76, w: CW, h: 0.56, fontSize: 28, bold: true, color: INK });

  const todo = [
    ["재현을 진짜 원장에 물린다", "python agents/cycle.py --run  ·  12편 중 5편이 검정 대상이다. 합성 자료로는 러너가 맞다는 것까지만 확인했다.", "원장 필요", GRN],
    ["트리거 발생률을 역산한다", "python agents/run_day.py --stage convene  ·  원장의 공시·변동 이력으로 실제 소집 건수를 잰다. 부하 수치를 가정값에서 실측으로 바꾼다.", "원장 필요", AMB],
    ["method_papers 두 편을 Crossref 로 재대조", "hlz2016 · nw1987. 서지는 세 곳에서 일치를 봤지만 빌드 환경은 Crossref 이그레스가 막혀 규율대로의 재대조를 못 했다.", "망 필요", CYN],
    ["needs_runner 가 비었다 — 유지할지 본다", "12편 중 8편이 검정 대상이고 나머지 4편은 추정량·모형이라 원래 대상이 아니다. 새 논문이 그 칸에 걸리면 사유를 적어 넣는다.", "확인", PUR],
    ["병행 2주 — 사람 산출과 대조", "스코어카드와 리플레이가 준비돼 있다. 전환 여부는 그 결과를 놓고 회의에서 사람이 정한다.", "회의", MAG],
  ];
  todo.forEach((t, i) => {
    const y = 1.62 + i * 0.94;
    panel(s, { x: M, y, w: 7.7, h: 0.82, fill: PANEL, line: EDGE });
    s.addShape(pres.ShapeType.rect, { x: M + 0.18, y: y + 0.19, w: 0.44, h: 0.44, fill: { color: t[3] }, line: { type: "none" } });
    mono(s, String(i + 1), { x: M + 0.18, y: y + 0.19, w: 0.44, h: 0.44, fontSize: 14, bold: true, color: "0D1018", align: "center", valign: "middle" });
    txt(s, t[0], { x: M + 0.78, y: y + 0.11, w: 5.4, h: 0.28, fontSize: 12.5, bold: true, color: INK });
    txt(s, t[1], { x: M + 0.78, y: y + 0.41, w: 5.8, h: 0.32, fontSize: 9.5, color: MUT });
    mono(s, t[2], { x: M + 6.62, y: y + 0.11, w: 0.9, h: 0.28, fontSize: 11, bold: true, color: t[3], align: "right" });
  });

  mono(s, "성공 판정 지표", { x: 8.6, y: 1.62, w: 4.1, h: 0.28, fontSize: 12, bold: true, color: AMB, charSpacing: 1 });
  const kpi = [["339개", "자체 검사", "키·네트워크·원장 없이 돈다", GRN],
               ["0줄", "ki_monitor.py 변경", "측정층은 손대지 않았다", CYN],
               ["8 / 12", "검정 대상 논문", "나머지 4편은 원래 대상 아님", AMB],
               ["0건", "미분류 논문", "전부 셋 중 하나로 분류됐다", MAG]];
  kpi.forEach((k, i) => {
    const y = 2.02 + i * 1.16;
    mono(s, k[0], { x: 8.6, y, w: 4.1, h: 0.44, fontSize: 25, bold: true, color: k[3] });
    txt(s, k[1], { x: 8.6, y: y + 0.46, w: 4.1, h: 0.24, fontSize: 11, bold: true, color: INK });
    txt(s, k[2], { x: 8.6, y: y + 0.7, w: 4.1, h: 0.24, fontSize: 9, color: MUT });
  });

  panel(s, { x: M, y: 6.32, w: 7.7, h: 0.5, fill: "16281C", line: "2A5A3A" });
  txt(s, "①②③ 이 여기서 안 되는 것은 미완이어서가 아니라 환경 때문이다 — 원장은 87MB 라 저장소에 없고, 빌드 환경은 외부 이그레스가 전면 차단돼 있다. 코드는 세 경우 모두 준비돼 있다.", {
    x: M + 0.24, y: 6.32, w: 7.3, h: 0.5, fontSize: 11, bold: true, color: GRN, valign: "middle" });
  mono(s, "내부 검토용 · 대외비 · 투자권유 자료 아님 · 계획안", {
    x: M, y: 7.00, w: 8.0, h: 0.28, fontSize: 9, color: DIM });
}


/* ── NEW: Executive Summary ── */
function sExec() {
  const s = slide();
  header(s, "EXECUTIVE SUMMARY", "요약 — 무엇을 바꾸고, 무엇을 지키는가",
         "측정 파이프라인은 이미 완성돼 있다. 이 방안이 손대는 것은 측정 결과를 읽는 층과, 그 읽기의 근거가 되는 논문이다.");

  const rows = [
    ["바꾼다", "주 1회 새 논문을 들여와 통과 테스트를 돌린다", "수확 → 심사 → 재현 → 채택이 매주 한 번 돈다. 반감기가 도래한 기존 채택본도 같은 사이클에서 재검된다.", GRN],
    ["바꾼다", "질문마다 데스크 하나 — 아홉으로 나눈다", "네 질문(q1~q4) 각각에 담당을 두고, 그 질문의 답이 달라졌을 때만 소집한다.", CYN],
    ["지킨다", "원장(ki.sqlite)은 여전히 사실만 담는다", "에이전트에게 쓰기 도구를 아예 주지 않는다. 규칙이 아니라 구조로 막는다.", AMB],
    ["지킨다", "판단은 여전히 회의에서 사람이 한다", "점수·등급·매매 시그널을 만들지 않는다. 올라가는 것은 쟁점이지 결론이 아니다.", PUR],
  ];
  rows.forEach((r, i) => {
    const y = 1.82 + i * 1.06;
    panel(s, { x: M, y, w: 7.9, h: 0.94, fill: PANEL, line: EDGE });
    s.addShape(pres.ShapeType.rect, { x: M + 0.18, y: y + 0.26, w: 1.0, h: 0.42, fill: { color: r[3] }, line: { type: "none" } });
    mono(s, r[0], { x: M + 0.18, y: y + 0.26, w: 1.0, h: 0.42, fontSize: 10.5, bold: true, color: "0D1018", align: "center", valign: "middle" });
    txt(s, r[1], { x: M + 1.34, y: y + 0.16, w: 6.3, h: 0.3, fontSize: 13.5, bold: true, color: INK });
    txt(s, r[2], { x: M + 1.34, y: y + 0.48, w: 6.4, h: 0.38, fontSize: 10.5, color: MUT });
  });

  const st = [["주 1회", "논문 사이클", "신규 + 재검 도래분"], ["N", "살아있는 논문", "고정값이 아니다"],
              ["7", "발행 게이트", "재현 관문 신설"], ["0", "원장 쓰기 권한", "에이전트는 못 쓴다"],
              ["0줄", "ki_monitor.py 변경", "측정층은 그대로"], ["339개", "자체 검사", "키·망·원장 없이"]];
  st.forEach((t, i) => {
    const x = 8.72 + (i % 2) * 2.02, y = 1.82 + Math.floor(i / 2) * 1.42;
    panel(s, { x, y, w: 1.88, h: 1.3, fill: PANEL, line: EDGE });
    mono(s, t[0], { x: x + 0.14, y: y + 0.14, w: 1.6, h: 0.38, fontSize: 19, bold: true, color: GLD });
    txt(s, t[1], { x: x + 0.14, y: y + 0.56, w: 1.62, h: 0.24, fontSize: 9.5, bold: true, color: INK });
    txt(s, t[2], { x: x + 0.14, y: y + 0.80, w: 1.62, h: 0.36, fontSize: 8.5, color: MUT });
  });

  panel(s, { x: M, y: 6.14, w: CW, h: 0.68, fill: "16281C", line: "2A5A3A" });
  txt(s, [
    { text: "핵심은 사이클이다 —  ", options: { bold: true, color: GRN } },
    { text: "논문을 한 번에 검증하고 끝내는 것이 아니라, 매주 새 논문이 들어오고 오래된 것이 재검되는 흐름을 만든다. 기존 12편도 반감기 순번이 오면 이 사이클에 들어온다.", options: { color: INK } },
  ], { x: M + 0.26, y: 6.14, w: CW - 0.52, h: 0.68, fontSize: 11.5, valign: "middle", fontFace: F, isTextBox: true, margin: 0 });
}

/* ── NEW: 이 문서의 구성 ── */
function sAgenda() {
  const s = slide();
  header(s, "CONTENTS", "이 문서의 구성",
         "다섯 부로 나뉜다. 2부(논문)가 먼저인 이유는, 재현되지 않은 방법론 위에 에이전트를 아무리 많이 띄워도 의미가 없기 때문이다.");

  const parts = [
    ["PART 1", "지금", ["현재 자산 진단", "왜 에이전트화인가", "깨면 안 되는 다섯 가지", "★ 리픽싱 · 희석 ≠ 권리락", "처분 여건"], "측정은 이미 된다. 문제는 독해다.", CYN],
    ["PART 2", "논문을 살린다", ["12편은 스냅샷이다", "주 1회 파이프라인 5단계", "★ 재현 관문", "감가 · 은퇴", "논문 원장 스키마"], "인용하기 전에 우리 데이터로 계산한다.", GRN],
    ["PART 3", "조직과 에이전트", ["★ 질문이 데스크를 정한다", "목표 조직도 — 9 데스크", "데스크 카탈로그 2장", "상설 3 vs 소집 6", "조달 · 트리거 · 부하"], "네 질문이 조직을 정한다.", AMB],
    ["PART 4", "통제", ["정보교류차단", "권한 매트릭스", "봉투 스키마", "일곱 게이트 · 스코어카드"], "벽은 규칙이 아니라 구조다.", MAG],
    ["PART 5", "실행", ["기술 스택 · MCP 설계", "하루 운영 · 로드맵", "리스크 · 착수와 KPI"], "기존 코드는 한 줄도 고치지 않는다.", PUR],
  ];
  const pw = 2.36, pg = 0.12;
  parts.forEach((p, i) => {
    const x = M + i * (pw + pg);
    panel(s, { x, y: 1.90, w: pw, h: 0.46, fill: p[4], line: null });
    mono(s, p[0], { x, y: 1.90, w: pw, h: 0.46, fontSize: 11, bold: true, color: "0D1018", align: "center", valign: "middle" });
    panel(s, { x, y: 2.46, w: pw, h: 3.5, fill: PANEL, line: EDGE });
    txt(s, p[1], { x: x + 0.16, y: 2.62, w: pw - 0.32, h: 0.6, fontSize: 16, bold: true, color: p[4] });
    p[2].forEach((t, j) => {
      s.addShape(pres.ShapeType.rect, { x: x + 0.18, y: 3.34 + j * 0.40, w: 0.08, h: 0.08, fill: { color: p[4] }, line: { type: "none" } });
      txt(s, t, { x: x + 0.36, y: 3.26 + j * 0.40, w: pw - 0.54, h: 0.40, fontSize: 10, color: INK });
    });
    panel(s, { x: x + 0.16, y: 5.38, w: pw - 0.32, h: 0.46, fill: PANEL2, line: null, off: 0 });
    txt(s, p[3], { x: x + 0.26, y: 5.38, w: pw - 0.52, h: 0.46, fontSize: 9, color: MUT, valign: "middle" });
  });

  panel(s, { x: M, y: 6.16, w: CW, h: 0.62, fill: PANEL3, line: EDGE });
  txt(s, [
    { text: "이 문서는 계획안이다. ", options: { bold: true, color: AMB } },
    { text: "아직 아무것도 구현하지 않았고, 숫자 중 시뮬레이션 가정값은 그 사실을 각 장 하단에 적어 두었다.", options: { color: INK } },
  ], { x: M + 0.26, y: 6.16, w: CW - 0.52, h: 0.62, fontSize: 11, valign: "middle", fontFace: F, isTextBox: true, margin: 0 });
}

/* ── NEW: AS-IS 진단 ── */
function sAsIs() {
  const s = slide();
  header(s, "PART 1 · AS-IS", "지금 가진 것 — 측정 파이프라인은 이미 완성돼 있다",
         "새로 만들 것은 측정이 아니라, 측정 결과를 읽고 정렬하는 층이다.");

  const flow = [
    ["공식 API 5종", "KRX · DART · ECOS\nKIS · FRED", CYN],
    ["ki.sqlite 원장", "사실만 담는다\n7개 테이블", GRN],
    ["측정 함수", "처분소요일 · 집행시뮬\n분위 · 매물대", BLU],
    ["HTML 리포트", "§1~§8 · 외부 리소스 0\n절마다 출처 등급", PUR],
    ["오프라인 회의", "사람이 결정한다", GLD],
  ];
  const bw = 2.14, gap = 0.34;
  flow.forEach((f, i) => {
    const x = M + i * (bw + gap);
    panel(s, { x, y: 1.96, w: bw, h: 1.6, fill: PANEL, line: f[2] });
    txt(s, f[0], { x: x + 0.12, y: 2.14, w: bw - 0.24, h: 0.3, fontSize: 12.5, bold: true, color: f[2], align: "center" });
    txt(s, f[1], { x: x + 0.1, y: 2.5, w: bw - 0.2, h: 0.86, fontSize: 9.5, color: MUT, align: "center", lineSpacing: 14 });
    if (i < 4) s.addImage({ data: img("ar_am"), x: x + bw + 0.02, y: 2.66, w: 0.3, h: 0.19 });
  });

  const st = [["8,684", "줄 · 단일 파일", "ki_monitor.py 하나가 수집·계산·리포트를 전부 한다", CYN],
              ["5", "1차 출처 공식 API", "크롤링 없음 · 유료 벤더 없음 · 뉴스 본문 없음", GRN],
              ["128", "자체 검증", "키·네트워크 없이 돈다. 실제로 128 passed 확인", AMB],
              ["12", "편 채택 논문", "팩터마다 논문 키를 달고 나간다 (.papers.json)", PUR]];
  st.forEach((t, i) => {
    const x = M + i * (2.98 + 0.13);
    panel(s, { x, y: 3.82, w: 2.98, h: 1.72, fill: PANEL, line: EDGE });
    mono(s, t[0], { x: x + 0.2, y: 4.0, w: 2.6, h: 0.5, fontSize: 28, bold: true, color: t[3] });
    txt(s, t[1], { x: x + 0.2, y: 4.56, w: 2.6, h: 0.26, fontSize: 11, bold: true, color: INK });
    txt(s, t[2], { x: x + 0.2, y: 4.86, w: 2.62, h: 0.5, fontSize: 9.5, color: MUT });
  });

  panel(s, { x: M, y: 5.72, w: CW, h: 1.02, fill: PANEL3, line: EDGE });
  txt(s, [
    { text: "결론 — ", options: { bold: true, color: GLD } },
    { text: "데이터 · 계산 · 검증은 손댈 것이 없다. 부족한 것은 두 가지다.\n", options: { color: INK } },
    { text: "① ", options: { bold: true, color: MAG } },
    { text: "산출물을 읽어 회의 쟁점으로 바꾸는 사람의 시간   ", options: { color: INK } },
    { text: "② ", options: { bold: true, color: MAG } },
    { text: "그 읽기의 근거가 되는 논문이 우리 시장에서 성립하는지에 대한 확인", options: { color: INK } },
  ], { x: M + 0.26, y: 5.72, w: CW - 0.52, h: 1.02, fontSize: 11.5, valign: "middle", lineSpacing: 20, fontFace: F, isTextBox: true, margin: 0 });
  foot(s, "// 출처: 저장소 실측 — ki_monitor.py 8,684줄 · CATALOG 31개 항목 · SECTIONS 18개 절 · selftest 128 passed 0 failed");
}

/* ── NEW: 왜 에이전트화인가 ── */
function sWhy() {
  const s = slide();
  header(s, "PART 1 · WHY", "병목은 계산이 아니라 독해다",
         "리포트는 매일 08:50에 나온다. 문제는 그것을 끝까지 읽을 사람이 없다는 것이다.");

  const cols = [
    { t: "지금의 병목", c: MAG, bg: "24141B", ln: "5C2A3A", ic: "ic_no", items: [
      ["읽는 사람이 한 명", "§1~§18을 통독하는 사람은 사실상 한 명이다."],
      ["85개 종목 × §5", "종목별 상세는 사람이 읽을 분량이 아니다. 몇 종목만 보고 회의에 들어간다."],
      ["이어 붙이기가 수작업", "DART 공시 원문 · 논문 · 매크로 일정을 종목에 연결하는 일은 전부 손이다."],
      ["방법론이 멈춰 있다", "채택본 최신이 2012년이다. 14년치 계량금융이 비어 있다."],
    ]},
    { t: "에이전트화 이후", c: GRN, bg: "13241A", ln: "2A5A3A", ic: "ic_ok", items: [
      ["데스크가 나눠 동시에 읽는다", "기업분석·계량·매크로·집행이 각자 자기 절만 맡는다."],
      ["변동분에만 초안이 붙는다", "전수가 아니라 그날 실제로 무언가 일어난 종목만 읽는다."],
      ["쟁점만 회의에 올라온다", "간사가 데스크 간 불일치와 결측만 추려 한 장으로 정렬한다."],
      ["방법론이 스스로 갱신된다", "매주 수확하고, 재현 검사를 통과한 것만 채택본에 들어온다."],
    ]},
  ];
  cols.forEach((col, ci) => {
    const x = M + ci * (6.02 + 0.26);
    panel(s, { x, y: 1.82, w: 6.02, h: 4.34, fill: col.bg, line: col.ln });
    txt(s, col.t, { x: x + 0.28, y: 2.0, w: 5.4, h: 0.34, fontSize: 16, bold: true, color: col.c });
    col.items.forEach((it, i) => {
      const y = 2.52 + i * 0.88;
      s.addImage({ data: img(col.ic), x: x + 0.28, y: y + 0.06, w: 0.2, h: 0.2 });
      txt(s, it[0], { x: x + 0.62, y, w: 5.2, h: 0.28, fontSize: 12.5, bold: true, color: INK });
      txt(s, it[1], { x: x + 0.62, y: y + 0.3, w: 5.22, h: 0.5, fontSize: 10, color: MUT });
    });
  });

  panel(s, { x: M, y: 6.28, w: CW, h: 0.6, fill: PANEL3, line: EDGE });
  txt(s, [
    { text: "자동화 대상은 '독해와 정렬'이다. ", options: { bold: true, color: GLD } },
    { text: "판단은 지금과 똑같이 회의에서 사람이 한다 — 이 경계가 흔들리면 에이전트화는 실패다.", options: { color: INK } },
  ], { x: M + 0.26, y: 6.28, w: CW - 0.52, h: 0.6, fontSize: 11.5, valign: "middle", fontFace: F, isTextBox: true, margin: 0 });
}

/* ── NEW: 깨면 안 되는 다섯 ── */
function sRules() {
  const s = slide();
  header(s, "PART 1 · NON-NEGOTIABLE", "에이전트가 들어와도 깨지 않는 다섯 가지",
         "아래는 CLAUDE.md 에 이미 적혀 있는 규칙이다. 에이전트화는 이것을 완화하는 일이 아니라, 코드가 아닌 곳에서도 지키게 만드는 일이다.");

  const rules = [
    ["재기만 하고 판단하지 않는다", "점수·등급·매매 시그널을 만들지 않는다.", "게이트 ① 판정 어휘", MAG],
    ["원장에는 측정한 사실만 쓴다", "추정·가정·장중 스냅샷(persist=False)을 넣지 않는다.", "MCP 에 쓰기 도구 미노출", GRN],
    ["없는 값을 만들지 않는다", "못 구한 값은 None 과 사유. 0 으로 채우지 않는다.", "봉투 null 허용 · 게이트 ⑤", CYN],
    ["재료에는 등급이 있다", "1차 · 참고 · 방법론 · 사내를 같은 표에 섞지 않는다.", "다섯 번째 등급 '해석' 신설", AMB],
    ["키와 대외비는 저장소 밖에 둔다", ".gitignore 는 약하다. git add -f 한 번이면 뚫린다.", "출력 scrub() 강제 · 게이트 ⑥", PUR],
  ];
  rules.forEach((r, i) => {
    const y = 2.24 + i * 0.86;
    panel(s, { x: M, y, w: CW, h: 0.74, fill: PANEL, line: EDGE });
    s.addShape(pres.ShapeType.rect, { x: M + 0.18, y: y + 0.16, w: 0.42, h: 0.42, fill: { color: r[3] }, line: { type: "none" } });
    mono(s, String(i + 1), { x: M + 0.18, y: y + 0.16, w: 0.42, h: 0.42, fontSize: 14, bold: true, color: "0D1018", align: "center", valign: "middle" });
    txt(s, r[0], { x: M + 0.76, y: y + 0.08, w: 3.9, h: 0.3, fontSize: 13, bold: true, color: INK });
    txt(s, r[1], { x: M + 0.76, y: y + 0.38, w: 5.0, h: 0.28, fontSize: 10, color: MUT });
    s.addShape(pres.ShapeType.rect, { x: M + 6.0, y: y + 0.17, w: 5.9, h: 0.4, fill: { color: PANEL2 }, line: { type: "none" } });
    s.addImage({ data: img("ar_gr"), x: M + 6.12, y: y + 0.28, w: 0.26, h: 0.16 });
    mono(s, "에이전트 적용 — " + r[2], { x: M + 6.48, y: y + 0.17, w: 5.3, h: 0.4, fontSize: 10, bold: true, color: r[3], valign: "middle" });
  });
  foot(s, "// 인용: CLAUDE.md '절대 깨지 말아야 할 것' §1~§5 · selftest 128개가 ①·⑤의 코드 측면을 이미 검사한다");
}




function sRbac() {
  const s = slide();
  header(s, "PART 4 · PERMISSIONS", "권한 매트릭스 — 누가 무엇을 할 수 있는가",
         "권한은 프롬프트가 아니라 도구 노출과 훅으로 강제한다. 아래는 실제로 부여할 도구 목록이다.");

  const cols = ["원장 읽기", "원장 쓰기", "외부 API", "KIS 주문", "회의자료 발행", "거부권"];
  const M_ = [
    ["q1-progress",        ["●","✕","✕","✕","✕","✕"]],
    ["q2-disposal",        ["●","✕","△ 원문만","✕","✕","✕"]],
    ["q3-execution",       ["●","✕","✕","✕","✕","✕"]],
    ["q4-timing",          ["●","✕","△ 원문만","✕","✕","✕"]],
    ["quant-method",       ["●","✕","△ 논문 4곳","✕","✕","✕"]],
    ["risk-officer",       ["●","✕","✕","✕","✕","●"]],
    ["compliance-officer", ["●","✕","✕","✕","●","●"]],
    ["data-ops",           ["●","●","● 5종 전부","✕","✕","✕"]],
    ["ic-chair",           ["●","✕","✕","✕","△ 초안만","✕"]],
  ];
  const head = [{ text: "에이전트", options: { bold: true, color: AMB, fill: { color: PANEL2 }, fontSize: 10.5, align: "left", fontFace: FM } }]
    .concat(cols.map(c => ({ text: c, options: { bold: true, color: AMB, fill: { color: PANEL2 }, fontSize: 10, align: "center", fontFace: F } })));
  const body = [head];
  M_.forEach(([k, vs], i) => {
    const bg = i % 2 ? PANEL3 : PANEL;
    const row = [{ text: k, options: { bold: true, color: INK, fontSize: 10, align: "left", valign: "middle", fontFace: FM, fill: { color: bg } } }];
    vs.forEach(v => {
      const yes = v.indexOf("●") === 0, no = v === "✕";
      row.push({ text: v, options: {
        fontSize: no ? 11 : 9.5, bold: yes, align: "center", valign: "middle",
        color: no ? "44506B" : (yes ? GRN : AMB),
        fill: { color: no ? bg : (yes ? "13241A" : "241E10") },
      }});
    });
    body.push(row);
  });
  s.addTable(body, {
    x: M, y: 1.82, w: CW, colW: [2.62, 1.28, 1.28, 1.85, 1.28, 1.62, 1.16],
    border: { type: "solid", color: EDGE, pt: 1 },
    fontFace: F, rowH: 0.40, margin: 0.07, autoPage: false,
  });

  const boxes = [
    ["외부 API 는 ingest-ops 뿐", "데스크는 네트워크를 쓰지 않는다. 실시간 호출을 허용하면 데스크마다 다른 시각의 값을 보게 되고 기준일이 깨진다.", MAG],
    ["원장 쓰기는 한 칸뿐", "data-ops 만 ●. 나머지 여덟 데스크는 MCP 읽기 도구만 받는다. 데스크가 몇이든 이 칸은 하나다.", GRN],
    ["△ 는 DART 원문 조회뿐", "수치는 전부 원장에서 읽는다. 밖으로 나가는 것은 접수번호로 지정된 공시 문서 한 건을 열 때뿐이다 — 검색이 아니다.", AMB],
  ];
  boxes.forEach((b, i) => {
    const x = M + i * 4.11;
    panel(s, { x, y: 6.22, w: 3.94, h: 0.84, fill: PANEL, line: EDGE });
    s.addShape(pres.ShapeType.rect, { x: x + 0.2, y: 6.39, w: 0.14, h: 0.14, fill: { color: b[2] }, line: { type: "none" } });
    txt(s, b[0], { x: x + 0.44, y: 6.31, w: 3.3, h: 0.28, fontSize: 11.5, bold: true, color: b[2] });
    txt(s, b[1], { x: x + 0.2, y: 6.61, w: 3.58, h: 0.42, fontSize: 8.8, color: MUT });
  });
}


/* ── NEW: 기술 스택 ── */
function sStack() {
  const s = slide();
  header(s, "PART 5 · TECH STACK", "구현 — 8,684줄을 다시 쓰지 않고 감싼다",
         "ki_monitor.py 는 한 줄도 고치지 않는다. 이미 있는 JSON 출력 명령(facts · candles · factors · calendar · macro)이 그대로 인터페이스가 된다.");

  const layers = [
    ["의결", "ic-chair 오케스트레이터", "Claude Agent SDK · 서브에이전트 팬아웃/팬인", "게이트 통과분만 조립", GLD],
    ["데스크", ".claude/agents/*.md  9개", "에이전트별 시스템 프롬프트 · 허용 도구 목록 · 담당 절", "도구 목록이 곧 권한", BLU],
    ["지식", ".claude/skills/  5종", "source-grading · envelope-schema · paper-adoption · replication · compliance-gate", "규칙을 프롬프트에 흩지 않는다", PUR],
    ["도구", "MCP 서버  ki-ledger (stdio · Python)", "ki_monitor.py 의 읽기 명령만 감싼 8개 도구. 쓰기 도구 없음", "벽이 세워지는 지점", GRN],
    ["배치", "재현 러너 · 수확 · 감가", "결정적 코드. 에이전트가 아니라 스케줄러가 돌린다", "매번 같은 답이 나와야 한다", CYN],
    ["통제", "Hooks  PreToolUse / PostToolUse", "화이트리스트 밖 호출 차단 · 모든 출력에 scrub() 강제 · 봉투 스키마 검증", "코드가 지키는 마지막 선", MAG],
    ["실행", "ki_monitor.py  ·  SCHEDULE.cmd", "변경 없음. 07:30 · 08:50 · 16:10 자동 실행도 그대로", "손대지 않는다", DIM],
  ];
  layers.forEach((l, i) => {
    const y = 1.96 + i * 0.66;
    panel(s, { x: M, y, w: CW, h: 0.58, fill: PANEL, line: EDGE });
    s.addShape(pres.ShapeType.rect, { x: M + 0.14, y: y + 0.1, w: 0.84, h: 0.38, fill: { color: l[4] }, line: { type: "none" } });
    txt(s, l[0], { x: M + 0.14, y: y + 0.1, w: 0.84, h: 0.38, fontSize: 10.5, bold: true, color: "0D1018", align: "center", valign: "middle" });
    txt(s, l[1], { x: M + 1.12, y, w: 3.9, h: 0.58, fontSize: 12, bold: true, color: INK, valign: "middle" });
    txt(s, l[2], { x: M + 5.1, y, w: 4.6, h: 0.58, fontSize: 9.5, color: MUT, valign: "middle" });
    mono(s, l[3], { x: M + 9.78, y, w: 2.28, h: 0.58, fontSize: 9, bold: true, color: l[4], align: "right", valign: "middle" });
  });

  panel(s, { x: M, y: 6.62, w: CW, h: 0.5, fill: PANEL3, line: EDGE });
  txt(s, [
    { text: "실제로 들어간 것 — agents/ 파이썬 16개 · 데스크 정의 9 · 스킬 5 · 자체 검사 339개. ", options: { bold: true, color: GRN } },
    { text: "기존 코드 변경은 0줄이다. ki_monitor.py 는 열지 않았다.", options: { color: INK } },
  ], { x: M + 0.26, y: 6.62, w: CW - 0.52, h: 0.5, fontSize: 10.5, valign: "middle", fontFace: F, isTextBox: true, margin: 0 });
}

/* ── NEW: MCP 서버 설계 ── */
function sMcp() {
  const s = slide();
  header(s, "PART 5 · MCP DESIGN", "ki-ledger — 벽이 실제로 세워지는 곳",
         "노출하는 도구가 곧 권한이다. 아래 열 개 외에는 존재하지 않으므로, 에이전트는 원장을 고칠 방법 자체가 없다.");

  const rows = [
    ["universe", "market · limit", "한 시장의 상장종목 목록"],
    ["facts", "code", "가장 최근 측정값 한 줄 (종가 기준)"],
    ["price_series", "code · start · end", "일봉 시계열 (오름차순)"],
    ["fundamentals", "code · period", "DART 재무 항목 · 기준일은 보고서 기간"],
    ["disclosures", "code · since", "DART 공시 목록 + 접수번호"],
    ["index_series", "index_name", "지수 일봉"],
    ["macro", "key · limit", "한국은행 ECOS · FRED 시계열"],
    ["staleness", "market", "원장이 며칠 뒤처졌는가"],
    ["papers", "key · state", "논문 장부 — 인용 가능 여부 · 붙는 표시"],
  ];
  const head = ["MCP 도구", "인자", "반환", "쓰기"].map((h, i) => ({
    text: h, options: { bold: true, color: AMB, fill: { color: PANEL2 }, fontSize: 10.5, valign: "middle",
                        fontFace: FM, align: i === 3 ? "center" : "left" },
  }));
  const body = [head];
  rows.forEach((r, i) => {
    const bg = i % 2 ? PANEL3 : PANEL;
    body.push([
      { text: r[0], options: { fontFace: FM, bold: true, color: i === 8 ? CYN : GRN, fontSize: 10, valign: "middle", fill: { color: bg } } },
      { text: r[1], options: { fontFace: FM, color: DIM, fontSize: 9.5, valign: "middle", fill: { color: bg } } },
      { text: r[2], options: { color: INK, fontSize: 9.5, valign: "middle", fill: { color: bg } } },
      { text: "✕", options: { bold: true, color: MAG, fontSize: 12, align: "center", valign: "middle", fill: { color: bg } } },
    ]);
  });
  s.addTable(body, {
    x: M, y: 1.94, w: 7.62, colW: [1.92, 2.28, 2.62, 0.8],
    border: { type: "solid", color: EDGE, pt: 1 },
    fontFace: F, rowH: 0.43, margin: 0.08, autoPage: false,
  });

  panel(s, { x: 8.42, y: 1.94, w: 4.31, h: 1.9, fill: "24141B", line: "5C2A3A" });
  txt(s, "노출하지 않는 것", { x: 8.66, y: 2.12, w: 3.8, h: 0.3, fontSize: 13, bold: true, color: MAG });
  ["ingest · catchup · fundamentals", "macro-us · import-keys · migrate-keys", "watch · live · eod (알림 발송)", "KIS 주문 계열 전부"].forEach((t, i) => {
    s.addImage({ data: img("ic_no"), x: 8.66, y: 2.52 + i * 0.31, w: 0.16, h: 0.16 });
    txt(s, t, { x: 8.92, y: 2.48 + i * 0.31, w: 3.6, h: 0.26, fontSize: 10, color: INK });
  });

  panel(s, { x: 8.42, y: 4.00, w: 4.31, h: 1.44, fill: PANEL, line: GRN });
  txt(s, "data-ops 는 예외다", { x: 8.66, y: 4.16, w: 3.8, h: 0.3, fontSize: 13, bold: true, color: GRN });
  txt(s, "원장운영역만 MCP 가 아니라 Bash 로 ki_monitor.py 를 직접 부른다. 대신 이 데스크에는 해석을 쓰는 권한이 없고, 산출물은 '적재 결과'와 '품질 경고'뿐이다.", {
    x: 8.66, y: 4.50, w: 3.86, h: 0.86, fontSize: 9.5, color: MUT });

  panel(s, { x: 8.42, y: 5.60, w: 4.31, h: 1.26, fill: PANEL2, line: EDGE });
  txt(s, "네트워크를 쓰지 않는다", { x: 8.66, y: 5.76, w: 3.8, h: 0.3, fontSize: 12.5, bold: true, color: GLD });
  txt(s, "열 도구 전부 읽기다. 오래됐으면 stale_days 로 알릴 뿐, 몰래 새로 받아오지 않는다. papers 는 원장이 아니라 논문 장부를 읽으므로 등급이 '방법론' 이다.", {
    x: 8.66, y: 6.08, w: 3.86, h: 0.7, fontSize: 9.5, color: MUT });
  foot(s, "// 세 겹으로 막는다 — 쓰기 도구가 없다 · 연결이 mode=ro 다 · 생 SQL 을 받지 않는다. stdout 은 JSON 만, 진단은 stderr.");
}

/* ── NEW: 리스크 레지스터 ── */
function sRisk() {
  const s = slide();
  header(s, "PART 5 · RISK REGISTER", "리스크와 완화",
         "가장 큰 위험은 에이전트가 틀리는 것이 아니라, 틀린 것이 맞는 것처럼 회의에 올라가는 것이다.");

  const risks = [
    ["높음", "환각 — 없는 값 생성", "원장에 없는 값을 그럴듯하게 채우는 것이 LLM 의 기본 실패 양식이다. 0 으로 채우는 것보다 나쁘다.", "봉투 스키마가 null 을 허용하고 근거 필드를 필수로 한다 + 게이트 ⑤ 신선도", MAG],
    ["높음", "등급 혼입 — 해석이 사실로", "에이전트 문장이 §5 표에서 측정값과 같은 무게로 읽히면, 이 도구가 막으려던 실패가 재현된다.", "'해석' 등급 신설 + 게이트 ② + 리포트에서 별도 블록으로 분리 렌더", AMB],
    ["높음", "재현 관문의 과신", "재현됐다고 인과가 성립하는 것은 아니다. 표본 구간을 바꾸면 판정이 뒤집힐 수 있다.", "판정에 표본 구간·n 을 항상 붙이고, 반감기마다 재검해 변화 자체를 기록한다", ORG],
    ["치명·비가역", "원장 오염", "추정치가 ki.sqlite 에 한 번 들어가면 다음 측정이 오염되고 되돌릴 수 없다.", "MCP 에 쓰기 도구 미노출 + data-ops 단독 권한 + PreToolUse 훅 차단", PUR],
    ["중", "유사투자자문 규제", "권고 · 목표가를 생성하는 순간 산출물의 성격이 바뀐다.", "권고 미생성 원칙 유지 + 배포통제 배너(STAGE) + 내부 검토용 고지 유지", CYN],
    ["중", "비용 · 지연", "이벤트가 몰린 날에는 인스턴스가 급증한다 (시뮬 피크 95).", "T1~T3 등급 분리 · 인스턴스별 예산 상한 · 17:00 배치로 몰아서 실행", GRN],
    ["높음", "합성 검증의 자기확인", "표를 만드는 쪽과 읽는 쪽이 같은 가정을 쓰면 둘 다 틀려도 통과한다. 검사 240개가 통과하는 동안 판단층은 진짜 원장에서 한 줄도 못 읽고 있었다.", "원장은 \"20260917\" · \"코스닥\" 이다 — dialect.py 가 짐작하지 않고 물어본다 + 합성 원장도 진짜 형식으로 + audit [11] 이 영문 이름을 금지", AMB],
  ];
  const head = ["등급", "리스크", "무엇이 문제인가", "완화"].map((h, i) => ({
    text: h, options: { bold: true, color: AMB, fill: { color: PANEL2 }, fontSize: 10.5, valign: "middle",
                        fontFace: FM, align: i === 0 ? "center" : "left" },
  }));
  const body = [head];
  risks.forEach((r, i) => {
    const bg = i % 2 ? PANEL3 : PANEL;
    body.push([
      { text: r[0], options: { bold: true, color: "0D1018", fill: { color: r[4] }, fontSize: 9.5, align: "center", valign: "middle" } },
      { text: r[1], options: { bold: true, color: r[4], fontSize: 10.5, valign: "middle", fill: { color: bg } } },
      { text: r[2], options: { color: INK, fontSize: 9, valign: "middle", fill: { color: bg } } },
      { text: r[3], options: { color: MUT, fontSize: 9, valign: "middle", fill: { color: bg } } },
    ]);
  });
  s.addTable(body, {
    x: M, y: 1.90, w: CW, colW: [1.14, 2.32, 4.52, 4.11],
    border: { type: "solid", color: EDGE, pt: 1 },
    fontFace: F, rowH: 0.545, margin: 0.06, autoPage: false,
  });

  panel(s, { x: M, y: 6.30, w: CW, h: 0.56, fill: PANEL3, line: EDGE });
  txt(s, [
    { text: "자격증명 — ", options: { bold: true, color: GLD } },
    { text: "원본 압축본의 env.txt 에 6종 키가 평문으로 있었다. 파일명이 .env 가 아니어서 기존 .gitignore 어떤 규칙에도 걸리지 않는다. 저장소에는 넣지 않았고 규칙을 추가했다.", options: { color: INK } },
  ], { x: M + 0.26, y: 6.30, w: CW - 0.52, h: 0.56, fontSize: 10.5, valign: "middle", fontFace: F, isTextBox: true, margin: 0 });
}

/* ── NEW: 부록 — 파일 배치 ── */
function sAppendix() {
  const s = slide();
  header(s, "APPENDIX", "저장소에 추가되는 것 — 파일 배치",
         "기존 파일은 하나도 옮기지 않는다. 아래는 전부 새로 생기는 경로다.");

  panel(s, { x: M, y: 1.90, w: 6.7, h: 4.95, fill: "0A1020", line: EDGE });
  mono(s, [
    'Stock_Agent/',
    '├─ stock-monitor/        ki_monitor.py 변경 0줄 · .papers.json v2',
    '├─ docs/                 audit.py 에 정의 대조 [10] · 원장 방언 [11]',
    '├─ RUN_ALL · SCHEDULE    월 07:40 주간 재현 한 줄 추가',
    '│',
    '├─ agents/               ← 들어감 (자체 검사 339개)',
    '│   ├─ dialect.py           원장의 말 (형식을 묻는다)  15',
    '│   ├─ scope.py             상장 포트폴리오사 범위      8',
    '│   ├─ watch.py             주가 모니터링 (매일)       20',
    '│   ├─ envelope.py          봉투 스키마 · 검증기      28',
    '│   ├─ papers.py            논문 장부 ki.papers/2    23',
    '│   ├─ replication.py       분위 러너 (달력 시간)    29',
    '│   ├─ eventstudy.py        이벤트 러너 (사건 시간)   19',
    '│   ├─ gates.py             게이트 ①~⑦ 검사기     20',
    '│   ├─ ki_ledger_mcp.py     MCP 서버 · 읽기 10종   34',
    '│   ├─ dispatch.py          지시서 발급 · 회수 대조    12',
    '│   ├─ selftest.py          열여섯 개를 한 번에',
    '│   ├─ triggers.py          트리거 스캐너 · 소집      32',
    '│   ├─ cycle.py             주간 논문 사이클         14',
    '│   ├─ run_day.py           소집 · 발행 · 승격        38',
    '│   ├─ reconcile.py         데스크 간 대조            15',
    '│   ├─ scorecard.py         계측 (고치지는 않는다)    16',
    '│   └─ replay.py            되짚기 · 원장 대조         15',
    '│',
    '└─ .claude/',
    '    ├─ agents/              데스크 9개 정의',
    '    │   ├─ q1-progress.md    q2-disposal.md',
    '    │   ├─ q3-execution.md   q4-timing.md',
    '    │   ├─ quant-method.md   risk-officer.md',
    '    │   ├─ compliance-officer.md',
    '    │   └─ data-ops.md       ic-chair.md',
    '    ├─ skills/              규칙 5종',
    '    │   ├─ source-grading/     등급 판정 기준',
    '    │   ├─ envelope-schema/    봉투 작성법',
    '    │   ├─ replication/        재현 설계 · 판정',
    '    │   ├─ paper-adoption/     채택 · 감가 · 은퇴',
    '    │   └─ compliance-gate/    게이트 판정 기준',
    '    └─ settings.json        훅 · MCP 등록',
  ].join("\n"), { x: M + 0.22, y: 2.02, w: 6.3, h: 4.71, fontSize: 7.6, color: "A9C8F0", lineSpacing: 9.5, valign: "top" });

  const notes = [
    ["ki_monitor.py 는 열지 않는다", "CRLF 파일이라 편집 도구가 줄바꿈을 바꾸면 파일 전체가 diff 에 잡힌다. 감싸기만 하고 손대지 않는 이유이기도 하다.", GRN],
    ["재현 러너는 에이전트가 아니다", "결정적 파이썬 코드다. 같은 원장·같은 구간이면 항상 같은 판정이 나와야 하므로 LLM 을 쓰지 않는다.", CYN],
    ["게이트는 selftest 와 나란히 돈다", "python agents/gates.py --selftest 를 기존 128개 옆에 붙인다. 검증은 한 곳에서 돌아야 실제로 돌아간다.", AMB],
    ["대외비 규칙은 확장한다", "데스크 산출 봉투도 포트폴리오사 실명을 담는다. out/ 과 같은 등급으로 .gitignore 에 넣는다.", MAG],
  ];
  notes.forEach((n, i) => {
    const y = 1.90 + i * 1.18;
    panel(s, { x: 7.52, y, w: 5.21, h: 1.06, fill: PANEL, line: EDGE });
    s.addShape(pres.ShapeType.rect, { x: 7.74, y: y + 0.2, w: 0.14, h: 0.14, fill: { color: n[2] }, line: { type: "none" } });
    txt(s, n[0], { x: 8.0, y: y + 0.12, w: 4.5, h: 0.3, fontSize: 12, bold: true, color: n[2] });
    txt(s, n[1], { x: 7.74, y: y + 0.44, w: 4.76, h: 0.56, fontSize: 9.5, color: MUT });
  });
  foot(s, "// 실제로 들어갔다 — agents/ 파이썬 16 · 데스크 정의 9 · 스킬 5 · 자체 검사 339개 · ki_monitor.py 변경 0줄");
}







function sRefix() {
  const s = slide();
  header(s, "PART 1 · ★ 이미 재고 있는 것 — 리픽싱", "리픽싱 — 주가가 더 내리면 희석이 얼마나 가속되는가",
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

function sNotExRight() {
  const s = slide();
  header(s, "PART 1 · ★★ 이미 재고 있는 것 — 희석 ≠ 권리락", "희석은 권리락이 아니다 — 수정주가를 조정하면 안 된다",
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

function sLiquidity() {
  const s = slide();
  header(s, "PART 1 · 이미 재고 있는 것 — 처분 여건", "처분 소요일수 — 평균과 중앙값을 나란히 낸다",
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


/* ═══ 시스템 한 장 — 목차를 겸한다 ═══ */
function sSystemMap() {
  const s = slide();
  header(s, "THE WHOLE THING", "한 장으로 — 무엇이 어디로 흐르는가",
         "이 한 장만 보셔도 됩니다. 각 블록에 붙은 PART 가 그것을 설명하는 곳입니다.");

  /* ① 측정층 */
  panel(s, { x: M, y: 2.02, w: 3.3, h: 2.72, fill: PANEL, line: GRN });
  s.addShape(pres.ShapeType.rect, { x: M, y: 2.02, w: 3.3, h: 0.36, fill: { color: GRN }, line: { type: "none" } });
  mono(s, "① 측정층", { x: M + 0.14, y: 2.02, w: 1.6, h: 0.36, fontSize: 10.5, bold: true, color: "0D1018", valign: "middle" });
  mono(s, "PART 1", { x: M + 1.9, y: 2.02, w: 1.26, h: 0.36, fontSize: 9, bold: true, color: "0D1018", align: "right", valign: "middle" });
  mono(s, "KRX · DART · ECOS · KIS · FRED", { x: M + 0.16, y: 2.5, w: 3.0, h: 0.24, fontSize: 9, color: MUT });
  mono(s, "▼  16:10 · ingest-ops 단독", { x: M + 0.16, y: 2.76, w: 3.0, h: 0.24, fontSize: 9, bold: true, color: AMB });
  s.addImage({ data: img("ob_db"), x: M + 0.18, y: 3.06, w: 0.54, h: 0.54 });
  txt(s, "ki.sqlite 원장", { x: M + 0.82, y: 3.1, w: 2.3, h: 0.3, fontSize: 14, bold: true, color: INK });
  mono(s, "7 tables · 사실만", { x: M + 0.82, y: 3.4, w: 2.3, h: 0.22, fontSize: 8.5, color: MUT });
  mono(s, "▼", { x: M + 0.16, y: 3.68, w: 3.0, h: 0.2, fontSize: 9, color: DIM });
  panel(s, { x: M + 0.16, y: 3.92, w: 2.98, h: 0.66, fill: PANEL2, line: null, off: 0 });
  txt(s, "측정 함수 — 계산은 여기서 끝난다", { x: M + 0.28, y: 3.96, w: 2.76, h: 0.26, fontSize: 9.5, bold: true, color: GRN });
  mono(s, "리픽싱 · 완전희석 · 처분소요일 · 집행시뮬", { x: M + 0.28, y: 4.22, w: 2.78, h: 0.24, fontSize: 7.6, color: MUT });

  /* 벽 */
  for (let i = 0; i < 5; i++) s.addImage({ data: img("ob_wall"), x: 4.04, y: 2.02 + i * 0.545, w: 0.56, h: 0.56 });
  s.addShape(pres.ShapeType.rect, { x: 3.92, y: 3.06, w: 0.8, h: 0.62, fill: { color: "0D1018" }, line: { color: AMB, width: 1.25 } });
  mono(s, "READ\nONLY", { x: 3.92, y: 3.06, w: 0.8, h: 0.62, fontSize: 8.5, bold: true, color: AMB, align: "center", valign: "middle", lineSpacing: 10 });
  mono(s, "MCP 8", { x: 3.86, y: 4.78, w: 0.92, h: 0.22, fontSize: 8, bold: true, color: AMB, align: "center" });

  /* ② 판단층 */
  panel(s, { x: 4.86, y: 2.02, w: 3.54, h: 2.72, fill: PANEL, line: BLU });
  s.addShape(pres.ShapeType.rect, { x: 4.86, y: 2.02, w: 3.54, h: 0.36, fill: { color: BLU }, line: { type: "none" } });
  mono(s, "② 판단층", { x: 5.0, y: 2.02, w: 1.6, h: 0.36, fontSize: 10.5, bold: true, color: "0D1018", valign: "middle" });
  mono(s, "PART 3", { x: 6.9, y: 2.02, w: 1.36, h: 0.36, fontSize: 9, bold: true, color: "0D1018", align: "right", valign: "middle" });
  txt(s, "데스크 9", { x: 5.02, y: 2.46, w: 3.2, h: 0.32, fontSize: 15, bold: true, color: INK });
  mono(s, "상설 3  +  이벤트 소집 6", { x: 5.02, y: 2.8, w: 3.2, h: 0.22, fontSize: 9, color: MUT });
  const units = [["q1 진척", CYN], ["q2 처분", GRN], ["q3 집행", AMB], ["q4 시점", MAG], ["계량 · 검산", PUR], ["준법 · 원장 · 간사", ORG]];
  units.forEach((u, i) => {
    const x = 5.02 + (i % 3) * 1.1, y = 3.12 + Math.floor(i / 3) * 0.36;
    s.addShape(pres.ShapeType.rect, { x, y, w: 1.02, h: 0.3, fill: { color: PANEL2 }, line: { type: "none" } });
    s.addShape(pres.ShapeType.rect, { x, y, w: 0.07, h: 0.3, fill: { color: u[1] }, line: { type: "none" } });
    mono(s, u[0], { x: x + 0.14, y, w: 0.86, h: 0.3, fontSize: 7.4, bold: true, color: INK, valign: "middle" });
  });
  panel(s, { x: 5.02, y: 3.92, w: 3.22, h: 0.66, fill: "1A1428", line: null, off: 0 });
  txt(s, "봉투 제출 — 등급 '해석'", { x: 5.14, y: 3.96, w: 3.0, h: 0.26, fontSize: 9.5, bold: true, color: PUR });
  mono(s, "계산하지 않는다 · 읽고 서술한다", { x: 5.14, y: 4.22, w: 3.0, h: 0.24, fontSize: 7.6, color: MUT });

  s.addImage({ data: img("ar_am"), x: 8.46, y: 3.24, w: 0.32, h: 0.2 });

  /* ③ 통제 */
  panel(s, { x: 8.86, y: 2.02, w: 2.2, h: 2.72, fill: PANEL, line: MAG });
  s.addShape(pres.ShapeType.rect, { x: 8.86, y: 2.02, w: 2.2, h: 0.36, fill: { color: MAG }, line: { type: "none" } });
  mono(s, "③ 통제", { x: 9.0, y: 2.02, w: 1.1, h: 0.36, fontSize: 10.5, bold: true, color: "0D1018", valign: "middle" });
  mono(s, "PART 4", { x: 9.6, y: 2.02, w: 1.32, h: 0.36, fontSize: 9, bold: true, color: "0D1018", align: "right", valign: "middle" });
  s.addImage({ data: img("ob_gate"), x: 9.02, y: 2.5, w: 0.44, h: 0.44 });
  txt(s, "게이트 ×7", { x: 9.56, y: 2.54, w: 1.4, h: 0.32, fontSize: 14, bold: true, color: INK });
  ["판정 어휘", "출처 등급", "★ 재현", "논문 실재", "신선도", "유출 검사", "4-eyes"].forEach((t, i) => {
    mono(s, (i + 1) + "  " + t, { x: 9.02, y: 3.1 + i * 0.22, w: 1.9, h: 0.2, fontSize: 7.6,
      color: t.indexOf("★") === 0 ? GRN : MUT });
  });

  s.addImage({ data: img("ar_am"), x: 11.12, y: 3.24, w: 0.32, h: 0.2 });

  /* ④ 의결 */
  panel(s, { x: 11.52, y: 2.02, w: 1.21, h: 2.72, fill: PANEL, line: GLD });
  s.addShape(pres.ShapeType.rect, { x: 11.52, y: 2.02, w: 1.21, h: 0.36, fill: { color: GLD }, line: { type: "none" } });
  mono(s, "④ 의결", { x: 11.52, y: 2.02, w: 1.21, h: 0.36, fontSize: 9.5, bold: true, color: "0D1018", align: "center", valign: "middle" });
  s.addImage({ data: img("ag_chair"), x: 11.82, y: 2.56, w: 0.6, h: 0.6 });
  txt(s, "투자\n심의\n위원회", { x: 11.58, y: 3.26, w: 1.1, h: 0.8, fontSize: 11, bold: true, color: INK, align: "center", lineSpacing: 15 });
  mono(s, "사람이\n결정한다", { x: 11.58, y: 4.12, w: 1.1, h: 0.5, fontSize: 8, color: GLD, align: "center", lineSpacing: 10 });

  /* 논문 원장 — 아래에서 판단층으로 */
  panel(s, { x: 4.86, y: 5.0, w: 3.54, h: 0.86, fill: PANEL, line: PUR });
  s.addImage({ data: img("ob_paper"), x: 5.02, y: 5.16, w: 0.38, h: 0.38 });
  txt(s, "논문 원장 — 재현 통과분만 인용 가능", { x: 5.5, y: 5.12, w: 2.8, h: 0.28, fontSize: 10.5, bold: true, color: PUR });
  mono(s, "ki.papers/2 · adopted | warned | retired", { x: 5.5, y: 5.42, w: 2.82, h: 0.22, fontSize: 7.6, color: MUT });
  mono(s, "PART 2", { x: 7.5, y: 5.6, w: 0.8, h: 0.22, fontSize: 8, bold: true, color: PUR, align: "right" });
  mono(s, "▲", { x: 5.02, y: 4.78, w: 0.4, h: 0.2, fontSize: 9, color: PUR });

  /* 좌우 보조 설명 */
  panel(s, { x: M, y: 5.0, w: 3.3, h: 0.86, fill: PANEL3, line: EDGE });
  txt(s, "여기서만 네트워크를 쓴다", { x: M + 0.16, y: 5.08, w: 3.0, h: 0.26, fontSize: 10, bold: true, color: GRN });
  txt(s, "하루 한 번, ingest-ops 하나. 그날의 유일한 원장 쓰기다.", { x: M + 0.16, y: 5.34, w: 3.02, h: 0.44, fontSize: 8.6, color: MUT });

  panel(s, { x: 8.86, y: 5.0, w: 3.87, h: 0.86, fill: PANEL3, line: EDGE });
  txt(s, "하나라도 걸리면 멈춘다", { x: 9.02, y: 5.08, w: 3.5, h: 0.26, fontSize: 10, bold: true, color: MAG });
  txt(s, "반려된 절은 빈칸이 아니라 '반려됨 — 사유' 로 회의자료에 남는다.", { x: 9.02, y: 5.34, w: 3.56, h: 0.44, fontSize: 8.6, color: MUT });

  panel(s, { x: M, y: 6.06, w: CW, h: 0.76, fill: PANEL3, line: EDGE });
  txt(s, [
    { text: "읽는 방향은 왼쪽에서 오른쪽, 한 방향뿐입니다. ", options: { bold: true, color: GLD } },
    { text: "해석이 원장으로 되돌아가는 경로는 스키마에도 도구에도 없습니다.\n", options: { color: INK } },
    { text: "PART 5 는 이 그림을 무엇으로 만드는가(기술 스택 · MCP 설계 · 하루 운영 · 로드맵)를 다룹니다.", options: { color: MUT } },
  ], { x: M + 0.26, y: 6.06, w: CW - 0.52, h: 0.76, fontSize: 10.5, valign: "middle", lineSpacing: 17, fontFace: F, isTextBox: true, margin: 0 });
}

/* ═══ 데이터 조달 — 에이전트는 API 를 부르지 않는다 ═══ */
function sSourcing() {
  const s = slide();
  header(s, "PART 3 · WHERE THE DATA COMES FROM", "에이전트는 API 를 부르지 않는다",
         "에이전트가 쓰는 것은 API 가 아니라 API 가 가져다 놓은 것이다. 네트워크 호출과 판단은 시각이 다르다.");

  /* 위: 16:10 */
  panel(s, { x: M, y: 1.88, w: CW, h: 1.44, fill: "13241A", line: GRN });
  s.addShape(pres.ShapeType.rect, { x: M, y: 1.88, w: 1.5, h: 1.44, fill: { color: GRN }, line: { type: "none" } });
  mono(s, "16:10", { x: M, y: 1.96, w: 1.5, h: 0.4, fontSize: 18, bold: true, color: "0D1018", align: "center" });
  mono(s, "네트워크\n있음", { x: M, y: 2.42, w: 1.5, h: 0.5, fontSize: 9, bold: true, color: "0D1018", align: "center", lineSpacing: 11 });
  txt(s, "ingest-ops 단독 — 그날의 유일한 원장 쓰기", {
    x: M + 1.7, y: 2.0, w: 6.0, h: 0.3, fontSize: 13.5, bold: true, color: GRN });
  mono(s, "KRX · DART · ECOS · KIS · FRED   ──→   ki.sqlite", {
    x: M + 1.7, y: 2.36, w: 6.4, h: 0.26, fontSize: 10.5, color: INK });
  txt(s, "이때 받은 값이 기준일로 고정된다. 이후 모든 데스크가 같은 원장을 본다.", {
    x: M + 1.7, y: 2.68, w: 6.4, h: 0.44, fontSize: 9.5, color: MUT });
  ["price_daily", "index_daily", "instruments", "disclosure", "fundamental", "macro_daily", "alert_log"].forEach((t, i) => {
    const x = 8.4 + (i % 2) * 2.16, y = 2.02 + Math.floor(i / 2) * 0.3;
    mono(s, "· " + t, { x, y, w: 2.1, h: 0.26, fontSize: 8.2, color: MUT });
  });

  mono(s, "════════════════════  하루의 경계  ════════════════════", {
    x: M, y: 3.44, w: CW, h: 0.24, fontSize: 9, bold: true, color: DIM, align: "center" });

  /* 아래: 17:00 */
  panel(s, { x: M, y: 3.8, w: CW, h: 1.62, fill: PANEL, line: BLU });
  s.addShape(pres.ShapeType.rect, { x: M, y: 3.8, w: 1.5, h: 1.62, fill: { color: BLU }, line: { type: "none" } });
  mono(s, "17:00", { x: M, y: 3.92, w: 1.5, h: 0.4, fontSize: 18, bold: true, color: "0D1018", align: "center" });
  mono(s, "네트워크\n없음", { x: M, y: 4.38, w: 1.5, h: 0.5, fontSize: 9, bold: true, color: "0D1018", align: "center", lineSpacing: 11 });
  txt(s, "데스크 19개 — 원장만 읽는다", { x: M + 1.7, y: 3.94, w: 5.0, h: 0.3, fontSize: 13.5, bold: true, color: BLU });
  const tools = ["facts", "price_series", "price_series", "calendar",
                 "macro", "disclosures", "staleness", "papers"];
  tools.forEach((t, i) => {
    const x = M + 1.7 + (i % 4) * 2.62, y = 4.32 + Math.floor(i / 4) * 0.34;
    s.addShape(pres.ShapeType.rect, { x, y, w: 2.5, h: 0.28, fill: { color: PANEL2 }, line: { type: "none" } });
    mono(s, t, { x: x + 0.1, y, w: 2.3, h: 0.28, fontSize: 8.4, bold: true, color: GRN, valign: "middle" });
  });
  txt(s, "계산은 이미 끝나 있다 — 데스크는 읽고 서술할 뿐, 숫자를 만들지 않는다.", {
    x: M + 1.7, y: 5.04, w: 10.2, h: 0.3, fontSize: 9.5, italic: true, color: MUT });

  /* 예외 · 이유 */
  panel(s, { x: M, y: 5.62, w: 4.5, h: 1.2, fill: "241E10", line: AMB });
  txt(s, "유일한 예외 — DART 원문", { x: M + 0.2, y: 5.74, w: 4.1, h: 0.28, fontSize: 11.5, bold: true, color: AMB });
  txt(s, "원장에는 접수번호와 제목까지만 있다. 발행조건·전환가·리픽싱 조항은 원문에 있으므로, 접수번호로 지정된 그 문서 한 건만 연다. 검색이 아니라 지정 조회다.", {
    x: M + 0.2, y: 6.04, w: 4.14, h: 0.7, fontSize: 8.8, color: INK });

  const why = [["재생 가능", "같은 입력 → 같은 봉투"], ["기준일 고정", "모든 데스크가 같은 날을 본다"],
               ["오염 차단", "장중 값이 일봉에 안 섞인다"], ["감사 가능", "언제 어디서 왔는지 남는다"]];
  why.forEach((w, i) => {
    const x = 5.32 + (i % 2) * 3.74, y = 5.62 + Math.floor(i / 2) * 0.62;
    panel(s, { x, y, w: 3.6, h: 0.54, fill: PANEL3, line: EDGE });
    s.addImage({ data: img("ic_ok"), x: x + 0.14, y: y + 0.19, w: 0.16, h: 0.16 });
    mono(s, w[0], { x: x + 0.38, y, w: 1.1, h: 0.54, fontSize: 9, bold: true, color: GRN, valign: "middle" });
    txt(s, w[1], { x: x + 1.5, y, w: 2.0, h: 0.54, fontSize: 8.6, color: MUT, valign: "middle" });
  });

  mono(s, "숫자는 원장에서, 원문은 링크로.", {
    x: 5.32, y: 6.88, w: 7.4, h: 0.26, fontSize: 10.5, bold: true, color: GLD, align: "center" });
}


/* ═══ 구현 규격 — 코드로 옮기기 전에 정할 값 ═══ */
function sSpec() {
  const s = slide();
  header(s, "PART 5 · IMPLEMENTATION SPEC", "확정값 — 코드가 이것을 지킨다",
         "제안이 아니다. 아래 값은 agents/ 에 들어가 있고, 문서와 코드가 어긋나면 docs/audit.py 가 잡는다.");

  /* ① 재현 관문 */
  panel(s, { x: M, y: 1.86, w: 6.1, h: 2.42, fill: PANEL, line: GRN });
  mono(s, "① 재현 관문 — 판정 기준", { x: M + 0.2, y: 1.98, w: 5.6, h: 0.26, fontSize: 11, bold: true, color: GRN });
  const rep = [
    [2.30, "유니버스",  "market 인자로 받는다 (기본 KOSDAQ). 종목·월 단위로 거른다", 0.28],
    [2.58, "최소 표본", "종목 n ≥ 100 · 유효 월 ≥ 36 (미달 시 계산 거부)", 0.28],
    [2.86, "포트폴리오", "팩터값 5분위 · 월말 리밸런싱 · 동일가중 · rank 로 동값 처리", 0.28],
    [3.14, "검정 통계", "분위: Q5−Q1 · NW t  |  이벤트: 긴 구간 달력시간 NW · 짧은 창 횡단면", 0.28],
    [3.44, "판정",      "|t| ≥ 3.0 & 부호 일치 → 재현됨 · 부호 반대 → 방향 반대\n|t| < 3.0                        → 판정 불가", 0.40],
    [3.90, "재검 순번", "recheck_due 오래된 순 · 주 ≤3편. 트리거와 같은 함수를 쓴다", 0.28],
  ];
  rep.forEach(r => {
    mono(s, r[1], { x: M + 0.2, y: r[0], w: 1.3, h: 0.26, fontSize: 8.6, bold: true, color: CYN });
    mono(s, r[2], { x: M + 1.56, y: r[0] - 0.01, w: 4.42, h: r[3], fontSize: 8.2, color: INK, lineSpacing: 10.5 });
  });

  /* ② 트리거 임계값 */
  panel(s, { x: 6.86, y: 1.86, w: 5.87, h: 2.42, fill: PANEL, line: AMB });
  mono(s, "② 트리거 임계값", { x: 7.06, y: 1.98, w: 5.4, h: 0.26, fontSize: 11, bold: true, color: AMB });
  const trg = [
    ["DART 신규 공시", "제목·태그로 q2 · q1 · q4 로 분기 (T1)"],
    ["종가 급변", "|일간수익률| ≥ 8% · 종목당 1회"],
    ["락업 만료 임박", "상장일 + 6개월, D-30 영업일 진입"],
    ["거시 갱신", "macro_daily 최신일 > 감시선 · 하루 1회"],
    ["재검 기한 도래", "주 ≤3편 (T3) · 은퇴본은 제외"],
    ["주간 사이클", "월 07:40 · RUN_ALL.cmd cycle"],
    ["신선도 경보", "stale_days > 3 영업일 → 게이트 ⑤ 반려"],
  ];
  trg.forEach((t, i) => {
    const y = 2.32 + i * 0.27;
    s.addShape(pres.ShapeType.rect, { x: 7.06, y, w: 5.5, h: 0.23, fill: { color: i % 2 ? PANEL3 : PANEL2 }, line: { type: "none" } });
    txt(s, t[0], { x: 7.16, y, w: 1.9, h: 0.23, fontSize: 8.4, bold: true, color: INK, valign: "middle" });
    mono(s, t[1], { x: 9.1, y, w: 3.4, h: 0.23, fontSize: 8, color: MUT, valign: "middle" });
  });

  /* ③ 봉투 필수 필드 */
  panel(s, { x: M, y: 4.44, w: 6.1, h: 2.06, fill: PANEL, line: PUR });
  mono(s, "③ 봉투 — 필수 필드 (게이트가 검사)", { x: M + 0.2, y: 4.56, w: 5.6, h: 0.26, fontSize: 11, bold: true, color: PUR });
  mono(s, [
    'required: claim · asof · source_grade · limits[] ·',
    '          desk · instance',
    '',
    'value 가 있으면  → unit 필수 · read[] 필수',
    'value 가 null 이면 → reason 필수 (0 으로 채우지 않는다)',
    'method.paper 가 있으면 → paper_state 필수',
    '  replication 은 필수가 아니다 — unverified 는 아직 없다',
    '',
    'read[] = {source, key, value, asof}   ← 재생 가능성',
    '  못 읽은 값도 value:null 로 적는다',
  ].join("\n"), { x: M + 0.2, y: 4.88, w: 5.66, h: 1.5, fontSize: 8.2, color: "A9C8F0", lineSpacing: 11, valign: "top" });

  /* ④ 예산 · 판정 어휘 */
  panel(s, { x: 6.86, y: 4.44, w: 5.87, h: 2.06, fill: PANEL, line: MAG });
  mono(s, "④ 예산 상한 · 판정 어휘 차단 목록", { x: 7.06, y: 4.56, w: 5.4, h: 0.26, fontSize: 11, bold: true, color: MAG });
  [["T1 경량", "12K 토큰 · 도구 6회"], ["T2 표준", "40K · 18회"], ["T3 상위", "90K · 40회"]].forEach((t, i) => {
    const x = 7.06 + i * 1.9;
    s.addShape(pres.ShapeType.rect, { x, y: 4.9, w: 1.78, h: 0.44, fill: { color: PANEL2 }, line: { type: "none" } });
    mono(s, t[0], { x: x + 0.1, y: 4.92, w: 1.6, h: 0.2, fontSize: 8.2, bold: true, color: AMB });
    mono(s, t[1], { x: x + 0.1, y: 5.12, w: 1.62, h: 0.2, fontSize: 7.6, color: MUT });
  });
  mono(s, "초과 시 '미완' 으로 기록 — 조용히 넘어가지 않는다", {
    x: 7.06, y: 5.4, w: 5.4, h: 0.22, fontSize: 8, italic: true, color: DIM });
  mono(s, "게이트 ① 차단 어휘 (정규식)", { x: 7.06, y: 5.7, w: 5.4, h: 0.22, fontSize: 8.6, bold: true, color: MAG });
  mono(s, "매수 · 매도 · 저평가 · 고평가 · 추천 · 목표가 · 목표주가\n비중확대 · 비중축소 · 적정주가 · 투자의견 · 강력매수", {
    x: 7.06, y: 5.94, w: 5.44, h: 0.48, fontSize: 8, color: INK, lineSpacing: 11 });

  panel(s, { x: M, y: 6.64, w: CW, h: 0.46, fill: PANEL3, line: EDGE });
  txt(s, [
    { text: "임계 3.0 은 자연상수가 아니다. ", options: { bold: true, color: GLD } },
    { text: "보정 방식과 가정한 검정 횟수에 따라 달라지는 값이고, 재검 대상이다. 다만 한 번의 판정을 위해 낮추지 않는다 — 낮추려면 사람이 정한다.", options: { color: INK } },
  ], { x: M + 0.26, y: 6.64, w: CW - 0.52, h: 0.46, fontSize: 10, valign: "middle", fontFace: F, isTextBox: true, margin: 0 });
}


/* ═══ 질문이 데스크를 정한다 (CATALOG 가 아니라) ═══ */
function sQuestionMap() {
  const s = slide();
  header(s, "PART 3 · WHY NINE", "데스크는 네 질문이 정한다",
         "앞선 안은 CATALOG(무슨 데이터가 있나)에서 데스크를 뽑았다. 그건 데이터 목록이지 결정 목록이 아니다. 이 도구가 답해야 하는 것은 네 질문이다.");

  const qs = [
    ["q1", "얼마나 왔는가", "회수계획 대비 진척", "§1 오늘 달라진 것 · §5 재무 · §7 목표단가 갭 · §9 총수익률", "논문 3편", CYN],
    ["q2", "팔 수 있는가", "처분 여건 · 거래비용", "§2 집중도 · §6 자본구조 · §8 유동성 · §11 희석 · §13 사채 · §14 지분 · §15 감사", "논문 5편", GRN],
    ["q3", "어떻게 팔 것인가", "실행", "§3 집행 시뮬레이션", "논문 2편", AMB],
    ["q4", "지금이 그 때인가", "시점 · 국면", "§4 국면 · §12 공시 이벤트 · CAR · §18 이번 주 일정", "논문 2편", MAG],
  ];
  qs.forEach((q, i) => {
    const y = 1.94 + i * 0.86;
    panel(s, { x: M, y, w: CW, h: 0.74, fill: PANEL, line: EDGE });
    s.addShape(pres.ShapeType.rect, { x: M + 0.18, y: y + 0.16, w: 0.5, h: 0.42, fill: { color: q[5] }, line: { type: "none" } });
    mono(s, q[0], { x: M + 0.18, y: y + 0.16, w: 0.5, h: 0.42, fontSize: 13, bold: true, color: "0D1018", align: "center", valign: "middle" });
    txt(s, q[1], { x: M + 0.84, y: y + 0.1, w: 2.5, h: 0.3, fontSize: 13.5, bold: true, color: INK });
    txt(s, q[2], { x: M + 0.84, y: y + 0.4, w: 2.6, h: 0.26, fontSize: 9.5, color: q[5] });
    mono(s, q[3], { x: M + 3.6, y, w: 6.9, h: 0.74, fontSize: 8.4, color: MUT, valign: "middle" });
    mono(s, q[4], { x: M + 10.6, y, w: 1.3, h: 0.74, fontSize: 9, bold: true, color: q[5], align: "right", valign: "middle" });
  });

  panel(s, { x: M, y: 5.46, w: 6.1, h: 1.36, fill: "24141B", line: "5C2A3A" });
  txt(s, "앞선 안의 오류", { x: M + 0.2, y: 5.58, w: 5.7, h: 0.28, fontSize: 12, bold: true, color: MAG });
  txt(s, "CATALOG 31개 항목 → SECTIONS 18개 절 → 데스크 20개로 뽑았다. 데이터가 있는 만큼 데스크를 만든 셈이다. 그러면 §16 스코어카드처럼 네 질문 중 어느 것도 바꾸지 않는 절에도 담당이 생긴다.", {
    x: M + 0.2, y: 5.88, w: 5.74, h: 0.86, fontSize: 9.5, color: INK });

  panel(s, { x: 6.86, y: 5.46, w: 5.87, h: 1.36, fill: "16281C", line: "2A5A3A" });
  txt(s, "고친 방식", { x: 7.06, y: 5.58, w: 5.4, h: 0.28, fontSize: 12, bold: true, color: GRN });
  txt(s, "질문 하나에 데스크 하나. 절은 질문에 딸려 온다. 논문도 이미 네 질문으로 태그돼 있다(.papers.json 의 question 필드) — 코드가 처음부터 이 구조였고, 조직도만 딴 데서 뽑았던 것이다.", {
    x: 7.06, y: 5.88, w: 5.5, h: 0.86, fontSize: 9.5, color: INK });
}

/* ═══ 목표 조직도 — 9 데스크 ═══ */
function sOrg() {
  const s = slide();
  header(s, "PART 3 · TARGET ORG", "아홉 데스크 — 질문 넷 · 방법론 하나 · 통제 셋 · 간사 하나",
         "회의 자료 한 장을 만드는 데 필요한 최소 분업이다. 늘리는 것은 쉽고, 늘린 만큼 조정 비용이 든다.");

  const cols = [
    { t: "질문 데스크", sub: "THE FOUR QUESTIONS", c: CYN, w: 5.6, items: [
      ["q1-progress", "진척역", "§1 · §5 · §7 · §9", CYN],
      ["q2-disposal", "처분역", "§2 · §6 · §8 · §11 · §13 · §14 · §15", GRN],
      ["q3-execution", "집행역", "§3", AMB],
      ["q4-timing", "시점역", "§4 · §12 · §18", MAG],
    ]},
    { t: "방법론 · 통제 · 조립", sub: "METHOD · CONTROL · ASSEMBLY", c: ORG, w: 6.53, items: [
      ["quant-method", "계량역 — 팩터 · 논문 재현", "§16", PUR],
      ["risk-officer", "검산역 — 숫자 재검산  (거부권)", "—", MAG],
      ["compliance-officer", "준법감시역 — 게이트  (거부권)", "—", ORG],
      ["data-ops", "원장운영역 — 쓰기 단독 · 품질", "§10", GRN],
      ["ic-chair", "간사 — 조립 · 쟁점 정렬", "—", GLD],
    ]},
  ];
  let x = M;
  cols.forEach(col => {
    panel(s, { x, y: 1.90, w: col.w, h: 0.56, fill: col.c, line: null });
    txt(s, col.t, { x: x + 0.18, y: 1.96, w: col.w - 0.36, h: 0.26, fontSize: 12.5, bold: true, color: "0D1018" });
    mono(s, col.sub, { x: x + 0.18, y: 2.2, w: col.w - 0.36, h: 0.2, fontSize: 7.6, color: "0D1018", charSpacing: 1 });
    col.items.forEach((d, j) => {
      const y = 2.58 + j * 0.57;
      panel(s, { x, y, w: col.w, h: 0.50, fill: PANEL, line: EDGE });
      s.addShape(pres.ShapeType.rect, { x: x + 0.14, y: y + 0.11, w: 0.1, h: 0.28, fill: { color: d[3] }, line: { type: "none" } });
      mono(s, d[0], { x: x + 0.36, y: y + 0.04, w: 2.0, h: 0.2, fontSize: 8.4, bold: true, color: INK });
      txt(s, d[1], { x: x + 0.36, y: y + 0.25, w: col.w - 1.9, h: 0.22, fontSize: 8.8, color: MUT });
      mono(s, d[2], { x: x + col.w - 1.5, y, w: 1.36, h: 0.50, fontSize: 7.4, color: d[3], align: "right", valign: "middle" });
    });
    x += col.w + 0.13;
  });

  panel(s, { x: M, y: 5.44, w: CW, h: 0.62, fill: PANEL3, line: EDGE });
  txt(s, [
    { text: "상설 3 (data-ops · compliance · ic-chair) + 이벤트 소집 6. ", options: { bold: true, color: GRN } },
    { text: "조용한 날은 상설 셋만 돈다. 질문 데스크는 그 질문의 답이 달라졌을 때만 소집된다.", options: { color: INK } },
  ], { x: M + 0.26, y: 5.44, w: CW - 0.52, h: 0.62, fontSize: 11, valign: "middle", fontFace: F, isTextBox: true, margin: 0 });

  panel(s, { x: M, y: 6.18, w: CW, h: 0.64, fill: GLD, line: null });
  txt(s, "의결  ·  투자심의위원회 (IC) — 아홉 데스크의 산출을 놓고 사람이 결정한다", {
    x: M + 0.26, y: 6.18, w: CW - 0.52, h: 0.64, fontSize: 12.5, bold: true, color: "2E2408", valign: "middle" });
}

/* ═══ 데스크 카탈로그 — 질문 넷 ═══ */
function sDesk1() {
  const s = slide();
  header(s, "PART 3 · CATALOG 1/2", "질문 데스크 넷 — 각자 하나의 질문에만 답한다",
         "담당 질문 밖은 읽지 않는다. 읽지 않은 것에 대해 말할 여지가 없다는 뜻이다.");
  const head = ["데스크", "질문", "읽는 것", "내는 것", "제약"].map(h => ({
    text: h, options: { bold: true, color: AMB, fill: { color: PANEL2 }, fontSize: 10, valign: "middle", fontFace: FM } }));
  const rows = [
    ["q1-progress\n진척역", "얼마나\n왔는가", "facts (종가·시총·배당)\ndart.fs.* · exit_plan.csv (사내)",
     "회수계획 대비 진척\n목표회수단가 갭 · 총수익률", "exit_plan 은 '사내' 등급.\n1차와 같은 표에 섞지 않는다", CYN],
    ["q2-disposal\n처분역", "팔 수\n있는가", "facts (거래량·거래대금·지분)\nds002/004/005 · calendar",
     "처분 소요일수 (평균·중앙값)\n유동성 · 희석 · 락업 잔여", "평균과 중앙값을 함께 낸다.\n락업은 '추정' 등급 고정", GRN],
    ["q3-execution\n집행역", "어떻게\n팔 것인가", "facts (일별 거래량)\nq2 의 처분 여건 봉투",
     "매도 규칙 4종 비교\n충격 가정의 민감도", "권고를 쓰지 않는다.\n주문 API 호출 불가", AMB],
    ["q4-timing\n시점역", "지금이\n그 때인가", "macro · calendar\ndisclosures (CAR)",
     "국면 (수준 아닌 분위)\n공시 이벤트 · 다가오는 일정", "일정 등급을 섞지 않는다\n(공표 · 규칙 · 추정)", MAG],
  ];
  const body=[head];
  rows.forEach((r,i)=>{ const bg=i%2?PANEL3:PANEL; body.push([
    {text:r[0],options:{bold:true,color:r[5],fontSize:10,valign:"middle",fontFace:FM,fill:{color:bg}}},
    {text:r[1],options:{bold:true,color:GLD,fontSize:9.5,align:"center",valign:"middle",fill:{color:bg}}},
    {text:r[2],options:{color:MUT,fontSize:9,valign:"middle",fill:{color:bg}}},
    {text:r[3],options:{color:INK,fontSize:9,valign:"middle",fill:{color:bg}}},
    {text:r[4],options:{color:DIM,fontSize:8.5,italic:true,valign:"middle",fill:{color:bg}}},
  ]);});
  s.addTable(body,{x:M,y:1.86,w:CW,colW:[2.18,1.06,3.08,2.86,2.95],
    border:{type:"solid",color:EDGE,pt:1},fontFace:F,rowH:0.80,margin:0.07,autoPage:false});
  panel(s,{x:M,y:6.0,w:CW,h:0.82,fill:PANEL3,line:EDGE});
  txt(s,"q3 집행역만 q2 의 봉투를 읽는다 — \"어떻게 팔 것인가\"는 \"팔 수 있는가\"의 답 위에서만 성립하기 때문이다. 나머지 셋은 서로의 산출을 보지 않는다. 같은 결론으로 수렴하면 교차검증의 의미가 사라진다.",
    {x:M+0.26,y:6.0,w:CW-0.52,h:0.82,fontSize:10.5,color:INK,valign:"middle"});
}

function sDesk2() {
  const s = slide();
  header(s, "PART 3 · CATALOG 2/2", "방법론 · 통제 · 조립 — 다섯 데스크",
         "새로운 해석을 만들지 않는다. 근거를 대고, 검사하고, 원장을 유지하고, 회의에 올린다.");
  const head = ["데스크", "역할", "읽는 것", "내는 것", "제약"].map(h => ({
    text: h, options: { bold: true, color: AMB, fill: { color: PANEL2 }, fontSize: 10, valign: "middle", fontFace: FM } }));
  const rows = [
    ["quant-method\n계량역", "방법론 근거", "price_series · papers\n(state=adopted 만)",
     "팩터 해설 + limits\n주간 재현 판정 검토", "네 질문 중 하나를 바꾸지 않는\n논문은 채택 대상이 아니다", PUR],
    ["risk-officer\n검산역  (거부권)", "숫자 재검산", "네 질문 데스크의 봉투 전량\nfacts 원본",
     "인용값 vs 원장값 대조\n가정 스트레스", "숫자를 고쳐 주지 않는다 —\n돌려보낸다", MAG],
    ["compliance-officer\n준법감시역  (거부권)", "발행 게이트", "발행 직전의 모든 산출물\nSECTION_SOURCES",
     "일곱 게이트 판정\n발행 승인 / 반려", "하나라도 걸리면 발행 중단.\n조용히 통과시키지 않는다", ORG],
    ["data-ops\n원장운영역  (쓰기 단독)", "원장 · 품질", "KRX·DART·ECOS·KIS·FRED\n.api_fields.json · stale_days",
     "그날의 유일한 원장 쓰기\n§10 품질 · 결측 경고", "해석을 만들지 않는다.\n이 데스크만 ki.sqlite 에 쓴다", GRN],
    ["ic-chair\n투자심의위원회 간사", "조립", "게이트 통과 봉투 전량",
     "회의자료 한 장으로 조립\n질문 간 불일치 · 결측 쟁점화", "종합 의견 · 권고를 쓰지 않는다.\n쟁점을 정렬할 뿐", GLD],
  ];
  const body=[head];
  rows.forEach((r,i)=>{ const bg=i%2?PANEL3:PANEL; body.push([
    {text:r[0],options:{bold:true,color:r[5],fontSize:9.5,valign:"middle",fontFace:FM,fill:{color:bg}}},
    {text:r[1],options:{bold:true,color:GLD,fontSize:9,align:"center",valign:"middle",fill:{color:bg}}},
    {text:r[2],options:{color:MUT,fontSize:8.8,valign:"middle",fill:{color:bg}}},
    {text:r[3],options:{color:INK,fontSize:8.8,valign:"middle",fill:{color:bg}}},
    {text:r[4],options:{color:DIM,fontSize:8.4,italic:true,valign:"middle",fill:{color:bg}}},
  ]);});
  s.addTable(body,{x:M,y:1.86,w:CW,colW:[2.46,1.06,3.0,2.76,2.85],
    border:{type:"solid",color:EDGE,pt:1},fontFace:F,rowH:0.66,margin:0.06,autoPage:false});
  panel(s,{x:M,y:6.0,w:CW,h:0.82,fill:PANEL3,line:EDGE});
  txt(s,[{text:"거부권은 실제로 발행을 멈추는 권한이다. ",options:{bold:true,color:MAG}},
    {text:"검산역과 준법감시 중 하나라도 반려하면 그날 회의자료에서 해당 질문이 통째로 빠지고, 그 자리에는 '반려됨 — 사유' 가 남는다. 빈칸으로 두지 않는다.",options:{color:INK}}],
    {x:M+0.26,y:6.0,w:CW-0.52,h:0.82,fontSize:10.5,valign:"middle",fontFace:F,isTextBox:true,margin:0});
}

/* ══════════════════ 슬라이드 순서 (37장) ══════════════════ */
sTitle();          sExec();        sSystemMap();
/* PART 1 — 지금 */
sAsIs();           sWhy();         sRules();
sRefix();          sNotExRight();  sLiquidity();
/* PART 2 — 논문을 살린다 */
sProblem();        sPipeline();    sReplication();  sDecay();     sLedger();
/* PART 3 — 조직과 에이전트 (20 데스크) */
sQuestionMap();    sOrg();         sDesk1();        sDesk2();     sSourcing();
sStandingSpawn();  sLifecycle();   sTriggers();     sLoad();      sEscalation();
/* PART 4 — 통제 */
sWall();           sRbac();        sEnvelope();     sGates();     sScorecard();
/* PART 5 — 실행 */
sStack();          sMcp();         sSpec();         sDay();       sRoadmap();  sRisk();   sNext();
sAppendix();

const OUT = process.argv[2] ||
  path.join(__dirname, "Stock_Agent_에이전트화_계획안.pptx");
pres.writeFile({ fileName: OUT })
  .then(f => console.log("WROTE " + f))
  .catch(e => { console.error(e); process.exit(1); });
