@echo off
chcp 65001 > nul
cd /d "%~dp0"
python run.py %*
if %ERRORLEVEL% NEQ 0 (
    echo.
    echo Execution finished with error code %ERRORLEVEL%.
)
echo.
pause
