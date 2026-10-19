$ErrorActionPreference = "Stop"
$Script = "C:\SAYDI\narration_director_v1\chapter2_v5_qc_guarded.py"
$Python = "C:\SAYDI\VieNeu-TTS\.venv\Scripts\python.exe"
$Work = "D:\SAYDI\OWNER_APPROVED_NATURAL_V5\Chuong_02"
$Log = Join-Path $Work "scheduled_runs.log"
if (-not (Test-Path -LiteralPath $Script) -or -not (Test-Path -LiteralPath $Python)) {
  throw "CH02 V5 runner or Python is missing"
}
New-Item -ItemType Directory -Force -Path $Work | Out-Null
Add-Content -LiteralPath $Log -Encoding UTF8 -Value ("["+ (Get-Date -Format 'yyyy-MM-dd HH:mm:ss') +"] START_SAFE_RESOURCE_GATE")
# The Python process owns the named mutex and manages separate render/QC stages.
# It exits quickly without loading a model if free RAM is below its safety gate.
& $Python $Script *>> $Log
$code = $LASTEXITCODE
Add-Content -LiteralPath $Log -Encoding UTF8 -Value ("["+ (Get-Date -Format 'yyyy-MM-dd HH:mm:ss') +"] EXIT="+$code)
exit $code
