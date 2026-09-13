@echo off
rem  RUN_ALL.cmd 와 같은 것을 부릅니다.
rem
rem  왜 둘인가: .cmd 연결이 깨져 있거나 정책이 .cmd 만 막는 컴퓨터가 있습니다.
rem  그런 자리에서는 더블클릭해도 아무 반응이 없는데, 오류도 안 납니다.
rem  .bat 은 다른 연결을 타므로 그때 이쪽이 열립니다. 내용은 없습니다 —
rem  진짜 일은 전부 RUN_ALL.cmd 가 합니다.
call "%~dp0RUN_ALL.cmd" %*
