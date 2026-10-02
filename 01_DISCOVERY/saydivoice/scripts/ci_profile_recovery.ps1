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
if (-not (Test-Path $chrome)) {
  $chromeCmd = Get-Command chrome.exe -ErrorAction SilentlyContinue
  if ($chromeCmd) { $chrome = $chromeCmd.Source }
}
if (-not (Test-Path $chrome)) { throw "Installed Google Chrome not found." }

$profile = Join-Path $env:LOCALAPPDATA "MAGASIN\MediaRobot\saydivoice\browser_profile"
$profilePattern = "*MAGASIN\MediaRobot\saydivoice\browser_profile*"

function Get-SaydiChromeHolders {
  return @(Get-CimInstance Win32_Process -Filter "Name='chrome.exe'" | Where-Object {
    $_.CommandLine -like $profilePattern
  })
}

Write-Host "SAYDI_PROFILE_RECOVERY_MACHINE=$env:COMPUTERNAME"
Write-Host "SAYDI_PROFILE_RECOVERY_ACCOUNT=$([Environment]::UserName)"
Write-Host "SAYDI_PROFILE_RECOVERY_PATH=$profile"
Write-Host "SAYDI_PROFILE_RECOVERY_BROWSER=$chrome"
Write-Host "SAYDI_PROFILE_RECOVERY_GENERATE_ALLOWED=false"
Write-Host "SAYDI_PROFILE_RECOVERY_LOGIN_MODE=NATIVE_INSTALLED_CHROME_THEN_PLAYWRIGHT_VERIFY"

$holders = @(Get-SaydiChromeHolders)
if ($holders.Count -gt 0) {
  throw "Saydi browser profile is locked by another Chrome process. Close only the Chrome window using the MAGASIN Saydi profile, then rerun."
}

Write-Host "Checking whether the persistent SaydiVoice profile is already authenticated."
$quickCheckArgs = @(
  "-m", "saydivoice_discovery.profile_setup",
  "--chromium-executable", $chrome,
  "--timeout-ms", "60000",
  "--auto-wait-seconds", "10",
  "--poll-ms", "1000"
)
& $venvPython @quickCheckArgs
$quickCheck = $LASTEXITCODE

if ($quickCheck -ne 0) {
  $holders = @(Get-SaydiChromeHolders)
  if ($holders.Count -gt 0) {
    throw "Saydi browser profile remained locked after the authentication probe."
  }

  Write-Host "SAYDI_PROFILE_NATIVE_LOGIN_REQUIRED=true"
  Write-Host "Opening INSTALLED Google Chrome directly, outside Playwright, with the dedicated persistent SAYDI profile."
  Write-Host "Owner action: sign in to Gmail/Google if required, then sign in to SaydiVoice in this Chrome window."
  Write-Host "Do not enter credentials in GitHub, terminal, logs, or chat."
  Write-Host "When Gmail and SaydiVoice are authenticated, CLOSE ALL Chrome windows that use this SAYDI profile."
  Write-Host "The workflow will then reopen the exact same profile under Playwright only for non-generative verification."

  New-Item -ItemType Directory -Force -Path $profile | Out-Null
  $nativeArgs = @(
    "--user-data-dir=$profile",
    "--profile-directory=Default",
    "--disable-background-mode",
    "--no-first-run",
    "--new-window",
    "https://accounts.google.com/",
    "https://voice.saydi.ai/vi/studio/tts/"
  )
  Start-Process -FilePath $chrome -ArgumentList $nativeArgs | Out-Null

  $deadline = (Get-Date).AddMinutes(10)
  $sawNativeChrome = $false
  while ((Get-Date) -lt $deadline) {
    Start-Sleep -Seconds 2
    $holders = @(Get-SaydiChromeHolders)
    if ($holders.Count -gt 0) {
      $sawNativeChrome = $true
      continue
    }
    if ($sawNativeChrome) { break }
  }

  $holders = @(Get-SaydiChromeHolders)
  if ($holders.Count -gt 0) {
    Write-Host "SAYDI_PROFILE_RECOVERY_RESULT=OWNER_LOGIN_WINDOW_STILL_OPEN_OR_TIMEOUT"
    Write-Host "SAYDI_PROFILE_RECOVERY_OWNER_ACTION=Complete Gmail/SaydiVoice login in the native Chrome window, close that SAYDI Chrome window, then rerun."
    exit 21
  }
  if (-not $sawNativeChrome) {
    Write-Host "SAYDI_PROFILE_RECOVERY_RESULT=NATIVE_CHROME_DID_NOT_STAY_OPEN"
    exit 22
  }
}

Write-Host "Verifying authentication by reopening the same persistent profile in a fresh installed-Chrome process controlled by Playwright."
$verifyArgs = @(
  "-m", "saydivoice_discovery.profile_setup",
  "--chromium-executable", $chrome,
  "--timeout-ms", "60000",
  "--auto-wait-seconds", "20",
  "--poll-ms", "1000"
)
& $venvPython @verifyArgs
if ($LASTEXITCODE -ne 0) {
  Write-Host "SAYDI_PROFILE_RECOVERY_RESULT=AUTH_NOT_CONFIRMED_AFTER_NATIVE_LOGIN"
  Write-Host "SAYDI_PROFILE_RECOVERY_OWNER_ACTION=Reopen native SAYDI Chrome profile, confirm SaydiVoice studio is logged in, close it, then rerun."
  exit $LASTEXITCODE
}

Write-Host "Authentication check passed. Reopening once more to verify persistence across browser-process restart."
Start-Sleep -Seconds 2
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
Write-Host "SAYDI_PROFILE_RECOVERY_NATIVE_CHROME=PASS"
Write-Host "SAYDI_PROFILE_RECOVERY_GENERATE_CLICKS=0"
