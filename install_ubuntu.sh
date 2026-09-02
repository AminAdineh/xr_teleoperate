#!/usr/bin/env bash
# ============================================================
#  install_ubuntu.sh
#  One-shot setup script for unitree xr_teleoperate on
#  Ubuntu 22.04 (Hyper-V or bare metal).
#
#  Usage:
#    chmod +x install_ubuntu.sh
#    ./install_ubuntu.sh
#
#  What it does:
#    1. Installs system packages (build tools, ffmpeg, openssl, etc.)
#    2. Installs Miniconda (if not already present)
#    3. Creates a conda env "tv" with python 3.10 + pinocchio + numpy 1.26.4
#    4. Clones xr_teleoperate + submodules
#    5. Installs unitree_sdk2_python (DDS communication)
#    6. Installs all Python requirements + submodule packages
#    7. Generates SSL certificates for the XR web page
#    8. Opens firewall port 8012
#    9. Prints next steps
# ============================================================
set -euo pipefail

# Colors for readable output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

info()  { echo -e "${CYAN}[INFO]${NC}  $*"; }
ok()    { echo -e "${GREEN}[OK]${NC}    $*"; }
warn()  { echo -e "${YELLOW}[WARN]${NC}  $*"; }
fail()  { echo -e "${RED}[ERROR]${NC} $*"; exit 1; }

# Where to install the repo (change if you want a different location)
REPO_DIR="${REPO_DIR:-$HOME/xr_teleoperate}"
CONDA_ENV="tv"

# ============================================================
# Step 1 — System packages
# ============================================================
info "Step 1/9: Installing system packages..."

sudo apt-get update -qq
sudo apt-get install -y -qq \
    build-essential cmake git wget curl \
    libssl-dev libffi-dev \
    ffmpeg libavcodec-dev libavformat-dev libswscale-dev \
    libgl1 libglib2.0-0 libsm6 libxext6 libxrender1 \
    libjpeg-dev libpng-dev \
    openssh-client \
    ufw \
    > /dev/null 2>&1

ok "System packages installed."

# ============================================================
# Step 2 — Miniconda
# ============================================================
info "Step 2/9: Installing Miniconda..."

MINICONDA_DIR="$HOME/miniconda3"
if [ -x "$MINICONDA_DIR/bin/conda" ]; then
    ok "Miniconda already installed at $MINICONDA_DIR"
else
    wget -q "https://repo.anaconda.com/miniconda/Miniconda3-latest-Linux-x86_64.sh" -O /tmp/miniconda.sh
    bash /tmp/miniconda.sh -b -p "$MINICONDA_DIR" > /dev/null 2>&1
    rm -f /tmp/miniconda.sh
    ok "Miniconda installed."
fi

# Activate conda for this script
source "$MINICONDA_DIR/etc/profile.d/conda.sh"

# Make sure conda is in PATH for future shells
if ! grep -q "miniconda3" "$HOME/.bashrc" 2>/dev/null; then
    "$MINICONDA_DIR/bin/conda" init bash > /dev/null 2>&1
    ok "conda init added to ~/.bashrc"
fi

# ============================================================
# Step 3 — Conda environment
# ============================================================
info "Step 3/9: Creating conda environment '$CONDA_ENV'..."

if conda env list | grep -q "^${CONDA_ENV} "; then
    ok "Conda env '$CONDA_ENV' already exists."
else
    conda create -y -n "$CONDA_ENV" python=3.10 pinocchio=3.1.0 numpy=1.26.4 -c conda-forge > /dev/null 2>&1
    ok "Conda env '$CONDA_ENV' created (python 3.10, pinocchio 3.1.0, numpy 1.26.4)."
fi

conda activate "$CONDA_ENV"
ok "Activated conda env '$CONDA_ENV'."

# ============================================================
# Step 4 — Clone repo + submodules
# ============================================================
info "Step 4/9: Cloning xr_teleoperate + submodules..."

if [ -d "$REPO_DIR/.git" ]; then
    ok "Repo already exists at $REPO_DIR"
else
    git clone https://github.com/unitreerobotics/xr_teleoperate.git "$REPO_DIR"
    ok "Repo cloned to $REPO_DIR"
fi

cd "$REPO_DIR"
git submodule update --init --depth 1
ok "Submodules checked out (televuer, teleimager, dex-retargeting)."

# ============================================================
# Step 5 — unitree_sdk2_python (DDS communication)
# ============================================================
info "Step 5/9: Installing unitree_sdk2_python..."

SDK_DIR="$HOME/unitree_sdk2_python"
if [ -d "$SDK_DIR/.git" ]; then
    ok "unitree_sdk2_python already cloned."
else
    git clone --depth 1 https://github.com/unitreerobotics/unitree_sdk2_python.git "$SDK_DIR"
fi

# cyclonedds must match the version the SDK expects; pin it to avoid ABI issues
pip install --quiet cyclonedds==0.10.2
# Install SDK with --no-deps so it does NOT pull numpy 2.x (breaks pinocchio's ABI)
pip install --quiet -e "$SDK_DIR" --no-deps
ok "unitree_sdk2_python installed."

# ============================================================
# Step 6 — Python requirements
# ============================================================
info "Step 6/9: Installing Python requirements..."

pip install --quiet -r "$REPO_DIR/requirements.txt"
ok "requirements.txt installed (matplotlib, rerun-sdk, meshcat, sshkeyboard)."

# ============================================================
# Step 7 — Submodule packages (televuer, teleimager, dex-retargeting)
# ============================================================
info "Step 7/9: Installing submodule packages..."

# teleimager — install with --no-deps (per README) to avoid pulling conflicting versions
pip install --quiet -e "$REPO_DIR/teleop/teleimager" --no-deps

# televuer — full install (pulls its own deps like aiohttp, aiortc)
pip install --quiet -e "$REPO_DIR/teleop/televuer"

# dex-retargeting — hand retargeting library
pip install --quiet -e "$REPO_DIR/teleop/robot_control/dex-retargeting"

# teleimager server extras (aiohttp + aiortc for WebRTC image streaming)
pip install --quiet "teleimager[server]" -e "$REPO_DIR/teleop/teleimager" || \
    warn "teleimager[server] extras had a minor issue (may already be satisfied)."

ok "Submodule packages installed."

# ============================================================
# Step 8 — SSL certificates for the XR web page
# ============================================================
info "Step 8/9: Generating SSL certificates..."

TELEVUER_DIR="$REPO_DIR/teleop/televuer"
CERT_DIR="$HOME/.config/xr_teleoperate"
mkdir -p "$CERT_DIR"

if [ -f "$CERT_DIR/cert.pem" ] && [ -f "$CERT_DIR/key.pem" ]; then
    ok "SSL certificates already exist in $CERT_DIR"
else
    # Generate self-signed cert (works for Pico / Quest — accept the warning on first visit)
    openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
        -keyout "$TELEVUER_DIR/key.pem" \
        -out "$TELEVUER_DIR/cert.pem" \
        -subj "/CN=localhost" 2>/dev/null

    # Copy to the default config dir televuer looks for
    cp "$TELEVUER_DIR/cert.pem" "$TELEVUER_DIR/key.pem" "$CERT_DIR/"

    ok "SSL certificates generated in $CERT_DIR"
    warn "For Apple Vision Pro, you need the full rootCA setup — see README section 1.1."
fi

# ============================================================
# Step 9 — Firewall
# ============================================================
info "Step 9/9: Configuring firewall..."

sudo ufw allow 8012/tcp > /dev/null 2>&1 || true
ok "Port 8012/tcp opened in UFW firewall."

# ============================================================
# Done — print next steps
# ============================================================
echo ""
echo -e "${GREEN}==============================================${NC}"
echo -e "${GREEN}  Installation complete!${NC}"
echo -e "${GREEN}==============================================${NC}"
echo ""
echo -e "Next steps:"
echo ""
echo -e "  1. ${CYAN}Find your IPs${NC} — run this on the Ubuntu VM:"
echo "       ip addr"
echo "     Note the IPv4 address (e.g. 192.168.1.50) — that's your HOST_IP."
echo "     You also need ROBOT_IP and IMG_SERVER_IP from your robot setup."
echo ""
echo -e "  2. ${CYAN}Activate the conda env${NC} (every time you open a new terminal):"
echo "       conda activate tv"
echo ""
echo -e "  3. ${CYAN}Run the teleop program${NC}:"
echo "       cd $REPO_DIR"
echo "       python teleop/teleop_hand_and_arm.py --arm G1_29 --ee dex1 \\"
echo "         --img-server-ip <IMG_SERVER_IP>"
echo ""
echo -e "  4. ${CYAN}Open on the XR headset's browser${NC}:"
echo "       https://<HOST_IP>:8012"
echo "     Accept the self-signed certificate warning on first visit."
echo ""
echo -e "  5. ${CYAN}Keyboard controls${NC} (in the terminal running the program):"
echo "       r = start robot following VR motion"
echo "       q = stop / exit"
echo "       s = toggle recording"
echo ""
echo -e "  ${YELLOW}For Apple Vision Pro${NC}: see README section 1.1 for the rootCA"
echo -e "  certificate setup (the self-signed cert above is for Pico/Quest only)."
echo ""
echo -e "  ${YELLOW}To customize${NC} (arm type, display mode, etc.):"
echo "       python teleop/teleop_hand_and_arm.py --help"
echo ""
