<#
.SYNOPSIS
  Guided eight-stage G3 operator wrapper (human host submission only).

.DESCRIPTION
  Displays run state, pilot id, remaining budget, required action, and whether
  proceeding is permitted. Does not contact or drive ChatGPT Images.
#>
param(
  [Parameter(Mandatory = $true)]
  [ValidateSet(
    'PREPARE', 'VERIFY_PROMPT', 'RECORD_PRE_SEND', 'SUBMIT_AND_RECORD',
    'RECORD_RESPONSE', 'VERIFY_DOWNLOAD', 'REVIEW_AND_SIGN', 'COMPLETE'
  )]
  [string]$Stage,

  [ValidateSet('PLVA01', 'PLVB01')]
  [string]$PilotId = 'PLVA01',

  [Parameter(Mandatory = $true)]
  [string]$WorkRoot,

  [string]$ImagePath = '',
  [string]$Signature = '',
  [switch]$ConfirmAllTrue,
  [int]$ReturnedCount = 1,
  [string]$HostLabel = 'Images'
)

$ErrorActionPreference = 'Stop'
$Here = $PSScriptRoot
$Capture = Join-Path $Here 'g3_followup_capture.ps1'

function Show-Banner([string]$Required, [string]$Permitted) {
  $Repo = (Resolve-Path (Join-Path $Here '..\..')).Path
  $Py = Join-Path $Repo '.venv\Scripts\python.exe'
  if (-not (Test-Path $Py)) { $Py = 'python' }
  $env:PYTHONPATH = (Join-Path $Repo 'src')
  Write-Host '======== G3 OPERATOR (HARDENED) ========'
  Write-Host "Stage:      $Stage"
  Write-Host "PilotId:    $PilotId"
  Write-Host "WorkRoot:   $WorkRoot"
  Write-Host "TRUST: Local tooling enforces state/budget/evidence only."
  Write-Host "TRUST: It does NOT control ChatGPT Images UI clicks."
  $status = & $Py -m aipf.exp019_v1_2_g3_hardening --root $WorkRoot --action status --pilot-id $PilotId 2>&1 | Out-String
  Write-Host $status
  Write-Host "Required:   $Required"
  Write-Host "Proceed:    $Permitted"
  Write-Host '========================================'
}

switch ($Stage) {
  'PREPARE' {
    Show-Banner 'Confirm Images UI; run preflight then authorize' 'yes if CREATED/PREFLIGHT'
    & $Capture -WorkRoot $WorkRoot -Action preflight
    & $Capture -WorkRoot $WorkRoot -Action record-host-label -Label $HostLabel
    & $Capture -WorkRoot $WorkRoot -Action authorize
    Write-Host 'NEXT: VERIFY_PROMPT'
  }
  'VERIFY_PROMPT' {
    Show-Banner 'Copy frozen prompt; paste manually; verify clipboard' 'yes if ACTIVE'
    & $Capture -WorkRoot $WorkRoot -PilotId $PilotId -Action copy
    Write-Host 'After Ctrl+V into ChatGPT Images, run VERIFY_PROMPT again is not needed;'
    Write-Host 'run: -Stage VERIFY_PROMPT already copied — now verify-clipboard via:'
    & $Capture -WorkRoot $WorkRoot -PilotId $PilotId -Action verify-clipboard
    Write-Host 'NEXT: RECORD_PRE_SEND (before Generate)'
  }
  'RECORD_PRE_SEND' {
    Show-Banner 'Record pre-send BEFORE clicking Generate' 'yes if ACTIVE'
    & $Capture -WorkRoot $WorkRoot -PilotId $PilotId -Action pre-send
    Write-Host 'NEXT: human clicks Generate once, then SUBMIT_AND_RECORD immediately'
  }
  'SUBMIT_AND_RECORD' {
    Show-Banner 'Immediately after Generate click, record submit' 'yes if ACTIVE'
    & $Capture -WorkRoot $WorkRoot -PilotId $PilotId -Action submit
    Write-Host 'NEXT: RECORD_RESPONSE when image appears'
  }
  'RECORD_RESPONSE' {
    Show-Banner 'Record response when image visible' 'yes if ACTIVE'
    & $Capture -WorkRoot $WorkRoot -PilotId $PilotId -Action response -ReturnedCount $ReturnedCount
    Write-Host 'NEXT: VERIFY_DOWNLOAD with quoted ImagePath'
  }
  'VERIFY_DOWNLOAD' {
    Show-Banner 'Hash/decode downloaded image' 'yes if ACTIVE'
    if (-not $ImagePath) { throw 'ImagePath required (quote paths with spaces)' }
    & $Capture -WorkRoot $WorkRoot -PilotId $PilotId -Action download -ImagePath $ImagePath
    Write-Host 'NEXT: REVIEW_AND_SIGN (unsigned first, then confirm)'
  }
  'REVIEW_AND_SIGN' {
    Show-Banner 'Review statements; sign only with ConfirmAllTrue' 'yes if ACTIVE'
    if (-not $Signature -or -not $ConfirmAllTrue) {
      & $Capture -WorkRoot $WorkRoot -PilotId $PilotId -Action attest
      Write-Host 'To sign after CONFIRM ALL TRUE: -Signature <name> -ConfirmAllTrue'
    } else {
      & $Capture -WorkRoot $WorkRoot -PilotId $PilotId -Action attest -Signature $Signature -ConfirmAllTrue
    }
  }
  'COMPLETE' {
    Show-Banner 'Mark run COMPLETED (disposition still owner-owned)' 'yes'
    & $Capture -WorkRoot $WorkRoot -Action complete
  }
}
