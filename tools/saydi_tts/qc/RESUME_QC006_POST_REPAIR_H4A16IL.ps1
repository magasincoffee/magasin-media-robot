param()

$ErrorActionPreference = "Stop"

if ($env:COMPUTERNAME -ne "DESKTOP-H4A16IL") {
    throw "QC-006 resume chỉ chạy trên DESKTOP-H4A16IL. Máy hiện tại: $env:COMPUTERNAME"
}

$QcRoot = "C:\SAYDI\qc"
$ConfigPath = "C:\SAYDI\worker\config.json"
$QcPython = Join-Path $QcRoot ".venv\Scripts\python.exe"
$RunQc = Join-Path $QcRoot "run_qc.py"
$FieldRoot = Join-Path $QcRoot "qc006"
$OwnerReview = Join-Path $FieldRoot "owner_review"
$PreReportPath = Join-Path $FieldRoot "targeted_repair_qc_summary.json"
$BookId = "66000000-0000-4000-8000-000000000005"
$JobId = "66100000-0000-4000-8000-000000000005"
$TargetIndex = 1
$ExpectedCanonical = "AI xử lý 15 kg dữ liệu trong năm 2026, còn CEO kiểm tra kết quả trước khi hệ thống gửi báo cáo qua API."
$WorkerTaskName = "SAYDI TTS Worker At Startup"

if (-not (Test-Path $ConfigPath)) { throw "Missing worker config: $ConfigPath" }
if (-not (Test-Path $QcPython)) { throw "Missing QC Python: $QcPython" }
if (-not (Test-Path $RunQc)) { throw "Missing run_qc.py: $RunQc" }
if (-not (Test-Path $PreReportPath)) {
    throw "Missing pre-repair QC evidence: $PreReportPath"
}

$cfg = Get-Content $ConfigPath -Raw | ConvertFrom-Json
$headers = @{ "X-SAYDI-WORKER-TOKEN" = $cfg.worker_token }

function Invoke-Saydi([hashtable]$Body) {
    $jsonBody = $Body | ConvertTo-Json -Depth 20 -Compress
    $utf8 = New-Object System.Text.UTF8Encoding($false)
    $bodyBytes = $utf8.GetBytes($jsonBody)
    return Invoke-RestMethod -Method Post -Uri $cfg.api_url -Headers $headers -ContentType "application/json; charset=utf-8" -Body $bodyBytes -TimeoutSec 90
}

function Get-Job {
    $response = Invoke-Saydi @{ action = "book_jobs"; book_id = $BookId; max_chapter = 1 }
    return @($response.jobs | Where-Object { [int]$_.chapter_number -eq 1 })[0]
}

function Get-AllChunks([string]$Id) {
    $all = @()
    $after = -1
    while ($true) {
        $page = Invoke-Saydi @{ action = "chunks"; job_id = $Id; after_index = $after; limit = 20 }
        $rows = @($page.chunks)
        if ($rows.Count -eq 0) { break }
        $all += $rows
        $after = [int]$rows[-1].chunk_index
    }
    return $all
}

Write-Host "[QC006-RESUME] Inspecting completed targeted repair..." -ForegroundColor Cyan
$job = Get-Job
if (-not $job) { throw "Targeted repair job not found." }
if ($job.status -ne "completed" -or [int]$job.completed_chunks -ne 3) {
    throw "Targeted repair is not complete. status=$($job.status) completed=$($job.completed_chunks)/3"
}
if (-not $job.output_file_name -or -not (Test-Path $job.output_file_name)) {
    throw "Completed output is missing: $($job.output_file_name)"
}

$chunkDir = Join-Path (Split-Path $job.output_file_name -Parent) "chunks"
$targetName = ("{0:D6}.wav" -f $TargetIndex)
$targetWav = Join-Path $chunkDir $targetName
if (-not (Test-Path $targetWav)) { throw "Post-repair target WAV missing: $targetWav" }

$pre = @(Get-Content $PreReportPath -Raw | ConvertFrom-Json)[0]
$preObs = @($pre.chunk_observations)
if ($preObs.Count -ne 3) { throw "Pre-repair evidence must contain 3 observations; got $($preObs.Count)" }

$hashBefore = @{}
foreach ($obs in $preObs) {
    if ($obs.audio_sha256 -notmatch '^[0-9a-fA-F]{64}$') {
        throw "Invalid pre-repair hash for chunk $($obs.chunk_index)"
    }
    $hashBefore[("{0:D6}.wav" -f [int]$obs.chunk_index)] = [string]$obs.audio_sha256
}

$changed = @()
foreach ($name in $hashBefore.Keys) {
    $path = Join-Path $chunkDir $name
    if (-not (Test-Path $path)) { throw "Chunk missing after repair: $name" }
    $afterHash = (Get-FileHash $path -Algorithm SHA256).Hash.ToLowerInvariant()
    if ($afterHash -ne ([string]$hashBefore[$name]).ToLowerInvariant()) {
        $changed += $name
    }
}
if ($changed.Count -ne 1 -or $changed[0] -ne $targetName) {
    throw "Targeted rerender invariant failed. Changed WAVs: $($changed -join ', ')"
}
Write-Host "[QC006-RESUME] Hash invariant PASS: only $targetName changed." -ForegroundColor Green

$chunks = Get-AllChunks $JobId
$target = @($chunks | Where-Object { [int]$_.chunk_index -eq $TargetIndex })[0]
if (-not $target) { throw "Target chunk state missing." }
if ($target.canonical_text_content -ne $ExpectedCanonical) {
    throw "Canonical text changed during targeted repair."
}
if (-not $target.spoken_override_applied) {
    throw "Expected spoken override is not active after repair."
}
if ([int]$target.qc_repair_attempts -lt 1 -or [int]$target.qc_repair_attempts -gt 2) {
    throw "Repair attempt bound failed: $($target.qc_repair_attempts)"
}

$workerTask = Get-ScheduledTask -TaskName $WorkerTaskName -ErrorAction SilentlyContinue
$workerWasRunning = $workerTask -and $workerTask.State -eq "Running"
if ($workerWasRunning) {
    Write-Host "[QC006-RESUME] Stopping idle TTS worker temporarily to free RAM..." -ForegroundColor Yellow
    Stop-ScheduledTask -TaskName $WorkerTaskName
    $deadline = (Get-Date).AddSeconds(30)
    do {
        Start-Sleep -Seconds 2
        $workerTask = Get-ScheduledTask -TaskName $WorkerTaskName -ErrorAction SilentlyContinue
    } while ($workerTask -and $workerTask.State -eq "Running" -and (Get-Date) -lt $deadline)
    Start-Sleep -Seconds 5
}

$oldMkl = $env:MKL_NUM_THREADS
$oldOmp = $env:OMP_NUM_THREADS
$env:MKL_NUM_THREADS = "2"
$env:OMP_NUM_THREADS = "2"

try {
    Write-Host "[QC006-RESUME] Running post-repair Whisper QC only..." -ForegroundColor Cyan
    & $QcPython $RunQc --book-id $BookId --max-chapter 1 --narration-profile GENERAL_CLEAR --observe-only
    if ($LASTEXITCODE -ne 0) { throw "Post-repair run_qc.py failed, exit=$LASTEXITCODE" }
} finally {
    $env:MKL_NUM_THREADS = $oldMkl
    $env:OMP_NUM_THREADS = $oldOmp
    if ($workerWasRunning) {
        Write-Host "[QC006-RESUME] Restarting SAYDI TTS worker..." -ForegroundColor Cyan
        Start-ScheduledTask -TaskName $WorkerTaskName
    }
}

$postPath = Join-Path $QcRoot ("reports\" + $BookId + "\qc_summary.json")
if (-not (Test-Path $postPath)) { throw "Missing post-repair QC report: $postPath" }
$post = @(Get-Content $postPath -Raw | ConvertFrom-Json)[0]
if ([int]$post.checked_chunks -ne 3) { throw "Post-repair QC did not observe all 3 chunks." }
if ($post.prosody_profile_key -ne "GENERAL_CLEAR") { throw "Post-repair profile mismatch." }

$postTarget = @($post.chunk_observations | Where-Object { [int]$_.chunk_index -eq $TargetIndex })[0]
if (-not $postTarget) { throw "Missing post-repair target observation." }
if ($postTarget.audio_sha256 -notmatch '^[0-9a-fA-F]{64}$') { throw "Invalid post-repair target hash." }

New-Item -ItemType Directory -Force -Path $OwnerReview | Out-Null
$beforeCopy = Join-Path $OwnerReview "target_before_repair.wav"
if (-not (Test-Path $beforeCopy)) {
    throw "Missing Owner BEFORE sample: $beforeCopy"
}
$afterCopy = Join-Path $OwnerReview "target_after_repair.wav"
Copy-Item $targetWav $afterCopy -Force

$preTarget = @($preObs | Where-Object { [int]$_.chunk_index -eq $TargetIndex })[0]
$result = [ordered]@{
    schema_version = "saydi-qc006-resume-result-v1"
    hostname = $env:COMPUTERNAME
    completed_at = (Get-Date).ToString("s")
    targeted_repair = [ordered]@{
        target_chunk_index = $TargetIndex
        changed_wavs = $changed
        canonical_text_preserved = $true
        repair_attempts = [int]$target.qc_repair_attempts
        max_repair_attempts = 2
        pre_canonical_similarity = $preTarget.canonical_asr_similarity
        post_canonical_similarity = $postTarget.canonical_asr_similarity
        post_warnings = [int]$post.warnings
        post_errors = [int]$post.errors
        post_qc_result = if (($post.warnings + $post.errors) -gt 0) { "REVIEW" } else { "PASS" }
        before_audio = $beforeCopy
        after_audio = $afterCopy
    }
    owner_listening_required = $true
    owner_review_folder = $OwnerReview
}

$resultPath = Join-Path $FieldRoot "QC006_FIELD_RESULT.json"
$result | ConvertTo-Json -Depth 20 | Set-Content -Encoding UTF8 $resultPath

$readme = @"
SAYDI QC-006 OWNER LISTENING GATE

BEFORE:
$beforeCopy

AFTER:
$afterCopy

Technical checks completed:
- targeted repair job completed 3/3;
- only chunk 000001.wav changed;
- canonical text remained unchanged;
- repair attempt stayed within the maximum of 2;
- post-repair Whisper QC completed after freeing TTS-worker memory;
- AFTER sample is the regenerated target audio.

QC-006 remains pending only Owner listening acceptance.
"@
$readme | Set-Content -Encoding UTF8 (Join-Path $OwnerReview "README.txt")

Write-Host ""
Write-Host "SAYDI QC-006 TECHNICAL FIELD RESULT" -ForegroundColor Cyan
Write-Host "Changed WAV only: $($changed -join ', ')" -ForegroundColor Green
Write-Host "Repair attempts: $($target.qc_repair_attempts)/2"
Write-Host "Pre canonical similarity:  $($preTarget.canonical_asr_similarity)"
Write-Host "Post canonical similarity: $($postTarget.canonical_asr_similarity)"
Write-Host "Post QC result: $($result.targeted_repair.post_qc_result)"
Write-Host "Technical field gate: PASS" -ForegroundColor Green
Write-Host "Owner listening gate: PENDING" -ForegroundColor Yellow
Write-Host "Listen here: $OwnerReview"
