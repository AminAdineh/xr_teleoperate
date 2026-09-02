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
- **Git for Windows** ([download](https://git-scm.com/download/win))
- **OpenSSL** (included with Git for Windows, or install separately)

---

## 2. Installation

### 2.1 Clone the repository

```powershell
git clone https://github.com/unitreerobotics/xr_teleoperate.git
cd xr_teleoperate
git submodule update --init --depth 1
```

### 2.2 Automated installation (recommended)

```powershell
.\scripts\install_windows.ps1
```

This script will:
1. Check Windows version and architecture
2. Verify Conda and Git are installed
3. Create a conda environment named `xr_teleoperate`
4. Install all dependencies (Pinocchio, NLopt via conda; others via pip)
5. Initialize git submodules and install local packages
6. Generate SSL certificates
7. Run the Windows diagnostics tool

### 2.3 Manual installation

If you prefer to install step by step:

```powershell
# Create conda environment
conda create -n xr_teleoperate python=3.10 -y
conda activate xr_teleoperate

# Install conda packages (Pinocchio, NLopt, etc.)
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
```

### 2.4 Generate SSL certificates

XR devices connect via HTTPS/WebRTC, which requires SSL certificates.

```powershell
# Create certificate directory
mkdir $env:APPDATA\xr_teleoperate

# Generate self-signed certificate
openssl req -x509 -nodes -days 365 -newkey rsa:2048 `
  -keyout $env:APPDATA\xr_teleoperate\key.pem `
  -out $env:APPDATA\xr_teleoperate\cert.pem `
  -subj "/CN=localhost"
```

For **Apple Vision Pro**, you need a CA-signed certificate. See the [upstream README](../README.md) for the full certificate procedure.

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

This adds firewall rules for the required ports:
- **8012/tcp** — Televuer HTTPS/WebRTC signaling
- **60000/tcp** — Teleimager camera config request
- **60100/tcp** — IPC data channel (Windows fallback)
- **60101/tcp** — IPC heartbeat channel (Windows fallback)

---

## 4. XR Device Setup

### Meta Quest 3 / PICO 4 Ultra
1. Put on the headset and open the web browser
2. Navigate to `https://<your-pc-ip>:8012` (e.g., `https://192.168.123.2:8012`)
3. Accept the self-signed certificate warning
4. Grant WebXR permissions when prompted

### Apple Vision Pro
1. Install the root CA certificate on the Vision Pro (via AirDrop or Safari)
2. Open Safari and navigate to `https://<your-pc-ip>:8012`
3. Grant WebXR permissions

See the [upstream README](../README.md) for detailed XR device instructions.

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

---

## 6. Simulation Mode

Simulation uses NVIDIA Isaac Sim and requires a CUDA GPU.

```powershell
conda activate xr_teleoperate

# Simulation mode (requires Isaac Sim running)
python teleop\teleop_hand_and_arm.py --arm G1_29 --ee dex3 --sim --network-interface Ethernet
```

---

## 7. Recording

```powershell
conda activate xr_teleoperate

# Record with task metadata
python teleop\teleop_hand_and_arm.py --arm G1_29 --ee dex3 --record `
  --task-name "pick cube" `
  --task-goal "pick up the red cube" `
  --task-desc "reach and grasp" `
  --task-steps "step1: reach; step2: grasp; step3: lift" `
  --network-interface Ethernet
```

Recordings are saved to `./utils/data/<task-name>/episode_XXXX/`.

---

## 8. Diagnostics

Run the Windows diagnostics tool to check your system:

```powershell
python tools\windows_diagnostics.py
```

With a specific robot IP:

```powershell
python tools\windows_diagnostics.py --robot-ip 192.168.123.164
```

This checks:
- Windows version and architecture
- Python version and architecture
- Conda environment
- CPU and GPU
- Network adapters
- Robot IP reachability
- All Python dependencies
- DDS initialization
- SSL certificates
- Firewall rules

---

## 9. Troubleshooting

### "Failed to subscribe dds within 5.0 seconds"
- The robot is not reachable or DDS cannot bind to the network interface
- Check: `python teleop\teleop_hand_and_arm.py --list-interfaces`
- Verify the robot is powered on and connected via Ethernet
- Try specifying the interface: `--network-interface Ethernet`
- Check firewall: `.\scripts\setup_windows.ps1` (as Administrator)

### "ModuleNotFoundError: No module named 'unitree_sdk2py'"
- Install the Unitree SDK:
  ```powershell
  git clone https://github.com/unitreerobotics/unitree_sdk2_python.git ..\unitree_sdk2_python
  cd ..\unitree_sdk2_python
  pip install -e .
  ```

### "ModuleNotFoundError: No module named 'pinocchio'"
- Install via conda: `conda install pinocchio -c conda-forge`
- Pinocchio is NOT available via pip on Windows

### "ModuleNotFoundError: No module named 'televuer'"
- Install the submodule: `cd teleop\televuer && pip install -e .`

### "SSL certificate not found"
- Generate certificates:
  ```powershell
  mkdir $env:APPDATA\xr_teleoperate
  openssl req -x509 -nodes -days 365 -newkey rsa:2048 -keyout $env:APPDATA\xr_teleoperate\key.pem -out $env:APPDATA\xr_teleoperate\cert.pem -subj "/CN=localhost"
  ```

### "ZMQ error: Protocol not supported"
- This should not happen after the Windows port. The IPC transport automatically uses TCP on Windows.
- If you see this, ensure you're using the Windows-compatible code (not the upstream Linux-only version).

### XR device cannot connect
- Verify the PC's IP address on the robot network: `ipconfig`
- Open `https://<your-pc-ip>:8012` in the XR browser
- Check firewall rules: `.\scripts\setup_windows.ps1`
- Verify SSL certificates are generated and accessible

### "ConnectionRefusedError: [WinError 1225]"
- The IPC TCP fallback port is blocked or in use
- Check: `netstat -an | findstr 60100`
- Restart the application

### Process crashes or hangs on exit
- Press **Ctrl+C** to trigger graceful shutdown
- The application cleans up DDS connections, image clients, and XR connections in the `finally` block
- If it hangs, close the terminal window (daemon threads will be cleaned up)

---

## 10. Platform-Specific Notes

### IPC Transport
On Linux, the application uses ZMQ's `ipc://` transport with abstract Unix sockets.
On Windows, ZMQ does not support `ipc://`, so the application automatically falls back to
`tcp://127.0.0.1` on fixed ports (60100, 60101). This is transparent to the user.

### Multiprocessing
On Linux, the application uses `multiprocessing.Process` (fork-based) for hand controller
and Vuer server processes. On Windows, these are replaced with `threading.Thread` to avoid
pickling issues with the spawn-based multiprocessing model. This does not affect robot
control behavior — the same control loops run at the same frequencies.

### Certificate Paths
- **Linux**: `~/.config/xr_teleoperate/cert.pem`
- **Windows**: `%APPDATA%/xr_teleoperate/cert.pem`
- **Environment variables**: `XR_TELEOP_CERT` and `XR_TELEOP_KEY` override the default paths

### Image Server
The `teleimager` image server (`image_server.py`) runs **on the robot** (Linux), not on the
Windows host PC. The Windows host PC only uses the `image_client.py` to receive images via ZMQ.
The image server's Linux-specific code (UVC camera paths, modprobe, etc.) does not need to
be ported to Windows.
