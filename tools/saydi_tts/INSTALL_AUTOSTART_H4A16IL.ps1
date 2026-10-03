$ErrorActionPreference = "Stop"

$ExpectedComputer = "DESKTOP-H4A16IL"
$WorkerDir = "C:\SAYDI\worker"
$HostPs1 = Join-Path $WorkerDir "worker-host.ps1"
$LogDir = "C:\SAYDI\logs"
$LogFile = Join-Path $LogDir "worker.log"
$TaskName = "SAYDI TTS Worker At Startup"

if ($env:COMPUTERNAME.ToUpper() -ne $ExpectedComputer.ToUpper()) {
    throw "Script này dành cho $ExpectedComputer, máy hiện tại là $env:COMPUTERNAME"
}
if (-not (Test-Path $HostPs1)) { throw "Không tìm thấy $HostPs1" }

$uv = (Get-Command uv -ErrorAction Stop).Source
$userProfile = $env:USERPROFILE
$homeDir = $HOME
$hfHome = if ($env:HF_HOME) { $env:HF_HOME } else { Join-Path $userProfile ".cache\huggingface" }
$tempDir = "C:\SAYDI\temp"
New-Item -ItemType Directory -Force -Path $LogDir,$tempDir | Out-Null

$hostScript = @"
$env:PYTHONUTF8 = "1"
$env:PYTHONIOENCODING = "utf-8"
$env:USERPROFILE = "$userProfile"
$env:HOME = "$homeDir"
$env:HF_HOME = "$hfHome"
$env:TEMP = "$tempDir"
$env:TMP = "$tempDir"
[Console]::OutputEncoding = [System.Text.UTF8Encoding]::new($false)

New-Item -ItemType Directory -Force -Path "$LogDir" | Out-Null
Set-Location "C:\SAYDI\VieNeu-TTS"
& "$uv" run python "C:\SAYDI\worker\saydi_worker.py" *>> "$LogFile"
"@
Set-Content -Path $HostPs1 -Value $hostScript -Encoding UTF8

Unregister-ScheduledTask -TaskName "SAYDI TTS Worker" -Confirm:$false -ErrorAction SilentlyContinue

$action = New-ScheduledTaskAction -Execute "powershell.exe" -Argument "-NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -File `"$HostPs1`""
$trigger = New-ScheduledTaskTrigger -AtStartup
$principal = New-ScheduledTaskPrincipal -UserId "SYSTEM" -LogonType ServiceAccount -RunLevel Highest
$settings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -StartWhenAvailable -RestartCount 10 -RestartInterval (New-TimeSpan -Minutes 1) -ExecutionTimeLimit ([TimeSpan]::Zero)

Register-ScheduledTask -TaskName $TaskName -Action $action -Trigger $trigger -Principal $principal -Settings $settings -Description "SAYDI VieNeu TTS worker; starts at Windows boot and resumes queued/rendering jobs." -Force | Out-Null

Get-CimInstance Win32_Process -ErrorAction SilentlyContinue |
    Where-Object { $_.CommandLine -and $_.CommandLine -like "*C:\SAYDI\worker\saydi_worker.py*" } |
    ForEach-Object { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }

Add-Content $LogFile ("`r`n===== AUTOSTART INSTALLED " + (Get-Date -Format s) + " =====")
Start-ScheduledTask -TaskName $TaskName
Start-Sleep -Seconds 5

$task = Get-ScheduledTask -TaskName $TaskName
$info = Get-ScheduledTaskInfo -TaskName $TaskName
Write-Host "SAYDI boot recovery: ENABLED" -ForegroundColor Green
Write-Host "Task: $TaskName"
Write-Host "State: $($task.State)"
Write-Host "LastTaskResult: $($info.LastTaskResult)"
Write-Host "Worker log: $LogFile"
Get-Content $LogFile -Tail 40