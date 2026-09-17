"""하루 운영 — 소집에서 발행까지.

`SCHEDULE.cmd` 의 07:30 · 08:50 · 16:10 을 **바꾸지 않는다.** 그 사이에
소집·게이트·조립을 끼워 넣는다.

    07:30  수확 · 재현 배치      cycle.py (배치다. 에이전트가 아니다)
    08:50  리포트 + 소집         이 파일 --stage convene
    장중   읽기만                데스크는 돌지 않는다
    16:10  종가 적재             data-ops 단독. 그날의 유일한 원장 쓰기
    17:00  게이트 → 조립         이 파일 --stage publish

**장중에 데스크를 돌리지 않는 이유** — 일봉 장부 위에 세운 해석을 장중 값과
섞으면 무엇을 근거로 읽었는지가 시각마다 달라진다. 하루 한 번, 같은 기준일
위에서만 읽는다.

## 이 파일이 하지 않는 것

데스크를 **대신 생각해 주지 않는다.** `convene` 이 내는 것은 작업지시서다 —
누구를, 어떤 입력으로, 어떤 예산 안에서 부를 것인가. 실제 판단은 그 지시서를
받은 인스턴스가 한다. `publish` 는 돌아온 봉투를 게이트에 통과시킨다.

그 사이가 비어 있는 것은 설계다. 오케스트레이터가 판단에 손을 대면 데스크의
격리가 형식만 남는다.

    python agents/run_day.py --selftest
    python agents/run_day.py --stage convene --since 2026-09-10
    python agents/run_day.py --stage publish --envelopes agents/envelopes
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
import gates as G                                        # noqa: E402
import papers as P                                       # noqa: E402
import triggers as T                                     # noqa: E402

SCHEMA = "ki.day/1"

# ── 예산 ──────────────────────────────────────────────────────────────
#
# 인스턴스마다 상한이 있다. 넘으면 **그대로 중단된다** — 조용히 줄여서
# 그럴듯한 답을 내는 것이 가장 나쁜 실패다. 미완은 미완이라고 적혀야 한다.
BUDGET = {
    "T1": {"tool_calls": 6, "tokens": 12000},    # 정형 추출. 답이 하나로 정해진다
    "T2": {"tool_calls": 18, "tokens": 40000},   # 해석·서술. 대부분이 여기다
    "T3": {"tool_calls": 40, "tokens": 90000},   # 이견·재현 설계. 틀리면 비싸다
}


def work_order(trigger: dict, desk: str, at: str) -> dict:
    """작업지시서 하나. 데스크가 볼 수 있는 것은 여기 담긴 것이 전부다.

    원장 연결도, 다른 종목 목록도, 다른 인스턴스의 산출도 넣지 않는다.
    넣는 순간 격리가 형식만 남는다."""
    tier = trigger.get("tier", "T2")
    subject = str(trigger.get("inputs", {}).get("code")
                  or trigger.get("subject") or "na")
    return {
        "instance": E.new_instance(desk, at, subject,
                                   salt=f"{trigger['kind']}:{trigger['subject']}"),
        "desk": desk,
        "tier": tier,
        "budget": dict(BUDGET[tier]),
        "trigger": {"kind": trigger["kind"], "subject": trigger["subject"],
                    "why": trigger["why"]},
        "inputs": dict(trigger.get("inputs") or {}),
        "tools": ["mcp__ki-ledger__*"],
        "must": [
            "봉투 하나를 낸다 (agents/envelope.py 형식)",
            "source_grade 는 '해석' 이다 — 1차로 올리지 않는다",
            "limits 를 비워 두지 않는다",
            "값이 없으면 reason 을 적는다. 0 으로 채우지 않는다",
            "예산을 넘기면 reason 에 '미완' 으로 적는다",
        ],
    }


def convene(con, at: str = None, since: str = None,
            paper_ledger: dict = None) -> dict:
    """08:50 — 트리거를 훑어 작업지시서를 낸다.

    트리거가 없으면 지시서도 없다. 조용한 날은 조용한 것이 정상이다."""
    at = at or date.today().isoformat()
    scan = T.scan(con, today=at, since=since, paper_ledger=paper_ledger)
    orders = [work_order(t, d, at) for t in scan["triggers"] for d in t["desks"]]
    cost = {k: sum(o["budget"][k] for o in orders) for k in ("tool_calls", "tokens")}
    return {
        "schema": SCHEMA, "stage": "convene", "at": at, "since": scan["since"],
        "standing": scan["standing"],
        "triggers": scan["n"],
        "orders": orders, "n": len(orders),
        "budget_ceiling": cost,
        "idle": scan["idle"],
        "note": ("작업지시서다. 판단은 여기 없다 — 지시서를 받은 인스턴스가 한다. "
                 "예산은 상한이지 목표가 아니다."),
    }


def publish(envelopes: list, ledger: dict, at: str = None) -> dict:
    """17:00 — 돌아온 봉투를 게이트에 건다.

    반려된 절은 **빈칸이 아니다.** '반려됨 — 사유' 로 남는다. 빈칸은 아무도
    묻지 않지만 '반려됨'은 반드시 묻게 된다."""
    at = at or date.today().isoformat()
    passed, rejected, marks = [], [], []
    halt = False
    for env in envelopes:
        r = G.run(env, ledger)
        row = {"instance": env.get("instance"), "desk": env.get("desk"),
               "claim": env.get("claim"), "gates": r["results"]}
        if r["halt_publication"]:
            halt = True
        if r["ok"]:
            passed.append({**row, "marks": r["marks"], "envelope": env})
            marks += r["marks"]
        else:
            rejected.append({**row, "reason": r["reason"]})
    return {
        "schema": SCHEMA, "stage": "publish", "at": at,
        "n_in": len(envelopes), "n_passed": len(passed), "n_rejected": len(rejected),
        # 유출이 하나라도 있으면 절이 아니라 발행 전체를 멈춘다. 되돌릴 수 없어서,
        # 다른 절이 멀쩡한지는 이 판단에 영향을 주지 않는다.
        "halt_publication": halt,
        "publishable": [] if halt else passed,
        "rejected": rejected,
        "marks": sorted(set(marks)),
        "note": ("반려는 빈칸이 아니라 '반려됨 — 사유' 로 회의자료에 남는다. "
                 "조용히 통과시키는 것이 가장 위험하다."),
    }


def load_envelopes(d: Path) -> list:
    out = []
    for f in sorted(d.glob("*.json")):
        try:
            out.append(json.loads(f.read_text(encoding="utf-8")))
        except ValueError as e:
            out.append({"claim": f"봉투를 읽지 못했습니다: {f.name}",
                        "reason": str(e), "desk": "unknown"})
    return out


# ── 자체 검사 ─────────────────────────────────────────────────────────

def selftest() -> int:
    passed_n, failed = 0, []

    def check(name, fn):
        nonlocal passed_n
        try:
            fn(); passed_n += 1
        except Exception as e:                            # noqa: BLE001
            failed.append(f"{name}: {type(e).__name__}: {e}")

    def _assert(c, why=""):
        if not c:
            raise AssertionError(why or "거짓")

    led = G._ledger()

    def _busy():
        con = T._ledger(
            rows_price=[("2026-09-10", "000660", "KOSDAQ", 100.0),
                        ("2026-09-11", "000660", "KOSDAQ", 88.0)],
            disclosures=[("R1", "000660", "2026-09-11", "전환가액의조정", "refix")])
        r = convene(con, at="2026-09-11", since="2026-09-10")
        con.close()
        _assert(r["n"] == 3, r["n"])          # 공시 1 + 변동 2데스크
        _assert(all(o["desk"] in T.DESKS for o in r["orders"]))
        _assert(r["budget_ceiling"]["tool_calls"] > 0)
    check("소집이 작업지시서를 낸다", _busy)

    def _quiet():
        con = T._ledger(rows_price=[("2026-09-10", "000660", "KOSDAQ", 100.0),
                                    ("2026-09-11", "000660", "KOSDAQ", 100.5)])
        r = convene(con, at="2026-09-11", since="2026-09-10")
        con.close()
        _assert(r["n"] == 0 and r["orders"] == [])
        _assert(r["budget_ceiling"]["tokens"] == 0)
        _assert(r["standing"] == list(T.STANDING))
    check("조용한 날은 지시서가 없다 (상설은 돈다)", _quiet)

    def _budget_by_tier():
        con = T._ledger(disclosures=[("R1", "000660", "2026-09-11", "기타", "")])
        r = convene(con, at="2026-09-11", since="2026-09-10")
        con.close()
        o = r["orders"][0]
        _assert(o["tier"] == "T1")            # 공시 분류는 정형 추출이다
        _assert(o["budget"] == BUDGET["T1"])
        _assert(o["budget"] is not BUDGET["T1"])   # 복사본이어야 한다
    check("예산은 급에 따라 다르고 복사본이다", _budget_by_tier)

    def _budget_t3_for_replication():
        led2 = {"papers": {"p": {"state": "unverified", "recheck_due": None,
                                 "question": "q1"}}}
        con = T._ledger()
        r = convene(con, at="2026-09-11", paper_ledger=led2)
        con.close()
        _assert(r["orders"][0]["tier"] == "T3")
        _assert(r["orders"][0]["budget"]["tool_calls"] == BUDGET["T3"]["tool_calls"])
    check("재현 설계는 상위 급 예산을 받는다", _budget_t3_for_replication)

    def _order_is_closed():
        """지시서에 원장 연결이나 남의 산출이 실리지 않는가 (격리)."""
        con = T._ledger(disclosures=[("R1", "000660", "2026-09-11", "전환가액의조정", "refix")])
        r = convene(con, at="2026-09-11", since="2026-09-10")
        con.close()
        blob = json.dumps(r, ensure_ascii=False)          # 직렬화되는가
        _assert(blob)
        for o in r["orders"]:
            _assert(set(o) == {"instance", "desk", "tier", "budget", "trigger",
                               "inputs", "tools", "must"}, set(o))
            _assert(o["tools"] == ["mcp__ki-ledger__*"])
            for v in o["inputs"].values():
                _assert(isinstance(v, (str, int, float, list, type(None))))
    check("지시서는 닫혀 있고 읽기 도구만 준다", _order_is_closed)

    def _instance_unique():
        """같은 데스크가 두 트리거로 불리면 인스턴스가 달라야 한다."""
        con = T._ledger(
            disclosures=[("R1", "000660", "2026-09-11", "전환가액의조정", "refix"),
                         ("R2", "000660", "2026-09-11", "임원소유상황보고", "insider")])
        r = convene(con, at="2026-09-11", since="2026-09-10")
        con.close()
        ids = [o["instance"] for o in r["orders"]]
        _assert(len(ids) == len(set(ids)), ids)
    check("인스턴스 ID 가 지시서마다 다르다", _instance_unique)

    def _publish_clean():
        env = G._env()
        r = publish([env], led, at="2026-09-11")
        _assert(r["n_passed"] == 1 and r["n_rejected"] == 0)
        _assert(not r["halt_publication"])
        _assert(any("미검증" in m for m in r["marks"]))
    check("통과한 봉투가 발행 목록에 오른다", _publish_clean)

    def _publish_rejects_with_reason():
        bad = G._env(claim="희석 4.2% — 매도 검토")
        r = publish([bad], led, at="2026-09-11")
        _assert(r["n_rejected"] == 1 and r["publishable"] == [])
        _assert(r["rejected"][0]["reason"])   # 빈칸이 아니라 사유가 남는다
        _assert(len(r["rejected"][0]["gates"]) == 7)
    check("반려는 사유와 함께 남는다 (빈칸이 아니다)", _publish_rejects_with_reason)

    def _leak_halts_everything():
        """유출 하나가 멀쩡한 절까지 멈춘다. 되돌릴 수 없기 때문이다."""
        good = G._env()
        leak = G._env(reason="https://opendart.fss.or.kr/api/list.json?crtfc_key=XYZ&c=1")
        r = publish([good, leak], led, at="2026-09-11")
        _assert(r["halt_publication"])
        _assert(r["publishable"] == [], "유출이 있는데 발행됐습니다")
        _assert(r["n_passed"] == 1)           # 통과한 것이 있었다는 사실은 남는다
    check("유출은 발행 전체를 멈춘다", _leak_halts_everything)

    def _mixed():
        r = publish([G._env(), G._env(stale_days=99), G._env(limits=[])],
                    led, at="2026-09-11")
        _assert(r["n_in"] == 3 and r["n_passed"] == 1 and r["n_rejected"] == 2)
    check("통과와 반려가 섞여도 둘 다 보고된다", _mixed)

    def _broken_envelope_file():
        import tempfile
        with tempfile.TemporaryDirectory() as d:
            p = Path(d)
            (p / "a.json").write_text(json.dumps(G._env(), ensure_ascii=False),
                                      encoding="utf-8")
            (p / "b.json").write_text("{깨진", encoding="utf-8")
            envs = load_envelopes(p)
            _assert(len(envs) == 2)
            r = publish(envs, led, at="2026-09-11")
            # 깨진 파일은 조용히 사라지지 않고 반려로 남는다
            _assert(r["n_rejected"] == 1 and r["n_passed"] == 1)
    check("깨진 봉투 파일은 조용히 사라지지 않고 반려된다", _broken_envelope_file)

    def _no_envelopes():
        r = publish([], led, at="2026-09-11")
        _assert(r["n_in"] == 0 and not r["halt_publication"])
        _assert(r["publishable"] == [])
    check("봉투가 없으면 발행도 없다", _no_envelopes)

    def _deterministic():
        rows = [("2026-09-10", "000660", "KOSDAQ", 100.0),
                ("2026-09-11", "000660", "KOSDAQ", 88.0)]
        a = T._ledger(rows_price=rows); ra = convene(a, at="2026-09-11", since="2026-09-10"); a.close()
        b = T._ledger(rows_price=rows); rb = convene(b, at="2026-09-11", since="2026-09-10"); b.close()
        _assert(ra == rb)
    check("두 번 소집하면 같은 지시서가 나온다", _deterministic)

    def _tiers_all_budgeted():
        _assert(set(BUDGET) == {"T1", "T2", "T3"})
        _assert(set(BUDGET) == set(E.TIERS))
        for t in ("T1", "T2", "T3"):
            _assert(BUDGET[t]["tool_calls"] > 0 and BUDGET[t]["tokens"] > 0)
        _assert(BUDGET["T1"]["tokens"] < BUDGET["T2"]["tokens"] < BUDGET["T3"]["tokens"])
    check("세 급 모두 예산이 있고 위로 갈수록 크다", _tiers_all_budgeted)

    for f in failed:
        print("  X  " + f, file=sys.stderr)
    print(f"run_day    {passed_n} passed, {len(failed)} failed")
    return 1 if failed else 0


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="하루 운영 — 소집 · 발행")
    ap.add_argument("--selftest", action="store_true")
    ap.add_argument("--stage", choices=["convene", "publish"])
    ap.add_argument("--since")
    ap.add_argument("--at")
    ap.add_argument("--db")
    ap.add_argument("--envelopes", default="agents/envelopes")
    ap.add_argument("--indent", type=int, default=2)
    a = ap.parse_args()
    if not a.stage:
        sys.exit(selftest())

    led = P.age_states(P.migrate(P.load())) if P.LEDGER.exists() else None
    if a.stage == "convene":
        import ki_ledger_mcp as M                         # noqa: E402
        try:
            con = sqlite3.connect(f"file:{a.db}?mode=ro", uri=True) if a.db else M.open_ledger()
        except M.Denied as e:
            print(M._scrub(e), file=sys.stderr)
            sys.exit(1)
        con.row_factory = sqlite3.Row
        try:
            out = convene(con, at=a.at, since=a.since, paper_ledger=led)
        finally:
            con.close()
    else:
        d = Path(a.envelopes)
        if not d.exists():
            print(f"봉투 폴더가 없습니다: {d}", file=sys.stderr)
            sys.exit(1)
        out = publish(load_envelopes(d), led, at=a.at)
    print(json.dumps(out, ensure_ascii=False, indent=a.indent))
    sys.exit(1 if out.get("halt_publication") else 0)
