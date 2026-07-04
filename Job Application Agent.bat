@echo off
REM ============================================================
REM  Double-click this file to launch the Job Search Assistant.
REM  It starts the local server and opens the app in your browser.
REM ============================================================

cd /d "%~dp0"

echo ============================================
echo   Job Search Assistant
echo ============================================
echo.
echo Starting the app... a browser tab will open shortly.
echo.
echo   KEEP THIS WINDOW OPEN while using the app.
echo   Close it (or press Ctrl+C) to stop the app.
echo.

REM Use the project's own virtual environment so the right Python is used
REM regardless of PATH. If it's missing, tell the user to run setup.
set "VENVPY=%~dp0.venv\Scripts\python.exe"
if not exist "%VENVPY%" (
    echo Setup has not been run yet ^(.venv is missing^).
    echo Please run setup.ps1 once:
    echo    powershell -ExecutionPolicy Bypass -File setup.ps1
    echo.
    pause
    exit /b 1
)

REM Open the browser after a short delay, once the server is ready.
start "" cmd /c "timeout /t 5 >nul & start http://localhost:8501"

REM Start the server (this holds the window open and runs the app).
"%VENVPY%" -m streamlit run app.py --server.headless true

REM If the app exits or errors, keep the window open so you can read it.
echo.
echo The app has stopped.
pause
