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

REM Open the browser after a short delay, once the server is ready.
start "" cmd /c "timeout /t 5 >nul & start http://localhost:8501"

REM Start the server (this holds the window open and runs the app).
python -m streamlit run app.py --server.headless true

REM If the app exits or errors, keep the window open so you can read it.
echo.
echo The app has stopped.
pause
