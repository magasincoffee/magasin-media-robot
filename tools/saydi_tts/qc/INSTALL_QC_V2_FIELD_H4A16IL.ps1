param(
    [string]$BookId = "1c0ea552-a391-4f53-9e45-874be5a7ed66",
    [int]$MaxChapter = 1
)

$ErrorActionPreference = "Stop"

if ($env:COMPUTERNAME -ne "DESKTOP-H4A16IL") {
    throw "Script này dành cho DESKTOP-H4A16IL. Máy hiện tại: $env:COMPUTERNAME"
}

$identity = [Security.Principal.WindowsIdentity]::GetCurrent()
$principalNow = New-Object Security.Principal.WindowsPrincipal($identity)
if (-not $principalNow.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) {
    throw "Hãy chạy PowerShell bằng Run as Administrator."
}

$QcRoot = "C:\SAYDI\qc"
$RunQc = Join-Path $QcRoot "run_qc.py"
$Backup = Join-Path $QcRoot ("run_qc.backup." + (Get-Date -Format "yyyyMMdd-HHmmss") + ".py")
$Log = Join-Path $QcRoot "qc_v2_field.log"
$PythonBase = "C:\SAYDI\VieNeu-TTS\.venv\Scripts\python.exe"
$QcPython = Join-Path $QcRoot ".venv\Scripts\python.exe"

New-Item -ItemType Directory -Force -Path $QcRoot | Out-Null

if (Test-Path $RunQc) {
    Copy-Item $RunQc $Backup -Force
}

$uri = "https://raw.githubusercontent.com/magasincoffee/magasin-media-robot/main/tools/saydi_tts/qc/run_qc.py"
Invoke-WebRequest -UseBasicParsing -Uri $uri -OutFile $RunQc

$uv = $null
$uvCmd = Get-Command uv.exe -ErrorAction SilentlyContinue
if ($uvCmd) { $uv = $uvCmd.Source }

if (-not $uv) {
    $found = Get-ChildItem "C:\Users" -Filter uv.exe -File -Recurse -ErrorAction SilentlyContinue | Select-Object -First 1
    if ($found) { $uv = $found.FullName }
}
if (-not $uv) { throw "Không tìm thấy uv.exe." }

if (-not (Test-Path $QcPython)) {
    & $uv venv (Join-Path $QcRoot ".venv") --python $PythonBase
    if ($LASTEXITCODE -ne 0) { throw "uv venv failed" }
}

& $uv pip install --python $QcPython "faster-whisper>=1.1,<2" "av>=11,<19" "numpy>=1.26,<3" "soundfile>=0.12,<1"
if ($LASTEXITCODE -ne 0) { throw "QC dependencies install failed" }

Add-Content $Log ("===== QC V2 FIELD START " + (Get-Date -Format s) + " =====")
& $QcPython $RunQc --book-id $BookId --max-chapter $MaxChapter --observe-only *>> $Log
if ($LASTEXITCODE -ne 0) {
    throw "QC v2 field run failed. Xem log: $Log"
}

$report = Join-Path $QcRoot ("reports\" + $BookId + "\qc_summary.json")
if (-not (Test-Path $report)) {
    throw "QC hoàn tất nhưng không tìm thấy report: $report"
}

$data = Get-Content $report -Raw | ConvertFrom-Json
$all = @()
foreach ($chapter in $data) {
    foreach ($o in @($chapter.chunk_observations)) {
        $all += $o
    }
}

if ($all.Count -eq 0) {
    throw "QC v2 không tạo được chunk observations."
}

$withWord = @($all | Where-Object { $null -ne $_.min_word_confidence })
$withPitch = @($all | Where-Object { $null -ne $_.pitch_variation_semitones })
$withRate = @($all | Where-Object { $null -ne $_.speaking_rate_wpm })
$withPause = @($all | Where-Object { $null -ne $_.pause_ratio })
$withEnergy = @($all | Where-Object { $null -ne $_.energy_variation_db })
$hashOk = @($all | Where-Object { $_.audio_sha256 -match '^[0-9a-fA-F]{64}$' })

Write-Host ""
Write-Host "SAYDI QC V2 FIELD RESULT" -ForegroundColor Cyan
Write-Host "Chunks observed: $($all.Count)"
Write-Host "Word-confidence: $($withWord.Count)/$($all.Count)"
Write-Host "Speaking-rate:   $($withRate.Count)/$($all.Count)"
Write-Host "Pause-ratio:     $($withPause.Count)/$($all.Count)"
Write-Host "Pitch-variation: $($withPitch.Count)/$($all.Count)"
Write-Host "Energy-variation:$($withEnergy.Count)/$($all.Count)"
Write-Host "Audio SHA-256:   $($hashOk.Count)/$($all.Count)"
Write-Host "Observe-only: không xóa WAV, không gọi repair_chunks." -ForegroundColor Green
Write-Host "Report: $report"
Write-Host "Log: $Log"

if ($withWord.Count -eq 0 -or $withRate.Count -eq 0 -or $withPause.Count -eq 0 -or
    $withEnergy.Count -eq 0 -or $hashOk.Count -ne $all.Count) {
    throw "FIELD GATE FAIL: thiếu metric bắt buộc."
}

Write-Host "FIELD GATE CORE METRICS: PASS" -ForegroundColor Green
if ($withPitch.Count -lt [Math]::Max(1,[int]($all.Count * 0.5))) {
    Write-Host "FIELD GATE NOTE: pitch variation chưa có ở phần lớn chunk; cần kiểm tra voiced-frame estimator." -ForegroundColor Yellow
}
