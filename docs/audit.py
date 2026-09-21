"""저장소 최종 감사 — 넘기기 전에 조용히 깨질 수 있는 것을 전부 본다.

    python docs/audit.py

테스트가 잡지 못하는 종류의 실패를 본다.

  · 줄바꿈이 바뀌어 diff 가 통째로 뜨는 것
  · 배치 파일의 괄호가 안 맞아 스케줄러에서만 죽는 것
  · config.js 와 ki-bridge.js 의 키가 어긋나 설정이 조용히 무시되는 것
  · 옵트인 스위치가 켜진 채로 나가는 것
  · 자격증명·포트폴리오사 실명이 저장소에 새는 것
  · 문서의 테스트 개수가 실제와 어긋나는 것

원본(0f8b36e)에 이미 있던 내용은 유출 검사에서 제외한다 — 원본을 지우는 것은
그 자체가 회귀이기 때문이다.
"""
import io
import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
fails = []
warns = []


def ok(label):
    print(f"  O  {label}")


def bad(label):
    fails.append(label)
    print(f"  X  {label}")


def warn(label):
    warns.append(label)
    print(f"  !  {label}")


print("[1] 줄바꿈 — 편집 도구가 바꾸면 diff 가 통째로 뜬다")
CRLF = ["stock-monitor/ki_monitor.py"]
LF = ["docs/audit.py", "docs/fetch_papers.py"]
for p in CRLF:
    b = (ROOT / p).read_bytes()
    (ok if b.count(b"\r\n") > 100 else bad)(f"{p} = CRLF")
for p in LF:
    b = (ROOT / p).read_bytes()
    (ok if b.count(b"\r\n") == 0 else bad)(f"{p} = LF")

print("\n[2] 배치 파일 — 스케줄러가 부르면 조용히 실패한다")
for p in sorted(ROOT.glob("*.cmd")):
    b = p.read_bytes()
    if b.count(b"\r\n") == 0:
        bad(f"{p.name} 가 LF — 윈도우 배치는 CRLF 여야 한다")
        continue
    txt = b.decode("utf-8")
    depth = 0
    for ln in txt.split("\r\n"):
        t = ln.strip()
        if t.lower().startswith("rem") or t.startswith("::"):
            continue
        core = re.sub(r"\^[()]", "", ln)
        core = re.sub(r'"[^"]*"', '""', core)
        depth += core.count("(") - core.count(")")
    (ok if depth == 0 else bad)(f"{p.name} 괄호 균형 ({depth:+d})")

print("\n[2-a2] 라벨 자리와 goto 대상 — 여기가 틀리면 창이 그냥 닫힌다")
# 괄호 블록 안의 라벨은 cmd 가 통째로 삼킨다. 없는 라벨로 goto 하면 그 자리에서
# 죽는다. 둘 다 오류 한 줄 없이 끝나서, 사람에게는 "실행이 안 된다" 로만 보인다.
# 실제로 편집 중에 두 번 만들었다 — 라벨을 줄 단위가 아니라 문자열로 찾다가
# 'call :키' 가 먼저 걸려 서브루틴이 본문 한가운데로 끼어들었다.
for _n in sorted(p.name for p in ROOT.glob("*.cmd")):
    _t = (ROOT / _n).read_bytes().decode("utf-8")
    _lines = _t.split("\r\n")
    _labels = {l.strip()[1:].split()[0].lower() for l in _lines
               if l.strip().startswith(":") and not l.strip().startswith("::")}
    _depth, _bad = 0, []
    for _i, _ln in enumerate(_lines, 1):
        _s = _ln.strip()
        if _s.lower().startswith("rem"):
            continue
        if _depth > 0 and _s.startswith(":") and not _s.startswith("::"):
            _bad.append(f"{_i}행 블록 안 라벨")
        _c = _s.replace("^(", "").replace("^)", "")
        _depth += _c.count("(") - _c.count(")")
        if _depth < 0:
            _depth = 0
    _miss = []
    for _i, _ln in enumerate(_lines, 1):
        for _m in re.finditer(r"(?:goto|call)\s+:([a-zA-Z_0-9]+)", _ln):
            if _m.group(1).lower() in ("eof",):
                continue                      # :eof 는 cmd 내장이다
            if _m.group(1).lower() not in _labels:
                _miss.append(f"{_i}행 :{_m.group(1)}")
    (ok if not _bad else bad)(f"{_n} 라벨이 괄호 밖에 있다 ({', '.join(_bad) or '이상 없음'})")
    (ok if not _miss else bad)(f"{_n} goto/call 대상이 실재한다 ({', '.join(_miss) or '이상 없음'})")

print("\n[2-b] for /f 안의 작은따옴표 — 여기서 틀리면 날짜가 통째로 빈다")
for p in sorted(ROOT.glob("*.cmd")):
    txt = p.read_bytes().decode("utf-8")
    hits = []
    for m in re.finditer(r"for /f [^\n]*in \('([^\n]*?)'\)", txt):
        # for /f 는 마지막 ' 까지를 명령으로 본다. 명령 안에 ' 가 있으면
        # 잘리는 위치가 달라져 조용히 빈 값이 된다.
        if "'" in m.group(1):
            hits.append(m.group(1)[:60])
    (ok if not hits else bad)(f"{p.name} for/f 인용 ({hits or '안전'})")

print("\n[2-c] 지연확장이 켜진 파일의 짝 없는 ! — 조용히 지워진다")
# setlocal enabledelayedexpansion 이 켜져 있으면 cmd 는 ! 를 변수 참조로
# 본다. 짝이 없으면 그 ! 를 지운다 — 오류도 안 난다. node -e 안의
# if(!Array.isArray(x)) 가 if(Array.isArray(x)) 가 되어 판정이 뒤집힌
# 적이 있다. !VAR! 형태만 남기고, 나머지 ! 는 쓰지 않는 것이 답이다.
for p in sorted(ROOT.glob("*.cmd")):
    txt = p.read_bytes().decode("utf-8")
    if "enabledelayedexpansion" not in txt.lower():
        continue
    hits = []
    for i, ln in enumerate(txt.split("\r\n"), 1):
        t = ln.strip()
        if t.lower().startswith("rem") or t.startswith("::"):
            continue
        # !VAR! 를 걷어내고 남은 ! 가 있으면 그것이 지워질 놈이다.
        rest = re.sub(r"![A-Za-z_][A-Za-z0-9_]*!", "", ln)
        if "!" in rest:
            hits.append(f"{i}행")
    (ok if not hits else bad)(f"{p.name} 짝 없는 ! ({', '.join(hits) or '없음'})")

print("\n[2-h] 감시 종목 자료도 스스로 구해 오는가")
# 워치리스트는 대외비라 저장소에 올리지 않는다. 새로 푼 폴더에는 없고,
# 그러면 감시 종목이 포트폴리오사로 안 맞춰진다. 화면에는 "그대로 둡니다"
# 한 줄만 지나가서 아무도 모른다 — 키와 같은 사다리로 가져와야 한다.
_ra4 = (ROOT / "RUN_ALL.cmd").read_bytes().decode("utf-8")
_i_keys = _ra4.find("call :keys\r")
_i_data = _ra4.find("call :data\r")
(ok if _i_data > 0 else bad)("RUN_ALL 이 감시 종목 자료를 가져온다")
(ok if 0 < _i_keys < _i_data else bad)("키 → 자료 순서다")
_km2 = (ROOT / "stock-monitor" / "ki_monitor.py").read_text(encoding="utf-8")
(ok if "def cmd_import_data" in _km2 else bad)("ki_monitor 에 import-data 가 있다")
(ok if "회사명은 찍지 않습니다" in _km2 else bad)("실명을 찍지 않는다")
(ok if "if d_.exists():" in _km2 else bad)("이미 있는 파일은 덮어쓰지 않는다")

print("\n[2-f] 압축 안에서 눌렀을 때 사람이 읽을 말이 나오는가")
# 탐색기·반디집은 더블클릭한 .cmd 하나만 %TEMP% 에 풀어서 실행한다. 옆 폴더가
# 통째로 없으니 node 가 "Cannot find module ...\\BNZ.xxxx\\server\\server.js" 를
# 토하고 끝난다. 실제로 그 화면을 받았다 — 원인이 안 보이는 실패라 여기서 잡는다.
for _n, _need in (("RUN_ALL.cmd", "stock-monitor/ki_monitor.py"),
                  ("SCHEDULE.cmd", "RUN_ALL.cmd")):
    _t = (ROOT / _n).read_bytes().decode("utf-8")
    _win = _need.replace("/", "\\")
    _i_g = _t.find(f'if not exist "%~dp0{_win}"')
    _i_run = -1                       # rem 줄은 세지 않는다 (주석에도 node 가 나온다)
    _off = 0
    for _ln in _t.split("\r\n"):
        if not _ln.lstrip().lower().startswith("rem") and (
                "node " in _ln or "%PY% " in _ln or "schtasks" in _ln):
            _i_run = _off
            break
        _off += len(_ln) + 2
    (ok if _i_g > 0 else bad)(f"{_n} 이 옆 파일을 먼저 확인한다 ({_need})")
    (ok if 0 < _i_g < _i_run else bad)(f"{_n} 확인이 실행보다 먼저 온다")
    (ok if (ROOT / _need).exists() else bad)(f"{_n} 이 찾는 파일이 실재한다")

print("\n[2-g] RUN_ALL 이 키를 스스로 구해 오는가")
# "RUN_ALL 만 누르면 끝" 이 이 프로젝트의 약속이다. 키가 없다고 사람에게
# 명령어를 시키는 순간 그 약속이 깨진다. 사다리는 세 칸이다 —
# 흔한 자리 → 넓게 훑기 → 물어보기. 자동 실행에는 답할 사람이 없으므로
# 묻는 칸은 건너뛴다.
_ra3 = (ROOT / "RUN_ALL.cmd").read_bytes().decode("utf-8")
# 얕은 탐색 줄을 **줄 끝**으로 찾았더니, 그 줄 끝에 리다이렉션을 붙이는
# 순간 검사가 "흔한 자리를 안 본다" 로 뒤집혔다. 실제로는 그대로 보고 있었다.
# 찾을 것은 줄의 생김새가 아니라 `--deep` 도 경로 인자도 없는 첫 호출이다.
_i_shallow = -1
for _ln in _ra3.split("\r\n"):
    _t = _ln.strip()
    if _t.lower().startswith("rem"):
        continue
    # 실제로 부르는 줄만 본다. 안내 문구에도 같은 명령이 적혀 있어서,
    # 낱말로만 찾으면 얕은 탐색을 통째로 지워도 그 안내 줄이 대신 걸린다.
    if _t.startswith("%PY% ki_monitor.py import-keys") and "--deep" not in _t \
            and "%KEYSRC%" not in _t:
        _i_shallow = _ra3.find(_ln)
        break
_i_deep = _ra3.find("import-keys --deep")
_i_ask = _ra3.find("set /p \"KEYSRC=")
(ok if _i_shallow > 0 else bad)("흔한 자리를 먼저 본다")
(ok if 0 < _i_shallow < _i_deep else bad)("못 찾으면 넓게 훑는다")
(ok if 0 < _i_deep < _i_ask else bad)("그래도 없으면 물어본다")
(ok if '"%MODE%"=="auto" goto :keys_none' in _ra3 else bad)(
    "자동 실행에서는 묻지 않는다")
_km = (ROOT / "stock-monitor" / "ki_monitor.py").read_text(encoding="utf-8")
(ok if "--deep" in _km and "def _walk_for_env" in _km else bad)(
    "ki_monitor 에 넓은 탐색이 있다")

print("\n[3] 배치가 부르는 파일이 실재하는가")
for p in sorted(ROOT.glob("*.cmd")):
    txt = p.read_bytes().decode("utf-8")
    for m in re.finditer(r"%~dp0([0-9A-Za-z_\\.]+\.cmd)", txt):
        (ok if (ROOT / m.group(1)).exists() else bad)(f"{p.name} → {m.group(1)}")
    for sub_ in re.finditer(r"(?:pushd|cd /d \"%~dp0)([a-z-]+)", txt):
        d = sub_.group(1)
        if d in ("stock-monitor",):
            (ok if (ROOT / d).is_dir() else bad)(f"{p.name} → {d}/")

print("\n[3-b] 배치가 넘기는 인자를 RUN_ALL 이 받는가")
# schtasks 가 "RUN_ALL.cmd morning" 을 걸어 두었는데 RUN_ALL 에 그 갈래가
# 없으면, 08:50 에 대화형 화면이 떠서 아무도 없는 앞에서 멈춘다. 오류도
# 안 난다 — 그냥 리포트가 없다. 조용한 실패라 여기서 잡는다.
runall = (ROOT / "RUN_ALL.cmd").read_bytes().decode("utf-8")
wanted = set()
for p in sorted(ROOT.glob("*.cmd")):
    for m in re.finditer(r'RUN_ALL\.cmd\\?"?\s+([a-z]+)"', p.read_bytes().decode("utf-8")):
        wanted.add(m.group(1))
(ok if wanted else warn)(f"스케줄러가 넘기는 인자 — {sorted(wanted) or '없음'}")
for arg in sorted(wanted):
    has = f'"%MODE%"=="{arg}"' in runall
    (ok if has else bad)(f"RUN_ALL.cmd 가 '{arg}' 를 분기한다")

print("\n[6] 파이썬 서브커맨드가 전부 도는가 (키 없이)")
for args, want in [(["selftest"], "passed"), (["macro"], "ki.macro/1"),
                   (["quote", "--code", "000660"], "ki.quote/1"),
                   (["facts", "--code", "000660"], "ki.facts/1"),
                   (["candles", "--code", "000660"], "ki.candles/1"),
                   (["doctor"], "[1] 패키지"), (["check-auth"], "KIS  필드매핑"),
                   (["catalog"], ""), (["--help"], "quote")]:
    r = subprocess.run([sys.executable, "ki_monitor.py"] + args,
                       cwd=ROOT / "stock-monitor", capture_output=True, text=True, timeout=120)
    out = r.stdout + r.stderr
    crashed = "Traceback" in out
    if crashed:
        bad(f"{' '.join(args)} — 예외 발생")
    elif want and want not in out:
        bad(f"{' '.join(args)} — 기대 문자열 없음 ({want})")
    else:
        ok(f"{' '.join(args)}")

print("\n[7] 주문 API 차단 — KIS 는 같은 서버에 주문이 있다")
# selftest 는 통과 항목명을 출력하지 않는다(실패만 찍는다). 그래서 출력이 아니라
# 소스에 그 검사가 실재하는지를 본다.
src = (ROOT / "stock-monitor" / "ki_monitor.py").read_text(encoding="utf-8")
for need in ["주문 API 는 호출 불가", "화이트리스트 밖 이름도 호출 불가",
             "시세 화이트리스트는 두 개뿐", "실시간 스냅샷은 원장에 쓰지 않는다"]:
    (ok if f'check("{need}"' in src else bad)(f"selftest 검사 존재: {need}")

print("\n[8] 저장소에 비밀·대외비가 없는가")
env = ROOT / "stock-monitor" / ".env"
if env.exists():
    vals = [l.split("=", 1)[1].strip() for l in io.open(env, encoding="utf-8")
            if "=" in l and not l.startswith("#") and len(l.split("=", 1)[1].strip()) >= 12]
    if vals:
        r = subprocess.run(["git", "grep", "-l", "-z", "-F", "-f", "/dev/stdin"],
                           input="\n".join(vals), capture_output=True, text=True, cwd=ROOT)
        (ok if not r.stdout.strip() else bad)(f"API 키 유출 — {r.stdout.strip() or '없음'}")
    else:
        warn(".env 에 검사할 키가 없다")
else:
    warn(".env 가 없어 키 유출 검사를 건너뛴다")

# 검사할 이름을 여기 적지 않는다. 적는 순간 이 파일이 유출이 된다
# (감사기가 자기 자신을 잡는다). watchlist.csv 에서 읽는다 — 그 파일은
# .gitignore 대상이고, 없으면 이 검사를 건너뛴다.
NAMES = []
_wl = ROOT / "stock-monitor" / "watchlist.csv"
if _wl.exists():
    for _line in io.open(_wl, encoding="utf-8-sig"):
        _line = _line.strip()
        if not _line or _line.startswith("#") or _line.startswith("code,"):
            continue
        _parts = _line.split(",")
        if len(_parts) >= 2 and _parts[1].strip():
            NAMES.append(_parts[1].strip())
if not NAMES:
    warn("watchlist.csv 가 없어 실명 유출 검사를 건너뛴다")
# -z 로 받는다. 한글 경로를 git 이 8진수로 이스케이프해 git show 가 못 찾는다.
r = (subprocess.run(["git", "grep", "-l", "-z", "-F", "-f", "/dev/stdin"],
                    input="\n".join(NAMES), capture_output=True, text=True, cwd=ROOT)
     if NAMES else subprocess.CompletedProcess([], 0, "", ""))
hit = [h for h in r.stdout.split("\0") if h.strip()]
# 원본 커밋에 이미 있던 파일은 제외한다 — 통합 작업이 새로 넣은 것만 본다.
# (원본을 지우는 것은 그 자체가 회귀다. CLAUDE.md 3항)
BASE = "0f8b36e"
added = []
for h in hit:
    p = h.strip().strip('"')
    was = subprocess.run(["git", "show", f"{BASE}:{p}"],
                         capture_output=True, text=True, cwd=ROOT)
    if was.returncode != 0 or not any(n in was.stdout for n in NAMES):
        added.append(p)
(ok if not added else bad)(f"통합이 새로 넣은 실명 — {added or '없음'}")

# 위 검사는 watchlist.csv 가 있어야 돈다. 그 파일은 .gitignore 대상이라
# 새로 푼 폴더·CI·원격 컨테이너에는 없고, 그때 검사는 '건너뜀' 한 줄만 남긴다.
# 실제로 그렇게 오래 숨어 있었다 — ki_monitor.py 의 주석에 포트폴리오사의
# 약칭과 정식명이 실명으로 적혀 있었는데, 워치리스트를 넣고 감사를 돌린
# 날에야 처음 잡혔다.
#
# 그래서 목록 없이도 도는 검사를 하나 더 둔다. 이름을 적지 않고 **모양**만
# 본다 — "약칭(...)" · "정식명(...)" · "회사명(...)" 처럼 괄호 안에 한글
# 고유명사를 예로 드는 자리다. 설명에 실명이 필요한 적은 없다.
_SHAPE = re.compile(r"(약칭|정식명|회사명|종목명|사명)\s*[(（]\s*[가-힣]{2,}")
_shape_hits = []
for _p in sorted(ROOT.rglob("*.py")):
    if any(x in _p.parts for x in (".git", "node_modules", "out", "logs")):
        continue
    try:
        _t = _p.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        continue
    # 이 감사기 자신의 무늬 정의에 걸리지 않게 산출부만 본다.
    if _p.name == "audit.py":
        continue
    for _m in _SHAPE.finditer(_t):
        _shape_hits.append(f"{_p.relative_to(ROOT)}:{_t[:_m.start()].count(chr(10))+1}")
(ok if not _shape_hits else bad)(
    f"실명을 예로 든 자리 — {_shape_hits or '없음'}")
if hit and not added:
    print(f"     (원본에 이미 있던 파일 {len(hit)}건은 제외)")

r = subprocess.run(["git", "ls-files"], capture_output=True, text=True, cwd=ROOT)
tracked = r.stdout.split()
FORBIDDEN = [".env", "ki.sqlite", "watchlist.csv", "exit_plan.csv", "positions.csv",
             "config.json", ".kis_token.json", ".api_verified.json"]
leaked = [t for t in tracked
          if any(t.endswith(f) for f in FORBIDDEN) and not t.endswith(".example")
          and "sample" not in t]
(ok if not leaked else bad)(f"금지 파일 추적 — {leaked or '없음'}")

print("\n[9] 문서의 테스트 개수가 실제와 맞는가")
py = subprocess.run([sys.executable, "ki_monitor.py", "selftest"],
                    cwd=ROOT / "stock-monitor", capture_output=True, text=True)
n_py = int(re.search(r"(\d+) passed", py.stdout).group(1))

# 판단층(agents/)도 자체 검사를 갖는다. 문서가 두 층의 개수를 함께 적으므로
# 여기서도 둘 다 실제로 돌려 본다 — 한쪽만 세면 다른 쪽 숫자가 낡아 간다.
n_ag = 0
if (ROOT / "agents" / "selftest.py").exists():
    ag = subprocess.run([sys.executable, "agents/selftest.py"],
                        cwd=ROOT, capture_output=True, text=True)
    n_ag = sum(int(x) for x in re.findall(r"(\d+) passed", ag.stdout))
    if ag.returncode != 0:
        bad(f"agents/selftest.py 가 실패했습니다 (rc={ag.returncode})")
print(f"     실제: selftest {n_py} · agents {n_ag}")
n_js = n_py
for p in ["README.md", "docs/RUN.md", "CLAUDE.md", "stock-monitor/README.md"]:
    txt = (ROOT / p).read_text(encoding="utf-8")
    stale = []
    for m in re.finditer(r"(\d+)개", txt):
        v = int(m.group(1))
        if 60 <= v <= 400 and v not in (n_py, n_js, n_ag):
            ctx = txt[max(0, m.start() - 40):m.end()]
            if "test" in ctx.lower() or "selftest" in ctx or "검증" in ctx:
                stale.append(v)
    (ok if not stale else bad)(f"{p} 테스트 개수 ({stale or '일치'})")

print("\n[8-b] 키가 저장소 밖에 있는가 — 그리고 키만 나갔는가")
# .gitignore 는 약하다. git add -f 한 번이면 뚫린다. 키는 저장소 밖에 둔다.
# 다만 옮기는 것은 키뿐이어야 한다 — 원장·워치리스트까지 끌고 나가면 쓰던
# 폴더가 통째로 안 맞는다. 그건 이 규칙의 값이 아니다.
_kmp = ROOT / "stock-monitor" / "ki_monitor.py"
_km2 = _kmp.read_bytes().decode("utf-8")
for label, ok_ in (
    ("키 폴더 개념이 있다", "def _keys_home()" in _km2 and "STOCK_AGENT_KEYS" in _km2),
    (".env 를 키 폴더에서 읽는다", 'keys_path(".env")' in _km2),
    ("옛 위치도 계속 읽는다 (기존 설정 보호)", "legacy = ROOT / name" in _km2),
    ("옮기는 명령이 있다", "migrate-keys" in _km2),
    ("원장은 저장소 옆 그대로", 'return str(ROOT / v)' in _km2),
    ("오류 문구를 가리는 장치가 있다", "def scrub(" in _km2),
):
    (ok if ok_ else bad)(label)
# 키 외의 것까지 키 폴더로 끌고 갔는지 — 범위 넘침 검사
_over = [n for n in ('"ki.sqlite"', '"watchlist.csv"', '"positions.csv"',
                     '"exit_plan.csv"')
         if f"keys_path({n})" in _km2]
(ok if not _over else bad)(f"키만 옮겼는가 ({_over or '키뿐'})")

# ── [10] 데스크·스킬 정의가 코드와 어긋나지 않는가 ──────────────────
#
# 마크다운 정의 파일은 테스트가 돌려 보지 않는다. 데스크 이름 하나를 코드에서
# 바꾸고 .md 를 안 고치면, 트리거는 있는데 아무도 오지 않는 소집이 생긴다.
# 그것은 오류 한 줄 없이 "조용한 날"처럼 보인다.
print("\n[10] 데스크·스킬 정의가 코드와 맞는가")
_ag_dir = ROOT / ".claude" / "agents"
_sk_dir = ROOT / ".claude" / "skills"
if not (ROOT / "agents" / "triggers.py").exists():
    warn("agents/triggers.py 가 없습니다 — 건너뜁니다")
else:
    sys.path.insert(0, str(ROOT / "agents"))
    import triggers as _T

    _md = sorted(f.stem for f in _ag_dir.glob("*.md")) if _ag_dir.exists() else []
    _code = sorted(_T.DESKS)
    (ok if _md == _code else bad)(
        f"데스크 정의 9개가 코드와 일치 ({'일치' if _md == _code else f'.md={_md} ≠ code={_code}'})")

    # frontmatter 의 name 이 파일명과 같은가 — 다르면 호출되지 않는다.
    _mis = []
    for f in sorted(_ag_dir.glob("*.md")) if _ag_dir.exists() else []:
        head = f.read_text(encoding="utf-8").split("---")[1] if "---" in f.read_text(encoding="utf-8") else ""
        nm = re.search(r"^name:\s*(\S+)", head, re.M)
        if not nm or nm.group(1) != f.stem:
            _mis.append(f.name)
    (ok if not _mis else bad)(f"데스크 frontmatter name 이 파일명과 일치 ({_mis or '일치'})")

    # 트리거가 부르는 데스크가 전부 실재하는가
    _unknown = sorted({d for _w, ds, _y in _T.DISCLOSURE_ROUTES for d in ds
                       if d not in _T.DESKS}
                      | {d for d in _T.DISCLOSURE_DEFAULT[0] if d not in _T.DESKS})
    (ok if not _unknown else bad)(f"트리거가 실재하는 데스크만 부른다 ({_unknown or '전부 실재'})")

    _skills = sorted(d.name for d in _sk_dir.iterdir() if d.is_dir()) if _sk_dir.exists() else []
    _want = ["compliance-gate", "envelope-schema", "paper-adoption",
             "replication", "source-grading"]
    (ok if _skills == _want else bad)(f"스킬 5종 ({_skills if _skills != _want else '전부 있음'})")
    _noskill = [d for d in _skills if not (_sk_dir / d / "SKILL.md").exists()]
    (ok if not _noskill else bad)(f"스킬마다 SKILL.md 가 있다 ({_noskill or '전부 있음'})")

    # 데스크가 없는 도구를 부르도록 적혀 있으면, 그 데스크는 자기 일을 못 하면서도
    # 오류를 내지 않는다 — 부르지 못한 도구만큼 조용히 비어 있는 봉투가 나온다.
    import ki_ledger_mcp as _M
    _badtool = []
    for f in sorted(_ag_dir.glob("*.md")) if _ag_dir.exists() else []:
        m = re.search(r"읽기 도구만 쓴다: `([^`]+)`", f.read_text(encoding="utf-8"))
        if not m:
            continue
        for t in (x.strip() for x in m.group(1).split(",")):
            if t not in _M.TOOLS:
                _badtool.append(f"{f.stem}:{t}")
    (ok if not _badtool else bad)(
        f"데스크가 실재하는 MCP 도구만 부른다 ({_badtool or '전부 실재'})")

    # 봉투는 **작업지시서가 준 instance** 를 그대로 적어야 한다. 데스크가 제
    # 번호를 지어내면 시킨 일과 돌아온 일이 영원히 안 맞고, 그러면 회수 대조가
    # 전부 '미이행 + 무단' 을 낸다 (`agents/dispatch.py`). 정의 파일에서 이
    # 줄이 빠지는 것은 테스트가 못 본다 — 그래서 여기서 본다.
    _noinst = []
    for f in sorted(_ag_dir.glob("*.md")) if _ag_dir.exists() else []:
        txt = f.read_text(encoding="utf-8")
        if "instance" not in txt:
            _noinst.append(f"{f.stem}:규칙없음")
        elif '"instance"' not in txt:
            _noinst.append(f"{f.stem}:산출예시없음")
    (ok if not _noinst else bad)(
        f"데스크가 지시서의 instance 를 적게 되어 있다 ({_noinst or '전부 있음'})")

    # agents/README.md 의 모듈별 개수. 총계만 세면 이 줄들이 조용히 낡는다 —
    # 실제로 두 번 어긋났고, 두 번 다 손으로 고치다 빠뜨려서 생긴 일이다.
    _rm = ROOT / "agents" / "README.md"
    if _rm.exists() and n_ag:
        _per = dict(re.findall(r"^(\w+)\s+(\d+) passed", ag.stdout, re.M))
        # 네 모듈(dialect · scope · watch · dispatch)이 이 표에 빠져 있었다.
        # 가장 나중에 들어온 것들이고, 그래서 가장 자주 바뀌는 것들이다 —
        # 검사에서 빠진 줄은 낡아도 아무도 모른다. 전부 센다.
        _MOD = {"dialect": "dialect.py", "scope": "scope.py",
                "watch": "watch.py", "dispatch": "dispatch.py",
                "envelope": "envelope.py", "papers": "papers.py",
                "replication": "replication.py", "eventstudy": "eventstudy.py",
                "gates": "gates.py", "triggers": "triggers.py",
                "mcp": "ki_ledger_mcp.py", "cycle": "cycle.py",
                "reconcile": "reconcile.py", "run_day": "run_day.py",
                "scorecard": "scorecard.py", "replay": "replay.py"}
        _txt = _rm.read_text(encoding="utf-8")
        _drift = []
        for _k, _fn in _MOD.items():
            _m = re.search(rf"^{re.escape(_fn)}\s+\S.*?\s+(\d+)$", _txt, re.M)
            if _m is None:
                _drift.append(f"{_fn}:줄없음")
            elif _m.group(1) != _per.get(_k):
                _drift.append(f"{_fn}:{_m.group(1)}≠{_per.get(_k)}")
        _tot = re.search(r"합계\s+(\d+)", _txt)
        if not _tot or int(_tot.group(1)) != n_ag:
            _drift.append(f"합계:{_tot.group(1) if _tot else '없음'}≠{n_ag}")
        (ok if not _drift else bad)(
            f"agents/README.md 모듈별 개수 ({_drift or '일치'})")

    # 덱의 JSON 예시에 코드에 없는 필드명이 있으면, 회의에서 그 이름으로 묻고
    # 아무도 찾지 못한다. 실제로 네 개가 어긋나 있었다(adopted_at·spread_bp 등).
    _deck = ROOT / "docs" / "agentization" / "build_deck.js"
    if _deck.exists():
        _js = _deck.read_text(encoding="utf-8")
        _src = "".join(f.read_text(encoding="utf-8")
                       for f in sorted((ROOT / "agents").glob("*.py")))
        _src += (ROOT / "stock-monitor" / "ki_monitor.py").read_text(encoding="utf-8")
        _noise = {"type", "text", "color", "fill", "line", "options",
                  "fontsize", "valign", "align"}
        _ghost = sorted(k for k in set(re.findall(r'"([a-z][a-z0-9_]{3,})":', _js))
                        - _noise if k not in _src)
        (ok if not _ghost else bad)(
            f"덱의 필드명이 코드에 실재한다 ({_ghost or '전부 실재'})")

        # 덱 부록의 모듈별 개수. README 만 세고 덱을 안 세면 덱이 조용히
        # 낡는다 — 실제로 `watch.py 20`(실제 21) · `envelope.py 28`(실제 29)
        # 로 어긋나 있었고, 같은 덱의 표지가 340 이라고 적고 있어서 부록의
        # 합(338)과 서로 달랐다. 회의에 올라가는 것은 덱이다.
        if n_ag:
            _per = dict(re.findall(r"^(\w+)\s+(\d+) passed", ag.stdout, re.M))
            _deck_n = dict(re.findall(r"[├└]─ (\w+\.py)\s+\S.*?\s(\d+)'", _js))
            _dd = []
            for _k, _fn in _MOD.items():
                if _fn not in _deck_n:
                    _dd.append(f"{_fn}:줄없음")
                elif _deck_n[_fn] != _per.get(_k):
                    _dd.append(f"{_fn}:{_deck_n[_fn]}≠{_per.get(_k)}")
            _sum = sum(int(v) for v in _deck_n.values())
            if _deck_n and _sum != n_ag:
                _dd.append(f"부록 합:{_sum}≠{n_ag}")
            (ok if not _dd else bad)(
                f"덱 부록의 모듈별 개수 ({_dd or '일치'})")

        # 덱이 말하는 '검정 대상 논문 수'. 이벤트 러너가 들어오면서 5 → 8 이
        # 됐는데 덱의 두 자리가 5 로 남아 있었다. 같은 슬라이드 안에서 5 와 8
        # 이 나란히 적혀 있었고, 읽는 사람은 그 모순을 자기가 잘못 본 것으로
        # 넘긴다. 세는 곳은 코드 하나여야 한다.
        # 빌드가 커밋된 자리에 떨어지는가. `README` 는 파일 **이름만** 넘기는
        # 명령을 적어 두었는데, 그 인자를 cwd 로 풀면 덱이 저장소 루트에
        # 떨어진다 — `.gitignore` 의 `*.pptx` 가 그 자리를 덮고 예외는
        # `docs/agentization/` 에만 걸려 있어서, 빌드는 "WROTE" 를 찍고
        # `git status` 는 한 줄도 내지 않고 커밋된 덱은 낡은 채 남는다.
        # 규칙 9 가 말하는 그 실패다. 여기서 실제로 한 번 겪었다.
        _outblk = re.search(r"const OUT =.*?;", _js, re.S)
        _ob = _outblk.group(0) if _outblk else ""
        _obad = []
        if not _ob:
            _obad.append("OUT 대입 없음")
        else:
            if "__dirname" not in _ob:
                _obad.append("__dirname 미사용")
            if "basename" not in _ob:
                _obad.append("이름만 준 인자를 덱 폴더로 풀지 않음")
        _rd = ROOT / "docs" / "agentization" / "README.md"
        if _rd.exists():
            for _m in re.findall(r"node \S*build_deck\.js\s+\"([^\"]+)\"",
                                 _rd.read_text(encoding="utf-8")):
                if "/" in _m and not _m.startswith("docs/agentization/"):
                    _obad.append(f"README 명령이 다른 자리로 쓴다:{_m}")
        (ok if not _obad else bad)(
            f"덱 빌드가 커밋된 자리에 떨어진다 ({_obad or '일치'})")

        import json as _json
        import replication as _RC
        _pj = ROOT / "stock-monitor" / ".papers.json"
        if _pj.exists():
            _keys = list(_json.loads(_pj.read_text(encoding="utf-8"))["papers"])
            _n_testable = sum(1 for k in _keys
                              if _RC.reducibility(k)[0] in ("testable", "event_time"))
            _said = sorted({int(m) for m in
                            re.findall(rf"{len(_keys)}편 중 (\d+)편", _js)})
            _pbad = [str(x) for x in _said if x != _n_testable]
            (ok if not _pbad else bad)(
                f"덱의 검정 대상 논문 수가 코드와 일치 "
                f"({len(_keys)}편 중 {_n_testable}편) "
                f"({_pbad or '일치'})")

    # 임계는 한 곳에서만 정해져야 한다. 문서가 다른 숫자를 말하면 그 문서가 규칙이 된다.
    import replication as _R
    _tbad = []
    for f in list(_ag_dir.glob("*.md")) + list(_sk_dir.glob("*/SKILL.md")):
        txt = f.read_text(encoding="utf-8")
        for m in re.finditer(r"\|t\|\s*[≥>=]+\s*([0-9.]+)", txt):
            if float(m.group(1)) != _R.T_MIN:
                _tbad.append(f"{f.name}:{m.group(1)}")
    (ok if not _tbad else bad)(
        f"문서의 재현 임계가 코드와 일치 (t≥{_R.T_MIN}) ({_tbad or '일치'})")

# ── [11] 판단층이 원장의 말을 짐작하지 않는가 ────────────────────────
#
# 검사가 못 보는 자리다. 합성 자료로 검증하면 자기 자신을 검증하기 때문이다 —
# 표를 만드는 쪽과 읽는 쪽이 같은 가정을 쓰면 둘 다 틀려도 통과한다.
#
# 진짜 원장은 날짜를 `"20260917"`, 시장·지수를 한글(`"코스닥"`)로 적는다.
# 판단층이 `"KOSDAQ"` 이나 ISO 날짜를 질의에 박으면 **모든 질의가 빈다.**
# 그리고 빈 결과는 '원장에 없습니다' 로 나간다 — 코드가 틀렸다는 말이 아니라
# 자료가 없다는 말로. 실제로 있었던 일이고, 오류는 한 줄도 나지 않았다.

print("\n[11] 판단층이 원장의 말을 짐작하지 않는가")

_AG = sorted((ROOT / "agents").glob("*.py"))
_SQLISH = re.compile(r'(?:SELECT|WHERE|ORDER BY|INSERT|VALUES)', re.I)
_hard = []
for f in _AG:
    if f.name == "dialect.py":
        continue                      # 별칭 표가 사는 곳이다
    for i, line in enumerate(f.read_text(encoding="utf-8").splitlines(), 1):
        if line.lstrip().startswith("#"):
            continue
        # SQLite 의 날짜 산술은 ISO 만 받는다. 원장은 ISO 가 아니다.
        if re.search(r"\bdate\(\s*\?", line):
            _hard.append(f"{f.name}:{i} SQLite date() 산술")
        # 질의 안의 영문 시장·지수 이름
        if _SQLISH.search(line) and re.search(r"KOSDAQ|KOSPI|KONEX", line):
            _hard.append(f"{f.name}:{i} 질의 안의 영문 시장 이름")
(ok if not _hard else bad)(
    f"질의가 원장의 형식을 짐작하지 않는다 ({_hard or '없음'})")

# 합성 원장이 진짜 원장의 형식으로 적히는가. 여기가 어긋나면 위의 모든 검사가
# 자기 가정을 다시 확인할 뿐이다.
_ISO_LIT = re.compile(r"""['"]\d{4}-\d{2}-\d{2}['"]""")
# 원장의 말로 바꿔 주는 것들. 이것을 거친 ISO 문자열은 표에 그대로 들어가지
# 않으므로 잡으면 안 된다 — 거짓 경보가 쌓이면 검사를 끄게 된다.
_WRAP = re.compile(r'(?:_d|D\.norm_date|D\.iso_date|D\.as_ledger_date|'
                   r'norm_date|as_ledger_date)\(\s*["\']'
                   r'[^"\']*["\']\s*\)')


def _stmt_at(txt: str, i: int) -> str:
    """`INSERT INTO` 가 들어 있는 execute() 호출 하나의 본문.

    줄 단위로 창을 잡으면 옆 줄의 상관없는 ISO 문자열까지 걸린다. 괄호가
    닫힐 때까지가 한 문장이다."""
    depth, j = 1, i
    while j < len(txt) and depth > 0:
        if txt[j] == "(":
            depth += 1
        elif txt[j] == ")":
            depth -= 1
        j += 1
    return txt[i:j]


_fix = []
for f in _AG:
    txt = f.read_text(encoding="utf-8")
    for m in re.finditer(r"INSERT INTO", txt):
        stmt = _WRAP.sub("", _stmt_at(txt, m.end()))
        if _ISO_LIT.search(stmt):
            _fix.append(f"{f.name}:{txt.count(chr(10), 0, m.start()) + 1}")
(ok if not _fix else bad)(
    f"합성 원장이 진짜 원장의 형식으로 적힌다 ({_fix or '전부 YYYYMMDD'})")

# ── [12] 상장 포트폴리오사만 보는가 ──────────────────────────────────
#
# 이 도구는 **시장 감시기가 아니다.** 우리가 들고 있는 상장 포트폴리오사의
# 회수 판단을 돕는 물건이고, 코스닥 전체는 배경이다 (리포트 §7).
#
# 측정층은 그 구분을 지킨다 — `_watchlist()` 가 주인공을 정한다. 판단층에는
# 그 구분이 없어서 트리거가 원장을 통째로 훑었다. 재 봤다: 코스닥 1,700종목
# 에서 하루 ±8% 이상 움직인 것이 37개, 그중 우리 것은 2개. 인스턴스 70개가
# 남의 회사에 쓰이고, 그 봉투가 회수 판단 리포트에 섞인다.
#
# 이 검사가 없으면 누군가 `codes=` 를 지워도 테스트는 전부 통과한다 —
# 합성 원장에는 우리 종목만 들어 있기 때문이다.

print("\n[12] 상장 포트폴리오사만 보는가")

_TRG = (ROOT / "agents" / "triggers.py").read_text(encoding="utf-8")
_SCOPED = ("scan_disclosures", "scan_price_moves", "scan_lockups",
           "scan_watch")
_unscoped = []
for _fn in _SCOPED:
    m = re.search(rf"def {_fn}\((.*?)\)\s*->", _TRG, re.S)
    if not m or "codes" not in m.group(1):
        _unscoped.append(f"{_fn}: codes 인자 없음")
        continue
    # 인자만 받고 안 쓰면 아무 일도 하지 않는다 — 본문에서 거르는지 본다
    body = _TRG[m.end():]
    body = body[:body.find("\ndef ")] if "\ndef " in body else body
    # 좁히는 방식은 둘이고 뜻이 다르다. `codes is not None` 은 목록이 있으면
    # 거른다는 것이고, `codes is None` 은 범위를 못 정했으면 아예 돌지 않는다는
    # 것이다(규칙 14). 뒤엣것이 더 엄하다 — 한쪽만 인정하면 더 엄한 쪽을 쓴
    # 스캐너가 '안 거른다'로 잡힌다. 인자를 쓰기만 하면 되는 게 아니라
    # **분기에 써야** 한다.
    if not any(p in body for p in ("codes is not None", "codes is None")):
        _unscoped.append(f"{_fn}: codes 를 받기만 하고 거르지 않음")
(ok if not _unscoped else bad)(
    f"종목 스캐너가 포트폴리오사로 좁힌다 ({_unscoped or '전부 좁힘'})")

# 범위를 못 정한 날이 '조용한 날'로 읽히면 안 된다.
(ok if '"scope"' in _TRG and "scope_row" in _TRG else bad)(
    "소집 산출이 범위를 밝힌다 (scope)")

# 종목코드는 대외비다 — 범위 산출에 실리면 안 된다.
_SCOPE_SRC = (ROOT / "agents" / "scope.py").read_text(encoding="utf-8")
# `scope_row` 가 아예 없으면 위 검사가 이미 잡는다. 여기서 쪼개다 터지면
# 감사가 **그 결함을 보고하지 못하고 죽는다** — 검사가 검사를 못 하게 된다.
_after = _TRG.split("scope_row")
(ok if len(_after) > 1 and '"codes"' not in _after[1][:400] else bad)(
    "범위 산출에 종목코드를 싣지 않는다")
(ok if "_watchlist" in _SCOPE_SRC else bad)(
    "범위는 측정층의 watchlist 파서를 쓴다")

# ── [13] 주가 모니터링이 사건 없이도 도는가 ──────────────────────────
#
# 트리거의 MOVE_PCT 는 **하루** 변동이다. 그것만 보면 천천히 빠지는 종목이
# 통째로 안 보인다 — 재 봤더니 6개월 -58%, 최악의 하루 -3.6%, 트리거 0건.
# 반토막이 나는 동안 아무도 안 봤다.
#
# 이 검사가 없으면 누군가 scan_watch 를 scan() 에서 빼도 테스트는 전부
# 통과한다. 합성 원장의 종목들은 얌전해서 어차피 안 걸리기 때문이다.

print("\n[13] 주가 모니터링이 사건 없이도 도는가")

import triggers as _TRG_MOD                        # noqa: E402
_TRIG_DESKS = set(_TRG_MOD.DESKS)
_W_ALL = (ROOT / "agents" / "watch.py").read_text(encoding="utf-8")
# **산출부만 본다.** 자체 검사에는 금지어 목록이 그대로 들어 있어서, 파일
# 전체를 낱말로 훑으면 검사가 자기 검사에 걸린다 — 같은 실수를 다섯 번 했다.
_W = _W_ALL.split("# ── 자체 검사")[0]
_T2 = (ROOT / "agents" / "triggers.py").read_text(encoding="utf-8")

(ok if "scan_watch(con, today, codes=codes)" in _T2 else bad)(
    "소집이 주가 모니터링을 부른다 (scan_watch)")

# 세 소집이 전부 실재하는 데스크로 가는가
_wr = re.search(r"WATCH_ROUTES\s*=\s*\{(.*?)\n\}", _T2, re.S)
_bad_route = []
if not _wr:
    _bad_route.append("WATCH_ROUTES 없음")
else:
    for _m in re.finditer(r'"([a-z0-9.]+)":\s*\(([^)]*)\)', _wr.group(1)):
        for _d in re.findall(r'"([a-z0-9-]+)"', _m.group(2)):
            if _d not in _TRIG_DESKS:
                _bad_route.append(f"{_m.group(1)}→{_d}")
(ok if not _bad_route else bad)(
    f"주가 모니터링 소집이 실재하는 데스크로 간다 ({_bad_route or '전부 실재'})")

# 임계가 사내 기준으로 표시되는가 — 논문·제도인 척하면 안 된다 (규칙 4)
(ok if '"grade": "사내"' in _W else bad)("임계가 사내 기준으로 표시된다")

# 재기만 하는가 — 산출 문자열에 판정 어휘가 없어야 한다 (규칙 1)
_judge = [w for w in ("매수", "매도", "추천", "목표가", "저평가", "고평가",
                      "비중확대")
          if re.search(rf'"[^"]*{w}[^"]*"', _W)]
(ok if not _judge else bad)(f"주가 모니터링에 판정 어휘가 없다 ({_judge or '없음'})")

print("\n" + "=" * 60)
if fails:
    print(f"실패 {len(fails)}건")
    for f in fails:
        print(f"  · {f}")
    raise SystemExit(1)
print(f"전부 통과 ({len(warns)}건 경고)" if warns else "전부 통과")
