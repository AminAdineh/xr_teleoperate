"""
Certificate service — wraps teleop.platform.certs for the GUI.

Provides status, generation, and path information.
"""
from __future__ import annotations

import logging
import os
from datetime import datetime
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)


class CertificateInfo:
    """Certificate status information for the GUI."""

    def __init__(self, exists: bool, valid: bool, cert_path: str,
                 key_path: str, cert_dir: str, expiry: Optional[str] = None,
                 error: str = ""):
        self.exists = exists
        self.valid = valid
        self.cert_path = cert_path
        self.key_path = key_path
        self.cert_dir = cert_dir
        self.expiry = expiry
        self.error = error


class CertificateService:

    def get_info(self) -> CertificateInfo:
        """Return current certificate status."""
        from teleop.platform.paths import get_cert_paths, get_cert_dir
        from teleop.platform.certs import is_certificate_valid

        cert_path, key_path = get_cert_paths()
        cert_dir = str(get_cert_dir())
        cert_exists = os.path.exists(cert_path) and os.path.exists(key_path)

        if not cert_exists:
            return CertificateInfo(
                exists=False, valid=False,
                cert_path=cert_path, key_path=key_path,
                cert_dir=cert_dir,
                error="Certificate files not found",
            )

        valid = False
        expiry = None
        error = ""
        try:
            valid = is_certificate_valid(cert_path, key_path)
        except Exception as exc:
            error = str(exc)

        # Try to get expiry date
        try:
            import subprocess
            result = subprocess.run(
                ["openssl", "x509", "-enddate", "-noout", "-in", cert_path],
                capture_output=True, text=True, timeout=5,
            )
            if result.returncode == 0:
                raw = result.stdout.strip().split("=", 1)[-1]
                # notAfter=Sep  2 12:00:00 2027 GMT
                expiry = raw
        except Exception:
            pass

        return CertificateInfo(
            exists=True, valid=valid,
            cert_path=cert_path, key_path=key_path,
            cert_dir=cert_dir, expiry=expiry, error=error,
        )

    def regenerate(self, lan_ip: str = None) -> tuple[str, str]:
        """Generate (or regenerate) the SSL certificate."""
        from teleop.platform.paths import get_cert_dir
        from teleop.platform.certs import generate_certificate
        cert_dir = get_cert_dir()
        return generate_certificate(cert_dir, lan_ip)

    def ensure(self) -> tuple[str, str]:
        """Ensure valid certificates exist, generating if necessary."""
        from teleop.platform.certs import ensure_certificates
        return ensure_certificates()

    def open_cert_dir(self) -> str:
        """Return the certificate directory path (for 'Open Folder')."""
        from teleop.platform.paths import get_cert_dir
        d = get_cert_dir()
        d.mkdir(parents=True, exist_ok=True)
        return str(d)
