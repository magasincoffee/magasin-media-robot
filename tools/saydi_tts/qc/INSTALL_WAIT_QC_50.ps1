$ErrorActionPreference = "Stop"

if ($env:COMPUTERNAME -ne "DESKTOP-H4A16IL") {
    throw "Script này dành cho DESKTOP-H4A16IL. Máy hiện tại: $env:COMPUTERNAME"
}

$identity = [Security.Principal.WindowsIdentity]::GetCurrent()
$principalNow = New-Object Security.Principal.WindowsPrincipal($identity)
if (-not $principalNow.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) {
    throw "Hãy chạy PowerShell bằng Run as Administrator."
}

$QcRoot = "C:\SAYDI\qc"
New-Item -ItemType Directory -Force -Path $QcRoot | Out-Null

$base = "https://raw.githubusercontent.com/magasincoffee/magasin-media-robot/main/tools/saydi_tts/qc"
Invoke-WebRequest -UseBasicParsing -Uri "$base/run_qc.py" -OutFile "$QcRoot\run_qc.py"

$CoreBase = "https://raw.githubusercontent.com/magasincoffee/magasin-media-robot/main/02_SAYDI_CORE/src/saydi_audiobook"
$PkgRoot = Join-Path $QcRoot "saydi_audiobook"
$PkgData = Join-Path $PkgRoot "data"
New-Item -ItemType Directory -Force -Path $PkgRoot,$PkgData | Out-Null
Invoke-WebRequest -UseBasicParsing -Uri "$CoreBase/__init__.py" -OutFile (Join-Path $PkgRoot "__init__.py")
Invoke-WebRequest -UseBasicParsing -Uri "$CoreBase/pronunciation.py" -OutFile (Join-Path $PkgRoot "pronunciation.py")
Invoke-WebRequest -UseBasicParsing -Uri "$CoreBase/repair.py" -OutFile (Join-Path $PkgRoot "repair.py")
Invoke-WebRequest -UseBasicParsing -Uri "$CoreBase/prosody.py" -OutFile (Join-Path $PkgRoot "prosody.py")
Invoke-WebRequest -UseBasicParsing -Uri "$CoreBase/data/vi_pronunciation_lexicon_v1.json" -OutFile (Join-Path $PkgData "vi_pronunciation_lexicon_v1.json")
Invoke-WebRequest -UseBasicParsing -Uri "$base/qc_after_50.ps1" -OutFile "$QcRoot\qc_after_50.ps1"

$taskName = "SAYDI QC 50 Percent Waiter"
Unregister-ScheduledTask -TaskName $taskName -Confirm:$false -ErrorAction SilentlyContinue

$action = New-ScheduledTaskAction -Execute "powershell.exe" -Argument '-NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -File "C:\SAYDI\qc\qc_after_50.ps1"'
$triggerStartup = New-ScheduledTaskTrigger -AtStartup
$triggerRepeat = New-ScheduledTaskTrigger -Once -At (Get-Date).AddMinutes(1) -RepetitionInterval (New-TimeSpan -Minutes 5) -RepetitionDuration (New-TimeSpan -Days 1)
$principal = New-ScheduledTaskPrincipal -UserId "SYSTEM" -LogonType ServiceAccount -RunLevel Highest
$settings = New-ScheduledTaskSettingsSet -StartWhenAvailable -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -ExecutionTimeLimit ([TimeSpan]::Zero) -MultipleInstances IgnoreNew

Register-ScheduledTask -TaskName $taskName -Action $action -Trigger @($triggerStartup,$triggerRepeat) -Principal $principal -Settings $settings -Description "Wait for chapters 1-5, then run local acoustic+ASR QC and bounded technical repair." -Force | Out-Null
Start-ScheduledTask -TaskName $taskName

Write-Host "SAYDI QC waiter đã được cài." -ForegroundColor Green
Write-Host "Không ảnh hưởng TTS đang render." -ForegroundColor Green
Write-Host "Khi Chương 1-5 completed, task tự chạy Acoustic QC + ASR + report + repair kỹ thuật." -ForegroundColor Cyan
Write-Host "Log: C:\SAYDI\qc\qc_waiter.log"
Write-Host "Report: C:\SAYDI\qc\reports\1c0ea552-a391-4f53-9e45-874be5a7ed66\QC_REPORT.md"
