"""상장 포트폴리오사 주가 모니터링 — 사건이 없어도 매일 잰다.

트리거는 **하루** 변동만 봤다 (`MOVE_PCT = 8.0`). 그래서 천천히 빠지는 종목이
통째로 안 보였다. 재 봤다 —

    6개월 누적        -58.1%
    최악의 하루       -3.6%      (임계 ±8.0%)
    거래대금 20일평균  -79%
    발동한 트리거      0건

반토막이 나고 유동성이 마르는 동안 데스크가 한 번도 안 불렸다. 그리고 이쪽이
회수 판단이 가장 필요한 경우다 — 하루에 8% 빠지는 날은 이미 늦은 날이고,
천천히 빠지는 구간은 아직 팔 수 있는 구간이다.

이 모듈은 **재기만 한다** (규칙 1). 낙폭이 크다고 '위험'이라 쓰지 않고, 거래
대금이 줄었다고 '처분 불가'라 쓰지 않는다. 그 판단은 데스크가 하고, 최종
결정은 회의가 한다. 여기서 나가는 것은 측정값과 그 한계다.

임계는 **사내 운영 기준**이다 (규칙 4 의 '사내'). 논문도 제도도 아니다 —
근거는 "그 값을 넘으면 회수 계획의 전제가 달라진다"는 것뿐이고, 그렇게 적는다.

    python agents/watch.py --db ki.sqlite
"""
from __future__ import annotations

import argparse
import json
import sqlite3
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import dialect as D                                      # noqa: E402
import scope as SC                                       # noqa: E402

SCHEMA = "ki.watch/1"

# ── 창 (영업일) ───────────────────────────────────────────────────────
W_1W, W_1M, W_3M, W_6M, W_52W = 5, 21, 63, 126, 252

# 최근 유동성을 재는 창과, 그 직전 비교 구간.
LIQ_NEAR, LIQ_BASE = 20, 60

# 임계를 넘은 **그날** 부르고, 넘은 채로 있는 동안은 다시 부르지 않는다.
# 이것이 없으면 3개월 -30% 인 종목이 분기 내내 매일 두 데스크를 부른다 —
# 한 종목에 126번이다. 매일 울리는 경보는 아무도 읽지 않는다.
# 표는 매일 보인다. 다시 보는 몫은 표가 하고, 소집은 넘는 순간이 한다.
RECROSS_D = 5

# ── 사내 운영 기준 ────────────────────────────────────────────────────
#
# 논문도 제도도 아니다. 근거는 하나씩 적는다 — 근거 없는 임계는 숫자가 아니라
# 취향이고, 취향은 회의에서 다투기만 한다.

# 하루 변동 임계. `triggers.MOVE_PCT` 와 **같은 값이어야** 한다 — why 문구가
# "하루 변동으로는 안 걸린다" 고 말할 때 기준이 되는 값이고, 두 곳에서 따로
# 정하면 그 문장이 조용히 거짓이 된다. 가져오지 못하면 기본값을 쓴다.
try:
    import triggers as _T                                # noqa: PLC0415
    MOVE_PCT_REF = float(_T.MOVE_PCT)
except Exception:                                        # noqa: BLE001
    MOVE_PCT_REF = 8.0

# 3개월 누적 낙폭. 하루 -8% 한 번과 같은 무게로 볼 만한 크기이고, 이 정도면
# 회수 계획에 적어 둔 목표 회수액 자체를 다시 계산해야 한다.
DRIFT_PCT = -25.0

# 최근 20일 평균 거래대금이 직전 60일의 절반 이하. 처분 소요일수가 두 배가
# 된다는 뜻이다 — 계획의 '며칠 안에 판다'가 그대로 두 배가 된다.
LIQ_RATIO = 0.5


def _cols(con) -> set:
    try:
        return {r[1] for r in con.execute("PRAGMA table_info(price_daily)")}
    except sqlite3.Error:
        return set()


def _bars(con, code: str, at: str = None, limit: int = W_52W + 5) -> tuple:
    """한 종목의 일봉. `(거래된 날, 정지 추정일 수, 시장)`.

    **수정주가를 쓴다.** `ki_monitor.price_panel` 이 `adj_factor` 를 곱하는
    것과 같은 이유다 — 5:1 액면분할을 원주가로 읽으면 하루에 -80% 가 되고,
    그 가짜 낙폭이 데스크를 부른다.

    **시장으로 거르지 않는다.** KRX 종목코드 6자리는 시장 사이에서 유일하고,
    워치리스트는 시장을 적지 않는다. 시장으로 거르면 코스피 보유분이 통째로
    안 보인다 — 빈 결과가 "원장에 없습니다" 로 나가 자료 탓이 된다.

    **기준일 이후는 보지 않는다.** `at` 을 무시하면 1월 기준으로 물어도 7월
    자료가 1월이라고 적혀 나가고, 되짚기가 성립하지 않는다."""
    have = _cols(con)
    if "close" not in have:
        return [], 0, None
    adj = ("close * COALESCE(adj_factor, 1.0)" if "adj_factor" in have
           else "close")
    val = "value" if "value" in have else "NULL"
    mkt = "market" if "market" in have else "NULL"
    q = (f"SELECT date, {adj} AS close, {val} AS value, {mkt} AS market "
         f"FROM price_daily WHERE code = ?")
    p = [code]
    if at:
        q += f" AND {D.sql_date('date')} <= ?"
        p.append(D.norm_date(at))
    q += f" ORDER BY {D.sql_date('date')} DESC LIMIT ?"
    p.append(limit)
    try:
        rows = con.execute(q, p).fetchall()
    except sqlite3.Error:
        return [], 0, None
    market = next((r["market"] for r in rows if r["market"]), None)
    out, halted = [], 0
    for r in rows:
        c = r["close"]
        # 종가가 없는 날은 거래정지로 **추정**한다. 단정하지 않는다 — 원장은
        # 정지 사유를 담지 않는다. 다만 세지 않고 버리면 "20일 중 16일 정지"
        # 가 "평소처럼 거래됐다" 로 읽힌다.
        if c is None or c <= 0:
            halted += 1
            continue
        out.append({"date": D.iso_date(r["date"]), "close": float(c),
                    "value": r["value"]})
    out.reverse()
    return out, halted, market


def _ret(bars: list, n: int):
    """n영업일 전 대비 수익률(%). 자료가 모자라면 None — 0 이 아니다."""
    if len(bars) < n + 1:
        return None
    a, b = bars[-(n + 1)]["close"], bars[-1]["close"]
    if not a or not b or a <= 0:
        return None
    return round((b / a - 1.0) * 100.0, 2)


def _mean(vals: list):
    """거래대금 평균. **0 인 날을 버리지 않는다.**

    버리면 20일 중 16일이 정지였는데 "평소처럼 거래됐다" 로 읽힌다. 0 도
    잰 값이다 (규칙 3). 값 자체가 없는 날(None)만 뺀다."""
    v = [float(x) for x in vals if x is not None]
    return (sum(v) / len(v)) if v else None


def measure(con, code: str, at: str = None, name: str = None) -> dict:
    """한 종목의 주가 상태. **판정하지 않는다** — 측정값과 사유뿐이다."""
    row = {"schema": SCHEMA, "code": code, "name": name, "market": None,
           "asof": None, "close": None, "ret": {}, "drawdown_pct": None,
           "low_52w": None, "liquidity": {}, "n_bars": 0, "n_halted": 0,
           "reason": None,
           "limits": [
               "종가 기준입니다. 장중 값이 아닙니다.",
               "거래정지·유상증자 권리락 등은 보정하지 않았습니다 — "
               "수익률이 그 사건을 그대로 반영합니다.",
               "거래대금은 평시 값입니다. 우리가 팔 때는 우리가 그 평시를 "
               "깹니다.",
           ]}
    bars, halted, market = _bars(con, code, at)
    row["n_bars"], row["n_halted"], row["market"] = len(bars), halted, market
    if halted:
        row["limits"].append(
            f"최근 {len(bars) + halted}영업일 중 {halted}일은 종가가 "
            f"없습니다 — 거래정지로 **추정**했을 뿐, 원장은 사유를 담지 "
            f"않습니다.")
    if not bars:
        row["reason"] = (f"{code} 의 일봉이 원장에 없습니다"
                         + (f" (종가 없는 날 {halted}일)" if halted else "")
                         + ". ingest 를 먼저 실행하십시오.")
        return row

    last = bars[-1]
    row["asof"], row["close"] = last["date"], last["close"]
    row["ret"] = {"1w": _ret(bars, W_1W), "1m": _ret(bars, W_1M),
                  "3m": _ret(bars, W_3M), "6m": _ret(bars, W_6M)}
    # 같은 값을 RECROSS_D 영업일 전 기준으로도 잰다. 임계를 **넘는 순간**만
    # 부르기 위해서다 — 넘은 채로 있는 동안 매일 부르면 아무도 안 읽는다.
    prior = bars[:-RECROSS_D] if len(bars) > RECROSS_D else []
    row["prior"] = {"ret_3m": _ret(prior, W_3M) if prior else None}

    # 창 안의 최악의 하루. why 문구가 "하루 변동으로는 안 걸린다" 고 단정하기
    # 전에 실제로 확인한다 — 확인 안 한 것을 적으면 그게 바로 이 시스템이
    # 막으려는 실패다.
    win = bars[-(W_3M + 1):]
    worst = None
    for i in range(1, len(win)):
        a0, b0 = win[i - 1]["close"], win[i]["close"]
        if a0 and a0 > 0:
            chg = (b0 / a0 - 1.0) * 100.0
            worst = chg if worst is None else min(worst, chg)
    row["worst_day_pct"] = None if worst is None else round(worst, 2)

    # 최고가 대비 낙폭. 창 안에서만 본다 — '사상 최고가'가 아니다.
    closes = [b["close"] for b in bars]
    row["low52_is_new"] = False
    if closes:
        peak = max(closes)
        if peak > 0:
            row["drawdown_pct"] = round((last["close"] / peak - 1.0) * 100.0, 2)
        row["low_52w"] = bool(len(bars) >= W_52W
                              and last["close"] <= min(closes))
        # 연일 신저가를 갱신하면 매일 부르게 된다. 직전 최저가 최근이면
        # 이미 부른 것으로 보고 넘긴다.
        if row["low_52w"]:
            head = closes[:-RECROSS_D] if len(closes) > RECROSS_D else []
            row["low52_is_new"] = bool(
                head and last["close"] <= min(head)
                and min(closes[-RECROSS_D:-1] or [float("inf")])
                > last["close"])

    # 비교 구간이 **온전히** 있을 때만 잰다. 짧은 원장에서 앞쪽을 잘라 쓰면
    # 신규 상장의 첫 주 거래대금이 기준이 되어, 비율이 0.06 같은 값으로
    # 나오고 매일 경보가 울린다.
    enough = len(bars) >= LIQ_NEAR + LIQ_BASE
    near = _mean([b["value"] for b in bars[-LIQ_NEAR:]]) if enough else None
    base = (_mean([b["value"] for b in bars[-(LIQ_NEAR + LIQ_BASE):-LIQ_NEAR]])
            if enough else None)
    row["liquidity"] = {
        "adv20": None if near is None else round(near, 1),
        "adv60_prior": None if base is None else round(base, 1),
        "ratio": (None if (near is None or not base)
                  else round(near / base, 3)),
        "why": (None if (near is not None and base) else
                (f"비교할 직전 구간이 모자랍니다 — 거래된 날이 "
                 f"{len(bars)}일이고 {LIQ_NEAR + LIQ_BASE}일이 필요합니다 "
                 f"(신규 상장이거나 원장이 짧습니다)")),
    }
    if len(bars) < W_3M + 1:
        row["reason"] = (f"일봉이 {len(bars)}개뿐입니다 — 3개월 수익률과 "
                         f"유동성 추세는 내지 못했습니다.")
    return row


def snapshot(con, at: str = None, portfolio: dict = None,
             market: str = None) -> dict:
    """상장 포트폴리오사 전부의 주가 상태. 사건이 없어도 매일 낸다.

    `market` 은 받지 않는 것이나 마찬가지다 — 종목마다 원장이 답한다."""
    pf = SC.portfolio() if portfolio is None else portfolio
    out = {"schema": SCHEMA, "at": at or date.today().isoformat(),
           "market": None,
           "scope": {"ok": bool(pf.get("ok")), "n_listed": int(pf.get("n") or 0),
                     "n_unlisted": int(pf.get("n_unlisted") or 0),
                     "why": pf.get("why")},
           "rows": [], "n": 0,
           # 여기에 금지어를 **부정문으로라도** 쓰지 않는다. 검사는 낱말을
           # 보므로 "…라 쓰지 않았습니다" 도 걸린다 — 같은 실수를 네 번째로
           # 했다. 하는 일을 적고, 안 하는 일은 이름을 부르지 않는다.
           "note": ("측정값입니다. 값의 크기를 등급이나 결론으로 옮기지 "
                    "않았습니다 — 그 판단은 데스크와 회의의 몫입니다."),
           "thresholds": {"drift_3m_pct": DRIFT_PCT, "liq_ratio": LIQ_RATIO,
                          "grade": "사내",
                          "why": ("논문도 제도도 아닌 사내 운영 기준입니다. "
                                  "넘으면 회수 계획의 전제가 달라진다는 "
                                  "뜻이고, 그 이상은 아닙니다.")}}
    if not pf.get("ok"):
        out["note"] = (f"**범위를 못 정한 날입니다** — {pf.get('why')} "
                       f"주가 모니터링을 하지 않았습니다. 조용한 날이 아닙니다.")
        return out

    # 시장으로 거르지 않는다. KRX 종목코드는 시장 사이에서 유일하고,
    # 워치리스트는 시장을 적지 않는다 — 거르면 코스피 보유분이 통째로
    # 안 보이고, 그 빈 결과가 "원장에 없습니다" 로 나간다.
    out["market"] = None
    for code in pf.get("codes") or []:
        out["rows"].append(measure(con, code, at=at))
    out["n"] = len(out["rows"])
    return out


def breaching(snap: dict) -> list:
    """**지금** 사내 기준을 넘고 있는 것. 상태이지 사건이 아니다.

    `findings` 는 넘는 **순간**만 낸다. 둘을 구분하지 않으면 표에 -30.6% 가
    찍혀 있는데 아래에는 "기준을 넘은 것 없음" 이라고 적히고, 읽는 사람은
    그 모순을 자기가 잘못 본 것으로 넘긴다."""
    out = []
    for r in snap.get("rows") or []:
        d3 = (r.get("ret") or {}).get("3m")
        if d3 is not None and d3 <= DRIFT_PCT:
            out.append({"code": r["code"], "kind": "price.drift",
                        "value": d3, "unit": "percent"})
        liq = r.get("liquidity") or {}
        if liq.get("ratio") is not None and liq["ratio"] <= LIQ_RATIO \
                and not liq.get("why"):
            out.append({"code": r["code"], "kind": "liquidity.dry",
                        "value": liq["ratio"], "unit": "ratio"})
        if r.get("low_52w"):
            out.append({"code": r["code"], "kind": "price.low52",
                        "value": r.get("close"), "unit": "KRW"})
    return sorted(out, key=lambda x: (x["code"], x["kind"]))


def findings(snap: dict) -> list:
    """임계를 **넘는 순간**의 소집 사유. 판정이 아니다.

    넘은 채로 있는 동안은 다시 내지 않는다. 그러지 않으면 3개월 -30% 인
    종목이 분기 내내 매일 두 데스크를 부른다 — 한 종목에 126번이다. 표는
    매일 보이므로 다시 보는 몫은 표가 하고, 소집은 넘는 순간이 한다."""
    out = []
    for r in snap.get("rows") or []:
        code = r["code"]
        prior = r.get("prior") or {}

        d3 = (r.get("ret") or {}).get("3m")
        was = prior.get("ret_3m")
        if d3 is not None and d3 <= DRIFT_PCT and not (
                was is not None and was <= DRIFT_PCT):
            worst = r.get("worst_day_pct")
            # 확인한 것만 적는다. 하루 변동으로도 걸렸을 구간이면 그렇게 쓴다.
            tail = ("하루 변동 임계로는 걸리지 않는 구간입니다."
                    if worst is None or abs(worst) < MOVE_PCT_REF
                    else f"이 구간에는 하루 {worst:+.1f}% 인 날도 있었습니다.")
            out.append({
                "kind": "price.drift", "code": code, "asof": r["asof"],
                "value": d3, "unit": "percent",
                "why": (f"3개월 누적 {d3:+.1f}% 로 사내 기준 "
                        f"{DRIFT_PCT:+.0f}% 를 넘었습니다. {tail}"),
            })

        liq = r.get("liquidity") or {}
        ratio = liq.get("ratio")
        if ratio is not None and ratio <= LIQ_RATIO and not liq.get("why"):
            out.append({
                "kind": "liquidity.dry", "code": code, "asof": r["asof"],
                "value": ratio, "unit": "ratio",
                "why": (f"최근 {LIQ_NEAR}일 평균 거래대금이 직전 {LIQ_BASE}일의 "
                        f"{ratio:.2f}배입니다 (사내 기준 {LIQ_RATIO}). "
                        f"처분 소요일수의 전제가 달라집니다."),
            })

        if r.get("low_52w") and r.get("low52_is_new"):
            out.append({
                "kind": "price.low52", "code": code, "asof": r["asof"],
                "value": r.get("close"), "unit": "KRW",
                "why": (f"52주 최저 종가입니다 (원장에 있는 구간 기준). "
                        f"직전 최저는 {RECROSS_D}영업일보다 전입니다."),
            })
    return sorted(out, key=lambda x: (x["code"], x["kind"]))


# ── 자체 검사 ─────────────────────────────────────────────────────────

def _con(rows) -> sqlite3.Connection:
    con = sqlite3.connect(":memory:")
    con.row_factory = sqlite3.Row
    con.execute("CREATE TABLE price_daily (date TEXT, code TEXT, market TEXT, "
                "close REAL, value REAL, PRIMARY KEY (date, code))")
    con.executemany("INSERT INTO price_daily VALUES (?,?,?,?,?)", rows)
    con.commit()
    return con


def _series(code="000660", n=140, start=10000.0, daily=-0.0055, val=3.0e8,
            val_daily=-0.012, market="KOSDAQ"):
    """진짜 원장의 형식으로 만든다 — 날짜 YYYYMMDD · price_daily.market 은 영문."""
    import pandas as pd
    days = pd.bdate_range("2026-01-02", periods=n)
    px, v, out = start, val, []
    for d in days:
        px *= (1 + daily)
        v *= (1 + val_daily)
        out.append((d.strftime("%Y%m%d"), code, market, px, max(v, 1e6)))
    return out


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

    def _pf(*codes, ok=True):
        return {"schema": "ki.scope/1", "ok": ok, "codes": list(codes),
                "n": len(codes), "n_unlisted": 0,
                "why": None if ok else "검사용 — 범위를 못 정한 날"}

    def _slow_bleed_is_caught():
        """하루 변동 임계로는 안 걸리는 구간을 잡는다.

        재 봤다 — 6개월 -58%, 최악의 하루 -3.6%, 트리거 0건. 반토막이 나는
        동안 아무도 안 봤다. 그리고 이쪽이 아직 팔 수 있는 구간이다."""
        rows = _series()
        con = _con(rows)
        cross = D.iso_date(rows[65][0])            # 3개월 창이 처음 서는 날
        snap = snapshot(con, at=cross, portfolio=_pf("000660"))
        con.close()
        r = snap["rows"][0]
        _assert(r["ret"]["3m"] is not None and r["ret"]["3m"] < DRIFT_PCT,
                r["ret"])
        _assert(abs(r["worst_day_pct"]) < MOVE_PCT_REF, r["worst_day_pct"])
        _assert({x["kind"] for x in findings(snap)} == {"price.drift"},
                findings(snap))
        # 확인한 것만 적는다
        _assert("하루 변동 임계로는 걸리지 않는" in findings(snap)[0]["why"])
    check("천천히 빠지는 구간을 잡는다", _slow_bleed_is_caught)

    def _crossed_once_is_not_called_daily():
        """넘은 채로 있는 동안 매일 부르지 않는다.

        이게 없으면 3개월 -30% 인 종목이 분기 내내 매일 두 데스크를 부른다 —
        한 종목에 126번이다. 매일 울리는 경보는 아무도 읽지 않는다.
        표는 그동안에도 매일 보인다."""
        rows = _series()
        con = _con(rows)
        fired = []
        for i in (65, 70, 90, 120):
            snap = snapshot(con, at=D.iso_date(rows[i][0]),
                            portfolio=_pf("000660"))
            fired.append(len(findings(snap)))
            # 소집은 멈춰도 표에는 계속 보인다
            _assert(snap["rows"][0]["ret"]["3m"] < DRIFT_PCT, i)
        con.close()
        _assert(fired == [1, 0, 0, 0], fired)
    check("한 번 넘으면 매일 부르지 않는다", _crossed_once_is_not_called_daily)

    def _split_is_not_a_crash():
        """액면분할을 원주가로 읽으면 하루에 -80% 가 되고, 그 가짜 낙폭이
        데스크를 부른다. `ki_monitor.price_panel` 이 adj_factor 를 곱하는
        것과 같은 이유로 여기서도 곱한다."""
        rows = _series(n=140, daily=0.0)
        con = _con(rows)
        con.execute("ALTER TABLE price_daily ADD COLUMN adj_factor REAL DEFAULT 1.0")
        # 마지막 20일에 5:1 분할 — 원주가는 1/5 이 되고 adj_factor 가 5 다
        cut = rows[-20][0]
        con.execute(f"UPDATE price_daily SET close = close / 5.0, "
                    f"adj_factor = 5.0 WHERE {D.sql_date('date')} >= ?", (cut,))
        con.commit()
        snap = snapshot(con, at=D.iso_date(rows[-1][0]),
                        portfolio=_pf("000660"))
        con.close()
        r = snap["rows"][0]
        _assert(abs(r["ret"]["3m"]) < 5.0, r["ret"])       # 분할은 낙폭이 아니다
        _assert(findings(snap) == [], findings(snap))
    check("액면분할을 폭락으로 읽지 않는다", _split_is_not_a_crash)

    def _halt_does_not_kill_the_day():
        """종가가 없는 날(거래정지 추정)이 하루치 소집 전체를 죽이면 안 된다.

        `None / peak` 하나가 TypeError 를 내면 그 예외가 scan → convene 까지
        올라가서, 한 종목이 정지됐다는 이유로 그날 아무도 소집되지 않는다."""
        rows = _series(n=140)
        con = _con(rows)
        con.execute("UPDATE price_daily SET close = NULL "
                    "WHERE date = (SELECT MAX(date) FROM price_daily)")
        con.commit()
        snap = snapshot(con, at=None, portfolio=_pf("000660"))
        con.close()
        r = snap["rows"][0]
        _assert(r["close"] is not None, r)             # 직전 거래일로 선다
        _assert(r["n_halted"] >= 1, r["n_halted"])
        _assert(any("거래정지로 **추정**" in x for x in r["limits"]), r["limits"])
    check("거래정지가 하루치 소집을 죽이지 않는다", _halt_does_not_kill_the_day)

    def _halted_days_are_counted_not_dropped():
        """0 거래대금을 버리면 '20일 중 16일 정지' 가 '평소처럼 거래됐다'
        로 읽힌다. 0 도 잰 값이다 (규칙 3)."""
        rows = _series(n=140, val_daily=0.0)
        con = _con(rows)
        con.execute("UPDATE price_daily SET value = 0 WHERE date IN "
                    "(SELECT date FROM price_daily ORDER BY date DESC LIMIT 16)")
        con.commit()
        snap = snapshot(con, at=None, portfolio=_pf("000660"))
        con.close()
        liq = snap["rows"][0]["liquidity"]
        _assert(liq["ratio"] is not None and liq["ratio"] < 0.5, liq)
        _assert({x["kind"] for x in findings(snap)} == {"liquidity.dry"},
                findings(snap))
    check("거래 없는 날을 버리지 않고 센다",
          _halted_days_are_counted_not_dropped)

    def _new_listing_does_not_ring_daily():
        """짧은 원장에서 앞쪽을 잘라 쓰면 신규 상장의 첫 주 거래대금이
        기준이 되어 비율이 0.06 같은 값으로 나오고 매일 울린다."""
        con = _con(_series(n=30, val_daily=-0.05))
        snap = snapshot(con, at=None, portfolio=_pf("000660"))
        con.close()
        liq = snap["rows"][0]["liquidity"]
        _assert(liq["ratio"] is None, liq)
        _assert(liq["why"] and "모자랍니다" in liq["why"], liq)
        _assert(findings(snap) == [], findings(snap))
    check("신규 상장이 매일 울리지 않는다", _new_listing_does_not_ring_daily)

    def _kospi_holding_is_visible():
        """워치리스트는 시장을 적지 않는다. 시장으로 거르면 코스피 보유분이
        통째로 안 보이고, 그 빈 결과가 '원장에 없습니다' 로 나간다."""
        con = _con(_series(market="KOSPI"))
        snap = snapshot(con, at=None, portfolio=_pf("000660"))
        con.close()
        r = snap["rows"][0]
        _assert(r["close"] is not None, r["reason"])
        _assert(r["market"] == "KOSPI", r["market"])
    check("코스피 보유분도 보인다", _kospi_holding_is_visible)

    def _at_is_respected():
        """기준일을 무시하면 1월로 물어도 7월 자료가 1월이라고 적혀 나가고,
        되짚기가 성립하지 않는다."""
        rows = _series(n=140)
        con = _con(rows)
        early = D.iso_date(rows[70][0])
        snap = snapshot(con, at=early, portfolio=_pf("000660"))
        con.close()
        _assert(snap["rows"][0]["asof"] == early, snap["rows"][0]["asof"])
        _assert(snap["at"] == early, snap["at"])
    check("기준일 이후를 보지 않는다", _at_is_respected)

    def _drying_liquidity_is_caught():
        """유동성은 따로 잰다. 임계마다 **진짜로 넘는 자료**로 재야 한다 —
        한 자료로 둘을 재려다 임계를 자료에 맞춰 낮추게 된다.

        0.5 는 최근 20일 평균이 직전 60일의 절반이라는 뜻이고, 완만한
        감소로는 안 걸린다(-1.2%/일 이면 0.60 이다). 걸리는 것은 마르는
        속도가 붙었을 때다."""
        con = _con(_series(val_daily=-0.030, daily=0.0))
        snap = snapshot(con, at="2026-07-20", portfolio=_pf("000660"))
        con.close()
        r = snap["rows"][0]
        _assert(r["liquidity"]["ratio"] <= LIQ_RATIO, r["liquidity"])
        _assert({x["kind"] for x in findings(snap)} == {"liquidity.dry"},
                findings(snap))
    check("마르는 유동성을 잡는다", _drying_liquidity_is_caught)

    def _gentle_liquidity_decline_does_not_fire():
        """완만한 감소로 매일 울리면 아무도 안 읽는다."""
        con = _con(_series(val_daily=-0.012, daily=0.0))
        snap = snapshot(con, at="2026-07-20", portfolio=_pf("000660"))
        con.close()
        _assert(0.5 < snap["rows"][0]["liquidity"]["ratio"] < 0.7,
                snap["rows"][0]["liquidity"])
        _assert(findings(snap) == [], findings(snap))
    check("완만한 감소로는 울리지 않는다",
          _gentle_liquidity_decline_does_not_fire)

    def _state_and_event_are_separate():
        """표에 -30.6% 가 찍혀 있는데 아래에 "넘은 것 없음" 이라고 적히면,
        읽는 사람은 그 모순을 자기가 잘못 본 것으로 넘긴다."""
        rows = _series()
        con = _con(rows)
        late = D.iso_date(rows[120][0])            # 넘은 지 한참 된 날
        snap = snapshot(con, at=late, portfolio=_pf("000660"))
        con.close()
        _assert(findings(snap) == [], findings(snap))          # 사건은 없다
        now = breaching(snap)
        _assert([x["kind"] for x in now] == ["price.drift"], now)  # 상태는 있다
        _assert(now[0]["value"] < DRIFT_PCT, now)
    check("지금 넘고 있는 것과 오늘 새로 넘은 것을 나눈다",
          _state_and_event_are_separate)

    def _calm_company_is_quiet():
        """잠잠한 종목은 잠잠해야 한다 — 매일 경보가 울리면 아무도 안 읽는다."""
        con = _con(_series(daily=0.0002, val_daily=0.0))
        snap = snapshot(con, at="2026-07-20", portfolio=_pf("000660"))
        con.close()
        _assert(findings(snap) == [], findings(snap))
    check("잠잠한 종목은 잠잠하다", _calm_company_is_quiet)

    def _no_judgement_words():
        """재기만 한다 (규칙 1). 판정 어휘가 섞이면 게이트 ① 이 반려한다."""
        con = _con(_series())
        snap = snapshot(con, at="2026-07-20", portfolio=_pf("000660"))
        con.close()
        blob = json.dumps(snap, ensure_ascii=False) + json.dumps(
            findings(snap), ensure_ascii=False)
        for w in ("매수", "매도", "추천", "목표가", "저평가", "고평가",
                  "비중확대", "위험합니다", "처분 불가"):
            _assert(w not in blob, w)
    check("판정 어휘를 쓰지 않는다", _no_judgement_words)

    def _missing_data_is_a_reason_not_a_zero():
        """자료가 모자라면 None 과 사유다. 0 으로 채우지 않는다 (규칙 3)."""
        con = _con(_series(n=10))
        snap = snapshot(con, at="2026-01-20", portfolio=_pf("000660"))
        con.close()
        r = snap["rows"][0]
        _assert(r["ret"]["3m"] is None and r["ret"]["6m"] is None, r["ret"])
        _assert(r["ret"]["1w"] is not None, r["ret"])
        _assert(r["reason"] and "일봉이 10개뿐" in r["reason"], r["reason"])
        _assert(r["liquidity"]["ratio"] is None, r["liquidity"])
        _assert(r["liquidity"]["why"], r["liquidity"])
    check("자료가 모자라면 0 이 아니라 사유를 낸다",
          _missing_data_is_a_reason_not_a_zero)

    def _unknown_code_says_so():
        con = _con(_series())
        snap = snapshot(con, at="2026-07-20", portfolio=_pf("999999"))
        con.close()
        r = snap["rows"][0]
        _assert(r["close"] is None and r["reason"], r)
        _assert("원장에 없습니다" in r["reason"], r["reason"])
    check("원장에 없는 종목은 사유를 낸다", _unknown_code_says_so)

    def _no_scope_is_not_a_quiet_day():
        """범위를 못 정한 날은 조용한 날이 아니다 (규칙 14)."""
        con = _con(_series())
        snap = snapshot(con, at="2026-07-20", portfolio=_pf(ok=False))
        con.close()
        _assert(snap["n"] == 0 and snap["rows"] == [], snap)
        _assert("범위를 못 정한" in snap["note"], snap["note"])
        _assert("조용한 날이 아닙니다" in snap["note"], snap["note"])
    check("범위를 못 정한 날을 조용한 날로 적지 않는다",
          _no_scope_is_not_a_quiet_day)

    def _thresholds_are_labelled_as_ours():
        """임계는 사내 기준이다. 논문·제도인 척하면 안 된다 (규칙 4)."""
        con = _con(_series())
        snap = snapshot(con, at="2026-07-20", portfolio=_pf("000660"))
        con.close()
        t = snap["thresholds"]
        _assert(t["grade"] == "사내", t)
        _assert("논문도 제도도 아닌" in t["why"], t)
    check("임계를 사내 기준으로 표시한다", _thresholds_are_labelled_as_ours)

    def _limits_are_never_empty():
        con = _con(_series())
        snap = snapshot(con, at="2026-07-20", portfolio=_pf("000660"))
        con.close()
        _assert(snap["rows"][0]["limits"], snap["rows"][0])
        _assert(any("평시" in x for x in snap["rows"][0]["limits"]))
    check("한계를 비워 두지 않는다", _limits_are_never_empty)

    def _low52_needs_a_full_year():
        """일 년 치가 없으면 '52주 신저가'라 부르지 않는다."""
        con = _con(_series(n=100))
        snap = snapshot(con, at="2026-05-20", portfolio=_pf("000660"))
        con.close()
        _assert(snap["rows"][0]["low_52w"] is False, snap["rows"][0])
    check("일 년 치가 없으면 52주 신저가라 하지 않는다",
          _low52_needs_a_full_year)

    def _reads_only():
        con = _con(_series())
        before = con.execute("SELECT COUNT(*) FROM price_daily").fetchone()[0]
        snapshot(con, at="2026-07-20", portfolio=_pf("000660"))
        after = con.execute("SELECT COUNT(*) FROM price_daily").fetchone()[0]
        con.close()
        _assert(before == after)
    check("원장을 읽기만 한다", _reads_only)

    for f in failed:
        print("  X  " + f, file=sys.stderr)
    print(f"watch      {passed} passed, {len(failed)} failed")
    return 1 if failed else 0


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="상장 포트폴리오사 주가 모니터링")
    ap.add_argument("--selftest", action="store_true")
    ap.add_argument("--db", help="원장 경로 (기본: ki_monitor 설정)")
    ap.add_argument("--market", default="KOSDAQ")
    ap.add_argument("--at")
    ap.add_argument("--json", action="store_true", help="표 대신 JSON")
    ap.add_argument("--indent", type=int, default=2)
    a = ap.parse_args()
    if a.selftest:
        sys.exit(selftest())

    import ki_ledger_mcp as M                             # noqa: E402
    try:
        con = (sqlite3.connect(f"file:{a.db}?mode=ro", uri=True)
               if a.db else M.open_ledger())
    except M.Denied as e:
        print(M._scrub(e), file=sys.stderr)
        sys.exit(1)
    con.row_factory = sqlite3.Row
    try:
        snap = snapshot(con, at=a.at, market=a.market)
        found = findings(snap)
    finally:
        con.close()

    if a.json:
        print(json.dumps({**snap, "findings": found}, ensure_ascii=False,
                         indent=a.indent))
        sys.exit(0)

    if not snap["scope"]["ok"]:
        print(snap["note"])
        sys.exit(1)
    mkts = sorted({r["market"] for r in snap["rows"] if r.get("market")})
    print(f"상장 포트폴리오사 주가 모니터링 — "
          f"{' · '.join(mkts) if mkts else '시장 미상'} · {snap['n']}곳 · "
          f"기준일 {snap['at']}")
    print("-" * 78)
    print(f"{'종목':<8}{'기준일':<12}{'종가':>10}{'1주':>8}{'1개월':>8}"
          f"{'3개월':>8}{'낙폭':>8}{'유동성':>8}")
    for r in snap["rows"]:
        g = lambda k: ("—" if r["ret"].get(k) is None       # noqa: E731
                       else f"{r['ret'][k]:+.1f}%")
        dd = "—" if r["drawdown_pct"] is None else f"{r['drawdown_pct']:+.1f}%"
        lq = r["liquidity"].get("ratio")
        print(f"{r['code']:<8}{r['asof'] or '—':<12}"
              f"{'' if r['close'] is None else format(r['close'], ',.0f'):>10}"
              f"{g('1w'):>8}{g('1m'):>8}{g('3m'):>8}{dd:>8}"
              f"{('—' if lq is None else f'{lq:.2f}x'):>8}")
        if r["reason"]:
            print(f"         ! {r['reason']}")
    print("-" * 78)
    # 상태와 사건을 나눠 적는다. 표에 -30.6% 가 찍혀 있는데 아래에 "넘은 것
    # 없음" 이라고 적으면, 읽는 사람은 그 모순을 자기가 잘못 본 것으로 넘긴다.
    now = breaching(snap)
    if now:
        print(f"지금 사내 기준을 넘고 있는 것 {len(now)}건 (상태)")
        for x in now:
            v = (f"{x['value']:+.1f}%" if x["unit"] == "percent"
                 else (f"{x['value']:.2f}x" if x["unit"] == "ratio"
                       else f"{x['value']:,.0f}원"))
            print(f"  · {x['code']} [{x['kind']}] {v}")
    else:
        print("지금 사내 기준을 넘고 있는 것 없음")
    if found:
        print(f"\n오늘 새로 넘은 것 {len(found)}건 — 판정이 아니라 소집 사유입니다")
        for x in found:
            print(f"  · {x['code']} [{x['kind']}] {x['why']}")
    else:
        print("\n오늘 새로 넘은 것 없음 — 넘은 채로 있는 동안은 다시 "
              "부르지 않습니다 (표에는 계속 보입니다)")
    print(f"\n{snap['note']}")
    sys.exit(0)
