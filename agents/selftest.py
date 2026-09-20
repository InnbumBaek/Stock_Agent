"""판단층 전체 자체 검사 — 키도 네트워크도 원장도 없이 돈다.

    python agents/selftest.py

측정층의 128개와 나란히 돌린다. 검증이 두 곳으로 갈라지면 한쪽은 곧 안 돌게
된다.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import cycle                                             # noqa: E402
import dialect                                           # noqa: E402
import dispatch                                          # noqa: E402
import envelope                                          # noqa: E402
import eventstudy                                        # noqa: E402
import gates                                             # noqa: E402
import ki_ledger_mcp                                     # noqa: E402
import papers                                            # noqa: E402
import reconcile                                         # noqa: E402
import replay                                            # noqa: E402
import replication                                       # noqa: E402
import run_day                                           # noqa: E402
import scope                                             # noqa: E402
import scorecard                                         # noqa: E402
import triggers                                          # noqa: E402

# `dialect` 가 맨 앞이다. 원장의 형식을 잘못 짚으면 그 아래 전부가 '원장에
# 없습니다' 를 내는데, 그 문장은 코드가 틀렸다는 뜻이 아니라 자료가 없다는
# 뜻으로 읽힌다 — 이 줄이 실패하면 아래의 통과는 뜻이 없다.
MODULES = (dialect, scope, envelope, papers, replication, eventstudy, gates,
           triggers, ki_ledger_mcp, dispatch, cycle, reconcile, run_day,
           scorecard, replay)


def main() -> int:
    rc = 0
    for m in MODULES:
        rc |= m.selftest()
    print("─" * 46)
    print("전부 통과" if rc == 0 else "실패가 있습니다")
    return rc


if __name__ == "__main__":
    sys.exit(main())
