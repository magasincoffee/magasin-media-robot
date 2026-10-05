param(
    [string]$BookId = "1c0ea552-a391-4f53-9e45-874be5a7ed66",
    [int]$ChunkIndex = 12
)

$ErrorActionPreference = "Stop"

if ($env:COMPUTERNAME -ne "DESKTOP-H4A16IL") {
    throw "QC-004 field gate chỉ chạy trên DESKTOP-H4A16IL. Máy hiện tại: $env:COMPUTERNAME"
}

$QcRoot = "C:\SAYDI\qc"
$ConfigPath = "C:\SAYDI\worker\config.json"
$QcPython = Join-Path $QcRoot ".venv\Scripts\python.exe"
$RunQc = Join-Path $QcRoot "run_qc.py"

if (-not (Test-Path $ConfigPath)) { throw "Missing worker config: $ConfigPath" }
if (-not (Test-Path $QcPython)) { throw "Missing QC Python: $QcPython" }

New-Item -ItemType Directory -Force -Path $QcRoot | Out-Null

$backup = Join-Path $QcRoot ("run_qc.before_qc004." + (Get-Date -Format "yyyyMMdd-HHmmss") + ".py")
if (Test-Path $RunQc) { Copy-Item $RunQc $backup -Force }

$RawBase = "https://raw.githubusercontent.com/magasincoffee/magasin-media-robot/main"
Invoke-WebRequest -UseBasicParsing -Uri "$RawBase/tools/saydi_tts/qc/run_qc.py" -OutFile $RunQc

$PkgRoot = Join-Path $QcRoot "saydi_audiobook"
$PkgData = Join-Path $PkgRoot "data"
New-Item -ItemType Directory -Force -Path $PkgRoot,$PkgData | Out-Null
Invoke-WebRequest -UseBasicParsing -Uri "$RawBase/02_SAYDI_CORE/src/saydi_audiobook/__init__.py" -OutFile (Join-Path $PkgRoot "__init__.py")
Invoke-WebRequest -UseBasicParsing -Uri "$RawBase/02_SAYDI_CORE/src/saydi_audiobook/pronunciation.py" -OutFile (Join-Path $PkgRoot "pronunciation.py")
Invoke-WebRequest -UseBasicParsing -Uri "$RawBase/02_SAYDI_CORE/src/saydi_audiobook/repair.py" -OutFile (Join-Path $PkgRoot "repair.py")
Invoke-WebRequest -UseBasicParsing -Uri "$RawBase/02_SAYDI_CORE/src/saydi_audiobook/contracts.py" -OutFile (Join-Path $PkgRoot "contracts.py")
Invoke-WebRequest -UseBasicParsing -Uri "$RawBase/02_SAYDI_CORE/src/saydi_audiobook/prosody.py" -OutFile (Join-Path $PkgRoot "prosody.py")
Invoke-WebRequest -UseBasicParsing -Uri "$RawBase/02_SAYDI_CORE/src/saydi_audiobook/data/vi_pronunciation_lexicon_v1.json" -OutFile (Join-Path $PkgData "vi_pronunciation_lexicon_v1.json")

$cfg = Get-Content $ConfigPath -Raw | ConvertFrom-Json
$headers = @{
    "Content-Type" = "application/json"
    "X-SAYDI-WORKER-TOKEN" = $cfg.worker_token
}

function Invoke-Saydi([hashtable]$Body) {
    return Invoke-RestMethod -Method Post -Uri $cfg.api_url -Headers $headers -Body ($Body | ConvertTo-Json -Depth 12) -TimeoutSec 90
}

function Get-Job {
    $result = Invoke-Saydi @{ action = "book_jobs"; book_id = $BookId; max_chapter = 1 }
    return @($result.jobs | Where-Object { [int]$_.chapter_number -eq 1 })[0]
}

function Get-AllChunks([string]$JobId) {
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

$job = Get-Job
if (-not $job) { throw "Chapter 1 job not found." }
if ($job.status -ne "completed") { throw "Chapter 1 must be completed before QC-004 field test. status=$($job.status)" }
if (-not $job.output_file_name -or -not (Test-Path $job.output_file_name)) {
    throw "Chapter output missing: $($job.output_file_name)"
}

$chunksBefore = Get-AllChunks $job.id
$targetBefore = @($chunksBefore | Where-Object { [int]$_.chunk_index -eq $ChunkIndex })[0]
if (-not $targetBefore) { throw "Target chunk $ChunkIndex not found." }
if ([int]$targetBefore.qc_repair_attempts -ne 0) {
    throw "Field target already has qc_repair_attempts=$($targetBefore.qc_repair_attempts). Use a fresh target or reset explicitly."
}
if ($targetBefore.spoken_override_applied) {
    throw "Field target already has a spoken override."
}

$chunkDir = Join-Path (Split-Path $job.output_file_name -Parent) "chunks"
$wavFiles = Get-ChildItem $chunkDir -Filter "*.wav" -File
if ($wavFiles.Count -lt 2) { throw "Expected multiple chunk WAV files in $chunkDir" }

$hashBefore = @{}
foreach ($wav in $wavFiles) {
    $hashBefore[$wav.Name] = (Get-FileHash $wav.FullName -Algorithm SHA256).Hash
}

Write-Host "QC-004 FIELD: running targeted repair for Chapter 1 chunk $ChunkIndex" -ForegroundColor Cyan
& $QcPython $RunQc --book-id $BookId --max-chapter 1 --only-chunk $ChunkIndex
if ($LASTEXITCODE -ne 0) {
    throw "run_qc.py failed with exit code $LASTEXITCODE"
}

$summaryPath = Join-Path $QcRoot ("reports\" + $BookId + "\qc_summary.json")
if (-not (Test-Path $summaryPath)) { throw "Missing QC summary: $summaryPath" }
$summary = @(Get-Content $summaryPath -Raw | ConvertFrom-Json)
if ($summary.Count -ne 1) { throw "Expected one chapter summary, got $($summary.Count)" }
$report = $summary[0]

$queued = @($report.queued_repair_indices | ForEach-Object { [int]$_ })
if ($queued.Count -ne 1 -or $queued[0] -ne $ChunkIndex) {
    throw "Expected only chunk $ChunkIndex to be queued. queued=$($queued -join ',')"
}
if ($null -eq $report.post_repair) {
    throw "Missing post_repair QC evidence."
}

$jobAfter = Get-Job
if ($jobAfter.status -ne "completed") { throw "Job did not return to completed: $($jobAfter.status)" }
$chunksAfter = Get-AllChunks $job.id
$targetAfter = @($chunksAfter | Where-Object { [int]$_.chunk_index -eq $ChunkIndex })[0]

if (-not $targetAfter.spoken_override_applied) {
    throw "Target chunk does not expose the TTS-only spoken override after repair."
}
if ([int]$targetAfter.qc_repair_attempts -ne 1) {
    throw "Expected qc_repair_attempts=1, got $($targetAfter.qc_repair_attempts)"
}
if ($targetAfter.canonical_text_content -ne $targetBefore.canonical_text_content) {
    throw "Canonical text changed during repair."
}
if ($targetAfter.text_content -eq $targetAfter.canonical_text_content) {
    throw "Effective spoken text did not change."
}

$changed = @()
$unchanged = @()
foreach ($name in $hashBefore.Keys) {
    $path = Join-Path $chunkDir $name
    if (-not (Test-Path $path)) { throw "Chunk disappeared after repair: $name" }
    $afterHash = (Get-FileHash $path -Algorithm SHA256).Hash
    if ($afterHash -eq $hashBefore[$name]) { $unchanged += $name } else { $changed += $name }
}

$expectedName = ("{0:D6}.wav" -f $ChunkIndex)
if ($changed.Count -ne 1 -or $changed[0] -ne $expectedName) {
    throw "Targeted rerender invariant failed. Changed WAVs: $($changed -join ', ')"
}

$preObs = @($report.chunk_observations | Where-Object { [int]$_.chunk_index -eq $ChunkIndex })[0]
$postObs = @($report.post_repair.chunk_observations | Where-Object { [int]$_.chunk_index -eq $ChunkIndex })[0]
if (-not $preObs -or -not $postObs) {
    throw "Missing pre/post chunk observations."
}

Write-Host ""
Write-Host "SAYDI QC-004 FIELD RESULT" -ForegroundColor Cyan
Write-Host "Queued only chunk: $ChunkIndex"
Write-Host "Changed WAV only: $expectedName"
Write-Host "Canonical text preserved: YES"
Write-Host "Spoken override applied: YES"
Write-Host "QC repair attempts: $($targetAfter.qc_repair_attempts)"
Write-Host "Pre similarity:  $($preObs.asr_similarity)"
Write-Host "Post similarity: $($postObs.asr_similarity)"
if (@($report.post_repair.repair_exhausted).Count -gt 0) {
    Write-Host "Persistent defect routed to REVIEW: $(@($report.post_repair.repair_exhausted) -join ',')" -ForegroundColor Yellow
} else {
    Write-Host "Persistent defect after repair: none in targeted repair plan" -ForegroundColor Green
}
Write-Host "FIELD GATE QC-004: PASS" -ForegroundColor Green
