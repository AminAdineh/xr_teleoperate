<#
.SYNOPSIS
    Build the complete Unitree XR Teleoperate Windows package.

.DESCRIPTION
    One-command build that produces:
      - dist\UnitreeXRTeleoperate\          (PyInstaller bundle)
      - dist\installer\UnitreeXRTeleoperateSetup.exe  (Inno Setup installer)
      - dist\UnitreeXRTeleoperatePortable.zip        (portable archive)

    The build is fully self-contained: it creates/updates the conda
    environment, installs all dependencies, submodules, the Unitree SDK,
    generates the app icon and SSL certificates, runs PyInstaller, compiles
    the installer, and smoke-tests the packaged executable.

.PARAMETER SkipInstaller
    Skip the Inno Setup installer step (use if ISCC is not installed).

.PARAMETER SkipSmokeTest
    Skip the post-build smoke test.

.EXAMPLE
    .\scripts\build_windows.ps1
#>
param(
    [string]$EnvName = "xr_teleoperate",
    [switch]$SkipInstaller,
    [switch]$SkipSmokeTest
)

$ErrorActionPreference = "Stop"
$ProjectRoot = Split-Path -Parent $PSScriptRoot
Set-Location $ProjectRoot

function Write-Step($msg) { Write-Host "`n=== $msg ===" -ForegroundColor Cyan }
function Write-OK($msg)   { Write-Host "[OK] $msg" -ForegroundColor Green }
function Write-Warn($msg) { Write-Host "[WARN] $msg" -ForegroundColor Yellow }
function Write-Err($msg)  { Write-Host "[ERROR] $msg" -ForegroundColor Red }

# ---------------------------------------------------------------------------
# 0. Pre-flight checks
# ---------------------------------------------------------------------------
Write-Step "Pre-flight checks"

if ($env:PROCESSOR_ARCHITECTURE -ne "AMD64") {
    Write-Err "64-bit Windows is required."
    exit 1
}
Write-OK "64-bit architecture"

$condaCmd = Get-Command conda -ErrorAction SilentlyContinue
if (-not $condaCmd) {
    Write-Err "Conda not found. Install Miniconda first:"
    Write-Host "  https://docs.conda.io/en/latest/miniconda.html"
    exit 1
}
Write-OK "Conda found: $($condaCmd.Source)"

# ---------------------------------------------------------------------------
# 1. Create / update conda environment
# ---------------------------------------------------------------------------
Write-Step "Setting up conda environment: $EnvName"

$envExists = conda env list 2>$null | Select-String "^$EnvName\s"
if ($envExists) {
    Write-Warn "Environment '$EnvName' exists — updating dependencies"
} else {
    Write-Host "Creating environment from environment-windows.yml..."
    conda env create -n $EnvName -f environment-windows.yml -y
    if ($LASTEXITCODE -ne 0) {
        Write-Err "Failed to create conda environment."
        exit 1
    }
    Write-OK "Environment created"
}

# Activate
conda activate $EnvName
if ($LASTEXITCODE -ne 0) {
    Write-Err "Failed to activate conda environment '$EnvName'"
    exit 1
}
Write-OK "Environment activated"

# Update conda packages (idempotent)
conda env update -n $EnvName -f environment-windows.yml -y 2>$null
Write-OK "Conda packages synced"

# ---------------------------------------------------------------------------
# 2. Install pip dependencies (app + build tools)
# ---------------------------------------------------------------------------
Write-Step "Installing pip dependencies"

pip install -r requirements-windows.txt
if ($LASTEXITCODE -ne 0) {
    Write-Warn "Some pip packages from requirements-windows.txt may have failed."
}

# Build-only + GUI dependencies not in the conda env file
pip install PySide6 pyinstaller qrcode Pillow
if ($LASTEXITCODE -ne 0) {
    Write-Err "Failed to install PySide6 / PyInstaller."
    exit 1
}
Write-OK "PySide6, PyInstaller, and build tools installed"

# ---------------------------------------------------------------------------
# 3. Initialize submodules and install local packages
# ---------------------------------------------------------------------------
Write-Step "Initializing git submodules"
git submodule update --init --depth 1
if ($LASTEXITCODE -ne 0) {
    Write-Err "Failed to initialize git submodules."
    exit 1
}
Write-OK "Submodules initialized"

Write-Step "Installing submodule Python packages"

Push-Location teleop\teleimager
pip install -e . --no-deps; Pop-Location
Write-OK "teleimager installed"

Push-Location teleop\televuer
pip install -e .; Pop-Location
Write-OK "televuer installed"

Push-Location teleop\robot_control\dex-retargeting
pip install -e .; Pop-Location
Write-OK "dex-retargeting installed"

# ---------------------------------------------------------------------------
# 4. Install unitree_sdk2_python
# ---------------------------------------------------------------------------
Write-Step "Installing unitree_sdk2_python"
$sdkDir = Join-Path $ProjectRoot "..\unitree_sdk2_python"
if (-not (Test-Path $sdkDir)) {
    git clone --depth 1 https://github.com/unitreerobotics/unitree_sdk2_python.git $sdkDir
}
Push-Location $sdkDir
pip install -e .; Pop-Location
Write-OK "unitree_sdk2_python installed"

# ---------------------------------------------------------------------------
# 5. Generate app icon + SSL certificates
# ---------------------------------------------------------------------------
Write-Step "Generating application icon"
python packaging\windows\generate_icon.py
Write-OK "Icon ready"

Write-Step "Generating SSL certificates"
python -c "from teleop.platform.certs import ensure_certificates; ensure_certificates()"
Write-OK "Certificates ready"

# ---------------------------------------------------------------------------
# 6. Run PyInstaller
# ---------------------------------------------------------------------------
Write-Step "Building with PyInstaller"

# Clean previous build
if (Test-Path "dist\UnitreeXRTeleoperate") {
    Remove-Item -Recurse -Force "dist\UnitreeXRTeleoperate"
}
if (Test-Path "build") {
    Remove-Item -Recurse -Force "build"
}

pyinstaller packaging\windows\unitree_xr_teleoperate.spec --noconfirm
if ($LASTEXITCODE -ne 0) {
    Write-Err "PyInstaller build failed."
    exit 1
}

$exePath = "dist\UnitreeXRTeleoperate\UnitreeXRTeleoperate.exe"
if (-not (Test-Path $exePath)) {
    Write-Err "Expected output not found: $exePath"
    exit 1
}
Write-OK "PyInstaller bundle created: $exePath"

# ---------------------------------------------------------------------------
# 7. Smoke test — verify the packaged exe starts and deps load
# ---------------------------------------------------------------------------
if (-not $SkipSmokeTest) {
    Write-Step "Smoke-testing packaged executable"
    & $exePath --check 2>&1 | Tee-Object -Variable smokeOutput
    if ($LASTEXITCODE -ne 0) {
        Write-Err "Smoke test FAILED — packaged exe could not load dependencies."
        exit 1
    }
    Write-OK "Smoke test passed"
}

# ---------------------------------------------------------------------------
# 8. Build portable zip
# ---------------------------------------------------------------------------
Write-Step "Creating portable zip"
$zipPath = "dist\UnitreeXRTeleoperatePortable.zip"
if (Test-Path $zipPath) { Remove-Item -Force $zipPath }

Compress-Archive -Path "dist\UnitreeXRTeleoperate\*" -DestinationPath $zipPath -CompressionLevel Optimal
Write-OK "Portable zip created: $zipPath"

# ---------------------------------------------------------------------------
# 9. Build Inno Setup installer
# ---------------------------------------------------------------------------
if (-not $SkipInstaller) {
    Write-Step "Building Inno Setup installer"

    $iscc = Get-Command iscc -ErrorAction SilentlyContinue
    if (-not $iscc) {
        # Try common install paths
        $isccPaths = @(
            "C:\Program Files (x86)\Inno Setup 6\ISCC.exe",
            "C:\Program Files\Inno Setup 6\ISCC.exe"
        )
        foreach ($p in $isccPaths) {
            if (Test-Path $p) { $iscc = @{ Source = $p }; break }
        }
    }

    if (-not $iscc) {
        Write-Warn "Inno Setup (ISCC) not found. Installing via chocolatey..."
        choco install innosetup -y
        $env:PATH = [System.Environment]::GetEnvironmentVariable("PATH", "Machine") + ";" + [System.Environment]::GetEnvironmentVariable("PATH", "User")
        $iscc = Get-Command iscc -ErrorAction SilentlyContinue
    }

    if ($iscc) {
        & $iscc.Source "packaging\installer\unitree_xr_teleoperate.iss"
        if ($LASTEXITCODE -ne 0) {
            Write-Err "Inno Setup compilation failed."
            exit 1
        }
        $installerPath = "dist\installer\UnitreeXRTeleoperateSetup.exe"
        if (Test-Path $installerPath) {
            $size = [math]::Round((Get-Item $installerPath).Length / 1MB, 1)
            Write-OK "Installer created: $installerPath ($size MB)"
        } else {
            Write-Err "Installer output not found."
            exit 1
        }
    } else {
        Write-Warn "Inno Setup not available — skipping installer. Install from https://jrsoftware.org/isdl.php"
    }
}

# ---------------------------------------------------------------------------
# 10. Summary
# ---------------------------------------------------------------------------
Write-Step "Build complete!"
Write-Host ""
Write-Host "Artifacts:"
if (Test-Path "dist\installer\UnitreeXRTeleoperateSetup.exe") {
    Write-Host "  Installer : dist\installer\UnitreeXRTeleoperateSetup.exe" -ForegroundColor Green
}
Write-Host "  Portable  : dist\UnitreeXRTeleoperatePortable.zip" -ForegroundColor Green
Write-Host "  Bundle    : dist\UnitreeXRTeleoperate\" -ForegroundColor Green
