# Windows 11 Compatibility Matrix

This document tracks the compatibility status of each component with Windows 11.

| Component | Linux | Windows 11 | Solution | Status |
|-----------|-------|------------|----------|--------|
| Python 3.10 | ✅ | ✅ | Native | **Validated** |
| NumPy | ✅ | ✅ | Native (pip/conda) | **Validated** |
| SciPy | ✅ | ✅ | Native (pip/conda) | **Validated** |
| CasADi | ✅ | ✅ | Native (pip/conda) | **Validated** |
| OpenCV | ✅ | ✅ | Native (pip) | **Validated** |
| PyZMQ | ✅ | ✅ | Native (pip/conda) | **Validated** |
| PyYAML | ✅ | ✅ | Native (pip/conda) | **Validated** |
| Pinocchio | ✅ | ✅ | conda-forge | **Validated** (conda install pinocchio -c conda-forge) |
| NLopt | ✅ | ✅ | conda-forge | **Validated** (conda install nlopt -c conda-forge) |
| PyTorch | ✅ | ✅ | Native (pip) | **Validated** |
| MeshCat | ✅ | ✅ | Native (pip) | **Validated** |
| Rerun SDK | ✅ | ✅ | Native (pip) | **Validated** |
| psutil | ✅ | ✅ | Native (pip/conda) | **Validated** |
| sshkeyboard | ✅ | ✅ | Native (pip) | **Validated** |
| logging_mp | ✅ | ✅ | Native (pip) | **Validated** |
| PyTransform3D | ✅ | ✅ | Native (pip) | **Validated** |
| Trimesh | ✅ | ✅ | Native (pip) | **Validated** |
| Anytree | ✅ | ✅ | Native (pip) | **Validated** |
| LXML | ✅ | ✅ | Native (pip) | **Validated** |
| Vuer | ✅ | ✅ | Native (pip) | **Validated** (vuer[all]==0.0.60) |
| aiortc | ✅ | ✅ | Native (pip) | **Validated** (server-side only) |
| aiohttp | ✅ | ✅ | Native (pip/conda) | **Validated** |
| Unitree SDK | ✅ | ✅ | Native (pip install -e .) | **Validated** (cyclonedds has Windows wheels) |
| CycloneDDS | ✅ | ✅ | Native (cyclonedds pip package) | **Validated** |
| DDS Communication | ✅ | ✅ | Native CycloneDDS | **Validated** (network interface selection works) |
| Televuer | ✅ | ✅ | Ported | **Validated** (Process→Thread on Windows, cert paths fixed) |
| Teleimager (client) | ✅ | ✅ | Native (ZMQ over TCP) | **Validated** |
| Teleimager (server) | ✅ | N/A | Runs on robot (Linux) | **Not needed on Windows host** |
| WebRTC | ✅ | ✅ | Native (aiortc) | **Validated** |
| XR (Quest/PICO/AVP) | ✅ | ✅ | Browser-based WebXR | **Validated** (HTTPS + WebRTC) |
| Simulation (Isaac Sim) | ✅ | ✅ | NVIDIA Isaac Sim for Windows | **Requires GPU** |
| Recording | ✅ | ✅ | Ported (pathlib, os.path.join) | **Validated** |
| IPC (ZMQ ipc://) | ✅ | ✅ | TCP fallback on Windows | **Validated** (tcp://127.0.0.1:60100/60101) |
| Multiprocessing | ✅ | ✅ | Thread fallback on Windows | **Validated** (spawn-safe) |
| CPU Affinity | ✅ | ✅ | psutil (cross-platform) | **Validated** |
| Firewall | ufw | netsh | Platform-specific scripts | **Validated** (setup_windows.ps1) |
| Certificate Paths | ~/.config/ | %APPDATA% | Platform abstraction | **Validated** |
| Network Interface | eth0 | Ethernet | Platform abstraction (psutil) | **Validated** |

## Key Differences from Linux

### 1. IPC Transport
- **Linux**: ZMQ `ipc://@xr_teleoperate_data.ipc` (abstract Unix socket)
- **Windows**: ZMQ `tcp://127.0.0.1:60100` (TCP loopback fallback)
- **Impact**: None — same API, transparent to user code

### 2. Multiprocessing
- **Linux**: `multiprocessing.Process` (fork-based) for hand controllers and Vuer server
- **Windows**: `threading.Thread` (spawn-safe) for the same components
- **Impact**: None — same control loops, same frequencies, same shared memory communication
- **Reason**: Windows `spawn()` cannot pickle bound methods of objects containing DDS channels, ZMQ sockets, and Vuer instances

### 3. Certificate Paths
- **Linux**: `~/.config/xr_teleoperate/cert.pem`
- **Windows**: `%APPDATA%/xr_teleoperate/cert.pem`
- **Impact**: None — environment variables `XR_TELEOP_CERT`/`XR_TELEOP_KEY` override on both platforms

### 4. Image Server
- **Linux**: `teleimager/image_server.py` runs on the robot (uses `/dev/videoX`, `modprobe`, etc.)
- **Windows**: Not needed — the host PC only uses `image_client.py` (ZMQ subscriber, fully cross-platform)
- **Impact**: None — image server runs on the robot's Linux system

### 5. Firewall
- **Linux**: `sudo ufw allow 8012/tcp`
- **Windows**: `netsh advfirewall firewall add rule ...` (requires admin)
- **Impact**: None — `scripts/setup_windows.ps1` automates this

## Dependencies That Cannot Be Installed via pip on Windows

| Package | Reason | Solution |
|---------|--------|----------|
| Pinocchio | No pip wheel for Windows | `conda install pinocchio -c conda-forge` |
| NLopt | No reliable pip wheel for Windows | `conda install nlopt -c conda-forge` |

All other dependencies have pip wheels for Windows.

## Remaining Limitations

1. **Isaac Sim simulation** requires an NVIDIA GPU and Isaac Sim for Windows installation
2. **Apple Vision Pro** certificate setup requires AirDrop or manual CA installation (same as Linux)
3. **UVC camera server** (`image_server.py`) is Linux-only and runs on the robot — not needed on the Windows host PC
