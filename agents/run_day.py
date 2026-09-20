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
import dispatch as D                                     # noqa: E402
import papers as P                                       # noqa: E402
import reconcile as RC                                   # noqa: E402
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


def publish(envelopes: list, ledger: dict, at: str = None,
            orders: list = None) -> dict:
    """17:00 — 돌아온 봉투를 게이트에 건다.

    반려된 절은 **빈칸이 아니다.** '반려됨 — 사유' 로 남는다. 빈칸은 아무도
    묻지 않지만 '반려됨'은 반드시 묻게 된다.

    `orders` 를 주면 **시킨 것과 돌아온 것을 짝지어** 본다 (`dispatch.py`).
    이것 없이는 봉투 폴더에 있는 것을 전부 받는다 — 그러면 소집했는데 안 온
    절이 '조용한 날'과 똑같이 생기고, 시킨 적 없는 봉투가 근거 있는 숫자 옆에
    나란히 선다."""
    at = at or date.today().isoformat()
    # `orders is None` 만 '대조 안 함'이다. 빈 목록은 **소집이 0건이었다**는
    # 뜻이고, 그날 온 봉투는 전부 무단이다.
    matched = orders is not None
    rec = D.reconcile(orders or [], envelopes)
    # 무단 봉투의 **번호만** 따로 둔다. 목록에서 빼지는 않는다 —
    # 게이트 ⑥(자격증명 유출)은 예외가 없어야 하기 때문이다. 빼고 돌렸더니
    # 키가 든 무단 봉투 하나가 발행을 멈추지 못하고 그대로 통과했다.
    # 유출은 되돌릴 수 없어서, 그 봉투를 발행하지 않는다는 것과 그 봉투를
    # 검사하지 않는다는 것은 전혀 다른 이야기다.
    # 번호가 있는 것만 담는다. `None` 을 넣으면 instance 가 아예 없는 봉투가
    # 전부 여기 걸려, 진짜 사유(읽지 못했다·형식이 깨졌다)가 "시킨 적 없는
    # 봉투" 로 바뀐다. 그 봉투는 게이트의 형식 검사가 제 사유로 반려한다.
    withheld_inst = ({r["instance"] for r in rec[D.UNASKED] if r["instance"]}
                     if matched else set())
    passed, rejected, marks = [], [], list(D.marks(rec)) if matched else []
    withheld = []
    halt = False
    for env in envelopes:
        r = G.run(env, ledger)                  # 전부 건다. 예외 없다.
        row = {"instance": env.get("instance"), "desk": env.get("desk"),
               "claim": env.get("claim"), "gates": r["results"]}
        if r["halt_publication"]:
            halt = True
        if env.get("instance") in withheld_inst:
            # 게이트는 걸었다. 다만 어느 소집에서 나왔는지 모르므로 발행하지
            # 않는다 — 되짚을 수 없는 주장이다.
            row = {**row, "reason": "시킨 적 없는 봉투입니다 — 어느 소집에서 "
                                    "나왔는지 알 수 없어 발행하지 않습니다"}
            withheld.append(row)
            rejected.append(row)
            continue
        if r["ok"]:
            passed.append({**row, "marks": r["marks"], "envelope": env})
            marks += r["marks"]
        else:
            rejected.append({**row, "reason": r["reason"]})
    # 안 온 절도 빈칸이 아니다. '미이행 — 사유' 로 회의자료에 남는다.
    missing = [{"instance": r["instance"], "desk": r["desk"], "claim": None,
                "gates": [], "reason": r["why"]} for r in rec[D.MISSING]]
    rejected += missing
    return {
        "schema": SCHEMA, "stage": "publish", "at": at,
        "dispatch": {**{k: v for k, v in rec.items() if k != "schema"},
                     "summary": D.summary(rec)} if matched else None,
        # `n_in` 은 **돌아온 봉투 수**다. 여기에 미이행을 섞으면 스코어카드가
        # 그 수로 통과율을 나눠, 아무도 보고하지 않은 날이 100% 로 보인다.
        "n_in": len(envelopes), "n_passed": len(passed),
        "n_rejected": len(rejected),
        "n_missing": len(missing), "n_withheld": len(withheld),
        # 유출이 하나라도 있으면 절이 아니라 발행 전체를 멈춘다. 되돌릴 수 없어서,
        # 다른 절이 멀쩡한지는 이 판단에 영향을 주지 않는다.
        "halt_publication": halt,
        "publishable": [] if halt else passed,
        "rejected": rejected,
        "marks": sorted(set(marks)),
        "note": ("반려는 빈칸이 아니라 '반려됨 — 사유' 로 회의자료에 남는다. "
                 "조용히 통과시키는 것이 가장 위험하다."),
    }


# ── 승격 ──────────────────────────────────────────────────────────────
#
# 덱이 적은 승격 조건 다섯 중 **지금 집행할 수 있는 둘**만 여기서 본다.
#
#   ○ 게이트에 반려됐다            publish 결과가 안다
#   ○ 예산 안에서 끝내지 못했다     봉투의 spent.completed 가 안다
#   ○ 두 데스크의 판정이 갈렸다     reconcile 이 기계적으로 찾는다
#   ✕ 리스크 검산 불일치           risk-officer 가 봉투를 내야 안다 — 다만
#                                  그 봉투가 오면 위의 '갈렸다'로 잡힌다
#   ✕ 재현이 '판정 불가'           quant-method 쪽 사이클이 따로 돈다
#
# 없는 조건을 있는 척 세지 않는다. 스코어카드가 세는 승격 분포는 위 셋의
# 분포이고, 그 사실이 산출에 적혀 나간다.

ESCALATABLE = ("gate_rejected", "budget_incomplete", "desks_disagree")

# 반려는 **두 번 연속**일 때만 올린다. 첫 반려는 같은 급에서 다시 한다.
#
# 금지어 하나를 고치는 데 T3 인스턴스를 띄우는 것은 낭비다. 게이트 반려는
# 대개 그 급에서 고칠 수 있는 것이고(문장 삭제·한계 보강), 한 번에 올리면
# 승격 분포가 "어디가 어려운가"가 아니라 "어디서 실수가 잦은가"가 된다.
#
# 나머지 둘은 한 번에 올린다.
#   · 예산 미완 — 같은 급에서 다시 하면 같은 벽에 부딪힌다
#   · 판정이 갈림 — 같은 데스크를 다시 돌려도 상대와의 차이는 그대로다
RETRY_FIRST = ("gate_rejected",)


def _assumes_of(env: dict) -> dict:
    """봉투의 가정. `method` 는 없을 수 있다 — 논문을 안 쓴 데스크도 있고,
    ⑦ 4-eyes 반려처럼 method 가 비어 있는 채로 오는 경우가 흔하다.

    여기서 터지면 그 한 건이 아니라 **승격 단계 전체**가 죽는다. 다른 승격도
    stuck 도 함께 사라지고, 로그에는 스택 트레이스만 남는다."""
    m = env.get("method")
    return dict(m.get("assumes") or {}) if isinstance(m, dict) else {}


def _subject_of(env: dict) -> str:
    rd = env.get("read") or [{}]
    return str(rd[0].get("key", env.get("subject") or "na")).split(".")[0]


def escalate(published: dict, envelopes: list, at: str = None,
             rel_tol: float = RC.REL_TOL) -> dict:
    """반려·미완을 한 급 위로 올린다. 올라간 이유가 기록된다.

    T3 위는 없다. 거기서 막힌 것은 승격이 아니라 **사람이 볼 일**이다."""
    at = at or date.today().isoformat()
    # 무단 봉투는 승격 대상이 아니다. 시킨 적 없는 봉투에 재시도 지시서를
    # 내면 **아무도 부르지 않은 데스크가 정식으로 소집된다.** 그리고 그
    # 봉투가 `RC.review` 에 섞이면 멀쩡한 봉투를 '갈렸다'로 끌어올린다.
    withheld = {r["instance"] for r in
                ((published.get("dispatch") or {}).get(D.UNASKED) or [])
                if r.get("instance")}
    envelopes = [e for e in envelopes
                 if e.get("instance") not in withheld]
    by_inst = {e.get("instance"): e for e in envelopes}
    orders, stuck, reasons = [], [], []

    cands = []
    for r in published.get("rejected") or []:
        cands.append((r.get("instance"), "gate_rejected", r.get("reason")))
    for e in envelopes:
        sp = e.get("spent") or {}
        if sp.get("completed") is False:
            cands.append((e.get("instance"), "budget_incomplete",
                          sp.get("why") or "예산 안에서 끝내지 못했습니다"))

    # 갈린 쪽은 **양쪽 다** 올린다. 어느 쪽이 틀렸는지 모르기 때문이다 —
    # 한쪽만 올리면 그 선택 자체가 판정이 된다.
    rec = RC.review(envelopes, rel_tol)
    for c in rec["conflicts"]:
        for side in ("left", "right"):
            cands.append((c[side].get("instance"), "desks_disagree",
                          f"{c['kind']} — {c['why']}"))

    # 한 인스턴스에 사유가 여럿이면 **올리는 쪽이 이긴다.** 첫 반려는 같은
    # 급에서 다시 하는데, 예산을 이미 다 쓴 인스턴스를 같은 예산으로 다시
    # 돌리면 같은 벽에 부딪힌다 — 그리고 예산 미완이라는 사실이 기록에서
    # 사라진다.
    #
    # 갈림이 반려보다 앞에 오는 것도 같은 이유다. 갈린 쪽이 마침 반려되기도
    # 했다고 해서 그쪽만 같은 급에 남으면, **양쪽이 함께 올라간다**는 규칙이
    # 깨진다 (CLAUDE.md 4-c). 한쪽만 올리면 그 선택 자체가 판정이다.
    rank = {w: i for i, w in enumerate(("budget_incomplete", "desks_disagree",
                                        "gate_rejected"))}
    cands.sort(key=lambda c: rank.get(c[1], 99))

    seen, retries = set(), []
    for inst, why, detail in cands:
        if inst in seen:
            continue
        seen.add(inst)
        env = by_inst.get(inst)
        if env is None:
            continue
        tier = env.get("tier") or "T2"
        attempt = env.get("attempt") or 1

        # 첫 반려는 같은 급에서 다시 한다. 승격이 아니다.
        if why in RETRY_FIRST and attempt < 2:
            retries.append({
                "instance": inst, "desk": env.get("desk"), "tier": tier,
                "attempt": attempt + 1, "why": why, "detail": detail,
                "note": ("첫 반려입니다. 같은 급에서 한 번 더 합니다 — 두 번 "
                         "연속 반려되면 그때 올라갑니다."),
            })
            orders.append({
                "instance": E.new_instance(env["desk"], at, _subject_of(env),
                                           salt=f"retry:{inst}"),
                "desk": env["desk"], "tier": tier, "attempt": attempt + 1,
                "budget": dict(BUDGET[tier]),
                "escalated_from": None, "escalated_because": None,
                "trigger": {"kind": "retry", "subject": inst, "why": detail},
                "inputs": _assumes_of(env),
                "tools": ["mcp__ki-ledger__*"],
                "must": [f"반려 사유를 먼저 읽어라: {detail}",
                         f'봉투에 "attempt": {attempt + 1} 을 적어라 — 적지 '
                         f"않으면 같은 급에서 영원히 반복되고 승격이 오지 않는다",
                         "같은 급에서 다시 낸다. 또 반려되면 위로 올라간다"],
            })
            continue

        nxt = E.NEXT_TIER.get(tier)
        row = {"instance": inst, "desk": env.get("desk"), "from": tier,
               "why": why, "detail": detail, "attempt": attempt}
        if nxt is None:
            # 더 올릴 급이 없다. 조용히 묻지 않고 사람에게 넘긴다.
            row["to"] = None
            row["note"] = ("T3 위는 없습니다. 자동으로 다시 돌리지 않고 "
                           "사람이 봅니다 — 반복해서 막히는 지점이 이 시스템이 "
                           "약한 곳입니다.")
            stuck.append(row)
            continue
        row["to"] = nxt
        o = {
            "instance": E.new_instance(env["desk"], at, _subject_of(env),
                                       salt=f"esc:{inst}"),
            "desk": env["desk"], "tier": nxt, "attempt": 1,
            "budget": dict(BUDGET[nxt]),
            "escalated_from": tier, "escalated_because": why,
            "trigger": {"kind": "escalation", "subject": inst, "why": detail},
            "inputs": _assumes_of(env),
            "tools": ["mcp__ki-ledger__*"],
            "must": [
                f"{tier} 에서 막힌 이유를 먼저 읽어라: {detail}",
                f'봉투에 "escalated_from": "{tier}" 와 "attempt": 1 을 적어라 '
                f"— 왜 올라왔는지가 남아야 한다",
                "같은 이유로 또 막히면 그것은 프롬프트가 아니라 규칙 문서의 문제다",
            ],
        }
        orders.append(o)
        reasons.append(row)

    return {
        "schema": SCHEMA, "stage": "escalate", "at": at,
        "n": len(orders), "orders": orders,
        "escalated": reasons, "retried": retries, "stuck": stuck,
        "reconcile": {k: rec[k] for k in
                      ("n_conflicts", "compared_pairs", "n_uncomparable",
                       "rel_tol", "blind_spot")},
        "note": ("승격은 기록된다. 승격이 잦은 지점이 이 시스템이 약한 곳이고, "
                 "스코어카드가 그 분포를 본다 — 고치는 것은 사람이다."),
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

    def _first_rejection_retries_same_tier():
        """첫 반려는 같은 급에서 다시 한다 — 금지어 하나에 T3 을 띄우지 않는다."""
        bad = G._env(claim="희석 4.2% — 매도 검토")
        bad["tier"] = "T1"
        pub = publish([bad], led, at="2026-09-18")
        r = escalate(pub, [bad], at="2026-09-18")
        _assert(r["escalated"] == [], r["escalated"])
        _assert(len(r["retried"]) == 1, r)
        o = r["orders"][0]
        _assert(o["tier"] == "T1" and o["attempt"] == 2)
        _assert(o["escalated_from"] is None)
        _assert(o["budget"] == BUDGET["T1"])
        _assert("두 번 연속" in r["retried"][0]["note"])
    check("첫 반려는 같은 급에서 다시 한다 (승격이 아니다)",
          _first_rejection_retries_same_tier)

    def _second_rejection_escalates():
        """두 번 연속 반려되면 그때 올라간다."""
        bad = G._env(claim="희석 4.2% — 매도 검토")
        bad["tier"], bad["attempt"] = "T1", 2
        pub = publish([bad], led, at="2026-09-18")
        r = escalate(pub, [bad], at="2026-09-18")
        _assert(r["retried"] == [], r["retried"])
        _assert(r["n"] == 1 and r["escalated"][0]["attempt"] == 2)
        o = r["orders"][0]
        _assert(o["tier"] == "T2" and o["escalated_from"] == "T1")
        _assert(o["attempt"] == 1)          # 새 급에서는 다시 첫 시도다
    check("두 번 연속 반려되면 올라간다", _second_rejection_escalates)

    def _escalate_on_incomplete():
        """예산 안에서 못 끝냈으면 올라간다 — 조용히 줄인 답을 통과시키지 않는다."""
        e = G._env()
        e["tier"] = "T2"
        e["spent"] = E.spent(18, False, "예산 18회를 다 써서 §6 을 못 봤습니다")
        pub = publish([e], led, at="2026-09-18")
        _assert(pub["n_passed"] == 1)          # 게이트는 통과했다
        r = escalate(pub, [e], at="2026-09-18")
        _assert(r["n"] == 1, r)                # 그래도 올라간다
        _assert(r["orders"][0]["escalated_because"] == "budget_incomplete")
        _assert(r["orders"][0]["tier"] == "T3")
        _assert(r["retried"] == [], "미완은 같은 급에서 다시 하지 않는다")
    check("미완이면 게이트를 통과했어도 바로 올라간다", _escalate_on_incomplete)

    def _t3_is_stuck_not_silent():
        """T3 위는 없다. 조용히 묻지 않고 사람에게 넘긴다."""
        bad = G._env(claim="매도 검토")
        bad["tier"], bad["attempt"] = "T3", 2
        pub = publish([bad], led, at="2026-09-18")
        r = escalate(pub, [bad], at="2026-09-18")
        _assert(r["n"] == 0 and len(r["stuck"]) == 1, r)
        _assert(r["stuck"][0]["to"] is None)
        _assert("사람이 봅니다" in r["stuck"][0]["note"])
    check("T3 에서 막히면 사람에게 넘긴다 (조용히 묻지 않는다)", _t3_is_stuck_not_silent)

    def _no_escalation_when_clean():
        e = G._env(); e["spent"] = E.spent(6, True)
        pub = publish([e], led, at="2026-09-18")
        r = escalate(pub, [e], at="2026-09-18")
        _assert(r["n"] == 0 and r["stuck"] == [])
    check("멀쩡히 통과하면 올라가지 않는다", _no_escalation_when_clean)

    def _escalation_not_doubled():
        """반려되고 미완이기도 하면 한 번만 올라간다."""
        bad = G._env(claim="매도 검토"); bad["tier"] = "T1"; bad["attempt"] = 2
        bad["spent"] = E.spent(6, False, "예산 초과")
        pub = publish([bad], led, at="2026-09-18")
        r = escalate(pub, [bad], at="2026-09-18")
        _assert(r["n"] == 1, r["orders"])
    check("같은 인스턴스를 두 번 올리지 않는다", _escalation_not_doubled)

    def _disagreement_does_not_retry():
        """판정이 갈린 것은 같은 급에서 다시 해도 상대와의 차이가 그대로다."""
        a = RC._env("q2-disposal", 25.0); b = RC._env("risk-officer", 41.0)
        a["tier"] = b["tier"] = "T2"
        r = escalate(publish([a, b], led, at="2026-09-18"), [a, b], at="2026-09-18")
        _assert(r["retried"] == [], r["retried"])
        _assert(r["n"] == 2)
    check("판정이 갈리면 다시 하지 않고 바로 올린다", _disagreement_does_not_retry)

    def _both_sides_go_up_even_if_one_was_rejected():
        """갈린 쪽이 마침 반려되기도 했다고 해서 그쪽만 남으면 안 된다.

        한쪽만 올리면 그 선택 자체가 판정이 된다 (CLAUDE.md 4-c)."""
        a = RC._env("q2-disposal", 25.0); b = RC._env("risk-officer", 41.0)
        a["tier"] = b["tier"] = "T2"
        a["claim"] = "처분 25일 — 매도 검토"        # 한쪽만 판정 어휘
        r = escalate(publish([a, b], led, at="2026-09-18"), [a, b], at="2026-09-18")
        up = sorted(x["desk"] for x in r["escalated"])
        _assert(up == ["q2-disposal", "risk-officer"], r["escalated"])
        _assert(r["retried"] == [], r["retried"])
    check("갈린 한쪽이 반려돼도 양쪽 다 올라간다", _both_sides_go_up_even_if_one_was_rejected)

    def _budget_beats_rejection():
        """예산을 다 쓴 인스턴스를 같은 예산으로 다시 돌리지 않는다."""
        e = G._env(claim="희석 4.2% — 매도 검토"); e["tier"] = "T2"
        e["spent"] = E.spent(18, False, "예산 18회를 다 썼습니다")
        r = escalate(publish([e], led, at="2026-09-18"), [e], at="2026-09-18")
        _assert(r["retried"] == [], r["retried"])
        _assert(r["escalated"][0]["why"] == "budget_incomplete", r["escalated"])
    check("예산 미완이 반려보다 먼저다 (같은 벽에 다시 부딪히지 않는다)",
          _budget_beats_rejection)

    def _no_method_does_not_kill_the_stage():
        """method 가 없는 봉투 하나가 승격 단계 전체를 죽이지 않는다.

        ⑦ 4-eyes 반려는 아주 흔하고, 그때 method 가 비어 있을 수 있다. 거기서
        터지면 그 한 건이 아니라 다른 승격도 stuck 도 함께 사라진다."""
        bad = E.make("값", value=1.0, unit="d", desk="q2-disposal",
                     asof="2026-09-18", stale_days=1, source_grade="해석",
                     sources=["KRX"], subject="000660", attempt=2,
                     read=[E.observation("KRX", "000660.close", 88.0, "2026-09-18")],
                     limits=["x"])
        bad["reviewed_by"] = ["risk"]              # compliance 없음 → ⑦ 반려
        _assert(bad["method"] is None and E.validate(bad) == [])
        ok = G._env()
        ok["spent"] = E.spent(18, False, "예산 초과")
        r = escalate(publish([bad, ok], led, at="2026-09-18"), [bad, ok],
                     at="2026-09-18")
        _assert(r["n"] == 2, r)                    # 둘 다 살아서 올라간다
    check("method 없는 봉투가 승격 단계를 죽이지 않는다",
          _no_method_does_not_kill_the_stage)

    def _only_enforceable_reasons():
        """집행할 수 없는 조건을 있는 척 세지 않는다."""
        _assert(set(ESCALATABLE) == {"gate_rejected", "budget_incomplete",
                                     "desks_disagree"})
    check("집행 가능한 승격 사유만 쓴다", _only_enforceable_reasons)

    def _disagreement_escalates_both():
        """갈리면 양쪽 다 올린다 — 한쪽만 올리면 그 선택이 판정이 된다."""
        a = RC._env("q2-disposal", 25.0); b = RC._env("risk-officer", 41.0)
        a["tier"] = b["tier"] = "T2"
        pub = publish([a, b], led, at="2026-09-18")
        r = escalate(pub, [a, b], at="2026-09-18")
        got = {x["desk"]: x for x in r["escalated"]}
        _assert(set(got) == {"q2-disposal", "risk-officer"}, r["escalated"])
        _assert(all(x["why"] == "desks_disagree" for x in got.values()))
        _assert(all(x["to"] == "T3" for x in got.values()))
        _assert(r["reconcile"]["n_conflicts"] >= 1)
    check("판정이 갈리면 양쪽 다 올린다", _disagreement_escalates_both)

    def _agreement_does_not_escalate():
        a = RC._env("q2-disposal", 25.0); b = RC._env("risk-officer", 25.4)
        pub = publish([a, b], led, at="2026-09-18")
        r = escalate(pub, [a, b], at="2026-09-18")
        _assert(r["n"] == 0, r["escalated"])
        _assert(r["reconcile"]["compared_pairs"] == 1)   # 비교는 했다
    check("값이 가까우면 올리지 않는다 (다만 비교는 한다)", _agreement_does_not_escalate)

    def _reconcile_summary_travels():
        """대조를 몇 건 했고 몇 건은 못 했는지가 산출에 남는다."""
        a = RC._env("q2-disposal", 25.0); a["measure"] = None
        pub = publish([a], led, at="2026-09-18")
        r = escalate(pub, [a], at="2026-09-18")
        _assert(r["reconcile"]["n_uncomparable"] == 1, r["reconcile"])
        _assert(r["reconcile"]["blind_spot"])
    check("대조하지 못한 건수가 승격 산출에 함께 나온다", _reconcile_summary_travels)

    def _tiers_all_budgeted():
        _assert(set(BUDGET) == {"T1", "T2", "T3"})
        _assert(set(BUDGET) == set(E.TIERS))
        for t in ("T1", "T2", "T3"):
            _assert(BUDGET[t]["tool_calls"] > 0 and BUDGET[t]["tokens"] > 0)
        _assert(BUDGET["T1"]["tokens"] < BUDGET["T2"]["tokens"] < BUDGET["T3"]["tokens"])
    check("세 급 모두 예산이 있고 위로 갈수록 크다", _tiers_all_budgeted)

    # ── 소집과 회수를 짝지은 채로 도는가 ──────────────────────────────
    #
    # 여기가 비어 있어서 검토 한 번에 결함 여섯이 나왔다. `publish(orders=)`
    # 경로를 아무도 돌려 보지 않았고, 그래서 게이트 ⑥ 을 건너뛰는 것도,
    # 승격이 무단 봉투에 지시서를 내는 것도 검사를 통과했다.

    def _ordered(desk="q2-disposal", subject="000660"):
        return work_order({"kind": "price.move", "subject": subject,
                           "desks": [desk], "inputs": {"code": subject},
                           "why": "하락", "at": "2026-09-18", "tier": "T2"},
                          desk, "2026-09-18")

    def _good(inst, desk="q2-disposal", claim="처분 소요 12.4 영업일"):
        return E.make(claim, value=12.4, unit="business_days", desk=desk,
                      asof="2026-09-18", stale_days=0, source_grade="해석",
                      sources=["KRX/일별매매정보"], subject="000660",
                      instance=inst, measure="disposal_days", read=[],
                      limits=["평시 거래대금 기준이다"], spent=E.spent(3, True))

    def _leak_still_halts_even_when_withheld():
        """무단 봉투도 게이트 ⑥ 은 통과시킨 뒤에 뺀다.

        빼고 나서 검사하면 키가 든 무단 봉투 하나가 발행을 멈추지 못한다.
        **발행하지 않는 것과 검사하지 않는 것은 전혀 다른 이야기다** —
        유출은 되돌릴 수 없다."""
        o = _ordered()
        ok = _good(o["instance"])
        rogue = E.make("https://opendart.fss.or.kr/api/list.json"
                       "?crtfc_key=abcdef0123456789abcdef0123456789abcdef01",
                       value=None, unit=None, desk="q1-progress",
                       asof="2026-09-18", stale_days=0, source_grade="해석",
                       sources=["DART/공시목록"], subject="na",
                       reason="회수계획 파일이 없습니다", read=[],
                       limits=["l"], spent=E.spent(1, True))
        pub = publish([ok, rogue], led, at="2026-09-18", orders=[o])
        _assert(pub["halt_publication"] is True, pub["halt_publication"])
        _assert(pub["publishable"] == [], pub["publishable"])
    check("무단 봉투의 유출도 발행을 멈춘다",
          _leak_still_halts_even_when_withheld)

    def _unasked_is_not_escalated():
        """시킨 적 없는 봉투에 재시도 지시서를 내면, 아무도 부르지 않은
        데스크가 정식으로 소집된다."""
        o = _ordered()
        ok = _good(o["instance"])
        rogue = _good("q1-progress-20260918-na-dead", desk="q1-progress",
                      claim="회수 진척 40%")
        envs = [ok, rogue]
        pub = publish(envs, led, at="2026-09-18", orders=[o])
        esc = escalate(pub, envs, at="2026-09-18")
        desks = {x["desk"] for x in esc.get("orders", [])}
        _assert("q1-progress" not in desks, esc.get("orders"))
        stuck = {x["desk"] for x in esc.get("stuck", [])}
        _assert("q1-progress" not in stuck, esc.get("stuck"))
    check("무단 봉투는 승격시키지 않는다", _unasked_is_not_escalated)

    def _missing_is_a_named_row_not_a_blank():
        """안 온 절도 빈칸이 아니다. 빈칸은 리포트에서 '조용한 날'과
        똑같이 생겼고, 아무도 묻지 않는다."""
        a1, a2 = _ordered(), _ordered("q4-timing", "000660")
        pub = publish([_good(a1["instance"])], led, at="2026-09-18",
                      orders=[a1, a2])
        rows = [r for r in pub["rejected"] if r["desk"] == "q4-timing"]
        _assert(len(rows) == 1, pub["rejected"])
        _assert("봉투가 오지 않았" in rows[0]["reason"], rows[0])
        _assert(pub["n_missing"] == 1 and pub["n_withheld"] == 0, pub)
    check("미이행은 이름 달린 행으로 남는다",
          _missing_is_a_named_row_not_a_blank)

    def _n_in_counts_envelopes_not_desk_rows():
        """`n_in` 에 미이행을 섞으면 스코어카드가 그 수로 통과율을 나눠,
        아무도 보고하지 않은 날이 100% 로 보인다."""
        a1, a2 = _ordered(), _ordered("q4-timing", "000660")
        pub = publish([_good(a1["instance"])], led, at="2026-09-18",
                      orders=[a1, a2])
        _assert(pub["n_in"] == 1, pub["n_in"])
        _assert(pub["n_rejected"] >= 1)
    check("n_in 은 돌아온 봉투 수다", _n_in_counts_envelopes_not_desk_rows)

    def _broken_envelope_keeps_its_own_reason():
        """읽지 못한 봉투는 instance 가 없다. 그것을 무단으로 몰면 진짜
        사유(형식이 깨졌다)가 '시킨 적 없는 봉투' 로 바뀐다."""
        o = _ordered()
        broken = {"claim": "봉투를 읽지 못했습니다: x.json",
                  "reason": "Expecting value", "desk": "unknown"}
        pub = publish([_good(o["instance"]), broken], led, at="2026-09-18",
                      orders=[o])
        row = [r for r in pub["rejected"] if r["desk"] == "unknown"]
        _assert(len(row) == 1, pub["rejected"])
        _assert("시킨 적 없는" not in (row[0]["reason"] or ""), row[0])
        _assert(pub["n_withheld"] == 0, pub["n_withheld"])
    check("읽지 못한 봉투는 제 사유를 지킨다",
          _broken_envelope_keeps_its_own_reason)

    def _no_orders_keeps_the_old_behaviour():
        """소집한 적이 없으면 대조할 상대가 없다 — 옛 동작 그대로다."""
        pub = publish([_good("아무거나")], led, at="2026-09-18")
        _assert(pub["dispatch"] is None, pub["dispatch"])
        _assert(pub["n_in"] == 1 and pub["n_withheld"] == 0)
    check("소집한 적이 없으면 대조도 없다", _no_orders_keeps_the_old_behaviour)

    def _quiet_day_still_catches_strays():
        """'소집이 0건이었다'와 '소집한 적이 없다'는 다르다.

        앞의 것은 조용한 날이고, 그날 봉투가 하나라도 있으면 전부 무단이다.
        둘을 같게 보면 **소집이 없던 날 떠돌던 봉투가 그대로 발행된다** —
        막으려던 구멍이 조용한 날에만 다시 열린다."""
        pub = publish([_good("떠돌이")], led, at="2026-09-18", orders=[])
        _assert(pub["dispatch"] is not None, pub["dispatch"])
        _assert(pub["n_withheld"] == 1, pub["n_withheld"])
        _assert(pub["publishable"] == [], pub["publishable"])
        # 진짜 조용한 날은 조용하다
        quiet = publish([], led, at="2026-09-18", orders=[])
        _assert(quiet["n_in"] == 0 and quiet["n_withheld"] == 0, quiet)
    check("소집 0건인 날의 떠돌이 봉투도 무단이다",
          _quiet_day_still_catches_strays)

    def _duplicate_is_marked_not_dropped():
        """중복을 빼면 그 절이 통째로 비고, 빈칸은 아무도 묻지 않는다."""
        o = _ordered()
        pub = publish([_good(o["instance"]), _good(o["instance"])], led,
                      at="2026-09-18", orders=[o])
        _assert(pub["n_in"] == 2, pub["n_in"])
        _assert(any("중복" in m for m in pub["marks"]), pub["marks"])
        _assert(pub["n_withheld"] == 0)
    check("중복은 빼지 않고 표시만 단다", _duplicate_is_marked_not_dropped)

    for f in failed:
        print("  X  " + f, file=sys.stderr)
    print(f"run_day    {passed_n} passed, {len(failed)} failed")
    return 1 if failed else 0


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="하루 운영 — 소집 · 발행")
    ap.add_argument("--selftest", action="store_true")
    ap.add_argument("--stage", choices=["convene", "publish", "escalate"])
    ap.add_argument("--since")
    ap.add_argument("--at")
    ap.add_argument("--db")
    ap.add_argument("--envelopes", default="agents/envelopes")
    ap.add_argument("--orders", default=str(D.ORDERS),
                    help="작업지시서 폴더 (소집이 쓰고 발행이 되읽는다)")
    ap.add_argument("--no-write-orders", action="store_true",
                    help="소집 결과를 디스크에 쓰지 않는다 (미리보기)")
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
        # 지시서를 디스크에 남긴다. 안 남기면 몇 시간 뒤 봉투가 왔을 때
        # 짝지을 상대가 없고, 석 달 뒤 되짚을 때도 없다.
        if not a.no_write_orders:
            out["issued"] = D.issue(out["orders"], out["at"], Path(a.orders))
    else:
        d = Path(a.envelopes)
        if not d.exists():
            print(f"봉투 폴더가 없습니다: {d}", file=sys.stderr)
            sys.exit(1)
        envs = load_envelopes(d)
        # 그날 시킨 것을 되읽어 짝을 맞춘다. 지시서가 없으면 대조도 없고,
        # 그때는 봉투 폴더에 있는 것을 전부 받는 옛 동작 그대로다.
        at_key = a.at or date.today().isoformat()
        # 소집한 적이 없으면 대조할 상대가 없다 (None). 소집했는데 0건이면
        # 빈 목록이고, 그날 온 봉투는 전부 무단이다.
        orders = (D.load_orders(at_key, Path(a.orders))
                  if D.convened(at_key, Path(a.orders)) else None)
        pub = publish(envs, led, at=a.at, orders=orders)
        if a.stage == "publish":
            out = pub
        else:
            out = escalate(pub, envs, at=a.at)
            # 승격이 낸 지시서도 남겨야 한다. 안 남기면 그 봉투가 다음
            # 발행에서 '무단' 이 되어 빠지고, 승격은 그것을 못 받았다고
            # 또 재시도를 낸다 — 재시도가 끝나지 않는다.
            if out.get("orders") and not a.no_write_orders:
                out["issued"] = D.issue(out["orders"], at_key, Path(a.orders))
    print(json.dumps(out, ensure_ascii=False, indent=a.indent))
    sys.exit(1 if out.get("halt_publication") else 0)
