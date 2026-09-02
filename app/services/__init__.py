"""
Service layer for the Unitree XR Teleoperate desktop application.

Services encapsulate all interaction with the existing teleoperation core
and platform layer.  The GUI calls services; services call the core.
"""
from app.services.config_service import ConfigService
from app.services.network_service import NetworkService
from app.services.certificate_service import CertificateService
from app.services.diagnostics_service import DiagnosticsService, CheckResult
from app.services.robot_service import RobotService
from app.services.worker_manager import WorkerManager
from app.services.logging_service import LoggingService
