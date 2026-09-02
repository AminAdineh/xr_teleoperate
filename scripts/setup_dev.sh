#!/usr/bin/env bash
# Install all dependencies for the dev/test environment.
# Heavy/optional packages are installed separately so one failure
# doesn't block the rest.

echo "=== Installing core pip dependencies ==="
pip install --no-cache-dir -r /app/requirements-dev.txt

echo "=== Installing torch (CPU) ==="
pip install --no-cache-dir torch==2.3.0 --index-url https://download.pytorch.org/whl/cpu || echo "WARN: torch install failed"

echo "=== Installing pinocchio (pin) with --no-deps ==="
pip install --no-cache-dir --no-deps "pin>=2.7.0" || echo "WARN: pin install failed"
# pin's deps that we actually need (without numpy>=2 constraint)
pip install --no-cache-dir "cmeel-boost~=1.90.0" "cmeel-urdfdom>=6" "coal<4,>=3.0.3" "libpinocchio" "eigenpy<4,>=3.13" || echo "WARN: pin deps install failed"

echo "=== Installing unitree_sdk2_python ==="
if [ ! -d /tmp/unitree_sdk2_python ]; then
  git clone --depth 1 https://github.com/unitreerobotics/unitree_sdk2_python.git /tmp/unitree_sdk2_python || echo "WARN: SDK clone failed"
fi
if [ -d /tmp/unitree_sdk2_python ]; then
  pip install --no-cache-dir -e /tmp/unitree_sdk2_python || echo "WARN: SDK install failed"
fi

echo "=== Installing submodules ==="
pip install --no-cache-dir --no-deps -e /app/teleop/televuer || echo "WARN: televuer install failed"
pip install --no-cache-dir --no-deps -e /app/teleop/robot_control/dex-retargeting || echo "WARN: dex-retargeting install failed"
# teleimager requires Python<3.12; add to PYTHONPATH instead (already set in compose)
# teleimager src dir is on PYTHONPATH via docker-compose environment

echo "=== Installing vuer (televuer dependency) ==="
pip install --no-cache-dir "vuer[all]==0.0.60" || echo "WARN: vuer install failed (non-critical)"
# Pin params_proto to a version compatible with vuer 0.0.60
pip install --no-cache-dir "params_proto==2.13.0" || echo "WARN: params_proto pin failed"

echo "=== Re-pinning numpy<2.0.0 (must be last) ==="
pip install --no-cache-dir --force-reinstall "numpy<2.0.0" || echo "WARN: numpy re-pin failed"

echo "=== Setup complete ==="
