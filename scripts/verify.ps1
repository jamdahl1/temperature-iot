$ErrorActionPreference = "Stop"
Set-Location (Join-Path $PSScriptRoot "..")
python -m temperature_demo.cli verify @args
exit $LASTEXITCODE
