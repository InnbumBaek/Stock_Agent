"""재현 러너 — 인용하기 전에 우리 데이터로 계산해 본다.

이 데스크가 다루는 것은 코스닥 소형주다. 논문 표본이 1970~90년대 미국 대형주
라면 그 결론은 **가설이지 근거가 아니다.** 그럴듯한 논문 한 편이 회의에서
근거처럼 읽히는 것을 막는 유일한 방법은, 그 주장을 우리 원장에 대고 한 번
계산해 보는 것이다.

**이것은 에이전트가 아니다.** 결정적 파이썬 코드다. 같은 원장·같은 구간이면
언제 돌려도 같은 판정이 나와야 한다. LLM 이 끼면 그 성질이 사라지고, 판정이
바뀐 것이 데이터가 바뀌어서인지 모형이 흔들려서인지 알 수 없게 된다.

읽기만 한다. 원장에 쓰지 않는다 (규칙 2).

    python agents/replication.py --selftest
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

import dialect as D                                     # noqa: E402

SCHEMA = "ki.replication/1"

# ── 유의 임계 ─────────────────────────────────────────────────────────
#
# t ≥ 3.0 이다. 2.0 이 아니다.
#
# 2.0 은 검정을 **한 번** 할 때의 값이다. 우리는 주 1회 논문을 들이고 한 편마다
# 여러 구간·여러 유니버스로 재현을 돌린다. 연 150회쯤 된다. 임계가 2.0 이면
# 아무 효과가 없는 팩터라도 우연히 통과하는 것이 연 7~8개 나온다. 그것들은
# "논문 근거 있음" 딱지를 달고 회의에 올라간다 — 이 시스템이 막으려고 만들어진
# 바로 그 실패다.
#
# Harvey, Liu and Zhu (2016), "…and the Cross-Section of Expected Returns",
# Review of Financial Studies 29(1), 5-68. doi:10.1093/rfs/hhv059
#   수백 개의 팩터가 발표된 뒤라면 다중검정 보정 후 t ≥ 3.0 을 요구해야
#   한다고 본다. 우리 사정은 그 논문의 사정보다 나쁘지 않다.
#
# 대가가 있다. 통과가 드물어진다. 그것이 의도다 — 이 관문은 통과시키려고
# 만든 것이 아니라 **가려내려고** 만든 것이다. 통과하지 못한 논문은 버려지지
# 않고 '미검증'으로 남아, 표시를 달고 인용된다.
T_MIN = 3.0
T_MIN_PAPER = "hlz2016"          # 장부: .papers.json / method_papers
NW_PAPER = "nw1987"              # 같은 곳

# 표본이 이보다 적으면 계산을 거부한다. 없는 값을 만들지 않는다 (규칙 3).
MIN_NAMES = 100          # 분위를 나누려면 종목이 이만큼은 있어야 한다
MIN_PERIODS = 36         # 월간 스프레드 36개 = 3년. 이보다 짧으면 t 가 무의미하다
QUANTILES = 5            # 5분위. Q5 - Q1 이 스프레드다

VERDICT_OK = "재현됨"
VERDICT_OPPOSITE = "방향 반대"
VERDICT_NONE = "판정 불가"


def newey_west_t(x: np.ndarray, lags: int | None = None) -> tuple[float, float, int]:
    """평균이 0 인가에 대한 Newey-West t. (t, se, lags) 를 낸다.

    월간 스프레드는 자기상관이 있다. 겹치는 구간, 지속되는 국면, 같은 종목이
    여러 달 같은 분위에 머무는 것 — 전부 관측을 부풀린다. 보통 표준오차를 쓰면
    t 가 과장되고, 과장된 t 로 임계를 올려 봐야 소용이 없다.

    Newey, W. K. and West, K. D. (1987), Econometrica 55(3), 703-708.
    시차는 Newey-West(1994) 의 경험식 floor(4*(T/100)^(2/9)) 를 쓴다."""
    x = np.asarray(x, dtype=float)
    x = x[np.isfinite(x)]
    T = x.size
    if T < 3:
        return float("nan"), float("nan"), 0
    if lags is None:
        lags = int(np.floor(4.0 * (T / 100.0) ** (2.0 / 9.0)))
    lags = max(0, min(lags, T - 1))

    d = x - x.mean()
    s = float(d @ d) / T                                # gamma_0
    for j in range(1, lags + 1):
        g = float(d[j:] @ d[:-j]) / T                   # gamma_j
        s += 2.0 * (1.0 - j / (lags + 1.0)) * g         # Bartlett 가중
    if s <= 0:
        return float("nan"), float("nan"), lags
    se = float(np.sqrt(s / T))
    return float(x.mean() / se), se, lags


def _monthly_panel(con: sqlite3.Connection, market: str,
                   start: str, end: str) -> pd.DataFrame:
    """월말 종가 패널. 원장에 있는 것만 쓴다 — 새로 받지 않는다."""
    df = pd.read_sql_query(
        "SELECT date, code, close, volume, value FROM price_daily "
        "WHERE market = ? AND date BETWEEN ? AND ? ORDER BY date",
        con, params=(market, start, end))
    if df.empty:
        return df
    df["date"] = pd.to_datetime(df["date"].map(D.norm_date), format="%Y%m%d")
    df = df.dropna(subset=["close"])
    df = df[df["close"] > 0]
    return df


def _index_returns(con: sqlite3.Connection, index_name: str,
                   start: str, end: str) -> pd.Series:
    """지수 일간 수익률. 없으면 빈 것을 낸다 — 0 으로 대신하지 않는다.

    받는 것은 **원장에 적힌 지수 이름**이다 (`dialect.resolve_index`). 여기에
    시장 별칭을 그대로 넣으면 질의가 늘 비고, 빈 결과가 '지수가 원장에
    없습니다' 로 나간다 — 코드가 틀렸다는 말이 아니라 자료 탓으로."""
    if not index_name:
        return pd.Series(dtype=float)
    try:
        idx = pd.read_sql_query(
            "SELECT date, close FROM index_daily WHERE index_name = ? "
            "AND date BETWEEN ? AND ? ORDER BY date",
            con, params=(index_name, start, end))
    except Exception:                                     # noqa: BLE001
        return pd.Series(dtype=float)
    if idx.empty:
        return pd.Series(dtype=float)
    s = pd.Series(idx["close"].to_numpy(dtype=float),
                  index=pd.to_datetime(idx["date"].map(D.norm_date),
                                       format="%Y%m%d"))
    return s.pct_change().dropna()


def _factor_amihud(g: pd.DataFrame) -> float:
    """Amihud 비유동성 — |일수익률| / 일거래대금."""
    c = g["close"].to_numpy(dtype=float)
    v = g["value"].to_numpy(dtype=float)
    if c.size < 15:
        return float("nan")
    r = np.abs(np.diff(c) / c[:-1])
    v = v[1:]
    ok = np.isfinite(r) & np.isfinite(v) & (v > 0)
    if ok.sum() < 10:
        return float("nan")
    return float(np.mean(r[ok] / v[ok]) * 1e6)


def _factor_ivol(g: pd.DataFrame, mkt: pd.Series) -> float:
    """고유변동성 — 그 달의 **일간** 수익률을 시장에 회귀하고 남은 잔차의 표준편차.

    논문은 Fama-French 3요인 잔차를 쓴다. 우리 원장에는 SMB·HML 이 없어서
    시장 하나로만 회귀한다(시장모형). 규모·가치 노출이 잔차에 남으므로 **같은
    양이 아니다** — 그 사실이 `limits` 에 적혀 나간다.

    월간 종가로 대용하지 않는 이유는 그것이 아예 다른 측정이기 때문이다. 일간을
    쓰면 빈도는 논문과 같고, 남는 차이는 요인 수 하나다."""
    c = g["close"].to_numpy(dtype=float)
    if c.size < 15:
        return float("nan")
    r = pd.Series(np.diff(c) / c[:-1], index=g["date"].to_numpy()[1:])
    m = mkt.reindex(r.index)
    ok = np.isfinite(r.to_numpy()) & np.isfinite(m.to_numpy())
    if ok.sum() < 12:
        return float("nan")
    y, x = r.to_numpy()[ok], m.to_numpy()[ok]
    vx = x.var()
    if not np.isfinite(vx) or vx <= 0:
        return float("nan")
    beta = float(np.cov(y, x, ddof=1)[0, 1] / vx)
    resid = y - (y.mean() - beta * x.mean()) - beta * x
    return float(resid.std(ddof=2)) if resid.size > 2 else float("nan")


def _factor_turnover(g: pd.DataFrame) -> float:
    v = g["volume"].to_numpy(dtype=float)
    v = v[np.isfinite(v)]
    return float(np.mean(v)) if v.size >= 10 else float("nan")


def _factor_mom_12_1(hist: pd.Series) -> float:
    """12-1 모멘텀. 최근 한 달은 뺀다 — 그 구간은 반대 방향이다."""
    if hist.size < 13:
        return float("nan")
    p_then, p_now = hist.iloc[-13], hist.iloc[-2]
    if not p_then:
        return float("nan")
    return float(p_now / p_then - 1.0)


def _factor_high52(hist: pd.Series) -> float:
    """52주 신고가 근접도 — 지금 주가 / 최근 1년 최고가.

    **논문과 같지 않다.** George·Hwang 은 일간 종가 기준 52주 최고가를 쓴다.
    여기서는 월말 종가 13개의 최고값으로 대용했다. 월중 고점이 빠지므로
    근접도가 과대평가되고, 그만큼 분위가 위로 쏠린다. 이 사실이 `limits` 에
    적혀 나가지 않으면 이 값은 논문 값인 척하게 된다."""
    if hist.size < 13:
        return float("nan")
    hi = float(hist.iloc[-13:].max())
    if not hi:
        return float("nan")
    return float(hist.iloc[-1] / hi)


def _factor_rev_1m(hist: pd.Series) -> float:
    if hist.size < 2 or not hist.iloc[-2]:
        return float("nan")
    return float(hist.iloc[-1] / hist.iloc[-2] - 1.0)


# ── 검정 가능한 주장 ──────────────────────────────────────────────────
#
# 논문에서 **방향이 있는 한 문장**을 뽑아 둔 것이다. 환원되지 않는 주장은
# 재현 대상이 아니다. sign 은 "그 팩터가 높은 분위가 이후 수익률이 더 높다"면
# +1, 더 낮다면 -1 이다.
CLAIMS: dict[str, dict] = {
    "amihud2002": {
        "factor": "amihud", "sign": +1,
        "claim": "비유동성이 높은 종목일수록 이후 수익률이 높다",
        "limits": ["논문 표본은 미국 상장주(NYSE) — 코스닥 외삽의 근거가 아니다",
                   "거래정지 구간을 제외하지 않았고 생존편의를 보정하지 않았다"],
    },
    "dnr1998": {
        "factor": "turnover", "sign": -1,
        "claim": "회전율이 낮은 종목일수록 이후 수익률이 높다",
        "limits": ["논문의 회전율은 유통주식수 대비다 — 여기서는 거래량으로 대용했다",
                   "대용이 성립한다는 근거는 우리 표본에서 확인하지 않았다"],
    },
    "jt1993": {
        "factor": "mom_12_1", "sign": +1,
        "claim": "과거 수익률이 높았던 종목이 이후에도 높다 (모멘텀)",
        "limits": ["논문 표본은 미국 대형주 — 코스닥 소형주에서 방향이 뒤집힌다는 보고가 많다",
                   "거래비용을 차감하지 않은 총수익 기준이다"],
    },
    "gh2004": {
        "factor": "high52", "sign": +1,
        "claim": "52주 최고가에 가까운 종목일수록 이후 수익률이 높다",
        "limits": ["논문은 일간 종가 기준 52주 최고가를 쓴다 — 여기서는 월말 종가 "
                   "13개의 최고값으로 대용했고, 월중 고점이 빠져 근접도가 "
                   "과대평가된다",
                   "논문 표본은 미국 상장주다. 코스닥에서 성립한다는 근거가 아니다"],
    },
    "ahxz2006": {
        "factor": "ivol", "sign": -1,
        "claim": "고유변동성이 높은 종목일수록 이후 수익률이 낮다",
        "limits": ["논문은 Fama-French 3요인 잔차를 쓴다 — 우리 원장에는 SMB·HML 이 "
                   "없어 시장 하나로만 회귀했다. 규모·가치 노출이 잔차에 남는다",
                   "논문 표본은 미국 상장주다. 코스닥에서 성립한다는 근거가 아니다",
                   "거래정지로 수익률이 0 으로 이어지는 구간을 제외하지 않았다 — "
                   "그 구간은 변동성을 실제보다 낮게 만든다"],
    },
    "j1990": {
        "factor": "rev_1m", "sign": -1,
        "claim": "직전 1개월 수익률이 낮았던 종목이 이후 수익률이 높다 (단기 반전)",
        "limits": ["호가 튕김(bid-ask bounce)이 반전의 일부를 만든다 — 분리하지 않았다"],
    },
}

_FACTOR_KIND = {"amihud": "cross", "turnover": "cross", "ivol": "cross_mkt",
                "mom_12_1": "hist", "rev_1m": "hist", "high52": "hist"}

# ── 재현 대상이 아닌 것 ───────────────────────────────────────────────
#
# 장부의 논문이 전부 '아직 재현 안 됨'으로 남아 있으면, 사이클이 밀리고 있는
# 것처럼 보인다. 실제로는 셋이 섞여 있고 셋은 뜻이 다르다.
#
#   · CLAIMS        지금 돌릴 수 있다
#   · NOT_A_FACTOR  분위 정렬로 검정할 물건이 아니다 — 앞으로도 아니다
#   · NEEDS_RUNNER  환원은 되는데 이 러너가 아직 못 한다
#
# 둘째와 셋째를 섞으면 "우리가 게을러서 안 한 것"과 "원래 이 관문의 대상이
# 아닌 것"이 구분되지 않는다.

NOT_A_FACTOR = {
    "roll1984": "유효 스프레드 **추정량**이다. 수익률 방향을 주장하지 않는다 — "
                "분위로 정렬해 초과수익을 볼 물건이 아니고, 검증은 다른 "
                "추정량·실측 체결가와 대조하는 방식이어야 한다.",
    "cs2012": "고가·저가로 스프레드를 재는 **추정량**이다. roll1984 와 같은 이유로 "
              "분위 검정 대상이 아니다.",
    "ac2000": "최적 집행 **모형**이다. '이렇게 팔면 비용이 최소'라는 규범적 주장이지 "
              "'이런 종목이 더 오른다'가 아니다.",
    "athl2005": "시장충격 함수의 **추정**이다. 우리가 빌려 쓰는 것은 제곱근이라는 "
                "형태이고, 그 형태는 분위 정렬로 검정되지 않는다.",
}

# 이벤트 시간으로 재는 것. 이 러너가 아니라 `agents/eventstudy.py` 가 돌린다.
EVENT_TIME = ("ritter1991", "fh2001")

# 환원은 되는데 아직 돌릴 러너가 없는 것. 지금은 비어 있다 — 새 논문이 들어와
# 여기 걸리면, '대상 아님'과 섞이지 않도록 사유를 적어 넣는다.
NEEDS_RUNNER: dict[str, str] = {}


def reducibility(key: str) -> tuple[str, str | None]:
    """이 논문을 어떤 러너로 검정하는가. (분류, 사유) 를 낸다.

    `testable` 은 이 파일의 분위 러너, `event_time` 은 `eventstudy.py` 다.
    둘을 한 칸에 넣으면 사이클이 어느 러너를 불러야 하는지 알 수 없다."""
    if key in CLAIMS:
        return "testable", None
    if key in EVENT_TIME:
        return "event_time", None
    if key in NOT_A_FACTOR:
        return "not_a_factor", NOT_A_FACTOR[key]
    if key in NEEDS_RUNNER:
        return "needs_runner", NEEDS_RUNNER[key]
    return "unclassified", ("검정 가능한 주장으로 환원할지, 애초에 분위 검정 "
                            "대상이 아닌지 아직 분류되지 않았습니다.")


def decide(mean: float, t: float, expected_sign: int,
           t_min: float = T_MIN) -> tuple[str, str | None]:
    """관측값에서 판정으로. 순수 함수다 — 원장도 난수도 타지 않는다.

    판정 규칙을 여기 한 곳에 모아 두는 이유는, 임계가 실제로 지켜지는지를
    표본 운에 기대지 않고 검사하기 위해서다. 합성 자료를 만들어 t 가 우연히
    2 와 3 사이에 떨어지기를 기다리는 검사는, 떨어지지 않는 날 조용히
    아무것도 검사하지 않는다."""
    if not (np.isfinite(t) and np.isfinite(mean)):
        return VERDICT_NONE, "t 를 계산할 수 없습니다"
    if abs(t) < t_min:
        return VERDICT_NONE, (f"|t| = {abs(t):.2f} 로 임계 {t_min} 에 미치지 못합니다. "
                              f"방향이 맞더라도 우연과 구분되지 않습니다.")
    if (1 if mean > 0 else -1) == expected_sign:
        return VERDICT_OK, None
    return VERDICT_OPPOSITE, ("우리 표본에서는 논문과 반대 방향으로 유의합니다. "
                              "재현 실패도 측정 결과입니다 — 지우지 않고 남깁니다.")


def run(con: sqlite3.Connection, key: str, market: str = "KOSDAQ",
        start: str = "1900-01-01", end: str = "2999-12-31",
        t_min: float = T_MIN, at: str = None) -> dict:
    """한 논문의 주장 하나를 원장에 대고 계산한다.

    낼 것은 판정과 **그 판정이 선 조건**이다. 구간이 바뀌면 판정이 바뀔 수
    있고, 그 변화 자체가 신호다."""
    spec = CLAIMS.get(key)
    # 판정한 날은 **분석 기준일**이지 벽시계가 아니다. 벽시계를 박으면 같은
    # 원장을 다른 날 다시 돌린 기록이 구분되지 않고, 재생이 성립하지 않는다.
    out = {
        "schema": SCHEMA, "paper": key, "at": at or date.today().isoformat(),
        "universe": market, "verdict": VERDICT_NONE, "claim": None,
        "window": None, "n": 0, "periods": 0, "observed": None,
        "t_min": t_min, "t_min_paper": T_MIN_PAPER, "se_paper": NW_PAPER,
        "reason": None,
    }
    if not spec:
        out["reason"] = f"{key!r} 에 대해 검정 가능한 주장이 등록돼 있지 않습니다"
        return out
    out["claim"] = spec["claim"]

    # 원장이 쓰는 말로 바꾼다. 짐작하면 질의가 비고, 빈 결과는 '자료가 없다'
    # 로 나간다 — 코드가 틀렸다는 말이 아니라.
    mkt_name, why = D.resolve_market(con, market)
    if mkt_name is None:
        out["reason"] = why
        return out
    out["universe"] = mkt_name
    style = D.date_style(con)
    lo, hi = D.as_ledger_date(start, style), D.as_ledger_date(end, style)

    df = _monthly_panel(con, mkt_name, lo, hi)
    if df.empty:
        out["reason"] = (f"원장에 {mkt_name} 일봉이 없습니다 "
                         f"(구간 {start}..{end})")
        return out

    df["ym"] = df["date"].dt.to_period("M")
    months = sorted(df["ym"].unique())
    if len(months) < MIN_PERIODS + 13:
        out["reason"] = (f"월 수가 {len(months)}개입니다 — "
                         f"{MIN_PERIODS + 13}개 이상이 필요합니다")
        return out

    # 월말 종가 (이후 수익률 계산용)
    px = (df.sort_values("date").groupby(["ym", "code"])["close"].last()
            .unstack("code").sort_index())
    fwd = px.shift(-1) / px - 1.0                       # 다음 달 수익률

    kind = _FACTOR_KIND[spec["factor"]]
    if kind == "cross_mkt":
        idx_name, why_idx = D.resolve_index(con, mkt_name)
        mkt = _index_returns(con, idx_name, lo, hi)
        if mkt.empty:
            # 사유는 두 겹이다 — 무엇이 없었는지(원장이 가진 이름을 함께)와,
            # 그래서 무엇을 못 했는지. 뒤엣것이 빠지면 읽는 사람이 이 값을
            # 0 으로 채워도 되는 줄 안다.
            detail = why_idx or (f"{idx_name} 지수가 원장에 없습니다 "
                                 f"(구간 {start}..{end})")
            out["reason"] = f"{detail} — 잔차를 만들 기준선이 없습니다"
            return out
        fn = {"ivol": _factor_ivol}[spec["factor"]]
        sig = (df.groupby(["ym", "code"])
                 .apply(lambda g: fn(g, mkt), include_groups=False)
                 .unstack("code").reindex(index=px.index, columns=px.columns))
    elif kind == "cross":
        fn = {"amihud": _factor_amihud, "turnover": _factor_turnover}[spec["factor"]]
        sig = (df.groupby(["ym", "code"]).apply(fn, include_groups=False)
                 .unstack("code").reindex(index=px.index, columns=px.columns))
    else:
        fn = {"mom_12_1": _factor_mom_12_1, "rev_1m": _factor_rev_1m,
              "high52": _factor_high52}[spec["factor"]]
        need = {"mom_12_1": 13, "high52": 13}.get(spec["factor"], 2)
        rows = {}
        for i in range(len(px.index)):
            if i + 1 < need:
                continue
            w = px.iloc[max(0, i + 1 - need):i + 1]
            rows[px.index[i]] = w.apply(lambda c: fn(c.dropna()), axis=0)
        sig = pd.DataFrame(rows).T.reindex(index=px.index, columns=px.columns)

    spreads, names = [], []
    for ym in px.index:
        s, f = sig.loc[ym], fwd.loc[ym]
        ok = s.notna() & f.notna()
        n = int(ok.sum())
        if n < MIN_NAMES:
            continue
        s, f = s[ok], f[ok]
        # 동값이 많으면 분위가 무너진다. rank 로 잘라 균등하게 나눈다.
        q = pd.qcut(s.rank(method="first"), QUANTILES, labels=False)
        hi, lo = f[q == QUANTILES - 1].mean(), f[q == 0].mean()
        if np.isfinite(hi) and np.isfinite(lo):
            spreads.append(float(hi - lo))
            names.append(n)

    out["periods"] = len(spreads)
    out["n"] = int(np.median(names)) if names else 0
    if len(spreads) < MIN_PERIODS:
        out["reason"] = (f"유효한 월이 {len(spreads)}개입니다 — {MIN_PERIODS}개 이상이 "
                         f"필요합니다 (종목 {MIN_NAMES}개 이상인 달만 셉니다)")
        return out

    arr = np.array(spreads, dtype=float)
    t, se, lags = newey_west_t(arr)
    mean = float(arr.mean())
    out["window"] = f"{px.index[0]}..{px.index[-1]}"
    out["observed"] = {
        "spread_mean_bp": round(mean * 1e4, 1),
        "t": None if not np.isfinite(t) else round(float(t), 2),
        "se_bp": None if not np.isfinite(se) else round(se * 1e4, 1),
        "nw_lags": lags, "periods": len(spreads),
        "expected_sign": spec["sign"],
    }

    out["verdict"], out["reason"] = decide(mean, t, spec["sign"], t_min)
    out["limits"] = list(spec["limits"])
    return out


# ── 자체 검사 ─────────────────────────────────────────────────────────

# 합성 원장이 쓸 시장 이름. 진짜 원장이 쓰는 값이다 — 영문을 박으면 검사가
# 자기 가정을 다시 확인할 뿐이다.
_MKT = D.MARKET_ALIASES["KOSDAQ"][0]


def _synthetic(effect: float = 0.0, months: int = 72, names: int = 200,
               seed: int = 7, ivol_spread: float = 0.0) -> sqlite3.Connection:
    """합성 원장. 키도 네트워크도 쓰지 않는다.

    effect 는 '팩터 상위 분위가 다음 달에 더 버는 정도'다. 0 이면 아무 효과가
    없는 세계 — 거기서 통과가 나오면 그 관문은 쓸모가 없다.

    **진짜 원장의 형식으로 만든다** — 날짜는 `YYYYMMDD`, 시장과 지수는 한글
    (`dialect` 참고). 여기서 `"2019-01-01"` · `"KOSDAQ"` 으로 만들면 검사가
    자기 가정을 다시 확인할 뿐이고, 진짜 원장에서는 모든 질의가 빈다."""
    rng = np.random.default_rng(seed)
    con = sqlite3.connect(":memory:")
    con.row_factory = sqlite3.Row
    con.execute("CREATE TABLE price_daily (date TEXT, code TEXT, market TEXT, "
                "close REAL, volume REAL, value REAL, PRIMARY KEY (date, code))")
    con.execute("CREATE TABLE index_daily (date TEXT, index_name TEXT, "
                "close REAL, PRIMARY KEY (date, index_name))")
    codes = [f"{i:06d}" for i in range(1, names + 1)]
    # 종목마다 고정된 비유동성 수준을 준다 — 분위가 달마다 뒤집히지 않도록.
    level = rng.uniform(0.5, 2.0, size=names)
    order = np.argsort(level)                    # 낮은 것부터
    rank = np.empty(names); rank[order] = np.linspace(-0.5, 0.5, names)

    # effect 는 '월간' 알파다. 극단 분위가 달마다 effect/2 만큼 더/덜 번다.
    drift = effect * rank / 21.0
    px = np.full(names, 10000.0)
    mkt = 1000.0
    rows, irows = [], []
    days = pd.bdate_range("2019-01-01", periods=months * 21)
    for d in days:
        # 공통 요인 하나와 종목 고유 잡음. ivol 은 그 고유 잡음의 크기다.
        mr = rng.normal(0.0002, 0.008)
        mkt *= (1.0 + mr)
        idio = rng.normal(0.0, 0.02, size=names) * (1.0 + ivol_spread * rank)
        r = mr + idio + drift
        px = np.maximum(px * (1.0 + r), 100.0)
        vol = rng.lognormal(10.0, 0.5, size=names)
        # 거래대금이 작을수록 Amihud 가 크다 — level 이 높은 종목을 작게 준다.
        #
        # 주가를 곱하지 않는다. 곱하면 알파가 실린 종목의 주가가 불어나면서
        # 거래대금이 함께 불어나고, 몇 해 지나면 비유동성 순위가 통째로
        # 뒤집힌다. 실제 시장에서는 맞는 이야기지만, 여기서 재려는 것은
        # 러너가 주어진 순위를 제대로 읽는가이지 그 되먹임이 아니다.
        val = 1.0e4 * vol / level
        ds = d.strftime("%Y%m%d")                # KRX BAS_DD 그대로
        irows.append((ds, D.BENCHMARK, float(mkt)))
        rows += [(ds, codes[i], _MKT, float(px[i]), float(vol[i]), float(val[i]))
                 for i in range(names)]
    con.executemany("INSERT INTO price_daily VALUES (?,?,?,?,?,?)", rows)
    con.executemany("INSERT INTO index_daily VALUES (?,?,?)", irows)
    con.commit()
    return con


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

    def _at_is_the_analysis_date():
        """판정일은 분석 기준일이다 — 벽시계를 박으면 재생이 성립하지 않는다."""
        con = _synthetic(effect=0.03, seed=5)
        a = run(con, "amihud2002", at="2026-09-11")
        b = run(con, "amihud2002", at="2027-10-01")
        con.close()
        _assert(a["at"] == "2026-09-11" and b["at"] == "2027-10-01")
        _assert(a != b)                     # 같은 원장이어도 기록이 구분된다
        _assert(a["observed"] == b["observed"])   # 다만 관측값은 같아야 한다
    check("판정일은 분석 기준일이다", _at_is_the_analysis_date)

    check("임계는 3.0 이다 (다중검정 보정)",
          lambda: _assert(T_MIN == 3.0 and T_MIN_PAPER == "hlz2016"))

    def _thresholds_are_cited():
        """임계와 추정량이 실재하는 논문을 인용하는가 (규칙 4).

        숫자만 적어 두면 근거 없는 상수가 된다. 장부에 실재해야 하고, 그 논문이
        **주장하지 않는 것**도 함께 있어야 한다."""
        import papers as P
        if not P.LEDGER.exists():
            return
        d = P.load()
        for k in (T_MIN_PAPER, NW_PAPER):
            _assert(k in P.method_papers(d), f"{k} 가 장부에 없습니다")
            _assert(P.method_cite(d, k), k)
            _assert(P.method_papers(d)[k]["limits"], k)
    check("임계와 추정량이 실재하는 논문을 인용한다", _thresholds_are_cited)

    def _nw_basic():
        rng = np.random.default_rng(1)
        x = rng.normal(0.0, 1.0, 400)
        t, se, lags = newey_west_t(x)
        _assert(abs(t) < 3.0)                   # 평균 0 인 잡음은 유의하지 않다
        _assert(se > 0 and lags >= 1)
    check("Newey-West: 잡음은 유의하지 않다", _nw_basic)

    def _nw_shift():
        rng = np.random.default_rng(1)
        x = rng.normal(0.0, 1.0, 400) + 0.5
        t, _, _ = newey_west_t(x)
        _assert(t > 5.0)                        # 확실한 평균 이동은 잡힌다
    check("Newey-West: 평균 이동은 잡힌다", _nw_shift)

    def _nw_autocorr():
        """자기상관이 있으면 t 가 작아져야 한다 — 그것이 이 추정량의 존재 이유다."""
        rng = np.random.default_rng(3)
        e = rng.normal(0, 1, 500)
        x = np.zeros(500)
        for i in range(1, 500):
            x[i] = 0.7 * x[i - 1] + e[i]        # AR(1)
        x = x + 0.3
        t_nw, se_nw, _ = newey_west_t(x)
        se_plain = x.std(ddof=1) / np.sqrt(x.size)
        _assert(se_nw > se_plain)
        _assert(abs(t_nw) < abs(x.mean() / se_plain))
    check("Newey-West: 자기상관을 보정해 t 를 줄인다", _nw_autocorr)

    def _nw_degenerate():
        t, se, _ = newey_west_t(np.ones(50))    # 분산 0
        _assert(not np.isfinite(t))
        t2, _, _ = newey_west_t(np.array([1.0, 2.0]))
        _assert(not np.isfinite(t2))            # 표본이 너무 적다
    check("Newey-West: 계산할 수 없으면 NaN 을 낸다 (0 을 내지 않는다)", _nw_degenerate)

    def _null_world():
        """효과가 없는 세계에서는 통과하지 않아야 한다."""
        con = _synthetic(effect=0.0, seed=11)
        r = run(con, "amihud2002")
        con.close()
        _assert(r["verdict"] != VERDICT_OK, f"효과 없는 세계에서 통과: {r}")
    check("효과가 없으면 재현되지 않는다", _null_world)

    def _real_effect():
        """효과가 뚜렷한 세계에서는 통과해야 한다 — 못 잡으면 관문이 아니라 벽이다."""
        con = _synthetic(effect=0.03, seed=5)
        r = run(con, "amihud2002")
        con.close()
        _assert(r["verdict"] == VERDICT_OK, f"뚜렷한 효과를 못 잡음: {r}")
        _assert(abs(r["observed"]["t"]) >= T_MIN)
        _assert(r["observed"]["expected_sign"] == 1)
    check("효과가 뚜렷하면 재현된다", _real_effect)

    def _opposite():
        """방향이 뒤집힌 세계는 '방향 반대'로 판정한다 — 조용히 버리지 않는다."""
        con = _synthetic(effect=-0.03, seed=5)
        r = run(con, "amihud2002")
        con.close()
        _assert(r["verdict"] == VERDICT_OPPOSITE, f"{r}")
        _assert(r["reason"] and "반대" in r["reason"])
    check("방향이 반대면 그렇게 판정한다", _opposite)

    def _threshold_binds():
        """임계가 실제로 판정을 가르는가.

        표본 운에 기대지 않는다. |t| 가 2 와 3 사이인 관측은 2.0 에서는 통과하고
        3.0 에서는 반려돼야 한다 — 이 한 칸이 이번에 정한 값의 전부다."""
        for t in (2.0, 2.31, 2.9, 2.999):
            _assert(decide(+0.01, t, +1, t_min=2.0)[0] == VERDICT_OK, f"t={t}")
            v, why = decide(+0.01, t, +1, t_min=3.0)
            _assert(v == VERDICT_NONE, f"t={t}")
            _assert("임계" in why, f"t={t}")
        # 3.0 이상은 양쪽에서 통과한다.
        for t in (3.0, 4.2, 9.9):
            _assert(decide(+0.01, t, +1, t_min=3.0)[0] == VERDICT_OK, f"t={t}")
        # 부호가 반대면 유의해도 재현이 아니다.
        _assert(decide(-0.01, -4.0, +1, t_min=3.0)[0] == VERDICT_OPPOSITE)
        _assert(decide(+0.01, +4.0, -1, t_min=3.0)[0] == VERDICT_OPPOSITE)
        # 유의하지 않으면 '방향 반대'조차 아니다 — 판정 불가다.
        _assert(decide(-0.01, -1.2, +1, t_min=3.0)[0] == VERDICT_NONE)
        # 계산 불가는 0 이 아니라 판정 불가다.
        _assert(decide(float("nan"), float("nan"), +1)[0] == VERDICT_NONE)
    check("임계가 실제로 판정을 가른다 (2.0 통과 · 3.0 반려)", _threshold_binds)

    def _thin_sample():
        """표본이 얇으면 계산을 거부한다. 없는 값을 만들지 않는다."""
        con = _synthetic(effect=0.03, months=20, names=200, seed=5)
        r = run(con, "amihud2002")
        con.close()
        _assert(r["verdict"] == VERDICT_NONE)
        _assert(r["reason"] and ("월" in r["reason"]))
        _assert(r["observed"] is None)
    check("구간이 짧으면 판정하지 않는다", _thin_sample)

    def _few_names():
        con = _synthetic(effect=0.03, months=72, names=40, seed=5)
        r = run(con, "amihud2002")
        con.close()
        _assert(r["verdict"] == VERDICT_NONE)
        _assert(r["reason"])
    check("종목이 적으면 분위를 나누지 않는다", _few_names)

    def _unknown_paper():
        con = _synthetic(months=60)
        r = run(con, "없는논문2099")
        con.close()
        _assert(r["verdict"] == VERDICT_NONE)
        _assert("등록" in (r["reason"] or ""))
    check("검정 가능한 주장이 없으면 판정하지 않는다", _unknown_paper)

    def _deterministic():
        """같은 원장·같은 구간이면 같은 판정. 이것이 깨지면 재현이 아니다."""
        a = _synthetic(effect=0.03, seed=5); ra = run(a, "amihud2002"); a.close()
        b = _synthetic(effect=0.03, seed=5); rb = run(b, "amihud2002"); b.close()
        _assert(ra["verdict"] == rb["verdict"])
        _assert(ra["observed"] == rb["observed"])
    check("두 번 돌리면 같은 결과가 나온다 (결정적)", _deterministic)

    def _reducibility_covers_the_ledger():
        """장부의 논문이 전부 분류돼 있는가.

        분류되지 않은 논문은 '아직 재현 안 됨'으로 보이지만, 실제로는 재현
        대상인지조차 정해지지 않은 것이다. 그 둘을 섞으면 사이클이 밀리고 있는
        정도를 잴 수 없다."""
        import papers as _P
        if not _P.LEDGER.exists():
            return
        unc = [k for k in (_P.load().get("papers") or {})
               if reducibility(k)[0] == "unclassified"]
        _assert(not unc, f"분류되지 않은 논문: {unc}")
    check("장부의 모든 논문이 분류돼 있다", _reducibility_covers_the_ledger)

    def _buckets_are_disjoint():
        sets = [set(CLAIMS), set(EVENT_TIME), set(NOT_A_FACTOR), set(NEEDS_RUNNER)]
        for i, a in enumerate(sets):
            for b in sets[i + 1:]:
                _assert(not (a & b), a & b)
        for d in (NOT_A_FACTOR, NEEDS_RUNNER):
            for k, why in d.items():
                _assert(why.strip() and len(why) > 30, k)   # 사유 없이 빼지 않는다
    check("네 분류가 겹치지 않고 사유가 있다", _buckets_are_disjoint)

    def _event_time_has_a_runner():
        """event_time 으로 분류한 논문은 실제로 돌릴 러너가 있어야 한다.

        분류만 바꿔 놓고 러너가 없으면, '대상 아님'을 '곧 할 것'으로 이름만
        바꾼 셈이 된다."""
        import eventstudy as ES
        for k in EVENT_TIME:
            _assert(k in ES.EVENT_CLAIMS, f"{k} 를 돌릴 러너가 없습니다")
    check("event_time 논문은 돌릴 러너가 있다", _event_time_has_a_runner)

    def _high52_proxy():
        """대용한 것은 대용했다고 적혀 있어야 한다."""
        _assert("대용" in " ".join(CLAIMS["gh2004"]["limits"]))
        con = _synthetic(effect=0.03, seed=5)
        r = run(con, "gh2004", at="2026-09-11")
        con.close()
        _assert(r["verdict"] in (VERDICT_OK, VERDICT_OPPOSITE, VERDICT_NONE))
        _assert(r["observed"] is not None, r)
    check("52주 신고가 근접도가 계산되고 대용을 밝힌다", _high52_proxy)

    def _ivol_daily():
        """고유변동성이 높은 쪽이 덜 번다는 세계에서 잡아내는가.

        rank 가 높을수록 고유 잡음이 크고(ivol 큼) 동시에 drift 가 낮도록
        만든다 — 논문이 말하는 방향(ivol ↑ → 수익 ↓)이다."""
        con = _synthetic(effect=-0.03, ivol_spread=0.9, seed=5)
        r = run(con, "ahxz2006", at="2026-09-18")
        con.close()
        _assert(r["observed"] is not None, r)
        _assert(r["verdict"] == VERDICT_OK, r)
        _assert(r["observed"]["t"] < -T_MIN, r["observed"])
    check("일간 잔차 변동성을 재고 방향을 잡는다", _ivol_daily)

    def _ivol_needs_index():
        """기준선이 없으면 잔차를 만들 수 없다 — 0 으로 대신하지 않는다."""
        con = _synthetic(effect=-0.03, ivol_spread=0.9, seed=5)
        con.execute("DELETE FROM index_daily")
        r = run(con, "ahxz2006", at="2026-09-18")
        con.close()
        _assert(r["verdict"] == VERDICT_NONE)
        _assert("기준선" in (r["reason"] or ""), r["reason"])
    check("지수가 없으면 고유변동성을 재지 않는다", _ivol_needs_index)

    def _ivol_is_daily_not_monthly():
        """월간 대용이 아니라 일간으로 재는가.

        월말 종가 12개로는 한 달 안의 잔차 변동성을 만들 수 없다. 일간을 쓰는
        것이 이 팩터를 논문과 같은 빈도로 만드는 유일한 방법이다."""
        _assert(_FACTOR_KIND["ivol"] == "cross_mkt")
        _assert("일간" in CLAIMS["ahxz2006"]["claim"] or
                "일간" in _factor_ivol.__doc__)
        _assert(any("3요인" in x for x in CLAIMS["ahxz2006"]["limits"]))
    check("고유변동성은 일간으로 재고 요인 차이를 밝힌다", _ivol_is_daily_not_monthly)

    def _needs_runner_is_empty():
        """지금은 러너가 없는 논문이 없다. 목록은 남겨 둔다 — 새 논문이 들어와
        여기 걸리면 '대상 아님'과 섞이지 않게 사유를 적어야 한다."""
        _assert(NEEDS_RUNNER == {})
        _assert(reducibility("ahxz2006")[0] == "testable")
    check("러너가 없는 논문이 없다", _needs_runner_is_empty)

    def _claims_have_limits():
        """모든 주장은 '그 논문이 주장하지 않는 것'을 달고 있어야 한다 (규칙 4)."""
        for k, c in CLAIMS.items():
            _assert(c["sign"] in (1, -1), k)
            _assert(c["claim"].strip(), k)
            _assert(c["limits"] and all(str(x).strip() for x in c["limits"]), k)
    check("모든 검정 주장이 한계를 달고 있다", _claims_have_limits)

    def _reads_only():
        """원장에 쓰지 않는다 (규칙 2)."""
        con = _synthetic(effect=0.03, seed=5)
        before = con.execute("SELECT COUNT(*) FROM price_daily").fetchone()[0]
        run(con, "amihud2002")
        after = con.execute("SELECT COUNT(*) FROM price_daily").fetchone()[0]
        con.close()
        _assert(before == after)
    check("원장을 읽기만 한다", _reads_only)

    # ── 원장의 말 (dialect) ───────────────────────────────────────────
    #
    # 여기가 합성 자료로 자기 자신을 검증하고 있던 자리다. 판단층 전체가
    # 날짜를 `YYYY-MM-DD`, 시장·지수를 `"KOSDAQ"` 이라고 가정했고, 검사도 그
    # 가정대로 표를 만들어 통과했다. 진짜 원장은 `"20260917"` · `"코스닥"`
    # 이므로 모든 질의가 빈다 — 그리고 빈 결과는 '원장에 없습니다' 로 나간다.

    def _fixture_is_the_real_dialect():
        con = _synthetic(months=14, names=20, seed=5)     # 형식만 본다
        d = con.execute("SELECT date, market FROM price_daily LIMIT 1").fetchone()
        i = con.execute("SELECT index_name FROM index_daily LIMIT 1").fetchone()
        con.close()
        _assert(len(str(d[0])) == 8 and str(d[0]).isdigit(), d[0])
        _assert(str(d[1]) == "코스닥", d[1])
        _assert(str(i[0]) == "코스닥", i[0])
    check("합성 원장이 진짜 원장의 형식이다", _fixture_is_the_real_dialect)

    def _english_hint_finds_korean_ledger():
        """사람은 `--market KOSDAQ` 으로 부른다. 원장은 한글로 적혀 있다."""
        con = _synthetic(effect=0.03, seed=5)
        r = run(con, "amihud2002", market="KOSDAQ", at="2026-09-18")
        con.close()
        _assert(r["universe"] == "코스닥", r["universe"])
        _assert(r["observed"] is not None, r["reason"])
    check("영문으로 불러도 한글 원장을 찾는다", _english_hint_finds_korean_ledger)

    def _iso_ledger_also_works():
        """형식이 바뀌어도 코드가 아니라 원장을 본다 — 물어보기 때문이다."""
        con = _synthetic(effect=-0.03, ivol_spread=0.9, seed=5)
        con.execute("UPDATE price_daily SET date = "
                    "substr(date,1,4)||'-'||substr(date,5,2)||'-'||substr(date,7,2)")
        con.execute("UPDATE index_daily SET date = "
                    "substr(date,1,4)||'-'||substr(date,5,2)||'-'||substr(date,7,2)")
        con.commit()
        r = run(con, "ahxz2006", at="2026-09-18")         # 지수를 쓰는 경로
        con.close()
        _assert(r["observed"] is not None, r["reason"])
        _assert(r["verdict"] == VERDICT_OK, r)
    check("원장이 ISO 날짜여도 같은 판정이 나온다", _iso_ledger_also_works)

    def _missing_market_says_what_is_there():
        """못 찾으면 원장에 무엇이 있는지 적는다. '없습니다' 만으로는 자료가
        없는 것인지 이름을 잘못 부른 것인지 구분되지 않는다."""
        con = _synthetic(months=14, names=20, seed=5)    # 사유만 본다
        r = run(con, "amihud2002", market="KOSPI", at="2026-09-18")
        con.close()
        _assert(r["verdict"] == VERDICT_NONE, r)
        _assert("코스닥" in (r["reason"] or ""), r["reason"])
    check("시장을 못 찾으면 원장에 있는 이름을 알려 준다",
          _missing_market_says_what_is_there)

    for f in failed:
        print("  X  " + f, file=sys.stderr)
    print(f"replication {passed} passed, {len(failed)} failed")
    return 1 if failed else 0


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="재현 러너 (결정적)")
    ap.add_argument("--selftest", action="store_true")
    ap.add_argument("--paper", help="재현할 논문 키")
    ap.add_argument("--market", default="KOSDAQ")
    ap.add_argument("--db", help="원장 경로 (기본: ki_monitor 설정)")
    ap.add_argument("--indent", type=int, default=2)
    a = ap.parse_args()
    if not a.paper:
        sys.exit(selftest())
    import ki_ledger_mcp as M                            # noqa: E402
    try:
        # 읽기 전용으로 연다. 러너는 원장에 쓰지 않는다 (규칙 2) — 쓰기 가능
        # 하게 열어 두면 그 규칙이 코드가 아니라 예의가 된다.
        con = (sqlite3.connect(f"file:{a.db}?mode=ro", uri=True)
               if a.db else M.open_ledger())
    except M.Denied as e:
        print(M._scrub(e), file=sys.stderr)
        sys.exit(1)
    con.row_factory = sqlite3.Row
    try:
        print(json.dumps(run(con, a.paper, a.market), ensure_ascii=False, indent=a.indent))
    finally:
        con.close()
