"""대조 — 두 데스크의 판정이 갈렸는가.

데스크는 서로의 산출을 보지 않는다. **수렴하면 교차검증의 뜻이 사라지기**
때문이다. 그런데 격리만 해 놓고 아무도 대조하지 않으면 격리가 사 주는 것이
없다 — 서로 무관한 문장이 나올 뿐이고, 회의에는 그중 하나만 올라간다.

**갈렸다는 사실 자체가 회의에서 가장 중요한 정보다.** 이 모듈은 그것을 찾아
낸다. 평균 내지 않고, 어느 쪽이 옳은지도 정하지 않는다.

## 세 가지만 본다 — 전부 기계적으로 판정된다

    ① 같은 칸을 다르게 읽었다     원장은 하나다. 다르면 둘 중 하나가 틀렸다
    ② 같은 논문을 다른 상태로 인용  장부는 하나다. 하나가 낡은 것을 물고 왔다
    ③ 같은 것을 재고 값이 벌어졌다  measure 가 같은데 값이 다르다

①②는 **모순**이라 허용 오차가 없다. 원장도 장부도 하나이므로, 다르면 다른
것이다. ③은 서로 다른 방법으로 잰 독립 추정이라 어느 정도 차이는 정상이고,
그래서 **상대 오차를 명시적으로 받는다.**

문장의 뜻이 어긋나는 것(같은 종목을 두고 한쪽은 "팔기 쉽다", 다른 쪽은
"어렵다")은 여기서 못 잡는다. 그건 의미 판단이고, 코드가 하면 조용히 틀린다.
그 몫은 ic-chair 와 회의다.

    python agents/reconcile.py --selftest
    python agents/reconcile.py --envelopes agents/envelopes
"""
from __future__ import annotations

import argparse
import json
import sys
from itertools import combinations
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import envelope as E                                     # noqa: E402

SCHEMA = "ki.reconcile/1"

# ③ 의 상대 오차. **자연상수가 아니다** — 재현 임계 3.0 과 같은 성격의 약속이다.
#
# 두 데스크가 서로 다른 방법으로 같은 것을 재면 얼마간은 벌어진다. 0 으로 두면
# 반올림까지 갈렸다고 보고돼 대조가 소음이 되고, 크게 두면 회의에서 다른
# 이야기가 될 만한 차이를 놓친다. 10% 는 "같은 결론을 낼 수 있는 범위"로
# 잡은 값이고, 산출에 언제나 함께 적혀 나간다.
REL_TOL = 0.10

READ_CONFLICT = "같은 칸을 다르게 읽음"
PAPER_CONFLICT = "같은 논문을 다른 상태로 인용"
MEASURE_GAP = "같은 것을 쟀는데 값이 벌어짐"


def _num(v):
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def _raw_reads(env: dict) -> dict:
    """원본으로 읽은 것만. 파생값은 계산 방법이 달라 비교 대상이 아니다."""
    out = {}
    for o in env.get("read") or []:
        if o.get("kind", E.RAW) != E.RAW:
            continue
        out[(o.get("key"), o.get("asof"))] = o.get("value")
    return out


def _same(a, b) -> bool:
    if a is None or b is None:
        return a is b
    fa, fb = _num(a), _num(b)
    if fa is None or fb is None:
        return a == b
    scale = max(abs(fa), abs(fb))
    return abs(fa - fb) <= 1e-9 * scale if scale else fa == fb


def conflicts(envelopes: list, rel_tol: float = REL_TOL) -> list:
    """갈린 곳을 찾는다. 어느 쪽이 옳은지는 정하지 않는다."""
    out = []
    for a, b in combinations([e for e in envelopes if isinstance(e, dict)], 2):
        ia, ib = a.get("instance"), b.get("instance")
        da, db = a.get("desk"), b.get("desk")
        if ia == ib:
            continue

        # ① 같은 칸을 다르게 읽었다 — 원장은 하나다
        ra, rb = _raw_reads(a), _raw_reads(b)
        for k in set(ra) & set(rb):
            if not _same(ra[k], rb[k]):
                out.append({
                    "kind": READ_CONFLICT, "key": k[0], "asof": k[1],
                    "left": {"instance": ia, "desk": da, "value": ra[k]},
                    "right": {"instance": ib, "desk": db, "value": rb[k]},
                    "why": ("원장은 하나입니다. 같은 칸을 같은 기준일로 읽었는데 "
                            "값이 다르면 둘 중 하나가 틀렸거나 낡았습니다."),
                })

        # ② 같은 논문을 다른 상태로 인용했다 — 장부는 하나다
        ma, mb = a.get("method") or {}, b.get("method") or {}
        if ma.get("paper") and ma.get("paper") == mb.get("paper") \
                and ma.get("paper_state") != mb.get("paper_state"):
            out.append({
                "kind": PAPER_CONFLICT, "paper": ma["paper"],
                "left": {"instance": ia, "desk": da, "state": ma.get("paper_state")},
                "right": {"instance": ib, "desk": db, "state": mb.get("paper_state")},
                "why": ("논문 장부는 하나입니다. 상태가 다르면 하나가 낡은 것을 "
                        "물고 왔습니다 — papers 도구로 다시 읽으십시오."),
            })

        # ③ 같은 것을 쟀는데 값이 벌어졌다
        if (a.get("measure") and a.get("measure") == b.get("measure")
                and a.get("subject") == b.get("subject")):
            va, vb = _num(a.get("value")), _num(b.get("value"))
            if va is not None and vb is not None:
                scale = max(abs(va), abs(vb))
                gap = abs(va - vb) / scale if scale else 0.0
                if gap > rel_tol:
                    out.append({
                        "kind": MEASURE_GAP, "measure": a["measure"],
                        "subject": a.get("subject"), "gap": round(gap, 4),
                        "rel_tol": rel_tol,
                        "left": {"instance": ia, "desk": da, "value": va,
                                 "unit": a.get("unit")},
                        "right": {"instance": ib, "desk": db, "value": vb,
                                  "unit": b.get("unit")},
                        "why": ("같은 것을 서로 다른 방법으로 쟀는데 값이 "
                                f"{gap:.0%} 벌어졌습니다 (허용 {rel_tol:.0%}). "
                                "평균 내지 마십시오 — 양쪽을 그대로 싣습니다."),
                    })
    return out


def review(envelopes: list, rel_tol: float = REL_TOL) -> dict:
    """대조 결과. **어느 쪽이 옳은지 정하지 않는다** — 갈렸다는 사실을 낸다."""
    envs = [e for e in envelopes if isinstance(e, dict)]
    cs = conflicts(envs, rel_tol)

    # 값을 냈는데 measure 가 없으면 대조 자체가 안 된다. 그 사실을 세지 않으면
    # "갈린 곳 없음"이 '합의'로 읽힌다. 실제로는 **비교하지 않았다** 는 뜻이다.
    uncomparable = [{"instance": e.get("instance"), "desk": e.get("desk"),
                     "claim": e.get("claim")}
                    for e in envs if e.get("value") is not None and not e.get("measure")]

    measured = {}
    for e in envs:
        if e.get("measure") and e.get("value") is not None:
            measured.setdefault((e["measure"], e.get("subject")), []).append(e)
    compared = sum(1 for v in measured.values() if len(v) > 1)

    return {
        "schema": SCHEMA, "n_envelopes": len(envs), "rel_tol": rel_tol,
        "conflicts": cs, "n_conflicts": len(cs),
        "compared_pairs": compared,
        "uncomparable": uncomparable, "n_uncomparable": len(uncomparable),
        "note": ("갈렸다는 사실이 회의에서 가장 중요한 정보입니다. 평균 내지 "
                 "말고 양쪽을 그대로 싣습니다. 어느 쪽이 옳은지는 사람이 "
                 "정합니다."),
        "blind_spot": ("문장의 뜻이 어긋나는 것은 여기서 못 잡습니다 — 의미 "
                       "판단이고, 코드가 하면 조용히 틀립니다. ic-chair 와 "
                       "회의의 몫입니다."),
    }


# ── 자체 검사 ─────────────────────────────────────────────────────────

def _env(desk, value, *, measure="disposal_days", subject="000660",
         reads=(), paper_state="unverified", salt=""):
    e = E.make(f"{measure} {value}", value=value, unit="business_days", desk=desk,
               asof="2026-09-18", stale_days=1, source_grade="해석",
               sources=["KRX/일별매매정보"], subject=subject, measure=measure,
               salt=salt or desk,
               method={"paper": "amihud2002", "paper_state": paper_state},
               read=list(reads) or [E.observation("KRX/일별매매정보",
                                                  "000660.close", 88.0, "2026-09-18")],
               limits=["평시 기준이다"])
    e["reviewed_by"] = ["risk", "compliance"]
    return e


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

    def _agree():
        r = review([_env("q2-disposal", 25.0), _env("risk-officer", 25.4)])
        _assert(r["n_conflicts"] == 0, r["conflicts"])
        _assert(r["compared_pairs"] == 1)      # 비교는 **했다**
    check("값이 가까우면 갈렸다고 하지 않는다", _agree)

    def _measure_gap():
        r = review([_env("q2-disposal", 25.0), _env("risk-officer", 41.0)])
        _assert(r["n_conflicts"] == 1, r["conflicts"])
        c = r["conflicts"][0]
        _assert(c["kind"] == MEASURE_GAP)
        _assert(c["gap"] > c["rel_tol"])
        _assert("평균 내지" in c["why"])
        _assert(c["left"]["desk"] != c["right"]["desk"])
    check("같은 것을 쟀는데 벌어지면 잡는다", _measure_gap)

    def _tolerance_is_explicit():
        """허용 오차가 산출에 언제나 적혀 나간다 — 보이지 않는 숫자를 두지 않는다."""
        a, b = _env("q2-disposal", 100.0), _env("risk-officer", 112.0)
        loose = review([a, b], rel_tol=0.20)
        tight = review([a, b], rel_tol=0.05)
        _assert(loose["n_conflicts"] == 0 and tight["n_conflicts"] == 1)
        _assert(loose["rel_tol"] == 0.20 and tight["rel_tol"] == 0.05)
        _assert(tight["conflicts"][0]["rel_tol"] == 0.05)
    check("허용 오차가 명시적이고 판정을 가른다", _tolerance_is_explicit)

    def _read_conflict_has_no_tolerance():
        """원장은 하나다 — 같은 칸이 다르면 허용 오차가 없다."""
        o1 = E.observation("KRX/일별매매정보", "000660.close", 88.0, "2026-09-18")
        o2 = E.observation("KRX/일별매매정보", "000660.close", 88.5, "2026-09-18")
        r = review([_env("q2-disposal", 25.0, reads=[o1]),
                    _env("q3-execution", 25.1, reads=[o2])])
        cs = [c for c in r["conflicts"] if c["kind"] == READ_CONFLICT]
        _assert(len(cs) == 1, r["conflicts"])   # 0.6% 차이인데도 잡는다
        _assert("원장은 하나" in cs[0]["why"])
    check("같은 칸을 다르게 읽으면 허용 오차 없이 잡는다", _read_conflict_has_no_tolerance)

    def _different_asof_is_not_conflict():
        """기준일이 다르면 값이 달라도 모순이 아니다."""
        o1 = E.observation("KRX", "000660.close", 88.0, "2026-09-18")
        o2 = E.observation("KRX", "000660.close", 91.0, "2026-09-17")
        r = review([_env("q2-disposal", 25.0, reads=[o1]),
                    _env("q3-execution", 25.1, reads=[o2])])
        _assert(not [c for c in r["conflicts"] if c["kind"] == READ_CONFLICT],
                r["conflicts"])
    check("기준일이 다르면 모순이 아니다", _different_asof_is_not_conflict)

    def _derived_not_compared():
        """파생값은 계산 방법이 달라 비교 대상이 아니다.

        앞서 되짚기에서 같은 실수를 했다 — 60일 평균을 원장의 칸과 비교해
        거짓 '바뀜'이 나왔다. 여기서 되풀이하지 않는다."""
        d1 = E.observation("KRX", "000660.adv", 1.0e8, "2026-09-18",
                           kind=E.DERIVED, basis="60일 평균")
        d2 = E.observation("KRX", "000660.adv", 4.0e8, "2026-09-18",
                           kind=E.DERIVED, basis="20일 평균")
        r = review([_env("q2-disposal", 25.0, reads=[d1]),
                    _env("q3-execution", 25.1, reads=[d2])])
        _assert(not [c for c in r["conflicts"] if c["kind"] == READ_CONFLICT],
                r["conflicts"])
    check("파생값은 서로 비교하지 않는다", _derived_not_compared)

    def _paper_state_conflict():
        r = review([_env("q2-disposal", 25.0, paper_state="unverified"),
                    _env("quant-method", 25.1, paper_state="adopted")])
        cs = [c for c in r["conflicts"] if c["kind"] == PAPER_CONFLICT]
        _assert(len(cs) == 1, r["conflicts"])
        _assert(cs[0]["paper"] == "amihud2002")
        _assert("낡은 것" in cs[0]["why"])
    check("같은 논문을 다른 상태로 인용하면 잡는다", _paper_state_conflict)

    def _different_subject():
        r = review([_env("q2-disposal", 25.0, subject="000660"),
                    _env("q2-disposal", 90.0, subject="111111", salt="x")])
        _assert(not [c for c in r["conflicts"] if c["kind"] == MEASURE_GAP])
    check("다른 종목이면 갈린 것이 아니다", _different_subject)

    def _uncomparable_is_counted():
        """대조하지 못한 것을 세지 않으면 '갈린 곳 없음'이 합의로 읽힌다.

        실제로는 비교를 **안 한** 것이다. 그 둘은 전혀 다르다."""
        a = _env("q2-disposal", 25.0); a["measure"] = None
        b = _env("q3-execution", 99.0); b["measure"] = None
        r = review([a, b])
        _assert(r["n_conflicts"] == 0)
        _assert(r["n_uncomparable"] == 2, r)
        _assert(r["compared_pairs"] == 0)
        _assert(r["uncomparable"][0]["desk"])
    check("대조하지 못한 봉투를 따로 센다 ('없음'과 '안 봄'은 다르다)",
          _uncomparable_is_counted)

    def _no_value_is_not_uncomparable():
        a = _env("q2-disposal", 25.0)
        a["measure"] = None; a["value"] = None; a["read"] = []
        a["reason"] = "일봉이 12개뿐입니다"
        r = review([a])
        _assert(r["n_uncomparable"] == 0)      # 값이 없으면 대조할 것도 없다
    check("값이 없는 봉투는 대조 대상이 아니다", _no_value_is_not_uncomparable)

    def _does_not_judge():
        """어느 쪽이 옳은지 정하지 않는다. 판정 어휘도 쓰지 않는다."""
        r = review([_env("q2-disposal", 25.0), _env("risk-officer", 41.0)])
        blob = json.dumps(r, ensure_ascii=False)
        for w in E.BANNED_WORDS:
            _assert(w not in blob, w)
        for w in ("옳다", "맞다", "틀렸다고 판정", "채택한다"):
            _assert(w not in blob, w)
        _assert("사람이" in r["note"])
        _assert(r.get("blind_spot"))           # 못 보는 것을 밝힌다
    check("어느 쪽이 옳은지 정하지 않고 못 보는 것을 밝힌다", _does_not_judge)

    def _deterministic():
        e = [_env("q2-disposal", 25.0), _env("risk-officer", 41.0)]
        _assert(review(e) == review(list(e)))
    check("두 번 대조하면 같은 결과가 나온다", _deterministic)

    def _self_not_compared():
        e = _env("q2-disposal", 25.0)
        _assert(review([e, dict(e)])["n_conflicts"] == 0)
    check("같은 인스턴스를 자기와 대조하지 않는다", _self_not_compared)

    for f in failed:
        print("  X  " + f, file=sys.stderr)
    print(f"reconcile  {passed} passed, {len(failed)} failed")
    return 1 if failed else 0


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="대조 — 두 데스크의 판정이 갈렸는가")
    ap.add_argument("--selftest", action="store_true")
    ap.add_argument("--envelopes")
    ap.add_argument("--rel-tol", type=float, default=REL_TOL)
    ap.add_argument("--indent", type=int, default=2)
    a = ap.parse_args()
    if not a.envelopes:
        sys.exit(selftest())
    import run_day as D                                   # noqa: E402
    envs = D.load_envelopes(Path(a.envelopes))
    print(json.dumps(review(envs, a.rel_tol), ensure_ascii=False, indent=a.indent))
