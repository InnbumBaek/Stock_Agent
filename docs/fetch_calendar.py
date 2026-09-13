"""매크로 캘린더가 바닥나기 전에 알려 준다.

금통위·FOMC 일정은 **공개 API 가 없습니다.** 기관이 연 1회 보도자료로 공표하고,
그걸 사람이 읽어 `stock-monitor/.calendar.json` 에 적습니다. 그래서 이 스크립트는
가져오지 않습니다 — **얼마나 남았는지 세고, 바닥나기 전에 말해 줍니다.**

가져올 수 없는 것을 가져온 척하지 않는 것이 이 프로젝트의 규율입니다. 대신
언제 무엇을 해야 하는지는 정확히 알려 줍니다.

    python docs/fetch_calendar.py             남은 일정 현황
    python docs/fetch_calendar.py --days 120  그 기간 안의 일정

RUN_ALL.cmd papers (평일 07:30) 가 이것을 함께 돌립니다. 일정이 60일 미만으로
남으면 화면과 기록에 경고가 뜹니다.
"""
import argparse
import io
import json
import sys
from datetime import date
from pathlib import Path

P = Path(__file__).resolve().parent.parent / "stock-monitor" / ".calendar.json"

WHERE = {
    "bok": ("한국은행 금융통화위원회",
            "bok.or.kr → 뉴스/자료 → 보도자료에서 "
            "'금융통화위원회 정기회의 개최 및 의사록 공개 예정일정' 검색 "
            "(보통 전년 10~11월 공표)"),
    "fomc": ("미 연방공개시장위원회",
             "federalreserve.gov/monetarypolicy/fomccalendars.htm "
             "(보통 1~2년치가 미리 올라와 있습니다)"),
}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--days", type=int, default=90, help="이 기간 안의 일정도 함께")
    a = ap.parse_args()

    try:
        doc = json.loads(io.open(P, encoding="utf-8").read())
    except (OSError, ValueError) as e:
        print(f"캘린더 파일을 읽지 못했습니다: {P.name} ({e})", file=sys.stderr)
        return 1

    today = date.today()
    print(f"오늘 {today}  ·  확인 시점 {doc.get('verified', '?')}")
    print("-" * 62)

    warn = 0
    for key, src in (doc.get("sources") or {}).items():
        future = []
        for item in src.get("events") or []:
            try:
                d = date.fromisoformat(item[0])
            except (ValueError, TypeError, IndexError):
                continue
            if d >= today:
                future.append((d, item[1]))
        future.sort()
        name = src.get("기관", key)
        if not future:
            print(f"  X  {name}")
            print(f"       **남은 일정이 없습니다.** 새로 채워야 합니다.")
            warn += 1
        else:
            last = future[-1][0]
            left = (last - today).days
            mark = "!" if left < 60 else "O"
            if left < 60:
                warn += 1
            print(f"  {mark}  {name:<24} 남은 {len(future)}건 · "
                  f"마지막 {last} (D+{left})")
            nxt = future[0]
            print(f"       다음: {nxt[0]}  {nxt[1]}  (D-{(nxt[0] - today).days})")
        if not future or (future and (future[-1][0] - today).days < 60):
            who, how = WHERE.get(key, (name, "기관 홈페이지에서 확인하십시오"))
            print(f"       채우는 곳: {how}")

    print("-" * 62)
    if warn:
        print(f"{warn}곳이 60일 안에 바닥납니다. .calendar.json 에 새 일정을 적고")
        print("verified 날짜와 확인 출처를 함께 갱신하십시오.")
        return 1
    print("여유 있습니다.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
