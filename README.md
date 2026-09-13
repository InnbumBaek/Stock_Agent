# Stock Agent

한국거래소·금융감독원 **공식 API** 로 상장 포트폴리오사의 숫자를 받아 원장에
쌓고, 그 원장으로 **회수 판단 리포트**를 만드는 도구입니다.

```
KRX · DART · ECOS · KIS  →  ki.sqlite (원장)  →  HTML 리포트  →  회의
     공식 API                 사실만 담는다       §1~§8           사람이 결정
```

- 도구 사용법 — [`stock-monitor/README.md`](stock-monitor/README.md)
- 실행 안내 — [`docs/RUN.md`](docs/RUN.md) · 처음이면 [`START-HERE.txt`](START-HERE.txt)
- 개발 규칙 — [`CLAUDE.md`](CLAUDE.md)
- 데이터 출처·이용 조건 — [`stock-monitor/SOURCES.md`](stock-monitor/SOURCES.md)
- **에이전트화 방안** — [`docs/agentization/`](docs/agentization/)

## 설계 원칙

**재기만 하고 판단하지 않습니다.** 점수·등급·매매 시그널을 만들지 않습니다.
결정은 회의에서 사람이 합니다.

## 대외비

`ki.sqlite` · `watchlist.csv` · `exit_plan.csv` · `positions.csv` · `out/` ·
`logs/` 는 저장소에 올리지 않습니다. 키는 저장소 **밖**에 둡니다
(`%USERPROFILE%\Stock-Agent-keys\.env`).

내부 검토용이며 투자권유·투자자문 자료가 아닙니다.
