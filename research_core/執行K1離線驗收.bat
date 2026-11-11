@echo off
setlocal
chcp 65001 >nul
cd /d "%~dp0.."
where py >nul 2>&1
if %errorlevel%==0 (
  set "PY=py -3"
) else (
  set "PY=python"
)
echo [SIGNAL K1] Running unit tests...
%PY% -m unittest discover -s research_core/tests -v
if errorlevel 1 goto failed
echo [SIGNAL K1] Generating synthetic-only as-of and QA reports...
%PY% -m research_core.demo
if errorlevel 1 goto failed
start "" "research_core\out\review.html"
echo.
echo K1 offline QA passed. No network or AI API calls.
pause
exit /b 0
:failed
echo.
echo K1 QA FAILED. Do not advance to K2.
pause
exit /b 1
