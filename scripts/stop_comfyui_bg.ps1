<#
.SYNOPSIS
  Stop the background ComfyUI process started by start_comfyui_bg.ps1.

.DESCRIPTION
  Reads the PID from .comfyui.pid. Falls back to port-based discovery
  if the pid file is missing or stale. Idempotent — already-stopped
  is a successful no-op.

.NOTES
  Safe to call from Claude when a /qContent run wants a clean restart
  (e.g. after model swap, or to recover a stuck workflow when the
  /interrupt API doesn't free the GPU).
#>

$ErrorActionPreference = "Continue"

$pidFile = "D:\Projects\super_code\ai_video\.comfyui.pid"

function Stop-IfRunning {
    param([int]$ProcId, [string]$Source)
    $proc = Get-Process -Id $ProcId -ErrorAction SilentlyContinue
    if ($proc) {
        Stop-Process -Id $ProcId -Force
        Start-Sleep -Milliseconds 800
        $still = Get-Process -Id $ProcId -ErrorAction SilentlyContinue
        if ($still) {
            Write-Output "Stopped PID $ProcId ($Source) — kill incomplete after 800ms"
            return $false
        }
        Write-Output "Killed PID $ProcId ($Source)"
        return $true
    }
    Write-Output "PID $ProcId ($Source) was not running"
    return $true
}

$pidFromFile = $null
if (Test-Path $pidFile) {
    try {
        $pidFromFile = [int](Get-Content $pidFile -Raw).Trim()
    } catch {
        Write-Output "PID file unreadable: $pidFile — falling back to port discovery"
    }
}

if ($pidFromFile) {
    [void](Stop-IfRunning -ProcId $pidFromFile -Source "pid file")
    Remove-Item $pidFile -ErrorAction SilentlyContinue
}

# Always also check port 8188 — covers the case where ComfyUI was
# started another way (e.g. start_comfyui.bat in a leftover terminal).
$conn = Get-NetTCPConnection -LocalPort 8188 -State Listen -ErrorAction SilentlyContinue
if ($conn) {
    $portPid = $conn[0].OwningProcess
    if ($portPid -ne $pidFromFile) {
        [void](Stop-IfRunning -ProcId $portPid -Source "port 8188")
    }
} else {
    if (-not $pidFromFile) {
        Write-Output "ComfyUI not running (no pid file, port 8188 free)"
    }
}

# Final GPU check for the user.
try {
    $g = (& nvidia-smi --query-gpu=utilization.gpu,memory.used --format=csv,noheader 2>&1) -join " | "
    Write-Output "GPU after stop: $g"
} catch {
    # nvidia-smi missing is fine — not all dev boxes have CUDA
}
