"""판단층 전체 자체 검사 — 키도 네트워크도 원장도 없이 돈다.

    python agents/selftest.py

측정층의 128개와 나란히 돌린다. 검증이 두 곳으로 갈라지면 한쪽은 곧 안 돌게
된다.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import envelope                                          # noqa: E402
import gates                                             # noqa: E402
import ki_ledger_mcp                                     # noqa: E402
import papers                                            # noqa: E402
import replication                                       # noqa: E402

MODULES = (envelope, papers, replication, gates, ki_ledger_mcp)


def main() -> int:
    rc = 0
    for m in MODULES:
        rc |= m.selftest()
    print("─" * 46)
    print("전부 통과" if rc == 0 else "실패가 있습니다")
    return rc


if __name__ == "__main__":
    sys.exit(main())
