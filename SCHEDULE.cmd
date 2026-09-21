@echo off
chcp 65001 >nul 2>&1
title Stock-Agent - 자동 실행
cd /d "%~dp0"

rem  ---- 압축을 풀지 않고 안에서 그대로 실행한 경우 -------------------
rem  탐색기·반디집·알집은 더블클릭한 .cmd **하나만** %TEMP% 에 풀어서
rem  실행한다. 옆에 있어야 할 폴더가 통째로 없으니, 안내도 없이
rem  node 가 "Cannot find module ...\BNZ.xxxx\server\server.js" 스택을
rem  토하고 끝난다. 그 화면으로는 원인을 알 수 없어서 여기서 먼저 잡는다.
if not exist "%~dp0RUN_ALL.cmd" (
  echo.
  echo  [X] 압축 파일 안에서 바로 실행하신 것 같습니다 - 폴더에 먼저 푸십시오.
  echo      지금 위치 : %~dp0
  echo      찾는 파일 : RUN_ALL.cmd  ^(없습니다^)
  echo      예^) C:\Users\%USERNAME%\Stock-Agent\SCHEDULE.cmd
  echo.
  pause
  exit /b 1
)


rem ===========================================================
rem  평일 자동 실행을 등록하거나 해제합니다.
rem
rem  등록되는 것은 넷이고, 넷 다 RUN_ALL.cmd 를 부릅니다.
rem
rem    07:30  RUN_ALL.cmd papers    논문 수확 + 채택 (하루 최대 1편)
rem    08:50  RUN_ALL.cmd morning   리포트만 (비용 없음)
rem    16:10  RUN_ALL.cmd close     시세 적재
rem
rem  월요일에만 하나 더 돕니다.
rem
rem    월 07:40  RUN_ALL.cmd cycle   주간 논문 재현 (주 3편 상한)
rem
rem  폴더를 옮기면 등록된 경로가 어긋납니다. 다만 RUN_ALL.cmd 가
rem  돌 때마다 그것을 확인하고 알아서 다시 등록하므로, 보통은
rem  손댈 일이 없습니다.
rem ===========================================================

rem  여는 화면은 **표가 전부**다. 시각과 무엇이 도는지 말고는 다 뺐다.
rem  "월요일 회의 자료는 금요일 밤에 완성됩니다" 는 지운 것이 아니라
rem  **틀린 것이었다** - 금요일 밤에 도는 작업이 없다. 평일 08:50 이 매일
rem  찍는다. 낡은 약속을 화면에 남겨 두면 줄여도 읽을 값이 없다.
echo.
echo   Stock-Agent 자동 실행        %~dp0
echo.
echo     평일 07:30   논문 수확 · 채택     하루 최대 1편
echo     평일 08:50   아침 리포트
echo     평일 16:10   장 마감 시세 적재
echo     월   07:40   주간 논문 재현       주 3편 상한
echo.
choice /C 1234 /N /M "  [1] 등록  [2] 해제  [3] 상태  [4] 그만두기 : "
if errorlevel 4 goto :end
if errorlevel 3 goto :show
if errorlevel 2 goto :remove

rem ---------------------------------------------------------- 등록
:install
rem  schtasks 는 성공할 때마다 "성공: 예약 작업 ..." 을 한 줄씩 찍는다.
rem  네 개면 네 줄이고, 전부 같은 말이다. 감추고 errorlevel 만 본다.
rem  실패하면 :failed 가 크게 말한다.
schtasks /Create /TN "StockAgent-Papers" /TR "\"%~dp0RUN_ALL.cmd\" papers" ^
  /SC WEEKLY /D MON,TUE,WED,THU,FRI /ST 07:30 /F >nul
if errorlevel 1 goto :failed

schtasks /Create /TN "StockAgent-Morning" /TR "\"%~dp0RUN_ALL.cmd\" morning" ^
  /SC WEEKLY /D MON,TUE,WED,THU,FRI /ST 08:50 /F >nul
if errorlevel 1 goto :failed

schtasks /Create /TN "StockAgent-AfterClose" /TR "\"%~dp0RUN_ALL.cmd\" close" ^
  /SC WEEKLY /D MON,TUE,WED,THU,FRI /ST 16:10 /F >nul
if errorlevel 1 goto :failed

schtasks /Create /TN "StockAgent-Cycle" /TR "\"%~dp0RUN_ALL.cmd\" cycle" ^
  /SC WEEKLY /D MON /ST 07:40 /F >nul
if errorlevel 1 goto :failed

rem  남긴 세 줄은 전부 "모르면 잘못 읽는 것" 이다. 꺼져 있으면 건너뛴다는
rem  것, 아무것도 안 한 날이 정상이라는 것, 원장이 먼저라는 것. 나머지
rem  안내는 docs\RUN.md 에 있다.
echo.
echo   등록됐습니다. 기록은 logs 폴더에, 해제는 이 파일 [2] 번.
echo.
echo   * 컴퓨터가 꺼져 있으면 그 시각은 건너뜁니다.
echo   * 새 논문 후보가 없는 날은 아무것도 하지 않습니다 ^(정상입니다^).
echo   * 원장이 없으면 아침 리포트가 안 나옵니다 - RUN_ALL.cmd 를 한 번 끝까지.
echo.
choice /C YN /M "  지금 아침 작업을 한 번 돌려 볼까요"
if errorlevel 2 goto :end
schtasks /Run /TN "StockAgent-Morning" >nul
echo   실행했습니다 - logs 폴더의 오늘 -morning.log 를 보십시오.
goto :end

rem ---------------------------------------------------------- 해제
:remove
rem  없는 작업을 지우면 schtasks 가 오류를 뱉는다. 처음부터 절반만 걸려
rem  있던 경우에 그 오류가 "해제 실패" 로 읽힌다 - 실제로는 지울 것이
rem  없었을 뿐이다. 그래서 지울 때는 조용히 지운다.
rem
rem  다만 **조용히 지우고 "해제했습니다" 라고 말하면 안 된다.** 권한이
rem  없어 못 지운 날에도 같은 줄이 나가고, 그러면 사람은 해제된 줄 알고
rem  창을 닫는다. 줄이는 것과 없는 것을 있다고 말하는 것은 다르다.
rem  지운 뒤에 **다시 물어보고** 남아 있으면 남아 있다고 한다.
schtasks /Delete /TN "StockAgent-Papers" /F >nul 2>&1
schtasks /Delete /TN "StockAgent-Morning" /F >nul 2>&1
schtasks /Delete /TN "StockAgent-AfterClose" /F >nul 2>&1
schtasks /Delete /TN "StockAgent-Cycle" /F >nul 2>&1
set "LEFT="
schtasks /Query /TN "StockAgent-Papers" >nul 2>&1 && set "LEFT=1"
schtasks /Query /TN "StockAgent-Morning" >nul 2>&1 && set "LEFT=1"
schtasks /Query /TN "StockAgent-AfterClose" >nul 2>&1 && set "LEFT=1"
schtasks /Query /TN "StockAgent-Cycle" >nul 2>&1 && set "LEFT=1"
echo.
if defined LEFT goto :remove_left
echo   해제했습니다. RUN_ALL.cmd 는 그대로라 손으로는 계속 쓰실 수 있습니다.
goto :end
:remove_left
echo   [X] 일부가 아직 남아 있습니다 - 이 파일을 관리자 권한으로 다시 여십시오.
echo       [3] 번으로 어느 것이 남았는지 보실 수 있습니다.
goto :end

rem ---------------------------------------------------------- 상태
:show
rem  /Query 는 작업 하나에 머리글까지 표를 한 벌씩 찍는다. 네 개면 십수
rem  줄인데, 여기서 알고 싶은 것은 **걸려 있나 아닌가** 한 가지다.
echo.
call :state Papers     "평일 07:30  논문 수확 · 채택"
call :state Morning    "평일 08:50  아침 리포트    "
call :state AfterClose "평일 16:10  장 마감 적재   "
call :state Cycle      "월   07:40  주간 논문 재현 "
goto :end

:state
set "ST=등록 안 됨"
schtasks /Query /TN "StockAgent-%~1" >nul 2>&1
if not errorlevel 1 set "ST=등록됨"
echo   %~2   %ST%
exit /b 0

rem ---------------------------------------------------------- 실패
:failed
echo.
echo   [X] 등록에 실패했습니다 - 이 파일을 우클릭해 관리자 권한으로 여십시오.

:end
echo.
pause
