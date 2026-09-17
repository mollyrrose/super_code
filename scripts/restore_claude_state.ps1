<#
.SYNOPSIS
  Restore the full personal ~/.claude state (settings, memory, hermes-auto
  skills, scripts, runtime state, fable-legacy, tokenjuice rules,
  memory-graph, okf, coord board, hermes data) from
  exclude/windows_reinstall_backup/dotclaude/. Reverse of
  backup_claude_state.ps1.

.DESCRIPTION
  De-tokenizes [USER] / [PY] / [REPO] for the CURRENT machine automatically --
  same resolution logic as restore_claude_config.ps1 (env override, then
  PATH, then a warned-about fallback for [PY]; this clone's own location for
  [REPO]; the current Windows profile folder for [USER]). No manual
  find/replace of a username is ever needed again, on any machine.

  This script also installs the base skill bundle from
  hermes-agent/claude_skills_backup/ (repo-tracked) before overlaying the
  backed-up hermes-auto-* skills, so a single run gives a complete
  ~/.claude/skills/.

.NOTES
  Only writes under $ClaudeHome (default ~/.claude). Existing settings.json /
  settings.local.json are backed up first, never silently overwritten.
  Kill switch: don't run it.
#>
[CmdletBinding()]
param(
  [string]$ClaudeHome = (Join-Path $env:USERPROFILE '.claude'),
  [switch]$NoSettings,
  [switch]$NoSkills
)
$ErrorActionPreference = 'Stop'

function Write-Utf8NoBom([string]$Path, [string]$Text) {
  [System.IO.File]::WriteAllText($Path, $Text, (New-Object System.Text.UTF8Encoding $false))
}

$repoRoot = Split-Path $PSScriptRoot -Parent
$src = Join-Path $repoRoot 'exclude\windows_reinstall_backup\dotclaude'
if (-not (Test-Path $src)) {
  throw "No backup found at $src -- run backup_claude_state.ps1 on a working machine first."
}

New-Item -ItemType Directory -Force -Path $ClaudeHome | Out-Null
$uname = Split-Path $env:USERPROFILE -Leaf

$py = $env:CLAUDE_PYTHON
if (-not $py) { $py = (Get-Command python  -ErrorAction SilentlyContinue).Source }
if (-not $py) { $py = (Get-Command python3 -ErrorAction SilentlyContinue).Source }
if (-not $py) { $py = (Get-Command py      -ErrorAction SilentlyContinue).Source }
if (-not $py) { $py = 'C:\Python314\python.exe'; Write-Warning "no Python on PATH; [PY] defaulted to $py -- install Python or set `$env:CLAUDE_PYTHON and re-run." }

function Restore-Detokenized([string]$srcFile, [string]$dstFile) {
  if (-not (Test-Path $srcFile)) { return }
  $raw = Get-Content -LiteralPath $srcFile -Raw
  $raw = $raw.Replace('[USER]', $uname)
  $raw = $raw.Replace('[REPO]', $repoRoot.Replace('\', '\\'))
  $raw = $raw.Replace('[PY]', $py.Replace('\', '\\'))
  if (Test-Path $dstFile) {
    $bak = "$dstFile.bak.$(Get-Date -Format yyyyMMdd-HHmmss)"
    Copy-Item -LiteralPath $dstFile -Destination $bak -Force
    Write-Host "[ok] backed up existing $(Split-Path $dstFile -Leaf) -> $bak"
  }
  Write-Utf8NoBom $dstFile $raw
}

if (-not $NoSettings) {
  if ($py -match '\[PY\]' -or $true) { Write-Host "[ok] [PY] -> $py" }
  Restore-Detokenized (Join-Path $src 'settings.json')       (Join-Path $ClaudeHome 'settings.json')
  Restore-Detokenized (Join-Path $src 'settings.local.json') (Join-Path $ClaudeHome 'settings.local.json')
  Write-Host "[ok] settings.json + settings.local.json restored for user '$uname'"

  foreach ($f in @('CLAUDE.md', 'INSTALL.md')) {
    $s = Join-Path $src $f
    if (Test-Path $s) { Copy-Item -LiteralPath $s -Destination (Join-Path $ClaudeHome $f) -Force }
  }
  Write-Host "[ok] CLAUDE.md + INSTALL.md restored"
}

# --- memory (project-key folder name comes from this repo's absolute path, not the
#     username, so it needs no tokenization -- always D--Projects-super-code here) ---
$memSrc = Join-Path $src 'memory'
if (Test-Path $memSrc) {
  $memDst = Join-Path $ClaudeHome 'projects\D--Projects-super-code\memory'
  New-Item -ItemType Directory -Force -Path $memDst | Out-Null
  Copy-Item "$memSrc\*" $memDst -Recurse -Force
  Write-Host "[ok] memory restored"
}

# --- skills: base bundle from the repo, then hermes-auto overlay from the backup ---
if (-not $NoSkills) {
  $skillsDst = Join-Path $ClaudeHome 'skills'
  New-Item -ItemType Directory -Force -Path $skillsDst | Out-Null
  $baseSkills = Join-Path $repoRoot 'hermes-agent\claude_skills_backup'
  if (Test-Path $baseSkills) {
    Copy-Item "$baseSkills\*" $skillsDst -Recurse -Force
    Write-Host "[ok] base skill bundle restored"
  }
  $autoSkills = Join-Path $src 'skills-hermes-auto'
  if (Test-Path $autoSkills) {
    Copy-Item "$autoSkills\*" $skillsDst -Recurse -Force
    Write-Host "[ok] hermes-auto skills restored"
  }
}

# --- scripts ---
$scriptsSrc = Join-Path $src 'scripts'
if (Test-Path $scriptsSrc) {
  $scriptsDst = Join-Path $ClaudeHome 'scripts'
  New-Item -ItemType Directory -Force -Path $scriptsDst | Out-Null
  Copy-Item "$scriptsSrc\*" $scriptsDst -Recurse -Force
  Write-Host "[ok] scripts restored"
}

# --- plain directory copies ---
foreach ($dir in @('fable-legacy', 'tokenjuice', 'memory-graph', 'okf', '.coord', '.hermes_data')) {
  $s = Join-Path $src $dir
  if (Test-Path $s) {
    $d = Join-Path $ClaudeHome $dir
    New-Item -ItemType Directory -Force -Path $d | Out-Null
    Copy-Item "$s\*" $d -Recurse -Force
    Write-Host "[ok] $dir restored"
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
  $s = Join-Path $src $f
  if (Test-Path $s) { Copy-Item -LiteralPath $s -Destination (Join-Path $ClaudeHome $f) -Force; $copied++ }
}
Write-Host "[ok] $copied/$($stateFiles.Count) state files restored"

Write-Host ""
Write-Host "Next steps:"
Write-Host "  1. Install Python 3.x + Node.js if not already present (any location, on PATH)."
Write-Host "  2. & '$py' -m pip install graphifyy psutil"
Write-Host "  3. Install plugins from settings.json enabledPlugins (ecc, ruflo-core) via /plugin."
Write-Host "  4. Verify hooks by opening this repo in Claude Code and running a test prompt."
