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

$venv = Join-Path $env:RUNNER_TEMP "saydi-audiobook-live-venv"
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
  $chromeCmd = Get-Command chrome.exe -ErrorAction SilentlyContinue
  if ($chromeCmd) { $chrome = $chromeCmd.Source }
}
if (-not (Test-Path $chrome)) { throw "Installed Google Chrome not found." }

$profile = Join-Path $env:LOCALAPPDATA "MAGASIN\MediaRobot\saydivoice\browser_profile"
if (-not (Test-Path $profile)) { throw "Saydi persistent browser profile is missing." }

$holders = @(Get-CimInstance Win32_Process -Filter "Name='chrome.exe'" | Where-Object {
  $_.CommandLine -like "*MAGASIN\MediaRobot\saydivoice\browser_profile*"
})
if ($holders.Count -gt 0) { throw "Saydi browser profile is locked by another Chrome process." }

$sample = Join-Path $repoRoot "02_SAYDI_CORE\fixtures\business_sample_vi.txt"
if (-not (Test-Path $sample)) { throw "Synthetic audiobook sample text is missing." }

$output = Join-Path $repoRoot "SAYDI_SAYDIVOICE_SAMPLE.mp3"
if (Test-Path $output) { Remove-Item $output -Force }

Write-Host "Authorized live side effect: exactly one SaydiVoice Generate click; no retry."
Write-Host "Preset: slow_emotional"
Write-Host "Sample source: synthetic repository fixture"

$argsList = @(
  "-m", "saydivoice_discovery.d7_controlled_generation",
  "--chromium-executable", $chrome,
  "--generation-timeout-ms", "90000",
  "--preset", "slow_emotional",
  "--sample-file", $sample,
  "--download-output", $output,
  "--allow-download",
  "--download-timeout-ms", "20000"
)
& $venvPython @argsList

if ($LASTEXITCODE -ne 0) {
  throw "Controlled SaydiVoice sample generation failed with exit code $LASTEXITCODE."
}
if (-not (Test-Path $output)) { throw "SaydiVoice MP3 output missing." }

$info = Get-Item $output
if ($info.Length -le 0) { throw "SaydiVoice MP3 output is empty." }
$hash = (Get-FileHash $output -Algorithm SHA256).Hash

Write-Host "SAYDI_SAYDIVOICE_MP3=$($info.FullName)"
Write-Host "SAYDI_SAYDIVOICE_BYTES=$($info.Length)"
Write-Host "SAYDI_SAYDIVOICE_SHA256=$hash"
