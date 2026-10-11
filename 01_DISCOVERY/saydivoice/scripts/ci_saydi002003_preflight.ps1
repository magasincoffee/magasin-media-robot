# SAYDI002-003 — non-generative authenticated provider preflight
# This runner is intentionally limited to the historical recovered host.
$ErrorActionPreference = "Stop"
if ($env:COMPUTERNAME.ToUpperInvariant() -ne "DESKTOP-4K7IM13") {
    throw "WRONG_RECOVERED_PROFILE_HOST: non-generative preflight refused"
}
if ($env:USERNAME.ToUpperInvariant() -ne "DELL") {
    throw "WRONG_RECOVERED_PROFILE_USER: preflight refused"
}
if (-not $env:RUNNER_TEMP -or -not $env:LOCALAPPDATA) {
    throw "REQUIRES_WINDOWS_SELF_HOSTED_RUNNER"
}
$profile = Join-Path $env:LOCALAPPDATA "MAGASIN\MediaRobot\saydivoice\browser_profile"
if (-not (Test-Path -LiteralPath $profile -PathType Container)) {
    throw "RECOVERED_PROFILE_NOT_FOUND"
}
$holders = @(Get-CimInstance Win32_Process -Filter "Name='chrome.exe'" | Where-Object {
    $_.CommandLine -like "*MAGASIN\MediaRobot\saydivoice\browser_profile*"
})
if ($holders.Count -gt 0) {
    throw "RECOVERED_PROFILE_BUSY: no Chrome processes stopped"
}
$chrome = Join-Path $env:ProgramFiles "Google\Chrome\Application\chrome.exe"
if (-not (Test-Path $chrome -PathType Leaf)) {
    $pf86 = [Environment]::GetEnvironmentVariable("ProgramFiles(x86)")
    if ($pf86) { $chrome = Join-Path $pf86 "Google\Chrome\Application\chrome.exe" }
}
if (-not (Test-Path $chrome -PathType Leaf)) {
    throw "INSTALLED_CHROME_NOT_FOUND"
}
$py = Get-Command py.exe -ErrorAction SilentlyContinue
if ($py) {
    $systemPython = (& $py.Source -3 -c "import sys; print(sys.executable)").Trim()
} else {
    $cmd = Get-Command python.exe -ErrorAction SilentlyContinue
    if (-not $cmd) { throw "PYTHON3_NOT_FOUND" }
    $systemPython = $cmd.Source
}
$venv = Join-Path $env:RUNNER_TEMP ("saydi002003-" + [Guid]::NewGuid().ToString("N"))
& $systemPython -m venv $venv
if ($LASTEXITCODE -ne 0) { throw "VENV_SETUP_FAILED" }
$python = Join-Path $venv "Scripts\python.exe"
$root = Resolve-Path (Join-Path $PSScriptRoot "..\..\..")
$src = Join-Path $root "01_DISCOVERY\saydivoice"
Push-Location $src
try {
    & $python -m pip install --quiet --disable-pip-version-check -r requirements.txt
    if ($LASTEXITCODE -ne 0) { throw "DEPENDENCY_SETUP_FAILED" }
    $env:PYTHONPATH = Join-Path $src "src"
    $outputDir = Join-Path $env:LOCALAPPDATA "MAGASIN\MediaRobot\saydivoice\reports"
    New-Item -ItemType Directory -Force -Path $outputDir | Out-Null
    $evidence = Join-Path $outputDir ("SAYDI002003_READONLY_" + [Guid]::NewGuid().ToString("N") + ".json")
    Write-Host "SAYDI002_003_HOST_VALIDATED=true"
    Write-Host "SAYDI002_003_PROFILE_FOUND=true"
    Write-Host "SAYDI002_003_MODE=NO_GENERATE_NO_LOGIN_NO_CONFIG_CHANGE"
    & $python -m saydivoice_discovery.saydi002_preflight --chrome $chrome --output $evidence --allow-authenticated-preflight
    if ($LASTEXITCODE -ne 0) { throw "NON_GENERATIVE_AUTH_CATALOG_PREFLIGHT_BLOCKED" }
    Write-Host "SAYDI002_003_LOCAL_METADATA_RECEIPT=CREATED"
    Write-Host "SAYDI002_003_PRIVATE_PROFILE_UPLOADED=false"
} finally {
    Pop-Location
    # No deletion of profile, browser sessions, TTS or runtime checkpoints.
}
