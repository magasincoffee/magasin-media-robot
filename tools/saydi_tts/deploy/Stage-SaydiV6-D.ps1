# SAYDI V6: isolate source staging on D:, never start TTS/ASR or touch V5.
# This script is intentionally invoked only by the dedicated workflow_dispatch workflow.
[CmdletBinding()]
param(
    [ValidateSet('Inspect', 'Stage', 'Install')]
    [string]$Mode = 'Inspect',
    [ValidatePattern('^[a-fA-F0-9]{40}$')]
    [string]$ExpectedSha
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'
$project = 'magasincoffee/magasin-media-robot'
$expectedMachine = 'DESKTOP-H4A16IL'
$stageParent = 'D:\SAYDI_V6_STAGING'
$minCFreeGiB = 2.0
$minDFreeGiB = 10.0

function Assert-PlainDirectory([string]$Directory) {
    $item = Get-Item -LiteralPath $Directory -Force -ErrorAction Stop
    if (-not $item.PSIsContainer) { throw 'NOT_A_DIRECTORY' }
    if (($item.Attributes -band [IO.FileAttributes]::ReparsePoint) -ne 0) {
        throw 'REPARSE_DIRECTORY_DENIED'
    }
}

# Never inherit Supervisor STOP/START state: SAYDI owns its separate authority.
# Source-only staging is NOT SAYDI START, model execution, V5 read,
# installation of services, or a production cutover.
if ([Environment]::MachineName -ne $expectedMachine) { throw 'WRONG_TARGET_H4' }
if ($env:GITHUB_EVENT_NAME -ne 'workflow_dispatch') { throw 'NOT_EXPLICIT_DISPATCH' }
if ($env:GITHUB_REPOSITORY -ne $project) { throw 'WRONG_REPOSITORY' }
if ($env:GITHUB_REF -ne 'refs/heads/main') { throw 'NOT_CANONICAL_MAIN' }
if ($env:GITHUB_ACTOR_ID -ne '191064507' -or $env:GITHUB_ACTOR -ne 'magasincoffee') { throw 'UNTRUSTED_WORKFLOW_ACTOR' }
if (-not $ExpectedSha -or $env:GITHUB_SHA -ne $ExpectedSha) { throw 'MAIN_SHA_MISMATCH' }

$c = Get-PSDrive -Name C -ErrorAction Stop
$d = Get-PSDrive -Name D -ErrorAction Stop
$cFree = [math]::Round($c.Free / 1GB, 3)
$dFree = [math]::Round($d.Free / 1GB, 3)
$diskReady = $cFree -ge $minCFreeGiB -and $dFree -ge $minDFreeGiB
$receipt = [ordered]@{
    schema = 'saydi-v6-d-drive-source-stage-v1'
    mode = $Mode
    host_verified = $true
    commit = $ExpectedSha
    c_free_gib = $cFree
    d_free_gib = $dFree
    threshold_c_gib = $minCFreeGiB
    threshold_d_gib = $minDFreeGiB
    resource_status = if ($diskReady) { 'CAPACITY_PASS' } else { 'HOLD_LOW_DISK' }
    stage_root = 'D_DRIVE_ISOLATED'
    saydi_started = $false
    model_loaded = $false
    production_modified = $false
}

if ($Mode -eq 'Inspect') {
    $receipt['status'] = 'INSPECT_ONLY'
    $receipt | ConvertTo-Json -Compress
    return
}

if (-not $diskReady) {
    $receipt['status'] = 'STAGE_DENIED_RESOURCE'
    $receipt | ConvertTo-Json -Compress
    throw 'STAGE_DENIED_RESOURCE'
}

# Read only canonical repository checkout, not C:\SAYDI or private caches.
$repo = [IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..\..\..'))
$core = Join-Path $repo '02_SAYDI_CORE'
$sot = Join-Path $repo '00_PROJECT\SOURCE_OF_TRUTH.md'
if (-not (Test-Path -LiteralPath $core -PathType Container)) { throw 'SOURCE_CORE_MISSING' }
if (-not (Test-Path -LiteralPath $sot -PathType Leaf)) { throw 'CANONICAL_SOT_MISSING' }
Assert-PlainDirectory $core
Assert-PlainDirectory $repo
if (-not (Test-Path -LiteralPath $stageParent -PathType Container)) {
    throw 'STAGE_PARENT_MISSING_USE_APPROVED_D_ROOT'
}
Assert-PlainDirectory 'D:\'
Assert-PlainDirectory $stageParent

$sourceEntries = @(Get-ChildItem -LiteralPath $core -Recurse -Force -ErrorAction Stop)
foreach ($entry in $sourceEntries) {
    if (($entry.Attributes -band [IO.FileAttributes]::ReparsePoint) -ne 0) {
        throw 'SOURCE_REPARSE_ENTRY_DENIED'
    }
}

$stageName = 'source-' + $ExpectedSha.ToLowerInvariant()
if ($Mode -eq 'Install') {
    $releaseBase = 'D:\SAYDI_V6'
    if (-not (Test-Path -LiteralPath $releaseBase -PathType Container)) {
        New-Item -ItemType Directory -Path $releaseBase -ErrorAction Stop | Out-Null
    }
    Assert-PlainDirectory $releaseBase
    $releases = Join-Path $releaseBase 'releases'
    if (-not (Test-Path -LiteralPath $releases -PathType Container)) {
        New-Item -ItemType Directory -Path $releases -ErrorAction Stop | Out-Null
    }
    Assert-PlainDirectory $releases
    $target = Join-Path $releases $ExpectedSha.ToLowerInvariant()
} else {
    $target = Join-Path $stageParent $stageName
}
if (Test-Path -LiteralPath $target) { throw 'STAGE_EXISTS_NO_OVERWRITE' }
# Never overwrite or delete on error; partial stage remains for later inspection.
New-Item -ItemType Directory -Path $target -ErrorAction Stop | Out-Null
$sourceDestination = Join-Path $target '02_SAYDI_CORE'
Copy-Item -LiteralPath $core -Destination $sourceDestination -Recurse -ErrorAction Stop
$sourceFingerprint = (Get-FileHash -LiteralPath (Join-Path $sourceDestination 'pyproject.toml') -Algorithm SHA256).Hash
if ($Mode -eq 'Install') {
    # Isolated source-based CLI install; it does NOT install or launch VieNeu.
    $python = 'C:\Users\admin\AppData\Local\Programs\Python\Python312\python.exe'
    if (-not (Test-Path -LiteralPath $python -PathType Leaf)) { throw 'TRUSTED_PYTHON_MISSING' }
    $venv = Join-Path $target '.venv'
    & $python -m venv $venv
    if ($LASTEXITCODE -ne 0) { throw 'V6_VENV_CREATION_FAILED' }
    $venvPython = Join-Path $venv 'Scripts\python.exe'
    if (-not (Test-Path -LiteralPath $venvPython -PathType Leaf)) { throw 'V6_VENV_PYTHON_MISSING' }
    $env:PYTHONPATH = Join-Path $sourceDestination 'src'
    try {
        & $venvPython -m saydi_audiobook --help | Out-Null
        if ($LASTEXITCODE -ne 0) { throw 'V6_CLI_SMOKE_FAILED' }
    } finally {
        $env:PYTHONPATH = $null
    }
    $receipt['status'] = 'V6_CLI_INSTALLED_ONLY_NO_TTS_START'
    $receipt['model_runtime'] = 'NOT_STARTED_LOCAL_SAYDI_GATE_REQUIRED'
} else {
    $receipt['status'] = 'SOURCE_STAGED_ONLY_NOT_INSTALLED'
}
$receipt['core_pyproject_sha256'] = $sourceFingerprint
$receipt['stage_identity'] = if ($Mode -eq 'Install') { $ExpectedSha.ToLowerInvariant() } else { $stageName }
$receipt | ConvertTo-Json -Compress | Set-Content -LiteralPath (Join-Path $target 'stage-receipt.json') -Encoding UTF8 -NoNewline
$receipt | ConvertTo-Json -Compress