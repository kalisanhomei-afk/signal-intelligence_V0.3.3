@echo off
cd /d "%~dp0"
echo [1/2] K3.2 data integrity audit and reports
python pipeline.py --output out
if errorlevel 1 (echo ERROR: Audit failed, inspect exception & conflicts. & pause & exit /b 1)
echo [2/2] Tests
python -m unittest discover -s tests -v
pause
