param(
  [Parameter(Mandatory = $true)]
  [string]$Label,
  [Parameter(Mandatory = $true)]
  [string]$WorkRoot
)
$ErrorActionPreference = 'Stop'
$Repo = (Resolve-Path (Join-Path $PSScriptRoot '..\..')).Path
$Py = Join-Path $Repo '.venv\Scripts\python.exe'
if (-not (Test-Path $Py)) { $Py = 'python' }
$env:PYTHONPATH = (Join-Path $Repo 'src')
& $Py -m aipf.exp019_v1_2_g3_hardening --root $WorkRoot --action record-host-label --label $Label
if ($LASTEXITCODE -ne 0) { throw 'record_host_label failed' }
