<#
.SYNOPSIS
  Start ComfyUI in the background, invisibly. No visible PowerShell window.

.DESCRIPTION
  Replaces the manual `start_comfyui.bat` flow for the Claude integration.
  Designed to be called by Claude (via the PowerShell tool) when a skill
  like /qContent needs ComfyUI but it's not running. The user never sees
  a terminal — the launched python.exe runs with -WindowStyle Hidden and
  its stdout/stderr are redirected to log files.

  Idempotent: if port 8188 is already listening, returns immediately
  without starting a second instance.

.OUTPUTS
  Writes the launched PID to D:\Projects\super_code\ai_video\.comfyui.pid
  Writes stdout to D:\Projects\super_code\ai_video\.comfyui.log
  Writes stderr to D:\Projects\super_code\ai_video\.comfyui.err

.NOTES
  Matches the flags from ai_video\start_comfyui.bat (Tier C profile).
  Mirror any flag changes in BOTH places — or better, delete the .bat
  once the BG launcher is the canonical path.
#>

$ErrorActionPreference = "Stop"

$root      = "D:\Projects\super_code\ai_video"
$comfyDir  = Join-Path $root "comfyui"
$python    = Join-Path $comfyDir ".venv\Scripts\python.exe"
$ffmpegDir = Join-Path $root "ffmpeg"
$pidFile   = Join-Path $root ".comfyui.pid"
$logFile   = Join-Path $root ".comfyui.log"
$errFile   = Join-Path $root ".comfyui.err"

# --- already-running short-circuit ----------------------------------------
$existing = Get-NetTCPConnection -LocalPort 8188 -State Listen -ErrorAction SilentlyContinue
if ($existing) {
    $existingPid = $existing[0].OwningProcess
    Write-Output "ComfyUI already running on :8188 (PID $existingPid). No action."
    # Keep pid file in sync if it's stale.
    Set-Content -Path $pidFile -Value $existingPid -Encoding ASCII
    exit 0
}

# --- pre-flight checks ----------------------------------------------------
if (-not (Test-Path $python)) {
    Write-Error "Venv python missing: $python. Run scripts\setup_ai_video.ps1 first."
    exit 2
}
if (-not (Test-Path (Join-Path $comfyDir "main.py"))) {
    Write-Error "ComfyUI not installed at $comfyDir. Run scripts\setup_ai_video.ps1 first."
    exit 2
}

# --- log rotation (5 MB cap) ----------------------------------------------
foreach ($f in @($logFile, $errFile)) {
    if (Test-Path $f) {
        if ((Get-Item $f).Length -gt 5MB) {
            Move-Item -Force $f "$f.old"
        }
    }
}

# --- prepend bundled ffmpeg dir to PATH so audio nodes find it ------------
# Affects this process's env block, which Start-Process inherits to the child.
$env:PATH = "$ffmpegDir;$env:PATH"

# --- launch --------------------------------------------------------------
# -u: unbuffered stdout/stderr so logs appear without delay.
# -WindowStyle Hidden: no console window flashes for the user.
# Redirect handles inherited by the child python.exe via Start-Process.
$pyArgs = @(
    "-u",
    "main.py",
    "--lowvram",
    "--reserve-vram", "1",
    "--preview-method", "taesd",
    "--fp8_e4m3fn-text-enc"
)

$proc = Start-Process -FilePath $python `
    -ArgumentList $pyArgs `
    -WorkingDirectory $comfyDir `
    -WindowStyle Hidden `
    -RedirectStandardOutput $logFile `
    -RedirectStandardError  $errFile `
    -PassThru

Set-Content -Path $pidFile -Value $proc.Id -Encoding ASCII

Write-Output "Started ComfyUI PID $($proc.Id)"
Write-Output "  log:    $logFile"
Write-Output "  errlog: $errFile"
Write-Output "  pid:    $pidFile"
Write-Output ""
Write-Output "Boot takes ~20-30s. Caller should poll http://127.0.0.1:8188/"
Write-Output "every 2s up to 60s before declaring failure."
