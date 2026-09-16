@echo off
setlocal
cd /d "%~dp0"

where py >nul 2>nul
if errorlevel 1 (
  echo [MAGASIN] Khong tim thay Python launcher ^(py^). Can Python 3.11+.
  pause
  exit /b 1
)

if not exist ".venv\Scripts\python.exe" py -3 -m venv .venv
if errorlevel 1 exit /b 1

call ".venv\Scripts\activate.bat"
python -c "import sys; raise SystemExit(0 if sys.version_info >= (3,11) else 1)"
if errorlevel 1 (
  echo [MAGASIN] Can Python 3.11 tro len.
  pause
  exit /b 1
)
python -m pip install --upgrade pip
python -m pip install -e ".[dev]"
python -m playwright install chromium

python -m pytest
if errorlevel 1 (
  echo [MAGASIN] Test that bai. Khong chay discovery cho den khi sua xong.
  pause
  exit /b 1
)

echo.
echo [MAGASIN] Cai dat Discovery V0.1 hoan tat.
echo Chay RUN_DISCOVERY.bat de bat dau.
pause
