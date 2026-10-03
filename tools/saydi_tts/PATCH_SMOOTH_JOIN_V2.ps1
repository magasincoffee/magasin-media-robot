$ErrorActionPreference = "Stop"

$ExpectedComputer = "DESKTOP-H4A16IL"
$WorkerDir = "C:\SAYDI\worker"
$WorkerPy = Join-Path $WorkerDir "saydi_worker.py"
$JoinPy = Join-Path $WorkerDir "saydi_audio_join.py"
$HostPs1 = Join-Path $WorkerDir "worker-host.ps1"
$LogFile = "C:\SAYDI\logs\worker.log"

if ($env:COMPUTERNAME.ToUpper() -ne $ExpectedComputer.ToUpper()) {
    throw "Patch này dành cho $ExpectedComputer, máy hiện tại là $env:COMPUTERNAME"
}
if (-not (Test-Path $WorkerPy)) { throw "Không tìm thấy $WorkerPy" }
if (-not (Test-Path $HostPs1)) { throw "Không tìm thấy $HostPs1" }

$joinModule = @'
from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path

import numpy as np
import soundfile as sf

JOIN_GAP_MS = 80
EDGE_KEEP_BEFORE_MS = 70
EDGE_KEEP_AFTER_MS = 90
FADE_MS = 12
SILENCE_THRESHOLD_DB = -50.0

def _find_ffmpeg():
    p = shutil.which("ffmpeg")
    if p:
        return p
    candidates = [
        Path(r"C:\ffmpeg\bin\ffmpeg.exe"),
        Path(r"C:\Program Files\ffmpeg\bin\ffmpeg.exe"),
        Path(os.environ.get("LOCALAPPDATA", "")) / "Microsoft" / "WinGet" / "Packages",
    ]
    for c in candidates[:2]:
        if c.is_file():
            return str(c)
    pkg_root = candidates[2]
    if pkg_root.exists():
        for pth in pkg_root.glob("**/ffmpeg.exe"):
            if pth.is_file():
                return str(pth)
    return None

def _prepare_segment(path: Path):
    audio, sr = sf.read(str(path), dtype="float32", always_2d=False)
    if audio.ndim > 1:
        audio = audio.mean(axis=1)
    if len(audio) == 0:
        raise RuntimeError(f"WAV rỗng: {path}")

    threshold = 10.0 ** (SILENCE_THRESHOLD_DB / 20.0)
    active = np.flatnonzero(np.abs(audio) > threshold)
    if active.size:
        keep_before = int(sr * EDGE_KEEP_BEFORE_MS / 1000.0)
        keep_after = int(sr * EDGE_KEEP_AFTER_MS / 1000.0)
        start = max(0, int(active[0]) - keep_before)
        end = min(len(audio), int(active[-1]) + keep_after + 1)
        audio = audio[start:end]

    fade_n = min(int(sr * FADE_MS / 1000.0), len(audio) // 4)
    if fade_n > 1:
        audio[:fade_n] *= np.linspace(0.0, 1.0, fade_n, dtype=np.float32)
        audio[-fade_n:] *= np.linspace(1.0, 0.0, fade_n, dtype=np.float32)

    return audio.astype(np.float32, copy=False), sr

def concat_and_normalize(chunk_files, output_file: Path):
    ffmpeg = _find_ffmpeg()
    if not ffmpeg:
        raise RuntimeError("Không tìm thấy FFmpeg")

    prepared = []
    sample_rate = None
    for path in chunk_files:
        segment, sr = _prepare_segment(Path(path))
        if sample_rate is None:
            sample_rate = sr
        elif sr != sample_rate:
            raise RuntimeError(f"Sample rate không đồng nhất: {sr} != {sample_rate}")
        prepared.append(segment)

    if not prepared or sample_rate is None:
        raise RuntimeError("Không có audio để ghép")

    gap = np.zeros(int(sample_rate * JOIN_GAP_MS / 1000.0), dtype=np.float32)
    pieces = []
    for i, segment in enumerate(prepared):
        if i:
            pieces.append(gap)
        pieces.append(segment)

    merged = np.concatenate(pieces)
    temp_wav = output_file.parent / "_saydi_smooth_merged.wav"
    sf.write(str(temp_wav), merged, sample_rate, subtype="PCM_16")

    if output_file.suffix.lower() == ".mp3":
        cmd = [ffmpeg, "-y", "-i", str(temp_wav),
               "-af", "loudnorm=I=-18:LRA=11:TP=-2",
               "-ar", "48000", "-ac", "1",
               "-c:a", "libmp3lame", "-b:a", "128k",
               str(output_file)]
    else:
        cmd = [ffmpeg, "-y", "-i", str(temp_wav),
               "-af", "loudnorm=I=-18:LRA=11:TP=-2",
               "-ar", "48000", "-ac", "1",
               "-c:a", "pcm_s16le",
               str(output_file)]

    proc = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace")
    try:
        temp_wav.unlink(missing_ok=True)
    except Exception:
        pass
    if proc.returncode != 0:
        raise RuntimeError("FFmpeg lỗi:\n" + proc.stderr[-5000:])
'@

Set-Content -Path $JoinPy -Value $joinModule -Encoding UTF8

$worker = Get-Content $WorkerPy -Raw
$marker = "# SAYDI_SMOOTH_JOIN_V2"
if ($worker -notmatch [regex]::Escape($marker)) {
    $needle = "def process_job(tts, job):"
    if ($worker -notmatch [regex]::Escape($needle)) {
        throw "Không tìm thấy process_job trong saydi_worker.py"
    }

    $replacement = @'
# SAYDI_SMOOTH_JOIN_V2
from saydi_audio_join import concat_and_normalize

def process_job(tts, job):
'@
    $worker = $worker.Replace($needle, $replacement)
    Copy-Item $WorkerPy "$WorkerPy.before-smooth-v2.bak" -Force
    Set-Content -Path $WorkerPy -Value $worker -Encoding UTF8
}

Get-CimInstance Win32_Process -ErrorAction SilentlyContinue | Where-Object { $_.CommandLine -and $_.CommandLine -like '*C:\SAYDI\worker\saydi_worker.py*' } | ForEach-Object { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }

New-Item -ItemType Directory -Force -Path "C:\SAYDI\logs" | Out-Null
Add-Content $LogFile ([Environment]::NewLine + "===== SMOOTH JOIN V2 " + (Get-Date -Format s) + " =====")

$argLine = '-NoProfile -ExecutionPolicy Bypass -File "' + $HostPs1 + '"'
Start-Process powershell.exe -WindowStyle Hidden -ArgumentList $argLine
Start-Sleep -Seconds 5

Write-Host "SAYDI Smooth Join V2 đã cài xong." -ForegroundColor Green
Write-Host "Job mới: trim khoảng lặng dư + fade nhẹ + gap 80ms." -ForegroundColor Cyan
Get-Content $LogFile -Tail 60
