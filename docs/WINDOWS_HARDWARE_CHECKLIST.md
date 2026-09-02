# Windows 11 Hardware Validation Checklist

This checklist must be completed with a physical Windows 11 PC, Unitree robot,
and supported XR device before claiming "Windows 11 compatible".

## Prerequisites

- [ ] Windows 11 PC (Build 22000+) with 64-bit Python 3.10
- [ ] Unitree robot (G1, H1/H1_2, H2, or R1) powered on
- [ ] Ethernet cable connecting PC to robot
- [ ] XR device (Meta Quest 3, PICO 4 Ultra Enterprise, or Apple Vision Pro)
- [ ] PC and XR device on the same LAN

## Step 1: Installation

```powershell
git clone https://github.com/unitreerobotics/xr_teleoperate.git
cd xr_teleoperate
git submodule update --init --depth 1
.\scripts\install_windows.ps1
```

- [ ] `install_windows.ps1` completes without errors
- [ ] `python tools/windows_diagnostics.py` passes all checks
- [ ] No missing dependencies

## Step 2: Network Configuration

- [ ] PC Ethernet adapter set to 192.168.123.x subnet
- [ ] `python teleop\teleop_hand_and_arm.py --list-interfaces` shows the adapter
- [ ] `.\scripts\setup_windows.ps1` (as Administrator) adds firewall rules
- [ ] Robot IP (192.168.123.164) is pingable from PC

## Step 3: DDS Connectivity

```powershell
python tools/windows_diagnostics.py --robot-ip 192.168.123.164 --dds-test
```

- [ ] DDS initialization succeeds (domain 0)
- [ ] DDS discovery finds the robot
- [ ] Robot state data received on DDS topics

## Step 4: XR Device Connection

- [ ] SSL certificate generated with correct LAN IP
- [ ] XR device browser can reach `https://<PC-IP>:8012`
- [ ] Certificate warning accepted (Meta Quest/PICO) or CA cert installed (Vision Pro)
- [ ] WebXR permissions granted
- [ ] Hand/controller tracking data received

## Step 5: Robot Control

```powershell
python teleop\teleop_hand_and_arm.py --arm G1_29 --ee dex3 --network-interface Ethernet
```

- [ ] Program starts without errors
- [ ] DDS subscribers connect to robot state topics
- [ ] Press 'r' — robot starts following movements
- [ ] Arm movement responds correctly
- [ ] Hand movement responds correctly (if using dex3/inspire/brainco)
- [ ] End effector control works
- [ ] Press 'q' — robot stops and program exits cleanly

## Step 6: Motion Control (if applicable)

```powershell
python teleop\teleop_hand_and_arm.py --arm G1_29 --ee dex1 --input-mode controller --motion --network-interface Ethernet
```

- [ ] Controller tracking works
- [ ] Walking/locomotion responds to thumbstick
- [ ] Damping mode works (both thumbsticks pressed)

## Step 7: Stability Tests

- [ ] 10-minute continuous operation — no crashes, no memory leaks
- [ ] 30-minute continuous operation — stable CPU, RAM, thread count
- [ ] Network interruption recovery — reconnects after brief network loss
- [ ] 20 restart cycles — no zombie processes, no port conflicts, no resource leaks

## Step 8: Recording (if applicable)

```powershell
python teleop\teleop_hand_and_arm.py --arm G1_29 --ee dex3 --record --network-interface Ethernet
```

- [ ] Press 's' to start recording
- [ ] Data files created in the task directory
- [ ] Press 's' again to save recording
- [ ] Recording files are valid (images + states + actions)

## Step 9: Timing Validation

```powershell
python tools\timing_monitor.py --frequency 30 --duration 60
```

- [ ] Actual frequency within 5% of target (28.5–31.5 Hz for 30 Hz target)
- [ ] Jitter < 5ms
- [ ] No significant drift over time

## Step 10: Numerical Validation

```powershell
python tools\numerical_validation.py --output windows_results.json
```

- [ ] All numerical tests pass
- [ ] Results match Linux reference (compare with `linux_results.json`)

## Sign-off

| Item | Result | Notes |
|------|--------|-------|
| Installation | | |
| Network | | |
| DDS | | |
| XR | | |
| Arm control | | |
| Hand control | | |
| Motion control | | |
| Stability (10 min) | | |
| Stability (30 min) | | |
| Restart cycles | | |
| Recording | | |
| Timing | | |
| Numerical | | |

**Overall:** ___________ (PASS / FAIL / BLOCKED)

**Tester:** _________________  **Date:** _________________

**Hardware used:**
- PC: _______________________
- Robot: _______________________
- XR device: _______________________
