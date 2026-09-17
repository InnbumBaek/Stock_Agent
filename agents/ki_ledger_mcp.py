"""ki-ledger — 원장을 읽는 MCP 서버. 읽기 전용이다.

에이전트에게 "원장에 쓰지 마라"고 **부탁하지 않는다.** 쓰는 도구를 아예 주지
않는다. 프롬프트로 건 금지는 프롬프트가 길어지면 희미해지고, 모형이 바뀌면
같이 바뀐다. 도구 목록에 없는 동작은 그런 식으로 새지 않는다.

세 겹으로 막는다.

  1. 쓰기 도구가 없다. 목록에 `tools/list` 로 나오는 것이 전부다.
  2. 연결을 `mode=ro` 로 연다. SQLite 가 파일 수준에서 거절한다.
  3. 생 SQL 을 받지 않는다. 도구마다 정해진 인자만 받아 질의를 조립한다.

규칙 2 가 지키려는 것이 이것이다 — 추정·가정·가상 포지션이 원장에 한 번
섞이면 다음 측정이 오염되고, 그 오염은 되돌릴 수 없다.

값에는 **기준일과 경과일수**가 항상 붙는다 (규칙 3). 원장은 일별 종가라 며칠
묵을 수 있고, 며칠 묵었는지 모르는 값은 근거로 쓸 수 없다.

    python agents/ki_ledger_mcp.py --selftest
    python agents/ki_ledger_mcp.py            # stdio MCP 서버로 선다
"""
from __future__ import annotations

import argparse
import json
import re
import sqlite3
import sys
from datetime import date, datetime
from pathlib import Path

PROTOCOL = "2025-06-18"
NAME = "ki-ledger"
VERSION = "1.0.0"

ROOT = Path(__file__).resolve().parent.parent
MONITOR = ROOT / "stock-monitor"

# 원장에서 오는 값의 등급. 이 서버가 내는 것은 전부 1차다 — 공식 API 로 받아
# 원장에 적힌 것만 돌려주기 때문이다. 데스크가 이것을 읽고 쓴 문장은 '해석'이다.
GRADE = "1차"

_CODE = re.compile(r"^\d{6}$")
_DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
_MARKETS = ("KOSPI", "KOSDAQ", "KONEX")
MAX_ROWS = 2000


class Denied(Exception):
    """도구가 거절한 요청. 사유는 사람이 읽을 수 있어야 한다."""


def _scrub(text) -> str:
    """오류 문구에서 인증키를 지운다 (규칙 5).

    측정층의 scrub() 과 같은 일을 한다. 그것을 그대로 쓰지 않는 이유는 이
    서버가 ki_monitor 없이도 서야 하기 때문이다 — 있으면 그쪽을 쓴다."""
    out = str(text)
    try:
        sys.path.insert(0, str(MONITOR))
        import ki_monitor                                # noqa: PLC0415
        return ki_monitor.scrub(out)
    except Exception:                                    # noqa: BLE001
        pass
    out = re.sub(r"((?:auth|api|crtfc|app)[_-]?(?:key|secret)|serviceKey|token)"
                 r"(\s*=\s*)[^&\s'\")]+", r"\1\2<가림>", out, flags=re.I)
    return out


def io_open(p):
    return open(p, encoding="utf-8")


def _code(v) -> str:
    if not (isinstance(v, str) and _CODE.match(v)):
        raise Denied(f"종목코드는 숫자 6자리여야 합니다 (받은 값: {v!r})")
    return v


def _market(v) -> str:
    if v not in _MARKETS:
        raise Denied(f"시장은 {_MARKETS} 중 하나여야 합니다 (받은 값: {v!r})")
    return v


def _day(v, what="날짜"):
    if v is None:
        return None
    if not (isinstance(v, str) and _DATE.match(v)):
        raise Denied(f"{what} 는 YYYY-MM-DD 여야 합니다 (받은 값: {v!r})")
    return v


def _limit(v, default=250) -> int:
    n = default if v is None else v
    if not isinstance(n, int) or isinstance(n, bool) or n < 1:
        raise Denied(f"limit 은 1 이상의 정수여야 합니다 (받은 값: {v!r})")
    return min(n, MAX_ROWS)


def _bdays_between(a: str, b: str) -> int:
    """영업일 수. 공휴일은 모른다 — 그 사실을 숨기지 않고 이름에 남긴다."""
    d0, d1 = datetime.fromisoformat(a).date(), datetime.fromisoformat(b).date()
    if d1 <= d0:
        return 0
    n, cur = 0, d0
    while cur < d1:
        cur = cur.fromordinal(cur.toordinal() + 1)
        if cur.weekday() < 5:
            n += 1
    return n


def _envelope(rows, asof, *, source, note=None, reason=None,
              grade: str = GRADE, **extra) -> dict:
    """원장에서 나가는 모든 응답이 입는 봉투.

    기준일 없이 값만 돌려주지 않는다. 받는 쪽이 며칠 묵었는지 모르면, 묵은
    값과 오늘 값이 같은 무게로 회의에 올라간다."""
    today = date.today().isoformat()
    out = {
        "ok": rows is not None,
        "source_grade": grade,
        "sources": [source],
        "asof": asof,
        "stale_days": _bdays_between(asof, today) if asof else None,
        "stale_days_note": "주말만 제외한 값입니다 — 공휴일은 반영되지 않습니다",
        "as_of_query": today,
        "rows": rows if rows is not None else [],
        "n": len(rows) if rows is not None else 0,
    }
    if note:
        out["note"] = note
    if reason:
        out["reason"] = reason
    out.update(extra)
    return out


# ── 도구 여덟 ─────────────────────────────────────────────────────────
#
# 전부 읽기다. 여기 없는 동작은 이 서버로 할 수 없다.

def t_universe(con, market: str = "KOSDAQ", limit: int = None) -> dict:
    market, limit = _market(market), _limit(limit, 500)
    r = con.execute(
        "SELECT code, name, market, list_date FROM instruments "
        "WHERE market = ? ORDER BY code LIMIT ?", (market, limit)).fetchall()
    asof = con.execute("SELECT MAX(date) FROM price_daily WHERE market = ?",
                       (market,)).fetchone()[0]
    return _envelope([dict(x) for x in r], asof, source="KRX/상장종목",
                     market=market)


def t_price_series(con, code: str, start: str = None, end: str = None,
                   limit: int = None) -> dict:
    code, limit = _code(code), _limit(limit)
    start, end = _day(start, "start"), _day(end, "end")
    q = "SELECT date, open, high, low, close, volume, value FROM price_daily WHERE code = ?"
    p = [code]
    if start:
        q += " AND date >= ?"; p.append(start)
    if end:
        q += " AND date <= ?"; p.append(end)
    q += " ORDER BY date DESC LIMIT ?"; p.append(limit)
    r = [dict(x) for x in con.execute(q, p).fetchall()]
    r.reverse()
    if not r:
        return _envelope(None, None, source="KRX/일별매매정보",
                         reason=f"{code} 의 일봉이 원장에 없습니다. "
                                f"ingest --universe <시장> 을 먼저 실행하십시오.")
    return _envelope(r, r[-1]["date"], source="KRX/일별매매정보", code=code)


def t_facts(con, code: str) -> dict:
    """가장 최근에 잰 값 한 줄. 계산하지 않는다 — 원장에 적힌 것만 낸다."""
    code = _code(code)
    r = con.execute(
        "SELECT date, code, name, market, open, high, low, close, volume, value, "
        "mktcap, shares FROM price_daily WHERE code = ? ORDER BY date DESC LIMIT 1",
        (code,)).fetchone()
    if r is None:
        return _envelope(None, None, source="KRX/일별매매정보",
                         reason=f"{code} 이(가) 원장에 없습니다")
    row = dict(r)
    return _envelope([row], row["date"], source="KRX/일별매매정보", code=code,
                     note="종가 기준입니다. 장중 값이 아닙니다.")


def t_fundamentals(con, code: str, period: str = None, limit: int = None) -> dict:
    code, limit = _code(code), _limit(limit)
    q = "SELECT code, period, key, value, unit, source FROM fundamental WHERE code = ?"
    p = [code]
    if period:
        q += " AND period = ?"; p.append(period)
    q += " ORDER BY period DESC, key LIMIT ?"; p.append(limit)
    r = [dict(x) for x in con.execute(q, p).fetchall()]
    asof = r[0]["period"] if r else None
    return _envelope(r, None, source="DART/재무",
                     period_latest=asof, code=code,
                     note="기준일은 보고서 기간(period)입니다 — 일자가 아닙니다. "
                          "정정공시가 나면 같은 칸이 덮어써집니다.")


def t_disclosures(con, code: str, since: str = None, limit: int = None) -> dict:
    code, limit = _code(code), _limit(limit, 100)
    since = _day(since, "since")
    q = "SELECT rcept_no, code, rcept_dt, title, tags FROM disclosure WHERE code = ?"
    p = [code]
    if since:
        q += " AND rcept_dt >= ?"; p.append(since)
    q += " ORDER BY rcept_dt DESC LIMIT ?"; p.append(limit)
    r = [dict(x) for x in con.execute(q, p).fetchall()]
    return _envelope(r, r[0]["rcept_dt"] if r else None, source="DART/공시목록",
                     code=code)


def t_index_series(con, index_name: str = "KOSDAQ", limit: int = None) -> dict:
    index_name, limit = _market(index_name), _limit(limit)
    r = [dict(x) for x in con.execute(
        "SELECT date, open, high, low, close FROM index_daily "
        "WHERE index_name = ? ORDER BY date DESC LIMIT ?",
        (index_name, limit)).fetchall()]
    r.reverse()
    if not r:
        return _envelope(None, None, source="KRX/지수",
                         reason=f"{index_name} 지수가 원장에 없습니다")
    return _envelope(r, r[-1]["date"], source="KRX/지수", index_name=index_name)


def t_macro(con, key: str = None, limit: int = None) -> dict:
    limit = _limit(limit)
    if key is not None and not (isinstance(key, str) and key.strip()):
        raise Denied("key 는 비어 있지 않은 문자열이어야 합니다")
    q = "SELECT date, key, value, unit, source FROM macro_daily"
    p = []
    if key:
        q += " WHERE key = ?"; p.append(key)
    q += " ORDER BY date DESC LIMIT ?"; p.append(limit)
    r = [dict(x) for x in con.execute(q, p).fetchall()]
    r.reverse()
    return _envelope(r, r[-1]["date"] if r else None,
                     source="한국은행 ECOS · FRED")


def t_staleness(con, market: str = "KOSDAQ") -> dict:
    """원장이 며칠 뒤처졌는가. 이것을 먼저 묻지 않으면 묵은 값을 새 값으로 읽는다."""
    market = _market(market)
    row = con.execute(
        "SELECT MAX(date) AS last, COUNT(DISTINCT code) AS codes "
        "FROM price_daily WHERE market = ?", (market,)).fetchone()
    last = row["last"] if row else None
    if not last:
        return _envelope(None, None, source="KRX/일별매매정보",
                         reason=f"{market} 일봉이 원장에 없습니다")
    return _envelope([{"market": market, "last_date": last, "codes": row["codes"]}],
                     last, source="KRX/일별매매정보",
                     note="catchup 으로 밀린 영업일을 채울 수 있습니다")


def t_papers(con, key: str = None, state: str = None) -> dict:
    """논문 장부 — 무엇을 인용해도 되는가.

    이것이 없으면 데스크가 봉투의 `method.paper_state` 를 채울 방법이 없다.
    추측해서 적으면 게이트 ③ 이 장부와 어긋난다고 반려한다 — **데스크가 볼 수
    없는 것을 근거로 반려하는 관문은 관문이 아니라 함정이다.**

    장부는 원장(`ki.sqlite`)이 아니라 `.papers.json` 이므로 `con` 을 쓰지
    않는다. 여기서도 읽기만 한다. 등급은 `1차` 가 아니라 `방법론` 이다 —
    논문은 계산 규칙의 출처이지 시세 출처가 아니다."""
    if key is not None and not (isinstance(key, str) and key.strip()):
        raise Denied("key 는 비어 있지 않은 문자열이어야 합니다")
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    import papers as P                                    # noqa: PLC0415
    if not P.LEDGER.exists():
        return _envelope(None, None, source="논문 장부(.papers.json)",
                         grade="방법론", reason="논문 장부가 없습니다")
    doc = P.age_states(P.migrate(P.load()))
    if state is not None and state not in P.STATES:
        raise Denied(f"state 는 {P.STATES} 중 하나여야 합니다 (받은 값: {state!r})")
    rows = []
    for k, v in (doc.get("papers") or {}).items():
        if (key and k != key) or (state and v.get("state") != state):
            continue
        ok, mark = P.citable(doc, k)
        rows.append({
            "paper": k, "state": v.get("state"), "question": v.get("question"),
            "citable": ok, "mark": mark,
            "state_reason": v.get("state_reason"),
            "recheck_due": v.get("recheck_due"),
            "citation": P.cite(doc, k),
            "limits": list(v.get("limits") or []),
            # 재현 기록은 쌓인다. 가장 최근 것만 낸다 — 전부 실으면 응답이
            # 커지고, 그때 기준이 필요하면 장부를 직접 봐야 한다.
            "last_replication": (v.get("replication") or [None])[-1],
        })
    rows.sort(key=lambda r: r["paper"])
    if key and not rows:
        return _envelope(None, doc.get("migrated_at"),
                         source="논문 장부(.papers.json)", grade="방법론",
                         reason=f"장부에 없는 논문입니다: {key}. 지어내지 마십시오.")
    return _envelope(rows, doc.get("migrated_at"),
                     source="논문 장부(.papers.json)", grade="방법론",
                     schema_version=doc.get("schema"),
                     note="인용이 막히는 것은 retired 뿐입니다. 나머지는 "
                          "mark 를 값에 붙여 내보내십시오.")


CALENDAR = MONITOR / ".calendar.json"


def t_calendar(con, since: str = None, until: str = None,
               limit: int = None) -> dict:
    """다가오는 일정 — 금통위·지수 정기변경·보호예수 해제 같은 것.

    **일정마다 등급이 다르다.** 기관이 공표한 확정 일정과, 제도에서 계산한 것과,
    상장일에서 관행으로 추정한 것을 같은 줄에 늘어놓으면 회의에서 전부 확정
    일정처럼 읽힌다. 등급을 항목마다 붙여서 낸다 (공표 · 규칙 · 추정).

    원장이 아니라 `.calendar.json` 을 읽는다. 여기서도 읽기만 한다."""
    since, until = _day(since, "since"), _day(until, "until")
    limit = _limit(limit, 100)
    if not CALENDAR.exists():
        return _envelope(None, None, source="일정표(.calendar.json)",
                         grade="참고",
                         reason="일정표가 없습니다. docs/fetch_calendar.py 로 "
                                "갱신하십시오.")
    try:
        with io_open(CALENDAR) as f:
            doc = json.load(f) or {}
    except (OSError, ValueError) as e:
        return _envelope(None, None, source="일정표(.calendar.json)",
                         grade="참고", reason=f"일정표를 읽지 못했습니다: {_scrub(e)}")
    today = date.today().isoformat()
    lo = since or today
    rows = []
    for name, src in (doc.get("sources") or {}).items():
        if not isinstance(src, dict):
            continue
        for ev in src.get("events") or []:
            if not (isinstance(ev, (list, tuple)) and len(ev) >= 2):
                continue
            when, what = str(ev[0]), str(ev[1])
            if when < lo or (until and when > until):
                continue
            rows.append({
                "date": when, "event": what, "source": name,
                "org": src.get("기관"), "grade": src.get("등급"),
                "checked": src.get("확인"),
            })
    rows.sort(key=lambda r: (r["date"], r["source"]))
    rows = rows[:limit]
    return _envelope(rows, doc.get("verified"), source="일정표(.calendar.json)",
                     grade="참고", grades=doc.get("grades"),
                     note="일정마다 등급이 다릅니다 — 공표·규칙·추정을 섞지 "
                          "마십시오. '추정' 은 증권신고서로 확인해야 하는 값입니다.")


TOOLS = {
    "universe": (t_universe, "한 시장의 상장종목 목록",
                 {"market": ("string", "KOSPI · KOSDAQ · KONEX"),
                  "limit": ("integer", "최대 행 수 (기본 500)")}, []),
    "facts": (t_facts, "한 종목의 가장 최근 측정값 한 줄 (종가 기준)",
              {"code": ("string", "종목코드 6자리")}, ["code"]),
    "price_series": (t_price_series, "한 종목의 일봉 시계열",
                     {"code": ("string", "종목코드 6자리"),
                      "start": ("string", "YYYY-MM-DD"),
                      "end": ("string", "YYYY-MM-DD"),
                      "limit": ("integer", "최대 행 수 (기본 250)")}, ["code"]),
    "fundamentals": (t_fundamentals, "한 종목의 재무 항목 (DART)",
                     {"code": ("string", "종목코드 6자리"),
                      "period": ("string", "보고서 기간"),
                      "limit": ("integer", "최대 행 수")}, ["code"]),
    "disclosures": (t_disclosures, "한 종목의 공시 목록 (DART)",
                    {"code": ("string", "종목코드 6자리"),
                     "since": ("string", "YYYY-MM-DD"),
                     "limit": ("integer", "최대 행 수 (기본 100)")}, ["code"]),
    "index_series": (t_index_series, "지수 일봉",
                     {"index_name": ("string", "KOSPI · KOSDAQ · KONEX"),
                      "limit": ("integer", "최대 행 수")}, []),
    "macro": (t_macro, "거시 시계열 (한국은행 ECOS · FRED)",
              {"key": ("string", "지표 키"),
               "limit": ("integer", "최대 행 수")}, []),
    "staleness": (t_staleness, "원장이 며칠 뒤처졌는가",
                  {"market": ("string", "KOSPI · KOSDAQ · KONEX")}, []),
    "papers": (t_papers, "논문 장부 — 무엇을 인용해도 되는가 · 어떤 표시가 붙는가",
               {"key": ("string", "논문 키 (없으면 전부)"),
                "state": ("string", "unverified · adopted · warned · retired")}, []),
    "calendar": (t_calendar, "다가오는 일정 — 항목마다 등급(공표·규칙·추정)이 붙는다",
                 {"since": ("string", "YYYY-MM-DD (기본 오늘)"),
                  "until": ("string", "YYYY-MM-DD"),
                  "limit": ("integer", "최대 행 수 (기본 100)")}, []),
}


def tool_list() -> list[dict]:
    out = []
    for name, (_fn, desc, props, req) in TOOLS.items():
        out.append({
            "name": name,
            "description": desc + " — 읽기 전용입니다.",
            "inputSchema": {
                "type": "object",
                "properties": {k: {"type": t, "description": d}
                               for k, (t, d) in props.items()},
                "required": list(req),
            },
        })
    return out


def open_ledger(path: Path = None) -> sqlite3.Connection:
    """읽기 전용으로 연다. 쓰기는 SQLite 가 파일 수준에서 거절한다."""
    if path is None:
        sys.path.insert(0, str(MONITOR))
        import ki_monitor                                # noqa: PLC0415
        path = Path(ki_monitor.env("db_path"))
    if not Path(path).exists():
        raise Denied(f"원장이 없습니다: {Path(path).name}. "
                     f"ingest --universe <시장> 을 먼저 실행하십시오.")
    con = sqlite3.connect(f"file:{path}?mode=ro", uri=True)
    con.row_factory = sqlite3.Row
    return con


def call_tool(con, name: str, args: dict) -> dict:
    # 논문 장부는 원장과 다른 파일이다. 원장이 없어도 읽을 수 있어야 한다.
    if con is None and name not in ("papers", "calendar"):
        raise Denied("원장이 아직 없습니다. stock-monitor 에서 "
                     "ingest --universe <시장> 을 먼저 실행하십시오. "
                     "원장이 생기면 이 서버를 다시 시작할 필요 없이 바로 읽습니다.")
    spec = TOOLS.get(name)
    if spec is None:
        raise Denied(f"없는 도구입니다: {name!r}. 이 서버는 읽기 도구만 제공합니다 "
                     f"({', '.join(TOOLS)}).")
    fn, _desc, props, _req = spec
    unknown = [k for k in (args or {}) if k not in props]
    if unknown:
        raise Denied(f"모르는 인자입니다: {', '.join(unknown)}")
    return fn(con, **(args or {}))


# ── JSON-RPC ──────────────────────────────────────────────────────────

def handle(req: dict, con) -> dict | None:
    """요청 하나를 처리한다. 알림(notification)이면 None 을 낸다."""
    mid, method = req.get("id"), req.get("method")

    def ok(result):
        return {"jsonrpc": "2.0", "id": mid, "result": result}

    def err(code, message):
        return {"jsonrpc": "2.0", "id": mid,
                "error": {"code": code, "message": _scrub(message)}}

    if method == "initialize":
        return ok({"protocolVersion": PROTOCOL,
                   "capabilities": {"tools": {}},
                   "serverInfo": {"name": NAME, "version": VERSION},
                   "instructions": (
                       "원장을 읽는 서버입니다. 쓰기 도구는 제공하지 않습니다. "
                       "모든 응답에는 기준일(asof)과 경과일수(stale_days)가 붙습니다 "
                       "— 며칠 묵었는지 밝히지 않은 값은 근거로 쓰지 마십시오. "
                       "이 서버가 내는 값의 등급은 '1차' 이고, 그것을 읽고 쓴 문장은 "
                       "'해석' 입니다. 해석은 1차로 승격되지 않습니다.")})
    if method in ("notifications/initialized", "initialized"):
        return None
    if method == "ping":
        return ok({})
    if method == "tools/list":
        return ok({"tools": tool_list()})
    if method == "tools/call":
        params = req.get("params") or {}
        try:
            payload = call_tool(con, params.get("name"), params.get("arguments") or {})
        except Denied as e:
            return ok({"content": [{"type": "text", "text": _scrub(e)}], "isError": True})
        except Exception as e:                           # noqa: BLE001
            return ok({"content": [{"type": "text",
                                    "text": f"{type(e).__name__}: {_scrub(e)}"}],
                       "isError": True})
        return ok({"content": [{"type": "text",
                                "text": json.dumps(payload, ensure_ascii=False)}],
                   "structuredContent": payload})
    return err(-32601, f"지원하지 않는 메서드입니다: {method!r}")


def serve(con, stdin=None, stdout=None) -> int:
    stdin, stdout = stdin or sys.stdin, stdout or sys.stdout
    for line in stdin:
        line = line.strip()
        if not line:
            continue
        try:
            req = json.loads(line)
        except ValueError:
            stdout.write(json.dumps({"jsonrpc": "2.0", "id": None,
                                     "error": {"code": -32700,
                                               "message": "JSON 이 아닙니다"}},
                                    ensure_ascii=False) + "\n")
            stdout.flush()
            continue
        resp = handle(req, con)
        if resp is not None:
            stdout.write(json.dumps(resp, ensure_ascii=False) + "\n")
            stdout.flush()
    return 0


# ── 자체 검사 ─────────────────────────────────────────────────────────

def _ledger(tmp: Path) -> Path:
    """합성 원장 파일. 읽기 전용 연결을 진짜로 시험하려면 파일이어야 한다."""
    p = tmp / "ki.sqlite"
    con = sqlite3.connect(p)
    con.executescript("""
    CREATE TABLE price_daily (date TEXT, code TEXT, name TEXT, market TEXT,
      open REAL, high REAL, low REAL, close REAL, volume REAL, value REAL,
      mktcap REAL, shares REAL, PRIMARY KEY (date, code));
    CREATE TABLE index_daily (date TEXT, index_name TEXT, open REAL, high REAL,
      low REAL, close REAL, PRIMARY KEY (date, index_name));
    CREATE TABLE instruments (code TEXT PRIMARY KEY, name TEXT, market TEXT,
      sector TEXT, isin TEXT, corp_code TEXT, list_date TEXT, updated_at TEXT);
    CREATE TABLE disclosure (rcept_no TEXT PRIMARY KEY, corp_code TEXT, code TEXT,
      rcept_dt TEXT, title TEXT, tags TEXT, fetched_at TEXT);
    CREATE TABLE fundamental (code TEXT, period TEXT, key TEXT, value REAL,
      unit TEXT, source TEXT, PRIMARY KEY (code, period, key));
    CREATE TABLE macro_daily (date TEXT, key TEXT, value REAL, unit TEXT,
      source TEXT, PRIMARY KEY (date, key));
    """)
    days = ["2026-09-07", "2026-09-08", "2026-09-09", "2026-09-10", "2026-09-11"]
    for i, d in enumerate(days):
        for c in ("000660", "111111"):
            con.execute("INSERT INTO price_daily (date, code, name, market, open, high,"
                        " low, close, volume, value, mktcap, shares) "
                        "VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
                        (d, c, "샘플", "KOSDAQ", 100.0, 110.0, 95.0, 100.0 + i,
                         1000.0, 100000.0, 1e11, 1e6))
        con.execute("INSERT INTO index_daily VALUES (?,?,?,?,?,?)",
                    (d, "KOSDAQ", 800.0, 810.0, 790.0, 800.0 + i))
    con.execute("INSERT INTO instruments (code, name, market, list_date) "
                "VALUES ('000660','샘플','KOSDAQ','2015-01-02')")
    con.execute("INSERT INTO disclosure (rcept_no, code, rcept_dt, title, tags) "
                "VALUES ('R1','000660','2026-09-10','전환가액의조정','refix')")
    con.execute("INSERT INTO fundamental VALUES ('000660','2026Q2','rev',1.0,'KRW','DART')")
    con.execute("INSERT INTO macro_daily VALUES ('2026-09-11','base_rate',3.0,'%','ECOS')")
    con.commit(); con.close()
    return p


def selftest() -> int:
    import tempfile
    passed, failed = 0, []

    def check(name, fn):
        nonlocal passed
        try:
            fn(); passed += 1
        except Exception as e:                           # noqa: BLE001
            failed.append(f"{name}: {type(e).__name__}: {e}")

    def _assert(c, why=""):
        if not c:
            raise AssertionError(why or "거짓")

    with tempfile.TemporaryDirectory() as d:
        path = _ledger(Path(d))
        con = open_ledger(path)

        def _readonly_connection():
            """연결 자체가 쓰기를 거절하는가 — 두 번째 겹."""
            try:
                con.execute("INSERT INTO price_daily (date, code) VALUES ('2026-01-01','999999')")
                con.commit()
            except sqlite3.OperationalError as e:
                _assert("readonly" in str(e).lower(), str(e))
                return
            raise AssertionError("읽기 전용 연결에 쓰기가 성공했습니다")
        check("연결이 읽기 전용이다 (SQLite 가 거절한다)", _readonly_connection)

        def _no_write_tools():
            """쓰기 도구가 목록에 없는가 — 첫 번째 겹이자 가장 중요한 겹."""
            names = set(TOOLS)
            for w in ("insert", "update", "delete", "write", "exec", "sql",
                      "query", "ingest", "upsert", "drop"):
                _assert(not any(w in n for n in names), w)
            _assert(len(names) == 10, names)
            for t in tool_list():
                _assert("읽기 전용" in t["description"])
        check("쓰기 도구가 존재하지 않는다 (8종 전부 읽기)", _no_write_tools)

        def _no_raw_sql():
            """생 SQL 을 받는 인자가 없는가 — 세 번째 겹."""
            for t in tool_list():
                for k in t["inputSchema"]["properties"]:
                    _assert(k not in ("sql", "query", "where", "expr", "filter"), k)
        check("생 SQL 을 받는 인자가 없다", _no_raw_sql)

        def _unknown_tool():
            try:
                call_tool(con, "delete_all", {})
            except Denied as e:
                _assert("읽기 도구만" in str(e))
                return
            raise AssertionError("없는 도구가 실행됐습니다")
        check("없는 도구는 거절한다", _unknown_tool)

        def _facts():
            r = t_facts(con, "000660")
            _assert(r["ok"] and r["n"] == 1)
            _assert(r["asof"] == "2026-09-11")
            _assert(r["source_grade"] == "1차")
            _assert(isinstance(r["stale_days"], int))
        check("facts 는 기준일과 등급을 달고 나온다", _facts)

        def _facts_missing():
            r = t_facts(con, "999999")
            _assert(not r["ok"] and r["rows"] == [])
            _assert(r["reason"])                         # 사유 없이 비우지 않는다
        check("없는 종목은 사유와 함께 빈 값을 낸다 (0 을 만들지 않는다)", _facts_missing)

        def _bad_code():
            for bad in ("00066", "abcdef", "000660; DROP TABLE price_daily", 660, None):
                try:
                    t_facts(con, bad)
                except Denied:
                    continue
                raise AssertionError(f"이상한 종목코드가 통과했습니다: {bad!r}")
        check("이상한 종목코드를 거절한다 (주입 포함)", _bad_code)

        def _series():
            r = t_price_series(con, "000660", limit=3)
            _assert(r["n"] == 3)
            _assert(r["rows"][0]["date"] < r["rows"][-1]["date"])   # 오름차순
            _assert(r["asof"] == "2026-09-11")
        check("일봉은 오름차순으로 나오고 마지막 날이 기준일이다", _series)

        def _limit_capped():
            r = t_price_series(con, "000660", limit=99999)
            _assert(r["n"] <= MAX_ROWS)
            for bad in (0, -1, "10", 1.5):
                try:
                    t_price_series(con, "000660", limit=bad)
                except Denied:
                    continue
                raise AssertionError(f"이상한 limit 이 통과했습니다: {bad!r}")
        check("limit 에 상한이 있고 이상한 값을 거절한다", _limit_capped)

        def _staleness():
            r = t_staleness(con, "KOSDAQ")
            _assert(r["ok"] and r["rows"][0]["last_date"] == "2026-09-11")
            _assert(r["rows"][0]["codes"] == 2)
            _assert("공휴일" in r["stale_days_note"])     # 모르는 것을 숨기지 않는다
        check("원장이 며칠 뒤처졌는지 낸다", _staleness)

        def _all_tools_envelope():
            """여덟 도구 전부가 봉투를 입고 나오는가."""
            calls = {"universe": {}, "facts": {"code": "000660"},
                     "price_series": {"code": "000660"},
                     "fundamentals": {"code": "000660"},
                     "disclosures": {"code": "000660"},
                     "index_series": {}, "macro": {}, "staleness": {},
                     "papers": {}, "calendar": {}}
            _assert(set(calls) == set(TOOLS))
            for n, a in calls.items():
                r = call_tool(con, n, a)
                for k in ("ok", "source_grade", "asof", "stale_days", "rows", "n"):
                    _assert(k in r, f"{n}.{k}")
                # 논문 장부는 방법론이다 — 계산 규칙의 출처이지 시세가 아니다.
                _assert(r["source_grade"] in ("1차", "방법론", "참고"),
                        (n, r["source_grade"]))
        check("여덟 도구가 모두 봉투를 입고 나온다", _all_tools_envelope)

        def _unknown_arg():
            try:
                call_tool(con, "facts", {"code": "000660", "drop": 1})
            except Denied:
                return
            raise AssertionError("모르는 인자가 통과했습니다")
        check("모르는 인자를 거절한다", _unknown_arg)

        # ── JSON-RPC ──
        def _initialize():
            r = handle({"jsonrpc": "2.0", "id": 1, "method": "initialize"}, con)
            _assert(r["result"]["protocolVersion"] == PROTOCOL)
            _assert(r["result"]["serverInfo"]["name"] == NAME)
            _assert("쓰기 도구는 제공하지 않습니다" in r["result"]["instructions"])
        check("initialize 가 규약대로 응답한다", _initialize)

        def _notification_silent():
            _assert(handle({"jsonrpc": "2.0",
                            "method": "notifications/initialized"}, con) is None)
        check("알림에는 응답하지 않는다", _notification_silent)

        def _tools_list():
            r = handle({"jsonrpc": "2.0", "id": 2, "method": "tools/list"}, con)
            _assert(len(r["result"]["tools"]) == 10)
        check("tools/list 가 열 개를 낸다", _tools_list)

        def _tools_call():
            r = handle({"jsonrpc": "2.0", "id": 3, "method": "tools/call",
                        "params": {"name": "facts",
                                   "arguments": {"code": "000660"}}}, con)
            _assert("structuredContent" in r["result"])
            _assert(r["result"]["structuredContent"]["asof"] == "2026-09-11")
            _assert(not r["result"].get("isError"))
        check("tools/call 이 구조화된 결과를 낸다", _tools_call)

        def _tools_call_error():
            r = handle({"jsonrpc": "2.0", "id": 4, "method": "tools/call",
                        "params": {"name": "facts",
                                   "arguments": {"code": "나쁜코드"}}}, con)
            _assert(r["result"]["isError"])
            _assert("6자리" in r["result"]["content"][0]["text"])
        check("도구 오류는 사유와 함께 돌아온다", _tools_call_error)

        def _unknown_method():
            r = handle({"jsonrpc": "2.0", "id": 5, "method": "resources/write"}, con)
            _assert(r["error"]["code"] == -32601)
        check("지원하지 않는 메서드를 거절한다", _unknown_method)

        def _scrub_on_error():
            """오류 문구에 키가 남지 않는가 (규칙 5)."""
            msg = _scrub("요청 실패 https://x/api?crtfc_key=SECRET123456&y=1")
            _assert("SECRET123456" not in msg, msg)
        check("오류 문구에서 인증키를 가린다", _scrub_on_error)

        def _serve_roundtrip():
            import io as _io
            inp = _io.StringIO(
                '{"jsonrpc":"2.0","id":1,"method":"initialize"}\n'
                '{"jsonrpc":"2.0","method":"notifications/initialized"}\n'
                'not json\n'
                '{"jsonrpc":"2.0","id":2,"method":"tools/list"}\n')
            out = _io.StringIO()
            serve(con, inp, out)
            lines = [json.loads(x) for x in out.getvalue().splitlines() if x.strip()]
            _assert(len(lines) == 3, lines)              # 알림에는 응답이 없다
            _assert(lines[1]["error"]["code"] == -32700)
            _assert(len(lines[2]["result"]["tools"]) == 10)
        check("stdio 왕복이 성립한다 (깨진 줄에도 서버가 죽지 않는다)", _serve_roundtrip)

        con.close()

        def _no_ledger_still_serves():
            """원장이 없어도 서버는 서고, 사유를 말한다."""
            r = handle({"jsonrpc": "2.0", "id": 9, "method": "tools/list"}, None)
            _assert(len(r["result"]["tools"]) == 10)     # 목록은 나온다
            r2 = handle({"jsonrpc": "2.0", "id": 10, "method": "tools/call",
                         "params": {"name": "facts",
                                    "arguments": {"code": "000660"}}}, None)
            _assert(r2["result"]["isError"])
            _assert("ingest" in r2["result"]["content"][0]["text"])
        check("원장이 없어도 서버는 서고 사유를 말한다", _no_ledger_still_serves)

        def _papers_tool():
            """데스크가 논문 상태를 읽을 수 있어야 한다.

            읽을 수 없으면 봉투의 paper_state 를 추측해서 적게 되고, 게이트 ③ 이
            장부와 어긋난다고 반려한다. 데스크가 볼 수 없는 것을 근거로 반려하는
            관문은 관문이 아니라 함정이다."""
            import papers as _P
            if not _P.LEDGER.exists():
                return
            r = call_tool(con, "papers", {})
            _assert(r["ok"] and r["n"] >= 1, r)
            _assert(r["source_grade"] == "방법론")
            row = r["rows"][0]
            for k in ("paper", "state", "citable", "mark", "citation"):
                _assert(k in row, k)
            _assert(row["state"] in _P.STATES)
            _assert(call_tool(con, "papers", {"key": row["paper"]})["n"] == 1)
            ghost = call_tool(con, "papers", {"key": "없는논문2099"})
            _assert(not ghost["ok"] and "지어내지" in ghost["reason"])
        check("데스크가 논문 상태를 읽을 수 있다", _papers_tool)

        def _papers_filter_state():
            import papers as _P
            if not _P.LEDGER.exists():
                return
            r = call_tool(con, "papers", {"state": "unverified"})
            _assert(all(x["state"] == "unverified" for x in r["rows"]))
            try:
                call_tool(con, "papers", {"state": "없는상태"})
            except Denied:
                return
            raise AssertionError("없는 상태가 통과했습니다")
        check("논문 상태로 거를 수 있고 없는 상태는 거절한다", _papers_filter_state)

        def _papers_without_ledger():
            """원장이 없어도 논문 장부는 읽힌다 — 다른 파일이기 때문이다."""
            import papers as _P
            if not _P.LEDGER.exists():
                return
            r = handle({"jsonrpc": "2.0", "id": 11, "method": "tools/call",
                        "params": {"name": "papers", "arguments": {}}}, None)
            _assert(not r["result"].get("isError"), r["result"])
        check("원장이 없어도 논문 장부는 읽힌다", _papers_without_ledger)

        def _calendar_grades():
            """일정마다 등급이 붙어 나오는가.

            공표된 확정 일정과 상장일에서 추정한 것을 같은 줄에 늘어놓으면
            회의에서 전부 확정 일정처럼 읽힌다."""
            if not CALENDAR.exists():
                return
            r = call_tool(con, "calendar", {"since": "2020-01-01", "limit": 5})
            _assert(r["ok"], r)
            _assert(r["source_grade"] == "참고")
            for row in r["rows"]:
                _assert(row.get("grade"), row)
                _assert(row.get("date") and row.get("event"), row)
            _assert(r.get("grades"))
            _assert("섞지" in r["note"])
        check("일정은 항목마다 등급을 달고 나온다", _calendar_grades)

        def _calendar_window():
            if not CALENDAR.exists():
                return
            r = call_tool(con, "calendar",
                          {"since": "2026-01-01", "until": "2026-06-30"})
            _assert(all("2026-01-01" <= x["date"] <= "2026-06-30" for x in r["rows"]))
            try:
                call_tool(con, "calendar", {"since": "2026/01/01"})
            except Denied:
                return
            raise AssertionError("이상한 날짜가 통과했습니다")
        check("일정 구간을 거르고 이상한 날짜를 거절한다", _calendar_window)

        def _missing_ledger():
            try:
                open_ledger(Path(d) / "없는파일.sqlite")
            except Denied as e:
                _assert("ingest" in str(e))              # 다음에 할 일을 알려 준다
                return
            raise AssertionError("없는 원장이 열렸습니다")
        check("원장이 없으면 무엇을 해야 하는지 알려 준다", _missing_ledger)

    for f in failed:
        print("  X  " + f, file=sys.stderr)
    print(f"mcp        {passed} passed, {len(failed)} failed")
    return 1 if failed else 0


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="ki-ledger MCP 서버 (읽기 전용)")
    ap.add_argument("--selftest", action="store_true")
    ap.add_argument("--db", help="원장 경로")
    a = ap.parse_args()
    if a.selftest:
        sys.exit(selftest())
    # 원장이 없어도 선다. 세션마다 죽어 있는 서버보다, 도구를 부르면 "원장이
    # 없습니다 — ingest 를 먼저 하십시오" 라고 답하는 서버가 쓸모 있다.
    con = None
    try:
        con = open_ledger(Path(a.db) if a.db else None)
    except Denied as e:
        print(_scrub(e), file=sys.stderr)
    try:
        sys.exit(serve(con))
    finally:
        if con is not None:
            con.close()
