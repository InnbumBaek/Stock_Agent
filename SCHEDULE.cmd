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
  echo  [X] 압축 파일 안에서 바로 실행하신 것 같습니다.
  echo.
  echo      지금 위치 : %~dp0
  echo      찾는 파일 : RUN_ALL.cmd  ^(없습니다^)
  echo.
  echo      zip 을 폴더에 먼저 **푸신 뒤**, 풀린 폴더 안의
  echo      SCHEDULE.cmd 를 실행하십시오.
  echo      예^) C:\Users\%USERNAME%\Stock-Agent\SCHEDULE.cmd
  echo.
  pause
  exit /b 1
)


rem ===========================================================
rem  평일 자동 실행을 등록하거나 해제합니다.
rem
rem  등록되는 것은 둘이고, 둘 다 RUN_ALL.cmd 를 부릅니다.
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

echo.
echo  ===============================================
echo   Stock-Agent 자동 실행
echo  ===============================================
echo.
echo   07:30  논문 수확 + 문헌 심사  ^(평일 매일 . 대개 몇 초^)
echo   08:50  아침 리포트 생성  ^(평일 매일 . 비용 없음^)
echo   16:10  장 마감 시세 적재  ^(평일 매일^)
echo.
echo   월 07:40  주간 논문 재현  ^(월요일만 . 네트워크 . 키 불필요^)
echo.
echo   월요일 회의 자료는 금요일 밤에 이미 완성됩니다.
echo   월요일 08:50 은 그것을 리포트로 찍어 내기만 합니다.
echo.
echo   지금 위치: %~dp0
echo   ^(폴더를 옮기셔도 RUN_ALL.cmd 가 다음에 돌 때 알아서 고칩니다^)
echo.
echo   [1] 등록   [2] 해제   [3] 지금 상태만 보기   [4] 그만두기
echo.
choice /C 1234 /N /M "  번호를 누르십시오: "
if errorlevel 4 goto :end
if errorlevel 3 goto :show
if errorlevel 2 goto :remove

rem ---------------------------------------------------------- 등록
:install
echo.
schtasks /Create /TN "StockAgent-Papers" /TR "\"%~dp0RUN_ALL.cmd\" papers" ^
  /SC WEEKLY /D MON,TUE,WED,THU,FRI /ST 07:30 /F
if errorlevel 1 goto :failed

schtasks /Create /TN "StockAgent-Morning" /TR "\"%~dp0RUN_ALL.cmd\" morning" ^
  /SC WEEKLY /D MON,TUE,WED,THU,FRI /ST 08:50 /F
if errorlevel 1 goto :failed

schtasks /Create /TN "StockAgent-AfterClose" /TR "\"%~dp0RUN_ALL.cmd\" close" ^
  /SC WEEKLY /D MON,TUE,WED,THU,FRI /ST 16:10 /F
if errorlevel 1 goto :failed

schtasks /Create /TN "StockAgent-Cycle" /TR "\"%~dp0RUN_ALL.cmd\" cycle" ^
  /SC WEEKLY /D MON /ST 07:40 /F
if errorlevel 1 goto :failed

echo.
echo  ===============================================
echo   등록됐습니다.
echo  ===============================================
echo.
echo   기록:  logs 폴더 ^(-papers.log . -morning.log . -close.log^)
echo   해제:  이 파일을 다시 열어 [2]
echo.
echo   * 컴퓨터가 꺼져 있으면 그 시각은 건너뜁니다.
echo     ^(켜져 있고 로그인돼 있어야 돕니다^)
echo   * 논문 심사는 하루 최대 한 해만 봅니다. 새 후보가 없는 날은
echo     아무것도 하지 않습니다 ^(그게 정상입니다^).
echo   * 원장이 아직 없다면 RUN_ALL.cmd 를 한 번 끝까지 돌리십시오.
echo     원장이 있어야 아침 리포트가 나옵니다.
echo.
echo   지금 한 번 돌려서 되는지 보시겠습니까?
choice /C YN /M "  아침 작업을 지금 실행"
if errorlevel 2 goto :end
schtasks /Run /TN "StockAgent-Morning"
echo.
echo   실행했습니다. logs 폴더의 오늘 날짜 -morning.log 를 열어 보십시오.
goto :end

rem ---------------------------------------------------------- 해제
:remove
echo.
schtasks /Delete /TN "StockAgent-Papers" /F
schtasks /Delete /TN "StockAgent-Morning" /F
schtasks /Delete /TN "StockAgent-AfterClose" /F
schtasks /Delete /TN "StockAgent-Cycle" /F
echo.
echo  해제했습니다. RUN_ALL.cmd 는 그대로 남아 있으니
echo  손으로는 계속 쓸 수 있습니다.
goto :end

rem ---------------------------------------------------------- 상태
:show
echo.
schtasks /Query /TN "StockAgent-Papers" 2>nul
if errorlevel 1 echo   논문 작업: 등록돼 있지 않습니다.
echo.
schtasks /Query /TN "StockAgent-Morning" 2>nul
if errorlevel 1 echo   아침 작업: 등록돼 있지 않습니다.
echo.
schtasks /Query /TN "StockAgent-AfterClose" 2>nul
if errorlevel 1 echo   마감 작업: 등록돼 있지 않습니다.
echo.
schtasks /Query /TN "StockAgent-Cycle" 2>nul
if errorlevel 1 echo   주간 재현: 등록돼 있지 않습니다.
goto :end

rem ---------------------------------------------------------- 실패
:failed
echo.
echo  [X] 등록에 실패했습니다.
echo      이 창을 관리자 권한으로 다시 열어 보십시오.
echo      ^(파일 우클릭 - 관리자 권한으로 실행^)

:end
echo.
pause
