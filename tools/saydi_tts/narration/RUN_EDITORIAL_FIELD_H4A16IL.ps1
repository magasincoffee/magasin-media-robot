param(
    [string]$BookId = "66000000-0000-4000-8000-000000000009",
    [string]$JobId = "66100000-0000-4000-8000-000000000009",
    [int]$WaitMinutes = 45
)

$ErrorActionPreference = "Stop"

if ($env:COMPUTERNAME -ne "DESKTOP-H4A16IL") {
    throw "Editorial field acceptance only runs on DESKTOP-H4A16IL. Current machine: $env:COMPUTERNAME"
}

$Root = "C:\SAYDI"
$QcRoot = Join-Path $Root "qc"
$ConfigPath = Join-Path $Root "worker\config.json"
$QcPython = Join-Path $QcRoot ".venv\Scripts\python.exe"
$RunQc = Join-Path $QcRoot "run_qc.py"
$PkgRoot = Join-Path $QcRoot "saydi_audiobook"
$PkgData = Join-Path $PkgRoot "data"
$FieldRoot = Join-Path $QcRoot "editorial_field"
$Builder = Join-Path $FieldRoot "build_directed_audio.py"
$ManifestPath = Join-Path $FieldRoot "editorial_field_manifest.json"
$FinalReport = Join-Path $FieldRoot "editorial_field_directed_report.json"

if (-not (Test-Path $ConfigPath)) { throw "Missing worker config: $ConfigPath" }
if (-not (Test-Path $QcPython)) { throw "Missing QC Python: $QcPython" }

New-Item -ItemType Directory -Force -Path $QcRoot,$PkgRoot,$PkgData,$FieldRoot | Out-Null

$RawBase = "https://raw.githubusercontent.com/magasincoffee/magasin-media-robot/main"

function Get-MainFile([string]$RelativePath,[string]$OutFile) {
    $uri = "$RawBase/$RelativePath"
    for ($attempt = 1; $attempt -le 3; $attempt++) {
        try {
            Write-Host "[EDITORIAL FIELD] download $RelativePath (attempt $attempt/3)" -ForegroundColor DarkCyan
            Invoke-WebRequest -UseBasicParsing -Uri $uri -OutFile $OutFile -TimeoutSec 30
            if (-not (Test-Path $OutFile) -or (Get-Item $OutFile).Length -eq 0) {
                throw "Downloaded file is empty: $OutFile"
            }
            return
        } catch {
            if ($attempt -eq 3) { throw }
            Start-Sleep -Seconds 2
        }
    }
}

Write-Host "[EDITORIAL FIELD] Installing current main QC + narration modules..." -ForegroundColor Cyan
Get-MainFile "tools/saydi_tts/qc/run_qc.py" $RunQc
Get-MainFile "tools/saydi_tts/narration/build_directed_audio.py" $Builder
Get-MainFile "02_SAYDI_CORE/src/saydi_audiobook/__init__.py" (Join-Path $PkgRoot "__init__.py")
Get-MainFile "02_SAYDI_CORE/src/saydi_audiobook/pronunciation.py" (Join-Path $PkgRoot "pronunciation.py")
Get-MainFile "02_SAYDI_CORE/src/saydi_audiobook/repair.py" (Join-Path $PkgRoot "repair.py")
Get-MainFile "02_SAYDI_CORE/src/saydi_audiobook/contracts.py" (Join-Path $PkgRoot "contracts.py")
Get-MainFile "02_SAYDI_CORE/src/saydi_audiobook/prosody.py" (Join-Path $PkgRoot "prosody.py")
Get-MainFile "02_SAYDI_CORE/src/saydi_audiobook/data/vi_pronunciation_lexicon_v1.json" (Join-Path $PkgData "vi_pronunciation_lexicon_v1.json")

$cfg = Get-Content $ConfigPath -Raw -Encoding UTF8 | ConvertFrom-Json
$headers = @{ "X-SAYDI-WORKER-TOKEN" = $cfg.worker_token }

function Invoke-Saydi([hashtable]$Body) {
    $jsonBody = $Body | ConvertTo-Json -Depth 30 -Compress
    $utf8 = New-Object System.Text.UTF8Encoding($false)
    $bodyBytes = $utf8.GetBytes($jsonBody)
    return Invoke-RestMethod -Method Post -Uri $cfg.api_url -Headers $headers -ContentType "application/json; charset=utf-8" -Body $bodyBytes -TimeoutSec 90
}

function Get-Job {
    $r = Invoke-Saydi @{ action = "book_jobs"; book_id = $BookId; max_chapter = 1 }
    return @($r.jobs | Where-Object { $_.id -eq $JobId })[0]
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

Write-Host "[EDITORIAL FIELD] Waiting for VieNeu field render..." -ForegroundColor Cyan
$deadline = (Get-Date).AddMinutes($WaitMinutes)
$job = $null
while ((Get-Date) -lt $deadline) {
    $job = Get-Job
    if ($job -and $job.status -eq "completed" -and $job.output_file_name) { break }
    if ($job -and $job.status -eq "failed") { throw "Render failed: $($job.error)" }
    $status = if ($job) { $job.status } else { "missing" }
    $done = if ($job) { $job.completed_chunks } else { 0 }
    $total = if ($job) { $job.total_chunks } else { 0 }
    Write-Host "[EDITORIAL FIELD] render status=$status chunks=$done/$total"
    Start-Sleep -Seconds 10
}
if (-not $job -or $job.status -ne "completed") {
    throw "Timed out waiting for editorial field render."
}

Write-Host "[EDITORIAL FIELD] Render COMPLETE: $($job.output_file_name)" -ForegroundColor Green

Write-Host "[EDITORIAL FIELD] Running post-render pronunciation/prosody/acoustic QC..." -ForegroundColor Cyan
Push-Location $QcRoot
try {
    & $QcPython $RunQc --book-id $BookId --max-chapter 1 --narration-profile STORY_NARRATIVE
    if ($LASTEXITCODE -ne 0) { throw "run_qc.py failed, exit=$LASTEXITCODE" }
} finally {
    Pop-Location
}

$job = Get-Job
if (-not $job.output_file_name) { throw "Job output path missing after QC." }
$out = [IO.FileInfo]$job.output_file_name
$ChunkDir = Join-Path $out.DirectoryName "chunks"
if (-not (Test-Path $ChunkDir)) { throw "Chunk directory missing: $ChunkDir" }

$chunks = @(Get-AllChunks)
if ($chunks.Count -ne [int]$job.total_chunks) {
    throw "Chunk API count mismatch: expected $($job.total_chunks), got $($chunks.Count)"
}

$segments = @()
foreach ($chunk in $chunks) {
    $meta = $chunk.spoken_text_override_meta
    $pause = 500
    if ($meta -and $null -ne $meta.pause_after_ms) { $pause = [int]$meta.pause_after_ms }
    $beat = "NARRATIVE"
    if ($meta -and $meta.beat) { $beat = [string]$meta.beat }

    $segments += [ordered]@{
        index = [int]$chunk.chunk_index
        beat = $beat
        tempo_factor = 1.0
        pause_before_ms = 0
        pause_after_ms = $pause
        canonical_text = [string]$chunk.canonical_text_content
        spoken_text = [string]$chunk.text_content
        must_check_phrases = @($meta.must_check_phrases)
        emphasis_phrases = @($meta.emphasis_phrases)
        pronunciation_qc_required = [bool]$meta.pronunciation_qc_required
    }
}

$manifest = [ordered]@{
    schema_version = "saydi-editorial-field-v1"
    director_version = "editorial-qa-v1"
    title = "Cach Song Chapter 4 Editorial QC Field"
    profile_key = "STORY_NARRATIVE"
    target = [ordered]@{
        duration_seconds_min = 180
        duration_seconds_max = 330
        effective_wpm_min = 110
        effective_wpm_max = 260
    }
    constraints = [ordered]@{
        tempo_factor = 1.0
        post_render_qc_required = $true
        private_manuscript_local_only = $true
    }
    segments = $segments
}

$json = $manifest | ConvertTo-Json -Depth 30
[IO.File]::WriteAllText($ManifestPath,$json,[Text.UTF8Encoding]::new($false))

$FinalMp3 = Join-Path $out.DirectoryName "CACH_SONG_CH4_EDITORIAL_QC_FINAL.mp3"
Write-Host "[EDITORIAL FIELD] Building click-safe final master..." -ForegroundColor Cyan
& $QcPython $Builder --manifest $ManifestPath --chunk-dir $ChunkDir --output $FinalMp3 --report $FinalReport
if ($LASTEXITCODE -ne 0) { throw "Directed audio builder failed, exit=$LASTEXITCODE" }

$report = Get-Content $FinalReport -Raw -Encoding UTF8 | ConvertFrom-Json
if (-not $report.stitching_gate_pass) {
    throw "Stitching gate failed. Review $FinalReport"
}

$summaryPath = Join-Path $QcRoot ("reports\" + $BookId + "\qc_summary.json")
if (-not (Test-Path $summaryPath)) { throw "QC summary missing: $summaryPath" }
$qcSummary = @(Get-Content $summaryPath -Raw -Encoding UTF8 | ConvertFrom-Json)[0]
$finalQc = if ($qcSummary.post_repair) { $qcSummary.post_repair } else { $qcSummary }
$mustCheckFailures = @(
    @($finalQc.chunk_observations) |
        Where-Object { $_.must_check_pass -eq $false }
)

Write-Host ""
Write-Host "[EDITORIAL FIELD] COMPLETE" -ForegroundColor Green
Write-Host "Final MP3: $FinalMp3"
Write-Host "Duration: $($report.duration_sec)s"
Write-Host "Effective WPM: $($report.effective_wpm)"
Write-Host "Stitching gate: $($report.stitching_gate_pass)"
Write-Host "Remaining MUST_CHECK failures: $($mustCheckFailures.Count)"
Write-Host "QC summary: $summaryPath"
Write-Host "Directed report: $FinalReport"

if ($mustCheckFailures.Count -gt 0) {
    Write-Warning "Pronunciation review remains required for: $($mustCheckFailures.chunk_index -join ', ')"
}

Start-Process explorer.exe -ArgumentList "/select,`"$FinalMp3`""
