# SAYDI002-VN-001 read-only H4 telemetry. Never starts/stops workers or writes files.
# Usage: powershell -NoProfile -File INSPECT_VN_8GB_H4_READONLY.ps1 |
#        python vn_8gb_resource_gate.py --input - --stage ASR
$ErrorActionPreference = "Stop"
$hostName = [Environment]::MachineName
if ($hostName -ne "DESKTOP-H4A16IL") { throw "WRONG_H4_HOST" }

$os = Get-CimInstance Win32_OperatingSystem
$logical = @(Get-CimInstance Win32_Processor | Measure-Object -Property NumberOfLogicalProcessors -Sum)[0].Sum
$storage = @{}
foreach ($drive in @("C:", "D:")) {
    $row = Get-CimInstance Win32_LogicalDisk -Filter "DeviceID='$drive'"
    $storage[$drive] = if ($row -and $null -ne $row.FreeSpace) {
        [math]::Round(($row.FreeSpace / 1GB), 3)
    } else { $null }
}

$ram = @()
for ($i=0; $i -lt 5; $i++) {
    $m = Get-CimInstance Win32_OperatingSystem
    if (-not $m -or $null -eq $m.FreePhysicalMemory) { throw "RAM_INVENTORY_UNAVAILABLE" }
    $ram += [math]::Round(($m.FreePhysicalMemory / 1MB), 3)
    if ($i -lt 4) { Start-Sleep -Milliseconds 1000 }
}

# No raw CommandLine / editor / file paths are output. An unrecognized SAYDI
# model script blocks resource admission. Normal status/UI observers are ignored.
$heavy = @()
$tts = "render_owner_approved_v5\.py|render_candidate_ch03_146(?:_r2)?\.py"
$asr = "qc_local_segments\.py|saydi_review_qc\.py"
$wrappers = "chapter_v5_job\.py|chapter2_v5_qc_guarded\.py|saydi_quality_improve\.py|repair_chapter1_owner_v5_r2\.py"
foreach ($proc in @(Get-CimInstance Win32_Process | Where-Object {
    $_.Name -match "^(python|pythonw|ffmpeg)(\.exe)?$"
})) {
    $line = [string]$proc.CommandLine
    if (-not $line) { continue }
    $kind = $null
    if ($line -match $wrappers) { $kind = "WRAPPER" }
    elseif ($line -match $tts) { $kind = "TTS" }
    elseif ($line -match $asr) { $kind = "ASR" }
    elseif ($line -match '(?i)vieneu|faster.whisper|onnxruntime|transcribe.*\.py|whisper.*\.py') {
        $kind = "UNKNOWN"
    }
    if ($kind) { $heavy += @{ kind = $kind; pid = [int]$proc.ProcessId } }
}
$tempDrive = $null
if ($env:TEMP -match "^[A-Za-z]:") { $tempDrive = $env:TEMP.Substring(0,2).ToUpperInvariant() }
$snapshot = @{
    schema = "saydi-vn-8gb-h4-telemetry-v1"
    host = $hostName
    captured_at = (Get-Date).ToString("o")
    physical_ram_gib = [math]::Round(($os.TotalVisibleMemorySize / 1MB), 3)
    cpu_logical_threads = [int]$logical
    ram_samples_gib = @($ram)
    disk_c_free_gib = $storage["C:"]
    disk_d_free_gib = $storage["D:"]
    temp_drive = $tempDrive
    heavy_workers = @($heavy)
    # Only verified secure Control lifecycle may set these; read-only probe
    # deliberately NEVER claims Owner authentication or exclusive ownership.
    owner_stop_latch = "UNKNOWN"
    checkpoint_ownership = "UNKNOWN"
    worker_mutex_state = "UNKNOWN"
}
ConvertTo-Json -InputObject $snapshot -Depth 5 -Compress
