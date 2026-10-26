<#
.SYNOPSIS
  Hardened G3 capture helper (Windows PowerShell 5.1+).

.DESCRIPTION
  Delegates to aipf.exp019_v1_2_g3_hardening. Enforces run_state, budget,
  and fail-closed capture. Does NOT drive ChatGPT Images.

  Spec: EXP019-V12-G3-HARDENING-SPEC-2026-10-26.r0
#>
param(
  [string]$PilotId = '',

  [Parameter(Mandatory = $true)]
  [ValidateSet(
    'preflight', 'authorize', 'owner-stop', 'complete', 'close', 'status',
    'copy', 'verify-clipboard', 'pre-send', 'submit', 'response', 'download', 'attest'
  )]
  [string]$Action,

  [int]$ReturnedCount = 1,
  [string]$ImagePath = '',
  [string]$Signature = '',
  [switch]$ConfirmAllTrue,
  [string]$AtUtc = '',
  [string]$ConversationRef = 'chatgpt.com/images',
  [Parameter(Mandatory = $true)]
  [string]$WorkRoot
)

$ErrorActionPreference = 'Stop'
$Root = $WorkRoot
if (-not (Test-Path $Root)) { throw "WorkRoot not found: $Root" }

$Repo = 'D:\1_PROJECT\AI_Kits\AI Image Prompt Factory\IDEA_POOL\ai-image-prompt-factory'
$Py = Join-Path $Repo '.venv\Scripts\python.exe'
if (-not (Test-Path $Py)) { $Py = 'python' }
$env:PYTHONPATH = (Join-Path $Repo 'src')

$Expected = @{
  PLVA01 = @{ Sha = '7b8d2f5c74058370aa191f22faf4cd813a7de6c081748fc887c0cead7e9d786c'; N = 328 }
  PLVB01 = @{ Sha = '2f25bbe661eff6b3eb1a020462c854d71097f454c65d02f070f5400b2916b28e'; N = 220 }
}

function Assert-Active([string]$Act) {
  & $Py -c @"
from pathlib import Path
from aipf.exp019_v1_2_g3_hardening import load_pilot_run, require_active_for_capture
r = Path(r'''$Root''')
require_active_for_capture(r, load_pilot_run(r), '''$Act''')
"@
  if ($LASTEXITCODE -ne 0) { throw "blocked by run_state for action $Act" }
}

function Get-FrozenBytes([string]$Id) {
  return [System.IO.File]::ReadAllBytes((Join-Path $Root "packets\$Id\frozen-prompt.txt"))
}

function Assert-Digest([byte[]]$Bytes, [string]$Id) {
  $sha = [System.BitConverter]::ToString(
    [System.Security.Cryptography.SHA256]::Create().ComputeHash($Bytes)
  ).Replace('-', '').ToLowerInvariant()
  if ($sha -ne $Expected[$Id].Sha -or $Bytes.Length -ne $Expected[$Id].N) {
    throw "DIGEST_MISMATCH $Id got $sha $($Bytes.Length)"
  }
  return $sha
}

if ($Action -in @('preflight', 'authorize', 'owner-stop', 'complete', 'close')) {
  & $Py -m aipf.exp019_v1_2_g3_hardening --root $Root --action $Action
  if ($LASTEXITCODE -ne 0) { throw "hardening failed: $LASTEXITCODE" }
  return
}

if ($Action -eq 'status') {
  $a = @('-m', 'aipf.exp019_v1_2_g3_hardening', '--root', $Root, '--action', 'status')
  if ($PilotId) { $a += @('--pilot-id', $PilotId) }
  & $Py @a
  if ($LASTEXITCODE -ne 0) { throw "hardening failed: $LASTEXITCODE" }
  return
}

if (-not $PilotId) { throw 'PilotId required' }
if ($PilotId -notin @('PLVA01', 'PLVB01')) { throw "unsupported PilotId $PilotId" }

$bytes = Get-FrozenBytes $PilotId
$sha = Assert-Digest $bytes $PilotId
$text = [System.Text.Encoding]::UTF8.GetString($bytes)

switch ($Action) {
  'copy' {
    Assert-Active 'copy'
    Set-Clipboard -Value $text
    Write-Host "OK copied $PilotId $sha $($bytes.Length) via Set-Clipboard"
    Write-Host "TRUST: local tooling does not control ChatGPT Images UI"
    Write-Host "NEXT: paste (Ctrl+V), verify-clipboard, pre-send BEFORE Generate"
  }
  'verify-clipboard' {
    Assert-Active 'verify-clipboard'
    $clip = Get-Clipboard -Raw
    $clipBytes = [System.Text.Encoding]::UTF8.GetBytes($clip)
    $csha = Assert-Digest $clipBytes $PilotId
    Write-Host "OK clipboard_matches_frozen $csha"
  }
  default {
    $pyArgs = @(
      '-m', 'aipf.exp019_v1_2_g3_hardening',
      '--root', $Root,
      '--pilot-id', $PilotId,
      '--action', $Action,
      '--conversation-ref', $ConversationRef
    )
    if ($AtUtc) { $pyArgs += @('--at-utc', $AtUtc) }
    if ($Action -eq 'response') { $pyArgs += @('--returned-count', "$ReturnedCount") }
    if ($Action -eq 'download') {
      if (-not $ImagePath) { throw 'ImagePath required for download' }
      $pyArgs += @('--image-path', $ImagePath)
    }
    if ($Action -eq 'attest') {
      if ($Signature) {
        $pyArgs += @('--signature', $Signature)
        if ($ConfirmAllTrue) { $pyArgs += '--confirm-all-true' }
        else { Write-Host 'NOTE: without -ConfirmAllTrue, attest writes UNSIGNED only' }
      }
    }
    & $Py @pyArgs
    if ($LASTEXITCODE -ne 0) { throw "python capture failed: $LASTEXITCODE" }
  }
}
