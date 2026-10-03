$ErrorActionPreference = "Stop"

$QcRoot = "C:\SAYDI\qc"
$BookId = "1c0ea552-a391-4f53-9e45-874be5a7ed66"
$MaxChapter = 11
$ConfigPath = "C:\SAYDI\worker\config.json"
$DoneMarker = Join-Path $QcRoot "QC_FULL_DONE.txt"
$RunLog = Join-Path $QcRoot "qc_waiter.log"
$PythonBase = "C:\SAYDI\VieNeu-TTS\.venv\Scripts\python.exe"
$QcPython = Join-Path $QcRoot ".venv\Scripts\python.exe"
$RunQc = Join-Path $QcRoot "run_qc.py"

New-Item -ItemType Directory -Force -Path $QcRoot | Out-Null
if (Test-Path $DoneMarker) { exit 0 }
if (-not (Test-Path $ConfigPath)) { throw "Missing worker config" }

$cfg = Get-Content $ConfigPath -Raw | ConvertFrom-Json
$headers = @{
    "Content-Type" = "application/json"
    "X-SAYDI-WORKER-TOKEN" = $cfg.worker_token
}
$body = @{
    action = "book_jobs"
    book_id = $BookId
    max_chapter = $MaxChapter
} | ConvertTo-Json

try {
    $status = Invoke-RestMethod -Method Post -Uri $cfg.api_url -Headers $headers -Body $body -TimeoutSec 60
} catch {
    Add-Content $RunLog ("[" + (Get-Date -Format s) + "] bridge unavailable: " + $_.Exception.Message)
    exit 0
}

$jobs = @($status.jobs)
$ready = ($jobs.Count -eq $MaxChapter)
if ($ready) {
    foreach ($j in $jobs) {
        if ($j.status -ne "completed" -or -not $j.output_file_name -or -not (Test-Path $j.output_file_name)) {
            $ready = $false
            break
        }
    }
}

if (-not $ready) {
    $states = ($jobs | ForEach-Object { "C$($_.chapter_number)=$($_.status):$($_.completed_chunks)/$($_.total_chunks)" }) -join " | "
    Add-Content $RunLog ("[" + (Get-Date -Format s) + "] WAIT " + $states)
    exit 0
}

Add-Content $RunLog ("[" + (Get-Date -Format s) + "] READY: full book completed. Installing/running QC.")

$uv = $null
$uvCmd = Get-Command uv.exe -ErrorAction SilentlyContinue
if ($uvCmd) { $uv = $uvCmd.Source }

if (-not $uv) {
    $roots = @("C:\Users")
    foreach ($root in $roots) {
        if ($uv) { break }
        $found = Get-ChildItem $root -Filter uv.exe -File -Recurse -ErrorAction SilentlyContinue | Select-Object -First 1
        if ($found) { $uv = $found.FullName }
    }
}
if (-not $uv) { throw "Cannot find uv.exe for QC environment" }

if (-not (Test-Path $QcPython)) {
    & $uv venv (Join-Path $QcRoot ".venv") --python $PythonBase
    if ($LASTEXITCODE -ne 0) { throw "uv venv failed" }
}

& $uv pip install --python $QcPython "faster-whisper>=1.1,<2" "numpy>=1.26,<3" "soundfile>=0.12,<1"
if ($LASTEXITCODE -ne 0) { throw "QC dependencies install failed" }

& $QcPython $RunQc --book-id $BookId --max-chapter $MaxChapter *>> $RunLog
if ($LASTEXITCODE -eq 0) {
    Set-Content -Path $DoneMarker -Value ("DONE " + (Get-Date -Format s)) -Encoding UTF8
    Disable-ScheduledTask -TaskName "SAYDI QC Full Book Waiter" -ErrorAction SilentlyContinue | Out-Null
}
