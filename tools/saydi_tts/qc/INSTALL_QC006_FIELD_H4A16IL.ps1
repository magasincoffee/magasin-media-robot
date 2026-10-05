param(
    [int]$WaitMinutes = 45
)

$ErrorActionPreference = "Stop"

if ($env:COMPUTERNAME -ne "DESKTOP-H4A16IL") {
    throw "QC-006 field acceptance chỉ chạy trên DESKTOP-H4A16IL. Máy hiện tại: $env:COMPUTERNAME"
}

$QcRoot = "C:\SAYDI\qc"
$ConfigPath = "C:\SAYDI\worker\config.json"
$QcPython = Join-Path $QcRoot ".venv\Scripts\python.exe"
$RunQc = Join-Path $QcRoot "run_qc.py"
$PkgRoot = Join-Path $QcRoot "saydi_audiobook"
$PkgData = Join-Path $PkgRoot "data"
$FieldRoot = Join-Path $QcRoot "qc006"
$OwnerReview = Join-Path $FieldRoot "owner_review"
$ManifestPath = Join-Path $FieldRoot "qc006_field_manifest.json"

if (-not (Test-Path $ConfigPath)) { throw "Missing worker config: $ConfigPath" }
if (-not (Test-Path $QcPython)) { throw "Missing QC Python: $QcPython" }

New-Item -ItemType Directory -Force -Path $QcRoot,$PkgRoot,$PkgData,$FieldRoot,$OwnerReview | Out-Null

$RawBase = "https://raw.githubusercontent.com/magasincoffee/magasin-media-robot/main"
Invoke-WebRequest -UseBasicParsing -Uri "$RawBase/tools/saydi_tts/qc/run_qc.py" -OutFile $RunQc
Invoke-WebRequest -UseBasicParsing -Uri "$RawBase/02_SAYDI_CORE/src/saydi_audiobook/__init__.py" -OutFile (Join-Path $PkgRoot "__init__.py")
Invoke-WebRequest -UseBasicParsing -Uri "$RawBase/02_SAYDI_CORE/src/saydi_audiobook/pronunciation.py" -OutFile (Join-Path $PkgRoot "pronunciation.py")
Invoke-WebRequest -UseBasicParsing -Uri "$RawBase/02_SAYDI_CORE/src/saydi_audiobook/repair.py" -OutFile (Join-Path $PkgRoot "repair.py")
Invoke-WebRequest -UseBasicParsing -Uri "$RawBase/02_SAYDI_CORE/src/saydi_audiobook/contracts.py" -OutFile (Join-Path $PkgRoot "contracts.py")
Invoke-WebRequest -UseBasicParsing -Uri "$RawBase/02_SAYDI_CORE/src/saydi_audiobook/prosody.py" -OutFile (Join-Path $PkgRoot "prosody.py")
Invoke-WebRequest -UseBasicParsing -Uri "$RawBase/02_SAYDI_CORE/src/saydi_audiobook/data/vi_pronunciation_lexicon_v1.json" -OutFile (Join-Path $PkgData "vi_pronunciation_lexicon_v1.json")
Invoke-WebRequest -UseBasicParsing -Uri "$RawBase/tools/saydi_tts/qc/fixtures/qc006_field_manifest.json" -OutFile $ManifestPath

$cfg = Get-Content $ConfigPath -Raw | ConvertFrom-Json
$manifest = Get-Content $ManifestPath -Raw | ConvertFrom-Json
$headers = @{
    "Content-Type" = "application/json"
    "X-SAYDI-WORKER-TOKEN" = $cfg.worker_token
}

function Invoke-Saydi([hashtable]$Body) {
    return Invoke-RestMethod -Method Post -Uri $cfg.api_url -Headers $headers -Body ($Body | ConvertTo-Json -Depth 20) -TimeoutSec 90
}

function Get-BookJob([string]$BookId) {
    $response = Invoke-Saydi @{ action = "book_jobs"; book_id = $BookId; max_chapter = 1 }
    return @($response.jobs | Where-Object { [int]$_.chapter_number -eq 1 })[0]
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

function Wait-BookCompleted([string]$BookId,[string]$CaseId) {
    $deadline = (Get-Date).AddMinutes($WaitMinutes)
    while ((Get-Date) -lt $deadline) {
        $job = Get-BookJob $BookId
        if ($job -and $job.status -eq "completed" -and $job.output_file_name) {
            Write-Host "[QC006] $CaseId render completed: $($job.output_file_name)" -ForegroundColor Green
            return $job
        }
        if ($job -and $job.status -eq "failed") {
            throw "QC006 render failed for ${CaseId}: $($job.error)"
        }
        $state = if ($job) { $job.status } else { "missing" }
        Write-Host "[QC006] waiting $CaseId ... status=$state"
        Start-Sleep -Seconds 10
    }
    throw "Timed out waiting for $CaseId after $WaitMinutes minutes."
}

function Run-ProfileQc($Case,[switch]$ObserveOnly) {
    $args = @(
        $RunQc,
        "--book-id", [string]$Case.book_id,
        "--max-chapter", "1",
        "--narration-profile", [string]$Case.profile_key
    )
    if ($ObserveOnly) { $args += "--observe-only" }
    Write-Host "[QC006] QC case=$($Case.case_id) profile=$($Case.profile_key)" -ForegroundColor Cyan
    & $QcPython @args
    if ($LASTEXITCODE -ne 0) {
        throw "run_qc.py failed for $($Case.case_id), exit=$LASTEXITCODE"
    }
    $summaryPath = Join-Path $QcRoot ("reports\" + [string]$Case.book_id + "\qc_summary.json")
    if (-not (Test-Path $summaryPath)) { throw "Missing QC summary: $summaryPath" }
    $copy = Join-Path $FieldRoot ("$($Case.case_id)_qc_summary.json")
    Copy-Item $summaryPath $copy -Force
    return @(Get-Content $summaryPath -Raw | ConvertFrom-Json)[0]
}

function Assert-ProfileEvidence($Case,$Report) {
    if ([int]$Report.checked_chunks -ne [int]$Case.expected_chunks) {
        throw "$($Case.case_id): expected $($Case.expected_chunks) chunks, got $($Report.checked_chunks)"
    }
    if ($Report.prosody_profile_key -ne $Case.profile_key) {
        throw "$($Case.case_id): profile mismatch $($Report.prosody_profile_key)"
    }
    if (-not $Report.prosody_profile_fingerprint) {
        throw "$($Case.case_id): missing profile fingerprint"
    }
    $observations = @($Report.chunk_observations)
    if ($observations.Count -ne [int]$Case.expected_chunks) {
        throw "$($Case.case_id): observation count mismatch"
    }
    foreach ($obs in $observations) {
        if ($obs.audio_sha256 -notmatch '^[0-9a-fA-F]{64}$') {
            throw "$($Case.case_id): invalid audio hash for chunk $($obs.chunk_index)"
        }
        if ($obs.prosody_profile_key -ne $Case.profile_key) {
            throw "$($Case.case_id): chunk $($obs.chunk_index) missing active profile"
        }
        if ($null -eq $obs.speaking_rate_wpm -or
            $null -eq $obs.pause_ratio -or
            $null -eq $obs.pitch_variation_semitones -or
            $null -eq $obs.energy_variation_db) {
            throw "$($Case.case_id): incomplete prosody metrics on chunk $($obs.chunk_index)"
        }
    }
}

function New-SpokenForm([string]$CanonicalText) {
    $sourcePath = Join-Path $FieldRoot "repair_source.txt"
    $outPath = Join-Path $FieldRoot "repair_spoken.txt"
    [IO.File]::WriteAllText($sourcePath,$CanonicalText,(New-Object Text.UTF8Encoding($false)))
    $py = @'
from pathlib import Path
from saydi_audiobook.pronunciation import build_spoken_form
source = Path(r"C:\SAYDI\qc\qc006\repair_source.txt").read_text(encoding="utf-8")
result = build_spoken_form(source)
Path(r"C:\SAYDI\qc\qc006\repair_spoken.txt").write_text(result.spoken_text, encoding="utf-8")
'@
    $pyPath = Join-Path $FieldRoot "build_spoken_form.py"
    [IO.File]::WriteAllText($pyPath,$py,(New-Object Text.UTF8Encoding($false)))
    & $QcPython $pyPath
    if ($LASTEXITCODE -ne 0 -or -not (Test-Path $outPath)) { throw "Failed to build spoken form." }
    return (Get-Content $outPath -Raw).Trim()
}

$jobs = @{}
foreach ($case in @($manifest.cases)) {
    $jobs[$case.case_id] = Wait-BookCompleted ([string]$case.book_id) ([string]$case.case_id)
}

$results = @()

foreach ($case in @($manifest.cases | Where-Object { $_.case_id -in @("business_clear","story_narrative","general_clear") })) {
    $report = Run-ProfileQc $case -ObserveOnly
    Assert-ProfileEvidence $case $report

    $pronunciationLocalized = @($report.chunk_observations | Where-Object {
        @($_.unclear_tokens).Count -gt 0 -or ($null -ne $_.min_word_confidence -and [double]$_.min_word_confidence -lt 0.68)
    }).Count
    $prosodyLocalized = @($report.chunk_observations | Where-Object {
        @($_.prosody_reasons).Count -gt 0
    }).Count

    $results += [pscustomobject]@{
        case_id = $case.case_id
        profile = $case.profile_key
        chunks = [int]$report.checked_chunks
        pronunciation_localized_chunks = $pronunciationLocalized
        prosody_localized_chunks = $prosodyLocalized
        warnings = [int]$report.warnings
        errors = [int]$report.errors
        qc_result = if (($report.warnings + $report.errors) -gt 0) { "REVIEW" } else { "PASS" }
    }
}

$repairCase = @($manifest.cases | Where-Object { $_.case_id -eq "targeted_repair" })[0]
$repairJob = $jobs["targeted_repair"]
$targetIndex = [int]$repairCase.repair_chunk_index
$preReport = Run-ProfileQc $repairCase -ObserveOnly
Assert-ProfileEvidence $repairCase $preReport
$preObs = @($preReport.chunk_observations | Where-Object { [int]$_.chunk_index -eq $targetIndex })[0]
if (-not $preObs) { throw "Missing pre-repair target observation." }
if ([double]$preObs.asr_similarity -ge 0.76) {
    throw "Controlled fault was not detected strongly enough. similarity=$($preObs.asr_similarity)"
}

$chunksBefore = Get-AllChunks $repairJob.id
$targetBefore = @($chunksBefore | Where-Object { [int]$_.chunk_index -eq $targetIndex })[0]
if (-not $targetBefore.spoken_override_applied) {
    throw "QC006 fault injection override is missing before repair."
}
if ([int]$targetBefore.qc_repair_attempts -ge 2) {
    throw "Target repair budget already exhausted."
}

$chunkDir = Join-Path (Split-Path $repairJob.output_file_name -Parent) "chunks"
$wavFiles = Get-ChildItem $chunkDir -Filter "*.wav" -File
if ($wavFiles.Count -ne [int]$repairCase.expected_chunks) {
    throw "Expected $($repairCase.expected_chunks) WAV files, got $($wavFiles.Count)"
}
$hashBefore = @{}
foreach ($wav in $wavFiles) {
    $hashBefore[$wav.Name] = (Get-FileHash $wav.FullName -Algorithm SHA256).Hash
}

$targetName = ("{0:D6}.wav" -f $targetIndex)
$targetWav = Join-Path $chunkDir $targetName
$beforeCopy = Join-Path $OwnerReview "target_before_repair.wav"
Copy-Item $targetWav $beforeCopy -Force

$staged = "$targetWav.qc006.before"
if (Test-Path $staged) { Remove-Item $staged -Force }
Move-Item $targetWav $staged

$spoken = New-SpokenForm ([string]$repairCase.canonical_text)
$requestId = "qc006-field-v1-target-1"
try {
    $repairResponse = Invoke-Saydi @{
        action = "repair_chunks"
        job_id = [string]$repairJob.id
        chunk_indices = @($targetIndex)
        repair_request_id = $requestId
        spoken_overrides = @(
            @{
                chunk_index = $targetIndex
                spoken_text = $spoken
                meta = @{
                    reason = "qc006_field_acceptance"
                    source = "synthetic_fault_injection"
                    canonical_text_preserved = $true
                    expected_profile = [string]$repairCase.profile_key
                }
            }
        )
    }
} catch {
    if (Test-Path $staged) { Move-Item $staged $targetWav -Force }
    throw
}

if (-not $repairResponse.queued) {
    if (Test-Path $staged) { Move-Item $staged $targetWav -Force }
    throw "Targeted repair was not queued: $($repairResponse | ConvertTo-Json -Depth 10)"
}

$repairJobAfter = Wait-BookCompleted ([string]$repairCase.book_id) "targeted_repair_post"
if (-not (Test-Path $targetWav)) {
    if (Test-Path $staged) { Move-Item $staged $targetWav -Force }
    throw "Target WAV was not regenerated."
}

$changed = @()
foreach ($name in $hashBefore.Keys) {
    $path = Join-Path $chunkDir $name
    if (-not (Test-Path $path)) { throw "Chunk disappeared: $name" }
    $afterHash = (Get-FileHash $path -Algorithm SHA256).Hash
    if ($afterHash -ne $hashBefore[$name]) { $changed += $name }
}
if ($changed.Count -ne 1 -or $changed[0] -ne $targetName) {
    throw "Targeted rerender invariant failed. Changed WAVs: $($changed -join ', ')"
}

$afterCopy = Join-Path $OwnerReview "target_after_repair.wav"
Copy-Item $targetWav $afterCopy -Force

$postReport = Run-ProfileQc $repairCase -ObserveOnly
Assert-ProfileEvidence $repairCase $postReport
$postObs = @($postReport.chunk_observations | Where-Object { [int]$_.chunk_index -eq $targetIndex })[0]
if (-not $postObs) { throw "Missing post-repair target observation." }

$chunksAfter = Get-AllChunks $repairJob.id
$targetAfter = @($chunksAfter | Where-Object { [int]$_.chunk_index -eq $targetIndex })[0]
if ($targetAfter.canonical_text_content -ne [string]$repairCase.canonical_text) {
    throw "Canonical text changed during QC006 repair."
}
if (-not $targetAfter.spoken_override_applied) {
    throw "Correct spoken override is not active after repair."
}
if ([int]$targetAfter.qc_repair_attempts -lt 1 -or [int]$targetAfter.qc_repair_attempts -gt 2) {
    throw "Bounded repair attempt invariant failed: $($targetAfter.qc_repair_attempts)"
}

if (Test-Path $staged) {
    Copy-Item $staged (Join-Path $OwnerReview "target_before_repair_original_staged.wav") -Force
    Remove-Item $staged -Force
}

$results += [pscustomobject]@{
    case_id = "targeted_repair"
    profile = $repairCase.profile_key
    chunks = [int]$postReport.checked_chunks
    pronunciation_localized_chunks = @($preReport.chunk_observations | Where-Object {
        [double]$_.asr_similarity -lt 0.76
    }).Count
    prosody_localized_chunks = @($postReport.chunk_observations | Where-Object {
        @($_.prosody_reasons).Count -gt 0
    }).Count
    warnings = [int]$postReport.warnings
    errors = [int]$postReport.errors
    qc_result = if (($postReport.warnings + $postReport.errors) -gt 0) { "REVIEW" } else { "PASS" }
    pre_similarity = [double]$preObs.asr_similarity
    post_similarity = [double]$postObs.asr_similarity
    changed_wavs = $changed -join ","
    repair_attempts = [int]$targetAfter.qc_repair_attempts
}

$summary = [ordered]@{
    schema_version = "saydi-qc006-field-result-v1"
    hostname = $env:COMPUTERNAME
    completed_at = (Get-Date).ToString("s")
    voice_name = [string]$manifest.voice_name
    synthetic_only = $true
    cases = $results
    targeted_repair = [ordered]@{
        target_chunk_index = $targetIndex
        changed_wavs = $changed
        canonical_text_preserved = $true
        repair_attempts = [int]$targetAfter.qc_repair_attempts
        max_repair_attempts = 2
        pre_similarity = [double]$preObs.asr_similarity
        post_similarity = [double]$postObs.asr_similarity
        before_audio = $beforeCopy
        after_audio = $afterCopy
    }
    owner_listening_required = $true
    owner_review_folder = $OwnerReview
}

$summaryPath = Join-Path $FieldRoot "QC006_FIELD_RESULT.json"
$summary | ConvertTo-Json -Depth 20 | Set-Content -Encoding UTF8 $summaryPath

$readme = @"
SAYDI QC-006 OWNER LISTENING GATE

Please compare:
BEFORE: $beforeCopy
AFTER:  $afterCopy

Technical field acceptance has verified:
- synthetic-only fixtures;
- profile-specific pronunciation/prosody measurements;
- exact audio hash traceability;
- controlled pronunciation/content defect localization;
- only the target chunk was rerendered;
- canonical text remained unchanged;
- repair attempts remained bounded;
- post-repair QC executed.

QC-006 is not DONE until Owner listens to BEFORE/AFTER and accepts the final narration quality.
"@
$readme | Set-Content -Encoding UTF8 (Join-Path $OwnerReview "README.txt")

Write-Host ""
Write-Host "SAYDI QC-006 TECHNICAL FIELD RESULT" -ForegroundColor Cyan
$results | Format-Table -AutoSize
Write-Host ""
Write-Host "Targeted repair changed only: $($changed -join ', ')" -ForegroundColor Green
Write-Host "Pre similarity:  $($preObs.asr_similarity)"
Write-Host "Post similarity: $($postObs.asr_similarity)"
Write-Host "Repair attempts: $($targetAfter.qc_repair_attempts)/2"
Write-Host "Technical field gate: PASS" -ForegroundColor Green
Write-Host "Owner listening gate: PENDING" -ForegroundColor Yellow
Write-Host "Listen here: $OwnerReview"
Write-Host "Result: $summaryPath"
