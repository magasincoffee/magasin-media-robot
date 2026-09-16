@echo off
setlocal
cd /d "%~dp0"

if not exist ".venv\Scripts\python.exe" (
  echo [MAGASIN] Chua co moi truong. Hay chay SETUP_DISCOVERY.bat truoc.
  pause
  exit /b 2
)

".venv\Scripts\python.exe" -m saydivoice_discovery.cli
set EXIT_CODE=%ERRORLEVEL%

echo.
echo [MAGASIN] Discovery ket thuc voi ma %EXIT_CODE%.
echo Du lieu cuc bo nam trong %%LOCALAPPDATA%%\MAGASIN\MediaRobot\saydivoice
pause
exit /b %EXIT_CODE%
