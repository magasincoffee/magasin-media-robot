param(
  [string]$RuntimeDir = "C:\SAYDI\control",
  [switch]$Open
)
$ErrorActionPreference = "Stop"
$SourceDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$PythonDir = "C:\MAGASIN_MCP\.venv\Scripts"
$Python = Join-Path $PythonDir "python.exe"
if (-not (Test-Path -LiteralPath $Python)) { throw "Local Python venv is missing: $Python" }
& $Python -c "import psutil;print('psutil='+psutil.__version__)"
if ($LASTEXITCODE -ne 0) { throw "Local psutil is required; do not install a heavy TTS environment here" }
New-Item -ItemType Directory -Force -Path $RuntimeDir | Out-Null
foreach ($filename in @("media_control.py","index.html","START_MEDIA_CONTROL.ps1","test_media_control.py","control_commands.py","RUN_CONTROL_JOBS.ps1","test_control_commands.py","activity_monitor.py","test_activity_monitor.py")) {
  $src = Join-Path $SourceDir $filename
  $dst = Join-Path $RuntimeDir $filename
  if (-not (Test-Path -LiteralPath $src)) { throw "Missing source file: $src" }
  if ($src -ne $dst) { Copy-Item -LiteralPath $src -Destination $dst -Force }
}
# Copy the chapter workflow scripts only from the trusted local repository.
$narrationSource = Join-Path (Split-Path -Parent $SourceDir) "narration"
$narrationDest = "C:\SAYDI\narration_director_v1"
foreach ($filename in @("chapter_v5_job.py","saydi_review_qc.py","saydi_quality_improve.py")) {
  $local = Join-Path $narrationDest $filename
  $repoCopy = Join-Path $narrationSource $filename
  if (Test-Path -LiteralPath $repoCopy) {
    New-Item -ItemType Directory -Force -Path $narrationDest | Out-Null
    Copy-Item -LiteralPath $repoCopy -Destination $local -Force
  } elseif (-not (Test-Path -LiteralPath $local)) {
    throw "Missing chapter workflow: $filename"
  }
}
$launcher = Join-Path $RuntimeDir "START_MEDIA_CONTROL.ps1"
$shortcut = Join-Path ([Environment]::GetFolderPath("Desktop")) "SAYDI MEDIA CONTROL.lnk"
$lnk = (New-Object -ComObject WScript.Shell).CreateShortcut($shortcut)
$lnk.TargetPath = "$env:SystemRoot\System32\WindowsPowerShell\v1.0\powershell.exe"
$lnk.Arguments = ('-NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -File "'+$launcher+'"')
$lnk.WorkingDirectory = $RuntimeDir
$lnk.Description = "SAYDI Media Control - trang thai, QC, CPU/RAM, nghe audio"
$lnk.Save()
$startup='"'+$env:SystemRoot+'\System32\WindowsPowerShell\v1.0\powershell.exe" -NoProfile -WindowStyle Hidden -ExecutionPolicy Bypass -File "'+$launcher+'" -StartOnly'
New-ItemProperty -Path "HKCU:\Software\Microsoft\Windows\CurrentVersion\Run" -Name "SAYDI_Media_Control" -PropertyType String -Value $startup -Force | Out-Null
& $Python -m py_compile (Join-Path $RuntimeDir "media_control.py")
if ($LASTEXITCODE -ne 0) { throw "Python compile failed" }
& (Join-Path $RuntimeDir "START_MEDIA_CONTROL.ps1") -StartOnly
$health = Invoke-WebRequest -UseBasicParsing -Uri "http://127.0.0.1:8776/healthz" -TimeoutSec 5
if ($health.StatusCode -ne 200) { throw "Local dashboard failed health check" }
$jobGuardian = "SAYDI Control Job Guardian"
if (-not(Get-ScheduledTask -TaskName $jobGuardian -ErrorAction SilentlyContinue)) {
  $taskCommand = 'powershell.exe -NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -File "C:\SAYDI\control\RUN_CONTROL_JOBS.ps1"'
  & schtasks.exe /Create /SC MINUTE /MO 3 /TN $jobGuardian /TR $taskCommand /F | Out-Null
  if ($LASTEXITCODE -ne 0) { throw "Could not install control job guardian" }
}
$guardSettings = New-ScheduledTaskSettingsSet -MultipleInstances IgnoreNew -StartWhenAvailable -ExecutionTimeLimit (New-TimeSpan -Hours 18)
Set-ScheduledTask -TaskName $jobGuardian -Settings $guardSettings | Out-Null
Write-Output "SAYDI_MEDIA_CONTROL_INSTALL=PASS"
Write-Output ("URL=http://127.0.0.1:8776/")
Write-Output ("DESKTOP_SHORTCUT="+$shortcut)
Write-Output "AUTOSTART=HKCU_CURRENT_USER_AT_LOGON"
if ($Open) {
  & (Join-Path $RuntimeDir "START_MEDIA_CONTROL.ps1")
}
