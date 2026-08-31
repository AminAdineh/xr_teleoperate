# Beginner's Guide: Run xr_teleoperate on Windows with Docker Desktop

Complete walkthrough — from zero to robot teleoperation on Windows, using only Docker Desktop (no Ubuntu, no WSL2 terminal).

---

## Step 1 — Install Docker Desktop

1. Go to https://www.docker.com/products/docker-desktop/ and download the Windows installer.
2. Run it. When it asks to enable **WSL2**, say yes (this is just a background engine Docker uses — you never open or touch WSL2 yourself).
3. Restart your PC if asked.
4. Open **Docker Desktop** from the Start menu. Wait until the whale icon in the bottom-left says **"Engine running"** (green). Leave it running.

---

## Step 2 — Get the project files

**Option A — if you already cloned the repo from GitHub:**
1. Open **PowerShell** (search "PowerShell" in the Start menu).
2. Navigate to your repo folder:
   ```powershell
   cd C:\Users\YourName\xr_teleoperate
   ```
   (use whatever path you cloned it to)
3. Download the 4 Docker files (Dockerfile, docker-compose.yml, docker-entrypoint.sh, SETUP_WINDOWS.md) and place them **into that folder** (next to the `teleop` folder, not inside it).
4. Still in PowerShell, check out the submodules:
   ```powershell
   git submodule update --init --depth 1
   ```
   Wait until it finishes (it downloads televuer, teleimager, and dex-retargeting).

**Option B — if you haven't cloned anything yet:**
```powershell
cd C:\Users\YourName
git clone https://github.com/unitreerobotics/xr_teleoperate.git
cd xr_teleoperate
git submodule update --init --depth 1
```
Then download the zip with the 4 Docker files and unzip them into that `xr_teleoperate` folder.

---

## Step 3 — Find your three IP addresses

You need three numbers. Open PowerShell and run:

```powershell
ipconfig
```

Look for the line under your Wi-Fi or Ethernet adapter that says **IPv4 Address** — e.g. `192.168.1.50`. That's your **HOST_IP** (your Windows PC on the network).

The other two you get from your robot setup:
- **ROBOT_IP** — the Unitree robot's IP (shown on the robot's display or in the Unitree app). Often `192.168.123.161`.
- **IMG_SERVER_IP** — the PC that has the cameras connected and runs the image server. Often `192.168.123.164` (the robot's onboard PC or a host PC).

---

## Step 4 — Create the `.env` file

In your `xr_teleoperate` folder (the one with `docker-compose.yml`), create a new text file named exactly `.env` (no name before the dot). Open it in Notepad and paste:

```env
ROBOT_IP=192.168.123.161
HOST_IP=192.168.1.50
IMG_SERVER_IP=192.168.123.164
```

Replace the numbers with your real IPs from Step 3. Save and close.

> **Notepad tip:** when saving, change "Save as type" to "All Files" so it doesn't add `.txt` to the end.

---

## Step 5 — Build the Docker image (one time, ~15–30 min)

In PowerShell, in your repo folder:

```powershell
docker compose build
```

This downloads everything (Python, PyTorch ~2GB, pinocchio, all the libraries) and builds the environment. **It's slow the first time — that's normal.** Go grab a coffee. You'll see lots of text scrolling. When it says "naming to ... xr-teleoperate:latest" and returns to the prompt, it's done.

If it fails, copy the last ~20 lines of the error and paste them to me.

---

## Step 6 — Start the teleoperation program

```powershell
docker compose up
```

You'll see logs scrolling. The container is now:
- generating an SSL certificate,
- connecting to the robot over DDS,
- starting the XR web page on port 8012.

**Leave this window open** — closing it stops the program.

---

## Step 7 — Connect your XR headset

On your headset's browser (Quest/Pico browser, or Vision Pro Safari), open:

```
https://192.168.1.50:8012
```
(replace with your real **HOST_IP** from Step 3)

- The first time it'll warn about an untrusted certificate — that's expected (it's self-signed). Click **Advanced → Proceed / Continue**.
- For **Apple Vision Pro**, you'll also need to install the root certificate (see the main README's cert section; for a first test you can skip it and just proceed past the warning).

Put on the headset and you should see the robot's camera view. Press **`r`** on your keyboard (in the PowerShell window) to start the robot following your hand movements. Press **`q`** to stop.

---

## Quick reference — what each command does

| Command | What it does |
|---------|-------------|
| `docker compose build` | Builds the image (once) |
| `docker compose up` | Starts teleoperation |
| `docker compose down` | Stops and cleans up |
| `docker compose run --rm teleop python teleop/teleop_hand_and_arm.py --help` | See all available flags |

---

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

---

## Troubleshooting

- **"Cannot connect to the Docker daemon"** → Docker Desktop isn't running. Open it and wait for "Engine running".
- **Headset page won't load** → check `HOST_IP` matches your PC's real IP, and that port 8012 isn't blocked by Windows Firewall (click "Allow access" if a firewall popup appears). You can also open it manually:
  ```powershell
  netsh advfirewall firewall add rule name="televuer" dir=in action=allow protocol=TCP localport=8012
  ```
- **Robot not moving / DDS timeout** → check `ROBOT_IP` is correct and you can `ping` the robot from PowerShell.
- **No camera image** → the image-server PC (`IMG_SERVER_IP`) must be running `teleimager-server` with cameras plugged in.
- **`_ARRAY_API` / segfault on import** → numpy got upgraded to 2.x — the Dockerfile pins numpy 1.26.4 and installs the SDK with `--no-deps` to prevent this; don't add a bare `pip install numpy` later.
- **Any build error** → paste the last 20 lines of the error and ask for help.
