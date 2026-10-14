$ErrorActionPreference = "Stop"
Set-Location (Join-Path $PSScriptRoot "..")
python -m temperature_demo.cli status @args
exit $LASTEXITCODE
