@echo off
setlocal
cd /d "%~dp0"

echo ============================================================
echo MAGASIN SaydiVoice - ONE-TIME LIVE PROFILE SETUP
echo ============================================================
echo.
echo Script nay chi chay 1 lan tren CHINH MAY Windows se lam
echo GitHub self-hosted runner. Browser profile duoc luu local tai:
echo %%LOCALAPPDATA%%\MAGASIN\MediaRobot\saydivoice\browser_profile
echo Va KHONG duoc commit/upload len GitHub.
echo.

if not exist ".venv\Scripts\python.exe" (
  py -3 -m venv .venv
  if errorlevel 1 goto :fail
)

call ".venv\Scripts\activate.bat"
python -m pip install --upgrade pip
if errorlevel 1 goto :fail
python -m pip install -r requirements-dev.txt
if errorlevel 1 goto :fail
python -m pip install -e .
if errorlevel 1 goto :fail
python -m playwright install chromium
if errorlevel 1 goto :fail

python -m saydivoice_discovery.profile_setup
set EXITCODE=%ERRORLEVEL%
if not "%EXITCODE%"=="0" goto :fail_code

echo.
echo PASS - profile da san sang cho GitHub Actions self-hosted runner.
pause
exit /b 0

:fail_code
echo.
echo SETUP CHUA DAT - exit code %EXITCODE%.
echo Co the chay lai file nay; profile cu khong bi xoa.
pause
exit /b %EXITCODE%

:fail
echo.
echo SETUP THAT BAI.
pause
exit /b 1
