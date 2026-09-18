# 실행 안내 (docs/RUN.md)

압축을 풀고 위에서부터 순서대로 하면 됩니다. 자세한 내용은 `README.md` 를 보십시오.

## 무엇을 하는 물건인가

한국거래소·금융감독원 **공식 API** 로 숫자를 받아 원장에 쌓고, 그 원장으로
회수 판단 리포트(HTML 한 장)를 만듭니다.

```
KRX · DART · ECOS · KIS  →  ki.sqlite (원장)  →  HTML 리포트  →  회의
     공식 API                 사실만 담는다      §1~§8            사람이 결정
```

**판단은 넣지 않습니다.** 이 도구는 재기만 하고, 점수·등급·매매 시그널을
만들지 않습니다. 결정은 회의에서 사람이 합니다.

**원장(`ki.sqlite`)이 이 구조의 중심입니다.** 87MB 파일 하나이고, 없으면 공식 API 로
언제든 다시 만듭니다. 이것이 있어야 나머지가 전부 돕니다.

---

## 한 번에 돌리기 — `RUN_ALL.cmd`

단계별로 하기 싫으시면 이것 하나면 됩니다.

```
RUN_ALL.cmd          물어보면서 진행 (처음이면 이것)
RUN_ALL.cmd auto     묻지 않고 끝까지 — 스케줄러용
```

환경 점검 → API 진단 → 원장 → 논문 → 리포트를 순서대로 돌리고,
**막히면 그 자리에서 이유와 다음에 할 일을 적고 멈춥니다.**

두 가지를 지킵니다.

- **다시 돌려도 안전합니다.** 원장이 이미 있으면 40분짜리 최초 적재를 다시 하지
  않고 하루치만 갱신합니다. 중간에 죽어도 다시 돌리면 이어서 갑니다.
  `demo`·`noai` 로 건너뛸 수 있고, `claude` CLI 가 없으면 자동으로 데모가 됩니다.

> 매주 자동으로 도는 일정(금요일 분석 → 월요일 리포트)은 `SCHEDULE.cmd` 가 등록합니다.
> 등록되는 것도 결국 `RUN_ALL.cmd morning` · `RUN_ALL.cmd close` 로, 같은 파일입니다.

아래는 단계별로 하고 싶을 때의 안내입니다.

---

## 0. 컴퓨터 준비 (약 10분)

| 필요한 것 | 확인 | 없으면 |
|---|---|---|
| Python 3.11+ | `python --version` | python.org — 설치할 때 **Add to PATH** 를 켜십시오 |
| Node 20+ | `node --version` | nodejs.org 의 LTS |

파이썬 패키지는 이 한 줄이 전부입니다.

```bash
pip install pandas numpy scipy requests lxml
```


> 윈도우에서 `python` 이 없다고 나오면 `py` 로 바꿔 보십시오.

---

## 1. 먼저 돌려 볼 것 — 키·네트워크 없이 되는 검증

```bash
cd stock-monitor
python ki_monitor.py selftest        # 128개 — 측정층

cd ..
python agents/selftest.py            # 232개 — 판단층
python docs/audit.py                 # 저장소 전반
```

셋 다 통과하면 코드는 정상입니다. 여기서 실패하면 아래로 진행하지 마십시오.

세 가지가 보는 것이 다릅니다. `selftest` 는 **재는 코드**가 성립하는지,
`agents/selftest.py` 는 **읽는 층과 그 관문**이, `docs/audit.py` 는 테스트가
못 보는 것(줄바꿈·배치 파일·키 유출·문서와 코드의 어긋남)을 봅니다.

---

## 2. 키 설정

**`RUN_ALL.cmd` 를 쓰신다면 여기는 건너뛰셔도 됩니다.** 키를 스스로 구해 옵니다 —
쓰던 `.env` 를 찾고(흔한 자리 → 넓게 훑기), 그래도 없으면 그 파일을 창에 끌어다
놓으라고 물어봅니다. 아래는 손으로 하실 때의 설명입니다.

```bash
cd stock-monitor
python ki_monitor.py import-keys          # 쓰던 .env 를 찾아 키 폴더로 복사
python ki_monitor.py import-keys --deep   # 흔한 자리에 없으면 넓게 (최대 1분)
python ki_monitor.py import-keys "경로"   # 어디 있는지 아시면
```

새로 만드실 때만:

```bash
cp .env.example .env
```

`.env` 를 열어 채웁니다.

```
KRX_API_KEY=...      # 한국거래소 — 서비스별 URL 사용신청도 별도로 필요합니다
DART_API_KEY=...     # 금융감독원
KIS_APP_KEY=...      # 한국투자증권 — 실시간 시세 (선택)
KIS_APP_SECRET=...   # 〃
FRED_API_KEY=...     # 선택 (해외 매크로)
```

> KIS 는 **없어도 됩니다.** 넣으면 리포트·프롬프트의 현재가가 원장의 일별 종가 대신
> 실시간이 됩니다. 안 넣으면 종전대로 원장 종가를 씁니다.

> **KRX 는 키 발급과 사용신청이 따로입니다.** 인증키를 받은 뒤 일별시세·지수·국고채·
> 선물 각 서비스에 **URL 사용신청**을 눌러야 합니다. 신청하지 않은 서비스는 키가
> 유효해도 `401` 을 돌려줍니다. `ingest` 가 401 이면 거의 이것입니다.

> `.env` 는 `.gitignore` 에 있습니다. 절대 커밋하지 마십시오.

### 준비가 됐는지 한 번에 보기

```bash
python ki_monitor.py doctor      # 패키지·키·원장·CSV 가 있는가
python ki_monitor.py diagnose    # API 5종을 실제로 불러 어디가 막혔는가
```

`doctor` 는 **있는지**를 보고, `diagnose` 는 **되는지**를 봅니다. 키가 다 있는데
안 될 때는 `diagnose` 가 답을 줍니다 — 키 문제인지, 서비스 신청 누락인지,
방화벽인지를 갈라 줍니다.

> 사내망에서 **"나가는 연결이 전부 막혀 있습니다"** 가 나오면 키 문제가
> 아닙니다. [`NETWORK.md`](NETWORK.md) 에 전산팀에 그대로 넘길 수 있는 허용
> 요청서와, 다른 망에서 원장을 만들어 옮기는 방법이 있습니다.

패키지·키·원장·CSV 를 전부 검사해 `O` / `X` 로 보여 주고, 마지막 줄에 다음 할 일을
알려 줍니다. **`X` 를 전부 `O` 로 만드는 것이 준비 과정의 전부입니다.**
(`-` 는 없어도 되는 항목입니다. 키 값은 출력하지 않습니다.)

```
[1] 패키지          O  pandas   O  numpy   -  weasyprint (선택)
[2] API 키          X  KRX_API_KEY        ← 이걸 채워야 합니다
[3] 데이터          X  원장 없음  ← ingest 로 만드십시오
```

---

## 3. 감시 대상 지정


**`RUN_ALL.cmd` 를 쓰신다면 여기도 건너뛰셔도 됩니다.** 키와 같은 방식으로
쓰던 `watchlist.csv`·`exit_plan.csv`·`positions.csv` 를 옛 폴더에서 찾아 복사합니다
(이미 있으면 건드리지 않습니다).

```bash
python ki_monitor.py import-data            # 쓰던 자료를 찾아 복사
python ki_monitor.py import-data --deep     # 흔한 자리에 없으면 넓게
python ki_monitor.py import-data "옛 폴더"  # 어디 있는지 아시면
```

```bash
cp watchlist.sample.csv watchlist.csv
cp exit_plan.sample.csv exit_plan.csv
```

`watchlist.csv` 를 실제 포트폴리오사로 바꿉니다. 상장사는 `code` 에 6자리,
비상장사는 `code` 를 비우고 `name` 만 적습니다.

```csv
code,name,memo
000660,SK하이닉스,코스피
035720,카카오,코스피
,예시비상장회사,비상장
```

> 아래 예시의 종목은 **배선 확인용 공개 대형주**입니다. 실제 대상으로 바꿔 쓰십시오.

> 이 세 CSV 도 `.gitignore` 대상입니다. 포트폴리오사 실명은 영업비밀입니다.

---

## 4. 원장 적재 (최초 1회, 약 30분)

```bash
python ki_monitor.py ingest --from 20250101 --universe KOSDAQ
python ki_monitor.py fundamentals --market KOSDAQ
```

코스피 종목도 보려면 `--universe KOSPI` 로 한 번 더 돌립니다.

이후로는 하루 한 번 이것만 돌리면 됩니다.

```bash
python ki_monitor.py daily --market KOSDAQ
```

**며칠 걸렀다면 먼저 `catchup` 입니다.** `daily` 는 하루치만 넣습니다 — 빠진
구간은 비어 있는 채로 남고, 몇 주 묵은 종가가 최신 종가 행세를 합니다.

```bash
python ki_monitor.py catchup --market KOSDAQ   # 밀린 영업일을 채웁니다
```

`RUN_ALL.cmd` 는 이것을 먼저 돌리고, 원장이 며칠 뒤처져 있는지를 화면에 적습니다.

---

## 5. 리포트 만들기

```bash
python ki_monitor.py report --market KOSDAQ
#   → out/KI_exit_YYYYMMDD.html
```

만들어진 HTML 을 더블클릭하면 브라우저에서 열립니다.

여기까지가 **통합 이전 원본과 완전히 같은 동작**입니다. 이 리포트가 제대로
나오는지 먼저 확인하십시오 — 나중에 문제가 생겼을 때 이 단계가 되는지만 보면
원인이 원장 쪽인지 계산 쪽인지 즉시 갈립니다.

---

## 6. 판단층 — 원장을 읽어 문장으로 만든다

여기부터는 `agents/` 입니다. 측정층은 **재기만** 하고, 이 층이 그것을 읽어
문장으로 만든 뒤 **그 문장이 나가도 되는지 검사**합니다. `ki_monitor.py` 는
한 줄도 건드리지 않습니다.

### 논문이 우리 표본에서 성립하는가

```bash
python agents/papers.py --show          # 12편의 상태 · 인용 가능 여부
python agents/cycle.py --dry-run        # 이번 주에 무엇이 도는지만
python agents/cycle.py --run            # 돌리고 장부에 쌓는다
```

`cycle.py` 는 **월요일 07:40** 에 자동으로 돕니다(`SCHEDULE.cmd` 가 등록).
재검 기한이 온 논문을 원장에 대고 다시 계산하고, 기한이 지난 채택본을
`warned` 로 내립니다. **주 3편 상한**이 있어 기한이 몰린 주에도 세 편만
돕니다 — 상한이 없으면 그 주의 재현이 전부 대충 돌아갑니다.

네트워크도 키도 쓰지 않습니다. 이미 받아 둔 원장만 읽습니다.

논문 하나만 따로 돌려 볼 수도 있습니다.

```bash
python agents/replication.py --paper amihud2002     # 달력 시간 분위 정렬
python agents/eventstudy.py  --paper ritter1991     # 사건 시간
```

통과 임계는 **|t| ≥ 3.0** 입니다. 2.0 이 아닌 이유는 `agents/README.md` 에
있습니다 — 요약하면, 주 1회 사이클이면 연 150회쯤 검정하게 되고 그때 2.0 은
효과 없는 팩터를 해마다 7~8개 통과시킵니다.

### 오늘 누가 불려 나오는가

```bash
python agents/run_day.py --stage convene --since 2026-09-17
```

원장의 변화가 데스크를 부릅니다 — 새 공시, 종가 ±8% 변동, 보호예수 해제
D-30, 거시 갱신, 재검 기한. **트리거가 없으면 아무도 소집되지 않습니다.**
조용한 날은 조용한 것이 정상입니다.

내는 것은 작업지시서입니다. 누구를, 어떤 입력으로, 어떤 예산 안에서 부를
것인가까지이고 판단은 들어 있지 않습니다.

### 나가도 되는 문장인가

```bash
python agents/gates.py --check 봉투.json
python agents/run_day.py --stage publish --envelopes agents/envelopes
```

일곱 관문을 전부 돌립니다. **통과 아니면 반려**이고, 반려된 절은 회의자료에
빈칸이 아니라 '반려됨 — 사유'로 남습니다. 키·인증 URL 이 문장에 남아 있으면
그 절이 아니라 **발행 전체**를 멈춥니다.

### 두 데스크의 판정이 갈렸는가

```bash
python agents/reconcile.py --envelopes agents/envelopes
```

데스크는 서로의 산출을 보지 않습니다. 격리가 교차검증의 전제이기 때문인데,
**아무도 대조하지 않으면 격리가 사 주는 것이 없습니다** — 서로 무관한 문장이
나올 뿐이고 회의에는 그중 하나만 올라갑니다.

세 가지를 기계적으로 봅니다.

| 무엇 | 왜 허용 오차가 없는가 |
|---|---|
| 같은 칸을 다르게 읽었다 | **원장은 하나**입니다. 다르면 둘 중 하나가 틀렸거나 낡았습니다 |
| 같은 논문을 다른 상태로 인용 | **장부는 하나**입니다. 하나가 낡은 것을 물고 왔습니다 |
| 같은 것을 쟀는데 값이 벌어졌다 | 서로 다른 방법의 독립 추정이라 **상대 오차(기본 10%)를 받습니다** |

평균 내지 않고 양쪽을 그대로 냅니다. 어느 쪽이 옳은지는 회의에서 정합니다.

**`n_uncomparable` 을 꼭 보십시오.** 봉투에 `measure` 가 없으면 비교 자체가
안 됩니다. 그때 "갈린 곳 없음"은 합의가 아니라 **안 봤다**는 뜻입니다.

문장의 뜻이 어긋나는 것은 여기서 못 잡습니다 — 의미 판단이고, 코드가 하면
조용히 틀립니다. `ic-chair` 와 회의의 몫입니다.

### 막힌 것을 위로 올린다

```bash
python agents/run_day.py --stage escalate --envelopes agents/envelopes
```

반려됐거나, 예산 안에서 못 끝냈거나, **판정이 갈린** 봉투를 한 급 위로
올립니다. 갈린 경우는 **양쪽 다** 올립니다 — 한쪽만 올리면 그 선택 자체가
판정이 됩니다.

**첫 반려는 승격이 아닙니다.** 같은 급에서 한 번 더 하고, 두 번 연속 반려되면
그때 올라갑니다 — 금지어 하나를 고치는 데 비싼 급을 띄우지 않기 위해서입니다.
예산 미완과 판정 갈림은 다시 해도 같은 결과라 한 번에 올립니다.

T3 위는 없습니다. 거기서 막힌 것은 자동으로 다시 돌리지 않고 사람에게
넘깁니다(`stuck`).

### 그때 왜 그렇게 읽었는가

```bash
python agents/replay.py --envelope 봉투.json
```

봉투가 적어 둔 것과 지금 원장을 대조합니다. 정정공시가 오면 원장의 같은 칸이
덮어써지므로, 이것이 있어야 **"에이전트가 틀렸다"와 "데이터가 바뀌었다"**를
구분할 수 있습니다.

### 어디가 약한가

```bash
python agents/scorecard.py --runs agents/out/publish
```

반려가 몰리는 게이트와 데스크를 셉니다. **계측이지 처방이 아닙니다** —
고치는 것은 사람입니다.

---

## 7. 자본구조까지 보려면

미상환 전환사채·최대주주 지분은 DART 조회가 필요합니다.

```bash
python ki_monitor.py facts --code 000660 --with-disclosures --indent 2
```

주지 않으면 FILING 이 *"자본구조 미조회 — 희석 규모를 모르는 상태"* 라고
정직하게 적습니다. 없는 것과 안 본 것은 다르기 때문입니다.

---

## 문제가 생기면

| 증상 | 원인·조치 |
|---|---|
| `.cmd` 를 더블클릭해도 **아무 반응이 없다** | 윈도우가 막은 것입니다(문법 오류면 창은 뜹니다). PowerShell 에 한 줄 붙여넣으면 폴더를 찾아 차단을 풀고 실행합니다: `$p=Get-ChildItem $HOME -Recurse -Filter RUN_ALL.cmd -EA 0 \| Select -First 1; Get-ChildItem $p.Directory -Recurse \| Unblock-File; Start-Process cmd -ArgumentList '/k',$p.FullName` |
| 무엇부터 볼지 모르겠다 | `python ki_monitor.py doctor` — `X` 항목이 곧 할 일입니다 |
| `ModuleNotFoundError` · `selftest` 실패 | 패키지 누락. `pip install pandas numpy scipy requests lxml` |
| `python` 을 못 찾음 (윈도우) | `py ki_monitor.py ...` 로 바꿔 보십시오 |
| `ingest` 가 401 | KRX 는 키 발급과 별개로 **서비스별 URL 사용신청**이 필요합니다 |
| 시세가 며칠 전 값 같다 | 원장이 밀린 것입니다. `python ki_monitor.py catchup --market KOSDAQ` — 리포트가 보는 값은 전부 원장의 마지막 종가입니다 |
| API 가 전부 안 됨 | `python ki_monitor.py diagnose` → 사내망 차단이면 `NETWORK.md` |
| `claude` 를 못 찾음 | 실전 런에만 필요합니다. 설치 전에는 `--demo` 로 배선만 확인하십시오 |
| `claude` 로그인을 매번 묻는다 | 장기 토큰을 만들면 다시 묻지 않습니다. `claude setup-token` → 나온 토큰을 `%USERPROFILE%\Stock-Agent-keys\claude-token.txt` 에 한 줄로. RUN_ALL 이 그것을 `CLAUDE_CODE_OAUTH_TOKEN` 으로 넘깁니다 (자동 실행도 이때 돕니다). RUN_ALL 이 물어볼 때 [2] 를 고르면 이 과정을 대신 해 줍니다 |
| `Yahoo chart HTTP 403` 인데 계속 진행됨 | 정상입니다. 원장의 KRX 공식 일봉으로 대체된 것이고 시세 줄에 그 사실이 표시됩니다 |
| FLOW 가 "실행 시뮬레이션 산출 실패" | 관측기간이 짧습니다(85영업일 이상 필요). `ingest --from` 을 앞당기십시오 |
| 리포트에 종목이 코드로 표시 | 원장에 그 종목 시세가 없습니다. `ingest --universe` 로 해당 시장을 적재하십시오 |
| 시세 줄이 여전히 "KRX 정규장 종가" | `ki.realtime` 이 꺼져 있거나 KIS 키가 없습니다. `python ki_monitor.py quote --code 000660 --indent 2` 로 원인을 보십시오 |
| `quote` 가 `EGW00133` | KIS 토큰 재발급 제한입니다. `.kis_token.json` 이 만들어졌는지 보고, 지웠다면 잠시 뒤 다시 하십시오 |
| 장 마감 후 실시간이 안 나옴 | 정상입니다. 정규장 밖에는 실시간이 없어 원장 종가로 돌아갑니다 |

---

## 저장소에 넣지 마십시오

`.env` · `ki.sqlite` · `watchlist.csv` · `exit_plan.csv` · `positions.csv` ·
`config.json` · `out/` · `reports/` — 전부 `.gitignore` 에 있습니다.
저작권이 아니라 **자격증명·영업비밀** 문제입니다.

---

## 면책

이 리포트는 **내부 검토용**이며 투자 조언이 아닙니다. 실제
주문·거래·자금 이동은 발생하지 않습니다. `stock-monitor` 가 만드는 리포트는
**대외비 문서**이며 투자권유·투자자문 자료가 아닙니다. 최종 판단과 책임은
이 문서를 읽는 사람에게 있습니다.
