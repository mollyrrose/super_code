<#
.SYNOPSIS
    Set up the super_code AI video pipeline: ComfyUI + LTX-Video locally, plus
    MCP servers exposing local ComfyUI and OpenAI Sora to Claude Code.

.DESCRIPTION
    Idempotent installer for the AI video stack documented in docs/AI_VIDEO_SETUP.md.

    Auto-detects GPU VRAM and classifies into tier S/A/B/C/D/E. Tier C is fully
    automated end-to-end (RTX 4070 Laptop class, 8-11 GB VRAM); other tiers print
    guidance and stop short of downloads.

    Steps (Tier C):
      1. Hardware check + tier classification
      2. Clone ComfyUI at a pinned commit
      3. Create per-pipeline Python venv
      4. Install PyTorch (CUDA 12.6 wheels)
      5. Install ComfyUI requirements.txt
      6. Download LTX 0.9.8 distilled fp8 + VAE + T5 text encoder (~23.5 GB)
      7. Generate start_comfyui.bat with the right Tier C flags
      8. Install MCP server runtime deps (mcp + openai) into system Python

    Manual follow-ups printed at the end: register MCPs, save workflow JSON,
    optionally set the Sora API key.

.PARAMETER Tier
    Override auto-detected tier. One of S, A, B, C, D, E.

.PARAMETER Redetect
    Print the detected tier and exit without installing anything.

.PARAMETER SystemPython
    Path to a system Python 3.10+ executable used for the MCP servers. The
    ComfyUI venv is created independently. Default: searches PATH.

.PARAMETER Force
    Re-download model files even if they already exist on disk.

.PARAMETER SkipModels
    Skip the model download step. Useful for re-running just the code parts.

.EXAMPLE
    .\scripts\setup_ai_video.ps1

.EXAMPLE
    .\scripts\setup_ai_video.ps1 -Redetect

.EXAMPLE
    .\scripts\setup_ai_video.ps1 -Tier C -SystemPython C:\Python314\python.exe
#>
[CmdletBinding()]
param(
    [ValidateSet('S','A','B','C','D','E')]
    [string]$Tier,
    [switch]$Redetect,
    [string]$SystemPython,
    [switch]$Force,
    [switch]$SkipModels,
    [switch]$WithTalkingHead,
    [switch]$SkipTalkingHead
)

$ErrorActionPreference = 'Stop'

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

$ProjectRoot  = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$AiVideoRoot  = Join-Path $ProjectRoot 'ai_video'
$ComfyUIRoot  = Join-Path $AiVideoRoot 'comfyui'
$VenvDir      = Join-Path $ComfyUIRoot '.venv'
$VenvPython   = Join-Path $VenvDir    'Scripts\python.exe'
$ModelsDir    = Join-Path $ComfyUIRoot 'models'
$WorkflowsDir = Join-Path $AiVideoRoot 'workflows'
$LaunchBat    = Join-Path $AiVideoRoot 'start_comfyui.bat'
$McpDir       = Join-Path $ProjectRoot 'hermes-agent\claude_code_integration\mcp_servers'

# Pinned ComfyUI commit known to work with LTX 0.9.8 (2026-06-12).
# Bump after testing a newer tip; the script will checkout this exact ref.
$ComfyUICommit = '822aca19'

# Lightricks LTX-Video Hugging Face base URL
$HfBase = 'https://huggingface.co/Lightricks/LTX-Video/resolve/main'

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------

function Write-Step  { param($Msg) Write-Host "`n[STEP] $Msg" -ForegroundColor Cyan }
function Write-OK    { param($Msg) Write-Host "  [ok] $Msg"   -ForegroundColor Green }
function Write-Skip  { param($Msg) Write-Host "  [skip] $Msg" -ForegroundColor DarkGray }
function Write-Warn  { param($Msg) Write-Host "  [warn] $Msg" -ForegroundColor Yellow }
function Write-Fail  { param($Msg) Write-Host "  [fail] $Msg" -ForegroundColor Red }

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

function Test-Command {
    param([string]$Name)
    $null -ne (Get-Command $Name -ErrorAction SilentlyContinue)
}

function Get-VramGB {
    # P2.7: distinguish "no NVIDIA GPU" from "nvidia-smi present but
    # returned unparseable output". The earlier `2>$null` + bare `catch {}`
    # made a driver crash look identical to a Tier-E CPU-only box.
    # Capture the full output into a variable so we can introspect it
    # instead of piping into Select-Object (which loses error context).
    # $LASTEXITCODE check is intentionally NOT used here — PowerShell's
    # $LASTEXITCODE state is unreliable across function/pipeline
    # boundaries and would generate confusing "exited with code ''" warnings
    # in the common happy path. Parsing the first line is sufficient.
    if (-not (Test-Command 'nvidia-smi')) { return 0 }
    try {
        $raw = (& nvidia-smi --query-gpu=memory.total --format=csv,noheader,nounits 2>&1) -join "`n"
        $firstLine = ($raw -split "`r?`n")[0].Trim()
        if ($firstLine -match '^\d+$') {
            return [math]::Round([int]$firstLine / 1024, 1)
        }
        Write-Warn "nvidia-smi returned unparseable output: '$raw'. Treating as no GPU."
    } catch {
        Write-Warn "nvidia-smi invocation failed: $_"
    }
    return 0
}

function Get-RamGB {
    [math]::Round((Get-CimInstance Win32_ComputerSystem).TotalPhysicalMemory / 1GB, 1)
}

function Get-FreeDiskGB {
    param([string]$Path)
    $drive = (Get-Item $Path).PSDrive
    [math]::Round($drive.Free / 1GB, 1)
}

function Classify-Tier {
    param([double]$Vram, [double]$Ram)
    if ($Vram -eq 0) { return 'E' }
    if ($Vram -ge 48) { return 'S' }
    if ($Vram -ge 24) { return 'A' }
    if ($Vram -ge 12) { return 'B' }
    if ($Vram -ge 8)  { return 'C' }
    if ($Vram -ge 4)  { return 'D' }
    return 'E'
}

function Resolve-SystemPython {
    if ($SystemPython -and (Test-Path $SystemPython)) { return $SystemPython }
    $candidates = @(
        'C:\Python314\python.exe',
        'C:\Python312\python.exe',
        'C:\Python311\python.exe',
        'C:\Python310\python.exe'
    )
    foreach ($c in $candidates) { if (Test-Path $c) { return $c } }
    $cmd = Get-Command python.exe -ErrorAction SilentlyContinue
    if ($cmd) { return $cmd.Source }
    return $null
}

function Download-File {
    param(
        [string]$Url,
        [string]$Target,
        [string]$Label
    )
    $dir = Split-Path $Target -Parent
    if (-not (Test-Path $dir)) { New-Item -ItemType Directory -Force -Path $dir | Out-Null }
    if ((Test-Path $Target) -and -not $Force) {
        $sizeMB = [math]::Round((Get-Item $Target).Length / 1MB, 1)
        Write-Skip "$Label already present (${sizeMB} MB)"
        return
    }
    Write-Host "  downloading $Label from $Url" -ForegroundColor DarkCyan
    Invoke-WebRequest -Uri $Url -OutFile $Target -UseBasicParsing
    $sizeMB = [math]::Round((Get-Item $Target).Length / 1MB, 1)
    Write-OK "$Label downloaded (${sizeMB} MB)"
}

# ---------------------------------------------------------------------------
# Phase 1 — Hardware detection
# ---------------------------------------------------------------------------

Write-Step 'Hardware detection'

$vramGB    = Get-VramGB
$ramGB     = Get-RamGB
$freeDisk  = Get-FreeDiskGB -Path $ProjectRoot

Write-Host ("  GPU VRAM: {0} GB" -f $vramGB)
Write-Host ("  RAM     : {0} GB" -f $ramGB)
Write-Host ("  Free disk on project drive: {0} GB" -f $freeDisk)

$detected = Classify-Tier -Vram $vramGB -Ram $ramGB
$chosen   = if ($Tier) { $Tier } else { $detected }

Write-Host ("  Tier (auto)   : {0}" -f $detected)
if ($Tier -and ($Tier -ne $detected)) {
    Write-Warn ("Tier overridden by -Tier: {0} (auto was {1})" -f $Tier, $detected)
}
Write-Host ("  Tier (chosen) : {0}" -f $chosen)

if ($Redetect) {
    Write-Host "`n-Redetect: exiting without any changes."
    exit 0
}

# ---------------------------------------------------------------------------
# Tier gate
# ---------------------------------------------------------------------------

if ($chosen -ne 'C') {
    Write-Step ("Tier {0} requested — only Tier C is fully automated in this script." -f $chosen)
    Write-Host @"
  The hardware tier table and per-tier guidance live in docs\AI_VIDEO_SETUP.md.
  For Tier S/A/B: bump VRAM checks, swap the LTX model URL to the larger one,
    drop --lowvram from the launcher.
  For Tier D    : add a custom-node install step for ComfyUI-GGUF (city96).
  For Tier E    : skip ComfyUI entirely, just use sora-cloud.

  Re-run with -Tier C if you want to force the Tier C path on this hardware.
"@
    exit 0
}

if ($freeDisk -lt 35) {
    Write-Fail ("Need >=35 GB free disk; only {0} GB available. Free up space and retry." -f $freeDisk)
    exit 1
}

if ($ramGB -lt 30) {
    Write-Warn ("Tier C wants >=32 GB RAM; only {0} GB present. The --lowvram swap will be slow." -f $ramGB)
}

# ---------------------------------------------------------------------------
# Phase 2 — Prerequisites
# ---------------------------------------------------------------------------

Write-Step 'Prerequisite checks'

if (-not (Test-Command 'git'))           { Write-Fail 'git not on PATH. Install Git for Windows and retry.'; exit 1 }
$sysPython = Resolve-SystemPython
if (-not $sysPython)                     { Write-Fail 'No Python 3.10+ found on PATH. Install Python and retry.'; exit 1 }
Write-OK ("git: {0}"        -f (& git --version))
Write-OK ("system python: {0}" -f $sysPython)

# ---------------------------------------------------------------------------
# Phase 3 — Clone ComfyUI (pinned)
# ---------------------------------------------------------------------------

Write-Step ("Clone ComfyUI at commit {0}" -f $ComfyUICommit)

if (Test-Path (Join-Path $ComfyUIRoot '.git')) {
    Write-Skip 'ComfyUI clone already present'
    $currentHead = (& git -C $ComfyUIRoot rev-parse --short HEAD).Trim()
    if ($currentHead -ne $ComfyUICommit.Substring(0, [Math]::Min(7, $ComfyUICommit.Length))) {
        Write-Warn ("HEAD is {0}, expected {1}. Leaving as-is; bump pinned commit in script if intentional." -f $currentHead, $ComfyUICommit)
    }
} else {
    if (-not (Test-Path $AiVideoRoot)) { New-Item -ItemType Directory -Force -Path $AiVideoRoot | Out-Null }
    Write-Host "  git clone https://github.com/comfyanonymous/ComfyUI ..."
    & git clone --quiet https://github.com/comfyanonymous/ComfyUI $ComfyUIRoot
    if ($LASTEXITCODE -ne 0) { Write-Fail 'git clone failed.'; exit 1 }
    & git -C $ComfyUIRoot checkout --quiet $ComfyUICommit
    if ($LASTEXITCODE -ne 0) { Write-Warn ("Pinned commit {0} not found; staying on tip." -f $ComfyUICommit) }
    Write-OK 'ComfyUI cloned'
}

# ---------------------------------------------------------------------------
# Phase 4 — Venv + PyTorch
# ---------------------------------------------------------------------------

Write-Step 'Create venv and install PyTorch CUDA 12.6'

if (Test-Path $VenvPython) {
    Write-Skip 'venv already present'
} else {
    & $sysPython -m venv $VenvDir
    if (-not (Test-Path $VenvPython)) { Write-Fail 'venv creation failed.'; exit 1 }
    Write-OK 'venv created'
}

$torchInstalled = $false
# P2.7: only probe if the venv python actually exists. If it doesn't, we
# already know we need to install; no point catching a "file not found"
# as a "torch not installed" signal.
if (Test-Path $VenvPython) {
    try {
        $torchProbe = & $VenvPython -c "import torch; print(torch.__version__)" 2>&1
        if ($LASTEXITCODE -eq 0 -and $torchProbe -match 'cu126') {
            $torchVer = $torchProbe
            $torchInstalled = $true
        } elseif ($LASTEXITCODE -ne 0 -and $torchProbe -notmatch 'ModuleNotFoundError|ImportError') {
            # Non-zero exit AND not the "module missing" path means
            # python crashed for a real reason (corrupt venv, segfault).
            Write-Warn "venv python probe non-zero: $($torchProbe -join ' ')"
        }
    } catch {
        Write-Warn "torch probe failed: $_"
    }
}

if ($torchInstalled) {
    Write-Skip ("torch already installed in venv ({0})" -f $torchVer.Trim())
} else {
    & $VenvPython -m pip install --upgrade --quiet pip
    Write-Host "  pip install torch torchvision torchaudio --index-url cu126 (~3 GB, 3-6 min) ..."
    & $VenvPython -m pip install --quiet torch torchvision torchaudio --index-url 'https://download.pytorch.org/whl/cu126'
    if ($LASTEXITCODE -ne 0) { Write-Fail 'PyTorch install failed.'; exit 1 }
    Write-OK 'PyTorch installed'
}

# ---------------------------------------------------------------------------
# Phase 5 — ComfyUI requirements.txt
# ---------------------------------------------------------------------------

Write-Step 'Install ComfyUI requirements'

# Cheap check: see if a representative ComfyUI dep is in the venv. The req
# file is large but installing into an up-to-date venv is fast (~1-2 min).
$comfyDepOK = $false
# P2.7: same shape as the torch probe — only run if venv python exists
# and surface non-ImportError crashes instead of silently treating them
# as "not installed".
if (Test-Path $VenvPython) {
    try {
        $depProbe = & $VenvPython -c "import safetensors, kornia, transformers" 2>&1
        if ($LASTEXITCODE -eq 0) {
            $comfyDepOK = $true
        } elseif ($depProbe -notmatch 'ModuleNotFoundError|ImportError') {
            Write-Warn "venv dep probe non-zero exit, output: $($depProbe -join ' ')"
        }
    } catch {
        Write-Warn "venv dep probe failed: $_"
    }
}

if ($comfyDepOK) {
    Write-Skip 'ComfyUI requirements appear satisfied'
} else {
    & $VenvPython -m pip install --quiet -r (Join-Path $ComfyUIRoot 'requirements.txt')
    if ($LASTEXITCODE -ne 0) { Write-Fail 'ComfyUI requirements install failed.'; exit 1 }
    Write-OK 'ComfyUI requirements installed'
}

# CUDA smoke
$cudaCheck = & $VenvPython -c "import torch; print('cuda=' + str(torch.cuda.is_available()) + ' name=' + (torch.cuda.get_device_name(0) if torch.cuda.is_available() else 'none'))"
Write-OK ("CUDA smoke: {0}" -f $cudaCheck.Trim())

# ---------------------------------------------------------------------------
# Phase 6 — LTX models
# ---------------------------------------------------------------------------

if ($SkipModels) {
    Write-Step 'Skipping model downloads (-SkipModels)'
} else {
    Write-Step 'Download LTX 0.9.8 model files (~23.5 GB)'

    $models = @(
        @{
            Label  = 'LTX 0.9.8 distilled fp8 (main diffusion)'
            Url    = "$HfBase/ltxv-2b-0.9.8-distilled-fp8.safetensors"
            Target = Join-Path $ModelsDir 'checkpoints\ltxv-2b-0.9.8-distilled-fp8.safetensors'
        },
        @{
            Label  = 'LTX VAE'
            Url    = "$HfBase/vae/diffusion_pytorch_model.safetensors"
            Target = Join-Path $ModelsDir 'vae\ltx_vae.safetensors'
        },
        @{
            Label  = 'T5-XXL text encoder shard 1/4'
            Url    = "$HfBase/text_encoder/model-00001-of-00004.safetensors"
            Target = Join-Path $ModelsDir 'text_encoders\t5xxl\model-00001-of-00004.safetensors'
        },
        @{
            Label  = 'T5-XXL text encoder shard 2/4'
            Url    = "$HfBase/text_encoder/model-00002-of-00004.safetensors"
            Target = Join-Path $ModelsDir 'text_encoders\t5xxl\model-00002-of-00004.safetensors'
        },
        @{
            Label  = 'T5-XXL text encoder shard 3/4'
            Url    = "$HfBase/text_encoder/model-00003-of-00004.safetensors"
            Target = Join-Path $ModelsDir 'text_encoders\t5xxl\model-00003-of-00004.safetensors'
        },
        @{
            Label  = 'T5-XXL text encoder shard 4/4'
            Url    = "$HfBase/text_encoder/model-00004-of-00004.safetensors"
            Target = Join-Path $ModelsDir 'text_encoders\t5xxl\model-00004-of-00004.safetensors'
        },
        @{
            Label  = 'T5-XXL text encoder index'
            Url    = "$HfBase/text_encoder/model.safetensors.index.json"
            Target = Join-Path $ModelsDir 'text_encoders\t5xxl\model.safetensors.index.json'
        }
    )

    foreach ($m in $models) {
        Download-File -Url $m.Url -Target $m.Target -Label $m.Label
    }
}

# ---------------------------------------------------------------------------
# Phase 7 — Launcher
# ---------------------------------------------------------------------------

Write-Step 'Generate start_comfyui.bat'

$batContent = @"
@echo off
REM ============================================================================
REM ComfyUI launcher - Tier C (generated by scripts\setup_ai_video.ps1)
REM
REM Flags rationale (see docs\AI_VIDEO_SETUP.md for details):
REM   --lowvram               load only the active model block to GPU
REM   --reserve-vram 1        keep 1 GB VRAM free for the OS/compositor
REM   --preview-method taesd  tiny autoencoder for live previews
REM   --fp8_e4m3fn-text-enc   T5 in fp8 (~10 GB instead of ~19 GB)
REM ============================================================================

cd /d $ComfyUIRoot

call .venv\Scripts\activate.bat

python main.py ^
  --lowvram ^
  --reserve-vram 1 ^
  --preview-method taesd ^
  --fp8_e4m3fn-text-enc

call .venv\Scripts\deactivate.bat
"@

Set-Content -Path $LaunchBat -Value $batContent -Encoding ASCII
Write-OK ("wrote {0}" -f $LaunchBat)

if (-not (Test-Path $WorkflowsDir)) {
    New-Item -ItemType Directory -Force -Path $WorkflowsDir | Out-Null
    Write-OK ("created {0}" -f $WorkflowsDir)
}

# ---------------------------------------------------------------------------
# Phase 8 — MCP server runtime deps (system Python)
# ---------------------------------------------------------------------------

Write-Step 'Install MCP server deps (mcp + openai) into system Python'

& $sysPython -c "import mcp" 2>$null
$mcpOk = ($LASTEXITCODE -eq 0)
& $sysPython -c "import openai" 2>$null
$openaiOk = ($LASTEXITCODE -eq 0)

if ($mcpOk) { Write-Skip 'mcp already installed' }
else {
    & $sysPython -m pip install --user --quiet mcp
    if ($LASTEXITCODE -ne 0) { Write-Warn 'mcp install failed; comfyui-local will not work until fixed.' }
    else { Write-OK 'mcp installed' }
}

if ($openaiOk) { Write-Skip 'openai already installed' }
else {
    & $sysPython -m pip install --user --quiet openai
    if ($LASTEXITCODE -ne 0) { Write-Warn 'openai install failed; sora-cloud will not work until fixed.' }
    else { Write-OK 'openai installed' }
}

# ---------------------------------------------------------------------------
# Phase 9 — Register MCP servers with Claude Code
# ---------------------------------------------------------------------------

Write-Step 'Register MCP servers with Claude Code'

if (-not (Test-Command 'claude')) {
    Write-Warn 'claude CLI not on PATH - skipping MCP registration.'
    Write-Host '    After installing Claude Code, run these two commands:'
    Write-Host "      claude mcp add comfyui-local -- `"$sysPython`" `"$McpDir\comfyui_mcp.py`""
    Write-Host "      claude mcp add sora-cloud    -- `"$sysPython`" `"$McpDir\sora_mcp.py`""
} else {
    # `claude mcp list` returns the registered MCPs; grep by name to skip
    # re-registering. The CLI errors out cleanly if you add the same name
    # twice, but no-op-on-skip is the cleaner UX for re-runs.
    $mcpList = (& claude mcp list 2>&1 | Out-String)

    $comfyMcp = Join-Path $McpDir 'comfyui_mcp.py'
    $soraMcp  = Join-Path $McpDir 'sora_mcp.py'

    if ($mcpList -match '(?m)^comfyui-local[:\s]') {
        Write-Skip 'comfyui-local already registered'
    } else {
        & claude mcp add comfyui-local '--' $sysPython $comfyMcp 2>&1 | Out-Null
        if ($LASTEXITCODE -eq 0) { Write-OK 'comfyui-local registered' }
        else { Write-Warn 'comfyui-local registration failed (re-run after Claude Code is fully set up)' }
    }

    if ($mcpList -match '(?m)^sora-cloud[:\s]') {
        Write-Skip 'sora-cloud already registered'
    } else {
        & claude mcp add sora-cloud '--' $sysPython $soraMcp 2>&1 | Out-Null
        if ($LASTEXITCODE -eq 0) { Write-OK 'sora-cloud registered' }
        else { Write-Warn 'sora-cloud registration failed (re-run after Claude Code is fully set up)' }
    }
}

# ---------------------------------------------------------------------------
# Phase 10 — Talking-head pipeline (FLOAT + F5-TTS + VideoHelperSuite)
# ---------------------------------------------------------------------------
#
# Optional. Adds an audio-driven talking-portrait pipeline on top of ComfyUI:
#   - FFmpeg shared build (DLLs for torchcodec — replaces essentials)
#   - ComfyUI-FLOAT (yuvraj108c) — audio-driven talking portrait
#   - ComfyUI-F5-TTS (niknah) — text-to-speech (Hungarian model bundled)
#   - ComfyUI-VideoHelperSuite (Kosinkadink) — video encoding
#   - transformers downgrade <5 (FLOAT incompatible with 5.x)
#
# Total disk: ~13 GB. Generation: ~1-2 min/5s talking-head clip on Tier C.
# License: FLOAT is CC BY-NC-SA 4.0 — non-commercial use only.

$installTH = $false
if ($WithTalkingHead) {
    $installTH = $true
} elseif ($SkipTalkingHead) {
    $installTH = $false
} else {
    Write-Host ""
    Write-Host "============================================================================" -ForegroundColor Cyan
    Write-Host "Optional add-on: talking-head pipeline (FLOAT + F5-TTS)" -ForegroundColor Cyan
    Write-Host "============================================================================" -ForegroundColor Cyan
    Write-Host @"
This adds an audio-driven talking-portrait pipeline to your ComfyUI:
  - FFmpeg shared build (replaces essentials, ~95 MB)
  - ComfyUI-FLOAT custom node + ~2 GB auto-downloaded models
  - ComfyUI-F5-TTS custom node + 672 MB Hungarian voice model
  - ComfyUI-VideoHelperSuite custom node
  - transformers downgrade to 4.x (FLOAT requires <5)

Total: ~13 GB extra disk.
Generation: ~1-2 min per 5-second talking-head clip on Tier C.
License: FLOAT is CC BY-NC-SA 4.0 — non-commercial use only.

You'll still need to:
  - Save a face portrait into ai_video/comfyui/input/
  - Either supply an audio file or generate speech via F5-TTS
  - Switch the VHS_VideoCombine 'format' dropdown to 'video/h264-mp4'
    (your nvidia driver is too old for the new ffmpeg's nvenc)
"@
    $answer = Read-Host "Install talking-head pipeline? [y/N]"
    $installTH = ($answer -match '^(y|Y|yes|YES)$')
}

if ($installTH) {
    Write-Step 'Talking-head pipeline'

    # Step 10a — replace ffmpeg-essentials with ffmpeg-shared (DLLs)
    $ffmpegDir = Join-Path $AiVideoRoot 'ffmpeg'
    $sharedMarker = Join-Path $ffmpegDir 'avcodec-62.dll'
    if (Test-Path $sharedMarker) {
        Write-Skip 'ffmpeg shared build already in place'
    } else {
        Write-Host '  downloading BtbN ffmpeg-shared zip (~95 MB) ...'
        $sharedZip = Join-Path $ProjectRoot '.scratch\ffmpeg_shared.zip'
        if (-not (Test-Path (Split-Path $sharedZip))) {
            New-Item -ItemType Directory -Force -Path (Split-Path $sharedZip) | Out-Null
        }
        Invoke-WebRequest -UseBasicParsing -Uri `
            'https://github.com/BtbN/FFmpeg-Builds/releases/download/latest/ffmpeg-master-latest-win64-gpl-shared.zip' `
            -OutFile $sharedZip
        if (-not (Test-Path $ffmpegDir)) { New-Item -ItemType Directory -Force -Path $ffmpegDir | Out-Null }
        # Wipe any older essentials build (no DLLs)
        Get-ChildItem $ffmpegDir -File | Remove-Item -Force
        # Extract bin/ contents (exes + DLLs) to flat ai_video/ffmpeg/.
        # P1 security fix from qRev review: pass the paths as argv instead
        # of interpolating into a Python here-string. Even though $sharedZip
        # and $ffmpegDir are derived from $PSScriptRoot today, a single
        # quote or backslash sequence inside an install path would let
        # PowerShell-level expansion inject Python source. Passing as argv
        # closes that.
        $extractScript = @'
import sys, zipfile, os, shutil
src, dst = sys.argv[1], sys.argv[2]
with zipfile.ZipFile(src) as z:
    members = [m for m in z.namelist() if '/bin/' in m and m.endswith(('.exe', '.dll'))]
    for m in members:
        target = os.path.join(dst, os.path.basename(m))
        with z.open(m) as sf, open(target, 'wb') as df:
            shutil.copyfileobj(sf, df)
print('extracted', len(members), 'files')
'@
        $extractOutput = & $VenvPython -c $extractScript $sharedZip $ffmpegDir 2>&1
        # P3 fix: surface non-zero exit code so a silent extraction
        # failure doesn't sail past with a misleading [ok] line.
        if ($LASTEXITCODE -ne 0) {
            Write-Fail "ffmpeg extract failed (exit $LASTEXITCODE): $($extractOutput -join ' ')"
            exit 1
        }
        Write-OK "ffmpeg-shared installed ($($extractOutput -join ' '))"
    }

    # Step 10b — clone custom nodes
    $customNodesDir = Join-Path $ComfyUIRoot 'custom_nodes'
    $thRepos = @(
        @{ Name = 'ComfyUI-FLOAT';            Url = 'https://github.com/yuvraj108c/ComfyUI-FLOAT.git' },
        @{ Name = 'ComfyUI-F5-TTS';           Url = 'https://github.com/niknah/ComfyUI-F5-TTS.git' },
        @{ Name = 'ComfyUI-VideoHelperSuite'; Url = 'https://github.com/Kosinkadink/ComfyUI-VideoHelperSuite.git' }
    )
    foreach ($repo in $thRepos) {
        $target = Join-Path $customNodesDir $repo.Name
        if (Test-Path (Join-Path $target '.git')) {
            Write-Skip "$($repo.Name) already cloned"
        } else {
            Write-Host "  git clone $($repo.Name) ..."
            & git -C $customNodesDir clone --depth 1 --quiet $repo.Url
            if ($LASTEXITCODE -eq 0) { Write-OK "$($repo.Name) cloned" }
            else { Write-Warn "$($repo.Name) clone failed" }
        }
    }

    # Step 10c — pip install all three nodes' requirements into venv
    foreach ($repo in $thRepos) {
        $req = Join-Path $customNodesDir "$($repo.Name)\requirements.txt"
        if (Test-Path $req) {
            Write-Host "  pip install $($repo.Name) deps ..."
            & $VenvPython -m pip install --quiet -r $req 2>&1 | Out-Null
            if ($LASTEXITCODE -eq 0) { Write-OK "$($repo.Name) deps installed" }
            else { Write-Warn "$($repo.Name) pip install non-zero exit (check manually)" }
        }
    }

    # Step 10d — downgrade transformers (FLOAT incompatible with 5.x)
    $tver = & $VenvPython -c "import transformers; print(transformers.__version__)" 2>&1
    if ($LASTEXITCODE -eq 0 -and $tver -match '^[0-4]\.') {
        Write-Skip "transformers $($tver.Trim()) already <5"
    } else {
        Write-Host "  downgrading transformers to 4.x (FLOAT requires <5) ..."
        $dgOutput = & $VenvPython -m pip install --quiet 'transformers<5' 2>&1
        # P3 fix: print the [ok] line only if pip actually succeeded.
        if ($LASTEXITCODE -eq 0) {
            Write-OK 'transformers downgraded'
        } else {
            Write-Warn "transformers downgrade failed (exit $LASTEXITCODE): $($dgOutput -join ' ')"
        }
    }

    # Step 10e — Hungarian F5-TTS model
    $f5Dir = Join-Path $ModelsDir 'checkpoints\F5-TTS'
    $huModel = Join-Path $f5Dir 'Hungarian.safetensors'
    $huVocab = Join-Path $f5Dir 'Hungarian.txt'
    if (Test-Path $huModel) {
        Write-Skip 'Hungarian F5-TTS already present'
    } else {
        if (-not (Test-Path $f5Dir)) { New-Item -ItemType Directory -Force -Path $f5Dir | Out-Null }
        Write-Host '  downloading Maxdorger29/f5-tts-hungarian (~672 MB) ...'
        Invoke-WebRequest -UseBasicParsing -Uri `
            'https://huggingface.co/Maxdorger29/f5-tts-hungarian/resolve/main/model_last_final.safetensors' `
            -OutFile $huModel
        Invoke-WebRequest -UseBasicParsing -Uri `
            'https://huggingface.co/Maxdorger29/f5-tts-hungarian/resolve/main/vocab.txt' `
            -OutFile $huVocab
        Write-OK 'Hungarian F5-TTS downloaded'
    }

    # Step 10f — copy FLOAT example workflow into user/default/workflows/
    $floatExample = Join-Path $customNodesDir 'ComfyUI-FLOAT\float_workflow.json'
    $uwfDir = Join-Path $ComfyUIRoot 'user\default\workflows'
    if (Test-Path $floatExample) {
        if (-not (Test-Path $uwfDir)) { New-Item -ItemType Directory -Force -Path $uwfDir | Out-Null }
        Copy-Item $floatExample (Join-Path $uwfDir 'float_talking_head.json') -Force
        Write-OK 'FLOAT workflow copied to user/default/workflows/'
    }

    # Step 10g — patch launcher.bat to prepend ai_video/ffmpeg/ to PATH.
    # P2.1 fix: the previous hard-coded `cd /d D:\projects\super_claude\...`
    # regex would silently no-op on any install rooted somewhere else, and
    # the user would hit the very torchcodec libtorchcodec_core8.dll error
    # this patch is supposed to prevent. Build the regex from the actual
    # $ComfyUIRoot value so it works regardless of where the repo lives.
    $launchTxt = Get-Content $LaunchBat -Raw
    if ($launchTxt -notmatch [regex]::Escape($ffmpegDir)) {
        $cdAnchor = "cd /d $ComfyUIRoot"
        $escapedCd = [regex]::Escape($cdAnchor)
        $patched = $launchTxt -replace `
            "($escapedCd\r?\n)", `
            "`$1`r`nREM Talking-head pipeline: torchcodec needs ffmpeg shared DLLs on PATH.`r`nset `"PATH=$ffmpegDir;%PATH%`"`r`n"
        if ($patched -eq $launchTxt) {
            # The replace didn't match — surface the failure instead of
            # silently writing back the unchanged content.
            Write-Warn ("launcher patch did NOT match. Expected anchor: '" + $cdAnchor + "'. Edit start_comfyui.bat manually to prepend " + $ffmpegDir + " to PATH.")
        } else {
            Set-Content -Path $LaunchBat -Value $patched -Encoding ASCII
            Write-OK 'launcher patched to prepend ffmpeg/ to PATH'
        }
    } else {
        Write-Skip 'launcher already includes ffmpeg PATH prefix'
    }

    Write-OK 'Talking-head pipeline installed'
}

# ---------------------------------------------------------------------------
# Final report
# ---------------------------------------------------------------------------

Write-Host "`n=== Setup complete ===" -ForegroundColor Green
Write-Host @"

NEXT STEPS (you do these manually, ~3 minutes):

1. Start ComfyUI:
     $LaunchBat
   It will be reachable at http://127.0.0.1:8188 in 30-60 seconds.

2. (Cloud only) Set the OpenAI API key, either:
     `$env:OPENAI_API_KEY = "sk-..."
   or:
     "sk-..." | Out-File -NoNewline "`$HOME\.claude\.openai_api_key"

3. (Local only) Save a workflow JSON from the ComfyUI UI:
   - Open http://127.0.0.1:8188 in a browser
   - Browse Templates -> Video -> LTX-Video
     IMPORTANT: pick a workflow that uses LTX 0.9.8 (the model we
     downloaded). LTX-2.3 templates reference 22B model files we
     don't have - they will throw "missing model" errors.
   - Save (API Format) to:
       $WorkflowsDir\ltxv_t2v.json

4. Restart Claude Code so it loads the new MCP servers. Then ask:
     "Use comfyui-local generate_video with prompt 'a slow push-in on a misty pine forest at dawn'"

5. (Talking-head only) Open ComfyUI -> File -> Open ->
     $ComfyUIRoot\user\default\workflows\float_talking_head.json
   - Drop a face portrait into ai_video\comfyui\input\
   - In the LoadImage node dropdown, pick that portrait
   - In the LoadAudio node dropdown, pick an audio sample
   - In VHS_VideoCombine, change 'format' to 'video/h264-mp4' (NOT nvenc)
   - Run. First call auto-downloads FLOAT models (~2 GB), then ~1-2 min/clip.

See docs\AI_VIDEO_SETUP.md for troubleshooting and per-tier guidance.
"@
