$ErrorActionPreference="Stop"
$Python="C:\MAGASIN_MCP\.venv\Scripts\python.exe"
$Controller="C:\SAYDI\control\control_commands.py"
$Log="C:\SAYDI\control\job_guardian.log"
if (-not(Test-Path -LiteralPath $Python) -or -not(Test-Path -LiteralPath $Controller)){
  throw "Control job runner missing"
}
Add-Content -LiteralPath $Log -Value ("["+(Get-Date -Format "yyyy-MM-dd HH:mm:ss")+"] TICK_START") -Encoding UTF8
& $Python $Controller --tick *>> $Log
$exit=$LASTEXITCODE
Add-Content -LiteralPath $Log -Value ("["+(Get-Date -Format "yyyy-MM-dd HH:mm:ss")+"] TICK_END="+$exit) -Encoding UTF8
exit $exit
