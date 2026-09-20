"""누구를 보는가 — 상장 포트폴리오사.

이 도구는 **시장 감시기가 아니다.** 우리가 들고 있는 상장 포트폴리오사의
회수 판단을 돕는 물건이고, 코스닥 전체는 그 판단의 배경일 뿐이다
(리포트 §7 '시장 배경'). 측정층은 그 구분을 지킨다 — `_watchlist()` 가
주인공을 정하고, `quant_frames` 가 만드는 시장 전체 행렬은 배경으로만 쓴다.

**판단층에는 그 구분이 없었다.** 트리거가 원장의 `price_daily` 를 통째로
훑어서, 하루 ±8% 움직인 종목마다 데스크를 불렀다. 재 봤다 —

    코스닥 1,700종목 · 일간 변동성 3.5%
    ±8% 이상 움직인 종목        37개
    그중 우리 포트폴리오사      2개
    낭비되는 인스턴스           70개 (종목당 q2-disposal + risk-officer)

95%가 남의 회사다. 그리고 낭비로 끝나지 않는다 — 데스크가 우리가 갖지도
않은 회사에 대해 봉투를 쓰고, 그 봉투가 게이트를 통과해 **회수 판단
리포트에 섞인다.**

목록을 못 읽으면 **코드를 내지 않고 사유를 낸다.** 전체로 넘기면 위의 일이
그대로 벌어지고, 빈 목록으로 넘기면 '조용한 날'이 되어 아무도 묻지 않는다.
둘 다 조용히 틀리는 쪽이다.

    python agents/scope.py --selftest
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

MONITOR = Path(__file__).resolve().parent.parent / "stock-monitor"

SCHEMA = "ki.scope/1"


def _read_watchlist():
    """측정층의 `_watchlist()` 를 그대로 쓴다. `(결과, 사유)` 를 낸다.

    여기서 CSV 를 다시 파싱하면 규칙이 두 곳으로 갈라진다 — 종목코드
    6자리 채우기, 주석 줄, 비상장 판정(코드가 비면 비상장)이 전부 거기
    있고, 갈라지면 어느 쪽이 맞는지 아무도 모르게 된다.

    **왜 못 읽었는지 구분한다.** 전부 "watchlist.csv 를 읽지 못했습니다" 로
    내면, 파일이 멀쩡한데 pandas 가 없거나 import 가 깨진 경우에도 멀쩡한
    파일을 탓하게 된다 — 고칠 곳을 엉뚱한 데서 찾는다."""
    # 경로를 앞에 꽂은 채로 두면 `agents/` 가 가려진다 — 같은 이름의 모듈이
    # 생기는 날 조용히 다른 파일이 잡힌다. 넣었으면 되돌린다.
    added = str(MONITOR) not in sys.path
    if added:
        sys.path.insert(0, str(MONITOR))
    try:
        import ki_monitor as _K                           # noqa: PLC0415
    except Exception as e:                                # noqa: BLE001
        return None, (f"측정층을 불러오지 못했습니다 ({type(e).__name__}). "
                      f"watchlist.csv 문제가 아닙니다 — stock-monitor/ 와 "
                      f"pandas 를 먼저 확인하십시오.")
    finally:
        if added:
            try:
                sys.path.remove(str(MONITOR))
            except ValueError:                            # noqa: PERF203
                pass
    try:
        return _K._watchlist(), None
    except Exception as e:                                # noqa: BLE001
        return None, f"watchlist.csv 를 읽다 실패했습니다 ({type(e).__name__})."


#: `portfolio(wl=MISSING)` 로 '못 읽음' 을 주입한다. 검사가 개발자 컴퓨터의
#: watchlist.csv 유무에 기대면, 그 컴퓨터에서는 not-ok 갈래가 아예 안 돈다.
MISSING = object()


def portfolio(wl=None) -> dict:
    """우리가 보는 상장 포트폴리오사.

    `{"ok": bool, "codes": [...], "n": int, "n_unlisted": int, "why": str|None}`

    `ok` 가 거짓이면 `codes` 는 비어 있고 `why` 가 이유를 말한다. 그때
    부르는 쪽은 **소집하지 않는다** — 전체를 훑지도, 조용히 넘어가지도
    않는다."""
    why_read = None
    if wl is MISSING:
        wl, why_read = None, "watchlist.csv 가 없습니다."
    elif wl is None:
        wl, why_read = _read_watchlist()
    if wl is None:
        return {"schema": SCHEMA, "ok": False, "codes": [], "n": 0,
                "n_unlisted": 0,
                "why": (why_read or "watchlist.csv 가 없습니다.")
                       + (" 상장 포트폴리오사를 모르면 누구를 볼지 정할 수 "
                          "없습니다 — 시장 전체를 훑지 않습니다. "
                          "RUN_ALL 이 이 파일을 찾아 옵니다.")}
    listed = wl.get("listed")
    codes = ([] if listed is None or listed.empty
             else sorted(str(c).strip().zfill(6) for c in listed["code"]
                         if str(c).strip()))
    n_un = 0 if wl.get("unlisted") is None else int(len(wl["unlisted"]))
    if not codes:
        return {"schema": SCHEMA, "ok": False, "codes": [], "n": 0,
                "n_unlisted": n_un,
                "why": ("watchlist.csv 에 상장 포트폴리오사가 없습니다 "
                        f"(비상장 {n_un}곳). 상장사는 code 칸에 종목코드 "
                        f"6자리를 적습니다.")}
    return {"schema": SCHEMA, "ok": True, "codes": codes, "n": len(codes),
            "n_unlisted": n_un, "why": None}


def as_set(p: dict) -> set:
    """필터에 바로 쓰는 집합. `ok` 가 거짓이면 비어 있다."""
    return set(p.get("codes") or ())


# ── 자체 검사 ─────────────────────────────────────────────────────────

class _DF(list):
    """pandas 없이 `_watchlist()` 의 모양만 흉내 낸다."""
    def __init__(self, rows):
        super().__init__(rows)
        self.empty = not rows

    def __getitem__(self, k):
        if k == "code":
            return [r["code"] for r in self]
        return list.__getitem__(self, k)


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

    def _wl(listed=(), unlisted=()):
        return {"listed": _DF([{"code": c} for c in listed]),
                "unlisted": _DF([{"code": ""} for _ in unlisted])}

    def _listed_only():
        p = portfolio(_wl(listed=("000660", "35720"), unlisted=("가", "나")))
        _assert(p["ok"] is True, p)
        _assert(p["codes"] == ["000660", "035720"], p["codes"])   # 6자리로 채운다
        _assert(p["n"] == 2 and p["n_unlisted"] == 2, p)
    check("상장사만 고르고 코드를 6자리로 채운다", _listed_only)

    def _missing_file_is_loud():
        """목록이 없으면 전체를 훑지도, 조용히 넘어가지도 않는다.

        `MISSING` 으로 주입한다 — 개발자 컴퓨터에 watchlist.csv 가 있으면
        이 갈래가 아예 안 돌기 때문이다."""
        p = portfolio(MISSING)
        _assert(p["ok"] is False, p)
        _assert(not p["codes"], p)
        _assert("시장 전체를 훑지 않습니다" in p["why"], p["why"])
    check("목록이 없으면 사유를 낸다 (전체를 훑지 않는다)", _missing_file_is_loud)

    def _import_failure_does_not_blame_the_file():
        """파일이 멀쩡한데 pandas 가 없으면, 멀쩡한 파일을 탓하면 안 된다 —
        고칠 곳을 엉뚱한 데서 찾게 된다."""
        import builtins
        real = builtins.__import__

        def boom(name, *a, **k):
            if name == "ki_monitor":
                raise ModuleNotFoundError("No module named 'pandas'")
            return real(name, *a, **k)

        sys.modules.pop("ki_monitor", None)
        builtins.__import__ = boom
        try:
            wl, why = _read_watchlist()
        finally:
            builtins.__import__ = real
            sys.modules.pop("ki_monitor", None)
        _assert(wl is None and why, (wl, why))
        _assert("watchlist.csv 문제가 아닙니다" in why, why)
    check("불러오기 실패를 파일 탓으로 돌리지 않는다",
          _import_failure_does_not_blame_the_file)

    def _sys_path_is_restored():
        """경로를 앞에 꽂은 채로 두면 `agents/` 가 가려진다."""
        before = list(sys.path)
        _read_watchlist()
        _assert(sys.path == before, [x for x in sys.path if x not in before])
    check("import 경로를 되돌린다", _sys_path_is_restored)

    def _unlisted_only_is_not_ok():
        """비상장만 있으면 상장 모니터링은 성립하지 않는다."""
        p = portfolio(_wl(listed=(), unlisted=("가", "나", "다")))
        _assert(p["ok"] is False, p)
        _assert(p["n_unlisted"] == 3, p)
        _assert("비상장 3곳" in p["why"], p["why"])
    check("비상장만 있으면 소집하지 않고 사유를 낸다", _unlisted_only_is_not_ok)

    def _as_set_is_empty_when_not_ok():
        _assert(as_set(portfolio(_wl())) == set())
        _assert(as_set(portfolio(_wl(listed=("000660",)))) == {"000660"})
    check("쓸 수 없는 범위는 빈 집합이다", _as_set_is_empty_when_not_ok)

    def _blank_codes_are_dropped():
        p = portfolio(_wl(listed=("000660", "  ", "")))
        _assert(p["codes"] == ["000660"], p["codes"])
    check("빈 코드는 버린다", _blank_codes_are_dropped)

    def _uses_the_measurement_layer_parser():
        """CSV 를 다시 파싱하지 않는다 — 규칙이 두 곳으로 갈라지면 안 된다.

        종목코드 6자리 채우기 · 주석 줄 · 비상장 판정(코드가 비면 비상장)이
        전부 측정층에 있다. 여기서 따로 읽으면 두 규칙이 갈라지고, 그때
        어느 쪽이 맞는지 아무도 모른다.

        **문구가 아니라 임포트를 본다.** 낱말로 찾으면 이 검사 자신의 설명에
        걸린다 — 같은 실수를 세 번 했다."""
        import ast as _ast
        src = Path(__file__).read_text(encoding="utf-8")
        mods = set()
        for node in _ast.walk(_ast.parse(src)):
            if isinstance(node, _ast.Import):
                mods |= {n.name.split(".")[0] for n in node.names}
            elif isinstance(node, _ast.ImportFrom) and node.module:
                mods.add(node.module.split(".")[0])
        _assert("csv" not in mods and "pandas" not in mods,
                f"watchlist 를 여기서 다시 파싱하고 있습니다: {mods & {'csv', 'pandas'}}")
        _assert("_watchlist" in src)
    check("목록 파싱은 측정층 것을 쓴다", _uses_the_measurement_layer_parser)

    for f in failed:
        print("  X  " + f, file=sys.stderr)
    print(f"scope      {passed} passed, {len(failed)} failed")
    return 1 if failed else 0


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="상장 포트폴리오사 범위")
    ap.add_argument("--selftest", action="store_true")
    ap.add_argument("--indent", type=int, default=2)
    a = ap.parse_args()
    if a.selftest:
        sys.exit(selftest())
    p = portfolio()
    # 종목코드는 대외비다 — 개수와 사유만 낸다.
    print(json.dumps({k: v for k, v in p.items() if k != "codes"},
                     ensure_ascii=False, indent=a.indent))
    sys.exit(0 if p["ok"] else 1)
