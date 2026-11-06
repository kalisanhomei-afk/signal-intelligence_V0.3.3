@echo off
chcp 65001 >nul
cd /d "%~dp0.."
where py >nul 2>&1
if %errorlevel%==0 (
    py -3 rebuild_r5\qa_gate.py --root . --out rebuild_r5\out
) else (
    where python >nul 2>&1
    if not %errorlevel%==0 (
        echo Python 3.10+ is required for local R5 tests. No change was made.
        pause
        exit /b 1
    )
    python rebuild_r5\qa_gate.py --root . --out rebuild_r5\out
)
if errorlevel 1 (
    echo R5 OFFLINE QA FAILED. See rebuild_r5\out\qa_result.json. Do NOT run paid AI.
    pause
    exit /b 1
)
echo R5 OFFLINE QA PASSED. No OpenAI API was called.
start "" "rebuild_r5\out\qa_review.html"
pause
