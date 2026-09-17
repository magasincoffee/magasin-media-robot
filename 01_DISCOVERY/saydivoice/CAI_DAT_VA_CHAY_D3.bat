@echo off
setlocal EnableExtensions
cd /d "%~dp0"
title MAGASIN - SaydiVoice D3 Generation Lifecycle

echo ============================================================
echo   MAGASIN SAYDIVOICE DISCOVERY V0.4.0 - D3 GENERATION
ECHO   CANH BAO: LAN CHAY NAY SE DUNG 1 LUOT TAO GIONG.
echo   Robot KHONG tai audio. Chi tao 1 mau ngan de quan sat lifecycle.
echo ============================================================
echo.
choice /C YN /N /M "Tiep tuc va dung 1 luot tao giong? [Y/N]: "
if errorlevel 2 exit /b 0

set "PY_CMD="
where py >nul 2>nul && set "PY_CMD=py -3"
if not defined PY_CMD (
  where python >nul 2>nul && set "PY_CMD=python"
)
if not defined PY_CMD (
  echo [LOI] Khong tim thay Python 3.11+ tren may.
  pause
  exit /b 1
)

%PY_CMD% -c "import sys; raise SystemExit(0 if sys.version_info >= (3,11) else 1)"
if errorlevel 1 (
  echo [LOI] Python hien tai thap hon 3.11.
  pause
  exit /b 1
)

if not exist ".venv\Scripts\python.exe" (
  echo [1/5] Tao moi truong Python rieng...
  %PY_CMD% -m venv .venv || goto :fail
)

echo [2/5] Cai/cap nhat Discovery V0.4.0...
".venv\Scripts\python.exe" -m pip install --disable-pip-version-check --upgrade pip || goto :fail
".venv\Scripts\python.exe" -m pip install -e ".[dev]" || goto :fail

echo [3/5] Kiem tra Chromium cua robot...
".venv\Scripts\python.exe" -m playwright install chromium || goto :fail

echo [4/5] Tu test truoc khi chay...
".venv\Scripts\python.exe" -m pytest || goto :fail

echo [5/5] Chay D3 controlled generation...
echo KHONG thao tac tren cua so SaydiVoice trong luc robot dang chay.
echo.
".venv\Scripts\python.exe" -m saydivoice_discovery.cli --login-wait-seconds 180 --allow-generate --generation-timeout-ms 60000
set "RC=%ERRORLEVEL%"

echo.
echo ============================================================
echo D3 ket thuc. Ma trang thai: %RC%
echo Du lieu: %LOCALAPPDATA%\MAGASIN\MediaRobot\saydivoice
echo Can gui: generation_lifecycle.json, d3_before_generate.png,
echo d3_after_generate.png, report JSON va JSONL log cung RUN ID.
echo ============================================================
if exist "%LOCALAPPDATA%\MAGASIN\MediaRobot\saydivoice" start "" explorer "%LOCALAPPDATA%\MAGASIN\MediaRobot\saydivoice"
pause
exit /b %RC%

:fail
echo.
echo [LOI] Cai dat/tu test that bai. Gui anh man hinh nay cho ChatGPT.
pause
exit /b 99
