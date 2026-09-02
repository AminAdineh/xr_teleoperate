"""
Cross-platform SSL certificate management for xr_teleoperate.

On Windows, certificates are stored in %APPDATA%/xr_teleoperate/.
On Linux, certificates are stored in ~/.config/xr_teleoperate/.

This module:
  - Creates the certificate directory if it doesn't exist
  - Generates self-signed certificates with SAN for localhost and LAN IP
  - Detects existing valid certificates
  - Regenerates invalid/expired certificates
  - Displays the PC's LAN IP for the user
  - Explains browser trust requirements

For Apple Vision Pro, a CA-signed certificate is required (see upstream README).
For Meta Quest 3 / PICO, self-signed certificates work with a browser warning.
"""
import os
import sys
import ssl
import socket
import logging
import subprocess
from pathlib import Path
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


def get_lan_ip() -> str:
    """
    Determine the primary LAN IP address of this machine.

    Opens a UDP socket to a public address (without sending data) to
    determine which local interface the OS would use for outbound traffic.
    Returns '127.0.0.1' if no external interface is found.
    """
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "127.0.0.1"


def get_all_lan_ips() -> list:
    """Return all non-loopback IPv4 addresses on this machine."""
    ips = []
    try:
        from teleop.platform.network import list_network_interfaces
        for ni in list_network_interfaces():
            if ni.ipv4 and not ni.is_loopback and ni.is_up:
                ips.append(ni.ipv4)
    except Exception:
        pass
    if not ips:
        ip = get_lan_ip()
        if ip != "127.0.0.1":
            ips.append(ip)
    return ips


def is_certificate_valid(cert_path: str, key_path: str) -> bool:
    """
    Check if a certificate file exists, is readable, and not expired.

    Returns True if the certificate is valid, False otherwise.
    """
    try:
        if not os.path.exists(cert_path) or not os.path.exists(key_path):
            return False

        # Try to load the certificate
        ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        ctx.load_cert_chain(cert_path, key_path)

        # Check expiration by reading the cert file
        # OpenSSL output: notAfter=Nov  3 12:00:00 2025 GMT
        import ssl as _ssl
        cert_dict = ctx._cert_info  # may not be available on all platforms

        # Fallback: use openssl to check expiration
        result = subprocess.run(
            ["openssl", "x509", "-enddate", "-noout", "-in", cert_path],
            capture_output=True, text=True, timeout=5
        )
        if result.returncode == 0:
            # Parse: notAfter=Nov  3 12:00:00 2025 GMT
            not_after_str = result.stdout.strip().split("=")[1]
            expiry = datetime.strptime(not_after_str, "%b %d %H:%M:%S %Y %Z")
            if expiry < datetime.now() + timedelta(days=1):
                logger.warning(f"Certificate expired or expiring soon: {not_after_str}")
                return False

        return True
    except Exception as e:
        logger.warning(f"Certificate validation failed: {e}")
        return False


def generate_certificate(cert_dir: Path, lan_ip: str = None) -> tuple:
    """
    Generate a self-signed SSL certificate with SAN for localhost and LAN IP.

    Args:
        cert_dir: Directory to store the certificate
        lan_ip: LAN IP address to include in the certificate SAN.
                If None, auto-detects.

    Returns:
        (cert_path, key_path) as strings
    """
    if lan_ip is None:
        lan_ip = get_lan_ip()

    cert_dir = Path(cert_dir)
    cert_dir.mkdir(parents=True, exist_ok=True)

    cert_path = cert_dir / "cert.pem"
    key_path = cert_dir / "key.pem"

    # Build SAN (Subject Alternative Name) extension
    san_entries = ["DNS:localhost", f"IP:127.0.0.1"]
    if lan_ip and lan_ip != "127.0.0.1":
        san_entries.append(f"IP:{lan_ip}")

    # Add all LAN IPs
    for ip in get_all_lan_ips():
        entry = f"IP:{ip}"
        if entry not in san_entries:
            san_entries.append(entry)

    san_arg = ",".join(san_entries)

    # Use openssl to generate the certificate
    cmd = [
        "openssl", "req", "-x509", "-nodes", "-days", "365",
        "-newkey", "rsa:2048",
        "-keyout", str(key_path),
        "-out", str(cert_path),
        "-subj", f"/CN={lan_ip}",
        "-addext", f"subjectAltName={san_arg}"
    ]

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
        if result.returncode != 0:
            # Fallback: without SAN (older OpenSSL)
            logger.warning(f"OpenSSL SAN extension failed ({result.stderr}), trying without SAN")
            cmd_simple = [
                "openssl", "req", "-x509", "-nodes", "-days", "365",
                "-newkey", "rsa:2048",
                "-keyout", str(key_path),
                "-out", str(cert_path),
                "-subj", f"/CN={lan_ip}"
            ]
            result = subprocess.run(cmd_simple, capture_output=True, text=True, timeout=10)
            if result.returncode != 0:
                raise RuntimeError(f"OpenSSL failed: {result.stderr}")
    except FileNotFoundError:
        raise RuntimeError(
            "OpenSSL not found. Install Git for Windows (includes OpenSSL) "
            "or install OpenSSL separately."
        )

    logger.info(f"Certificate generated: {cert_path}")
    logger.info(f"  CN: {lan_ip}")
    logger.info(f"  SAN: {san_arg}")
    return str(cert_path), str(key_path)


def ensure_certificates() -> tuple:
    """
    Ensure valid SSL certificates exist, generating if necessary.

    Returns:
        (cert_path, key_path) as strings
    """
    from teleop.platform.paths import get_cert_paths, get_cert_dir

    cert_path, key_path = get_cert_paths()

    if is_certificate_valid(cert_path, key_path):
        logger.info(f"Using existing certificate: {cert_path}")
        return cert_path, key_path

    # Generate new certificates
    cert_dir = get_cert_dir()
    lan_ip = get_lan_ip()
    logger.info(f"Generating new SSL certificate for LAN IP: {lan_ip}")
    return generate_certificate(cert_dir, lan_ip)


def print_certificate_instructions():
    """Print instructions for the user about certificate trust."""
    from teleop.platform.paths import get_cert_paths, get_cert_dir

    cert_path, key_path = get_cert_paths()
    cert_dir = get_cert_dir()
    lan_ip = get_lan_ip()

    print("\n=== SSL Certificate Information ===")
    print(f"Certificate directory: {cert_dir}")
    print(f"Certificate file: {cert_path}")
    print(f"Key file: {key_path}")
    print(f"PC LAN IP: {lan_ip}")
    print()
    print("XR Device Connection:")
    print(f"  Navigate to: https://{lan_ip}:8012")
    print()
    print("Browser Trust:")
    print("  Meta Quest 3 / PICO 4 Ultra:")
    print("    - Open the browser and navigate to the URL above")
    print("    - Accept the self-signed certificate warning")
    print()
    print("  Apple Vision Pro:")
    print("    - A CA-signed certificate is required (see upstream README)")
    print("    - The self-signed certificate will NOT work on Vision Pro")
    print()
    print("  If the IP address changes (e.g., DHCP reassigns):")
    print("    - Regenerate certificates: python -m teleop.platform.certs --regenerate")
    print("    - Or delete the certificate files and restart the application")
    print()


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="SSL certificate management")
    parser.add_argument("--regenerate", action="store_true",
                        help="Force regenerate certificates even if valid ones exist")
    args = parser.parse_args()

    if args.regenerate:
        from teleop.platform.paths import get_cert_dir
        cert_dir = get_cert_dir()
        lan_ip = get_lan_ip()
        print(f"Regenerating SSL certificate for LAN IP: {lan_ip}")
        generate_certificate(cert_dir, lan_ip)
    else:
        ensure_certificates()
    print_certificate_instructions()
