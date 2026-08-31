# Docker image for unitree xr_teleoperate.
# Uses conda (conda-forge) because pinocchio is not pip-installable as the robot dynamics lib.
# Build once on your machine (Docker Desktop on Windows is fine), then `docker compose up`.
FROM continuumio/miniconda3:24.7.1-0

# System libraries needed by OpenCV, aiortc/WebRTC, nlopt, ffmpeg, openssl.
RUN apt-get update && apt-get install -y --no-install-recommends \
        build-essential cmake git wget \
        libgl1 libglib2.0-0 libsm6 libxext6 libxrender1 \
        libjpeg-dev libpng-dev \
        ffmpeg libavcodec-dev libavformat-dev libswscale-dev \
        libssl-dev libnlopt-dev \
        openssh-client \
    && rm -rf /var/lib/apt/lists/*

# Conda env matching the README: python 3.10, pinocchio 3.1.0, numpy 1.26.4.
RUN conda create -y -n tv python=3.10 pinocchio=3.1.0 numpy=1.26.4 -c conda-forge \
    && conda clean -afy

# All subsequent RUN/CMD execute inside the conda env.
SHELL ["conda", "run", "-n", "tv", "/bin/bash", "-c"]

ENV PATH="/opt/conda/envs/tv/bin:${PATH}"

# unitree_sdk2_python: DDS communication library (cloned separately, per README 1.2).
# Install cyclonedds (the DDS python binding) explicitly, then the SDK with --no-deps
# so it does NOT pull an unpinned numpy 2.x that breaks pinocchio's ABI (built vs numpy 1.x).
RUN git clone --depth 1 https://github.com/unitreerobotics/unitree_sdk2_python.git /opt/unitree_sdk2_python \
    && pip install --no-cache-dir cyclonedds==0.10.2 \
    && cd /opt/unitree_sdk2_python && pip install --no-cache-dir -e . --no-deps

WORKDIR /app

# Install the repo's own Python requirements first (good layer cache).
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Copy the full source so the editable submodule installs resolve at build time.
# At runtime the repo is bind-mounted over /app, so edits are picked up without a rebuild.
COPY . /app

# Submodules (already checked out locally before building):
#   teleop/televuer, teleop/teleimager, teleop/robot_control/dex-retargeting
RUN pip install --no-cache-dir -e teleop/televuer \
    && pip install --no-cache-dir -e teleop/teleimager \
    && pip install --no-cache-dir -e teleop/robot_control/dex-retargeting

# teleimager server extras (aiohttp + aiortc) in case you run the image server in-container.
RUN pip install --no-cache-dir "teleimager[server]" -e teleop/teleimager || true

# Default runtime config dir for certs (televuer falls back to ~/.config/xr_teleoperate).
RUN mkdir -p /root/.config/xr_teleoperate

COPY docker-entrypoint.sh /usr/local/bin/docker-entrypoint.sh
RUN chmod +x /usr/local/bin/docker-entrypoint.sh

ENTRYPOINT ["/usr/local/bin/docker-entrypoint.sh"]
CMD ["python", "teleop/teleop_hand_and_arm.py", "--arm", "G1_29"]
