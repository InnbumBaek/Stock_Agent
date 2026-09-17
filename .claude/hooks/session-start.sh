#!/bin/bash
# 세션 시작 훅 — 이 저장소를 만지는 데 필요한 것을 깔아 둔다.
#
# 왜 있나: 컨테이너는 매 세션 새로 뜨고, 그때마다 같은 것을 다시 깔았다.
#   · pandas/numpy/scipy/lxml 없으면 selftest 자체가 안 돈다
#   · libreoffice-impress 없으면 pptx 를 눈으로 확인할 수 없고,
#     "파일이 깨졌나"를 진단하는 데 왕복이 몇 번 든다
#   · pptxgenjs 는 스크래치패드에만 있어서 세션이 끝나면 사라진다
#
# 원칙: 여러 번 돌려도 같다(idempotent). 이미 있으면 건너뛴다.
#       선택 의존성이 실패해도 세션을 막지 않는다.
set -uo pipefail

# 원격(Claude Code on the web)에서만 돈다. 로컬 개발 환경은 건드리지 않는다.
if [ "${CLAUDE_CODE_REMOTE:-}" != "true" ]; then
  exit 0
fi

log() { printf '[session-start] %s\n' "$*" >&2; }

# ── 1. 파이썬 ─────────────────────────────────────────────────────────
# ki_monitor.py 가 요구하는 것 + 저장소 도구가 쓰는 것.
PY_REQUIRED="pandas numpy scipy requests jinja2 lxml defusedxml"
PY_TOOLING="Pillow python-pptx"

need_py=""
for mod in pandas numpy scipy requests jinja2 lxml defusedxml PIL pptx; do
  python3 -c "import $mod" >/dev/null 2>&1 || need_py="yes"
done

if [ -n "$need_py" ]; then
  log "파이썬 패키지 설치"
  pip3 install --quiet --disable-pip-version-check $PY_REQUIRED $PY_TOOLING \
    || log "경고: 파이썬 패키지 일부 설치 실패"
else
  log "파이썬 패키지 이미 있음"
fi

# weasyprint 는 선택이다 — 없으면 ki_monitor 가 자체 조판으로 HTML 을 만든다.
# 시스템 라이브러리(cairo·pango)를 끌고 오므로 실패해도 넘어간다.
python3 -c "import weasyprint" >/dev/null 2>&1 \
  || pip3 install --quiet --disable-pip-version-check weasyprint >/dev/null 2>&1 \
  || log "weasyprint 없음 (PDF 출력만 영향, HTML 리포트는 정상)"

# ── 2. 문서/덱 확인 도구 ──────────────────────────────────────────────
# pptx 는 눈으로 봐야 검증된다: soffice 로 PDF, pdftoppm 으로 PNG.
# fonts-noto-cjk 가 없으면 한글이 전부 두부(□)로 렌더된다.
APT_NEED=""
for pkg in libreoffice-impress poppler-utils fonts-noto-cjk; do
  dpkg -s "$pkg" >/dev/null 2>&1 || APT_NEED="$APT_NEED $pkg"
done

if [ -n "$APT_NEED" ]; then
  log "apt 설치:$APT_NEED"
  export DEBIAN_FRONTEND=noninteractive
  apt-get update -qq >/dev/null 2>&1 || log "경고: apt-get update 실패"
  apt-get install -y -qq $APT_NEED >/dev/null 2>&1 \
    || log "경고: apt 설치 실패 ($APT_NEED) — pptx 렌더 확인이 안 될 수 있음"
else
  log "apt 패키지 이미 있음"
fi

# ── 3. 노드 ───────────────────────────────────────────────────────────
# docs/agentization/build_deck.js 가 pptxgenjs 를 require 한다.
# 저장소 안에 node_modules 를 만들지 않는다 — 전역에 깔고 NODE_PATH 로 잡는다.
NODE_GLOBAL="$(npm root -g 2>/dev/null || true)"
if [ -n "$NODE_GLOBAL" ] && [ ! -d "$NODE_GLOBAL/pptxgenjs" ]; then
  log "pptxgenjs 설치"
  npm install -g --silent pptxgenjs@4 >/dev/null 2>&1 \
    || log "경고: pptxgenjs 설치 실패 — 덱 재빌드 불가"
fi

# ── 4. 세션 환경변수 ──────────────────────────────────────────────────
if [ -n "${CLAUDE_ENV_FILE:-}" ]; then
  [ -n "$NODE_GLOBAL" ] && echo "export NODE_PATH=\"$NODE_GLOBAL\"" >> "$CLAUDE_ENV_FILE"
  # 픽셀 스프라이트 경로 — build_deck.js 가 PX_DIR 을 본다.
  echo "export PX_DIR=\"${CLAUDE_PROJECT_DIR:-$PWD}/docs/agentization/sprites\"" >> "$CLAUDE_ENV_FILE"
fi

log "완료"
exit 0
