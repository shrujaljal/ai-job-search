@echo off
setlocal
cd /d "%~dp0"

echo ============================================
echo   Job Application Agent V2
echo ============================================
echo.

if not exist ".venv\Scripts\python.exe" (
  echo First launch: installing local dependencies...
  where py >nul 2>nul
  if %errorlevel% equ 0 (
    py -3 run.py --install
  ) else (
    python run.py --install
  )
  if errorlevel 1 goto :error
)

echo Starting the app. Keep this window open while using it.
echo.
".venv\Scripts\python.exe" run.py
if errorlevel 1 goto :error
goto :eof

:error
echo.
echo The app could not start. Run this for diagnostics:
echo   .venv\Scripts\python.exe run.py --doctor
echo.
pause
exit /b 1
