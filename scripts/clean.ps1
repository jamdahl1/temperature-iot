$ErrorActionPreference = "Stop"
Set-Location (Join-Path $PSScriptRoot "..")
python -m temperature_demo.cli clean @args
exit $LASTEXITCODE
