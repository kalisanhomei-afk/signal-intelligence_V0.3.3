@echo off
chcp 65001 >nul
cd /d "%~dp0\..\.."
py -3 -m unittest discover -s research_core\k31\tests -v
if errorlevel 1 (
  echo K3.1 offline QA FAIL. Please do not merge or run paid API.
  pause
  exit /b 1
)
py -3 -m research_core.k31.demo
if errorlevel 1 (
  echo K3.1 report generation FAIL.
  pause
  exit /b 1
)
start "" "%~dp0out\k31_review.html"
