param()

$ErrorActionPreference = "Stop"

if ($env:COMPUTERNAME -ne "DESKTOP-H4A16IL") {
    throw "QC-006 UTF8 repair chỉ chạy trên DESKTOP-H4A16IL. Máy hiện tại: $env:COMPUTERNAME"
}

$QcRoot = "C:\SAYDI\qc"
$ConfigPath = "C:\SAYDI\worker\config.json"
$QcPython = Join-Path $QcRoot ".venv\Scripts\python.exe"
$RunQc = Join-Path $QcRoot "run_qc.py"
$FieldRoot = Join-Path $QcRoot "qc006"
$OwnerReview = Join-Path $FieldRoot "owner_review"
$BookId = "66000000-0000-4000-8000-000000000005"
$JobId = "66100000-0000-4000-8000-000000000005"
$TargetIndex = 1
$WorkerTaskName = "SAYDI TTS Worker At Startup"
$ExpectedCanonicalSha256 = "46cc170b7a131f122e182e08bd8d56520c2922b5b6a330b83d131e897549f2ce"
$ExpectedSpokenSha256 = "37cb469eef6ce9d666ac1a3af874ad54aeed95c1543b21ee61ec5e58920cafe9"

if (-not (Test-Path $ConfigPath)) { throw "Missing worker config: $ConfigPath" }
if (-not (Test-Path $QcPython)) { throw "Missing QC Python: $QcPython" }
if (-not (Test-Path $RunQc)) { throw "Missing run_qc.py: $RunQc" }

New-Item -ItemType Directory -Force -Path $FieldRoot,$OwnerReview | Out-Null

$cfg = Get-Content $ConfigPath -Raw -Encoding UTF8 | ConvertFrom-Json
$headers = @{ "X-SAYDI-WORKER-TOKEN" = $cfg.worker_token }

function Get-Utf8Sha256([string]$Value) {
    $utf8 = New-Object System.Text.UTF8Encoding($false)
    $bytes = $utf8.GetBytes($Value)
    return [BitConverter]::ToString(
        [Security.Cryptography.SHA256]::Create().ComputeHash($bytes)
    ).Replace("-","").ToLowerInvariant()
}

function Invoke-Saydi([hashtable]$Body) {
    $jsonBody = $Body | ConvertTo-Json -Depth 20 -Compress
    $utf8 = New-Object System.Text.UTF8Encoding($false)
    $bodyBytes = $utf8.GetBytes($jsonBody)
    try {
        return Invoke-RestMethod -Method Post -Uri $cfg.api_url -Headers $headers -ContentType "application/json; charset=utf-8" -Body $bodyBytes -TimeoutSec 90
    } catch {
        $detail = $_.Exception.Message
        try {
            if ($_.Exception.Response -and $_.Exception.Response.GetResponseStream()) {
                $reader = New-Object IO.StreamReader($_.Exception.Response.GetResponseStream())
                $responseBody = $reader.ReadToEnd()
                if ($responseBody) { $detail = "$detail :: $responseBody" }
            }
        } catch {}
        throw "SAYDI API call failed action=$($Body.action): $detail"
    }
}

function Get-Job {
    $response = Invoke-Saydi @{ action = "book_jobs"; book_id = $BookId; max_chapter = 1 }
    return @($response.jobs | Where-Object { [int]$_.chapter_number -eq 1 })[0]
}

function Get-AllChunks {
    $all = @()
    $after = -1
    while ($true) {
        $page = Invoke-Saydi @{ action = "chunks"; job_id = $JobId; after_index = $after; limit = 20 }
        $rows = @($page.chunks)
        if ($rows.Count -eq 0) { break }
        $all += $rows
        $after = [int]$rows[-1].chunk_index
    }
    return $all
}

function Ensure-WorkerRunning {
    $task = Get-ScheduledTask -TaskName $WorkerTaskName -ErrorAction SilentlyContinue
    if (-not $task) { throw "Scheduled task not found: $WorkerTaskName" }
    if ($task.State -ne "Running") {
        Write-Host "[QC006-UTF8] Starting TTS worker..." -ForegroundColor Cyan
        Start-ScheduledTask -TaskName $WorkerTaskName
    }
}

function Wait-Completed([int]$Minutes = 30) {
    $deadline = (Get-Date).AddMinutes($Minutes)
    while ((Get-Date) -lt $deadline) {
        $job = Get-Job
        if ($job.status -eq "completed" -and [int]$job.completed_chunks -eq 3) {
            return $job
        }
        if ($job.status -eq "failed") {
            throw "Repair render failed: $($job.error)"
        }
        Write-Host "[QC006-UTF8] waiting repair render ... status=$($job.status) completed=$($job.completed_chunks)/3"
        Start-Sleep -Seconds 10
    }
    throw "Timed out waiting for repaired target render."
}

Write-Host "[QC006-UTF8] Inspecting canonical text and repair budget..." -ForegroundColor Cyan
$job = Get-Job
if (-not $job -or $job.status -ne "completed") {
    throw "Targeted repair job must be completed before UTF8 correction. status=$($job.status)"
}

$chunks = Get-AllChunks
$target = @($chunks | Where-Object { [int]$_.chunk_index -eq $TargetIndex })[0]
if (-not $target) { throw "Target chunk missing." }

$canonical = [string]$target.canonical_text_content
$canonicalHash = Get-Utf8Sha256 $canonical
if ($canonicalHash -ne $ExpectedCanonicalSha256) {
    throw "Canonical hash mismatch. Expected=$ExpectedCanonicalSha256 actual=$canonicalHash"
}
Write-Host "[QC006-UTF8] Canonical invariant PASS." -ForegroundColor Green

if ([int]$target.qc_repair_attempts -ne 1) {
    throw "Expected exactly one prior repair attempt before UTF8 correction; got $($target.qc_repair_attempts)"
}

$canonicalPath = Join-Path $FieldRoot "canonical_utf8.txt"
$spokenPath = Join-Path $FieldRoot "spoken_utf8.txt"
$helperPath = Join-Path $QcRoot "build_spoken_form_qc006_utf8.py"
[IO.File]::WriteAllText($canonicalPath,$canonical,(New-Object Text.UTF8Encoding($false)))

$py = @'
from pathlib import Path
from saydi_audiobook.pronunciation import build_spoken_form
source = Path(r"C:\SAYDI\qc\qc006\canonical_utf8.txt").read_text(encoding="utf-8")
result = build_spoken_form(source)
Path(r"C:\SAYDI\qc\qc006\spoken_utf8.txt").write_text(result.spoken_text, encoding="utf-8")
'@
[IO.File]::WriteAllText($helperPath,$py,(New-Object Text.UTF8Encoding($false)))

& $QcPython $helperPath
if ($LASTEXITCODE -ne 0 -or -not (Test-Path $spokenPath)) {
    throw "Failed to build UTF8 spoken form."
}
$spoken = (Get-Content $spokenPath -Raw -Encoding UTF8).Trim()
$spokenHash = Get-Utf8Sha256 $spoken
if ($spokenHash -ne $ExpectedSpokenSha256) {
    throw "Spoken-form UTF8 hash mismatch. Expected=$ExpectedSpokenSha256 actual=$spokenHash"
}
Write-Host "[QC006-UTF8] Spoken-form UTF8 invariant PASS." -ForegroundColor Green

$chunkDir = Join-Path (Split-Path $job.output_file_name -Parent) "chunks"
$targetName = ("{0:D6}.wav" -f $TargetIndex)
$targetWav = Join-Path $chunkDir $targetName
if (-not (Test-Path $targetWav)) { throw "Target WAV missing: $targetWav" }

$hashBefore = @{}
Get-ChildItem $chunkDir -Filter "*.wav" -File | ForEach-Object {
    $hashBefore[$_.Name] = (Get-FileHash $_.FullName -Algorithm SHA256).Hash.ToLowerInvariant()
}
if ($hashBefore.Count -ne 3) { throw "Expected exactly 3 chunk WAVs; got $($hashBefore.Count)" }

$badEncodingCopy = Join-Path $OwnerReview "target_after_first_repair_bad_encoding.wav"
Copy-Item $targetWav $badEncodingCopy -Force

$stage = "$targetWav.qc006.utf8.before"
if (Test-Path $stage) { Remove-Item $stage -Force }
Move-Item $targetWav $stage

$requestId = "qc006-field-v1-target-2-utf8"
try {
    $repair = Invoke-Saydi @{
        action = "repair_chunks"
        job_id = $JobId
        chunk_indices = @($TargetIndex)
        repair_request_id = $requestId
        spoken_overrides = @(
            @{
                chunk_index = $TargetIndex
                spoken_text = $spoken
                meta = @{
                    reason = "qc006_utf8_correction"
                    source = "canonical_utf8_hash_verified"
                    canonical_sha256 = $ExpectedCanonicalSha256
                    spoken_sha256 = $ExpectedSpokenSha256
                }
            }
        )
    }
} catch {
    if (Test-Path $stage) { Move-Item $stage $targetWav -Force }
    throw
}

if (-not $repair.queued) {
    if (Test-Path $stage) { Move-Item $stage $targetWav -Force }
    throw "UTF8 corrective repair was not queued."
}

Ensure-WorkerRunning
$job = Wait-Completed
if (-not (Test-Path $targetWav)) {
    if (Test-Path $stage) { Move-Item $stage $targetWav -Force }
    throw "Corrected target WAV was not regenerated."
}

$changed = @()
foreach ($name in $hashBefore.Keys) {
    $path = Join-Path $chunkDir $name
    if (-not (Test-Path $path)) { throw "Chunk disappeared: $name" }
    $afterHash = (Get-FileHash $path -Algorithm SHA256).Hash.ToLowerInvariant()
    if ($afterHash -ne $hashBefore[$name]) { $changed += $name }
}
if ($changed.Count -ne 1 -or $changed[0] -ne $targetName) {
    throw "UTF8 targeted-rerender invariant failed. Changed WAVs: $($changed -join ', ')"
}
Write-Host "[QC006-UTF8] Hash invariant PASS: only $targetName changed." -ForegroundColor Green

$chunks = Get-AllChunks
$target = @($chunks | Where-Object { [int]$_.chunk_index -eq $TargetIndex })[0]
if ((Get-Utf8Sha256 ([string]$target.canonical_text_content)) -ne $ExpectedCanonicalSha256) {
    throw "Canonical text changed after UTF8 correction."
}
if ([int]$target.qc_repair_attempts -ne 2) {
    throw "Expected bounded repair attempt 2/2; got $($target.qc_repair_attempts)"
}
if ((Get-Utf8Sha256 ([string]$target.text_content)) -ne $ExpectedSpokenSha256) {
    throw "Effective TTS text is not the verified UTF8 spoken form after repair."
}

$correctAfterCopy = Join-Path $OwnerReview "target_after_repair.wav"
Copy-Item $targetWav $correctAfterCopy -Force
if (Test-Path $stage) {
    Copy-Item $stage (Join-Path $OwnerReview "target_before_utf8_correction.wav") -Force
    Remove-Item $stage -Force
}

$workerTask = Get-ScheduledTask -TaskName $WorkerTaskName -ErrorAction SilentlyContinue
$workerWasRunning = $workerTask -and $workerTask.State -eq "Running"
if ($workerWasRunning) {
    Write-Host "[QC006-UTF8] Stopping idle TTS worker temporarily to free RAM for Whisper QC..." -ForegroundColor Yellow
    Stop-ScheduledTask -TaskName $WorkerTaskName
    Start-Sleep -Seconds 7
}

$oldMkl = $env:MKL_NUM_THREADS
$oldOmp = $env:OMP_NUM_THREADS
$env:MKL_NUM_THREADS = "2"
$env:OMP_NUM_THREADS = "2"

try {
    Write-Host "[QC006-UTF8] Running post-repair Whisper QC..." -ForegroundColor Cyan
    & $QcPython $RunQc --book-id $BookId --max-chapter 1 --narration-profile GENERAL_CLEAR --observe-only
    if ($LASTEXITCODE -ne 0) { throw "Post-repair run_qc.py failed, exit=$LASTEXITCODE" }
} finally {
    $env:MKL_NUM_THREADS = $oldMkl
    $env:OMP_NUM_THREADS = $oldOmp
    if ($workerWasRunning) {
        Write-Host "[QC006-UTF8] Restarting SAYDI TTS worker..." -ForegroundColor Cyan
        Start-ScheduledTask -TaskName $WorkerTaskName
    }
}

$postPath = Join-Path $QcRoot ("reports\" + $BookId + "\qc_summary.json")
if (-not (Test-Path $postPath)) { throw "Missing post-repair QC report: $postPath" }
$post = @(Get-Content $postPath -Raw -Encoding UTF8 | ConvertFrom-Json)[0]
if ([int]$post.checked_chunks -ne 3) { throw "Post-repair QC did not observe all 3 chunks." }
$postTarget = @($post.chunk_observations | Where-Object { [int]$_.chunk_index -eq $TargetIndex })[0]
if (-not $postTarget) { throw "Missing post-repair target observation." }

$result = [ordered]@{
    schema_version = "saydi-qc006-utf8-final-v1"
    hostname = $env:COMPUTERNAME
    completed_at = (Get-Date).ToString("s")
    canonical_sha256 = $ExpectedCanonicalSha256
    spoken_sha256 = $ExpectedSpokenSha256
    changed_wavs = $changed
    repair_attempts = [int]$target.qc_repair_attempts
    max_repair_attempts = 2
    post_effective_similarity = $postTarget.asr_similarity
    post_canonical_similarity = $postTarget.canonical_asr_similarity
    post_warnings = [int]$post.warnings
    post_errors = [int]$post.errors
    owner_before = (Join-Path $OwnerReview "target_before_repair.wav")
    owner_after = $correctAfterCopy
    bad_encoding_audit = $badEncodingCopy
}
$resultPath = Join-Path $FieldRoot "QC006_FIELD_RESULT.json"
$result | ConvertTo-Json -Depth 20 | Set-Content -Encoding UTF8 $resultPath

$readme = @"
SAYDI QC-006 OWNER LISTENING GATE

BEFORE (controlled bad fixture):
$(Join-Path $OwnerReview "target_before_repair.wav")

AFTER (verified UTF-8 spoken form):
$correctAfterCopy

DO NOT use this audit file for acceptance:
$badEncodingCopy

Technical checks:
- canonical text SHA-256 verified and unchanged;
- spoken form SHA-256 verified before render;
- bounded repair reached exactly 2/2 attempts;
- only chunk 000001.wav changed;
- post-repair Whisper QC completed with TTS worker temporarily released from RAM.

QC-006 remains pending only Owner listening acceptance.
"@
$readme | Set-Content -Encoding UTF8 (Join-Path $OwnerReview "README.txt")

Write-Host ""
Write-Host "SAYDI QC-006 UTF8 FINAL RESULT" -ForegroundColor Cyan
Write-Host "Canonical invariant: PASS" -ForegroundColor Green
Write-Host "Spoken-form UTF8 invariant: PASS" -ForegroundColor Green
Write-Host "Changed WAV only: $($changed -join ', ')" -ForegroundColor Green
Write-Host "Repair attempts: $($target.qc_repair_attempts)/2"
Write-Host "Post effective similarity: $($postTarget.asr_similarity)"
Write-Host "Post canonical similarity: $($postTarget.canonical_asr_similarity)"
Write-Host "Technical field gate: PASS" -ForegroundColor Green
Write-Host "Owner listening gate: PENDING" -ForegroundColor Yellow
Write-Host "Listen AFTER: $correctAfterCopy"
