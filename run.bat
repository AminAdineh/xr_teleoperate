@echo off
REM ============================================================
REM  run.bat — Start xr_teleoperate with keyboard control.
REM  Double-click this file, or run it from PowerShell.
REM  Press r = start robot, q = stop, s = record (while running).
REM ============================================================
docker compose run --rm -it --service-ports teleop
pause
