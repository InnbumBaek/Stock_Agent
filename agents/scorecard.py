"""스코어카드 — 데스크를 계측한다. 다만 자동으로 고치지는 않는다.

무엇이 얼마나 반려됐고 무엇이 재현에 실패했는지를 매주 본다.

**프롬프트를 고치는 것은 사람이다.** 반려율이 높다고 코드가 프롬프트를 손보게
하면, 데스크는 게이트를 통과하는 법을 배우지 게이트가 지키려던 것을 배우지
않는다. 그건 관문을 우회하는 훈련이다.

스코어카드가 실제로 답하는 질문은 하나다 — **이 시스템이 어디서 약한가.**

  · 반려가 몰리는 게이트  → 그 게이트가 요구하는 것을 스킬 문서가 안 가르친다
  · 반려가 몰리는 데스크  → 그 데스크의 질문 경계가 흐리다
  · 승격이 잦은 지점      → 그 일이 생각보다 어렵다
  · 미검증 인용 비율      → 재현 사이클이 밀리고 있다

    python agents/scorecard.py --selftest
    python agents/scorecard.py --runs agents/out/publish
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path

SCHEMA = "ki.scorecard/1"


def _pct(a: int, b: int) -> float | None:
    """없는 값을 만들지 않는다 — 분모가 0 이면 비율이 없다."""
    return None if not b else round(a / b, 4)


def tally(runs: list) -> dict:
    """발행 결과(run_day.publish 산출)들을 모아 센다.

    받은 것만 센다. 빠진 날을 0 으로 채우지 않는다 — 돌지 않은 날과 아무것도
    반려되지 않은 날은 다르다."""
    if not runs:
        return {"schema": SCHEMA, "ok": False, "n_runs": 0,
                "reason": "집계할 발행 기록이 없습니다"}

    per_desk = {}
    gate_fail = Counter()
    marks = Counter()
    tiers = Counter()
    escalated = Counter()
    halted = 0
    n_in = n_pass = n_rej = 0
    incomplete = 0
    retried = 0
    calls = []
    days = []

    for r in runs:
        days.append(r.get("at"))
        if r.get("halt_publication"):
            halted += 1
        n_in += int(r.get("n_in") or 0)
        n_pass += int(r.get("n_passed") or 0)
        n_rej += int(r.get("n_rejected") or 0)
        for row in (r.get("publishable") or []) + (r.get("rejected") or []):
            d = row.get("desk") or "unknown"
            s = per_desk.setdefault(d, {"passed": 0, "rejected": 0, "gates": Counter()})
            ok = not row.get("reason")
            s["passed" if ok else "rejected"] += 1
            # 표시는 **봉투마다** 센다. 발행 단위 목록은 중복이 제거돼 있어서
            # 그것을 세면 "몇 건에 붙었는가"가 아니라 "며칠에 나왔는가"가 된다.
            if ok:
                for m in row.get("marks") or []:
                    marks[m] += 1
            for g in row.get("gates") or []:
                if not g.get("ok"):
                    label = f"{g.get('gate')} {g.get('name')}"
                    gate_fail[label] += 1
                    s["gates"][label] += 1
            env = row.get("envelope") or {}
            if env.get("tier"):
                tiers[env["tier"]] += 1
            if env.get("escalated_from"):
                escalated[f"{env['escalated_from']}→{env.get('tier')}"] += 1
            # 재시도는 승격이 아니다. 따로 세지 않으면, 같은 급에서 두 번
            # 도는 데스크가 "한 번에 통과한 데스크"와 구분되지 않는다.
            if (env.get("attempt") or 1) > 1:
                retried += 1
            sp = env.get("spent") or {}
            if sp.get("completed") is False:
                incomplete += 1
            if isinstance(sp.get("tool_calls"), int):
                calls.append(sp["tool_calls"])

    desks = []
    for d, s in sorted(per_desk.items()):
        tot = s["passed"] + s["rejected"]
        desks.append({
            "desk": d, "n": tot, "passed": s["passed"], "rejected": s["rejected"],
            "pass_rate": _pct(s["passed"], tot),
            "top_gate": (s["gates"].most_common(1)[0][0] if s["gates"] else None),
        })

    # 표시 포화도 — 모든 문장에 붙는 표시는 정보가 아니다.
    #
    # 실제로 그렇게 됐다. 12편이 전부 unverified 라 모든 봉투가 '미검증' 을
    # 달고 나갔다. 그러면 읽는 사람이 그 표시를 배경으로 읽기 시작하고, 정작
    # 한 편만 미검증인 날에도 눈에 띄지 않는다.
    #
    # 임계를 걸어 경고하지 않는다 — 그건 처방이다. 포화도를 재서 낸다.
    sat = []
    for m, n in marks.most_common():
        share = _pct(n, n_pass)
        row = {"mark": m, "n": n, "share": share}
        if share is not None and share >= 1.0:
            row["note"] = ("발행된 모든 문장에 붙었습니다. 모든 것에 붙는 표시는 "
                           "구분하지 못하므로, 읽는 사람에게는 배경입니다.")
        sat.append(row)

    return {
        "schema": SCHEMA, "ok": True,
        "n_runs": len(runs),
        "days": [d for d in days if d],
        "n_envelopes": n_in, "passed": n_pass, "rejected": n_rej,
        "pass_rate": _pct(n_pass, n_in),
        "halted_days": halted,
        "desks": desks,
        "gate_failures": [{"gate": g, "n": c} for g, c in gate_fail.most_common()],
        "marks": sat,
        "tiers": dict(tiers),
        "escalations": [{"path": k, "n": v} for k, v in escalated.most_common()],
        "retried": retried,
        "retried_share": _pct(retried, n_in),
        "escalation_note": ("집행하는 승격 사유는 셋입니다 — 게이트에 두 번 연속 "
                            "반려 · 예산 미완 · 데스크 간 판정이 갈림. 첫 반려는 "
                            "승격이 아니라 같은 급에서의 재시도이고, retried 로 "
                            "따로 셉니다. 리스크 검산 불일치는 위의 '갈림'이 "
                            "덮고, 재현 '판정 불가'는 사이클이 따로 돕니다."),
        # 호출 수만 센다. 토큰은 신뢰성 있게 셀 수 없어 봉투가 담지 않는다.
        "spent": {
            "incomplete": incomplete,
            "incomplete_share": _pct(incomplete, n_in),
            "tool_calls_median": (sorted(calls)[len(calls) // 2] if calls else None),
            "reported": len(calls),
            "note": "호출 수만 셉니다 — 토큰은 에이전트가 신뢰성 있게 세지 못합니다",
        },
        "note": ("계측이지 처방이 아니다. 반려가 몰리는 게이트는 그 게이트가 "
                 "요구하는 것을 스킬 문서가 가르치지 않는다는 뜻이고, 고치는 "
                 "것은 사람이다."),
    }


def papers_health(ledger: dict) -> dict:
    """논문 장부가 건강한가 — 재현 사이클이 밀리고 있지 않은가."""
    ps = (ledger or {}).get("papers") or {}
    if not ps:
        return {"ok": False, "reason": "논문 장부가 비어 있습니다"}
    st = Counter(p.get("state") for p in ps.values())
    n = len(ps)
    return {
        "ok": True, "n": n, "states": dict(st),
        "unverified_share": _pct(st.get("unverified", 0), n),
        "citable": st.get("unverified", 0) + st.get("adopted", 0) + st.get("warned", 0),
        "blocked": st.get("retired", 0),
        "note": ("미검증 비율이 줄지 않으면 재현 사이클이 밀리고 있다는 뜻이다. "
                 "인용이 막히는 것은 retired 뿐이므로, 막히지 않는다고 해서 "
                 "괜찮다는 뜻은 아니다."),
    }


def load_runs(d: Path) -> list:
    out = []
    for f in sorted(d.glob("*.json")):
        try:
            j = json.loads(f.read_text(encoding="utf-8"))
        except ValueError:
            continue
        if j.get("stage") == "publish":
            out.append(j)
    return out


# ── 자체 검사 ─────────────────────────────────────────────────────────

def _run(at, rows, halt=False, marks=()):
    """rows: (desk, 통과여부, 실패게이트, tier). marks 는 통과한 봉투마다 붙는다."""
    pub, rej = [], []
    for desk, ok, gate, tier in rows:
        gates = [{"gate": "①", "name": "판정 어휘", "ok": True}]
        if not ok:
            gates = [{"gate": gate[0], "name": gate[1], "ok": False}]
        row = {"instance": f"{desk}-x", "desk": desk, "claim": "c", "gates": gates}
        if ok:
            pub.append({**row, "marks": list(marks), "envelope": {"tier": tier}})
        else:
            rej.append({**row, "reason": f"{gate[0]} {gate[1]}: 사유"})
    return {"schema": "ki.day/1", "stage": "publish", "at": at,
            "n_in": len(rows), "n_passed": len(pub), "n_rejected": len(rej),
            "halt_publication": halt,
            "publishable": [] if halt else pub, "rejected": rej,
            "marks": list(marks)}


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

    def _empty():
        r = tally([])
        _assert(not r["ok"] and r["reason"])   # 0 으로 채우지 않는다
        _assert("pass_rate" not in r)
    check("기록이 없으면 사유를 낸다 (0 으로 채우지 않는다)", _empty)

    def _basic():
        r = tally([_run("2026-09-11", [
            ("q2-disposal", True, None, "T2"),
            ("q2-disposal", False, ("④", "논문 실재"), "T2"),
            ("q1-progress", True, None, "T1"),
        ])])
        _assert(r["ok"] and r["n_envelopes"] == 3)
        _assert(r["passed"] == 2 and r["rejected"] == 1)
        _assert(r["pass_rate"] == round(2 / 3, 4))
        by = {d["desk"]: d for d in r["desks"]}
        _assert(by["q2-disposal"]["pass_rate"] == 0.5)
        _assert(by["q2-disposal"]["top_gate"] == "④ 논문 실재")
        _assert(by["q1-progress"]["pass_rate"] == 1.0)
    check("데스크별 통과율과 반려가 몰리는 게이트를 센다", _basic)

    def _gate_ranking():
        r = tally([_run("2026-09-11", [
            ("q2-disposal", False, ("④", "논문 실재"), "T2"),
            ("q1-progress", False, ("④", "논문 실재"), "T2"),
            ("q3-execution", False, ("⑤", "신선도"), "T2"),
        ])])
        _assert(r["gate_failures"][0] == {"gate": "④ 논문 실재", "n": 2})
        _assert(r["gate_failures"][1]["n"] == 1)
    check("반려가 몰리는 게이트가 위로 온다", _gate_ranking)

    def _halt_counted():
        r = tally([_run("2026-09-11", [("q2-disposal", True, None, "T2")], halt=True)])
        _assert(r["halted_days"] == 1)
        # 통과한 것이 있었다는 사실은 남되, 발행되지는 않았다
        _assert(r["passed"] == 1)
        _assert(r["desks"] == [] or all(d["n"] >= 0 for d in r["desks"]))
    check("발행이 멈춘 날이 따로 세어진다", _halt_counted)

    def _marks():
        r = tally([_run("2026-09-11", [("q2-disposal", True, None, "T2")],
                        marks=["미검증 — 우리 표본으로 재현해 본 적 없음"])])
        _assert(r["marks"][0]["n"] == 1)
        _assert("미검증" in r["marks"][0]["mark"])
    check("값에 붙은 표시를 센다", _marks)

    def _mark_saturation():
        """모든 문장에 붙은 표시를 그렇다고 말한다.

        실제로 그렇게 됐다 — 12편이 전부 unverified 라 모든 봉투가 '미검증' 을
        달고 나갔다. 그러면 그 표시는 배경이 된다."""
        M = "미검증 — 우리 표본으로 재현해 본 적 없음"
        r = tally([_run("2026-09-18", [("q2-disposal", True, None, "T2"),
                                       ("q1-progress", True, None, "T2")], marks=[M])])
        _assert(r["marks"][0]["share"] == 1.0, r["marks"])
        _assert("배경" in r["marks"][0]["note"])
        # 일부에만 붙으면 경고하지 않는다 — 그때는 표시가 구분을 한다.
        run = _run("2026-09-18", [("q2-disposal", True, None, "T2"),
                                  ("q1-progress", True, None, "T2")], marks=[M])
        run["publishable"][1]["marks"] = []      # 둘 중 하나만 미검증
        r2 = tally([run])
        _assert(r2["marks"][0]["share"] == 0.5, r2["marks"])
        _assert("note" not in r2["marks"][0], r2["marks"])
    check("모든 문장에 붙은 표시를 그렇다고 말한다", _mark_saturation)

    def _spent_counted():
        """미완과 호출 수를 센다. 토큰은 세지 않는다."""
        run = _run("2026-09-18", [("q2-disposal", True, None, "T2")])
        run["publishable"][0]["envelope"] = {"tier": "T2",
            "spent": {"tool_calls": 18, "completed": False, "why": "예산 초과"}}
        r = tally([run])
        _assert(r["spent"]["incomplete"] == 1)
        _assert(r["spent"]["tool_calls_median"] == 18)
        _assert("토큰" in r["spent"]["note"])
        _assert("tokens" not in json.dumps(r["spent"]))
    check("미완과 호출 수를 세고 토큰은 세지 않는다", _spent_counted)

    def _retry_counted_separately():
        """재시도는 승격이 아니다 — 따로 세지 않으면 한 번에 통과한 것과 같아 보인다."""
        run = _run("2026-09-18", [("q2-disposal", True, None, "T2"),
                                  ("q1-progress", True, None, "T2")])
        run["publishable"][0]["envelope"] = {"tier": "T2", "attempt": 2}
        run["publishable"][1]["envelope"] = {"tier": "T2", "attempt": 1}
        r = tally([run])
        _assert(r["retried"] == 1, r)
        _assert(r["retried_share"] == 0.5)
        _assert(r["escalations"] == [])          # 재시도는 승격으로 안 센다
    check("재시도를 승격과 따로 센다", _retry_counted_separately)

    def _escalation_note_matches_code():
        """문구가 실제 집행 사유와 맞는가. 안 맞으면 그 문구가 규칙처럼 읽힌다."""
        import run_day as D
        r = tally([_run("2026-09-18", [("q2-disposal", True, None, "T2")])])
        _assert("셋" in r["escalation_note"], r["escalation_note"])
        _assert(len(D.ESCALATABLE) == 3)
        _assert("두 번 연속" in r["escalation_note"])
    check("승격 문구가 실제 집행 사유와 맞는다", _escalation_note_matches_code)

    def _escalation_counted():
        run = _run("2026-09-18", [("q2-disposal", True, None, "T3")])
        run["publishable"][0]["envelope"] = {"tier": "T3", "escalated_from": "T2"}
        r = tally([run])
        _assert(r["escalations"] == [{"path": "T2→T3", "n": 1}], r["escalations"])
        _assert("셋" in r["escalation_note"])
    check("승격 분포를 센다 (이제 실제로 채워지는 칸이다)", _escalation_counted)

    def _tiers():
        r = tally([_run("2026-09-11", [("q1-progress", True, None, "T1"),
                                       ("q2-disposal", True, None, "T2"),
                                       ("quant-method", True, None, "T3")])])
        _assert(r["tiers"] == {"T1": 1, "T2": 1, "T3": 1})
    check("급별 분포를 센다", _tiers)

    def _multi_day():
        r = tally([_run("2026-09-11", [("q2-disposal", True, None, "T2")]),
                   _run("2026-09-12", [("q2-disposal", False, ("①", "판정 어휘"), "T2")])])
        _assert(r["n_runs"] == 2 and r["days"] == ["2026-09-11", "2026-09-12"])
        _assert(r["pass_rate"] == 0.5)
    check("여러 날을 모아 센다", _multi_day)

    def _no_prescription():
        """처방을 내지 않는다 — 계측만 한다."""
        r = tally([_run("2026-09-11", [("q2-disposal", False, ("①", "판정 어휘"), "T2")])])
        blob = json.dumps(r, ensure_ascii=False)
        for w in ("프롬프트를 고쳐라", "자동으로", "수정했", "재학습"):
            _assert(w not in blob or "사람이" in blob, w)
        _assert("사람이" in r["note"])
    check("처방하지 않는다 (고치는 것은 사람이다)", _no_prescription)

    def _papers_health():
        import papers as P
        led = P.migrate({"schema": "ki.papers/1", "papers": {
            "a": {"authors": "A", "year": 2000, "title": "T", "journal": "J",
                  "question": "q1", "adopted": True},
            "b": {"authors": "B", "year": 2001, "title": "T", "journal": "J",
                  "question": "q2", "adopted": False}}}, at="2026-01-01")
        h = papers_health(led)
        _assert(h["ok"] and h["n"] == 2)
        _assert(h["states"]["unverified"] == 1 and h["states"]["retired"] == 1)
        _assert(h["unverified_share"] == 0.5)
        _assert(h["citable"] == 1 and h["blocked"] == 1)
    check("논문 장부의 건강 상태를 낸다", _papers_health)

    def _papers_health_empty():
        _assert(not papers_health({})["ok"])
        _assert(papers_health({}).get("reason"))
    check("장부가 비면 사유를 낸다", _papers_health_empty)

    def _load_skips_non_publish():
        import tempfile
        with tempfile.TemporaryDirectory() as d:
            p = Path(d)
            (p / "a.json").write_text(json.dumps(_run("2026-09-11", [
                ("q2-disposal", True, None, "T2")]), ensure_ascii=False), encoding="utf-8")
            (p / "b.json").write_text(json.dumps({"stage": "convene"}), encoding="utf-8")
            (p / "c.json").write_text("{깨진", encoding="utf-8")
            runs = load_runs(p)
            _assert(len(runs) == 1, len(runs))
    check("발행 기록만 골라 읽는다", _load_skips_non_publish)

    for f in failed:
        print("  X  " + f, file=sys.stderr)
    print(f"scorecard  {passed} passed, {len(failed)} failed")
    return 1 if failed else 0


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="스코어카드 (계측만 한다)")
    ap.add_argument("--selftest", action="store_true")
    ap.add_argument("--runs", help="발행 기록 폴더")
    ap.add_argument("--indent", type=int, default=2)
    a = ap.parse_args()
    if not a.runs:
        sys.exit(selftest())
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    import papers as P                                    # noqa: E402
    out = {"desks": tally(load_runs(Path(a.runs)))}
    if P.LEDGER.exists():
        out["papers"] = papers_health(P.age_states(P.migrate(P.load())))
    print(json.dumps(out, ensure_ascii=False, indent=a.indent))
