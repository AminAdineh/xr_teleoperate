"""
Minimal dev status server for the Base44 preview.

Serves a simple HTML page on port 3000 showing:
  - Application info (version, robot models supported)
  - Latest test results (if available)
  - Project structure overview

This is NOT the actual PyQt desktop application — that requires a display
server and robot hardware.  This server provides a web-accessible status
dashboard for the development environment.
"""
from __future__ import annotations

import http.server
import os
import re
import socketserver
import sys
from pathlib import Path

PORT = 3000
PROJECT_ROOT = Path(__file__).resolve().parent


def _read_test_results() -> str:
    path = PROJECT_ROOT / "test_results.txt"
    if not path.exists():
        return "<p class='muted'>No test results yet. Tests run on container startup.</p>"
    raw = path.read_text(errors="replace")
    # Escape HTML
    raw = raw.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    # Color-code pass/fail lines
    lines = []
    for line in raw.splitlines():
        cls = "log-line"
        if "PASSED" in line:
            cls = "log-pass"
        elif "FAILED" in line:
            cls = "log-fail"
        elif "ERROR" in line:
            cls = "log-error"
        elif line.startswith("---"):
            cls = "log-sep"
        lines.append(f'<div class="{cls}">{line}</div>')
    return "\n".join(lines)


def _build_page() -> str:
    # Read app version
    try:
        sys.path.insert(0, str(PROJECT_ROOT))
        from app import __version__, __app_name__
    except Exception:
        __version__ = "?"
        __app_name__ = "Unitree XR Teleoperate"

    test_html = _read_test_results()

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{__app_name__} — Dev Status</title>
<style>
  :root {{
    --bg: #0d1117;
    --card: #161b22;
    --border: #30363d;
    --text: #c9d1d9;
    --muted: #8b949e;
    --accent: #4cc2ff;
    --pass: #3fb950;
    --fail: #f85149;
    --error: #f85149;
  }}
  * {{ box-sizing: border-box; margin: 0; padding: 0; }}
  body {{
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
    background: var(--bg);
    color: var(--text);
    padding: 2rem;
    max-width: 900px;
    margin: 0 auto;
  }}
  h1 {{ color: var(--accent); font-size: 1.5rem; margin-bottom: 0.25rem; }}
  .subtitle {{ color: var(--muted); margin-bottom: 1.5rem; }}
  .card {{
    background: var(--card);
    border: 1px solid var(--border);
    border-radius: 8px;
    padding: 1.25rem;
    margin-bottom: 1rem;
  }}
  .card h2 {{ font-size: 1rem; margin-bottom: 0.75rem; color: var(--accent); }}
  .info-grid {{ display: grid; grid-template-columns: 1fr 1fr; gap: 0.5rem; }}
  .info-item {{ display: flex; justify-content: space-between; padding: 0.25rem 0; }}
  .info-item .label {{ color: var(--muted); }}
  .log-box {{
    background: #0d1117;
    border: 1px solid var(--border);
    border-radius: 4px;
    padding: 0.75rem;
    font-family: 'SF Mono', 'Cascadia Code', monospace;
    font-size: 0.8rem;
    max-height: 400px;
    overflow-y: auto;
    line-height: 1.5;
  }}
  .log-pass {{ color: var(--pass); }}
  .log-fail {{ color: var(--fail); font-weight: bold; }}
  .log-error {{ color: var(--error); }}
  .log-sep {{ color: var(--muted); border-top: 1px solid var(--border); margin-top: 0.5rem; padding-top: 0.5rem; }}
  .log-line {{ color: var(--text); }}
  .muted {{ color: var(--muted); }}
  .badge {{
    display: inline-block;
    padding: 2px 8px;
    border-radius: 4px;
    font-size: 0.75rem;
    font-weight: 600;
  }}
  .badge-desktop {{ background: #1f3a5f; color: var(--accent); }}
  .badge-python {{ background: #1f3f1f; color: #7ee787; }}
</style>
</head>
<body>
  <h1>{__app_name__}</h1>
  <p class="subtitle">
    <span class="badge badge-desktop">PyQt Desktop App</span>
    <span class="badge badge-python">Python 3.12</span>
    v{__version__}
  </p>

  <div class="card">
    <h2>About</h2>
    <p>This is the Unitree XR Teleoperate desktop application — a PyQt GUI for
    teleoperating Unitree humanoid robots (G1, H1, H2, R1) using XR devices.
    The GUI launches <code>teleop_hand_and_arm.py</code> as a subprocess and
    communicates via ZMQ IPC.</p>
    <p style="margin-top:0.5rem">The actual desktop application requires a display server and robot
    hardware. This page shows the development/test status.</p>
  </div>

  <div class="card">
    <h2>Test Results</h2>
    <div class="log-box">
      {test_html}
    </div>
  </div>

  <div class="card">
    <h2>Project Structure</h2>
    <div class="info-grid">
      <div class="info-item"><span class="label">GUI App</span><span>app/</span></div>
      <div class="info-item"><span class="label">Teleop Core</span><span>teleop/</span></div>
      <div class="info-item"><span class="label">Platform Layer</span><span>teleop/platform/</span></div>
      <div class="info-item"><span class="label">Tests</span><span>tests/</span></div>
      <div class="info-item"><span class="label">Tools</span><span>tools/</span></div>
      <div class="info-item"><span class="label">Packaging</span><span>packaging/</span></div>
    </div>
  </div>
</body>
</html>"""


class Handler(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        page = _build_page()
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.end_headers()
        self.wfile.write(page.encode("utf-8"))

    def log_message(self, *args):
        pass  # suppress access logs


if __name__ == "__main__":
    with socketserver.TCPServer(("0.0.0.0", PORT), Handler) as httpd:
        print(f"Dev status server on http://0.0.0.0:{PORT}")
        httpd.serve_forever()
