@echo off
setlocal
cd /d "%~dp0"
title MAGASIN - SaydiVoice Discovery V0.2
if not exist ".venv\Scripts\python.exe" (
  echo Chua cai dat. Hay chay CAI_DAT_VA_CHAY.bat truoc.
  pause
  exit /b 2
)
".venv\Scripts\python.exe" -m saydivoice_discovery.cli --login-wait-seconds 180
set RC=%ERRORLEVEL%
echo.
echo Discovery V0.2 ket thuc: %RC%
if exist "%LOCALAPPDATA%\MAGASIN\MediaRobot\saydivoice" start "" explorer "%LOCALAPPDATA%\MAGASIN\MediaRobot\saydivoice"
pause
exit /b %RC%
