@echo off
chcp 65001 >nul 2>&1
setlocal enabledelayedexpansion
title Stock-Agent - 전체 실행
cd /d "%~dp0"

rem  ---- 압축을 풀지 않고 안에서 그대로 실행한 경우 -------------------
rem  탐색기·반디집·알집은 더블클릭한 .cmd **하나만** %TEMP% 에 풀어서
rem  실행한다. 옆에 있어야 할 폴더가 통째로 없으니, 안내도 없이
rem  파이썬이 "그런 파일이 없습니다" 만 뱉고 끝난다. 그 화면으로는 원인을
rem  알 수 없어서 여기서 먼저 잡는다.
if not exist "%~dp0stock-monitor\ki_monitor.py" (
  echo.
  echo  [X] 압축 파일 안에서 바로 실행하신 것 같습니다 - 폴더에 먼저 푸십시오.
  echo      지금 위치 : %~dp0
  echo      찾는 파일 : stock-monitor\ki_monitor.py  ^(없습니다^)
  echo      예^) C:\Users\%USERNAME%\Stock-Agent\RUN_ALL.cmd
  echo.
  pause
  exit /b 1
)


rem ===========================================================
rem  전체 과정을 한 번에 돌립니다.
rem
rem    RUN_ALL.cmd          물어보면서 진행 (처음이면 이것)
rem    RUN_ALL.cmd auto     묻지 않고 끝까지
rem
rem  중간에 죽어도 다시 돌리면 이어서 갑니다. 원장이 이미 있으면
rem  40분짜리 최초 적재를 다시 하지 않고 하루치만 갱신합니다.
rem
rem  ---- 아래 둘은 SCHEDULE.cmd 가 부르는 것입니다. 손으로 누를
rem       일은 없지만, 자동 실행이 하는 일을 직접 확인하고 싶으면
rem       그대로 쳐 보셔도 됩니다.
rem
rem    RUN_ALL.cmd morning  리포트만 만든다          (평일 08:50)
rem    RUN_ALL.cmd close    시세 적재 + 금요일 분석   (평일 16:10)
rem    RUN_ALL.cmd papers   논문 수확 + 문헌 심사     (평일 07:30)
rem    RUN_ALL.cmd cycle    주간 논문 재현 사이클     (월요일 07:40)
rem
rem  대상 시장을 바꾸려면 아래 MARKET 을 KOSPI 로 고치십시오.
rem  네 갈래 전부 이 한 줄을 씁니다.
rem ===========================================================
set MARKET=KOSDAQ
set MODE=%~1
if "%MODE%"=="" set MODE=ask

if not exist logs mkdir logs
for /f %%i in ('powershell -NoProfile -Command "Get-Date -Format yyyyMMdd-HHmmss"') do set STAMP=%%i
set LOGNAME=runall
if /I "%MODE%"=="morning" set LOGNAME=morning
if /I "%MODE%"=="close" set LOGNAME=close
if /I "%MODE%"=="papers" set LOGNAME=papers
if /I "%MODE%"=="cycle" set LOGNAME=cycle
set LOG=%~dp0logs\%STAMP%-%LOGNAME%.log

where python >nul 2>&1
if errorlevel 1 (set PY=py) else (set PY=python)

rem ---------------------------------------------------------------
rem  등록된 자동 실행이 옛 경로를 가리키면 여기서 조용히 고칩니다.
rem
rem  작업 스케줄러에는 파일의 전체 경로가 박힙니다. 폴더를 옮기거나
rem  실행기 이름이 바뀌면 그 경로가 어긋나는데, 어긋난 채로도 오류가
rem  안 납니다 - 그냥 08:50 에 아무 일도 일어나지 않습니다. 월요일
rem  아침에 리포트가 없는 것으로만 알게 됩니다.
rem
rem  그래서 돌릴 때마다 확인하고, 어긋나 있으면 다시 등록합니다.
rem  등록한 적이 없으면 아무것도 하지 않습니다 - 묻지도 않은 자동
rem  실행을 몰래 걸어 두지는 않습니다.
rem ---------------------------------------------------------------
schtasks /Query /TN "StockAgent-Morning" >nul 2>&1
if errorlevel 1 goto :sched_done
schtasks /Query /TN "StockAgent-Morning" /FO LIST /V 2>nul | find /I "%~dp0RUN_ALL.cmd" >nul
if not errorlevel 1 goto :sched_done
schtasks /Create /TN "StockAgent-Morning" /TR "\"%~dp0RUN_ALL.cmd\" morning" /SC WEEKLY /D MON,TUE,WED,THU,FRI /ST 08:50 /F >nul 2>&1
schtasks /Create /TN "StockAgent-AfterClose" /TR "\"%~dp0RUN_ALL.cmd\" close" /SC WEEKLY /D MON,TUE,WED,THU,FRI /ST 16:10 /F >nul 2>&1
schtasks /Create /TN "StockAgent-Papers" /TR "\"%~dp0RUN_ALL.cmd\" papers" /SC WEEKLY /D MON,TUE,WED,THU,FRI /ST 07:30 /F >nul 2>&1
schtasks /Create /TN "StockAgent-Cycle" /TR "\"%~dp0RUN_ALL.cmd\" cycle" /SC WEEKLY /D MON /ST 07:40 /F >nul 2>&1
if errorlevel 1 (
  call :say "     [알림] 자동 실행이 옛 경로를 가리킵니다. 다시 등록하지 못했습니다."
  call :say "            SCHEDULE.cmd 를 관리자 권한으로 한 번 열어 주십시오."
) else (
  call :say "     자동 실행이 옛 경로를 가리켜 다시 등록했습니다."
)
:sched_done

rem  키 폴더는 모드 분기보다 **먼저** 정한다. 자동 갈래도 claude 장기 토큰을
rem  여기서 읽어야 하는데, 예전에는 이 줄이 분기 뒤에 있어서 스케줄러가 부른
rem  런은 토큰을 못 봤다. 금요일 16:10 분석이 통째로 로그아웃으로 끝났다.
set "KEYDIR=%USERPROFILE%\Stock-Agent-keys"
if defined STOCK_AGENT_KEYS set "KEYDIR=%STOCK_AGENT_KEYS%"

rem  스케줄러가 부르는 두 갈래는 사람에게 물어보지 않고 곧장 갑니다.
if /I "%MODE%"=="morning" goto :auto_morning
if /I "%MODE%"=="close" goto :auto_close
if /I "%MODE%"=="papers" goto :auto_papers
if /I "%MODE%"=="cycle" goto :auto_cycle

call :say ""
call :say "  Stock-Agent 전체 실행   (기록: logs\%STAMP%-runall.log)"

rem ---------------------------------------------------------- 1/5 환경
call :stage "1/5" "환경 · 키 · 감시 종목"
%PY% --version >nul 2>&1
if errorlevel 1 (
  call :fail "파이썬을 찾지 못했습니다." "python.org 에서 설치(Add to PATH 켜기) 후 창을 새로 여십시오."
  goto :end
)
%PY% -m pip install --quiet pandas numpy scipy requests lxml >> "%LOG%" 2>&1
if errorlevel 1 (
  call :fail "파이썬 패키지 설치 실패" "logs 폴더의 오늘 기록을 보십시오."
  goto :end
)

rem -- 키는 저장소 바깥에 둔다.
rem
rem  .gitignore 로 막는 방법도 있지만 그건 약하다 - git add -f 한 번이면 뚫린다.
rem  아예 저장소 밖이면 실수로 커밋할 경로 자체가 없다. 옮기는 것은 키뿐이고,
rem  원장·워치리스트·포지션·리포트는 원래 자리 그대로다.
rem
rem  키가 없으면 **먼저 찾아본다.** 쓰던 .env 가 이미 있는데 못 찾아서
rem  "키를 넣으십시오"라고 말하는 것이 가장 흔한 헛걸음이다.
set "KEYDIR=%USERPROFILE%\Stock-Agent-keys"
if defined STOCK_AGENT_KEYS set "KEYDIR=%STOCK_AGENT_KEYS%"
call :keys
call :data

rem ---------------------------------------------------------- 2/5 API
call :stage "2/5" "API 진단"
pushd stock-monitor
%PY% ki_monitor.py diagnose > "%TEMP%\sa_diag.txt" 2>&1
set DIAG=%ERRORLEVEL%
popd
rem  진단은 다섯 줄을 전부 찍었다. 다 정상인 날에도 다섯 줄이라 매일 같고,
rem  그래서 막힌 줄이 그 사이에 묻힌다. 화면에는 **막힌 줄(X)만** 올린다 -
rem  다 정상이면 한 줄도 안 나온다. 기록에는 언제나 전부 남는다.
rem
rem  건너뛴 줄(-)은 안 올린다. 그건 "키가 없어 안 부름"이라 사건이 아니라
rem  설정이고, 매일 같은 세 줄이 되어 정작 X 를 가린다. 그 결과는 리포트의
rem  해당 절이 사유와 함께 비는 것으로 나온다 (규칙 3).
type "%TEMP%\sa_diag.txt" >> "%LOG%" 2>&1
if not "%DIAG%"=="0" (
  type "%TEMP%\sa_diag.txt"
  call :fail "필수 API 를 부르지 못했습니다." "위 진단을 보십시오. 전부 막혀 있으면 사내 방화벽입니다 - docs\NETWORK.md 를 전산팀에 주십시오."
  goto :end
)
findstr /C:"  X  " "%TEMP%\sa_diag.txt"

rem ---------------------------------------------------------- 3/5 원장
call :stage "3/5" "원장"
if exist "stock-monitor\ki.sqlite" (
  rem  daily 는 하루치만 넣는다. 며칠 걸렀다가 돌리면 그 사이가 빈 채로 남고,
  rem  몇 주 묵은 종가가 최신 종가 행세를 한다. 화면에는 "원장 갱신" 만 찍혀서
  rem  아무도 모른다 — 그래서 catchup 이 잰 것을 화면에 그대로 띄운다.
  pushd stock-monitor
  %PY% ki_monitor.py catchup --market %MARKET% > "%TEMP%\sa_cu.txt" 2>&1
  %PY% ki_monitor.py daily --market %MARKET% >> "%LOG%" 2>&1
  popd
  type "%TEMP%\sa_cu.txt"
  type "%TEMP%\sa_cu.txt" >> "%LOG%" 2>&1
) else (
  call :say "     처음입니다 - 최초 적재에 약 40분. 창을 닫지 마십시오 (한 번만 합니다)."
  pushd stock-monitor
  %PY% ki_monitor.py ingest --from 20250101 --universe KOSDAQ >> "%LOG%" 2>&1
  if errorlevel 1 goto :ingest_failed
  %PY% ki_monitor.py ingest --from 20250101 --universe KOSPI >> "%LOG%" 2>&1
  if errorlevel 1 goto :ingest_failed
  %PY% ki_monitor.py fundamentals --market KOSDAQ >> "%LOG%" 2>&1
  %PY% ki_monitor.py fundamentals --market KOSPI >> "%LOG%" 2>&1
  popd
)

rem ---------------------------------------------------------- 4/5 논문
rem  하루 한 편까지. 수확은 공개 API 라 비용이 없고, 채택은 발행 정보를
rem  Crossref 로 다시 대조한 것만 넣는다. 대조에 실패하면 넣지 않는다.
call :stage "4/5" "논문 수확 · 채택"
pushd stock-monitor
%PY% ..\docs\fetch_papers.py --harvest-years 2 --max-per-year 25 >> "%LOG%" 2>&1
if errorlevel 1 call :say "     [알림] 수확 실패 - 네트워크나 논문 API 쪽 문제입니다."
%PY% ..\docs\fetch_papers.py --adopt --max-adopt 1 >> "%LOG%" 2>&1
popd

rem ---------------------------------------------------------- 5/5 회의 자료
call :stage "5/5" "회의 자료"
pushd stock-monitor
%PY% ki_monitor.py report --market %MARKET% >> "%LOG%" 2>&1
set RPRC=%ERRORLEVEL%
popd
if not "%RPRC%"=="0" (
  call :fail "리포트를 만들지 못했습니다." "기록을 보십시오: %LOG%"
  goto :end
)

for /f "delims=" %%f in ('dir /b /o-d "stock-monitor\out\KI_exit_*.html" 2^>nul') do (
  call :say ""
  call :say "  끝났습니다 - stock-monitor\out\%%f"
  if /I not "%MODE%"=="auto" start "" "stock-monitor\out\%%f"
  goto :done
)
:done
goto :end

:ingest_failed
popd
call :fail "원장 적재가 실패했습니다." "401 이 보이면 KRX 에서 '서비스별 URL 사용신청'을 안 하신 겁니다. 키 문제가 아닙니다."
goto :end

rem ==========================================================
rem  스케줄러 전용 - 평일 08:50  리포트만 만든다
rem ==========================================================
:auto_morning
call :say "%DATE% %TIME%  아침 리포트 시작"
pushd stock-monitor
%PY% ki_monitor.py report --market %MARKET% >> "%LOG%" 2>&1
popd
call :say "%DATE% %TIME%  끝"
exit /b 0

rem ==========================================================
rem  스케줄러 전용 - 평일 16:10  장 마감 적재
rem ==========================================================
:auto_close
call :say "%DATE% %TIME%  장 마감 적재 시작"
pushd stock-monitor
%PY% ki_monitor.py catchup --market %MARKET% >> "%LOG%" 2>&1
%PY% ki_monitor.py daily --market %MARKET% >> "%LOG%" 2>&1
popd
call :say "%DATE% %TIME%  끝"
exit /b 0

rem ==========================================================
rem  스케줄러 전용 - 평일 07:30  논문 수확 + 채택
rem
rem  수확은 공개 API 라 비용이 없습니다. 채택은 발행 정보를 Crossref 로
rem  다시 대조한 것만, 하루 한 편까지. 대조에 실패하면 넣지 않습니다.
rem ==========================================================
:auto_papers
call :say "%DATE% %TIME%  논문 수확 · 채택 시작"
pushd stock-monitor
%PY% ..\docs\fetch_papers.py --harvest-years 2 --max-per-year 25 >> "%LOG%" 2>&1
%PY% ..\docs\fetch_papers.py --adopt --max-adopt 1 >> "%LOG%" 2>&1
popd
call :say "%DATE% %TIME%  끝"
exit /b 0

rem ==========================================================
rem  주간 논문 재현 사이클 - 월요일 07:40
rem
rem  수확(07:30)이 끝난 뒤에 돈다. 재검 기한이 온 논문을 우리 원장에
rem  대고 다시 계산하고, 기한이 지난 채택본을 warned 로 내린다.
rem  주 3편 상한이 있어서 기한이 몰린 주에도 세 편만 돈다.
rem
rem  네트워크도 키도 쓰지 않는다 - 이미 받아 둔 원장만 읽는다.
rem  원장이 없으면 사유를 로그에 적고 그대로 끝난다.
rem ==========================================================
:auto_cycle
call :say "%DATE% %TIME%  주간 논문 재현 사이클 시작"
%PY% agents\cycle.py --run >> "%LOG%" 2>&1
if errorlevel 1 call :say "  사이클이 끝까지 돌지 못했습니다. 로그를 보십시오."
call :say "%DATE% %TIME%  끝"
exit /b 0

rem ---------------------------------------------------------- 유틸
:keys
rem  키를 스스로 구해 온다. 여기서 사람에게 일을 시키지 않는다.
rem
rem    1) 흔한 자리를 본다        (키 폴더 · 저장소 · 바탕화면 · 문서 · OneDrive)
rem    2) 넓게 훑는다             (홈 아래 · 저장소 위 · 고정 드라이브, 최대 1분)
rem    3) 그래도 없으면 물어본다  (탐색기에서 .env 를 끌어다 놓으면 된다)
rem
rem  import-keys 는 채워진 키 파일이 이미 있으면 아무것도 하지 않는다.
rem  빈 서식만 있으면 덮어쓴다 — 그 빈 파일이 예전에 탐색을 막았다.
if exist "stock-monitor\.env" (
  if not exist "%KEYDIR%\.env" (
    call :say "  [알림] 키를 저장소 안에서 읽고 있습니다. 밖으로 옮기시려면:"
    call :say "         cd stock-monitor ^&^& python ki_monitor.py migrate-keys"
  )
)
rem  고르는 무늬는 **ASCII 로만** 쓴다. 이 .cmd 는 UTF-8 이고 파이썬이 파일로
rem  내보낸 글자는 그 컴퓨터의 로캘 인코딩이다. 한글 낱말로 findstr 을 걸면
rem  두 인코딩이 다른 컴퓨터에서 한 줄도 안 맞아 조용히 사라진다.
rem  "들여쓴 줄"(^  )은 개수 줄만 고르면서 한글을 한 자도 안 쓴다.
rem  import-keys 는 잘 된 날에도 "이미 키 파일이 있습니다: <긴 경로>" 를 찍었다.
rem  매일 같은 두 줄이라 아무도 안 읽는다. 기록에는 전부 남기고, 화면에는
rem  **개수 줄만** 올린다 - 키가 6개에서 2개로 줄어든 날은 보여야 한다.
rem  실패하면 그때는 통째로 띄운다. errorlevel 은 type 이 덮어쓰므로 먼저 챙긴다.
pushd stock-monitor
%PY% ki_monitor.py import-keys > "%TEMP%\sa_keys.txt" 2>&1
set KRC=%ERRORLEVEL%
type "%TEMP%\sa_keys.txt" >> "%LOG%" 2>&1
if not "%KRC%"=="0" goto :keys_deep
findstr /R /C:"^  " "%TEMP%\sa_keys.txt"
goto :keys_ok
:keys_deep
call :say "     흔한 자리에는 없습니다 - 조금 더 넓게 찾아봅니다 (최대 1분)"
%PY% ki_monitor.py import-keys --deep > "%TEMP%\sa_keys.txt" 2>&1
set KRC=%ERRORLEVEL%
type "%TEMP%\sa_keys.txt"
type "%TEMP%\sa_keys.txt" >> "%LOG%" 2>&1
if "%KRC%"=="0" goto :keys_ok
rem  자동 실행(스케줄러)에는 답할 사람이 없다. 묻지 않고 넘어간다.
if /I "%MODE%"=="auto" goto :keys_none
if /I "%MODE%"=="morning" goto :keys_none
if /I "%MODE%"=="close" goto :keys_none
if /I "%MODE%"=="papers" goto :keys_none
if /I "%MODE%"=="cycle" goto :keys_none
echo.
echo      쓰시던 .env 를 못 찾았습니다.
echo      그 파일을 탐색기에서 이 창으로 끌어다 놓고 엔터를 치십시오.
echo      ^(없으면 그냥 엔터 - 새로 발급받는 안내가 나옵니다^)
echo.
set "KEYSRC="
set /p "KEYSRC=  경로: "
if not defined KEYSRC goto :keys_none
%PY% ki_monitor.py import-keys %KEYSRC%
if not errorlevel 1 goto :keys_ok
:keys_none
popd
if not exist "%KEYDIR%" mkdir "%KEYDIR%" >nul 2>&1
if not exist "%KEYDIR%\.env" copy /y "stock-monitor\.env.example" "%KEYDIR%\.env" >nul 2>&1
call :say ""
call :say "     쓰시던 키를 못 찾았습니다. 키 파일은 여기입니다:"
call :say "       %KEYDIR%\.env"
call :say "     메모장으로 열어 채우시거나, 경로를 아시면:"
call :say "       cd stock-monitor ^&^& python ki_monitor.py import-keys \"경로\""
exit /b 0
:keys_ok
popd
exit /b 0


:data
rem  감시 종목·회수계획·포지션도 키와 똑같은 이야기다.
rem  대외비라 저장소에 올리지 않으므로 새로 푼 폴더에는 없다. 그러면 감시
rem  종목이 포트폴리오사로 안 맞춰지는데, 화면에는 "그대로 둡니다" 한 줄만
rem  지나가서 아무도 모른다. 그래서 키와 같은 사다리로 옛 폴더에서 가져온다.
rem  이미 있으면 아무것도 하지 않는다 (손으로 고친 것을 덮어쓰지 않는다).
pushd stock-monitor
%PY% ki_monitor.py import-data > "%TEMP%\sa_data.txt" 2>&1
set DRC=%ERRORLEVEL%
type "%TEMP%\sa_data.txt" >> "%LOG%" 2>&1
if not "%DRC%"=="0" goto :data_deep
findstr /R /C:"^  " "%TEMP%\sa_data.txt"
goto :data_ok
:data_deep
call :say "     감시 종목 파일을 찾습니다 - 조금 더 넓게 봅니다 (최대 1분)"
%PY% ki_monitor.py import-data --deep > "%TEMP%\sa_data.txt" 2>&1
set DRC=%ERRORLEVEL%
type "%TEMP%\sa_data.txt"
type "%TEMP%\sa_data.txt" >> "%LOG%" 2>&1
if "%DRC%"=="0" goto :data_ok
popd
call :say ""
call :say "     감시 종목 파일(watchlist.csv)이 없습니다."
call :say "     쓰시던 것이 있으면:"
call :say "       cd stock-monitor ^&^& python ki_monitor.py import-data \"옛 폴더\""
call :say "     처음이시면 stock-monitor\watchlist.sample.csv 를 복사해 채우십시오."
exit /b 0
:data_ok
popd
exit /b 0


:say
echo %~1
echo %~1 >> "%LOG%" 2>&1
exit /b 0


:stage
call :say "  [%~1] %~2"
exit /b 0


:fail
call :say ""
call :say "      X  %~1"
call :say "         %~2"
exit /b 0


:end
if /I "%MODE%"=="auto" goto :nopause
if /I "%MODE%"=="morning" goto :nopause
if /I "%MODE%"=="close" goto :nopause
if /I "%MODE%"=="papers" goto :nopause
if /I "%MODE%"=="cycle" goto :nopause
pause
:nopause
endlocal

