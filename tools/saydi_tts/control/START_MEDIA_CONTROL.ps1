param([switch]$StartOnly)
$ErrorActionPreference = "Stop"
$HostIP = "127.0.0.1"
$Port = 8776
$URL = "http://127.0.0.1:8776/"
$Script = "C:\SAYDI\control\media_control.py"
$PythonW = "C:\MAGASIN_MCP\.venv\Scripts\pythonw.exe"
$LogFile = "C:\SAYDI\control\launcher.log"
function Write-LocalLog([string]$Message) {
  Add-Content -LiteralPath $LogFile -Encoding UTF8 -Value ("["+(Get-Date -Format "yyyy-MM-dd HH:mm:ss")+"] "+$Message)
}
function Test-Health {
  try {
    $response = Invoke-WebRequest -UseBasicParsing -Uri ($URL+"healthz") -TimeoutSec 2
    return [bool]($response.StatusCode -eq 200 -and $response.Content -eq "ok")
  } catch {
    return $false
  }
}
if (-not (Test-Path -LiteralPath $PythonW) -or -not (Test-Path -LiteralPath $Script)) {
  Write-LocalLog "MISSING_RUNTIME_FILES"
  throw "Cannot start Media Control: files missing."
}
if (-not (Test-Health)) {
  $listener = Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue
  if ($listener) {
    Write-LocalLog ("PORT_BUSY_BY="+$listener.OwningProcess)
    throw "Port 8776 belongs to an unresponsive service; refusing to kill other processes."
  }
  Start-Process -FilePath $PythonW -ArgumentList ('"'+$Script+'"') -WindowStyle Hidden
  $ready = $false
  for ($attempt=0; $attempt -lt 15; $attempt++) {
    Start-Sleep -Milliseconds 350
    if (Test-Health) {$ready=$true;break}
  }
  if (-not $ready) {
    Write-LocalLog "START_TIMEOUT"
    throw "Media Control did not respond after startup."
  }
  Write-LocalLog "START_SUCCESS"
} else {
  Write-LocalLog "ALREADY_RUNNING"
}
if (-not $StartOnly) {
  $chrome = @(
    "C:\Program Files\Google\Chrome\Application\chrome.exe",
    "C:\Program Files (x86)\Google\Chrome\Application\chrome.exe"
  ) | Where-Object {Test-Path -LiteralPath $_} | Select-Object -First 1
  if ($chrome) {
    Start-Process -FilePath $chrome -ArgumentList ("--app="+$URL)
  } else {
    Start-Process $URL
  }
  Write-LocalLog "OPENED_BROWSER"
}
