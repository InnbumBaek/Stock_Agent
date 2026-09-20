"""작업지시서의 생애 — 발급과 회수. 소집과 발행 사이의 빈칸이다.

파이프라인은 이렇게 생겼다.

    convene  ──→  작업지시서  ──→  [데스크가 돈다]  ──→  봉투  ──→  publish

그런데 가운데가 비어 있었다. `convene` 은 지시서를 **stdout 으로만** 냈고
디스크에 남기지 않았다. `publish` 는 봉투 폴더에 있는 것을 **전부** 받았다.
둘을 짝지어 보는 코드가 없었다.

그래서 셋이 구분되지 않았다.

  **미이행**  소집했는데 봉투가 안 왔다. 그 절이 조용히 빈다. 빈칸은 아무도
              묻지 않는다 — 리포트에서 '조용한 날'과 똑같이 생겼다.
  **무단**    시킨 적 없는 봉투가 왔다. 게이트만 통과하면 발행된다. 출처가
              없는 주장이 근거 있는 숫자 옆에 나란히 선다.
  **중복**    한 지시서에 봉투가 둘 왔다. 같은 것을 두 번 재서 값이 다르면,
              회의는 그중 하나만 본다.

`publish` 는 이 대조를 싣고 나간다. **반려된 절이 빈칸이 아니듯, 안 온 절도
빈칸이 아니다** — '미이행' 으로 남는다.

읽기만 한다. 원장에 쓰지 않는다 (규칙 2).

    python agents/dispatch.py --selftest
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

SCHEMA = "ki.dispatch/1"

ROOT = Path(__file__).resolve().parent
ORDERS = ROOT / "orders"            # .gitignore — 종목 코드·공시 제목이 들어간다
ENVELOPES = ROOT / "envelopes"

# 네 가지 상태. 이름을 코드 밖에서도 쓰므로 한 곳에 둔다.
DONE = "이행"
MISSING = "미이행"
UNASKED = "무단"
DUPLICATE = "중복"


def day_dir(at: str, root: Path = None) -> Path:
    """그날의 지시서 폴더. 날짜로 나누는 이유는 회수 대조가 하루 단위이기
    때문이다 — 어제 것과 섞이면 어제 안 온 봉투가 오늘 미이행으로 뜬다."""
    return (root or ORDERS) / str(at)


def issue(orders: list, at: str, root: Path = None) -> dict:
    """지시서를 디스크에 쓴다.

    stdout 으로만 내면 누가 무엇을 시켰는지 남지 않는다. 그러면 몇 시간 뒤
    봉투가 왔을 때 짝지을 상대가 없고, 석 달 뒤 되짚을 때도 없다.

    **하루 폴더는 덧붙이기다. 지우지 않는다.** 두 가지 때문이다.

    하나, 승격이 낸 재시도 지시서가 같은 폴더에 들어온다. 다시 소집할 때마다
    폴더를 비우면 그 재시도가 사라지고, 그 봉투는 다음 발행에서 '무단' 이
    된다.

    둘, 한 번 시킨 것은 시킨 것이다. 아침에 부른 데스크가 안 왔는데 낮에 다시
    소집하면서 그 기록을 지우면, **안 왔다는 사실 자체가 없어진다.** 그것이
    바로 이 모듈이 막으려는 빈칸이다. 낡은 지시서는 계속 '미이행' 으로 뜨는
    것이 맞다."""
    d = day_dir(at, root)
    d.mkdir(parents=True, exist_ok=True)
    written = []
    for o in orders:
        inst = o.get("instance")
        if not inst:
            continue                        # instance 없는 지시서는 짝지을 수 없다
        f = d / f"{inst}.json"
        f.write_text(json.dumps(o, ensure_ascii=False, indent=2),
                     encoding="utf-8")
        written.append(inst)
    return {"schema": SCHEMA, "at": at, "dir": str(d),
            "n": len(written), "instances": sorted(written),
            "skipped": len(orders) - len(written)}


def convened(at: str, root: Path = None) -> bool:
    """그날 **소집을 하기는 했는가.**

    '소집이 0건이었다'와 '소집한 적이 없다'는 다르다. 앞의 것은 조용한 날이고,
    그날 봉투가 하나라도 있으면 그것은 전부 무단이다. 뒤의 것은 대조할 상대가
    없는 상태라, 봉투 폴더에 있는 것을 전부 받는 옛 동작이 맞다.

    둘을 구분하지 않으면 **소집이 없던 날 떠돌던 봉투가 그대로 발행된다** —
    이 모듈이 막으려던 바로 그 구멍이 조용한 날에만 다시 열린다."""
    return day_dir(at, root).is_dir()


def load_orders(at: str, root: Path = None) -> list:
    """그날 발급한 지시서. 없으면 빈 목록이다 — 그 자체가 '소집이 없었다'다."""
    d = day_dir(at, root)
    if not d.is_dir():
        return []
    out = []
    for f in sorted(d.glob("*.json")):
        try:
            out.append(json.loads(f.read_text(encoding="utf-8")))
        except ValueError:                                # noqa: PERF203
            # 읽지 못한 지시서를 조용히 빼면 그 데스크가 소집된 적이 없는
            # 것이 된다. 이름만이라도 남겨 미이행으로 세게 한다.
            out.append({"instance": f.stem, "desk": None,
                        "broken": f"지시서를 읽지 못했습니다: {f.name}"})
    return out


def reconcile(orders: list, envelopes: list) -> dict:
    """시킨 것과 돌아온 것을 `instance` 로 짝짓는다.

    짝이 되는 근거는 지시서가 준 `instance` 를 봉투가 그대로 적었다는 것이다
    (`envelope.make(instance=...)`). 봉투가 제 것을 지어내면 전부 미이행이자
    전부 무단이 되므로, 그 경우가 이 대조의 가장 흔한 오작동이다."""
    by_order = {o.get("instance"): o for o in orders if o.get("instance")}
    got: dict = {}
    orphan = []
    for e in envelopes:
        if not isinstance(e, dict):
            continue
        inst = e.get("instance")
        if inst in by_order:
            got.setdefault(inst, []).append(e)
        else:
            orphan.append(e)

    done, missing, dup = [], [], []
    for inst, o in by_order.items():
        envs = got.get(inst, [])
        row = {"instance": inst, "desk": o.get("desk"), "tier": o.get("tier"),
               "trigger": (o.get("trigger") or {}).get("kind"),
               "subject": (o.get("trigger") or {}).get("subject")}
        if not envs:
            missing.append({**row, "why": "소집했으나 봉투가 오지 않았습니다"})
        elif len(envs) == 1:
            done.append(row)
        else:
            dup.append({**row, "n": len(envs),
                        "why": f"한 지시서에 봉투가 {len(envs)}개 왔습니다"})

    return {
        "schema": SCHEMA,
        "n_orders": len(by_order), "n_envelopes": len([
            e for e in envelopes if isinstance(e, dict)]),
        DONE: done,
        MISSING: missing,
        UNASKED: [{"instance": e.get("instance"), "desk": e.get("desk"),
                   "claim": e.get("claim"),
                   "why": "시킨 적 없는 봉투입니다 — 어느 소집에서 나왔는지 "
                          "알 수 없습니다"} for e in orphan],
        DUPLICATE: dup,
        # 대조가 성립했는가. 지시서도 봉투도 없으면 '조용한 날'이지 사고가
        # 아니다. 지시서는 있는데 하나도 안 맞으면 그것은 사고다.
        "ok": not missing and not orphan and not dup,
    }


def summary(rec: dict) -> str:
    """한 줄. 로그와 배치 화면에 그대로 나간다."""
    bits = [f"이행 {len(rec[DONE])}"]
    for k, label in ((MISSING, "미이행"), (UNASKED, "무단"), (DUPLICATE, "중복")):
        if rec[k]:
            bits.append(f"{label} {len(rec[k])}")
    return " · ".join(bits)


def marks(rec: dict) -> list:
    """발행물에 붙는 표시. 중복은 값을 버리지 않는 대신 표시로 남긴다.

    **무단을 걸러 주는 함수는 여기 없다.** 한 번 있었고, 그것이 결함이었다 —
    `publish` 가 게이트 **앞에서** 무단을 빼는 바람에 게이트 ⑥(자격증명
    유출)이 그 봉투를 보지 못했고, 키가 든 무단 봉투 하나가 발행을 멈추지
    못했다.

    발행하지 않는 것과 검사하지 않는 것은 전혀 다른 이야기다. 유출은 되돌릴
    수 없어서, 무단이든 아니든 게이트는 전부 통과시킨 뒤에 뺀다. 거르는 쪽은
    `reconcile` 이 낸 `무단` 의 번호를 보고 `publish` 가 직접 한다."""
    out = []
    for r in rec[DUPLICATE]:
        out.append(f"중복 소집 — {r['desk']} 가 같은 지시서에 봉투를 "
                   f"{r['n']}개 냈습니다 ({r['instance']})")
    return out


# ── 자체 검사 ─────────────────────────────────────────────────────────

def _order(inst, desk="q2-disposal", kind="price.move", subject="000660"):
    return {"instance": inst, "desk": desk, "tier": "T2",
            "budget": {"tool_calls": 6, "tokens": 12000},
            "trigger": {"kind": kind, "subject": subject, "why": "하락"},
            "inputs": {"code": subject}, "tools": ["mcp__ki-ledger__*"],
            "must": ["봉투 하나를 낸다"]}


def _env(inst, desk="q2-disposal", claim="처분 소요 12영업일"):
    return {"schema": "ki.envelope/2", "instance": inst, "desk": desk,
            "claim": claim, "value": 12.4, "unit": "business_days",
            "asof": "2026-09-18", "source_grade": "해석",
            "sources": ["KRX/일별매매정보"], "limits": ["l"], "read": [],
            "attempt": 1}


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

    def _all_four_states():
        orders = [_order("A"), _order("B", desk="q4-timing"),
                  _order("C", desk="risk-officer")]
        envs = [_env("A"),                       # 이행
                _env("C"), _env("C"),            # 중복
                _env("Z", desk="q1-progress")]   # 무단  (B 는 미이행)
        r = reconcile(orders, envs)
        _assert([x["instance"] for x in r[DONE]] == ["A"], r[DONE])
        _assert([x["instance"] for x in r[MISSING]] == ["B"], r[MISSING])
        _assert([x["instance"] for x in r[UNASKED]] == ["Z"], r[UNASKED])
        _assert([x["instance"] for x in r[DUPLICATE]] == ["C"], r[DUPLICATE])
        _assert(r[DUPLICATE][0]["n"] == 2)
        _assert(r["ok"] is False)
    check("이행·미이행·무단·중복을 가른다", _all_four_states)

    def _quiet_day_is_not_an_incident():
        """지시서도 봉투도 없으면 조용한 날이다. 사고가 아니다."""
        r = reconcile([], [])
        _assert(r["ok"] is True, r)
        _assert(summary(r) == "이행 0", summary(r))
    check("조용한 날은 사고가 아니다", _quiet_day_is_not_an_incident)

    def _everything_missing_is_an_incident():
        """봉투가 제 instance 를 지어내면 전부 미이행이자 전부 무단이 된다.
        이 대조의 가장 흔한 오작동이라 눈에 보여야 한다."""
        r = reconcile([_order("A"), _order("B")],
                      [_env("지어낸것1"), _env("지어낸것2")])
        _assert(len(r[MISSING]) == 2 and len(r[UNASKED]) == 2, r)
        _assert(r["ok"] is False)
        _assert("미이행 2" in summary(r) and "무단 2" in summary(r), summary(r))
    check("봉투가 제 번호를 지어내면 전부 어긋난다",
          _everything_missing_is_an_incident)

    def _duplicate_is_marked_not_dropped():
        """중복은 빼지 않는다 — 빼면 그 절이 통째로 비고, 빈칸은 아무도 묻지
        않는다. 표시를 달아 회의가 보게 한다. 무단을 빼는 것은 `publish` 의
        몫이다 — 게이트를 전부 통과시킨 **뒤에** 뺀다."""
        orders = [_order("A"), _order("C", desk="risk-officer")]
        envs = [_env("A"), _env("C"), _env("C"), _env("Z")]
        r = reconcile(orders, envs)
        m = marks(r)
        _assert(len(m) == 1 and "중복" in m[0] and "C" in m[0], m)
        _assert([x["instance"] for x in r[UNASKED]] == ["Z"], r[UNASKED])
    check("중복은 표시만 단다", _duplicate_is_marked_not_dropped)

    def _no_pre_gate_filter_survives():
        """게이트 **앞에서** 무단을 거르는 함수를 다시 만들지 않는다.

        한 번 있었고 그것이 결함이었다 — 게이트 ⑥(자격증명 유출)이 그 봉투를
        보지 못해, 키가 든 무단 봉투 하나가 발행을 멈추지 못했다."""
        import re as _re
        # 줄 첫머리의 **정의**만 본다. 낱말로 찾으면 이 검사 자신의 설명에
        # 걸린다 — 앞서 같은 실수를 한 번 했다.
        src = Path(__file__).read_text(encoding="utf-8")
        _assert(_re.search(r"^def partition\(", src, _re.M) is None,
                "게이트 앞에서 거르는 함수가 다시 생겼습니다")
    check("게이트 앞에서 거르는 함수를 두지 않는다",
          _no_pre_gate_filter_survives)

    def _missing_names_the_desk():
        """'미이행' 이 이름을 달고 나가야 회의에서 물을 수 있다. 빈칸은
        아무도 묻지 않는다."""
        r = reconcile([_order("B", desk="q4-timing", kind="macro.update",
                              subject="2026-09-18")], [])
        row = r[MISSING][0]
        _assert(row["desk"] == "q4-timing", row)
        _assert(row["trigger"] == "macro.update" and row["subject"], row)
        _assert(row["why"], row)
    check("미이행은 어느 데스크인지 밝힌다", _missing_names_the_desk)

    def _issue_and_load_round_trip():
        import tempfile
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            orders = [_order("A"), _order("B", desk="q4-timing")]
            w = issue(orders, "2026-09-18", root)
            _assert(w["n"] == 2 and w["skipped"] == 0, w)
            back = load_orders("2026-09-18", root)
            _assert(sorted(o["instance"] for o in back) == ["A", "B"], back)
            _assert(back[0]["trigger"]["kind"] == "price.move", back[0])
            # 다른 날은 안 섞인다 — 어제 안 온 봉투가 오늘 미이행으로 뜨면 안 된다
            _assert(load_orders("2026-09-17", root) == [])
    check("지시서를 쓰고 그대로 되읽는다", _issue_and_load_round_trip)

    def _issue_is_idempotent():
        """같은 날 다시 소집해도 같은 파일이다. 지시서는 결정적이다."""
        import tempfile
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            issue([_order("A")], "2026-09-18", root)
            issue([_order("A")], "2026-09-18", root)
            _assert(len(load_orders("2026-09-18", root)) == 1)
    check("두 번 발급해도 하나다", _issue_is_idempotent)

    def _day_folder_is_append_only():
        """다시 소집해도 앞서 시킨 것을 지우지 않는다.

        지우면 승격이 낸 재시도가 사라지고, 아침에 부른 데스크가 안 왔다는
        사실도 함께 없어진다 — 그것이 이 모듈이 막으려는 빈칸이다."""
        import tempfile
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            issue([_order("아침")], "2026-09-18", root)
            issue([_order("재시도")], "2026-09-18", root)   # 승격이 낸 것
            issue([_order("낮에다시")], "2026-09-18", root)
            back = sorted(o["instance"] for o in load_orders("2026-09-18", root))
            _assert(back == ["낮에다시", "아침", "재시도"], back)
            # 셋 다 봉투가 없으므로 셋 다 미이행이다 — 그게 맞다
            _assert(len(reconcile(load_orders("2026-09-18", root), [])[MISSING])
                    == 3)
    check("하루 폴더는 덧붙이기다 (지우지 않는다)", _day_folder_is_append_only)

    def _broken_order_still_counts():
        """읽지 못한 지시서를 조용히 빼면 그 데스크가 소집된 적이 없는 것이
        된다. 이름만이라도 남겨 미이행으로 센다."""
        import tempfile
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            dd = day_dir("2026-09-18", root)
            dd.mkdir(parents=True)
            (dd / "A.json").write_text("{깨진 json", encoding="utf-8")
            back = load_orders("2026-09-18", root)
            _assert(len(back) == 1 and back[0]["instance"] == "A", back)
            _assert(back[0]["broken"], back[0])
            r = reconcile(back, [])
            _assert(len(r[MISSING]) == 1, r)
    check("깨진 지시서도 미이행으로 센다", _broken_order_still_counts)

    def _order_without_instance_is_not_silently_dropped():
        import tempfile
        with tempfile.TemporaryDirectory() as d:
            w = issue([{"desk": "q2-disposal"}], "2026-09-18", Path(d))
            _assert(w["n"] == 0 and w["skipped"] == 1, w)
    check("번호 없는 지시서는 세어서 알린다",
          _order_without_instance_is_not_silently_dropped)

    def _reads_nothing_but_disk():
        """원장을 건드리지 않는다 (규칙 2). 이 모듈은 디스크만 본다.

        문구가 아니라 **코드**를 본다 — 이 검사 자신이 원장 이야기를 하므로,
        낱말로 찾으면 자기 설명에 걸린다."""
        import re as _re
        src = Path(__file__).read_text(encoding="utf-8")
        hit = _re.search(r"^\s*(?:import sqlite3|from sqlite3)|sqlite3\.connect",
                         src, _re.M)
        _assert(hit is None, f"원장을 여는 코드가 있습니다: {hit and hit.group()}")
    check("원장을 건드리지 않는다", _reads_nothing_but_disk)

    for f in failed:
        print("  X  " + f, file=sys.stderr)
    print(f"dispatch   {passed} passed, {len(failed)} failed")
    return 1 if failed else 0


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="작업지시서 발급·회수 대조")
    ap.add_argument("--selftest", action="store_true")
    ap.add_argument("--at", help="기준일 (기본: 오늘)")
    ap.add_argument("--orders", default=str(ORDERS))
    ap.add_argument("--envelopes", default=str(ENVELOPES))
    ap.add_argument("--indent", type=int, default=2)
    a = ap.parse_args()
    if a.selftest or not a.at:
        sys.exit(selftest())
    import run_day as RD                                  # noqa: E402
    at = a.at
    orders = load_orders(at, Path(a.orders))
    envs = RD.load_envelopes(Path(a.envelopes)) if Path(a.envelopes).is_dir() else []
    rec = reconcile(orders, envs)
    rec["summary"] = summary(rec)
    print(json.dumps(rec, ensure_ascii=False, indent=a.indent))
    sys.exit(0 if rec["ok"] else 1)
