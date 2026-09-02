<#
.SYNOPSIS
    Setup script for Windows Defender Firewall rules.

.DESCRIPTION
    Adds Windows Defender Firewall inbound rules for all ports required
    by xr_teleoperate. Must be run in an elevated PowerShell prompt
    (Run as Administrator).

.EXAMPLE
    .\scripts\setup_windows.ps1
#>

$ErrorActionPreference = "Stop"

# Check for admin privileges
$isAdmin = ([Security.Principal.WindowsPrincipal] [Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)

if (-not $isAdmin) {
    Write-Host "ERROR: This script requires administrator privileges." -ForegroundColor Red
    Write-Host "Right-click PowerShell -> Run as Administrator, then run this script." -ForegroundColor Yellow
    exit 1
}

Write-Host "=== Windows Defender Firewall Setup for xr_teleoperate ===" -ForegroundColor Cyan

# Define firewall rules
$rules = @(
    @{ Name = "xr_teleoperate - Televuer HTTPS (8012)"; Port = 8012; Protocol = "TCP"; Description = "Televuer HTTPS/WebRTC signaling" },
    @{ Name = "xr_teleoperate - Teleimager Config (60000)"; Port = 60000; Protocol = "TCP"; Description = "Teleimager camera config request" },
    @{ Name = "xr_teleoperate - IPC Data (60100)"; Port = 60100; Protocol = "TCP"; Description = "IPC data channel (Windows fallback)" },
    @{ Name = "xr_teleoperate - IPC Heartbeat (60101)"; Port = 60101; Protocol = "TCP"; Description = "IPC heartbeat channel (Windows fallback)" }
)

foreach ($rule in $rules) {
    $existing = Get-NetFirewallRule -DisplayName $rule.Name -ErrorAction SilentlyContinue
    if ($existing) {
        Write-Host "[SKIP] Rule already exists: $($rule.Name)" -ForegroundColor Yellow
    } else {
        New-NetFirewallRule -DisplayName $rule.Name -Direction Inbound -Action Allow -Protocol $rule.Protocol -LocalPort $rule.Port | Out-Null
        Write-Host "[OK] Added rule: $($rule.Name)" -ForegroundColor Green
    }
}

Write-Host ""
Write-Host "Firewall setup complete." -ForegroundColor Green
Write-Host "The following ports are now allowed for inbound traffic:"
foreach ($rule in $rules) {
    Write-Host "  Port $($rule.Port)/$($rule.Protocol) - $($rule.Description)"
}
