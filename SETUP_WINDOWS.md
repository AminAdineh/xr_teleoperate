# Running xr_teleoperate on Windows with Docker Desktop

This lets you run the Unitree XR teleoperation stack on Windows **without WSL2 or a native Ubuntu install** — only Docker Desktop.

## Prerequisites

- [Docker Desktop](https://www.docker.com/products/docker-desktop/) installed and running.
- This repo cloned to your Windows machine, **with submodules**:
  ```powershell
  git clone https://github.com/<your-fork>/xr_teleoperate.git
  cd xr_teleoperate
  git submodule update --init --depth 1
  ```
- Your Windows PC on the **same LAN** as the robot and the camera/image-server PC.

## 1. Configure the IPs

Create a `.env` file next to `docker-compose.yml` (Docker Compose reads it automatically):

```env
# Your Unitree robot's LAN IP (find it on the robot's display or via the Unitree app)
ROBOT_IP=192.168.123.161

# Your WINDOWS PC's LAN IP — the XR headset connects here over HTTPS
# Run `ipconfig` in PowerShell and use your Wi-Fi/Ethernet IPv4 address.
HOST_IP=192.168.1.50

# The PC running teleimager with the cameras (often the robot's onboard PC or a host PC)
IMG_SERVER_IP=192.168.123.164
```

## 2. Build the image (first time only)

```powershell
docker compose build
```

This takes **15–30 minutes** the first time — it downloads PyTorch (~2 GB) and builds the conda environment with `pinocchio`. Subsequent builds are fast thanks to layer caching.

## 3. Start teleoperation

```powershell
docker compose up
```

The container will:
- generate a self-signed SSL certificate (with your `HOST_IP` in it) for the televuer HTTPS page,
- write a unicast CycloneDDS config pointing at `ROBOT_IP` (multicast can't cross Docker's NAT),
- launch `teleop/teleop_hand_and_arm.py`.

## 4. Connect the XR headset

On the headset browser, open:

```
https://<HOST_IP>:8012
```

Accept the self-signed certificate warning the first time (for Apple Vision Pro, also install the generated `rootCA` — see the main README's cert section).

## How the networking works

Docker Desktop runs the container behind a NAT. Two things make the robot reachable:

- **DDS (robot control):** CycloneDDS normally discovers the robot via multicast, which can't cross Docker's NAT. The entrypoint writes a `cyclonedds.xml` that uses **unicast** — it talks to the robot by explicit IP (`ROBOT_IP`). Unicast crosses the NAT fine.
- **televuer (XR page):** Port `8012` is mapped from the container to your Windows host, so the headset reaches it at your PC's LAN IP.

## Customizing the run

The launch command is in `docker-compose.yml` under `command:`. Common flags:

| Flag | Options | Default in compose |
|------|---------|--------------------|
| `--arm` | `G1_29` `G1_23` `H1_2` `H1` `H2` `R1_A5` `R1_A7` | `G1_29` |
| `--ee` | `dex1` `dex1_internal` `dex3` `inspire_ftp` `inspire_dfx` `brainco` | `dex1` |
| `--display-mode` | `immersive` `ego` `pass-through` | `immersive` |
| `--input-mode` | `hand` `controller` | `hand` |
| `--motion` | flag — enable walking control | off |
| `--sim` | flag — Isaac Sim mode | off |

See all flags:
```powershell
docker compose run --rm teleop python teleop/teleop_hand_and_arm.py --help
```

## Troubleshooting

- **Headset can't open the page:** check `HOST_IP` is your PC's real LAN IP and port 8012 isn't firewalled (`netsh advfirewall firewall add rule name="televuer" dir=in action=allow protocol=TCP localport=8012`).
- **Robot not responding / DDS timeout:** confirm `ROBOT_IP` is correct and the robot is reachable from Windows (`ping <ROBOT_IP>`). The container needs the robot on the same LAN.
- **No camera image:** the `IMG_SERVER_IP` PC must be running `teleimager-server` with cameras attached.
- **`_ARRAY_API` / segfault on import:** numpy got upgraded to 2.x — the Dockerfile pins numpy 1.26.4 and installs the SDK with `--no-deps` to prevent this; don't add a bare `pip install numpy` later.
