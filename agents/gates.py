"""게이트 ①~⑦ — 발행 전 일곱 관문.

`selftest` 는 **코드**가 성립하는지 본다. 게이트는 **에이전트가 쓴 문장**이
성립하는지 본다. 둘은 다른 층이고, 앞의 것이 아무리 촘촘해도 뒤의 것을 대신하지
못한다. 측정 함수가 12.4 를 정확히 계산해도, 그 값에 "매도 검토" 라는 말이
붙어 회의자료로 나가면 이 시스템은 실패한 것이다.

**통과 아니면 반려다.** "대체로 지켜졌다"는 판정이 없다. 반려된 절은 회의자료에
빈칸이 아니라 '반려됨 — 사유' 로 보인다. 빈칸은 아무도 묻지 않지만 '반려됨'은
반드시 묻게 되기 때문이다. 조용히 통과시키는 것이 가장 위험하다.

    python agents/gates.py --selftest
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

import envelope as E
import papers as P

SCHEMA = "ki.gates/1"

# 신선도 임계 — 원장은 일별 종가라 며칠 묵는다 (규칙 3).
STALE_MAX_D = 3

# 4-eyes: 이 둘이 함께 봐야 한다.
REVIEWERS = ("risk", "compliance")

# 유출 검사에서 찾는 것. 키 값 자체는 여기 적지 않는다 — 이름만 본다.
_KEY_NAMES = ("KRX_API_KEY", "DART_API_KEY", "ECOS_API_KEY", "FRED_API_KEY",
              "KIS_APP_KEY", "KIS_APP_SECRET", "S2_API_KEY")
_SECRET_PARAM = re.compile(
    r"(auth[_-]?key|api[_-]?key|crtfc[_-]?key|appkey|appsecret|serviceKey|token)"
    r"\s*=\s*[^&\s'\")]+", re.I)
_URL_WITH_QUERY = re.compile(r"https?://[^\s'\"]+\?[^\s'\"]+")


class Result:
    __slots__ = ("gate", "name", "ok", "reason", "marks")

    def __init__(self, gate, name, ok, reason=None, marks=None):
        self.gate, self.name, self.ok = gate, name, ok
        self.reason, self.marks = reason, list(marks or [])

    def as_dict(self) -> dict:
        return {"gate": self.gate, "name": self.name, "ok": self.ok,
                "reason": self.reason, "marks": self.marks}

    def __repr__(self):
        return f"<{self.gate} {self.name} {'통과' if self.ok else '반려'}>"


# ── ① 판정 어휘 ───────────────────────────────────────────────────────

def gate1_verdict_words(env: dict, **_) -> Result:
    """점수·목표주가·매수/매도 어휘가 있는가 (규칙 1).

    산문에만 건다. 봉투에는 `source_grade` 처럼 '등급'이라는 말이 정당하게
    들어가는 자리가 있어서, 봉투 전체를 훑으면 멀쩡한 필드가 걸린다."""
    text = E.prose(env)
    hit = [w for w in E.BANNED_WORDS if w in text]
    bad_keys = [".".join(path + (k,)) for path, k in E._walk_keys(env)
                if k in E.BANNED_KEYS and (path + (k,)) != E._VERDICT_OK_PATH]
    if hit or bad_keys:
        why = []
        if hit:
            why.append(f"금지된 말 {', '.join(hit)}")
        if bad_keys:
            why.append(f"판단을 뜻하는 키 {', '.join(bad_keys)}")
        return Result("①", "판정 어휘", False,
                      " · ".join(why) + " — 해당 문장을 삭제한 뒤 다시 내십시오")
    return Result("①", "판정 어휘", True)


# ── ② 출처 등급 ───────────────────────────────────────────────────────

def gate2_source_grade(env: dict, **_) -> Result:
    """모든 주장에 등급이 있는가 · '해석'이 승격되지 않았는가 (규칙 4)."""
    g = env.get("source_grade")
    if g not in E.GRADES:
        return Result("②", "출처 등급", False,
                      f"등급이 없거나 목록에 없습니다: {g!r}")
    if g == E.PRIMARY and not (env.get("sources") or []):
        return Result("②", "출처 등급", False,
                      "1차 라고 적었는데 공식 출처가 비어 있습니다")
    # 해석이 1차로 올라온 흔적. 승격 경로가 없으므로 이건 사람이 손으로 고친 것이다.
    if env.get("promoted_from") in E.NEVER_PROMOTED:
        return Result("②", "출처 등급", False,
                      f"{env['promoted_from']!r} 는 승격되지 않습니다 — "
                      f"데스크가 재료를 읽고 쓴 문장은 그 재료의 등급을 물려받지 않습니다")
    return Result("②", "출처 등급", True)


# ── ③ 재현 ────────────────────────────────────────────────────────────

def gate3_replication(env: dict, ledger: dict = None, **_) -> Result:
    """인용한 논문이 우리 표본에서 어떻게 나왔는가.

    막는 것은 **은퇴본과 방향 반대**뿐이다. `unverified` 는 통과시키되 '미검증'
    표시를 함께 내보낸다.

    왜 미검증을 막지 않는가 — 주 1회 사이클로 돌리면 어느 시점에나 아직 재현을
    돌리지 못한 논문이 남는다. 그것을 전부 막으면 관문이 아니라 정지 버튼이
    된다. 표시를 달고 나가면 회의에서 그 문장의 무게가 달라지고, 그것이 이
    관문이 실제로 원하는 것이다."""
    m = env.get("method") or {}
    key = m.get("paper")
    if not key:
        return Result("③", "재현", True)                # 논문을 안 썼으면 볼 것이 없다
    if ledger is None:
        return Result("③", "재현", False, "논문 장부를 읽을 수 없습니다")

    ok, mark = P.citable(ledger, key)
    st = P.state_of(ledger, key)
    if not ok:
        return Result("③", "재현", False, f"{key}: {mark}")
    if m.get("paper_state") and m["paper_state"] != st:
        return Result("③", "재현", False,
                      f"{key}: 봉투는 {m['paper_state']!r} 라고 적었는데 "
                      f"장부는 {st!r} 입니다")
    rep = m.get("replication")
    if rep and rep.get("verdict") == "방향 반대":
        return Result("③", "재현", False,
                      f"{key}: 우리 표본에서 논문과 반대 방향입니다")
    return Result("③", "재현", True, marks=[mark] if mark else [])


# ── ④ 논문 실재 ───────────────────────────────────────────────────────

def gate4_paper_exists(env: dict, ledger: dict = None, **_) -> Result:
    """인용한 논문이 장부에 실재하는가 · 한계가 비어 있지 않은가 (규칙 4).

    가장 흔한 사고는 논문이 말한 적 없는 것을 말했다고 읽는 것이다. 그래서
    값과 함께 **그 논문이 주장하지 않는 것**을 반드시 같이 낸다."""
    m = env.get("method") or {}
    key = m.get("paper")
    if key:
        if ledger is None or P.state_of(ledger, key) is None:
            return Result("④", "논문 실재", False,
                          f"장부에 없는 논문입니다: {key} — 지어낸 인용일 수 있습니다")
    lim = env.get("limits")
    if not (isinstance(lim, list) and lim and all(str(x).strip() for x in lim)):
        return Result("④", "논문 실재", False,
                      "limits 가 비어 있습니다 — 그 방법이 주장하지 않는 것을 적으십시오")
    return Result("④", "논문 실재", True)


# ── ⑤ 신선도 ──────────────────────────────────────────────────────────

def gate5_freshness(env: dict, stale_max: int = STALE_MAX_D, **_) -> Result:
    """기준일과 경과일수가 임계를 넘지 않는가 (규칙 3).

    넘으면 값을 지우고 '데이터 없음'으로 바꾼다. 묵은 값을 조용히 내보내는
    것보다 빈칸이 낫다 — 빈칸은 며칠 묵었는지 묻게 만든다."""
    if not env.get("asof"):
        return Result("⑤", "신선도", False, "기준일(asof)이 없습니다")
    sd = env.get("stale_days")
    if sd is None:
        return Result("⑤", "신선도", True)              # 경과일수를 못 재는 값도 있다
    if sd > stale_max:
        return Result("⑤", "신선도", False,
                      f"기준일이 {sd}영업일 지났습니다 (임계 {stale_max}) — "
                      f"값 대신 '데이터 없음'으로 내보내십시오")
    return Result("⑤", "신선도", True)


# ── ⑥ 유출 검사 ───────────────────────────────────────────────────────

def gate6_leak(env: dict, secret_names=_KEY_NAMES, **_) -> Result:
    """키·인증 URL 이 문장에 남았는가 (규칙 5).

    `requests` 예외에는 호출 URL 이 통째로 들어가고 DART 는 인증키를 쿼리
    파라미터로 보낸다. 에이전트가 오류 문구를 그대로 봉투에 옮겨 담으면 그
    키가 회의자료까지 간다.

    하나라도 걸리면 그 절이 아니라 **발행 전체**를 멈춘다. 유출은 되돌릴 수
    없어서, 다른 절이 멀쩡한지는 이 판단에 영향을 주지 않는다."""
    blob = json.dumps(env, ensure_ascii=False)
    hits = []
    if _SECRET_PARAM.search(blob):
        hits.append("인증 파라미터가 포함된 문자열")
    if _URL_WITH_QUERY.search(blob):
        hits.append("쿼리가 붙은 호출 URL")
    import os
    for n in secret_names:
        v = os.environ.get(n, "").strip()
        if v and len(v) >= 8 and v in blob:
            hits.append(f"{n} 값")
    if hits:
        return Result("⑥", "유출 검사", False,
                      f"{' · '.join(hits)} 이(가) 남아 있습니다 — "
                      f"scrub() 을 통과시킨 뒤 다시 내십시오. 발행을 멈춥니다.")
    return Result("⑥", "유출 검사", True)


# ── ⑦ 4-eyes ─────────────────────────────────────────────────────────

def gate7_four_eyes(env: dict, reviewers=REVIEWERS, **_) -> Result:
    """리스크와 준법감시 양쪽이 봤는가.

    같은 데스크가 스스로를 승인할 수 없다. 자기 검토는 검토가 아니다."""
    seen = set(env.get("reviewed_by") or [])
    missing = [r for r in reviewers if r not in seen]
    if missing:
        return Result("⑦", "4-eyes", False,
                      f"{', '.join(missing)} 승인이 없습니다 — 해당 절을 제외합니다")
    if env.get("desk") in seen:
        return Result("⑦", "4-eyes", False,
                      f"{env['desk']} 가 자기 문장을 승인했습니다 — 자기 검토는 검토가 아닙니다")
    return Result("⑦", "4-eyes", True)


GATES = (gate1_verdict_words, gate2_source_grade, gate3_replication,
         gate4_paper_exists, gate5_freshness, gate6_leak, gate7_four_eyes)


def run(env: dict, ledger: dict = None, **kw) -> dict:
    """일곱 관문을 전부 돌린다. 하나 걸렸다고 멈추지 않는다.

    첫 반려에서 멈추면 두 번째 문제를 볼 때까지 왕복이 는다. 다만 ⑥ 유출이
    걸리면 그것은 절 단위가 아니라 발행 전체를 멈추는 사유다."""
    shape = E.validate(env)
    results = [r.as_dict() for r in (g(env, ledger=ledger, **kw) for g in GATES)]
    failed = [r for r in results if not r["ok"]]
    leak = any(r["gate"] == "⑥" and not r["ok"] for r in results)
    return {
        "schema": SCHEMA,
        "instance": env.get("instance"),
        "desk": env.get("desk"),
        "ok": not failed and not shape,
        "halt_publication": leak,
        "shape_problems": shape,
        "results": results,
        "marks": [m for r in results for m in r["marks"]],
        "reason": None if (not failed and not shape) else
                  " / ".join([f"{r['gate']} {r['name']}: {r['reason']}" for r in failed]
                             + shape),
    }


# ── 자체 검사 ─────────────────────────────────────────────────────────

def _ledger() -> dict:
    d = P.migrate({
        "schema": "ki.papers/1",
        "papers": {
            "amihud2002": {"authors": "A", "year": 2002, "title": "T", "journal": "J",
                           "question": "q2", "adopted": True},
            "jt1993": {"authors": "B", "year": 1993, "title": "T", "journal": "J",
                       "question": "q1", "adopted": True},
        }}, at="2026-09-17")
    # jt1993 은 우리 표본에서 방향이 뒤집혔다고 하자 — 널리 알려진 사실이다.
    d = P.record(d, "jt1993", {"verdict": "방향 반대", "observed": {"t": -4.1}},
                 at="2026-09-17")
    return d


def _env(**over) -> dict:
    e = E.make(
        "처분 소요일수 12.4 영업일", value=12.4, unit="business_days",
        desk="q2-disposal", asof="2026-09-11", stale_days=2,
        source_grade="해석", sources=["KRX/일별매매정보"], subject="000660",
        method={"paper": "amihud2002", "paper_state": "unverified"},
        limits=["논문 표본은 미국 상장주 — 코스닥 외삽의 근거가 아니다"],
    )
    e["reviewed_by"] = ["risk", "compliance"]
    e.update(over)
    return e


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

    L = _ledger()

    def _clean_passes():
        r = run(_env(), L)
        _assert(r["ok"], r["reason"])
        _assert(not r["halt_publication"])
    check("성립하는 봉투는 일곱 관문을 통과한다", _clean_passes)

    def _g1_words():
        for w in ("매수", "저평가", "목표주가", "비중확대"):
            e = _env(claim=f"처분 소요일수 12.4 영업일 — {w} 검토")
            r = run(e, L)
            _assert(not r["ok"], w)
            _assert(any(x["gate"] == "①" and not x["ok"] for x in r["results"]), w)
    check("① 판정 어휘를 잡는다", _g1_words)

    def _g1_in_limits():
        """한계 칸에 숨겨도 잡힌다 — 산문은 어디에 있든 산문이다."""
        e = _env(limits=["표본이 다르다", "다만 저평가 국면에서는 다를 수 있다"])
        _assert(not run(e, L)["ok"])
    check("① 한계 칸에 숨긴 판정 어휘도 잡는다", _g1_in_limits)

    def _g1_grade_field_ok():
        """'등급'이라는 말이 정당하게 있는 필드는 걸리면 안 된다."""
        _assert(run(_env(source_grade="해석"), L)["ok"])
    check("① 등급 필드를 오탐하지 않는다", _g1_grade_field_ok)

    def _g2_missing():
        e = _env(); e["source_grade"] = None
        r = run(e, L)
        _assert(any(x["gate"] == "②" and not x["ok"] for x in r["results"]))
    check("② 등급 없는 주장을 막는다", _g2_missing)

    def _g2_promotion():
        e = _env(source_grade="1차", promoted_from="해석")
        r = run(e, L)
        _assert(any(x["gate"] == "②" and not x["ok"] for x in r["results"]))
    check("② 해석의 승격을 막는다", _g2_promotion)

    def _g3_unverified_passes_with_mark():
        r = run(_env(), L)
        _assert(r["ok"])
        _assert(any("미검증" in m for m in r["marks"]), r["marks"])
    check("③ 미검증은 통과하되 표시가 붙는다", _g3_unverified_passes_with_mark)

    def _g3_retired_blocked():
        e = _env(method={"paper": "jt1993", "paper_state": "retired"})
        r = run(e, L)
        _assert(not r["ok"])
        _assert(any(x["gate"] == "③" and not x["ok"] for x in r["results"]))
    check("③ 은퇴본 인용을 반려한다", _g3_retired_blocked)

    def _g3_state_mismatch():
        """봉투가 적은 상태와 장부가 다르면 반려한다 — 오래된 상태를 물고 온 것이다."""
        e = _env(method={"paper": "amihud2002", "paper_state": "adopted"})
        r = run(e, L)
        _assert(not r["ok"])
        _assert(any(x["gate"] == "③" and "장부" in (x["reason"] or "")
                    for x in r["results"]))
    check("③ 봉투와 장부의 상태가 어긋나면 반려한다", _g3_state_mismatch)

    def _g4_ghost_paper():
        e = _env(method={"paper": "없는논문2099", "paper_state": "adopted"})
        r = run(e, L)
        _assert(not r["ok"])
        _assert(any(x["gate"] == "④" and not x["ok"] for x in r["results"]))
    check("④ 장부에 없는 논문 인용을 막는다 (지어낸 인용)", _g4_ghost_paper)

    def _g4_no_limits():
        e = _env(limits=[])
        r = run(e, L)
        _assert(any(x["gate"] == "④" and not x["ok"] for x in r["results"]))
    check("④ 한계 없는 주장을 막는다", _g4_no_limits)

    def _g5_stale():
        e = _env(stale_days=9)
        r = run(e, L)
        _assert(not r["ok"])
        _assert(any(x["gate"] == "⑤" and not x["ok"] for x in r["results"]))
        _assert(run(_env(stale_days=3), L)["ok"])       # 임계값은 통과
    check("⑤ 묵은 값을 막는다 (임계 3영업일)", _g5_stale)

    def _g6_key_in_text():
        import os
        os.environ["DART_API_KEY"] = "abcdef0123456789"
        try:
            e = _env(reason="요청 실패: key=abcdef0123456789")
            r = run(e, L)
            _assert(not r["ok"])
            _assert(r["halt_publication"], "유출은 발행 전체를 멈춰야 합니다")
        finally:
            os.environ.pop("DART_API_KEY", None)
    check("⑥ 문장에 남은 키를 잡고 발행을 멈춘다", _g6_key_in_text)

    def _g6_url():
        e = _env(reason="https://opendart.fss.or.kr/api/list.json?crtfc_key=XYZ&code=1")
        r = run(e, L)
        _assert(not r["ok"] and r["halt_publication"])
    check("⑥ 인증키가 붙은 호출 URL 을 잡는다", _g6_url)

    def _g6_clean():
        e = _env(reason="요청 실패: 인증키가 거부됐습니다 (<DART_API_KEY>)")
        _assert(run(e, L)["ok"])                        # scrub 된 문구는 통과
    check("⑥ scrub 된 문구는 통과시킨다", _g6_clean)

    def _g7_missing():
        e = _env(); e["reviewed_by"] = ["risk"]
        r = run(e, L)
        _assert(not r["ok"])
        _assert(any(x["gate"] == "⑦" and "compliance" in (x["reason"] or "")
                    for x in r["results"]))
    check("⑦ 한쪽 승인만으로는 통과하지 않는다", _g7_missing)

    def _g7_self_review():
        e = _env(); e["reviewed_by"] = ["risk", "compliance", "q2-disposal"]
        r = run(e, L)
        _assert(not r["ok"])
    check("⑦ 자기 검토를 막는다", _g7_self_review)

    def _all_gates_report():
        """하나 걸렸다고 나머지를 건너뛰지 않는다 — 왕복을 줄이기 위해서다."""
        e = _env(claim="매수 검토", limits=[], stale_days=99)
        e["reviewed_by"] = []
        r = run(e, L)
        _assert(len(r["results"]) == 7)
        bad = [x["gate"] for x in r["results"] if not x["ok"]]
        _assert(set(bad) >= {"①", "④", "⑤", "⑦"}, bad)
    check("반려돼도 일곱 관문을 모두 보고한다", _all_gates_report)

    def _shape_checked():
        e = _env(); del e["instance"]
        r = run(e, L)
        _assert(not r["ok"] and r["shape_problems"])
    check("봉투 형식도 함께 검사한다", _shape_checked)

    def _no_ledger():
        e = _env()
        r = run(e, None)
        _assert(not r["ok"])                            # 장부 없이 통과시키지 않는다
    check("논문 장부가 없으면 통과시키지 않는다", _no_ledger)

    for f in failed:
        print("  X  " + f, file=sys.stderr)
    print(f"gates      {passed} passed, {len(failed)} failed")
    return 1 if failed else 0


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="게이트 ①~⑦")
    ap.add_argument("--selftest", action="store_true")
    ap.add_argument("--check", help="봉투 JSON 파일을 검사한다")
    ap.add_argument("--indent", type=int, default=2)
    a = ap.parse_args()
    if a.check:
        env_doc = json.loads(Path(a.check).read_text(encoding="utf-8"))
        led = P.age_states(P.migrate(P.load())) if P.LEDGER.exists() else None
        out = run(env_doc, led)
        print(json.dumps(out, ensure_ascii=False, indent=a.indent))
        sys.exit(0 if out["ok"] else 1)
    sys.exit(selftest())
