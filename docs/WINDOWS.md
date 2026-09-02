# Windows 11 Installation & Usage Guide

This guide walks you through setting up and running **xr_teleoperate** on a native Windows 11 computer — no WSL, Docker, or Linux VM required.

---

## 1. Requirements

### Hardware
- **Windows 11 64-bit** (Build 22000 or later)
- **8+ GB RAM** (16 GB recommended for simulation)
- **Ethernet port** (for connecting to the Unitree robot)
- **XR device**: Meta Quest 3, PICO 4 Ultra Enterprise, or Apple Vision Pro
- **Unitree robot**: G1, H1/H1_2, H2, or R1

### Software
- **Miniconda or Anaconda** ([download](https://docs.conda.io/en/latest/miniconda.html))
- **Git for Windows** ([download](https://git-scm.com/download/win)) — includes OpenSSL

---

## 2. Installation (from clean Windows 11)

### 2.1 Clone and install

```powershell
git clone https://github.com/unitreerobotics/xr_teleoperate.git
cd xr_teleoperate
git submodule update --init --depth 1
.\scripts\install_windows.ps1
```

The install script will:
1. Check Windows version and architecture
2. Verify Conda and Git are installed
3. Create a conda environment named `xr_teleoperate`
4. Install all dependencies (Pinocchio, NLopt via conda; others via pip)
5. Initialize git submodules and install local packages
6. Clone and install `unitree_sdk2_python` (if not present)
7. Generate SSL certificates with the PC's LAN IP
8. Run the Windows diagnostics tool

### 2.2 Verify installation

```powershell
python tools\windows_diagnostics.py
```

This checks:
- Windows version and architecture
- Python version and architecture
- Conda environment
- CPU and GPU
- Network adapters
- Robot IP reachability
- All Python dependencies
- Native DLL loading (use `--dll-check`)
- DDS initialization
- ZMQ IPC transport
- SSL certificates
- Firewall rules
- Process/thread model

With a robot connected:
```powershell
python tools\windows_diagnostics.py --robot-ip 192.168.123.164 --dds-test
```

### 2.3 Manual installation (if automated script fails)

```powershell
# Create conda environment
conda create -n xr_teleoperate python=3.10 -y
conda activate xr_teleoperate

# Install conda packages
conda install pinocchio nlopt numpy scipy casadi opencv pyzmq pyyaml matplotlib psutil -c conda-forge -y

# Install pip packages
pip install -r requirements-windows.txt

# Initialize submodules
git submodule update --init --depth 1

# Install submodule packages
cd teleop\teleimager
pip install -e . --no-deps
cd ..\..

cd teleop\televuer
pip install -e .
cd ..\..

cd teleop\robot_control\dex-retargeting
pip install -e .
cd ..\..

# Install Unitree SDK
git clone https://github.com/unitreerobotics/unitree_sdk2_python.git ..\unitree_sdk2_python
cd ..\unitree_sdk2_python
pip install -e .
cd ..\xr_teleoperate

# Generate SSL certificates
python -c "from teleop.platform.certs import ensure_certificates, print_certificate_instructions; ensure_certificates(); print_certificate_instructions()"
```

---

## 3. Network Configuration

### 3.1 Connect to the robot

1. Connect an Ethernet cable from your Windows PC to the Unitree robot
2. The robot's default IP is `192.168.123.164`
3. Set your PC's Ethernet adapter to the same subnet:
   - IP: `192.168.123.2` (or any free address on 192.168.123.x)
   - Subnet mask: `255.255.255.0`

### 3.2 Find your network interface

```powershell
python teleop\teleop_hand_and_arm.py --list-interfaces
```

This will print all available network adapters:

```
Name                     IPv4             MAC                Status
----------------------------------------------------------------------
Ethernet                 192.168.123.2    00:1a:2b:...      UP
Wi-Fi                    192.168.1.50     00:1a:2b:...      UP
Loopback Pseudo-Interface 1 127.0.0.1                        UP (loopback)
```

Note the name of the adapter connected to the robot (e.g., `Ethernet`).

### 3.3 Configure Windows Defender Firewall

Run in an **elevated PowerShell prompt** (Run as Administrator):

```powershell
.\scripts\setup_windows.ps1
```

**Required ports:**

| Port | Protocol | Purpose | Scope |
|------|----------|---------|-------|
| 8012 | TCP | Televuer HTTPS/WebRTC signaling | LAN |
| 60000 | TCP | Teleimager camera config request | LAN |
| 60100 | TCP | IPC data channel (Windows) | localhost only |
| 60101 | TCP | IPC heartbeat channel (Windows) | localhost only |
| 7400-7500 | UDP | DDS multicast/unicast discovery | LAN |
| 49152-65535 | UDP | WebRTC media (dynamic) | LAN |

**Note:** DDS uses UDP multicast on port 7400 by default. The firewall must
allow UDP traffic on the robot network interface. If you have virtual adapters
(Docker, VMware, Hyper-V, WSL), DDS may try to use them — use `--network-interface`
to force the correct adapter.

---

## 4. SSL Certificates

XR devices connect via HTTPS, which requires SSL certificates.

### 4.1 Automatic generation

The install script generates certificates automatically. To regenerate:

```powershell
python -m teleop.platform.certs --regenerate
```

The certificate includes:
- **CN**: The PC's LAN IP address
- **SAN**: localhost, 127.0.0.1, and all detected LAN IPs

### 4.2 Certificate location

- **Windows**: `%APPDATA%\xr_teleoperate\cert.pem` and `key.pem`
- **Linux**: `~/.config/xr_teleoperate/cert.pem` and `key.pem`

### 4.3 Browser trust

**Meta Quest 3 / PICO 4 Ultra:**
1. Open the browser on the headset
2. Navigate to `https://<your-pc-ip>:8012`
3. Accept the self-signed certificate warning
4. Grant WebXR permissions

**Apple Vision Pro:**
1. A CA-signed certificate is required (self-signed will NOT work)
2. Install the root CA certificate on the Vision Pro
3. Open Safari and navigate to `https://<your-pc-ip>:8012`
4. Grant WebXR permissions

See the [upstream README](../README.md) for the full Vision Pro certificate procedure.

### 4.4 When the IP changes

If your PC's IP address changes (e.g., DHCP reassignment):
1. Regenerate certificates: `python -m teleop.platform.certs --regenerate`
2. Or delete the certificate files and restart the application

---

## 5. Launch Teleoperation

### Physical robot

```powershell
conda activate xr_teleoperate

# Basic command (G1 with Dex3 hand, hand tracking)
python teleop\teleop_hand_and_arm.py --arm G1_29 --ee dex3 --network-interface Ethernet

# With motion control (walking)
python teleop\teleop_hand_and_arm.py --arm G1_29 --ee dex3 --motion --network-interface Ethernet

# With controller input instead of hand tracking
python teleop\teleop_hand_and_arm.py --arm G1_29 --ee dex1 --input-mode controller --network-interface Ethernet

# H1_2 robot
python teleop\teleop_hand_and_arm.py --arm H1_2 --ee dex3 --network-interface Ethernet

# R1 robot (5-DoF arm)
python teleop\teleop_hand_and_arm.py --arm R1_A5 --ee dex3 --network-interface Ethernet
```

### Controls
- **[r]** — Start robot following your movements
- **[s]** — Start/stop recording (toggle)
- **[q]** — Stop and exit

### Simulation mode

```powershell
conda activate xr_teleoperate
python teleop\teleop_hand_and_arm.py --arm G1_29 --ee dex3 --sim --network-interface Ethernet
```

Simulation requires NVIDIA Isaac Sim and a CUDA GPU.

---

## 6. Diagnostics and Troubleshooting

### Network diagnostics

```powershell
# List network interfaces
python teleop\teleop_hand_and_arm.py --list-interfaces

# Check robot reachability
python tools\windows_diagnostics.py --robot-ip 192.168.123.164

# Full diagnostics with DDS test
python tools\windows_diagnostics.py --robot-ip 192.168.123.164 --dds-test
```

### DLL validation

```powershell
python tools\windows_diagnostics.py --dll-check
```

This checks that all native libraries (CycloneDDS, Pinocchio, CasADi, NLopt)
are loadable and reports the DLL path for each.

### Timing validation

```powershell
python tools\timing_monitor.py --frequency 30 --duration 60
```

### Numerical validation

```powershell
python tools\numerical_validation.py --output windows_results.json
```

### Common issues

#### "Failed to subscribe dds within 5.0 seconds"
- The robot is not reachable or DDS cannot bind to the network interface
- Check: `python teleop\teleop_hand_and_arm.py --list-interfaces`
- Verify the robot is powered on and connected via Ethernet
- Try specifying the interface: `--network-interface Ethernet`
- Check firewall: `.\scripts\setup_windows.ps1` (as Administrator)
- Check for virtual adapters (Docker, VMware, Hyper-V) that may interfere with DDS

#### "ModuleNotFoundError: No module named 'unitree_sdk2py'"
```powershell
git clone https://github.com/unitreerobotics/unitree_sdk2_python.git ..\unitree_sdk2_python
cd ..\unitree_sdk2_python
pip install -e .
```

#### "ModuleNotFoundError: No module named 'pinocchio'"
```powershell
conda install pinocchio -c conda-forge
```
Pinocchio is NOT available via pip on Windows.

#### "DLL load failed" or "The specified module could not be found"
- Ensure you're using 64-bit Python: `python -c "import platform; print(platform.architecture())"`
- Reinstall the failing package via conda: `conda install <package> -c conda-forge`
- Run DLL diagnostics: `python tools\windows_diagnostics.py --dll-check`

#### "SSL certificate not found"
```powershell
python -c "from teleop.platform.certs import ensure_certificates; ensure_certificates()"
```

#### "ZMQ error: Protocol not supported"
- This should not happen after the Windows port. If it does, ensure
  `teleop.platform.ipc_transport` is being imported correctly.
- Check: `python -c "from teleop.platform.ipc_transport import get_ipc_endpoint; print(get_ipc_endpoint('test'))"`

#### "Address already in use" (ZMQ bind error)
- A previous instance may not have shut down cleanly
- Wait 30 seconds for TIME_WAIT to expire, or:
- The IPC transport module will automatically retry on the next available port

#### XR device cannot connect
- Verify the PC's LAN IP: `python -c "from teleop.platform.certs import get_lan_ip; print(get_lan_ip())"`
- Ensure the XR device is on the same network
- Check firewall rules for port 8012
- Verify the certificate includes the PC's LAN IP in the SAN

---

## 7. See also

- [Windows Compatibility Matrix](WINDOWS_COMPATIBILITY.md) — detailed component status
- [Windows Test Results](WINDOWS_TEST_RESULTS.md) — test matrix with evidence
- [Hardware Validation Checklist](WINDOWS_HARDWARE_CHECKLIST.md) — physical robot test procedure
- [Upstream README](../README.md) — original Linux documentation
