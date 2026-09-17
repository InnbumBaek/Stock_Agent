"""판단층 — 측정층(stock-monitor/ki_monitor.py)을 감싸기만 하고 손대지 않는다.

측정층은 재고, 이 층은 그것을 읽어 문장으로 만든다. 두 층 사이에 관문이 있다.

    envelope.py       모든 주장이 입는 형식 (측정값 + 등급 + 가정 + 한계)
    papers.py         논문 장부 ki.papers/2 — 네 상태 · append-only
    replication.py    재현 러너. 결정적이다 — LLM 을 쓰지 않는다
    gates.py          게이트 ①~⑦. 통과 아니면 반려다
    ki_ledger_mcp.py  원장을 읽는 MCP 서버. 쓰기 도구가 없다

ki_monitor.py 는 열지 않는다. CRLF 파일이라 편집 도구가 줄바꿈을 바꾸면 파일
전체가 diff 에 잡히고, 실제 변경이 그 안에 묻힌다.
"""
