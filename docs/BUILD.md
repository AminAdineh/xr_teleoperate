# Building the Windows Installer

This document describes how the standalone Windows package is built.
The build runs **on Windows** (GitHub Actions `windows-latest` runners, or
your own Windows 11 machine) — PyInstaller cannot cross-compile from Linux.

## Automated build (GitHub Actions)

A workflow at `.github/workflows/build-windows.yml` builds the complete
package on every push to `main`/`base44` branches, on version tags (`v*`),
and via manual dispatch (Actions tab → "Run workflow").

**To get the finished installer:**

1. Go to the **Actions** tab → **Build Windows Package** → **Run workflow**,
   or push a tag: `git tag v1.0.0 && git push origin v1.0.0`.
2. Wait ~15 minutes for the build to complete.
3. Download the artifacts from the run page:
   - `UnitreeXRTeleoperateSetup.exe` — the installer
   - `UnitreeXRTeleoperatePortable.zip` — portable no-install version
4. If a tag was pushed, both files are also published as a **GitHub Release**.

## Local build (your own Windows 11 machine)

```powershell
git clone https://github.com/AminAdineh/xr_teleoperate.git
cd xr_teleoperate
git submodule update --init --depth 1
.\scripts\build_windows.ps1
```

Prerequisites: Miniconda/Anaconda, Git for Windows, Inno Setup 6
(the script auto-installs Inno Setup via Chocolatey if missing).

## What the build bundles

The PyInstaller bundle includes the embedded Python runtime and all
dependencies: PySide6/Qt, NumPy, SciPy, CasADi, OpenCV, PyZMQ, PyTorch,
Pinocchio, NLopt, psutil, CycloneDDS, Unitree SDK, televuer, teleimager,
dex-retargeting, qrcode, plus all native DLLs and data files (URDFs,
assets, certificates).

## Installer features

- Start Menu shortcut + optional Desktop shortcut
- Application icon
- Optional Windows Firewall rule configuration (robot/XR networking ports)
- Full uninstaller (removes files and firewall rules)
- License agreement page
- 64-bit only (Windows 11 x64)

## Smoke test

The packaged executable supports a headless dependency check:

```powershell
UnitreeXRTeleoperate.exe --check     # verify all deps load (CI uses this)
UnitreeXRTeleoperate.exe --version   # print version
UnitreeXRTeleoperate.exe --firewall  # configure firewall rules (admin)
```

## Output structure

```
dist/
├── UnitreeXRTeleoperate/              # PyInstaller bundle (everything)
│   └── UnitreeXRTeleoperate.exe
├── installer/
│   └── UnitreeXRTeleoperateSetup.exe  # Inno Setup installer
└── UnitreeXRTeleoperatePortable.zip   # portable archive
```
