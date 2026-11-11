@echo off
chcp 65001 >nul
cd /d "%~dp0\..\.."
py -3 -m unittest discover -s research_core/k2/tests -v
if errorlevel 1 (
  echo K2 unittest FAILED. Do not proceed.
  pause
  exit /b 1
)
py -3 -m research_core.k2.demo
if errorlevel 1 (
  echo K2 demo FAILED. Do not proceed.
  pause
  exit /b 1
)
start "" "research_core\k2\out\k2_review.html"
echo K2 verification succeeded.
pause
