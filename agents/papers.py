"""논문 원장 — 목록이 아니라 장부다.

`.papers.json` 은 v1 에서 '채택된 논문 목록'이었다. 채택은 `adopted: true` 한
칸이었고, 그 칸은 **왜** 채택됐는지도 **언제** 다시 봐야 하는지도 담지 못했다.
한번 들어온 논문은 영원히 근거였다.

v2 는 같은 파일을 장부로 바꾼다.

    state        unverified · adopted · warned · retired  (네 상태)
    replication  append-only. 판정은 덮어쓰지 않고 쌓인다
    recheck_due  다시 볼 날. 지나면 스스로 낡았다고 말한다

**은퇴본도 지우지 않는다.** "이 논문은 코스닥에서 성립하지 않는다"는 것도
측정 결과다. 지워 버리면 다음 사람이 같은 논문을 다시 주워 온다.

이관에 대하여 — 기존 12편은 전부 `unverified` 로 들어간다. `adopted` 가 아니다.
그것들은 사람이 읽고 고른 좋은 논문이지만, 우리 원장에 대고 계산해 본 적은
없다. 재현 관문을 만들면서 기존 항목만 통과한 것으로 쳐 주면 그 관문은 처음부터
빈 관문이다. `unverified` 는 **인용을 막지 않는다** — '미검증' 표시를 달고 나갈
뿐이다.

    python agents/papers.py --selftest
    python agents/papers.py --migrate      # v1 → v2 (되돌릴 수 있다)
"""
from __future__ import annotations

import argparse
import copy
import io
import json
import sys
from datetime import date, datetime, timedelta
from pathlib import Path

SCHEMA = "ki.papers/2"
LEDGER = Path(__file__).resolve().parent.parent / "stock-monitor" / ".papers.json"

# ── 네 상태 ───────────────────────────────────────────────────────────
UNVERIFIED = "unverified"   # 사람이 골랐으나 우리 표본으로 계산해 본 적 없음
ADOPTED = "adopted"         # 재현됨. 근거로 삼아도 된다
WARNED = "warned"           # 재현이 흔들렸거나 기한이 지났다. 표시를 달고 인용
RETIRED = "retired"         # 우리 표본에서 성립하지 않는다. 인용 금지
STATES = (UNVERIFIED, ADOPTED, WARNED, RETIRED)

# 인용 자체가 막히는 것은 은퇴본뿐이다. 나머지는 표시를 달고 나간다.
CITABLE = (UNVERIFIED, ADOPTED, WARNED)

MARK = {
    UNVERIFIED: "미검증 — 우리 표본으로 재현해 본 적 없음",
    ADOPTED: "",
    WARNED: "주의 — 재현이 흔들렸거나 재검 기한이 지남",
    RETIRED: "은퇴 — 우리 표본에서 성립하지 않음. 인용 불가",
}

# 재검 주기. 방법론은 오래 가고, 시장 미시구조는 제도가 바뀌면 같이 바뀐다.
DEFAULT_HALF_LIFE_D = 365


def load(path: Path = None) -> dict:
    path = path or LEDGER
    with io.open(path, encoding="utf-8") as f:
        return json.load(f) or {}


def save(doc: dict, path: Path = None) -> None:
    path = path or LEDGER
    with io.open(path, "w", encoding="utf-8", newline="\n") as f:
        json.dump(doc, f, ensure_ascii=False, indent=2)
        f.write("\n")


def migrate(doc: dict, at: str = None) -> dict:
    """v1 → v2. 값을 지어내지 않는다 — 없던 정보는 없는 채로 둔다.

    되돌릴 수 있다. v1 이 갖고 있던 칸은 하나도 지우지 않는다."""
    at = at or date.today().isoformat()
    if doc.get("schema") == SCHEMA:
        return copy.deepcopy(doc)                       # 이미 v2. 두 번 돌려도 같다
    out = copy.deepcopy(doc)
    out["schema"] = SCHEMA
    out["migrated_at"] = at
    out["note"] = (
        "팩터가 근거로 삼는 논문 장부. state 는 unverified·adopted·warned·retired "
        "네 가지이고, replication 은 덮어쓰지 않고 쌓는다. 은퇴본도 지우지 않는다 "
        "— 성립하지 않는다는 것도 측정 결과이고, 지우면 같은 논문을 다시 주워 온다. "
        "새 논문은 docs/fetch_papers.py --harvest 로 후보에 쌓고, 사람이 네 질문 중 "
        "하나에 걸릴 때만 이리로 들인다."
    )
    for key, p in (out.get("papers") or {}).items():
        # v1 의 adopted 는 '사람이 골랐다'는 뜻이었지 '재현됐다'는 뜻이 아니다.
        # 그것을 adopted 로 옮기면 재현 관문이 처음부터 빈 관문이 된다.
        p["state"] = RETIRED if p.get("adopted") is False else UNVERIFIED
        p["state_reason"] = (
            "v1 에서 후보였음 (채택되지 않음)" if p.get("adopted") is False else
            "v1 에서 사람이 채택했으나 우리 표본으로 재현한 기록이 없음"
        )
        p["state_at"] = at
        p.setdefault("replication", [])                 # append-only
        p.setdefault("half_life_d", DEFAULT_HALF_LIFE_D)
        p.setdefault("recheck_due", None)               # 재현을 돌린 날 정해진다
        p.setdefault("limits", [])
        # adopted 는 남겨 둔다 — ki_monitor.papers() 가 이 칸을 본다.
        # 측정층을 건드리지 않고 장부만 바꾸기 위한 다리다.
        p.setdefault("adopted", True)
    return out


def record(doc: dict, key: str, rep: dict, at: str = None,
           half_life_d: int = None) -> dict:
    """재현 판정 하나를 장부에 쌓고 상태를 다시 매긴다.

    덮어쓰지 않는다. 같은 논문을 다른 구간으로 다시 돌린 결과는 **옆에** 쌓여야
    한다 — 구간이 바뀌면서 판정이 바뀌는 것 자체가 신호이기 때문이다."""
    at = at or date.today().isoformat()
    out = copy.deepcopy(doc)
    p = (out.get("papers") or {}).get(key)
    if p is None:
        raise KeyError(f"장부에 없는 논문입니다: {key}")

    p.setdefault("replication", []).append(rep)
    v = rep.get("verdict")
    prev = p.get("state") or UNVERIFIED
    if v == "재현됨":
        p["state"], p["state_reason"] = ADOPTED, f"{at} 재현됨 (t={rep.get('observed', {}).get('t')})"
        p["state_at"] = at
    elif v == "방향 반대":
        p["state"] = RETIRED
        p["state_reason"] = (f"{at} 우리 표본에서 논문과 반대 방향으로 유의. "
                             f"기록은 남기고 인용은 막는다.")
        p["state_at"] = at
    elif prev == RETIRED:
        # 판정 불가는 **되살리지 못한다.** 은퇴는 '우리 표본에서 반대 방향으로
        # 유의했다'는 측정 결과이고, '이번에는 못 쟀다'가 그것을 뒤집을 수는
        # 없다. 상태도 사유도 그대로 두고 기록만 쌓는다 — 되살리면 인용이
        # 다시 열리는데, 그 재개방의 근거가 '못 쟀다'가 된다.
        pass
    else:
        # 판정 불가는 은퇴가 아니다. 표본이 얇거나 유의하지 않았을 뿐이다.
        # 다만 **올리지도 않는다.** warned 를 unverified 로 되돌리면 '흔들린
        # 적이 있다'가 '아직 해 본 적이 없다'로 바뀌어, 방금 돌려 보고도
        # 안 돌려 본 것처럼 읽힌다.
        p["state"] = WARNED if prev in (ADOPTED, WARNED) else UNVERIFIED
        p["state_reason"] = f"{at} 판정 불가 — {rep.get('reason') or '사유 없음'}"
        p["state_at"] = at
    hl = half_life_d or p.get("half_life_d") or DEFAULT_HALF_LIFE_D
    p["half_life_d"] = hl
    p["recheck_due"] = (datetime.fromisoformat(at).date() + timedelta(days=hl)).isoformat()
    return out


def age_states(doc: dict, today: str = None) -> dict:
    """재검 기한이 지난 채택본을 `warned` 로 내린다.

    자동으로 은퇴시키지는 않는다. 기한이 지났다는 것은 '다시 봐야 한다'이지
    '틀렸다'가 아니다. 판정을 바꾸는 것은 재현 러너뿐이다."""
    today = today or date.today().isoformat()
    out = copy.deepcopy(doc)
    for key, p in (out.get("papers") or {}).items():
        due = p.get("recheck_due")
        if p.get("state") == ADOPTED and due and due < today:
            p["state"] = WARNED
            p["state_reason"] = f"{today} 재검 기한({due})이 지났습니다"
            p["state_at"] = today
    return out


def method_papers(doc: dict) -> dict:
    """이 도구 자신의 계산 규칙이 근거로 삼는 논문.

    팩터의 출처(`papers`)와 나누어 둔다. 섞으면 측정층의 "모든 팩터가 실재하는
    논문을 인용하는가" 검사가, 팩터와 아무 상관 없는 추정량 논문까지 팩터
    출처로 세게 된다 — 검사가 통과해도 뜻이 없어진다."""
    return {k: v for k, v in (doc.get("method_papers") or {}).items()
            if isinstance(v, dict)}


def cite(doc: dict, key: str) -> str:
    """논문 한 줄 인용. 없으면 빈 문자열 — 지어내지 않는다.

    `ki_monitor.cite()` 와 같은 일을 하되 장부를 인자로 받는다. 측정층을
    import 하지 않고도 인용문을 만들 수 있어야 하기 때문이다."""
    v = (doc.get("papers") or {}).get(key)
    if not v:
        return ""
    where = ", ".join(x for x in (str(v.get("volume") or ""),
                                  str(v.get("pages") or "")) if x)
    doi = f" doi:{v['doi']}" if v.get("doi") else ""
    return (f"{v.get('authors')} ({v.get('year')}) {v.get('title')}. "
            f"{v.get('journal')}{' ' + where if where else ''}.{doi}")


def method_cite(doc: dict, key: str) -> str:
    """방법론 논문 한 줄 인용. 없으면 빈 문자열 — 지어내지 않는다."""
    m = method_papers(doc).get(key)
    if not m:
        return ""
    where = ", ".join(x for x in (str(m.get("volume") or ""),
                                  str(m.get("pages") or "")) if x)
    doi = f" doi:{m['doi']}" if m.get("doi") else ""
    return (f"{m['authors']} ({m['year']}) {m['title']}. "
            f"{m['journal']}{' ' + where if where else ''}.{doi}")


def state_of(doc: dict, key: str) -> str | None:
    p = (doc.get("papers") or {}).get(key)
    return p.get("state") if p else None


def citable(doc: dict, key: str) -> tuple[bool, str]:
    """인용해도 되는가. (가능 여부, 함께 나갈 표시) 를 낸다."""
    st = state_of(doc, key)
    if st is None:
        return False, f"장부에 없는 논문입니다: {key}"
    if st == RETIRED:
        return False, MARK[RETIRED]
    return True, MARK.get(st, "")


def validate(doc: dict) -> list[str]:
    p: list[str] = []
    if doc.get("schema") != SCHEMA:
        p.append(f"schema 가 {SCHEMA} 가 아닙니다: {doc.get('schema')!r}")
    papers = doc.get("papers")
    if not isinstance(papers, dict) or not papers:
        return p + ["papers 가 비어 있습니다"]
    for k, v in papers.items():
        if v.get("state") not in STATES:
            p.append(f"{k}: state 가 {STATES} 중 하나가 아닙니다 ({v.get('state')!r})")
        if not isinstance(v.get("replication"), list):
            p.append(f"{k}: replication 은 리스트여야 합니다 (append-only)")
        if not isinstance(v.get("year"), int) or not (1900 < v["year"] < 2100):
            p.append(f"{k}: year 가 없거나 이상합니다")
        if not str(v.get("question") or "").strip():
            p.append(f"{k}: 어느 질문에 걸리는지(question)가 없습니다")
        # 증명은 **올릴 때** 요구한다. 내릴 때는 요구하지 않는다.
        #
        # adopted 는 "우리 표본에서 성립한다"는 주장이므로 근거가 있어야 한다.
        # retired 는 "인용하지 않는다"일 뿐이어서, 재현 실패 말고도 사람이
        # 빼기로 한 것·철회된 논문처럼 다른 사유로도 그렇게 될 수 있다.
        # 양쪽에 같은 증명을 요구하면, 빼려면 먼저 검정부터 통과시켜야 하는
        # 거꾸로 된 관문이 된다.
        if v.get("state") == ADOPTED and not v.get("replication"):
            p.append(f"{k}: state=adopted 인데 재현 기록이 없습니다 "
                     f"— 재현 없이 근거가 될 수 없습니다")
        if v.get("state") == RETIRED and not str(v.get("state_reason") or "").strip():
            p.append(f"{k}: state=retired 인데 사유가 없습니다")
    for k, v in method_papers(doc).items():
        for field in ("authors", "year", "title", "journal", "doi", "used_for", "claim"):
            if not v.get(field):
                p.append(f"method_papers.{k}: {field} 가 없습니다")
        if not (v.get("limits") and all(str(x).strip() for x in v["limits"])):
            p.append(f"method_papers.{k}: limits 가 비어 있습니다 "
                     f"— 그 논문이 주장하지 않는 것을 적으십시오")
        if not str(v.get("checked") or "").strip():
            p.append(f"method_papers.{k}: 대조 기록(checked)이 없습니다")
    return p


# ── 자체 검사 ─────────────────────────────────────────────────────────

def _v1() -> dict:
    return {
        "schema": "ki.papers/1", "verified": "2026-09-05",
        "papers": {
            "amihud2002": {"authors": "Amihud, Y.", "year": 2002, "title": "T",
                           "journal": "J", "doi": "10.x/a", "question": "q2",
                           "adopted": True},
            "cand9999": {"authors": "B", "year": 2025, "title": "후보",
                         "journal": "J", "doi": "10.x/b", "question": "q1",
                         "adopted": False},
        },
        "questions": {"q1": "얼마나 왔는가", "q2": "팔 수 있는가"},
    }


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

    def _migrate_shape():
        d = migrate(_v1(), at="2026-09-17")
        _assert(d["schema"] == SCHEMA)
        _assert(validate(d) == [], validate(d))
    check("이관 결과가 v2 로 성립한다", _migrate_shape)

    def _migrate_unverified():
        """기존 채택본은 unverified 로 들어간다 — adopted 가 아니다.

        여기가 이 관문의 정직성이 정해지는 자리다. 기존 항목을 통과한 것으로
        쳐 주면 재현 관문은 만들자마자 빈 관문이 된다."""
        d = migrate(_v1(), at="2026-09-17")
        _assert(state_of(d, "amihud2002") == UNVERIFIED, state_of(d, "amihud2002"))
        _assert(d["papers"]["amihud2002"]["replication"] == [])
    check("기존 채택본은 unverified 로 이관된다 (통과로 쳐 주지 않는다)",
          _migrate_unverified)

    def _migrate_candidate_retired():
        d = migrate(_v1(), at="2026-09-17")
        _assert(state_of(d, "cand9999") == RETIRED)
    check("v1 의 후보(adopted=false)는 은퇴본으로 이관된다", _migrate_candidate_retired)

    def _migrate_idempotent():
        a = migrate(_v1(), at="2026-09-17")
        b = migrate(a, at="2026-12-31")
        _assert(a == b)                                 # 두 번 돌려도 같다
    check("이관은 두 번 돌려도 같다", _migrate_idempotent)

    def _migrate_keeps_v1_fields():
        """되돌릴 수 있어야 한다 — v1 의 칸을 하나도 지우지 않는다."""
        v1 = _v1()
        d = migrate(v1, at="2026-09-17")
        for k, p in v1["papers"].items():
            for field, val in p.items():
                _assert(d["papers"][k].get(field) == val, f"{k}.{field}")
        _assert(d["questions"] == v1["questions"])
    check("이관이 v1 의 칸을 지우지 않는다", _migrate_keeps_v1_fields)

    def _bridge_to_ki_monitor():
        """ki_monitor.papers() 는 adopted 칸을 본다. 그 다리가 끊기면 안 된다."""
        d = migrate(_v1(), at="2026-09-17")
        _assert(d["papers"]["amihud2002"].get("adopted") is True)
        _assert(d["papers"]["cand9999"].get("adopted") is False)
    check("측정층으로 가는 다리(adopted)가 유지된다", _bridge_to_ki_monitor)

    def _unverified_is_citable():
        d = migrate(_v1(), at="2026-09-17")
        ok, mark = citable(d, "amihud2002")
        _assert(ok)                                     # 막지 않는다
        _assert("미검증" in mark)                        # 표시는 달고 나간다
    check("미검증은 인용을 막지 않고 표시를 단다", _unverified_is_citable)

    def _retired_blocked():
        d = migrate(_v1(), at="2026-09-17")
        ok, mark = citable(d, "cand9999")
        _assert(not ok and "은퇴" in mark)
    check("은퇴본은 인용이 막힌다", _retired_blocked)

    def _unknown_blocked():
        d = migrate(_v1(), at="2026-09-17")
        ok, _ = citable(d, "없는논문")
        _assert(not ok)                                 # 없는 논문은 지어내지 않는다
    check("장부에 없는 논문은 인용되지 않는다", _unknown_blocked)

    def _record_adopts():
        d = migrate(_v1(), at="2026-09-17")
        d = record(d, "amihud2002",
                   {"verdict": "재현됨", "observed": {"t": 4.2}}, at="2026-09-17")
        _assert(state_of(d, "amihud2002") == ADOPTED)
        _assert(d["papers"]["amihud2002"]["recheck_due"] == "2027-09-17")
        _assert(validate(d) == [], validate(d))
    check("재현되면 adopted 로 올라가고 재검일이 잡힌다", _record_adopts)

    def _record_retires():
        d = migrate(_v1(), at="2026-09-17")
        d = record(d, "amihud2002",
                   {"verdict": "방향 반대", "observed": {"t": -4.9}}, at="2026-09-17")
        _assert(state_of(d, "amihud2002") == RETIRED)
        ok, _ = citable(d, "amihud2002")
        _assert(not ok)
    check("방향이 반대면 은퇴한다", _record_retires)

    def _record_append_only():
        """덮어쓰지 않는다. 구간이 바뀌며 판정이 바뀌는 것 자체가 신호다."""
        d = migrate(_v1(), at="2026-09-17")
        d = record(d, "amihud2002", {"verdict": "재현됨", "window": "A"}, at="2026-09-17")
        d = record(d, "amihud2002", {"verdict": "판정 불가", "window": "B"}, at="2027-03-01")
        reps = d["papers"]["amihud2002"]["replication"]
        _assert(len(reps) == 2, len(reps))
        _assert(reps[0]["window"] == "A" and reps[1]["window"] == "B")
        _assert(state_of(d, "amihud2002") == WARNED)    # 채택본이 흔들리면 warned
    check("재현 기록은 쌓이고 덮어쓰이지 않는다", _record_append_only)

    def _record_unknown():
        d = migrate(_v1(), at="2026-09-17")
        try:
            record(d, "없는논문", {"verdict": "재현됨"})
        except KeyError:
            return
        raise AssertionError("없는 논문에 기록이 쌓였습니다")
    check("없는 논문에는 기록을 쌓지 않는다", _record_unknown)

    def _aging():
        d = migrate(_v1(), at="2026-09-17")
        d = record(d, "amihud2002", {"verdict": "재현됨"}, at="2026-09-17")
        same = age_states(d, today="2027-01-01")
        _assert(state_of(same, "amihud2002") == ADOPTED)     # 기한 전이면 그대로
        old = age_states(d, today="2027-10-01")
        _assert(state_of(old, "amihud2002") == WARNED)       # 지나면 주의
        _assert("기한" in old["papers"]["amihud2002"]["state_reason"])
    check("재검 기한이 지나면 주의로 내려간다 (은퇴시키지는 않는다)", _aging)

    def _aging_never_retires():
        """기한이 지났다는 것은 '다시 봐야 한다'이지 '틀렸다'가 아니다."""
        d = migrate(_v1(), at="2026-09-17")
        d = record(d, "amihud2002", {"verdict": "재현됨"}, at="2026-09-17")
        old = age_states(d, today="2099-01-01")
        _assert(state_of(old, "amihud2002") != RETIRED)
    check("기한 경과만으로는 은퇴시키지 않는다", _aging_never_retires)

    def _validate_catches_fake_adopted():
        """재현 기록 없이 adopted 를 손으로 써 넣는 것을 막는다."""
        d = migrate(_v1(), at="2026-09-17")
        d["papers"]["amihud2002"]["state"] = ADOPTED
        _assert(any("재현 없이" in x for x in validate(d)), validate(d))
    check("재현 기록 없는 adopted 는 검증에서 걸린다", _validate_catches_fake_adopted)

    def _cite_does_not_invent():
        d = migrate(_v1(), at="2026-09-17")
        _assert("2002" in cite(d, "amihud2002"))
        _assert(cite(d, "없는논문") == "")      # 지어내지 않는다
    check("인용문을 지어내지 않는다", _cite_does_not_invent)

    def _method_papers_real():
        """코드가 인용하는 방법론 논문이 장부에 실재하는가 (규칙 4).

        재현 관문의 임계와 표준오차 추정량은 둘 다 논문에서 온 것이다. 그
        출처를 주석에만 적어 두면, 몇 달 뒤 그 숫자는 근거 없는 상수가 된다."""
        if not LEDGER.exists():
            return
        d = load()
        mp = method_papers(d)
        for k in ("hlz2016", "nw1987"):
            _assert(k in mp, f"{k} 가 장부에 없습니다")
            _assert(method_cite(d, k), k)
            _assert(str(mp[k]["year"]) in method_cite(d, k), k)
        _assert(method_cite(d, "없는논문") == "")
        _assert(validate(d) == [], validate(d))
    check("코드가 인용하는 방법론 논문이 장부에 실재한다", _method_papers_real)

    def _method_papers_separate():
        """방법론 논문이 팩터 출처와 섞이지 않는가."""
        if not LEDGER.exists():
            return
        d = load()
        _assert(not (set(method_papers(d)) & set(d.get("papers") or {})))
        for k, v in (d.get("papers") or {}).items():
            _assert(v.get("question") in ("q1", "q2", "q3", "q4"), k)
    check("방법론 논문은 팩터 출처와 섞이지 않는다", _method_papers_separate)

    def _real_ledger():
        """실제 .papers.json 이 이관 가능한 모양인가."""
        if not LEDGER.exists():
            return
        d = load()
        m = migrate(d, at="2026-09-17")
        _assert(validate(m) == [], validate(m))
        _assert(len(m["papers"]) == len(d["papers"]))
        _assert(all(p["state"] in STATES for p in m["papers"].values()))
    check("실제 장부가 이관된다", _real_ledger)

    # ── 판정 불가는 상태를 되돌리지 못한다 ────────────────────────────
    #
    # '이번에는 못 쟀다'는 판정이 아니다. 그것이 이전 판정을 뒤집으면,
    # 표본이 얇은 구간을 한 번 돌리는 것만으로 경고가 지워지고 은퇴가
    # 풀린다 — 재개방의 근거가 '못 쟀다'가 된다.

    def _none_verdict(reason="표본이 얇습니다"):
        return {"schema": "ki.replication/1", "verdict": "판정 불가",
                "observed": None, "reason": reason}

    def _none_does_not_lift_warned():
        d = migrate(_v1(), at="2026-01-01")
        k = next(iter(d["papers"]))
        d["papers"][k]["state"] = WARNED
        d["papers"][k]["state_reason"] = "2026-03-01 흔들렸다"
        out = record(d, k, _none_verdict(), at="2026-09-18")
        _assert(out["papers"][k]["state"] == WARNED, out["papers"][k]["state"])
    check("판정 불가는 warned 를 unverified 로 올리지 않는다",
          _none_does_not_lift_warned)

    def _none_does_not_revive_retired():
        d = migrate(_v1(), at="2026-01-01")
        k = next(iter(d["papers"]))
        d["papers"][k]["state"] = RETIRED
        d["papers"][k]["state_reason"] = "2026-03-01 우리 표본에서 반대 방향"
        d["papers"][k]["state_at"] = "2026-03-01"
        out = record(d, k, _none_verdict(), at="2026-09-18")
        got = out["papers"][k]
        _assert(got["state"] == RETIRED, got["state"])
        _assert("반대 방향" in got["state_reason"], got["state_reason"])
        _assert(got["state_at"] == "2026-03-01", got["state_at"])
        _assert(len(got["replication"]) == 1, got["replication"])   # 기록은 쌓인다
    check("판정 불가는 은퇴본을 되살리지 않는다", _none_does_not_revive_retired)

    def _none_still_demotes_adopted():
        """되돌리지 않는다는 것이 아무것도 안 한다는 뜻은 아니다."""
        d = migrate(_v1(), at="2026-01-01")
        k = next(iter(d["papers"]))
        d["papers"][k]["state"] = ADOPTED
        out = record(d, k, _none_verdict(), at="2026-09-18")
        _assert(out["papers"][k]["state"] == WARNED, out["papers"][k]["state"])
    check("판정 불가는 채택본을 경고로 내린다", _none_still_demotes_adopted)

    for f in failed:
        print("  X  " + f, file=sys.stderr)
    print(f"papers     {passed} passed, {len(failed)} failed")
    return 1 if failed else 0


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="논문 장부 ki.papers/2")
    ap.add_argument("--selftest", action="store_true")
    ap.add_argument("--migrate", action="store_true", help="v1 → v2 로 옮긴다")
    ap.add_argument("--show", action="store_true", help="상태 요약")
    a = ap.parse_args()
    if a.migrate:
        d = load()
        was = d.get("schema")
        m = migrate(d)
        probs = validate(m)
        if probs:
            for x in probs:
                print("  X  " + x, file=sys.stderr)
            sys.exit(1)
        save(m)
        print(f"{was} → {m['schema']}  ({len(m['papers'])}편)")
        for k, p in m["papers"].items():
            print(f"  {k:14} {p['state']:11} {p.get('question', '?')}  {p['state_reason']}")
        sys.exit(0)
    if a.show:
        d = age_states(load())
        for k, p in d.get("papers", {}).items():
            ok, mark = citable(d, k)
            print(f"  {k:14} {p.get('state', '?'):11} 인용={'O' if ok else 'X'}  {mark}")
        sys.exit(0)
    sys.exit(selftest())
