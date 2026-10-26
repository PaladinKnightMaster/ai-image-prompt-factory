param(
  [Parameter(Mandatory = $true)]
  [string]$Label,
  [Parameter(Mandatory = $true)]
  [string]$WorkRoot
)
$ErrorActionPreference = 'Stop'
$Repo = 'D:\1_PROJECT\AI_Kits\AI Image Prompt Factory\IDEA_POOL\ai-image-prompt-factory'
$Py = Join-Path $Repo '.venv\Scripts\python.exe'
$env:PYTHONPATH = (Join-Path $Repo 'src')
& $Py -c @"
from pathlib import Path
from aipf.exp019_v1_2_g3_hardening import load_pilot_run, save_pilot_run, utc_now
r = Path(r'''$WorkRoot''')
m = load_pilot_run(r)
m['host_ui_label_observed'] = '''$Label'''
m['host_ui_label_recorded_at_utc'] = utc_now()
save_pilot_run(r, m)
print('RECORDED host_ui_label_observed=' + m['host_ui_label_observed'] + ' (utf-8 no BOM)')
"@
if ($LASTEXITCODE -ne 0) { throw 'record_host_label failed' }
