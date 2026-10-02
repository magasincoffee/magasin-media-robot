$ErrorActionPreference = "Stop"

$repoRoot = Resolve-Path (Join-Path $PSScriptRoot "..\..\..")
$saydiRoot = Join-Path $repoRoot "01_DISCOVERY\saydivoice"
Set-Location $saydiRoot

$python = $null
$py = Get-Command py.exe -ErrorAction SilentlyContinue
if ($py) {
  $candidate = (& $py.Source -3 -c "import sys; print(sys.executable)").Trim()
  if ($LASTEXITCODE -eq 0 -and (Test-Path $candidate)) { $python = $candidate }
}
if (-not $python) {
  $cmd = Get-Command python.exe -ErrorAction SilentlyContinue
  if ($cmd) { $python = $cmd.Source }
}
if (-not $python) { throw "Python 3 not found." }

$venv = Join-Path $env:RUNNER_TEMP "saydi-profile-recovery-venv"
if (Test-Path $venv) { Remove-Item $venv -Recurse -Force }
& $python -m venv $venv
if ($LASTEXITCODE -ne 0) { throw "venv creation failed" }

$venvPython = Join-Path $venv "Scripts\python.exe"
& $venvPython -m pip install --disable-pip-version-check --quiet --upgrade pip
if ($LASTEXITCODE -ne 0) { throw "pip upgrade failed" }
& $venvPython -m pip install --disable-pip-version-check --quiet -r requirements-dev.txt
if ($LASTEXITCODE -ne 0) { throw "dependency install failed" }
& $venvPython -m pip install --disable-pip-version-check --quiet -e .
if ($LASTEXITCODE -ne 0) { throw "package install failed" }

$chrome = Join-Path $env:ProgramFiles "Google\Chrome\Application\chrome.exe"
if (-not (Test-Path $chrome)) {
  $pf86 = [Environment]::GetEnvironmentVariable("ProgramFiles(x86)")
  if ($pf86) { $chrome = Join-Path $pf86 "Google\Chrome\Application\chrome.exe" }
}
if (-not (Test-Path $chrome)) { throw "Installed Google Chrome not found." }

$profile = Join-Path $env:LOCALAPPDATA "MAGASIN\MediaRobot\saydivoice\browser_profile"
Write-Host "SAYDI_PROFILE_RECOVERY_MACHINE=$env:COMPUTERNAME"
Write-Host "SAYDI_PROFILE_RECOVERY_ACCOUNT=$([Environment]::UserName)"
Write-Host "SAYDI_PROFILE_RECOVERY_PATH=$profile"
Write-Host "SAYDI_PROFILE_RECOVERY_GENERATE_ALLOWED=false"

$holders = @(Get-CimInstance Win32_Process -Filter "Name='chrome.exe'" | Where-Object {
  $_.CommandLine -like "*MAGASIN\MediaRobot\saydivoice\browser_profile*"
})
if ($holders.Count -gt 0) {
  throw "Saydi browser profile is locked by another Chrome process. Close only the Chrome window using the MAGASIN Saydi profile, then rerun."
}

Write-Host "Opening the exact persistent SaydiVoice profile for authentication recovery."
Write-Host "If Saydi requests login, complete it in this visible Chrome window. This workflow cannot click Generate."
$setupArgs = @(
  "-m", "saydivoice_discovery.profile_setup",
  "--chromium-executable", $chrome,
  "--timeout-ms", "60000",
  "--auto-wait-seconds", "600",
  "--poll-ms", "2000"
)
& $venvPython @setupArgs
$first = $LASTEXITCODE
if ($first -ne 0) {
  Write-Host "SAYDI_PROFILE_RECOVERY_RESULT=OWNER_LOGIN_REQUIRED_OR_AUTH_NOT_CONFIRMED"
  exit $first
}

Write-Host "First authentication check passed. Reopening the profile in a fresh browser process to verify persistence."
Start-Sleep -Seconds 2
$verifyArgs = @(
  "-m", "saydivoice_discovery.profile_setup",
  "--chromium-executable", $chrome,
  "--timeout-ms", "60000",
  "--auto-wait-seconds", "15",
  "--poll-ms", "1000"
)
& $venvPython @verifyArgs
if ($LASTEXITCODE -ne 0) {
  Write-Host "SAYDI_PROFILE_RECOVERY_RESULT=PERSISTENCE_CHECK_FAILED"
  exit $LASTEXITCODE
}

Write-Host "Persistent auth survived browser-process restart. Running non-generative surface/catalog discovery."
& $venvPython -m saydivoice_discovery.cli --chromium-executable $chrome --timeout-ms 60000 --settle-ms 2500
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

& $venvPython -m saydivoice_discovery.ci_gate
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "SAYDI_PROFILE_RECOVERY_RESULT=PASS"
Write-Host "SAYDI_PROFILE_RECOVERY_PERSISTENCE=PASS"
Write-Host "SAYDI_PROFILE_RECOVERY_AUTH_GATE=PASS"
Write-Host "SAYDI_PROFILE_RECOVERY_GENERATE_CLICKS=0"
