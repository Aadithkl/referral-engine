#!/usr/bin/env python3
"""Start script — auto-detects port and launches the unified server."""

import socket
import sys
import os
import subprocess

# Landing page directory (overridable via LANDING_PAGE_DIR env var)
os.environ.setdefault("LANDING_PAGE_DIR", os.path.join(os.path.dirname(__file__) or ".", "static"))


def find_free_port(start=3000, max_attempts=20):
    """Auto-detect an available port starting from `start`."""
    for port in range(start, start + max_attempts):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            if s.connect_ex(("127.0.0.1", port)) != 0:
                return port
    raise RuntimeError(f"No free port found in range {start}-{start + max_attempts - 1}")


def main():
    host = os.environ.get("HOST", "0.0.0.0")
    port = int(os.environ.get("PORT", find_free_port()))

    # Use the venv Python if available
    venv_python = os.path.join(os.path.dirname(__file__), ".venv", "Scripts", "python.exe")
    python = venv_python if os.path.exists(venv_python) else sys.executable

    cmd = [
        python, "-m", "uvicorn",
        "src.referral_engine.main:app",
        "--host", host,
        "--port", str(port),
        "--reload" if os.environ.get("DEV") else "",
    ]
    cmd = [c for c in cmd if c]  # remove empty strings

    print(f"Referral Engine starting at http://{host}:{port}")
    print(f"   Landing page: {os.environ['LANDING_PAGE_DIR']}")
    print(f"   Press Ctrl+C to stop\n")

    try:
        subprocess.run(cmd, cwd=os.path.dirname(__file__))
    except KeyboardInterrupt:
        print("\nServer stopped.")


if __name__ == "__main__":
    main()
