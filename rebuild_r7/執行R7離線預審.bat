@echo off
chcp 65001 >nul
cd /d "%~dp0"
where py >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] 找不到 Python Launcher (py)。可直接開啟 out\r7_quality_review.html 閱讀預先產生的報告。
    pause
    exit /b 1
)
py -3 evaluate_r6.py
if errorlevel 1 (echo [ERROR] 預審失敗 & pause & exit /b 1)
py -3 -m unittest discover -s . -p "test_evaluate_r6.py" -v
if errorlevel 1 (echo [ERROR] 測試未通過 & pause & exit /b 1)
start "" "%CD%\out\r7_quality_review.html"
echo [OK] R7 離線預審已完成。發布狀態仍為 NO-GO。
pause
