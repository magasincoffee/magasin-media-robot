@echo off
setlocal EnableExtensions
cd /d "%~dp0"
title MAGASIN - SaydiVoice Discovery V0.3

echo ============================================================
echo   MAGASIN SAYDIVOICE DISCOVERY V0.3 - D2 VOICE + SETTINGS CATALOG
echo   Cai dat + tu test + mo SaydiVoice + thu thap D2 catalog artifacts
echo ============================================================
echo.

set "PY_CMD="
where py >nul 2>nul && set "PY_CMD=py -3"
if not defined PY_CMD (
  where python >nul 2>nul && set "PY_CMD=python"
)
if not defined PY_CMD (
  echo [LOI] Khong tim thay Python 3.11+ tren may.
  echo Hay cai Python 3.11 tro len, tick Add Python to PATH, roi chay lai.
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

echo [2/5] Cap nhat Discovery V0.3...
".venv\Scripts\python.exe" -m pip install --disable-pip-version-check --upgrade pip || goto :fail
".venv\Scripts\python.exe" -m pip install -e ".[dev]" || goto :fail

echo [3/5] Kiem tra Chromium cua robot...
".venv\Scripts\python.exe" -m playwright install chromium || goto :fail

echo [4/5] Tu test V0.3 truoc khi chay...
".venv\Scripts\python.exe" -m pytest || goto :fail

echo [5/5] Mo SaydiVoice Discovery V0.3...
echo Khong bam Tao giong noi. Robot se tu mo cac menu Giong / Ngon ngu / Ngat nghi de quan sat, sau do dong lai.
echo Neu hien man hinh dang nhap rieng, co the dang nhap trong Chromium robot.
echo.
".venv\Scripts\python.exe" -m saydivoice_discovery.cli --login-wait-seconds 180
set "RC=%ERRORLEVEL%"

echo.
echo ============================================================
echo Discovery V0.3 ket thuc. Ma trang thai: %RC%
echo Du lieu: %LOCALAPPDATA%\MAGASIN\MediaRobot\saydivoice
echo Can gui lai ChatGPT cac file moi nhat:
echo   1. reports\discovery_report_*.json
echo   2. runs\RUN_ID\dom_inventory.json
echo   3. runs\RUN_ID\saydi_map.json
echo   4. runs\RUN_ID\selectors.json
echo   5. runs\RUN_ID\voice_catalog.json
echo   6. runs\RUN_ID\settings_catalog.json
echo   7. screenshots\saydivoice_*.png
echo   8. logs\discovery_*.jsonl
echo ============================================================
if exist "%LOCALAPPDATA%\MAGASIN\MediaRobot\saydivoice" start "" explorer "%LOCALAPPDATA%\MAGASIN\MediaRobot\saydivoice"
pause
exit /b %RC%

:fail
echo.
echo [LOI] Qua trinh cai dat/tu test that bai. Gui anh man hinh nay cho ChatGPT.
pause
exit /b 99
