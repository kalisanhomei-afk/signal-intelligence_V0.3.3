@echo off
chcp 65001 >nul
cd /d "%~dp0\..\.."
py -3 -m unittest discover -s research_core/k3/tests -v
if errorlevel 1 (pause & exit /b 1)
py -3 -m research_core.k3.demo
if errorlevel 1 (pause & exit /b 1)
start "" "%~dp0out\k3_review.html"
pause
