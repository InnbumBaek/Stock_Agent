"""이벤트 시간 러너 — 달력이 아니라 사건을 기준으로 잰다.

`replication.py` 는 달력 시간에 분위를 정렬한다. 그것으로 재지 못하는 주장이
있다. "상장하고 3년 지나면 시장보다 못하다"나 "보호예수가 풀리는 날 주변에서
주가가 눌린다"는 **각 종목마다 기준일이 다른** 주장이다. 달력으로 줄을 세우면
사건이 서로 상쇄돼 아무것도 안 보인다.

두 종류를 나눠 쓴다. 섞으면 t 가 거짓말을 한다.

**긴 구간 — 달력시간 포트폴리오.** 상장 후 3년 같은 긴 창은 종목마다 구간이
겹친다. 겹친 표본을 횡단면 t 로 재면 관측 수가 부풀려져 없는 효과가 유의하게
나온다. 매달 '해당 구간에 있는 종목' 포트폴리오를 만들어 그 시계열에
Newey-West 를 걸면 겹침이 포트폴리오 안으로 들어간다 (Fama 1998 이 권하는
방식이고, Ritter 자신도 이 문제를 지적한다).

**짧은 창 — 횡단면 CAR.** ±5영업일이면 겹침이 적어 횡단면 t 로 충분하다.
다만 같은 날 여러 종목이 풀리면 그 날짜에 몰린다 — 한계에 적는다.

읽기만 한다. 원장에 쓰지 않는다. 결정적이다.

    python agents/eventstudy.py --selftest
    python agents/eventstudy.py --paper ritter1991
"""
from __future__ import annotations

import argparse
import json
import sqlite3
import sys
from datetime import date
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))

import dialect as D                                      # noqa: E402
import replication as R                                  # noqa: E402

SCHEMA = "ki.eventstudy/1"

# 임계는 재현 관문과 같은 값을 쓴다. 이벤트라고 문턱을 낮추면, 낮춰서 통과한
# 것과 넘어서 통과한 것이 장부에서 구분되지 않는다.
T_MIN = R.T_MIN

MIN_EVENTS = 30          # 이보다 적으면 평균이 몇 종목에 끌려다닌다
MIN_MONTHS = 36          # 달력시간 포트폴리오의 최소 길이

LOCKUP_MONTHS = 6        # ki_monitor · triggers 와 같은 값


def _add_months(d: date, n: int) -> date:
    m = d.month - 1 + n
    y, m = d.year + m // 12, m % 12 + 1
    try:
        return d.replace(year=y, month=m)
    except ValueError:                                   # 2/30 같은 날짜
        return d.replace(year=y, month=m, day=28)


# ── 검정 가능한 주장 ──────────────────────────────────────────────────

EVENT_CLAIMS: dict[str, dict] = {
    "ritter1991": {
        "kind": "calendar_time",
        "anchor": "list_date", "months": 36, "sign": -1,
        "claim": "상장 후 3년 동안 시장 대비 수익률이 낮다",
        "limits": [
            "논문 표본은 1975~84년 미국 IPO 다. 코스닥에서 성립한다는 근거가 아니다",
            "기준선은 코스닥 지수다 — 논문의 규모·업종 대응 표본이 아니므로 "
            "규모 효과가 섞여 들어간다",
            "상장폐지된 종목은 원장에서 사라진다. 생존편의를 보정하지 않았고, "
            "그 방향은 이 검정을 **덜** 유의하게 만드는 쪽이 아니다",
        ],
    },
    "fh2001": {
        "kind": "window",
        "anchor": "lockup_end", "pre": 5, "post": 5, "sign": -1,
        "claim": "보호예수 해제일 주변에서 시장 대비 초과수익이 음(-)이다",
        "limits": [
            "해제일은 상장일 + 6개월로 **추정**한 값이다. 실제 확약 기간은 "
            "증권신고서를 봐야 하고, 종목마다 다르다",
            "같은 날 여러 종목이 풀리면 그 날짜에 표본이 몰린다 — 횡단면 t 는 "
            "그 군집을 보정하지 않는다",
            "논문 표본은 미국 IPO 다. 한국의 의무보유 제도는 대상·기간이 다르다",
        ],
    },
}


# ── 원장에서 읽기 ─────────────────────────────────────────────────────

def _read(con, sql: str, params) -> pd.DataFrame:
    """표가 없으면 빈 것을 낸다. 예외로 죽지 않는다 — 부르는 쪽이 사유를 만든다."""
    try:
        return pd.read_sql_query(sql, con, params=params)
    except Exception:                                     # noqa: BLE001
        return pd.DataFrame()


def _prices(con, market: str) -> pd.DataFrame:
    df = _read(con, "SELECT date, code, close FROM price_daily WHERE market = ? "
                    "AND close > 0 ORDER BY code, date", (market,))
    if df.empty:
        return df
    df["date"] = pd.to_datetime(df["date"].map(D.norm_date), format="%Y%m%d")
    return df


def _index(con, index_name: str) -> pd.Series:
    """받는 것은 **원장에 적힌 지수 이름**이다 (`dialect.resolve_index`)."""
    if not index_name:
        return pd.Series(dtype=float)
    idx = _read(con, "SELECT date, close FROM index_daily WHERE index_name = ? "
                     "ORDER BY date", (index_name,))
    if idx.empty:
        return pd.Series(dtype=float)
    return pd.Series(idx["close"].to_numpy(dtype=float),
                     index=pd.to_datetime(idx["date"].map(D.norm_date),
                                          format="%Y%m%d"))


def _parse_list_date(ld) -> "date | None":
    """상장일을 읽는다. 못 읽으면 None — 지어내지 않는다 (규칙 3).

    KRX `LIST_DD` 는 `"20170102"` 로 온다. `datetime.fromisoformat` 이 그
    형식을 받아 주는 것은 파이썬 3.11 부터다. 3.10 에서는 전 종목이 조용히
    빠지고 '상장일이 있는 종목이 없습니다' 로 나간다 — 원장은 멀쩡한데.

    읽는 규칙은 `dialect` 한 곳에 있다. 여기서 따로 쓰면 읽는 쪽마다 받는
    형식이 달라지고, 그 차이는 '어떤 종목만 빠진다'로만 보인다."""
    return D.parse_date(ld)


def _events(con, anchor: str, market: str) -> dict:
    """종목별 사건일. 지어내지 않는다 — 상장일이 없으면 그 종목은 빠진다."""
    try:
        rows = con.execute(
            "SELECT code, list_date FROM instruments WHERE market = ? "
            "AND list_date IS NOT NULL AND list_date <> '' ORDER BY code",
            (market,)).fetchall()
    except Exception:                                     # noqa: BLE001
        return {}
    out = {}
    for r in rows:
        code = r[0] if not hasattr(r, "keys") else r["code"]
        ld = r[1] if not hasattr(r, "keys") else r["list_date"]
        d = _parse_list_date(ld)
        if d is None:
            continue
        out[code] = d if anchor == "list_date" else _add_months(d, LOCKUP_MONTHS)
    return out


# ── 긴 구간 — 달력시간 포트폴리오 ─────────────────────────────────────

def _calendar_time(px: pd.DataFrame, idx: pd.Series, events: dict,
                   months: int) -> tuple[np.ndarray, int, str | None]:
    """매달 '사건 후 `months` 개월 안에 있는 종목' 포트폴리오의 초과수익.

    겹침이 포트폴리오 안으로 들어가므로 관측 수가 부풀려지지 않는다."""
    wide = px.pivot(index="date", columns="code", values="close")
    m_px = wide.resample("ME").last()
    m_ret = m_px.pct_change()
    m_idx = idx.resample("ME").last().pct_change().reindex(m_ret.index)

    rows, n_used = [], set()
    for t in m_ret.index:
        members = [c for c, ev in events.items()
                   if c in m_ret.columns
                   and pd.Timestamp(ev) < t <= pd.Timestamp(_add_months(ev, months))]
        if not members:
            continue
        r = m_ret.loc[t, members].dropna()
        if r.empty or not np.isfinite(m_idx.loc[t]):
            continue
        rows.append(float(r.mean() - m_idx.loc[t]))
        n_used.update(members)
    if len(rows) < MIN_MONTHS:
        return (np.array([]), len(n_used),
                f"달력시간 포트폴리오가 {len(rows)}개월뿐입니다 "
                f"({MIN_MONTHS}개월 이상 필요)")
    # 달 수만 보면 안 된다. 세 종목짜리 포트폴리오도 36개월은 채운다 — 그때
    # 나오는 t 는 그 세 종목 이야기이고, 논문 주장의 재현이 아니다.
    if len(n_used) < MIN_EVENTS:
        return (np.array([]), len(n_used),
                f"포트폴리오에 들어온 종목이 {len(n_used)}개뿐입니다 "
                f"({MIN_EVENTS}개 이상 필요)")
    return np.array(rows, dtype=float), len(n_used), None


# ── 짧은 창 — 횡단면 CAR ──────────────────────────────────────────────

def _window_car(px: pd.DataFrame, idx: pd.Series, events: dict,
                pre: int, post: int) -> tuple[np.ndarray, int, str | None]:
    """사건일 ±n영업일의 누적초과수익. 종목마다 하나씩 나온다."""
    wide = px.pivot(index="date", columns="code", values="close")
    ret = wide.pct_change()
    iret = idx.pct_change().reindex(ret.index)
    days = ret.index

    cars = []
    for code, ev in events.items():
        if code not in ret.columns:
            continue
        pos = days.searchsorted(pd.Timestamp(ev))
        lo, hi = pos - pre, pos + post + 1
        if lo < 0 or hi > len(days):
            continue                                     # 창이 원장 밖으로 나간다
        ar = ret[code].iloc[lo:hi] - iret.iloc[lo:hi]
        ar = ar.dropna()
        if len(ar) < (pre + post + 1) - 2:               # 결측이 너무 많다
            continue
        cars.append(float(ar.sum()))
    if len(cars) < MIN_EVENTS:
        return (np.array([]), len(cars),
                f"창이 성립하는 사건이 {len(cars)}건뿐입니다 "
                f"({MIN_EVENTS}건 이상 필요)")
    return np.array(cars, dtype=float), len(cars), None


def _cross_t(x: np.ndarray) -> tuple[float, float]:
    """횡단면 t. 짧은 창에서만 쓴다 — 긴 구간에는 겹침 때문에 못 쓴다."""
    n = x.size
    sd = x.std(ddof=1)
    if n < 2 or not np.isfinite(sd) or sd <= 0:
        return float("nan"), float("nan")
    se = sd / np.sqrt(n)
    return float(x.mean() / se), float(se)


def run(con, key: str, market: str = "KOSDAQ", t_min: float = T_MIN,
        at: str = None) -> dict:
    spec = EVENT_CLAIMS.get(key)
    out = {
        "schema": SCHEMA, "paper": key, "at": at or date.today().isoformat(),
        "universe": market, "verdict": R.VERDICT_NONE, "claim": None,
        "method": None, "n": 0, "observed": None,
        "t_min": t_min, "t_min_paper": R.T_MIN_PAPER, "reason": None,
    }
    if not spec:
        out["reason"] = (f"{key!r} 에 대해 검정 가능한 이벤트 주장이 등록돼 "
                         f"있지 않습니다")
        return out
    out["claim"] = spec["claim"]
    out["method"] = spec["kind"]

    # 원장이 쓰는 말로 바꾼다 (`dialect`). 짐작하면 질의가 비고, 빈 결과는
    # '자료가 없다' 로 나간다 — 코드가 틀렸다는 말이 아니라.
    mkt_name, why = D.resolve_market(con, market)
    if mkt_name is None:
        out["reason"] = why
        return out
    out["universe"] = mkt_name

    px = _prices(con, mkt_name)
    if px.empty:
        out["reason"] = f"원장에 {mkt_name} 일봉이 없습니다"
        return out
    idx_name, why_idx = D.resolve_index(con, mkt_name)
    idx = _index(con, idx_name)
    if idx.empty:
        detail = why_idx or f"{idx_name} 지수가 원장에 없습니다"
        out["reason"] = f"{detail} — 초과수익의 기준선을 만들 수 없습니다"
        return out
    events = _events(con, spec["anchor"], mkt_name)
    if not events:
        out["reason"] = "상장일이 있는 종목이 없습니다 (instruments.list_date)"
        return out

    if spec["kind"] == "calendar_time":
        series, n, why = _calendar_time(px, idx, events, spec["months"])
        stat = "newey_west"
    else:
        series, n, why = _window_car(px, idx, events, spec["pre"], spec["post"])
        stat = "cross_section"
    out["n"] = n
    if why:
        out["reason"] = why
        return out

    if stat == "newey_west":
        t, se, lags = R.newey_west_t(series)
        extra = {"nw_lags": lags, "periods": int(series.size)}
    else:
        t, se = _cross_t(series)
        extra = {"events": int(series.size)}
    mean = float(series.mean())
    out["observed"] = {
        "mean_bp": round(mean * 1e4, 1),
        "t": None if not np.isfinite(t) else round(float(t), 2),
        "se_bp": None if not np.isfinite(se) else round(se * 1e4, 1),
        "stat": stat, "expected_sign": spec["sign"], **extra,
    }
    out["verdict"], out["reason"] = R.decide(mean, t, spec["sign"], t_min)
    out["limits"] = list(spec["limits"])
    return out


# ── 자체 검사 ─────────────────────────────────────────────────────────

# 합성 원장이 쓸 시장 이름. 진짜 원장이 쓰는 값이다 (`dialect`).
_MKT = D.MARKET_ALIASES["KOSDAQ"][0]


def _synth(effect: float = 0.0, names: int = 120, years: int = 9,
           seed: int = 3, window_effect: float = 0.0) -> sqlite3.Connection:
    """합성 원장. 상장일을 흩뿌리고 그 뒤 구간에만 효과를 싣는다.

    effect 는 상장 후 36개월 동안의 **월간** 초과수익이고, window_effect 는
    보호예수 해제일 ±5영업일에 한 번 실리는 초과수익이다.

    **진짜 원장의 형식으로 만든다** — 날짜·상장일은 `YYYYMMDD`, 시장과 지수는
    한글이다. 영문·ISO 로 만들면 검사가 자기 가정을 다시 확인할 뿐이다."""
    rng = np.random.default_rng(seed)
    con = sqlite3.connect(":memory:")
    con.row_factory = sqlite3.Row
    con.executescript("""
    CREATE TABLE price_daily (date TEXT, code TEXT, market TEXT, close REAL,
      PRIMARY KEY (date, code));
    CREATE TABLE index_daily (date TEXT, index_name TEXT, close REAL,
      PRIMARY KEY (date, index_name));
    CREATE TABLE instruments (code TEXT PRIMARY KEY, name TEXT, market TEXT,
      list_date TEXT);
    """)
    days = pd.bdate_range("2017-01-02", periods=years * 252)
    codes = [f"{i:06d}" for i in range(1, names + 1)]
    # 상장일을 앞쪽 구간에 흩뿌린다 — 뒤쪽이 검정에 쓰인다. 구간이 짧으면
    # 그 안에서 흩뿌린다 (짧은 원장 검사가 합성기 때문에 깨지면 안 된다).
    spread = max(1, min(252 * 3, len(days) // 2))
    listed = [days[int(rng.integers(0, spread))] for _ in codes]
    lock = [pd.Timestamp(_add_months(d.date(), LOCKUP_MONTHS)) for d in listed]

    mkt = 1000.0
    px = np.full(names, 10000.0)
    rows, irows = [], []
    for d in days:
        mr = rng.normal(0.0003, 0.010)
        mkt *= (1.0 + mr)
        drift = np.zeros(names)
        for i in range(names):
            if listed[i] < d <= pd.Timestamp(_add_months(listed[i].date(),
                                                         36)):
                drift[i] += effect / 21.0
            if window_effect and abs((d - lock[i]).days) <= 7:
                drift[i] += window_effect / 11.0
        r = rng.normal(0.0, 0.018, size=names) + mr + drift
        px = np.maximum(px * (1.0 + r), 100.0)
        ds = d.strftime("%Y%m%d")                # KRX BAS_DD 그대로
        irows.append((ds, D.BENCHMARK, float(mkt)))
        rows += [(ds, codes[i], _MKT, float(px[i])) for i in range(names)
                 if d >= listed[i]]
    con.executemany("INSERT INTO price_daily VALUES (?,?,?,?)", rows)
    con.executemany("INSERT INTO index_daily VALUES (?,?,?)", irows)
    con.executemany("INSERT INTO instruments VALUES (?,?,?,?)",
                    [(codes[i], "샘플", _MKT, listed[i].strftime("%Y%m%d"))
                     for i in range(names)])
    con.commit()
    return con


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

    check("임계는 재현 관문과 같다", lambda: _assert(T_MIN == R.T_MIN == 3.0))

    def _null_long():
        """효과가 없으면 통과하지 않아야 한다."""
        con = _synth(effect=0.0, seed=11)
        r = run(con, "ritter1991", at="2026-09-18"); con.close()
        _assert(r["verdict"] != R.VERDICT_OK, r)
        _assert(r["observed"]["stat"] == "newey_west")
    check("긴 구간 — 효과가 없으면 재현되지 않는다", _null_long)

    def _real_long():
        """상장 후 언더퍼폼이 뚜렷하면 잡아야 한다."""
        con = _synth(effect=-0.02, seed=5)
        r = run(con, "ritter1991", at="2026-09-18"); con.close()
        _assert(r["verdict"] == R.VERDICT_OK, r)
        _assert(r["observed"]["t"] < -T_MIN, r["observed"])
        _assert(r["observed"]["expected_sign"] == -1)
        _assert(r["n"] >= MIN_EVENTS)
    check("긴 구간 — 상장 후 언더퍼폼을 잡는다", _real_long)

    def _opposite_long():
        con = _synth(effect=+0.02, seed=5)
        r = run(con, "ritter1991", at="2026-09-18"); con.close()
        _assert(r["verdict"] == R.VERDICT_OPPOSITE, r)
    check("긴 구간 — 방향이 반대면 그렇게 판정한다", _opposite_long)

    def _null_window():
        con = _synth(effect=0.0, window_effect=0.0, seed=7)
        r = run(con, "fh2001", at="2026-09-18"); con.close()
        _assert(r["verdict"] != R.VERDICT_OK, r)
        _assert(r["observed"]["stat"] == "cross_section")
    check("짧은 창 — 효과가 없으면 재현되지 않는다", _null_window)

    def _real_window():
        con = _synth(effect=0.0, window_effect=-0.05, seed=7)
        r = run(con, "fh2001", at="2026-09-18"); con.close()
        _assert(r["verdict"] == R.VERDICT_OK, r)
        _assert(r["observed"]["t"] < -T_MIN, r["observed"])
    check("짧은 창 — 해제일 주변 눌림을 잡는다", _real_window)

    def _two_statistics():
        """긴 구간과 짧은 창이 다른 통계를 쓴다.

        겹치는 긴 표본에 횡단면 t 를 쓰면 관측 수가 부풀려져 없는 효과가
        유의하게 나온다. 이 구분이 이 모듈의 존재 이유다."""
        con = _synth(effect=-0.02, window_effect=-0.05, seed=5)
        a = run(con, "ritter1991", at="2026-09-18")
        b = run(con, "fh2001", at="2026-09-18")
        con.close()
        _assert(a["observed"]["stat"] == "newey_west")
        _assert("nw_lags" in a["observed"])
        _assert(b["observed"]["stat"] == "cross_section")
        _assert("events" in b["observed"])
    check("긴 구간과 짧은 창이 다른 통계를 쓴다", _two_statistics)

    def _thin():
        con = _synth(effect=-0.02, names=10, years=9, seed=5)
        r = run(con, "fh2001", at="2026-09-18"); con.close()
        _assert(r["verdict"] == R.VERDICT_NONE)
        _assert(r["reason"] and r["observed"] is None)
    check("사건이 적으면 판정하지 않는다", _thin)

    def _short_history():
        con = _synth(effect=-0.02, years=2, seed=5)
        r = run(con, "ritter1991", at="2026-09-18"); con.close()
        _assert(r["verdict"] == R.VERDICT_NONE)
        _assert(r["reason"])
    check("구간이 짧으면 판정하지 않는다", _short_history)

    def _no_index():
        """기준선이 없으면 초과수익을 만들 수 없다 — 0 으로 대신하지 않는다."""
        con = _synth(effect=-0.02, seed=5)
        con.execute("DELETE FROM index_daily")
        r = run(con, "ritter1991", at="2026-09-18"); con.close()
        _assert(r["verdict"] == R.VERDICT_NONE)
        _assert("기준선" in r["reason"])
    check("지수가 없으면 판정하지 않는다 (0 으로 대신하지 않는다)", _no_index)

    def _missing_tables():
        """표가 통째로 없어도 사유를 내고 끝난다 — 예외로 죽지 않는다.

        사이클이 이것을 예외로 받으면 '오류'로 기록되고, 그러면 못 돌린 이유가
        '원장에 지수가 없다'가 아니라 스택 트레이스가 된다."""
        con = sqlite3.connect(":memory:")
        con.row_factory = sqlite3.Row
        r = run(con, "ritter1991", at="2026-09-18")
        con.close()
        _assert(r["verdict"] == R.VERDICT_NONE)
        _assert(r["reason"] and "일봉" in r["reason"], r["reason"])
    check("표가 없어도 사유를 내고 끝난다 (예외로 죽지 않는다)", _missing_tables)

    def _unknown():
        con = _synth(years=4)
        r = run(con, "없는논문2099"); con.close()
        _assert(r["verdict"] == R.VERDICT_NONE and "등록" in r["reason"])
    check("등록되지 않은 주장은 판정하지 않는다", _unknown)

    def _limits():
        for k, c in EVENT_CLAIMS.items():
            _assert(c["sign"] in (1, -1), k)
            _assert(c["limits"] and all(str(x).strip() for x in c["limits"]), k)
            _assert(c["kind"] in ("calendar_time", "window"), k)
    check("모든 이벤트 주장이 한계를 달고 있다", _limits)

    def _deterministic():
        a = _synth(effect=-0.02, seed=5); ra = run(a, "ritter1991", at="2026-09-18"); a.close()
        b = _synth(effect=-0.02, seed=5); rb = run(b, "ritter1991", at="2026-09-18"); b.close()
        _assert(ra == rb)
    check("두 번 돌리면 같은 결과가 나온다", _deterministic)

    def _reads_only():
        con = _synth(effect=-0.02, seed=5)
        before = con.execute("SELECT COUNT(*) FROM price_daily").fetchone()[0]
        run(con, "ritter1991", at="2026-09-18")
        after = con.execute("SELECT COUNT(*) FROM price_daily").fetchone()[0]
        con.close()
        _assert(before == after)
    check("원장을 읽기만 한다", _reads_only)

    def _at_is_analysis_date():
        con = _synth(effect=-0.02, seed=5)
        a = run(con, "ritter1991", at="2026-09-18")
        b = run(con, "ritter1991", at="2027-01-01")
        con.close()
        _assert(a["at"] != b["at"] and a["observed"] == b["observed"])
    check("판정일은 분석 기준일이다", _at_is_analysis_date)

    # ── 원장의 말 (dialect) ───────────────────────────────────────────
    #
    # 아래 셋은 합성 자료로 검증하다 자기 가정을 다시 확인하고 있던 자리다.
    # 원장은 날짜를 `YYYYMMDD`, 시장·지수를 한글로 적는다. 판단층이 영문·ISO
    # 를 박아 두면 진짜 원장에서 **모든 질의가 빈다.** 그리고 빈 결과는
    # '원장에 없습니다' 로 나간다 — 코드가 틀렸다는 말이 아니라.

    def _reads_the_real_ledger_dialect():
        con = _synth(effect=-0.02, seed=5)
        d = con.execute("SELECT date, market FROM price_daily LIMIT 1").fetchone()
        _assert(len(str(d[0])) == 8 and str(d[0]).isdigit(), d[0])
        _assert(str(d[1]) == "코스닥", d[1])
        r = run(con, "ritter1991", market="KOSDAQ", at="2026-09-18")
        con.close()
        _assert(r["universe"] == "코스닥", r["universe"])   # 해소된 이름을 적는다
        _assert(r["observed"] is not None, r["reason"])
    check("원장이 한글·YYYYMMDD 여도 읽는다", _reads_the_real_ledger_dialect)

    def _list_date_compact():
        """KRX LIST_DD 는 `20170102` 다. 3.10 의 fromisoformat 은 이것을
        못 읽고, 그러면 전 종목이 조용히 빠진다."""
        _assert(_parse_list_date("20170102").isoformat() == "2017-01-02")
        _assert(_parse_list_date("2017-01-02").isoformat() == "2017-01-02")
        _assert(_parse_list_date("") is None)
        _assert(_parse_list_date(None) is None)
        _assert(_parse_list_date("2017/01/02") is None)   # 지어내지 않는다
        _assert(_parse_list_date("20171332") is None)     # 없는 날
    check("상장일을 너그럽게, 그러나 지어내지 않고 읽는다", _list_date_compact)

    def _calendar_time_needs_enough_names():
        """달 수만 보면 세 종목짜리 포트폴리오도 36개월을 채운다. 그때 나오는
        t 는 그 세 종목 이야기이지 논문 주장의 재현이 아니다."""
        con = _synth(effect=-0.02, names=3, years=9, seed=3)
        r = run(con, "ritter1991", at="2026-09-18")
        con.close()
        _assert(r["verdict"] == R.VERDICT_NONE, r)
        _assert(r["observed"] is None, r)
        _assert(str(MIN_EVENTS) in (r["reason"] or ""), r["reason"])
    check("달력시간도 최소 종목 수를 건다", _calendar_time_needs_enough_names)

    for f in failed:
        print("  X  " + f, file=sys.stderr)
    print(f"eventstudy {passed} passed, {len(failed)} failed")
    return 1 if failed else 0


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="이벤트 시간 러너 (결정적)")
    ap.add_argument("--selftest", action="store_true")
    ap.add_argument("--paper")
    ap.add_argument("--market", default="KOSDAQ")
    ap.add_argument("--db")
    ap.add_argument("--indent", type=int, default=2)
    a = ap.parse_args()
    if not a.paper:
        sys.exit(selftest())
    import ki_ledger_mcp as M                             # noqa: E402
    try:
        con = sqlite3.connect(f"file:{a.db}?mode=ro", uri=True) if a.db else M.open_ledger()
    except M.Denied as e:
        print(M._scrub(e), file=sys.stderr)
        sys.exit(1)
    con.row_factory = sqlite3.Row
    try:
        print(json.dumps(run(con, a.paper, a.market), ensure_ascii=False,
                         indent=a.indent))
    finally:
        con.close()
