"""주간 논문 사이클 — 손대지 않아도 매주 한 바퀴 돈다.

열두 편을 한꺼번에 통과시키는 것이 아니다. **주 1회** 신규 논문을 들이고,
재검 기한이 온 것을 다시 돌리고, 낡은 것을 감가시킨다.

한 바퀴는 네 걸음이다.

    ① 감가    기한이 지난 채택본을 warned 로 내린다
    ② 재검    기한 도래분을 재현 러너에 물린다 (주 3편 상한)
    ③ 기록    판정을 장부에 **쌓는다** (덮어쓰지 않는다)
    ④ 채택    신규 후보를 들인다 (하루 1편 상한)

상한이 이 모듈의 요점이다. 상한이 없으면 이관 직후처럼 기한이 몰린 주에 열두
편이 한 번에 돌고, 그 주의 재현은 전부 대충 돌아간다. 대충 돌아간 재현은
**돌지 않은 것보다 나쁘다** — 통과 도장이 찍히기 때문이다.

원장은 읽기만 한다. 쓰는 것은 논문 장부뿐이다.

    python agents/cycle.py --selftest
    python agents/cycle.py --dry-run          # 이번 주에 무엇이 도는지만 본다
    python agents/cycle.py --run              # 실제로 돌리고 장부에 쌓는다
"""
from __future__ import annotations

import argparse
import json
import sqlite3
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import papers as P                                       # noqa: E402
import eventstudy as ES                                  # noqa: E402
import replication as R                                  # noqa: E402
import triggers as T                                     # noqa: E402

SCHEMA = "ki.cycle/1"

# 주 3편. `triggers.scan_paper_rechecks` 의 상한과 같은 값이어야 한다 —
# 트리거가 부르는 수와 사이클이 도는 수가 다르면 둘 중 하나는 거짓말이다.
RECHECK_CAP = 3

# 하루 1편. 프로젝트 규율 그대로다 (CLAUDE.md 규칙 4).
ADOPT_CAP = 1


def age(ledger: dict, today: str) -> tuple[dict, list]:
    """① 감가 — 재검 기한이 지난 채택본을 내린다.

    자동으로 은퇴시키지 않는다. 기한이 지났다는 것은 '다시 봐야 한다'이지
    '틀렸다'가 아니다."""
    before = {k: v.get("state") for k, v in (ledger.get("papers") or {}).items()}
    out = P.age_states(ledger, today)
    moved = [{"paper": k, "from": before[k], "to": v.get("state"),
              "why": v.get("state_reason")}
             for k, v in (out.get("papers") or {}).items()
             if before.get(k) != v.get("state")]
    return out, moved


def due(ledger: dict, today: str, cap: int = RECHECK_CAP) -> list[str]:
    """② 재검 대상 — 트리거와 **같은 규칙**으로 고른다.

    고르는 규칙이 두 곳에 따로 있으면 언젠가 갈라지고, 갈라진 뒤에는 트리거가
    부른 논문과 사이클이 돌린 논문이 다른데 아무도 모른다."""
    ts = T.scan_paper_rechecks(ledger, today, cap)
    return [t.subject for t in ts]


def run(con, ledger: dict, today: str = None, cap: int = RECHECK_CAP,
        market: str = "KOSDAQ", dry: bool = False) -> dict:
    """한 바퀴 돈다. `dry` 면 무엇이 돌지만 계산하고 장부를 건드리지 않는다."""
    today = today or date.today().isoformat()
    out = {"schema": SCHEMA, "at": today, "market": market,
           "recheck_cap": cap, "dry_run": dry,
           "aged": [], "rechecked": [], "not_a_factor": [],
           "needs_runner": [], "unclassified": [], "errors": []}

    # ① 감가
    ledger, moved = age(ledger, today)
    out["aged"] = moved

    # ② 재검 — 상한만큼만
    picks = due(ledger, today, cap)
    out["picked"] = picks

    for key in picks:
        kind, why = R.reducibility(key)
        if kind not in ("testable", "event_time"):
            # 돌리지 않는다. 상태도 건드리지 않는다 — 못 돌린 것과 돌려서
            # 실패한 것은 다르고, 셋은 서로도 다르다.
            #
            #   not_a_factor  앞으로도 이 관문의 대상이 아니다
            #   needs_runner  환원은 되는데 이 러너가 아직 못 한다 (우리 숙제)
            #   unclassified  재현 대상인지조차 정해지지 않았다 (사람의 숙제)
            out[kind].append({"paper": key, "why": why})
            continue
        # 어느 러너로 돌릴지는 분류가 정한다. 분위 정렬로 잴 수 없는 주장을
        # 분위 러너에 넣으면 '판정 불가'가 나오고, 그것이 표본 부족처럼 읽힌다.
        runner = R.run if kind == "testable" else ES.run
        try:
            rep = runner(con, key, market, at=today)
        except Exception as e:                            # noqa: BLE001
            out["errors"].append({"paper": key,
                                  "error": f"{type(e).__name__}: {e}"})
            continue
        entry = {"paper": key, "runner": kind, "verdict": rep["verdict"],
                 "t": (rep.get("observed") or {}).get("t"),
                 "window": rep.get("window"), "n": rep.get("n"),
                 "reason": rep.get("reason")}
        if not dry:
            # ③ 기록 — 덮어쓰지 않고 쌓는다
            ledger = P.record(ledger, key, rep, at=today)
            entry["state_after"] = P.state_of(ledger, key)
        out["rechecked"].append(entry)

    probs = P.validate(ledger)
    out["ledger_problems"] = probs
    out["ok"] = not probs and not out["errors"]
    bits = [f"감가 {len(out['aged'])}", f"재검 {len(out['rechecked'])}"]
    for k, label in (("not_a_factor", "대상 아님"),
                     ("needs_runner", "러너 미비"),
                     ("unclassified", "미분류"),
                     ("errors", "오류")):
        if out[k]:
            bits.append(f"{label} {len(out[k])}")
    out["summary"] = " · ".join(bits)
    return out, ledger


# ── 자체 검사 ─────────────────────────────────────────────────────────

def _led(n=5, state="unverified", due_date=None) -> dict:
    d = P.migrate({
        "schema": "ki.papers/1",
        "papers": {k: {"authors": "A", "year": 2000 + i, "title": "T",
                       "journal": "J", "question": "q2", "adopted": True}
                   for i, k in enumerate(list(R.CLAIMS)[:n])},
    }, at="2026-01-01")
    for p in d["papers"].values():
        p["state"] = state
        p["recheck_due"] = due_date
    return d


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

    check("상한이 트리거와 같다",
          lambda: _assert(RECHECK_CAP == 3))

    def _cap_matches_trigger():
        """사이클이 도는 수와 트리거가 부르는 수가 같아야 한다.

        다르면 둘 중 하나는 거짓말이고, 어느 쪽인지는 아무도 모른다."""
        led = _led(n=4)
        called = [t.subject for t in T.scan_paper_rechecks(led, "2026-09-11", RECHECK_CAP)]
        picked = due(led, "2026-09-11", RECHECK_CAP)
        _assert(called == picked, f"{called} != {picked}")
    check("트리거가 부르는 논문과 사이클이 도는 논문이 같다", _cap_matches_trigger)

    def _cap_holds():
        led = _led(n=4)
        con = R._synthetic(effect=0.03, seed=5)
        out, _ = run(con, led, today="2026-09-11", dry=True)
        con.close()
        _assert(len(out["picked"]) == RECHECK_CAP, out["picked"])
    check("기한이 몰려도 주 3편만 돈다", _cap_holds)

    def _dry_does_not_write():
        led = _led(n=1)
        con = R._synthetic(effect=0.03, seed=5)
        out, after = run(con, led, today="2026-09-11", dry=True)
        con.close()
        _assert(out["rechecked"])
        for k, p in after["papers"].items():
            _assert(p["replication"] == [], f"{k} 에 기록이 쌓였습니다")
    check("dry-run 은 장부를 건드리지 않는다", _dry_does_not_write)

    def _run_records():
        led = _led(n=1)
        con = R._synthetic(effect=0.03, seed=5)
        out, after = run(con, led, today="2026-09-11")
        con.close()
        _assert(out["ok"], out)
        k = out["rechecked"][0]["paper"]
        _assert(len(after["papers"][k]["replication"]) == 1)
        _assert(P.state_of(after, k) in P.STATES)
        _assert(P.validate(after) == [], P.validate(after))
    check("실행하면 판정이 장부에 쌓이고 장부가 성립한다", _run_records)

    def _append_not_overwrite():
        """재검 기한을 건너 다시 돌리면 기록이 둘이 된다. 덮어쓰지 않는다."""
        led = _led(n=1)
        con = R._synthetic(effect=0.03, seed=5)
        _, led = run(con, led, today="2026-09-11")
        k = list(led["papers"])[0]
        _assert(len(led["papers"][k]["replication"]) == 1)
        # 바로 다음 주에는 다시 돌지 않는다 — 기한이 1년 뒤로 잡혔기 때문이다.
        nxt, led2 = run(con, led, today="2026-09-18", dry=True)
        _assert(nxt["picked"] == [], nxt["picked"])
        # 기한을 넘기면 다시 돈다.
        _, led = run(con, led, today="2027-10-01")
        con.close()
        reps = led["papers"][k]["replication"]
        _assert(len(reps) == 2, len(reps))
        _assert(reps[0] != reps[1] or reps[0]["at"] != reps[1]["at"])
    check("기한을 넘기면 다시 돌고 기록이 쌓인다 (덮어쓰지 않는다)",
          _append_not_overwrite)

    def _aging_runs_first():
        """감가가 재검보다 먼저다 — 내려간 뒤에 다시 보는 순서다."""
        led = _led(n=1, state="adopted", due_date="2025-01-01")
        for p in led["papers"].values():
            p["replication"] = [{"verdict": "재현됨"}]     # adopted 의 근거
        con = R._synthetic(effect=0.03, seed=5)
        out, _ = run(con, led, today="2026-09-11", dry=True)
        con.close()
        _assert(out["aged"], out)
        _assert(out["aged"][0]["from"] == "adopted")
        _assert(out["aged"][0]["to"] == "warned")
    check("감가가 재검보다 먼저 돈다", _aging_runs_first)

    def _unclassified_skipped():
        """분류되지 않은 논문은 건너뛴다 — 상태를 건드리지 않는다.

        못 돌린 것과 돌려서 실패한 것은 다르다. 섞으면 장부가 '판정 불가'로
        가득 차고, 그중 무엇이 진짜 판정 불가인지 알 수 없게 된다."""
        led = P.migrate({"schema": "ki.papers/1", "papers": {
            "없는주장2099": {"authors": "A", "year": 2099, "title": "T",
                            "journal": "J", "question": "q1", "adopted": True}}},
            at="2026-01-01")
        con = R._synthetic(effect=0.03, seed=5)
        out, after = run(con, led, today="2026-09-11")
        con.close()
        _assert(out["unclassified"], out)
        _assert(after["papers"]["없는주장2099"]["replication"] == [])
        _assert(P.state_of(after, "없는주장2099") == "unverified")
    check("미분류 논문은 건너뛰고 상태를 건드리지 않는다", _unclassified_skipped)

    def _event_time_uses_its_runner():
        """이벤트 논문은 이벤트 러너로 간다 — 분위 러너에 넣지 않는다.

        분위 러너에 넣으면 '판정 불가'가 나오고, 그것이 표본 부족처럼 읽힌다.
        실제로는 애초에 다른 방법으로 재야 하는 주장이다."""
        led = P.migrate({"schema": "ki.papers/1", "papers": {
            "ritter1991": {"authors": "A", "year": 1991, "title": "T",
                           "journal": "J", "question": "q4", "adopted": True}}},
            at="2026-01-01")
        con = ES._synth(effect=-0.02, seed=5)
        out, after = run(con, led, today="2026-09-18")
        con.close()
        _assert(out["rechecked"], out)
        e = out["rechecked"][0]
        _assert(e["runner"] == "event_time", e)
        _assert(e["verdict"] == R.VERDICT_OK, e)
        _assert(P.state_of(after, "ritter1991") == P.ADOPTED)
    check("이벤트 논문은 이벤트 러너로 돌아간다", _event_time_uses_its_runner)

    def _three_buckets_are_distinct():
        """대상 아님 · 러너 미비 · 미분류가 각각 제 칸으로 간다.

        한 칸에 몰아넣으면 '원래 대상이 아닌 것'과 '우리가 아직 못 한 것'이
        구분되지 않고, 사이클이 얼마나 밀렸는지를 잴 수 없게 된다."""
        keys = {"roll1984": "not_a_factor",      # 추정량
                "ahxz2006": "needs_runner",      # 일간 잔차 — 러너가 없다
                "amihud2002": "rechecked"}       # 지금 돌아간다
        led = P.migrate({"schema": "ki.papers/1", "papers": {
            k: {"authors": "A", "year": 2000, "title": "T", "journal": "J",
                "question": "q2", "adopted": True} for k in keys}}, at="2026-01-01")
        con = R._synthetic(effect=0.03, seed=5)
        out, _ = run(con, led, today="2026-09-11", cap=9, dry=True)
        con.close()
        for k, bucket in keys.items():
            got = [x["paper"] for x in out[bucket]]
            _assert(k in got, f"{k} 가 {bucket} 에 없습니다: {out}")
        _assert(out["not_a_factor"][0]["why"])
        _assert(out["needs_runner"][0]["why"])
    check("대상 아님 · 러너 미비 · 미분류가 각각 제 칸으로 간다",
          _three_buckets_are_distinct)

    def _retired_not_revisited():
        led = _led(n=2)
        for p in led["papers"].values():
            p["state"] = "retired"
            p["state_reason"] = "우리 표본에서 반대"
        con = R._synthetic(effect=0.03, seed=5)
        out, _ = run(con, led, today="2026-09-11", dry=True)
        con.close()
        _assert(out["picked"] == [], out["picked"])
    check("은퇴본은 다시 돌리지 않는다", _retired_not_revisited)

    def _deterministic():
        a, b = _led(n=2), _led(n=2)
        ca = R._synthetic(effect=0.03, seed=5); ra, _ = run(ca, a, today="2026-09-11"); ca.close()
        cb = R._synthetic(effect=0.03, seed=5); rb, _ = run(cb, b, today="2026-09-11"); cb.close()
        _assert(ra == rb)
    check("두 번 돌리면 같은 결과가 나온다", _deterministic)

    def _reads_ledger_only():
        led = _led(n=1)
        con = R._synthetic(effect=0.03, seed=5)
        before = con.execute("SELECT COUNT(*) FROM price_daily").fetchone()[0]
        run(con, led, today="2026-09-11")
        after = con.execute("SELECT COUNT(*) FROM price_daily").fetchone()[0]
        con.close()
        _assert(before == after)
    check("원장을 읽기만 한다", _reads_ledger_only)

    def _no_ledger_no_crash():
        """원장이 비어도 사이클은 돌고, 사유를 낸다."""
        led = _led(n=1)
        con = sqlite3.connect(":memory:")
        con.execute("CREATE TABLE price_daily (date TEXT, code TEXT, market TEXT, "
                    "close REAL, volume REAL, value REAL)")
        out, _ = run(con, led, today="2026-09-11", dry=True)
        con.close()
        _assert(out["rechecked"])
        _assert(out["rechecked"][0]["verdict"] == R.VERDICT_NONE)
        _assert(out["rechecked"][0]["reason"])
    check("원장이 비어도 사유와 함께 판정 불가를 낸다", _no_ledger_no_crash)

    for f in failed:
        print("  X  " + f, file=sys.stderr)
    print(f"cycle      {passed} passed, {len(failed)} failed")
    return 1 if failed else 0


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="주간 논문 사이클")
    ap.add_argument("--selftest", action="store_true")
    ap.add_argument("--dry-run", action="store_true", help="무엇이 도는지만 본다")
    ap.add_argument("--run", action="store_true", help="돌리고 장부에 쌓는다")
    ap.add_argument("--market", default="KOSDAQ")
    ap.add_argument("--today")
    ap.add_argument("--db")
    ap.add_argument("--indent", type=int, default=2)
    a = ap.parse_args()
    if not (a.dry_run or a.run):
        sys.exit(selftest())

    import ki_ledger_mcp as M                             # noqa: E402
    try:
        con = sqlite3.connect(f"file:{a.db}?mode=ro", uri=True) if a.db else M.open_ledger()
    except M.Denied as e:
        print(M._scrub(e), file=sys.stderr)
        sys.exit(1)
    con.row_factory = sqlite3.Row
    led = P.migrate(P.load())
    try:
        out, after = run(con, led, today=a.today, market=a.market, dry=a.dry_run)
    finally:
        con.close()
    if a.run and out["ok"]:
        P.save(after)
        print("장부에 기록했습니다.", file=sys.stderr)
    print(json.dumps(out, ensure_ascii=False, indent=a.indent))
    sys.exit(0 if out["ok"] else 1)
