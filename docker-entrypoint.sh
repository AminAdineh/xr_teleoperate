#!/usr/bin/env bash
# Entrypoint for the xr_teleoperate container.
# Handles two things the README does manually:
#   1. Generates self-signed SSL certs for televuer (so the XR headset can connect over HTTPS).
#   2. Writes a unicast CycloneDDS config pointing at the robot IP (multicast can't cross Docker's NAT).
set -euo pipefail

CERT_DIR="${XR_TELEOP_CERT_DIR:-/root/.config/xr_teleoperate}"
CERT_FILE="${CERT_DIR}/cert.pem"
KEY_FILE="${CERT_DIR}/key.pem"

# --- 1. SSL certs -----------------------------------------------------------
HOST_IP="${HOST_IP:-}"
if [[ -z "${HOST_IP}" ]]; then
  echo "[entrypoint] WARNING: HOST_IP not set. The XR headset connects to your Windows PC's LAN IP."
  echo "[entrypoint]          Set HOST_IP in docker-compose.yml so the cert includes it, or the headset will reject the cert."
fi

if [[ ! -f "${CERT_FILE}" || ! -f "${KEY_FILE}" ]]; then
  echo "[entrypoint] Generating self-signed SSL cert for televuer..."
  mkdir -p "${CERT_DIR}"
  if [[ -n "${HOST_IP}" ]]; then
    openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
      -keyout "${KEY_FILE}" -out "${CERT_FILE}" \
      -subj "/CN=localhost" \
      -addext "subjectAltName=DNS:localhost,IP:${HOST_IP}"
  else
    openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
      -keyout "${KEY_FILE}" -out "${CERT_FILE}" \
      -subj "/CN=localhost"
  fi
fi

export XR_TELEOP_CERT="${CERT_FILE}"
export XR_TELEOP_KEY="${KEY_FILE}"

# --- 2. CycloneDDS unicast config ------------------------------------------
# Docker Desktop NATs the container; DDS multicast discovery can't cross it.
# We tell CycloneDDS to talk to the robot by explicit IP (unicast) instead.
ROBOT_IP="${ROBOT_IP:-192.168.123.161}"
NET_IFACE="${NET_IFACE:-eth0}"
DDS_CONF="/tmp/cyclonedds.xml"

cat > "${DDS_CONF}" <<EOF
<?xml version="1.0" encoding="UTF-8" ?>
<CycloneDDS xmlns="https://cdds.io/config" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xsi:schemaLocation="https://cdds.io/config https://raw.githubusercontent.com/eclipse-cyclonedds/cyclonedds/master/etc/cyclonedds.xsd">
  <Domain id="any">
    <General>
      <Interfaces>
        <NetworkInterface name="${NET_IFACE}"/>
      </Interfaces>
    </General>
    <Discovery>
      <Peers>
        <Peer address="${ROBOT_IP}"/>
      </Peers>
      <ParticipantIndex>auto</ParticipantIndex>
    </Discovery>
  </Domain>
</CycloneDDS>
EOF

export CYCLONEDDS_URI="file://${DDS_CONF}"

echo "[entrypoint] DDS peer robot IP : ${ROBOT_IP}"
echo "[entrypoint] televuer HTTPS cert: ${CERT_FILE} (SAN includes ${HOST_IP:-localhost})"
echo "[entrypoint] Running: $*"

exec "$@"
