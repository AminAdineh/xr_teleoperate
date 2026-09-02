# Windows 11 Compatibility Matrix

This document uses precise status definitions. We do NOT claim compatibility
without actual testing.

**Status definitions:**
- `SUPPORTED` — The feature is designed and implemented for Windows
- `TESTED` — The feature has been validated on Windows 11 with evidence
- `UNTESTED` — The feature is implemented but not yet validated on Windows
- `PARTIAL` — The feature works with limitations
- `BLOCKED` — The feature cannot work on Windows due to a known blocker

---

## Component Status

| Component | Status | Notes |
|-----------|--------|-------|
| **Python runtime** | SUPPORTED | Python 3.10 64-bit required |
| **NumPy / SciPy** | TESTED | Cross-platform, identical results |
| **Pinocchio** | UNTESTED | Installed via conda-forge; native C++ lib with Python bindings. Requires validation on Windows |
| **CasADi** | UNTESTED | Installed via conda-forge; IPOPT solver. Requires validation on Windows |
| **NLopt** | UNTESTED | Installed via conda-forge. Requires validation on Windows |
| **OpenCV** | SUPPORTED | pip install opencv-python provides Windows wheels |
| **PyZMQ** | TESTED | TCP fallback for IPC works on Windows; ipc:// not supported |
| **CycloneDDS** | UNTESTED | CycloneDDS supports Windows, but Unitree SDK binding requires validation |
| **unitree_sdk2_python** | UNTESTED | Requires CycloneDDS native lib + DDS network. Must validate DLL loading and DDS discovery on Windows |
| **Vuer (XR server)** | UNTESTED | HTTPS + WebSocket server; requires certificate + firewall config |
| **WebRTC** | UNTESTED | aiortc for image streaming; requires UDP firewall rules |
| **Meshcat** | SUPPORTED | Pure Python 3D visualization |
| **Rerun SDK** | SUPPORTED | pip install rerun-sdk provides Windows wheels |
| **psutil** | TESTED | Cross-platform process/network management |
| **sshkeyboard** | SUPPORTED | Cross-platform keyboard input |
| **logging-mp** | SUPPORTED | Cross-platform multiprocessing logging |
| **PyTorch** | SUPPORTED | pip install torch provides Windows wheels |
| **dex-retargeting** | UNTESTED | Pure Python (NumPy/PyTorch); should work but requires validation |
| **teleimager** | PARTIAL | Image *client* works on Windows; image *server* uses Linux-specific /dev/video, modprobe, sysfs |
| **televuer** | UNTESTED | Vuer server + WebRTC; requires HTTPS cert + XR device |

---

## Platform Abstraction Layer

| Module | Status | Notes |
|--------|--------|-------|
| `teleop.platform.__init__` | TESTED | Platform detection (is_windows, is_linux) |
| `teleop.platform.paths` | TESTED | Config/cert dir resolution (APPDATA on Windows, XDG on Linux) |
| `teleop.platform.network` | TESTED | Network interface enumeration via psutil |
| `teleop.platform.ipc_transport` | TESTED | ZMQ endpoint selection (ipc:// on Linux, tcp:// on Windows) |
| `teleop.platform.process` | TESTED | WorkerHandle (Process on Linux, Thread on Windows) |
| `teleop.platform.cpu_affinity` | TESTED | CPU affinity via psutil (cross-platform) |
| `teleop.platform.firewall` | TESTED | Firewall instructions (netsh on Windows, ufw on Linux) |
| `teleop.platform.certs` | UNTESTED | Certificate generation with SAN; requires OpenSSL on Windows |

---

## Process Model

| Feature | Linux | Windows | Notes |
|---------|-------|---------|-------|
| Hand control workers | `multiprocessing.Process` (fork) | `threading.Thread` | Thread is safe: DDS is I/O-bound, GIL impact minimal |
| Televuer server | `multiprocessing.Process` (fork) | `threading.Thread` | Vuer server is asyncio-based (I/O-bound) |
| Shared state | `multiprocessing.Array/Value` | `multiprocessing.Array/Value` | Works with both threads and processes |
| Shared memory | `shared_memory.SharedMemory` | `shared_memory.SharedMemory` | Available on Windows (Python 3.8+) |
| IPC transport | `ipc://@` (abstract socket) | `tcp://127.0.0.1:PORT` | TCP fallback with port retry |

### Thread vs Process Analysis

The conversion from `Process` to `Thread` on Windows is safe because:

1. **DDS communication is I/O-bound**: The DDS read/write calls release the GIL
   while waiting for network I/O, so the main control loop is not blocked.

2. **Retargeting computation is CPU-bound but short**: The hand retargeting
   computation takes < 1ms per iteration at 100 Hz. The GIL is held briefly,
   but the main loop (30 Hz) has 33ms between iterations, leaving ample time.

3. **No shared mutable state without locks**: All shared state uses
   `multiprocessing.Array/Value` with explicit locks, which are thread-safe.

4. **Daemon threads clean up on exit**: Daemon threads are automatically
   killed when the main process exits, preventing zombie processes.

5. **`multiprocessing.spawn()` would fail**: Windows uses `spawn()` which
   requires picklable targets. The hand controller objects contain DDS
   channels (non-picklable C++ bindings), making `Process` impossible.

---

## Known Limitations

1. **teleimager image server**: Uses Linux-specific `/dev/video*`, `modprobe`,
   `sysfs` paths. The image *client* works on Windows, but the image *server*
   must run on the robot (Linux). This is the original design — the server
   runs on the robot's onboard computer, not the Windows PC.

2. **Isaac Sim simulation**: Requires CUDA GPU and NVIDIA Isaac Sim. The
   simulation mode (`--sim`) depends on Isaac Sim's Windows support.

3. **Apple Vision Pro**: Requires a CA-signed certificate, not self-signed.
   The user must follow the upstream certificate procedure.

4. **DDS multicast on virtual adapters**: Virtual adapters (Docker, VMware,
   Hyper-V, WSL) can interfere with DDS multicast discovery. The
   `--network-interface` argument must be used to select the correct adapter.

---

## Overall Assessment

**Status: Windows 11 port implemented; hardware validation pending.**

The codebase is designed for Windows 11 with a platform abstraction layer,
but the complete real-time pipeline has not been validated with physical
hardware. The following must be completed before claiming "Windows 11
fully supported":

1. Validate native DLL loading (Pinocchio, CycloneDDS, CasADi, NLopt)
2. Validate DDS discovery and robot state reception
3. Validate XR device connection and tracking
4. Validate arm/hand control with physical robot
5. Validate 30-minute stability
6. Validate 20 restart cycles
7. Validate timing (frequency, jitter)
8. Validate numerical results match Linux
