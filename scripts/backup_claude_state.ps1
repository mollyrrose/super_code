<#
.SYNOPSIS
  Snapshot the LIVE, personal ~/.claude state (memory, hermes-auto skills,
  scripts, runtime state files, fable-legacy, tokenjuice rules, memory-graph,
  okf, coord board, hermes data, settings) into
  exclude/windows_reinstall_backup/dotclaude/, for disaster recovery after a
  Windows reinstall or on a new machine.

.DESCRIPTION
  Complements sync_claude_config.ps1, which only mirrors settings.json +
  CLAUDE.md into the git-tracked home_dotclaude/. This script covers
  everything gitignored that isn't reproducible from the repo: personal
  memory, auto-learned skills, decision logs, curator/qrev state, etc.

  settings.json / settings.local.json are TOKENIZED on the way out, same
  scheme as sync_claude_config.ps1:
    - live profile username  -> [USER]
    - python.exe interpreter -> [PY]
    - this repo's root path  -> [REPO]
  so the SAME snapshot restores cleanly on any machine / any Windows username
  with restore_claude_state.ps1 -- no manual find/replace ever again.

  Unlike sync_claude_config.ps1, secrets are NOT redacted here: this folder
  is private (gitignored, exclude/) and the whole point of this backup is a
  single-shot restore without re-entering API keys.

.NOTES
  Destination is entirely under exclude/, which is gitignored -- nothing this
  script writes ever reaches git. Re-run any time to refresh the snapshot.
  Kill switch: don't run it.
#>
[CmdletBinding()]
param(
  [string]$ClaudeHome = (Join-Path $env:USERPROFILE '.claude')
)
$ErrorActionPreference = 'Stop'

function Write-Utf8NoBom([string]$Path, [string]$Text) {
  [System.IO.File]::WriteAllText($Path, $Text, (New-Object System.Text.UTF8Encoding $false))
}

$repoRoot = Split-Path $PSScriptRoot -Parent
$dst = Join-Path $repoRoot 'exclude\windows_reinstall_backup\dotclaude'
New-Item -ItemType Directory -Force -Path $dst | Out-Null

$uname = Split-Path $env:USERPROFILE -Leaf

function Copy-Tokenized([string]$srcFile, [string]$dstFile) {
  if (-not (Test-Path $srcFile)) { return }
  $raw = Get-Content -LiteralPath $srcFile -Raw
  if ($uname) { $raw = $raw -replace [regex]::Escape($uname), '[USER]' }
  $raw = $raw -replace '(?i)[A-Za-z]:\\\\[^"]*?python\.exe', '[PY]'
  $repoEscBack = [regex]::Escape($repoRoot.Replace('\', '\\'))
  $repoEscFwd  = [regex]::Escape($repoRoot.Replace('\', '/'))
  $raw = $raw -replace "(?i)$repoEscBack", '[REPO]'
  $raw = $raw -replace "(?i)$repoEscFwd",  '[REPO]'
  Write-Utf8NoBom $dstFile $raw
}

# --- config files (tokenized: [USER] / [PY] / [REPO], secrets kept as-is) ---
Copy-Tokenized (Join-Path $ClaudeHome 'settings.json')       (Join-Path $dst 'settings.json')
Copy-Tokenized (Join-Path $ClaudeHome 'settings.local.json') (Join-Path $dst 'settings.local.json')
Write-Host "[ok] settings.json + settings.local.json tokenized -> $dst"

foreach ($f in @('CLAUDE.md', 'INSTALL.md')) {
  $s = Join-Path $ClaudeHome $f
  if (Test-Path $s) { Copy-Item -LiteralPath $s -Destination (Join-Path $dst $f) -Force }
}
Write-Host "[ok] CLAUDE.md + INSTALL.md copied"

# --- memory ---
$memSrc = Join-Path $ClaudeHome 'projects\D--Projects-super-code\memory'
if (Test-Path $memSrc) {
  $memDst = Join-Path $dst 'memory'
  New-Item -ItemType Directory -Force -Path $memDst | Out-Null
  Copy-Item "$memSrc\*" $memDst -Recurse -Force
  Write-Host "[ok] memory copied"
}

# --- hermes-auto skills only (the base ~165+ skill bundle is repo-tracked, no need to back it up) ---
$skillsSrc = Join-Path $ClaudeHome 'skills'
if (Test-Path $skillsSrc) {
  $autoDst = Join-Path $dst 'skills-hermes-auto'
  New-Item -ItemType Directory -Force -Path $autoDst | Out-Null
  Get-ChildItem $skillsSrc -Directory -Filter 'hermes-auto-*' | ForEach-Object {
    Copy-Item $_.FullName (Join-Path $autoDst $_.Name) -Recurse -Force
  }
  Write-Host "[ok] hermes-auto skills copied"
}

# --- scripts (also covers local-only files not tracked in the repo, e.g. rev_learn_sessionend.py) ---
$scriptsSrc = Join-Path $ClaudeHome 'scripts'
if (Test-Path $scriptsSrc) {
  $scriptsDst = Join-Path $dst 'scripts'
  New-Item -ItemType Directory -Force -Path $scriptsDst | Out-Null
  Copy-Item "$scriptsSrc\*" $scriptsDst -Recurse -Force
  Write-Host "[ok] scripts copied"
}

# --- plain directory copies ---
foreach ($dir in @('fable-legacy', 'tokenjuice', 'memory-graph', 'okf', '.coord', '.hermes_data')) {
  $s = Join-Path $ClaudeHome $dir
  if (Test-Path $s) {
    $d = Join-Path $dst $dir
    New-Item -ItemType Directory -Force -Path $d | Out-Null
    Copy-Item "$s\*" $d -Recurse -Force
    Write-Host "[ok] $dir copied"
  }
}

# --- state files ---
$stateFiles = @(
  '.banner_hook_state.json', '.context_qupd_flush_state.json', '.decision_log.jsonl',
  '.hermes_curator_state.json', '.hermes_qplan_curator_queue.json', '.hermes_skill_state.json',
  '.openclaw_installed.json', '.qclose_index.jsonl', '.qrev_auto_state.json',
  '.rev_learn_config.json', '.rev_learn_state.json', '.skillspector_log.jsonl',
  '.smart_router_eval.jsonl', '.smart_router_eval_backfill.jsonl'
)
$copied = 0
foreach ($f in $stateFiles) {
  $s = Join-Path $ClaudeHome $f
  if (Test-Path $s) { Copy-Item -LiteralPath $s -Destination (Join-Path $dst $f) -Force; $copied++ }
}
Write-Host "[ok] $copied/$($stateFiles.Count) state files copied"

Write-Host ""
Write-Host "Backup complete -> $dst"
Write-Host "Restore on any machine with: powershell -File $repoRoot\scripts\restore_claude_state.ps1"
