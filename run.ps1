# Windows PowerShell 启动脚本（真正的逻辑在 start.py，三平台共用）
$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

$py = Get-Command py -ErrorAction SilentlyContinue
if ($py) {
    & py -3 start.py @args
} elseif (Get-Command python -ErrorAction SilentlyContinue) {
    & python start.py @args
} else {
    Write-Host "[x] 没有找到 Python 3.9+，下载：https://www.python.org/downloads/" -ForegroundColor Red
    exit 1
}
exit $LASTEXITCODE
