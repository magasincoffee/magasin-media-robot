param(
    [int]$WaitMinutes = 45
)

$ErrorActionPreference = "Stop"

if ($env:COMPUTERNAME -ne "DESKTOP-H4A16IL") {
    throw "Golden Story V3 chỉ chạy trên DESKTOP-H4A16IL. Máy hiện tại: $env:COMPUTERNAME"
}

$BookId = "66000000-0000-4000-8000-000000000007"
$JobId = "66100000-0000-4000-8000-000000000007"
$Root = "C:\SAYDI\narration_director_v1"
$ConfigPath = "C:\SAYDI\worker\config.json"
$Python = "C:\SAYDI\qc\.venv\Scripts\python.exe"
$Manifest = Join-Path $Root "golden_story_v3_manifest.json"
$Builder = Join-Path $Root "build_directed_audio.py"

if (-not (Test-Path $ConfigPath)) { throw "Missing worker config: $ConfigPath" }
if (-not (Test-Path $Python)) { throw "Missing QC Python: $Python" }

New-Item -ItemType Directory -Force -Path $Root | Out-Null

$RawBase = "https://raw.githubusercontent.com/magasincoffee/magasin-media-robot/main"
function Get-File([string]$Relative,[string]$Destination) {
    Write-Host "[DIRECTOR] download $Relative ..." -ForegroundColor DarkCyan
    Invoke-WebRequest -UseBasicParsing -Uri "$RawBase/$Relative" -OutFile $Destination -TimeoutSec 30
    if (-not (Test-Path $Destination) -or (Get-Item $Destination).Length -eq 0) {
        throw "Downloaded file is empty: $Destination"
    }
}

Get-File "tools/saydi_tts/narration/golden_story_v3_manifest.json" $Manifest
Get-File "tools/saydi_tts/narration/build_directed_audio.py" $Builder

$cfg = Get-Content $ConfigPath -Raw -Encoding UTF8 | ConvertFrom-Json
$headers = @{ "X-SAYDI-WORKER-TOKEN" = $cfg.worker_token }

function Invoke-Saydi([hashtable]$Body) {
    $jsonBody = $Body | ConvertTo-Json -Depth 20 -Compress
    $utf8 = New-Object Text.UTF8Encoding($false)
    $bytes = $utf8.GetBytes($jsonBody)
    return Invoke-RestMethod -Method Post -Uri $cfg.api_url -Headers $headers -ContentType "application/json; charset=utf-8" -Body $bytes -TimeoutSec 90
}

function Get-Job {
    $response = Invoke-Saydi @{ action = "book_jobs"; book_id = $BookId; max_chapter = 1 }
    return @($response.jobs | Where-Object { $_.id -eq $JobId })[0]
}

$deadline = (Get-Date).AddMinutes($WaitMinutes)
do {
    $job = Get-Job
    if (-not $job) { throw "Golden Story V3 job not found." }

    if ($job.status -eq "completed" -and [int]$job.completed_chunks -eq 17 -and $job.output_file_name) {
        break
    }
    if ($job.status -eq "failed") {
        throw "Golden Story V3 render failed: $($job.error)"
    }

    Write-Host "[DIRECTOR] TTS render: $($job.status) $($job.completed_chunks)/17" -ForegroundColor Cyan
    Start-Sleep -Seconds 10
} while ((Get-Date) -lt $deadline)

if ($job.status -ne "completed") {
    throw "Timed out waiting for Golden Story V3 render."
}

$OutputDir = Split-Path $job.output_file_name -Parent
$ChunkDir = Join-Path $OutputDir "chunks"
$FinalMp3 = Join-Path $OutputDir "SAYDI_STORY_GOLDEN_V3_FINAL.mp3"
$Report = Join-Path $OutputDir "SAYDI_STORY_GOLDEN_V3_REPORT.json"

$wavCount = @(Get-ChildItem $ChunkDir -Filter "*.wav" -File).Count
if ($wavCount -ne 17) {
    throw "Expected 17 chunk WAVs; got $wavCount"
}

Write-Host "[DIRECTOR] Building V3 natural-speed / semantic-pause master..." -ForegroundColor Cyan
& $Python $Builder --manifest $Manifest --chunk-dir $ChunkDir --output $FinalMp3 --report $Report
if ($LASTEXITCODE -ne 0) {
    throw "Narration Director builder failed, exit=$LASTEXITCODE"
}

$result = Get-Content $Report -Raw -Encoding UTF8 | ConvertFrom-Json
if ($result.technical_gate -ne "PASS") {
    Write-Host "[DIRECTOR] Technical gate REVIEW" -ForegroundColor Yellow
    Write-Host "Duration: $([math]::Round([double]$result.duration_sec,1)) sec"
    Write-Host "Effective WPM: $($result.effective_wpm)"
    throw "Golden Story V3 missed duration/WPM target."
}

Write-Host ""
Write-Host "SAYDI GOLDEN STORY V3" -ForegroundColor Cyan
Write-Host "Narration Director: PASS" -ForegroundColor Green
Write-Host "Duration: $([math]::Round([double]$result.duration_sec,1)) sec"
Write-Host "Effective WPM: $($result.effective_wpm)"
Write-Host "Final MP3: $FinalMp3" -ForegroundColor Green
Write-Host "Report: $Report"
Write-Host ""
Write-Host "Owner listening gate: PENDING" -ForegroundColor Yellow

Start-Process explorer.exe -ArgumentList "/select,`"$FinalMp3`""
