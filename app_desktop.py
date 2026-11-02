#!/usr/bin/env python3
"""
JobFlow Desktop App Launcher

Creates a self-contained desktop application that:
- Boots a tiny local Flask server on a random free port
- Opens a native window (PyWebView) pointing to the server
- Seeds demo data on first run
- Stores data in the user's OS data directory
- Shuts down cleanly when the window closes
"""

import os
import sys
import time
import socket
import threading
import shutil
import json
from pathlib import Path

import webview
from platformdirs import user_data_dir

from app import create_app

APP_NAME = "JobFlow Tracker"
ORG = "pilotchoc"


def free_port():
    """Find a free port to run the Flask server on."""
    s = socket.socket()
    s.bind(('', 0))
    port = s.getsockname()[1]
    s.close()
    return port


def ensure_seed(data_dir: Path, seed_dir: Path):
    """Seed demo data only if there are no JSON files yet."""
    if any(data_dir.glob("*.json")):
        return
    
    data_dir.mkdir(parents=True, exist_ok=True)
    
    for name in ("jobs.json", "followups.json", "journal.json"):
        src = seed_dir / name
        dst = data_dir / name
        if src.exists():
            shutil.copyfile(src, dst)


def wait_until_up(port, timeout=10):
    """Wait for the Flask server to start up."""
    import http.client
    
    start_time = time.time()
    while time.time() - start_time < timeout:
        try:
            conn = http.client.HTTPConnection("127.0.0.1", port, timeout=0.5)
            conn.request("GET", "/api/health")
            response = conn.getresponse()
            if response.status in (200, 404):
                return True
        except Exception:
            pass
        time.sleep(0.2)
    return False


def run_server(app, port):
    """Run the Flask server with Waitress or fallback to built-in server."""
    try:
        from waitress import serve
        serve(app, host='127.0.0.1', port=port, threads=8)
    except Exception:
        app.run(host='127.0.0.1', port=port, debug=False, threaded=True)


def main():
    """Main entry point for the desktop application."""
    # Resolve bundle root when frozen
    root = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent))
    seed_dir = root / "seed_data"

    # Set up data directory
    data_dir = Path(user_data_dir(APP_NAME, ORG))
    os.environ["JOBFLOW_DATA_DIR"] = str(data_dir)
    ensure_seed(data_dir, seed_dir)

    # Create Flask app
    app = create_app(data_dir=data_dir)
    port = free_port()
    
    # Start server in background thread
    server_thread = threading.Thread(target=run_server, args=(app, port), daemon=True)
    server_thread.start()

    # Wait for server to be ready
    if not wait_until_up(port, timeout=12):
        # Fallback: show error window
        webview.create_window(
            APP_NAME, 
            html="<h3>Server failed to start. Please retry.</h3>",
            width=400,
            height=200
        )
        webview.start()
        os._exit(1)

    # Create main application window
    url = f"http://127.0.0.1:{port}/"
    window = webview.create_window(
        APP_NAME,
        url,
        width=1280,
        height=800,
        min_size=(800, 600),
        confirm_close=True,
        resizable=True
    )

    def on_closed():
        """Handle window close event."""
        os._exit(0)  # Hard exit to ensure Waitress thread stops

    # Start the webview
    webview.start(on_closed, debug=False)


if __name__ == "__main__":
    main()