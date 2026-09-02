<#
.SYNOPSIS
    Install script for xr_teleoperate on Windows 11.

.DESCRIPTION
    This script automates the installation of xr_teleoperate on a clean
    Windows 11 machine. It checks prerequisites, creates a conda environment,
    installs all dependencies, initializes submodules, and configures SSL
    certificates.

.EXAMPLE
    .\scripts\install_windows.ps1

.NOTES
    Requirements:
      - Windows 11 64-bit
      - Miniconda or Anaconda installed
      - Git installed
      - PowerShell 5.1+ (built into Windows 11)
#>

param(
    [string]$EnvName = "xr_teleoperate",
    [switch]$SkipConda = $false,
    [switch]$SkipSubmodules = $false,
    [switch]$SkipCerts = $false
)

$ErrorActionPreference = "Stop"

function Write-Step($msg) { Write-Host "`n=== $msg ===" -ForegroundColor Cyan }
function Write-OK($msg)   { Write-Host "[OK] $msg" -ForegroundColor Green }
function Write-Warn($msg) { Write-Host "[WARN] $msg" -ForegroundColor Yellow }
function Write-Err($msg)   { Write-Host "[ERROR] $msg" -ForegroundColor Red }

# ---------------------------------------------------------------------------
# 1. Check Windows version
# ---------------------------------------------------------------------------
Write-Step "Checking Windows version"
$osInfo = Get-CimInstance Win32_OperatingSystem
$caption = $osInfo.Caption
$buildNumber = [int]$osInfo.BuildNumber
Write-Host "OS: $caption (Build $buildNumber)"
if ($buildNumber -lt 22000) {
    Write-Warn "Windows 11 (Build 22000+) is recommended. Your build is $buildNumber."
    Write-Warn "The project may still work but is not officially supported."
} else {
    Write-OK "Windows 11 detected"
}

# Check 64-bit
$arch = $env:PROCESSOR_ARCHITECTURE
if ($arch -ne "AMD64") {
    Write-Err "64-bit Windows is required. Detected: $arch"
    exit 1
}
Write-OK "64-bit architecture confirmed"

# ---------------------------------------------------------------------------
# 2. Check Python / Conda
# ---------------------------------------------------------------------------
Write-Step "Checking Conda"
$condaCmd = Get-Command conda -ErrorAction SilentlyContinue
if (-not $condaCmd) {
    Write-Err "Conda not found. Please install Miniconda or Anaconda."
    Write-Host "  Download: https://docs.conda.io/en/latest/miniconda.html"
    exit 1
}
Write-OK "Conda found: $($condaCmd.Source)"

# ---------------------------------------------------------------------------
# 3. Check Git
# ---------------------------------------------------------------------------
Write-Step "Checking Git"
$gitCmd = Get-Command git -ErrorAction SilentlyContinue
if (-not $gitCmd) {
    Write-Err "Git not found. Please install Git for Windows."
    Write-Host "  Download: https://git-scm.com/download/win"
    exit 1
}
Write-OK "Git found: $($gitCmd.Source)"

# ---------------------------------------------------------------------------
# 4. Create conda environment
# ---------------------------------------------------------------------------
if (-not $SkipConda) {
    Write-Step "Creating conda environment: $EnvName"
    
    # Check if environment already exists
    $envExists = conda env list | Select-String "^$EnvName\s"
    if ($envExists) {
        Write-Warn "Conda environment '$EnvName' already exists. Skipping creation."
        Write-Host "  To recreate: conda env remove -n $EnvName"
    } else {
        conda create -n $EnvName python=3.10 -y
        Write-OK "Conda environment '$EnvName' created"
    }

    # Activate the environment
    Write-Step "Activating conda environment"
    conda activate $EnvName
    if ($LASTEXITCODE -ne 0) {
        Write-Err "Failed to activate conda environment '$EnvName'"
        Write-Host "  Try manually: conda activate $EnvName"
        exit 1
    }
    Write-OK "Conda environment activated"

    # ---------------------------------------------------------------------------
    # 5. Install conda packages (Pinocchio, NLopt, etc.)
    # ---------------------------------------------------------------------------
    Write-Step "Installing conda packages (pinocchio, nlopt, etc.)"
    conda install -n $EnvName pinocchio nlopt numpy scipy casadi opencv pyzmq pyyaml matplotlib psutil -c conda-forge -y
    if ($LASTEXITCODE -ne 0) {
        Write-Warn "Some conda packages may have failed to install. Check output above."
    } else {
        Write-OK "Conda packages installed"
    }

    # ---------------------------------------------------------------------------
    # 6. Install pip packages
    # ---------------------------------------------------------------------------
    Write-Step "Installing pip packages"
    pip install -r requirements-windows.txt
    if ($LASTEXITCODE -ne 0) {
        Write-Warn "Some pip packages may have failed to install."
    } else {
        Write-OK "Pip packages installed"
    }
} else {
    Write-Warn "Skipping conda environment creation (--SkipConda)"
}

# ---------------------------------------------------------------------------
# 7. Initialize submodules
# ---------------------------------------------------------------------------
if (-not $SkipSubmodules) {
    Write-Step "Initializing git submodules"
    git submodule update --init --depth 1
    if ($LASTEXITCODE -ne 0) {
        Write-Err "Failed to initialize git submodules"
        exit 1
    }
    Write-OK "Git submodules initialized"

    # Install submodule packages
    Write-Step "Installing submodule Python packages"
    
    # teleimager
    Push-Location teleop/teleimager
    pip install -e . --no-deps
    Pop-Location
    Write-OK "teleimager installed"

    # televuer
    Push-Location teleop/televuer
    pip install -e .
    Pop-Location
    Write-OK "televuer installed"

    # dex-retargeting
    Push-Location teleop/robot_control/dex-retargeting
    pip install -e .
    Pop-Location
    Write-OK "dex-retargeting installed"
} else {
    Write-Warn "Skipping submodule initialization (--SkipSubmodules)"
}

# ---------------------------------------------------------------------------
# 8. Install unitree_sdk2_python
# ---------------------------------------------------------------------------
Write-Step "Installing unitree_sdk2_python"
$sdkDir = "../unitree_sdk2_python"
if (Test-Path $sdkDir) {
    Push-Location $sdkDir
    pip install -e .
    Pop-Location
    Write-OK "unitree_sdk2_python installed"
} else {
    Write-Host "  Cloning unitree_sdk2_python..."
    git clone https://github.com/unitreerobotics/unitree_sdk2_python.git $sdkDir
    if ($LASTEXITCODE -eq 0) {
        Push-Location $sdkDir
        pip install -e .
        Pop-Location
        Write-OK "unitree_sdk2_python installed"
    } else {
        Write-Warn "Failed to clone unitree_sdk2_python. Please install manually:"
        Write-Host "    git clone https://github.com/unitreerobotics/unitree_sdk2_python.git"
        Write-Host "    cd unitree_sdk2_python"
        Write-Host "    pip install -e ."
    }
}

# ---------------------------------------------------------------------------
# 9. Configure SSL certificates
# ---------------------------------------------------------------------------
if (-not $SkipCerts) {
    Write-Step "Configuring SSL certificates"
    
    # Use the Python certificate module for proper SAN generation
    python -c "from teleop.platform.certs import ensure_certificates, print_certificate_instructions; ensure_certificates(); print_certificate_instructions()"
    if ($LASTEXITCODE -ne 0) {
        Write-Warn "Python certificate generation failed. Trying OpenSSL fallback..."
        
        $certDir = "$env:APPDATA\xr_teleoperate"
        if (-not (Test-Path $certDir)) {
            New-Item -ItemType Directory -Path $certDir -Force | Out-Null
        }
        
        $certFile = "$certDir\cert.pem"
        $keyFile = "$certDir\key.pem"
        
        if ((Test-Path $certFile) -and (Test-Path $keyFile)) {
            Write-OK "SSL certificates already exist at $certDir"
        } else {
            # Get LAN IP for certificate CN
            $lanIp = (Get-NetIPAddress -AddressFamily IPv4 | Where-Object { $_.IPAddress -notlike "127.*" -and $_.IPAddress -notlike "169.*" } | Select-Object -First 1).IPAddress
            if (-not $lanIp) { $lanIp = "localhost" }
            
            openssl req -x509 -nodes -days 365 -newkey rsa:2048 -keyout $keyFile -out $certFile -subj "/CN=$lanIp"
            if ($LASTEXITCODE -ne 0) {
                Write-Warn "OpenSSL not found or failed. Please generate certificates manually."
                Write-Host "  See docs/WINDOWS.md for instructions."
            } else {
                Write-OK "SSL certificates generated at $certDir (CN: $lanIp)"
            }
        }
    } else {
        Write-OK "SSL certificates configured"
    }
} else {
    Write-Warn "Skipping certificate generation (--SkipCerts)"
}

# ---------------------------------------------------------------------------
# 10. Windows compatibility test
# ---------------------------------------------------------------------------
Write-Step "Running Windows compatibility test"
python tools/windows_diagnostics.py
if ($LASTEXITCODE -ne 0) {
    Write-Warn "Diagnostics reported issues. Please review the output above."
} else {
    Write-OK "Diagnostics passed"
}

Write-Step "Installation complete!"
Write-Host ""
Write-Host "Next steps:"
Write-Host "  1. Connect your Windows PC to the Unitree robot via Ethernet"
Write-Host "  2. Find your network interface: python teleop/teleop_hand_and_arm.py --list-interfaces"
Write-Host "  3. Start teleoperation: python teleop/teleop_hand_and_arm.py --arm G1_29 --ee dex3 --network-interface Ethernet"
Write-Host ""
Write-Host "See docs/WINDOWS.md for the complete guide."
