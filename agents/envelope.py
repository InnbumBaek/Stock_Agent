"""봉투 — 데스크가 내놓는 모든 주장이 입는 형식.

에이전트는 문장을 쓴다. 문장은 숫자와 달리 조용히 틀린다. "처분에 12영업일"
이라는 말은 그 자체로는 근거의 등급도, 언제 잰 값인지도, 그 방법이 무엇을
주장하지 않는지도 담지 않는다. 회의에서 위험한 것은 틀린 숫자가 아니라 **등급이
지워진 숫자**다.

그래서 데스크는 값을 그냥 내놓지 못한다. 반드시 이 봉투에 담는다.

    측정값 + 출처 등급 + 가정 + 한계 + 누가 언제 만들었는가

`validate()` 는 봉투가 성립하는지만 본다. 값이 맞는지는 보지 않는다 — 그것은
재현 러너와 원장의 몫이다. 여기서 보는 것은 **말해도 되는 형식인가**다.

    python agents/envelope.py --selftest
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from datetime import date, datetime

SCHEMA = "ki.envelope/2"

# ── 출처 등급 ─────────────────────────────────────────────────────────
#
# CLAUDE.md 규칙 4 의 네 등급에 다섯 번째를 더한다. 앞의 넷은 재료의 등급이고,
# "해석"은 **데스크가 만든 문장**의 등급이다.
#
# 이 다섯 번째가 이 시스템의 핵심이다. 에이전트가 1차 자료를 읽고 쓴 문장은
# 1차 자료가 아니다. 읽은 재료가 KRX 였다는 사실이 그 해석을 KRX 로 만들지
# 않는다. 승격 경로를 아예 없애 두지 않으면, 몇 단계를 거치는 사이에 누군가의
# 추측이 공식 통계의 얼굴로 회의에 올라온다.
GRADES = ("1차", "참고", "방법론", "사내", "해석")

PRIMARY = "1차"

# 해석은 무엇으로도 승격되지 않는다. 재료를 더 붙여도, 여러 데스크가 같은 말을
# 해도, 리스크가 승인해도 해석이다. 올리려면 사람이 1차 자료를 직접 인용하는
# 새 문장을 써야 한다 — 그것은 승격이 아니라 다른 주장이다.
NEVER_PROMOTED = ("해석",)

# ── 판정 어휘 ─────────────────────────────────────────────────────────
#
# ki_monitor.py 의 selftest 가 쓰는 목록과 같은 것에서 시작한다. 측정층에서
# 금지된 말이 판단층에서 허용될 이유가 없다. 데스크는 재료를 정리하고 그것이
# 무엇을 뜻할 수 있는지까지 쓴다. "사서 오른다"는 회의에서 사람이 말한다.
BANNED_WORDS = (
    "매수", "매도", "저평가", "고평가", "추천", "목표가", "목표주가",
    "비중확대", "비중축소", "적정주가", "투자의견", "강력매수",
)

# 봉투의 키로도 들어오면 안 되는 것. facts 가 막는 것과 같은 목록이다.
BANNED_KEYS = frozenset({
    "score", "rating", "recommendation", "signal", "verdict",
    "action", "advice", "target_price",
})

# verdict 는 금지 키지만 replication 안에서는 재현 **판정**을 뜻한다. 그것은
# 종목에 대한 판단이 아니라 논문에 대한 측정이므로 이 경로에서만 허용한다.
_VERDICT_OK_PATH = ("method", "replication", "verdict")

TIERS = ("T1", "T2", "T3")

_DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
_INSTANCE = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*-[0-9a-f]{4}$")


def new_instance(desk: str, at: str, subject: str, salt: str = "") -> str:
    """인스턴스 ID — 어느 실행이 이 문장을 만들었는가.

    같은 데스크·같은 날·같은 종목이라도 실행이 다르면 다른 ID 여야 한다.
    뒤 네 자리는 그 구분이고, 앞은 사람이 눈으로 읽기 위한 것이다.
    이 ID 가 있어야 "그때 그 값이 왜 그랬는가"를 되짚을 수 있다."""
    raw = f"{desk}|{at}|{subject}|{salt}".encode("utf-8")
    tail = hashlib.sha256(raw).hexdigest()[:4]
    slug = re.sub(r"[^a-z0-9]+", "-", f"{desk}-{at.replace('-', '')}-{subject}".lower())
    return f"{slug.strip('-')}-{tail}"


def observation(source: str, key: str, value, asof: str) -> dict:
    """관측 한 줄 — **그때 원장에 무엇이 적혀 있었는가.**

    이것이 재생 가능성의 전부다. 원장은 `INSERT OR REPLACE` 로 덮어써진다 —
    DART 정정공시가 오면 같은 칸이 조용히 바뀐다. 그러면 나중에 같은 질문을
    다시 던져도 다른 답이 나오고, **"에이전트가 틀렸다"와 "데이터가 바뀌었다"를
    구분할 수 없다.**

    원장을 양방향 시간 장부로 바꾸는 것은 큰 공사다. 그 대신 봉투가 자기가 읽은
    것을 적어 두면 같은 구분이 선다 — 지금 원장과 대조하면 어느 쪽이 움직였는지
    가 바로 나온다."""
    return {"source": source, "key": key, "value": value, "asof": asof}


def _walk_keys(obj, path=()):
    """봉투 전체를 훑으며 (경로, 키) 를 낸다."""
    if isinstance(obj, dict):
        for k, v in obj.items():
            yield path, k
            yield from _walk_keys(v, path + (k,))
    elif isinstance(obj, list):
        for v in obj:
            yield from _walk_keys(v, path)


def prose(env: dict) -> str:
    """사람이 읽는 부분만 모은다.

    판정 어휘 검사는 여기에만 건다. 봉투에는 `source_grade` 처럼 '등급'이라는
    말이 정당하게 들어가는 자리가 있어서, 봉투 전체를 문자열로 훑으면 멀쩡한
    필드가 걸린다."""
    bits = [str(env.get("claim") or "")]
    bits += [str(x) for x in (env.get("limits") or [])]
    bits += [str(x) for x in (env.get("notes") or [])]
    m = env.get("method") or {}
    bits.append(str(m.get("claim") or ""))
    return "\n".join(bits)


def validate(env: dict) -> list[str]:
    """봉투가 성립하는가. 문제 목록을 낸다 — 비어 있으면 통과다.

    예외를 던지지 않는다. 문제를 **전부** 모아서 내는 것이 목적이다. 하나씩
    고치게 하면 두 번째 문제를 볼 때까지 세 번을 왕복한다."""
    p: list[str] = []
    if not isinstance(env, dict):
        return ["봉투가 dict 가 아닙니다"]

    # ── 읽은 것 (재생 가능성) ──
    rd = env.get("read")
    if rd is not None:
        if not isinstance(rd, list):
            p.append("read 는 관측의 리스트여야 합니다")
        else:
            for i, o in enumerate(rd):
                if not isinstance(o, dict):
                    p.append(f"read[{i}] 가 dict 가 아닙니다")
                    continue
                for k in ("source", "key", "asof"):
                    if not str(o.get(k) or "").strip():
                        p.append(f"read[{i}].{k} 가 비어 있습니다")
                if "value" not in o:
                    p.append(f"read[{i}].value 가 없습니다 (None 이어도 적습니다)")
    # 값을 냈으면 무엇을 읽고 냈는지 적어야 한다. 적지 않으면 나중에 그 값이
    # 왜 그랬는지 되짚을 수 없고, 리플레이는 말로만 남는다.
    if env.get("value") is not None and not rd:
        p.append("value 가 있으면 read 에 무엇을 읽었는지 적어야 합니다 "
                 "— 적지 않으면 나중에 재생할 수 없습니다")

    # ── 있어야 하는 것 ──
    for k in ("claim", "asof", "source_grade", "limits", "desk", "instance"):
        if k not in env:
            p.append(f"필수 항목이 없습니다: {k}")

    claim = env.get("claim")
    if "claim" in env and not (isinstance(claim, str) and claim.strip()):
        p.append("claim 이 비어 있습니다")

    # ── 값과 단위 ──
    # 값이 없는 것은 죄가 아니다(규칙 3). 다만 사유가 있어야 한다.
    if env.get("value") is None and not str(env.get("reason") or "").strip():
        p.append("value 가 없으면 reason 이 있어야 합니다 (0 으로 채우지 않습니다)")
    if env.get("value") is not None and not str(env.get("unit") or "").strip():
        p.append("value 가 있으면 unit 이 있어야 합니다")

    # ── 기준일과 경과일수 (규칙 3) ──
    asof = env.get("asof")
    if "asof" in env and not (isinstance(asof, str) and _DATE.match(asof)):
        p.append("asof 는 YYYY-MM-DD 여야 합니다")
    sd = env.get("stale_days")
    if sd is not None and not (isinstance(sd, int) and not isinstance(sd, bool) and sd >= 0):
        p.append("stale_days 는 0 이상의 정수여야 합니다")

    # ── 출처 등급 (규칙 4) ──
    g = env.get("source_grade")
    if "source_grade" in env and g not in GRADES:
        p.append(f"source_grade 는 {GRADES} 중 하나여야 합니다 (받은 값: {g!r})")
    srcs = env.get("sources")
    if g in ("1차", "참고") and not (isinstance(srcs, list) and srcs):
        p.append(f"source_grade={g!r} 이면 sources 가 비어 있을 수 없습니다")

    # ── 한계 (규칙 4) ──
    lim = env.get("limits")
    if "limits" in env and not (isinstance(lim, list) and lim and all(str(x).strip() for x in lim)):
        p.append("limits 는 비어 있지 않은 문자열의 리스트여야 합니다 "
                 "— 그 방법이 주장하지 않는 것을 적습니다")

    # ── 방법 ──
    m = env.get("method")
    if m is not None:
        if not isinstance(m, dict):
            p.append("method 는 dict 여야 합니다")
        else:
            if m.get("paper") and not str(m.get("paper_state") or "").strip():
                p.append("method.paper 가 있으면 paper_state 가 있어야 합니다")
            r = m.get("replication")
            if r is not None and not isinstance(r, dict):
                p.append("method.replication 은 dict 여야 합니다")

    # ── 누가 만들었는가 ──
    inst = env.get("instance")
    if "instance" in env and not (isinstance(inst, str) and _INSTANCE.match(inst)):
        p.append("instance 형식이 아닙니다 (예: q2-disposal-20260911-000660-a91f)")
    tier = env.get("tier")
    if tier is not None and tier not in TIERS:
        p.append(f"tier 는 {TIERS} 중 하나여야 합니다")

    # ── 금지 키 ──
    for path, k in _walk_keys(env):
        if k in BANNED_KEYS and (path + (k,)) != _VERDICT_OK_PATH:
            where = ".".join(path + (k,)) if path else k
            p.append(f"판단을 뜻하는 키가 있습니다: {where}")

    return p


def promote(env: dict, to: str) -> tuple[bool, str]:
    """등급을 올릴 수 있는가. (가능 여부, 사유) 를 낸다.

    막는 것이 목적인 함수다. 올려도 되는 경우가 드물다."""
    if to not in GRADES:
        return False, f"{to!r} 는 등급이 아닙니다"
    cur = env.get("source_grade")
    if cur == to:
        return True, "같은 등급입니다"
    if cur in NEVER_PROMOTED:
        return False, (f"{cur!r} 는 승격되지 않습니다. 데스크가 재료를 읽고 쓴 문장은 "
                       f"그 재료의 등급을 물려받지 않습니다 — 1차 자료를 직접 인용하는 "
                       f"새 주장을 쓰십시오.")
    if to == PRIMARY and not (env.get("sources") or []):
        return False, "1차 로 올리려면 sources 에 공식 출처가 있어야 합니다"
    return True, ""


def make(claim, *, desk, asof, source_grade, limits, value=None, unit=None,
         sources=None, method=None, reason=None, subject="", tier="T2",
         stale_days=None, salt="", read=None) -> dict:
    """봉투를 짓는다. 지어낸 값을 채워 넣지 않는다 — 빠진 것은 빠진 채로 둔다."""
    env = {
        "schema": SCHEMA,
        "claim": claim,
        "value": value,
        "unit": unit,
        "asof": asof,
        "stale_days": stale_days,
        "source_grade": source_grade,
        "sources": list(sources or []),
        "method": method,
        "read": list(read or []),
        "limits": list(limits or []),
        "reason": reason,
        "desk": desk,
        "tier": tier,
        "escalated_from": None,
        "reviewed_by": [],
        "instance": new_instance(desk, asof, subject or "na", salt),
    }
    return env


# ── 자체 검사 ─────────────────────────────────────────────────────────

def _sample() -> dict:
    return make(
        "처분 소요일수 12.4 영업일", value=12.4, unit="business_days",
        desk="q2-disposal", asof="2026-09-11", stale_days=2,
        source_grade="해석", sources=["KRX/일별매매정보"], subject="000660",
        method={"paper": "amihud2002", "paper_state": "unverified",
                "assumes": {"participation": 0.15}},
        read=[observation("KRX/일별매매정보", "000660.close", 88.0, "2026-09-11"),
              observation("KRX/일별매매정보", "000660.value", 1.0e8, "2026-09-11")],
        limits=["논문 표본은 미국 상장주 — 코스닥 외삽 근거가 아니다"],
    )


def selftest() -> int:
    passed, failed = 0, []

    def check(name, fn):
        nonlocal passed
        try:
            fn()
            passed += 1
        except Exception as e:                          # noqa: BLE001
            failed.append(f"{name}: {type(e).__name__}: {e}")

    def _assert(c, why=""):
        if not c:
            raise AssertionError(why or "거짓")

    check("성립하는 봉투는 통과한다", lambda: _assert(validate(_sample()) == []))

    def _missing():
        e = _sample(); del e["limits"]
        _assert(any("limits" in x for x in validate(e)))
    check("limits 없는 봉투는 반려된다", _missing)

    def _empty_limits():
        e = _sample(); e["limits"] = []
        _assert(validate(e))
    check("limits 가 비면 반려된다 (한계를 적지 않은 것)", _empty_limits)

    def _no_value_no_reason():
        e = _sample(); e["value"] = None; e["reason"] = None
        _assert(any("reason" in x for x in validate(e)))
        e["reason"] = "일봉이 12개뿐입니다"
        _assert(validate(e) == [])      # 사유가 있으면 값이 없어도 된다
    check("값이 없으면 사유를 요구한다 (0 으로 채우지 않는다)", _no_value_no_reason)

    def _zero_is_a_value():
        e = _sample(); e["value"] = 0.0
        _assert(validate(e) == [])      # 0 은 '없음'이 아니라 잰 값이다
    check("0 은 값으로 인정된다", _zero_is_a_value)

    def _bad_grade():
        e = _sample(); e["source_grade"] = "공식"
        _assert(any("source_grade" in x for x in validate(e)))
    check("없는 등급은 반려된다", _bad_grade)

    def _primary_needs_source():
        e = _sample(); e["source_grade"] = "1차"; e["sources"] = []
        _assert(any("sources" in x for x in validate(e)))
    check("1차 인데 출처가 없으면 반려된다", _primary_needs_source)

    def _never_promote():
        e = _sample()
        ok, why = promote(e, "1차")
        _assert(not ok and "승격" in why)
        ok, _ = promote(e, "참고")
        _assert(not ok)                 # 해석은 어느 쪽으로도 안 올라간다
    check("해석은 어떤 등급으로도 승격되지 않는다", _never_promote)

    def _promote_ok():
        e = _sample(); e["source_grade"] = "참고"; e["sources"] = ["KRX/일별매매정보"]
        ok, _ = promote(e, "1차")
        _assert(ok)
    check("참고는 출처가 있으면 1차로 올라간다", _promote_ok)

    def _banned_key():
        e = _sample(); e["target_price"] = 12000
        _assert(any("target_price" in x for x in validate(e)))
    check("판단을 뜻하는 키는 반려된다", _banned_key)

    def _banned_key_nested():
        e = _sample(); e["method"] = dict(e["method"]); e["method"]["signal"] = "up"
        _assert(any("signal" in x for x in validate(e)))
    check("중첩된 판단 키도 잡힌다", _banned_key_nested)

    def _replication_verdict_allowed():
        e = _sample()
        e["method"] = dict(e["method"])
        e["method"]["replication"] = {"verdict": "재현됨", "t": 3.4}
        _assert(validate(e) == [])      # 논문에 대한 판정은 종목 판단이 아니다
    check("재현 판정(verdict)은 그 자리에서만 허용된다", _replication_verdict_allowed)

    def _prose_only():
        e = _sample()
        _assert("해석" not in prose(e))  # 등급 필드는 산문에 섞이지 않는다
        _assert("소요일수" in prose(e))
    check("판정 어휘 검사는 산문에만 걸린다", _prose_only)

    def _instance_unique():
        a = new_instance("q2-disposal", "2026-09-11", "000660")
        b = new_instance("q2-disposal", "2026-09-11", "000660", salt="2회차")
        c = new_instance("q2-disposal", "2026-09-11", "000660")
        _assert(a == c)                 # 같은 실행이면 같다
        _assert(a != b)                 # 다른 실행이면 다르다
        _assert(_INSTANCE.match(a))
    check("인스턴스 ID 는 결정적이고 실행마다 다르다", _instance_unique)

    def _read_required_with_value():
        """값을 냈으면 무엇을 읽고 냈는지 적어야 한다."""
        e = _sample(); e["read"] = []
        _assert(any("read" in x for x in validate(e)), validate(e))
        # 값이 없으면 읽은 것이 없어도 된다 — 사유만 있으면 성립한다.
        e2 = _sample(); e2["read"] = []; e2["value"] = None
        e2["reason"] = "일봉이 12개뿐입니다"
        _assert(validate(e2) == [], validate(e2))
    check("값을 냈으면 읽은 것을 적어야 한다 (재생 가능성)", _read_required_with_value)

    def _read_shape():
        e = _sample()
        e["read"] = [{"source": "KRX", "key": "k"}]       # asof · value 없음
        probs = validate(e)
        _assert(any("asof" in x for x in probs), probs)
        _assert(any("value" in x for x in probs), probs)
    check("관측은 출처·키·기준일·값을 모두 적는다", _read_shape)

    def _read_none_value_ok():
        """못 읽은 것도 적는다 — 0 으로 채우지 않고 None 으로 적는다."""
        e = _sample()
        e["read"] = [observation("DART/재무", "000660.2026Q2.rev", None, "2026Q2")]
        _assert(validate(e) == [], validate(e))
    check("못 읽은 값도 None 으로 적는다", _read_none_value_ok)

    def _asof_shape():
        e = _sample(); e["asof"] = "2026/09/11"
        _assert(any("asof" in x for x in validate(e)))
    check("기준일 형식을 검사한다", _asof_shape)

    def _paper_needs_state():
        e = _sample(); e["method"] = {"paper": "amihud2002"}
        _assert(any("paper_state" in x for x in validate(e)))
    check("논문을 인용하면 그 상태를 함께 낸다", _paper_needs_state)

    for f in failed:
        print("  X  " + f, file=sys.stderr)
    print(f"envelope   {passed} passed, {len(failed)} failed")
    return 1 if failed else 0


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="봉투 스키마 · 검증기")
    ap.add_argument("--selftest", action="store_true")
    ap.add_argument("--sample", action="store_true", help="예시 봉투를 낸다")
    a = ap.parse_args()
    if a.sample:
        print(json.dumps(_sample(), ensure_ascii=False, indent=2))
        sys.exit(0)
    sys.exit(selftest())
