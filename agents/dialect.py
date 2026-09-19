"""원장의 말 — 저장된 형식을 코드가 짐작하지 않고 물어본다.

이 모듈이 생긴 이유는 한 가지다. **합성 자료로 검증하면 자기 자신을 검증한다.**

판단층 전체를 만들면서 원장의 날짜를 `YYYY-MM-DD`, 시장을 `"KOSDAQ"`, 지수를
`"KOSDAQ"` 이라고 가정했다. 검사도 그 가정대로 표를 만들어 통과했다. 그런데
진짜 원장은 다르다.

    date         "20260917"   KRX BAS_DD 를 문자열 그대로 (대시 없음)
    market       "코스닥"      KRX MKT_NM 을 그대로
    index_name   "코스닥"      KRX IDX_NM 을 그대로 (ki_monitor.BENCHMARK)

그대로 뒀으면 진짜 원장에서 **모든 질의가 빈 결과**를 냈을 것이다. 그리고
빈 결과는 "원장에 없습니다" 로 나간다 — 코드가 틀렸다는 말이 아니라 자료가
없다는 말로 읽힌다. 조용히 틀리는 쪽이다.

그래서 여기서는 **짐작하지 않고 원장에 물어본다.** 형식이 바뀌어도 코드가
아니라 이 모듈 하나만 본다.
"""
from __future__ import annotations

import re
import sys
from datetime import date as _date, datetime
from pathlib import Path

MONITOR = Path(__file__).resolve().parent.parent / "stock-monitor"

# 측정층이 쓰는 기준 지수 이름. 가져오지 못하면 KRX 가 주는 값을 그대로 쓴다.
try:
    sys.path.insert(0, str(MONITOR))
    import ki_monitor as _K                              # noqa: PLC0415
    BENCHMARK = getattr(_K, "BENCHMARK", "코스닥")
except Exception:                                        # noqa: BLE001
    BENCHMARK = "코스닥"

# 사람이 부르는 이름 → 원장에 적힐 법한 이름. 원장에 물어보는 것이 먼저이고,
# 이것은 물어볼 수 없을 때의 차선이다.
MARKET_ALIASES = {
    "KOSDAQ": ("코스닥", "KOSDAQ"),
    "KOSPI": ("유가증권", "코스피", "KOSPI"),
    "KONEX": ("코넥스", "KONEX"),
}

_COMPACT = re.compile(r"^\d{8}$")
_ISO = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def norm_date(d: str) -> str:
    """어떤 형식으로 오든 `YYYYMMDD` 로. 대시만 떼면 된다."""
    s = str(d or "").strip()
    return s.replace("-", "") if _ISO.match(s) else s


def iso_date(d: str) -> str:
    """사람과 봉투가 읽는 `YYYY-MM-DD` 로."""
    s = str(d or "").strip()
    if _COMPACT.match(s):
        return f"{s[:4]}-{s[4:6]}-{s[6:]}"
    return s


def parse_date(v) -> "_date | None":
    """날짜 한 칸을 읽는다. 못 읽으면 None — 지어내지 않는다 (규칙 3).

    원장은 한 형식이 아니다. KRX 는 `"20260917"`, DART 의 `rcept_dt` 도 같고,
    FRED 를 거친 `macro_daily` 에는 `"2026-09-17 00:00:00"` 이 들어 있다.
    `datetime.fromisoformat` 은 첫째를 3.11 부터만 받고 셋째는 date 가 아니다.
    읽는 쪽이 저마다 다르게 처리하면, 어떤 스캐너는 종목을 통째로 빠뜨리고
    어떤 스캐너는 안 빠뜨린다 — 그 차이를 아무도 못 본다."""
    # 대시만 떼고 앞 여덟 자리를 본다. 시각이 붙어 있어도(`"... 00:00:00"`)
    # 날짜만 남고, `"2026/09/17"` 처럼 모르는 구분자는 숫자가 아니어서 걸린다.
    s = str(v or "").strip().replace("-", "")[:8]
    if len(s) != 8 or not s.isdigit():
        return None
    try:
        return datetime.strptime(s, "%Y%m%d").date()
    except ValueError:
        return None


def sql_date(col: str) -> str:
    """SQL 안에서 날짜 칸을 `YYYYMMDD` 로 맞춘 식.

    `date > date(?, '-7 day')` 처럼 SQLite 의 날짜 함수에 기대면 안 된다.
    그 함수들은 ISO 만 받고, 원장은 `"20260917"` 이다. 둘을 문자열로 비교하면
    4번째 글자에서 `'0'` 과 `'-'` 이 만나 **같은 해의 모든 날짜가 통과한다** —
    7일 창이 조용히 '올해 전체'가 된다. 그 결과가 '없음'이면 차라리 낫다.
    실제로는 여덟 달 전 -40% 하락이 **오늘의 소집**으로 올라왔다.

    색인을 타지 못하지만, 이 스캐너들은 어차피 전수 정렬을 한다."""
    return f"substr(replace({col}, '-', ''), 1, 8)"


def date_style(con) -> str:
    """원장이 날짜를 어떻게 적어 두었는가. 물어봐서 정한다."""
    try:
        r = con.execute("SELECT date FROM price_daily LIMIT 1").fetchone()
    except Exception:                                    # noqa: BLE001
        return "compact"
    if not r:
        return "compact"
    v = str(r[0] if not hasattr(r, "keys") else r["date"])
    return "iso" if _ISO.match(v) else "compact"


def as_ledger_date(d: str, style: str) -> str:
    """질의에 넣을 형태로. 원장이 쓰는 형식에 맞춘다."""
    return iso_date(d) if style == "iso" else norm_date(d)


def _distinct(con, table: str, col: str) -> list:
    try:
        return [str(r[0]) for r in
                con.execute(f"SELECT DISTINCT {col} FROM {table} "
                            f"WHERE {col} IS NOT NULL AND {col} <> ''")]
    except Exception:                                    # noqa: BLE001
        return []


def _pick(have: list, hint: str) -> str | None:
    """원장이 실제로 가진 값 중에서 고른다. 없는 이름을 지어내지 않는다."""
    if not hint:
        return None
    if hint in have:
        return hint
    for alias in MARKET_ALIASES.get(hint.upper(), ()):
        if alias in have:
            return alias
    # 부분 일치 — '코스닥 (외국주포함)' 같은 변형을 위해서다. 짧은 것이 본체다.
    cands = [h for a in MARKET_ALIASES.get(hint.upper(), (hint,))
             for h in have if a and a in h]
    return min(cands, key=len) if cands else None


def resolve_market(con, hint: str = "KOSDAQ") -> tuple[str | None, str | None]:
    """시장 이름을 원장에 맞춘다. (이름, 사유) — 못 찾으면 이름이 None 이다."""
    have = _distinct(con, "price_daily", "market")
    if not have:
        return None, "원장에 일봉이 없습니다"
    got = _pick(have, hint)
    if got is None:
        return None, (f"{hint!r} 에 해당하는 시장이 원장에 없습니다. "
                      f"원장에 있는 것: {', '.join(sorted(have)[:5])}")
    return got, None


def resolve_index(con, market: str = None) -> tuple[str | None, str | None]:
    """지수 이름을 원장에 맞춘다.

    KRX 는 `IDX_NM` 을 한글로 준다. 여기서 영문을 넣으면 질의가 늘 비고, 그
    빈 결과가 "지수가 원장에 없습니다" 로 나가 자료 탓이 된다."""
    have = _distinct(con, "index_daily", "index_name")
    if not have:
        return None, "원장에 지수가 없습니다"
    for hint in (market, BENCHMARK, "KOSDAQ"):
        got = _pick(have, hint) if hint else None
        if got:
            return got, None
    return None, (f"기준 지수를 찾지 못했습니다. 원장에 있는 것: "
                  f"{', '.join(sorted(have)[:5])}")


# ── 자체 검사 ─────────────────────────────────────────────────────────

def _fixture(style="compact", market="코스닥", index="코스닥"):
    """**진짜 원장의 형식**으로 만든다. 이것이 이 모듈의 존재 이유다."""
    import sqlite3
    con = sqlite3.connect(":memory:")
    con.row_factory = sqlite3.Row
    con.executescript("""
    CREATE TABLE price_daily (date TEXT, code TEXT, market TEXT, close REAL);
    CREATE TABLE index_daily (date TEXT, index_name TEXT, close REAL);
    """)
    d = "2026-09-17" if style == "iso" else "20260917"
    con.execute("INSERT INTO price_daily VALUES (?,?,?,?)", (d, "000660", market, 88.0))
    con.execute("INSERT INTO index_daily VALUES (?,?,?)", (d, index, 800.0))
    con.commit()
    return con


def selftest() -> int:
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

    def _benchmark_comes_from_the_measurement_layer():
        """기준 지수 이름을 짐작하지 않는다 — 측정층이 쓰는 값을 가져온다."""
        _assert(BENCHMARK == "코스닥", BENCHMARK)
    check("기준 지수 이름을 측정층에서 가져온다",
          _benchmark_comes_from_the_measurement_layer)

    def _parse_every_form_the_ledger_uses():
        """원장에 실제로 들어 있는 세 형식을 모두 읽는다."""
        _assert(parse_date("20260917").isoformat() == "2026-09-17")
        _assert(parse_date("2026-09-17").isoformat() == "2026-09-17")
        _assert(parse_date("2026-09-17 00:00:00").isoformat() == "2026-09-17")
        _assert(parse_date("") is None and parse_date(None) is None)
        _assert(parse_date("2026/09/17") is None)        # 지어내지 않는다
        _assert(parse_date("20261332") is None)          # 없는 날
    check("원장이 쓰는 날짜 형식을 모두 읽는다",
          _parse_every_form_the_ledger_uses)

    def _sql_date_beats_string_comparison():
        """맨눈 비교가 왜 안 되는지를 검사로 박아 둔다."""
        import sqlite3
        con = sqlite3.connect(":memory:")
        con.execute("CREATE TABLE t (d TEXT)")
        con.executemany("INSERT INTO t VALUES (?)",
                        [("20260108",), ("20260911",), ("2026-09-11 00:00:00",)])
        # 맨눈 비교 — 1월 8일이 9월 4일보다 '크다'고 나온다
        bad = con.execute("SELECT COUNT(*) FROM t WHERE d > ?",
                          ("2026-09-04",)).fetchone()[0]
        _assert(bad == 3, bad)
        good = con.execute(f"SELECT COUNT(*) FROM t WHERE {sql_date('d')} > ?",
                           ("20260904",)).fetchone()[0]
        _assert(good == 2, good)                         # 1월 8일은 빠진다
        con.close()
    check("SQL 안에서 두 형식을 같은 자로 잰다",
          _sql_date_beats_string_comparison)

    def _date_both_ways():
        _assert(norm_date("2026-09-17") == "20260917")
        _assert(norm_date("20260917") == "20260917")
        _assert(iso_date("20260917") == "2026-09-17")
        _assert(iso_date("2026-09-17") == "2026-09-17")
        _assert(norm_date(None) == "" and iso_date("") == "")
    check("날짜를 양방향으로 바꾼다", _date_both_ways)

    def _style_is_asked_not_guessed():
        c1 = _fixture("compact"); c2 = _fixture("iso")
        _assert(date_style(c1) == "compact")
        _assert(date_style(c2) == "iso")
        _assert(as_ledger_date("2026-09-17", "compact") == "20260917")
        _assert(as_ledger_date("20260917", "iso") == "2026-09-17")
        c1.close(); c2.close()
    check("날짜 형식을 원장에 물어본다", _style_is_asked_not_guessed)

    def _korean_market_resolves():
        """영문으로 불러도 원장의 한글 값을 찾아낸다.

        이것이 안 되면 진짜 원장에서 모든 질의가 빈 결과를 내고, 그 빈 결과가
        '원장에 없습니다' 로 나간다 — 코드가 틀렸다는 말이 아니라."""
        con = _fixture(market="코스닥")
        got, why = resolve_market(con, "KOSDAQ")
        _assert(got == "코스닥" and why is None, (got, why))
        _assert(resolve_market(con, "코스닥")[0] == "코스닥")
        con.close()
    check("영문 이름으로 원장의 한글 시장을 찾는다", _korean_market_resolves)

    def _index_resolves():
        con = _fixture(index="코스닥")
        got, why = resolve_index(con, "코스닥")
        _assert(got == "코스닥" and why is None, (got, why))
        _assert(resolve_index(con, "KOSDAQ")[0] == "코스닥")
        _assert(resolve_index(con, None)[0] == "코스닥")   # BENCHMARK 로 찾는다
        con.close()
    check("지수 이름을 원장에 맞춘다", _index_resolves)

    def _variant_picks_the_shorter():
        """'코스닥 (외국주포함)' 은 거래대금만 있고 지수가 빈 행이다."""
        con = _fixture()
        con.execute("INSERT INTO index_daily VALUES ('20260917','코스닥 (외국주포함)',0)")
        con.commit()
        _assert(resolve_index(con, "KOSDAQ")[0] == "코스닥")
        con.close()
    check("이름 변형이 있어도 본체를 고른다", _variant_picks_the_shorter)

    def _missing_says_what_is_there():
        con = _fixture(market="유가증권", index="코스피")
        got, why = resolve_market(con, "KOSDAQ")
        _assert(got is None and "유가증권" in why, (got, why))
        con.close()
    check("못 찾으면 원장에 무엇이 있는지 알려 준다", _missing_says_what_is_there)

    def _empty_ledger():
        import sqlite3
        con = sqlite3.connect(":memory:")
        con.executescript("CREATE TABLE price_daily (date TEXT, market TEXT);"
                          "CREATE TABLE index_daily (date TEXT, index_name TEXT);")
        _assert(resolve_market(con, "KOSDAQ") == (None, "원장에 일봉이 없습니다"))
        _assert(resolve_index(con)[0] is None)
        _assert(date_style(con) == "compact")            # 못 물어보면 기본값
        con.close()
    check("빈 원장에서도 사유를 낸다", _empty_ledger)

    def _no_english_hardcode_survives():
        """이 모듈 자신이 영문 이름을 정답으로 들고 있지 않은가."""
        _assert("KOSDAQ" in MARKET_ALIASES)
        _assert("코스닥" in MARKET_ALIASES["KOSDAQ"])
        _assert(MARKET_ALIASES["KOSDAQ"][0] == "코스닥",
                "원장의 값이 먼저 와야 한다")
    check("원장의 값이 별칭 목록의 앞에 온다", _no_english_hardcode_survives)

    for f in failed:
        print("  X  " + f, file=sys.stderr)
    print(f"dialect    {passed} passed, {len(failed)} failed")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(selftest())
