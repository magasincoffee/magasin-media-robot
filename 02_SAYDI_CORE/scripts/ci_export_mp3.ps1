$ErrorActionPreference = "Stop"

$repoRoot = Resolve-Path (Join-Path $PSScriptRoot "..\..")
Set-Location $repoRoot

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

$env:PYTHONPATH = "$repoRoot\02_SAYDI_CORE\src"

& $python -m compileall -q 02_SAYDI_CORE\src 02_SAYDI_CORE\tests
if ($LASTEXITCODE -ne 0) { throw "compileall failed" }

& $python -m unittest discover -s 02_SAYDI_CORE\tests -v
if ($LASTEXITCODE -ne 0) { throw "unit tests failed" }

$runId = if ($env:GITHUB_RUN_ID) { $env:GITHUB_RUN_ID } else { "local" }
$run = Join-Path $env:RUNNER_TEMP "saydi-run-$runId"
New-Item -ItemType Directory -Force -Path $run | Out-Null

& $python -m saydi_audiobook prepare --input 02_SAYDI_CORE\fixtures\business_sample_vi.txt --run-dir $run --analysis rules
if ($LASTEXITCODE -ne 0) { throw "prepare failed" }

& $python -m saydi_audiobook decide-text --run-dir $run --decision approve
if ($LASTEXITCODE -ne 0) { throw "text approval failed" }

& $python -m saydi_audiobook synthesize-sample --run-dir $run --provider windows-sapi
if ($LASTEXITCODE -ne 0) { throw "SAPI synthesis failed" }

$audioDir = Join-Path $run "audio"
$wav = Get-ChildItem $audioDir -Filter *.wav -File | Select-Object -First 1
if (-not $wav) { throw "No WAV output produced." }

$deps = Join-Path $env:RUNNER_TEMP "saydi-mp3-deps"
New-Item -ItemType Directory -Force -Path $deps | Out-Null
& $python -m pip install --disable-pip-version-check --quiet --target $deps lameenc
if ($LASTEXITCODE -ne 0) { throw "lameenc install failed" }

$env:PYTHONPATH = "$deps;$repoRoot\02_SAYDI_CORE\src"
$mp3 = Join-Path $repoRoot "SAYDI_SAMPLE.mp3"

& $python 02_SAYDI_CORE\scripts\wav_to_mp3.py $wav.FullName $mp3 --bit-rate 128
if ($LASTEXITCODE -ne 0) { throw "MP3 conversion failed" }
if (-not (Test-Path $mp3)) { throw "MP3 output missing: $mp3" }

$info = Get-Item $mp3
$hash = (Get-FileHash $mp3 -Algorithm SHA256).Hash
Write-Host "SAYDI_MP3_FILE=$($info.FullName)"
Write-Host "SAYDI_MP3_BYTES=$($info.Length)"
Write-Host "SAYDI_MP3_SHA256=$hash"
