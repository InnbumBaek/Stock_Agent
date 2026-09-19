"""트리거 스캐너 — 무엇이 누구를 부르는가.

사람이 데스크를 부르지 않는다. **원장의 변화**가 부른다.

전수 실행은 종목 수에 고정으로 묶인다. 종목이 40개면 조용한 날에도 40번을
돌리고, 그 40번은 대부분 "달라진 것이 없다"는 말을 만들어 낸다. 할 말이 없는데
데스크를 돌려 말을 만들게 하는 것이 이 구조가 막으려는 실패다.

**조용한 날은 조용한 것이 정상이다.** 트리거가 없으면 아무도 소집되지 않는다.

읽기만 한다. 원장에 쓰지 않는다 (규칙 2). 결정적이다 — 같은 원장·같은 감시선
이면 같은 소집이 나온다.

    python agents/triggers.py --selftest
    python agents/triggers.py --since 2026-09-10        # 실제 원장으로 훑는다
"""
from __future__ import annotations

import argparse
import json
import sqlite3
import sys
from datetime import date, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import dialect as D                                      # noqa: E402

SCHEMA = "ki.triggers/1"

# ── 상설 · 소집 ───────────────────────────────────────────────────────
#
# 상설 셋은 트리거 없이도 매일 돈다. 원장 품질·게이트·조립은 '변화가 있을 때'가
# 아니라 '매일' 확인해야 하는 것들이다.
STANDING = ("data-ops", "compliance-officer", "ic-chair")

# 질문 데스크 넷과 계량·검산은 부를 일이 있을 때만 소집된다.
ON_EVENT = ("q1-progress", "q2-disposal", "q3-execution", "q4-timing",
            "quant-method", "risk-officer")

DESKS = STANDING + ON_EVENT

# 종가가 이만큼 움직이면 처분 여건을 다시 본다.
MOVE_PCT = 8.0

# IPO 보호예수 — ki_monitor.LOCKUP_MONTHS 와 같은 값이다. 물량이 풀리기
# 30영업일 전에 미리 부른다. 풀린 날 부르면 이미 늦다.
LOCKUP_MONTHS = 6
LOCKUP_WARN_D = 30

# 공시 종류 → 어느 질문이 달라지는가. 태그는 ki_monitor 가 붙여 둔 것이다.
DISCLOSURE_ROUTES = (
    (("refix", "cb", "bw", "전환가액", "증자", "희석"), ("q2-disposal",),
     "희석·자본구조가 달라졌다"),
    (("insider", "지분", "대량보유", "임원"), ("q2-disposal",),
     "지분 구조가 달라졌다"),
    (("audit", "감사", "지배구조", "소송"), ("q2-disposal", "risk-officer"),
     "감사·지배구조 사건이다"),
    (("실적", "잠정", "영업"), ("q1-progress",),
     "회수계획 대비 진척이 달라졌다"),
)
DISCLOSURE_DEFAULT = (("q4-timing",), "공시 이벤트다 — 시점 판단에 들어간다")


class Trigger:
    """소집 한 건. 데스크가 볼 수 있는 것은 여기 담긴 입력이 전부다."""

    __slots__ = ("kind", "subject", "desks", "inputs", "why", "at", "tier")

    def __init__(self, kind, subject, desks, inputs, why, at, tier="T2"):
        self.kind, self.subject, self.desks = kind, subject, tuple(desks)
        self.inputs, self.why, self.at, self.tier = inputs, why, at, tier

    def key(self) -> tuple:
        """같은 것을 두 번 부르지 않기 위한 열쇠."""
        return (self.kind, self.subject)

    def as_dict(self) -> dict:
        return {"kind": self.kind, "subject": self.subject,
                "desks": list(self.desks), "inputs": self.inputs,
                "why": self.why, "at": self.at, "tier": self.tier}

    def __repr__(self):
        return f"<{self.kind} {self.subject} → {','.join(self.desks)}>"


def _bdays_before(d: str, n: int) -> str:
    cur = D.parse_date(d)
    left = n
    while left > 0:
        cur -= timedelta(days=1)
        if cur.weekday() < 5:
            left -= 1
    return cur.isoformat()


def _route_disclosure(title: str, tags: str) -> tuple[tuple, str]:
    blob = f"{title or ''} {tags or ''}"
    for words, desks, why in DISCLOSURE_ROUTES:
        if any(w in blob for w in words):
            return desks, why
    return DISCLOSURE_DEFAULT


# ── 스캐너 ────────────────────────────────────────────────────────────

def scan_disclosures(con, since: str, limit: int = 200) -> list[Trigger]:
    """새 공시 하나에 소집 하나. 공시 종류로 어느 데스크인지 갈린다.

    DART 의 `rcept_dt` 는 `"20260108"` 이다. `since` 는 ISO 다. 둘을 맨눈으로
    비교하면 같은 해의 옛 공시가 전부 '새 공시'가 된다 (`dialect.sql_date`)."""
    cut = D.norm_date(since)
    rows = con.execute(
        f"SELECT rcept_no, code, rcept_dt, title, tags FROM disclosure "
        f"WHERE {D.sql_date('rcept_dt')} > ? "
        f"ORDER BY {D.sql_date('rcept_dt')}, rcept_no LIMIT ?",
        (cut, limit)).fetchall()
    out = []
    for r in rows:
        desks, why = _route_disclosure(r["title"], r["tags"])
        # 밖으로 내는 날짜는 ISO 다. 봉투·소집·리포트가 모두 ISO 를 쓰는데
        # 여기만 원장 형식을 흘리면 두 형식이 섞여 대조가 어긋난다.
        dt = D.iso_date(r["rcept_dt"])
        out.append(Trigger(
            "disclosure.new", r["rcept_no"], desks,
            {"code": r["code"], "rcept_no": r["rcept_no"],
             "rcept_dt": dt, "title": r["title"]},
            why, dt, tier="T1"))
    return out


def scan_price_moves(con, since: str, pct: float = MOVE_PCT) -> list[Trigger]:
    """종가가 크게 움직인 종목. 처분 여건이 달라졌을 수 있다.

    종목당 하나만 낸다. 사흘 연속 움직였다고 세 번 부르면, 세 인스턴스가 거의
    같은 말을 하고 그중 하나만 회의에 올라간다."""
    # 창의 시작을 파이썬에서 계산한다. SQLite 의 `date(?, '-7 day')` 에
    # 기대면 안 된다 — 그 함수는 ISO 만 받고 원장은 `"20260911"` 이라, 비교가
    # 4번째 글자에서 무너져 **같은 해 전체**가 창 안으로 들어온다. 그러면 여덟
    # 달 전 하락이 오늘의 소집으로 올라간다.
    base = D.parse_date(since)
    if base is None:
        return []
    cut = D.norm_date((base - timedelta(days=7)).isoformat())
    since_c = D.norm_date(since)
    rows = con.execute(
        f"SELECT date, code, close FROM price_daily "
        f"WHERE {D.sql_date('date')} > ? "
        f"ORDER BY code, {D.sql_date('date')}", (cut,)).fetchall()
    out, prev, seen = [], {}, set()
    for r in rows:
        c, d, px = r["code"], D.norm_date(r["date"]), r["close"]
        p = prev.get(c)
        prev[c] = px
        if p is None or not p or d <= since_c or c in seen:
            continue
        chg = (px / p - 1.0) * 100.0
        if abs(chg) >= pct:
            seen.add(c)
            iso = D.iso_date(d)                  # 밖으로는 ISO 로 낸다
            out.append(Trigger(
                "price.move", c, ("q2-disposal", "risk-officer"),
                {"code": c, "date": iso, "change_pct": round(chg, 2),
                 "close": px, "prev_close": p},
                f"종가가 하루에 {chg:+.1f}% 움직였다 (임계 ±{pct}%)", iso))
    return sorted(out, key=lambda t: t.subject)


def scan_lockups(con, today: str, warn_d: int = LOCKUP_WARN_D) -> list[Trigger]:
    """보호예수 해제가 다가오는 종목. 풀린 날 부르면 이미 늦다."""
    rows = con.execute(
        "SELECT code, name, list_date FROM instruments "
        "WHERE list_date IS NOT NULL AND list_date <> '' ORDER BY code").fetchall()
    out = []
    for r in rows:
        # KRX `LIST_DD` 는 `"20170102"` 다. `fromisoformat` 이 그 형식을 받는
        # 것은 3.11 부터라, 3.10 에서는 전 종목이 조용히 빠진다.
        ld = D.parse_date(r["list_date"])
        if ld is None:
            continue
        m = ld.month - 1 + LOCKUP_MONTHS
        try:
            end = ld.replace(year=ld.year + m // 12, month=m % 12 + 1)
        except ValueError:                      # 2/30 같은 날짜
            end = ld.replace(year=ld.year + m // 12, month=m % 12 + 1, day=28)
        warn_from = _bdays_before(end.isoformat(), warn_d)
        if warn_from <= today <= end.isoformat():
            out.append(Trigger(
                "lockup.d30", r["code"], ("q3-execution", "q4-timing"),
                {"code": r["code"], "list_date": ld.isoformat(),
                 "lockup_end": end.isoformat(),
                 "lockup_months": LOCKUP_MONTHS},
                f"보호예수 해제({end.isoformat()})가 {warn_d}영업일 안으로 들어왔다. "
                f"물량 압력은 **추정**이다 — 실제 해제 물량은 공시로 확인해야 한다.",
                today))
    return out


def scan_macro(con, since: str) -> list[Trigger]:
    """거시 지표가 갱신됐다. 국면 서술이 달라질 수 있다. 하루 한 번만."""
    # `macro_daily` 는 한 형식이 아니다. KRX 경로는 `"20260911"`, FRED 경로는
    # 판다스 Timestamp 가 그대로 들어가 `"2026-09-11 00:00:00"` 이다. 가장
    # 최근 날짜를 고르려면 둘을 같은 자로 재야 한다 — 맨눈으로 MAX 를 뽑으면
    # 형식이 긴 쪽이 늘 이긴다.
    r = con.execute(
        f"SELECT MAX({D.sql_date('date')}) AS d FROM macro_daily").fetchone()
    last = r["d"] if r else None
    if not last or last <= D.norm_date(since):
        return []
    # 키도 정규화한 날짜로 고른다. 같은 날이 두 형식으로 들어와 있으면
    # (KRX 가 넣은 행과 FRED 가 넣은 행) 한쪽만 세게 된다.
    keys = [x["key"] for x in con.execute(
        f"SELECT DISTINCT key FROM macro_daily "
        f"WHERE {D.sql_date('date')} = ? ORDER BY key", (last,)).fetchall()]
    iso = D.iso_date(last)
    return [Trigger("macro.update", iso, ("q4-timing",),
                    {"date": iso, "keys": keys},
                    "거시 지표가 갱신됐다", iso)]


def scan_paper_rechecks(paper_ledger: dict, today: str,
                        cap: int = 3) -> list[Trigger]:
    """재검 기한이 지난 논문. 주당 상한을 두어 4주에 걸쳐 나눠 본다.

    상한이 없으면 이관 직후처럼 기한이 한꺼번에 몰린 날 열두 편이 한 번에
    소집된다. 그러면 그 주의 재현은 전부 대충 돌아간다."""
    if not paper_ledger:
        return []
    # 어떤 러너로도 검정할 수 없는 논문은 부르지 않는다. 추정량·모형은 분위로
    # 정렬해 초과수익을 볼 물건이 아니라서, 소집해 봐야 계량역이 "이건 그런
    # 물건이 아닙니다"를 매주 다시 쓰게 된다. 영원히 반복되는 빈 소집이다.
    try:
        import replication as _R                 # noqa: PLC0415
        never = set(_R.NOT_A_FACTOR)
    except Exception:                            # noqa: BLE001
        never = set()

    due = []
    for k, p in (paper_ledger.get("papers") or {}).items():
        if p.get("state") == "retired" or k in never:
            continue                            # 은퇴본·대상 아님은 부르지 않는다
        d = p.get("recheck_due")
        if d is None or d <= today:
            due.append((d or "", k, p))
    # 기한이 오래 지난 것부터. 기한이 없는 것(미검증)은 그다음이다.
    due.sort(key=lambda x: (x[0] == "", x[0], x[1]))
    out = []
    for d, k, p in due[:cap]:
        out.append(Trigger(
            "paper.recheck", k, ("quant-method",),
            {"paper": k, "state": p.get("state"), "recheck_due": d or None,
             "question": p.get("question")},
            ("재검 기한이 지났다" if d else "아직 우리 표본으로 재현해 본 적이 없다"),
            today, tier="T3"))                  # 재현 설계는 틀리면 비싸다
    return out


def scan(con, today: str = None, since: str = None,
         paper_ledger: dict = None, recheck_cap: int = 3) -> dict:
    """원장을 한 번 훑어 그날의 소집을 낸다.

    `since` 는 마지막으로 훑은 날이다. 이것이 없으면 원장 전체가 '새 것'이
    되어 첫 실행에 수백 건이 쏟아진다."""
    today = today or date.today().isoformat()
    since = since or _bdays_before(today, 1)

    ts: list[Trigger] = []
    ts += scan_disclosures(con, since)
    ts += scan_price_moves(con, since)
    ts += scan_lockups(con, today)
    ts += scan_macro(con, since)
    ts += scan_paper_rechecks(paper_ledger or {}, today, recheck_cap)

    # 같은 것을 두 번 부르지 않는다.
    seen, uniq = set(), []
    for t in ts:
        if t.key() in seen:
            continue
        seen.add(t.key())
        uniq.append(t)

    convened = sorted({d for t in uniq for d in t.desks})
    return {
        "schema": SCHEMA, "at": today, "since": since,
        "standing": list(STANDING),
        "triggers": [t.as_dict() for t in uniq],
        "n": len(uniq),
        "convened": convened,
        "idle": sorted(set(ON_EVENT) - set(convened)),
        "note": ("트리거가 없으면 아무도 소집되지 않는다. 조용한 날은 조용한 것이 "
                 "정상이다 — 상설 셋은 그래도 돈다."),
    }


# ── 자체 검사 ─────────────────────────────────────────────────────────

# 합성 원장이 쓸 시장 이름. 진짜 원장이 쓰는 값이다 (`dialect`).
_MKT = D.MARKET_ALIASES["KOSDAQ"][0]


def _ledger(rows_price=(), disclosures=(), instruments=(), macro=(),
            iso: bool = False) -> sqlite3.Connection:
    """합성 원장.

    호출부는 읽기 쉬운 ISO·영문으로 준다. 표에 **들어가는 것은 진짜 원장의
    형식**이다 — 날짜는 `YYYYMMDD`, 시장은 한글. 여기서 호출부의 형식을 그대로
    넣으면 검사가 자기 가정을 다시 확인할 뿐이고, 그 사이 스캐너는 진짜
    원장에서 여덟 달 전 하락을 오늘의 소집으로 올린다.

    `iso=True` 는 형식이 바뀐 원장을 흉내 낸다 — 읽는 쪽이 짐작하지 않고
    물어보는지 확인하는 용도다."""
    def _d(v):
        return D.iso_date(v) if iso else D.norm_date(v)

    def _m(v):
        return v if iso else (D._pick([_MKT], v) or _MKT)

    con = sqlite3.connect(":memory:")
    con.row_factory = sqlite3.Row
    con.executescript("""
    CREATE TABLE price_daily (date TEXT, code TEXT, market TEXT, close REAL,
      PRIMARY KEY (date, code));
    CREATE TABLE disclosure (rcept_no TEXT PRIMARY KEY, code TEXT, rcept_dt TEXT,
      title TEXT, tags TEXT);
    CREATE TABLE instruments (code TEXT PRIMARY KEY, name TEXT, market TEXT,
      list_date TEXT);
    CREATE TABLE macro_daily (date TEXT, key TEXT, value REAL,
      PRIMARY KEY (date, key));
    """)
    con.executemany("INSERT INTO price_daily (date, code, market, close) VALUES (?,?,?,?)",
                    [(_d(d), c, _m(m), px) for d, c, m, px in rows_price])
    con.executemany("INSERT INTO disclosure VALUES (?,?,?,?,?)",
                    [(no, c, _d(dt), t, g) for no, c, dt, t, g in disclosures])
    con.executemany("INSERT INTO instruments VALUES (?,?,?,?)",
                    [(c, n, _m(m), _d(ld)) for c, n, m, ld in instruments])
    con.executemany("INSERT INTO macro_daily VALUES (?,?,?)",
                    [(_d(d), k, v) for d, k, v in macro])
    con.commit()
    return con


def selftest() -> int:
    passed, failed = 0, []

    def check(name, fn):
        nonlocal passed
        try:
            fn(); passed += 1
        except Exception as e:                          # noqa: BLE001
            failed.append(f"{name}: {type(e).__name__}: {e}")

    def _assert(c, why=""):
        if not c:
            raise AssertionError(why or "거짓")

    def _quiet_day():
        """조용한 날은 아무도 소집되지 않는다 — 이 구조의 요점이다."""
        con = _ledger(rows_price=[("2026-09-10", "000660", "KOSDAQ", 100.0),
                                  ("2026-09-11", "000660", "KOSDAQ", 100.5)])
        r = scan(con, today="2026-09-11", since="2026-09-10")
        con.close()
        _assert(r["n"] == 0, r["triggers"])
        _assert(r["convened"] == [])
        _assert(set(r["idle"]) == set(ON_EVENT))
        _assert(r["standing"] == list(STANDING))        # 상설은 그래도 돈다
    check("조용한 날은 아무도 소집되지 않는다", _quiet_day)

    def _price_move():
        con = _ledger(rows_price=[("2026-09-10", "000660", "KOSDAQ", 100.0),
                                  ("2026-09-11", "000660", "KOSDAQ", 88.0)])
        r = scan(con, today="2026-09-11", since="2026-09-10")
        con.close()
        t = [x for x in r["triggers"] if x["kind"] == "price.move"]
        _assert(len(t) == 1, r["triggers"])
        _assert(t[0]["inputs"]["change_pct"] == -12.0)
        _assert("q2-disposal" in t[0]["desks"] and "risk-officer" in t[0]["desks"])
    check("큰 가격 변동이 처분·검산을 부른다", _price_move)

    def _small_move_ignored():
        con = _ledger(rows_price=[("2026-09-10", "000660", "KOSDAQ", 100.0),
                                  ("2026-09-11", "000660", "KOSDAQ", 95.0)])
        r = scan(con, today="2026-09-11", since="2026-09-10")
        con.close()
        _assert(r["n"] == 0)                            # -5% 는 임계 아래
    check("임계 아래 변동은 부르지 않는다", _small_move_ignored)

    def _one_per_code():
        """사흘 연속 움직여도 종목당 한 번만 부른다."""
        con = _ledger(rows_price=[("2026-09-09", "000660", "KOSDAQ", 100.0),
                                  ("2026-09-10", "000660", "KOSDAQ", 88.0),
                                  ("2026-09-11", "000660", "KOSDAQ", 77.0)])
        r = scan(con, today="2026-09-11", since="2026-09-09")
        con.close()
        _assert(len([x for x in r["triggers"] if x["kind"] == "price.move"]) == 1)
    check("같은 종목을 두 번 부르지 않는다", _one_per_code)

    def _disclosure_routing():
        con = _ledger(disclosures=[
            ("R1", "000660", "2026-09-11", "전환가액의조정", "refix"),
            ("R2", "000660", "2026-09-11", "임원ㆍ주요주주특정증권등소유상황보고서", "insider"),
            ("R3", "000660", "2026-09-11", "매출액또는손익구조30%이상변동", "실적"),
            ("R4", "000660", "2026-09-11", "기타경영사항", ""),
        ])
        r = scan(con, today="2026-09-11", since="2026-09-10")
        con.close()
        by = {x["subject"]: x for x in r["triggers"]}
        _assert(by["R1"]["desks"] == ["q2-disposal"], by["R1"])
        _assert(by["R2"]["desks"] == ["q2-disposal"])
        _assert(by["R3"]["desks"] == ["q1-progress"])
        _assert(by["R4"]["desks"] == ["q4-timing"])     # 분류 안 되면 시점역
        _assert(all(x["tier"] == "T1" for x in r["triggers"]))
    check("공시는 종류에 따라 다른 데스크를 부른다", _disclosure_routing)

    def _disclosure_since():
        """이미 본 공시를 다시 부르지 않는다."""
        con = _ledger(disclosures=[("R1", "000660", "2026-09-09", "전환가액의조정", "refix")])
        r = scan(con, today="2026-09-11", since="2026-09-10")
        con.close()
        _assert(r["n"] == 0)
    check("감시선 이전의 공시는 다시 부르지 않는다", _disclosure_since)

    def _lockup():
        # 2026-03-20 상장 → 6개월 뒤 2026-09-20 해제. 30영업일 전부터 경고.
        con = _ledger(instruments=[("000660", "샘플", "KOSDAQ", "2026-03-20")])
        near = scan(con, today="2026-09-11")
        far = scan(con, today="2026-05-01")
        after = scan(con, today="2026-10-15")
        con.close()
        t = [x for x in near["triggers"] if x["kind"] == "lockup.d30"]
        _assert(len(t) == 1, near["triggers"])
        _assert(t[0]["inputs"]["lockup_end"] == "2026-09-20")
        _assert("q3-execution" in t[0]["desks"])
        _assert("추정" in t[0]["why"])                   # 등급을 숨기지 않는다
        _assert(not [x for x in far["triggers"] if x["kind"] == "lockup.d30"])
        _assert(not [x for x in after["triggers"] if x["kind"] == "lockup.d30"])
    check("보호예수 해제는 30영업일 전에 부른다", _lockup)

    def _macro():
        con = _ledger(macro=[("2026-09-11", "base_rate", 3.0),
                             ("2026-09-11", "usdkrw", 1300.0)])
        r = scan(con, today="2026-09-11", since="2026-09-10")
        con.close()
        t = [x for x in r["triggers"] if x["kind"] == "macro.update"]
        _assert(len(t) == 1)
        _assert(t[0]["inputs"]["keys"] == ["base_rate", "usdkrw"])
        _assert(t[0]["desks"] == ["q4-timing"])
    check("거시 갱신은 하루 한 번만 부른다", _macro)

    def _paper_recheck_cap():
        """이관 직후처럼 기한이 몰린 날에도 주당 상한을 지킨다."""
        led = {"papers": {f"p{i}": {"state": "unverified", "recheck_due": None,
                                    "question": "q2"} for i in range(12)}}
        con = _ledger()
        r = scan(con, today="2026-09-11", paper_ledger=led)
        con.close()
        t = [x for x in r["triggers"] if x["kind"] == "paper.recheck"]
        _assert(len(t) == 3, len(t))                    # 12편이 아니라 3편
        _assert(all(x["desks"] == ["quant-method"] for x in t))
        _assert(all(x["tier"] == "T3" for x in t))      # 재현 설계는 상위 급
    check("재검은 주당 상한을 지킨다 (12편이 한 번에 쏟아지지 않는다)",
          _paper_recheck_cap)

    def _paper_recheck_order():
        """기한이 오래 지난 것이 먼저다."""
        led = {"papers": {
            "old": {"state": "adopted", "recheck_due": "2025-01-01", "question": "q1"},
            "new": {"state": "adopted", "recheck_due": "2026-09-01", "question": "q1"},
            "none": {"state": "unverified", "recheck_due": None, "question": "q1"},
        }}
        con = _ledger()
        r = scan(con, today="2026-09-11", paper_ledger=led, recheck_cap=2)
        con.close()
        got = [x["subject"] for x in r["triggers"] if x["kind"] == "paper.recheck"]
        _assert(got == ["old", "new"], got)
    check("기한이 오래 지난 논문부터 재검한다", _paper_recheck_order)

    def _not_a_factor_not_convened():
        """어떤 러너로도 못 재는 논문은 소집하지 않는다.

        통합 실행에서 실제로 나왔다 — quant-method 가 ac2000(최적 집행 모형)을
        재검하러 불려 나왔다. 그 논문은 앞으로도 분위 검정 대상이 아니므로
        매주 같은 빈 소집이 반복된다."""
        import replication as _R
        never = sorted(_R.NOT_A_FACTOR)
        _assert(never, "대상 아님 목록이 비었습니다")
        led = {"papers": {k: {"state": "unverified", "recheck_due": None,
                              "question": "q2"} for k in never}}
        led["papers"]["amihud2002"] = {"state": "unverified",
                                       "recheck_due": None, "question": "q2"}
        con = _ledger()
        r = scan(con, today="2026-09-11", paper_ledger=led)
        con.close()
        got = [t["subject"] for t in r["triggers"] if t["kind"] == "paper.recheck"]
        _assert(got == ["amihud2002"], got)
    check("검정할 수 없는 논문은 소집하지 않는다", _not_a_factor_not_convened)

    def _retired_not_rechecked():
        led = {"papers": {"dead": {"state": "retired", "recheck_due": "2020-01-01",
                                   "question": "q1"}}}
        con = _ledger()
        r = scan(con, today="2026-09-11", paper_ledger=led)
        con.close()
        _assert(r["n"] == 0)                            # 은퇴본은 다시 보지 않는다
    check("은퇴한 논문은 재검하지 않는다", _retired_not_rechecked)

    def _future_due_not_called():
        led = {"papers": {"ok": {"state": "adopted", "recheck_due": "2099-01-01",
                                 "question": "q1"}}}
        con = _ledger()
        r = scan(con, today="2026-09-11", paper_ledger=led)
        con.close()
        _assert(r["n"] == 0)
    check("기한 전인 논문은 부르지 않는다", _future_due_not_called)

    def _inputs_are_closed():
        """데스크가 볼 수 있는 것은 넘겨받은 입력이 전부다 (격리).

        트리거가 원장 연결이나 전체 종목 목록을 실어 보내면, 소집된 데스크가
        자기 질문 밖을 들여다보게 된다. 그러면 격리가 형식만 남는다."""
        con = _ledger(disclosures=[("R1", "000660", "2026-09-11", "전환가액의조정", "refix")],
                      rows_price=[("2026-09-10", "000660", "KOSDAQ", 100.0),
                                  ("2026-09-11", "000660", "KOSDAQ", 88.0)])
        r = scan(con, today="2026-09-11", since="2026-09-10")
        con.close()
        blob = json.dumps(r, ensure_ascii=False)        # 직렬화되는가 (무상태)
        _assert(blob)
        for t in r["triggers"]:
            _assert(isinstance(t["inputs"], dict) and t["inputs"])
            for v in t["inputs"].values():
                _assert(isinstance(v, (str, int, float, list, type(None))), v)
    check("트리거가 넘기는 입력은 닫혀 있고 직렬화된다", _inputs_are_closed)

    def _desks_are_known():
        """모르는 데스크를 부르지 않는다 — 옛 이름이 남아 있으면 여기서 걸린다."""
        con = _ledger(disclosures=[("R1", "000660", "2026-09-11", "감사보고서제출", "audit"),
                                   ("R2", "000660", "2026-09-11", "기타", "")],
                      instruments=[("000660", "샘플", "KOSDAQ", "2026-03-20")],
                      macro=[("2026-09-11", "base_rate", 3.0)],
                      rows_price=[("2026-09-10", "000660", "KOSDAQ", 100.0),
                                  ("2026-09-11", "000660", "KOSDAQ", 88.0)])
        led = {"papers": {"p": {"state": "unverified", "recheck_due": None,
                                "question": "q1"}}}
        r = scan(con, today="2026-09-11", since="2026-09-10", paper_ledger=led)
        con.close()
        for t in r["triggers"]:
            for d in t["desks"]:
                _assert(d in DESKS, f"{t['kind']} → 모르는 데스크 {d!r}")
        for _words, desks, _why in DISCLOSURE_ROUTES:
            for d in desks:
                _assert(d in DESKS, d)
        for d in DISCLOSURE_DEFAULT[0]:
            _assert(d in DESKS, d)
    check("트리거는 실재하는 데스크만 부른다", _desks_are_known)

    def _deterministic():
        rows = [("2026-09-10", "000660", "KOSDAQ", 100.0),
                ("2026-09-11", "000660", "KOSDAQ", 88.0)]
        a = _ledger(rows_price=rows); ra = scan(a, today="2026-09-11", since="2026-09-10"); a.close()
        b = _ledger(rows_price=rows); rb = scan(b, today="2026-09-11", since="2026-09-10"); b.close()
        _assert(ra == rb)
    check("두 번 훑으면 같은 소집이 나온다 (결정적)", _deterministic)

    def _reads_only():
        con = _ledger(rows_price=[("2026-09-10", "000660", "KOSDAQ", 100.0),
                                  ("2026-09-11", "000660", "KOSDAQ", 88.0)])
        before = con.execute("SELECT COUNT(*) FROM price_daily").fetchone()[0]
        scan(con, today="2026-09-11", since="2026-09-10")
        after = con.execute("SELECT COUNT(*) FROM price_daily").fetchone()[0]
        con.close()
        _assert(before == after)
    check("원장을 읽기만 한다", _reads_only)

    # ── 원장의 말 (dialect) ───────────────────────────────────────────
    #
    # 스캐너의 창은 문자열 비교로 서 있었다. 원장은 `"20260911"`, `since` 는
    # ISO `"2026-09-11"` 이라 4번째 글자에서 `'0'` 과 `'-'` 이 만나고, 그때
    # **같은 해의 모든 날짜가 창 안으로 들어온다.** 없는 결과가 나오면 차라리
    # 나았다 — 실제로는 여덟 달 전 -40% 하락이 오늘의 소집으로 올라왔다.

    def _fixture_is_the_real_dialect():
        con = _ledger(rows_price=[("2026-09-11", "000660", "KOSDAQ", 100.0)],
                      instruments=[("000660", "샘플", "KOSDAQ", "2026-03-20")])
        d = con.execute("SELECT date, market FROM price_daily").fetchone()
        i = con.execute("SELECT market, list_date FROM instruments").fetchone()
        con.close()
        _assert(d["date"] == "20260911", d["date"])
        _assert(d["market"] == "코스닥", d["market"])
        _assert(i["market"] == "코스닥" and i["list_date"] == "20260320", tuple(i))
    check("합성 원장이 진짜 원장의 형식이다", _fixture_is_the_real_dialect)

    def _window_is_seven_days_not_this_year():
        """창 밖의 하락을 오늘의 소집으로 올리지 않는다."""
        con = _ledger(rows_price=[("2026-01-05", "000660", "KOSDAQ", 100.0),
                                  ("2026-01-08", "000660", "KOSDAQ", 60.0),
                                  ("2026-09-10", "000660", "KOSDAQ", 100.0),
                                  ("2026-09-11", "000660", "KOSDAQ", 100.2)])
        ts = scan_price_moves(con, "2026-09-10")
        con.close()
        _assert(ts == [], [t.as_dict() for t in ts])
    check("가격 창은 7일이다 (같은 해 전체가 아니다)",
          _window_is_seven_days_not_this_year)

    def _old_disclosure_is_not_new():
        con = _ledger(disclosures=[("X", "000660", "2026-01-08", "유상증자 결정", "")])
        ts = scan_disclosures(con, "2026-09-11")
        con.close()
        _assert(ts == [], [t.as_dict() for t in ts])
    check("옛 공시는 새 공시가 아니다", _old_disclosure_is_not_new)

    def _macro_max_is_by_date_not_by_string_length():
        """`macro_daily` 는 한 형식이 아니다 — KRX 는 `20260911`, FRED 를 거친
        행은 `2026-09-11 00:00:00` 이다. 맨눈 MAX 는 긴 쪽이 늘 이긴다."""
        con = _ledger(macro=[("2026-09-11", "k1", 1.0)])
        con.execute("INSERT INTO macro_daily VALUES ('2026-01-08 00:00:00','k2',2.0)")
        con.commit()
        ts = scan_macro(con, "2026-09-10")
        con.close()
        _assert(len(ts) == 1, [t.as_dict() for t in ts])
        _assert(ts[0].inputs["date"] == "2026-09-11", ts[0].as_dict())
        _assert(ts[0].inputs["keys"] == ["k1"], ts[0].as_dict())
    check("거시는 형식이 섞여 있어도 가장 최근 날을 고른다",
          _macro_max_is_by_date_not_by_string_length)

    def _macro_same_day_two_formats():
        """같은 날이 두 형식으로 들어와 있으면 (KRX 행과 FRED 행) 한쪽만
        세지 않는다 — 거시 지표 절반이 조용히 빠진다."""
        con = _ledger(macro=[("2026-09-17", "krx_key", 1.0)])
        con.execute("INSERT INTO macro_daily VALUES ('2026-09-17 00:00:00',"
                    "'fred_key',2.0)")
        con.commit()
        ts = scan_macro(con, "2026-09-16")
        con.close()
        _assert(len(ts) == 1, [t.as_dict() for t in ts])
        _assert(ts[0].inputs["keys"] == ["fred_key", "krx_key"],
                ts[0].as_dict())
    check("같은 날이 두 형식이어도 키를 다 센다", _macro_same_day_two_formats)

    def _emits_iso_whatever_the_ledger_stores():
        """밖으로 내는 날짜는 ISO 다. 여기만 원장 형식을 흘리면 봉투·대조가
        두 형식으로 갈린다."""
        for iso in (False, True):
            con = _ledger(
                rows_price=[("2026-09-10", "000660", "KOSDAQ", 100.0),
                            ("2026-09-11", "000660", "KOSDAQ", 88.0)],
                disclosures=[("X", "000660", "2026-09-11", "유상증자 결정", "")],
                instruments=[("000660", "샘플", "KOSDAQ", "2026-03-20")],
                macro=[("2026-09-11", "k", 1.0)], iso=iso)
            r = scan(con, today="2026-09-11", since="2026-09-10")
            con.close()
            for t in r["triggers"]:
                _assert(len(t["at"]) == 10 and t["at"][4] == "-",
                        (iso, t["kind"], t["at"]))
            kinds = {t["kind"] for t in r["triggers"]}
            _assert({"price.move", "disclosure.new", "macro.update"} <= kinds,
                    (iso, kinds))
    check("원장 형식과 무관하게 ISO 로 낸다",
          _emits_iso_whatever_the_ledger_stores)

    for f in failed:
        print("  X  " + f, file=sys.stderr)
    print(f"triggers   {passed} passed, {len(failed)} failed")
    return 1 if failed else 0


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="트리거 스캐너 · 소집")
    ap.add_argument("--selftest", action="store_true")
    ap.add_argument("--since", help="마지막으로 훑은 날 (YYYY-MM-DD)")
    ap.add_argument("--today", help="기준일 (기본: 오늘)")
    ap.add_argument("--db", help="원장 경로")
    ap.add_argument("--indent", type=int, default=2)
    a = ap.parse_args()
    if a.selftest or not (a.since or a.db):
        sys.exit(selftest())
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    import papers as P                                   # noqa: E402
    if a.db:
        con = sqlite3.connect(f"file:{a.db}?mode=ro", uri=True)
    else:
        import ki_ledger_mcp as M                        # noqa: E402
        con = M.open_ledger()
    con.row_factory = sqlite3.Row
    led = P.age_states(P.migrate(P.load())) if P.LEDGER.exists() else None
    try:
        print(json.dumps(scan(con, today=a.today, since=a.since, paper_ledger=led),
                         ensure_ascii=False, indent=a.indent))
    finally:
        con.close()
