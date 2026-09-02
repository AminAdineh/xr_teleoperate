<#
.SYNOPSIS
    Configure Windows Defender Firewall for xr_teleoperate.

.DESCRIPTION
    Adds inbound firewall rules for all ports required by xr_teleoperate.
    Must be run in an elevated PowerShell prompt (Run as Administrator).

.EXAMPLE
    .\scripts\setup_windows.ps1
#>

$ErrorActionPreference = "Stop"

function Write-Step($msg) { Write-Host "`n=== $msg ===" -ForegroundColor Cyan }
function Write-OK($msg)   { Write-Host "[OK] $msg" -ForegroundColor Green }
function Write-Warn($msg) { Write-Host "[WARN] $msg" -ForegroundColor Yellow }
function Write-Err($msg)   { Write-Host "[ERROR] $msg" -ForegroundColor Red }

# Check admin
$isAdmin = ([Security.Principal.WindowsPrincipal] [Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
if (-not $isAdmin) {
    Write-Err "This script must be run as Administrator."
    Write-Host "  Right-click PowerShell -> Run as Administrator"
    exit 1
}

Write-Step "Configuring Windows Defender Firewall for xr_teleoperate"

# Define firewall rules
$rules = @(
    @{Name="xr_teleoperate HTTPS/WebRTC signaling"; Port=8012;  Protocol="TCP"; Dir="in"; Scope="any"},
    @{Name="xr_teleoperate Teleimager config";       Port=60000; Protocol="TCP"; Dir="in"; Scope="any"},
    @{Name="xr_teleoperate IPC data (localhost)";    Port=60100; Protocol="TCP"; Dir="in"; Scope="localsubnet"},
    @{Name="xr_teleoperate IPC heartbeat (localhost)"; Port=60101; Protocol="TCP"; Dir="in"; Scope="localsubnet"},
    @{Name="xr_teleoperate DDS multicast";           Port=7400;  Protocol="UDP"; Dir="in"; Scope="any"},
    @{Name="xr_teleoperate DDS unicast range";        Port=7401-7500; Protocol="UDP"; Dir="in"; Scope="any"},
    @{Name="xr_teleoperate WebRTC media";             Port=49152-65535; Protocol="UDP"; Dir="in"; Scope="any"}
)

foreach ($rule in $rules) {
    $ruleName = $rule.Name
    $port = $rule.Port
    $proto = $rule.Protocol
    $dir = $rule.Dir
    $scope = $rule.Scope

    # Check if rule already exists
    $existing = Get-NetFirewallRule -DisplayName $ruleName -ErrorAction SilentlyContinue
    if ($existing) {
        Write-Warn "Firewall rule '$ruleName' already exists. Skipping."
        continue
    }

    try {
        if ($port -match "-") {
            # Port range
            $portStr = $port
        } else {
            $portStr = $port
        }

        if ($scope -eq "localsubnet") {
            netsh advfirewall firewall add rule name="$ruleName" dir=$dir action=allow protocol=$proto localport=$portStr remoteip=LocalSubnet 2>&1 | Out-Null
        } else {
            netsh advfirewall firewall add rule name="$ruleName" dir=$dir action=allow protocol=$proto localport=$portStr 2>&1 | Out-Null
        }

        if ($LASTEXITCODE -eq 0) {
            Write-OK "Added: $ruleName ($proto/$port)"
        } else {
            Write-Err "Failed to add: $ruleName ($proto/$port)"
        }
    } catch {
        Write-Err "Error adding rule '$ruleName': $_"
    }
}

Write-Step "Firewall configuration complete"
Write-Host ""
Write-Host "Added rules:"
Write-Host "  Port 8012/tcp  - HTTPS/WebRTC signaling (LAN)"
Write-Host "  Port 60000/tcp - Teleimager camera config (LAN)"
Write-Host "  Port 60100/tcp - IPC data channel (localhost)"
Write-Host "  Port 60101/tcp - IPC heartbeat channel (localhost)"
Write-Host "  Port 7400/udp  - DDS multicast (LAN)"
Write-Host "  Port 7401-7500/udp - DDS unicast (LAN)"
Write-Host "  Port 49152-65535/udp - WebRTC media (LAN)"
Write-Host ""
Write-Host "To remove all rules:"
Write-Host '  Get-NetFirewallRule -DisplayName "xr_teleoperate*" | Remove-NetFirewallRule'
