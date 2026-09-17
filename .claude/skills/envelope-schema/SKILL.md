---
name: envelope-schema
description: 봉투를 쓰는 법 — 측정값 + 등급 + 가정 + 한계. 데스크 산출을 만들 때, 게이트에 반려됐을 때, limits 에 무엇을 적어야 할지 모를 때 쓴다.
---

# 봉투

문장은 숫자와 달리 조용히 틀린다. "처분에 12영업일"은 그 자체로는 근거의
등급도, 언제 잰 값인지도, 그 방법이 무엇을 **주장하지 않는지**도 담지 않는다.

그래서 데스크는 값을 그냥 내놓지 못한다. 반드시 봉투에 담는다.

```json
{
  "claim":        "처분 소요일수 12.4 영업일",
  "value":        12.4,
  "unit":         "business_days",
  "asof":         "2026-09-11",  "stale_days": 2,

  "source_grade": "해석",
  "sources":      ["KRX/일별매매정보"],

  "method": {
    "paper":       "amihud2002",
    "paper_state": "unverified",
    "replication": {"verdict": "재현됨", "at": "2026-02-11",
                    "universe": "KOSDAQ", "n": 1418,
                    "observed": {"spread_bp": 41, "t": 3.42}},
    "assumes":     {"participation": 0.15}
  },

  "limits": ["논문 표본은 미국 상장주 — 코스닥 외삽의 근거가 아니다"],
  "reason": null,

  "desk": "q2-disposal",
  "instance": "q2-disposal-20260911-000660-a91f",
  "tier": "T2", "escalated_from": null,
  "reviewed_by": ["risk", "compliance"]
}
```

## `limits` 에 무엇을 적는가

**그 방법이 주장하지 않는 것**을 적는다. 값의 단점이 아니라 **적용 범위의
경계**다. 가장 흔한 사고는 논문이나 데이터가 말한 적 없는 것을 말했다고 읽는
것이다.

좋은 예 — 경계가 보인다.

- "논문 표본은 미국 상장주(NYSE) — 코스닥 외삽의 근거가 아니다"
- "평시 거래대금 기준이다. 우리 물량이 그 평시를 깨는 경우는 담기지 않았다"
- "거래정지 구간을 제외하지 않았고 생존편의를 보정하지 않았다"

나쁜 예 — 아무것도 말하지 않는다.

- "참고용입니다" · "정확하지 않을 수 있습니다" · "투자 판단은 본인 책임입니다"

`limits` 가 비면 게이트 ④ 에서 반려된다.

## 값이 없을 때

**0 으로 채우지 마라.** 못 구한 값은 `null` 이고 `reason` 에 사유를 적는다.

```json
{"value": null, "reason": "일봉이 12개뿐입니다 (30개 이상 필요)"}
```

0 은 '없음'이 아니라 잰 값이다. 0 을 넣으면 그 0 이 평균에 들어간다.

## 기준일과 경과일수

원장은 **일별 종가**라 며칠 묵는다. `asof` 와 `stale_days` 를 항상 붙인다.
3영업일을 넘으면 게이트 ⑤ 가 반려하고, 값 대신 '데이터 없음'으로 나간다.

묵은 값을 조용히 내보내는 것보다 빈칸이 낫다 — 빈칸은 며칠 묵었는지 묻게
만든다.

## 판단 어휘를 쓰지 마라

`매수 · 매도 · 저평가 · 고평가 · 추천 · 목표가 · 목표주가 · 비중확대`
그리고 `score · rating · recommendation · signal · verdict · action ·
advice · target_price` 키.

게이트 ① 이 `claim` · `limits` · `notes` 를 훑는다. 한계 칸에 숨겨도 잡힌다.

예외가 하나 있다. `method.replication.verdict` 는 **논문에 대한 판정**이지
종목 판단이 아니므로 그 자리에서만 허용된다.

## 검증

```bash
python agents/envelope.py --sample      # 예시 봉투
python agents/gates.py --check 봉투.json
```
