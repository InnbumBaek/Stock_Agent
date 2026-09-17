"""리플레이 — 왜 그렇게 읽었는가를 되짚는다.

회의에서 나오는 가장 어려운 질문은 "그때 왜 그렇게 읽었나"다. 석 달 전 봉투를
다시 열어 지금 원장에 물어보면 다른 숫자가 나온다. 그때 **둘 중 무엇인지**를
말할 수 없으면 그 시스템은 자기 이력을 설명하지 못한다.

    에이전트가 틀렸다     같은 자료를 보고 다르게 읽었다
    데이터가 바뀌었다     자료 자체가 그 뒤에 달라졌다

원장은 `INSERT OR REPLACE` 로 덮어써진다. DART 정정공시가 오면 같은 칸이
조용히 바뀌고, 옛 값은 남지 않는다. 원장을 양방향 시간 장부로 바꾸는 것은 큰
공사이고 측정층을 건드려야 한다.

그래서 **봉투 쪽에서 푼다.** 봉투가 자기가 읽은 것(`read`)을 적어 두면, 지금
원장과 대조하는 것만으로 같은 구분이 선다. 측정층은 한 줄도 건드리지 않는다.

    python agents/replay.py --selftest
    python agents/replay.py --envelope 봉투.json
"""
from __future__ import annotations

import argparse
import json
import sqlite3
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import envelope as E                                     # noqa: E402
import papers as P                                       # noqa: E402

SCHEMA = "ki.replay/1"

SAME = "일치"
DATA_MOVED = "데이터가 바뀜"
GONE = "원장에서 사라짐"
NOT_RECORDED = "재생 불가 — 읽은 것을 적지 않음"
UNKNOWN_KEY = "키를 해석할 수 없음"

# 부동소수 비교. 종가·거래대금은 실수라 정확히 같기를 요구하면 늘 다르다고 나온다.
REL_TOL = 1e-9


def _close(a, b) -> bool:
    if a is None or b is None:
        return a is b
    try:
        fa, fb = float(a), float(b)
    except (TypeError, ValueError):
        return a == b
    if fa == fb:
        return True
    scale = max(abs(fa), abs(fb))
    return abs(fa - fb) <= REL_TOL * scale


def _lookup(con, key: str):
    """관측 키를 원장에서 다시 읽는다. 지어내지 않는다 — 못 읽으면 사유를 낸다.

    키는 `<종목코드>.<칼럼>` 또는 `<종목코드>.<기간>.<항목>` 이다. 생 SQL 을
    받지 않는 것은 MCP 서버와 같은 이유다 — 되짚기가 원장을 헤집는 통로가 되면
    안 된다."""
    parts = (key or "").split(".")
    if len(parts) == 2:
        code, col = parts
        if col not in ("open", "high", "low", "close", "volume", "value",
                       "mktcap", "shares"):
            return None, UNKNOWN_KEY, f"모르는 칼럼입니다: {col}"
        r = con.execute(
            f"SELECT date, {col} AS v FROM price_daily WHERE code = ? "
            f"ORDER BY date DESC LIMIT 1", (code,)).fetchone()
        if r is None:
            return None, GONE, f"{code} 의 일봉이 원장에 없습니다"
        return r["v"], None, None
    if len(parts) == 3:
        code, period, item = parts
        r = con.execute(
            "SELECT value AS v FROM fundamental WHERE code = ? AND period = ? "
            "AND key = ?", (code, period, item)).fetchone()
        if r is None:
            return None, GONE, f"{code}/{period}/{item} 이 원장에 없습니다"
        return r["v"], None, None
    return None, UNKNOWN_KEY, "키 형식이 <코드>.<칼럼> 도 <코드>.<기간>.<항목> 도 아닙니다"


def replay(env: dict, con, paper_ledger: dict = None,
           at: str = None) -> dict:
    """봉투 하나를 되짚는다.

    낼 것은 판정이 아니라 **대조표**다. 무엇이 같고 무엇이 달라졌는지까지가
    이 함수의 몫이고, 그래서 그 문장이 틀렸는지는 사람이 본다."""
    at = at or date.today().isoformat()
    out = {
        "schema": SCHEMA, "at": at,
        "instance": env.get("instance"), "desk": env.get("desk"),
        "claim": env.get("claim"), "envelope_asof": env.get("asof"),
        "observations": [], "paper": None,
        "replayable": True, "data_moved": False, "reason": None,
    }

    rd = env.get("read")
    if env.get("value") is not None and not rd:
        out["replayable"] = False
        out["reason"] = (
            "봉투가 읽은 것을 적지 않았습니다. 지금 원장과 대조할 기준이 없으므로 "
            "'에이전트가 틀렸다'와 '데이터가 바뀌었다'를 구분할 수 없습니다.")
        return out

    for o in rd or []:
        now, verdict, why = _lookup(con, o.get("key"))
        if verdict is None:
            verdict = SAME if _close(o.get("value"), now) else DATA_MOVED
        row = {"key": o.get("key"), "source": o.get("source"),
               "then": o.get("value"), "now": now,
               "asof_then": o.get("asof"), "verdict": verdict}
        if why:
            row["reason"] = why
        if verdict in (DATA_MOVED, GONE):
            out["data_moved"] = True
        out["observations"].append(row)

    # 논문 상태는 append-only 라 그때 기준으로 되짚을 수 있다.
    m = env.get("method") or {}
    if m.get("paper"):
        then = m.get("paper_state")
        now = P.state_of(paper_ledger or {}, m["paper"])
        out["paper"] = {
            "paper": m["paper"], "state_then": then, "state_now": now,
            "moved": bool(now and then and now != then),
            "note": ("논문 장부는 덮어쓰지 않고 쌓이므로, 지금 상태가 달라도 "
                     "그때 판정이 무엇이었는지는 장부에 남아 있습니다."),
        }

    moved = [o for o in out["observations"] if o["verdict"] != SAME]
    if moved:
        out["reason"] = (
            f"읽은 값 {len(moved)}개가 그때와 다릅니다. **에이전트가 틀렸다고 "
            f"보기 전에 자료가 움직였는지를 먼저 보십시오** — 정정공시가 오면 "
            f"원장의 같은 칸이 덮어써집니다.")
    elif out["observations"]:
        out["reason"] = ("읽은 값이 그때와 전부 같습니다. 문장이 지금 이상해 "
                         "보인다면 자료가 아니라 읽은 방식을 보십시오.")
    return out


def replay_all(envs: list, con, paper_ledger: dict = None, at: str = None) -> dict:
    rows = [replay(e, con, paper_ledger, at) for e in envs]
    return {
        "schema": SCHEMA, "at": at or date.today().isoformat(),
        "n": len(rows),
        "replayable": sum(1 for r in rows if r["replayable"]),
        "data_moved": sum(1 for r in rows if r["data_moved"]),
        "rows": rows,
        "note": ("되짚기는 판정이 아니라 대조표다. 무엇이 움직였는지까지가 "
                 "이 도구의 몫이고, 그래서 그 문장이 틀렸는지는 사람이 본다."),
    }


# ── 자체 검사 ─────────────────────────────────────────────────────────

def _con(close=88.0, rev=1.0) -> sqlite3.Connection:
    con = sqlite3.connect(":memory:")
    con.row_factory = sqlite3.Row
    con.executescript("""
    CREATE TABLE price_daily (date TEXT, code TEXT, market TEXT, open REAL,
      high REAL, low REAL, close REAL, volume REAL, value REAL, mktcap REAL,
      shares REAL, PRIMARY KEY (date, code));
    CREATE TABLE fundamental (code TEXT, period TEXT, key TEXT, value REAL,
      PRIMARY KEY (code, period, key));
    """)
    con.execute("INSERT INTO price_daily (date, code, market, close, value) "
                "VALUES ('2026-09-11','000660','KOSDAQ',?,1.0e8)", (close,))
    con.execute("INSERT INTO fundamental VALUES ('000660','2026Q2','rev',?)", (rev,))
    con.commit()
    return con


def selftest() -> int:
    passed, failed = 0, []

    def check(name, fn):
        nonlocal passed
        try:
            fn(); passed += 1
        except Exception as e:                            # noqa: BLE001
            failed.append(f"{name}: {type(e).__name__}: {e}")

    def _assert(c, why=""):
        if not c:
            raise AssertionError(why or "거짓")

    led = P.migrate({"schema": "ki.papers/1", "papers": {
        "amihud2002": {"authors": "A", "year": 2002, "title": "T", "journal": "J",
                       "question": "q2", "adopted": True}}}, at="2026-01-01")

    def _same():
        con = _con(close=88.0)
        r = replay(E._sample(), con, led, at="2026-12-01")
        con.close()
        _assert(r["replayable"] and not r["data_moved"], r)
        _assert(all(o["verdict"] == SAME for o in r["observations"]), r["observations"])
        _assert("읽은 방식" in r["reason"])
    check("자료가 그대로면 '읽은 방식을 보라'고 한다", _same)

    def _data_moved():
        """정정공시로 원장이 덮어써진 경우 — 이 구분이 이 모듈의 존재 이유다."""
        con = _con(close=91.5)                            # 88.0 → 91.5 로 바뀜
        r = replay(E._sample(), con, led, at="2026-12-01")
        con.close()
        _assert(r["data_moved"], r)
        moved = [o for o in r["observations"] if o["verdict"] == DATA_MOVED]
        _assert(len(moved) == 1, r["observations"])
        _assert(moved[0]["then"] == 88.0 and moved[0]["now"] == 91.5)
        _assert("자료가 움직였는지를 먼저" in r["reason"])
    check("자료가 바뀌면 그것부터 보라고 한다", _data_moved)

    def _not_recorded():
        e = E._sample(); e["read"] = []
        con = _con()
        r = replay(e, con, led, at="2026-12-01")
        con.close()
        _assert(not r["replayable"])
        _assert("구분할 수 없" in r["reason"])
        _assert(r["observations"] == [])
    check("읽은 것을 안 적은 봉투는 재생 불가라고 말한다", _not_recorded)

    def _no_value_is_replayable():
        """값이 없는 봉투는 읽은 것이 없어도 재생 가능하다 — 대조할 것이 없을 뿐."""
        e = E._sample(); e["read"] = []; e["value"] = None
        e["reason"] = "일봉이 12개뿐입니다"
        con = _con()
        r = replay(e, con, led, at="2026-12-01")
        con.close()
        _assert(r["replayable"] and not r["data_moved"])
    check("값이 없는 봉투는 재생 불가가 아니다", _no_value_is_replayable)

    def _gone():
        e = E._sample()
        e["read"] = [E.observation("KRX/일별매매정보", "999999.close", 1.0, "2026-09-11")]
        con = _con()
        r = replay(e, con, led, at="2026-12-01")
        con.close()
        _assert(r["observations"][0]["verdict"] == GONE)
        _assert(r["observations"][0]["reason"])           # 사유 없이 비우지 않는다
        _assert(r["data_moved"])
    check("원장에서 사라진 값은 사유와 함께 표시된다", _gone)

    def _fundamental_restatement():
        """정정공시가 가장 자주 덮어쓰는 곳이 재무다."""
        e = E._sample()
        e["read"] = [E.observation("DART/재무", "000660.2026Q2.rev", 1.0, "2026Q2")]
        con = _con(rev=1.4)
        r = replay(e, con, led, at="2026-12-01")
        con.close()
        _assert(r["observations"][0]["verdict"] == DATA_MOVED)
        _assert(r["observations"][0]["now"] == 1.4)
    check("재무 정정을 잡는다", _fundamental_restatement)

    def _no_raw_sql():
        """되짚기가 원장을 헤집는 통로가 되면 안 된다."""
        e = E._sample()
        for bad in ("000660.close; DROP TABLE price_daily",
                    "000660.rowid", "*", "", "a.b.c.d"):
            e["read"] = [E.observation("X", bad, 1.0, "2026-09-11")]
            con = _con()
            r = replay(e, con, led, at="2026-12-01")
            still = con.execute("SELECT COUNT(*) FROM price_daily").fetchone()[0]
            con.close()
            _assert(still == 1, bad)
            _assert(r["observations"][0]["verdict"] in (UNKNOWN_KEY, GONE), bad)
    check("모르는 키는 거절하고 원장을 헤집지 않는다", _no_raw_sql)

    def _float_tolerance():
        e = E._sample()
        e["read"] = [E.observation("KRX", "000660.close", 88.0 + 1e-13, "2026-09-11")]
        con = _con(close=88.0)
        r = replay(e, con, led, at="2026-12-01")
        con.close()
        _assert(r["observations"][0]["verdict"] == SAME)  # 부동소수 잡음은 변화가 아니다
    check("부동소수 잡음을 변화로 읽지 않는다", _float_tolerance)

    def _paper_state_tracked():
        e = E._sample()
        moved = P.record(led, "amihud2002",
                         {"verdict": "재현됨", "observed": {"t": 4.2}}, at="2026-10-01")
        con = _con()
        r = replay(e, con, moved, at="2026-12-01")
        con.close()
        _assert(r["paper"]["state_then"] == "unverified")
        _assert(r["paper"]["state_now"] == "adopted")
        _assert(r["paper"]["moved"])
    check("그때와 지금의 논문 상태가 함께 나온다", _paper_state_tracked)

    def _reads_only():
        con = _con()
        before = con.execute("SELECT COUNT(*) FROM price_daily").fetchone()[0]
        replay(E._sample(), con, led, at="2026-12-01")
        after = con.execute("SELECT COUNT(*) FROM price_daily").fetchone()[0]
        con.close()
        _assert(before == after)
    check("원장을 읽기만 한다", _reads_only)

    def _all():
        con = _con(close=91.5)
        e2 = E._sample(); e2["read"] = []; e2["value"] = None
        e2["reason"] = "일봉 부족"
        r = replay_all([E._sample(), e2], con, led, at="2026-12-01")
        con.close()
        _assert(r["n"] == 2 and r["replayable"] == 2 and r["data_moved"] == 1)
    check("여러 봉투를 한 번에 되짚는다", _all)

    def _no_verdict_words():
        """되짚기는 판정하지 않는다 — 대조표를 낼 뿐이다."""
        con = _con(close=91.5)
        r = replay(E._sample(), con, led, at="2026-12-01")
        con.close()
        blob = json.dumps(r, ensure_ascii=False)
        for w in E.BANNED_WORDS:
            _assert(w not in blob, w)
        _assert("사람이 본다" in replay_all([], con if False else _con(), led)["note"])
    check("되짚기에 판정 어휘가 없다", _no_verdict_words)

    for f in failed:
        print("  X  " + f, file=sys.stderr)
    print(f"replay     {passed} passed, {len(failed)} failed")
    return 1 if failed else 0


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="리플레이 — 봉투를 지금 원장과 대조")
    ap.add_argument("--selftest", action="store_true")
    ap.add_argument("--envelope", help="봉투 JSON 파일")
    ap.add_argument("--envelopes", help="봉투 폴더")
    ap.add_argument("--db")
    ap.add_argument("--indent", type=int, default=2)
    a = ap.parse_args()
    if not (a.envelope or a.envelopes):
        sys.exit(selftest())

    import ki_ledger_mcp as M                             # noqa: E402
    try:
        con = sqlite3.connect(f"file:{a.db}?mode=ro", uri=True) if a.db else M.open_ledger()
    except M.Denied as e:
        print(M._scrub(e), file=sys.stderr)
        sys.exit(1)
    con.row_factory = sqlite3.Row
    led = P.age_states(P.migrate(P.load())) if P.LEDGER.exists() else None
    if a.envelope:
        envs = [json.loads(Path(a.envelope).read_text(encoding="utf-8"))]
    else:
        import run_day as D                               # noqa: E402
        envs = D.load_envelopes(Path(a.envelopes))
    try:
        print(json.dumps(replay_all(envs, con, led), ensure_ascii=False, indent=a.indent))
    finally:
        con.close()
