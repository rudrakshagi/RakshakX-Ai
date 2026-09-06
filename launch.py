"""RakshakX Unified Platform Launcher.

Boots all platform services in a single command:
1. Python Backend REST API (Port 8080)
2. React + TypeScript Enterprise Console UI (Port 3000)
3. Model Context Protocol (MCP) Bridge for Antigravity, OpenCode & Claude
"""

from __future__ import annotations

import os
import subprocess
import sys
import threading
import time
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent
WEB_DIR = ROOT_DIR / "web"


def start_bridge():
    """Start the OpenCode bridge on port 8787 (proxied via Vite /v1)."""
    npm_cmd = "npm.cmd" if sys.platform == "win32" else "npm"
    bridge_dir = ROOT_DIR / "opencode-bridge"
    subprocess.run([npm_cmd, "start"], cwd=str(bridge_dir))


def start_backend():
    """Start the Python Backend API server on port 8080."""
    os.environ["PYTHONPATH"] = str(ROOT_DIR)
    # Operator-owned domains the scope guard allows without warnings.
    # Only list domains you own or are explicitly authorized to test.
    os.environ.setdefault("RAKSHAK_ALLOWED_SCOPES", "rudrakshai.in")
    from rakshak.interface.viewer.server import start_viewer_server
    start_viewer_server("latest", port=8080)


def start_frontend():
    """Start the React Vite frontend dev server on port 3000."""
    npm_cmd = "npm.cmd" if sys.platform == "win32" else "npm"
    subprocess.run([npm_cmd, "run", "dev", "--", "--port", "3000", "--host", "0.0.0.0"], cwd=str(WEB_DIR))


def main():
    print("""
===============================================================
  🛡️  RakshakX — Autonomous AI Cybersecurity Platform
===============================================================
  [✓] Backend REST API  : http://127.0.0.1:8080
  [✓] OpenCode Bridge   : http://127.0.0.1:8787 (proxied via /v1)
  [✓] Web Console UI    : http://localhost:3000
  [✓] MCP Bridge Protocol: Stdio / JSON-RPC 2.0
  [✓] Isolated Sandbox   : Docker Kali Linux sidecar
===============================================================
  👉 OPEN YOUR BROWSER AT: http://localhost:3000
===============================================================
""")
    try:
        start_frontend()
    except KeyboardInterrupt:
        print("\n[*] Shutting down RakshakX platform cleanly...")


if __name__ == "__main__":
    main()
