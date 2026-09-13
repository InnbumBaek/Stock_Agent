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
_i_shallow = _ra3.find("ki_monitor.py import-keys\r")
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
print(f"     실제: selftest {n_py}")
n_js = n_py
for p in ["README.md", "docs/RUN.md", "CLAUDE.md", "stock-monitor/README.md"]:
    txt = (ROOT / p).read_text(encoding="utf-8")
    stale = []
    for m in re.finditer(r"(\d+)개", txt):
        v = int(m.group(1))
        if 60 <= v <= 400 and v not in (n_py, n_js):
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

print("\n" + "=" * 60)
if fails:
    print(f"실패 {len(fails)}건")
    for f in fails:
        print(f"  · {f}")
    raise SystemExit(1)
print(f"전부 통과 ({len(warns)}건 경고)" if warns else "전부 통과")
